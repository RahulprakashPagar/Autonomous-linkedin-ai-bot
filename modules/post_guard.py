"""
Post Guard — Bulletproof Deduplication
Tracks every subject and headline the bot has EVER used.
Whether you delete a post on LinkedIn or not, this file remembers.

COOLDOWNS (reduced to prevent 0 fresh headlines issue):
  - Same SUBJECT not repeated within 1 day — allows daily posting
  - Same HEADLINE not repeated within 30 days — no repeats within a month
  - Same CONTENT fingerprint never repeated (ever)
"""

import json
import hashlib
import logging
from datetime import datetime, timedelta
from pathlib import Path

log = logging.getLogger(__name__)

GUARD_FILE             = "post_guard.json"
SUBJECT_COOLDOWN_DAYS  = 1    # same subject blocked for 1 day — allows daily posting
HEADLINE_COOLDOWN_DAYS = 30   # same headline blocked for 30 days — no repeats within a month


def _load() -> dict:
    if Path(GUARD_FILE).exists():
        try:
            with open(GUARD_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"subjects": [], "headlines": [], "fingerprints": []}


def _save(data: dict):
    with open(GUARD_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _fingerprint(text: str) -> str:
    cleaned = " ".join(text.lower().split())
    return hashlib.md5(cleaned[:500].encode()).hexdigest()[:16]


def get_blocked_subjects() -> list[str]:
    """Return subjects in cooldown — must not be used today."""
    data    = _load()
    cutoff  = datetime.now() - timedelta(days=SUBJECT_COOLDOWN_DAYS)
    blocked = []
    for entry in data.get("subjects", []):
        try:
            if datetime.fromisoformat(entry["date"][:19]) >= cutoff:
                if entry["subject"] not in blocked:
                    blocked.append(entry["subject"])
        except Exception:
            continue
    log.info(f"   Blocked subjects (last {SUBJECT_COOLDOWN_DAYS}d): {blocked}")
    return blocked


def get_blocked_headlines() -> list[str]:
    """Return headlines in cooldown — must not be used today."""
    data    = _load()
    cutoff  = datetime.now() - timedelta(days=HEADLINE_COOLDOWN_DAYS)
    blocked = []
    for entry in data.get("headlines", []):
        try:
            if datetime.fromisoformat(entry["date"][:19]) >= cutoff:
                if entry["headline"] not in blocked:
                    blocked.append(entry["headline"])
        except Exception:
            continue
    log.info(f"   Blocked headlines (last {HEADLINE_COOLDOWN_DAYS}d): {len(blocked)} headlines")
    return blocked


def is_content_duplicate(post_text: str) -> bool:
    """Check if this exact content has ever been posted before."""
    data        = _load()
    fingerprint = _fingerprint(post_text)
    if fingerprint in data.get("fingerprints", []):
        log.warning(f"   Content duplicate detected!")
        return True
    return False


def is_headline_blocked(headline: str, blocked_headlines: list[str]) -> bool:
    """Check if headline is too similar to a recently used one."""
    headline_lower = headline.lower()[:80]
    for blocked in blocked_headlines:
        blocked_lower = blocked.lower()[:80]
        if (headline_lower[:60] in blocked_lower or
                blocked_lower[:60] in headline_lower):
            return True
    return False


def record_post(subject: str, headline: str, post_text: str):
    """
    Record a successful post permanently.
    Called after every post regardless of whether you delete it from LinkedIn.
    """
    data        = _load()
    now         = datetime.now().isoformat()
    fingerprint = _fingerprint(post_text)

    data.setdefault("subjects",  []).append({"subject":  subject,  "date": now})
    data.setdefault("headlines", []).append({"headline": headline, "date": now})

    if fingerprint not in data.get("fingerprints", []):
        data.setdefault("fingerprints", []).append(fingerprint)

    # Clean up old entries — keep last 90 days for subjects/headlines
    cutoff = datetime.now() - timedelta(days=90)
    data["subjects"]  = [
        e for e in data["subjects"]
        if datetime.fromisoformat(e["date"][:19]) >= cutoff
    ]
    data["headlines"] = [
        e for e in data["headlines"]
        if datetime.fromisoformat(e["date"][:19]) >= cutoff
    ]

    _save(data)
    log.info(f"   Post Guard: recorded subject='{subject}' headline='{headline[:50]}'")


def get_summary() -> dict:
    """Return summary of what the guard is tracking."""
    data      = _load()
    blocked_s = get_blocked_subjects()
    blocked_h = get_blocked_headlines()
    return {
        "blocked_subjects":         blocked_s,
        "blocked_subjects_count":   len(blocked_s),
        "blocked_headlines_count":  len(blocked_h),
        "total_fingerprints":       len(data.get("fingerprints", [])),
        "total_recorded_subjects":  len(data.get("subjects", [])),
        "total_recorded_headlines": len(data.get("headlines", [])),
    }
