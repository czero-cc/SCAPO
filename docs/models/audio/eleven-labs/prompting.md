# Eleven Labs Prompting Guide

*Last updated: 2025-08-16*

## Tips & Techniques

- I built my own tool, just for me. No subscriptions, no limits, just fast, clean voice generation. Cost me ~ $4/month to run.
- Use ElevenLabsService(voice_name="Mun W") in Manim Voiceover
- MiniMax have daily credit refresh in TTS not like ElevenLabs where you need to wait 1 month to refresh.
- The ElevenLabs voice agent is the entry point into the whole system, and then it will pass off web development or web design requests over to n8n agents via a webhook in order to actually do the work.
- Use the free plan to get 10,000 credits per month for free.
- So, when I do, I use a temporary email to create a new account so the 10,000 chatacter limit 'resets.'
- self.set_speech_service(ElevenLabsService(voice_name="Mun W"))
- MacWhisper 11.10 supports ElevenLabs Scribe for cloud transcription.
- from manim_voiceover.services.elevenlabs import ElevenLabsService
- I built my own tool to avoid ElevenLabs fees.
- When converting text to voice, adding periods between letters (e.g., B.O.D.) can force the model to pronounce acronyms letter by letter, though it may consume more credits.
- ElevenLabs Scribe v1 achieves 15.0% WER on 5-10 minute patient-doctor chats, averaging 36 seconds per file.

## Recommended Settings

- voice_name=Mun W
- Server URL=https://9df9e70d40a2.ngrok-free.app/v1/big-chief
- Model ID=gemini-2.0-flash
- API Key=YOUR_API_KEY

## Sources

- Reddit community discussions
- User-reported experiences
