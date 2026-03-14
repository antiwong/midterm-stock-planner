#!/usr/bin/env python3
"""
Parse Moby.co Email Alerts
============================
Connects to Gmail (antiwongmoby@gmail.com) via IMAP, reads Moby newsletter
emails, and extracts stock picks, ratings, and sentiment.

Setup:
    1. Enable IMAP in Gmail: Settings > See all settings > Forwarding and POP/IMAP > Enable IMAP
    2. Create App Password: Google Account > Security > 2-Step Verification > App passwords
       (Or if no 2FA: Allow less secure apps)
    3. Set env vars:
       export MOBY_EMAIL=antiwongmoby@gmail.com
       export MOBY_APP_PASSWORD=your_app_password

Usage:
    python scripts/parse_moby_emails.py
    python scripts/parse_moby_emails.py --days 30
    python scripts/parse_moby_emails.py --output data/sentiment/moby_picks.csv
"""

import os
import sys
import re
import imaplib
import email
from email.header import decode_header
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class MobyEmailParser:
    """Parses Moby.co newsletter emails for stock picks and sentiment."""

    IMAP_SERVER = "imap.gmail.com"
    IMAP_PORT = 993

    # Patterns to extract stock tickers and ratings from Moby emails
    TICKER_PATTERN = re.compile(
        r'\b([A-Z]{1,5})\b'
    )
    # Common Moby rating keywords
    BULLISH_KEYWORDS = [
        "buy", "bullish", "strong buy", "overweight", "outperform",
        "upgrade", "top pick", "conviction", "accumulate", "positive"
    ]
    BEARISH_KEYWORDS = [
        "sell", "bearish", "underweight", "underperform",
        "downgrade", "avoid", "reduce", "negative", "caution"
    ]

    # Known stock tickers to avoid false positives from common words
    COMMON_WORDS = {
        "THE", "AND", "FOR", "ARE", "BUT", "NOT", "YOU", "ALL", "CAN",
        "HER", "WAS", "ONE", "OUR", "OUT", "DAY", "HAD", "HAS", "HIS",
        "HOW", "ITS", "MAY", "NEW", "NOW", "OLD", "SEE", "WAY", "WHO",
        "DID", "GET", "LET", "SAY", "SHE", "TOO", "USE", "CEO", "IPO",
        "GDP", "ETF", "SEC", "FED", "USA", "USD", "FAQ", "CEO", "CFO",
        "COO", "CTO", "AI", "US", "UK", "EU", "PM", "AM", "VS", "RE",
        "TOP", "BIG", "LOW", "HIGH", "UP", "DOWN", "JUST", "LIKE",
        "MORE", "MOST", "MUCH", "NEXT", "OVER", "SAME", "THAN", "THAT",
        "THIS", "VERY", "WHAT", "WHEN", "WILL", "WITH", "FROM", "HAVE",
        "HERE", "INTO", "JUST", "MAKE", "MANY", "SOME", "TAKE", "THEM",
        "THEN", "THEY", "TIME", "BEEN", "COME", "EACH", "EVEN", "FIND",
        "FIRST", "GIVE", "GOOD", "KEEP", "KNOW", "LAST", "LONG", "LOOK",
        "PART", "YEAR", "ALSO", "BACK", "CALL", "WANT", "WELL", "WORK",
        "FREE", "BEST", "READ", "WEEK", "WANT", "NEWS", "TECH", "GAIN",
        "LOSS", "RISE", "FELL", "DROP", "JUMP", "MOVE", "PUSH", "PULL",
        "OPEN", "PLAN", "DEAL", "RATE", "FUND", "CASH", "DEBT", "BOND",
        "NOTE", "SELL", "HOLD",
    }

    def __init__(self, email_addr: Optional[str] = None, password: Optional[str] = None):
        self.email_addr = email_addr or os.environ.get("MOBY_EMAIL", "antiwongmoby@gmail.com")
        self.password = password or os.environ.get("MOBY_APP_PASSWORD", "")

        if not self.password:
            raise ValueError(
                "MOBY_APP_PASSWORD not set.\n"
                "Steps:\n"
                "1. Go to Gmail Settings > Enable IMAP\n"
                "2. Go to Google Account > Security > App passwords\n"
                "3. Generate an app password for 'Mail'\n"
                "4. export MOBY_APP_PASSWORD=your_16_char_password"
            )

    def connect(self) -> imaplib.IMAP4_SSL:
        """Connect to Gmail IMAP."""
        mail = imaplib.IMAP4_SSL(self.IMAP_SERVER, self.IMAP_PORT)
        mail.login(self.email_addr, self.password)
        return mail

    def fetch_emails(self, days: int = 90, folder: str = "INBOX") -> List[Dict]:
        """Fetch Moby emails from the last N days."""
        mail = self.connect()
        mail.select(folder)

        since_date = (datetime.now() - timedelta(days=days)).strftime("%d-%b-%Y")
        # Search for emails from Moby
        search_queries = [
            f'(FROM "moby" SINCE {since_date})',
            f'(FROM "investwithmoby" SINCE {since_date})',
            f'(SUBJECT "moby" SINCE {since_date})',
        ]

        all_ids = set()
        for query in search_queries:
            try:
                status, data = mail.search(None, query)
                if status == "OK" and data[0]:
                    all_ids.update(data[0].split())
            except Exception:
                continue

        print(f"  Found {len(all_ids)} Moby emails in last {days} days")

        emails = []
        for msg_id in sorted(all_ids):
            try:
                status, msg_data = mail.fetch(msg_id, "(RFC822)")
                if status != "OK":
                    continue

                msg = email.message_from_bytes(msg_data[0][1])

                # Decode subject
                subject = ""
                raw_subject = msg.get("Subject", "")
                if raw_subject:
                    decoded = decode_header(raw_subject)
                    subject = "".join(
                        part.decode(enc or "utf-8") if isinstance(part, bytes) else part
                        for part, enc in decoded
                    )

                # Get date
                date_str = msg.get("Date", "")
                try:
                    date_parsed = email.utils.parsedate_to_datetime(date_str)
                except Exception:
                    date_parsed = datetime.now()

                # Extract body
                body = self._get_body(msg)

                emails.append({
                    "date": date_parsed.strftime("%Y-%m-%d %H:%M:%S"),
                    "subject": subject,
                    "body": body,
                    "from": msg.get("From", ""),
                })
            except Exception as e:
                print(f"    Error parsing email {msg_id}: {e}")

        mail.logout()
        return emails

    def _get_body(self, msg) -> str:
        """Extract text body from email message."""
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain":
                    try:
                        payload = part.get_payload(decode=True)
                        if payload:
                            body = payload.decode("utf-8", errors="replace")
                            break
                    except Exception:
                        continue
                elif content_type == "text/html" and not body:
                    try:
                        payload = part.get_payload(decode=True)
                        if payload:
                            # Strip HTML tags
                            html = payload.decode("utf-8", errors="replace")
                            body = re.sub(r"<[^>]+>", " ", html)
                            body = re.sub(r"\s+", " ", body).strip()
                    except Exception:
                        continue
        else:
            try:
                payload = msg.get_payload(decode=True)
                if payload:
                    body = payload.decode("utf-8", errors="replace")
            except Exception:
                pass
        return body[:5000]  # Limit body length

    def extract_picks(self, emails: List[Dict]) -> pd.DataFrame:
        """Extract stock picks and sentiment from email content."""
        picks = []

        for em in emails:
            text = f"{em['subject']} {em['body']}".upper()
            text_lower = text.lower()

            # Find potential tickers (1-5 uppercase letters)
            potential_tickers = set(self.TICKER_PATTERN.findall(text))
            # Filter out common words
            tickers = [t for t in potential_tickers if t not in self.COMMON_WORDS and len(t) >= 2]

            # Compute overall sentiment of the email
            bullish_count = sum(1 for kw in self.BULLISH_KEYWORDS if kw in text_lower)
            bearish_count = sum(1 for kw in self.BEARISH_KEYWORDS if kw in text_lower)

            if bullish_count + bearish_count > 0:
                sentiment_score = (bullish_count - bearish_count) / (bullish_count + bearish_count)
            else:
                sentiment_score = 0.0

            sentiment_label = "neutral"
            if sentiment_score > 0.3:
                sentiment_label = "bullish"
            elif sentiment_score < -0.3:
                sentiment_label = "bearish"

            for ticker in tickers:
                picks.append({
                    "date": em["date"],
                    "ticker": ticker,
                    "source": "moby",
                    "subject": em["subject"][:200],
                    "sentiment_score": round(sentiment_score, 3),
                    "sentiment_label": sentiment_label,
                    "bullish_keywords": bullish_count,
                    "bearish_keywords": bearish_count,
                })

        if picks:
            df = pd.DataFrame(picks)
            df["date"] = pd.to_datetime(df["date"])
            return df.sort_values(["date", "ticker"])
        return pd.DataFrame()

    def download(self, days: int = 90, output: str = "data/sentiment/moby_picks.csv") -> pd.DataFrame:
        """Full pipeline: fetch emails → extract picks → save."""
        print(f"Fetching Moby emails ({self.email_addr}, last {days} days)...")

        emails = self.fetch_emails(days=days)
        if not emails:
            print("  No Moby emails found")
            return pd.DataFrame()

        print(f"  Parsing {len(emails)} emails for stock picks...")
        picks_df = self.extract_picks(emails)

        if not picks_df.empty:
            output_path = Path(output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            picks_df.to_csv(output_path, index=False)
            print(f"  Saved {len(picks_df)} picks to {output_path}")
            print(f"  Tickers found: {sorted(picks_df['ticker'].unique())}")
            print(f"  Sentiment: {picks_df['sentiment_label'].value_counts().to_dict()}")
        else:
            print("  No stock picks extracted")

        return picks_df


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Parse Moby.co email alerts for stock picks")
    parser.add_argument("--days", "-d", type=int, default=90, help="Days of email history")
    parser.add_argument("--output", "-o", type=str, default="data/sentiment/moby_picks.csv")
    args = parser.parse_args()

    try:
        parser_obj = MobyEmailParser()
        parser_obj.download(days=args.days, output=args.output)
    except ValueError as e:
        print(f"\n{e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
