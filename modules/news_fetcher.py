"""
News Fetcher — fetches real trending news headlines
Sources : NewsAPI.org (free tier — 100 req/day)
          GNews API   (free tier — 100 req/day)
          RSS feeds   (completely free, no key needed)
"""

import os
import logging
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

log = logging.getLogger(__name__)

NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "")
GNEWS_KEY   = os.getenv("GNEWS_KEY",   "")

TOPIC_QUERIES = {
    "Data Analytics":              "data analytics business intelligence",
    "Power BI":                    "Power BI Microsoft analytics",
    "Data Visualization":          "data visualization tableau analytics",
    "Artificial Intelligence":     "artificial intelligence AI OpenAI Google",
    "Use of AI in Data Analytics": "AI machine learning data analytics automation",
    "SQL":                         "SQL database DuckDB data engineering",
    "Machine Learning":            "machine learning deep learning AI model",
}

RSS_FEEDS = {
    "Artificial Intelligence":     "https://feeds.feedburner.com/oreilly/radar",
    "Machine Learning":            "https://feeds.feedburner.com/oreilly/radar",
    "Data Analytics":              "https://feeds.feedburner.com/oreilly/radar",
    "Power BI":                    "https://feeds.feedburner.com/oreilly/radar",
    "Data Visualization":          "https://feeds.feedburner.com/oreilly/radar",
    "SQL":                         "https://feeds.feedburner.com/oreilly/radar",
    "Use of AI in Data Analytics": "https://feeds.feedburner.com/oreilly/radar",
    "default":                     "https://feeds.feedburner.com/oreilly/radar",
}

FALLBACK_RSS = [
    "https://techcrunch.com/feed/",
    "https://www.technologyreview.com/feed/",
    "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml",
]


def fetch_news_headlines(topic: str) -> list[dict]:
    query = TOPIC_QUERIES.get(topic, topic)

    if NEWSAPI_KEY:
        headlines = _fetch_newsapi(query)
        if headlines:
            log.info(f"   NewsAPI: found {len(headlines)} headlines for '{topic}'")
            return headlines

    if GNEWS_KEY:
        headlines = _fetch_gnews(query)
        if headlines:
            log.info(f"   GNews: found {len(headlines)} headlines for '{topic}'")
            return headlines

    headlines = _fetch_rss(topic)
    if headlines:
        log.info(f"   RSS: found {len(headlines)} headlines for '{topic}'")
        return headlines

    log.warning(f"   All news sources failed for '{topic}'")
    return []


def _fetch_newsapi(query: str) -> list[dict]:
    try:
        from_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        r = requests.get(
            "https://newsapi.org/v2/everything",
            params={
                "q":        query,
                "from":     from_date,
                "sortBy":   "relevancy",
                "language": "en",
                "pageSize": 5,
                "apiKey":   NEWSAPI_KEY
            },
            timeout=15
        )
        r.raise_for_status()
        articles = r.json().get("articles", [])
        return [
            {
                "title":       a.get("title", ""),
                "description": a.get("description", ""),
                "url":         a.get("url", ""),
                "publishedAt": a.get("publishedAt", ""),
                "source":      a.get("source", {}).get("name", "NewsAPI")
            }
            for a in articles
            if a.get("title") and "[Removed]" not in a.get("title", "")
        ]
    except Exception as e:
        log.warning(f"   NewsAPI error: {e}")
        return []


def _fetch_gnews(query: str) -> list[dict]:
    try:
        r = requests.get(
            "https://gnews.io/api/v4/search",
            params={
                "q":      query,
                "lang":   "en",
                "max":    5,
                "sortby": "relevance",
                "token":  GNEWS_KEY
            },
            timeout=15
        )
        r.raise_for_status()
        articles = r.json().get("articles", [])
        return [
            {
                "title":       a.get("title", ""),
                "description": a.get("description", ""),
                "url":         a.get("url", ""),
                "publishedAt": a.get("publishedAt", ""),
                "source":      a.get("source", {}).get("name", "GNews")
            }
            for a in articles
            if a.get("title")
        ]
    except Exception as e:
        log.warning(f"   GNews error: {e}")
        return []


def _fetch_rss(topic: str) -> list[dict]:
    feed_url  = RSS_FEEDS.get(topic, RSS_FEEDS["default"])
    all_feeds = [feed_url] + FALLBACK_RSS

    for url in all_feeds:
        try:
            r = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
            r.raise_for_status()
            root  = ET.fromstring(r.content)
            items = []

            for item in root.findall(".//item")[:5]:
                title = item.findtext("title", "")
                desc  = item.findtext("description", "")
                link  = item.findtext("link", "")
                date  = item.findtext("pubDate", "")

                if title:
                    items.append({
                        "title":       title.strip(),
                        "description": desc.strip()[:300] if desc else "",
                        "url":         link,
                        "publishedAt": date,
                        "source":      "RSS"
                    })

            if items:
                return items

        except Exception as e:
            log.warning(f"   RSS error for {url}: {e}")
            continue

    return []