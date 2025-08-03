# LLM Processing Pipeline

## Overview

The SOTA Practices system includes an intelligent LLM processing layer that cleans and structures raw scraped content. This addresses the key issue that community content is often noisy, unstructured, and contains irrelevant information.

## The Problem with Raw Content

Raw scraped content typically includes:
- Off-topic discussions ("Thanks for the gold!")
- Conflicting advice
- Unverified claims
- Poor formatting
- Mixed quality information

Example raw Reddit post:
```
Finally got GPT-4 to stop hallucinating! Temperature = 0 is KEY!
EDIT: Wow this blew up!
EDIT 2: RIP my inbox lol
Also try top_p = 0.1...
```

## LLM Processing Solution

The LLM processor:
1. **Extracts** actionable practices from noise
2. **Structures** information into consistent format
3. **Validates** claims and assigns confidence scores
4. **Categorizes** practices (prompting, parameters, pitfalls, tips)
5. **Links** practices to specific models

## Configuration

### Local LLM (Ollama) - Recommended for Privacy

```bash
# Install Ollama
curl https://ollama.ai/install.sh | sh

# Pull a model (auto-detects context window)
ollama pull llama3       # 8K context
ollama pull mistral      # 8K context  
ollama pull mixtral      # 32K context
ollama pull phi3         # 128K context

# Start Ollama server
ollama serve
```

Configure in `.env`:
```env
LLM_PROVIDER=local
LOCAL_LLM_URL=http://localhost:11434
LOCAL_LLM_MODEL=llama3
LOCAL_LLM_TYPE=ollama
LLM_PROCESSING_ENABLED=true
```

### Local LLM (LM Studio)

1. Download LM Studio: https://lmstudio.ai/
2. Download a model (e.g., Llama 3, Mistral)
3. Start the server (usually on port 1234)

Configure in `.env`:
```env
LLM_PROVIDER=local
LOCAL_LLM_URL=http://localhost:1234
LOCAL_LLM_MODEL=your-model-name
LOCAL_LLM_TYPE=lmstudio
```

### Cloud LLM (OpenRouter)

1. Get API key from https://openrouter.ai/
2. Configure in `.env`:

```env
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=your-api-key
OPENROUTER_MODEL=anthropic/claude-3-haiku  # Fast & cheap
```

## Context Window Management

The system automatically manages context windows for local models:

| Model | Context Window | Auto-detected |
|-------|---------------|---------------|
| llama2 | 4,096 | ✅ |
| llama3 | 8,192 | ✅ |
| llama3.1 | 128,000 | ✅ |
| mistral | 8,192 | ✅ |
| mixtral | 32,768 | ✅ |
| phi3 | 128,000 | ✅ |
| codellama | 16,384 | ✅ |

For unknown models, it defaults to 4,096 tokens and logs a warning.

## Output Format

Processed practices are structured as:

```json
{
  "practice_type": "parameter",
  "content": "Set temperature to 0 for factual tasks",
  "confidence": 0.9,
  "applicable_models": ["gpt-4", "gpt-3.5-turbo"],
  "source_quality": "high",
  "extracted_parameters": {
    "temperature": 0,
    "top_p": 0.1
  },
  "example_code": null,
  "warnings": []
}
```

## Processing Flow

1. **Scraper** collects raw posts
2. **Initial extraction** uses regex patterns
3. **LLM processor** enhances top posts:
   - Truncates to fit context window
   - Sends structured prompt
   - Parses JSON response
   - Handles errors gracefully
4. **Results** merged into final practices

## Usage Examples

### Test LLM Processing
```bash
python examples/test_llm_processing.py
```

### Run Scraper with LLM
```bash
# With LLM processing enabled (default)
python -m src.scrapers.run reddit --limit 10

# Disable LLM processing
LLM_PROCESSING_ENABLED=false python -m src.scrapers.run reddit
```

### API Response with LLM-Enhanced Data
```json
{
  "practices": {
    "prompting": [...],
    "parameters": [...],
    "llm_processed": [
      {
        "type": "parameter",
        "content": "Use temperature=0 for factual accuracy",
        "confidence": 0.95,
        "models": ["gpt-4"],
        "source_post": "reddit_abc123"
      }
    ]
  }
}
```

## Cost Considerations

- **Local LLM**: Free, private, but requires GPU/CPU resources
- **OpenRouter**: 
  - Claude 3 Haiku: ~$0.25 per million tokens
  - Processes ~5 posts per scrape
  - Estimated: <$0.01 per scraping run

## Best Practices

1. **Use local LLMs** for privacy and cost savings
2. **Choose appropriate models**:
   - Small models (7B) for basic extraction
   - Larger models (70B+) for nuanced understanding
3. **Monitor context usage** - logs show when truncation occurs
4. **Validate output** - LLM extraction isn't perfect
5. **Cache results** to avoid reprocessing

## Troubleshooting

### Ollama not responding
```bash
# Check if running
curl http://localhost:11434/api/tags

# Restart
ollama serve
```

### Context window errors
- Check model context size in logs
- Use a model with larger context
- Reduce `MAX_POSTS_PER_SCRAPE`

### Poor extraction quality
- Try a different model
- Adjust the extraction prompt
- Increase confidence thresholds

## Character Limit Configuration

For better UX, the system uses character limits instead of token counts:

### Configuration Options

```env
# In .env file
LLM_MAX_CHARS=4000        # Default: 4000 chars (about 1000 tokens)
LLM_CHAR_HARD_LIMIT=50000 # Safety limit to prevent huge payloads
```

### CLI Usage

```bash
# Use custom character limit
python -m src.scrapers.run reddit --limit 10 --llm-max-chars 8000

# Small limit for fast processing
python -m src.scrapers.run reddit --llm-max-chars 2000

# Large limit for detailed extraction
python -m src.scrapers.run github --llm-max-chars 10000
```

### API Usage

```bash
# Trigger scraping with custom character limit
curl -X POST "http://localhost:8000/api/v1/scrapers/run?source=reddit&limit=10&llm_max_chars=5000"
```

### Character Limit Guidelines

| Use Case | Recommended Chars | Notes |
|----------|------------------|-------|
| Quick extraction | 2000-3000 | Fast, catches main points |
| Standard processing | 4000-6000 | Good balance (default) |
| Detailed analysis | 8000-12000 | Slower but thorough |
| Maximum extraction | 15000-20000 | For critical content |

The system will:
- Truncate content to fit the limit
- Add `[Content truncated...]` marker
- Log when truncation occurs
- Never exceed the hard limit (50K chars)

## Future Enhancements

1. **Fine-tuned models** specifically for practice extraction
2. **Embedding-based** relevance scoring
3. **Multi-pass extraction** for complex content
4. **Automatic quality validation**
5. **Smart chunking** to process long content in parts