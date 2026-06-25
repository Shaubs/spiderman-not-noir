# Feed Forward Neural Network Classifier

A PyTorch-based neural network for Spider-Man gesture classification.

## Why FFNN over Random Forest?

The Random Forest classifier had severe false positive issues:
- **Loser sign:** 70% false positive rate
- **Thumbs up:** 30% false positive rate  
- **Rock sign:** Also triggered false positives

These gestures share similar finger patterns but differ in palm orientation - something the RF couldn't learn well from synthetic negatives.

## Architecture

```
Input (82 features)
    ↓
Linear(82 → 64) + BatchNorm + ReLU + Dropout(0.3)
    ↓
Linear(64 → 32) + BatchNorm + ReLU + Dropout(0.3)
    ↓
Linear(32 → 16) + ReLU
    ↓
Linear(16 → 1) + Sigmoid
    ↓
Output (probability)
```

## Features (82 total)

**Raw coordinates (63):** 21 landmarks × 3 (x, y, z)

**Derived features (19):**
- Palm orientation (wrist y - middle knuckle y)
- Finger extension ratios (5)
- Finger curl angles (5)
- Hand openness
- Thumb-pinky distance
- Index-pinky angle
- Wrist angle
- Z-depth variance
- Palm normal vector (3)
- Hand scale

## Usage

### 1. Collect Negative Samples

**Critical:** Collect real samples of similar gestures:
```bash
python data_creation_lab/collect_samples.py
```

Save as:
- `loser_samples_*.json` (palm facing camera, index+pinky up)
- `thumbsup_samples_*.json`
- `rock_samples_*.json`
- `random_samples_*.json`

### 2. Train the Model

```bash
python ffnn_classifier/train.py
```

Options:
- `--epochs 100` - Number of training epochs
- `--lr 0.001` - Learning rate
- `--batch-size 32` - Batch size

### 3. Run Real-Time Classifier

```bash
python ffnn_classifier/run_classifier.py
```

Controls:
- `+/-` - Adjust confidence threshold
- `p` - Toggle pose detection
- `q` - Quit

## Training Tips

1. **Balance your data:** Aim for ~equal positive and negative samples
2. **Include confusing gestures:** Loser, rock, thumbs up are essential negatives
3. **Augment data:** Training includes noise augmentation
4. **Watch for overfitting:** Monitor validation loss

## Files

- `train.py` - Training script
- `run_classifier.py` - Real-time inference
- `model.pt` - Saved PyTorch model (after training)
