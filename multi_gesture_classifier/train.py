#!/usr/bin/env python3
"""
Multi-Gesture FFNN Classifier Training

Trains a neural network to detect multiple gestures:
- Spider-Man (thumb + index + pinky extended)
- Dr. Strange (all fingers spread wide)

This is separate from the Spider-Man game code and can be used independently.
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
from datetime import datetime


class MultiGestureNet(nn.Module):
    """
    Feed Forward Neural Network for multi-gesture classification.
    
    Architecture:
        Input (82) → 128 → 64 → 32 → num_classes (softmax)
    
    Output is a probability distribution over gesture classes.
    """
    
    def __init__(self, input_size=82, num_classes=3):
        """
        Args:
            input_size: Number of input features (82 for hand landmarks)
            num_classes: Number of gesture classes (including "none")
        """
        super(MultiGestureNet, self).__init__()
        
        self.network = nn.Sequential(
            # First hidden layer
            nn.Linear(input_size, 128),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Dropout(0.3),
            
            # Second hidden layer
            nn.Linear(128, 64),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.Dropout(0.3),
            
            # Third hidden layer
            nn.Linear(64, 32),
            nn.BatchNorm1d(32),
            nn.ReLU(),
            nn.Dropout(0.2),
            
            # Output layer
            nn.Linear(32, num_classes),
        )
    
    def forward(self, x):
        return self.network(x)
    
    def predict_proba(self, x):
        """Get probability distribution over classes."""
        with torch.no_grad():
            logits = self.forward(x)
            return torch.softmax(logits, dim=1)


def extract_features(landmarks: list[dict]) -> np.ndarray:
    """
    Extract 82 features from 21 hand landmarks.
    Same feature extraction as the Spider-Man classifier.
    """
    # Raw coordinates (63 features)
    coords = []
    for lm in landmarks:
        coords.extend([lm['x'], lm['y'], lm['z']])
    
    # Derived features (19 features)
    derived = []
    
    # 1. Palm orientation
    wrist = landmarks[0]
    middle_mcp = landmarks[9]
    palm_orientation = wrist['y'] - middle_mcp['y']
    derived.append(palm_orientation)
    
    # 2-6. Finger extension ratios
    finger_tips = [4, 8, 12, 16, 20]
    finger_mcps = [2, 5, 9, 13, 17]
    
    for tip_idx, mcp_idx in zip(finger_tips, finger_mcps):
        tip = landmarks[tip_idx]
        mcp = landmarks[mcp_idx]
        extension = tip['y'] - mcp['y']
        derived.append(extension)
    
    # 7-11. Finger curl
    for tip_idx, mcp_idx in zip(finger_tips, finger_mcps):
        tip = landmarks[tip_idx]
        mcp = landmarks[mcp_idx]
        curl = np.sqrt(
            (tip['x'] - mcp['x'])**2 + 
            (tip['y'] - mcp['y'])**2 + 
            (tip['z'] - mcp['z'])**2
        )
        derived.append(curl)
    
    # 12. Hand openness
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
    
    # 13. Thumb-pinky distance
    thumb_tip = landmarks[4]
    pinky_tip = landmarks[20]
    thumb_pinky_dist = np.sqrt(
        (thumb_tip['x'] - pinky_tip['x'])**2 +
        (thumb_tip['y'] - pinky_tip['y'])**2 +
        (thumb_tip['z'] - pinky_tip['z'])**2
    )
    derived.append(thumb_pinky_dist)
    
    # 14. Index-pinky angle
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
    
    # 15. Wrist angle
    index_mcp = landmarks[5]
    pinky_mcp = landmarks[17]
    wrist_angle = np.arctan2(
        pinky_mcp['y'] - index_mcp['y'],
        pinky_mcp['x'] - index_mcp['x']
    )
    derived.append(wrist_angle)
    
    # 16. Z-depth variance
    z_values = [lm['z'] for lm in landmarks]
    z_variance = np.var(z_values)
    derived.append(z_variance)
    
    # 17-19. Palm normal vector
    v1 = np.array([
        index_mcp['x'] - wrist['x'],
        index_mcp['y'] - wrist['y'],
        index_mcp['z'] - wrist['z']
    ])
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
    
    all_features = coords + derived
    return np.array(all_features, dtype=np.float32)


# Gesture class mapping
GESTURE_CLASSES = {
    'none': 0,        # No recognized gesture
    'spiderman': 1,   # Spider-Man gesture
    'dr_strange': 2,  # Dr. Strange gesture
}

CLASS_NAMES = {v: k for k, v in GESTURE_CLASSES.items()}


def load_samples(samples_dir: Path) -> tuple[np.ndarray, np.ndarray]:
    """
    Load all sample files and extract features with multi-class labels.
    
    Labels:
        0 = none (negative samples)
        1 = spiderman
        2 = dr_strange
    """
    X_list = []
    y_list = []
    
    class_counts = {name: 0 for name in GESTURE_CLASSES.keys()}
    
    for json_file in samples_dir.glob("**/*.json"):
        with open(json_file, 'r') as f:
            data = json.load(f)
        
        gesture_name = data.get('gesture', 'unknown')
        is_positive = data.get('is_positive', False)
        samples = data.get('samples', [])
        
        # Determine class label
        if gesture_name == 'spiderman' and is_positive:
            label = GESTURE_CLASSES['spiderman']
        elif gesture_name == 'dr_strange':
            # Dr. Strange samples - mark as dr_strange class
            label = GESTURE_CLASSES['dr_strange']
        else:
            # All other gestures are "none" (negative class)
            label = GESTURE_CLASSES['none']
        
        for sample in samples:
            landmarks = sample.get('hand_landmarks', [])
            if landmarks is None:
                continue
            if len(landmarks) == 21:
                features = extract_features(landmarks)
                X_list.append(features)
                y_list.append(label)
                class_counts[CLASS_NAMES[label]] += 1
    
    print("\n📊 Sample counts per class:")
    for name, count in class_counts.items():
        print(f"   {name}: {count}")
    
    return np.array(X_list), np.array(y_list)


def train_model(
    samples_dir: Path,
    output_path: Path,
    epochs: int = 200,
    batch_size: int = 32,
    learning_rate: float = 0.001,
    test_size: float = 0.2,
):
    """Train the multi-gesture classifier."""
    print("🔮 Multi-Gesture FFNN Classifier Training")
    print("=" * 50)
    
    # Load data
    print("\n📂 Loading samples...")
    X, y = load_samples(samples_dir)
    
    if len(X) == 0:
        raise ValueError("No samples found!")
    
    print(f"\n📊 Total samples: {len(X)}")
    print(f"   Feature dimension: {X.shape[1]}")
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=42, stratify=y
    )
    
    print(f"\n📊 Train/Test split:")
    print(f"   Training: {len(X_train)}")
    print(f"   Testing: {len(X_test)}")
    
    # Convert to tensors
    X_train_tensor = torch.FloatTensor(X_train)
    y_train_tensor = torch.LongTensor(y_train)
    X_test_tensor = torch.FloatTensor(X_test)
    y_test_tensor = torch.LongTensor(y_test)
    
    # Create data loaders
    train_dataset = TensorDataset(X_train_tensor, y_train_tensor)
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    
    # Initialize model
    num_classes = len(GESTURE_CLASSES)
    model = MultiGestureNet(input_size=X.shape[1], num_classes=num_classes)
    
    # Loss and optimizer
    # Use class weights to handle imbalance
    class_counts = np.bincount(y_train, minlength=num_classes)
    class_weights = 1.0 / (class_counts + 1)
    class_weights = class_weights / class_weights.sum() * num_classes
    class_weights_tensor = torch.FloatTensor(class_weights)
    
    criterion = nn.CrossEntropyLoss(weight=class_weights_tensor)
    optimizer = optim.Adam(model.parameters(), lr=learning_rate, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=20, factor=0.5)
    
    # Training loop
    print("\n🏋️ Training...")
    best_accuracy = 0.0
    best_model_state = None
    
    for epoch in range(epochs):
        model.train()
        total_loss = 0.0
        
        for batch_X, batch_y in train_loader:
            optimizer.zero_grad()
            outputs = model(batch_X)
            loss = criterion(outputs, batch_y)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
        
        avg_loss = total_loss / len(train_loader)
        scheduler.step(avg_loss)
        
        # Evaluate
        model.eval()
        with torch.no_grad():
            outputs = model(X_test_tensor)
            _, predicted = torch.max(outputs, 1)
            accuracy = (predicted == y_test_tensor).float().mean().item()
        
        if accuracy > best_accuracy:
            best_accuracy = accuracy
            best_model_state = model.state_dict().copy()
        
        if (epoch + 1) % 20 == 0:
            print(f"   Epoch {epoch+1}/{epochs} - Loss: {avg_loss:.4f} - Accuracy: {accuracy:.2%}")
    
    # Load best model
    model.load_state_dict(best_model_state)
    
    # Final evaluation
    print("\n📊 Final Evaluation:")
    model.eval()
    with torch.no_grad():
        outputs = model(X_test_tensor)
        probs = torch.softmax(outputs, dim=1)
        _, predicted = torch.max(outputs, 1)
        
        # Per-class metrics
        for class_idx, class_name in CLASS_NAMES.items():
            mask = y_test_tensor == class_idx
            if mask.sum() > 0:
                class_correct = (predicted[mask] == y_test_tensor[mask]).float().mean().item()
                print(f"   {class_name}: {class_correct:.2%} accuracy")
        
        overall_accuracy = (predicted == y_test_tensor).float().mean().item()
        print(f"\n   Overall: {overall_accuracy:.2%} accuracy")
    
    # Save model
    output_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save({
        'model_state_dict': model.state_dict(),
        'input_size': X.shape[1],
        'num_classes': num_classes,
        'class_names': CLASS_NAMES,
        'gesture_classes': GESTURE_CLASSES,
        'accuracy': best_accuracy,
        'trained_at': datetime.now().isoformat(),
    }, output_path)
    
    print(f"\n✅ Model saved to: {output_path}")
    print(f"   Best accuracy: {best_accuracy:.2%}")
    
    return model, best_accuracy


if __name__ == "__main__":
    # Paths
    samples_dir = Path(__file__).parent.parent / "ffnn_training_samples"
    output_path = Path(__file__).parent / "multi_gesture_model.pt"
    
    # Train
    train_model(
        samples_dir=samples_dir,
        output_path=output_path,
        epochs=200,
        batch_size=32,
        learning_rate=0.001,
    )
