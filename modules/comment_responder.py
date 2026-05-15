"""
Comment Auto-Responder
Fetches new comments on recent LinkedIn posts.
Generates reply suggestions using ChatGPT.
Sends them to Telegram for your one-tap approval.

HOW IT WORKS:
1. Fetches comments on your last 10 posts via LinkedIn API
2. Filters only NEW comments (not yet replied to)
3. ChatGPT generates a warm, professional reply as Rahul
4. Sends to Telegram: comment + suggested reply + approve/skip buttons
5. You tap Approve - bot posts the reply
   You tap Skip - bot moves on

IMPORTANT: Run this separately from main.py
Command: python respond_comments.py
"""

import os
import json
import logging
import requests
from datetime import datetime
from openai import OpenAI
from modules.history_tracker import load_history

log = logging.getLogger(__name__)

LINKEDIN_TOKEN  = os.getenv("LINKEDIN_ACCESS_TOKEN", "")
PERSON_URN      = os.getenv("LINKEDIN_PERSON_URN",   "")
OPENAI_API_KEY  = os.getenv("OPENAI_API_KEY",        "")
TELEGRAM_TOKEN  = os.getenv("TELEGRAM_BOT_TOKEN",    "")
TELEGRAM_CHAT   = os.getenv("TELEGRAM_CHAT_ID",      "")

REPLIED_FILE    = "replied_comments.json"

REPLY_PROMPT = """You are Rahul, a Data and Business Analyst pursuing an MSc in Business Analytics at Dublin Business School. You are replying to a comment on your LinkedIn post.

Write a warm, genuine, professional reply that:
- Acknowledges their specific point
- Adds a brief insight or asks a follow-up question
- Sounds like a real person, not a bot
- Is 2 to 4 sentences maximum
- Never uses dashes, bullet points or hashtags

Post topic: {topic}
Original post preview: {post_preview}
Comment from {commenter}: {comment_text}

Write only the reply text, nothing else."""


def load_replied() -> set:
    try:
        with open(REPLIED_FILE) as f:
            return set(json.load(f))
    except Exception:
        return set()


def save_replied(comment_id: str):
    replied = load_replied()
    replied.add(comment_id)
    with open(REPLIED_FILE, "w") as f:
        json.dump(list(replied), f)


def get_recent_post_ids() -> list[dict]:
    """Get post IDs from last 10 posts in history."""
    history = load_history()
    posts   = history.get("posts", [])[-10:]
    return [
        {"post_id": p.get("post_id", ""), "subject": p.get("subject", ""),
         "content": p.get("content", "")[:200]}
        for p in posts
        if p.get("post_id") and p.get("posted")
    ]


def fetch_comments(post_id: str) -> list[dict]:
    """Fetch comments on a LinkedIn post."""
    if not LINKEDIN_TOKEN:
        return []
    try:
        # Extract the numeric ID from the URN
        numeric_id = post_id.split(":")[-1] if ":" in post_id else post_id

        r = requests.get(
            f"https://api.linkedin.com/v2/socialActions/urn:li:share:{numeric_id}/comments",
            headers={
                "Authorization": f"Bearer {LINKEDIN_TOKEN}",
                "X-Restli-Protocol-Version": "2.0.0"
            },
            params={"count": 20},
            timeout=15
        )
        r.raise_for_status()
        elements = r.json().get("elements", [])

        comments = []
        for e in elements:
            comment_id   = e.get("$URN", "")
            comment_text = e.get("message", {}).get("text", "")
            author_urn   = e.get("actor", "")
            author_name  = _get_author_name(author_urn)

            if comment_text and comment_id:
                comments.append({
                    "id":      comment_id,
                    "text":    comment_text,
                    "author":  author_name,
                    "post_id": post_id
                })
        return comments

    except Exception as e:
        log.warning(f"   Failed to fetch comments for {post_id}: {e}")
        return []


def _get_author_name(author_urn: str) -> str:
    """Try to get author display name — falls back to 'a connection'."""
    try:
        person_id = author_urn.split(":")[-1]
        r = requests.get(
            f"https://api.linkedin.com/v2/people/{person_id}",
            headers={"Authorization": f"Bearer {LINKEDIN_TOKEN}"},
            params={"projection": "(localizedFirstName,localizedLastName)"},
            timeout=10
        )
        if r.status_code == 200:
            data = r.json()
            return f"{data.get('localizedFirstName', '')} {data.get('localizedLastName', '')}".strip()
    except Exception:
        pass
    return "a connection"


def generate_reply(comment: str, topic: str, post_preview: str, commenter: str) -> str:
    """Generate a reply using ChatGPT."""
    if not OPENAI_API_KEY:
        return f"Thank you for your thoughtful comment! Really appreciate you engaging with this. What has been your experience with {topic}?"

    try:
        client   = OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": REPLY_PROMPT.format(
                    topic=topic,
                    post_preview=post_preview,
                    commenter=commenter,
                    comment_text=comment
                )
            }],
            temperature=0.8,
            max_tokens=150
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        log.warning(f"   ChatGPT reply generation failed: {e}")
        return f"Thank you for engaging with this post! Really appreciate your perspective on {topic}."


def post_reply(post_id: str, comment_id: str, reply_text: str) -> bool:
    """Post a reply to a LinkedIn comment."""
    try:
        numeric_id = post_id.split(":")[-1] if ":" in post_id else post_id
        r = requests.post(
            f"https://api.linkedin.com/v2/socialActions/urn:li:share:{numeric_id}/comments",
            headers={
                "Authorization":             f"Bearer {LINKEDIN_TOKEN}",
                "Content-Type":              "application/json",
                "X-Restli-Protocol-Version": "2.0.0"
            },
            json={
                "actor":   PERSON_URN,
                "message": {"text": reply_text},
                "parentComment": comment_id
            },
            timeout=15
        )
        r.raise_for_status()
        return True
    except Exception as e:
        log.error(f"   Failed to post reply: {e}")
        return False


def send_for_approval(comment_data: dict, reply_text: str) -> bool:
    """
    Send comment + reply to Telegram for approval.
    Returns True if user approves, False if skipped.
    Simple implementation: sends message and waits for reply.
    """
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT:
        log.warning("Telegram not configured.")
        return False

    message = (
        f"<b>New LinkedIn Comment</b>\n\n"
        f"<b>Topic:</b> {comment_data.get('topic', 'Unknown')}\n"
        f"<b>From:</b> {comment_data.get('author', 'Unknown')}\n\n"
        f"<b>Comment:</b>\n{comment_data.get('text', '')}\n\n"
        f"<b>Suggested reply:</b>\n{reply_text}\n\n"
        f"Reply <b>YES</b> to post this reply\n"
        f"Reply <b>NO</b> to skip"
    )

    try:
        # Send message
        r = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={
                "chat_id":    TELEGRAM_CHAT,
                "text":       message,
                "parse_mode": "HTML"
            },
            timeout=15
        )
        r.raise_for_status()

        # Wait for user response (poll for 60 seconds)
        import time
        last_update_id = _get_last_update_id()
        for _ in range(12):   # check every 5 seconds for 60 seconds
            time.sleep(5)
            response_text = _check_telegram_response(last_update_id)
            if response_text:
                if response_text.upper().strip() == "YES":
                    return True
                elif response_text.upper().strip() == "NO":
                    return False

        log.info("   No response received in 60s — skipping comment.")
        return False

    except Exception as e:
        log.error(f"   Telegram approval failed: {e}")
        return False


def _get_last_update_id() -> int:
    try:
        r = requests.get(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates",
            params={"limit": 1, "offset": -1},
            timeout=10
        )
        updates = r.json().get("result", [])
        if updates:
            return updates[-1].get("update_id", 0)
    except Exception:
        pass
    return 0


def _check_telegram_response(after_update_id: int) -> str | None:
    try:
        r = requests.get(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates",
            params={"offset": after_update_id + 1, "limit": 5, "timeout": 5},
            timeout=15
        )
        updates = r.json().get("result", [])
        for update in updates:
            text = update.get("message", {}).get("text", "")
            if text.upper().strip() in ["YES", "NO"]:
                return text
    except Exception:
        pass
    return None


def run_comment_responder():
    """
    Main function — fetch all new comments, generate replies,
    send for Telegram approval, post approved replies.
    """
    log.info("=" * 50)
    log.info("Comment Responder — Starting")
    log.info("=" * 50)

    replied    = load_replied()
    posts      = get_recent_post_ids()
    new_count  = 0
    sent_count = 0

    log.info(f"Checking comments on {len(posts)} recent posts...")

    for post in posts:
        post_id  = post["post_id"]
        subject  = post["subject"]
        preview  = post["content"]
        comments = fetch_comments(post_id)

        for comment in comments:
            comment_id = comment["id"]

            # Skip already replied
            if comment_id in replied:
                continue

            new_count += 1
            log.info(f"   New comment from {comment['author']}: {comment['text'][:60]}...")

            # Generate reply
            reply = generate_reply(
                comment=comment["text"],
                topic=subject,
                post_preview=preview,
                commenter=comment["author"]
            )

            # Send for approval
            comment["topic"] = subject
            approved = send_for_approval(comment, reply)

            if approved:
                success = post_reply(post_id, comment_id, reply)
                if success:
                    save_replied(comment_id)
                    sent_count += 1
                    log.info(f"   Reply posted successfully.")
            else:
                log.info(f"   Reply skipped.")

    log.info(f"Comment responder complete. Found {new_count} new, replied to {sent_count}.")


if __name__ == "__main__":
    import config
    run_comment_responder()
