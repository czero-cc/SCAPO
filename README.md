# SOTA Practices

A programmatically queryable knowledge base for AI model best practices. This repository provides a centralized, up-to-date collection of prompting strategies, parameter recommendations, and usage guidelines for various generative AI models.

## Overview

SOTA Practices allows LLM-powered applications to fetch specific best practice files for AI models in real-time. When a user is working with a specific model (e.g., GPT-4, Stable Diffusion, wan2.2), applications can query this repository to get:

- Optimal prompt structures and examples
- Recommended parameter settings
- Common pitfalls to avoid
- Model-specific tips and tricks

## Features

- **RESTful API** for querying model best practices
- **Web scraping pipeline** to gather practices from Reddit, Discord, and forums
- **Structured data format** for consistent access across different models
- **Version tracking** and source citations for all practices
- **High-performance** architecture with caching and async operations
- **Comprehensive monitoring** with Prometheus and Grafana

## Quick Start

### Prerequisites

- Python 3.12+
- PostgreSQL 14+ (optional, SQLite works for development)
- Redis 6+ (optional, for caching)
- Docker & Docker Compose (optional)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/fiefworks/sota-practices.git
cd sota-practices
```

2. Install uv package manager:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

3. Create and activate virtual environment:
```bash
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

4. Install dependencies:
```bash
uv pip install -r requirements.txt
```

5. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your credentials
```

6. Start the API server:
```bash
uvicorn src.api.server:app --reload
```

The API will be available at `http://localhost:8000`

### Docker Deployment

For production deployment using Docker:

```bash
docker-compose up -d
```

This will start:
- API server on port 8000
- PostgreSQL database on port 5432
- Redis cache on port 6379
- Celery workers for background tasks
- Prometheus metrics on port 9090
- Grafana dashboards on port 3000

## API Usage

### Authentication

All API endpoints require an API key:

```bash
curl -H "X-API-Key: your_api_key" http://localhost:8000/api/v1/models/
```

### Example Endpoints

#### List all models
```bash
GET /api/v1/models/
```

#### Get all practices for a model
```bash
GET /api/v1/models/text/gpt-4/all
```

#### Get prompting guide
```bash
GET /api/v1/models/text/gpt-4/prompting
```

#### Get parameter recommendations
```bash
GET /api/v1/models/video/wan2.2/parameters
```

#### Search models
```bash
GET /api/v1/models/search?q=stable+diffusion
```

## Repository Structure

```
sota-practices/
├── models/                 # Model best practices files
│   ├── text/              # Text generation models
│   ├── image/             # Image generation models
│   ├── video/             # Video generation models
│   └── audio/             # Audio generation models
├── src/                   # Source code
│   ├── api/               # FastAPI application
│   ├── scrapers/          # Web scraping modules
│   ├── core/              # Core functionality
│   └── services/          # Business logic
├── tests/                 # Test suite
└── docker-compose.yml     # Docker configuration
```

## Configured Scraping Sources

The system automatically scrapes from 31+ sources:

- **Reddit** (12 subreddits): r/PromptEngineering, r/LocalLLaMA, r/StableDiffusion, r/OpenAI, r/ClaudeAI, r/midjourney, etc.
- **GitHub** (6 repositories): DAIR-AI Prompt Engineering Guide, Awesome lists, Brex practices, OpenAI Cookbook
- **Forums** (3): OpenAI Community, Hugging Face, AIPRM
- **News**: Hacker News AI discussions
- **APIs**: LangChain Hub, Hugging Face Datasets, Papers with Code
- **Discord** (3 servers - requires bot setup)
- **RSS Feeds** (3): DEV.to, Towards Data Science, AI Alignment Forum

All sources are configured in `src/scrapers/sources.yaml`

## LLM Processing

The system includes an intelligent LLM processing layer to clean noisy scraped content. See [docs/LLM_PROCESSING.md](docs/LLM_PROCESSING.md) for details.

- **Local LLM** support via Ollama/LM Studio
- **Cloud LLM** support via OpenRouter
- Automatic context window management
- Character-based limits for better UX
- Structured extraction of practices

### Character Limits

Instead of token counts, we use character limits for better user experience:

```bash
# CLI with custom character limit
python -m src.scrapers.run reddit --llm-max-chars 8000

# API with character limit
curl -X POST "http://localhost:8000/api/v1/scrapers/run?source=reddit&llm_max_chars=5000"
```

## Development

### Running Tests

```bash
make test
```

### Code Quality

```bash
make lint    # Run linting
make format  # Format code
```

### Adding New Models

1. Create a directory under the appropriate category:
```bash
mkdir -p models/text/new-model/examples
```

2. Add required files:
- `prompting.md` - Prompting guide
- `parameters.json` - Parameter recommendations
- `pitfalls.md` - Common mistakes
- `metadata.json` - Model metadata
- `examples/prompts.json` - Example prompts

### Running Scrapers

```bash
# Scrape specific source
python -m src.scrapers.run reddit --limit 100
python -m src.scrapers.run github --limit 50

# With custom LLM character limit
python -m src.scrapers.run reddit --limit 10 --llm-max-chars 8000

# Scrape all sources
python -m src.scrapers.run all --limit 100

# Using make commands (if configured)
make scrape-reddit
make scrape-all
```

### Using the CLI

```bash
# Install CLI
pip install -e .

# Use CLI commands
sota models list
sota models search gpt
sota scrape run reddit --limit 50
sota scrape status
```

## Current Implementation Status

### Working Features
- ✅ Model service with example models (GPT-4, Stable Diffusion, wan2.2)
- ✅ GitHub scraper for awesome lists
- ✅ Reddit scraper (requires API credentials)
- ✅ Forum scraper for Discourse-based forums
- ✅ Hacker News scraper
- ✅ RESTful API with FastAPI
- ✅ CLI interface
- ✅ Model discovery system

### Pending Features
- ⏳ Database migrations (Alembic configured but not initialized)
- ⏳ Discord scraper (requires bot setup)
- ⏳ Celery background tasks
- ⏳ Prometheus/Grafana monitoring dashboards

### Notes
- For development, the system uses SQLite instead of PostgreSQL
- Redis is optional; the system works without it
- The `/api` and `/scripts` root folders are empty (actual code is in `/src`)

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Fiefworks, Inc. - Project sponsor
- Open source community for AI best practices
- Contributors from Reddit, Discord, and various AI communities

## Contact

For questions or support, please contact: info@czero.cc