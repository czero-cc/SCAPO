# Kilo Code Prompting Guide

*Last updated: 2025-08-16*

## Tips & Techniques

- Get Your API Key: Visit https://build.nvidia.com/settings/api-keys to generate you
- Activate Kilo Code from anywhere with Cmd+Shift+A (Mac) or Ctrl+Shift+A (Windows)
- Flexible Credit Management: Control exactly when your balance reloads from your payment method—no monthly minimums or hidden fees
- Run llama.cpp in server mode (OpenAI-compatible API) for local inference
- Deploy Qdrant in Docker as the vector DB with cosine similarity
- I pay $20 and I get ~ $40 worth of AI usage (1000 o3 requests)
- Qdrant (Docker) as the vector DB (cosine)
- Use custom keyboard shortcuts for accepting suggestions
- Create a new config profile called 'Nano' that uses GPT-4.1-Nano instead of Claude 3.7 Sonnet to speed up the Enhance Prompt feature
- Use OpenRouter to set up Claude 4 in Kilo Code to avoid rate limiting
- If you purchase at least 10 credits on Openrouter, your daily limit is increased to 1000 :free model requests per day, which applies to Kilo Code.
- Kilo Code with built-in indexer
- Use Cmd+I for quick inline tasks directly in your editor - select code, describe what you want, get AI suggestions without breaking flow
- Configure the Enhance Prompt feature to use a different model (e.g., GPT-4.1-Nano) than your main coding tasks
- Use the MCP Marketplace to install AI capabilities with a single click
- When using Claude 4 in Kilo Code, note that the :thinking variety is not selectable.
- Use Kilo Code's built-in indexer for local-first codebase indexing
- Use Cmd+L: "Let Kilo Decide" - AI automatically suggests obvious improvements based on context
- llama.cpp in server mode (OpenAI-compatible API)
- Use nomic-embed-code (GGUF, Q6_K_L) as the embedder for 3,584-dim embeddings
- Enable system notifications to never miss approval requests even when the editor is minimized
- Use Openrouter API with at least $10 credits to increase daily limit to 1000 :free model requests per day for Kilo Code.
- nomic-embed-code (GGUF, Q6_K_L) as the embedder (3,584-dim)
- Local-first codebase indexing can be achieved by using Kilo Code with built-in indexer, llama.cpp server mode, nomic-embed-code, and Qdrant Docker.
- Set up Claude 4 through Openrouter to avoid immediate rate limiting in Kilo Code.

## Recommended Settings

- profile=Nano
- model=GPT-4.1-Nano
- global_shortcut=Cmd+Shift+A (Mac) or Ctrl+Shift+A (Windows)
- indexer=built-in
- llama.cpp=server_mode
- embedder=nomic-embed-code
- vector_db=Qdrant_Docker
- api_key_source=build.nvidia.com

## Sources

- Reddit community discussions
- User-reported experiences
