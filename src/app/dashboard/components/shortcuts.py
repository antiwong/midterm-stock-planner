"""
Keyboard Shortcuts Support
==========================
Keyboard shortcuts for common dashboard actions.
"""

import streamlit as st
from typing import Dict, Callable, Optional


# Define keyboard shortcuts
SHORTCUTS = {
    # Navigation
    'r': 'Refresh page',
    'n': 'New analysis',
    'o': 'Overview',
    'a': 'Run analysis',
    'p': 'Portfolio builder',
    'w': 'Watchlist manager',
    'd': 'Documentation',
    's': 'Settings',
    'c': 'Comprehensive Analysis',
    'i': 'AI Insights',
    'e': 'Stock Explorer',
    't': 'Purchase Triggers',
    'm': 'Portfolio Analysis',
    '?': 'Show shortcuts',
    # Actions
    'x': 'Export data',
    'f': 'Filter/Search',
    'u': 'Update data',
    'v': 'Validate data',
}


def render_shortcuts_help():
    """Render a help dialog showing available keyboard shortcuts."""
    st.markdown("### ⌨️ Keyboard Shortcuts")
    st.markdown("""
    **Navigation:**
    | Key | Action |
    |-----|--------|
    | `O` | Go to Overview |
    | `A` | Run Analysis |
    | `P` | Portfolio Builder |
    | `W` | Watchlist Manager |
    | `C` | Comprehensive Analysis |
    | `I` | AI Insights |
    | `E` | Stock Explorer |
    | `T` | Purchase Triggers |
    | `M` | Portfolio Analysis |
    | `D` | Documentation |
    | `S` | Settings |
    
    **Actions:**
    | Key | Action |
    |-----|--------|
    | `R` | Refresh current page |
    | `N` | Start new analysis |
    | `X` | Export data |
    | `F` | Open filter/search |
    | `U` | Update data |
    | `V` | Validate data |
    | `?` | Show this help dialog |
    
    **Tips:**
    - Shortcuts work when you're not typing in input fields
    - Press `?` anytime to see this help
    - Some shortcuts may require page refresh to take effect
    """)
    
    st.info("💡 **Tip**: Press `?` anytime to see this help dialog. Shortcuts are most reliable when not focused on input fields.")


def handle_shortcut(key: str) -> Optional[str]:
    """Handle keyboard shortcut and return navigation target if applicable.
    
    Args:
        key: Pressed key (lowercase)
    
    Returns:
        Navigation target page identifier or None
    """
    from ..config import MAIN_WORKFLOW, STANDALONE_TOOLS, UTILITIES
    
    # Map shortcuts to pages
    shortcut_map = {
        'o': 'overview',
        'a': 'run_analysis',
        'p': 'portfolio_builder',
        'w': 'watchlist_manager',
        'c': 'comprehensive_analysis',
        'i': 'ai_insights',
        'e': 'stock_explorer',
        't': 'purchase_triggers',
        'm': 'portfolio_analysis',
        'd': 'documentation',
        's': 'settings',
    }
    
    if key == 'r':
        st.rerun()
        return None
    elif key == 'n':
        # Trigger new analysis (will be handled by page)
        st.session_state['trigger_new_analysis'] = True
        return 'run_analysis'
    elif key in shortcut_map:
        target = shortcut_map[key]
        # Find page label
        all_pages = MAIN_WORKFLOW + STANDALONE_TOOLS + UTILITIES
        for label, identifier in all_pages:
            if identifier == target:
                return label
    elif key == '?':
        st.session_state['show_shortcuts'] = True
        return None
    
    return None


def inject_shortcuts_script():
    """Inject JavaScript to capture keyboard shortcuts."""
    st.markdown("""
    <script>
    document.addEventListener('keydown', function(e) {
        // Only capture if not typing in input fields
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
            return;
        }
        
        const key = e.key.toLowerCase();
        const shortcuts = ['r', 'n', 'o', 'a', 'p', 'w', 'c', 'i', 'e', 't', 'm', 'd', 's', 'x', 'f', 'u', 'v', '?'];
        
        if (shortcuts.includes(key)) {
            // Store in session storage for Python to read
            sessionStorage.setItem('shortcut_pressed', key);
            // Trigger a small delay to allow Streamlit to process
            setTimeout(() => {
                window.location.reload();
            }, 100);
        }
    });
    </script>
    """, unsafe_allow_html=True)


def check_shortcuts():
    """Check for keyboard shortcuts and handle them.
    
    Note: This is a simplified implementation. Full keyboard shortcut
    support in Streamlit requires more complex JavaScript integration.
    For now, we provide visual shortcuts help and session state triggers.
    """
    # Check if shortcuts help should be shown
    if st.session_state.get('show_shortcuts', False):
        with st.expander("⌨️ Keyboard Shortcuts", expanded=True):
            render_shortcuts_help()
        st.session_state['show_shortcuts'] = False
    
    # Inject shortcuts script
    inject_shortcuts_script()
