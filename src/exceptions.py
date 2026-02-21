"""Custom exceptions for mid-term stock planner.

This module defines custom exception classes for better error handling
and user-friendly error messages.
"""


class StockPlannerError(Exception):
    """Base exception for all stock planner errors."""
    pass


class DataValidationError(StockPlannerError):
    """Raised when data validation fails."""
    pass


class ConfigurationError(StockPlannerError):
    """Raised when configuration is invalid."""
    pass


class ModelError(StockPlannerError):
    """Raised when model training or prediction fails."""
    pass


class BacktestError(StockPlannerError):
    """Raised when backtest execution fails."""

    def __init__(self, message: str, diagnostics: dict | None = None):
        super().__init__(message)
        self.diagnostics = diagnostics or {}


class InsufficientBacktestDataError(BacktestError):
    """Raised when training data span is too short for walk-forward windows."""

    def __init__(
        self,
        message: str,
        data_range_days: int | None = None,
        required_days: int | None = None,
        windows_attempted: int = 0,
        windows_skipped: int = 0,
        skipped_reasons: list | None = None,
        suggested_fix: str | None = None,
    ):
        super().__init__(
            message,
            diagnostics={
                "data_range_days": data_range_days,
                "required_days": required_days,
                "windows_attempted": windows_attempted,
                "windows_skipped": windows_skipped,
                "skipped_reasons": skipped_reasons or [],
                "suggested_fix": suggested_fix,
            },
        )


class InsufficientDataError(DataValidationError):
    """Raised when there is insufficient data for an operation."""
    pass


class FeatureMismatchError(ModelError):
    """Raised when features don't match between training and inference."""
    pass


def format_error_message(error: Exception, context: str = "") -> str:
    """
    Format an error message for user display.
    
    Args:
        error: The exception that occurred.
        context: Additional context about what was being done.
    
    Returns:
        Formatted error message string.
    """
    error_type = type(error).__name__
    message = str(error)
    
    if context:
        return f"Error {context}: {message} ({error_type})"
    else:
        return f"{error_type}: {message}"


def handle_cli_error(error: Exception, verbose: bool = False) -> str:
    """
    Handle an error for CLI output.
    
    Args:
        error: The exception that occurred.
        verbose: Whether to include traceback information.
    
    Returns:
        User-friendly error message.
    """
    if isinstance(error, DataValidationError):
        return f"Data Error: {error}\nPlease check your data files and formats."
    
    elif isinstance(error, ConfigurationError):
        return f"Configuration Error: {error}\nPlease check your config file."
    
    elif isinstance(error, ModelError):
        return f"Model Error: {error}\nPlease check your model and feature setup."
    
    elif isinstance(error, BacktestError):
        msg = str(error)
        # Use brief header only if message doesn't already include Fix/suggestions
        if "Fix:" in msg or "Suggested" in msg or "python scripts/" in msg:
            return msg
        return f"Backtest Error: {msg}\nPlease check your data and parameters."
    
    elif isinstance(error, FileNotFoundError):
        return f"File Not Found: {error}\nPlease verify the file path exists."
    
    elif isinstance(error, PermissionError):
        return f"Permission Denied: {error}\nPlease check file permissions."
    
    else:
        if verbose:
            import traceback
            return f"Unexpected Error: {error}\n\n{traceback.format_exc()}"
        else:
            return f"Unexpected Error: {error}\nRun with --verbose for more details."
