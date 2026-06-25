#!/usr/bin/env python3
"""
Feed Forward Neural Network Training for Spider-Man Gesture Detection.

This replaces the Random Forest approach which had high false positive rates
for similar gestures (loser sign: 70%, thumbs up: 30%, rock sign).
"""

import json
import os
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
from sklearn.model_selection import train_test_split
from pathlib import Path


class GestureNet(nn.Module):
    """
    Feed Forward Neural Network for gesture classification.
    
    Architecture:
        Input (82) → 64 → 32 → 16 → 1 (sigmoid)
    """
    
    def __init__(self, input_size=82):
        super(GestureNet, self).__init__()
        
        self.network = nn.Sequential(
            # First hidden layer
            nn.Linear(input_size, 64),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.Dropout(0.3),
            
            # Second hidden layer
            nn.Linear(64, 32),
            nn.BatchNorm1d(32),
            nn.ReLU(),
            nn.Dropout(0.3),
            
            # Third hidden layer
            nn.Linear(32, 16),
            nn.ReLU(),
            
            # Output layer
            nn.Linear(16, 1),
            nn.Sigmoid()
        )
    
    def forward(self, x):
        return self.network(x)


def extract_features(landmarks: list[dict]) -> np.ndarray:
    """
    Extract 82 features from 21 hand landmarks.
    
    Features:
        - 63 raw coordinates (21 × 3)
        - 19 derived features for palm orientation, finger positions, etc.
    """
    # Raw coordinates (63 features)
    coords = []
    for lm in landmarks:
        coords.extend([lm['x'], lm['y'], lm['z']])
    
    # Derived features (19 features)
    derived = []
    
    # 1. Palm orientation: wrist y - middle finger MCP y (inverted palm = positive)
    wrist = landmarks[0]
    middle_mcp = landmarks[9]
    palm_orientation = wrist['y'] - middle_mcp['y']
    derived.append(palm_orientation)
    
    # 2-6. Finger extension ratios (tip y relative to MCP y)
    finger_tips = [4, 8, 12, 16, 20]  # thumb, index, middle, ring, pinky
    finger_mcps = [2, 5, 9, 13, 17]   # corresponding MCPs
    
    for tip_idx, mcp_idx in zip(finger_tips, finger_mcps):
        tip = landmarks[tip_idx]
        mcp = landmarks[mcp_idx]
        # Negative = extended (tip above MCP in inverted palm)
        extension = tip['y'] - mcp['y']
        derived.append(extension)
    
    # 7-11. Finger curl (distance from tip to MCP, normalized)
    for tip_idx, mcp_idx in zip(finger_tips, finger_mcps):
        tip = landmarks[tip_idx]
        mcp = landmarks[mcp_idx]
        curl = np.sqrt(
            (tip['x'] - mcp['x'])**2 + 
            (tip['y'] - mcp['y'])**2 + 
            (tip['z'] - mcp['z'])**2
        )
        derived.append(curl)
    
    # 12. Hand openness (average distance of fingertips from palm center)
    palm_center_x = np.mean([landmarks[i]['x'] for i in [0, 5, 9, 13, 17]])
    palm_center_y = np.mean([landmarks[i]['y'] for i in [0, 5, 9, 13, 17]])
    palm_center_z = np.mean([landmarks[i]['z'] for i in [0, 5, 9, 13, 17]])
    
    fingertip_distances = []
    for tip_idx in finger_tips:
        tip = landmarks[tip_idx]
        dist = np.sqrt(
            (tip['x'] - palm_center_x)**2 +
            (tip['y'] - palm_center_y)**2 +
            (tip['z'] - palm_center_z)**2
        )
        fingertip_distances.append(dist)
    hand_openness = np.mean(fingertip_distances)
    derived.append(hand_openness)
    
    # 13. Thumb-pinky distance (for spread detection)
    thumb_tip = landmarks[4]
    pinky_tip = landmarks[20]
    thumb_pinky_dist = np.sqrt(
        (thumb_tip['x'] - pinky_tip['x'])**2 +
        (thumb_tip['y'] - pinky_tip['y'])**2 +
        (thumb_tip['z'] - pinky_tip['z'])**2
    )
    derived.append(thumb_pinky_dist)
    
    # 14. Index-pinky angle (spread of extended fingers)
    index_tip = landmarks[8]
    index_vec = np.array([index_tip['x'] - wrist['x'], index_tip['y'] - wrist['y']])
    pinky_vec = np.array([pinky_tip['x'] - wrist['x'], pinky_tip['y'] - wrist['y']])
    
    index_norm = np.linalg.norm(index_vec)
    pinky_norm = np.linalg.norm(pinky_vec)
    
    if index_norm > 0 and pinky_norm > 0:
        cos_angle = np.dot(index_vec, pinky_vec) / (index_norm * pinky_norm)
        cos_angle = np.clip(cos_angle, -1, 1)
        index_pinky_angle = np.arccos(cos_angle)
    else:
        index_pinky_angle = 0
    derived.append(index_pinky_angle)
    
    # 15. Wrist angle (rotation in x-y plane)
    index_mcp = landmarks[5]
    pinky_mcp = landmarks[17]
    wrist_angle = np.arctan2(
        pinky_mcp['y'] - index_mcp['y'],
        pinky_mcp['x'] - index_mcp['x']
    )
    derived.append(wrist_angle)
    
    # 16. Z-depth variance (how flat is the hand)
    z_values = [lm['z'] for lm in landmarks]
    z_variance = np.var(z_values)
    derived.append(z_variance)
    
    # 17-19. Palm normal vector (cross product of palm vectors)
    # Vector from wrist to index MCP
    v1 = np.array([
        index_mcp['x'] - wrist['x'],
        index_mcp['y'] - wrist['y'],
        index_mcp['z'] - wrist['z']
    ])
    # Vector from wrist to pinky MCP
    v2 = np.array([
        pinky_mcp['x'] - wrist['x'],
        pinky_mcp['y'] - wrist['y'],
        pinky_mcp['z'] - wrist['z']
    ])
    palm_normal = np.cross(v1, v2)
    palm_normal_norm = np.linalg.norm(palm_normal)
    if palm_normal_norm > 0:
        palm_normal = palm_normal / palm_normal_norm
    derived.extend(palm_normal.tolist())
    
    # Combine all features
    all_features = coords + derived
    return np.array(all_features, dtype=np.float32)


def load_samples(samples_dir: Path) -> tuple[np.ndarray, np.ndarray]:
    """
    Load all sample files from nested folder structure and extract features.
    
    Folder structure: samples_dir/{gesture_name}/{gesture}_{hand}_{timestamp}.json
    Uses 'is_positive' field from JSON metadata for labeling.
    """
    X_list = []
    y_list = []
    
    positive_count = 0
    negative_count = 0
    gesture_counts = {}
    
    # Recursively find all JSON files in subdirectories
    for json_file in samples_dir.glob("**/*.json"):
        with open(json_file, 'r') as f:
            data = json.load(f)
        
        samples = data.get('samples', [])
        
        # Use is_positive field from metadata, fallback to folder name
        if 'is_positive' in data:
            is_positive = data['is_positive']
        else:
            # Fallback: check if 'spiderman' in folder name or filename
            is_positive = 'spiderman' in json_file.parent.name.lower()
        
        label = 1 if is_positive else 0
        gesture_name = data.get('gesture', json_file.parent.name)
        
        for sample in samples:
            # Support both 'landmarks' and 'hand_landmarks' keys
            landmarks = sample.get('hand_landmarks') or sample.get('landmarks', [])
            if len(landmarks) == 21:
                features = extract_features(landmarks)
                X_list.append(features)
                y_list.append(label)
                
                if is_positive:
                    positive_count += 1
                else:
                    negative_count += 1
                
                # Track per-gesture counts
                gesture_counts[gesture_name] = gesture_counts.get(gesture_name, 0) + 1
    
    print(f"\nLoaded samples by gesture:")
    for gesture, count in sorted(gesture_counts.items()):
        label_str = "✓ POSITIVE" if gesture == "spiderman" else "✗ negative"
        print(f"  {gesture}: {count} samples ({label_str})")
    
    print(f"\nTotal: {positive_count} positive (spiderman), {negative_count} negative (other gestures)")
    
    if negative_count == 0:
        print("\n⚠️  WARNING: No negative samples found!")
        print("Please collect samples of other gestures:")
        print("  - loser_samples_*.json (index+pinky, palm facing camera)")
        print("  - rock_samples_*.json")
        print("  - thumbsup_samples_*.json")
        print("  - random_samples_*.json")
        print("\nRun: python data_creation_lab/collect_samples.py")
        print("Then rename the output file appropriately.\n")
    
    return np.array(X_list), np.array(y_list)


def augment_data(X: np.ndarray, y: np.ndarray, noise_factor: float = 0.02) -> tuple[np.ndarray, np.ndarray]:
    """
    Augment training data with noise.
    """
    augmented_X = []
    augmented_y = []
    
    for features, label in zip(X, y):
        # Original sample
        augmented_X.append(features)
        augmented_y.append(label)
        
        # Add 2 noisy versions
        for _ in range(2):
            noise = np.random.normal(0, noise_factor, features.shape)
            noisy_features = features + noise
            augmented_X.append(noisy_features.astype(np.float32))
            augmented_y.append(label)
    
    return np.array(augmented_X), np.array(augmented_y)


def train_model(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_val: np.ndarray,
    y_val: np.ndarray,
    epochs: int = 100,
    batch_size: int = 32,
    learning_rate: float = 0.001
) -> GestureNet:
    """
    Train the neural network.
    """
    # Convert to tensors
    X_train_tensor = torch.FloatTensor(X_train)
    y_train_tensor = torch.FloatTensor(y_train).unsqueeze(1)
    X_val_tensor = torch.FloatTensor(X_val)
    y_val_tensor = torch.FloatTensor(y_val).unsqueeze(1)
    
    # Create data loaders
    train_dataset = TensorDataset(X_train_tensor, y_train_tensor)
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    
    # Initialize model
    model = GestureNet(input_size=X_train.shape[1])
    criterion = nn.BCELoss()
    optimizer = optim.Adam(model.parameters(), lr=learning_rate, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=10, factor=0.5)
    
    best_val_loss = float('inf')
    best_model_state = None
    patience_counter = 0
    max_patience = 20
    
    print("\nTraining...")
    print("-" * 60)
    
    for epoch in range(epochs):
        # Training phase
        model.train()
        train_loss = 0.0
        
        for batch_X, batch_y in train_loader:
            optimizer.zero_grad()
            outputs = model(batch_X)
            loss = criterion(outputs, batch_y)
            loss.backward()
            optimizer.step()
            train_loss += loss.item()
        
        train_loss /= len(train_loader)
        
        # Validation phase
        model.eval()
        with torch.no_grad():
            val_outputs = model(X_val_tensor)
            val_loss = criterion(val_outputs, y_val_tensor).item()
            
            # Calculate accuracy
            val_preds = (val_outputs > 0.5).float()
            val_acc = (val_preds == y_val_tensor).float().mean().item()
        
        scheduler.step(val_loss)
        
        # Early stopping check
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_model_state = model.state_dict().copy()
            patience_counter = 0
        else:
            patience_counter += 1
        
        if (epoch + 1) % 10 == 0 or epoch == 0:
            print(f"Epoch {epoch+1:3d}/{epochs} | "
                  f"Train Loss: {train_loss:.4f} | "
                  f"Val Loss: {val_loss:.4f} | "
                  f"Val Acc: {val_acc:.2%}")
        
        if patience_counter >= max_patience:
            print(f"\nEarly stopping at epoch {epoch+1}")
            break
    
    # Load best model
    if best_model_state is not None:
        model.load_state_dict(best_model_state)
    
    return model


def evaluate_model(model: GestureNet, X_test: np.ndarray, y_test: np.ndarray):
    """
    Evaluate the trained model.
    """
    model.eval()
    X_test_tensor = torch.FloatTensor(X_test)
    
    with torch.no_grad():
        outputs = model(X_test_tensor)
        predictions = (outputs > 0.5).numpy().flatten()
    
    # Calculate metrics
    accuracy = np.mean(predictions == y_test)
    
    # Confusion matrix components
    tp = np.sum((predictions == 1) & (y_test == 1))
    tn = np.sum((predictions == 0) & (y_test == 0))
    fp = np.sum((predictions == 1) & (y_test == 0))
    fn = np.sum((predictions == 0) & (y_test == 1))
    
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    
    print("\n" + "=" * 60)
    print("TEST RESULTS")
    print("=" * 60)
    print(f"Accuracy:  {accuracy:.2%}")
    print(f"Precision: {precision:.2%}")
    print(f"Recall:    {recall:.2%}")
    print(f"F1 Score:  {f1:.2%}")
    print("-" * 60)
    print(f"True Positives:  {tp}")
    print(f"True Negatives:  {tn}")
    print(f"False Positives: {fp}")
    print(f"False Negatives: {fn}")
    print("=" * 60)


def main():
    # Paths
    script_dir = Path(__file__).parent
    samples_dir = script_dir.parent / "ffnn_training_samples"
    model_path = script_dir / "model.pt"
    
    print("=" * 60)
    print("Feed Forward Neural Network Training")
    print("=" * 60)
    
    # Load data
    X, y = load_samples(samples_dir)
    
    if len(X) == 0:
        print("No samples found! Please collect some training data first.")
        return
    
    # Check class balance
    n_positive = np.sum(y == 1)
    n_negative = np.sum(y == 0)
    print(f"\nClass balance: {n_positive} positive, {n_negative} negative")
    
    if n_negative == 0:
        print("\n❌ Cannot train without negative samples!")
        print("The Random Forest failed because of synthetic negatives.")
        print("Please collect REAL negative samples before training.\n")
        return
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    X_train, X_val, y_train, y_val = train_test_split(
        X_train, y_train, test_size=0.2, random_state=42, stratify=y_train
    )
    
    print(f"Train: {len(X_train)}, Val: {len(X_val)}, Test: {len(X_test)}")
    
    # Augment training data
    X_train_aug, y_train_aug = augment_data(X_train, y_train)
    print(f"After augmentation: {len(X_train_aug)} training samples")
    
    # Train
    model = train_model(X_train_aug, y_train_aug, X_val, y_val)
    
    # Evaluate
    evaluate_model(model, X_test, y_test)
    
    # Save model
    torch.save({
        'model_state_dict': model.state_dict(),
        'input_size': X.shape[1],
    }, model_path)
    
    print(f"\n✅ Model saved to: {model_path}")


if __name__ == "__main__":
    main()
