# SCAPO Configuration Guide

This guide covers all configuration options available in SCAPO.

## Environment Variables

Create a `.env` file in the project root (copy from `.env.example`):

```bash
cp .env.example .env
```

### LLM Provider Configuration

#### OpenRouter (Cloud-based)
```bash
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=your_api_key_here
OPENROUTER_MODEL=anthropic/claude-3.5-haiku  # Fast & affordable
```

Popular models:
- `anthropic/claude-3.5-haiku` - Fast, cheap, good quality
- `anthropic/claude-opus-4` - World's best coding model
- `openai/gpt-4-turbo` - High quality
- `deepseek/deepseek-r1:free` - Free reasoning model!

#### Ollama (Local)
```bash
LLM_PROVIDER=local
LOCAL_LLM_TYPE=ollama
LOCAL_LLM_URL=http://localhost:11434
LOCAL_LLM_MODEL=llama3
```

#### LM Studio (Local)
```bash
LLM_PROVIDER=local
LOCAL_LLM_TYPE=lmstudio
LOCAL_LLM_URL=http://localhost:1234
# Model is selected in LM Studio GUI
```

### Processing Limits

Control how much content is sent to LLMs:

```bash
LLM_MAX_CHARS=4000        # User-friendly limit (default)
LLM_CHAR_HARD_LIMIT=50000 # Absolute safety limit
```

Lower values = faster processing, lower costs
Higher values = more context, better extraction

### Quality Filtering

SCAPO uses LLM-based quality evaluation to filter out generic or irrelevant practices:

```bash
LLM_QUALITY_THRESHOLD=0.6  # Minimum quality score (0.0-1.0)
```

Each extracted practice is evaluated for:
- **Relevance**: Is it specific to the claimed model?
- **Specificity**: Does it provide model-specific guidance?
- **Actionability**: Can users actually apply this advice?

Recommended values:
- `0.4` - Lenient (more practices, may include generic advice)
- `0.6` - Balanced (default - filters obvious mismatches)
- `0.8` - Strict (only high-quality, model-specific practices)
- `0.9` - Very strict (only exceptional practices)

### Scraping Configuration

#### Speed Control
```bash
SCRAPING_DELAY_SECONDS=2  # Delay between pages/posts
```

Recommended values:
- `0.5` - Fast mode (testing only!)
- `2.0` - Default (balanced)
- `5.0` - Slow mode (very respectful)
- `10.0` - Ultra-slow (for sensitive sites)

#### Scheduled Scraping
```bash
SCRAPING_INTERVAL_HOURS=6  # How often to run scheduled scraping
```

To use scheduled scraping:
```bash
# Set your desired interval in .env
SCRAPING_INTERVAL_HOURS=12  # Run twice daily

# Start the scheduler
python -m src.cli schedule
```

#### Content Limits
```bash
MAX_POSTS_PER_SCRAPE=100   # Max posts per source
MIN_UPVOTE_RATIO=0.8       # Reddit quality filter (0.0-1.0)
```

### Logging Configuration

```bash
LOG_LEVEL=INFO      # Options: DEBUG, INFO, WARNING, ERROR
LOG_FORMAT=json     # Options: json, text
```

## Performance Tuning

### Fast Testing Setup
For development and testing:
```bash
SCRAPING_DELAY_SECONDS=0.5
MAX_POSTS_PER_SCRAPE=5
LLM_MAX_CHARS=2000
```

### Production Setup
For regular use:
```bash
SCRAPING_DELAY_SECONDS=2
MAX_POSTS_PER_SCRAPE=50
LLM_MAX_CHARS=4000
```

### Respectful Scraping Setup
For sensitive sites or when being extra polite:
```bash
SCRAPING_DELAY_SECONDS=5
MAX_POSTS_PER_SCRAPE=20
```

## OpenRouter Rate Limiting

The pipeline automatically handles OpenRouter rate limits with:
- Exponential backoff (1s, 2s, 4s...)
- Respects Retry-After headers
- Minimum 0.5s between requests
- Maximum 3 retry attempts

If you're hitting rate limits frequently, consider:
1. Increasing `SCRAPING_DELAY_SECONDS`
2. Decreasing `MAX_POSTS_PER_SCRAPE`
3. Using a different OpenRouter model
4. Switching to local LLM (Ollama/LM Studio)

## Local LLM Performance

For best local LLM performance:

### Ollama
```bash
# Use quantized models
ollama pull llama3:8b-instruct-q4_0  # Smaller, faster
ollama pull qwen2.5:14b              # Larger, better quality

# Set appropriate context window
LLM_MAX_CHARS=3000  # Don't overwhelm local models
```

### LM Studio
- Enable GPU acceleration
- Use GGUF quantized models
- Adjust context length in GUI
- Monitor RAM/VRAM usage

## Troubleshooting

### "429 Too Many Requests" Errors
```bash
# Increase delays
SCRAPING_DELAY_SECONDS=5

# Or switch to local LLM
LLM_PROVIDER=local
```

### Slow Processing
```bash
# Reduce content sent to LLM
LLM_MAX_CHARS=2000

# Use faster model
OPENROUTER_MODEL=anthropic/claude-3.5-haiku
```

### Memory Issues (Local LLM)
```bash
# Use smaller model or reduce context
LLM_MAX_CHARS=1500
LOCAL_LLM_MODEL=llama3:7b  # Instead of 70b
```

## Environment Variable Priority

Variables are loaded in this order:
1. System environment variables
2. `.env` file
3. Default values in `config.py`

To override temporarily:
```bash
SCRAPING_DELAY_SECONDS=0.5 python -m src.cli scrape run
```