# ADR-006: Data Collection Strategy for Random Forest Training

**Date:** 2026-06-25  
**Status:** Accepted

## Context

To train a Random Forest classifier for Spider-Man gesture detection, we need to collect labeled training data. The data collection process has challenges:

1. **Transition noise:** When pressing keys to start/stop recording, hand position changes
2. **Setup time:** User needs time to position hand correctly after pressing start
3. **Data quality:** Need clean samples without motion artifacts

## Decision

**Create a dedicated Data Collection Lab** with automatic trimming of start/end frames.

### Key Features

1. **Auto-trimming:** First and last 4 seconds of each recording are automatically discarded
   - First 4s: User is getting into position after pressing 's'
   - Last 4s: User is moving to press 's' to stop

2. **Combined capture:** Each sample includes:
   - Hand landmarks (21 points × 3 coordinates)
   - Pose landmarks (shoulder, elbow, wrist)
   - Handedness (Left/Right)
   - Timestamp

3. **Visual feedback:**
   - Recording indicator (flashing red dot)
   - "GET READY" warning during trim zone
   - Elapsed time and usable time counters
   - Sample count

### Recording Flow

```
Press 's'
    │
    ▼
┌─────────────────┐
│  TRIM ZONE      │  ← First 4 seconds (discarded)
│  "GET READY"    │     User positions hand
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  CAPTURE ZONE   │  ← Usable samples collected
│  Hold gesture   │     (minimum 4 seconds)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  TRIM ZONE      │  ← Last 4 seconds (discarded)
│  (moving to     │     User reaches for 's' key
│   press 's')    │
└────────┬────────┘
         │
         ▼
Press 's' to stop
```

### Minimum Recording Duration

```
4s (start trim) + 4s (usable) + 4s (end trim) = 12 seconds minimum
```

Recommended: **15-20 seconds** per recording session.

## Implementation

### File Structure

```
data_creation_lab/
├── __init__.py
├── collect_samples.py    # Main collection script
├── README.md             # Instructions
└── samples/              # Output directory
    ├── spiderman_samples_20260625_103000.json
    └── ...
```

### Output Format

```json
{
  "gesture": "spiderman_palm_up",
  "recorded_at": "2026-06-25T10:30:00",
  "num_samples": 180,
  "trim_seconds": 4,
  "samples": [
    {
      "timestamp": 1234567890.123,
      "hand_landmarks": [{"id": 0, "x": 0.5, "y": 0.5, "z": 0.0}, ...],
      "pose_landmarks": {
        "left_elbow": [0.3, 0.4, 0.0],
        "left_wrist": [0.35, 0.5, 0.0],
        ...
      },
      "handedness": "Right"
    }
  ]
}
```

## Consequences

- ✅ Clean training data without transition artifacts
- ✅ User has time to position hand correctly
- ✅ No need to manually edit recorded data
- ✅ Visual feedback helps user understand recording state
- ⚠️ Requires longer recording sessions (12s minimum)
- ⚠️ Short accidental recordings produce no usable data (by design)

## Usage

```bash
python data_creation_lab/collect_samples.py
```

### Controls

| Key | Action |
|-----|--------|
| `s` | Start/Stop recording |
| `p` | Toggle pose landmarks |
| `n` | Toggle hand numbers |
| `q` | Quit |

## Data Collection Plan

### Positive Samples (Spider-Man Gesture)
- Palm facing UP
- Index + pinky extended
- Middle + ring folded
- Multiple sessions with slight variations
- **Target:** 50+ samples per session, 3-5 sessions

### Negative Samples (Non-Gestures)
- Open palm
- Closed fist
- Random finger positions
- Different orientations
- **Target:** Match positive sample count

## References

- [ADR-002: Random Forest vs Neural Network](002-random-forest-vs-neural-network.md)
- [ML Gesture Guide](../ml_gesture_guide.md)
