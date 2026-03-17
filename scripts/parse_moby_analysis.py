#!/usr/bin/env python3
"""
Parse Moby.co Stock Analysis Markdown Files
=============================================
Extracts structured data (ticker, price, target, upside, rating, earnings date)
from moby_news/ markdown files and saves to CSV for use by the model and dashboard.

Input:  moby_news/Moby.co Stock Analysis - *.md
Output: data/sentiment/moby_analysis.csv

Usage:
    python scripts/parse_moby_analysis.py
    python scripts/parse_moby_analysis.py --input moby_news/ --output data/sentiment/moby_analysis.csv
"""

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd


# Patterns for extracting structured data from Moby analysis markdown
# Match: ## 1\. Lumen Technologies Inc. (LUMN)
# Also: 3\. Cameco Corporation (CCJ)
HEADER_PATTERN = re.compile(
    r'^(?:##\s+)?\d+\\?\.\s+(.+?)\s*\(([A-Z]{1,5})\)\s*$'
)

# Match: Current Price: ~$6.40 | Price Target: $7.43 (16% upside) | Rating: Overweight
METRICS_PATTERN = re.compile(
    r'Current\s+Price:\s*\\?~?\$?([\d,]+\.?\d*)\s*\|'
    r'\s*Price\s+Target:\s*\$?([\d,]+\.?\d*)\s*'
    r'\((\d+)%\s*upside\)\s*\|'
    r'\s*Rating:\s*(\w+)'
)

# Match: Upcoming Earnings: April 29
EARNINGS_PATTERN = re.compile(
    r'Upcoming\s+Earnings:\s*(\w+\s+\d+)'
)

# Match: Article Title: "Some title here"
TITLE_PATTERN = re.compile(
    r'Article\s+Title:\s*["\u201c](.+?)["\u201d]'
)


def parse_analysis_file(filepath: Path) -> List[Dict]:
    """Parse a single Moby stock analysis markdown file."""
    text = filepath.read_text(encoding="utf-8")
    lines = text.split("\n")

    # Extract date from filename: "Moby.co Stock Analysis - March 17, 2026.md"
    date_match = re.search(r'(\w+ \d+,? \d{4})', filepath.name)
    file_date = ""
    if date_match:
        try:
            file_date = pd.to_datetime(date_match.group(1)).strftime("%Y-%m-%d")
        except Exception:
            file_date = date_match.group(1)

    results = []
    current = None

    for i, line in enumerate(lines):
        line_stripped = line.rstrip()
        # Check for stock header
        header = HEADER_PATTERN.match(line_stripped)
        if header:
            if current:
                # Extract body text for sentiment
                current["body_length"] = len(current.get("_body", ""))
                current.pop("_body", None)
                results.append(current)

            current = {
                "date": file_date,
                "company": header.group(1).replace("\\", ""),
                "ticker": header.group(2),
                "current_price": None,
                "price_target": None,
                "upside_pct": None,
                "rating": None,
                "earnings_date": None,
                "article_title": None,
                "source_file": filepath.name,
                "_body": "",
            }
            continue

        if current is None:
            continue

        # Check for metrics line (strip markdown formatting like ###### * ... *)
        clean_line = line.replace("\\~", "~").replace("\\", "").strip(" *#")
        metrics = METRICS_PATTERN.search(clean_line)
        if metrics:
            current["current_price"] = float(metrics.group(1).replace(",", ""))
            current["price_target"] = float(metrics.group(2).replace(",", ""))
            current["upside_pct"] = int(metrics.group(3))
            current["rating"] = metrics.group(4)

        # Check for earnings date
        earnings = EARNINGS_PATTERN.search(clean_line)
        if earnings:
            current["earnings_date"] = earnings.group(1)

        # Check for article title
        title = TITLE_PATTERN.search(clean_line)
        if title:
            current["article_title"] = title.group(1)

        # Accumulate body text
        current["_body"] += line + "\n"

    # Don't forget last stock
    if current:
        current["body_length"] = len(current.get("_body", ""))
        current.pop("_body", None)
        results.append(current)

    return results


def parse_all_files(input_dir: Path) -> pd.DataFrame:
    """Parse all Moby analysis files in directory."""
    all_results = []

    analysis_files = sorted(input_dir.glob("*Stock Analysis*.md"))
    if not analysis_files:
        print(f"No analysis files found in {input_dir}")
        return pd.DataFrame()

    for filepath in analysis_files:
        print(f"  Parsing: {filepath.name}")
        stocks = parse_analysis_file(filepath)
        all_results.extend(stocks)
        for s in stocks:
            target_str = f"${s['price_target']:,.0f}" if s['price_target'] else "?"
            print(f"    {s['ticker']:6s} ${s['current_price']:>8,.2f} -> {target_str} "
                  f"({s['upside_pct']}% upside) [{s['rating']}]")

    df = pd.DataFrame(all_results)
    return df


def main():
    parser = argparse.ArgumentParser(description="Parse Moby stock analysis markdown files")
    parser.add_argument("--input", "-i", default="moby_news/",
                        help="Input directory with Moby markdown files")
    parser.add_argument("--output", "-o", default="data/sentiment/moby_analysis.csv",
                        help="Output CSV path")
    args = parser.parse_args()

    input_dir = Path(args.input)
    output_path = Path(args.output)

    print(f"Parsing Moby analysis files from {input_dir}")
    df = parse_all_files(input_dir)

    if len(df) == 0:
        print("No stocks found.")
        return 1

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Merge with existing if present
    if output_path.exists():
        existing = pd.read_csv(output_path)
        df = pd.concat([existing, df], ignore_index=True)
        df = df.drop_duplicates(subset=["date", "ticker"], keep="last")

    df.to_csv(output_path, index=False)
    print(f"\nSaved {len(df)} stock analyses to {output_path}")

    # Summary
    print(f"\nSummary:")
    print(f"  Stocks: {len(df)}")
    print(f"  Dates: {df['date'].nunique()}")
    if "upside_pct" in df.columns:
        print(f"  Avg upside: {df['upside_pct'].mean():.0f}%")
        print(f"  Ratings: {df['rating'].value_counts().to_dict()}")

    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
