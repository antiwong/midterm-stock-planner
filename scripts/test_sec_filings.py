"""Test SEC filings and fundamental data functionality."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.fundamental.data_fetcher import (
    FundamentalDataFetcher,
    fetch_fundamentals_for_universe,
)


def main():
    print("=" * 70)
    print("SEC FILINGS & FUNDAMENTAL DATA TEST")
    print("=" * 70)
    print()
    
    # Test with AMD and AMZN
    tickers = ["AMD", "AMZN"]
    
    fetcher = FundamentalDataFetcher()
    
    # =========================================================================
    # Test Company Info
    # =========================================================================
    print("-" * 70)
    print("COMPANY INFORMATION")
    print("-" * 70)
    
    for ticker in tickers:
        info = fetcher.get_company_info(ticker)
        if info:
            print(f"\n{info.name} ({info.ticker})")
            print(f"  Sector: {info.sector}")
            print(f"  Industry: {info.industry}")
            print(f"  Market Cap: ${info.market_cap/1e9:.1f}B" if info.market_cap else "  Market Cap: N/A")
            print(f"  Employees: {info.employees:,}" if info.employees else "  Employees: N/A")
    
    print()
    
    # =========================================================================
    # Test Financial Metrics
    # =========================================================================
    print("-" * 70)
    print("FINANCIAL METRICS")
    print("-" * 70)
    
    for ticker in tickers:
        metrics = fetcher.get_financial_metrics(ticker)
        if metrics:
            print(f"\n{ticker} Valuation & Financials:")
            print(f"  Trailing P/E: {metrics.trailing_pe:.1f}" if metrics.trailing_pe else "  Trailing P/E: N/A")
            print(f"  Forward P/E: {metrics.forward_pe:.1f}" if metrics.forward_pe else "  Forward P/E: N/A")
            print(f"  P/B Ratio: {metrics.price_to_book:.1f}" if metrics.price_to_book else "  P/B Ratio: N/A")
            print(f"  P/S Ratio: {metrics.price_to_sales:.1f}" if metrics.price_to_sales else "  P/S Ratio: N/A")
            print(f"  PEG Ratio: {metrics.peg_ratio:.2f}" if metrics.peg_ratio else "  PEG Ratio: N/A")
            print()
            print(f"  Profit Margin: {metrics.profit_margin*100:.1f}%" if metrics.profit_margin else "  Profit Margin: N/A")
            print(f"  Operating Margin: {metrics.operating_margin*100:.1f}%" if metrics.operating_margin else "  Operating Margin: N/A")
            print(f"  ROE: {metrics.return_on_equity*100:.1f}%" if metrics.return_on_equity else "  ROE: N/A")
            print(f"  ROA: {metrics.return_on_assets*100:.1f}%" if metrics.return_on_assets else "  ROA: N/A")
            print()
            print(f"  Revenue Growth: {metrics.revenue_growth*100:.1f}%" if metrics.revenue_growth else "  Revenue Growth: N/A")
            print(f"  Earnings Growth: {metrics.earnings_growth*100:.1f}%" if metrics.earnings_growth else "  Earnings Growth: N/A")
            print()
            print(f"  Current Ratio: {metrics.current_ratio:.2f}" if metrics.current_ratio else "  Current Ratio: N/A")
            print(f"  Debt/Equity: {metrics.debt_to_equity:.1f}%" if metrics.debt_to_equity else "  Debt/Equity: N/A")
            print(f"  Beta: {metrics.beta:.2f}" if metrics.beta else "  Beta: N/A")
    
    print()
    
    # =========================================================================
    # Test Financial Statements
    # =========================================================================
    print("-" * 70)
    print("FINANCIAL STATEMENTS (Annual)")
    print("-" * 70)
    
    for ticker in tickers:
        statements = fetcher.get_financial_statements(ticker, period="annual")
        
        if "income_statement" in statements and not statements["income_statement"].empty:
            print(f"\n{ticker} Income Statement (last 2 years):")
            income = statements["income_statement"]
            
            # Show key metrics
            key_items = ["Total Revenue", "Gross Profit", "Operating Income", "Net Income"]
            for item in key_items:
                if item in income.columns:
                    values = income[item].head(2)
                    if len(values) > 0:
                        latest = values.iloc[0] / 1e9 if values.iloc[0] else 0
                        print(f"  {item}: ${latest:.1f}B")
        
        if "balance_sheet" in statements and not statements["balance_sheet"].empty:
            print(f"\n{ticker} Balance Sheet (latest):")
            balance = statements["balance_sheet"]
            
            key_items = ["Total Assets", "Total Liabilities Net Minority Interest", "Total Equity Gross Minority Interest"]
            for item in key_items:
                if item in balance.columns:
                    value = balance[item].iloc[0] / 1e9 if balance[item].iloc[0] else 0
                    label = item.replace(" Gross Minority Interest", "").replace(" Net Minority Interest", "")
                    print(f"  {label}: ${value:.1f}B")
    
    print()
    
    # =========================================================================
    # Test Analyst Recommendations
    # =========================================================================
    print("-" * 70)
    print("ANALYST RECOMMENDATIONS")
    print("-" * 70)
    
    for ticker in tickers:
        recs = fetcher.get_analyst_recommendations(ticker)
        if not recs.empty:
            print(f"\n{ticker} Recent Recommendations:")
            recent = recs.tail(5)
            for idx, row in recent.iterrows():
                firm = row.get("Firm", "Unknown")
                grade = row.get("To Grade", row.get("toGrade", "N/A"))
                print(f"  {idx}: {firm} -> {grade}")
    
    print()
    
    # =========================================================================
    # Test News
    # =========================================================================
    print("-" * 70)
    print("RECENT NEWS")
    print("-" * 70)
    
    for ticker in tickers:
        news = fetcher.get_news(ticker, max_items=3)
        if news:
            print(f"\n{ticker} Recent News:")
            for item in news:
                print(f"  • {item['title'][:70]}...")
                print(f"    Source: {item['publisher']}")
    
    print()
    
    # =========================================================================
    # Test Batch Fetch
    # =========================================================================
    print("-" * 70)
    print("BATCH FUNDAMENTAL DATA")
    print("-" * 70)
    
    fundamentals_df = fetch_fundamentals_for_universe(tickers)
    
    if not fundamentals_df.empty:
        print("\nFundamental Metrics DataFrame:")
        print(fundamentals_df[["ticker", "trailing_pe", "forward_pe", "price_to_book", 
                               "profit_margin", "return_on_equity", "debt_to_equity"]].to_string(index=False))
    
    print()
    
    # =========================================================================
    # Test SEC Filings (if available)
    # =========================================================================
    print("-" * 70)
    print("SEC FILINGS")
    print("-" * 70)
    
    try:
        from src.fundamental.sec_filings import SECFilingsDownloader
        
        print("\nNote: SEC filing download requires sec-edgar-downloader package.")
        print("Install with: pip install sec-edgar-downloader")
        print()
        
        downloader = SECFilingsDownloader(
            company_name="MidtermStockPlanner",
            email="research@example.com"
        )
        
        if downloader.downloader:
            print("SEC downloader initialized successfully!")
            print("To download filings, run:")
            print("  downloader.download_filings('AMD', filing_types=['10-K', '10-Q'], num_filings=2)")
        else:
            print("SEC downloader not available (package not installed)")
            
    except ImportError as e:
        print(f"SEC filing module not available: {e}")
    
    print()
    print("=" * 70)
    print("TEST COMPLETE!")
    print("=" * 70)


if __name__ == "__main__":
    main()
