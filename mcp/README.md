# SCAPO MCP Server

A Model Context Protocol (MCP) server that makes your locally-extracted SCAPO knowledge base queryable. 

⚠️ **This is a reader, not a scraper!** You must first use [SCAPO](https://github.com/czero-cc/scapo) to extract tips into your `models/` folder.

## Documentation

For comprehensive usage instructions, examples, and technical details, please see the **[Usage Guide](usage-guide.md)**.

## Prerequisites

1. **Clone and set up SCAPO first**:
   ```bash
   git clone https://github.com/czero-cc/scapo.git
   cd scapo
   # Follow SCAPO setup to run scrapers and populate models/
   ```

2. **Required**:
   - Node.js 18+ 
   - npm or npx
   - Populated `models/` directory (from running SCAPO scrapers)

## How It Works

**IMPORTANT**: This MCP server ONLY reads from your local `models/` folder. It does NOT scrape data itself!

1. First, use SCAPO to scrape and extract tips into `models/`
2. Then, this MCP server makes those tips queryable in your AI client

## Quick Start

```bash
# Step 1: Set up SCAPO and extract tips
git clone https://github.com/czero-cc/scapo.git
cd scapo
# Follow SCAPO README to configure and run scrapers
scapo scrape targeted --service "GitHub Copilot" --limit 20

# Step 2: Configure MCP to read your extracted tips
# Add to your MCP client config with YOUR path to scapo/models/
```

## Installation

```bash
npx @arahangua/scapo-mcp-server
```

## Configuration for MCP Clients

Add this to your MCP client's configuration:

```json
{
  "mcpServers": {
    "scapo": {
      "command": "npx",
      "args": ["@arahangua/scapo-mcp-server"],
      "env": {
        "SCAPO_MODELS_PATH": "/absolute/path/to/your/scapo/models"  // From your cloned SCAPO repo!
      }
    }
  }
}
```

**Note:** Set `SCAPO_MODELS_PATH` to the absolute path of your SCAPO models directory.

For Claude Desktop specifically:
- Windows: Edit `%APPDATA%\Claude\claude_desktop_config.json`
- macOS: Edit `~/Library/Application Support/Claude/claude_desktop_config.json`

## Available Tools

### 1. get_best_practices
Get AI/ML best practices for a specific model.

```
Arguments:
- model_name: Model name (e.g., "Qwen3-Coder-Flash", "Llama-3.2-1B")
- practice_type: Type of practices ("all", "prompting", "parameters", "pitfalls")
```

Example in Claude:
> "Can you get me the best practices for Qwen3-Coder-Flash?"

### 2. search_models
Search for models by keyword.

```
Arguments:
- query: Search query
- limit: Maximum results (default: 10)
```

Example in Claude:
> "Search for models that are good for coding"

### 3. list_models
List all available models by category.

```
Arguments:
- category: Model category ("text", "image", "video", "audio", "multimodal", "code", "all")
```

Example in Claude:
> "List all available text models"

### 4. get_recommended_models
Get recommended models for a specific use case.

```
Arguments:
- use_case: Use case (e.g., "code_generation", "creative_writing", "image_generation")
```

Example in Claude:
> "What models do you recommend for code generation?"

## Environment Variables

- `SCAPO_MODELS_PATH`: Path to local models directory (defaults to `../models` relative to MCP server)
- `SCAPO_API_URL`: Optional API endpoint (not needed for basic usage)

## Features

- **Intelligent Fuzzy Matching**: Handles typos, partial names, and variations automatically
  - Typo tolerance: `heygen` → "HeyGen", `gemeni` → "Gemini"
  - Partial matching: `qwen` → finds all Qwen variants
  - Case insensitive: `LLAMA-3` → "llama-3"
- **Fully Standalone**: Works without any API server running
- **Direct File Access**: Reads from local model files
- **Smart Search**: Advanced search with similarity scoring
- **Smart Recommendations**: Suggests models based on use case
- **Easy Integration**: Works with any MCP-compatible client
- **Helpful Suggestions**: Provides alternatives when exact matches aren't found

## Use Cases

The MCP server recognizes these use cases for recommendations:
- `code_generation`: Programming and code completion
- `creative_writing`: Stories, articles, creative content
- `image_generation`: Text-to-image generation
- `chat_conversation`: Conversational AI

## Directory Structure

The server expects this structure in your models directory:

```
models/
├── text/
│   ├── Qwen3-Coder-Flash/
│   │   ├── prompting.md
│   │   ├── parameters.json
│   │   ├── pitfalls.md
│   │   └── metadata.json
│   └── Llama-3.2-1B/
│       └── ...
├── image/
│   └── stable-diffusion/
│       └── ...
└── ...
```

## Contributing

To contribute improvements:
1. Fork the [SCAPO repository](https://github.com/czero-cc/SCAPO)
2. Make your changes in the `mcp/` directory
3. Submit a pull request

## License

Same as the parent [SCAPO](https://github.com/czero-cc/SCAPO) repository.