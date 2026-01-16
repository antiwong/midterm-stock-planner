"""
Dashboard Customizer
===================
Customize dashboard layout and widgets.
"""

import streamlit as st
from typing import List, Dict, Any, Optional
from ..utils import load_ui_settings, save_ui_settings


DASHBOARD_PRESETS = {
    'analyst': {
        'name': 'Analyst',
        'description': 'Detailed metrics and analysis',
        'widgets': ['summary_metrics', 'recent_runs', 'performance_chart', 'data_quality', 'quick_insights']
    },
    'executive': {
        'name': 'Executive',
        'description': 'High-level overview',
        'widgets': ['summary_metrics', 'performance_chart', 'quick_insights']
    },
    'trader': {
        'name': 'Trader',
        'description': 'Real-time focus',
        'widgets': ['summary_metrics', 'recent_runs', 'performance_chart', 'quick_insights']
    },
    'custom': {
        'name': 'Custom',
        'description': 'Your custom layout',
        'widgets': []
    }
}


def get_dashboard_config() -> Dict[str, Any]:
    """Get current dashboard configuration."""
    settings = load_ui_settings()
    return settings.get('dashboard_config', {
        'preset': 'analyst',
        'widgets': DASHBOARD_PRESETS['analyst']['widgets'],
        'widget_order': DASHBOARD_PRESETS['analyst']['widgets']
    })


def save_dashboard_config(config: Dict[str, Any]):
    """Save dashboard configuration."""
    settings = load_ui_settings()
    settings['dashboard_config'] = config
    save_ui_settings(settings)


def render_dashboard_customizer():
    """Render dashboard customization interface."""
    from ..components.sidebar import render_section_header
    
    render_section_header("Dashboard Customization", "🎨")
    
    config = get_dashboard_config()
    
    # Preset selection
    st.markdown("### Presets")
    preset_options = {p['name']: k for k, p in DASHBOARD_PRESETS.items()}
    selected_preset = st.selectbox(
        "Choose Preset",
        options=list(preset_options.keys()),
        index=list(preset_options.values()).index(config.get('preset', 'analyst')),
        help="Select a preset dashboard layout"
    )
    
    preset_key = preset_options[selected_preset]
    
    if preset_key != config.get('preset'):
        config['preset'] = preset_key
        if preset_key != 'custom':
            config['widgets'] = DASHBOARD_PRESETS[preset_key]['widgets']
            config['widget_order'] = DASHBOARD_PRESETS[preset_key]['widgets']
        save_dashboard_config(config)
        st.success(f"✅ Switched to {selected_preset} preset")
        st.rerun()
    
    st.markdown("---")
    
    # Widget selection
    st.markdown("### Widgets")
    available_widgets = {
        'summary_metrics': 'Summary Metrics',
        'recent_runs': 'Recent Runs',
        'performance_chart': 'Performance Chart',
        'data_quality': 'Data Quality',
        'quick_insights': 'Quick Insights',
    }
    
    selected_widgets = []
    for widget_id, widget_name in available_widgets.items():
        if st.checkbox(
            widget_name,
            value=widget_id in config.get('widgets', []),
            key=f"widget_{widget_id}",
            disabled=(preset_key != 'custom')
        ):
            selected_widgets.append(widget_id)
    
    if preset_key == 'custom' and selected_widgets != config.get('widgets', []):
        config['widgets'] = selected_widgets
        config['widget_order'] = selected_widgets
        save_dashboard_config(config)
        st.success("✅ Dashboard configuration saved")
        st.rerun()
    
    st.markdown("---")
    
    # Reset button
    if st.button("🔄 Reset to Default", use_container_width=True):
        config = {
            'preset': 'analyst',
            'widgets': DASHBOARD_PRESETS['analyst']['widgets'],
            'widget_order': DASHBOARD_PRESETS['analyst']['widgets']
        }
        save_dashboard_config(config)
        st.success("✅ Reset to default configuration")
        st.rerun()
