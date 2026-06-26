# ADR-018: Dr. Strange Gesture - Multi-Gesture Classifier

## Status
Accepted

## Date
2026-06-27

## Context

The original Spider-Man game only detected the Spider-Man hand gesture (thumb, index, and pinky extended). We wanted to add variety with a new gesture inspired by Dr. Strange's magic hand pose, which would trigger a different visual effect.

### Dr. Strange Gesture Definition
The Dr. Strange gesture consists of:
- **Thumb**: Extended
- **Index finger**: Extended  
- **Middle finger**: Extended (or partially extended)
- **Ring finger**: Curled
- **Pinky**: Extended

This creates a hand pose similar to the mystic arts hand signs from the Marvel movies.

## Decision

### Multi-Gesture Classifier Architecture

Instead of modifying the existing Spider-Man classifier, we created a **new multi-gesture classifier** as a separate module:

```
multi_gesture_classifier/
├── __init__.py
├── train.py              # Training script
├── run_classifier.py     # Runtime classifier with demo
└── multi_gesture_model.pt # Trained model (3-class)
```

### Model Architecture

- **Type**: Feed-forward Neural Network (FFNN)
- **Input**: 21 landmarks × 3 coordinates = 63 features (normalized)
- **Hidden Layers**: 128 → 64 → 32 neurons with ReLU + Dropout(0.3)
- **Output**: 3 classes (none, spiderman, dr_strange)
- **Training**: Adam optimizer, CrossEntropyLoss, 100 epochs

### Training Data

Data was collected and processed from the `ffnn_training_samples/` directory:
- **none**: 1808 samples (from random, open_palm, closed_fist, thumbs_up, loser, l_sign)
- **spiderman**: 8 samples (from spiderman gesture files)
- **dr_strange**: 24 samples (from dr_strange gesture files)

Despite class imbalance, the model achieved **99.73% accuracy** due to the distinct hand poses.

### Performance
```
Epoch 100/100, Loss: 0.0020
Accuracy: 99.73%
Classification Report:
              precision    recall  f1-score   support
           0       1.00      1.00      1.00       353
           1       1.00      1.00      1.00         5
           2       1.00      0.95      0.97        19
```

## Implementation

### Visual Effects - Fire Magic Circle

When Dr. Strange gesture is detected and **held for 1.5 seconds**:

1. **Magic Circle Spawns**: Centered between landmarks 16 (ring finger tip) and 20 (pinky tip)
2. **Fire Color Palette** (BGR):
   ```python
   FIRE_COLORS = [
       (0, 50, 139),    # Dark red/brown
       (0, 69, 190),    # Deep orange
       (0, 100, 220),   # Orange
       (0, 140, 255),   # Bright orange
       (30, 180, 255),  # Yellow-orange
       (50, 200, 255),  # Light orange/yellow
   ]
   ```

3. **Circle Components**:
   - Outer glow rings (4 concentric circles)
   - Main pulsing circle (radius 10px with sinusoidal pulse)
   - 8 revolving fire particles at varying radii
   - 6 inner sparks rotating opposite direction
   - Connecting lines to landmarks 16 and 20

4. **Path Tracing**:
   - Records hand position as user moves
   - Maximum 100 points stored
   - Fire trail fades over 3 seconds
   - Line thickness and brightness decrease with age
   - Flickering particles along the path

### Integration in game.py

```python
# State variables
dr_strange_start_time = None
dr_strange_magic_active = False
dr_strange_hand_landmarks = None
dr_strange_circle_angle = 0.0
dr_strange_path = []  # [(x, y, timestamp), ...]

# Constants
DR_STRANGE_HOLD_TIME = 1.5
DR_STRANGE_PATH_MAX_POINTS = 100
DR_STRANGE_PATH_FADE_TIME = 3.0
```

The classifier runs on each frame alongside the Spider-Man detector, with no significant performance impact due to the lightweight FFNN architecture.

## Consequences

### Positive
- Adds variety to gameplay with a new gesture
- Visual effect is distinct and eye-catching (fire vs spider webs)
- Modular design - multi_gesture_classifier is independent
- Easy to add more gestures in the future (just add training data)
- Path tracing creates satisfying "drawing in the air" experience

### Negative
- Additional model file (~100KB) in distribution
- Slight increase in per-frame computation
- Training data is imbalanced (but doesn't affect accuracy significantly)

### Future Considerations
- Could add more gestures (Hulk smash, Iron Man repulsor, etc.)
- Path tracing could be extended to recognize shapes/runes
- Could add sound effects for Dr. Strange activation

## References
- ADR-008: FFNN Implementation Results
- Multi-gesture classifier: `multi_gesture_classifier/`
- Training samples: `ffnn_training_samples/dr_strange/`
