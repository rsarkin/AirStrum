"""
Air Strum — Renderer Module
Renders a premium dark-themed user interface over the webcam stream using OpenCV.
Handles animations (hover scale, selection glow, strum ripples, progress indicators).
"""

import cv2
import numpy as np
import math
import time
from typing import Dict, List, Tuple, Optional
import config

class UIRenderer:
    """
    Manages the graphical layers, text rendering, glass panels,
    and micro-animations (pulse, glow, scale) for the UI.
    """
    def __init__(self):
        # Slice scale multipliers for chord wheel segments (C, F, Em, Dm, Am, G)
        self.slice_scales: Dict[str, float] = {chord: 1.0 for chord in ["C", "F", "Em", "Dm", "Am", "G"]}
        # Strum ripple animation storage
        self.ripples: List[Dict] = []
        # Pulse animation for successful play
        self.active_chord_pulse = 0.0  # Expands chord wheel inner radius momentarily on strum
        self.last_frame_time = time.time()
        
        # Chord labels matching the clockwise angular order (index 0 is Top)
        self.chords_angular = ["C", "F", "Em", "Dm", "Am", "G"]

        # Virtual strings animation states
        self.string_vibrations: List[float] = [0.0] * config.NUM_STRINGS
        self.string_glows: List[float] = [0.0] * config.NUM_STRINGS
        
        # Calculate Y coordinate positions of the strings (horizontal strings)
        self.string_ys: List[float] = []
        height = config.STRINGS_Y_END - config.STRINGS_Y_START
        spacing = height / (config.NUM_STRINGS - 1)
        for i in range(config.NUM_STRINGS):
            self.string_ys.append(config.STRINGS_Y_START + i * spacing)

    def update_animations(self, hovered_chord: Optional[str], active_chord: str) -> None:
        """Interpolates animation states over time (lerping scales, ticking ripples)."""
        current_time = time.time()
        dt = min(0.1, current_time - self.last_frame_time)  # cap dt to prevent huge jumps
        self.last_frame_time = current_time
        
        # Lerp slice scales
        for chord in self.slice_scales:
            if chord == hovered_chord:
                target = 1.18  # Expand significantly on hover
            elif chord == active_chord:
                target = 1.08  # Slight expansion for active chord
            else:
                target = 1.00  # Default scale
            
            # Smooth lerp
            self.slice_scales[chord] += (target - self.slice_scales[chord]) * (15.0 * dt)
            
        # Decay active chord pulse
        if self.active_chord_pulse > 0.0:
            self.active_chord_pulse -= 4.0 * dt
            if self.active_chord_pulse < 0.0:
                self.active_chord_pulse = 0.0
                
        # Tick strum ripples
        active_ripples = []
        for rip in self.ripples:
            rip["radius"] += 450.0 * dt  # Expand outward (pixels/sec)
            rip["opacity"] -= 3.5 * dt   # Fade out
            if rip["opacity"] > 0:
                active_ripples.append(rip)
        self.ripples = active_ripples

        # Decay string vibrations and glows
        for i in range(config.NUM_STRINGS):
            if self.string_vibrations[i] > 0.0:
                self.string_vibrations[i] -= 10.0 * dt  # fast vibration decay
                if self.string_vibrations[i] < 0.0:
                    self.string_vibrations[i] = 0.0
            if self.string_glows[i] > 0.0:
                self.string_glows[i] -= 3.0 * dt  # slower glow decay
                if self.string_glows[i] < 0.0:
                    self.string_glows[i] = 0.0

    def trigger_strum_pulse(self, start_pos: Tuple[float, float], is_downstroke: bool) -> None:
        """Triggers a physical strum pulse (visual expanding rings and screen flash)."""
        self.active_chord_pulse = 1.0  # Set pulse trigger
        
        # Add visual ripples from the strum coordinate
        color = config.COLOR_ACCENT if is_downstroke else config.COLOR_SELECTED
        self.ripples.append({
            "pos": start_pos,
            "radius": 15.0,
            "opacity": 1.0,
            "color": color
        })

    def trigger_string_pluck(self, string_idx: int) -> None:
        """Triggers vibration and glow animations for a specific string."""
        if 0 <= string_idx < config.NUM_STRINGS:
            self.string_vibrations[string_idx] = 1.0
            self.string_glows[string_idx] = 1.0

    def draw(self, frame: cv2.Mat, hands_data: Dict[str, Dict[str, Tuple[float, float]]],
             hovered_chord: Optional[str], hover_progress: float, active_chord: str,
             fps: float, synth_mode: bool) -> cv2.Mat:
        """
        Main drawing function. Combines raw camera frames with layered drawing overlays.
        """
        # No dark overlay - show raw camera feed directly at full brightness
        h, w, _ = frame.shape
        
        # Overlay canvas for transparent glassmorphic drawings
        ui_overlay = np.zeros_like(frame)
        # Glow canvas for blurred elements
        glow_canvas = np.zeros_like(frame)
        
        # 2. Draw active chord glow (Glow layer)
        self._draw_selection_glow(glow_canvas, active_chord)
        # Apply Gaussian Blur to the glow layer for a beautiful neon look
        glow_blurred = cv2.GaussianBlur(glow_canvas, (49, 49), 0)
        # Add the glow to the frame
        frame = cv2.addWeighted(frame, 1.0, glow_blurred, 0.6, 0)
        
        # 3. Draw Chord Wheel (UI Overlay layer)
        self._draw_chord_wheel(ui_overlay, hovered_chord, active_chord)
        
        # 4. Draw Strum Ripples (UI Overlay layer)
        self._draw_strum_ripples(ui_overlay)
        
        # 5. Draw Virtual Strings (UI Overlay layer) - Disabled: Invisible strings request
        # self._draw_virtual_strings(ui_overlay, active_chord)
        
        # 6. Draw Hand Cursors & Selection progress
        self._draw_hand_cursors(ui_overlay, hands_data, hovered_chord, hover_progress)
        
        # 7. Blend UI overlay with frame (increased alpha to 0.80 for high visibility on bright backgrounds)
        frame = cv2.addWeighted(frame, 1.0, ui_overlay, 0.80, 0)
        
        # 7. Render status overlays (non-transparent text/UI)
        self._draw_status_panel(frame, hands_data, active_chord, fps, synth_mode)
        
        return frame

    def _draw_selection_glow(self, canvas: cv2.Mat, active_chord: str) -> None:
        """Draws a solid colored arc of the active chord which will be blurred to form a glow."""
        cx, cy = config.CHORD_WHEEL_CENTER_X, config.CHORD_WHEEL_CENTER_Y
        r_out = config.CHORD_WHEEL_RADIUS_OUTER
        
        if active_chord in self.chords_angular:
            idx = self.chords_angular.index(active_chord)
            # Calculate angles
            center_angle = idx * 60 - 90
            start_angle = center_angle - 28
            end_angle = center_angle + 28
            
            # Draw a thick arc on the glow canvas using success green color
            # Thickness 12 creates a strong blurred outline matched to the slightly larger wheel size
            cv2.ellipse(canvas, (cx, cy), (int(r_out * 1.15), int(r_out * 1.15)),
                        0, start_angle, end_angle, config.COLOR_SUCCESS, 12)

    def _draw_chord_wheel(self, overlay: cv2.Mat, hovered_chord: Optional[str], active_chord: str) -> None:
        """Draws the transparent segments and chord names of the radial chord wheel."""
        cx, cy = config.CHORD_WHEEL_CENTER_X, config.CHORD_WHEEL_CENTER_Y
        r_in_base = config.CHORD_WHEEL_RADIUS_INNER
        r_out_base = config.CHORD_WHEEL_RADIUS_OUTER
        
        # Add visual pulse expansion to the inner radius on strum
        pulse_expansion = int(self.active_chord_pulse * 15)
        r_in = r_in_base - pulse_expansion
        
        # Draw the 6 chord sectors
        for idx, chord in enumerate(self.chords_angular):
            scale = self.slice_scales[chord]
            
            # Segment radial boundaries
            r_out_scaled = int(r_out_base * scale)
            r_in_scaled = int(r_in * scale)
            
            center_angle = idx * 60 - 90
            # Small gap between segments for layout separation
            start_angle = center_angle - 28
            end_angle = center_angle + 28
            
            # Colors
            if chord == hovered_chord:
                # Hovering slice matches Accent Cyan
                color = config.COLOR_ACCENT
                opacity_factor = 1.3
            elif chord == active_chord:
                # Active selected slice matches Success Green
                color = config.COLOR_SUCCESS
                opacity_factor = 1.1
            else:
                # Inactive slices are elegant dark glass
                color = config.COLOR_GLASS_BG
                opacity_factor = 0.6
                
            # Draw filled sector
            cv2.ellipse(overlay, (cx, cy), (r_out_scaled, r_out_scaled), 0, start_angle, end_angle, color, -1)
            # Antialias outer edge of filled sector to remove jaggies
            cv2.ellipse(overlay, (cx, cy), (r_out_scaled, r_out_scaled), 0, start_angle, end_angle, color, 1, cv2.LINE_AA)
            
            # Draw a clean outline with LINE_AA for hovered/active slices to make them look ultra-sharp
            if chord == hovered_chord:
                cv2.ellipse(overlay, (cx, cy), (r_out_scaled, r_out_scaled), 0, start_angle, end_angle,
                            config.COLOR_ACCENT, 2, cv2.LINE_AA)
            elif chord == active_chord:
                cv2.ellipse(overlay, (cx, cy), (r_out_scaled, r_out_scaled), 0, start_angle, end_angle,
                            config.COLOR_SUCCESS, 2, cv2.LINE_AA)
            
            # Render Chord label text
            # Compute text coordinate in center of slice
            angle_rad = math.radians(center_angle)
            r_mid = (r_in_scaled + r_out_scaled) / 2
            tx = int(cx + r_mid * math.cos(angle_rad))
            ty = int(cy + r_mid * math.sin(angle_rad))
            
            # Font size scaling matching segment scale (solid DUPLEX font)
            font_scale = 0.45 * scale
            font_thickness = 2
            font_face = cv2.FONT_HERSHEY_DUPLEX
            
            text_size = cv2.getTextSize(chord, font_face, font_scale, font_thickness)[0]
            text_x = tx - text_size[0] // 2
            text_y = ty + text_size[1] // 2
            
            # Draw drop-shadow
            cv2.putText(overlay, chord, (text_x + 1, text_y + 1), font_face,
                        font_scale, (10, 10, 10), font_thickness, cv2.LINE_AA)
            # Draw main label
            cv2.putText(overlay, chord, (text_x, text_y), font_face,
                        font_scale, config.COLOR_TEXT_PRIMARY, font_thickness, cv2.LINE_AA)
            
        # Draw central dark mask circle to shape the segments into donut slices
        # We draw a slightly lighter dark gray circle for a premium glass mask look
        cv2.circle(overlay, (cx, cy), r_in, (16, 16, 16), -1)
        
        # Double-ring borders for high-quality definition
        cv2.circle(overlay, (cx, cy), r_in, (80, 80, 80), 1, cv2.LINE_AA)
        cv2.circle(overlay, (cx, cy), r_in + 2, (35, 35, 35), 1, cv2.LINE_AA)
        
        # Draw outer thin grouping ring around the entire wheel
        cv2.circle(overlay, (cx, cy), r_out_base, (75, 75, 75), 1, cv2.LINE_AA)
        
        # Render current active chord in the center of the wheel (bold DUPLEX font)
        center_text = active_chord
        center_font_scale = 0.85
        center_thickness = 2
        center_face = cv2.FONT_HERSHEY_DUPLEX
        center_size = cv2.getTextSize(center_text, center_face,
                                      center_font_scale, center_thickness)[0]
        cc_x = cx - center_size[0] // 2
        cc_y = cy + center_size[1] // 2
        
        # Glowing shadow text for depth
        cv2.putText(overlay, center_text, (cc_x + 1, cc_y + 1), center_face,
                    center_font_scale, (10, 10, 10), center_thickness, cv2.LINE_AA)
        cv2.putText(overlay, center_text, (cc_x, cc_y), center_face,
                    center_font_scale, config.COLOR_SUCCESS, center_thickness, cv2.LINE_AA)

    def _draw_strum_ripples(self, overlay: cv2.Mat) -> None:
        """Draws the expanding ring ripples triggered by right hand strumming."""
        for rip in self.ripples:
            center = (int(rip["pos"][0]), int(rip["pos"][1]))
            radius = int(rip["radius"])
            opacity = rip["opacity"]
            base_color = rip["color"]
            
            # Blend ripple color with opacity
            color = (
                int(base_color[0] * opacity),
                int(base_color[1] * opacity),
                int(base_color[2] * opacity)
            )
            thickness = max(1, int(4 * opacity))
            
            cv2.circle(overlay, center, radius, color, thickness, cv2.LINE_AA)

    def _draw_virtual_strings(self, overlay: cv2.Mat, active_chord: str) -> None:
        """Draws the virtual strings panel, interactive strings, vibrating physics, and note labels."""
        # 1. Define chord string labels mapping
        CHORD_STRING_LABELS = {
            "C": ["C3", "E3", "G3", "C4", "E4", "C5"],
            "G": ["G2", "B2", "D3", "G3", "B3", "G4"],
            "F": ["F2", "C3", "F3", "A3", "C4", "F4"],
            "Am": ["A2", "D3", "E3", "A3", "C4", "E4"],
            "Em": ["E2", "B2", "E3", "G3", "B3", "E4"],
            "Dm": ["A2", "D3", "A3", "D4", "F4", "A4"]
        }
        
        labels = CHORD_STRING_LABELS.get(active_chord, [""] * 6)
        
        # 2. Draw glass panel container (horizontal strings box)
        px_start = config.STRINGS_X_START - 40
        py_start = config.STRINGS_Y_START - 30
        px_end = config.STRINGS_X_END + 40
        py_end = config.STRINGS_Y_END + 30
        
        # Draw background panel with elegant semi-transparent dark glass color
        cv2.rectangle(overlay, (px_start, py_start), (px_end, py_end), config.COLOR_GLASS_BG, -1)
        # Border
        cv2.rectangle(overlay, (px_start, py_start), (px_end, py_end), (55, 55, 55), 2, cv2.LINE_AA)
        
        # 3. Draw each string and its corresponding labels
        for i in range(config.NUM_STRINGS):
            str_y = self.string_ys[i]
            
            # Interpolate color based on glow (from muted gray to success green)
            glow = self.string_glows[i]
            color = (
                int(config.COLOR_SUCCESS[0] * glow + config.COLOR_TEXT_MUTED[0] * (1.0 - glow)),
                int(config.COLOR_SUCCESS[1] * glow + config.COLOR_TEXT_MUTED[1] * (1.0 - glow)),
                int(config.COLOR_SUCCESS[2] * glow + config.COLOR_TEXT_MUTED[2] * (1.0 - glow))
            )
            
            thickness = int(1 + 3 * glow)
            
            # String vibration logic (vertical sine wave offset)
            if self.string_vibrations[i] > 0.0:
                amp = int(12 * self.string_vibrations[i] * math.sin(time.time() * 65))
                mid_x = (config.STRINGS_X_START + config.STRINGS_X_END) // 2
                # Draw vibrating horizontal string segments
                cv2.line(overlay, (config.STRINGS_X_START, int(str_y)), (mid_x, int(str_y + amp)), color, thickness, cv2.LINE_AA)
                cv2.line(overlay, (mid_x, int(str_y + amp)), (config.STRINGS_X_END, int(str_y)), color, thickness, cv2.LINE_AA)
            else:
                # Draw straight resting horizontal string
                cv2.line(overlay, (config.STRINGS_X_START, int(str_y)), (config.STRINGS_X_END, int(str_y)), color, thickness, cv2.LINE_AA)
                
            # 4. Render left and right note labels
            label = labels[i]
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.45
            txt_thickness = 1
            
            text_size = cv2.getTextSize(label, font, font_scale, txt_thickness)[0]
            
            # Left label (note name)
            tx_left = config.STRINGS_X_START - 10 - text_size[0]
            ty_left = int(str_y + text_size[1] // 2)
            cv2.putText(overlay, label, (tx_left, ty_left), font, font_scale, config.COLOR_TEXT_PRIMARY, txt_thickness, cv2.LINE_AA)
            
            # Right label (mute gray name)
            tx_right = config.STRINGS_X_END + 10
            ty_right = int(str_y + text_size[1] // 2)
            cv2.putText(overlay, label, (tx_right, ty_right), font, font_scale, config.COLOR_TEXT_MUTED, txt_thickness, cv2.LINE_AA)

    def _draw_hand_cursors(self, overlay: cv2.Mat, hands_data: Dict[str, Dict[str, Tuple[float, float]]],
                           hovered_chord: Optional[str], hover_progress: float) -> None:
        """Draws cursor points and hover circular progress indicators."""
        # 1. Left Hand Cursor (Disabled: No hand cursor shown on screen)
        
        # 2. Right Hand Cursor (Disabled: Invisible right side pick cursor request)
        pass

    def _draw_status_panel(self, frame: cv2.Mat, hands_data: Dict[str, Dict[str, Tuple[float, float]]],
                           active_chord: str, fps: float, synth_mode: bool) -> None:
        """Draws flat text banners and statuses for user instructions (mirror-adjusted)."""
        h, w, _ = frame.shape
        
        # Check tracking states
        l_tracked = "cursor" in hands_data.get("Left", {})
        r_tracked = "index_tip" in hands_data.get("Right", {})
        
        # 1. Main User Guidance message
        if not l_tracked and not r_tracked:
            msg = "SHOW BOTH HANDS TO BEGIN"
            color = config.COLOR_TEXT_MUTED
        elif not l_tracked:
            msg = "RAISE LEFT HAND TO SELECT CHORD"
            color = config.COLOR_ACCENT
        elif not r_tracked:
            msg = "RAISE RIGHT HAND TO STRUM"
            color = config.COLOR_ACCENT
        else:
            msg = f"READY TO PLAY! ACTIVE: {active_chord}"
            color = config.COLOR_SUCCESS
            
        # Draw Message banner at top
        font_scale = 0.95
        thickness = 2
        text_size = cv2.getTextSize(msg, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)[0]
        tx = w // 2 - text_size[0] // 2
        ty = 50
        
        # Draw background bar for banner
        cv2.rectangle(frame, (tx - 20, ty - 30), (tx + text_size[0] + 20, ty + 12), (10, 10, 10), -1)
        cv2.rectangle(frame, (tx - 20, ty - 30), (tx + text_size[0] + 20, ty + 12), (50, 50, 50), 1)
        # Draw Text
        cv2.putText(frame, msg, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX,
                    font_scale, color, thickness, cv2.LINE_AA)
        
        # 2. Performance and Mode Details (Bottom-left)
        perf_text = f"FPS: {int(fps)}"
        cv2.putText(frame, perf_text, (20, h - 25), cv2.FONT_HERSHEY_SIMPLEX,
                    0.55, config.COLOR_TEXT_MUTED, 1, cv2.LINE_AA)
                    
        # 3. Audio status (Removed: Clean overlay request)
        pass
