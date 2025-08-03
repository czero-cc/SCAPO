# Common Pitfalls

## Overly Complex Prompts

GPT-4 can get confused with prompts that have too many nested instructions or conflicting requirements.

**Example:** "As an expert in X, Y, and Z, while considering A, B, and C, please analyze D but make sure to include E, F, G..."

**Severity:** high

**Solution:** Break complex tasks into sequential prompts or use clear section headers

---

## Assuming Perfect Memory

GPT-4 doesn't retain information between separate conversations and has a limited context window.

**Example:** Referencing information from a previous conversation without re-providing context

**Severity:** high

**Solution:** Always include necessary context in each prompt; use system messages for persistent instructions

---

## Ignoring Token Limits

Not accounting for token limits can result in truncated responses or errors.

**Example:** Requesting a 10,000 word essay when the model has a 4,096 token limit

**Severity:** medium

**Solution:** Be aware of token limits; break large tasks into smaller chunks

---

## Ambiguous Instructions

Vague or ambiguous instructions lead to inconsistent and unpredictable outputs.

**Example:** "Make it better" or "Fix this"

**Severity:** high

**Solution:** Provide specific, measurable criteria for improvement

---

## Over-relying on Default Parameters

Using default parameters for all use cases can lead to suboptimal results.

**Example:** Using temperature=1.0 for factual queries

**Severity:** medium

**Solution:** Adjust parameters based on use case: low temperature for facts, higher for creativity

---

## Not Validating Outputs

Assuming all model outputs are accurate without verification.

**Example:** Using generated statistics or citations without fact-checking

**Severity:** high

**Solution:** Always verify factual claims, especially numbers, dates, and citations

---

## Prompt Injection Vulnerabilities

Not sanitizing user inputs in production applications.

**Example:** Allowing users to override system instructions through their input

**Severity:** high

**Solution:** Use proper input validation and separate user content from instructions