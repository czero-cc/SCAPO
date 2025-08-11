# 🚀 SCAPO Quick Start Guide

## 2-Minute Setup for AI Service Optimization

### 1. Install SCAPO
```bash
git clone https://github.com/czero-cc/scapo.git
cd scapo
curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
uv pip install -e .
uv run playwright install
```

### 2. Configure LLM (Choose One)

#### Option A: OpenRouter (Recommended - Free Model!)
```bash
cp .env.example .env
# Edit .env:
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=sk-or-v1-your-key-here  # Get from openrouter.ai
OPENROUTER_MODEL=your_model
```

#### Option B: Ollama (Local)
```bash
ollama serve
ollama pull model_alias
# Edit .env:
LLM_PROVIDER=local
LOCAL_LLM_TYPE=ollama
LOCAL_LLM_URL=http://localhost:11434
LOCAL_LLM_MODEL=model_alias
```
#### Option C: LM Studio (Local)
1. Install [LM Studio](https://lmstudio.ai/)
2. Load any GGUF model
3. Start the server
4. Edit `.env`:
```bash
LLM_PROVIDER=local
LOCAL_LLM_TYPE=lmstudio
LOCAL_LLM_URL=http://localhost:1234
```

### 3. Choose Your Approach

## 🎯 Approach 1: Service Discovery (Recommended)

Extract specific optimization tips for AI services:

```bash
# Step 1: Discover services (381+ services from GitHub)
scapo scrape discover --update

# Step 2: Extract tips for specific services
scapo scrape targeted --service "Eleven Labs" --limit 20
scapo scrape targeted --service "GitHub Copilot" --limit 20

# Or batch process by category
scapo scrape batch --category video --limit 15
scapo scrape batch --max-services 3 --priority ultra
```

### Key Commands:
- `discover --update` - Find services from GitHub Awesome lists
- `targeted --service NAME` - Extract tips for one service
- `batch --category TYPE` - Process multiple services
- `update-status` - See what needs updating

## 📚 Approach 2: Legacy Sources

Use predefined sources from `sources.yaml`:

```bash
# Check available sources
scapo sources

# Scrape from specific sources
scapo scrape run --sources reddit:LocalLLaMA --limit 10
scapo scrape run --sources reddit:OpenAI hackernews --limit 20

# Interactive source selection
scapo scrape run --interactive --limit 15
```

### 4. View Results

```bash
# Interactive TUI explorer (best experience!)
scapo tui
# Use arrow keys to navigate, Enter to view, q to quit

# CLI commands
scapo models list                      # List all extracted models
scapo models search "copilot"         # Search for specific models
cat models/audio/eleven-labs/cost_optimization.md
```

## 📊 Understanding the Output

SCAPO creates organized documentation:
```
models/
├── audio/
│   └── eleven-labs/
│       ├── prompting.md         # Technical usage tips
│       ├── cost_optimization.md # Resource optimization
│       ├── pitfalls.md         # Known issues & fixes
│       └── parameters.json     # Recommended settings
```

## ⚙️ Optimization Tips

### For Better Extraction:
```bash
# More posts = better tips (15-20 minimum)
scapo scrape targeted --service "HeyGen" --limit 20

# Multiple search types
scapo scrape targeted --service "Midjourney" --max-queries 10

# Process similar services together
scapo scrape batch --category audio --limit 15
```

### Adjust Quality Threshold:
```bash
# Edit .env:
LLM_QUALITY_THRESHOLD=0.6   # Default (strict)
LLM_QUALITY_THRESHOLD=0.4   # More tips (less strict)
```

## 🔧 Common Issues & Solutions

### "No tips extracted"
```bash
# Solution: Use more posts
scapo scrape targeted --service "Service Name" --limit 25
```

### "Service not found"
```bash
# Solution: Try variations
scapo scrape targeted --service "elevenlabs" --dry-run
scapo scrape targeted --service "Eleven Labs" --dry-run
```

### "Rate limited"
```bash
# Edit .env:
SCRAPING_DELAY_SECONDS=3  # Increase delay
```

## 📈 What You'll Get

Real optimization techniques like:
- "Use `<break time='1.5s' />` tags in ElevenLabs"
- "GitHub Copilot: 300 requests/day limit"
- "HeyGen: Use 720p instead of 1080p to save 40%"
- "Character.AI: 32,000 character limit"

NOT generic advice like (but sometimes we get them... sadly):
- ❌ "Write better prompts"
- ❌ "Be patient"
- ❌ "Try different approaches"

## 🚀 Next Steps

1. **Explore extracted tips**: `scapo tui`
2. **Update regularly**: `scapo scrape update-status`
3. **Track changes**: `python scripts/git_update.py --status`
4. **Contribute**: Share your findings via PR!

## Need Help?

- Check full docs: [README.md](README.md)
- Open an issue on GitHub
- Remember: Stay Calm and Prompt On! 🧘