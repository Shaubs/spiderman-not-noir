# ADR-003: State Machine for Gesture Sequence Detection

**Date:** 2026-06-25  
**Status:** Proposed

## Context

Static gesture detection (identifying "Spider-Man hand" pose) is implemented. However, the full gesture requires detecting a **sequence of movements**:

1. Spider-Man hand appears
2. Hand moves UP
3. Hand moves DOWN (web-shooting motion)

A single-frame classifier cannot detect this temporal sequence.

## Decision

**Implement a State Machine** that tracks gesture progression across video frames.

### State Machine Design

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  ┌──────────┐    Hand      ┌──────────┐    Wrist    ┌────────┐ │
│  │ STATE 0  │──detected───▶│ STATE 1  │────UP──────▶│STATE 2 │ │
│  │ Looking  │              │ Record   │             │ Armed  │ │
│  │          │◀──timeout────│ Position │◀──timeout───│        │ │
│  └──────────┘              └──────────┘             └───┬────┘ │
│       ▲                                                 │      │
│       │                                            Wrist DOWN  │
│       │                                                 │      │
│       │         ┌──────────┐                           ▼      │
│       └─────────│ STATE 3  │◀──────────────────────────┘      │
│                 │ TRIGGER! │                                   │
│                 └──────────┘                                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### States

| State | Name | Description | Transition Condition |
|-------|------|-------------|---------------------|
| 0 | LOOKING | Waiting for Spider-Man hand | Hand detected → State 1 |
| 1 | DETECTED | Hand found, record wrist Y position | Wrist moves UP by X pixels → State 2 |
| 2 | ARMED | Hand raised, waiting for downward motion | Wrist moves DOWN by Y pixels → State 3 |
| 3 | TRIGGERED | Gesture complete! Fire action | Reset → State 0 |

### Parameters

```python
UPWARD_THRESHOLD = 50    # pixels wrist must move up
DOWNWARD_THRESHOLD = 30  # pixels wrist must move down
TIMEOUT_FRAMES = 30      # frames before state resets (~1 second at 30fps)
```

## Consequences

- ✅ ML model stays simple (static pose detection only)
- ✅ State machine handles all temporal logic
- ✅ Easy to debug - can log state transitions
- ✅ Tunable thresholds for sensitivity
- ✅ Can add visual feedback per state
- ⚠️ Requires tracking across frames (minimal memory)
- ⚠️ Need to handle hand loss mid-gesture

## Implementation Plan

1. Create `GestureStateMachine` class
2. Track wrist Y position history
3. Implement state transitions with timeouts
4. Add visual feedback (show current state on screen)
5. Fire callback on TRIGGERED state

## References

- [Gesture Detection Plan](../gesture_detection_plan.md)
