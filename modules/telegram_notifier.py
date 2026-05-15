"""
Telegram Notifier
Sends a message to your Telegram after every LinkedIn post
Setup: 5 minutes — see instructions below
"""

import os
import logging
import requests

log = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID",   "")

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"


def send_notification(success: bool, post_data: dict):
    """
    Send a Telegram message after a LinkedIn post attempt.
    post_data should contain: subject, trend, content, image_source, post_id
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        log.warning("Telegram credentials not set — skipping notification.")
        return

    message = _build_message(success, post_data)

    try:
        r = requests.post(
            TELEGRAM_API.format(token=TELEGRAM_BOT_TOKEN),
            json={
                "chat_id":    TELEGRAM_CHAT_ID,
                "text":       message,
                "parse_mode": "HTML"
            },
            timeout=15
        )
        r.raise_for_status()
        log.info("✅ Telegram notification sent.")

    except Exception as e:
        log.warning(f"Telegram notification failed: {e}")


def _build_message(success: bool, post_data: dict) -> str:
    from datetime import datetime
    now     = datetime.now().strftime("%d %b %Y at %I:%M %p")
    subject = post_data.get("subject", "Unknown")
    trend   = post_data.get("trend",   "")
    preview = post_data.get("content", "")[:200].replace("<", "").replace(">", "")
    image   = post_data.get("image_source", "none")
    post_id = post_data.get("post_id", "")

    if success:
        return (
            f"✅ <b>LinkedIn Post Published!</b>\n\n"
            f"📅 <b>Date:</b> {now}\n"
            f"📌 <b>Topic:</b> {subject}\n"
            f"📰 <b>Trend:</b> {trend[:120]}\n"
            f"🖼️ <b>Image:</b> {image}\n"
            f"🔗 <b>Post ID:</b> {post_id}\n\n"
            f"📝 <b>Preview:</b>\n{preview}...\n\n"
            f"<i>Your LinkedIn bot is working perfectly 🚀</i>"
        )
    else:
        return (
            f"❌ <b>LinkedIn Post FAILED</b>\n\n"
            f"📅 <b>Date:</b> {now}\n"
            f"📌 <b>Topic:</b> {subject}\n"
            f"📰 <b>Trend:</b> {trend[:120]}\n\n"
            f"⚠️ Post was generated but could not be published to LinkedIn.\n"
            f"Please check your LinkedIn token — it may have expired.\n\n"
            f"<i>Check logs\\bot.log for details.</i>"
        )
