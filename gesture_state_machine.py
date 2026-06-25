"""
Gesture State Machine for detecting gesture sequences across video frames.

Implements temporal gesture detection by tracking state transitions:
- State 0: Looking for gesture
- State 1: Gesture detected, recording position
- State 2: Upward motion detected (armed)
- State 3: Downward motion detected (triggered!)
"""

from enum import Enum, auto
from dataclasses import dataclass
from typing import Optional, Callable, List
import time


class GestureState(Enum):
    """States for gesture sequence detection."""
    LOOKING = auto()      # Waiting for gesture
    DETECTED = auto()     # Gesture found, recording position
    ARMED = auto()        # Upward motion detected
    TRIGGERED = auto()    # Gesture sequence complete!


@dataclass
class StateConfig:
    """Configuration for state machine thresholds."""
    upward_threshold: float = 0.08      # Normalized Y movement up (decrease in Y)
    downward_threshold: float = 0.05    # Normalized Y movement down (increase in Y)
    timeout_seconds: float = 1.0        # Seconds before state resets
    cooldown_seconds: float = 0.5       # Seconds after trigger before accepting new gesture


class GestureStateMachine:
    """
    Tracks gesture sequences across video frames.
    
    Detects the pattern:
    1. Spider-Man hand appears (static pose)
    2. Hand moves UP
    3. Hand moves DOWN → TRIGGER!
    """
    
    def __init__(self, config: Optional[StateConfig] = None):
        self.config = config or StateConfig()
        self.state = GestureState.LOOKING
        self.initial_wrist_y: Optional[float] = None
        self.armed_wrist_y: Optional[float] = None
        self.state_enter_time: float = time.time()
        self.last_trigger_time: float = 0
        self.callbacks: List[Callable[[], None]] = []
        
        # For debugging/visualization
        self.state_history: List[tuple] = []
    
    def on_trigger(self, callback: Callable[[], None]):
        """Register a callback for when gesture is triggered."""
        self.callbacks.append(callback)
    
    def _change_state(self, new_state: GestureState):
        """Transition to a new state."""
        old_state = self.state
        self.state = new_state
        self.state_enter_time = time.time()
        self.state_history.append((time.time(), old_state, new_state))
        
        # Keep history bounded
        if len(self.state_history) > 100:
            self.state_history = self.state_history[-50:]
    
    def _check_timeout(self) -> bool:
        """Check if current state has timed out."""
        if self.state == GestureState.LOOKING:
            return False  # LOOKING state never times out
        
        elapsed = time.time() - self.state_enter_time
        return elapsed > self.config.timeout_seconds
    
    def _in_cooldown(self) -> bool:
        """Check if we're in cooldown period after trigger."""
        return time.time() - self.last_trigger_time < self.config.cooldown_seconds
    
    def update(self, gesture_detected: bool, wrist_y: Optional[float] = None) -> GestureState:
        """
        Update state machine with current frame data.
        
        Args:
            gesture_detected: Whether the static gesture (Spider-Man hand) is detected
            wrist_y: Normalized Y coordinate of wrist (0-1, top to bottom)
        
        Returns:
            Current state after update
        """
        # Check timeout - reset to LOOKING if timed out
        if self._check_timeout():
            self._change_state(GestureState.LOOKING)
            self.initial_wrist_y = None
            self.armed_wrist_y = None
        
        # Handle cooldown period
        if self._in_cooldown():
            return self.state
        
        # State machine logic
        if self.state == GestureState.LOOKING:
            if gesture_detected and wrist_y is not None:
                self._change_state(GestureState.DETECTED)
                self.initial_wrist_y = wrist_y
        
        elif self.state == GestureState.DETECTED:
            if not gesture_detected:
                # Lost gesture, reset
                self._change_state(GestureState.LOOKING)
                self.initial_wrist_y = None
            elif wrist_y is not None and self.initial_wrist_y is not None:
                # Check for upward movement (Y decreases when moving up)
                y_delta = self.initial_wrist_y - wrist_y
                if y_delta > self.config.upward_threshold:
                    self._change_state(GestureState.ARMED)
                    self.armed_wrist_y = wrist_y
        
        elif self.state == GestureState.ARMED:
            if not gesture_detected:
                # Lost gesture, reset
                self._change_state(GestureState.LOOKING)
                self.initial_wrist_y = None
                self.armed_wrist_y = None
            elif wrist_y is not None and self.armed_wrist_y is not None:
                # Check for downward movement (Y increases when moving down)
                y_delta = wrist_y - self.armed_wrist_y
                if y_delta > self.config.downward_threshold:
                    self._change_state(GestureState.TRIGGERED)
                    self._fire_trigger()
        
        elif self.state == GestureState.TRIGGERED:
            # Immediately reset after trigger
            self._change_state(GestureState.LOOKING)
            self.initial_wrist_y = None
            self.armed_wrist_y = None
        
        return self.state
    
    def _fire_trigger(self):
        """Execute trigger callbacks."""
        self.last_trigger_time = time.time()
        for callback in self.callbacks:
            callback()
    
    def reset(self):
        """Reset state machine to initial state."""
        self.state = GestureState.LOOKING
        self.initial_wrist_y = None
        self.armed_wrist_y = None
        self.state_enter_time = time.time()
    
    def get_state_info(self) -> dict:
        """Get current state information for debugging/display."""
        return {
            "state": self.state.name,
            "initial_wrist_y": self.initial_wrist_y,
            "armed_wrist_y": self.armed_wrist_y,
            "time_in_state": time.time() - self.state_enter_time,
            "in_cooldown": self._in_cooldown()
        }
    
    def get_state_color(self) -> tuple:
        """Get BGR color for current state visualization."""
        colors = {
            GestureState.LOOKING: (128, 128, 128),    # Gray
            GestureState.DETECTED: (0, 255, 255),     # Yellow
            GestureState.ARMED: (0, 165, 255),        # Orange
            GestureState.TRIGGERED: (0, 255, 0),      # Green
        }
        return colors.get(self.state, (255, 255, 255))
