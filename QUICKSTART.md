# 🚀 SCAPO Quick Start Guide

## 5-Minute Setup

### 1. Install SCAPO
```bash
git clone https://github.com/czero-cc/scapo.git
cd scapo
curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
uv pip install -e .  # Install scapo CLI and dependencies
uv run playwright install  # Install browser automation
```

### 2. Choose Your LLM Provider

#### Option A: OpenRouter (Easiest - Cloud)
1. Get API key from [openrouter.ai](https://openrouter.ai/)
2. Edit `.env`:
```bash
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=sk-or-v1-your-key-here
OPENROUTER_MODEL=anthropic/claude-3.5-haiku  # Fast & cheap
```

Popular models:
- `anthropic/claude-3.5-haiku` - Fast, cheap, good quality ⭐
- `anthropic/claude-opus-4` - World's best coding model!
- `anthropic/claude-sonnet-4` - State-of-the-art performance
- `deepseek/deepseek-r1:free` - Free reasoning model!
- `openai/gpt-4-turbo` - High quality but pricier

#### Option B: Ollama (Free - Local)
1. Install [Ollama](https://ollama.com/)
2. Run: `ollama serve` then `ollama pull llama3`
3. Edit `.env`:
```bash
LLM_PROVIDER=local
LOCAL_LLM_TYPE=ollama
LOCAL_LLM_URL=http://localhost:11434
LOCAL_LLM_MODEL=llama3
```

#### Option C: LM Studio (Free - Local)
1. Install [LM Studio](https://lmstudio.ai/)
2. Load any GGUF model
3. Start the server
4. Edit `.env`:
```bash
LLM_PROVIDER=local
LOCAL_LLM_TYPE=lmstudio
LOCAL_LLM_URL=http://localhost:1234
```

> **💡 Note**: For quality filtering, use models with 7B+ parameters. Smaller models may struggle to evaluate if practices are truly model-specific.

### 3. Run Your First Scrape
```bash
# Check your setup
scapo init

# Run your first scrape
scapo scrape run --sources reddit:LocalLLaMA --limit 5

# Or with uv if not installed globally
uv run scapo scrape run --sources reddit:LocalLLaMA --limit 5

# This will:
# 1. Open a browser (headless)
# 2. Scrape Reddit posts
# 3. Extract AI-related content
# 4. Evaluate quality of practices
# 5. Save best practices to models/
```

#### Adjust Scraping Speed & Quality
```bash
# Edit .env to control scraping speed
SCRAPING_DELAY_SECONDS=0.5  # Fast (for testing)
SCRAPING_DELAY_SECONDS=2    # Default (respectful)
SCRAPING_DELAY_SECONDS=5    # Slow (very polite)

# Adjust quality filtering (if needed)
LLM_QUALITY_THRESHOLD=0.6   # Default (strict)
LLM_QUALITY_THRESHOLD=0.4   # Lower (more practices)
LLM_QUALITY_THRESHOLD=0.8   # Higher (only best practices)
```

### 4. Check Results
```bash
# List all available models
uv run scapo models list

# See what was found
ls models/text/

# Check a specific model
cat models/text/llama-3/prompting.md
```

## Common Issues

### "No practices extracted"
- Your LLM might be too conservative
- Try a different source with more AI content
- Try scraping with more posts: `scapo scrape run --sources reddit:LocalLLaMA --limit 20`

### "502 Bad Gateway" (OpenRouter)
- Check your API key
- Try a different model
- Check OpenRouter status

### "Model not found" (Ollama)
- Run `ollama list` to see available models
- Pull a model: `ollama pull llama3`

### "Timeout" (LM Studio)
- Make sure LM Studio server is running
- Check that a model is loaded
- Try http://localhost:1234/v1/models in browser

## Next Steps

- Add more sources: See [ADD_NEW_SOURCE.md](docs/ADD_NEW_SOURCE.md)
- Use with Claude: Install the MCP server
- Run scheduled scraping: `scapo schedule`
- Contribute: We need more sources and model coverage!

## Need Help?

- Check [README.md](README.md) for detailed docs
- Open an issue on GitHub
- Remember: Stay Calm and Prompt On! 🧘