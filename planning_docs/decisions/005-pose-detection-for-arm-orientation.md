# ADR-005: Add Pose Detection for Arm Orientation

**Date:** 2026-06-25  
**Status:** Proposed

## Context

Current palm orientation detection relies solely on hand landmark positions (wrist vs knuckles). This has limitations:

1. **No elbow information** - Cannot determine arm angle
2. **Ambiguous palm facing** - Hard to tell if palm faces camera or away
3. **False positives** - Similar finger positions in different arm orientations

MediaPipe Hand Landmarker only detects 21 hand points (wrist to fingertips). It does NOT detect the elbow or shoulder.

## Decision

**Add MediaPipe Pose Landmarker** alongside Hand Landmarker to detect arm orientation.

### Pose Landmarks Used

| Index | Name | Purpose |
|-------|------|---------|
| 11 | Left Shoulder | Arm origin |
| 12 | Right Shoulder | Arm origin |
| 13 | Left Elbow | Arm angle |
| 14 | Right Elbow | Arm angle |
| 15 | Left Wrist | Connect to hand |
| 16 | Right Wrist | Connect to hand |

### Combined Detection

```
Pose Landmarker          Hand Landmarker
       │                        │
       ▼                        ▼
┌─────────────┐          ┌─────────────┐
│  Shoulder   │          │   Wrist     │
│    Elbow    │◄─match──▶│  21 Points  │
│    Wrist    │          │  (fingers)  │
└─────────────┘          └─────────────┘
       │                        │
       ▼                        ▼
   Arm Angle              Finger Pose
       │                        │
       └──────────┬─────────────┘
                  ▼
         Combined Gesture Detection
```

### Arm Orientation Features

From pose landmarks, we can compute:

1. **Arm vector:** `elbow → wrist` direction
2. **Arm angle:** Angle relative to vertical
3. **Palm facing:** Cross-product of arm vector and shoulder-to-shoulder vector

## Consequences

- ✅ More accurate palm orientation detection
- ✅ Can require specific arm positions (e.g., arm extended forward)
- ✅ Reduces false positives from random hand positions
- ⚠️ Requires full body in frame (at least upper body)
- ⚠️ Additional CPU usage (two models running)
- ⚠️ Pose model file download (~4MB)

## Implementation

### Updated HandTracker

```python
class HandTracker:
    def __init__(self, enable_pose=True):
        self.hand_detector = ...  # Hand Landmarker
        self.pose_detector = ...  # Pose Landmarker (optional)
    
    def detect_all(self, frame):
        """Detect both hands and pose."""
        hand_results = self.detect(frame)
        pose_results = self.detect_pose(frame)
        return hand_results, pose_results
```

### PoseLandmarks Dataclass

```python
@dataclass
class PoseLandmarks:
    left_shoulder: Optional[tuple] = None
    right_shoulder: Optional[tuple] = None
    left_elbow: Optional[tuple] = None
    right_elbow: Optional[tuple] = None
    left_wrist: Optional[tuple] = None
    right_wrist: Optional[tuple] = None
```

## Future Enhancements

- [ ] Compute arm angle for gesture requirements
- [ ] Match pose wrist to hand wrist for hand-to-arm association
- [ ] Require arm extended forward for Spider-Man gesture
- [ ] Use shoulder-elbow-wrist angle for more precise orientation

## References

- [MediaPipe Pose Landmarker](https://ai.google.dev/edge/mediapipe/solutions/vision/pose_landmarker)
- [ADR-004: Upside-Down Palm Requirement](004-upside-down-palm-requirement.md)
