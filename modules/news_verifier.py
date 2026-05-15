"""
News Verifier — Balanced Version
Filters headlines for:
1. Relevance   — must be about data, analytics, AI in professional/business context
2. Authenticity — trusted sources, no clickbait
3. Quality     — blocks gaming, entertainment, sports, politics

FIXES:
- "war" removed from IRRELEVANT_KEYWORDS — was blocking "Warren Buffett", "software"
- PROFESSIONAL_CONTEXT expanded — more words that appear in real news
- Funding/investment news now passes — OpenAI $122B is valid business news
- Tutorial headlines no longer blocked — only pure beginner tutorials rejected
"""

import os
import logging
import requests
import json

log = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_URL     = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.0-flash:generateContent?key={key}"
)

# ── Trusted sources ───────────────────────────────────────────────────────────
TRUSTED_SOURCES = {
    "TechCrunch", "MIT Technology Review", "The Verge", "Wired",
    "Reuters", "Bloomberg", "BBC Technology", "The Guardian",
    "Forbes", "Harvard Business Review", "VentureBeat",
    "ZDNet", "InfoWorld", "Towards Data Science", "KDnuggets",
    "O'Reilly", "IEEE Spectrum", "Ars Technica", "InfoQ",
    "Microsoft Blog", "Google Blog", "OpenAI Blog", "Anthropic",
    "Gartner", "McKinsey", "Deloitte", "Accenture", "IDC",
    "Analytics Vidhya", "Towards AI", "DataCamp", "Kaggle Blog",
    "AWS Blog", "Azure Blog", "Google Cloud Blog",
    "Wall Street Journal", "Financial Times", "New York Times Technology",
    "Business Insider", "CNBC", "MarketWatch", "TechRepublic",
}

# ── Immediately reject if ANY of these appear in headline ─────────────────────
# NOTE: Keep these very specific — short words cause false positives
# "war" was removed because it matched "Warren", "software", "reward"
IRRELEVANT_KEYWORDS = [
    # Gaming — very specific phrases only
    "video game", "gaming industry", "esports", "game developer",
    "playstation", "xbox console", "nintendo switch",
    "beat AI at video", "AI at chess game", "AI plays game",

    # Entertainment
    "movie review", "film review", "box office",
    "celebrity", "singer", "music album", "concert tour",
    "reality tv", "netflix series", "streaming show",
    "fashion week", "makeup tutorial",

    # Sports
    "football match", "soccer game", "cricket match",
    "basketball game", "tennis tournament",
    "world cup", "sports championship", "athlete signs",
    "transfer fee", "player traded",

    # Politics — specific phrases not single words
    "election campaign", "political party", "senate vote",
    "congress passes", "government shutdown",
    "military operation", "war crimes", "nuclear weapons",
    "sanctions imposed",

    # Personal lifestyle
    "weight loss tips", "diet plan", "travel guide",
    "holiday destination", "wedding planning", "dating advice",
    "cooking recipe",

    # Clearly off-topic tech
    "crypto price", "bitcoin crashes", "nft drops",
    "real estate market", "housing prices",
    "natural disaster", "earthquake hits", "flood damage",

    # Cybersecurity vulnerabilities -- not relevant to data analytics audience
    "cve-202", "rce flaw", "zero-day exploit", "remote code execution",
    "ransomware attack", "ransomware campaign",
    "phishing attack", "phishing campaign",
    "security exploit", "vulnerability exploit", "exploited within",
    "malware campaign", "cyberattack", "cyber attack",
    "data breach", "password leak", "credential theft",
    "backdoor", "rootkit", "botnet",

    # Hardware / consumer tech -- not data analytics
    "smartphone review", "iphone launch", "android phone",
    "laptop review", "graphics card", "cpu benchmark",
    "gaming laptop", "headphones review","laptop battery", 
    "surface laptop", "linux foundation key",
    "fix laptop", "battery life",

    # Salary listicles and job gossip -- too generic
    "salaries revealed", "highest paying jobs",
    "quit my job", "fired from",
    "proud his team", "monthly ai bill", "racked up a",
    "startup ceo says", "ceo says he",

    # Sensational / viral tech stories -- not professional analytics
    "deepfake yourself", "data centers in space",
    "in space wants", "patent law has raised",
    "youtubers sue", "trained on scra",
    "article about ai doesn", "doesn't need ai art",
    "lousy cloud security",

    # Space / science unrelated to data
    "nasa astronaut", "space mission", "rocket launch",
    "climate change study", "medical study", "health study",

    # Press releases and marketing disguised as news
    "precedence research", "precedence q",
    "proud to announce", "pleased to announce",
    "proud to introduce", "excited to announce",
    "excited to introduce", "we are thrilled",
    "launches new platform", "introduces new solution",
    "new tool that changes", "game changing platform",
    "unveils revolutionary", "groundbreaking new tool",
    "proprietary platform", "cutting-edge solution",

    # Generic newsletter headlines with no specific news
    "ai updates for the week", "weekly roundup",
    "this week in ai", "top stories this week",
    "news digest", "weekly digest",

    # Interviews and personal opinion pieces
    "an interview with", "in conversation with",
    "i spoke with", "we spoke with",
    "my thoughts on", "my take on",
    "opinion:", "perspective:",
]

# ── Headline MUST contain at least one of these ───────────────────────────────
RELEVANT_KEYWORDS = [
    # Core data topics
    "data", "analytics", "analysis", "analyst",
    "machine learning", "deep learning", "neural network",
    "artificial intelligence", " ai ", "ai-powered", "ai-driven",
    "power bi", "tableau", "visualization", "dashboard",
    "sql", "database", "data engineering", "etl", "pipeline",
    "python", "automation", "algorithm", "model training",

    # Business intelligence
    "business intelligence", " bi ", "reporting",
    "insight", "metric", "kpi", "performance indicator",
    "forecasting", "prediction", "decision making",

    # Specific tools and platforms
    "llm", "gpt", "generative ai", "copilot", "large language",
    "cloud computing", "microsoft", "google", "openai", "anthropic",
    "aws", "azure", "databricks", "snowflake", "dbt",
    "pandas", "spark", "hadoop", "kafka", "airflow",

    # Business outcomes
    "productivity", "efficiency", "revenue", "cost reduction",
    "roi", "market size", "investment", "funding", "billion",
    "workforce", "upskilling", "reskilling", "talent",

    # Research and reports
    "report", "study", "survey", "research", "findings",
    "market report", "industry report", "whitepaper",
]

# ── Professional context — at least one required ──────────────────────────────
# Expanded significantly to catch more valid business/tech news
PROFESSIONAL_CONTEXT = [
    # Organisation types
    "enterprise", "business", "company", "organisation", "organization",
    "corporation", "firm", "startup", "vendor", "provider",
    "industry", "sector", "market", "global", "worldwide",

    # People/roles
    "professional", "analyst", "engineer", "scientist", "developer",
    "manager", "executive", "cto", "cdo", "ceo", "leader",
    "team", "workforce", "employee", "worker", "talent",

    # Business activities
    "productivity", "efficiency", "revenue", "cost", "roi",
    "strategy", "deployment", "implementation", "adoption",
    "investment", "funding", "billion", "million", "growth",
    "launch", "release", "announce", "unveil", "introduce",

    # Research/reports
    "research", "study", "report", "survey", "findings",
    "according to", "shows", "reveals", "highlights",

    # Tech business context
    "platform", "solution", "tool", "product", "service",
    "cloud", "saas", "software", "application", "system",

    # Training and skills
    "training", "upskill", "reskill", "learn", "skill",
    "certification", "course", "education",

    # Size/scale indicators
    "billion", "million", "percent", "%", "increase", "growth",
    "rise", "decline", "market size", "hit usd", "valued at",
]

CLICKBAIT_PATTERNS = [
    "you won't believe", "shocking truth", "mind-blowing",
    "obliterates", "crushes", "annihilates",
    "they don't want you to know", "secret revealed",
    "one weird trick", "insane trick",
    "exposed", "scandal", "outrage",
]


def verify_headline(headline_data: dict) -> dict:
    """
    Verify a headline for authenticity AND professional relevance.
    Returns dict with trust_score, verdict and reason.
    """
    title       = headline_data.get("title", "")
    url         = headline_data.get("url", "")
    source      = headline_data.get("source", "")
    desc        = headline_data.get("description", "")
    combined    = f"{title} {desc}".lower()
    title_lower = title.lower()

    score   = 50
    reasons = []

    # ── Check 1: Reject clearly irrelevant topics ─────────────────────────────
    irrelevant_found = [kw for kw in IRRELEVANT_KEYWORDS if kw.lower() in combined]
    if irrelevant_found:
        log.info(f"   REJECTED (irrelevant): '{title[:60]}' — {irrelevant_found[:2]}")
        return {
            "trust_score": 0,
            "verdict":     "reject",
            "reason":      f"Irrelevant content: {irrelevant_found[:2]}",
            "title":       title,
            "source":      source
        }

    # ── Check 2: Must contain at least one relevant keyword ───────────────────
    relevant_found = [kw for kw in RELEVANT_KEYWORDS if kw.lower() in combined]
    if not relevant_found:
        log.info(f"   REJECTED (no relevant keywords): '{title[:60]}'")
        return {
            "trust_score": 0,
            "verdict":     "reject",
            "reason":      "No data/AI/analytics keywords found",
            "title":       title,
            "source":      source
        }
    score  += 15
    reasons.append(f"Relevant keywords: {relevant_found[:2]}")

    # ── Check 3: Must have professional/business context ──────────────────────
    professional_found = [kw for kw in PROFESSIONAL_CONTEXT if kw.lower() in combined]
    if not professional_found:
        log.info(f"   REJECTED (no professional context): '{title[:60]}'")
        return {
            "trust_score": 10,
            "verdict":     "reject",
            "reason":      "No professional/business context found",
            "title":       title,
            "source":      source
        }
    score  += 15
    reasons.append(f"Professional context: {professional_found[:2]}")

    # ── Check 4: Trusted source bonus ────────────────────────────────────────
    if any(trusted.lower() in source.lower() for trusted in TRUSTED_SOURCES):
        score  += 15
        reasons.append(f"Trusted source: {source}")
    else:
        reasons.append(f"Unknown source: {source}")

    # ── Check 5: Clickbait check ──────────────────────────────────────────────
    flagged = [p for p in CLICKBAIT_PATTERNS if p.lower() in title_lower]
    if flagged:
        score  -= 25
        reasons.append(f"Clickbait: {flagged}")
    else:
        score  += 10
        reasons.append("No clickbait")

    # ── Check 6: URL reachable ────────────────────────────────────────────────
    if url:
        if _check_url(url):
            score += 10
            reasons.append("URL reachable")
        else:
            score -= 5

    # ── Check 7: Title length sanity ─────────────────────────────────────────
    if 20 < len(title) < 200:
        score += 5
    else:
        score -= 10
        reasons.append("Suspicious title length")

    # Clamp score 0-100
    score   = max(0, min(100, score))
    verdict = "use" if score >= 60 else ("caution" if score >= 40 else "reject")

    log.info(f"   Verify: '{title[:55]}' score={score} verdict={verdict}")
    return {
        "trust_score": score,
        "verdict":     verdict,
        "reason":      " | ".join(reasons),
        "title":       title,
        "source":      source
    }


def _check_url(url: str) -> bool:
    try:
        r = requests.head(
            url, timeout=6,
            headers={"User-Agent": "Mozilla/5.0"},
            allow_redirects=True
        )
        return r.status_code < 400
    except Exception:
        return False


def filter_headlines(headlines: list[dict]) -> list[dict]:
    """
    Filter a list of headlines.
    Returns only verified headlines sorted by trust score descending.
    """
    verified = []
    rejected = 0

    for h in headlines:
        result = verify_headline(h)
        if result["verdict"] != "reject":
            h["trust_score"]  = result["trust_score"]
            h["trust_reason"] = result["reason"]
            verified.append(h)
        else:
            rejected += 1

    verified.sort(key=lambda x: x.get("trust_score", 0), reverse=True)
    log.info(f"   Verification: {len(verified)} passed, {rejected} rejected")
    return verified
