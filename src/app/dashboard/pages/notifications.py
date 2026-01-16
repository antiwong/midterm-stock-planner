"""
Notifications Page
==================
Notification center for viewing and managing notifications.
"""

from ..components.notifications import render_notification_center


def render_notifications():
    """Render notifications page."""
    render_notification_center()
