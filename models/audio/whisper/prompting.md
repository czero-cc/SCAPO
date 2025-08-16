# Whisper Prompting Guide

*Last updated: 2025-08-16*

## Tips & Techniques

- Use faster-whisper-server (now speaches) for a local STT server that adheres to the Open AI Whisper API
- Use the offline version of Whisper that does not require an API key so you won't be paying a few cents each time the scripts run
- It can recognize speech in numerous languages and convert it to text.
- I believe in the power of open-source tools and want to share how you can set up a free, private, and unlimited transcription system on your own computer using OpenAI's Whisper.
- Use transcribe(file_path, language="en", beam_size=5, no_speech_threshold=0.3, condition_on_previous_text=False, temperature=0, vad_filter=True) to minimize hallucinations
- Use curl to send audio to local Whisper API: curl -X POST -F "audio=@/2025-02-03_14-31-12.m4a" -F "model=base" http://192.168.60.96:5000/transcribe
- MacWhisper is a free Mac app to transcribe audio and video files for easy transcription and subtitle generation.

## Recommended Settings

- language=en
- beam_size=5
- no_speech_threshold=0.3
- condition_on_previous_text=False
- temperature=0
- vad_filter=True
- model=base
- endpoint=http://192.168.60.96:5000/transcribe

## Sources

- Reddit community discussions
- User-reported experiences
