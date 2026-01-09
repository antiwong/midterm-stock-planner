"""SEC EDGAR filings downloader and parser for fundamental analysis.

This module provides functionality to:
1. Download SEC filings (10-K, 10-Q, 8-K) from EDGAR
2. Parse filings to extract key financial metrics
3. Create time series of fundamental data for feature engineering

SEC Filing Types:
- 10-K: Annual report (most comprehensive)
- 10-Q: Quarterly report
- 8-K: Current report (material events)
- DEF 14A: Proxy statement
"""

import os
import re
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict

import pandas as pd

# Optional dependencies
try:
    from sec_edgar_downloader import Downloader
    SEC_EDGAR_AVAILABLE = True
except ImportError:
    SEC_EDGAR_AVAILABLE = False

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False


logger = logging.getLogger(__name__)


@dataclass
class FilingMetadata:
    """Metadata for a single SEC filing."""
    ticker: str
    filing_type: str
    filing_date: str
    accession_number: str
    file_path: str
    period_of_report: Optional[str] = None


@dataclass
class ExtractedFinancials:
    """Extracted financial metrics from SEC filings."""
    ticker: str
    filing_date: str
    filing_type: str
    period_end: Optional[str] = None
    
    # Income Statement
    revenue: Optional[float] = None
    cost_of_revenue: Optional[float] = None
    gross_profit: Optional[float] = None
    operating_income: Optional[float] = None
    net_income: Optional[float] = None
    eps_basic: Optional[float] = None
    eps_diluted: Optional[float] = None
    
    # Balance Sheet
    total_assets: Optional[float] = None
    total_liabilities: Optional[float] = None
    total_equity: Optional[float] = None
    cash_and_equivalents: Optional[float] = None
    total_debt: Optional[float] = None
    current_assets: Optional[float] = None
    current_liabilities: Optional[float] = None
    
    # Cash Flow
    operating_cash_flow: Optional[float] = None
    investing_cash_flow: Optional[float] = None
    financing_cash_flow: Optional[float] = None
    free_cash_flow: Optional[float] = None
    capex: Optional[float] = None
    
    # Ratios (calculated)
    gross_margin: Optional[float] = None
    operating_margin: Optional[float] = None
    net_margin: Optional[float] = None
    current_ratio: Optional[float] = None
    debt_to_equity: Optional[float] = None
    
    def to_dict(self) -> Dict:
        return asdict(self)


class SECFilingsDownloader:
    """Download SEC filings from EDGAR database."""
    
    def __init__(
        self,
        company_name: str = "MidtermStockPlanner",
        email: str = "research@example.com",
        download_dir: str = "data/sec-filings"
    ):
        """
        Initialize SEC filings downloader.
        
        SEC requires identification for programmatic access.
        
        Args:
            company_name: Your company/project name for SEC compliance
            email: Your email for SEC compliance
            download_dir: Directory to save downloaded filings
        """
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.downloader = None
        
        if not SEC_EDGAR_AVAILABLE:
            logger.warning(
                "sec-edgar-downloader not installed. "
                "Install with: pip install sec-edgar-downloader"
            )
        else:
            try:
                self.downloader = Downloader(company_name, email, str(self.download_dir))
                logger.info(f"SEC downloader initialized (dir: {download_dir})")
            except Exception as e:
                logger.error(f"Failed to initialize SEC downloader: {e}")
    
    def download_filings(
        self,
        ticker: str,
        filing_types: Optional[List[str]] = None,
        num_filings: int = 4,
        after_date: Optional[str] = None,
        before_date: Optional[str] = None
    ) -> Dict[str, List[FilingMetadata]]:
        """
        Download SEC filings for a ticker.
        
        Args:
            ticker: Stock ticker symbol
            filing_types: Types to download (default: ['10-K', '10-Q'])
            num_filings: Number of each type to download
            after_date: Only filings after this date (YYYY-MM-DD)
            before_date: Only filings before this date (YYYY-MM-DD)
        
        Returns:
            Dict mapping filing type to list of FilingMetadata
        """
        if not SEC_EDGAR_AVAILABLE or not self.downloader:
            logger.error("SEC downloader not available")
            return {}
        
        if filing_types is None:
            filing_types = ["10-K", "10-Q"]
        
        results = {}
        
        for filing_type in filing_types:
            try:
                logger.info(f"Downloading {num_filings} {filing_type} filings for {ticker}...")
                
                # Download filings
                self.downloader.get(
                    filing_type,
                    ticker,
                    limit=num_filings,
                    after=after_date,
                    before=before_date
                )
                
                # Find downloaded files
                filings = self._find_downloaded_filings(ticker, filing_type)
                results[filing_type] = filings
                
                logger.info(f"Downloaded {len(filings)} {filing_type} filings for {ticker}")
                
            except Exception as e:
                logger.error(f"Error downloading {filing_type} for {ticker}: {e}")
                results[filing_type] = []
        
        return results
    
    def _find_downloaded_filings(
        self,
        ticker: str,
        filing_type: str
    ) -> List[FilingMetadata]:
        """Find downloaded filings and extract metadata."""
        filings = []
        ticker_dir = self.download_dir / "sec-edgar-filings" / ticker / filing_type
        
        if not ticker_dir.exists():
            # Try alternate path structure
            ticker_dir = self.download_dir / ticker / filing_type
        
        if not ticker_dir.exists():
            return filings
        
        for filing_dir in ticker_dir.iterdir():
            if filing_dir.is_dir():
                # Accession number is the folder name
                accession = filing_dir.name
                
                # Find the primary document
                for file in filing_dir.iterdir():
                    if file.suffix in [".htm", ".html", ".txt"]:
                        # Parse filing date from accession number
                        # Format: XXXXXXXXXX-YY-NNNNNN where YY is year
                        parts = accession.split("-")
                        if len(parts) >= 2:
                            year = int(parts[1])
                            year = year + 2000 if year < 50 else year + 1900
                            filing_date = f"{year}-01-01"  # Approximate
                        else:
                            filing_date = "unknown"
                        
                        filings.append(FilingMetadata(
                            ticker=ticker,
                            filing_type=filing_type,
                            filing_date=filing_date,
                            accession_number=accession,
                            file_path=str(file)
                        ))
                        break
        
        return filings
    
    def get_filing_paths(self, ticker: str) -> Dict[str, List[str]]:
        """
        Get paths to all downloaded filings for a ticker.
        
        Args:
            ticker: Stock ticker symbol
        
        Returns:
            Dict mapping filing type to list of file paths
        """
        paths = {}
        
        for filing_type in ["10-K", "10-Q", "8-K", "DEF 14A"]:
            ticker_dir = self.download_dir / "sec-edgar-filings" / ticker / filing_type
            if not ticker_dir.exists():
                ticker_dir = self.download_dir / ticker / filing_type
            
            if ticker_dir.exists():
                files = list(ticker_dir.rglob("*.htm")) + list(ticker_dir.rglob("*.txt"))
                if files:
                    paths[filing_type] = [str(f) for f in files]
        
        return paths


class SECFilingParser:
    """Parse SEC filings to extract financial data."""
    
    # Common XBRL tags for financial metrics
    REVENUE_TAGS = [
        "Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax",
        "SalesRevenueNet", "TotalRevenues", "NetSales"
    ]
    NET_INCOME_TAGS = [
        "NetIncomeLoss", "ProfitLoss", "NetIncome"
    ]
    TOTAL_ASSETS_TAGS = [
        "Assets", "TotalAssets"
    ]
    TOTAL_EQUITY_TAGS = [
        "StockholdersEquity", "TotalEquity", "ShareholdersEquity"
    ]
    
    def __init__(self):
        """Initialize SEC filing parser."""
        if not BS4_AVAILABLE:
            logger.warning(
                "BeautifulSoup not installed. "
                "Install with: pip install beautifulsoup4 lxml"
            )
    
    def parse_filing(self, file_path: str) -> Optional[ExtractedFinancials]:
        """
        Parse an SEC filing to extract financial metrics.
        
        Args:
            file_path: Path to the filing document
        
        Returns:
            ExtractedFinancials object or None if parsing fails
        """
        if not BS4_AVAILABLE:
            logger.error("BeautifulSoup required for parsing")
            return None
        
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            
            soup = BeautifulSoup(content, "lxml")
            
            # Extract ticker and filing info from path
            path = Path(file_path)
            parts = path.parts
            ticker = "UNKNOWN"
            filing_type = "UNKNOWN"
            
            for i, part in enumerate(parts):
                if part in ["10-K", "10-Q", "8-K"]:
                    filing_type = part
                    if i > 0:
                        ticker = parts[i - 1]
                    break
            
            # Extract financial data
            financials = ExtractedFinancials(
                ticker=ticker,
                filing_date=datetime.now().strftime("%Y-%m-%d"),
                filing_type=filing_type
            )
            
            # Try to extract values using XBRL tags
            financials.revenue = self._extract_value(soup, self.REVENUE_TAGS)
            financials.net_income = self._extract_value(soup, self.NET_INCOME_TAGS)
            financials.total_assets = self._extract_value(soup, self.TOTAL_ASSETS_TAGS)
            financials.total_equity = self._extract_value(soup, self.TOTAL_EQUITY_TAGS)
            
            # Calculate ratios if we have the data
            if financials.revenue and financials.net_income:
                financials.net_margin = financials.net_income / financials.revenue
            
            if financials.total_equity and financials.total_assets:
                financials.total_liabilities = financials.total_assets - financials.total_equity
                if financials.total_equity > 0:
                    financials.debt_to_equity = financials.total_liabilities / financials.total_equity
            
            return financials
            
        except Exception as e:
            logger.error(f"Error parsing filing {file_path}: {e}")
            return None
    
    def _extract_value(
        self,
        soup: "BeautifulSoup",
        tags: List[str]
    ) -> Optional[float]:
        """Extract a numeric value from XBRL tags."""
        for tag in tags:
            # Try different tag patterns
            elements = soup.find_all(attrs={"name": re.compile(tag, re.IGNORECASE)})
            if not elements:
                elements = soup.find_all(tag.lower())
            if not elements:
                elements = soup.find_all(re.compile(f".*:{tag}$", re.IGNORECASE))
            
            for elem in elements:
                try:
                    text = elem.get_text(strip=True)
                    # Remove commas and parentheses (negative numbers)
                    text = text.replace(",", "").replace("(", "-").replace(")", "")
                    value = float(text)
                    return value
                except (ValueError, AttributeError):
                    continue
        
        return None
    
    def parse_multiple_filings(
        self,
        filings: List[FilingMetadata]
    ) -> pd.DataFrame:
        """
        Parse multiple filings and return as DataFrame.
        
        Args:
            filings: List of FilingMetadata objects
        
        Returns:
            DataFrame with extracted financials
        """
        results = []
        
        for filing in filings:
            financials = self.parse_filing(filing.file_path)
            if financials:
                results.append(financials.to_dict())
        
        if not results:
            return pd.DataFrame()
        
        df = pd.DataFrame(results)
        df = df.sort_values("filing_date")
        
        return df


def download_and_parse_filings(
    tickers: List[str],
    num_annual: int = 4,
    num_quarterly: int = 8,
    company_name: str = "MidtermStockPlanner",
    email: str = "research@example.com"
) -> pd.DataFrame:
    """
    Convenience function to download and parse SEC filings for multiple tickers.
    
    Args:
        tickers: List of stock ticker symbols
        num_annual: Number of 10-K filings to download per ticker
        num_quarterly: Number of 10-Q filings to download per ticker
        company_name: Company name for SEC compliance
        email: Email for SEC compliance
    
    Returns:
        DataFrame with extracted financial metrics
    """
    downloader = SECFilingsDownloader(company_name, email)
    parser = SECFilingParser()
    
    all_financials = []
    
    for ticker in tickers:
        logger.info(f"Processing {ticker}...")
        
        # Download filings
        filings = downloader.download_filings(
            ticker,
            filing_types=["10-K", "10-Q"],
            num_filings=max(num_annual, num_quarterly)
        )
        
        # Parse each filing type
        for filing_type, filing_list in filings.items():
            df = parser.parse_multiple_filings(filing_list)
            if not df.empty:
                all_financials.append(df)
    
    if not all_financials:
        return pd.DataFrame()
    
    return pd.concat(all_financials, ignore_index=True)


def create_fundamental_features(
    filings_df: pd.DataFrame,
    price_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Create fundamental features from SEC filings for use in ML models.
    
    Merges financial data with price data and calculates additional features.
    
    Args:
        filings_df: DataFrame from parse_multiple_filings
        price_df: DataFrame with columns ['date', 'ticker', 'close', ...]
    
    Returns:
        price_df with additional fundamental features
    """
    if filings_df.empty:
        return price_df
    
    df = price_df.copy()
    df["date"] = pd.to_datetime(df["date"])
    
    # Ensure filings_df has proper date format
    filings_df = filings_df.copy()
    filings_df["filing_date"] = pd.to_datetime(filings_df["filing_date"])
    
    # Merge fundamental data with price data using merge_asof
    # This ensures we only use fundamental data that was available at each date
    result_dfs = []
    
    for ticker in df["ticker"].unique():
        ticker_prices = df[df["ticker"] == ticker].copy()
        ticker_filings = filings_df[filings_df["ticker"] == ticker].copy()
        
        if ticker_filings.empty:
            result_dfs.append(ticker_prices)
            continue
        
        ticker_prices = ticker_prices.sort_values("date")
        ticker_filings = ticker_filings.sort_values("filing_date")
        
        # Select columns to merge
        fund_cols = [
            "filing_date", "revenue", "net_income", "total_assets",
            "total_equity", "net_margin", "debt_to_equity"
        ]
        fund_cols = [c for c in fund_cols if c in ticker_filings.columns]
        
        merged = pd.merge_asof(
            ticker_prices,
            ticker_filings[fund_cols],
            left_on="date",
            right_on="filing_date",
            direction="backward"
        )
        
        result_dfs.append(merged)
    
    return pd.concat(result_dfs, ignore_index=True)
