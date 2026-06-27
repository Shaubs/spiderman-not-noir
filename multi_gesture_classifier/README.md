# Multi-Gesture Classifier

A neural network classifier that detects multiple hand gestures including Spider-Man and Dr. Strange.

## Gestures Detected

| Gesture | Description | Detection |
|---------|-------------|-----------|
| **Spider-Man** 🕷️ | Thumb + Index + Pinky extended, Middle + Ring curled | ✅ |
| **Dr. Strange** 🔮 | All fingers spread wide (magic casting pose) | ✅ |
| **None** | No recognized gesture | Default |

## Training Results

```
📊 Final Evaluation:
   none: 99.45% accuracy
   spiderman: 50.00% accuracy  
   dr_strange: 100.00% accuracy

   Overall: 99.73% accuracy
```

Note: Spider-Man accuracy is lower due to limited positive samples (8). Consider collecting more Spider-Man training data for better detection.

## Usage

### As a Module

```python
from multi_gesture_classifier import MultiGestureClassifier

# Initialize
classifier = MultiGestureClassifier()

# Predict from hand landmarks (MediaPipe format)
result = classifier.predict(hand_landmarks)

print(f"Gesture: {result.gesture}")        # 'spiderman', 'dr_strange', or 'none'
print(f"Confidence: {result.confidence}")  # 0.0 to 1.0
print(f"All probs: {result.all_probs}")    # {'none': 0.1, 'spiderman': 0.2, 'dr_strange': 0.7}

# Check specific gestures
is_spiderman, conf = classifier.predict_spiderman(hand_landmarks)
is_dr_strange, conf = classifier.predict_dr_strange(hand_landmarks)
```

### Demo with Webcam

```bash
python multi_gesture_classifier/run_classifier.py
```

This opens a webcam window and shows detected gestures in real-time.

## Files

| File | Purpose |
|------|---------|
| `train.py` | Training script for the neural network |
| `run_classifier.py` | Runtime classifier with demo |
| `multi_gesture_model.pt` | Trained model weights |
| `__init__.py` | Module exports |

## Training

To retrain the model with new data:

```bash
# Add training samples to ffnn_training_samples/{gesture_name}/
# Then run:
python multi_gesture_classifier/train.py
```

### Training Data Format

```json
{
  "gesture": "dr_strange",
  "display_name": "Dr. Strange",
  "is_positive": true,
  "hand": "right",
  "samples": [
    {
      "hand_landmarks": [
        {"id": 0, "x": 0.5, "y": 0.5, "z": 0.0},
        // ... 21 landmarks total
      ]
    }
  ]
}
```

## Architecture

```
Input (82 features) → 128 → 64 → 32 → 3 classes (softmax)

Features:
  - 63 raw coordinates (21 landmarks × 3)
  - 19 derived features (palm orientation, finger extensions, etc.)
```

## Thresholds

Default confidence thresholds:
- Spider-Man: 70%
- Dr. Strange: 70%

Customize thresholds:
```python
classifier = MultiGestureClassifier(
    thresholds={'spiderman': 0.8, 'dr_strange': 0.6}
)
```

## Independence from Spider-Man Game

This classifier is **completely independent** from the Spider-Man: Not Noir game code. It can be used in any project that needs multi-gesture detection.

The original Spider-Man game continues to use its own binary classifier in `ffnn_classifier/` for optimal performance.
