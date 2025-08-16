# 🚀 SCAPO Quick Start Guide

## 2-Minute Setup for AI Service Optimization

### 1. Install SCAPO
```bash
git clone https://github.com/czero-cc/scapo.git
cd scapo
curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate (if venv is not activated, you need to run scapo commands with 'uv run')
uv pip install -e .
uv run playwright install
```

### 2. Configure LLM (Choose One)

**Important:** Extraction quality varies by LLM - stronger models find more specific tips!

#### Option A: OpenRouter (Recommended - Free Model!)
```bash
cp .env.example .env
# Edit .env:
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=sk-or-v1-your-key-here  # Get from openrouter.ai
OPENROUTER_MODEL=your_model

# IMPORTANT: Update model context cache for accurate batching
scapo update-context  # Without this, defaults to 4096 tokens (poor performance!)
```

#### Option B: Ollama (Local)
```bash
ollama serve
ollama pull model_alias # or you can just configure using the recent Ollama gui 
# Edit .env:
LLM_PROVIDER=local
LOCAL_LLM_TYPE=ollama
LOCAL_LLM_URL=http://localhost:11434
LOCAL_LLM_MODEL=model_alias
# Important: Set your model's context size!
LOCAL_LLM_MAX_CONTEXT=8192  # e.g., 4096, 8192, 32768
LOCAL_LLM_OPTIMAL_CHUNK=2048  # Typically 1/4 of max
LOCAL_LLM_TIMEOUT_SECONDS=600  # 10 minutes for slower local models
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
# Important: Set your model's context size!
LOCAL_LLM_MAX_CONTEXT=8192  # Check your model's specs
LOCAL_LLM_OPTIMAL_CHUNK=2048  # Typically 1/4 of max
LOCAL_LLM_TIMEOUT_SECONDS=600  # 10 minutes for slower local models
```

### 3. Choose Your Approach

## 🎯 Approach 1: Service Discovery (Recommended)

Extract specific optimization tips for AI services:

```bash
# Step 1: Discover services (381+ services from GitHub)
scapo scrape discover --update

# Step 2: Extract tips for specific services
scapo scrape targeted --service "Eleven Labs" --limit 20 --query-limit 20
scapo scrape targeted --service "GitHub Copilot" --limit 20 --query-limit 20

# Or batch process by category
scapo scrape batch --category video --limit 20 --batch-size 3

# Process ALL priority services one by one
scapo scrape all --limit 20 --query-limit 20 --priority ultra    # Process all ultra priority services
scapo scrape all --dry-run                                       # Preview what will be processed
```

### Key Commands:
- `discover --update` - Find services from GitHub Awesome lists  
- `targeted --service NAME` - Extract tips for one service
- `batch --category TYPE` - Process ALL services in category (in batches)
- `all --priority LEVEL` - Process ALL services one by one

### Important Parameters:
- **--query-limit**: Number of search patterns (5 = quick, 20 = comprehensive)
- **--batch-size**: Services to process in parallel (3 = default balance)
- **--limit**: Posts per search (20+ recommended for best results)


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

### 5. (Optional) MCP Server - Query Your Extracted Tips

**Important:** The MCP server only reads tips you've already extracted. Run scrapers first (Steps 3-4) to populate models/ folder!

Add SCAPO as an MCP server to query your extracted tips directly in MCP-compatible clients:

```json
// Add to config.json
{
  "mcpServers": {
    "scapo": {
      "command": "npx",
      "args": ["@arahangua/scapo-mcp-server"],
      "env": {
        "SCAPO_MODELS_PATH": "/path/to/scapo/models"
      }
    }
  }
}
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

## ⚙️ Utility Commands

```bash
# Update OpenRouter model context cache (for accurate batching)
scapo update-context        # Updates if >24h old
scapo update-context -f     # Force update

# View extracted tips
scapo tui                   # Interactive TUI explorer
scapo models list           # List all extracted models
scapo models search "copilot"  # Search for specific models
```

## ⚙️ The --limit flag

```bash
# ❌ Too few posts = no useful tips found
scapo scrape targeted --service "HeyGen" --limit 5 --query-limit 5     # ~20% success rate

# ✅ Sweet spot = reliable extraction  
scapo scrape targeted --service "HeyGen" --limit 20 --query-limit 20    # ~80% success rate

# 🎯 Maximum insights = comprehensive coverage
scapo scrape targeted --service "HeyGen" --limit 30 --query-limit 20    # Finds rare edge cases
```
**Why it matters:** LLMs need multiple examples to identify patterns. More posts = higher chance of finding specific pricing, bugs, and workarounds.

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
scapo scrape targeted --service "Service Name" --limit 25 --query-limit 20
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

### "Local LLM timeout errors"
```bash
# Solution: Increase timeout for slower models
# Edit .env:
LOCAL_LLM_TIMEOUT_SECONDS=600  # 10 minutes
LOCAL_LLM_TIMEOUT_SECONDS=1200  # 20 minutes for very slow models
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
2. **Track changes**: `python scripts/git_update.py --status`
3. **Contribute**: Share your findings via PR!

## Need Help?

- Check full docs: [README.md](README.md)
- Open an issue on GitHub
- Remember: Stay Calm and Prompt On! 🧘