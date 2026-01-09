# Fundamental Data

> **Part of**: [Mid-term Stock Planner Design](design.md)
> 
> This document covers SEC filings, fundamental data fetching, and financial metrics.

## Related Documents

- [design.md](design.md) - Main overview and architecture
- [data-engineering.md](data-engineering.md) - Core data loading
- [technical-indicators.md](technical-indicators.md) - Technical features

---

## 1. Fundamental Data Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    FUNDAMENTAL DATA SOURCES                                  │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                         SEC EDGAR                                            │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐                        │
│  │    10-K     │   │    10-Q     │   │    8-K      │                        │
│  │  (Annual)   │   │ (Quarterly) │   │  (Current)  │                        │
│  └──────┬──────┘   └──────┬──────┘   └──────┬──────┘                        │
│         │                 │                 │                                │
│         └─────────────────┼─────────────────┘                                │
│                           │                                                  │
│                           ▼                                                  │
│                    ┌─────────────┐                                           │
│                    │ XBRL Parser │                                           │
│                    └──────┬──────┘                                           │
└──────────────────────────┼──────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      YAHOO FINANCE                                           │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐     │
│  │  Company    │   │  Valuation  │   │  Financials │   │   Analyst   │     │
│  │    Info     │   │   Ratios    │   │  Statements │   │    Data     │     │
│  └─────────────┘   └─────────────┘   └─────────────┘   └─────────────┘     │
└─────────────────────────────────────────────────────────────────────────────┘
                           │
                           ▼
                    ┌─────────────────┐
                    │ Feature Vector  │
                    │ (Fundamentals)  │
                    └─────────────────┘
```

---

## 2. SEC Filings

### 2.1 SEC Filings Downloader

```python
# src/fundamental/sec_filings.py

class SECFilingsDownloader:
    """Download and parse SEC filings from EDGAR."""
    
    def __init__(self, download_dir: Path = Path("data/sec-filings")):
        self.download_dir = download_dir
        self.downloader = Downloader("MyCompany", "email@example.com")
    
    def download_filings(
        self,
        ticker: str,
        filing_types: List[str] = ["10-K", "10-Q", "8-K"],
        num_filings: int = 4
    ) -> List[Path]:
        """
        Download recent SEC filings for a ticker.
        
        Args:
            ticker: Stock symbol
            filing_types: Types of filings to download
            num_filings: Number of each type to download
        
        Returns:
            List of paths to downloaded filings
        """
```

### 2.2 XBRL Parsing

```python
def parse_xbrl_financials(self, filing_path: Path) -> Dict[str, Any]:
    """
    Parse XBRL data from SEC filing.
    
    Extracts:
    - Revenue
    - Net income
    - Total assets
    - Total equity
    - Operating cash flow
    - EPS
    """

def extract_metrics_from_filing(self, filing_path: Path) -> Dict[str, float]:
    """
    Extract key financial metrics from filing.
    
    Returns:
        Dict with metrics:
        - revenue
        - net_income
        - gross_profit
        - operating_income
        - total_assets
        - total_liabilities
        - total_equity
        - cash_and_equivalents
        - debt
    """
```

### 2.3 Financial Ratios

```python
def calculate_ratios(self, metrics: Dict[str, float]) -> Dict[str, float]:
    """
    Calculate financial ratios from metrics.
    
    Returns:
        Dict with ratios:
        - gross_margin: gross_profit / revenue
        - operating_margin: operating_income / revenue
        - net_margin: net_income / revenue
        - debt_to_equity: debt / total_equity
        - current_ratio: current_assets / current_liabilities
        - roa: net_income / total_assets
        - roe: net_income / total_equity
    """
```

### 2.4 Time Series Creation

```python
def create_fundamental_time_series(
    self,
    ticker: str,
    filing_types: List[str] = ["10-K", "10-Q"]
) -> pd.DataFrame:
    """
    Create time series of fundamental data from filings.
    
    Returns:
        DataFrame with columns:
        - date: Filing date
        - ticker
        - revenue, net_income, assets, equity, etc.
        - gross_margin, operating_margin, roe, etc.
    """
```

---

## 3. Yahoo Finance Data

### 3.1 FundamentalDataFetcher

```python
# src/fundamental/data_fetcher.py

class FundamentalDataFetcher:
    """Fetch fundamental data from Yahoo Finance."""
    
    def __init__(self):
        pass
    
    def get_company_info(self, ticker: str) -> Dict[str, Any]:
        """
        Get company information.
        
        Returns:
            Dict with:
            - name: Company name
            - sector: Sector classification
            - industry: Industry classification
            - description: Business description
            - employees: Number of employees
            - website: Company website
        """
    
    def get_valuation_ratios(self, ticker: str) -> Dict[str, float]:
        """
        Get valuation ratios.
        
        Returns:
            Dict with:
            - pe_ratio: Price/Earnings (trailing)
            - forward_pe: Price/Earnings (forward)
            - pb_ratio: Price/Book
            - ps_ratio: Price/Sales
            - peg_ratio: P/E to Growth ratio
            - enterprise_value: EV
            - ev_to_ebitda: EV/EBITDA
        """
    
    def get_profitability_metrics(self, ticker: str) -> Dict[str, float]:
        """
        Get profitability metrics.
        
        Returns:
            Dict with:
            - roe: Return on Equity
            - roa: Return on Assets
            - gross_margin: Gross profit margin
            - operating_margin: Operating margin
            - net_margin: Net profit margin
        """
    
    def get_financial_health_metrics(self, ticker: str) -> Dict[str, float]:
        """
        Get financial health metrics.
        
        Returns:
            Dict with:
            - current_ratio: Current assets / Current liabilities
            - quick_ratio: (Current assets - Inventory) / Current liab.
            - debt_to_equity: Total debt / Total equity
            - interest_coverage: EBIT / Interest expense
        """
```

### 3.2 Additional Data

```python
def get_dividend_data(self, ticker: str) -> Dict[str, Any]:
    """Get dividend information."""

def get_financial_statements(self, ticker: str) -> Dict[str, pd.DataFrame]:
    """
    Get financial statements.
    
    Returns:
        Dict with:
        - income_statement: Annual income statement
        - balance_sheet: Annual balance sheet
        - cash_flow: Annual cash flow statement
        - income_statement_quarterly: Quarterly income statement
    """

def get_analyst_data(self, ticker: str) -> Dict[str, Any]:
    """
    Get analyst recommendations and estimates.
    
    Returns:
        Dict with:
        - recommendation: Current recommendation
        - target_price: Average target price
        - target_low: Low target
        - target_high: High target
        - num_analysts: Number of analysts
        - earnings_estimates: EPS estimates
    """

def get_news(self, ticker: str, max_articles: int = 10) -> List[Dict]:
    """Get recent news articles."""

def get_institutional_holders(self, ticker: str) -> pd.DataFrame:
    """Get top institutional holders."""

def get_insider_transactions(self, ticker: str) -> pd.DataFrame:
    """Get recent insider transactions."""
```

### 3.3 All-in-One Fetch

```python
def get_all_fundamental_data(self, ticker: str) -> Dict[str, Any]:
    """
    Fetch all available fundamental data for a ticker.
    
    Returns comprehensive dict with all metrics.
    """
    return {
        "company_info": self.get_company_info(ticker),
        "valuation": self.get_valuation_ratios(ticker),
        "profitability": self.get_profitability_metrics(ticker),
        "financial_health": self.get_financial_health_metrics(ticker),
        "dividends": self.get_dividend_data(ticker),
        "analyst": self.get_analyst_data(ticker),
        "statements": self.get_financial_statements(ticker),
    }
```

---

## 4. Feature Creation

### 4.1 Fundamental Features

```python
def create_fundamental_features(
    price_df: pd.DataFrame,
    fundamental_data: Dict[str, Dict]
) -> pd.DataFrame:
    """
    Merge fundamental data with price data.
    
    Handles:
    - Forward-filling fundamentals between reports
    - Lag application to avoid look-ahead bias
    - Normalization and ranking
    """
```

### 4.2 Valuation Features

```python
def create_valuation_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create cross-sectional valuation features.
    
    Adds:
    - pe_rank: PE ratio percentile within universe
    - pb_rank: PB ratio percentile
    - value_score: Composite value score
    - quality_score: ROE + margins composite
    """
```

---

## 5. Data Quality

### 5.1 Handling Missing Data

```python
def handle_missing_fundamentals(
    df: pd.DataFrame,
    method: str = "forward_fill",
    max_gap_days: int = 120
) -> pd.DataFrame:
    """
    Handle missing fundamental data.
    
    Methods:
    - forward_fill: Fill forward from last known value
    - interpolate: Linear interpolation
    - sector_median: Fill with sector median
    """
```

### 5.2 Data Validation

```python
def validate_fundamental_data(data: Dict[str, Any]) -> List[str]:
    """
    Validate fundamental data quality.
    
    Checks:
    - Required fields present
    - Values within reasonable ranges
    - Consistency between metrics
    """
```

---

## 6. Usage Examples

### 6.1 Fetch Fundamental Data

```python
from src.fundamental.data_fetcher import FundamentalDataFetcher

fetcher = FundamentalDataFetcher()

# Get all data for a ticker
data = fetcher.get_all_fundamental_data("NVDA")

print(f"Company: {data['company_info']['name']}")
print(f"Sector: {data['company_info']['sector']}")
print(f"PE Ratio: {data['valuation']['pe_ratio']:.2f}")
print(f"ROE: {data['profitability']['roe']:.2%}")
```

### 6.2 Download SEC Filings

```python
from src.fundamental.sec_filings import SECFilingsDownloader

downloader = SECFilingsDownloader()

# Download recent 10-K and 10-Q filings
filings = downloader.download_filings(
    ticker="NVDA",
    filing_types=["10-K", "10-Q"],
    num_filings=4
)

# Parse and extract metrics
for filing in filings:
    metrics = downloader.extract_metrics_from_filing(filing)
    ratios = downloader.calculate_ratios(metrics)
    print(f"Revenue: ${metrics['revenue']:,.0f}")
    print(f"Net Margin: {ratios['net_margin']:.2%}")
```

### 6.3 Create Time Series

```python
# Create fundamental time series
fund_ts = downloader.create_fundamental_time_series("NVDA")

# Merge with price data
df = create_fundamental_features(price_df, fund_ts)
```

---

## 7. Metrics Summary

| Category | Metrics |
|----------|---------|
| **Valuation** | PE, Forward PE, PB, PS, PEG, EV/EBITDA |
| **Profitability** | ROE, ROA, Gross Margin, Operating Margin, Net Margin |
| **Financial Health** | Current Ratio, Quick Ratio, Debt/Equity, Interest Coverage |
| **Growth** | Revenue Growth, EPS Growth, Earnings Estimates |
| **Analyst** | Recommendation, Target Price, Number of Analysts |
| **Quality** | ROE Stability, Margin Stability, Earnings Quality |

---

## Related Documents

- **Back to**: [design.md](design.md) - Main overview
- **Core Data**: [data-engineering.md](data-engineering.md) - Data loading
- **Technical**: [technical-indicators.md](technical-indicators.md) - Technical features
