# GitHub Copilot - Common Pitfalls & Issues

*Last updated: 2025-08-14*

## Technical Issues

### ⚠️ GitHub Copilot keeps suggesting API keys ending in '9e1': when typing openai_key = "sk-", Copilot autocompletes an OpenAI API key that ends with '9e1', and similarly for AWS keys, always ending with '9e1'.
**Fix**: Store API keys in environment variables or use a secrets manager.

### ⚠️ I’ve tried various tools - GitHub Copilot, Gemini CLI, Lovable, and Cursor (and probably a few others I’ve forgotten) - but apart from very simple HTML/CSS projects, I’ve never managed to complete something that actually worked. It always ends in an endless loop of the AI trying to fix bugs.

### ⚠️ I’ve already tried GitHub Copilot Pro (with GPT-4.1) and Claude 4 inside VS Code, but honestly… they were pretty bad. Neither could fix simple bugs or handle multi-file logic cleanly.

### ⚠️ GitHub Copilot extension lost Gemini API access: using gemini-2.5-pro API through the GitHub Copilot extension in VS Code, the model is gone and the ability to add new API keys is gone (besides Groq and OpenRouter). All versions of the extension break and give no models to select other than the Pre-Release version currently...
**Fix**: Store API keys in environment variables or use a secrets manager.

### ⚠️ GitHub Copilot fails in VS Code OSS Production Build: Extension 'GitHub.copilot-chat' CANNOT use API proposal: chatParticipantPrivate. Its package.json#enabledApiProposals-property declares: but NOT chatParticipantPrivate. Similar errors for other proposed APIs like ...

