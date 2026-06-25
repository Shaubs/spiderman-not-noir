# Random Forest Classifier for Gesture Detection

This folder contains the training pipeline and model for gesture classification.

## Quick Start

### 1. Train the Model

```bash
python random_forest_classifier/train.py
```

### 2. Use the Model

```bash
python random_forest_classifier/run_classifier.py
```

## Files

| File | Description |
|------|-------------|
| `train.py` | Training script - loads samples, trains model, saves to `model.pkl` |
| `run_classifier.py` | Real-time classifier using trained model |
| `model.pkl` | Trained model (generated after training) |

## Training Data

Training data is loaded from `data_creation_lab/samples/`:
- Files named `spiderman_*.json` → Positive samples
- Files named `negative_*.json` → Negative samples

## Model Details

- **Algorithm:** Random Forest Classifier
- **Features:** 
  - 21 hand landmarks × 3 coordinates = 63 features
  - Relative finger positions
  - Finger curl measurements
