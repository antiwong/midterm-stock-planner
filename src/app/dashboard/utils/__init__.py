"""
Dashboard Utilities
===================
Utility modules for dashboard functionality.
"""

from .retry import (
    retry_on_failure,
    retry_with_exponential_backoff,
    RetryableOperation,
    retry_network,
    retry_api,
    retry_database
)

from .data_validation import (
    DataQualityChecker,
    validate_before_analysis
)

from .parallel import (
    ParallelProcessor,
    parallel_download,
    parallel_analysis,
    parallel_calculation,
    parallel_map,
    parallel_filter,
    parallelize,
    ParallelPerformanceMonitor
)

from .cache import (
    QueryCache,
    cached_query,
    cache_key_for_run,
    cache_key_for_watchlist,
    clear_cache,
    get_cache_stats
)

# Import general utilities from the parent utils.py module
# This allows backward compatibility while using the new modular structure
# We need to import from the parent directory's utils.py file
import sys
from pathlib import Path
import importlib.util

# Import from parent utils.py (not the utils/ package)
_parent_dir = Path(__file__).parent.parent
_utils_py_path = _parent_dir / "utils.py"

if _utils_py_path.exists():
    # Load utils.py as a module to avoid circular imports
    spec = importlib.util.spec_from_file_location("dashboard_utils_module", _utils_py_path)
    if spec and spec.loader:
        dashboard_utils_module = importlib.util.module_from_spec(spec)
        # Temporarily add parent to sys.path for any imports utils.py might need
        _original_path = sys.path[:]
        try:
            sys.path.insert(0, str(_parent_dir))
            spec.loader.exec_module(dashboard_utils_module)
        finally:
            sys.path[:] = _original_path
        
        # Export commonly used functions
        get_project_root = dashboard_utils_module.get_project_root
        format_percent = dashboard_utils_module.format_percent
        format_number = dashboard_utils_module.format_number
        format_currency = dashboard_utils_module.format_currency
        format_date = dashboard_utils_module.format_date
        get_color_for_value = dashboard_utils_module.get_color_for_value
        truncate_string = dashboard_utils_module.truncate_string
        safe_get = dashboard_utils_module.safe_get
        calculate_change = dashboard_utils_module.calculate_change
        get_run_folder = dashboard_utils_module.get_run_folder
        find_run_folder = dashboard_utils_module.find_run_folder
        check_run_folder_exists = dashboard_utils_module.check_run_folder_exists
        get_run_files = dashboard_utils_module.get_run_files
        categorize_file = dashboard_utils_module.categorize_file
        get_status_emoji = dashboard_utils_module.get_status_emoji
        create_metric_html = dashboard_utils_module.create_metric_html
        create_stock_card_html = dashboard_utils_module.create_stock_card_html
        create_progress_step_html = dashboard_utils_module.create_progress_step_html
        get_version = dashboard_utils_module.get_version
        get_ui_settings_path = dashboard_utils_module.get_ui_settings_path
        load_ui_settings = dashboard_utils_module.load_ui_settings
        save_ui_settings = dashboard_utils_module.save_ui_settings
        DEFAULT_UI_SETTINGS = getattr(dashboard_utils_module, 'DEFAULT_UI_SETTINGS', {})
    else:
        # Fallback if spec creation failed
        raise ImportError("Could not create module spec for utils.py")
else:
    # Fallback if utils.py doesn't exist
    def get_project_root():
        return Path(__file__).parent.parent.parent.parent
    
    def load_ui_settings():
        return {}
    
    def save_ui_settings(settings):
        pass
    
    DEFAULT_UI_SETTINGS = {}
    
    # Define other functions as needed
    def format_percent(value, with_sign=True):
        return "N/A"
    
    def format_number(value, decimals=2, with_commas=True):
        return "N/A"
    
    def get_version():
        return "Unknown"
    
    # Define other required functions with minimal implementations
    def format_currency(value, currency="$"):
        return "N/A"
    
    def format_date(value, fmt="%Y-%m-%d %H:%M"):
        return "N/A"
    
    def get_color_for_value(value, positive_good=True):
        return "#000000"
    
    def truncate_string(s, max_length=20, suffix="..."):
        return s[:max_length] + suffix if len(s) > max_length else s
    
    def safe_get(data, key, default=None):
        return data.get(key, default) if isinstance(data, dict) else default
    
    def calculate_change(current, previous):
        return (current - previous) / previous if previous != 0 else None
    
    def get_run_folder(run_id, watchlist=None):
        return get_project_root() / "output" / f"run_{run_id}"
    
    def find_run_folder(run_id):
        return get_run_folder(run_id)
    
    def check_run_folder_exists(run_id):
        return get_run_folder(run_id).exists()
    
    def get_run_files(run_id):
        folder = get_run_folder(run_id)
        return list(folder.glob("*")) if folder.exists() else []
    
    def categorize_file(filename):
        return "other"
    
    def get_status_emoji(status):
        return "❓"
    
    def create_metric_html(label, value, delta=None, color=None):
        return f"<div>{label}: {value}</div>"
    
    def create_stock_card_html(ticker, score, sector="", change=None):
        return f"<div>{ticker}: {score}</div>"
    
    def create_progress_step_html(step, label, status="pending"):
        return f"<div>Step {step}: {label}</div>"
    
    def get_ui_settings_path():
        return get_project_root() / "data" / "ui_settings.json"

__all__ = [
    'retry_on_failure',
    'retry_with_exponential_backoff',
    'RetryableOperation',
    'retry_network',
    'retry_api',
    'retry_database',
    'DataQualityChecker',
    'validate_before_analysis',
    'ParallelProcessor',
    'parallel_download',
    'parallel_analysis',
    'parallel_calculation',
    'parallel_map',
    'parallel_filter',
    'parallelize',
    'ParallelPerformanceMonitor',
    'QueryCache',
    'cached_query',
    'cache_key_for_run',
    'cache_key_for_watchlist',
    'clear_cache',
    'get_cache_stats',
    # General utilities
    'get_project_root',
    'format_percent',
    'format_number',
    'format_currency',
    'format_date',
    'get_color_for_value',
    'truncate_string',
    'safe_get',
    'calculate_change',
    'get_run_folder',
    'find_run_folder',
    'check_run_folder_exists',
    'get_run_files',
    'categorize_file',
    'get_status_emoji',
    'create_metric_html',
    'create_stock_card_html',
    'create_progress_step_html',
    'get_version',
    'get_ui_settings_path',
    'load_ui_settings',
    'save_ui_settings',
    'DEFAULT_UI_SETTINGS',
]
