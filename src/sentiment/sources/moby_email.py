"""Moby email newsletter parser.

Connects to antiwongmoby@gmail.com via IMAP to fetch:
1. Moby (hello@moby.co) — daily market commentary with sentiment
2. FSMOne — analyst ratings (buy/sell/hold with target prices)

Note: Moby portfolio tier data (platinum/gold/silver) comes from the
Moby web app, not email. Emails contain market commentary only.

Usage:
    from src.sentiment.sources.moby_email import MobyEmailParser
    parser = MobyEmailParser()
    articles = parser.fetch_all()
"""

import email
import imaplib
import os
import re
from datetime import datetime, timedelta
from email.header import decode_header
from typing import Dict, List, Optional

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class MobyEmailParser:
    """Parse Moby and broker newsletter emails for sentiment signals."""

    IMAP_SERVER = "imap.gmail.com"

    def __init__(self, email_addr: Optional[str] = None, app_password: Optional[str] = None):
        self.email_addr = email_addr or os.environ.get("MOBY_EMAIL", "")
        self.app_password = app_password or os.environ.get("MOBY_APP_PASSWORD", "")
        if not self.email_addr or not self.app_password:
            raise ValueError(
                "MOBY_EMAIL and MOBY_APP_PASSWORD must be set in .env or environment."
            )

    def _connect(self) -> imaplib.IMAP4_SSL:
        mail = imaplib.IMAP4_SSL(self.IMAP_SERVER)
        mail.login(self.email_addr, self.app_password)
        return mail

    def _decode_subject(self, msg) -> str:
        subject = decode_header(msg["Subject"])[0][0]
        if isinstance(subject, bytes):
            subject = subject.decode("utf-8", errors="replace")
        return str(subject)

    def _get_text(self, msg) -> str:
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                ct = part.get_content_type()
                if ct == "text/html":
                    body = part.get_payload(decode=True).decode("utf-8", errors="replace")
                    break
                elif ct == "text/plain" and not body:
                    body = part.get_payload(decode=True).decode("utf-8", errors="replace")
        else:
            body = msg.get_payload(decode=True).decode("utf-8", errors="replace")

        if BeautifulSoup and ("<html" in body.lower() or "<div" in body.lower()):
            soup = BeautifulSoup(body, "html.parser")
            return soup.get_text(separator="\n", strip=True)
        return body

    def _extract_market_data(self, text: str) -> Dict[str, float]:
        """Extract market index changes from Moby email format."""
        data = {}
        patterns = {
            "dow": r"Dow\s*[▲▼]\s*([\d.]+)%",
            "sp500": r"S&P\s*[▲▼]\s*([\d.]+)%",
            "nasdaq": r"Nasdaq\s*[▲▼]\s*([\d.]+)%",
            "bitcoin": r"Bitcoin\s*[▲▼]\s*([\d.]+)%",
        }
        for key, pattern in patterns.items():
            match = re.search(pattern, text)
            if match:
                val = float(match.group(1))
                if "▼" in text[max(0, match.start() - 5):match.start()]:
                    val = -val
                data[key] = val
        return data

    def _extract_ticker_mentions(self, text: str, known_tickers: set) -> List[str]:
        """Extract known ticker mentions from text."""
        words = re.findall(r"\b[A-Z]{2,5}\b", text)
        return list(set(w for w in words if w in known_tickers))

    def _extract_analyst_ratings(self, text: str) -> List[Dict]:
        """Extract analyst buy/sell ratings from FSMOne emails."""
        ratings = []
        # Pattern variations:
        # "BUY rating for AMD with a target price of USD 245"
        # "assign a 'BUY' rating for AMD with a target price of USD 245"
        # "SELL rating for INTC target price USD 30"
        for rating_type in ["BUY", "SELL", "HOLD"]:
            pattern = (
                rf"['\"\u2018\u2019\u201c\u201d]?{rating_type}['\"\u2018\u2019\u201c\u201d]?"
                rf"\s+(?:rating\s+)?(?:for\s+)?([A-Z]{{2,5}})"
                rf".*?target\s+price\s+.*?USD\s+([\d.]+)"
            )
            for match in re.finditer(pattern, text, re.IGNORECASE):
                ratings.append({
                    "ticker": match.group(1),
                    "rating": rating_type,
                    "target_price": float(match.group(2)),
                })

        return ratings

    def fetch_moby_emails(self, days_back: int = 30) -> List[Dict]:
        """Fetch and parse Moby newsletter emails."""
        mail = self._connect()
        mail.select('"[Gmail]/All Mail"')

        since_date = (datetime.now() - timedelta(days=days_back)).strftime("%d-%b-%Y")
        status, messages = mail.search(None, "FROM", '"moby.co"', "SINCE", since_date)
        ids = messages[0].split() if messages[0] else []

        articles = []
        for msg_id in ids:
            status, data = mail.fetch(msg_id, "(RFC822)")
            msg = email.message_from_bytes(data[0][1])
            subject = self._decode_subject(msg)
            date = msg["Date"]
            text = self._get_text(msg)

            market_data = self._extract_market_data(text)

            articles.append({
                "date": date,
                "source": "moby",
                "subject": subject,
                "text": text[:2000],
                "market_data": market_data,
                "type": "market_commentary",
            })

        mail.logout()
        return articles

    def fetch_broker_emails(self, days_back: int = 30) -> List[Dict]:
        """Fetch and parse broker newsletter emails (FSMOne, Tiger, etc.)."""
        mail = self._connect()
        mail.select('"[Gmail]/All Mail"')

        since_date = (datetime.now() - timedelta(days=days_back)).strftime("%d-%b-%Y")

        # Search for broker emails
        all_broker = []
        for sender in ["fundsupermart", "tigerbrokers"]:
            status, messages = mail.search(None, "FROM", f'"{sender}"', "SINCE", since_date)
            ids = messages[0].split() if messages[0] else []

            for msg_id in ids:
                status, data = mail.fetch(msg_id, "(RFC822)")
                msg = email.message_from_bytes(data[0][1])
                subject = self._decode_subject(msg)
                date = msg["Date"]
                text = self._get_text(msg)

                ratings = self._extract_analyst_ratings(text)

                all_broker.append({
                    "date": date,
                    "source": "fsm_one" if "fundsupermart" in sender else sender,
                    "subject": subject,
                    "text": text[:2000],
                    "analyst_ratings": ratings,
                    "type": "analyst_report",
                })

        mail.logout()
        return all_broker

    def fetch_all(self, days_back: int = 30) -> Dict[str, List[Dict]]:
        """Fetch all email sources."""
        return {
            "moby": self.fetch_moby_emails(days_back),
            "broker": self.fetch_broker_emails(days_back),
        }
