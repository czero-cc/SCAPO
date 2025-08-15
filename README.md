# 🧘 Stay Calm and Prompt On (SCAPO)

<div align="center">

![AI Prompting Challenges](assets/guy_freaking_out1.png)

**The Community-Driven Knowledge Base for AI Service Optimization**

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Made with Love](https://img.shields.io/badge/Made%20with-❤️-red.svg)](https://github.com/czero-cc/scapo)
[![No API Keys](https://img.shields.io/badge/API%20Keys-Not%20Required-brightgreen.svg)]()<br/>
[![LLM Powered](https://img.shields.io/badge/LLM-Powered-blue.svg)]()
[![Browser Magic](https://img.shields.io/badge/Scraping-Browser%20Based-orange.svg)]()
[![MCP Ready](https://img.shields.io/badge/Claude-MCP%20Ready-purple.svg)]()
[![PRs Welcome](https://img.shields.io/badge/PRs-Welcome-brightgreen.svg)](CONTRIBUTING.md)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

### 🎯 Real usage tips from real users for AI services

If you find **SCAPO** useful, please consider giving it a star on GitHub!  
Your support helps the project grow and reach more people.  

[![Star on GitHub](https://img.shields.io/github/stars/czero-cc/SCAPO?style=social)](https://github.com/czero-cc/SCAPO/stargazers)

</div>

## 🤔 What is SCAPO?

**Keywords**: AI cost optimization, prompt engineering, LLM tips, OpenAI, Claude, Anthropic, Midjourney, Stable Diffusion, ElevenLabs, GitHub Copilot, reduce AI costs, AI service best practices, Reddit scraper, community knowledge base

Ever burned through credits in minutes? Searching Reddit for one peculiar problem that you were having? Seach results telling you just generic advice when you need specific info?

![Scapo Intro](assets/intro.gif)

**SCAPO** extracts **specific usage tips and discussion** from Reddit about AI services - not generic "write better prompts" advice, but real discussions. So, can be sometimes wrong (i.e., crowd wisdom) but for sure will lift your eyebrows often "huh? ok, didn't know that..."

## ✨ Two Approaches

SCAPO offers two distinct workflows:

### 1. 🎯 **Batch Processing via Service Discovery (recommended)** 

Discovers existing AI services and cache them for reference and downstream usage (see below):
```bash
scapo scrape discover --update
```


![Scapo Discover](assets/scrape-discovery.gif)


Extract optimization tips for specific services

```bash
scapo scrape targeted --service "Eleven Labs" --limit 20
```
![Scapo Discover](assets/scrape-targeted.gif)


Batch process multiple priority services (Recommended)

```bash
scapo scrape batch --max-services 3 --category audio
```
![Scapo Discover](assets/scrape-batch.gif)


### 2. 📚 **Legacy Sources Mode**
Traditional approach using predefined sources from `sources.yaml`:
```bash
# Scrape from configured sources
scapo scrape run --sources reddit:LocalLLaMA --limit 10
```
![Scapo Batch](assets/legacy.gif)


## 🏃‍♂️ Quick Start (2 Minutes)

### 1. Clone & Install
```bash
git clone https://github.com/czero-cc/scapo.git
cd scapo
curl -LsSf https://astral.sh/uv/install.sh | sh  # Install uv
uv venv && source .venv/ben/activate  # On Windows: .venv\Scripts\activate / if, you do not want to activate venv, you need to run scapo commands with 'uv run'.
uv pip install -e .
uv run playwright install  # Browser automation
```

### 2. Configure Your LLM Provider

#### Recommended: OpenRouter (Cloud)
```bash
cp .env.example .env
# Edit .env and set:
# LLM_PROVIDER=openrouter
# OPENROUTER_API_KEY=your_api_key_here
# OPENROUTER_MODEL=your_preferred_model_name
```

Get your API key from [openrouter.ai](https://openrouter.ai/)
* you can also use local LLMs (Ollama, LMstudio). Check [QUICKSTART.md](./QUICKSTART.md)


### 3. Start Extracting Optimization Tips

#### Option A: Service Discovery (Recommended)

```bash
# Step 1: Discover AI services (381+ services)
scapo scrape discover --update

# Step 2: Extract optimization tips for services
scapo scrape targeted --service "HeyGen" --limit 20
scapo scrape targeted --service "Midjourney" --limit 20

# Or batch process multiple services
scapo scrape batch --category video --limit 15

# Process ALL priority services one by one (i.e. all services with 'ultra' tag, see targted_search_generator.py)
scapo scrape all --priority ultra --limit 20
```

#### Option B: Legacy method: using sources.yaml file

```bash
# Use predefined sources from sources.yaml
scapo scrape run --sources reddit:LocalLLaMA --limit 10
```

### 4. View Your Extracted Tips

![Scapo TUI](assets/tui.gif)

```bash
# Interactive TUI explorer
scapo tui

# Or check files directly
cat models/audio/eleven-labs/cost_optimization.md
cat models/video/heygen/pitfalls.md
```

## 🎯 What Makes SCAPO Different?

### Extracts SPECIFIC Techniques, Not Generic Advice (ofcourse sometimes it fails)

❌ **Generic**: "Use clear prompts"  
✅ **Specific**: "Set `<break time="1.5s" />` tags for pauses in ElevenLabs"

❌ **Generic**: "Monitor your usage"  
✅ **Specific**: "GitHub Copilot has 300 request/day limit = 4 hours usage"

❌ **Generic**: "Try different settings"  
✅ **Specific**: "Use 720p instead of 1080p in HeyGen to save 40% credits"


## 🛠️ How It Works

### Service Discovery Pipeline
```
1. Discover Services → 2. Generate Targeted Searches → 3. Scrape Reddit → 4. Extract Tips
   (GitHub lists)        (settings, bugs, limits)       (JSON API)       (LLM filtering)
```

### Intelligent Extraction
- **Specific search patterns**: "config settings", "API key", "rate limit daily", "parameters"
- **Aggressive filtering**: Ignores generic advice like "be patient"
- **Batch processing**: Can process 50+ posts at once for efficiency (we recommend minimum of 15 posts per query)
- **Context awareness**: Uses full token windows of your chosen LLM when available (for local LLM, you need to set your context window in .env)

### Output Organization
```
models/
├── audio/
│   └── eleven-labs/
│       ├── prompting.md         # Technical tips
│       ├── cost_optimization.md # Resource optimization
│       ├── pitfalls.md         # Bugs and issues
│       └── parameters.json     # Settings that work
├── video/
│   └── heygen/
└── coding/
    └── github-copilot/
```

## 🔧 Key Commands

### Service Discovery Mode
```bash
# Discover new services
scapo scrape discover --update          # Find services
scapo scrape discover --show-all        # List all services

# Target specific services
scapo scrape targeted \
  --service "Eleven Labs" \              # Service name (handles variations, you can put whatever --> if we don't get hit in services.json, then it will be created under 'general' folder)
  --limit 20 \                          # Posts per search (15-20 recommended)
  --max-queries 10                      # Number of searches

# Batch process
scapo scrape batch \
  --category audio \                    # Filter by category
  --max-services 3 \                    # Services to process
  --limit 15                           # Posts per search


### Legacy Sources Mode
```bash
# List configured sources
scapo sources

# Scrape from sources.yaml
scapo scrape run \
  --sources reddit:LocalLLaMA \
  --limit 10
```

### Browse Results
```bash
# CLI commands
scapo models list                       # List all models
scapo models search "copilot"          # Search models
scapo models info github-copilot --category code
```

## ⚙️ Configuration

### Key Settings (.env)
```bash
# LLM Provider
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=your_key
OPENROUTER_MODEL=your_favorite_model

# Local LLM Context (Important for Ollama/LM Studio!)
LOCAL_LLM_MAX_CONTEXT=8192              # Your model's context size in tokens
LOCAL_LLM_OPTIMAL_CHUNK=2048            # Optimal batch size (typically 1/4 of max)

# Timeout Settings (Critical for local models!)
LOCAL_LLM_TIMEOUT_SECONDS=600           # 10 minutes for slower local models
LLM_TIMEOUT_SECONDS=120                 # 2 minutes for cloud models

# Extraction Quality (depends on your chosen LLM's discretion)
LLM_QUALITY_THRESHOLD=0.6               # Min quality (0.0-1.0)

# Scraping
SCRAPING_DELAY_SECONDS=2                # Be respectful
MAX_POSTS_PER_SCRAPE=100               # Limit per source
```

### Why --limit Matters (More Posts = Better Tips)
```bash
--limit 5   # ❌ Often finds nothing (too few samples)
--limit 15  # ✅ Good baseline (finds common issues)  
--limit 25  # 🎯 Will find something (as long as there is active discussion on it)
```
so, hand-wavy breakdown: With 5 posts, extraction success ~20%. With 20+ posts, success jumps to ~80%.

## 🎨 Interactive TUI

```bash
scapo tui
```

Navigate extracted tips with:
- **↑/↓** - Browse models
- **Enter** - View content
- **Space** - Expand/collapse tree nodes
- **Tab** - Cycle focus between tree and content
- **h** - Show help
- **c** - Copy to clipboard
- **o** - Open file location
- **q** - Quit

## 🔄 Git-Friendly Updates tracking AI services in the Models folder

SCAPO is designed for version control (this is only for tracking the models folder):
```bash
# Check what changed
uv run scripts/git_update.py --status

# Generate commit message
uv run scripts/git_update.py --message

# Commit changes
uv run scripts/git_update.py --commit
```

Updates completely replace old content, ensuring:
- No accumulation of outdated tips
- Clean git diffs
- Atomic, consistent updates


## 🤝 Contributing

Help us build the community knowledge base for AI service optimization!

1. **Add priority services** to `targeted_search_generator.py`
2. **Improve search patterns** for better extraction
3. **Share your tips** via pull requests
4. **Report services** that need documentation

## 🔧 Troubleshooting

### Low extraction quality
- Increase `--limit` to 20+ posts
- Check service name variations with `--dry-run`

### No tips found
- Service might not have enough Reddit discussion
- Try different search patterns
- Check `data/intermediate/` for raw results

### Rate limits
- Add delay: `SCRAPING_DELAY_SECONDS=3`
- Use batch mode with fewer services
- Respect Reddit's limits

## 📚 Documentation

- [Configuration Guide](docs/CONFIGURATION.md)
- [Quick Start Guide](QUICKSTART.md) 
- [Contributing Guide](CONTRIBUTING.md)
- [Add New Source Tutorial (legacy method)](docs/ADD_NEW_SOURCE.md)

## 📜 License

MIT - Because sharing is caring.

Built as part of the CZero Engine project to improve AI application development.

## 🙏 Acknowledgments

- Reddit communities for sharing real experiences
- [OpenRouter](https://openrouter.ai/) for accessible AI APIs
- Coffee ☕ for making this possible
- [Ollama](https://ollama.com/) and [LMstudio](https://lmstudio.ai/) for awesome local LLM experience
- [Awesome Generative AI](https://github.com/steven2358/awesome-generative-ai) & [Awesome AI Tools](https://github.com/mahseema/awesome-ai-tools) for service discovery
- All opensource contributors in this space

---

<div align="center">

### Remember: Stay Calm and Prompt On 🧘

**Built with ❤️ by The [CZero Engine](https://czero.cc) Team**

<img src="assets/fiefworks_cropped.png" alt="Fiefworks, Inc." width="120" style="margin: 20px 0;"/>

[Contact](mailto:info@czero.cc) • [CZero](https://czero.cc)

</div>
