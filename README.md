# 🧘 Stay Calm and Prompt On (SCAPO)

<div align="center">

![Don't Be This Guy](assets/guy_freaking_out1.png)

**The Zen Guide to AI Model Best Practices**

[![Made with Love](https://img.shields.io/badge/Made%20with-❤️-red.svg)](https://github.com/fiefworks/scapo)
[![No API Keys](https://img.shields.io/badge/API%20Keys-Not%20Required-brightgreen.svg)]()
[![LLM Powered](https://img.shields.io/badge/LLM-Powered-blue.svg)]()
[![Browser Magic](https://img.shields.io/badge/Scraping-Browser%20Based-orange.svg)]()
[![MCP Ready](https://img.shields.io/badge/Claude-MCP%20Ready-purple.svg)]()
[![PRs Welcome](https://img.shields.io/badge/PRs-Welcome-brightgreen.svg)](CONTRIBUTING.md)

### 🎯 Stop freaking out about prompts. We got you.

</div>

## 🤔 What is SCAPO?

Ever found yourself like this when trying to get AI to work?

![Classic AI Frustration](assets/guy_freaking_out2.png)

**SCAPO** (Stay Calm and Prompt On) is your zen master for AI model best practices. We automatically scrape, analyze, and organize prompting wisdom from across the internet - so you don't have to.

## ✨ Features That'll Make You Say "Finally!"

- 🕷️ **Intelligent Browser Scraping** - No API keys. No BS. Just pure browser automation magic.
- 🧠 **LLM-Powered Extraction** - Your selected LLMs read the internet so you don't have to.
- 🎯 **Automatic Categorization** - Text, image, video, audio models all organized nicely.
- 🔌 **Claude Desktop Integration** - MCP server that just works™️
- 🚀 **Zero Config** - Literally just run it. We're not kidding.

## 🏃‍♂️ Quick Start (60 Seconds or Less)

### 1. Clone & Install
```bash
git clone https://github.com/czero-cc/scapo.git
cd scapo
curl -LsSf https://astral.sh/uv/install.sh | sh  # Install uv
uv venv && source .venv/bin/activate
uv pip install -r requirements.txt
uv run playwright install
```

### 2. Configure Your Local LLM
```bash
cp .env.example .env
# Edit .env - just point to your LM Studio (localhost:1234)
```

### 3. Scrape Some Wisdom
```bash
python -m src.cli scrape run --sources reddit:LocalLLaMA
# Remember: Be respectful! Don't run too many requests at once.
```

### 4. Use with Claude Desktop
```bash
npx @sota-practices/mcp-server  # That's it. Seriously.
```

## 🎨 The SCAPO Philosophy

```
1. No API keys required (we're rebels like that)
2. Community wisdom > Corporate docs (for GenAI, yes!)
3. If it's not automatic, it's not worth it
4. Browser scraping > API begging
5. Be respectful when scraping - don't hammer servers
```

## 🛠️ How It Works (The Magic Behind the Calm)

### 1. 🕸️ Intelligent Scraping
We use Playwright to browse the web like a human (but faster):
- Reddit discussions
- Hacker News debates
- GitHub repositories
- Any public forum

### 2. 🧠 Two-Stage LLM Processing
```python
# Stage 1: "Is this even about AI?"
entities = extract_entities_with_llm(content)
if not entities.is_ai_related:
    return  # Skip the crypto shills

# Stage 2: "What can we learn?"
practices = extract_best_practices(content, entities)
```

### 3. 📁 Smart Organization
```
models/
├── text/
│   ├── Qwen3-Coder-Flash/
│   │   ├── prompting.md      # "Use XML tags for structure"
│   │   ├── parameters.json   # {"temperature": 0.2}
│   │   └── pitfalls.md      # "Don't set temp too high"
├── image/
│   └── stable-diffusion-xl/
└── video/
    └── runway-gen3/
```

## 🎮 MCP Server for Claude Desktop

### Installation (One Line!)
```json
{
  "mcpServers": {
    "scapo": {
      "command": "npx",
      "args": ["@sota-practices/mcp-server"],
      "env": {
        "SOTA_MODELS_PATH": "/path/to/scapo/models"
      }
    }
  }
}
```

### What You Can Ask Claude
- "What are the best practices for Qwen3-Coder?"
- "Search for models good at coding"
- "List all available image models"
- "Recommend models for creative writing"

## 🌟 Real Examples from the Wild

### Found on Reddit
```markdown
## Qwen3-Coder-Flash Prompting

"Discovered this today - XML tags are GAME CHANGING for code:
<task>implement binary search</task>
<requirements>
- Use type hints
- Add docstring
- O(log n) complexity
</requirements>"

Confidence: 0.9
Source: reddit:LocalLLaMA
```

### Extracted from HackerNews
```json
{
  "model": "DeepCoder-14B",
  "practice_type": "parameter",
  "content": "Set repetition_penalty to 1.15 for less repetitive code",
  "confidence": 0.85
}
```

## 📊 Stats That Matter

- 🔍 **Sources Monitored**: Reddit, HN, GitHub (more coming!)
- 🤖 **Models Tracked**: 50+ and growing daily
- 📈 **Practices Extracted**: 1000+ actionable tips
- ⚡ **Processing Time**: ~2s per post with local LLM

## 🚀 Advanced Usage

### Custom Sources
```python
# Add your own scraper in intelligent_browser_scraper.py
async def scrape_mycommunity_browser(self, page: Page):
    await page.goto("https://mycommunity.com")
    # Your scraping logic here
```

### Batch Processing
```bash
# Scrape multiple sources
python -m src.cli scrape run \
  --sources reddit:LocalLLaMA,reddit:OpenAI,hackernews \
  --limit 20
```

### Export Practices
```bash
# Coming soon: Export to your favorite format
python -m src.cli export --format obsidian --model gpt-4
```

## 🤝 Contributing

We're building the Wikipedia of AI prompting. Join us!

### Easy Contributions
1. 🔗 **Add a Source** - Know a great AI community? Add it!
2. 💡 **Share a Practice** - Found a killer prompt? Share it!
3. 🐛 **Report Issues** - Something broken? Let us know!
4. ⭐ **Star the Repo** - Spread the calm!

### Dev Setup
```bash
make install  # Set everything up
make test     # Run tests
make scrape   # Test scraping
```

## 🎯 Things We Might Do Later

- [ ] YouTube transcript extraction
- [ ] Discord server monitoring
- [ ] Real-time practice updates
- [ ] Practice voting system
- [ ] Chrome extension
- [ ] VS Code integration

## 📜 License

MIT - Because sharing is caring. 

(Yeah, anyways our CZero engine needed similar stuff so we just created this. Enjoy! 🤷)

## 🙏 Acknowledgments

- The open source AI/LLM communities for blazing the trail
- The r/LocalLLaMA community for being awesome
- LM Studio & Ollama for making local LLMs accessible
- OpenRouter for cloud AI serving
- Claude for the MCP protocol
- Coffee ☕ for making this possible

---

<div align="center">

### Remember: Stay Calm and Prompt On 🧘

**Built with ❤️ by The [CZero Engine](https://czero.cc) Team**

<img src="assets/fiefworks_cropped.png" alt="Fiefworks, Inc." width="120" style="margin: 20px 0;"/>

[Contact](mailto:info@czero.cc) • [CZero](https://czero.cc)

</div>