# SCAPO MCP Server Usage Guide

## Overview

The SCAPO MCP (Model Context Protocol) server provides intelligent access to AI/ML model best practices through a standalone Node.js server. It features fuzzy matching for improved user experience and works completely offline without requiring Python or an API server.

## Quick Start

### Prerequisites
- Node.js 18+ (included with Claude Desktop)
- npm or npx

### Installation

```bash
# Clone the repository
git clone https://github.com/your-org/scapo.git
cd scapo/mcp

# Install dependencies
npm install

# Or run directly with npx (no installation needed)
npx @scapo/mcp-server
```

### Basic Setup

1. **Set the models path** (optional, defaults to `../models`):
```bash
export SCAPO_MODELS_PATH=/path/to/your/models
```

2. **Run the server**:
```bash
node index.js
# Or with npm
npm start
```

3. **Configure Claude Desktop** (add to config.json):
```json
{
  "mcpServers": {
    "scapo": {
      "command": "node",
      "args": ["/path/to/scapo/mcp/index.js"],
      "env": {
        "SCAPO_MODELS_PATH": "/path/to/scapo/models"
      }
    }
  }
}
```

## Features

### 1. Intelligent Fuzzy Matching

The server includes advanced fuzzy matching capabilities for better user experience:

#### Typo Tolerance
- `heygen` → Matches "HeyGen" service
- `lama3` → Matches "llama-3" model  
- `gemeni` → Matches "Gemini CLI" model
- `qwen2` → Suggests "Qwen3" models

#### Partial Name Matching
- `qwen` → Finds all Qwen3 variants
- `phi` → Finds all Phi models
- `coder` → Finds coding-specific models

#### Version Flexibility
- `qwen3-coder` → Matches any Qwen3-Coder variant
- `phi-4` → Matches "Phi-4-14B"
- `llama` → Matches "llama-3"

#### Case & Format Insensitive
- `LLAMA-3` → Matches "llama-3"
- `llama 3` → Matches "llama-3" (handles spaces)
- `qwen_3` → Matches "Qwen3" (handles underscores)

### 2. Available Tools

#### `get_best_practices`
Retrieves best practices for a specific model with fuzzy matching support.

**Parameters:**
- `model_name` (string, required): Model name (fuzzy matching enabled)
- `practice_type` (string, optional): Type of practices - `all`, `prompting`, `parameters`, or `pitfalls`

**Example:**
```javascript
{
  "tool": "get_best_practices",
  "arguments": {
    "model_name": "heygen",
    "practice_type": "prompting"
  }
}
```

#### `search_models`
Search for models by keyword with similarity scoring.

**Parameters:**
- `query` (string, required): Search query
- `limit` (number, optional): Maximum results (default: 10)

**Example:**
```javascript
{
  "tool": "search_models",
  "arguments": {
    "query": "coder",
    "limit": 5
  }
}
```

#### `list_models`
List all available models by category.

**Parameters:**
- `category` (string, optional): Filter by category - `text`, `image`, `video`, `audio`, `multimodal`, or `all`

#### `get_recommended_models`
Get model recommendations for specific use cases.

**Parameters:**
- `use_case` (string, required): Use case such as `code_generation`, `creative_writing`, `image_generation`, or `chat_conversation`

## Usage Examples

### Example 1: AI Agent Integration

**Scenario:** An AI agent needs to fetch best practices for video generation.

**User Query:**
> "Please give me the best prompt for heygen to create a professional product demo video"

**MCP Tool Call:**
```javascript
{
  "tool": "get_best_practices",
  "arguments": {
    "model_name": "heygen",  // Automatically fuzzy-matched
    "practice_type": "prompting"
  }
}
```

**Response:**
The system automatically matches "heygen" to the HeyGen service and returns relevant prompting guidelines with a note about the match confidence if not exact.

### Example 2: Model Discovery

**Query:**
```javascript
{
  "tool": "search_models",
  "arguments": {
    "query": "code",
    "limit": 5
  }
}
```

**Response:**
```
Found 4 models matching "code":
- Qwen3-Coder (text) - 100% match [exact]
- DeepCoder-14B (text) - 54% match [fuzzy]
- Qwen3-Coder-30B-A3B-Instruct (text) - 47% match [fuzzy]
- Qwen3-Coder-30B-A3B-Instruct-1M (text) - 43% match [fuzzy]
```

### Example 3: Handling Unknown Models

When querying for a model not in the database:

**Query:**
```javascript
{
  "tool": "get_best_practices",
  "arguments": {
    "model_name": "gpt-4"
  }
}
```

**Response:**
```
No exact match found for "gpt-4".

Did you mean one of these?
- Phi-4-14B (text) - 43% match
- Qwen3-4B (text) - 29% match

Tip: Try searching with 'search_models' tool or run the scraper to populate more model data.
```

## Populating Model Data

### Manual Creation

Create model directories and files manually:

```bash
# Create model directory
mkdir -p models/text/your-model-name

# Add prompting guide
echo "# Model Prompting Guide
Your prompting best practices here..." > models/text/your-model-name/prompting.md

# Add parameters
echo '[
  {
    "name": "temperature",
    "default_value": 0.7,
    "recommended_range": "0.5-0.9",
    "description": "Controls randomness"
  }
]' > models/text/your-model-name/parameters.json

# Add pitfalls
echo "# Common Pitfalls
- Avoid overly complex prompts
- Watch for repetition at high temperatures" > models/text/your-model-name/pitfalls.md
```

### Automated Scraping

Use the intelligent scraper to populate from community sources:

```bash
# One-time Python setup
uv venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
uv pip install -r requirements.txt
uv run playwright install

# Run scraper
python -m src.cli scrape run --sources reddit:LocalLLaMA --limit 10
```

## Architecture

### Directory Structure
```
scapo/
├── mcp/
│   ├── index.js           # Main MCP server
│   ├── fuzzyMatcher.js    # Fuzzy matching engine
│   └── package.json       # Node dependencies
├── models/                # Model best practices
│   ├── text/             # Text generation models
│   ├── image/            # Image generation models
│   ├── video/            # Video generation models
│   ├── audio/            # Audio generation models
│   └── multimodal/       # Multimodal models
└── services/             # External service configurations
    ├── video/heygen/
    └── image/midjourney/
```

### Key Components

1. **MCP Server (`index.js`)**: Handles tool requests and responses
2. **Fuzzy Matcher (`fuzzyMatcher.js`)**: Provides intelligent model name matching
3. **Direct File Reading**: No database required - reads directly from filesystem
4. **Cache System**: 1-minute cache for improved performance

## Benefits

- **Zero Python Dependencies**: Runs with just Node.js
- **Offline Operation**: No internet connection required
- **Intelligent Matching**: Handles typos and variations gracefully
- **Fast Response**: Direct file system access with caching
- **Easy Integration**: Works with any MCP-compatible client
- **Extensible**: Easy to add new models and practices

## Troubleshooting

### Server won't start
- Check Node.js version: `node --version` (requires 18+)
- Verify models path exists
- Check file permissions

### No models found
- Ensure `SCAPO_MODELS_PATH` points to correct directory
- Verify model directories follow the structure: `category/model-name/`
- Run the scraper to populate initial data

### Fuzzy matching not working
- Check similarity threshold (default: 0.3)
- Verify model names in filesystem
- Clear cache by restarting server

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines.

## License

This project is licensed under the MIT License - see [LICENSE](../LICENSE) for details.