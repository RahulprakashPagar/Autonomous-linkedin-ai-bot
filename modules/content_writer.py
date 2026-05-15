"""
Stage 2 — Content Writer
Model : GPT-4o mini via OpenAI API

FORMAT: Short punchy LinkedIn posts — 220 to 250 words STRICTLY ENFORCED
- 3 regeneration attempts if under 220 words
- Hook first line that stops the scroll
- Key insight in 3-4 sentences
- One question to drive comments
- 10 to 12 hashtags — standard + keyword hashtags from news content
- Spell check pass before publishing
"""

import os
import re
import json
import logging
from openai import OpenAI
from modules.history_tracker import load_history

log = logging.getLogger(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GPT_MODEL      = "gpt-4o-mini"

TONE_MODES = {
    "storytelling": {
        "name": "Storytelling",
        "hook": (
            "Open with a single surprising or personal observation that makes someone stop scrolling. "
            "Example: 'I came across something this week that completely changed how I think about [topic].'"
        )
    },
    "data_breakdown": {
        "name": "Data Breakdown",
        "hook": (
            "Open with one specific surprising number or fact from the news. "
            "Example: 'This number stopped me: [specific stat from the news].'"
        )
    },
    "practical_tips": {
        "name": "Practical Tips",
        "hook": (
            "Open with a bold practical statement about what this news means right now. "
            "Example: 'If you work with data, this changes something you do every day.'"
        )
    },
    "thought_leader": {
        "name": "Thought Leadership",
        "hook": (
            "Open with a bold contrarian or forward-looking statement. "
            "Example: 'Most people are missing what this actually means for data professionals.'"
        )
    }
}

SYSTEM_PROMPT = """You are Rahul, a Data and Business Analyst who completed a Masters in Business Analytics from Dublin Business School, Ireland. You write short punchy LinkedIn posts that make people stop scrolling.

STRUCTURE — follow exactly:
Paragraph 1 (1-2 sentences): The HOOK — surprising, bold or personal. Must reference the specific news.
Paragraph 2 (3-4 sentences): The KEY INSIGHT — what this specific news means for data professionals. Be concrete and specific. Reference the actual news item, company or finding by name.
Paragraph 3 (2-3 sentences): Expand the insight with one real-world implication or example that makes it tangible.
Paragraph 4 (1-2 sentences): ONE question that drives comments. Make it easy and specific to answer.
Last line: 10 to 12 hashtags — two types mixed together:
  TYPE 1 — Standard topic hashtags (pick 7 to 9):
    #DataAnalytics #AI #MachineLearning #DataScience #Python #ArtificialIntelligence
    #PowerBI #SQL #DataVisualization #BusinessIntelligence #Analytics #Innovation
    #DataDriven #TechTrends #Automation #BigData #PredictiveAnalytics #DataEngineering
  TYPE 2 — Keyword hashtags from the news (pick 2 to 3):
    Extract product names, company names, specific technologies from the news headline
    Example: post about Microsoft Fabric → add #MicrosoftFabric
    Example: post about Amazon QuickSight → add #AmazonQuickSight
    Example: post about Power BI Copilot → add #Copilot

STRICT WORD COUNT RULE:
You MUST write between 220 and 250 words for the post body (excluding hashtags).
Before finishing, count every word in your post body.
If you are under 220 words you MUST expand — add more sentences to paragraph 2 or 3.
This is the single most important rule. Do not submit under 220 words.

OTHER STRICT RULES:
- NEVER use dashes anywhere (em dash, en dash, hyphen as connector)
- NEVER use bullet points or numbered lists
- NEVER reference years of experience
- NEVER use: leverage, synergy, game-changer, delve, transformative, groundbreaking, In today's world, In the age of AI
- Maximum 1 emoji in the entire post
- Sound human and conversational — not corporate
- Perfect spelling and grammar — zero mistakes allowed
- NEVER include #DublinBusinessSchool or any university or college hashtag
- Total hashtags: 10 to 12 on the final line

OUTPUT FORMAT:
Write the complete post.
Then on a new line write ONLY:
{"image_keywords": "keyword1, keyword2, keyword3"}"""

USER_PROMPT = """Write a LinkedIn post for Rahul about this specific news.

SUBJECT: {subject}
NEWS HEADLINE: {news_headline}
NEWS DETAIL: {news_detail}
WHY IT MATTERS: {why_trending}

WRITING MODE: {tone_name}
HOOK STYLE: {hook_style}

PARAGRAPH STRUCTURE:
1. HOOK (1-2 sentences) — {hook_style}
2. KEY INSIGHT (3-4 sentences) — Name the specific company, product or finding from the news.
3. REAL WORLD IMPLICATION (2-3 sentences) — Tangible example for data professionals.
4. QUESTION (1-2 sentences) — Easy, specific, drives comments.

HASHTAGS (last line, 10 to 12 total):
- 7 to 9 from the standard list in system prompt
- 2 to 3 keyword hashtags from this headline: {news_headline}
  (look for product names, companies, technologies — make them into hashtags)

MANDATORY WORD COUNT:
Your post body MUST be 220 to 250 words. Count before you finish.
Current target: write at least 8 sentences across 4 paragraphs.
If paragraph 2 is less than 3 sentences, add another sentence.
If paragraph 3 is less than 2 sentences, add another sentence.

Write the post now:"""

EXPAND_PROMPT = """The LinkedIn post below is only {word_count} words. It must be 220 to 250 words.

EXPAND IT by:
1. Adding 1-2 more sentences to paragraph 2 with specific details about: {news_headline}
2. Adding 1 more sentence to paragraph 3 with a concrete real-world example
3. Keep everything else exactly the same — same hook, same question, same hashtags

Do NOT change the structure, tone, hashtags or meaning.
Return ONLY the expanded post with no explanation.

CURRENT POST:
{post}"""

SPELLCHECK_PROMPT = """You are a professional proofreader.
Fix any spelling mistakes, grammar errors or typos in this LinkedIn post.
Do NOT change the meaning, structure, tone, content or hashtags.
Do NOT add or remove sentences.
Return ONLY the corrected post with no explanation.

POST:
{post}"""


def get_current_tone() -> dict:
    history    = load_history()
    post_count = len(history.get("posts", []))
    tone_keys  = list(TONE_MODES.keys())
    tone       = TONE_MODES[tone_keys[post_count % len(tone_keys)]]
    log.info(f"   Tone mode: {tone['name']} (post #{post_count + 1})")
    return tone


def generate_post_content(topic: str, trend_data: dict) -> tuple[str, str]:
    subject       = trend_data.get("subject",       topic)
    news_headline = trend_data.get("news_headline", trend_data.get("trend", ""))
    news_detail   = trend_data.get("news_detail",   trend_data.get("why_trending", ""))
    why_trending  = trend_data.get("why_trending",  "")

    if not news_headline or len(news_headline.strip()) < 15:
        news_headline = f"New developments in {subject} are changing how data teams work"
        news_detail   = f"The {subject} space is shifting with direct implications for analysts."

    if not news_detail or len(news_detail.strip()) < 20:
        news_detail = f"This development in {subject} has real practical implications for data professionals."

    log.info(f"   Writing post about: {news_headline[:80]}")

    if not OPENAI_API_KEY:
        log.warning("OPENAI_API_KEY not set — using fallback")
        return _fallback(subject, news_headline, news_detail)

    try:
        tone   = get_current_tone()
        client = OpenAI(api_key=OPENAI_API_KEY)

        user_prompt = USER_PROMPT.format(
            subject=subject,
            news_headline=news_headline,
            news_detail=news_detail,
            why_trending=why_trending,
            tone_name=tone["name"],
            hook_style=tone["hook"]
        )

        # First attempt
        response = client.chat.completions.create(
            model=GPT_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": user_prompt}
            ],
            temperature=0.85,
            max_tokens=700,
        )
        raw                       = response.choices[0].message.content.strip()
        post_text, image_keywords = _parse_output(raw, trend_data)
        post_text                 = _clean_post(post_text)
        word_count                = len(post_text.split())
        log.info(f"   Word count: {word_count}")

        # Up to 3 expansion attempts if under 220
        for attempt in range(1, 4):
            if word_count >= 220:
                break
            log.warning(f"   Too short ({word_count} words) — expanding (attempt {attempt})...")
            expand_response = client.chat.completions.create(
                model=GPT_MODEL,
                messages=[{
                    "role": "user",
                    "content": EXPAND_PROMPT.format(
                        word_count=word_count,
                        news_headline=news_headline,
                        post=post_text
                    )
                }],
                temperature=0.7,
                max_tokens=700,
            )
            expanded_raw               = expand_response.choices[0].message.content.strip()
            expanded_text, expanded_kw = _parse_output(expanded_raw, trend_data)
            expanded_text              = _clean_post(expanded_text)
            new_count                  = len(expanded_text.split())
            log.info(f"   After expansion attempt {attempt}: {new_count} words")
            # Only accept if longer than before AND not over 260
            if new_count > word_count and new_count <= 260:
                post_text      = expanded_text
                image_keywords = expanded_kw
                word_count     = new_count
            elif new_count > 260:
                # Trim back down
                post_text      = expanded_text
                image_keywords = expanded_kw
                word_count     = new_count
                break  # will be trimmed in next step

        # If still under 220 after 3 attempts log a warning but continue
        if word_count < 220:
            log.warning(f"   Still under 220 after 3 expansion attempts ({word_count}) — posting anyway")

        # Too long — trim once
        if word_count > 270:
            log.warning(f"   Too long ({word_count} words) — trimming...")
            trim_response = client.chat.completions.create(
                model=GPT_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": user_prompt +
                     "\n\nRewrite in exactly 220 to 250 words. Keep hook, insight and question."}
                ],
                temperature=0.80,
                max_tokens=700,
            )
            raw_t       = trim_response.choices[0].message.content.strip()
            post_text_t, image_keywords_t = _parse_output(raw_t, trend_data)
            post_text_t = _clean_post(post_text_t)
            if len(post_text_t.split()) < word_count:
                post_text      = post_text_t
                image_keywords = image_keywords_t

        # Validate relevance
        if not _is_relevant(post_text, news_headline):
            log.warning("   Not relevant to headline — regenerating...")
            rel_response = client.chat.completions.create(
                model=GPT_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": user_prompt +
                     f"\n\nMust reference this specific news in paragraph 1: '{news_headline}'"}
                ],
                temperature=0.80,
                max_tokens=700,
            )
            raw_r       = rel_response.choices[0].message.content.strip()
            post_text_r, image_keywords_r = _parse_output(raw_r, trend_data)
            post_text_r = _clean_post(post_text_r)
            post_text      = post_text_r
            image_keywords = image_keywords_r

        # Final spell check
        post_text = _spellcheck(client, post_text)

        final_count = len(post_text.split())
        log.info(f"   Final word count: {final_count}")
        log.info(f"   Words    : {final_count}")
        log.info(f"   Preview  : {post_text[:80]}...")
        return post_text, image_keywords

    except Exception as e:
        log.error(f"ChatGPT failed ({e}) — using fallback")
        return _fallback(subject, news_headline, news_detail)


def _spellcheck(client, post_text: str) -> str:
    try:
        response = client.chat.completions.create(
            model=GPT_MODEL,
            messages=[{
                "role": "user",
                "content": SPELLCHECK_PROMPT.format(post=post_text)
            }],
            temperature=0.1,
            max_tokens=700,
        )
        corrected = response.choices[0].message.content.strip()
        if 0.85 <= len(corrected.split()) / max(1, len(post_text.split())) <= 1.15:
            log.info("   Spellcheck passed")
            return corrected
        return post_text
    except Exception as e:
        log.warning(f"   Spellcheck failed ({e})")
        return post_text


def _is_relevant(post_text: str, news_headline: str) -> bool:
    stop_words = {"about","their","which","there","these","those","after",
                  "before","where","while","could","would","should","being"}
    post_lower     = post_text.lower()
    headline_words = [
        w.lower().strip(".,()[]':\"") for w in news_headline.split()
        if len(w) >= 5 and w.lower().strip(".,()[]':\"") not in stop_words
    ]
    if not headline_words:
        return True
    matches = sum(1 for w in headline_words if w in post_lower)
    return matches >= min(2, len(headline_words))


def _remove_unwanted_hashtags(text: str) -> str:
    unwanted = [
        "#DublinBusinessSchool","#Dublin","#Ireland","#DBS",
        "#MSc","#MBA","#Masters","#University","#College",
        "#Student","#Graduate","#Alumni",
    ]
    for tag in unwanted:
        text = text.replace(tag,"").replace(tag.lower(),"")
    return re.sub(r'  +',' ',text).strip()


def _clean_post(text: str) -> str:
    text = text.replace("\u2014"," ").replace("\u2013"," ")
    text = text.replace("—"," ").replace("–"," ")
    text = re.sub(r'\s+-\s+',' ',text)
    text = re.sub(r'([.!?])\s*-\s*',r'\1 ',text)
    text = re.sub(r'(\w)\s*-\s+(\w)',r'\1 \2',text)
    for p in [
        r"[Aa]fter \d+\+?\s*years?\s+(of\s+)?(working|experience|in)[^.]*\.",
        r"[Ii]n my \d+\+?\s*years?[^.]*\.",
        r"\d+\+?\s*years? of experience[^.]*\.",
    ]:
        text = re.sub(p,"",text)
    text = _remove_unwanted_hashtags(text)
    text = re.sub(r'  +',' ',text)
    text = re.sub(r'\n{3,}','\n\n',text)
    return text.strip()


def _parse_output(raw: str, trend_data: dict) -> tuple[str, str]:
    image_keywords = trend_data.get("image_keywords","technology, data, AI")
    try:
        idx = raw.rfind('{"image_keywords"')
        if idx != -1:
            post_text      = raw[:idx].strip()
            parsed         = json.loads(raw[idx:])
            image_keywords = parsed.get("image_keywords", image_keywords)
        else:
            post_text = raw
    except Exception:
        post_text = raw
    return post_text, image_keywords


def _fallback(subject: str, news_headline: str, news_detail: str) -> tuple[str, str]:
    words  = [w.strip(".,()[]':\"") for w in news_headline.split() if len(w) > 5]
    kw_tag = f"#{words[0].replace(' ','')}" if words else f"#{subject.replace(' ','')}"
    post = (
        f"Something in {subject} caught my attention this week and I wanted to share it.\n\n"
        f"I came across this: {news_headline}. {news_detail[:150]} "
        f"What strikes me most is how directly this affects the way data professionals "
        f"work right now. This is not a distant future development. "
        f"It is already shaping decisions being made in organisations today. "
        f"The teams that understand this properly will have a real advantage.\n\n"
        f"The practical implication is clear. Understanding the specific details "
        f"of what is changing in {subject} matters more than having a general awareness. "
        f"Most professionals stop at awareness. The ones who go deeper are the ones "
        f"who end up having more influence in their organisations. "
        f"This is one of those moments where going deeper genuinely pays off.\n\n"
        f"Have you come across this yet and how is your team thinking about it?\n\n"
        f"#DataAnalytics #AI #MachineLearning #DataScience #Python "
        f"#ArtificialIntelligence #Analytics #Innovation #DataDriven #TechTrends "
        f"{kw_tag} #BigData"
    )
    return post, f"{subject.lower()}, data, technology, analytics"
