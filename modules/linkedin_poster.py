"""
Stage 4 — LinkedIn Poster
Handles both IMAGE and VIDEO posts.

IMAGE: uses legacy assets API (unchanged)
VIDEO: uses LinkedIn Video API with 3-step upload:
       1. Initialize upload
       2. Upload video chunks
       3. Finalize upload
       Then publish with VIDEO media category
"""

import os
import time
import logging
import requests
from pathlib import Path

log = logging.getLogger(__name__)

TOKEN      = os.getenv("LINKEDIN_ACCESS_TOKEN", "")
PERSON_URN = os.getenv("LINKEDIN_PERSON_URN",   "")

MAX_IMAGE_SIZE_MB = 4
MAX_DIMENSION     = 1920


def _auth_headers():
    return {
        "Authorization":             f"Bearer {TOKEN}",
        "Content-Type":              "application/json",
        "X-Restli-Protocol-Version": "2.0.0"
    }


def _is_video(file_path: str) -> bool:
    return str(file_path).lower().endswith((".mp4", ".mov", ".avi"))


def _resize_if_needed(image_path: str) -> str:
    try:
        size_mb = Path(image_path).stat().st_size / (1024 * 1024)
        if size_mb <= MAX_IMAGE_SIZE_MB:
            return image_path
        log.info(f"   Image too large ({size_mb:.1f}MB) — resizing...")
        from PIL import Image
        img = Image.open(image_path)
        img.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.LANCZOS)
        resized_path = image_path.replace(".jpg", "_resized.jpg")
        img.save(resized_path, "JPEG", quality=85, optimize=True)
        new_size_mb = Path(resized_path).stat().st_size / (1024 * 1024)
        log.info(f"   Resized to {img.size[0]}x{img.size[1]}px ({new_size_mb:.1f}MB)")
        return resized_path
    except Exception as e:
        log.warning(f"   Resize failed ({e}) — using original")
        return image_path


def post_to_linkedin(post_text: str,
                     media_path: str | None) -> tuple[bool, str]:
    if not TOKEN or not PERSON_URN:
        log.error("LinkedIn credentials not configured.")
        return False, ""

    if not media_path:
        log.warning("Posting without media (text only).")
        return _publish_text(post_text)

    if _is_video(media_path):
        log.info(f"   Detected video file — using Video API")
        video_urn = _upload_video(media_path)
        if not video_urn:
            log.error("   Video upload failed — aborting post.")
            return False, ""
        return _publish_video(post_text, video_urn)
    else:
        media_path = _resize_if_needed(media_path)
        image_urn  = _upload_image(media_path)
        if not image_urn:
            log.warning("   Image upload failed — posting text only.")
        return _publish_image(post_text, image_urn)


# ── VIDEO UPLOAD (3 steps) ────────────────────────────────────────────────────

def _upload_video(video_path: str) -> str | None:
    """
    LinkedIn Video Upload — 3 steps:
    1. Initialize upload → get uploadUrl + video URN
    2. Upload video binary in one PUT request
    3. Finalize upload
    """
    try:
        file_size = Path(video_path).stat().st_size
        log.info(f"   Uploading video: {Path(video_path).name} ({file_size/1024/1024:.1f}MB)")

        # Step 1 — Initialize upload
        init_r = requests.post(
            "https://api.linkedin.com/rest/videos?action=initializeUpload",
            headers={
                "Authorization":             f"Bearer {TOKEN}",
                "Content-Type":              "application/json",
                "X-Restli-Protocol-Version": "2.0.0",
                "LinkedIn-Version":          "202304"
            },
            json={
                "initializeUploadRequest": {
                    "owner":          PERSON_URN,
                    "fileSizeBytes":  file_size,
                    "uploadCaptions": False,
                    "uploadThumbnail": False
                }
            },
            timeout=30
        )
        init_r.raise_for_status()
        init_data  = init_r.json().get("value", {})
        upload_url = init_data.get("uploadInstructions", [{}])[0].get("uploadUrl")
        video_urn  = init_data.get("video")

        if not upload_url or not video_urn:
            log.error(f"   Video init failed — response: {init_r.json()}")
            return None

        log.info(f"   Video URN: {video_urn}")

        # Step 2 — Upload binary
        with open(video_path, "rb") as f:
            video_data = f.read()

        upload_r = requests.put(
            upload_url,
            headers={
                "Authorization": f"Bearer {TOKEN}",
                "Content-Type":  "application/octet-stream"
            },
            data=video_data,
            timeout=120
        )
        upload_r.raise_for_status()
        etag = upload_r.headers.get("ETag", "")
        log.info(f"   Video binary uploaded — ETag: {etag}")

        # Step 3 — Finalize upload
        final_r = requests.post(
            "https://api.linkedin.com/rest/videos?action=finalizeUpload",
            headers={
                "Authorization":             f"Bearer {TOKEN}",
                "Content-Type":              "application/json",
                "X-Restli-Protocol-Version": "2.0.0",
                "LinkedIn-Version":          "202304"
            },
            json={
                "finalizeUploadRequest": {
                    "video":  video_urn,
                    "uploadToken": "",
                    "uploadedPartIds": [etag] if etag else []
                }
            },
            timeout=30
        )
        final_r.raise_for_status()
        log.info(f"   Video upload finalized")

        # Wait for LinkedIn to process video (usually 5-15 seconds)
        log.info("   Waiting 10s for LinkedIn to process video...")
        time.sleep(10)

        return video_urn

    except Exception as e:
        log.error(f"   Video upload failed: {e}")
        return None


def _publish_video(text: str, video_urn: str) -> tuple[bool, str]:
    """Publish post with video using ugcPosts API."""
    try:
        r = requests.post(
            "https://api.linkedin.com/v2/ugcPosts",
            headers=_auth_headers(),
            json={
                "author":         PERSON_URN,
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary":    {"text": text},
                        "shareMediaCategory": "VIDEO",
                        "media": [{
                            "status": "READY",
                            "media":   video_urn,
                            "title":  {"text": ""}
                        }]
                    }
                },
                "visibility": {
                    "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
                }
            },
            timeout=30
        )
        r.raise_for_status()
        post_id = r.headers.get("X-RestLi-Id", "")
        log.info(f"   Video post published: {post_id}")
        return True, post_id

    except Exception as e:
        log.error(f"   Video publish failed: {e}")
        if hasattr(e, 'response') and e.response is not None:
            log.error(f"   Response: {e.response.text[:300]}")
        return False, ""


# ── IMAGE UPLOAD (unchanged) ──────────────────────────────────────────────────

def _upload_image(image_path: str) -> str | None:
    try:
        r = requests.post(
            "https://api.linkedin.com/v2/assets?action=registerUpload",
            headers=_auth_headers(),
            json={
                "registerUploadRequest": {
                    "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
                    "owner":   PERSON_URN,
                    "serviceRelationships": [{
                        "relationshipType": "OWNER",
                        "identifier":       "urn:li:userGeneratedContent"
                    }]
                }
            },
            timeout=15
        )
        r.raise_for_status()
        data       = r.json()
        upload_url = data["value"]["uploadMechanism"][
            "com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"
        ]["uploadUrl"]
        asset_urn  = data["value"]["asset"]

        for attempt in range(1, 4):
            try:
                with open(image_path, "rb") as f:
                    r2 = requests.put(
                        upload_url,
                        headers={
                            "Authorization": f"Bearer {TOKEN}",
                            "Content-Type":  "image/jpeg"
                        },
                        data=f,
                        timeout=60
                    )
                r2.raise_for_status()
                log.info(f"   Image uploaded: {asset_urn}")
                return asset_urn
            except Exception as e:
                log.warning(f"   Upload attempt {attempt}/3 failed: {e}")
                if attempt < 3:
                    time.sleep(3)

        log.error("   All upload attempts failed.")
        return None

    except Exception as e:
        log.error(f"Image upload failed: {e}")
        return None


def _publish_image(text: str, image_urn: str | None) -> tuple[bool, str]:
    try:
        share_content = {
            "shareCommentary":    {"text": text},
            "shareMediaCategory": "IMAGE" if image_urn else "NONE"
        }
        if image_urn:
            share_content["media"] = [{
                "status":      "READY",
                "description": {"text": ""},
                "media":        image_urn,
                "title":       {"text": ""}
            }]

        r = requests.post(
            "https://api.linkedin.com/v2/ugcPosts",
            headers=_auth_headers(),
            json={
                "author":         PERSON_URN,
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": share_content
                },
                "visibility": {
                    "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
                }
            },
            timeout=15
        )
        r.raise_for_status()
        post_id = r.headers.get("X-RestLi-Id", "unknown")
        return True, post_id

    except Exception as e:
        log.error(f"LinkedIn publish failed: {e}")
        return False, ""


def _publish_text(text: str) -> tuple[bool, str]:
    return _publish_image(text, None)
