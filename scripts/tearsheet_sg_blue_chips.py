"""Generate quantstats tear sheet for sg_blue_chips paper portfolio.

Reconstructs daily MTM from trades + yfinance closes, computes returns,
benchmarks vs ES3.SI (STI ETF).
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd
import yfinance as yf
import quantstats as qs

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "paper_trading_sg_blue_chips.db"
OUTPUT = ROOT / "reports" / "sgx_blue_chips_tearsheet_2026-04-12.html"
INITIAL_CAPITAL = 100_000.0
START = pd.Timestamp("2026-03-20")
DAY1 = pd.Timestamp("2026-03-25")
END = pd.Timestamp("2026-04-12")
BENCHMARK = "ES3.SI"


def load_trades() -> pd.DataFrame:
    with sqlite3.connect(DB) as conn:
        return pd.read_sql_query(
            "SELECT date, ticker, action, shares, value FROM trades ORDER BY date, id",
            conn,
            parse_dates=["date"],
        )


def apply_trade(shares: float, cash: float, action: str, qty: float, value: float) -> tuple[float, float]:
    # BUY: +shares, -cash. SELL & REBALANCE (sell-side trim): -shares, +cash.
    if action == "BUY":
        return shares + qty, cash - value
    return shares - qty, cash + value


def build_daily_positions(trades: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Return (holdings_by_ticker indexed by date, cash series indexed by date).

    Values are END-OF-DAY after all trades of that day.
    """
    tickers = sorted(trades["ticker"].unique())
    holdings = {t: 0.0 for t in tickers}
    cash = INITIAL_CAPITAL
    rows = []
    cash_by_date = {}
    for date, group in trades.groupby("date"):
        for _, r in group.iterrows():
            holdings[r.ticker], cash = apply_trade(
                holdings[r.ticker], cash, r.action, r.shares, r.value
            )
        rows.append({"date": date, **holdings})
        cash_by_date[date] = cash
    df = pd.DataFrame(rows).set_index("date")
    return df, pd.Series(cash_by_date, name="cash")


def expand_to_daily(holdings: pd.DataFrame, cash: pd.Series, trading_days: pd.DatetimeIndex) -> tuple[pd.DataFrame, pd.Series]:
    """Forward-fill holdings/cash across every trading day."""
    holdings_d = holdings.reindex(trading_days, method="ffill").fillna(0.0)
    cash_d = cash.reindex(trading_days, method="ffill").fillna(INITIAL_CAPITAL)
    return holdings_d, cash_d


def fetch_closes(tickers: list[str], start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    data = yf.download(
        tickers,
        start=start.strftime("%Y-%m-%d"),
        end=(end + pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
        auto_adjust=False,
        progress=False,
    )
    # yfinance returns Close as a top-level field when multi-ticker
    if isinstance(data.columns, pd.MultiIndex):
        closes = data["Close"]
    else:
        closes = data[["Close"]].rename(columns={"Close": tickers[0]})
    closes.index = pd.to_datetime(closes.index)
    return closes


def main() -> None:
    trades = load_trades()
    holdings_eod, cash_eod = build_daily_positions(trades)
    all_tickers = sorted(set(trades["ticker"]) | {BENCHMARK})

    closes = fetch_closes(all_tickers, START, END)
    closes = closes.loc[(closes.index >= START) & (closes.index <= END)].dropna(how="all")
    trading_days = closes.index

    holdings_d, cash_d = expand_to_daily(holdings_eod, cash_eod, trading_days)

    # Align columns
    held_tickers = [t for t in holdings_d.columns if t in closes.columns]
    mv = (holdings_d[held_tickers] * closes[held_tickers]).sum(axis=1)
    portfolio_value = mv + cash_d
    portfolio_value.name = "portfolio_value"

    # Anchor: on 2026-03-20 (before any trades) PV == INITIAL_CAPITAL.
    # Prepend anchor row so returns start fresh.
    anchor_date = trading_days[0]
    if anchor_date > START:
        portfolio_value.loc[START] = INITIAL_CAPITAL
        portfolio_value = portfolio_value.sort_index()

    # Slice Day 1 → end
    pv = portfolio_value.loc[portfolio_value.index <= END]
    # Use first valid date on/before DAY1 as baseline
    baseline_date = pv.index[pv.index <= DAY1][-1]
    returns = pv.pct_change().dropna()
    returns = returns.loc[returns.index >= baseline_date]
    # tz-naive for quantstats
    returns.index = returns.index.tz_localize(None)
    returns.name = "sg_blue_chips"

    # Benchmark returns
    bench_px = closes[BENCHMARK].dropna()
    bench_px.index = bench_px.index.tz_localize(None)
    bench_returns = bench_px.pct_change().dropna()
    bench_returns = bench_returns.loc[bench_returns.index >= baseline_date]
    bench_returns.name = BENCHMARK

    # Align
    idx = returns.index.intersection(bench_returns.index)
    returns = returns.loc[idx]
    bench_returns = bench_returns.loc[idx]

    print("=" * 70)
    print("sg_blue_chips Forward Test  |  Mar 25 → Apr 12 2026")
    print("=" * 70)
    print(f"Trading days in sample: {len(returns)}")
    print(f"Baseline date: {baseline_date.date()}   End date: {returns.index[-1].date()}")
    print()
    print("Daily portfolio values:")
    print(pv.loc[returns.index[0] - pd.Timedelta(days=7):].round(2).to_string())
    print()

    qs.extend_pandas()
    cum_ret = (1 + returns).prod() - 1
    cum_bench = (1 + bench_returns).prod() - 1
    sharpe = qs.stats.sharpe(returns)
    max_dd = qs.stats.max_drawdown(returns)
    win_rate = qs.stats.win_rate(returns)

    print("KEY STATS (portfolio):")
    print(f"  Cumulative return   : {cum_ret*100:+.2f}%")
    print(f"  Sharpe ratio (annl.): {sharpe:.3f}")
    print(f"  Max drawdown        : {max_dd*100:+.2f}%")
    print(f"  Win rate            : {win_rate*100:.1f}%")
    print()
    print("BENCHMARK (ES3.SI, STI ETF):")
    print(f"  Cumulative return   : {cum_bench*100:+.2f}%")
    print(f"  Excess return       : {(cum_ret - cum_bench)*100:+.2f}%")
    print()
    print(f"NOTE: only {len(returns)} trading days of data. Sharpe at this sample")
    print("      size is NOT statistically meaningful — directional check only.")
    print()

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    qs.reports.html(
        returns,
        benchmark=bench_returns,
        output=str(OUTPUT),
        title="sg_blue_chips Forward Test — Mar 25 to Apr 12 2026",
    )
    print(f"Tear sheet written → {OUTPUT}")


if __name__ == "__main__":
    main()
