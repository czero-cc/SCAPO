# CivitAI Prompting Guide

*Last updated: 2025-08-16*

## Tips & Techniques

- Use civitdl v2.0.0 for batch downloading from CivitAI: pip install civitdl --upgrade.
- Finally, I realized that I was using the model page URL instead of the model ***download*** link 😅😝.
- Using wget or curl with the CivitAI API key to download models.
- CivitAI making style LoRAs with only 10 epochs and less than 1,000 steps

## Recommended Settings

- remote_api_tokens.url_regex=civitai.com
- remote_api_tokens.token=11111111111111111111111111111111111
- engine=kohya
- unetLR=0.0001
- clipSkip=1
- loraType=lora

## Sources

- Reddit community discussions
- User-reported experiences
