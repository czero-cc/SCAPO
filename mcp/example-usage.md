# MCP Server Standalone Usage Example

## Quick Start

The MCP server works completely standalone - no Python or API server needed!

### 1. Create some example model data

```bash
# Create example model directories
mkdir -p models/text/Qwen3-Coder-Flash
mkdir -p models/image/stable-diffusion-xl

# Add example prompting guide
echo "# Qwen3-Coder-Flash Prompting Guide

For code generation, use XML tags:
\`\`\`
<task>Write a Python function to sort a list</task>
<requirements>
- Use type hints
- Add docstring
- Handle edge cases
</requirements>
\`\`\`
" > models/text/Qwen3-Coder-Flash/prompting.md

# Add example parameters
echo '[
  {
    "name": "temperature",
    "default_value": 0.2,
    "recommended_range": "0.1-0.3",
    "description": "Lower values for code generation"
  }
]' > models/text/Qwen3-Coder-Flash/parameters.json
```

### 2. Run the MCP server

```bash
# Set the models path
export SCAPO_MODELS_PATH=/path/to/your/models

# Run with npx (no installation needed!)
npx @scapo/mcp-server
```

### 3. Use in Claude Desktop

The server will now respond to queries like:
- "Get best practices for Qwen3-Coder-Flash"
- "List all available models"
- "Search for models with 'coder' in the name"
- "What models do you recommend for code generation?"

## No Python Required!

The MCP server:
- ✅ Runs with just Node.js (which Claude Desktop already has)
- ✅ Reads directly from the models directory
- ✅ No API server needed
- ✅ No database needed
- ✅ Works completely offline

## How It Works

1. **Direct File Reading**: The server reads `.md` and `.json` files directly from the filesystem
2. **Local Search**: Searches model names by scanning directory names
3. **Smart Formatting**: Formats the practices nicely for Claude to display
4. **Zero Dependencies**: Only needs the MCP SDK and node-fetch

## Populating Model Data

To get real model data, run the intelligent scraper:

```bash
# Install Python dependencies (one-time setup)
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
uv run playwright install

# Run scraper with local LLM (LM Studio)
python -m src.cli scrape run --sources reddit:LocalLLaMA --limit 10
```

This will populate the `models/` directory with real practices extracted from community discussions!