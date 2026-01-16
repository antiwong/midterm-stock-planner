"""
Alert System
============
Email/SMS notifications for portfolio alerts and important events.
"""

import smtplib
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum
import logging

from src.analytics.models import get_db, Base
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship

logger = logging.getLogger(__name__)


class AlertType(Enum):
    """Types of alerts."""
    DRAWDOWN = "drawdown"
    PRICE_CHANGE = "price_change"
    POSITION_CHANGE = "position_change"
    VOLUME_SPIKE = "volume_spike"
    REBALANCING = "rebalancing"
    BENCHMARK_DIVERGENCE = "benchmark_divergence"
    CUSTOM = "custom"


class AlertChannel(Enum):
    """Alert delivery channels."""
    EMAIL = "email"
    SMS = "sms"
    IN_APP = "in_app"


class AlertConfig(Base):
    """Alert configuration for a user/run."""
    __tablename__ = 'alert_configs'
    
    id = Column(Integer, primary_key=True)
    run_id = Column(String(50), ForeignKey('runs.run_id'), nullable=True, index=True)
    user_email = Column(String(200), nullable=True, index=True)
    user_phone = Column(String(50), nullable=True)
    
    # Alert type and thresholds
    alert_type = Column(String(50), nullable=False)
    enabled = Column(Boolean, default=True)
    threshold = Column(Float, nullable=True)  # e.g., -0.10 for 10% drawdown
    
    # Notification channels
    channels_json = Column(Text, default='["in_app"]')  # JSON array of channels
    
    # Frequency control
    min_interval_hours = Column(Float, default=1.0)  # Minimum time between alerts
    last_sent_at = Column(DateTime, nullable=True)
    
    # Additional settings
    settings_json = Column(Text)  # JSON for type-specific settings
    
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    def get_channels(self) -> List[str]:
        """Get list of notification channels."""
        return json.loads(self.channels_json) if self.channels_json else ['in_app']
    
    def set_channels(self, channels: List[str]):
        """Set notification channels."""
        self.channels_json = json.dumps(channels)
    
    def get_settings(self) -> Dict:
        """Get type-specific settings."""
        return json.loads(self.settings_json) if self.settings_json else {}
    
    def set_settings(self, settings: Dict):
        """Set type-specific settings."""
        self.settings_json = json.dumps(settings)


class AlertHistory(Base):
    """History of sent alerts."""
    __tablename__ = 'alert_history'
    
    id = Column(Integer, primary_key=True)
    alert_config_id = Column(Integer, ForeignKey('alert_configs.id'), nullable=False, index=True)
    run_id = Column(String(50), ForeignKey('runs.run_id'), nullable=True, index=True)
    
    alert_type = Column(String(50), nullable=False)
    level = Column(String(20), nullable=False)  # info, warning, critical
    message = Column(Text, nullable=False)
    
    # Alert data
    data_json = Column(Text)  # JSON with alert-specific data
    
    # Delivery status
    channels_sent = Column(Text)  # JSON array of channels used
    sent_at = Column(DateTime, default=datetime.now, index=True)
    delivered = Column(Boolean, default=False)
    error_message = Column(Text, nullable=True)
    
    def get_data(self) -> Dict:
        """Get alert data."""
        return json.loads(self.data_json) if self.data_json else {}
    
    def set_data(self, data: Dict):
        """Set alert data."""
        self.data_json = json.dumps(data)
    
    def get_channels_sent(self) -> List[str]:
        """Get list of channels used."""
        return json.loads(self.channels_sent) if self.channels_sent else []


class AlertService:
    """Service for managing and sending alerts."""
    
    def __init__(self, db_path: str = "data/analysis.db", smtp_config: Optional[Dict] = None):
        """
        Initialize alert service.
        
        Args:
            db_path: Path to database
            smtp_config: SMTP configuration dict with keys:
                - host: SMTP server host
                - port: SMTP server port
                - username: SMTP username
                - password: SMTP password
                - use_tls: Use TLS (default True)
        """
        self.db = get_db(db_path)
        self.smtp_config = smtp_config or {}
        self.sms_config = {}  # SMS configuration (Twilio, etc.)
    
    def create_alert_config(
        self,
        alert_type: str,
        run_id: Optional[str] = None,
        user_email: Optional[str] = None,
        threshold: Optional[float] = None,
        channels: Optional[List[str]] = None,
        min_interval_hours: float = 1.0,
        settings: Optional[Dict] = None
    ) -> AlertConfig:
        """
        Create a new alert configuration.
        
        Args:
            alert_type: Type of alert (drawdown, price_change, etc.)
            run_id: Optional run ID to monitor
            user_email: User email for notifications
            threshold: Alert threshold (type-specific)
            channels: List of channels (email, sms, in_app)
            min_interval_hours: Minimum hours between alerts
            settings: Type-specific settings
            
        Returns:
            Created AlertConfig
        """
        session = self.db.get_session()
        try:
            config = AlertConfig(
                run_id=run_id,
                user_email=user_email,
                alert_type=alert_type,
                threshold=threshold,
                min_interval_hours=min_interval_hours
            )
            
            if channels:
                config.set_channels(channels)
            else:
                config.set_channels(['in_app'])
            
            if settings:
                config.set_settings(settings)
            
            session.add(config)
            session.commit()
            session.refresh(config)
            return config
        except Exception as e:
            session.rollback()
            logger.error(f"Error creating alert config: {e}")
            raise
        finally:
            session.close()
    
    def check_and_send_alerts(
        self,
        run_id: str,
        alert_data: Dict[str, Any]
    ) -> List[AlertHistory]:
        """
        Check alert conditions and send notifications.
        
        Args:
            run_id: Run ID to check alerts for
            alert_data: Dictionary with alert information:
                - type: Alert type
                - level: Alert level (info, warning, critical)
                - message: Alert message
                - value: Alert value (e.g., drawdown percentage)
                - data: Additional alert data
                
        Returns:
            List of sent AlertHistory records
        """
        session = self.db.get_session()
        sent_alerts = []
        
        try:
            # Find matching alert configs
            configs = session.query(AlertConfig).filter_by(
                run_id=run_id,
                enabled=True
            ).all()
            
            # Also check for user-level configs (no run_id)
            user_configs = session.query(AlertConfig).filter(
                AlertConfig.run_id.is_(None),
                AlertConfig.enabled == True
            ).all()
            
            all_configs = configs + user_configs
            
            for config in all_configs:
                # Check if alert type matches
                if config.alert_type != alert_data.get('type'):
                    continue
                
                # Check threshold
                if config.threshold is not None:
                    alert_value = alert_data.get('value')
                    if alert_value is None:
                        continue
                    
                    # For negative thresholds (drawdown), check if value is <= threshold
                    # For positive thresholds (price change), check if abs(value) >= threshold
                    if config.threshold < 0:
                        if alert_value > config.threshold:
                            continue
                    else:
                        if abs(alert_value) < config.threshold:
                            continue
                
                # Check minimum interval
                if config.last_sent_at:
                    time_since_last = datetime.now() - config.last_sent_at
                    if time_since_last.total_seconds() < config.min_interval_hours * 3600:
                        continue
                
                # Send alert
                try:
                    alert_history = self._send_alert(config, alert_data)
                    if alert_history:
                        sent_alerts.append(alert_history)
                        config.last_sent_at = datetime.now()
                        session.add(config)
                except Exception as e:
                    logger.error(f"Error sending alert for config {config.id}: {e}")
            
            session.commit()
            return sent_alerts
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error checking alerts: {e}")
            raise
        finally:
            session.close()
    
    def _send_alert(
        self,
        config: AlertConfig,
        alert_data: Dict[str, Any]
    ) -> Optional[AlertHistory]:
        """Send alert through configured channels."""
        session = self.db.get_session()
        
        try:
            channels = config.get_channels()
            channels_sent = []
            
            # Create alert history record
            alert_history = AlertHistory(
                alert_config_id=config.id,
                run_id=config.run_id,
                alert_type=alert_data.get('type', 'custom'),
                level=alert_data.get('level', 'info'),
                message=alert_data.get('message', ''),
                sent_at=datetime.now()
            )
            alert_history.set_data(alert_data.get('data', {}))
            
            # Send via each channel
            for channel in channels:
                try:
                    if channel == 'email' and config.user_email:
                        self._send_email(config.user_email, alert_data)
                        channels_sent.append('email')
                    elif channel == 'sms' and config.user_phone:
                        self._send_sms(config.user_phone, alert_data)
                        channels_sent.append('sms')
                    elif channel == 'in_app':
                        # In-app alerts are just stored
                        channels_sent.append('in_app')
                except Exception as e:
                    logger.error(f"Error sending alert via {channel}: {e}")
                    alert_history.error_message = str(e)
            
            alert_history.channels_sent = json.dumps(channels_sent)
            alert_history.delivered = len(channels_sent) > 0
            
            session.add(alert_history)
            session.commit()
            session.refresh(alert_history)
            
            return alert_history
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error in _send_alert: {e}")
            return None
        finally:
            session.close()
    
    def _send_email(self, recipient: str, alert_data: Dict[str, Any]):
        """Send email alert."""
        if not self.smtp_config:
            logger.warning("SMTP not configured, skipping email")
            return
        
        try:
            msg = MIMEMultipart()
            msg['From'] = self.smtp_config.get('from', self.smtp_config.get('username'))
            msg['To'] = recipient
            msg['Subject'] = f"Portfolio Alert: {alert_data.get('type', 'Alert').replace('_', ' ').title()}"
            
            # Create email body
            body = f"""
Portfolio Alert Notification
============================

Type: {alert_data.get('type', 'Unknown').replace('_', ' ').title()}
Level: {alert_data.get('level', 'info').upper()}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

{alert_data.get('message', 'No message provided')}

"""
            if alert_data.get('value') is not None:
                body += f"Value: {alert_data.get('value'):.2%}\n"
            
            if alert_data.get('data'):
                body += f"\nAdditional Data:\n{json.dumps(alert_data.get('data'), indent=2)}\n"
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            with smtplib.SMTP(
                self.smtp_config.get('host', 'localhost'),
                self.smtp_config.get('port', 587)
            ) as server:
                if self.smtp_config.get('use_tls', True):
                    server.starttls()
                
                if self.smtp_config.get('username'):
                    server.login(
                        self.smtp_config.get('username'),
                        self.smtp_config.get('password', '')
                    )
                
                server.send_message(msg)
                logger.info(f"Email sent to {recipient}")
                
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            raise
    
    def _send_sms(self, phone: str, alert_data: Dict[str, Any]):
        """Send SMS alert (placeholder - requires SMS service integration)."""
        # TODO: Integrate with Twilio or similar service
        logger.warning(f"SMS not yet implemented. Would send to {phone}: {alert_data.get('message')}")
    
    def get_alert_history(
        self,
        run_id: Optional[str] = None,
        alert_type: Optional[str] = None,
        limit: int = 100
    ) -> List[AlertHistory]:
        """Get alert history."""
        session = self.db.get_session()
        try:
            query = session.query(AlertHistory)
            
            if run_id:
                query = query.filter_by(run_id=run_id)
            if alert_type:
                query = query.filter_by(alert_type=alert_type)
            
            return query.order_by(AlertHistory.sent_at.desc()).limit(limit).all()
        finally:
            session.close()
    
    def get_alert_configs(
        self,
        run_id: Optional[str] = None,
        user_email: Optional[str] = None
    ) -> List[AlertConfig]:
        """Get alert configurations."""
        session = self.db.get_session()
        try:
            query = session.query(AlertConfig)
            
            if run_id:
                query = query.filter_by(run_id=run_id)
            if user_email:
                query = query.filter_by(user_email=user_email)
            
            return query.all()
        finally:
            session.close()
