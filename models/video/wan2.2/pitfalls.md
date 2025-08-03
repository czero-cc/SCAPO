# Common Pitfalls

## Overly Complex Motion Descriptions

Wan2.2 struggles with prompts that describe too many simultaneous movements or complex choreography.

**Example:** "A person juggling while riding a unicycle, doing backflips, and singing, with birds flying in formation around them"

**Severity:** high

**Solution:** Focus on one primary motion with simple secondary elements. Break complex scenes into multiple generations if needed.

---

## Inconsistent Physics

Requesting physically impossible or contradictory movements can cause artifacts and unstable generation.

**Example:** "Water flowing upward while fire burns underwater in zero gravity"

**Severity:** high

**Solution:** Ensure your prompt respects basic physics unless explicitly going for a surreal/fantasy style.

---

## Rapid Scene Changes

Attempting to include multiple scene changes or locations in a single short video.

**Example:** "Starting in Paris, then New York, ending in Tokyo" (in a 3-second video)

**Severity:** high

**Solution:** Focus on a single scene or use smooth transitions between closely related environments.

---

## Ignoring Aspect Ratio Impact

Not considering how aspect ratio affects composition and subject visibility.

**Example:** Using portrait orientation for landscape scenes or wide action sequences

**Severity:** medium

**Solution:** Match aspect ratio to content type: landscape for scenic, portrait for single subjects, square for balanced compositions.

---

## Overloading Style Modifiers

Using too many conflicting style descriptors that confuse the model.

**Example:** "Photorealistic cartoon anime oil painting sketch style"

**Severity:** medium

**Solution:** Choose one primary style and optionally one complementary modifier.

---

## Temporal Inconsistency in Descriptions

Describing actions that conflict with the specified duration.

**Example:** "A flower blooming from seed to full bloom" with duration=2 seconds

**Severity:** medium

**Solution:** Match action complexity to video duration. Quick actions for short videos, gradual changes for longer ones.

---

## Neglecting Lighting Consistency

Not maintaining consistent lighting throughout the prompt description.

**Example:** "Bright sunlight with deep shadows in a dark cave"

**Severity:** medium

**Solution:** Ensure lighting descriptions are coherent with the environment and maintain consistency.

---

## Face and Hand Detail Issues

Expecting perfect facial expressions or hand gestures in wide shots.

**Example:** "Wide landscape shot with person showing detailed emotional expressions"

**Severity:** high

**Solution:** Use appropriate shot types for the level of detail needed. Close-ups for faces/hands, wide shots for overall action.

---

## Excessive Camera Movement

Requesting complex camera movements that can cause motion sickness or instability.

**Example:** "Rapid spinning drone shot with quick zooms and shaky cam effect"

**Severity:** medium

**Solution:** Use smooth, purposeful camera movements. One primary movement type per video is usually best.