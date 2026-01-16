"""
Enhanced Error Messages and User Guidance
=========================================
Improved error handling with actionable guidance for users.
"""

import streamlit as st
from typing import Optional, List, Dict, Any
import traceback


class ErrorHandler:
    """Enhanced error handler with actionable guidance."""
    
    ERROR_GUIDANCE = {
        'file_not_found': {
            'title': 'File Not Found',
            'message': 'The requested file could not be found.',
            'actions': [
                'Check if the file path is correct',
                'Verify the file exists in the expected location',
                'Try refreshing the page or restarting the analysis'
            ]
        },
        'data_loading_error': {
            'title': 'Data Loading Error',
            'message': 'Failed to load required data.',
            'actions': [
                'Verify data files exist in the data directory',
                'Check file permissions',
                'Ensure data files are properly formatted',
                'Try running the data download process again'
            ]
        },
        'analysis_error': {
            'title': 'Analysis Error',
            'message': 'An error occurred during analysis.',
            'actions': [
                'Check if all required data is available',
                'Verify configuration settings',
                'Review error details below',
                'Try running the analysis again'
            ]
        },
        'database_error': {
            'title': 'Database Error',
            'message': 'Failed to connect to or query the database.',
            'actions': [
                'Check database file exists and is accessible',
                'Verify database permissions',
                'Try refreshing the page',
                'Contact support if the issue persists'
            ]
        },
        'validation_error': {
            'title': 'Validation Error',
            'message': 'Data validation failed.',
            'actions': [
                'Review the validation errors below',
                'Fix data quality issues',
                'Ensure all required fields are present',
                'Check data format and types'
            ]
        },
        'export_error': {
            'title': 'Export Error',
            'message': 'Failed to export data.',
            'actions': [
                'Check if export format is supported',
                'Verify required packages are installed',
                'Ensure sufficient disk space',
                'Try exporting in a different format'
            ]
        }
    }
    
    @staticmethod
    def render_error(
        error: Exception,
        error_type: Optional[str] = None,
        show_traceback: bool = False,
        custom_message: Optional[str] = None,
        custom_actions: Optional[List[str]] = None
    ):
        """Render an enhanced error message with guidance.
        
        Args:
            error: The exception that occurred
            error_type: Type of error (key in ERROR_GUIDANCE)
            show_traceback: Whether to show full traceback
            custom_message: Custom error message
            custom_actions: Custom action items
        """
        # Determine error type if not provided
        if not error_type:
            error_type = ErrorHandler._classify_error(error)
        
        # Get guidance
        guidance = ErrorHandler.ERROR_GUIDANCE.get(error_type, {
            'title': 'Error',
            'message': str(error),
            'actions': ['Review the error details', 'Try the operation again']
        })
        
        # Use custom message if provided
        message = custom_message or guidance.get('message', str(error))
        actions = custom_actions or guidance.get('actions', [])
        
        # Get dark mode setting
        from ..utils import load_ui_settings
        settings = load_ui_settings()
        dark_mode = settings.get("dark_mode", False)
        
        if dark_mode:
            error_bg = "#3a2a2a"
            error_text = "#f5f5f7"
            error_border = "#4a3a3a"
        else:
            error_bg = "#ffe4e6"
            error_text = "#0b0b0f"
            error_border = "#fecdd3"
        
        # Render error card
        st.markdown(f"""
        <div style="
            background: {error_bg};
            padding: 1.5rem;
            border-radius: 12px;
            color: {error_text};
            margin: 1rem 0;
            border: 1px solid {error_border};
        ">
            <h3 style="margin: 0 0 0.5rem 0; color: {error_text};">
                ❌ {guidance['title']}
            </h3>
            <p style="margin: 0 0 1rem 0; opacity: 0.95;">{message}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Render actionable guidance
        if actions:
            with st.expander("🔧 How to Fix", expanded=True):
                st.markdown("**Try these steps:**")
                for i, action in enumerate(actions, 1):
                    st.markdown(f"{i}. {action}")
        
        # Show traceback if requested
        if show_traceback:
            with st.expander("🔍 Technical Details", expanded=False):
                st.code(traceback.format_exc())
    
    @staticmethod
    def _classify_error(error: Exception) -> str:
        """Classify error type based on exception."""
        error_str = str(error).lower()
        error_type = type(error).__name__
        
        if 'file' in error_str or 'not found' in error_str:
            return 'file_not_found'
        elif 'data' in error_str or 'load' in error_str:
            return 'data_loading_error'
        elif 'database' in error_str or 'sql' in error_str:
            return 'database_error'
        elif 'validation' in error_str or 'validate' in error_str:
            return 'validation_error'
        elif 'export' in error_str:
            return 'export_error'
        elif 'analysis' in error_str:
            return 'analysis_error'
        else:
            return 'analysis_error'  # Default


def render_warning_with_actions(
    message: str,
    actions: List[str],
    icon: str = "⚠️"
):
    """Render a warning with actionable steps (dark mode supported).
    
    Args:
        message: Warning message
        actions: List of actionable steps
        icon: Warning icon
    """
    from ..utils import load_ui_settings
    settings = load_ui_settings()
    dark_mode = settings.get("dark_mode", False)
    
    if dark_mode:
        warning_bg = "#3a3a2a"
        warning_text = "#f5f5f7"
        warning_border = "#4a4a3a"
    else:
        warning_bg = "#fff2d9"
        warning_text = "#0b0b0f"
        warning_border = "#ffe0b2"
    
    st.markdown(f"""
    <div style="
        background: {warning_bg};
        padding: 1.5rem;
        border-radius: 12px;
        color: {warning_text};
        margin: 1rem 0;
        border: 1px solid {warning_border};
    ">
        <h4 style="margin: 0 0 0.5rem 0; color: {warning_text};">
            {icon} Warning
        </h4>
        <p style="margin: 0 0 1rem 0; opacity: 0.95;">{message}</p>
    </div>
    """, unsafe_allow_html=True)
    
    if actions:
        with st.expander("💡 Recommended Actions", expanded=False):
            for i, action in enumerate(actions, 1):
                st.markdown(f"{i}. {action}")


def render_info_with_help(
    message: str,
    help_text: str,
    icon: str = "ℹ️"
):
    """Render an info message with help text (dark mode supported).
    
    Args:
        message: Info message
        help_text: Help text to display
        icon: Info icon
    """
    from ..utils import load_ui_settings
    settings = load_ui_settings()
    dark_mode = settings.get("dark_mode", False)
    
    if dark_mode:
        info_bg = "#2a2a3a"
        info_text = "#f5f5f7"
        info_border = "#3a3a4a"
    else:
        info_bg = "#eaf3ff"
        info_text = "#0b0b0f"
        info_border = "#d6e6ff"
    
    st.markdown(f"""
    <div style="
        background: {info_bg};
        padding: 1.5rem;
        border-radius: 12px;
        color: {info_text};
        margin: 1rem 0;
        border: 1px solid {info_border};
    ">
        <h4 style="margin: 0 0 0.5rem 0; color: {info_text};">
            {icon} Information
        </h4>
        <p style="margin: 0; opacity: 0.95;">{message}</p>
    </div>
    """, unsafe_allow_html=True)
    
    with st.expander("❓ Learn More", expanded=False):
        st.markdown(help_text)
