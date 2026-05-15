"""
Token Monitor
Checks LinkedIn token age daily and sends Telegram warning 10 days before expiry.
No more surprise failures.
"""

import os
import logging
import requests
from datetime import datetime, timedelta

log = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID",   "")
LINKEDIN_TOKEN_DATE = os.getenv("LINKEDIN_TOKEN_DATE", "")  # Format: YYYY-MM-DD

TOKEN_VALIDITY_DAYS = 60   # LinkedIn tokens last 60 days
WARNING_DAYS_BEFORE = 10   # Warn 10 days before expiry


def check_token_expiry():
    """
    Check if LinkedIn token is approaching expiry.
    Call this once daily before running the pipeline.
    """
    if not LINKEDIN_TOKEN_DATE:
        log.warning("LINKEDIN_TOKEN_DATE not set in config.py — cannot check token expiry.")
        return

    try:
        token_created = datetime.strptime(LINKEDIN_TOKEN_DATE, "%Y-%m-%d")
        expiry_date   = token_created + timedelta(days=TOKEN_VALIDITY_DAYS)
        days_left     = (expiry_date - datetime.now()).days

        log.info(f"   LinkedIn token expires in {days_left} days ({expiry_date.strftime('%d %b %Y')})")

        if days_left <= 0:
            _send_alert(
                "expired",
                days_left,
                expiry_date.strftime("%d %b %Y")
            )
        elif days_left <= WARNING_DAYS_BEFORE:
            _send_alert(
                "warning",
                days_left,
                expiry_date.strftime("%d %b %Y")
            )
        elif days_left <= 20:
            _send_alert(
                "reminder",
                days_left,
                expiry_date.strftime("%d %b %Y")
            )

    except Exception as e:
        log.warning(f"   Token expiry check failed: {e}")


def _send_alert(alert_type: str, days_left: int, expiry_date: str):
    """Send Telegram alert about token status."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        log.warning("Telegram not configured — cannot send token warning.")
        return

    if alert_type == "expired":
        message = (
            f"<b>LinkedIn Token EXPIRED</b>\n\n"
            f"Your LinkedIn token expired on {expiry_date}.\n"
            f"The bot cannot post until you renew it.\n\n"
            f"<b>Steps to fix:</b>\n"
            f"1. Go to linkedin.com/developers\n"
            f"2. Open your app - Auth tab\n"
            f"3. Generate new token\n"
            f"4. Update LINKEDIN_ACCESS_TOKEN in config.py\n"
            f"5. Update LINKEDIN_TOKEN_DATE to today's date"
        )
    elif alert_type == "warning":
        message = (
            f"<b>LinkedIn Token Expiring Soon</b>\n\n"
            f"Your token expires in <b>{days_left} days</b> on {expiry_date}.\n\n"
            f"<b>Renew now to avoid interruption:</b>\n"
            f"1. Go to linkedin.com/developers\n"
            f"2. Open your app - Auth tab\n"
            f"3. Generate new token\n"
            f"4. Update config.py with new token and today's date"
        )
    else:  # reminder
        message = (
            f"<b>LinkedIn Token Reminder</b>\n\n"
            f"Token expires in {days_left} days on {expiry_date}.\n"
            f"No action needed yet — just a heads up."
        )

    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={
                "chat_id":    TELEGRAM_CHAT_ID,
                "text":       message,
                "parse_mode": "HTML"
            },
            timeout=15
        )
        r.raise_for_status()
        log.info(f"   Token {alert_type} alert sent via Telegram.")
    except Exception as e:
        log.warning(f"   Failed to send token alert: {e}")
