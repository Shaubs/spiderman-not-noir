from tracking.gesture_detector import Gesture
from typing import Optional


class SpidermanGesture(Gesture):
    """
    Detects the Spider-Man web-shooting gesture with upside-down palm.
    Palm base above fingers, index and pinky extended, middle and ring folded.
    """
    
    @property
    def name(self) -> str:
        return "spiderman"
    
    def detect(self, hand_landmarks) -> Optional[float]:
        """Detect the Spider-Man gesture with upside-down palm."""
        
        EXTENSION_THRESHOLD = 0.04
        FOLD_THRESHOLD = 0.03
        
        # Wrist (palm base)
        wrist = hand_landmarks[0]
        
        # Finger tips
        thumb_tip = hand_landmarks[4]
        index_tip = hand_landmarks[8]
        middle_tip = hand_landmarks[12]
        ring_tip = hand_landmarks[16]
        pinky_tip = hand_landmarks[20]
        
        # Finger MCP joints (knuckles - base of fingers)
        index_mcp = hand_landmarks[5]
        middle_mcp = hand_landmarks[9]
        ring_mcp = hand_landmarks[13]
        pinky_mcp = hand_landmarks[17]
        
        # Finger PIP joints
        index_pip = hand_landmarks[6]
        middle_pip = hand_landmarks[10]
        ring_pip = hand_landmarks[14]
        pinky_pip = hand_landmarks[18]
        
        # ===== CHECK 1: Palm is upside-down (wrist ABOVE finger bases) =====
        # In screen coordinates, y increases downward, so wrist.y < knuckles.y means wrist is above
        avg_knuckle_y = (index_mcp.y + middle_mcp.y + ring_mcp.y + pinky_mcp.y) / 4
        palm_inverted = wrist.y < avg_knuckle_y
        
        if not palm_inverted:
            return None
        
        # ===== CHECK 2: Palm is exposed (facing camera) =====
        # For an exposed palm, thumb should be on the outer side
        # This varies by hand, but we check thumb tip is away from middle finger
        palm_width = abs(pinky_mcp.x - index_mcp.x)
        thumb_spread = abs(thumb_tip.x - middle_mcp.x)
        palm_exposed = thumb_spread > palm_width * 0.3
        
        if not palm_exposed:
            return None
        
        # ===== CHECK 3: Finger positions =====
        # For upside-down palm, "extended" means tip is BELOW pip (higher y value)
        # and "folded" means tip is ABOVE pip (lower y value) - opposite of normal
        
        # Index finger extended (tip below PIP when palm inverted)
        index_extension = index_tip.y - index_pip.y
        index_extended = index_extension > EXTENSION_THRESHOLD
        
        # Pinky extended
        pinky_extension = pinky_tip.y - pinky_pip.y
        pinky_extended = pinky_extension > EXTENSION_THRESHOLD
        
        # Middle finger folded (tip above PIP when palm inverted)
        middle_fold = middle_pip.y - middle_tip.y
        middle_folded = middle_fold > FOLD_THRESHOLD
        
        # Ring finger folded
        ring_fold = ring_pip.y - ring_tip.y
        ring_folded = ring_fold > FOLD_THRESHOLD
        
        # Middle and ring should be curled (tips closer to wrist than knuckles)
        middle_curled = middle_tip.y < middle_mcp.y
        ring_curled = ring_tip.y < ring_mcp.y
        
        # Thumb extended outward
        thumb_mcp = hand_landmarks[2]
        thumb_extended = abs(thumb_tip.x - thumb_mcp.x) > 0.05
        
        if (index_extended and pinky_extended and 
            middle_folded and ring_folded and
            middle_curled and ring_curled):
            
            confidence_score = 0.0
            confidence_score += min(index_extension / 0.08, 0.2)
            confidence_score += min(pinky_extension / 0.08, 0.2)
            confidence_score += min(middle_fold / 0.06, 0.15)
            confidence_score += min(ring_fold / 0.06, 0.15)
            # Bonus for clear palm inversion
            inversion_amount = avg_knuckle_y - wrist.y
            confidence_score += min(inversion_amount / 0.1, 0.2)
            if thumb_extended:
                confidence_score += 0.1
            
            if confidence_score >= 0.6:
                return min(confidence_score, 1.0)
        
        return None


class ThumbsUpGesture(Gesture):
    """Detects a thumbs up gesture."""
    
    @property
    def name(self) -> str:
        return "thumbs_up"
    
    def detect(self, hand_landmarks) -> Optional[float]:
        """Detect thumbs up gesture with strict thresholds."""
        
        THUMB_EXTENSION_THRESHOLD = 0.05
        FINGER_FOLD_THRESHOLD = 0.03
        
        thumb_tip = hand_landmarks[4]
        thumb_ip = hand_landmarks[3]
        
        index_tip = hand_landmarks[8]
        middle_tip = hand_landmarks[12]
        ring_tip = hand_landmarks[16]
        pinky_tip = hand_landmarks[20]
        
        index_pip = hand_landmarks[6]
        middle_pip = hand_landmarks[10]
        ring_pip = hand_landmarks[14]
        pinky_pip = hand_landmarks[18]
        
        index_mcp = hand_landmarks[5]
        
        thumb_extension = thumb_ip.y - thumb_tip.y
        thumb_up = thumb_extension > THUMB_EXTENSION_THRESHOLD
        
        index_folded = (index_tip.y - index_pip.y) > FINGER_FOLD_THRESHOLD
        middle_folded = (middle_tip.y - middle_pip.y) > FINGER_FOLD_THRESHOLD
        ring_folded = (ring_tip.y - ring_pip.y) > FINGER_FOLD_THRESHOLD
        pinky_folded = (pinky_tip.y - pinky_pip.y) > FINGER_FOLD_THRESHOLD
        
        fingers_curled = (
            index_tip.y > index_mcp.y and
            middle_tip.y > index_mcp.y and
            ring_tip.y > index_mcp.y and
            pinky_tip.y > index_mcp.y
        )
        
        if thumb_up and index_folded and middle_folded and ring_folded and pinky_folded and fingers_curled:
            confidence = 0.7
            confidence += min(thumb_extension / 0.1, 0.15)
            confidence += 0.15 if all([index_folded, middle_folded, ring_folded, pinky_folded]) else 0
            return min(confidence, 1.0)
        
        return None