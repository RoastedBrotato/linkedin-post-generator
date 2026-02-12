# LinkedIn Trend Posts Generator

A local-first pipeline that turns tech/AI trends into LinkedIn-ready posts. Includes a CLI review/publish workflow and a modern web UI backed by a FastAPI service.

## Interfaces

- **CLI**: review, approve, and publish posts from the terminal.
- **Web UI**: run research queries, generate posts, and edit them in a minimal UI.

## Features

- 🤖 Local LLM integration (Ollama; OpenAI fallback optional)
- 🧭 Trend aggregation from Hacker News, RSS feeds, Reddit, and GitHub Trending
- ✍️ Post generation pipeline with validation + source citations
- 🎨 **Automatic AI image generation** for posts using Stable Diffusion
- ✅ Manual review + approval workflow (CLI + Web UI)
- 🔗 LinkedIn OAuth 2.0 posting flow with token refresh
- 💾 Local storage (SQLite + file-based artifacts)
- 🌗 Light/Dark theme in the Web UI

## Project Structure

```
.
├── src/                     # Core application
│   ├── api/                 # FastAPI backend for the web UI
│   ├── sources/             # Trend sources (HN, RSS, Reddit, GitHub)
│   ├── llm.py               # LLM integration
│   ├── trends.py            # Trend fetch/aggregate
│   ├── post_generator.py    # Post generation pipeline
│   ├── review_cli.py        # Review/approve CLI
│   ├── publish_cli.py       # Publish CLI
│   ├── linkedin_api.py      # LinkedIn API client + OAuth
│   └── database.py          # SQLite storage + migrations
├── scripts/                 # Utilities (OAuth flow, testing, generation)
├── config/                  # Settings + prompts
├── data/                    # SQLite DB + generated posts
├── web/                     # Astro web UI
├── .env.example             # Environment template
├── requirements.txt         # Python dependencies
└── README.md
```

## Setup

### 1) Python environment

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2) Configure environment

```bash
cp .env.example .env
```

Update `.env` with your settings. The database is created automatically on first run.

### 3) Local LLM (Ollama recommended)

```bash
# Install Ollama: https://ollama.ai
ollama pull llama2
```

### 4) Image Generation (Hugging Face)

Get a free API token for automatic image generation:

```bash
# 1. Visit https://huggingface.co/settings/tokens
# 2. Create a new token
# 3. Add to .env:
HUGGINGFACE_API_TOKEN=hf_your_token_here
```

See `IMAGE_GENERATION_SETUP.md` for detailed setup instructions.

### 5) Optional: LinkedIn OAuth (publishing)

```bash
python scripts/linkedin_oauth.py
```

This stores tokens in `.env`. See `LINKEDIN_SETUP.md` for the full walkthrough.

### 6) Optional: Reddit source setup

See `REDDIT_SETUP.md` to configure Reddit API credentials.

## Running the Web UI

### Start the API (FastAPI)

```bash
uvicorn src.api.app:app --reload --port 8000
```

Environment notes:
- `WEB_UI_ORIGINS` controls CORS for the API (defaults to local dev hosts).
- The web UI reads `PUBLIC_API_BASE` to reach the API (default: `http://localhost:8000`).

### Start the Web UI (Astro)

```bash
cd web
npm install
npm run dev
```

Visit `http://localhost:4321`.

## CLI Workflow

### Generate a post from current trends

```bash
python scripts/generate_post_from_trend.py --save-to-db
```

### Review and approve posts

```bash
python src/review_cli.py
```

### Publish approved posts

```bash
python src/publish_cli.py
```

## Notes

- `.env` is ignored by git. Do not commit secrets.
- Publishing requires LinkedIn app credentials and OAuth approval.
- Web UI currently focuses on research + post creation; CLI handles review/publish.

## Roadmap (high level)

- Automation & scheduling for end-to-end runs
- Notifications (Slack/email)
- Expanded trend source controls + analytics
