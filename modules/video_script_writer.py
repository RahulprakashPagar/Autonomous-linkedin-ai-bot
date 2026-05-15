"""
Video Script Writer
Writes a 60-second speaking script for the D-ID avatar video.
Different from the LinkedIn post — conversational, spoken English,
no hashtags, no bullet points, sounds natural when spoken aloud.
"""

import os
import logging
from openai import OpenAI

log = logging.getLogger(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GPT_MODEL      = "gpt-4o-mini"

SCRIPT_SYSTEM = """You write short spoken video scripts for LinkedIn.
The script will be read aloud by an AI avatar so it must sound completely natural when spoken.

RULES:
- 120 to 140 words ONLY — this is exactly 60 seconds of speaking
- Conversational spoken English — no formal writing
- No hashtags, no bullet points, no headers
- No dashes or hyphens
- Short sentences — easy to follow when listening
- First sentence must hook the listener immediately
- End with one question that invites comments
- Sound like a real person sharing genuine insight
- Never say "In today's video" or "Hi guys" or "Don't forget to like"
- Speak directly to data professionals

STRUCTURE:
Sentence 1-2: Hook — surprising fact or bold statement from the news
Sentence 3-5: What this means for data professionals specifically
Sentence 6-7: One real world example or implication
Sentence 8-9: Question to drive engagement
Final sentence: Natural sign-off like "Would love to hear your thoughts."

OUTPUT: Write only the script text. Nothing else."""

SCRIPT_USER = """Write a 60-second LinkedIn video script for Rahul, a Data and Business Analyst.

NEWS HEADLINE: {headline}
NEWS DETAIL: {detail}
TOPIC: {topic}

The script should be 120 to 140 words, sound natural when spoken aloud, and end with a question.
Write the script now:"""


def generate_video_script(topic: str, trend_data: dict) -> str:
    """
    Generate a 60-second speaking script from the news data.
    Returns the script text.
    """
    headline = trend_data.get("news_headline", "")
    detail   = trend_data.get("news_detail",   "")

    if not headline:
        headline = f"New developments in {topic} are reshaping how data teams work"
    if not detail:
        detail = f"The {topic} space is evolving with significant implications for data professionals."

    log.info(f"   Writing video script for: {headline[:60]}")

    if not OPENAI_API_KEY:
        return _fallback_script(topic, headline)

    try:
        client   = OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model=GPT_MODEL,
            messages=[
                {"role": "system", "content": SCRIPT_SYSTEM},
                {"role": "user",   "content": SCRIPT_USER.format(
                    headline=headline,
                    detail=detail,
                    topic=topic
                )}
            ],
            temperature=0.80,
            max_tokens=300,
        )
        script     = response.choices[0].message.content.strip()
        word_count = len(script.split())
        log.info(f"   Video script: {word_count} words (~{word_count//2}s speaking time)")
        return script

    except Exception as e:
        log.error(f"   Video script generation failed: {e}")
        return _fallback_script(topic, headline)


def _fallback_script(topic: str, headline: str) -> str:
    return (
        f"Here is something every data professional needs to hear. "
        f"{headline}. "
        f"This is not a distant future shift. It is happening right now and it directly "
        f"affects how we work with data every single day. "
        f"The teams that pay attention to developments like this will have a real advantage "
        f"over those who are still catching up. "
        f"Whether you work in analytics, business intelligence or machine learning, "
        f"understanding what is changing in {topic} gives you sharper insights and "
        f"more credibility with your stakeholders. "
        f"That edge compounds over time. "
        f"What is your take on this? How is your team adapting? "
        f"Would love to hear your thoughts."
    )
