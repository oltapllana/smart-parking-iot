#!/usr/bin/env python3
"""
SMS Notification Service
Sends short SMS alerts via Twilio for critical parking conditions.
Silently disabled when Twilio credentials are not configured.
"""
import sys
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

from datetime import datetime, timedelta

try:
    from twilio.rest import Client as TwilioClient
    _TWILIO_AVAILABLE = True
except ImportError:
    _TWILIO_AVAILABLE = False

from alert_config import (
    TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN,
    TWILIO_FROM_NUMBER, TWILIO_TO_NUMBER,
    SMS_ENABLED, SMS_COOLDOWN_MINUTES,
)


class SmsNotificationService:
    """
    Wraps Twilio to send short parking alert SMS messages.
    Enforces a per-type cooldown so the same alert does not flood.
    """

    def __init__(self):
        self._client = None
        self._last_sent: dict[str, datetime] = {}  # alert_type -> last send time

        if SMS_ENABLED and _TWILIO_AVAILABLE:
            try:
                self._client = TwilioClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
                print("📱 SMS notification service ready (Twilio)")
            except Exception as e:
                print(f"⚠️  Twilio init failed: {e} — SMS disabled")
        elif not _TWILIO_AVAILABLE:
            print("📱 SMS disabled: twilio package not installed (pip install twilio)")
        else:
            print("📱 SMS disabled: Twilio credentials not set in alert_config.py / env vars")

    @property
    def enabled(self) -> bool:
        return self._client is not None

    @property
    def status(self) -> dict:
        return {
            "enabled": self.enabled,
            "twilio_available": _TWILIO_AVAILABLE,
            "credentials_configured": SMS_ENABLED,
        }

    def _format_critical_body(self, alert_type: str, message: str, occupancy: float, lot_id: str | None = None) -> str:
        prefix = f"[{lot_id}] " if lot_id else ""
        return f"PARKING ALERT {prefix}{occupancy:.0f}% full. {message[:90]}"

    def _in_cooldown(self, alert_type: str) -> bool:
        last = self._last_sent.get(alert_type)
        if last is None:
            return False
        return datetime.now() - last < timedelta(minutes=SMS_COOLDOWN_MINUTES)

    def send_critical_alert(self, alert_type: str, message: str, occupancy: float, lot_id: str | None = None) -> bool:
        """
        Send an SMS for a critical alert.
        Returns True if the message was sent, False otherwise.
        """
        if not self.enabled:
            return False
        if self._in_cooldown(alert_type):
            return False

        body = self._format_critical_body(alert_type, message, occupancy, lot_id)

        try:
            self._client.messages.create(
                body=body,
                from_=TWILIO_FROM_NUMBER,
                to=TWILIO_TO_NUMBER,
            )
            self._last_sent[alert_type] = datetime.now()
            print(f"📱 SMS sent: {body}")
            return True
        except Exception as e:
            print(f"⚠️  SMS send failed: {e}")
            return False

    def preview_critical_alert(self, alert_type: str, message: str, occupancy: float, lot_id: str | None = None) -> str:
        return self._format_critical_body(alert_type, message, occupancy, lot_id)

    def send_warning(self, message: str) -> bool:
        """Send a generic warning SMS (no cooldown key — use sparingly)."""
        if not self.enabled:
            return False
        try:
            self._client.messages.create(
                body=message[:160],
                from_=TWILIO_FROM_NUMBER,
                to=TWILIO_TO_NUMBER,
            )
            print(f"📱 SMS sent: {message[:160]}")
            return True
        except Exception as e:
            print(f"⚠️  SMS send failed: {e}")
            return False

    def send_test_message(self, lot_id: str = "LOT-TEST-001", occupancy: float = 92.0) -> dict:
        """Send a test SMS using the same path as a critical alert."""
        message = "Test SMS from Smart Parking IoT. Critical alert pipeline is working."
        body = self._format_critical_body("test", message, occupancy, lot_id)

        if not self.enabled:
            return {
                "sent": False,
                "reason": "SMS disabled",
                "body": body,
                "status": self.status,
            }

        try:
            self._client.messages.create(
                body=body,
                from_=TWILIO_FROM_NUMBER,
                to=TWILIO_TO_NUMBER,
            )
            print(f"📱 Test SMS sent: {body}")
            return {
                "sent": True,
                "body": body,
                "status": self.status,
            }
        except Exception as e:
            print(f"⚠️  Test SMS send failed: {e}")
            return {
                "sent": False,
                "reason": str(e),
                "body": body,
                "status": self.status,
            }
