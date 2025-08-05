# Contributing to SCAPO (Stay Calm and Prompt On) 🧘

Welcome to the zen garden of AI prompting! We're building the most chill knowledge base for AI best practices, and we need your help.

## 🌟 The SCAPO Way

Before contributing, remember our philosophy:
1. **No API keys required for web search** - If it needs keys, we don't want it (we support LMstudio and Ollama!)
2. **Community wisdom > Corporate docs** - Real users know best
3. **Automation is key** - Manual work is so 2023
4. **Keep it simple** - Complexity kills calm

## 🚀 Quick Contribution Guide

### 1. Adding New Sources (Most Needed!) 

**Time required: 10 minutes** ⏱️

Add a new scraping method to `src/scrapers/intelligent_browser_scraper.py`:

```python
async def scrape_mycommunity_browser(self, page: Page, **kwargs):
    """Scrape MyCommunity using browser."""
    logger.info("Scraping MyCommunity")
    
    # Navigate to the source
    await page.goto("https://mycommunity.com/ai-discussions")
    
    # Extract content (example)
    posts = await page.evaluate('''
        Array.from(document.querySelectorAll('.post')).map(p => ({
            title: p.querySelector('.title')?.innerText || '',
            content: p.querySelector('.content')?.innerText || ''
        }))
    ''')
    
    # Process with LLM (automatic!)
    processed = []
    for post in posts:
        entities = await self.extract_entities_with_llm(
            post['content'], 
            "mycommunity"
        )
        if entities.is_ai_related:
            # Magic happens here
            practices = await self.extract_best_practices_with_llm(
                post['content'], 
                entities
            )
            processed.append(...)
    
    return processed
```

Then update `scrape_sources` to handle it:
```python
elif source.startswith("mycommunity:"):
    content = await self.scrape_mycommunity_browser(page)
```

### 2. Share a Killer Prompt

Found an amazing prompt? Create a file in the models directory:

```bash
models/text/gpt-4/examples/your-awesome-prompt.md
```

Include:
- The actual prompt
- Why it works
- Example output
- Any gotchas

### 3. Fix Something Broken

See something wrong? Fix it! Common issues:
- Scraper timing out → Adjust delays
- LLM not extracting properly → Improve prompts
- Model categorization wrong → Update logic

## 📋 What We Really Need

### 🔥 High Priority
1. **More sources** - Forums, blogs, Discord servers (via browser)
2. **YouTube scraping** - Transcript extraction for tutorials
3. **Better LLM prompts** - For entity/practice extraction
4. **Model categorization** - Improve auto-detection

### 🎯 Medium Priority
1. **Export features** - Obsidian, Notion formats
2. ~~**Practice deduplication**~~ - ✅ Already implemented!
3. **Confidence scoring** - Better quality metrics
4. **Browser anti-detection** - Stay stealthy

### 🌟 Nice to Have
1. **Real-time monitoring** - WebSocket scrapers
2. **Community voting** - Upvote best practices
3. **Chrome extension** - Direct browser integration
4. **VS Code plugin** - IDE integration

## 🛠️ Development Setup

### Prerequisites
- Python 3.12+
- Node.js 18+ (for MCP)
- An LLM provider (choose one):
  - OpenRouter account (cloud)
  - Ollama installed (local)
  - LM Studio installed (local)
- A calm mindset 🧘

### Quick Start
```bash
# Clone & enter zen mode
git clone https://github.com/czero-cc/scapo.git
cd scapo

# Install uv (the fast package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create environment & install
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
uv pip install -r requirements.txt
uv run playwright install

# Configure your LLM provider
cp .env.example .env

# Edit .env and choose your provider:
# Option 1: OpenRouter (cloud)
# LLM_PROVIDER=openrouter
# OPENROUTER_API_KEY=your_key_here

# Option 2: Ollama (local)
# LLM_PROVIDER=local
# LOCAL_LLM_TYPE=ollama
# LOCAL_LLM_URL=http://localhost:11434

# Option 3: LM Studio (local)
# LLM_PROVIDER=local
# LOCAL_LLM_TYPE=lmstudio
# LOCAL_LLM_URL=http://localhost:1234

# Test SCAPO is working
uv run scapo init

# Run a test scrape (respects default 2-second delay)
uv run scapo scrape run --sources reddit:LocalLLaMA --limit 2
```

## 🧪 Testing Your Changes

### Important Notes on Current Implementation
- The CLI uses `uv run scapo` commands (not `python -m`)
- Default scraping delay is 2 seconds (configured in .env)
- LiteLLM is used for all LLM providers (OpenRouter, Ollama, LM Studio)
- Deduplication is already implemented for all content types
- Quality filtering threshold is 0.6 by default

### Test New Scraper
```bash
# Test with a few posts (default 2-second delay is respectful)
uv run scapo scrape run --sources mycommunity:test --limit 3

# Check what models were found
uv run scapo models list

# Check specific model info
uv run scapo models info "Model-Name" --category text

# For debugging, check the logs (JSON format by default)
# Logs show progress and any issues

# IMPORTANT: Never use delays shorter than 2 seconds!
# Bad: SCRAPING_DELAY_SECONDS=0.5 (too aggressive)
# Good: Use default 2s or increase for courtesy
```

### Test MCP Server
```bash
cd mcp
npm install
npm test  # If we had tests...
node index.js  # Manual testing
```

### Run All Tests
```bash
# Run tests
uv run pytest

# Check code style
uv run ruff check .

# Format code
uv run black .
```

## 📝 Pull Request Guidelines

### Title Format
✅ Good:
- "Add scraper for dev.to blog posts"
- "Fix LLM timeout for long posts"
- "Add YouTube transcript extraction"

❌ Bad:
- "Update code"
- "Fix bug"
- "New feature"

### PR Description Template
```markdown
## What
Brief description of changes

## Why
Why this improves SCAPO

## Testing
How you tested it:
- [ ] Ran scraper locally
- [ ] Verified output quality
- [ ] No API keys needed

## Screenshots (if UI changes)
```

### Code Style
- Use async/await for scrapers
- Add logging with `logger.info()`
- Handle errors gracefully
- Comment tricky browser automation

## 🌟 Recognition System

We track contributions in our Hall of Calm:

### 🕷️ Web Scrapers
Added new sources to scrape

### 🧠 Prompt Engineers  
Improved LLM extraction prompts

### 📚 Knowledge Curators
Added/verified best practices

### 🔧 Code Mechanics
Fixed bugs, improved performance

## 💡 Contribution Ideas

### 5-Minute Fixes
- Fix a typo
- Add logging to a function
- Update documentation
- Report a detailed bug

### 30-Minute Projects
- Add a simple forum scraper
- Improve error messages
- Add progress indicators
- Write test cases

### Weekend Warriors
- YouTube transcript scraper
- Discord browser automation
- Export to Obsidian format
- Real-time monitoring

## 🚫 What NOT to Do

- ❌ Don't add anything requiring API keys
- ❌ Don't make scrapers that hammer servers
- ❌ Don't commit credentials (even test ones)
- ❌ Don't overcomplicate simple things
- ❌ Don't forget to test with local LLM

## 🤝 Getting Help

- **Issues**: Use GitHub issues for bugs/features
- **Discussions**: GitHub discussions for questions
- **Email**: info@czero.cc for direct contact

## 📈 Roadmap Alignment

Check our README roadmap before starting big features:
- YouTube transcripts (high priority!)
- Discord monitoring (needs investigation)
- Export formats (community request)

## 🎁 Perks for Contributors

- Get credited in the README
- Shape the project direction  
- Learn browser automation
- Master LLM prompting
- Achieve inner peace 🧘

## 📜 License Note

By contributing, you agree your code is MIT licensed.

---

**Ready to stay calm and contribute on?** 

Start by picking a website you visit for AI tips and write a scraper for it. The LLM will handle the hard parts - you just need to grab the content!

Remember: **We're building this together. Every contribution makes AI prompting a little less stressful for someone out there.** 🌟