"""
Dashboard Utility Functions
===========================
Helper functions for formatting, data processing, and common operations.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Optional, Union, List, Dict, Any


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent.parent.parent


def format_percent(value: Optional[float], with_sign: bool = True) -> str:
    """Format value as percentage.
    
    Args:
        value: Value to format (0.1 = 10%)
        with_sign: Whether to include + for positive values
    
    Returns:
        Formatted percentage string
    """
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "N/A"
    
    if abs(value) < 10:  # Normal percentage
        if with_sign:
            return f"{value*100:+.2f}%"
        return f"{value*100:.2f}%"
    else:  # Already a percentage or large number
        return f"{value:.2f}%"


def format_number(value: Optional[float], decimals: int = 2, with_commas: bool = True) -> str:
    """Format number with specified decimals.
    
    Args:
        value: Value to format
        decimals: Number of decimal places
        with_commas: Whether to include thousand separators
    
    Returns:
        Formatted number string
    """
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "N/A"
    
    if with_commas:
        return f"{value:,.{decimals}f}"
    return f"{value:.{decimals}f}"


def format_currency(value: Optional[float], currency: str = "$") -> str:
    """Format value as currency.
    
    Args:
        value: Value to format
        currency: Currency symbol
    
    Returns:
        Formatted currency string
    """
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "N/A"
    
    if value >= 0:
        return f"{currency}{value:,.2f}"
    return f"-{currency}{abs(value):,.2f}"


def format_date(value: Optional[Union[str, datetime]], fmt: str = "%Y-%m-%d %H:%M") -> str:
    """Format datetime value.
    
    Args:
        value: DateTime value or string
        fmt: Output format
    
    Returns:
        Formatted date string
    """
    if value is None:
        return "N/A"
    
    if isinstance(value, str):
        try:
            value = pd.to_datetime(value)
        except:
            return value
    
    return value.strftime(fmt)


def get_color_for_value(value: Optional[float], positive_good: bool = True) -> str:
    """Get CSS class for positive/negative values.
    
    Args:
        value: Value to evaluate
        positive_good: Whether positive values are good (green) or bad (red)
    
    Returns:
        CSS class name
    """
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "neutral"
    
    if positive_good:
        return "positive" if value > 0 else "negative" if value < 0 else "neutral"
    else:
        return "negative" if value > 0 else "positive" if value < 0 else "neutral"


def truncate_string(s: str, max_length: int = 20, suffix: str = "...") -> str:
    """Truncate string to max length.
    
    Args:
        s: String to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated
    
    Returns:
        Truncated string
    """
    if len(s) <= max_length:
        return s
    return s[:max_length - len(suffix)] + suffix


def safe_get(data: Dict[str, Any], key: str, default: Any = None) -> Any:
    """Safely get a value from a dictionary.
    
    Args:
        data: Dictionary to search
        key: Key to look for
        default: Default value if not found or None
    
    Returns:
        Value or default
    """
    value = data.get(key, default)
    if value is None:
        return default
    return value


def calculate_change(current: float, previous: float) -> Optional[float]:
    """Calculate percentage change between two values.
    
    Args:
        current: Current value
        previous: Previous value
    
    Returns:
        Percentage change or None
    """
    if previous is None or previous == 0:
        return None
    return (current - previous) / abs(previous)


def get_run_folder(run_id: str, watchlist: Optional[str] = None) -> Path:
    """Get the output folder for a specific run.
    
    Args:
        run_id: Run ID
        watchlist: Optional watchlist name (for new format with watchlist prefix)
    
    Returns:
        Path to run folder
    """
    output_base = get_project_root() / "output"
    
    # First check if a folder with watchlist prefix exists
    if watchlist:
        watchlist_folder = output_base / f"run_{watchlist}_{run_id[:16]}"
        if watchlist_folder.exists():
            return watchlist_folder
    
    # Search for any matching folder (handles cases with watchlist prefix)
    for folder in output_base.iterdir():
        if folder.is_dir() and run_id[:16] in folder.name:
            return folder
    
    # Default to standard format
    return output_base / f"run_{run_id[:16]}"


def find_run_folder(run_id: str) -> Optional[Path]:
    """Find the output folder for a run, handling different naming formats.
    
    Args:
        run_id: Run ID (full or partial)
    
    Returns:
        Path to run folder if found, None otherwise
    """
    output_base = get_project_root() / "output"
    
    if not output_base.exists():
        return None
    
    run_id_short = run_id[:16]
    
    # Search for matching folder
    for folder in output_base.iterdir():
        if folder.is_dir() and folder.name.startswith('run_'):
            # Check if run_id is in the folder name
            if run_id_short in folder.name:
                return folder
    
    return None


def check_run_folder_exists(run_id: str) -> bool:
    """Check if a run folder exists.
    
    Args:
        run_id: Run ID
    
    Returns:
        True if folder exists
    """
    return get_run_folder(run_id).exists()


def get_run_files(run_id: str) -> List[Path]:
    """Get all files in a run folder.
    
    Args:
        run_id: Run ID
    
    Returns:
        List of file paths
    """
    folder = get_run_folder(run_id)
    if not folder.exists():
        return []
    return list(folder.iterdir())


def categorize_file(filename: str) -> str:
    """Categorize a file by its name.
    
    Args:
        filename: Name of the file
    
    Returns:
        Category string
    """
    filename_lower = filename.lower()
    
    if 'backtest' in filename_lower:
        return 'backtest'
    elif 'vertical' in filename_lower:
        return 'vertical'
    elif 'horizontal' in filename_lower or 'portfolio' in filename_lower:
        return 'horizontal'
    elif 'ai' in filename_lower or 'commentary' in filename_lower or 'recommendation' in filename_lower:
        return 'ai'
    elif 'enriched' in filename_lower:
        return 'enriched'
    else:
        return 'other'


def get_status_emoji(status: str) -> str:
    """Get emoji for a status string.
    
    Args:
        status: Status string
    
    Returns:
        Emoji string
    """
    status_map = {
        'completed': '✅',
        'running': '🔄',
        'failed': '❌',
        'pending': '⏳',
        'partial': '🟡',
    }
    return status_map.get(status.lower(), '❓')


def create_metric_html(label: str, value: str, delta: Optional[str] = None, 
                       delta_color: str = "normal") -> str:
    """Create HTML for a styled metric card.
    
    Args:
        label: Metric label
        value: Metric value
        delta: Optional delta/change text
        delta_color: Color for delta (normal, positive, negative)
    
    Returns:
        HTML string
    """
    delta_html = ""
    if delta:
        delta_class = ""
        if delta_color == "positive":
            delta_class = "positive"
        elif delta_color == "negative":
            delta_class = "negative"
        delta_html = f'<div class="delta {delta_class}">{delta}</div>'
    
    return f"""
    <div class="metric-card">
        <h3>{label}</h3>
        <div class="value">{value}</div>
        {delta_html}
    </div>
    """


def create_stock_card_html(ticker: str, score: float, sector: str = "",
                           change: Optional[float] = None) -> str:
    """Create HTML for a stock card.
    
    Args:
        ticker: Stock ticker
        score: Stock score
        sector: Sector name
        change: Price change
    
    Returns:
        HTML string
    """
    card_class = "stock-card"
    if change is not None:
        card_class += " positive" if change > 0 else " negative" if change < 0 else ""
    
    change_html = ""
    if change is not None:
        change_class = "positive" if change > 0 else "negative" if change < 0 else "neutral"
        change_html = f'<span class="{change_class}">{change:+.2f}%</span>'
    
    return f"""
    <div class="{card_class}">
        <div class="ticker">{ticker}</div>
        <div class="sector">{sector}</div>
        <div style="margin-top: 0.5rem;">
            Score: <strong>{score:.1f}</strong> {change_html}
        </div>
    </div>
    """


def create_progress_step_html(step: int, label: str, status: str = "pending") -> str:
    """Create HTML for a progress step.
    
    Args:
        step: Step number
        label: Step label
        status: Step status (pending, active, complete)
    
    Returns:
        HTML string
    """
    icon = "✓" if status == "complete" else str(step)
    
    return f"""
    <div class="progress-step {status}">
        <div class="step-icon">{icon}</div>
        <div class="step-label">{label}</div>
    </div>
    """
