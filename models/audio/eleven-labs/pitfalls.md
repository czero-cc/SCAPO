# Eleven Labs - Common Pitfalls & Issues

*Last updated: 2025-08-14*

## Technical Issues

### ⚠️ crashes when X>100

### ⚠️ hitting walls trying to figure out how to get their ElevenLabs API key properly set up
**Fix**: Store API keys in environment variables or use a secrets manager.

### ⚠️ Error when accessing eleven labs api from a selfhosted n8n.

### ⚠️ Playing back a female voice regardless of male/female voice selection when using the ElevenLabs API in a JS chatbot.

### ⚠️ Encountered a 401 Client Error: Unauthorized when trying to add audio to cards using the ElevenLabs API with HyperTTS.

### ⚠️ Unable to switch back to a Custom LLM after testing with a built-in model (`gemini-2.0-flash`) on the ElevenLabs Conversational AI dashboard, even after correctly filling out Server URL (e.g., `https://9df9e70d40a2.ngrok-free.app/v1/big-chief`), Model ID (e.g., `gemini-2.0-flash`), and API Key. The interface shows an error message about fixing errors even when there are no errors.
**Fix**: Store API keys in environment variables or use a secrets manager.

### ⚠️ API keys for ElevenLabs were compromised in a hack affecting Rabbit R1.
**Fix**: Store API keys in environment variables or use a secrets manager.

## Policy & Account Issues

### ⚠️ Eleven Labs just wiped 400,000 credits from a $99/month plan account because the paywall wouldn't let the user renew their subscription despite having 60% of credits remaining and submitting a support ticket.
**Note**: Be aware of terms of service regarding account creation.

## Cost & Limits

### 💰 Getting ElevenLabs to accept calls from another provider than Twilio is difficult; calls are routed to the PBX, then forwarded to the Twilio number, costing more.

### 💰 ElevenLabs Creator plan ($22/month, 100k characters)

### 💰 ElevenLabs free plan offers 10k characters each month.

### 💰 ElevenLabs Creator plan is $22/month with a 100k character limit.

