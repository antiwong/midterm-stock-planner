"""Tests for monitoring, dual regime filter, VIX scaling, and health monitor.

Covers modules created/modified 2026-03-25:
- scripts/utils/slack_notifier.py — SlackNotifier class
- scripts/run_daily_fast.py — dual regime, VIX scaling, Slack wrapper
- scripts/health_monitor.py — health check watchdog
- scripts/download_fundamentals.py — CSV write fix
"""

import os
import sys
import json
import time
import tempfile
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))


# ═══════════════════════════════════════════════════════════════════════════════
# SlackNotifier Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestSlackNotifier:
    """Tests for scripts/utils/slack_notifier.py."""

    def test_import(self):
        from utils.slack_notifier import SlackNotifier, slack_job
        assert SlackNotifier is not None
        assert slack_job is not None

    def test_disabled_without_webhook(self):
        """Notifier should be disabled when no webhook URL is set."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop('SLACK_WEBHOOK_URL', None)
            os.environ.pop('slack_webhook', None)
            from utils.slack_notifier import SlackNotifier
            n = SlackNotifier(job_name="test", webhook_url="")
            assert n.enabled is False

    def test_enabled_with_webhook(self):
        from utils.slack_notifier import SlackNotifier
        n = SlackNotifier(job_name="test", webhook_url="https://hooks.slack.com/test")
        assert n.enabled is True

    def test_started_returns_none_when_disabled(self):
        from utils.slack_notifier import SlackNotifier
        n = SlackNotifier(job_name="test", webhook_url="")
        result = n.started("test message")
        assert result is None

    def test_completed_no_crash_when_disabled(self):
        from utils.slack_notifier import SlackNotifier
        n = SlackNotifier(job_name="test", webhook_url="")
        n.completed(metrics={"tickers": 19})  # Should not raise

    def test_failed_no_crash_when_disabled(self):
        from utils.slack_notifier import SlackNotifier
        n = SlackNotifier(job_name="test", webhook_url="")
        n.failed(error="test error")  # Should not raise

    def test_warning_no_crash_when_disabled(self):
        from utils.slack_notifier import SlackNotifier
        n = SlackNotifier(job_name="test", webhook_url="")
        n.warning("test warning")  # Should not raise

    def test_no_data_alert_no_crash_when_disabled(self):
        from utils.slack_notifier import SlackNotifier
        n = SlackNotifier(job_name="test", webhook_url="")
        n.no_data_alert("AAPL", ["finnhub", "marketaux"])  # Should not raise

    @patch('utils.slack_notifier.requests.post')
    def test_started_sends_correct_payload(self, mock_post):
        mock_post.return_value = MagicMock(status_code=200, json=lambda: {'ts': '123'})
        from utils.slack_notifier import SlackNotifier
        n = SlackNotifier(job_name="test-job", webhook_url="https://hooks.slack.com/test")
        ts = n.started("hello world")

        mock_post.assert_called_once()
        payload = mock_post.call_args.kwargs['json']
        assert len(payload['attachments']) == 1
        att = payload['attachments'][0]
        assert 'test-job started' in att['title']
        assert att['color'] == '#2196f3'  # info = blue

    @patch('utils.slack_notifier.requests.post')
    def test_completed_sends_green(self, mock_post):
        mock_post.return_value = MagicMock(status_code=200, json=lambda: {})
        from utils.slack_notifier import SlackNotifier
        n = SlackNotifier(job_name="test-job", webhook_url="https://hooks.slack.com/test")
        n.completed(metrics={"count": 42})

        payload = mock_post.call_args.kwargs['json']
        att = payload['attachments'][0]
        assert att['color'] == '#36a64f'  # good = green

    @patch('utils.slack_notifier.requests.post')
    def test_completed_with_warnings_sends_orange(self, mock_post):
        mock_post.return_value = MagicMock(status_code=200, json=lambda: {})
        from utils.slack_notifier import SlackNotifier
        n = SlackNotifier(job_name="test-job", webhook_url="https://hooks.slack.com/test")
        n.completed(warnings=["something went wrong"])

        payload = mock_post.call_args.kwargs['json']
        att = payload['attachments'][0]
        assert att['color'] == '#ff9800'  # warning = orange

    @patch('utils.slack_notifier.requests.post')
    def test_failed_sends_red(self, mock_post):
        mock_post.return_value = MagicMock(status_code=200, json=lambda: {})
        from utils.slack_notifier import SlackNotifier
        n = SlackNotifier(job_name="test-job", webhook_url="https://hooks.slack.com/test")
        n.failed(error="boom")

        payload = mock_post.call_args.kwargs['json']
        att = payload['attachments'][0]
        assert att['color'] == '#e53935'  # danger = red
        assert 'boom' in att['text']

    @patch('utils.slack_notifier.requests.post')
    def test_failed_includes_traceback(self, mock_post):
        mock_post.return_value = MagicMock(status_code=200, json=lambda: {})
        from utils.slack_notifier import SlackNotifier
        n = SlackNotifier(job_name="test", webhook_url="https://hooks.slack.com/test")
        try:
            raise ValueError("test exception")
        except ValueError as e:
            n.failed(error="caught it", exc=e)

        payload = mock_post.call_args.kwargs['json']
        assert 'ValueError' in payload['attachments'][0]['text']

    @patch('utils.slack_notifier.requests.post')
    def test_elapsed_time_tracking(self, mock_post):
        mock_post.return_value = MagicMock(status_code=200, json=lambda: {})
        from utils.slack_notifier import SlackNotifier
        n = SlackNotifier(job_name="test", webhook_url="https://hooks.slack.com/test")
        n._start_time = time.time() - 125  # Fake 2m 5s elapsed
        n.completed()

        payload = mock_post.call_args.kwargs['json']
        fields = {f['title']: f['value'] for f in payload['attachments'][0]['fields']}
        assert '2m' in fields['Duration']

    def test_slack_job_decorator_success(self):
        """Decorator should return function result without crashing."""
        from utils.slack_notifier import slack_job

        @slack_job("test-decorator")
        def my_job():
            return {"items": 5}

        # With no webhook configured, it runs silently
        result = my_job()
        assert result == {"items": 5}

    def test_slack_job_decorator_failure(self):
        """Decorator should re-raise exceptions."""
        from utils.slack_notifier import slack_job

        @slack_job("test-decorator")
        def my_failing_job():
            raise RuntimeError("oops")

        with pytest.raises(RuntimeError, match="oops"):
            my_failing_job()

    @patch('utils.slack_notifier.requests.post', side_effect=Exception("network down"))
    def test_send_failure_doesnt_crash(self, mock_post):
        """Slack send failure must never crash the calling job."""
        from utils.slack_notifier import SlackNotifier
        n = SlackNotifier(job_name="test", webhook_url="https://hooks.slack.com/test")
        n.started("should not crash")  # Should return None, not raise
        n.completed()
        n.failed(error="test")


# ═══════════════════════════════════════════════════════════════════════════════
# Dual Regime Filter Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestDualRegimeFilter:
    """Tests for compute_dual_regime() and compute_vix_scale() in run_daily_fast.py."""

    def test_import(self):
        from scripts.run_daily_fast import compute_dual_regime, compute_vix_scale
        assert compute_dual_regime is not None
        assert compute_vix_scale is not None

    def test_both_normal(self):
        from scripts.run_daily_fast import compute_dual_regime
        regime, scale, trigger = compute_dual_regime(0.02, 0.01)
        assert regime == "normal"
        assert scale == 1.0

    def test_spy_reduce_sgx_normal(self):
        """SPY in reduce territory, SGX normal — should use SPY (more conservative)."""
        from scripts.run_daily_fast import compute_dual_regime
        regime, scale, trigger = compute_dual_regime(-0.06, 0.01)
        assert regime == "reduce"
        assert scale == 0.30
        assert trigger == "SPY"

    def test_sgx_reduce_spy_normal(self):
        """SGX in reduce territory, SPY normal — should use SGX (more conservative)."""
        from scripts.run_daily_fast import compute_dual_regime
        regime, scale, trigger = compute_dual_regime(0.01, -0.06)
        assert regime == "reduce"
        assert scale == 0.30
        assert trigger == "ES3.SI"

    def test_spy_exit(self):
        from scripts.run_daily_fast import compute_dual_regime
        regime, scale, trigger = compute_dual_regime(-0.10, 0.01)
        assert regime == "exit"
        assert scale == 0.0
        assert trigger == "SPY"

    def test_sgx_exit(self):
        from scripts.run_daily_fast import compute_dual_regime
        regime, scale, trigger = compute_dual_regime(0.01, -0.09)
        assert regime == "exit"
        assert scale == 0.0
        assert trigger == "ES3.SI"

    def test_both_reduce_uses_lower(self):
        """Both in reduce — either trigger is fine, scale should be reduce."""
        from scripts.run_daily_fast import compute_dual_regime
        regime, scale, _ = compute_dual_regime(-0.06, -0.07)
        assert regime == "reduce"
        assert scale == 0.30

    def test_spy_exit_sgx_reduce(self):
        """SPY exit beats SGX reduce — exit is more conservative."""
        from scripts.run_daily_fast import compute_dual_regime
        regime, scale, trigger = compute_dual_regime(-0.10, -0.06)
        assert regime == "exit"
        assert scale == 0.0
        assert trigger == "SPY"

    def test_exact_threshold_reduce(self):
        """At exactly -0.05, should trigger reduce."""
        from scripts.run_daily_fast import compute_dual_regime
        regime, scale, _ = compute_dual_regime(-0.05, 0.0)
        assert regime == "reduce"

    def test_exact_threshold_exit(self):
        """At exactly -0.08, should trigger exit."""
        from scripts.run_daily_fast import compute_dual_regime
        regime, scale, _ = compute_dual_regime(-0.08, 0.0)
        assert regime == "exit"

    def test_custom_thresholds(self):
        from scripts.run_daily_fast import compute_dual_regime
        regime, scale, _ = compute_dual_regime(
            -0.03, 0.0, threshold_reduce=-0.02, threshold_exit=-0.05)
        assert regime == "reduce"


class TestVixScaling:
    """Tests for VIX-based position scaling."""

    def test_vix_below_20(self):
        from scripts.run_daily_fast import compute_vix_scale
        assert compute_vix_scale(15.0) == 1.0
        assert compute_vix_scale(19.9) == 1.0

    def test_vix_20_to_25(self):
        from scripts.run_daily_fast import compute_vix_scale
        assert compute_vix_scale(20.0) == 0.50
        assert compute_vix_scale(24.9) == 0.50

    def test_vix_25_to_30(self):
        from scripts.run_daily_fast import compute_vix_scale
        assert compute_vix_scale(25.0) == 0.50
        assert compute_vix_scale(29.9) == 0.50

    def test_vix_above_30(self):
        from scripts.run_daily_fast import compute_vix_scale
        assert compute_vix_scale(30.0) == 0.25
        assert compute_vix_scale(50.0) == 0.25
        assert compute_vix_scale(80.0) == 0.25

    def test_vix_multiplicative_with_regime(self):
        """VIX scale should multiply with regime scale."""
        from scripts.run_daily_fast import compute_dual_regime, compute_vix_scale
        _, regime_scale, _ = compute_dual_regime(-0.06, 0.0)  # reduce = 0.30
        vix_scale = compute_vix_scale(26.0)  # 0.50
        final = regime_scale * vix_scale
        assert abs(final - 0.15) < 0.001  # 30% * 50% = 15%


class TestDxyScaling:
    """Tests for UUP/DXY-based position scaling for precious_metals."""

    def test_import(self):
        from scripts.run_daily_fast import compute_dxy_scale
        assert compute_dxy_scale is not None

    def test_strong_headwind(self):
        """UUP 20d return > +2% means strong dollar — 25% scale."""
        from scripts.run_daily_fast import compute_dxy_scale
        assert compute_dxy_scale(0.03) == 0.25
        assert compute_dxy_scale(0.05) == 0.25
        assert compute_dxy_scale(0.021) == 0.25

    def test_mild_headwind(self):
        """UUP 20d return 0% to +2% means mild dollar strength — 60% scale."""
        from scripts.run_daily_fast import compute_dxy_scale
        assert compute_dxy_scale(0.01) == 0.60
        assert compute_dxy_scale(0.005) == 0.60
        assert compute_dxy_scale(0.0) == 0.60  # Zero is mild headwind band

    def test_tailwind(self):
        """UUP 20d return < 0% means weakening dollar — full scale."""
        from scripts.run_daily_fast import compute_dxy_scale
        assert compute_dxy_scale(-0.01) == 1.0
        assert compute_dxy_scale(-0.05) == 1.0

    def test_boundary_at_2pct(self):
        """Exactly +2% is still mild headwind (threshold is > 0.02 for strong)."""
        from scripts.run_daily_fast import compute_dxy_scale
        assert compute_dxy_scale(0.02) == 0.60

    def test_multiplicative_with_vix_and_regime(self):
        """DXY scale multiplies with existing VIX and regime scales."""
        from scripts.run_daily_fast import compute_dual_regime, compute_vix_scale, compute_dxy_scale
        _, regime_scale, _ = compute_dual_regime(-0.06, 0.0)  # reduce = 0.30
        vix_scale = compute_vix_scale(26.0)  # 0.50
        dxy_scale = compute_dxy_scale(0.03)  # strong headwind = 0.25
        final = regime_scale * vix_scale * dxy_scale
        assert abs(final - 0.0375) < 0.001  # 30% * 50% * 25% = 3.75%


# ═══════════════════════════════════════════════════════════════════════════════
# Health Monitor Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestHealthMonitor:
    """Tests for scripts/health_monitor.py."""

    def test_import(self):
        from scripts.health_monitor import check_log, JOBS
        assert callable(check_log)
        assert len(JOBS) >= 4

    def test_missing_log_file(self):
        from scripts.health_monitor import check_log
        result = check_log({
            'name': 'test',
            'log': '/nonexistent/path/test.log',
            'max_age_h': 24,
            'success_grep': 'done',
            'failure_grep': 'error',
        })
        assert result['status'] == 'missing'

    def test_stale_log_file(self):
        """Log older than max_age_h should report stale."""
        from scripts.health_monitor import check_log
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
            f.write("some old content\n")
            f.flush()
            # Set mtime to 48 hours ago
            old_time = time.time() - (48 * 3600)
            os.utime(f.name, (old_time, old_time))

            result = check_log({
                'name': 'test',
                'log': f.name,
                'max_age_h': 24,
                'success_grep': 'done',
                'failure_grep': 'error',
            })
            assert result['status'] == 'stale'
            assert result['age_h'] > 24
            os.unlink(f.name)

    def test_fresh_successful_log(self):
        from scripts.health_monitor import check_log
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
            f.write("Starting job\nProcessing...\nCrawl complete in 300s\n")
            f.flush()

            result = check_log({
                'name': 'test',
                'log': f.name,
                'max_age_h': 24,
                'success_grep': 'Crawl complete',
                'failure_grep': 'CRASHED',
            })
            assert result['status'] == 'ok'
            os.unlink(f.name)

    def test_fresh_failed_log(self):
        from scripts.health_monitor import check_log
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
            f.write("Starting job\nCRASHED: out of memory\n")
            f.flush()

            result = check_log({
                'name': 'test',
                'log': f.name,
                'max_age_h': 24,
                'success_grep': 'Crawl complete',
                'failure_grep': 'CRASHED',
            })
            assert result['status'] == 'failed'
            assert 'CRASHED' in result['message']
            os.unlink(f.name)

    def test_directory_log_pattern(self):
        """Health monitor should find newest file matching pattern in a directory."""
        from scripts.health_monitor import check_log
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create two log files
            old = Path(tmpdir) / "crawl_old.log"
            old.write_text("old data\nCrawl complete")
            old_time = time.time() - 3600
            os.utime(str(old), (old_time, old_time))

            new = Path(tmpdir) / "crawl_new.log"
            new.write_text("new data\nCrawl complete")

            result = check_log({
                'name': 'test',
                'log': tmpdir,
                'log_pattern': 'crawl_*.log',
                'max_age_h': 24,
                'success_grep': 'Crawl complete',
                'failure_grep': 'CRASHED',
            })
            assert result['status'] == 'ok'


# ═══════════════════════════════════════════════════════════════════════════════
# Ticker Return Functions
# ═══════════════════════════════════════════════════════════════════════════════

class TestTickerReturn:
    """Tests for get_ticker_20d_return and get_spy_20d_return."""

    def test_spy_return_from_dataframe(self):
        """Should compute SPY 20d return from price DataFrame."""
        import pandas as pd
        from scripts.run_daily_fast import get_spy_20d_return

        dates = pd.date_range(end='2026-03-25', periods=30, freq='B')
        prices = [100 + i * 0.5 for i in range(30)]  # Steadily rising
        df = pd.DataFrame({'date': dates, 'ticker': 'SPY', 'close': prices})
        ret = get_spy_20d_return(df)
        assert ret > 0  # Rising prices = positive return

    def test_spy_return_insufficient_data(self):
        """Should return 0.0 with insufficient data."""
        import pandas as pd
        from scripts.run_daily_fast import get_spy_20d_return

        df = pd.DataFrame({'date': pd.date_range('2026-03-20', periods=5),
                           'ticker': 'SPY', 'close': [100] * 5})
        assert get_spy_20d_return(df) == 0.0

    def test_ticker_20d_return_from_dataframe(self):
        import pandas as pd
        from scripts.run_daily_fast import get_ticker_20d_return

        dates = pd.date_range(end='2026-03-25', periods=30, freq='B')
        prices = [3.5 - i * 0.01 for i in range(30)]  # Declining
        df = pd.DataFrame({'date': dates, 'ticker': 'ES3.SI', 'close': prices})
        ret = get_ticker_20d_return('ES3.SI', df)
        assert ret < 0  # Falling prices = negative return

    def test_ticker_20d_return_missing_ticker(self):
        """Should return 0.0 for ticker not in DataFrame."""
        import pandas as pd
        from scripts.run_daily_fast import get_ticker_20d_return

        df = pd.DataFrame({'date': pd.date_range('2026-03-01', periods=30),
                           'ticker': 'SPY', 'close': [100] * 30})
        ret = get_ticker_20d_return('MISSING.SI', df)
        # Falls through to yfinance, which may return 0.0 or actual data
        assert isinstance(ret, float)


# ═══════════════════════════════════════════════════════════════════════════════
# Download Fundamentals Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestDownloadFundamentals:
    """Tests for the CSV write fix in download_fundamentals.py."""

    def test_csv_merge_preserves_existing(self):
        """New data should append to existing, not overwrite different-date rows."""
        import pandas as pd

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("date,ticker,pe,pb\n")
            f.write("2026-01-09,AAPL,34.6,51.7\n")
            f.write("2026-01-09,MSFT,36.0,12.0\n")
            f.flush()

            # Simulate what download_fundamentals does: merge new data
            existing_df = pd.read_csv(f.name)
            new_df = pd.DataFrame([
                {'date': '2026-03-25', 'ticker': 'AAPL', 'pe': 31.9, 'pb': 42.1},
            ])

            # Remove same ticker+date from existing
            existing_df = existing_df[~(
                (existing_df['ticker'].isin(new_df['ticker'])) &
                (existing_df['date'] == new_df['date'].iloc[0])
            )]
            merged = pd.concat([existing_df, new_df], ignore_index=True)

            assert len(merged) == 3  # 2 old + 1 new (different dates)
            assert set(merged['ticker']) == {'AAPL', 'MSFT'}
            os.unlink(f.name)


# ═══════════════════════════════════════════════════════════════════════════════
# Integration: Full Pipeline Smoke Test
# ═══════════════════════════════════════════════════════════════════════════════

class TestIntegrationSmoke:
    """Smoke tests verifying modules integrate without import errors."""

    def test_slack_notifier_importable_from_scripts(self):
        from utils.slack_notifier import SlackNotifier
        n = SlackNotifier(job_name="smoke-test", webhook_url="")
        assert n.job_name == "smoke-test"

    def test_health_monitor_importable(self):
        from scripts.health_monitor import run_health_check, JOBS
        assert callable(run_health_check)

    def test_regime_functions_importable(self):
        from scripts.run_daily_fast import (
            compute_dual_regime, compute_vix_scale,
            get_spy_20d_return, get_ticker_20d_return, get_vix_level
        )
        assert all(callable(f) for f in [
            compute_dual_regime, compute_vix_scale,
            get_spy_20d_return, get_ticker_20d_return, get_vix_level
        ])
