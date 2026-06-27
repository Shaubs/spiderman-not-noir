"""
Random Forest Classifier Training Script (Legacy)

Trains a Random Forest model on collected gesture samples.
Note: This classifier has been superseded by the FFNN classifier
which has better accuracy for distinguishing similar gestures.
"""

import json
import os
import sys
import glob
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report, confusion_matrix
import pickle
from pathlib import Path

# Paths - relative to project root
PROJECT_ROOT = Path(__file__).parent.parent.parent
SAMPLES_DIR = PROJECT_ROOT / "data_creation_lab" / "samples"
MODEL_OUTPUT = Path(__file__).parent / "model.pkl"


def load_samples_from_file(filepath: str) -> list:
    """Load samples from a JSON file."""
    with open(filepath, 'r') as f:
        data = json.load(f)
    return data.get("samples", [])


def extract_features(sample: dict) -> list:
    """
    Extract features from a single sample.
    
    Features include:
    - Raw hand landmark coordinates (21 × 3 = 63)
    - Relative distances (fingertips from wrist)
    - Finger curl measurements (tip to pip distance)
    """
    hand_landmarks = sample.get("hand_landmarks")
    
    if not hand_landmarks or len(hand_landmarks) < 21:
        return None
    
    features = []
    
    # Raw coordinates (21 landmarks × 3 coordinates = 63 features)
    for lm in hand_landmarks:
        features.extend([lm["x"], lm["y"], lm["z"]])
    
    # Relative features: fingertip distances from wrist
    wrist = hand_landmarks[0]
    fingertips = [4, 8, 12, 16, 20]
    for tip_idx in fingertips:
        tip = hand_landmarks[tip_idx]
        dist_x = tip["x"] - wrist["x"]
        dist_y = tip["y"] - wrist["y"]
        features.extend([dist_x, dist_y])
    
    # Knuckle distances from wrist (palm orientation)
    knuckles = [5, 9, 13, 17]
    for knuckle_idx in knuckles:
        knuckle = hand_landmarks[knuckle_idx]
        dist_y = knuckle["y"] - wrist["y"]
        features.append(dist_y)
    
    # Finger curl features (tip to pip y-distance)
    finger_pairs = [(8, 6), (12, 10), (16, 14), (20, 18)]  # tip, pip
    for tip_idx, pip_idx in finger_pairs:
        tip = hand_landmarks[tip_idx]
        pip = hand_landmarks[pip_idx]
        curl = tip["y"] - pip["y"]
        features.append(curl)
    
    # Palm inversion feature
    avg_knuckle_y = sum(hand_landmarks[k]["y"] for k in knuckles) / len(knuckles)
    palm_inverted = wrist["y"] - avg_knuckle_y
    features.append(palm_inverted)
    
    return features


def load_all_samples():
    """Load all samples from the samples directory."""
    X, y = [], []
    
    # Find all sample files
    all_files = list(SAMPLES_DIR.glob("*.json"))
    
    positive_files = [f for f in all_files if "spiderman" in f.name.lower()]
    negative_files = [f for f in all_files if "negative" in f.name.lower()]
    
    print(f"Found {len(positive_files)} positive sample files")
    print(f"Found {len(negative_files)} negative sample files")
    
    # Load positive samples
    positive_count = 0
    for filepath in positive_files:
        samples = load_samples_from_file(filepath)
        for sample in samples:
            features = extract_features(sample)
            if features:
                X.append(features)
                y.append(1)  # Positive class
                positive_count += 1
    
    print(f"Loaded {positive_count} positive samples")
    
    # Load negative samples
    negative_count = 0
    for filepath in negative_files:
        samples = load_samples_from_file(filepath)
        for sample in samples:
            features = extract_features(sample)
            if features:
                X.append(features)
                y.append(0)  # Negative class
                negative_count += 1
    
    print(f"Loaded {negative_count} negative samples")
    
    # If no negative samples, create synthetic negatives by perturbing positives
    if negative_count == 0 and positive_count > 0:
        print("\n⚠️  No negative samples found!")
        print("   Creating synthetic negatives by shuffling positive features...")
        
        # Create synthetic negatives by shuffling coordinates
        np.random.seed(42)
        num_synthetic = min(positive_count, 500)
        
        for i in range(num_synthetic):
            # Take a random positive sample and shuffle its features
            base_features = list(X[i % positive_count])
            # Shuffle the raw coordinates portion (first 63 features)
            shuffled = base_features[:63]
            np.random.shuffle(shuffled)
            synthetic = shuffled + base_features[63:]  # Keep derived features
            X.append(synthetic)
            y.append(0)
        
        print(f"   Created {num_synthetic} synthetic negative samples")
    
    return np.array(X), np.array(y)


def train_model(X, y):
    """Train a Random Forest classifier."""
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    print(f"\nTraining set: {len(X_train)} samples")
    print(f"Test set: {len(X_test)} samples")
    
    # Create and train model
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=15,
        min_samples_split=5,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1  # Use all CPU cores
    )
    
    # Cross-validation
    print("\nPerforming 5-fold cross-validation...")
    cv_scores = cross_val_score(model, X_train, y_train, cv=5)
    print(f"CV scores: {cv_scores}")
    print(f"Mean CV accuracy: {cv_scores.mean():.2%} (+/- {cv_scores.std() * 2:.2%})")
    
    # Fit on full training set
    print("\nTraining final model...")
    model.fit(X_train, y_train)
    
    # Evaluate on test set
    y_pred = model.predict(X_test)
    
    print(f"\n{'='*50}")
    print("TEST SET RESULTS")
    print(f"{'='*50}")
    print(f"Accuracy: {model.score(X_test, y_test):.2%}")
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=["Negative", "Positive"]))
    
    print("Confusion Matrix:")
    print(confusion_matrix(y_test, y_pred))
    
    # Feature importance (top 10)
    print(f"\n{'='*50}")
    print("TOP 10 IMPORTANT FEATURES")
    print(f"{'='*50}")
    importances = model.feature_importances_
    indices = np.argsort(importances)[::-1][:10]
    
    feature_names = []
    # Raw coordinates
    for i in range(21):
        for coord in ['x', 'y', 'z']:
            feature_names.append(f"lm{i}_{coord}")
    # Fingertip distances
    for finger in ['thumb', 'index', 'middle', 'ring', 'pinky']:
        feature_names.extend([f"{finger}_dist_x", f"{finger}_dist_y"])
    # Knuckle distances
    for finger in ['index', 'middle', 'ring', 'pinky']:
        feature_names.append(f"{finger}_knuckle_y")
    # Curl features
    for finger in ['index', 'middle', 'ring', 'pinky']:
        feature_names.append(f"{finger}_curl")
    # Palm inversion
    feature_names.append("palm_inverted")
    
    for rank, idx in enumerate(indices, 1):
        name = feature_names[idx] if idx < len(feature_names) else f"feature_{idx}"
        print(f"  {rank}. {name}: {importances[idx]:.4f}")
    
    return model


def save_model(model, filepath: Path):
    """Save trained model to file."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, 'wb') as f:
        pickle.dump(model, f)
    print(f"\n✅ Model saved to: {filepath}")


def main():
    print("="*60)
    print("🌲 RANDOM FOREST CLASSIFIER TRAINING")
    print("="*60)
    
    # Load data
    print("\nLoading samples...")
    X, y = load_all_samples()
    
    if len(X) == 0:
        print("\n❌ No samples found!")
        print(f"   Please add samples to: {SAMPLES_DIR}")
        return
    
    print(f"\nTotal samples: {len(X)}")
    print(f"  Positive: {sum(y)}")
    print(f"  Negative: {len(y) - sum(y)}")
    print(f"  Features per sample: {len(X[0])}")
    
    # Train model
    model = train_model(X, y)
    
    # Save model
    save_model(model, MODEL_OUTPUT)
    
    print("\n" + "="*60)
    print("✅ TRAINING COMPLETE")
    print("="*60)
    print(f"\nTo use the model, run:")
    print(f"  python classifiers/random_forest/run_classifier.py")


if __name__ == "__main__":
    main()
