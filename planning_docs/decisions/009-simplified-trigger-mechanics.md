# ADR-009: Simplified Trigger Mechanics Based on Real-World Testing

## Status
Accepted

## Date
2026-06-25

## Context

After implementing the web shooter application with FFNN-based gesture detection and a 4-state state machine (LOOKING → DETECTED → ARMED → TRIGGERED), real-world testing revealed that the original trigger mechanics were too complex and didn't align with natural user behavior.

### Original Design
The original state machine required:
1. **LOOKING** → Detect Spider-Man hand → **DETECTED**
2. **DETECTED** → Move hand UP by 6% of frame height → **ARMED**
3. **ARMED** → Move hand DOWN by 4% of frame height → **TRIGGERED**
4. **TRIGGERED** → Fire web effect

### Observations from Testing

During real-world testing, the following behaviors were observed:

1. **Rapid Detection Toggling**: When the user makes the Spider-Man gesture and moves their hand quickly (simulating a "thwip" motion), the detection rapidly toggles between DETECTED and LOOKING states. This happens because:
   - Quick hand movement causes momentary loss of clear landmark detection
   - The gesture classifier confidence fluctuates during motion
   - This rapid toggling is actually a **natural indicator of the shooting motion**

2. **ARMED State = Intent to Shoot**: Reaching the ARMED state (hand moved up after detection) already indicates the user's clear intent to shoot. The additional requirement to move down adds unnecessary complexity.

3. **Sustained Detection = Intent to Shoot**: If the Spider-Man gesture is held steadily in DETECTED state for more than 1 second, this indicates the user is deliberately holding the pose, likely intending to shoot.

## Decision

We are modifying the state machine trigger mechanics based on these observations:

### New Trigger Conditions

The web will be triggered (shoot) under ANY of these conditions:

1. **Rapid Toggle Trigger**: If detection toggles between DETECTED and LOOKING more than 2 times within 1 second
   - This captures the natural "flicking" motion of a web shoot
   - Mimics the quick wrist action Spider-Man uses

2. **Armed State Trigger**: Reaching the ARMED state immediately triggers a shoot
   - If the user has moved their hand up while maintaining the gesture, they clearly intend to shoot
   - No need to wait for downward movement

3. **Sustained Detection Trigger**: If DETECTED state is maintained for longer than 1 second
   - Holding the pose steadily indicates deliberate intent
   - Provides an alternative trigger method for users who prefer stability over motion

### State Machine Simplification

The state machine is simplified to:
- **LOOKING**: No Spider-Man hand detected
- **DETECTED**: Spider-Man hand detected, tracking for trigger conditions
- **TRIGGERED**: Web fired (auto-resets to LOOKING after cooldown)

The ARMED state is effectively merged into the trigger conditions rather than being a separate state.

## Consequences

### Positive
- **More Natural Interaction**: Aligns with how users naturally try to "shoot" webs
- **Multiple Trigger Methods**: Users can trigger via quick motion OR sustained hold
- **Reduced Frustration**: No longer requires precise up-then-down motion
- **Better Responsiveness**: Captures the quick "thwip" motion that feels more Spider-Man-like

### Negative
- **Potential False Triggers**: Rapid toggling might occasionally trigger unintentionally
  - Mitigated by requiring 3+ toggles, not just 1-2
- **Less Precise Control**: Removes the deliberate "aim then shoot" mechanic
  - Acceptable trade-off for better user experience

### Neutral
- **Cooldown Required**: Need to implement a short cooldown (0.5-1s) between shots to prevent rapid-fire unintentional triggers

## Implementation Notes

1. Track toggle count and timestamps in the state machine
2. Add sustained detection timer
3. Implement cooldown period after each trigger
4. Remove or repurpose the ARMED state
5. Update UI to reflect new trigger indicators

## References
- ADR-003: State Machine for Gesture Sequence
- ADR-008: FFNN Implementation Results
