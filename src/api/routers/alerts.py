from src.api.db import cached_response
"""Alert Management + Notifications router."""

from fastapi import APIRouter

from src.data.shared_db import get_analysis_db

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


def _get_alert_service():
    from src.analytics.alert_system import AlertService
    return AlertService()


@router.get("/configs")
@cached_response(ttl=60)
def list_configs(run_id: str | None = None):
    """List alert configurations."""
    service = _get_alert_service()
    configs = service.get_alert_configs(run_id=run_id)
    return {
        "configs": [
            {
                "id": c.id,
                "alert_type": c.alert_type,
                "run_id": c.run_id,
                "threshold": c.threshold,
                "channels": c.get_channels(),
                "min_interval_hours": c.min_interval_hours,
                "enabled": c.enabled,
                "last_sent_at": c.last_sent_at.isoformat() if c.last_sent_at else None,
            }
            for c in configs
        ]
    }


@router.get("/history")
@cached_response(ttl=60)
def alert_history(run_id: str | None = None, alert_type: str | None = None, limit: int = 100):
    """Get alert history."""
    service = _get_alert_service()
    history = service.get_alert_history(
        run_id=run_id,
        alert_type=alert_type,
        limit=limit,
    )
    return {
        "history": [
            {
                "id": a.id,
                "alert_type": a.alert_type,
                "level": a.level,
                "message": a.message,
                "sent_at": a.sent_at.isoformat() if a.sent_at else None,
                "channels_sent": a.get_channels_sent(),
                "delivered": a.delivered,
            }
            for a in history
        ]
    }


@router.get("/notifications")
@cached_response(ttl=60)
def get_notifications():
    """Get recent notifications (from alert history, last 50)."""
    service = _get_alert_service()
    history = service.get_alert_history(limit=50)
    return {
        "notifications": [
            {
                "id": a.id,
                "type": a.level,
                "category": a.alert_type,
                "message": a.message,
                "timestamp": a.sent_at.isoformat() if a.sent_at else None,
                "read": a.delivered,
            }
            for a in history
        ]
    }
