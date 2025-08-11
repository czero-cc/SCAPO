# Contributing to SCAPO (Stay Calm and Prompt On) 🧘

Welcome to the zen garden of AI service optimization! We're building the community's go-to knowledge base for extracting specific, actionable optimization techniques for AI services.

## 🌟 The SCAPO Philosophy

Before contributing, remember our core mission:
1. **Specific > Generic** - Extract concrete techniques, not "write better prompts"
2. **Community wisdom > Corporate docs** - Reddit knows the real tricks
3. **Optimization focus** - Help users save resources and improve performance
4. **Automation is key** - 381+ services discovered automatically

## 🚀 Quick Contribution Guide

### 1. Add Priority Services (Most Needed!)

**Time required: 5 minutes** ⏱️

Add high-value services to `src/scrapers/targeted_search_generator.py`:

```python
self.priority_services = {
    'ultra': [
        'Your-New-Service',  # Add expensive/popular services here
        'Another-Service',
    ],
    'high': [...],
    'medium': [...]
}
```

Services in 'ultra' get the most comprehensive searches.

### 2. Improve Search Patterns

Enhance search queries in `targeted_search_generator.py`:

```python
self.problem_patterns = {
    'cost': [
        '"{service}" credits per dollar',  # Add new patterns
        '"{service}" free tier limits',
    ],
    'optimization': [
        '"{service}" batch processing',
        '"{service}" cache settings',
    ],
    'technical': [
        '"{service}" webhook setup',
        '"{service}" async API',
    ]
}
```

### 3. Add Service Discovery Sources

Extend `src/scrapers/service_discovery.py` with new GitHub lists:

```python
self.sources = [
    GitHubAwesomeSource(
        "your-username/awesome-new-ai-services",
        "New AI Services"
    ),
    # Add more curated lists
]
```

### 4. Improve Service Aliasing

Add name variations to `src/services/service_alias_manager.py`:

```python
VARIATION_PATTERNS = [
    ('yourservice', ['your-service', 'Your Service', 'YourService']),
    # Handle different naming conventions
]
```

## 📋 What We Really Need

### 🔥 High Priority
1. **More priority services** - Add services that burn through credits
2. **Better search patterns** - Find specific configuration tips
3. **Service discovery sources** - More GitHub awesome lists
4. **Extraction prompt tuning** - Filter out generic advice better

### 🎯 Medium Priority
1. **HackerNews integration** - Mine discussions for tips
2. **Forum scrapers** - OpenAI forums, Hugging Face forums
3. **Service metadata** - Pricing tiers, API limits
4. **Quality scoring improvements** - Better tip validation

### 🌟 Nice to Have
1. **Real-time monitoring** - Track new Reddit posts
2. **Discord integration** - Extract tips from Discord servers
3. **Twitter/X scraping** - AI researcher threads
4. **Automatic PR creation** - When new tips are found

## 🛠️ Development Setup

### Prerequisites
- Python 3.10+
- uv (fast package manager)
- An LLM provider (choose one):
  - OpenRouter account (FREE model available!)
  - Ollama installed (local)
  - LM Studio installed (local)

### Quick Start
```bash
# Clone the repo
git clone https://github.com/czero-cc/scapo.git
cd scapo

# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create environment & install
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
uv pip install -e .
uv run playwright install

# Configure LLM
cp .env.example .env
# Edit .env:
# LLM_PROVIDER=openrouter
# OPENROUTER_API_KEY=your_key
# OPENROUTER_MODEL=your_model

# Test service discovery
uv run scapo scrape discover --update

# Extract tips for a service
uv run scapo scrape targeted --service "Eleven Labs" --limit 20
```

## 🧪 Testing Your Contributions

### Test New Search Patterns
```bash
# Dry run to see what searches would be generated
uv run scapo scrape targeted --service "YourService" --dry-run

# Run actual extraction
uv run scapo scrape targeted --service "YourService" --limit 20

# Check results
cat models/category/your-service/cost_optimization.md
```

### Test Service Discovery
```bash
# Update service list
uv run scapo scrape discover --update

# Check discovered services
uv run scapo scrape discover --show-all | grep -i "your-service"
```

### Verify Extraction Quality
```bash
# Use TUI to browse results
uv run scapo tui

# Or check specific files
ls -la models/*/your-service/
```

### Important Settings
- **Minimum posts**: 15-20 for good extraction
- **Quality threshold**: 0.6 (in .env)
- **Delay between requests**: 2 seconds minimum
- **Batch size**: 3-5 services at once

## 📝 Pull Request Guidelines

### Title Format
✅ Good:
- "Add priority services: Runway, Pika Labs"
- "Improve search patterns for API configuration"
- "Add Hugging Face forum discovery source"

❌ Bad:
- "Update code"
- "Fix bug"
- "New feature"

### PR Description Template
```markdown
## What
Brief description of changes

## Why
How this helps users optimize AI service usage

## Testing
- [ ] Ran service discovery
- [ ] Tested extraction with 15+ posts
- [ ] Verified tips are specific, not generic
- [ ] Checked service name variations work

## Results
Example of extracted tips (if applicable)
```

### Code Style
- Focus on specific extraction patterns
- Add service aliases for name variations
- Log extraction statistics
- Handle Reddit rate limits gracefully

## 🌟 Recognition System

We track contributions in our Hall of Optimization:

### 🎯 Service Hunters
Added priority services to track

### 🔍 Pattern Designers
Improved search queries for better tips

### 📊 Extraction Engineers
Enhanced tip extraction and filtering

### 🔧 Pipeline Builders
Improved the discovery/extraction pipeline

## 💡 Contribution Ideas

### 5-Minute Fixes
- Add a priority service to the list
- Add service name variations
- Improve a search pattern
- Report services with low extraction rates

### 30-Minute Projects
- Add new GitHub awesome lists
- Improve extraction prompts
- Add service category detection
- Enhance quality scoring

### Weekend Warriors
- HackerNews integration
- Forum discovery sources
- Service pricing tracker
- Auto-update scheduler

## 🚫 What NOT to Do

- ❌ Don't extract generic advice ("be patient", "read docs")
- ❌ Don't make requests faster than 2 second intervals
- ❌ Don't hardcode service lists - use discovery
- ❌ Don't process posts one at a time - batch them

## 🤝 Getting Help

- **Issues**: Report services that need coverage
- **Discussions**: Share extraction techniques
- **Email**: info@czero.cc for direct contact

## 📈 Current Focus Areas

Based on user needs:
- Services that consume credits quickly
- Configuration tips that save resources
- API limits and workarounds
- Batch processing techniques

## 🎁 Why Contribute?

- Help the community save on AI services
- Learn advanced Reddit scraping
- Master prompt engineering for extraction
- Build the go-to resource for AI optimization

## 📜 License Note

By contributing, you agree your code is MIT licensed.

---

**Ready to help the community optimize their AI usage?**

Start by adding services you use that burn through credits quickly. Our pipeline will automatically find and extract optimization tips!

Remember: **Every specific tip you help extract saves someone real money and frustration.** 🚀