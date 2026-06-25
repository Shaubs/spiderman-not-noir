# ADR-001: Rule-Based vs Machine Learning for Gesture Detection

**Date:** 2026-06-25  
**Status:** Accepted

## Context

We need to detect hand gestures (specifically Spider-Man web-shooting gesture) from webcam input using MediaPipe hand landmarks (21 3D points per hand).

Two approaches were considered:
1. **Rule-Based:** Define explicit conditions based on finger positions
2. **Machine Learning:** Train a classifier on landmark features

## Decision

**Start with Rule-Based approach**, with ML as fallback.

### Rationale

| Factor | Rule-Based | ML |
|--------|------------|-----|
| Training data needed | None | 50-200+ samples |
| Implementation time | Fast | Slower |
| Interpretability | High | Low |
| Accuracy for simple gestures | Good | Good |
| Accuracy for complex gestures | Limited | Better |

For a well-defined gesture like Spider-Man hand (index + pinky extended, middle + ring folded), rule-based detection is sufficient and faster to implement.

## Consequences

- ✅ No training data collection required initially
- ✅ Easy to debug and tune thresholds
- ✅ Immediate iteration possible
- ⚠️ May need ML if gesture variations are too complex
- ⚠️ Rules need adjustment for different hand sizes/orientations

## References

- [Gesture Detection Plan](../gesture_detection_plan.md)
- [ML Gesture Guide](../ml_gesture_guide.md) (fallback path)
