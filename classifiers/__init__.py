"""
Classifiers Module

Contains all gesture classification models:
- ffnn: Feed Forward Neural Network (primary, used in game)
- random_forest: Random Forest (legacy, kept for comparison)
"""

from .ffnn.run_classifier import FFNNClassifier
from .ffnn.train import GestureNet, extract_features

__all__ = [
    'FFNNClassifier',
    'GestureNet',
    'extract_features',
]
