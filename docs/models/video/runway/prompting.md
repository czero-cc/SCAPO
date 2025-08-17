# Runway Prompting Guide

*Last updated: 2025-08-16*

## Tips & Techniques

- Runway is pretty user-friendly, but only lets you input 30 seconds of video at a time.
- Use Gen-4 References via the Runway API to generate images with up to 3 reference images per request.
- Obtain an API key from https://dev.runwayml.com/ to access Runway’s image generation features.
- Use automation to bypass throttling on Unlimited accounts
- Use the Python SDK v3.1 for easier integration with Runway services.

## Recommended Settings

- credits_per_video=25
- standard_plan_videos=25
- standard_plan_credits=625
- pro_plan_videos=90
- pro_plan_credits=2250
- unlimited_plan_cost=$95
- standard_plan_cost=$15
- pro_plan_cost=$35
- automation_workaround=use automation script
- credits_per_image=8
- cost_per_image=0.08
- max_references=3
- sdk_version=python_v3.1
- api_docs=https://docs.dev.runwayml.com/
- api_key_url=https://dev.runwayml.com/

## Sources

- Reddit community discussions
- User-reported experiences
