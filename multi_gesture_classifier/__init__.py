"""
Multi-Gesture Classifier Module

Detects multiple hand gestures including Spider-Man and Dr. Strange.
This is independent from the Spider-Man game code.

Usage:
    from multi_gesture_classifier import MultiGestureClassifier
    
    classifier = MultiGestureClassifier()
    result = classifier.predict(hand_landmarks)
    
    print(f"Gesture: {result.gesture}")
    print(f"Confidence: {result.confidence:.0%}")
"""

from .run_classifier import MultiGestureClassifier, GestureResult

__all__ = ['MultiGestureClassifier', 'GestureResult']
