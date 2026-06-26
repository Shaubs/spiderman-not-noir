"""
Gesture State Machine for detecting gesture sequences across video frames.

Implements temporal gesture detection with simplified trigger mechanics (ADR-009):

Trigger Conditions (ANY of these will fire):
1. Rapid Toggle: Detection toggles DETECTED↔LOOKING N times within window
2. Armed State: Hand moves UP while gesture is held → immediate trigger
3. Sustained Hold: DETECTED state maintained for X seconds

States:
- LOOKING: No Spider-Man hand detected
- DETECTED: Spider-Man hand detected, monitoring for triggers
- TRIGGERED: Web fired (auto-resets after cooldown)

All timing values are configurable via config.py
"""

from enum import Enum, auto
from dataclasses import dataclass
from typing import Optional, Callable, List
import time


class GestureState(Enum):
    """States for gesture sequence detection."""
    LOOKING = auto()      # Waiting for gesture
    DETECTED = auto()     # Gesture found, monitoring triggers
    TRIGGERED = auto()    # Gesture sequence complete!


@dataclass
class StateConfig:
    """Configuration for state machine thresholds. 
    
    Note: These are defaults. The actual values come from config.py via GameConfig.
    """
    # Rapid toggle trigger
    toggle_count_threshold: int = 2          # Number of toggles to trigger
    toggle_window_seconds: float = 0.5       # Time window for counting toggles
    
    # Armed trigger (upward motion)
    upward_threshold: float = 0.04           # Normalized Y movement up
    
    # Sustained hold trigger
    sustained_hold_seconds: float = 0.4      # Seconds to hold for trigger
    
    # Cooldown
    cooldown_seconds: float = 0.3            # Seconds after trigger before accepting new gesture


class GestureStateMachine:
    """
    Tracks gesture sequences with simplified trigger mechanics.
    
    Three ways to trigger (any one fires the web):
    1. Quick flicking motion (rapid toggle between detected/looking)
    2. Move hand UP while holding gesture (armed motion)
    3. Hold steady for 1+ second (sustained detection)
    """
    
    def __init__(self, config: Optional[StateConfig] = None):
        self.config = config or StateConfig()
        self.state = GestureState.LOOKING
        self.state_enter_time: float = time.time()
        self.last_trigger_time: float = 0
        self.callbacks: List[Callable[[], None]] = []
        
        # For rapid toggle detection
        self.toggle_timestamps: List[float] = []
        
        # For armed (upward motion) detection
        self.initial_wrist_y: Optional[float] = None
        
        # For debugging/visualization
        self.state_history: List[tuple] = []
        self.last_trigger_reason: str = ""
        
        # Flag for game.py to know when trigger just fired
        self._just_triggered: bool = False
    
    def on_trigger(self, callback: Callable[[], None]):
        """Register a callback for when gesture is triggered."""
        self.callbacks.append(callback)
    
    def _change_state(self, new_state: GestureState):
        """Transition to a new state."""
        old_state = self.state
        self.state = new_state
        self.state_enter_time = time.time()
        self.state_history.append((time.time(), old_state, new_state))
        
        # Track state toggles for rapid toggle detection
        if (old_state == GestureState.DETECTED and new_state == GestureState.LOOKING) or \
           (old_state == GestureState.LOOKING and new_state == GestureState.DETECTED):
            self.toggle_timestamps.append(time.time())
            # Clean old timestamps
            cutoff = time.time() - self.config.toggle_window_seconds
            self.toggle_timestamps = [t for t in self.toggle_timestamps if t > cutoff]
        
        # Debug output
        print(f"DEBUG: State transition: {old_state.name} → {new_state.name}")
        
        # Keep history bounded
        if len(self.state_history) > 100:
            self.state_history = self.state_history[-50:]
    
    def _in_cooldown(self) -> bool:
        """Check if we're in cooldown period after trigger."""
        return time.time() - self.last_trigger_time < self.config.cooldown_seconds
    
    def _check_rapid_toggle_trigger(self) -> bool:
        """Check if rapid toggling should trigger."""
        cutoff = time.time() - self.config.toggle_window_seconds
        recent_toggles = [t for t in self.toggle_timestamps if t > cutoff]
        return len(recent_toggles) >= self.config.toggle_count_threshold
    
    def _check_sustained_hold_trigger(self) -> bool:
        """Check if sustained hold should trigger."""
        if self.state != GestureState.DETECTED:
            return False
        time_in_state = time.time() - self.state_enter_time
        return time_in_state >= self.config.sustained_hold_seconds
    
    def _check_armed_trigger(self, wrist_y: Optional[float]) -> bool:
        """Check if upward motion should trigger."""
        if wrist_y is None or self.initial_wrist_y is None:
            return False
        # Y decreases when moving up in image coordinates
        y_delta = self.initial_wrist_y - wrist_y
        return y_delta > self.config.upward_threshold
    
    def update(self, gesture_detected: bool, wrist_y: Optional[float] = None) -> GestureState:
        """
        Update state machine with current frame data.
        
        Args:
            gesture_detected: Whether the static gesture (Spider-Man hand) is detected
            wrist_y: Normalized Y coordinate of wrist (0-1, top to bottom)
        
        Returns:
            Current state after update
        """
        # Handle cooldown period
        if self._in_cooldown():
            if self.state == GestureState.TRIGGERED:
                self._change_state(GestureState.LOOKING)
                self.initial_wrist_y = None
                self.toggle_timestamps.clear()
            return self.state
        
        # Check for rapid toggle trigger (can fire from any state)
        if self._check_rapid_toggle_trigger():
            self.last_trigger_reason = "RAPID_TOGGLE"
            print(f"DEBUG: Trigger fired! Reason: {self.last_trigger_reason}")
            self._change_state(GestureState.TRIGGERED)
            self._fire_trigger()
            return self.state
        
        # State machine logic
        if self.state == GestureState.LOOKING:
            if gesture_detected and wrist_y is not None:
                self._change_state(GestureState.DETECTED)
                self.initial_wrist_y = wrist_y
        
        elif self.state == GestureState.DETECTED:
            if not gesture_detected:
                # Lost gesture - go back to looking (toggle counted above)
                self._change_state(GestureState.LOOKING)
                self.initial_wrist_y = None
            else:
                # Check sustained hold trigger
                if self._check_sustained_hold_trigger():
                    self.last_trigger_reason = "SUSTAINED_HOLD"
                    print(f"DEBUG: Trigger fired! Reason: {self.last_trigger_reason}")
                    self._change_state(GestureState.TRIGGERED)
                    self._fire_trigger()
                # Check armed (upward motion) trigger
                elif self._check_armed_trigger(wrist_y):
                    self.last_trigger_reason = "ARMED_MOTION"
                    print(f"DEBUG: Trigger fired! Reason: {self.last_trigger_reason}")
                    self._change_state(GestureState.TRIGGERED)
                    self._fire_trigger()
        
        elif self.state == GestureState.TRIGGERED:
            # Reset after trigger (cooldown handled above)
            self._change_state(GestureState.LOOKING)
            self.initial_wrist_y = None
            self.toggle_timestamps.clear()
        
        return self.state
    
    def _fire_trigger(self):
        """Execute trigger callbacks."""
        self.last_trigger_time = time.time()
        self._just_triggered = True  # Set flag for external code
        for callback in self.callbacks:
            callback()
    
    def reset(self):
        """Reset state machine to initial state."""
        self.state = GestureState.LOOKING
        self.initial_wrist_y = None
        self.state_enter_time = time.time()
        self.toggle_timestamps.clear()
        self.last_trigger_reason = ""
        self._just_triggered = False
    
    def get_state_info(self) -> dict:
        """Get current state information for debugging/display."""
        cutoff = time.time() - self.config.toggle_window_seconds
        recent_toggles = len([t for t in self.toggle_timestamps if t > cutoff])
        
        return {
            "state": self.state.name,
            "initial_wrist_y": self.initial_wrist_y,
            "time_in_state": time.time() - self.state_enter_time,
            "in_cooldown": self._in_cooldown(),
            "toggle_count": recent_toggles,
            "last_trigger_reason": self.last_trigger_reason,
            "sustained_progress": min(1.0, (time.time() - self.state_enter_time) / self.config.sustained_hold_seconds) if self.state == GestureState.DETECTED else 0,
        }
    
    def get_state_color(self) -> tuple:
        """Get BGR color for current state visualization."""
        colors = {
            GestureState.LOOKING: (128, 128, 128),    # Gray
            GestureState.DETECTED: (0, 255, 255),     # Yellow
            GestureState.TRIGGERED: (0, 255, 0),      # Green
        }
        return colors.get(self.state, (255, 255, 255))
