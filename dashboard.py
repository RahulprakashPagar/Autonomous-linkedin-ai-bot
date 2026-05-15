"""
LinkedIn Bot Dashboard
Run   : python dashboard.py
Open  : http://localhost:5000
Shows : all posts, topics, dates, success/fail status
"""

import json
import os
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template_string

app = Flask(__name__)

HISTORY_FILE = "post_history.json"

HTML = """
<!DOCTYPE html>
<html>
<head>
  <title>LinkedIn Bot Dashboard</title>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
           background: #0f172a; color: #e2e8f0; min-height: 100vh; }

    .header { background: #1e293b; border-bottom: 1px solid #334155;
              padding: 20px 32px; display: flex; align-items: center;
              justify-content: space-between; flex-wrap: wrap; gap: 10px; }
    .header h1 { font-size: 20px; font-weight: 600; color: #f1f5f9; }
    .header-right { font-size: 13px; color: #64748b; }
    .header-right a { color: #60a5fa; text-decoration: none; }
    .header-right a:hover { text-decoration: underline; }

    .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(155px, 1fr));
             gap: 14px; padding: 24px 32px 0; }
    .stat { background: #1e293b; border: 1px solid #334155;
            border-radius: 12px; padding: 16px; }
    .stat-label { font-size: 12px; color: #64748b; margin-bottom: 8px; }
    .stat-value { font-size: 26px; font-weight: 600; color: #f1f5f9; }
    .stat-value.green { color: #34d399; }
    .stat-value.red   { color: #f87171; }
    .stat-value.blue  { color: #60a5fa; }
    .stat-value.small { font-size: 14px; margin-top: 4px; font-weight: 500; }

    .section-title { padding: 24px 32px 10px;
                     font-size: 13px; font-weight: 500; color: #64748b;
                     text-transform: uppercase; letter-spacing: 0.05em; }

    .filters { padding: 0 32px 16px; display: flex; gap: 8px; flex-wrap: wrap; }
    .filter-btn { padding: 5px 14px; border-radius: 20px; font-size: 12px;
                  font-weight: 500; cursor: pointer; border: 1px solid #334155;
                  background: #1e293b; color: #94a3b8; transition: all 0.15s; }
    .filter-btn:hover { border-color: #60a5fa; color: #60a5fa; }
    .filter-btn.active { background: #1d4ed8; border-color: #1d4ed8; color: #fff; }

    .table-wrap { padding: 0 32px 40px; overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; min-width: 700px; }
    th { text-align: left; padding: 10px 14px; font-size: 11px; font-weight: 600;
         color: #475569; border-bottom: 1px solid #334155;
         white-space: nowrap; text-transform: uppercase; letter-spacing: 0.04em; }
    td { padding: 12px 14px; font-size: 13px; color: #cbd5e1;
         border-bottom: 1px solid #1a2744; vertical-align: middle; }
    tr:hover td { background: #1e293b; }

    .badge { display: inline-block; padding: 3px 10px; border-radius: 20px;
             font-size: 11px; font-weight: 600; white-space: nowrap; }
    .badge-ai   { background: #312e81; color: #a5b4fc; }
    .badge-ml   { background: #134e4a; color: #5eead4; }
    .badge-da   { background: #1e3a5f; color: #7dd3fc; }
    .badge-pbi  { background: #14532d; color: #86efac; }
    .badge-sql  { background: #431407; color: #fdba74; }
    .badge-dv   { background: #3b0764; color: #d8b4fe; }
    .badge-aida { background: #064e3b; color: #6ee7b7; }
    .badge-other{ background: #334155; color: #94a3b8; }

    .ok   { display:inline-block; background:#064e3b; color:#34d399;
            padding:3px 10px; border-radius:20px; font-size:11px; font-weight:600; }
    .fail { display:inline-block; background:#450a0a; color:#f87171;
            padding:3px 10px; border-radius:20px; font-size:11px; font-weight:600; }

    .preview { max-width: 280px; white-space: nowrap; overflow: hidden;
               text-overflow: ellipsis; color: #64748b; font-size: 12px; }
    .trend-cell { max-width: 220px; font-size: 12px; color: #94a3b8;
                  white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .num { color: #334155; font-size: 12px; }
    .words { color: #475569; font-size: 12px; text-align: center; }
    .img-badge { font-size: 11px; color: #475569;
                 background: #1e293b; border: 1px solid #334155;
                 padding: 2px 8px; border-radius: 10px; white-space: nowrap; }
    .postid { font-size: 10px; color: #334155; font-family: monospace; }
    .date-cell { white-space: nowrap; font-size: 12px; color: #94a3b8; }

    .empty { text-align: center; padding: 80px 20px; color: #334155; }
    .empty p { font-size: 15px; margin-bottom: 8px; }
    .empty code { font-size: 13px; color: #475569; }

    .today-badge { display: inline-block; background: #1d4ed8;
                   color: #bfdbfe; font-size: 10px; padding: 1px 6px;
                   border-radius: 6px; margin-left: 6px; vertical-align: middle; }
  </style>
</head>
<body>

<div class="header">
  <h1>LinkedIn Bot Dashboard</h1>
  <div class="header-right">
    Last updated: {{ now }} &nbsp;|&nbsp;
    <a href="/">Refresh</a>
  </div>
</div>

<div class="stats">
  <div class="stat">
    <div class="stat-label">Total posts</div>
    <div class="stat-value blue">{{ stats.total }}</div>
  </div>
  <div class="stat">
    <div class="stat-label">Successful</div>
    <div class="stat-value green">{{ stats.success }}</div>
  </div>
  <div class="stat">
    <div class="stat-label">Failed</div>
    <div class="stat-value red">{{ stats.failed }}</div>
  </div>
  <div class="stat">
    <div class="stat-label">This month</div>
    <div class="stat-value blue">{{ stats.this_month }}</div>
  </div>
  <div class="stat">
    <div class="stat-label">Last posted</div>
    <div class="stat-value small">{{ stats.last_date }}</div>
  </div>
  <div class="stat">
    <div class="stat-label">Top topic</div>
    <div class="stat-value small">{{ stats.top_topic }}</div>
  </div>
</div>

<div class="section-title">Post History</div>

<div class="filters">
  <button class="filter-btn active" onclick="filterTopic('all', this)">All</button>
  {% for topic in topics %}
  <button class="filter-btn" onclick="filterTopic('{{ topic }}', this)">{{ topic }}</button>
  {% endfor %}
</div>

<div class="table-wrap">
  {% if posts %}
  <table id="posts-table">
    <thead>
      <tr>
        <th>#</th>
        <th>Date &amp; Time</th>
        <th>Topic</th>
        <th>Headline</th>
        <th>Post preview</th>
        <th style="text-align:center">Words</th>
        <th>Image</th>
        <th>Status</th>
        <th>Post ID</th>
      </tr>
    </thead>
    <tbody>
      {% for p in posts %}
      <tr data-topic="{{ p.subject }}">
        <td class="num">{{ loop.revindex }}</td>
        <td class="date-cell">
          {{ p.date_fmt }}
          {% if p.is_today %}<span class="today-badge">Today</span>{% endif %}
        </td>
        <td><span class="badge {{ p.badge }}">{{ p.subject }}</span></td>
        <td class="trend-cell" title="{{ p.trend }}">{{ p.trend }}</td>
        <td class="preview" title="{{ p.content }}">{{ p.content[:130] }}...</td>
        <td class="words">{{ p.word_count }}</td>
        <td><span class="img-badge">{{ p.image_source }}</span></td>
        <td>
          {% if p.posted %}
          <span class="ok">Posted</span>
          {% else %}
          <span class="fail">Failed</span>
          {% endif %}
        </td>
        <td class="postid">
          {% if p.post_id and p.post_id != 'unknown' and p.post_id != '' %}
          {{ p.post_id[-20:] }}
          {% else %}—{% endif %}
        </td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
  {% else %}
  <div class="empty">
    <p>No posts yet.</p>
    <code>Run python main.py to post for the first time.</code>
  </div>
  {% endif %}
</div>

<script>
function filterTopic(topic, btn) {
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  document.querySelectorAll('#posts-table tbody tr').forEach(row => {
    row.style.display = (topic === 'all' || row.dataset.topic === topic) ? '' : 'none';
  });
}
setTimeout(() => location.reload(), 60000);
</script>
</body>
</html>
"""

BADGE_MAP = {
    "Artificial Intelligence":     "badge-ai",
    "Machine Learning":            "badge-ml",
    "Data Analytics":              "badge-da",
    "Power BI":                    "badge-pbi",
    "SQL":                         "badge-sql",
    "Data Visualization":          "badge-dv",
    "Use of AI in Data Analytics": "badge-aida",
}


def load_history() -> dict:
    if Path(HISTORY_FILE).exists():
        with open(HISTORY_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {"posts": []}


def safe_parse_date(date_str: str) -> tuple[datetime | None, str]:
    """Safely parse ISO date string and return (datetime, formatted string)."""
    if not date_str:
        return None, "Unknown"
    try:
        # Handle both with and without microseconds
        date_str_clean = date_str[:19]   # take only YYYY-MM-DDTHH:MM:SS
        dt = datetime.strptime(date_str_clean, "%Y-%m-%dT%H:%M:%S")
        return dt, dt.strftime("%d %b %Y  %I:%M %p")
    except Exception:
        return None, date_str[:16]


def build_stats(posts: list) -> dict:
    from collections import Counter
    now        = datetime.now()
    total      = len(posts)
    success    = sum(1 for p in posts if p.get("posted"))
    failed     = total - success
    this_month = sum(
        1 for p in posts
        if p.get("raw_date") and
        p["raw_date"].year == now.year and
        p["raw_date"].month == now.month
    )
    last_date  = posts[0]["date_fmt"] if posts else "Never"
    subjects   = [p.get("subject", "Unknown") for p in posts]
    top_topic  = Counter(subjects).most_common(1)[0][0] if subjects else "None"

    return {
        "total":      total,
        "success":    success,
        "failed":     failed,
        "this_month": this_month,
        "last_date":  last_date,
        "top_topic":  top_topic,
    }


@app.route("/")
def index():
    history = load_history()
    today   = datetime.now().date()
    posts   = []

    for p in reversed(history.get("posts", [])):
        raw_dt, date_fmt = safe_parse_date(p.get("date", ""))
        is_today = (raw_dt.date() == today) if raw_dt else False
        subject  = p.get("subject", p.get("topic", "Unknown"))
        trend    = p.get("trend", p.get("news_headline", ""))

        posts.append({
            **p,
            "subject":      subject,
            "date_fmt":     date_fmt,
            "raw_date":     raw_dt,
            "is_today":     is_today,
            "badge":        BADGE_MAP.get(subject, "badge-other"),
            "trend":        trend,
            "content":      p.get("content", ""),
            "word_count":   p.get("word_count", len(p.get("content", "").split())),
            "image_source": p.get("image_source", "unknown"),
            "post_id":      p.get("post_id", ""),
        })

    stats  = build_stats(posts)
    topics = sorted(set(p["subject"] for p in posts))
    now    = datetime.now().strftime("%d %b %Y %I:%M %p")

    return render_template_string(HTML, posts=posts, stats=stats,
                                  topics=topics, now=now)


if __name__ == "__main__":
    print("=" * 50)
    print("LinkedIn Bot Dashboard")
    print("Open in browser: http://localhost:5000")
    print("Press Ctrl+C to stop.")
    print("=" * 50)
    app.run(debug=False, port=5000)
