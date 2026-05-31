#!/usr/bin/env python3
"""
Alert configuration — thresholds and Twilio credentials.
Set Twilio values via environment variables (recommended) or edit here directly.
SMS is silently disabled when any credential is missing.
"""
import os

# Occupancy thresholds (%)
WARNING_THRESHOLD  = 75
CRITICAL_THRESHOLD = 90

# Zone occupancy threshold to trigger a zone-full alert (%)
ZONE_FULL_THRESHOLD = 95

# Twilio SMS configuration
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN  = os.getenv("TWILIO_AUTH_TOKEN",  "")
TWILIO_FROM_NUMBER = os.getenv("TWILIO_FROM_NUMBER", "")  # e.g. "+1234567890"
TWILIO_TO_NUMBER   = os.getenv("TWILIO_TO_NUMBER",   "")  # verified recipient number

# SMS fires only when all four credentials are present
SMS_ENABLED = all([
    TWILIO_ACCOUNT_SID,
    TWILIO_AUTH_TOKEN,
    TWILIO_FROM_NUMBER,
    TWILIO_TO_NUMBER,
])

# Minimum minutes between repeated SMS for the same alert type
SMS_COOLDOWN_MINUTES = 10
