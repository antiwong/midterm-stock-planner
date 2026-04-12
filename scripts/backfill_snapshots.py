"""Backfill daily_snapshots for every paper-trading DB.

For each portfolio:
  - Reconstruct EOD holdings + cash from the trades table.
  - Fetch daily closes via yfinance for every ticker ever held + the benchmark.
  - Use the benchmark's trading-day index as the portfolio's calendar
    (SGX vs NYSE holidays differ).
  - Mark every trading day from the earliest existing snapshot → today to market.
  - INSERT OR REPLACE into daily_snapshots (overwrites stale rows).
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path
from typing import Dict

import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"

# watchlist -> benchmark ticker
PORTFOLIOS: Dict[str, str] = {
    "moby_picks":        "SPY",
    "tech_giants":       "SPY",
    "semiconductors":    "SPY",
    "precious_metals":   "SPY",
    "sg_reits":          "ES3.SI",
    "sg_blue_chips":     "ES3.SI",
    "anthony_watchlist": "SPY",
    "sp500":             "SPY",
    "clean_energy":      "SPY",
    "etfs":              "SPY",
}


def ensure_schema(conn: sqlite3.Connection) -> None:
    cols = {r[1] for r in conn.execute("PRAGMA table_info(daily_snapshots)").fetchall()}
    if "invested_pct" not in cols:
        conn.execute("ALTER TABLE daily_snapshots ADD COLUMN invested_pct REAL")
    if "positions_count" not in cols:
        conn.execute("ALTER TABLE daily_snapshots ADD COLUMN positions_count INTEGER")
    conn.commit()


def fetch_closes(tickers: list[str], start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    data = yf.download(
        tickers,
        start=(start - pd.Timedelta(days=5)).strftime("%Y-%m-%d"),
        end=(end + pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
        auto_adjust=False,
        progress=False,
    )
    if isinstance(data.columns, pd.MultiIndex):
        closes = data["Close"]
    else:
        closes = data[["Close"]].rename(columns={"Close": tickers[0]})
    closes.index = pd.to_datetime(closes.index).tz_localize(None)
    return closes


def build_eod_state(trades: pd.DataFrame, initial_cash: float) -> tuple[pd.DataFrame, pd.Series]:
    """Return (holdings_by_ticker_at_eod, cash_at_eod) indexed by trade date."""
    tickers = sorted(trades["ticker"].unique()) if len(trades) else []
    holdings = {t: 0.0 for t in tickers}
    cash = initial_cash
    hold_rows = []
    cash_rows: Dict[pd.Timestamp, float] = {}
    for date, group in trades.groupby("date"):
        for _, r in group.iterrows():
            if r.action == "BUY":
                holdings[r.ticker] += r.shares
                cash -= r.value
            else:  # SELL and REBALANCE both trim shares and return cash
                holdings[r.ticker] -= r.shares
                cash += r.value
        hold_rows.append({"date": date, **holdings})
        cash_rows[date] = cash
    if not hold_rows:
        # No trades yet — return empty frame, will forward-fill to 0.0
        return pd.DataFrame(columns=tickers), pd.Series(dtype=float)
    df = pd.DataFrame(hold_rows).set_index("date")
    return df, pd.Series(cash_rows)


def backfill_portfolio(wl: str, benchmark: str, today: pd.Timestamp) -> dict:
    db = DATA_DIR / f"paper_trading_{wl}.db"
    if not db.exists():
        return {"wl": wl, "error": "no DB"}

    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row
        ensure_schema(conn)
        state = conn.execute(
            "SELECT initial_value FROM portfolio_state WHERE id = 1"
        ).fetchone()
        if state is None:
            return {"wl": wl, "error": "no portfolio_state"}
        initial = float(state["initial_value"]) or 1.0
        actual_cash_row = conn.execute(
            "SELECT cash FROM portfolio_state WHERE id = 1"
        ).fetchone()
        actual_cash = float(actual_cash_row["cash"]) if actual_cash_row else None
        earliest_snap = conn.execute(
            "SELECT MIN(date) FROM daily_snapshots"
        ).fetchone()[0]
        trades = pd.read_sql_query(
            "SELECT date, ticker, action, shares, value FROM trades ORDER BY date, id",
            conn,
            parse_dates=["date"],
        )

    if earliest_snap is None and trades.empty:
        return {"wl": wl, "error": "no snapshots, no trades"}
    earliest = pd.Timestamp(earliest_snap) if earliest_snap else trades["date"].min()

    # Guard: if ANY non-trivial trade is missing a share count (shares==0 but value>0),
    # the local trades table is incomplete — positions are authoritative via an external
    # broker (Alpaca). Reconstruction would treat those as cash-only sinks and produce
    # nonsensical negative equity. Skip and rely on forward EOD snapshots.
    broken_rows = (not trades.empty) and (
        ((trades["shares"].abs() < 1e-9) & (trades["value"].abs() > 1.0)).any()
    )

    # Cross-check: reconstruct cash from trades and compare with portfolio_state.cash.
    # Portfolios fed by BOTH run_daily_fast (local sim) AND paper_trading.py (Alpaca
    # fills) can have mixed trade conventions, so trade-based reconstruction won't
    # agree with the broker-authoritative cash. Skip those.
    cash_diverged = False
    if not broken_rows and not trades.empty and actual_cash is not None:
        _, reconstructed = build_eod_state(trades, initial)
        if not reconstructed.empty:
            tolerance = max(0.05 * initial, 100.0)
            if abs(float(reconstructed.iloc[-1]) - actual_cash) > tolerance:
                cash_diverged = True

    if broken_rows or cash_diverged:
        with sqlite3.connect(db) as conn:
            # Strip any non-trading-day rows (Sunday pollution from Step 1)
            closes_bench = fetch_closes([benchmark], earliest, today)
            cal_bench = closes_bench[benchmark].dropna().index
            cal_bench = cal_bench[(cal_bench >= earliest) & (cal_bench <= today)]
            valid = {d.strftime("%Y-%m-%d") for d in cal_bench}
            existing = [r[0] for r in conn.execute("SELECT date FROM daily_snapshots").fetchall()]
            stale = [d for d in existing if d not in valid]
            for d in stale:
                conn.execute("DELETE FROM daily_snapshots WHERE date = ?", (d,))
            conn.commit()
            final_count = conn.execute("SELECT COUNT(*) FROM daily_snapshots").fetchone()[0]
        return {"wl": wl, "skipped_alpaca_synced": True, "rows_kept": final_count,
                "stale_deleted": len(stale),
                "reason": "cash divergence" if cash_diverged else "zero-share trades"}

    tickers_needed = sorted(set(trades["ticker"]) | {benchmark}) if not trades.empty else [benchmark]
    closes = fetch_closes(tickers_needed, earliest, today)
    if benchmark not in closes.columns:
        return {"wl": wl, "error": f"benchmark {benchmark} not fetched"}

    # Benchmark-defined trading calendar
    cal = closes[benchmark].dropna().index
    cal = cal[(cal >= earliest) & (cal <= today)]
    if len(cal) == 0:
        return {"wl": wl, "error": "empty calendar"}

    hold_eod, cash_eod = build_eod_state(trades, initial)
    hold_d = hold_eod.reindex(cal, method="ffill").fillna(0.0) if not hold_eod.empty else pd.DataFrame(0.0, index=cal, columns=[])
    cash_d = cash_eod.reindex(cal, method="ffill").fillna(initial) if not cash_eod.empty else pd.Series(initial, index=cal)

    held_cols = [t for t in hold_d.columns if t in closes.columns]
    px = closes[held_cols].reindex(cal).ffill()  # carry last close for dates with no quote (rare)
    mv = (hold_d[held_cols] * px).sum(axis=1) if held_cols else pd.Series(0.0, index=cal)
    pv = mv + cash_d

    written = 0
    with sqlite3.connect(db) as conn:
        # Remove any existing rows outside the benchmark trading calendar
        # (e.g. weekend snapshots accidentally written by an unconditional pass).
        valid_dates = {d.strftime("%Y-%m-%d") for d in cal}
        existing = [r[0] for r in conn.execute(
            "SELECT date FROM daily_snapshots WHERE date >= ?", (earliest.strftime("%Y-%m-%d"),)
        ).fetchall()]
        for d in existing:
            if d not in valid_dates:
                conn.execute("DELETE FROM daily_snapshots WHERE date = ?", (d,))
        conn.commit()

        prev_pv = None
        for d in cal:
            d_str = d.strftime("%Y-%m-%d")
            pv_val = float(pv.loc[d])
            cash_val = float(cash_d.loc[d])
            inv_val = float(mv.loc[d])
            inv_pct = inv_val / pv_val if pv_val > 0 else 0.0
            pos_count = int((hold_d.loc[d] > 1e-6).sum()) if held_cols else 0
            daily_ret = (pv_val / prev_pv - 1.0) if prev_pv else 0.0
            cum = (pv_val / initial) - 1.0
            conn.execute(
                "INSERT OR REPLACE INTO daily_snapshots "
                "(date, portfolio_value, cash, invested, daily_return, cumulative_return, "
                "invested_pct, positions_count) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (d_str, pv_val, cash_val, inv_val, daily_ret, cum, inv_pct, pos_count),
            )
            prev_pv = pv_val
            written += 1
        conn.commit()

    return {
        "wl": wl,
        "first": cal[0].strftime("%Y-%m-%d"),
        "last": cal[-1].strftime("%Y-%m-%d"),
        "written": written,
        "pv_final": float(pv.iloc[-1]),
        "cum_final": (float(pv.iloc[-1]) / initial) - 1.0,
    }


def main() -> None:
    today = pd.Timestamp.today().normalize()
    results = []
    for wl, bench in PORTFOLIOS.items():
        print(f"  backfilling {wl} (benchmark={bench})...", flush=True)
        r = backfill_portfolio(wl, bench, today)
        results.append(r)
        if "error" in r:
            print(f"    ERROR: {r['error']}")
        elif r.get("skipped_alpaca_synced"):
            print(f"    SKIPPED ({r.get('reason','broker-authoritative')}) "
                  f"— {r['stale_deleted']} non-calendar rows deleted, {r['rows_kept']} kept")
        else:
            print(f"    {r['first']} → {r['last']}  rows={r['written']}  "
                  f"PV=${r['pv_final']:,.0f}  cum={r['cum_final']:+.2%}")

    # Audit: count rows + check for gaps against the ACTUAL benchmark calendar
    print("\n" + "=" * 90)
    print(f"{'portfolio':25s} {'bench':>7s} {'rows':>5s} {'first':>12s} {'last':>12s} {'gaps':>5s}  notes")
    print("-" * 90)
    total = 0
    for wl, bench in PORTFOLIOS.items():
        db = DATA_DIR / f"paper_trading_{wl}.db"
        with sqlite3.connect(db) as c:
            rows = [r[0] for r in c.execute("SELECT date FROM daily_snapshots ORDER BY date").fetchall()]
        if not rows:
            print(f"{wl:25s} {bench:>7s} {'0':>5s}  (no snapshots)")
            continue
        first, last = rows[0], rows[-1]
        bench_px = fetch_closes([bench], pd.Timestamp(first), pd.Timestamp(last))
        cal = bench_px[bench].dropna().index
        cal = cal[(cal >= pd.Timestamp(first)) & (cal <= pd.Timestamp(last))]
        expected = {d.strftime("%Y-%m-%d") for d in cal}
        missing = expected - set(rows)
        extra = set(rows) - expected
        note = ""
        if missing:
            note += f"missing={sorted(missing)} "
        if extra:
            note += f"extra={sorted(extra)}"
        total += len(rows)
        print(f"{wl:25s} {bench:>7s} {len(rows):>5d} {first:>12s} {last:>12s} "
              f"{len(missing):>5d}  {note}")
    print("-" * 90)
    print(f"{'TOTAL':25s} {'':>7s} {total:>5d}")


if __name__ == "__main__":
    main()
