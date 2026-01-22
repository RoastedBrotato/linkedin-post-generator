# LinkedIn Trend Posts Generator - Project Plan

## Overview
Automated system for researching AI and tech trends, generating grounded LinkedIn posts with LLM, requiring human approval before publishing via LinkedIn API.

---

## Core Components

### 1. Trend Research Module (`src/trends.py`)
**Purpose**: Fetch and aggregate AI/tech trends from multiple sources

**Sub-components**:
- **Data Sources Integration**
  - RSS feeds (TechCrunch, VentureBeat, AI-specific blogs)
  - APIs (Reddit, Hacker News, Twitter/X)
  - GitHub trending repositories
  - arXiv paper abstracts (AI/ML section)
  - Google Trends API

- **Trend Aggregator**
  - Fetch content from multiple sources
  - Deduplication logic
  - Relevance filtering (AI/tech focus)
  - Trend scoring/ranking algorithm

- **Data Storage**
  - Save raw trend data to database
  - Cache mechanism to avoid re-fetching
  - Metadata tracking (source, timestamp, relevance score)

**Dependencies**: `requests`, `feedparser`, `beautifulsoup4`, `praw` (Reddit)

---

### 2. LLM Integration Module (`src/llm.py`)
**Purpose**: Generate grounded, engaging LinkedIn posts from trend data

**Sub-components**:
- **LLM Provider Interface**
  - Ollama integration (local)
  - Alternative: OpenAI API (cloud fallback)
  - Model configuration and selection

- **Prompt Engineering**
  - System prompts for LinkedIn writing style
  - Context injection (trend data, sources)
  - Few-shot examples for consistency
  - Fact-grounding instructions

- **Post Generation Pipeline**
  - Format trend data for LLM consumption
  - Generate post with citations/sources
  - Post-processing (length limits, hashtags)
  - Quality validation (readability, tone)

- **Source Citation System**
  - Include references to original sources
  - Fact-checking metadata
  - Link preservation

**Dependencies**: `ollama`, `openai` (optional), `tiktoken`

---

### 3. Content Storage & Database (`data/database.db`)
**Purpose**: Track trends, generated posts, and publishing status

**Schema Design**:
- **trends** table
  - id, title, description, source_url, fetched_at, relevance_score, category

- **posts** table
  - id, trend_id, content, status (pending/approved/rejected/published), generated_at, reviewed_at, published_at

- **sources** table
  - id, post_id, source_name, source_url, citation_type

- **publishing_history** table
  - id, post_id, platform, published_at, engagement_metrics

**Dependencies**: `sqlite3`, `sqlalchemy` (optional ORM)

---

### 4. Review & Approval Workflow
**Purpose**: Human-in-the-loop validation before publishing

**Sub-components**:
- **CLI Review Interface** (MVP)
  - Display pending posts
  - Show source citations
  - Approve/Reject/Edit options
  - Queue management

- **Web UI** (Future enhancement)
  - Dashboard for pending posts
  - Inline editing
  - Preview mode
  - Batch operations

- **Approval Logic**
  - Status tracking (pending → approved/rejected)
  - Edit history
  - Reviewer comments/notes

**Dependencies**: `rich` (CLI formatting), `flask/fastapi` (web UI - optional)

---

### 5. LinkedIn API Integration (`src/linkedin_api.py`)
**Purpose**: Authenticate and publish approved posts to LinkedIn

**Sub-components**:
- **OAuth 2.0 Authentication**
  - Authorization code flow
  - Token storage and refresh
  - Credential management

- **Publishing API**
  - Create text posts
  - Add links/media (optional)
  - Error handling and retries
  - Rate limiting compliance

- **Post Verification**
  - Confirm successful publication
  - Retrieve post URL
  - Update database status

**Dependencies**: `requests-oauthlib`, `python-linkedin-api`

---

### 6. Scheduling System (`src/scheduler.py`)
**Purpose**: Automate trend fetching and post generation

**Sub-components**:
- **Job Scheduler**
  - Periodic trend fetching (e.g., every 6 hours)
  - Post generation workflow
  - Configurable intervals

- **Task Queue**
  - Async task execution
  - Error handling and retries
  - Job logging

- **Notification System**
  - Alert when posts are ready for review
  - Error notifications
  - Daily summary

**Dependencies**: `APScheduler`, `celery` (optional for distributed tasks)

---

### 7. Configuration Management (`config/settings.py`)
**Purpose**: Centralized configuration for all modules

**Configuration Areas**:
- LLM settings (model, temperature, max_tokens)
- Trend sources (enabled/disabled, refresh intervals)
- LinkedIn API credentials
- Scheduling intervals
- Content policies (min/max post length, hashtag limits)
- Logging configuration

**Dependencies**: `pydantic`, `python-dotenv`

---

### 8. Logging & Monitoring
**Purpose**: Track system behavior and debug issues

**Components**:
- Structured logging (JSON format)
- Error tracking and alerting
- Performance metrics
- Audit trail for approvals/publications

**Dependencies**: `loguru`, `sentry-sdk` (optional)

---

## Execution Plan

### Phase 1: Foundation (Week 1)
**Goal**: Set up core infrastructure and data pipeline

1. **Database Schema Implementation**
   - Create SQLite schema (trends, posts, sources tables)
   - Write database utility functions (CRUD operations)
   - Add migration support

2. **Configuration System**
   - Finalize `settings.py` with Pydantic models
   - Set up `.env` file structure
   - Create config validation

3. **Logging Infrastructure**
   - Configure loguru
   - Set up log rotation
   - Add structured logging helpers

**Deliverable**: Working database + config system

---

### Phase 2: Trend Research (Week 2)
**Goal**: Build trend fetching and aggregation

4. **Trend Sources Integration**
   - Implement RSS feed parser (TechCrunch, VentureBeat, etc.)
   - Add Hacker News API integration
   - Add Reddit API integration (r/MachineLearning, r/artificial)
   - Add GitHub trending scraper

5. **Trend Processing Pipeline**
   - Build aggregation logic
   - Implement deduplication
   - Create relevance scoring algorithm
   - Store trends in database

6. **Testing & Validation**
   - Unit tests for each source
   - Validate data quality
   - Test edge cases (API failures, malformed data)

**Deliverable**: Automated trend fetching system

---

### Phase 3: LLM Integration (Week 3)
**Goal**: Generate high-quality, grounded LinkedIn posts

7. **LLM Setup**
   - Install and configure Ollama
   - Test model performance (llama2, mistral, etc.)
   - Set up fallback to OpenAI API

8. **Prompt Engineering**
   - Write system prompts for LinkedIn style
   - Create few-shot examples
   - Add source citation instructions
   - Test and iterate on prompt quality

9. **Post Generation Pipeline**
   - Build trend → post conversion logic
   - Implement source citation system
   - Add post validation (length, format)
   - Store generated posts in database

10. **Quality Assurance**
    - Test with various trend types
    - Validate fact grounding
    - Check citation accuracy

**Deliverable**: Working LLM post generation

---

### Phase 4: Review Workflow (Week 4)
**Goal**: Enable human review and approval

11. **CLI Review Tool**
    - Build interactive CLI with `rich` library
    - Display posts with formatting
    - Show source citations
    - Implement approve/reject/edit actions

12. **Edit Capabilities**
    - In-place editing before approval
    - Track edit history
    - Re-validate edited posts

13. **Queue Management**
    - List all pending posts
    - Filter by status
    - Bulk operations

**Deliverable**: Functional review interface

---

### Phase 5: LinkedIn Publishing (Week 5)
**Goal**: Publish approved posts to LinkedIn

14. **LinkedIn OAuth Setup**
    - Register LinkedIn app
    - Implement OAuth 2.0 flow
    - Store/refresh access tokens securely

15. **Publishing API Integration**
    - Implement post creation API
    - Add error handling and retries
    - Handle rate limits

16. **Post-Publishing Actions**
    - Update database status
    - Store post URL and metadata
    - Log publishing events

**Deliverable**: End-to-end publishing capability

---

### Phase 6: Automation & Scheduling (Week 6)
**Goal**: Fully automate the workflow

17. **Scheduler Implementation**
    - Configure APScheduler jobs
    - Set up trend fetching schedule (every 6 hours)
    - Set up post generation schedule (daily)

18. **Notification System**
    - Alert when posts need review (email/Slack)
    - Error notifications
    - Daily summary reports

19. **Error Recovery**
    - Retry logic for failed jobs
    - Dead letter queue for persistent failures
    - Graceful degradation

**Deliverable**: Fully automated system

---

### Phase 7: Testing & Refinement (Week 7)
**Goal**: Ensure reliability and quality

20. **End-to-End Testing**
    - Full workflow testing (trend → post → approval → publish)
    - Integration tests for all modules
    - Load testing (multiple trends, concurrent posts)

21. **Quality Improvements**
    - Refine prompts based on generated content
    - Tune trend relevance scoring
    - Optimize LLM parameters

22. **Documentation**
    - API documentation
    - User guide for review process
    - Troubleshooting guide
    - Deployment instructions

**Deliverable**: Production-ready system

---

### Phase 8: Enhancements (Week 8+)
**Goal**: Add advanced features

23. **Web Dashboard** (Optional)
    - Build Flask/FastAPI web interface
    - Rich text editor for posts
    - Analytics dashboard
    - Calendar view for scheduled posts

24. **Advanced Features**
    - Multi-platform support (Twitter, Medium)
    - Image generation for posts (DALL-E, Stable Diffusion)
    - A/B testing for post variations
    - Engagement tracking and analysis

25. **ML Improvements**
    - Fine-tune LLM on your writing style
    - Trend prediction model
    - Optimal posting time prediction
    - Engagement optimization

**Deliverable**: Enhanced system with advanced features

---

## Success Metrics

- **Trend Quality**: 80%+ of fetched trends are relevant to AI/tech
- **Post Quality**: 70%+ of generated posts approved without edits
- **Publishing Success**: 95%+ success rate for LinkedIn publishing
- **Automation**: System runs for 7 days without manual intervention
- **Grounding**: 100% of posts include source citations

---

## Technical Decisions

### Why Local LLM?
- Cost-effective for high volume
- Data privacy (trends/drafts stay local)
- Customization and fine-tuning
- Fallback to cloud API when needed

### Why SQLite?
- Simple setup, no external database server
- Sufficient for single-user application
- Easy to backup and migrate
- Can upgrade to PostgreSQL later if needed

### Why APScheduler?
- Lightweight, no message broker needed
- Sufficient for single-machine deployment
- Easy to configure and debug
- Can migrate to Celery for distributed tasks

---

## Risk Mitigation

### API Rate Limits
- Implement exponential backoff
- Cache responses where possible
- Monitor rate limit headers
- Use multiple data sources

### LLM Hallucination
- Always include source citations
- Require human approval
- Implement fact-checking prompts
- Track hallucination incidents

### LinkedIn API Changes
- Monitor LinkedIn developer updates
- Maintain error logs
- Have manual posting fallback
- Version lock API dependencies

### Data Quality
- Validate all external data
- Implement content filters
- Regular audits of generated posts
- Feedback loop for improvements

---

## Development Principles

1. **Start Simple**: Build MVP first, enhance later
2. **Human in the Loop**: Always require approval before publishing
3. **Source Everything**: Every claim must have a citation
4. **Fail Gracefully**: Handle errors without crashing
5. **Log Everything**: Comprehensive logging for debugging
6. **Test Continuously**: Write tests as you build
7. **Iterate on Quality**: Refine prompts and filters based on results

---

## Next Immediate Steps

1. Set up virtual environment and install dependencies
2. Create database schema and test basic CRUD
3. Implement first trend source (Hacker News API - simplest)
4. Write initial LLM prompt and test with sample trend
5. Build minimal CLI review tool
6. Test end-to-end with manual trigger (before scheduling)

---

**Last Updated**: 2026-01-20
**Status**: Planning Phase
**Current Phase**: Phase 0 - Foundation Setup
