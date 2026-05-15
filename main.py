"""
LinkedIn AI Bot — Final Version
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MONDAY  → AI Avatar Video (D-ID) + script
Tue-Sun → Normal image post (DALL-E / Pollinations)

Stage 1 → Gemini Flash        : Real trending news
Stage 2 → ChatGPT             : Writes post or video script
Stage 3 → DALL-E 3 / D-ID     : Image or video
Stage 4 → LinkedIn API        : Publishes post
Stage 5 → Post Guard          : Records to prevent repeats
Stage 6 → Telegram            : Sends notification

PROTECTIONS:
1. Wait up to 60s for internet before starting
2. Skip posting if no real news available
3. Skip posting if no image/video generated
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import config
import os
import socket
import time
import logging
from datetime import datetime
from modules.trend_selector      import get_trending_topic
from modules.content_writer      import generate_post_content
from modules.video_script_writer import generate_video_script
from modules.image_provider      import get_image_for_post
from modules.video_maker         import generate_video
from modules.linkedin_poster     import post_to_linkedin
from modules.history_tracker     import save_post
from modules.telegram_notifier   import send_notification
from modules.token_monitor       import check_token_expiry
from modules.post_guard          import record_post, is_content_duplicate, get_summary

os.makedirs("logs",   exist_ok=True)
os.makedirs("images", exist_ok=True)
os.makedirs("videos", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/bot.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

STATIC_FALLBACK_PHRASES = [
    "professionals need to know today",
    "key developments in",
    "caught my attention this week and I wanted to share it",
]


def _wait_for_internet(max_wait_seconds=60):
    log.info("   Checking internet connectivity...")
    for attempt in range(max_wait_seconds // 5):
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            log.info("   Internet connection confirmed.")
            return True
        except OSError:
            waited = (attempt + 1) * 5
            log.warning(f"   No internet yet — waiting 5s (attempt {attempt+1}, {waited}s elapsed)...")
            time.sleep(5)
    log.error(f"   No internet after {max_wait_seconds}s.")
    return False


def _is_static_fallback(headline):
    return any(phrase in headline.lower() for phrase in STATIC_FALLBACK_PHRASES)


def _is_monday():
    return datetime.now().weekday() == 0


def run_pipeline(force_video=False):
    log.info("=" * 60)
    log.info("LinkedIn Bot — Pipeline Start")
    log.info(f"    {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log.info("=" * 60)

    post_data = {}
    is_video  = force_video or _is_monday()
    log.info(f"   Mode: {'VIDEO (Monday)' if is_video else 'IMAGE (Normal day)'}")

    try:
        # Internet check
        if not _wait_for_internet(60):
            log.error("Aborting — no internet connection.")
            send_notification(False, {"subject": "No Internet", "trend": "",
                "content": "Bot aborted — no internet at startup.", "image_source": "none", "post_id": ""})
            return

        # Token check
        log.info("Checking LinkedIn token expiry...")
        check_token_expiry()

        guard_summary = get_summary()
        log.info(f"Post Guard: {guard_summary['blocked_subjects_count']} subjects blocked, "
                 f"{guard_summary['blocked_headlines_count']} headlines blocked, "
                 f"{guard_summary['total_fingerprints']} unique posts ever")

        # Stage 1 — Real trending news
        log.info("Stage 1 - Gemini: Fetching trending news...")
        trend_data    = get_trending_topic()
        subject       = trend_data.get("subject",       "Data Analytics")
        news_headline = trend_data.get("news_headline",  trend_data.get("trend", ""))
        image_style   = trend_data.get("image_style",   "")
        image_kw      = trend_data.get("image_keywords", "data technology")

        log.info(f"   Subject : {subject}")
        log.info(f"   Headline: {news_headline[:80]}")

        # Skip if static fallback
        if _is_static_fallback(news_headline):
            log.warning("   Static fallback detected — skipping post.")
            send_notification(False, {"subject": subject, "trend": news_headline,
                "content": "Skipped — no real news available today.", "image_source": "skipped", "post_id": ""})
            return

        # MONDAY: Video pipeline
        if is_video:
            log.info("Stage 2 - ChatGPT: Writing VIDEO SCRIPT...")
            script     = generate_video_script(subject, trend_data)
            post_text  = script
            refined_kw = image_kw
            log.info(f"   Script words : {len(script.split())}")
            log.info(f"   Preview      : {script[:80]}...")

            log.info("Stage 3 - D-ID: Generating avatar video...")
            media_path   = generate_video(script, subject)
            image_source = "D-ID Video"

            if not media_path:
                log.warning("   Video generation failed — skipping post.")
                send_notification(False, {"subject": subject, "trend": news_headline,
                    "content": "Skipped — D-ID video generation failed.", "image_source": "failed", "post_id": ""})
                return

        # NORMAL DAYS: Image pipeline
        else:
            log.info("Stage 2 - ChatGPT: Writing post...")
            post_text, refined_kw = generate_post_content(subject, trend_data)
            log.info(f"   Words   : {len(post_text.split())}")
            log.info(f"   Preview : {post_text[:80]}...")

            if is_content_duplicate(post_text):
                log.warning("Content duplicate — regenerating...")
                post_text, refined_kw = generate_post_content(subject, trend_data)
                if is_content_duplicate(post_text):
                    log.error("Duplicate on regeneration — aborting.")
                    return

            log.info("Stage 3 - Image: Generating...")
            media_path, image_source = get_image_for_post(
                image_keywords=refined_kw or image_kw,
                topic=subject,
                image_style=image_style,
                post_summary=post_text[:300],
                news_headline=news_headline
            )
            log.info(f"   Source  : {image_source}")

            if not media_path or image_source == "none":
                log.warning("   No image — skipping post.")
                send_notification(False, {"subject": subject, "trend": news_headline,
                    "content": "Skipped — image generation failed.", "image_source": "failed", "post_id": ""})
                return

        # Stage 4 — LinkedIn publish
        log.info("Stage 4 - LinkedIn: Publishing...")
        success, post_id = post_to_linkedin(post_text, media_path)

        post_data = {
            "date":         datetime.now().isoformat(),
            "subject":      subject,
            "trend":        news_headline,
            "content":      post_text,
            "word_count":   len(post_text.split()),
            "image_source": image_source,
            "image_path":   str(media_path or ""),
            "posted":       success,
            "post_id":      post_id
        }
        save_post(post_data)

        record_post(subject=subject, headline=news_headline, post_text=post_text)
        log.info("Stage 5 - Post Guard: Recorded.")

        log.info("Stage 6 - Telegram: Sending notification...")
        send_notification(success, post_data)

        if success:
            log.info(f"Done! Post ID: {post_id}")
        else:
            log.warning("LinkedIn publish failed — check token.")

    except Exception as e:
        log.error(f"Pipeline crashed: {e}", exc_info=True)
        send_notification(False, {"subject": post_data.get("subject","Unknown"),
            "trend": post_data.get("trend",""), "content": f"Pipeline crashed: {str(e)}",
            "image_source": "none", "post_id": ""})


if __name__ == "__main__":
    import sys
    force_video = "--video" in sys.argv
    run_pipeline(force_video=force_video)
