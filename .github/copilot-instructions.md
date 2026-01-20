# GitHub Copilot Instructions

This project generates LinkedIn posts about tech and AI trends using a local LLM model.

## Project Overview
- **Purpose**: Scheduled bot for generating LinkedIn posts with manual review workflow
- **Stack**: Python, Local LLM (Ollama/vLLM), APScheduler, LinkedIn API
- **Status**: MVP - Early development

## Architecture
- `src/`: Core application modules (scheduler, LLM, trends, LinkedIn)
- `config/`: Configuration and prompts
- `data/`: Local storage for posts and database
- `tests/`: Unit tests

## Current TODOs
- [ ] Implement trend fetching (Hacker News, ArXiv, Reddit, etc.)
- [ ] Set up LLM integration with Ollama
- [ ] LinkedIn API authentication and publishing
- [ ] Database schema setup
- [ ] Post review workflow

## Development Tips
- Use `requirements.txt` for dependency management
- Configuration via `.env` file
- LLM runs locally - see setup instructions in README
- Manual review before LinkedIn publishing
