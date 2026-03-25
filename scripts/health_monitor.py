#!/usr/bin/env python3
"""Health monitor watchdog — runs every 2 hours via cron.

Checks that all scheduled jobs ran within their expected window.
Sends Slack alert if any job is overdue.

This catches what neither systemd OnFailure nor application-level
error handling catches: jobs that silently never started.
"""

import os
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
os.chdir(str(PROJECT_ROOT))

from utils.slack_notifier import SlackNotifier

notifier = SlackNotifier(job_name="health-monitor")

# ── Job definitions ──────────────────────────────────────────────────────────
JOBS = [
    {
        'name':         'sentimentpulse-crawl',
        'log':          '/home/deploy/sentimental_blogs/logs/',
        'log_pattern':  'crawl_*.log',
        'max_age_h':    7,
        'success_grep': 'Crawl complete',
        'failure_grep': 'CRASHED',
    },
    {
        'name':         'daily-fast',
        'log':          '/home/deploy/stock-planner/logs/daily_cron.log',
        'max_age_h':    26,     # Runs Mon-Fri 6:30 AM SGT
        'success_grep': 'COMPLETE in',
        'failure_grep': 'Error',
    },
    {
        'name':         'feedback-eval',
        'log':          '/home/deploy/stock-planner/logs/feedback_cron.log',
        'max_age_h':    25,     # Runs daily 7:00 PM SGT
        'success_grep': 'FEEDBACK REPORT',
        'failure_grep': 'Error',
    },
    {
        'name':         'fundamentals-refresh',
        'log':          '/home/deploy/stock-planner/logs/fundamentals_cron.log',
        'max_age_h':    170,    # Runs weekly Saturday
        'success_grep': 'Done!',
        'failure_grep': 'Error',
    },
]


def check_log(job: dict) -> dict:
    """Check a job's log file for freshness and success/failure markers."""
    result = {
        'name':    job['name'],
        'status':  'unknown',
        'age_h':   None,
        'message': '',
    }

    # Handle directory-based logs (find most recent file matching pattern)
    log_path = Path(job['log'])
    if log_path.is_dir():
        import glob
        pattern = str(log_path / job.get('log_pattern', '*.log'))
        files = sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)
        if not files:
            result['status'] = 'missing'
            result['message'] = f"No log files matching {pattern}"
            return result
        log_path = Path(files[0])
    elif not log_path.exists():
        result['status'] = 'missing'
        result['message'] = f"Log file not found: {job['log']}"
        return result

    # Check file age
    mtime = datetime.fromtimestamp(log_path.stat().st_mtime)
    age_h = (datetime.now() - mtime).total_seconds() / 3600
    result['age_h'] = round(age_h, 1)

    if age_h > job['max_age_h']:
        result['status'] = 'stale'
        result['message'] = f"Last run {age_h:.1f}h ago (max: {job['max_age_h']}h)"
        return result

    # Check last run content
    try:
        text = log_path.read_text(errors='ignore')
        lines = text.splitlines()
        recent = '\n'.join(lines[-100:])

        has_success = job.get('success_grep', '') in recent
        has_failure = job.get('failure_grep', '') in recent

        if has_failure and not has_success:
            result['status'] = 'failed'
            error_lines = [l for l in lines[-50:] if job.get('failure_grep', '') in l]
            result['message'] = '\n'.join(error_lines[-3:])[:200]
        elif has_success:
            result['status'] = 'ok'
            result['message'] = f"Last run {age_h:.1f}h ago"
        else:
            result['status'] = 'warning'
            result['message'] = f"Last run {age_h:.1f}h ago — no success marker"
    except Exception as e:
        result['status'] = 'error'
        result['message'] = f"Could not read log: {e}"

    return result


def run_health_check():
    results = [check_log(job) for job in JOBS]
    failures = [r for r in results if r['status'] in ('failed', 'missing', 'stale')]
    warnings = [r for r in results if r['status'] in ('warning', 'unknown')]
    healthy = [r for r in results if r['status'] == 'ok']

    # Always log summary
    print(f"\n=== Health Check {datetime.now().strftime('%Y-%m-%d %H:%M')} ===")
    icons = {'ok': '✅', 'failed': '❌', 'stale': '⏰',
             'warning': '⚠️', 'missing': '🚫', 'unknown': '❓', 'error': '💥'}
    for r in results:
        icon = icons.get(r['status'], '❓')
        print(f"  {icon} {r['name']}: {r['status']} ({r['message'][:80]})")

    # Send Slack alert only if there are failures
    if failures:
        fields = {f['name']: f"{f['status'].upper()}: {f['message'][:100]}" for f in failures}
        fields['Healthy'] = str(len(healthy))
        notifier.failed(error=f"{len(failures)} job(s) failed or overdue", context=fields)

    elif warnings:
        fields = {w['name']: f"{w['status']}: {w['message'][:100]}" for w in warnings}
        notifier.warning(f"{len(warnings)} job(s) need attention", context=fields)

    # Daily 8 AM SGT summary (0 UTC) even if everything is fine
    current_hour = datetime.now().hour - 8  # SGT to UTC approximation
    if current_hour == 0:
        notifier.completed(metrics={
            'healthy': len(healthy),
            'warnings': len(warnings),
            'failures': len(failures),
        })

    return len(failures)


if __name__ == '__main__':
    sys.exit(run_health_check())
