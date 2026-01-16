#!/usr/bin/env python3
"""
Download Stock Prices Script
============================
Downloads historical price data for watchlist stocks using yfinance.

Features:
- Downloads OHLCV data for all stocks in a watchlist
- Validates data integrity (missing stocks, date ranges, gaps)
- Generates a validation report
- Merges with existing price data

Usage:
    # Download for a specific watchlist
    python scripts/download_prices.py --watchlist nasdaq_100
    
    # Download for all watchlists (everything)
    python scripts/download_prices.py --watchlist everything
    
    # Specify date range
    python scripts/download_prices.py --watchlist sp500 --start 2020-01-01 --end 2024-12-31
    
    # Validate only (no download)
    python scripts/download_prices.py --validate-only
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import json
import time

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    print("⚠️ yfinance not installed. Run: pip install yfinance")


class DataValidator:
    """Validates price data integrity."""
    
    def __init__(self, price_df: pd.DataFrame, required_tickers: List[str], 
                 start_date: str, end_date: str):
        self.price_df = price_df
        self.required_tickers = [t.upper() for t in required_tickers]
        self.start_date = pd.to_datetime(start_date)
        self.end_date = pd.to_datetime(end_date)
        self.errors = []
        self.warnings = []
        self.stats = {}
    
    def validate(self) -> Dict[str, Any]:
        """Run all validation checks."""
        self._check_missing_tickers()
        self._check_date_range()
        self._check_data_gaps()
        self._check_data_quality()
        self._compute_stats()
        
        return {
            'valid': len(self.errors) == 0,
            'errors': self.errors,
            'warnings': self.warnings,
            'stats': self.stats,
            'summary': self._generate_summary()
        }
    
    def _check_missing_tickers(self):
        """Check for tickers in watchlist but not in data."""
        if self.price_df.empty:
            self.errors.append({
                'type': 'NO_DATA',
                'message': 'Price dataframe is empty',
                'details': None
            })
            return
        
        available_tickers = set(self.price_df['ticker'].str.upper().unique())
        missing = set(self.required_tickers) - available_tickers
        
        if missing:
            self.errors.append({
                'type': 'MISSING_TICKERS',
                'message': f'{len(missing)} tickers missing from price data',
                'details': sorted(list(missing))
            })
        
        self.stats['available_tickers'] = len(available_tickers & set(self.required_tickers))
        self.stats['missing_tickers'] = len(missing)
        self.stats['total_required'] = len(self.required_tickers)
        self.stats['coverage_pct'] = (self.stats['available_tickers'] / self.stats['total_required'] * 100) if self.stats['total_required'] > 0 else 0
    
    def _check_date_range(self):
        """Check if data covers the required date range."""
        if self.price_df.empty:
            return
        
        self.price_df['date'] = pd.to_datetime(self.price_df['date'])
        data_start = self.price_df['date'].min()
        data_end = self.price_df['date'].max()
        
        self.stats['data_start'] = str(data_start.date())
        self.stats['data_end'] = str(data_end.date())
        self.stats['required_start'] = str(self.start_date.date())
        self.stats['required_end'] = str(self.end_date.date())
        
        if data_start > self.start_date:
            self.warnings.append({
                'type': 'DATE_RANGE_START',
                'message': f'Data starts at {data_start.date()}, but {self.start_date.date()} was requested',
                'details': {'data_start': str(data_start.date()), 'required_start': str(self.start_date.date())}
            })
        
        if data_end < self.end_date:
            self.warnings.append({
                'type': 'DATE_RANGE_END',
                'message': f'Data ends at {data_end.date()}, but {self.end_date.date()} was requested',
                'details': {'data_end': str(data_end.date()), 'required_end': str(self.end_date.date())}
            })
    
    def _check_data_gaps(self):
        """Check for significant gaps in data for each ticker."""
        if self.price_df.empty:
            return
        
        gap_issues = []
        
        for ticker in self.price_df['ticker'].unique():
            ticker_data = self.price_df[self.price_df['ticker'] == ticker].sort_values('date')
            
            if len(ticker_data) < 10:
                gap_issues.append({
                    'ticker': ticker,
                    'issue': 'insufficient_data',
                    'rows': len(ticker_data)
                })
                continue
            
            # Check for gaps > 5 business days
            ticker_data['date_diff'] = ticker_data['date'].diff().dt.days
            large_gaps = ticker_data[ticker_data['date_diff'] > 7]
            
            if len(large_gaps) > 0:
                gap_issues.append({
                    'ticker': ticker,
                    'issue': 'large_gaps',
                    'gap_count': len(large_gaps),
                    'max_gap_days': int(ticker_data['date_diff'].max())
                })
        
        if gap_issues:
            self.warnings.append({
                'type': 'DATA_GAPS',
                'message': f'{len(gap_issues)} tickers have data gaps or insufficient data',
                'details': gap_issues[:10]  # Limit to first 10
            })
        
        self.stats['tickers_with_gaps'] = len(gap_issues)
    
    def _check_data_quality(self):
        """Check for data quality issues (nulls, negative prices, etc.)."""
        if self.price_df.empty:
            return
        
        quality_issues = []
        
        # Check for null values
        null_counts = self.price_df[['open', 'high', 'low', 'close', 'volume']].isnull().sum()
        if null_counts.sum() > 0:
            quality_issues.append({
                'issue': 'null_values',
                'details': null_counts[null_counts > 0].to_dict()
            })
        
        # Check for negative prices
        for col in ['open', 'high', 'low', 'close']:
            if col in self.price_df.columns:
                neg_count = (self.price_df[col] < 0).sum()
                if neg_count > 0:
                    quality_issues.append({
                        'issue': 'negative_prices',
                        'column': col,
                        'count': int(neg_count)
                    })
        
        # Check for zero volume
        if 'volume' in self.price_df.columns:
            zero_vol = (self.price_df['volume'] == 0).sum()
            if zero_vol > len(self.price_df) * 0.1:  # More than 10%
                quality_issues.append({
                    'issue': 'zero_volume',
                    'count': int(zero_vol),
                    'pct': round(zero_vol / len(self.price_df) * 100, 1)
                })
        
        if quality_issues:
            self.warnings.append({
                'type': 'DATA_QUALITY',
                'message': f'{len(quality_issues)} data quality issues detected',
                'details': quality_issues
            })
        
        self.stats['quality_issues'] = len(quality_issues)
    
    def _compute_stats(self):
        """Compute overall statistics."""
        if self.price_df.empty:
            return
        
        self.stats['total_rows'] = len(self.price_df)
        self.stats['unique_tickers'] = self.price_df['ticker'].nunique()
        self.stats['date_range_days'] = (self.price_df['date'].max() - self.price_df['date'].min()).days
        self.stats['avg_rows_per_ticker'] = round(len(self.price_df) / self.price_df['ticker'].nunique(), 0)
    
    def _generate_summary(self) -> str:
        """Generate human-readable summary."""
        lines = []
        
        if len(self.errors) == 0:
            lines.append("✅ Data validation PASSED")
        else:
            lines.append(f"❌ Data validation FAILED with {len(self.errors)} error(s)")
        
        if len(self.warnings) > 0:
            lines.append(f"⚠️ {len(self.warnings)} warning(s) detected")
        
        lines.append(f"\nCoverage: {self.stats.get('available_tickers', 0)}/{self.stats.get('total_required', 0)} tickers ({self.stats.get('coverage_pct', 0):.1f}%)")
        lines.append(f"Date Range: {self.stats.get('data_start', 'N/A')} to {self.stats.get('data_end', 'N/A')}")
        lines.append(f"Total Rows: {self.stats.get('total_rows', 0):,}")
        
        return '\n'.join(lines)


class PriceDownloader:
    """Downloads historical price data using yfinance."""
    
    def __init__(self, output_path: str = "data/prices.csv"):
        self.output_path = Path(output_path)
        self.download_log = []
        self.failed_tickers = []
        self.successful_tickers = []
        self.failed_reasons = {}  # Track why each ticker failed
    
    def _normalize_ticker(self, ticker: str) -> tuple[str, Optional[str]]:
        """Normalize ticker format and return (normalized_ticker, original_if_changed).
        
        Args:
            ticker: Original ticker symbol
        
        Returns:
            Tuple of (normalized_ticker, original_if_changed_or_None)
        """
        original = ticker.upper()
        
        # Known format fixes
        format_fixes = {
            'BRK.B': 'BRK-B',
            'BRKB': 'BRK-B',
        }
        
        if original in format_fixes:
            return format_fixes[original], original
        
        return original, None
    
    def download(self, tickers: List[str], start_date: str, end_date: str,
                 merge_existing: bool = True, batch_size: int = 50) -> pd.DataFrame:
        """
        Download price data for tickers.
        
        Args:
            tickers: List of ticker symbols
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            merge_existing: Whether to merge with existing data
            batch_size: Number of tickers to download per batch
        
        Returns:
            DataFrame with all price data
        """
        if not YFINANCE_AVAILABLE:
            raise ImportError("yfinance is required. Install with: pip install yfinance")
        
        print(f"\n📥 Downloading price data for {len(tickers)} tickers...")
        print(f"   Period: {start_date} to {end_date}")
        
        all_data = []
        # Normalize tickers and track format changes
        normalized_tickers = []
        ticker_map = {}  # Maps normalized -> original for display
        
        for t in tickers:
            normalized, original = self._normalize_ticker(t)
            normalized_tickers.append(normalized)
            if original:
                ticker_map[normalized] = original
                print(f"   ℹ️  Format fix: {original} → {normalized}")
        
        tickers = normalized_tickers
        
        # Process in batches
        for i in range(0, len(tickers), batch_size):
            batch = tickers[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(tickers) + batch_size - 1) // batch_size
            
            print(f"\n   Batch {batch_num}/{total_batches}: {len(batch)} tickers...")
            
            try:
                # Download batch with retry logic
                from src.app.dashboard.utils.retry import retry_network
                
                @retry_network
                def download_batch():
                    return yf.download(
                        batch,
                        start=start_date,
                        end=end_date,
                        group_by='ticker',
                        auto_adjust=True,
                        progress=False,
                        threads=True
                    )
                
                data = download_batch()
                
                # Process downloaded data
                if len(batch) == 1:
                    # Single ticker - different format
                    ticker = batch[0]
                    if not data.empty:
                        df = data.reset_index()
                        df['ticker'] = ticker
                        df.columns = [c.lower() for c in df.columns]
                        all_data.append(df)
                        self.successful_tickers.append(ticker)
                        self._log(f"✓ {ticker}: {len(df)} rows")
                    else:
                        original = ticker_map.get(ticker, ticker)
                        self.failed_tickers.append(original)
                        self.failed_reasons[original] = "No data returned (possibly delisted)"
                        self._log(f"✗ {ticker}: No data")
                else:
                    # Multiple tickers
                    for ticker in batch:
                        try:
                            if ticker in data.columns.get_level_values(0):
                                ticker_data = data[ticker].reset_index()
                                ticker_data['ticker'] = ticker
                                ticker_data.columns = [c.lower() for c in ticker_data.columns]
                                
                                # Drop rows with all NaN
                                ticker_data = ticker_data.dropna(subset=['close'])
                                
                                if len(ticker_data) > 0:
                                    all_data.append(ticker_data)
                                    # Use original ticker name if it was normalized
                                    display_ticker = ticker_map.get(ticker, ticker)
                                    self.successful_tickers.append(display_ticker)
                                    self._log(f"✓ {display_ticker}: {len(ticker_data)} rows")
                                else:
                                    original = ticker_map.get(ticker, ticker)
                                    self.failed_tickers.append(original)
                                    self.failed_reasons[original] = "No valid data (all NaN)"
                                    self._log(f"✗ {ticker}: No valid data")
                            else:
                                original = ticker_map.get(ticker, ticker)
                                self.failed_tickers.append(original)
                                self.failed_reasons[original] = "Symbol not found in download results"
                                self._log(f"✗ {ticker}: Not found")
                        except Exception as e:
                            original = ticker_map.get(ticker, ticker)
                            self.failed_tickers.append(original)
                            error_msg = str(e)
                            if 'delisted' in error_msg.lower() or 'timezone' in error_msg.lower():
                                self.failed_reasons[original] = "Possibly delisted or invalid symbol"
                            elif 'timeout' in error_msg.lower():
                                self.failed_reasons[original] = "Download timeout (try again later)"
                            else:
                                self.failed_reasons[original] = f"Error: {error_msg[:100]}"
                            self._log(f"✗ {ticker}: {error_msg[:50]}")
                
                # Rate limiting
                time.sleep(0.5)
                
            except Exception as e:
                error_msg = str(e)
                print(f"   ⚠️ Batch failed: {error_msg}")
                
                # Categorize batch failure
                if 'delisted' in error_msg.lower() or 'timezone' in error_msg.lower():
                    reason = "Possibly delisted or invalid symbols"
                elif 'timeout' in error_msg.lower():
                    reason = "Download timeout (try again later)"
                else:
                    reason = f"Batch error: {error_msg[:100]}"
                
                # Mark each ticker in batch as failed
                for ticker in batch:
                    original = ticker_map.get(ticker, ticker)
                    self.failed_tickers.append(original)
                    self.failed_reasons[original] = reason
        
        # Combine all data
        if all_data:
            result_df = pd.concat(all_data, ignore_index=True)
            
            # Standardize columns
            result_df = result_df.rename(columns={
                'date': 'date',
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'volume': 'volume'
            })
            
            # Ensure required columns
            required_cols = ['date', 'ticker', 'open', 'high', 'low', 'close', 'volume']
            for col in required_cols:
                if col not in result_df.columns:
                    result_df[col] = np.nan
            
            result_df = result_df[required_cols]
            result_df['date'] = pd.to_datetime(result_df['date']).dt.date
            
            # Merge with existing if requested
            if merge_existing and self.output_path.exists():
                print(f"\n   Merging with existing data...")
                existing_df = pd.read_csv(self.output_path, parse_dates=['date'])
                existing_df['date'] = pd.to_datetime(existing_df['date']).dt.date
                
                # Remove duplicates (keep new data)
                combined = pd.concat([existing_df, result_df], ignore_index=True)
                combined = combined.drop_duplicates(subset=['date', 'ticker'], keep='last')
                combined = combined.sort_values(['ticker', 'date'])
                result_df = combined
            
            return result_df
        else:
            return pd.DataFrame()
    
    def save(self, df: pd.DataFrame):
        """Save DataFrame to CSV."""
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(self.output_path, index=False)
        print(f"\n   💾 Saved to {self.output_path}")
    
    def _log(self, message: str):
        """Add to download log."""
        self.download_log.append(message)
    
    def get_report(self) -> Dict[str, Any]:
        """Get download report."""
        return {
            'successful': len(self.successful_tickers),
            'failed': len(self.failed_tickers),
            'failed_tickers': self.failed_tickers,
            'failed_reasons': getattr(self, 'failed_reasons', {}),
            'log': self.download_log
        }


def generate_validation_report(validation_result: Dict, download_report: Optional[Dict],
                               output_path: Path, watchlist_name: str) -> Path:
    """Generate a validation report file."""
    
    report = {
        'report_type': 'data_validation',
        'generated_at': datetime.now().isoformat(),
        'watchlist': watchlist_name,
        'validation': validation_result,
    }
    
    if download_report:
        report['download'] = download_report
    
    # Determine report status
    if validation_result['valid']:
        report['status'] = 'PASSED'
        report['status_emoji'] = '✅'
    elif validation_result['errors']:
        report['status'] = 'FAILED'
        report['status_emoji'] = '❌'
    else:
        report['status'] = 'WARNING'
        report['status_emoji'] = '⚠️'
    
    # Save JSON report
    report_path = output_path / f"data_validation_{watchlist_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    
    # Also generate markdown report
    md_path = output_path / f"data_validation_{watchlist_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(md_path, 'w') as f:
        f.write(f"# Data Validation Report\n\n")
        f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Watchlist:** {watchlist_name}\n")
        f.write(f"**Status:** {report['status_emoji']} {report['status']}\n\n")
        
        f.write("---\n\n")
        
        # Summary
        f.write("## Summary\n\n")
        f.write(validation_result['summary'] + "\n\n")
        
        # Errors
        if validation_result['errors']:
            f.write("## ❌ Errors\n\n")
            for error in validation_result['errors']:
                f.write(f"### {error['type']}\n")
                f.write(f"{error['message']}\n\n")
                if error.get('details'):
                    if isinstance(error['details'], list):
                        f.write("**Affected items:**\n")
                        for item in error['details'][:20]:
                            f.write(f"- {item}\n")
                        if len(error['details']) > 20:
                            f.write(f"- ... and {len(error['details']) - 20} more\n")
                    else:
                        f.write(f"**Details:** {error['details']}\n")
                f.write("\n")
        
        # Warnings
        if validation_result['warnings']:
            f.write("## ⚠️ Warnings\n\n")
            for warning in validation_result['warnings']:
                f.write(f"### {warning['type']}\n")
                f.write(f"{warning['message']}\n\n")
                if warning.get('details'):
                    f.write(f"```json\n{json.dumps(warning['details'], indent=2, default=str)[:500]}\n```\n\n")
        
        # Statistics
        f.write("## 📊 Statistics\n\n")
        for key, value in validation_result['stats'].items():
            f.write(f"- **{key.replace('_', ' ').title()}:** {value}\n")
        f.write("\n")
        
        # Download report
        if download_report:
            f.write("## 📥 Download Report\n\n")
            f.write(f"- **Successful:** {download_report['successful']}\n")
            f.write(f"- **Failed:** {download_report['failed']}\n")
            if download_report['failed_tickers']:
                f.write(f"\n**Failed tickers:** {', '.join(download_report['failed_tickers'][:50])}\n")
                if len(download_report['failed_tickers']) > 50:
                    f.write(f"... and {len(download_report['failed_tickers']) - 50} more\n")
    
    return report_path


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Download and validate stock price data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download for a specific watchlist
  python scripts/download_prices.py --watchlist nasdaq_100
  
  # Download with custom date range
  python scripts/download_prices.py --watchlist sp500 --start 2020-01-01 --end 2024-12-31
  
  # Validate existing data only
  python scripts/download_prices.py --watchlist everything --validate-only
  
  # Force fresh download (don't merge)
  python scripts/download_prices.py --watchlist tech_giants --no-merge
"""
    )
    
    parser.add_argument("--watchlist", "-w", type=str, default="custom",
                       help="Watchlist to download (default: custom)")
    parser.add_argument("--start", "-s", type=str, default=None,
                       help="Start date (YYYY-MM-DD, default: 3 years ago)")
    parser.add_argument("--end", "-e", type=str, default=None,
                       help="End date (YYYY-MM-DD, default: today)")
    parser.add_argument("--output", "-o", type=str, default="data/prices.csv",
                       help="Output file path")
    parser.add_argument("--validate-only", action="store_true",
                       help="Only validate existing data, don't download")
    parser.add_argument("--no-merge", action="store_true",
                       help="Don't merge with existing data (fresh download)")
    parser.add_argument("--report-dir", type=str, default="output",
                       help="Directory for validation reports")
    
    args = parser.parse_args()
    
    # Set default dates
    if args.end is None:
        args.end = datetime.now().strftime('%Y-%m-%d')
    if args.start is None:
        args.start = (datetime.now() - timedelta(days=3*365)).strftime('%Y-%m-%d')
    
    print("=" * 70)
    print("STOCK PRICE DOWNLOAD & VALIDATION")
    print("=" * 70)
    print(f"Watchlist: {args.watchlist}")
    print(f"Period: {args.start} to {args.end}")
    print(f"Output: {args.output}")
    print("=" * 70)
    
    # Load watchlist
    from src.data.watchlists import WatchlistManager
    
    wm = WatchlistManager.from_config_dir('config')
    watchlist = wm.get_watchlist(args.watchlist)
    
    if not watchlist:
        print(f"❌ Watchlist '{args.watchlist}' not found")
        print(f"   Available: {', '.join(wm.list_watchlists())}")
        return 1
    
    tickers = watchlist.symbols
    print(f"\n📋 Watchlist '{args.watchlist}' contains {len(tickers)} tickers")
    
    download_report = None
    
    if not args.validate_only:
        # Download data
        if not YFINANCE_AVAILABLE:
            print("\n❌ yfinance is required for downloading.")
            print("   Install with: pip install yfinance")
            return 1
        
        downloader = PriceDownloader(args.output)
        
        try:
            df = downloader.download(
                tickers=tickers,
                start_date=args.start,
                end_date=args.end,
                merge_existing=not args.no_merge
            )
            
            if not df.empty:
                downloader.save(df)
                download_report = downloader.get_report()
                
                print(f"\n📊 Download Summary:")
                print(f"   ✅ Successful: {download_report['successful']}")
                print(f"   ❌ Failed: {download_report['failed']}")
            else:
                print("\n❌ No data downloaded")
                return 1
                
        except Exception as e:
            print(f"\n❌ Download failed: {e}")
            import traceback
            traceback.print_exc()
            return 1
    
    # Validate data
    print("\n" + "=" * 70)
    print("DATA VALIDATION")
    print("=" * 70)
    
    output_path = Path(args.output)
    if not output_path.exists():
        print(f"❌ Price file not found: {args.output}")
        return 1
    
    price_df = pd.read_csv(output_path, parse_dates=['date'])
    
    validator = DataValidator(
        price_df=price_df,
        required_tickers=tickers,
        start_date=args.start,
        end_date=args.end
    )
    
    validation_result = validator.validate()
    
    print(f"\n{validation_result['summary']}")
    
    # Generate report
    report_dir = Path(args.report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    
    report_path = generate_validation_report(
        validation_result=validation_result,
        download_report=download_report,
        output_path=report_dir,
        watchlist_name=args.watchlist
    )
    
    print(f"\n📄 Validation report saved: {report_path}")
    
    # Print errors/warnings
    if validation_result['errors']:
        print("\n" + "=" * 70)
        print("❌ ERRORS")
        print("=" * 70)
        for error in validation_result['errors']:
            print(f"\n   {error['type']}: {error['message']}")
            if error.get('details') and isinstance(error['details'], list):
                print(f"   Missing: {', '.join(error['details'][:10])}...")
    
    if validation_result['warnings']:
        print("\n" + "=" * 70)
        print("⚠️ WARNINGS")
        print("=" * 70)
        for warning in validation_result['warnings']:
            print(f"\n   {warning['type']}: {warning['message']}")
    
    print("\n" + "=" * 70)
    if validation_result['valid']:
        print("✅ DATA VALIDATION PASSED")
    else:
        print("❌ DATA VALIDATION FAILED - Review errors above")
    print("=" * 70)
    
    return 0 if validation_result['valid'] else 1


if __name__ == "__main__":
    sys.exit(main())
