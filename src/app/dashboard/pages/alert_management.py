"""
Alert Management Page
=====================
Manage alert configurations and view alert history.
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any

from ..components.sidebar import render_page_header
from ..data import load_runs
from src.analytics.alert_system import AlertService, AlertType, AlertChannel


def render_alert_management():
    """Render alert management page."""
    render_page_header("Alert Management", "Configure and manage portfolio alerts")
    
    alert_service = AlertService()
    
    # Tabs
    tab1, tab2, tab3 = st.tabs(["📋 Alert Configurations", "📨 Alert History", "➕ Create Alert"])
    
    with tab1:
        _render_alert_configs(alert_service)
    
    with tab2:
        _render_alert_history(alert_service)
    
    with tab3:
        _render_create_alert(alert_service)


def _render_alert_configs(alert_service: AlertService):
    """Render alert configurations."""
    st.subheader("Active Alert Configurations")
    
    # Get runs for filtering
    runs = load_runs()
    run_options = {f"{r['name'] or r['run_id'][:16]}": r['run_id'] for r in runs}
    run_options['All Runs'] = None
    
    selected_run = st.selectbox(
        "Filter by Run",
        options=list(run_options.keys()),
        key="alert_config_run_filter"
    )
    selected_run_id = run_options[selected_run]
    
    # Get configs
    configs = alert_service.get_alert_configs(run_id=selected_run_id)
    
    if not configs:
        st.info("No alert configurations found. Create one in the 'Create Alert' tab.")
        return
    
    # Display configs
    for config in configs:
        with st.expander(f"🔔 {config.alert_type.replace('_', ' ').title()} - {config.run_id[:16] if config.run_id else 'Global'}", expanded=False):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.write(f"**Type:** {config.alert_type}")
                st.write(f"**Run ID:** {config.run_id[:16] if config.run_id else 'All Runs'}")
                st.write(f"**Threshold:** {config.threshold:.2%}" if config.threshold else "**Threshold:** Any")
                st.write(f"**Channels:** {', '.join(config.get_channels())}")
                st.write(f"**Min Interval:** {config.min_interval_hours} hours")
                st.write(f"**Status:** {'✅ Enabled' if config.enabled else '❌ Disabled'}")
            
            with col2:
                if st.button("🗑️ Delete", key=f"delete_config_{config.id}"):
                    # Delete logic would go here
                    st.warning("Delete functionality to be implemented")
                
                if st.button("✏️ Edit", key=f"edit_config_{config.id}"):
                    st.info("Edit functionality to be implemented")
            
            if config.last_sent_at:
                st.caption(f"Last sent: {config.last_sent_at.strftime('%Y-%m-%d %H:%M:%S')}")


def _render_alert_history(alert_service: AlertService):
    """Render alert history."""
    st.subheader("Alert History")
    
    # Filters
    col1, col2 = st.columns(2)
    
    with col1:
        runs = load_runs()
        run_options = {f"{r['name'] or r['run_id'][:16]}": r['run_id'] for r in runs}
        run_options['All Runs'] = None
        selected_run = st.selectbox(
            "Filter by Run",
            options=list(run_options.keys()),
            key="alert_history_run_filter"
        )
        selected_run_id = run_options[selected_run]
    
    with col2:
        alert_types = ['drawdown', 'price_change', 'position_change', 'volume_spike', 'rebalancing', 'benchmark_divergence']
        selected_type = st.selectbox(
            "Filter by Type",
            options=['All'] + alert_types,
            key="alert_history_type_filter"
        )
    
    # Get history
    history = alert_service.get_alert_history(
        run_id=selected_run_id,
        alert_type=selected_type if selected_type != 'All' else None,
        limit=100
    )
    
    if not history:
        st.info("No alert history found.")
        return
    
    # Display as table
    history_data = []
    for alert in history:
        history_data.append({
            'Time': alert.sent_at.strftime('%Y-%m-%d %H:%M:%S'),
            'Type': alert.alert_type.replace('_', ' ').title(),
            'Level': alert.level.upper(),
            'Message': alert.message[:100] + '...' if len(alert.message) > 100 else alert.message,
            'Channels': ', '.join(alert.get_channels_sent()),
            'Delivered': '✅' if alert.delivered else '❌'
        })
    
    df = pd.DataFrame(history_data)
    st.dataframe(df, use_container_width=True, hide_index=True)


def _render_create_alert(alert_service: AlertService):
    """Render create alert form."""
    st.subheader("Create New Alert Configuration")
    
    with st.form("create_alert_form"):
        # Run selection
        runs = load_runs()
        run_options = {f"{r['name'] or r['run_id'][:16]}": r['run_id'] for r in runs}
        run_options['All Runs (Global)'] = None
        
        selected_run_label = st.selectbox(
            "Run (or Global)",
            options=list(run_options.keys()),
            key="create_alert_run"
        )
        selected_run_id = run_options[selected_run_label]
        
        # Alert type
        alert_type = st.selectbox(
            "Alert Type",
            options=[t.value for t in AlertType],
            format_func=lambda x: x.replace('_', ' ').title(),
            key="create_alert_type"
        )
        
        # Threshold
        threshold = st.number_input(
            "Threshold",
            min_value=-1.0,
            max_value=1.0,
            value=-0.10,
            step=0.01,
            format="%.2f",
            help="For drawdown: negative value (e.g., -0.10 for 10% drawdown). For price change: positive value (e.g., 0.05 for 5% change).",
            key="create_alert_threshold"
        )
        
        # Channels
        channels = st.multiselect(
            "Notification Channels",
            options=[c.value for c in AlertChannel],
            default=['in_app'],
            format_func=lambda x: x.replace('_', ' ').title(),
            key="create_alert_channels"
        )
        
        # Email (if email channel selected)
        user_email = None
        if 'email' in channels:
            user_email = st.text_input(
                "Email Address",
                key="create_alert_email"
            )
        
        # Phone (if SMS channel selected)
        user_phone = None
        if 'sms' in channels:
            user_phone = st.text_input(
                "Phone Number",
                help="Format: +1234567890",
                key="create_alert_phone"
            )
        
        # Min interval
        min_interval = st.number_input(
            "Minimum Interval (hours)",
            min_value=0.1,
            max_value=168.0,
            value=1.0,
            step=0.5,
            help="Minimum time between alerts of this type",
            key="create_alert_interval"
        )
        
        # Submit
        submitted = st.form_submit_button("Create Alert Configuration", use_container_width=True)
        
        if submitted:
            if 'email' in channels and not user_email:
                st.error("Email address required when email channel is selected.")
            elif 'sms' in channels and not user_phone:
                st.error("Phone number required when SMS channel is selected.")
            else:
                try:
                    config = alert_service.create_alert_config(
                        alert_type=alert_type,
                        run_id=selected_run_id,
                        user_email=user_email,
                        threshold=threshold,
                        channels=channels,
                        min_interval_hours=min_interval
                    )
                    st.success(f"✅ Alert configuration created successfully! (ID: {config.id})")
                    st.info("Note: Email/SMS notifications require SMTP/SMS configuration in settings.")
                except Exception as e:
                    st.error(f"❌ Error creating alert: {e}")
                    import traceback
                    st.code(traceback.format_exc())
