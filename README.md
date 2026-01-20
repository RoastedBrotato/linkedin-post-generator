# LinkedIn Trend Posts Generator

A Python-based scheduled bot that generates LinkedIn posts about tech and AI trends using a local LLM model, with manual review before publishing.

## Features

- 🤖 Local LLM integration (Ollama, vLLM, LM Studio)
- ⏰ Scheduled post generation (APScheduler)
- 📊 Trend fetching and analysis
- ✅ Manual review workflow before publishing
- 💾 Local storage (SQLite + file-based)
- 🔗 LinkedIn API integration

## Project Structure

```
.
├── src/                    # Core application
│   ├── __init__.py
│   ├── main.py            # Entry point
│   ├── scheduler.py       # Scheduling logic
│   ├── llm.py            # LLM integration
│   ├── trends.py         # Trend fetching
│   └── linkedin.py       # LinkedIn API
├── config/               # Configuration files
│   ├── settings.py
│   └── prompts.txt       # LLM prompts
├── data/                 # Data storage
│   ├── posts/           # Generated posts
│   └── database.db      # SQLite database
├── tests/               # Unit tests
├── .env.example         # Environment template
├── requirements.txt     # Python dependencies
└── README.md
```

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Configure environment:
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

3. Set up local LLM (e.g., Ollama):
   ```bash
   # Follow https://ollama.ai for setup
   ollama pull llama2
   ```

4. Run the application:
   ```bash
   python src/main.py
   ```

## Workflow

1. Scheduler triggers trend fetching at set intervals
2. Trends are analyzed and passed to local LLM
3. Generated posts are saved to `data/posts/` (pending review)
4. User reviews posts
5. Approved posts are published to LinkedIn

## Configuration

See `.env.example` for all available options.

## TODO

- [ ] Implement trend fetching sources
- [ ] LLM integration with Ollama
- [ ] LinkedIn API authentication
- [ ] Database schema setup
- [ ] Post review UI (optional)
