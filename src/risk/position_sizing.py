"""Position sizing calculations for portfolio construction."""

import numpy as np
import pandas as pd
from typing import Dict, Optional, List
from dataclasses import dataclass


@dataclass
class PositionSizeResult:
    """Result of position sizing calculation."""
    symbol: str
    shares: int
    position_value: float
    weight_pct: float
    method: str


class PositionSizer:
    """Calculate optimal position sizes using various methods."""
    
    def __init__(self, capital: float = 100000.0):
        """
        Initialize position sizer.
        
        Args:
            capital: Total available capital
        """
        self.capital = capital
    
    def equal_weight(
        self,
        symbols: List[str],
        prices: Dict[str, float],
        max_positions: Optional[int] = None
    ) -> List[PositionSizeResult]:
        """
        Equal weight position sizing.
        
        Allocates equal capital to each position.
        
        Args:
            symbols: List of symbols to allocate
            prices: Dict mapping symbol to current price
            max_positions: Maximum number of positions (default all)
        
        Returns:
            List of PositionSizeResult for each symbol
        """
        if max_positions:
            symbols = symbols[:max_positions]
        
        if not symbols:
            return []
        
        weight = 1.0 / len(symbols)
        capital_per_position = self.capital * weight
        
        results = []
        for symbol in symbols:
            price = prices.get(symbol, 0)
            if price > 0:
                shares = int(capital_per_position / price)
                position_value = shares * price
                results.append(PositionSizeResult(
                    symbol=symbol,
                    shares=shares,
                    position_value=position_value,
                    weight_pct=weight * 100,
                    method="equal_weight"
                ))
        
        return results
    
    def volatility_weighted(
        self,
        symbols: List[str],
        prices: Dict[str, float],
        volatilities: Dict[str, float],
        target_volatility: float = 0.15
    ) -> List[PositionSizeResult]:
        """
        Volatility-weighted (risk parity) position sizing.
        
        Allocates more capital to lower volatility stocks.
        
        Args:
            symbols: List of symbols to allocate
            prices: Dict mapping symbol to current price
            volatilities: Dict mapping symbol to annualized volatility
            target_volatility: Target portfolio volatility (default 15%)
        
        Returns:
            List of PositionSizeResult for each symbol
        """
        if not symbols:
            return []
        
        # Inverse volatility weights
        inv_vols = []
        valid_symbols = []
        for symbol in symbols:
            vol = volatilities.get(symbol, 0)
            if vol > 0:
                inv_vols.append(1.0 / vol)
                valid_symbols.append(symbol)
        
        if not valid_symbols:
            return []
        
        total_inv_vol = sum(inv_vols)
        weights = [iv / total_inv_vol for iv in inv_vols]
        
        results = []
        for symbol, weight in zip(valid_symbols, weights):
            price = prices.get(symbol, 0)
            if price > 0:
                capital_alloc = self.capital * weight
                shares = int(capital_alloc / price)
                position_value = shares * price
                results.append(PositionSizeResult(
                    symbol=symbol,
                    shares=shares,
                    position_value=position_value,
                    weight_pct=weight * 100,
                    method="volatility_weighted"
                ))
        
        return results
    
    def score_weighted(
        self,
        symbols: List[str],
        prices: Dict[str, float],
        scores: Dict[str, float],
        min_weight: float = 0.02,
        max_weight: float = 0.15
    ) -> List[PositionSizeResult]:
        """
        Score-weighted position sizing.
        
        Allocates more capital to higher-scoring stocks.
        Useful for factor/alpha strategies.
        
        Args:
            symbols: List of symbols to allocate
            prices: Dict mapping symbol to current price
            scores: Dict mapping symbol to score/rank (higher = better)
            min_weight: Minimum position weight
            max_weight: Maximum position weight
        
        Returns:
            List of PositionSizeResult for each symbol
        """
        if not symbols:
            return []
        
        # Normalize scores to weights
        valid_symbols = []
        symbol_scores = []
        for symbol in symbols:
            score = scores.get(symbol, 0)
            if score > 0:
                valid_symbols.append(symbol)
                symbol_scores.append(score)
        
        if not valid_symbols:
            return []
        
        total_score = sum(symbol_scores)
        raw_weights = [s / total_score for s in symbol_scores]
        
        # Apply min/max constraints
        weights = []
        for w in raw_weights:
            w = max(min_weight, min(max_weight, w))
            weights.append(w)
        
        # Renormalize to sum to 1
        total_weight = sum(weights)
        weights = [w / total_weight for w in weights]
        
        results = []
        for symbol, weight in zip(valid_symbols, weights):
            price = prices.get(symbol, 0)
            if price > 0:
                capital_alloc = self.capital * weight
                shares = int(capital_alloc / price)
                position_value = shares * price
                results.append(PositionSizeResult(
                    symbol=symbol,
                    shares=shares,
                    position_value=position_value,
                    weight_pct=weight * 100,
                    method="score_weighted"
                ))
        
        return results
    
    def kelly_criterion(
        self,
        win_rate: float,
        avg_win: float,
        avg_loss: float,
        fraction: float = 0.25
    ) -> float:
        """
        Calculate Kelly criterion for optimal bet size.
        
        Kelly is often too aggressive, so fractional Kelly (fraction < 1) is used.
        
        Args:
            win_rate: Probability of winning (0-1)
            avg_win: Average winning amount
            avg_loss: Average losing amount (absolute value)
            fraction: Fraction of full Kelly (default 0.25 = quarter Kelly)
        
        Returns:
            Optimal position size as fraction of capital
        """
        if avg_loss == 0:
            return 0.0
        
        # Kelly formula: f* = (p*b - q) / b
        # where p = win_rate, q = 1-p, b = win/loss ratio
        b = avg_win / avg_loss
        kelly_pct = (win_rate * b - (1 - win_rate)) / b
        
        kelly_pct = max(0.0, kelly_pct) * fraction
        return min(kelly_pct, 0.25)  # Cap at 25%
    
    def atr_based(
        self,
        symbol: str,
        price: float,
        atr: float,
        risk_per_trade: float = 0.02,
        atr_multiplier: float = 2.0
    ) -> PositionSizeResult:
        """
        ATR-based position sizing (volatility stop method).
        
        Risk a fixed percentage of capital per trade, with stop loss
        at a multiple of ATR.
        
        Args:
            symbol: Stock symbol
            price: Current price
            atr: Average True Range
            risk_per_trade: Percentage of capital to risk (default 2%)
            atr_multiplier: ATR multiplier for stop distance (default 2)
        
        Returns:
            PositionSizeResult with calculated shares
        """
        if atr <= 0 or price <= 0:
            return PositionSizeResult(
                symbol=symbol, shares=0, position_value=0,
                weight_pct=0, method="atr_based"
            )
        
        # Stop loss distance
        stop_distance = atr * atr_multiplier
        
        # Risk amount
        risk_amount = self.capital * risk_per_trade
        
        # Shares = risk_amount / stop_distance
        shares = int(risk_amount / stop_distance)
        
        # Cap at 10% of capital
        max_shares = int((self.capital * 0.10) / price)
        shares = min(shares, max_shares)
        
        position_value = shares * price
        weight_pct = (position_value / self.capital) * 100
        
        return PositionSizeResult(
            symbol=symbol,
            shares=max(0, shares),
            position_value=position_value,
            weight_pct=weight_pct,
            method="atr_based"
        )
    
    def apply_constraints(
        self,
        positions: List[PositionSizeResult],
        max_position_pct: float = 0.10,
        max_sector_pct: Optional[float] = None,
        sector_map: Optional[Dict[str, str]] = None
    ) -> List[PositionSizeResult]:
        """
        Apply position and sector constraints to sized positions.
        
        Args:
            positions: List of position sizes
            max_position_pct: Maximum single position as % of capital
            max_sector_pct: Maximum sector exposure as % of capital
            sector_map: Dict mapping symbol to sector
        
        Returns:
            Adjusted list of positions
        """
        adjusted = []
        max_value = self.capital * max_position_pct
        
        # Track sector exposure
        sector_exposure: Dict[str, float] = {}
        max_sector_value = self.capital * max_sector_pct if max_sector_pct else float("inf")
        
        for pos in positions:
            new_value = pos.position_value
            
            # Single position limit
            if new_value > max_value:
                new_value = max_value
            
            # Sector limit
            if sector_map and max_sector_pct:
                sector = sector_map.get(pos.symbol, "Other")
                current_sector = sector_exposure.get(sector, 0)
                if current_sector + new_value > max_sector_value:
                    new_value = max(0, max_sector_value - current_sector)
                sector_exposure[sector] = current_sector + new_value
            
            if new_value > 0:
                # Recalculate shares
                price = pos.position_value / pos.shares if pos.shares > 0 else 0
                shares = int(new_value / price) if price > 0 else 0
                adjusted.append(PositionSizeResult(
                    symbol=pos.symbol,
                    shares=shares,
                    position_value=shares * price if price > 0 else 0,
                    weight_pct=(shares * price / self.capital * 100) if price > 0 else 0,
                    method=pos.method
                ))
        
        return adjusted
