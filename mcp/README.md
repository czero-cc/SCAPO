# SCAPO MCP Server

A Model Context Protocol (MCP) server for querying AI/ML best practices from the SCAPO (Stay Calm and Prompt On) knowledge base.

## Installation

You can use this MCP server directly with `npx` (no Python required):

```bash
npx @scapo/mcp-server
```

Or install it globally:

```bash
npm install -g @scapo/mcp-server
```

## Usage with Claude Desktop

Add this to your Claude Desktop configuration file:

### Windows
Edit `%APPDATA%\Claude\claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "scapo": {
      "command": "npx",
      "args": ["@scapo/mcp-server"],
      "env": {
        "SCAPO_MODELS_PATH": "C:\\path\\to\\scapo\\models"
      }
    }
  }
}
```

### macOS
Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "scapo": {
      "command": "npx",
      "args": ["@scapo/mcp-server"],
      "env": {
        "SCAPO_MODELS_PATH": "/path/to/scapo/models"
      }
    }
  }
}
```

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
- category: Model category ("text", "image", "video", "audio", "multimodal", "all")
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

- **No Python Required**: Pure Node.js implementation using npx
- **Fully Standalone**: Works without any API server running
- **Direct File Access**: Reads from local model files
- **Smart Search**: Searches models by name locally
- **Smart Recommendations**: Suggests models based on use case
- **Easy Integration**: Works seamlessly with Claude Desktop

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

## Advantages Over Python Version

1. **No Python Setup**: Works with just Node.js (which Claude Desktop already has)
2. **Simple npx Usage**: One command to run, no installation needed
3. **Better IDE Integration**: Works seamlessly with Cursor and other IDEs
4. **Faster Startup**: Node.js starts faster than Python
5. **Native JSON Handling**: Better performance for JSON operations

## Contributing

To publish updates to npm:

```bash
cd mcp
npm version patch  # or minor/major
npm publish --access public
```

## License

Same as the parent SCAPO repository.