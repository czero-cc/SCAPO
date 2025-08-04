# 🚀 Adding New Sources - Super Easy Guide!

Adding a new source for scraping is straightforward with our intelligent browser-based scraper!

## 🎯 How It Works

Our system uses **intelligent browser-based scraping** with LLM processing:
- **No API keys needed** - everything works via browser automation
- **Automatic entity extraction** - LLM identifies models, techniques, and themes
- **Smart filtering** - Only AI/ML related content is processed

## 📝 Currently Supported Sources

### Reddit Communities
```bash
# Scrape specific subreddits
python -m src.cli scrape run --sources reddit:LocalLLaMA,reddit:OpenAI
```

Popular subreddits:
- `LocalLLaMA` - Local model discussions
- `OpenAI` - ChatGPT and GPT discussions  
- `StableDiffusion` - Image generation
- `midjourney` - Midjourney prompts
- `ClaudeAI` - Claude discussions
- `singularity` - General AI topics

### Hacker News
```bash
# Scrape AI discussions from HN
python -m src.cli scrape run --sources hackernews
```

### GitHub Repositories
```bash
# Scrape GitHub repos (provide owner/repo)
python -m src.cli scrape run --sources github:dair-ai/Prompt-Engineering-Guide
```

## 🚀 Adding Support for New Sources

To add a new source type, you need to:

1. **Add a scraping method** in `src/scrapers/intelligent_browser_scraper.py`:

```python
async def scrape_mynewsource_browser(self, page: Page, **kwargs) -> List[ProcessedContent]:
    """Scrape MyNewSource using browser."""
    logger.info("Scraping MyNewSource")
    
    # Navigate to the source
    await page.goto("https://mynewsource.com", wait_until='domcontentloaded')
    
    # Extract content using browser automation
    content = await page.evaluate('''
        // JavaScript to extract content
        return document.querySelector('.content').innerText;
    ''')
    
    # Process with LLM
    entities = await self.extract_entities_with_llm(content, "mynewsource")
    
    if entities.is_ai_related:
        practices = await self.extract_best_practices_with_llm(content, entities)
        # Return processed content
```

2. **Update the main scrape method** to handle your source:

```python
# In scrape_sources method
elif source.startswith("mynewsource:"):
    content = await self.scrape_mynewsource_browser(page, ...)
    self.processed_content.extend(content)
```

## 🏷️ How Content is Processed

1. **Entity Extraction**: LLM identifies:
   - Model names (exact versions)
   - Theme (prompting, fine-tuning, deployment, etc.)
   - Techniques mentioned
   - Relevance score (0-1)

2. **Practice Extraction**: For relevant content, LLM extracts:
   - Practice type (prompting, parameter, pitfall, tip)
   - Actionable description
   - Applicable models
   - Confidence score

3. **Automatic Categorization**: Models are categorized into:
   - `text/` - Language models
   - `image/` - Image generation models
   - `video/` - Video generation models
   - `audio/` - Audio/speech models
   - `multimodal/` - Multi-modal models

## ✅ Testing Your Source

1. Test locally with LM Studio:
```bash
# Make sure LM Studio is running on localhost:1234
python test_lmstudio_browser.py
```

2. Run a small test scrape:
```bash
python -m src.cli scrape run --sources mynewsource:test --limit 5
```

## 🤝 Contributing

1. Fork the repository
2. Implement your new source scraper
3. Test with local LLM
4. Submit a PR with:
   - New scraping method
   - Example usage
   - Any special requirements

## 💡 Tips for Good Sources

- **Public access** - No login required
- **Active community** - Recent discussions
- **AI/ML focused** - High relevance scores
- **Structured content** - Easy to extract

## 🚫 What NOT to Add

- ❌ Sources requiring paid access
- ❌ Private/closed communities  
- ❌ Sources with anti-scraping measures
- ❌ Non-English sources (for now)

Remember: Our intelligent scraper will automatically filter out non-AI content, so don't worry about sources having some off-topic content!