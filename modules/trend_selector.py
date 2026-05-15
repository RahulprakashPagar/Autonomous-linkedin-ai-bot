"""
Stage 1 — Trend Selector
Model  : Google Gemini 1.5 Flash (higher free tier limit than 2.0)
News   : NewsAPI / RSS feeds (real headlines only)

KEY RULES:
- Google Trends removed — was causing 429 errors
- Gemini own knowledge REMOVED — bot never generates fake news
- Only real headlines from NewsAPI are ever used
- If no fresh headlines → static fallback only, no AI invention
- Gemini retry: if 429 wait 30s and try once more before fallback
- gemini-1.5-flash has higher RPM limit than gemini-2.0-flash
"""

import os
import json
import time
import logging
import requests
from modules.news_fetcher  import fetch_news_headlines
from modules.news_verifier import verify_headline
from modules.post_guard    import (
    get_blocked_subjects,
    get_blocked_headlines,
    is_headline_blocked,
)

log = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# gemini-2.0-flash — correct model name
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.0-flash:generateContent?key={key}"
)

SUBJECTS = [
    "Data Analytics",
    "Power BI",
    "Data Visualization",
    "Artificial Intelligence",
    "Use of AI in Data Analytics",
    "SQL",
    "Machine Learning",
    "Python for Data Science",
    "Business Intelligence",
    "Data Engineering",
    "Generative AI",
    "Cloud Computing",
    "Data Strategy",
]

PROMPT = """You are a LinkedIn content strategist for a Data and Business Analyst.

You have been given REAL news headlines fetched TODAY from trusted news sources.
Your ONLY job is to pick the single best headline from this list.
Do NOT invent, generate or suggest any headline that is not in the list below.

REAL NEWS HEADLINES (these are the ONLY options):
{headlines_block}

HEADLINE COUNT SCORES (more articles today = higher relevance):
{trends_block}

RECENTLY POSTED SUBJECTS — do NOT pick from these:
{recent_subjects_block}

RECENTLY USED HEADLINES — do NOT pick any of these:
{recent_headlines_block}

STRICT RULES:
1. Pick a headline that EXISTS in the list above
2. Do NOT modify the headline text
3. Do NOT invent headlines
4. Do NOT pick from recently posted subjects
5. Prefer subjects with higher headline count scores

Return ONLY valid JSON, no markdown, no extra text:
{{
  "subject": "chosen subject from the list",
  "news_headline": "the exact headline from the list — copy word for word",
  "news_detail": "2 to 3 sentences on what this news means for data professionals",
  "why_trending": "one sentence on why professionals are talking about this now",
  "image_keywords": "4 to 5 comma-separated keywords for a relevant image",
  "image_style": "vivid description of a professional image matching this news"
}}"""


def get_trending_topic(topic: str = "") -> dict:
    # Step 1 — Get blocked subjects and headlines
    blocked_subjects  = get_blocked_subjects()
    blocked_headlines = get_blocked_headlines()

    log.info(f"   Blocked subjects (last 3d): {blocked_subjects}")
    log.info(f"   Blocked headlines (last 14d): {len(blocked_headlines)} headlines")

    available_subjects = [s for s in SUBJECTS if s not in blocked_subjects]
    if not available_subjects:
        log.warning("   All subjects blocked — opening all subjects")
        available_subjects = SUBJECTS

    # Step 2 — Fetch REAL news headlines
    log.info("   Fetching real news headlines...")
    all_headlines   = []
    headline_counts = {}

    for subject in SUBJECTS:
        raw_headlines = fetch_news_headlines(subject)
        count = 0
        for h in raw_headlines[:5]:
            title = h.get("title", "").strip()
            if not title or len(title) < 15:
                continue
            if subject in blocked_subjects:
                continue
            if is_headline_blocked(title, blocked_headlines):
                continue
            # verify_headline returns a dict — check verdict
            try:
                vr = verify_headline(h)
                if isinstance(vr, dict) and vr.get('verdict') == 'reject':
                    continue
                elif not isinstance(vr, dict) and not vr:
                    continue
            except Exception:
                pass  # if verifier errors entirely, allow through
            all_headlines.append({
                "subject":     subject,
                "title":       title,
                "description": h.get("description", ""),
                "url":         h.get("url", ""),
                "source":      h.get("source", "NewsAPI"),
                "publishedAt": h.get("publishedAt", ""),
            })
            count += 1
        headline_counts[subject] = count
        if count > 0:
            log.info(f"   NewsAPI: found {count} headlines for '{subject}'")

    blocked_total = len(blocked_subjects) + len(blocked_headlines)
    log.info(f"   Pre-filtered {blocked_total} blocked headlines/subjects")
    log.info(f"   {len(all_headlines)} fresh headlines available for Gemini")

    # Step 3 — No real news → static fallback only, never ask Gemini to invent
    if not all_headlines:
        log.warning("   No fresh real headlines — using static fallback. No fake news generated.")
        return _static_fallback(blocked_subjects)

    # Step 4 — Gemini picks best real headline (with retry on 429)
    if GEMINI_API_KEY:
        result = _gemini_pick_best(
            all_headlines, blocked_subjects, blocked_headlines, headline_counts
        )
        if result:
            # Verify Gemini picked a real headline not an invented one
            picked     = result.get("news_headline", "").lower()[:80]
            real_titles = [h["title"].lower()[:80] for h in all_headlines]
            is_real    = any(
                picked[:60] in t or t[:60] in picked
                for t in real_titles
            )
            if not is_real:
                log.warning("   Gemini invented a headline — using first real headline instead")
                return _fallback_from_headlines(all_headlines, blocked_subjects)
            return result

    # Step 5 — Gemini unavailable → pick best real headline directly
    return _fallback_from_headlines(all_headlines, blocked_subjects)


def _gemini_pick_best(headlines: list, blocked_subjects: list,
                      blocked_headlines: list, scores: dict) -> dict | None:
    """Call Gemini with one retry on 429."""
    for attempt in range(1, 3):  # max 2 attempts
        try:
            headlines_block = ""
            for i, h in enumerate(headlines[:20], 1):
                headlines_block += (
                    f"{i}. [{h['subject']}] {h['title']}\n"
                    f"   {h['description'][:150] if h['description'] else 'No description'}\n"
                    f"   Source: {h['source']} | Date: {h['publishedAt'][:10] if h['publishedAt'] else 'recent'}\n\n"
                )

            trends_block = "\n".join(
                f"- {s}: {v} fresh articles today"
                for s, v in sorted(scores.items(), key=lambda x: x[1], reverse=True)
                if v > 0
            ) or "All subjects have fresh headlines available."

            recent_subjects_block = (
                ", ".join(blocked_subjects) if blocked_subjects
                else "None — all subjects available."
            )

            recent_headlines_block = (
                "\n".join(f"- {h[:100]}" for h in blocked_headlines[:10])
                if blocked_headlines else "None."
            )

            prompt = PROMPT.format(
                headlines_block=headlines_block,
                trends_block=trends_block,
                recent_subjects_block=recent_subjects_block,
                recent_headlines_block=recent_headlines_block,
            )

            url     = GEMINI_URL.format(key=GEMINI_API_KEY)
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.4, "maxOutputTokens": 500}
            }

            r = requests.post(url, json=payload, timeout=25)

            # On 429 wait and retry once
            if r.status_code == 429:
                if attempt == 1:
                    log.warning("   Gemini 429 — waiting 30s before retry...")
                    time.sleep(30)
                    continue
                else:
                    log.warning("   Gemini 429 on retry — falling back to direct headline pick")
                    return None

            r.raise_for_status()
            raw  = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            raw  = raw.replace("```json", "").replace("```", "").strip()
            data = json.loads(raw)

            log.info(f"   Subject : {data.get('subject', '')}")
            log.info(f"   Headline: {data.get('news_headline', '')[:80]}")
            return data

        except Exception as e:
            if "429" in str(e) and attempt == 1:
                log.warning("   Gemini 429 — waiting 30s before retry...")
                time.sleep(30)
                continue
            log.warning(f"   Gemini failed ({e})")
            return None

    return None


# Keywords that make a headline MORE relevant to data analytics audience
HEADLINE_QUALITY_KEYWORDS = [
    "data analytics", "business intelligence", "machine learning",
    "artificial intelligence", "power bi", "data visualization",
    "data engineering", "generative ai", "cloud", "microsoft",
    "amazon", "google", "openai", "analytics platform",
    "market size", "billion", "enterprise", "workforce",
    "productivity", "automation", "ai strategy", "data strategy",
    "report", "study", "research", "survey", "findings",
    "reshape", "transform", "adopt", "deploy", "implement",
]

# Keywords that make a headline LESS relevant — penalise these
HEADLINE_NOISE_KEYWORDS = [
    "ceo proud", "monthly bill", "patent law", "deepfake yourself",
    "data centers in space", "in space", "startup ceo says",
    "racked up", "ai bill", "harvey for", "lousy",
    "youtubers sue", "trained on scra", "article about ai",
    "doesn't need ai art",
]


def _score_headline(title: str, subject: str) -> int:
    """
    Score a headline 0-100 for relevance to data analytics audience.
    Higher = more relevant = should be picked first by fallback.
    """
    title_lower = title.lower()
    score = 50

    # Boost for quality keywords
    for kw in HEADLINE_QUALITY_KEYWORDS:
        if kw in title_lower:
            score += 8

    # Penalise noise keywords
    for kw in HEADLINE_NOISE_KEYWORDS:
        if kw in title_lower:
            score -= 30

    # Boost if subject name appears in headline
    if subject.lower()[:10] in title_lower:
        score += 10

    # Boost for market/research news (high value for audience)
    if any(w in title_lower for w in ["market size", "billion", "report", "survey", "study"]):
        score += 15

    # Penalise gossip/opinion patterns
    if any(w in title_lower for w in ["says he", "says she", "i quit", "proud his", "proud their"]):
        score -= 25

    return max(0, min(100, score))


def _fallback_from_headlines(headlines: list, blocked_subjects: list) -> dict:
    """
    Pick best real headline using quality scoring — no AI involved.
    Scores every headline and picks the highest scoring one.
    Falls back to priority order if all scores are equal.
    """
    # Priority order for subject preference
    priority = [
        "Data Analytics", "Artificial Intelligence", "Machine Learning",
        "Power BI", "Data Visualization", "Use of AI in Data Analytics",
        "SQL", "Business Intelligence", "Data Engineering",
        "Generative AI", "Cloud Computing", "Data Strategy",
        "Python for Data Science",
    ]

    # Score all available headlines
    scored = []
    for h in headlines:
        subj  = h.get("subject", "")
        title = h.get("title", "")
        # Base priority score from subject order
        subj_score = len(priority) - priority.index(subj) if subj in priority else 0
        # Quality score from headline content
        quality = _score_headline(title, subj)
        # Skip blocked subjects but still score them (lower priority)
        blocked_penalty = -50 if subj in blocked_subjects else 0
        total = quality + subj_score + blocked_penalty
        scored.append((total, h))

    # Sort by score descending
    scored.sort(key=lambda x: x[0], reverse=True)

    if scored:
        best_score, best_h = scored[0]
        log.info(f"   Fallback scored {len(scored)} headlines — best score: {best_score}")
        log.info(f"   Fallback picked: {best_h['title'][:60]}")
        return {
            "subject":        best_h["subject"],
            "news_headline":  best_h["title"],
            "news_detail":    best_h.get("description", ""),
            "why_trending":   "Significant discussion among data and technology professionals.",
            "image_keywords": f"{best_h['subject'].lower()}, data, technology, professional, analytics",
            "image_style":    (
                f"Cinematic professional image about {best_h['subject']}. "
                f"Dark background with blue and cyan glowing elements. Ultra sharp."
            ),
        }

    return _static_fallback(blocked_subjects)

def _static_fallback(blocked_subjects: list = []) -> dict:
    """Last resort — zero real headlines from NewsAPI. Generic only, no AI."""
    import random
    available = [s for s in SUBJECTS if s not in blocked_subjects] or SUBJECTS
    subject   = random.choice(available)
    log.warning(f"   Static fallback used for subject: {subject}")
    return {
        "subject":        subject,
        "news_headline":  f"Key developments in {subject} professionals need to know today",
        "news_detail":    (
            f"The {subject} space continues to evolve with new tools, frameworks and "
            f"approaches emerging for data professionals."
        ),
        "why_trending":   (
            f"Data professionals are actively discussing how {subject} developments "
            f"affect day-to-day workflows and career growth."
        ),
        "image_keywords": f"{subject.lower()}, data analytics, technology, professional",
        "image_style":    (
            f"Cinematic dark professional image representing {subject}. "
            f"Glowing blue and cyan elements. Ultra sharp photorealistic."
        ),
    }
