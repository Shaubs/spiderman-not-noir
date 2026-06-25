# Data Creation Lab

Tools for collecting and preparing training data for gesture recognition.

## Quick Start

```bash
# From project root
python data_creation_lab/collect_samples.py
```

## Workflow

### 1. Collect Positive Samples (Spider-Man Gesture)

1. Run `collect_samples.py`
2. Position hand with **palm facing UP**
3. Make Spider-Man gesture (index + pinky extended, middle + ring folded)
4. Press **'s'** to start recording
5. Hold gesture steady for **10-15 seconds**
6. Press **'s'** to stop

The first and last 4 seconds are automatically trimmed.

### 2. Collect Negative Samples

Run the same script but show **non-gesture** hand positions:
- Open palm
- Closed fist
- Random finger positions
- Different orientations

Rename the output file to indicate negative samples.

### 3. Organize Data

```
data_creation_lab/
├── samples/
│   ├── spiderman_samples_20260625_*.json  # Positive samples
│   └── negative_samples_20260625_*.json   # Negative samples
└── ...
```

## Controls

| Key | Action |
|-----|--------|
| `s` | Start/Stop recording |
| `p` | Toggle pose landmarks |
| `n` | Toggle hand landmark numbers |
| `q` | Quit |

## Output Format

Each JSON file contains:

```json
{
  "gesture": "spiderman_palm_up",
  "recorded_at": "2026-06-25T10:30:00",
  "num_samples": 180,
  "trim_seconds": 4,
  "samples": [
    {
      "timestamp": 1234567890.123,
      "hand_landmarks": [
        {"id": 0, "x": 0.5, "y": 0.5, "z": 0.0},
        ...
      ],
      "pose_landmarks": {
        "left_elbow": [0.3, 0.4, 0.0],
        "left_wrist": [0.35, 0.5, 0.0],
        ...
      },
      "handedness": "Right"
    },
    ...
  ]
}
```

## Tips

1. **Lighting**: Ensure consistent lighting
2. **Background**: Plain backgrounds work better
3. **Distance**: Keep hand 1-2 feet from camera
4. **Variations**: Record multiple sessions with slight variations
5. **Duration**: Record at least 10 seconds (after trimming = 2s usable minimum)
