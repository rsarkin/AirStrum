"""
Air Strum — Chord Wheel Module
Handles circular coordinate layout mapping, hover segment calculations, and selection timers.
"""

import math
import time
from typing import Optional, Tuple
import config

class ChordWheel:
    """
    Manages the radial chord wheel layout and hover selection physics.
    Chords are laid out clockwise starting from the top: C, F, Em, Dm, Am, G.
    """
    def __init__(self):
        self.cx = config.CHORD_WHEEL_CENTER_X
        self.cy = config.CHORD_WHEEL_CENTER_Y
        self.r_in = config.CHORD_WHEEL_RADIUS_INNER
        self.r_out = config.CHORD_WHEEL_RADIUS_OUTER
        
        # Clockwise chord arrangement from 12 o'clock (0 degrees relative to top)
        self.chords = ["C", "F", "Em", "Dm", "Am", "G"]
        
        self.active_chord = "C"               # Default selected chord on boot
        self.hovered_chord: Optional[str] = None
        self.hover_duration = 0.0
        self.last_update_time = time.time()

    def update(self, cursor_pos: Optional[Tuple[float, float]]) -> Tuple[str, float]:
        """
        Updates selection state instantly based on current cursor coordinate.
        Does not require hover waiting (non-elastic), maps center to default chord C.
        """
        if cursor_pos is None:
            # Keep the active_chord selected even when tracking is lost
            return self.active_chord, 1.0
            
        px, py = cursor_pos
        dx = px - self.cx
        dy = py - self.cy
        dist = math.hypot(dx, dy)
        
        if dist < self.r_in:
            # Middle zone selects default chord "C"
            self.active_chord = "C"
        else:
            # Angular sectors select other chords instantly (unbound by r_out)
            angle_rad = math.atan2(dy, dx)
            angle_deg = (math.degrees(angle_rad) + 360) % 360
            rotated_angle = (angle_deg + 90) % 360
            segment_idx = int(((rotated_angle + 30) % 360) / 60)
            
            if 0 <= segment_idx < len(self.chords):
                self.active_chord = self.chords[segment_idx]
                
        return self.active_chord, 1.0
