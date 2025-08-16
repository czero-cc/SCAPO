# klingai Prompting Guide

*Last updated: 2025-08-16*

## Tips & Techniques

- During a special sale, image creations on KlingAI did not cost any credits
- The API supports both free and paid Kling accounts.
- Key features of Kling API v1 include video generation from elements, special effects, virtual try-on, video extension, lip-syncing, and text-to-speech.
- Use KlingAI’s new 'Virtual Try-On' feature: first generate a virtual model (you can even use MidJourney for this), then pick basic tops and bottoms to showcase, upload everything to KlingAI and let the magic happen.
- The gift card option for KlingAI has the same cost/credit combos as regular subscription plans and is a one-time purchase with no auto-renew or need to cancel later
- Kling API v1 offers text-to-video, image-to-video, and image manipulation capabilities.
- Kling API v1 supports model versions 1.5, 1.6, and 2.0.
- You can select up to six elements within an image to define their motion trajectories (supported on 1.5 model).

## Recommended Settings

- kling_access_key=config.kling_access_key
- kling_secret_key=config.kling_secret_key
- alg=HS256
- typ=JWT
- iss=self.ak
- exp=int(time.time())+1800
- nbf=int(time.time())-5

## Sources

- Reddit community discussions
- User-reported experiences
