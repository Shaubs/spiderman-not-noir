"""
Tracking Module

Hand and pose tracking using MediaPipe.
- HandTracker: Dual-model hand + pose detection
- HolisticTracker: Single-model optimized detection
- GestureDetector: Spider-Man gesture detection
- GestureStateMachine: Temporal gesture state tracking
"""

from .hand_tracker import HandTracker, PoseLandmarks
from .holistic_tracker import HolisticTracker, HolisticResults
from .gesture_detector import GestureDetector, GestureEvent, Gesture
from .gesture_state_machine import GestureStateMachine, GestureState, StateConfig

__all__ = [
    'HandTracker',
    'HolisticTracker',
    'HolisticResults',
    'PoseLandmarks',
    'GestureDetector',
    'GestureEvent',
    'Gesture',
    'GestureStateMachine',
    'GestureState',
    'StateConfig',
]
