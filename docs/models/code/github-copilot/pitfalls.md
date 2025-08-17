# GitHub Copilot - Common Pitfalls & Issues

*Last updated: 2025-08-14*

## Technical Issues

### ⚠️ GitHub Copilot fails in VS Code OSS production build due to proposed API and signature verification issues: Extension 'GitHub.copilot-chat' CANNOT use API proposal: chatParticipantPrivate. Its package.json#enabledApiProposals-property declares: but NOT chatParticipantPrivate. Similar errors for other proposed APIs like

### ⚠️ GitHub Copilot keeps suggesting API keys ending in '9e1' for OpenAI and AWS keys; the autocompleted keys always end with '9e1', which are random and do not work.
**Fix**: Store API keys in environment variables or use a secrets manager.

### ⚠️ GitHub Copilot extension lost Gemini API access; the ability to add new API keys is gone except for Groq and OpenRouter; all extension versions break and give no models to select other than the Pre-Release version currently.
**Fix**: Store API keys in environment variables or use a secrets manager.

