from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Callable


@dataclass
class GestureEvent:
    """Represents a detected gesture event."""
    name: str
    confidence: float
    hand_index: int


class Gesture(ABC):
    """Abstract base class for gesture definitions."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        pass
    
    @abstractmethod
    def detect(self, hand_landmarks) -> Optional[float]:
        """
        Check if gesture is detected.
        Returns confidence score (0-1) if detected, None otherwise.
        """
        pass


class GestureDetector:
    """Manages gesture detection and triggers callbacks."""
    
    def __init__(self):
        self.gestures: List[Gesture] = []
        self.callbacks: List[Callable[[GestureEvent], None]] = []
        self.gesture_counts: dict = {}
        self._last_detected: dict = {}  # Track last detection to avoid counting every frame
    
    def register_gesture(self, gesture: Gesture):
        """Register a gesture to detect."""
        self.gestures.append(gesture)
        self.gesture_counts[gesture.name] = 0
        self._last_detected[gesture.name] = False
    
    def on_gesture(self, callback: Callable[[GestureEvent], None]):
        """Register a callback for when a gesture is detected."""
        self.callbacks.append(callback)
    
    def process(self, results) -> List[GestureEvent]:
        """Process hand landmarks and detect gestures."""
        detected_events = []
        current_detections = {g.name: False for g in self.gestures}
        
        if not results.hand_landmarks:
            # Reset last detected when no hands
            for gesture_name in self._last_detected:
                self._last_detected[gesture_name] = False
            return detected_events
        
        for hand_idx, hand_landmarks in enumerate(results.hand_landmarks):
            for gesture in self.gestures:
                confidence = gesture.detect(hand_landmarks)
                
                if confidence is not None:
                    current_detections[gesture.name] = True
                    
                    # Only count if this is a new detection (wasn't detected last frame)
                    if not self._last_detected[gesture.name]:
                        event = GestureEvent(
                            name=gesture.name,
                            confidence=confidence,
                            hand_index=hand_idx
                        )
                        detected_events.append(event)
                        self.gesture_counts[gesture.name] += 1
                        
                        # Trigger callbacks
                        for callback in self.callbacks:
                            callback(event)
        
        # Update last detected state
        for gesture_name, detected in current_detections.items():
            self._last_detected[gesture_name] = detected
        
        return detected_events
    
    def get_count(self, gesture_name: str) -> int:
        """Get the count of times a gesture was detected."""
        return self.gesture_counts.get(gesture_name, 0)
