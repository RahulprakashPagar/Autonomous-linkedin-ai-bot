# LinkedIn AI Content Automation

An end to end AI powered LinkedIn automation system that discovers real trending news, generates professional LinkedIn content, creates AI images and avatar videos, publishes directly to LinkedIn, and monitors the entire workflow automatically.

Built for personal branding, AI driven social media automation, and professional LinkedIn growth.

---

# Features

## Real Time Trending News Detection
Fetches fresh headlines daily from:
- NewsAPI
- GNews
- RSS feeds

Filters:
- Fake news
- Clickbait
- Entertainment content
- Duplicate headlines
- Low quality articles

---

## AI Powered LinkedIn Content Generation
Generates:
- High engagement LinkedIn posts
- Human sounding storytelling
- Professional insights
- Scroll stopping hooks
- Comment driving questions
- Relevant hashtags

Supports multiple writing styles:
- Storytelling
- Thought leadership
- Data breakdown
- Practical tips

---

## AI Generated Images
Automatically creates cinematic LinkedIn visuals using:
- DALL E 3
- Pollinations AI fallback

Features:
- Dynamic image styles
- Cinematic backgrounds
- Text overlay mode
- Retry handling
- Professional branding visuals

---

## AI Avatar Video Generation
Every Monday the system creates:
- AI talking head videos
- Voice narrated content
- 60 second LinkedIn videos

Powered by:
- D ID Talks API
- GPT generated scripts
- AI voice narration

---

## LinkedIn Auto Publishing
Automatically publishes:
- Image posts
- Video posts
- Text only posts

Supports:
- LinkedIn Image API
- LinkedIn Video API
- Media uploads
- Upload retries
- Automatic image resizing

---

## Smart Duplicate Protection
Custom Post Guard system prevents:
- Duplicate headlines
- Repeated subjects
- Reused content
- Spam style posting

Includes:
- Fingerprint tracking
- Cooldown windows
- Headline similarity detection

---

## Telegram Monitoring System
Real time Telegram notifications for:
- Successful posts
- Failed posts
- Token expiry alerts
- Post previews
- Pipeline status

---

## Comment Auto Responder
Automatically:
- Fetches new LinkedIn comments
- Generates intelligent reply suggestions
- Sends approval flow to Telegram
- Allows one tap approval before replying

---

## Live Dashboard
Flask powered dashboard to monitor:
- Published posts
- Success and failure logs
- Topic tracking
- Trend tracking
- AI generated content history

---

# Technologies Used

## Programming Language
- Python

## AI and LLMs
- OpenAI GPT 4o Mini
- Google Gemini Flash
- DALL E 3
- D ID Talks API

## Backend Framework
- Flask

## APIs and Services
- LinkedIn API
- Telegram Bot API
- NewsAPI
- GNews API

## Image Processing
- Pillow

## Data Handling
- JSON
- RSS XML feeds

## HTTP and API Communication
- Requests

---

# System Architecture

```text
Stage 1
Trending News Detection
        ↓
Stage 2
AI Content Generation
        ↓
Stage 3
AI Image or Video Generation
        ↓
Stage 4
LinkedIn Publishing
        ↓
Stage 5
Duplicate Detection and Tracking
        ↓
Stage 6
Telegram Notifications
```

---

# Run the Bot

## Main Pipeline

```bash
python main.py
```

---

## Dashboard

```bash
python dashboard.py
```

Open:
```text
http://localhost:5000
```

---

## Comment Responder

```bash
python comment_responder.py
```

---

# Automation Workflow

## Monday
- AI avatar video generation
- Voice narration
- Video publishing

## Tuesday to Sunday
- AI image generation
- LinkedIn image posts

---

# Safety Features

The project includes:
- Internet connectivity checks
- Retry handling
- Headline verification
- Duplicate prevention
- Telegram alerts
- Token expiry monitoring
- Content fingerprinting
- Fallback content generation

---

# Future Improvements

Potential future enhancements:
- Twitter/X integration
- Instagram automation
- AI analytics dashboard
- Engagement prediction
- AI generated carousel posts
- Multi language support

---

# Use Cases

- Personal branding automation
- AI content marketing
- LinkedIn growth automation
- Thought leadership systems
- Social media automation
- Professional AI workflows

---

# Author

## Rahul Prakash Pagar

Data and Business Analyst  
MSc in Business Analytics  
Dublin, Ireland

### Connect with Me

- LinkedIn: www.linkedin.com/in/rahul-pagar1993
- GitHub: github.com/RahulprakashPagar
- Email: rahulpagar423@gmail.com

---

# License

MIT License

You are free to use, modify, and distribute this project with attribution.

---

# Acknowledgements

Special thanks to:
- OpenAI
- Google Gemini
- LinkedIn Developers Platform
- D ID
- NewsAPI
- Flask community

---

# Disclaimer

This project is intended for educational and professional automation purposes only.

Users are responsible for complying with:
- LinkedIn API policies
- OpenAI usage policies
- Platform rate limits
- Content publishing regulations
