"""
Video Maker — D-ID Talks API
Generates a talking head video using Rahul's photo and a script.
Used every Monday instead of the regular image post.

API: D-ID Talks API (not Agents API)
Free tier: 5 videos per month
"""

import os
import time
import logging
import requests
from pathlib import Path
from datetime import datetime

log = logging.getLogger(__name__)

VIDEO_DIR = Path("videos")
VIDEO_DIR.mkdir(exist_ok=True)

DID_API_KEY   = os.getenv("DID_API_KEY", "")
DID_AGENT_ID  = os.getenv("DID_AGENT_ID", "v2_agt_kMlGaY2G")

# D-ID API endpoints
DID_BASE      = "https://api.d-id.com"
TALKS_URL     = f"{DID_BASE}/talks"

# Voice settings — natural English male voice
VOICE_ID      = "en-US-GuyNeural"   # Microsoft natural male voice
VOICE_STYLE   = "Newscast"          # professional news delivery style


def generate_video(script: str, topic: str) -> str | None:
    """
    Generate a talking head video using D-ID Talks API.
    Returns path to downloaded video file, or None if failed.

    Steps:
    1. Create a talk (POST /talks) with script + agent photo
    2. Poll until status = done
    3. Download the video file
    4. Return local path
    """
    if not DID_API_KEY:
        log.error("   DID_API_KEY not set in config")
        return None

    headers = {
        "Authorization": f"Basic {DID_API_KEY}",
        "Content-Type":  "application/json",
        "Accept":        "application/json",
    }

    # Step 1 — Get agent's source image URL
    photo_url = _get_agent_photo_url(headers)
    if not photo_url:
        log.error("   Could not get photo URL from D-ID agent")
        return None

    log.info(f"   D-ID: creating talk for topic '{topic}'...")
    log.info(f"   Script length: {len(script.split())} words")

    # Step 2 — Create the talk
    payload = {
        "source_url": photo_url,
        "script": {
            "type":     "text",
            "input":    script,
            "provider": {
                "type":     "microsoft",
                "voice_id": VOICE_ID,
                "voice_config": {
                    "style": VOICE_STYLE
                }
            }
        },
        "config": {
            "fluent":       True,
            "pad_audio":    0.0,
            "stitch":       True,
        }
    }

    try:
        r = requests.post(TALKS_URL, json=payload, headers=headers, timeout=30)
        r.raise_for_status()
        talk_id = r.json().get("id")
        if not talk_id:
            log.error(f"   D-ID: no talk ID returned — {r.json()}")
            return None
        log.info(f"   D-ID: talk created — ID: {talk_id}")
    except Exception as e:
        log.error(f"   D-ID create talk failed: {e}")
        return None

    # Step 3 — Poll until done (max 3 minutes)
    video_url = _poll_until_done(talk_id, headers, max_wait=180)
    if not video_url:
        log.error("   D-ID: video generation timed out or failed")
        return None

    # Step 4 — Download video
    video_path = _download_video(video_url, topic)
    if video_path:
        log.info(f"   D-ID: video saved to {video_path}")
    return video_path


def _get_agent_photo_url(headers: dict) -> str | None:
    """Get the source image URL from the D-ID agent."""
    try:
        r = requests.get(
            f"{DID_BASE}/agents/{DID_AGENT_ID}",
            headers=headers,
            timeout=15
        )
        r.raise_for_status()
        data = r.json()

        # Try different fields where photo URL might be
        photo_url = (
            data.get("presenter", {}).get("source_url") or
            data.get("source_url") or
            data.get("presenter_id")
        )

        if photo_url:
            log.info(f"   D-ID: got photo URL from agent")
            return photo_url

        # If no URL found log the response to help debug
        log.warning(f"   D-ID agent response keys: {list(data.keys())}")
        return None

    except Exception as e:
        log.error(f"   D-ID get agent failed: {e}")
        return None


def _poll_until_done(talk_id: str, headers: dict,
                     max_wait: int = 180) -> str | None:
    """Poll D-ID until video is ready. Returns video URL or None."""
    start   = time.time()
    attempt = 0

    while time.time() - start < max_wait:
        attempt += 1
        try:
            r = requests.get(
                f"{TALKS_URL}/{talk_id}",
                headers=headers,
                timeout=15
            )
            r.raise_for_status()
            data   = r.json()
            status = data.get("status", "")

            log.info(f"   D-ID status (attempt {attempt}): {status}")

            if status == "done":
                return data.get("result_url")
            elif status in ["error", "rejected"]:
                log.error(f"   D-ID failed with status: {status}")
                log.error(f"   D-ID error details: {data.get('error', {})}")
                return None

            # Wait before next check
            time.sleep(8)

        except Exception as e:
            log.warning(f"   D-ID poll error: {e}")
            time.sleep(8)

    log.error(f"   D-ID timed out after {max_wait}s")
    return None


def _download_video(video_url: str, topic: str) -> str | None:
    """Download the generated video to local storage."""
    try:
        date      = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_topic = topic.lower().replace(" ", "_")[:20]
        filename  = f"{date}_{safe_topic}.mp4"
        filepath  = VIDEO_DIR / filename

        log.info(f"   Downloading video from D-ID...")
        r = requests.get(video_url, timeout=120, stream=True)
        r.raise_for_status()

        with open(filepath, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)

        size_mb = filepath.stat().st_size / (1024 * 1024)
        log.info(f"   Video downloaded: {filename} ({size_mb:.1f}MB)")
        return str(filepath)

    except Exception as e:
        log.error(f"   Video download failed: {e}")
        return None
