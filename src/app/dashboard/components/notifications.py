"""
Notification System
==================
In-app notifications, preferences, and history.
"""

import streamlit as st
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
from pathlib import Path


class NotificationManager:
    """Manage in-app notifications."""
    
    def __init__(self):
        if 'notifications' not in st.session_state:
            st.session_state['notifications'] = []
        if 'notification_preferences' not in st.session_state:
            st.session_state['notification_preferences'] = {
                'analysis_complete': True,
                'data_updates': True,
                'errors': True,
                'warnings': False,
            }
    
    def add_notification(
        self,
        message: str,
        type: str = 'info',
        category: str = 'general',
        action: Optional[str] = None,
        action_label: Optional[str] = None
    ):
        """Add a notification.
        
        Args:
            message: Notification message
            type: Type (info, success, warning, error)
            category: Category (analysis, data, error, etc.)
            action: Optional action identifier
            action_label: Optional action button label
        """
        notification = {
            'id': len(st.session_state['notifications']),
            'message': message,
            'type': type,
            'category': category,
            'action': action,
            'action_label': action_label,
            'timestamp': datetime.now().isoformat(),
            'read': False
        }
        st.session_state['notifications'].insert(0, notification)  # Add to beginning
    
    def get_unread_count(self) -> int:
        """Get count of unread notifications."""
        return sum(1 for n in st.session_state['notifications'] if not n.get('read', False))
    
    def mark_all_read(self):
        """Mark all notifications as read."""
        for n in st.session_state['notifications']:
            n['read'] = True
    
    def clear_all(self):
        """Clear all notifications."""
        st.session_state['notifications'] = []
    
    def get_notifications(self, unread_only: bool = False) -> List[Dict[str, Any]]:
        """Get notifications.
        
        Args:
            unread_only: If True, only return unread notifications
        
        Returns:
            List of notifications
        """
        notifications = st.session_state['notifications']
        if unread_only:
            return [n for n in notifications if not n.get('read', False)]
        return notifications


def render_notification_bell() -> bool:
    """Render notification bell icon in sidebar. Returns True if clicked."""
    unread_count = NotificationManager().get_unread_count()
    
    if unread_count > 0:
        bell_label = f"🔔 ({unread_count})"
    else:
        bell_label = "🔔"
    
    if st.sidebar.button(bell_label, key="notification_bell", use_container_width=True):
        return True
    return False


def render_notification_center():
    """Render notification center page."""
    from ..components.sidebar import render_page_header, render_section_header
    
    render_page_header(
        "Notifications",
        "View and manage your notifications"
    )
    
    manager = NotificationManager()
    notifications = manager.get_notifications()
    
    # Filter options
    col1, col2, col3 = st.columns(3)
    with col1:
        filter_type = st.selectbox("Filter by Type", ["All", "Info", "Success", "Warning", "Error"])
    with col2:
        show_unread_only = st.checkbox("Unread Only", value=False)
    with col3:
        if st.button("Mark All Read"):
            manager.mark_all_read()
            st.rerun()
    
    # Filter notifications
    filtered = notifications
    if filter_type != "All":
        filtered = [n for n in filtered if n['type'] == filter_type.lower()]
    if show_unread_only:
        filtered = [n for n in filtered if not n.get('read', False)]
    
    # Display notifications
    if not filtered:
        st.info("No notifications")
        return
    
    for notification in filtered:
        with st.container():
            col1, col2 = st.columns([4, 1])
            
            with col1:
                icon = {
                    'info': 'ℹ️',
                    'success': '✅',
                    'warning': '⚠️',
                    'error': '❌'
                }.get(notification['type'], 'ℹ️')
                
                timestamp = datetime.fromisoformat(notification['timestamp'])
                time_str = timestamp.strftime("%Y-%m-%d %H:%M")
                
                if not notification.get('read', False):
                    st.markdown(f"**{icon} {notification['message']}**")
                else:
                    st.markdown(f"{icon} {notification['message']}")
                
                st.caption(f"{notification['category']} • {time_str}")
            
            with col2:
                if not notification.get('read', False):
                    if st.button("✓", key=f"read_{notification['id']}"):
                        notification['read'] = True
                        st.rerun()
                
                if notification.get('action'):
                    if st.button(
                        notification.get('action_label', 'View'),
                        key=f"action_{notification['id']}"
                    ):
                        # Handle action
                        st.session_state['selected_nav_item'] = notification['action']
                        st.rerun()
    
    # Clear all button
    st.markdown("---")
    if st.button("🗑️ Clear All Notifications", type="secondary"):
        manager.clear_all()
        st.rerun()
