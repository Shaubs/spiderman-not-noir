# ADR-004: Upside-Down Palm Orientation Requirement

**Date:** 2026-06-25  
**Status:** Accepted

## Context

Initial Spider-Man gesture detection had many false positives. The gesture was triggering on normal hand positions that happened to have similar finger configurations.

## Decision

**Require upside-down palm orientation** as a prerequisite for Spider-Man gesture detection.

### Definition of Upside-Down Palm

- Palm facing camera (exposed)
- Wrist/palm base positioned ABOVE the fingers
- Fingers pointing downward

### Detection Logic

```python
# Screen coordinates: Y increases downward
# Wrist above knuckles means wrist.y < knuckles.y

avg_knuckle_y = (index_mcp.y + middle_mcp.y + ring_mcp.y + pinky_mcp.y) / 4
palm_inverted = wrist.y < avg_knuckle_y - threshold
```

### Finger Position Inversion

For inverted palm, finger extension/fold logic is reversed:

| Condition | Normal Palm | Inverted Palm |
|-----------|-------------|---------------|
| Extended | tip.y < pip.y | tip.y > pip.y |
| Folded | tip.y > pip.y | tip.y < pip.y |

## Consequences

- ✅ Dramatically reduces false positives
- ✅ More natural for web-shooting motion (hand down, then swing up)
- ✅ Distinct from common hand positions
- ⚠️ Detection logic must account for inverted coordinates
- ⚠️ User must learn specific hand orientation

## References

- [Gesture Analysis Study](../gesture_analysis_study.md)
