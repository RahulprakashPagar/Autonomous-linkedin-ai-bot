"""
Stage 3 — Image Provider
Primary  : DALL-E 3 via OpenAI API
Fallback : Pollinations.ai (free, no key needed)

UPDATED: Strictly male figures only. No women, no girls, no female figures
         in any generated image.

Two styles rotating:
  Style A (even posts) — pure cinematic scene, no text overlay
  Style B (odd posts)  — cinematic background + bold text overlay
"""

import os
import time
import logging
import requests
import urllib.parse
from datetime import datetime
from pathlib import Path
from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont
from modules.history_tracker import load_history

log       = logging.getLogger(__name__)
IMAGE_DIR = Path("images")
IMAGE_DIR.mkdir(exist_ok=True)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# ── MALE-ONLY instruction appended to every prompt ────────────────────────────
MALE_ONLY = (
    "If any human figure appears, it must strictly be a male professional or man. "
    "No women, no girls, no female figures, no female silhouettes anywhere in the image. "
    "Male figures only."
)

SUFFIX = (
    "Cinematic quality. Ultra photorealistic. 4K resolution. "
    "No text, no words, no letters anywhere. No watermarks. No logos. "
    "No social media icons. Dramatic professional lighting. "
    + MALE_ONLY
)

# ── Style A: Pure cinematic scene prompts ─────────────────────────────────────
STYLE_A_PROMPTS = {
    "Data Analytics": (
        "Cinematic ultra-realistic scene: A male professional data analyst at a futuristic "
        "workstation surrounded by holographic glowing dashboards and colorful charts. "
        "Dark blue environment with orange and cyan accent lighting. "
        "Multiple screens showing analytics data. Dramatic depth of field. "
        "Photorealistic movie quality. No text anywhere."
    ),
    "Power BI": (
        "Cinematic ultra-realistic scene: A sleek corporate boardroom at night with "
        "massive curved screens displaying vivid orange and blue business intelligence dashboards. "
        "A male executive reviewing data at the front. Dramatic spotlight lighting. "
        "Photorealistic movie quality. No text anywhere."
    ),
    "Data Visualization": (
        "Cinematic ultra-realistic scene: Stunning abstract data visualization — "
        "thousands of glowing blue and purple data points forming patterns in dark space. "
        "A silhouetted male analyst reaching toward floating holographic charts. "
        "Dramatic neon lighting. Photorealistic movie quality. No text anywhere."
    ),
    "Artificial Intelligence": (
        "Cinematic ultra-realistic scene: A glowing AI neural brain floating above "
        "a futuristic city skyline at night. Orange and blue energy streams connecting "
        "nodes. A male professional analyst in foreground looking up at it. "
        "Dramatic atmospheric lighting. Photorealistic movie quality. No text anywhere."
    ),
    "Use of AI in Data Analytics": (
        "Cinematic ultra-realistic scene: A male data scientist using AI holographic interface "
        "with floating data streams and neural network visualizations around him. "
        "Dark tech environment with blue and amber glow. "
        "Dramatic cinematic lighting. Photorealistic movie quality. No text anywhere."
    ),
    "SQL": (
        "Cinematic ultra-realistic scene: A male developer in a dark room illuminated by "
        "the green glow of database architecture visualizations floating in 3D space. "
        "Glowing data nodes and connection lines. Dramatic moody lighting. "
        "Photorealistic movie quality. No text anywhere."
    ),
    "Machine Learning": (
        "Cinematic ultra-realistic scene: A male engineer working at a glowing workstation "
        "with machine learning model visualizations floating around him. "
        "Dark blue and amber dramatic lighting. City skyline in background. "
        "Photorealistic movie quality. No text anywhere."
    ),
}

# ── Style B: Background for text overlay ──────────────────────────────────────
STYLE_B_PROMPTS = {
    "Data Analytics": (
        "Cinematic photorealistic background: A male professional analyst from behind "
        "sitting at desk with multiple glowing monitor screens showing colorful dashboards. "
        "Dark room with blue and orange accent lighting. Strong left side shadow "
        "for text overlay. No text in image. Ultra sharp."
    ),
    "Power BI": (
        "Cinematic photorealistic background: Large corporate screen showing vibrant "
        "Power BI style dashboard with orange blue charts in dark boardroom. "
        "A male executive silhouette in foreground. "
        "Strong shadowed left area for text. No text in image. Ultra sharp."
    ),
    "Data Visualization": (
        "Cinematic photorealistic background: Abstract glowing data streams and "
        "geometric shapes in deep space. Vibrant neon blue purple on black. "
        "Left third darker for text overlay. No text. Ultra sharp."
    ),
    "Artificial Intelligence": (
        "Cinematic photorealistic background: AI neural network brain glowing blue "
        "and orange with data streams. Dark atmospheric scene. "
        "Left side heavily shadowed for text overlay. No text. Ultra sharp."
    ),
    "Use of AI in Data Analytics": (
        "Cinematic photorealistic background: A male professional at futuristic desk "
        "with AI holograms floating around him. Dark blue and amber glow. "
        "Left area dark for text overlay. No text. Ultra sharp."
    ),
    "SQL": (
        "Cinematic photorealistic background: Dark server room with glowing green "
        "database architecture visualizations. Matrix-style data streams. "
        "Left side dark for text overlay. No text. Ultra sharp."
    ),
    "Machine Learning": (
        "Cinematic photorealistic background: Futuristic neural network layers "
        "glowing in dark space. Amber and blue dramatic light. "
        "Left third shadowed for text overlay. No text. Ultra sharp."
    ),
}


def get_image_for_post(image_keywords: str, topic: str = "",
                       image_style: str = "",
                       post_summary: str = "",
                       news_headline: str = "") -> tuple[str | None, str]:
    history     = load_history()
    post_count  = len(history.get("posts", []))
    use_style_b = (post_count % 2 == 1)

    style_name = "B (text overlay)" if use_style_b else "A (pure scene)"
    log.info(f"   Image style: {style_name} (post #{post_count + 1})")

    if OPENAI_API_KEY:
        if use_style_b:
            path = _generate_style_b(topic, news_headline, post_summary)
        else:
            path = _generate_style_a(topic, news_headline)

        if path:
            return path, "DALL-E 3"
        log.warning("   DALL-E failed — falling back to Pollinations")

    for attempt in range(1, 4):
        seed = int(time.time()) % 99999 + attempt * 1111
        path = _try_pollinations(topic, news_headline, use_style_b, seed)
        if path:
            if use_style_b and news_headline:
                final = _overlay_text(path, news_headline, post_summary, topic)
                return (final or path), "Pollinations.ai"
            return path, "Pollinations.ai"
        if attempt < 3:
            log.info(f"   Waiting 10s before retry {attempt+1}...")
            time.sleep(10)

    log.error("   All image sources failed.")
    return None, "none"


def _generate_style_a(topic: str, news_headline: str) -> str | None:
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        base   = STYLE_A_PROMPTS.get(
            topic,
            f"Cinematic ultra-realistic professional technology scene about {topic}. "
            f"A male professional working in a dark dramatic environment. "
            f"Photorealistic movie quality."
        )
        prompt = f"{base} {SUFFIX}"
        log.info("   DALL-E Style A: generating cinematic scene...")

        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1792x1024",
            quality="hd",
            n=1,
            style="vivid"
        )
        r = requests.get(response.data[0].url, timeout=30, stream=True)
        r.raise_for_status()
        return _save_stream(r, f"styleA_{int(time.time())}.png", min_kb=20)

    except Exception as e:
        log.warning(f"   Style A DALL-E error: {e}")
        return None


def _generate_style_b(topic: str, news_headline: str, post_summary: str) -> str | None:
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        base   = STYLE_B_PROMPTS.get(
            topic,
            f"Cinematic dark dramatic background about {topic}. "
            f"Male professional in dark tech environment. Left side darker for text overlay."
        )
        prompt = f"{base} {SUFFIX}"
        log.info("   DALL-E Style B: generating background for text overlay...")

        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1792x1024",
            quality="standard",
            n=1,
            style="vivid"
        )
        r = requests.get(response.data[0].url, timeout=30, stream=True)
        r.raise_for_status()
        bg_path = _save_stream(r, f"styleB_bg_{int(time.time())}.png", min_kb=20)

        if bg_path and news_headline:
            final = _overlay_text(bg_path, news_headline, post_summary, topic)
            return final or bg_path

        return bg_path

    except Exception as e:
        log.warning(f"   Style B DALL-E error: {e}")
        return None


def _overlay_text(bg_path: str, headline: str, post_summary: str,
                  topic: str) -> str | None:
    try:
        img = Image.open(bg_path).convert("RGBA")
        W, H = img.size

        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ov_draw = ImageDraw.Draw(overlay)
        for x in range(int(W * 0.60)):
            alpha = int(160 * (1 - x / (W * 0.60)))
            ov_draw.line([(x, 0), (x, H)], fill=(0, 0, 0, alpha))
        img = Image.alpha_composite(img, overlay)
        draw = ImageDraw.Draw(img)

        try:
            fb = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            fr = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
            f_headline = ImageFont.truetype(fb, max(36, H // 16))
            f_bullet   = ImageFont.truetype(fr, max(20, H // 28))
            f_tagline  = ImageFont.truetype(fb, max(22, H // 24))
            f_credit   = ImageFont.truetype(fr, max(16, H // 40))
        except:
            f_headline = f_bullet = f_tagline = f_credit = ImageFont.load_default()

        PAD    = int(W * 0.04)
        MAX_TW = int(W * 0.48)
        WHITE  = "#ffffff"
        ORANGE = "#f59e0b"
        GREEN  = "#22c55e"
        SOFT   = "#e2e8f0"

        clean   = headline.replace('"', '').replace("'", "").strip()
        lines   = _wrap(draw, clean, f_headline, MAX_TW)[:4]
        line_h  = int(H // 14)
        total_h = len(lines) * line_h
        start_y = int(H * 0.12)

        for i, line in enumerate(lines):
            y = start_y + i * line_h
            draw.text((PAD + 2, y + 2), line, font=f_headline, fill=(0, 0, 0))
            color = ORANGE if i % 2 == 1 and i > 0 else WHITE
            draw.text((PAD, y), line, font=f_headline, fill=color)

        bullet_points = _extract_bullets(post_summary, headline)
        by = start_y + total_h + int(H * 0.06)
        for bp in bullet_points[:4]:
            r  = int(H * 0.018)
            cx = PAD + r
            cy = by + r + 4
            draw.ellipse([cx-r, cy-r, cx+r, cy+r], outline=ORANGE, width=2)
            draw.text((PAD + r*2 + 10, by), bp, font=f_bullet, fill=SOFT)
            by += int(H * 0.075)

        tagline = "AI + Analytics = Real-World Impact."
        tl_y    = H - int(H * 0.14)
        draw.text((PAD + 1, tl_y + 1), tagline, font=f_tagline, fill=(0, 0, 0))
        draw.text((PAD,     tl_y),     tagline, font=f_tagline, fill=SOFT)

        sub = "#DataAnalytics  #AI  #MachineLearning"
        draw.text((PAD, tl_y + int(H * 0.06)), sub, font=f_credit, fill=ORANGE)

        credit = "@RahulPagar"
        b  = draw.textbbox((0, 0), credit, font=f_credit)
        cw = b[2] - b[0]
        draw.text((W - cw - PAD, H - int(H * 0.06)), credit, font=f_credit, fill=GREEN)

        final    = img.convert("RGB")
        date     = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = IMAGE_DIR / f"{date}_styleB_final.jpg"
        final.save(str(out_path), "JPEG", quality=93)
        log.info(f"   Text overlay saved: {out_path.name}")
        return str(out_path)

    except Exception as e:
        log.warning(f"   Text overlay failed: {e}")
        return bg_path


def _wrap(draw, text: str, font, max_w: int) -> list[str]:
    words = text.split()
    lines = []
    line  = ""
    for w in words:
        test = (line + " " + w).strip()
        b    = draw.textbbox((0, 0), test, font=font)
        if b[2] - b[0] <= max_w:
            line = test
        else:
            if line: lines.append(line)
            line = w
    if line: lines.append(line)
    return lines


def _extract_bullets(post_summary: str, headline: str) -> list[str]:
    if not post_summary or len(post_summary) < 30:
        return [
            "AI is reshaping data analytics",
            "New tools emerging rapidly",
            "Professionals must adapt now",
            "Real-world impact ahead",
        ]
    sentences = [
        s.strip() for s in post_summary.replace('\n', ' ').split('.')
        if len(s.strip()) > 20
    ]
    bullets = []
    for s in sentences[:6]:
        words = s.split()
        if len(words) > 10:
            s = ' '.join(words[:9]) + '...'
        bullets.append(s)
        if len(bullets) == 4:
            break
    defaults = [
        "AI tools advancing fast",
        "Data teams must stay current",
        "Insights drive decisions",
        "The future of analytics is now",
    ]
    while len(bullets) < 3:
        bullets.append(defaults[len(bullets)])
    return bullets


def _try_pollinations(topic: str, news_headline: str,
                      use_style_b: bool, seed: int) -> str | None:
    try:
        prompts = STYLE_B_PROMPTS if use_style_b else STYLE_A_PROMPTS
        base    = prompts.get(
            topic,
            f"Cinematic dramatic professional technology scene about {topic}. "
            f"Male professional in dark environment."
        )
        prompt  = f"{base} {SUFFIX}"
        encoded = urllib.parse.quote(prompt)
        url     = (
            f"https://image.pollinations.ai/prompt/{encoded}"
            f"?width=1280&height=720&nologo=true&seed={seed}&model=flux"
        )
        log.info(f"   Pollinations attempt (seed={seed})...")
        r = requests.get(url, timeout=120, stream=True)
        if r.status_code != 200:
            return None
        if "image" not in r.headers.get("Content-Type", ""):
            return None
        return _save_stream(r, f"poll_{seed}.jpg", min_kb=25)
    except Exception as e:
        log.warning(f"   Pollinations error: {e}")
        return None


def _save_stream(response, filename: str, min_kb: int) -> str | None:
    try:
        date = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = IMAGE_DIR / f"{date}_{filename}"
        with open(path, "wb") as f:
            for chunk in response.iter_content(8192):
                f.write(chunk)
        size_kb = path.stat().st_size // 1024
        if size_kb < min_kb:
            log.warning(f"   Too small: {size_kb}KB")
            path.unlink(missing_ok=True)
            return None
        with open(path, "rb") as f:
            header = f.read(8)
        is_jpeg = header[:3] == b'\xff\xd8\xff'
        is_png  = header[:8] == b'\x89PNG\r\n\x1a\n'
        if not is_jpeg and not is_png:
            log.warning("   Invalid format")
            path.unlink(missing_ok=True)
            return None
        fmt = "JPEG" if is_jpeg else "PNG"
        log.info(f"   Saved: {path.name} ({size_kb}KB) [{fmt}]")
        return str(path)
    except Exception as e:
        log.warning(f"   Save error: {e}")
        return None
