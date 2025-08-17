# CivitAI - Common Pitfalls & Issues

*Last updated: 2025-08-16*

## Technical Issues

### ⚠️ Whenever I have a CivitAI tab open in Chrome, even on a page with relatively few images, the CPU and memory usage goes through the roof. The website consumes more memory than Stable Diffusion itself does when generating. If the CivitAI tab is left open too long, after a while the PC will completely blue screen.. This happened more and more often until the PC crashed entirely.

### ⚠️ Using civitai lora URLs with Replicate Flux Dev LoRA returns error: "Prediction failed. Command '['pget', 'https://civitai.com/api/download/models/947302?type=Model&format=SafeTensor&token=XXXXX']'"

### ⚠️ Prediction failed. Command '['pget', 'https://civitai.com/api/download/models/947302?type=Model&format=SafeTensor&token=XXXXX'" when using civitai lora URLs with Replicate.

### ⚠️ I've tried testing some CivitAI models, but when I try to generate images, the PC freezes and crashes. These models are around 20GB or more. My conclusion was that those models weren't made to run on my GPU, so I tried other model sizes around 11GB. They didn't work either, they give errors, but at least they don't freeze my PC. So far, only the 'flux1-dev-bnb-nf4-v2' mode

