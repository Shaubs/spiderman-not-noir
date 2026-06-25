# Gesture Detection Plan

## Overview

This document outlines the approach for detecting custom hand gestures using MediaPipe hand landmarks.

**Related Decisions:**
- [ADR-001: Rule-Based vs ML](decisions/001-rule-based-vs-ml.md)
- [ADR-002: Random Forest vs Neural Network](decisions/002-random-forest-vs-neural-network.md)
- [ADR-003: State Machine for Gesture Sequence](decisions/003-state-machine-for-gesture-sequence.md)
- [ADR-004: Upside-Down Palm Requirement](decisions/004-upside-down-palm-requirement.md)

---

## Current Setup

### Hand Landmark Detection
- **MediaPipe HandLandmarker** detects 21 3D points per hand
- Each landmark has `x`, `y`, `z` coordinates (normalized 0-1)

### Landmark Reference
```
0  = Wrist
1-4  = Thumb (1=CMC, 2=MCP, 3=IP, 4=Tip)
5-8  = Index finger (5=MCP, 6=PIP, 7=DIP, 8=Tip)
9-12 = Middle finger
13-16 = Ring finger
17-20 = Pinky
```

---

## Two Approaches

| Approach | Complexity | Accuracy | Training Data Needed |
|----------|------------|----------|----------------------|
| **Rule-Based** | Low | Good for simple gestures | None |
| **Machine Learning** | Medium-High | Better for complex gestures | 50-200+ samples |

---

## Recommended: Rule-Based Analysis

### Step 1: Capture Samples

Run the gesture analyzer:
```bash
python analyze_gesture.py
```

Controls:
- `c` - Capture sample (capture 10-20 samples)
- `a` - Analyze captured samples
- `s` - Save data to JSON
- `r` - Reset/clear samples
- `q` - Quit

### Step 2: Hold Your Gesture

1. Position your hand with the target gesture
2. Press `c` multiple times (15-20 samples)
3. Move hand slightly between captures (different angles/distances)

### Step 3: Analyze

Press `a` to get:
- Percentage analysis of finger positions
- Suggested detection code

See **[Gesture Analysis Study](gesture_analysis_study.md)** for:
- Detailed explanation of percentage analysis methodology
- How to interpret results
- Recording study results and findings

### Step 4: Implement

Copy the suggested code into `gestures/spiderman.py` and test.

---

## Key Detection Logic

### Palm Orientation

**Upside-down palm** (wrist above fingers):
```python
# Screen coordinates: y increases downward
# So wrist.y < knuckles.y means wrist is ABOVE
avg_knuckle_y = (index_mcp.y + middle_mcp.y + ring_mcp.y + pinky_mcp.y) / 4
palm_inverted = wrist.y < avg_knuckle_y
```

### Finger Extended vs Folded

**Normal palm (fingers up):**
```python
# Extended: tip ABOVE pip (lower y value)
finger_extended = tip.y < pip.y

# Folded: tip BELOW pip (higher y value)  
finger_folded = tip.y > pip.y
```

**Inverted palm (fingers down):**
```python
# Extended: tip BELOW pip (higher y value)
finger_extended = tip.y > pip.y

# Folded: tip ABOVE pip (lower y value)
finger_folded = tip.y < pip.y
```

### Thresholds

Use thresholds to avoid false positives:
```python
EXTENSION_THRESHOLD = 0.04  # Minimum distance for "extended"
FOLD_THRESHOLD = 0.03       # Minimum distance for "folded"

# Check with threshold
index_extension = index_pip.y - index_tip.y
index_extended = index_extension > EXTENSION_THRESHOLD
```

---

## Spider-Man Gesture Definition

**Target gesture:** Upside-down exposed palm with index + pinky extended, middle + ring folded.

### Detection Criteria

1. **Palm inverted:** Wrist above knuckles
2. **Palm exposed:** Thumb spread outward (facing camera)
3. **Index extended:** Tip below PIP (for inverted palm)
4. **Pinky extended:** Tip below PIP
5. **Middle folded:** Tip above PIP
6. **Ring folded:** Tip above PIP

---

## Machine Learning Path (If Needed)

If rule-based detection isn't accurate enough, see the **[ML Gesture Guide](ml_gesture_guide.md)** for:

- Collecting training data (positive/negative samples)
- Training a Random Forest classifier
- Integrating ML model into the gesture system
- Hyperparameter tuning and troubleshooting

---

## File Structure

```
spiderman-not-noir/
├── main.py              # Entry point
├── hand_tracker.py      # Hand detection class
├── gesture_detector.py  # Gesture detection system
├── analyze_gesture.py   # Tool for analyzing new gestures
├── train_gesture.py     # ML training script (optional)
├── gestures/
│   ├── __init__.py
│   └── spiderman.py     # Gesture definitions
├── gesture_data/        # Captured samples (JSON)
└── snapshots/           # Hand orientation snapshots
```

---

## Tips

1. **Lighting matters:** Consistent lighting improves detection
2. **Distance:** Keep hand 1-2 feet from camera
3. **Background:** Plain backgrounds work better
4. **Thresholds:** Increase if too many false positives, decrease if gesture not detected
5. **Multiple samples:** Capture from different angles and distances
