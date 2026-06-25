# Machine Learning Gesture Detection Guide

This guide covers training a machine learning model to detect custom hand gestures when rule-based detection isn't sufficient.

---

## When to Use ML

| Scenario | Approach |
|----------|----------|
| Simple, well-defined gesture | Rule-based |
| Complex gesture with variations | **ML** |
| Multiple similar gestures to distinguish | **ML** |
| Gesture varies significantly between people | **ML** |

---

## Prerequisites

Install required packages:
```bash
pip install scikit-learn numpy
```

---

## Step 1: Collect Training Data

### Capture Positive Samples (Your Gesture)

```bash
python analyze_gesture.py
```

1. Hold your target gesture
2. Press `c` to capture (50+ samples recommended)
3. Vary your hand position slightly between captures:
   - Different distances from camera
   - Slight angle variations
   - Different lighting if possible
4. Press `s` to save
5. Rename the file to `gesture_data/positive_samples.json`

### Capture Negative Samples (Non-Gestures)

1. Run `analyze_gesture.py` again
2. Show various **non-target** hand positions:
   - Open palm
   - Closed fist
   - Random finger positions
   - Different orientations
3. Capture 50+ samples
4. Save as `gesture_data/negative_samples.json`

---

## Step 2: Training Script

Create `train_gesture.py`:

```python
import json
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report, confusion_matrix
import pickle
import os


def load_samples(positive_file: str, negative_file: str):
    """Load gesture samples from JSON files."""
    
    X, y = [], []
    
    # Load positive samples
    with open(positive_file, 'r') as f:
        positive_samples = json.load(f)
    
    for sample in positive_samples:
        features = extract_features(sample["landmarks"])
        X.append(features)
        y.append(1)  # Positive class
    
    # Load negative samples
    with open(negative_file, 'r') as f:
        negative_samples = json.load(f)
    
    for sample in negative_samples:
        features = extract_features(sample["landmarks"])
        X.append(features)
        y.append(0)  # Negative class
    
    return np.array(X), np.array(y)


def extract_features(landmarks: list) -> list:
    """
    Extract features from landmarks.
    Using raw coordinates + relative distances for better accuracy.
    """
    features = []
    
    # Raw coordinates (21 landmarks × 3 coordinates = 63 features)
    for lm in landmarks:
        features.extend([lm["x"], lm["y"], lm["z"]])
    
    # Relative features (distances between key points)
    wrist = landmarks[0]
    
    # Fingertip distances from wrist
    fingertips = [4, 8, 12, 16, 20]
    for tip_idx in fingertips:
        tip = landmarks[tip_idx]
        dist_x = tip["x"] - wrist["x"]
        dist_y = tip["y"] - wrist["y"]
        features.extend([dist_x, dist_y])
    
    # Knuckle distances from wrist (palm orientation)
    knuckles = [5, 9, 13, 17]
    for knuckle_idx in knuckles:
        knuckle = landmarks[knuckle_idx]
        dist_y = knuckle["y"] - wrist["y"]
        features.append(dist_y)
    
    # Finger curl features (tip to pip distance)
    finger_pairs = [(8, 6), (12, 10), (16, 14), (20, 18)]  # tip, pip
    for tip_idx, pip_idx in finger_pairs:
        tip = landmarks[tip_idx]
        pip = landmarks[pip_idx]
        curl = tip["y"] - pip["y"]
        features.append(curl)
    
    return features


def train_model(X, y):
    """Train a Random Forest classifier with cross-validation."""
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    # Train model
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        min_samples_split=5,
        random_state=42
    )
    
    # Cross-validation
    cv_scores = cross_val_score(model, X_train, y_train, cv=5)
    print(f"\nCross-validation scores: {cv_scores}")
    print(f"Mean CV accuracy: {cv_scores.mean():.2%} (+/- {cv_scores.std() * 2:.2%})")
    
    # Fit on full training set
    model.fit(X_train, y_train)
    
    # Evaluate on test set
    y_pred = model.predict(X_test)
    
    print(f"\nTest set accuracy: {model.score(X_test, y_test):.2%}")
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=["Negative", "Positive"]))
    
    print("Confusion Matrix:")
    print(confusion_matrix(y_test, y_pred))
    
    return model


def save_model(model, filename="gesture_model.pkl"):
    """Save trained model to file."""
    with open(filename, 'wb') as f:
        pickle.dump(model, f)
    print(f"\nModel saved to {filename}")


def main():
    positive_file = "gesture_data/positive_samples.json"
    negative_file = "gesture_data/negative_samples.json"
    
    # Check files exist
    if not os.path.exists(positive_file):
        print(f"Error: {positive_file} not found")
        print("Run analyze_gesture.py to capture positive samples first.")
        return
    
    if not os.path.exists(negative_file):
        print(f"Error: {negative_file} not found")
        print("Run analyze_gesture.py to capture negative samples.")
        return
    
    print("Loading samples...")
    X, y = load_samples(positive_file, negative_file)
    print(f"Loaded {len(X)} samples ({sum(y)} positive, {len(y) - sum(y)} negative)")
    
    print("\nTraining model...")
    model = train_model(X, y)
    
    save_model(model)
    print("\nDone! Use MLGesture class to integrate the model.")


if __name__ == "__main__":
    main()
```

---

## Step 3: Run Training

```bash
python train_gesture.py
```

Expected output:
```
Loading samples...
Loaded 100 samples (50 positive, 50 negative)

Training model...

Cross-validation scores: [0.95 0.9  0.95 0.85 0.9 ]
Mean CV accuracy: 91.00% (+/- 7.48%)

Test set accuracy: 90.00%

Classification Report:
              precision    recall  f1-score   support
    Negative       0.91      0.91      0.91        11
    Positive       0.89      0.89      0.89         9

Confusion Matrix:
[[10  1]
 [ 1  8]]

Model saved to gesture_model.pkl
```

---

## Step 4: Create ML Gesture Class

Add to `gestures/ml_gesture.py`:

```python
import pickle
import os
from gesture_detector import Gesture
from typing import Optional


class MLGesture(Gesture):
    """Machine learning-based gesture detection."""
    
    def __init__(self, model_path: str = "gesture_model.pkl", 
                 gesture_name: str = "ml_gesture",
                 confidence_threshold: float = 0.8):
        
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model not found: {model_path}")
        
        with open(model_path, 'rb') as f:
            self.model = pickle.load(f)
        
        self._name = gesture_name
        self.confidence_threshold = confidence_threshold
    
    @property
    def name(self) -> str:
        return self._name
    
    def _extract_features(self, hand_landmarks) -> list:
        """Extract features matching training format."""
        features = []
        
        # Raw coordinates
        for lm in hand_landmarks:
            features.extend([lm.x, lm.y, lm.z])
        
        # Relative features
        wrist = hand_landmarks[0]
        
        # Fingertip distances from wrist
        for tip_idx in [4, 8, 12, 16, 20]:
            tip = hand_landmarks[tip_idx]
            features.extend([tip.x - wrist.x, tip.y - wrist.y])
        
        # Knuckle distances from wrist
        for knuckle_idx in [5, 9, 13, 17]:
            knuckle = hand_landmarks[knuckle_idx]
            features.append(knuckle.y - wrist.y)
        
        # Finger curl features
        for tip_idx, pip_idx in [(8, 6), (12, 10), (16, 14), (20, 18)]:
            tip = hand_landmarks[tip_idx]
            pip = hand_landmarks[pip_idx]
            features.append(tip.y - pip.y)
        
        return features
    
    def detect(self, hand_landmarks) -> Optional[float]:
        """Detect gesture using ML model."""
        features = self._extract_features(hand_landmarks)
        
        # Get prediction and probability
        prediction = self.model.predict([features])[0]
        probabilities = self.model.predict_proba([features])[0]
        confidence = probabilities[1]  # Probability of positive class
        
        if prediction == 1 and confidence >= self.confidence_threshold:
            return confidence
        
        return None
```

---

## Step 5: Integrate into Main

Update `main.py`:

```python
from gestures.ml_gesture import MLGesture

# In main():
detector.register_gesture(MLGesture(
    model_path="gesture_model.pkl",
    gesture_name="custom_gesture",
    confidence_threshold=0.8
))
```

---

## Improving Accuracy

### More Training Data
- Capture 100+ samples of each class
- Include variations in lighting, distance, angle

### Feature Engineering
Add more features to `extract_features()`:
- Angles between fingers
- Hand size normalization
- Velocity (if tracking over time)

### Hyperparameter Tuning
```python
from sklearn.model_selection import GridSearchCV

param_grid = {
    'n_estimators': [50, 100, 200],
    'max_depth': [5, 10, 15, None],
    'min_samples_split': [2, 5, 10]
}

grid_search = GridSearchCV(
    RandomForestClassifier(random_state=42),
    param_grid,
    cv=5,
    scoring='accuracy'
)
grid_search.fit(X_train, y_train)
print(f"Best params: {grid_search.best_params_}")
```

### Try Different Models
```python
from sklearn.svm import SVC
from sklearn.neural_network import MLPClassifier

# SVM
svm_model = SVC(kernel='rbf', probability=True)

# Neural Network
nn_model = MLPClassifier(
    hidden_layer_sizes=(64, 32),
    max_iter=500
)
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Low accuracy | Collect more diverse training data |
| False positives | Increase `confidence_threshold` |
| False negatives | Decrease `confidence_threshold` or add more positive samples |
| Overfitting | Reduce `max_depth`, increase `min_samples_split` |

---

## File Checklist

```
gesture_data/
├── positive_samples.json    # Your gesture samples
└── negative_samples.json    # Non-gesture samples

gestures/
├── __init__.py
├── spiderman.py             # Rule-based gestures
└── ml_gesture.py            # ML-based gesture class

train_gesture.py             # Training script
gesture_model.pkl            # Trained model (generated)
```

---

**← Back to [Gesture Detection Plan](gesture_detection_plan.md)**
