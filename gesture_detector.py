"""
Air Strum — Gesture Detector Module
Analyzes right hand velocity over time to detect downstroke and upstroke gestures with cooldown lockouts.
Now also tracks string crossing for the virtual guitar strings.
"""

import time
from collections import deque
from typing import Dict, Tuple, Optional, List
import config

class GestureDetector:
    """
    Tracks vertical movement velocity of the right wrist to detect air-strumming.
    Now also tracks index tip coordinates to detect virtual string pluck events.
    """
    def __init__(self):
        # Stores (timestamp, normalized_y)
        self.history = deque(maxlen=config.STRUM_HISTORY_LEN)
        self.last_strum_time = 0.0
        self.last_strum_direction: Optional[str] = None

        # String tracking coordinates
        self.last_x: Optional[float] = None
        self.last_y: Optional[float] = None
        self.string_cooldowns = [0.0] * config.NUM_STRINGS
        
        # Calculate Y coordinate positions of the strings (horizontal strings)
        self.string_ys = []
        height = config.STRINGS_Y_END - config.STRINGS_Y_START
        spacing = height / (config.NUM_STRINGS - 1)
        for i in range(config.NUM_STRINGS):
            self.string_ys.append(config.STRINGS_Y_START + i * spacing)

    def update(self, right_hand_landmarks: Dict[str, Tuple[float, float]]) -> Optional[str]:
        """
        Analyzes right wrist coordinates. (Fallback)
        """
        if "index_tip_normalized" not in right_hand_landmarks:
            # Right hand lost, reset history to avoid stale motion calculations
            self.history.clear()
            return None
            
        current_time = time.time()
        _, norm_y = right_hand_landmarks["index_tip_normalized"]
        
        self.history.append((current_time, norm_y))
        
        # Wait until we have enough history to compute velocity
        if len(self.history) < config.STRUM_HISTORY_LEN:
            return None
            
        # Compute velocity (dy / dt) in screen heights per second
        t_oldest, y_oldest = self.history[0]
        t_newest, y_newest = self.history[-1]
        
        dt = t_newest - t_oldest
        if dt <= 0.001:
            return None
            
        velocity = (y_newest - y_oldest) / dt
        
        # Enforce temporal cooldown lockout
        if current_time - self.last_strum_time > config.STRUM_COOLDOWN:
            # Positive velocity = downward motion (since screen 0 is top, screen H is bottom)
            if velocity > config.STRUM_SPEED_THRESHOLD:  # Downstroke threshold
                self.last_strum_time = current_time
                self.last_strum_direction = "down"
                return "down"
            # Negative velocity = upward motion
            elif velocity < -config.STRUM_SPEED_THRESHOLD:  # Upstroke threshold
                self.last_strum_time = current_time
                self.last_strum_direction = "up"
                return "up"
                
        return None

    def update_strings(self, right_hand_landmarks: Dict[str, Tuple[float, float]]) -> List[int]:
        """
        Checks right index tip coordinates and compares them to the virtual strings' Y coordinates.
        Returns a list of string indices [0..5] that were crossed/plucked in this frame.
        """
        plucked_strings = []
        if "index_tip" not in right_hand_landmarks:
            # Reset last position when hand is lost
            self.last_x = None
            self.last_y = None
            return plucked_strings
            
        x, y = right_hand_landmarks["index_tip"]
        current_time = time.time()
        
        if self.last_x is not None and self.last_y is not None:
            # Check horizontal bounds: did the cursor reside in the X span?
            in_x_bounds = (config.STRINGS_X_START <= x <= config.STRINGS_X_END) or \
                          (config.STRINGS_X_START <= self.last_x <= config.STRINGS_X_END)
            
            if in_x_bounds:
                for i, str_y in enumerate(self.string_ys):
                    # Check vertical crossing
                    crossed = False
                    if self.last_y < str_y <= y:
                        crossed = True
                    elif y <= str_y < self.last_y:
                        crossed = True
                        
                    if crossed:
                        # Enforce per-string cooldown
                        if current_time - self.string_cooldowns[i] > config.STRING_COOLDOWN:
                            plucked_strings.append(i)
                            self.string_cooldowns[i] = current_time
                            
        self.last_x = x
        self.last_y = y
        return plucked_strings
