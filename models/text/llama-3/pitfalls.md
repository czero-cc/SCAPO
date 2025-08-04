# Common Pitfalls - Llama-3

## Be aware of potential bugs in GGUF models or llama...

Be aware of potential bugs in GGUF models or llama.cpp implementations, as subtle issues can negatively impact inference quality.

**Severity:** medium

**Solution:** See description for details

---

## Avoid relying on early or untested GGUF models, as...

Avoid relying on early or untested GGUF models, as they may contain bugs or performance issues.

**Severity:** medium

**Solution:** See description for details

---

## Running large language models locally with substan...

Running large language models locally with substantial context windows (50k-150k tokens) on consumer hardware (e.g., Macs) can be slow (5+ minutes per output) and may not be practical for many coding tasks.

**Severity:** medium

**Solution:** See description for details

---

## Local LLMs are generally better suited for tasks w...

Local LLMs are generally better suited for tasks with smaller context windows. Large context window performance is limited by hardware requirements.

**Severity:** medium

**Solution:** See description for details

---

## Avoid prompt injection attacks by carefully saniti...

Avoid prompt injection attacks by carefully sanitizing user inputs and limiting the LLM's ability to execute arbitrary commands or access sensitive data.

**Severity:** medium

**Solution:** See description for details

---

## Avoid relying solely on GUI tools (like LM Studio)...

Avoid relying solely on GUI tools (like LM Studio) if CPU tensor offloading is a critical requirement. Raw llama.cpp offers more flexibility in this area.

**Severity:** medium

**Solution:** See description for details

---

## Avoiding overly complex prompts. Break down comple...

Avoiding overly complex prompts. Break down complex tasks into smaller, simpler steps and guide the model incrementally.

**Severity:** medium

**Solution:** See description for details

---

