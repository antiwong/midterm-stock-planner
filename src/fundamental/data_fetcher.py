"""Fundamental data fetcher for financial metrics and company information.

This module fetches fundamental data from Yahoo Finance including:
- Financial ratios (PE, PB, ROE, etc.)
- Financial statements (income, balance sheet, cash flow)
- Analyst recommendations
- Company news

Data can be used directly or combined with SEC filings for comprehensive analysis.
"""

import json
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict

import pandas as pd
import numpy as np

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False


logger = logging.getLogger(__name__)


@dataclass
class CompanyInfo:
    """Basic company information."""
    ticker: str
    name: str
    sector: Optional[str] = None
    industry: Optional[str] = None
    market_cap: Optional[float] = None
    employees: Optional[int] = None
    website: Optional[str] = None
    description: Optional[str] = None


@dataclass
class FinancialMetrics:
    """Key financial metrics and ratios."""
    ticker: str
    as_of_date: str
    
    # Valuation
    market_cap: Optional[float] = None
    enterprise_value: Optional[float] = None
    trailing_pe: Optional[float] = None
    forward_pe: Optional[float] = None
    peg_ratio: Optional[float] = None
    price_to_book: Optional[float] = None
    price_to_sales: Optional[float] = None
    
    # Profitability
    profit_margin: Optional[float] = None
    operating_margin: Optional[float] = None
    gross_margin: Optional[float] = None
    return_on_equity: Optional[float] = None
    return_on_assets: Optional[float] = None
    
    # Growth
    revenue_growth: Optional[float] = None
    earnings_growth: Optional[float] = None
    
    # Financial Health
    current_ratio: Optional[float] = None
    quick_ratio: Optional[float] = None
    debt_to_equity: Optional[float] = None
    
    # Dividends
    dividend_yield: Optional[float] = None
    dividend_rate: Optional[float] = None
    payout_ratio: Optional[float] = None
    
    # Trading
    beta: Optional[float] = None
    fifty_two_week_high: Optional[float] = None
    fifty_two_week_low: Optional[float] = None
    avg_volume: Optional[float] = None
    
    def to_dict(self) -> Dict:
        return asdict(self)


class FundamentalDataFetcher:
    """Fetch fundamental data from Yahoo Finance and other sources."""
    
    def __init__(self):
        """Initialize fundamental data fetcher."""
        if not YFINANCE_AVAILABLE:
            logger.warning(
                "yfinance not installed. "
                "Install with: pip install yfinance"
            )
    
    def get_company_info(self, ticker: str) -> Optional[CompanyInfo]:
        """
        Get basic company information.
        
        Args:
            ticker: Stock ticker symbol
        
        Returns:
            CompanyInfo object or None if error
        """
        if not YFINANCE_AVAILABLE:
            return None
        
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            return CompanyInfo(
                ticker=ticker,
                name=info.get("longName", info.get("shortName", ticker)),
                sector=info.get("sector"),
                industry=info.get("industry"),
                market_cap=info.get("marketCap"),
                employees=info.get("fullTimeEmployees"),
                website=info.get("website"),
                description=info.get("longBusinessSummary")
            )
        except Exception as e:
            logger.error(f"Error fetching company info for {ticker}: {e}")
            return None
    
    def get_financial_metrics(self, ticker: str) -> Optional[FinancialMetrics]:
        """
        Get key financial metrics and ratios.
        
        Args:
            ticker: Stock ticker symbol
        
        Returns:
            FinancialMetrics object or None if error
        """
        if not YFINANCE_AVAILABLE:
            return None
        
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            return FinancialMetrics(
                ticker=ticker,
                as_of_date=datetime.now().strftime("%Y-%m-%d"),
                
                # Valuation
                market_cap=info.get("marketCap"),
                enterprise_value=info.get("enterpriseValue"),
                trailing_pe=info.get("trailingPE"),
                forward_pe=info.get("forwardPE"),
                peg_ratio=info.get("pegRatio"),
                price_to_book=info.get("priceToBook"),
                price_to_sales=info.get("priceToSalesTrailing12Months"),
                
                # Profitability
                profit_margin=info.get("profitMargins"),
                operating_margin=info.get("operatingMargins"),
                gross_margin=info.get("grossMargins"),
                return_on_equity=info.get("returnOnEquity"),
                return_on_assets=info.get("returnOnAssets"),
                
                # Growth
                revenue_growth=info.get("revenueGrowth"),
                earnings_growth=info.get("earningsQuarterlyGrowth"),
                
                # Financial Health
                current_ratio=info.get("currentRatio"),
                quick_ratio=info.get("quickRatio"),
                debt_to_equity=info.get("debtToEquity"),
                
                # Dividends
                dividend_yield=info.get("dividendYield"),
                dividend_rate=info.get("dividendRate"),
                payout_ratio=info.get("payoutRatio"),
                
                # Trading
                beta=info.get("beta"),
                fifty_two_week_high=info.get("fiftyTwoWeekHigh"),
                fifty_two_week_low=info.get("fiftyTwoWeekLow"),
                avg_volume=info.get("averageVolume")
            )
        except Exception as e:
            logger.error(f"Error fetching financial metrics for {ticker}: {e}")
            return None
    
    def get_financial_statements(
        self,
        ticker: str,
        period: str = "annual"
    ) -> Dict[str, pd.DataFrame]:
        """
        Get financial statements (income, balance sheet, cash flow).
        
        Args:
            ticker: Stock ticker symbol
            period: "annual" or "quarterly"
        
        Returns:
            Dict with DataFrames for each statement type
        """
        if not YFINANCE_AVAILABLE:
            return {}
        
        statements = {}
        
        try:
            stock = yf.Ticker(ticker)
            
            if period == "quarterly":
                statements["income_statement"] = stock.quarterly_financials.T
                statements["balance_sheet"] = stock.quarterly_balance_sheet.T
                statements["cash_flow"] = stock.quarterly_cashflow.T
            else:
                statements["income_statement"] = stock.financials.T
                statements["balance_sheet"] = stock.balance_sheet.T
                statements["cash_flow"] = stock.cashflow.T
            
            # Add ticker column to each
            for key in statements:
                if not statements[key].empty:
                    statements[key]["ticker"] = ticker
                    statements[key].index.name = "date"
                    statements[key] = statements[key].reset_index()
            
        except Exception as e:
            logger.error(f"Error fetching statements for {ticker}: {e}")
        
        return statements
    
    def get_analyst_recommendations(self, ticker: str) -> pd.DataFrame:
        """
        Get analyst recommendations and price targets.
        
        Args:
            ticker: Stock ticker symbol
        
        Returns:
            DataFrame with recommendations
        """
        if not YFINANCE_AVAILABLE:
            return pd.DataFrame()
        
        try:
            stock = yf.Ticker(ticker)
            recs = stock.recommendations
            
            if recs is not None and not recs.empty:
                recs["ticker"] = ticker
                return recs
            
        except Exception as e:
            logger.error(f"Error fetching recommendations for {ticker}: {e}")
        
        return pd.DataFrame()
    
    def get_news(self, ticker: str, max_items: int = 10) -> List[Dict]:
        """
        Get recent news articles for a ticker.
        
        Args:
            ticker: Stock ticker symbol
            max_items: Maximum number of news items
        
        Returns:
            List of news article dictionaries
        """
        if not YFINANCE_AVAILABLE:
            return []
        
        news = []
        
        try:
            stock = yf.Ticker(ticker)
            
            for item in (stock.news or [])[:max_items]:
                if item.get("title") and item.get("link"):
                    news.append({
                        "ticker": ticker,
                        "title": item.get("title"),
                        "publisher": item.get("publisher"),
                        "link": item.get("link"),
                        "type": item.get("type"),
                        "published": datetime.utcfromtimestamp(
                            item.get("providerPublishTime", 0)
                        ).isoformat() if item.get("providerPublishTime") else None
                    })
                    
        except Exception as e:
            logger.error(f"Error fetching news for {ticker}: {e}")
        
        return news
    
    def get_institutional_holders(self, ticker: str) -> pd.DataFrame:
        """
        Get institutional holders information.
        
        Args:
            ticker: Stock ticker symbol
        
        Returns:
            DataFrame with institutional holders
        """
        if not YFINANCE_AVAILABLE:
            return pd.DataFrame()
        
        try:
            stock = yf.Ticker(ticker)
            holders = stock.institutional_holders
            
            if holders is not None and not holders.empty:
                holders["ticker"] = ticker
                return holders
                
        except Exception as e:
            logger.error(f"Error fetching institutional holders for {ticker}: {e}")
        
        return pd.DataFrame()
    
    def get_insider_transactions(self, ticker: str) -> pd.DataFrame:
        """
        Get recent insider transactions.
        
        Args:
            ticker: Stock ticker symbol
        
        Returns:
            DataFrame with insider transactions
        """
        if not YFINANCE_AVAILABLE:
            return pd.DataFrame()
        
        try:
            stock = yf.Ticker(ticker)
            insiders = stock.insider_transactions
            
            if insiders is not None and not insiders.empty:
                insiders["ticker"] = ticker
                return insiders
                
        except Exception as e:
            logger.error(f"Error fetching insider transactions for {ticker}: {e}")
        
        return pd.DataFrame()


def fetch_fundamentals_for_universe(
    tickers: List[str],
    include_statements: bool = False
) -> pd.DataFrame:
    """
    Fetch fundamental metrics for a list of tickers.
    
    Args:
        tickers: List of stock ticker symbols
        include_statements: Whether to include financial statements
    
    Returns:
        DataFrame with fundamental metrics
    """
    fetcher = FundamentalDataFetcher()
    
    metrics_list = []
    
    for ticker in tickers:
        logger.info(f"Fetching fundamentals for {ticker}...")
        
        metrics = fetcher.get_financial_metrics(ticker)
        if metrics:
            metrics_list.append(metrics.to_dict())
    
    if not metrics_list:
        return pd.DataFrame()
    
    return pd.DataFrame(metrics_list)


def create_valuation_features(
    fundamentals_df: pd.DataFrame,
    price_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Create valuation features from fundamental data.
    
    Merges fundamental metrics with price data and calculates relative valuations.
    
    Args:
        fundamentals_df: DataFrame from fetch_fundamentals_for_universe
        price_df: DataFrame with ['date', 'ticker', 'close', ...]
    
    Returns:
        price_df with additional valuation features
    """
    if fundamentals_df.empty:
        return price_df
    
    df = price_df.copy()
    
    # Merge fundamental data by ticker
    fund_cols = [
        "ticker", "trailing_pe", "forward_pe", "price_to_book", "price_to_sales",
        "profit_margin", "operating_margin", "return_on_equity", "return_on_assets",
        "revenue_growth", "earnings_growth", "current_ratio", "debt_to_equity",
        "dividend_yield", "beta"
    ]
    
    available_cols = ["ticker"] + [c for c in fund_cols[1:] if c in fundamentals_df.columns]
    
    df = df.merge(
        fundamentals_df[available_cols],
        on="ticker",
        how="left"
    )
    
    # Calculate relative valuation features (percentile within each date)
    valuation_cols = ["trailing_pe", "forward_pe", "price_to_book", "price_to_sales"]
    
    for col in valuation_cols:
        if col in df.columns:
            df[f"{col}_rank"] = df.groupby("date")[col].rank(pct=True)
    
    # Calculate composite value score (lower PE/PB = higher value)
    if "trailing_pe" in df.columns and "price_to_book" in df.columns:
        df["value_score"] = (
            (1 - df["trailing_pe_rank"].fillna(0.5)) + 
            (1 - df.get("price_to_book_rank", pd.Series(0.5, index=df.index)).fillna(0.5))
        ) / 2
    
    # Quality score (higher ROE, margins = higher quality)
    quality_cols = ["return_on_equity", "profit_margin", "current_ratio"]
    quality_available = [c for c in quality_cols if c in df.columns]
    
    if quality_available:
        for col in quality_available:
            df[f"{col}_rank"] = df.groupby("date")[col].rank(pct=True)
        
        df["quality_score"] = df[[f"{c}_rank" for c in quality_available]].mean(axis=1)
    
    return df
