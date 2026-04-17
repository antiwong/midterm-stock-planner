"""
Alpaca Broker – Paper Trading Integration
==========================================
Wraps the Alpaca Trading API (alpaca-py SDK) for paper trading.

This module provides order execution, position management, and portfolio
rebalancing against an Alpaca paper-trading account.  All public methods
return plain Python dicts/lists for easy serialization.

Setup:
    export ALPACA_API_KEY=your_paper_key
    export ALPACA_SECRET_KEY=your_paper_secret

    Or create a .env file with these values.
    Paper vs. live is auto-detected by Alpaca based on the key prefix.
"""

import os
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional, Union

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ---------------------------------------------------------------------------
# SDK imports – gracefully degrade when alpaca-py is not installed
# ---------------------------------------------------------------------------
try:
    from alpaca.trading.client import TradingClient
    from alpaca.trading.requests import (
        GetOrdersRequest,
        LimitOrderRequest,
        MarketOrderRequest,
    )
    from alpaca.trading.enums import (
        OrderSide,
        OrderStatus,
        OrderType,
        QueryOrderStatus,
        TimeInForce,
    )
    ALPACA_TRADING_AVAILABLE = True
except ImportError:
    ALPACA_TRADING_AVAILABLE = False

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _obj_to_dict(obj) -> dict:
    """Convert an Alpaca SDK model to a plain dict.

    The SDK objects expose a ``model_dump`` / ``dict`` method (pydantic v2/v1).
    We also stringify datetimes and UUID fields so the result is JSON-safe.
    """
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj

    # pydantic v2 (alpaca-py >= 0.20)
    if hasattr(obj, "model_dump"):
        d = obj.model_dump()
    elif hasattr(obj, "dict"):
        d = obj.dict()
    elif hasattr(obj, "__dict__"):
        d = dict(obj.__dict__)
    else:
        return {"raw": str(obj)}

    # Make values JSON-friendly
    cleaned: dict = {}
    for k, v in d.items():
        if isinstance(v, datetime):
            cleaned[k] = v.isoformat()
        elif hasattr(v, "value"):
            # Enum-like
            cleaned[k] = v.value if not callable(v.value) else str(v)
        else:
            cleaned[k] = v
    return cleaned


# ---------------------------------------------------------------------------
# AlpacaBroker
# ---------------------------------------------------------------------------

class AlpacaBroker:
    """Thin wrapper around Alpaca's Trading API for paper trading.

    Every public method returns plain dicts/lists (never raw SDK objects)
    so callers can serialise results to JSON or store them in SQLite without
    any conversion.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        paper: bool = True,
    ):
        if not ALPACA_TRADING_AVAILABLE:
            raise ImportError(
                "alpaca-py trading modules not installed. "
                "Run: pip install alpaca-py"
            )

        self.api_key = api_key or os.environ.get("ALPACA_API_KEY", "")
        self.secret_key = secret_key or os.environ.get("ALPACA_SECRET_KEY", "")

        if not self.api_key or not self.secret_key:
            raise ValueError(
                "Alpaca API keys not found. Set ALPACA_API_KEY and "
                "ALPACA_SECRET_KEY environment variables or pass them "
                "directly.\nSign up (free) at: https://app.alpaca.markets/signup"
            )

        self.paper = paper
        self.client = TradingClient(
            api_key=self.api_key,
            secret_key=self.secret_key,
            paper=self.paper,
        )
        logger.info("AlpacaBroker initialised (paper=%s)", self.paper)

    # ------------------------------------------------------------------
    # Account
    # ------------------------------------------------------------------

    def get_account(self) -> dict:
        """Return account summary (equity, cash, buying_power, etc.)."""
        try:
            acct = self.client.get_account()
            return _obj_to_dict(acct)
        except Exception as exc:
            logger.error("Failed to get account: %s", exc)
            raise RuntimeError(f"Failed to get account: {exc}") from exc

    # ------------------------------------------------------------------
    # Positions
    # ------------------------------------------------------------------

    def get_positions(self) -> List[dict]:
        """Return all open positions as a list of dicts."""
        try:
            positions = self.client.get_all_positions()
            return [_obj_to_dict(p) for p in positions]
        except Exception as exc:
            logger.error("Failed to get positions: %s", exc)
            raise RuntimeError(f"Failed to get positions: {exc}") from exc

    def get_position(self, symbol: str) -> Optional[dict]:
        """Return a single position dict, or None if not held."""
        try:
            pos = self.client.get_open_position(symbol.upper())
            return _obj_to_dict(pos)
        except Exception as exc:
            err = str(exc).lower()
            if "404" in err or "not found" in err or "no position" in err:
                return None
            logger.error("Failed to get position for %s: %s", symbol, exc)
            raise RuntimeError(
                f"Failed to get position for {symbol}: {exc}"
            ) from exc

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
        """Submit a generic order.

        Args:
            symbol: Ticker symbol.
            qty: Number of shares (fractional OK for market orders).
            side: 'buy' or 'sell'.
            type: 'market' or 'limit'.
            time_in_force: 'day', 'gtc', 'ioc', 'fok'.
            limit_price: Required when type='limit'.
        """
        order_side = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL
        tif = self._parse_tif(time_in_force)

        try:
            if type.lower() == "limit":
                if limit_price is None:
                    raise ValueError("limit_price is required for limit orders")
                req = LimitOrderRequest(
                    symbol=symbol.upper(),
                    qty=qty,
                    side=order_side,
                    time_in_force=tif,
                    limit_price=limit_price,
                )
            else:
                req = MarketOrderRequest(
                    symbol=symbol.upper(),
                    qty=qty,
                    side=order_side,
                    time_in_force=tif,
                )

            order = self.client.submit_order(req)
            logger.info(
                "Order submitted: %s %s %s @ %s",
                side, qty, symbol, type,
            )
            return _obj_to_dict(order)
        except Exception as exc:
            logger.error("Order failed (%s %s %s): %s", side, qty, symbol, exc)
            raise RuntimeError(
                f"Order failed ({side} {qty} {symbol}): {exc}"
            ) from exc

    def submit_market_order(
        self,
        symbol: str,
        notional: Optional[float] = None,
        qty: Optional[float] = None,
        side: str = "buy",
    ) -> dict:
        """Submit a market order by dollar amount (notional) or share qty.

        Exactly one of *notional* or *qty* must be provided.
        """
        if notional is not None and qty is not None:
            raise ValueError("Provide either notional or qty, not both")
        if notional is None and qty is None:
            raise ValueError("Provide either notional or qty")

        order_side = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL

        try:
            kwargs = dict(
                symbol=symbol.upper(),
                side=order_side,
                time_in_force=TimeInForce.DAY,
            )
            if notional is not None:
                kwargs["notional"] = round(notional, 2)
            else:
                kwargs["qty"] = qty

            req = MarketOrderRequest(**kwargs)
            order = self.client.submit_order(req)
            logger.info(
                "Market order submitted: %s %s (notional=%s, qty=%s)",
                side, symbol, notional, qty,
            )
            return _obj_to_dict(order)
        except Exception as exc:
            logger.error(
                "Market order failed (%s %s): %s", side, symbol, exc
            )
            raise RuntimeError(
                f"Market order failed ({side} {symbol}): {exc}"
            ) from exc

    def get_orders(
        self, status: str = "open", limit: int = 100
    ) -> List[dict]:
        """Return orders filtered by status ('open', 'closed', 'all')."""
        status_map = {
            "open": QueryOrderStatus.OPEN,
            "closed": QueryOrderStatus.CLOSED,
            "all": QueryOrderStatus.ALL,
        }
        query_status = status_map.get(status.lower(), QueryOrderStatus.OPEN)

        try:
            req = GetOrdersRequest(status=query_status, limit=limit)
            orders = self.client.get_orders(req)
            return [_obj_to_dict(o) for o in orders]
        except Exception as exc:
            logger.error("Failed to get orders: %s", exc)
            raise RuntimeError(f"Failed to get orders: {exc}") from exc

    def get_order(self, order_id: str) -> dict:
        """Return a single order by its ID."""
        try:
            order = self.client.get_order_by_id(order_id)
            return _obj_to_dict(order)
        except Exception as exc:
            logger.error("Failed to get order %s: %s", order_id, exc)
            raise RuntimeError(
                f"Failed to get order {order_id}: {exc}"
            ) from exc

    def cancel_all_orders(self) -> None:
        """Cancel every open order."""
        try:
            self.client.cancel_orders()
            logger.info("All open orders cancelled")
        except Exception as exc:
            logger.error("Failed to cancel orders: %s", exc)
            raise RuntimeError(f"Failed to cancel orders: {exc}") from exc

    # ------------------------------------------------------------------
    # Close positions
    # ------------------------------------------------------------------

    def close_position(self, symbol: str) -> dict:
        """Close an entire position in *symbol*."""
        try:
            order = self.client.close_position(symbol.upper())
            logger.info("Closed position: %s", symbol)
            return _obj_to_dict(order)
        except Exception as exc:
            logger.error("Failed to close position %s: %s", symbol, exc)
            raise RuntimeError(
                f"Failed to close position {symbol}: {exc}"
            ) from exc

    def close_all_positions(self) -> List[dict]:
        """Liquidate all open positions."""
        try:
            responses = self.client.close_all_positions(cancel_orders=True)
            results = []
            for resp in responses:
                # close_all_positions returns ClosePositionResponse objects
                if hasattr(resp, "body") and resp.body:
                    results.append(_obj_to_dict(resp.body))
                else:
                    results.append(_obj_to_dict(resp))
            logger.info("Closed all positions (%d)", len(results))
            return results
        except Exception as exc:
            logger.error("Failed to close all positions: %s", exc)
            raise RuntimeError(
                f"Failed to close all positions: {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Wait / polling
    # ------------------------------------------------------------------

    def wait_for_order(
        self, order_id: str, timeout: int = 30
    ) -> dict:
        """Poll until an order reaches a terminal state or *timeout* seconds.

        Terminal states: filled, canceled, expired, replaced.
        """
        terminal = {"filled", "canceled", "expired", "replaced", "rejected"}
        deadline = time.time() + timeout

        while time.time() < deadline:
            order = self.get_order(order_id)
            status = str(order.get("status", "")).lower()
            if status in terminal:
                return order
            time.sleep(0.5)

        # Return whatever the last status was
        return self.get_order(order_id)

    # ------------------------------------------------------------------
    # Market clock
    # ------------------------------------------------------------------

    def is_market_open(self) -> bool:
        """Return True if the US equity market is currently open."""
        clock = self.client.get_clock()
        return bool(clock.is_open)

    def get_clock(self) -> dict:
        """Return market clock info (is_open, next_open, next_close)."""
        try:
            clock = self.client.get_clock()
            return {
                "is_open": clock.is_open,
                "next_open": clock.next_open.isoformat()
                if clock.next_open
                else None,
                "next_close": clock.next_close.isoformat()
                if clock.next_close
                else None,
                "timestamp": clock.timestamp.isoformat()
                if clock.timestamp
                else None,
            }
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
        """Rebalance the portfolio to match *target_weights*.

        Args:
            target_weights: Mapping of symbol -> target weight (0-1).
                            Weights do not need to sum to 1; remaining equity
                            stays in cash.
            portfolio_value: Override the portfolio value used for
                             calculations.  If None, the current account
                             equity is used.
            managed_universe: If provided, Phase 1 only liquidates positions
                              within this set — positions outside are left
                              untouched (used for market-scoped rebalances).

        Returns:
            List of trade dicts (one per executed order).

        Strategy:
            1. Sell positions NOT in target_weights.
            2. For positions in target_weights, sell down if over-weight.
            3. Wait for sells to fill.
            4. Buy / top-up positions that are under-weight.
        """
        # Validate weights
        total_weight = sum(target_weights.values())
        if total_weight > 1.01:
            raise ValueError(
                f"Target weights sum to {total_weight:.3f} (> 1.0). "
                "Reduce allocations."
            )

        target_weights = {
            sym.upper(): w for sym, w in target_weights.items()
        }
        managed_set = {s.upper() for s in managed_universe} if managed_universe else None

        # Current state
        if portfolio_value is None:
            acct = self.get_account()
            portfolio_value = float(acct.get("equity", 0))
            if portfolio_value <= 0:
                raise RuntimeError(
                    "Account equity is zero – cannot rebalance."
                )

        current_positions = {
            p["symbol"]: p for p in self.get_positions()
        }

        trades: List[dict] = []

        # --- Phase 1: sell everything not in target -----------------------
        symbols_to_sell_fully = set(current_positions) - set(target_weights)
        if managed_set is not None:
            symbols_to_sell_fully &= managed_set
        sell_order_ids: List[str] = []

        for sym in symbols_to_sell_fully:
            logger.info("Rebalance: liquidating %s (not in target)", sym)
            try:
                order = self.close_position(sym)
                trades.append(
                    {"action": "sell_all", "symbol": sym, "order": order}
                )
                oid = order.get("id") or order.get("order_id")
                if oid:
                    sell_order_ids.append(str(oid))
            except Exception as exc:
                logger.warning("Could not close %s: %s", sym, exc)
                trades.append(
                    {"action": "sell_all", "symbol": sym, "error": str(exc)}
                )

        # --- Phase 2: adjust held positions --------------------------------
        for sym, target_w in target_weights.items():
            target_value = portfolio_value * target_w
            current_value = float(
                current_positions.get(sym, {}).get("market_value", 0)
            )
            delta_value = target_value - current_value

            # Skip tiny adjustments (< $5 or < 0.5% of portfolio)
            if abs(delta_value) < max(5.0, portfolio_value * 0.005):
                logger.debug(
                    "Rebalance: skipping %s (delta=$%.2f)", sym, delta_value
                )
                continue

            if delta_value < 0:
                # Need to sell some
                sell_notional = abs(delta_value)
                logger.info(
                    "Rebalance: trimming %s by $%.2f", sym, sell_notional
                )
                try:
                    order = self.submit_market_order(
                        symbol=sym, notional=sell_notional, side="sell"
                    )
                    trades.append(
                        {
                            "action": "sell_trim",
                            "symbol": sym,
                            "notional": sell_notional,
                            "order": order,
                        }
                    )
                    oid = order.get("id") or order.get("order_id")
                    if oid:
                        sell_order_ids.append(str(oid))
                except Exception as exc:
                    logger.warning("Could not trim %s: %s", sym, exc)
                    trades.append(
                        {
                            "action": "sell_trim",
                            "symbol": sym,
                            "error": str(exc),
                        }
                    )

        # Wait for all sells to (likely) fill before buying
        for oid in sell_order_ids:
            self.wait_for_order(oid, timeout=15)

        # --- Phase 3: buy / top-up ----------------------------------------
        # Re-fetch account after sells settled
        acct = self.get_account()
        available_cash = float(acct.get("cash", 0))

        for sym, target_w in target_weights.items():
            target_value = portfolio_value * target_w
            # Re-check current position value (may have changed after sells)
            pos = self.get_position(sym)
            current_value = float(pos["market_value"]) if pos else 0.0
            buy_notional = target_value - current_value

            if buy_notional < max(5.0, portfolio_value * 0.005):
                continue

            # Don't exceed available cash
            buy_notional = min(buy_notional, available_cash)
            if buy_notional < 1.0:
                logger.debug(
                    "Rebalance: insufficient cash for %s ($%.2f)",
                    sym,
                    buy_notional,
                )
                continue

            logger.info(
                "Rebalance: buying $%.2f of %s", buy_notional, sym
            )
            try:
                order = self.submit_market_order(
                    symbol=sym, notional=buy_notional, side="buy"
                )
                trades.append(
                    {
                        "action": "buy",
                        "symbol": sym,
                        "notional": buy_notional,
                        "order": order,
                    }
                )
                available_cash -= buy_notional
            except Exception as exc:
                logger.warning("Could not buy %s: %s", sym, exc)
                trades.append(
                    {"action": "buy", "symbol": sym, "error": str(exc)}
                )

        logger.info(
            "Rebalance complete: %d trades executed", len(trades)
        )
        return trades

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_tif(tif_str: str) -> "TimeInForce":
        """Convert a human-friendly time-in-force string to the SDK enum."""
        mapping = {
            "day": TimeInForce.DAY,
            "gtc": TimeInForce.GTC,
            "ioc": TimeInForce.IOC,
            "fok": TimeInForce.FOK,
        }
        result = mapping.get(tif_str.lower())
        if result is None:
            raise ValueError(
                f"Unknown time_in_force '{tif_str}'. "
                f"Use one of: {list(mapping.keys())}"
            )
        return result
