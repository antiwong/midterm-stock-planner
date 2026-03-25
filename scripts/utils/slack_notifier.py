"""Slack notification utility for SentimentPulse and midterm-stock-planner.

Sends structured messages to Slack with:
- Job status (started / completed / failed / warning)
- Rich context (what ran, what failed, key metrics)
- Color-coded severity (good=green, warning=yellow, danger=red)

Environment variables:
    SLACK_WEBHOOK_URL or slack_webhook — primary webhook
    SLACK_WEBHOOK_SENTIMENT — sentiment channel webhook (optional)

Usage:
    notifier = SlackNotifier(job_name="sg_blue_chips_daily")
    ts = notifier.started("Running daily signals for 19 tickers")
    # ... do work ...
    notifier.completed(ts, metrics={"tickers": 19, "trades": 3})
    # or on failure:
    notifier.failed(ts, error="DuckDB timeout", context={...})
"""

import os
import json
import time
import traceback
import requests
from datetime import datetime
from typing import Optional, Dict, Any


class SlackNotifier:

    COLORS = {
        'good':    '#36a64f',   # Green — success
        'warning': '#ff9800',   # Orange — partial / degraded
        'danger':  '#e53935',   # Red — failure
        'info':    '#2196f3',   # Blue — informational
    }

    def __init__(self, job_name: str, webhook_url: Optional[str] = None):
        self.job_name = job_name
        self.webhook_url = (
            webhook_url
            or os.environ.get('SLACK_WEBHOOK_URL')
            or os.environ.get('slack_webhook', '')
        )
        self.hostname = os.uname().nodename
        self.enabled = bool(self.webhook_url)
        self._start_time = time.time()

    # ── Public API ───────────────────────────────────────────────────────────

    def started(self, message: str = "") -> Optional[str]:
        """Send job-started notification. Returns timestamp for thread replies."""
        self._start_time = time.time()
        return self._send(
            color='info',
            title=f"▶ {self.job_name} started",
            text=message or f"Job started on {self.hostname}",
            fields={'Time': self._now(), 'Host': self.hostname},
        )

    def completed(self, thread_ts: Optional[str] = None,
                  metrics: Optional[Dict] = None,
                  warnings: Optional[list] = None) -> None:
        """Send job-completed notification."""
        fields = {'Time': self._now(), 'Duration': self._elapsed()}
        if metrics:
            fields.update({k: str(v) for k, v in metrics.items()})

        color = 'warning' if warnings else 'good'
        warning_text = '\n'.join(f"⚠️ {w}" for w in warnings) if warnings else ""

        self._send(
            color=color,
            title=f"✅ {self.job_name} completed" + (" (with warnings)" if warnings else ""),
            text=warning_text,
            fields=fields,
            thread_ts=thread_ts,
        )

    def failed(self, thread_ts: Optional[str] = None,
               error: str = "",
               context: Optional[Dict] = None,
               exc: Optional[Exception] = None) -> None:
        """Send job-failed notification with full error context."""
        fields = {'Time': self._now(), 'Host': self.hostname, 'Duration': self._elapsed()}
        if context:
            fields.update({k: str(v) for k, v in context.items()})

        tb = ""
        if exc:
            tb = traceback.format_exception(type(exc), exc, exc.__traceback__)
            tb = ''.join(tb)

        text_parts = []
        if error:
            text_parts.append(f"*Error*: {error}")
        if tb:
            text_parts.append(f"```{tb[-800:]}```")

        self._send(
            color='danger',
            title=f"❌ {self.job_name} FAILED",
            text='\n'.join(text_parts),
            fields=fields,
            thread_ts=thread_ts,
        )

    def warning(self, message: str,
                thread_ts: Optional[str] = None,
                context: Optional[Dict] = None) -> None:
        """Send a warning without failing the job."""
        fields = {'Time': self._now()}
        if context:
            fields.update({k: str(v) for k, v in context.items()})

        self._send(
            color='warning',
            title=f"⚠️ {self.job_name} — warning",
            text=message,
            fields=fields,
            thread_ts=thread_ts,
        )

    def no_data_alert(self, ticker: str, sources_tried: list,
                      thread_ts: Optional[str] = None) -> None:
        """Alert for 'no articles found' — the most common silent failure."""
        self._send(
            color='warning',
            title=f"📭 No data — {ticker}",
            text=(
                f"All {len(sources_tried)} sources returned 0 articles for {ticker}.\n"
                f"Sources tried: {', '.join(sources_tried)}"
            ),
            fields={'Ticker': ticker, 'Sources tried': str(len(sources_tried))},
            thread_ts=thread_ts,
        )

    # ── Private ──────────────────────────────────────────────────────────────

    def _send(self, color: str, title: str, text: str = "",
              fields: Optional[Dict] = None,
              thread_ts: Optional[str] = None) -> Optional[str]:
        if not self.enabled:
            return None

        attachment = {
            "color": self.COLORS.get(color, '#888888'),
            "title": title,
            "text": text,
            "footer": f"{self.hostname} | {self.job_name}",
            "ts": int(time.time()),
        }

        if fields:
            attachment["fields"] = [
                {"title": k, "value": v, "short": len(str(v)) < 25}
                for k, v in fields.items()
            ]

        payload = {"attachments": [attachment]}
        if thread_ts:
            payload["thread_ts"] = thread_ts

        try:
            resp = requests.post(self.webhook_url, json=payload, timeout=10)
            if resp.status_code == 200:
                try:
                    return resp.json().get('ts')
                except Exception:
                    return str(time.time())
        except Exception as e:
            import logging
            logging.warning(f"Slack notification failed: {e}")
        return None

    def _now(self) -> str:
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    def _elapsed(self) -> str:
        elapsed = time.time() - self._start_time
        m, s = divmod(int(elapsed), 60)
        return f"{m}m {s}s"


# ── Decorator for automatic job wrapping ─────────────────────────────────────

def slack_job(job_name: str, notify_start: bool = True):
    """Decorator that wraps a function with Slack notifications.

    Usage:
        @slack_job("sg_blue_chips_daily")
        def run():
            return {"tickers": 19, "trades": 3}  # dict becomes metrics
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            notifier = SlackNotifier(job_name=job_name)
            thread_ts = notifier.started() if notify_start else None
            try:
                result = func(*args, **kwargs)
                metrics = result if isinstance(result, dict) else {}
                notifier.completed(thread_ts=thread_ts, metrics=metrics)
                return result
            except Exception as e:
                notifier.failed(thread_ts=thread_ts, error=str(e), exc=e)
                raise
        return wrapper
    return decorator
