"""
Tiger Broker – Paper & Live Trading Integration
================================================
Wraps the Tiger Open API (tigeropen SDK) for paper and live trading.

This module provides order execution, position management, and portfolio
rebalancing against a Tiger Brokers account.  All public methods return
plain Python dicts/lists for easy serialization — matching the AlpacaBroker
interface so it can be used as a drop-in replacement.

Setup:
    export TIGER_BROKERS_ID=your_tiger_id
    export TIGER_BROKERS_SECRET_KEY=your_rsa_private_key
    export TIGER_BROKERS_ACCOUNT=your_account_number  (optional — auto-discovered)

    Or create a .env file with these values.
"""

import math
import os
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ---------------------------------------------------------------------------
# SDK imports – gracefully degrade when tigeropen is not installed
# ---------------------------------------------------------------------------
try:
    from tigeropen.tiger_open_config import TigerOpenClientConfig
    from tigeropen.common.consts import Language, Market, TradingSession, Currency
    from tigeropen.trade.trade_client import TradeClient
    from tigeropen.quote.quote_client import QuoteClient
    from tigeropen.common.util.contract_utils import stock_contract
    from tigeropen.common.util.order_utils import market_order, limit_order
    TIGER_TRADING_AVAILABLE = True
except ImportError:
    TIGER_TRADING_AVAILABLE = False

logger = logging.getLogger(__name__)

# Account IDs that must never be traded on
_PROTECTED_ACCOUNTS = frozenset({"50411574", "50992715"})


def _safe_float(val, default=0.0):
    """Return val as float, replacing inf/nan with default."""
    if val is None:
        return default
    f = float(val)
    if math.isinf(f) or math.isnan(f):
        return default
    return f


def _build_config(
    tiger_id: str,
    private_key: str,
    account: str,
) -> "TigerOpenClientConfig":
    """Create a TigerOpenClientConfig from credentials."""
    config = TigerOpenClientConfig()
    config.private_key = private_key
    config.tiger_id = tiger_id
    config.account = account
    config.language = Language.en_US
    return config


class TigerBroker:
    """Thin wrapper around Tiger's Open API for paper/live trading.

    Every public method returns plain dicts/lists (never raw SDK objects)
    so callers can serialise results to JSON or store them in SQLite.

    Interface is compatible with AlpacaBroker for drop-in use.
    """

    def __init__(
        self,
        tiger_id: Optional[str] = None,
        private_key: Optional[str] = None,
        account: Optional[str] = None,
        paper: bool = True,
    ):
        if not TIGER_TRADING_AVAILABLE:
            raise ImportError(
                "tigeropen SDK not installed. Run: pip install tigeropen"
            )

        self.tiger_id = tiger_id or os.environ.get("TIGER_BROKERS_ID", "")
        self.private_key = private_key or os.environ.get("TIGER_BROKERS_SECRET_KEY", "")

        if not self.tiger_id or not self.private_key:
            raise ValueError(
                "Tiger API credentials not found. Set TIGER_BROKERS_ID and "
                "TIGER_BROKERS_SECRET_KEY environment variables or pass them directly."
            )

        self.paper = paper

        # Discover or use provided account
        if account:
            self._account = account
        else:
            self._account = os.environ.get("TIGER_BROKERS_ACCOUNT", "")

        # If no account specified, auto-discover
        if not self._account:
            self._account = self._discover_account()

        # Safety check
        if self._account in _PROTECTED_ACCOUNTS:
            raise ValueError(
                f"Account {self._account} is protected and cannot be used for trading. "
                "Use a different account."
            )

        self._config = _build_config(self.tiger_id, self.private_key, self._account)
        self._trade_client = TradeClient(self._config)
        self._quote_client = None  # lazy init
        logger.info(
            "TigerBroker initialised (account=%s, paper=%s)",
            self._account, self.paper,
        )

    def _discover_account(self) -> str:
        """Auto-discover the appropriate account (paper or first real)."""
        config = _build_config(self.tiger_id, self.private_key, "")
        # Need a temporary config with any account to call get_managed_accounts
        config.account = "discovery"
        try:
            tc = TradeClient(config)
            accounts = tc.get_managed_accounts()
        except Exception:
            # Some SDK versions need a valid account; try without
            raise ValueError(
                "Could not discover Tiger accounts. "
                "Set TIGER_BROKERS_ACCOUNT in your environment."
            )

        if not accounts:
            raise ValueError("No Tiger accounts found for this tiger_id.")

        for a in accounts:
            acct_id = a.account if hasattr(a, "account") else str(a)
            acct_type = getattr(a, "account_type", "")

            # Skip protected accounts
            if acct_id in _PROTECTED_ACCOUNTS:
                continue

            if self.paper and acct_type == "PAPER":
                logger.info("Auto-discovered paper account: %s", acct_id)
                return acct_id
            elif not self.paper and acct_type != "PAPER":
                logger.info("Auto-discovered live account: %s", acct_id)
                return acct_id

        # Fallback: if paper requested but no paper account, use first non-protected
        for a in accounts:
            acct_id = a.account if hasattr(a, "account") else str(a)
            if acct_id not in _PROTECTED_ACCOUNTS:
                logger.warning("Using fallback account: %s", acct_id)
                return acct_id

        raise ValueError("No suitable Tiger account found.")

    @property
    def quote_client(self) -> "QuoteClient":
        """Lazy-init quote client."""
        if self._quote_client is None:
            self._quote_client = QuoteClient(self._config)
        return self._quote_client

    # ------------------------------------------------------------------
    # Account
    # ------------------------------------------------------------------

    def get_account(self) -> dict:
        """Return account summary (equity, cash, buying_power, etc.).

        Returns dict with keys matching AlpacaBroker output:
        equity, cash, buying_power, portfolio_value, etc.
        """
        try:
            assets = self._trade_client.get_assets()
            if not assets:
                return {"account": self._account}

            a = assets[0] if isinstance(assets, list) else assets
            summary = a._summary if hasattr(a, "_summary") else a

            return {
                "account": self._account,
                "equity": _safe_float(getattr(summary, "net_liquidation", 0)),
                "net_liquidation": _safe_float(getattr(summary, "net_liquidation", 0)),
                "cash": _safe_float(getattr(summary, "cash", 0)),
                "buying_power": _safe_float(getattr(summary, "buying_power", 0)),
                "portfolio_value": _safe_float(getattr(summary, "gross_position_value", 0)),
                "unrealized_pnl": _safe_float(getattr(summary, "unrealized_pnl", 0)),
                "realized_pnl": _safe_float(getattr(summary, "realized_pnl", 0)),
                "currency": getattr(summary, "currency", "USD"),
            }
        except Exception as exc:
            logger.error("Failed to get account: %s", exc)
            raise RuntimeError(f"Failed to get account: {exc}") from exc

    # ------------------------------------------------------------------
    # Positions
    # ------------------------------------------------------------------

    def get_positions(self) -> List[dict]:
        """Return all open positions as a list of dicts."""
        try:
            positions = self._trade_client.get_positions()
            if not positions:
                return []
            return [self._position_to_dict(p) for p in positions]
        except Exception as exc:
            logger.error("Failed to get positions: %s", exc)
            raise RuntimeError(f"Failed to get positions: {exc}") from exc

    def get_position(self, symbol: str) -> Optional[dict]:
        """Return a single position dict, or None if not held."""
        positions = self.get_positions()
        symbol_upper = symbol.upper()
        for p in positions:
            if p.get("symbol", "").upper() == symbol_upper:
                return p
        return None

    @staticmethod
    def _position_to_dict(pos) -> dict:
        """Convert a Tiger Position object to a plain dict."""
        contract = getattr(pos, "contract", None)
        symbol = ""
        if contract:
            symbol = getattr(contract, "symbol", "") or str(contract)

        quantity = getattr(pos, "quantity", 0) or 0
        avg_cost = getattr(pos, "average_cost", 0) or 0
        market_price = getattr(pos, "market_price", 0) or 0
        market_value = getattr(pos, "market_value", 0) or 0
        unrealized_pnl = getattr(pos, "unrealized_pnl", 0) or 0

        return {
            "symbol": symbol,
            "qty": str(quantity),
            "avg_entry_price": str(avg_cost),
            "current_price": str(market_price),
            "market_value": str(market_value),
            "unrealized_pl": str(unrealized_pnl),
            "unrealized_plpc": str(
                (market_price / avg_cost - 1) if avg_cost > 0 else 0
            ),
            "side": "long" if quantity > 0 else "short",
        }

    # ------------------------------------------------------------------
    # Orders
    # ------------------------------------------------------------------

    def submit_order(
        self,
        symbol: str,
        qty: float,
        side: str,
        type: str = "market",
        time_in_force: str = "day",
        limit_price: Optional[float] = None,
    ) -> dict:
        """Submit an order. Interface matches AlpacaBroker.submit_order."""
        symbol_up = symbol.upper()
        # Tiger rejects market orders for SGX tickers ("Order type is invalid").
        # Auto-convert to a limit order with a 1% slippage buffer using current price.
        is_sgx = symbol_up.endswith(".SI") or symbol_up.endswith(".SG")
        if is_sgx and type.lower() == "market":
            price = self._get_latest_price(symbol_up)
            if price <= 0:
                raise RuntimeError(f"Cannot get price for {symbol} to build SGX limit order")
            buffer = 1.01 if side.lower() == "buy" else 0.99
            limit_price = round(price * buffer, 2)
            type = "limit"
            logger.info("SGX %s: market->limit @ %.2f (spot %.2f)", symbol_up, limit_price, price)

        contract = stock_contract(symbol=symbol_up, currency="USD")
        action = "BUY" if side.lower() == "buy" else "SELL"

        try:
            if type.lower() == "limit":
                if limit_price is None:
                    raise ValueError("limit_price required for limit orders")
                order = limit_order(
                    account=self._account,
                    contract=contract,
                    action=action,
                    limit_price=limit_price,
                    quantity=int(qty),
                )
            else:
                order = market_order(
                    account=self._account,
                    contract=contract,
                    action=action,
                    quantity=int(qty),
                )

            result = self._trade_client.place_order(order)
            logger.info("Order submitted: %s %s %s @ %s", side, qty, symbol, type)
            return self._order_to_dict(result, symbol, side, qty)
        except Exception as exc:
            logger.error("Order failed (%s %s %s): %s", side, qty, symbol, exc)
            raise RuntimeError(f"Order failed ({side} {qty} {symbol}): {exc}") from exc

    def submit_market_order(
        self,
        symbol: str,
        notional: Optional[float] = None,
        qty: Optional[float] = None,
        side: str = "buy",
    ) -> dict:
        """Submit a market order by dollar amount or share qty.

        Tiger doesn't support notional orders natively, so we convert
        notional to qty using the current market price.
        """
        if notional is not None and qty is not None:
            raise ValueError("Provide either notional or qty, not both")
        if notional is None and qty is None:
            raise ValueError("Provide either notional or qty")

        if notional is not None:
            # Convert notional to qty using current price
            price = self._get_latest_price(symbol)
            if price <= 0:
                raise RuntimeError(f"Cannot get price for {symbol} to convert notional to qty")
            qty = int(notional / price)
            if qty < 1:
                logger.warning(
                    "Notional $%.2f too small for %s @ $%.2f (< 1 share)",
                    notional, symbol, price,
                )
                return {
                    "symbol": symbol,
                    "side": side,
                    "status": "skipped",
                    "reason": f"notional ${notional:.2f} < 1 share @ ${price:.2f}",
                }

        return self.submit_order(symbol=symbol, qty=qty, side=side, type="market")

    def get_orders(
        self, status: str = "open", limit: int = 100
    ) -> List[dict]:
        """Return orders filtered by status ('open', 'closed', 'all')."""
        try:
            if status.lower() == "open":
                orders = self._trade_client.get_open_orders()
            elif status.lower() == "closed":
                orders = self._trade_client.get_filled_orders(
                    start_date=(datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
                    end_date=datetime.now().strftime("%Y-%m-%d"),
                )
            else:
                orders = self._trade_client.get_orders(
                    start_date=(datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
                    end_date=datetime.now().strftime("%Y-%m-%d"),
                )
            if not orders:
                return []
            return [self._raw_order_to_dict(o) for o in orders[:limit]]
        except Exception as exc:
            logger.error("Failed to get orders: %s", exc)
            raise RuntimeError(f"Failed to get orders: {exc}") from exc

    def get_order(self, order_id: str) -> dict:
        """Return a single order by ID."""
        try:
            order = self._trade_client.get_order(id=int(order_id))
            return self._raw_order_to_dict(order)
        except Exception as exc:
            logger.error("Failed to get order %s: %s", order_id, exc)
            raise RuntimeError(f"Failed to get order {order_id}: {exc}") from exc

    def cancel_all_orders(self) -> None:
        """Cancel every open order."""
        try:
            open_orders = self._trade_client.get_open_orders()
            if open_orders:
                for o in open_orders:
                    oid = getattr(o, "id", None) or getattr(o, "order_id", None)
                    if oid:
                        self._trade_client.cancel_order(id=int(oid))
            logger.info("All open orders cancelled")
        except Exception as exc:
            logger.error("Failed to cancel orders: %s", exc)
            raise RuntimeError(f"Failed to cancel orders: {exc}") from exc

    # ------------------------------------------------------------------
    # Close positions
    # ------------------------------------------------------------------

    def close_position(self, symbol: str) -> dict:
        """Close an entire position in *symbol*."""
        pos = self.get_position(symbol)
        if not pos:
            return {"symbol": symbol, "status": "no_position"}

        qty = abs(float(pos.get("qty", 0)))
        if qty < 1:
            return {"symbol": symbol, "status": "no_position", "qty": qty}

        current_side = pos.get("side", "long")
        sell_side = "sell" if current_side == "long" else "buy"

        return self.submit_order(
            symbol=symbol, qty=qty, side=sell_side, type="market"
        )

    def close_all_positions(self) -> List[dict]:
        """Liquidate all open positions."""
        self.cancel_all_orders()
        positions = self.get_positions()
        results = []
        for p in positions:
            symbol = p.get("symbol", "")
            if symbol:
                try:
                    result = self.close_position(symbol)
                    results.append(result)
                except Exception as exc:
                    logger.warning("Could not close %s: %s", symbol, exc)
                    results.append({"symbol": symbol, "error": str(exc)})
        logger.info("Closed all positions (%d)", len(results))
        return results

    # ------------------------------------------------------------------
    # Wait / polling
    # ------------------------------------------------------------------

    def wait_for_order(self, order_id: str, timeout: int = 30) -> dict:
        """Poll until an order reaches a terminal state or timeout."""
        terminal = {"filled", "cancelled", "expired", "rejected", "inactive"}
        deadline = time.time() + timeout

        while time.time() < deadline:
            try:
                order = self.get_order(order_id)
                status = str(order.get("status", "")).lower()
                if status in terminal:
                    return order
            except Exception:
                pass
            time.sleep(1)

        return self.get_order(order_id)

    # ------------------------------------------------------------------
    # Market clock
    # ------------------------------------------------------------------

    def is_market_open(self) -> bool:
        """Return True if the US equity market is currently open."""
        try:
            statuses = self.quote_client.get_market_status(Market.US)
            if statuses:
                s = statuses[0]
                trading_status = getattr(s, "trading_status", "")
                return str(trading_status).upper() in ("TRADING", "OPEN")
            return False
        except Exception as exc:
            logger.warning("Could not check market status: %s", exc)
            return False

    def get_clock(self) -> dict:
        """Return market clock info."""
        try:
            statuses = self.quote_client.get_market_status(Market.US)
            if statuses:
                s = statuses[0]
                return {
                    "is_open": str(getattr(s, "trading_status", "")).upper()
                    in ("TRADING", "OPEN"),
                    "market": getattr(s, "market", "US"),
                    "status": str(getattr(s, "status", "")),
                    "trading_status": str(getattr(s, "trading_status", "")),
                    "open_time": str(getattr(s, "open_time", "")),
                }
            return {"is_open": False}
        except Exception as exc:
            logger.error("Failed to get clock: %s", exc)
            raise RuntimeError(f"Failed to get clock: {exc}") from exc

    # ------------------------------------------------------------------
    # Portfolio rebalance
    # ------------------------------------------------------------------

    def rebalance_portfolio(
        self,
        target_weights: Dict[str, float],
        portfolio_value: Optional[float] = None,
        managed_universe: Optional[List[str]] = None,
    ) -> List[dict]:
        """Rebalance the portfolio to match target_weights.

        Same interface and strategy as AlpacaBroker.rebalance_portfolio:
        1. Sell positions NOT in target_weights.
        2. Trim over-weight positions.
        3. Wait for sells.
        4. Buy under-weight positions.

        If managed_universe is provided, Phase 1 only liquidates positions
        within that set — positions outside are left untouched (used for
        market-scoped rebalances, e.g. SG-only or US-only runs).
        """
        total_weight = sum(target_weights.values())
        if total_weight > 1.01:
            raise ValueError(
                f"Target weights sum to {total_weight:.3f} (> 1.0). "
                "Reduce allocations."
            )

        target_weights = {sym.upper(): w for sym, w in target_weights.items()}
        managed_set = {s.upper() for s in managed_universe} if managed_universe else None

        if portfolio_value is None:
            acct = self.get_account()
            portfolio_value = float(acct.get("equity", 0))
            if portfolio_value <= 0:
                raise RuntimeError("Account equity is zero – cannot rebalance.")

        current_positions = {p["symbol"]: p for p in self.get_positions()}
        trades: List[dict] = []
        sell_order_ids: List[str] = []

        # Phase 1: sell everything not in target (scoped to managed_universe if given)
        to_liquidate = set(current_positions) - set(target_weights)
        if managed_set is not None:
            to_liquidate &= managed_set
        for sym in to_liquidate:
            logger.info("Rebalance: liquidating %s (not in target)", sym)
            try:
                order = self.close_position(sym)
                trades.append({"action": "sell_all", "symbol": sym, "order": order})
                oid = order.get("id") or order.get("order_id")
                if oid:
                    sell_order_ids.append(str(oid))
            except Exception as exc:
                logger.warning("Could not close %s: %s", sym, exc)
                trades.append({"action": "sell_all", "symbol": sym, "error": str(exc)})

        # Phase 2: trim over-weight positions
        for sym, target_w in target_weights.items():
            target_value = portfolio_value * target_w
            current_value = abs(float(current_positions.get(sym, {}).get("market_value", 0)))
            delta_value = target_value - current_value

            if abs(delta_value) < max(5.0, portfolio_value * 0.005):
                continue

            if delta_value < 0:
                sell_notional = abs(delta_value)
                logger.info("Rebalance: trimming %s by $%.2f", sym, sell_notional)
                try:
                    order = self.submit_market_order(
                        symbol=sym, notional=sell_notional, side="sell"
                    )
                    trades.append({
                        "action": "sell_trim", "symbol": sym,
                        "notional": sell_notional, "order": order,
                    })
                    oid = order.get("id") or order.get("order_id")
                    if oid:
                        sell_order_ids.append(str(oid))
                except Exception as exc:
                    logger.warning("Could not trim %s: %s", sym, exc)
                    trades.append({"action": "sell_trim", "symbol": sym, "error": str(exc)})

        # Wait for sells to fill
        for oid in sell_order_ids:
            self.wait_for_order(oid, timeout=15)

        # Phase 3: buy under-weight positions
        acct = self.get_account()
        available_cash = float(acct.get("cash", 0))

        for sym, target_w in target_weights.items():
            target_value = portfolio_value * target_w
            pos = self.get_position(sym)
            current_value = abs(float(pos["market_value"])) if pos else 0.0
            buy_notional = target_value - current_value

            if buy_notional < max(5.0, portfolio_value * 0.005):
                continue

            buy_notional = min(buy_notional, available_cash)
            if buy_notional < 1.0:
                continue

            logger.info("Rebalance: buying $%.2f of %s", buy_notional, sym)
            try:
                order = self.submit_market_order(
                    symbol=sym, notional=buy_notional, side="buy"
                )
                trades.append({
                    "action": "buy", "symbol": sym,
                    "notional": buy_notional, "order": order,
                })
                available_cash -= buy_notional
            except Exception as exc:
                logger.warning("Could not buy %s: %s", sym, exc)
                trades.append({"action": "buy", "symbol": sym, "error": str(exc)})

        logger.info("Rebalance complete: %d trades executed", len(trades))
        return trades

    # ------------------------------------------------------------------
    # Monitoring helpers (read-only — safe for live accounts)
    # ------------------------------------------------------------------

    def get_portfolio_summary(self) -> dict:
        """Comprehensive portfolio snapshot for monitoring."""
        acct = self.get_account()
        positions = self.get_positions()

        total_mkt_value = sum(abs(float(p.get("market_value", 0))) for p in positions)
        total_unrealized = sum(float(p.get("unrealized_pl", 0)) for p in positions)

        return {
            "account": self._account,
            "timestamp": datetime.now().isoformat(),
            "equity": acct.get("equity", 0),
            "cash": acct.get("cash", 0),
            "buying_power": acct.get("buying_power", 0),
            "positions_count": len(positions),
            "total_market_value": total_mkt_value,
            "total_unrealized_pnl": total_unrealized,
            "positions": positions,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_latest_price(self, symbol: str) -> float:
        """Get latest price for a symbol. Falls back to delay briefs."""
        try:
            briefs = self.quote_client.get_stock_delay_briefs([symbol.upper()])
            if briefs is not None and len(briefs) > 0:
                return float(briefs.iloc[0].get("close", 0) or briefs.iloc[0].get("latest_price", 0))
        except Exception:
            pass

        # Fallback: try yfinance
        try:
            import yfinance as yf
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="1d")
            if not hist.empty:
                return float(hist["Close"].iloc[-1])
        except Exception:
            pass

        return 0.0

    @staticmethod
    def _order_to_dict(order_result, symbol: str, side: str, qty: float) -> dict:
        """Convert a Tiger order result to a plain dict."""
        if isinstance(order_result, dict):
            return order_result

        oid = getattr(order_result, "id", None) or getattr(order_result, "order_id", None)
        status = getattr(order_result, "status", "unknown")
        avg_fill = getattr(order_result, "avg_fill_price", 0)
        filled = getattr(order_result, "filled", 0)

        return {
            "id": str(oid) if oid else None,
            "order_id": str(oid) if oid else None,
            "symbol": symbol,
            "side": side,
            "qty": str(qty),
            "status": str(status),
            "filled_qty": str(filled),
            "filled_avg_price": str(avg_fill),
        }

    @staticmethod
    def _raw_order_to_dict(order) -> dict:
        """Convert a raw Tiger Order object to a dict."""
        contract = getattr(order, "contract", None)
        symbol = ""
        if contract:
            symbol = getattr(contract, "symbol", "") or str(contract)

        return {
            "id": str(getattr(order, "id", "") or getattr(order, "order_id", "")),
            "order_id": str(getattr(order, "id", "") or getattr(order, "order_id", "")),
            "symbol": symbol,
            "side": str(getattr(order, "action", "")),
            "qty": str(getattr(order, "quantity", 0)),
            "status": str(getattr(order, "status", "")),
            "filled_qty": str(getattr(order, "filled", 0)),
            "filled_avg_price": str(getattr(order, "avg_fill_price", 0)),
            "limit_price": str(getattr(order, "limit_price", "")),
            "order_type": str(getattr(order, "order_type", "")),
            "trade_time": str(getattr(order, "trade_time", "")),
        }
