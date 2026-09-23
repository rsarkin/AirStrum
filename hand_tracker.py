"""
Air Strum — Hand Tracker Module
Wraps MediaPipe Hands to track left/right hand coordinates and apply smoothing to reduce jitter.
"""

import os
import cv2
import time
import urllib.request
import mediapipe as mp
import numpy as np
from typing import Dict, Optional, Tuple
import config

# Static hand connections for debug drawing
HAND_CONNECTIONS = [
    (0, 1), (1, 5), (9, 13), (13, 17), (5, 9), (0, 17),
    (1, 2), (2, 3), (3, 4),
    (5, 6), (6, 7), (7, 8),
    (9, 10), (10, 11), (11, 12),
    (13, 14), (14, 15), (15, 16),
    (17, 18), (18, 19), (19, 20)
]

class HandTracker:
    """
    Interfaces with MediaPipe Hands Tasks API to detect and track key landmarks for
    both hands. Resolves mirror-swapping and smooths cursor movements.
    """
    def __init__(self):
        # Set up model path
        model_dir = os.path.join("assets", "models")
        os.makedirs(model_dir, exist_ok=True)
        model_path = os.path.normpath(os.path.join(model_dir, "hand_landmarker.task"))

        # Download model if not present
        if not os.path.exists(model_path):
            print(f"[HandTracker] Model not found. Downloading hand_landmarker.task to {model_path}...")
            url = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
            urllib.request.urlretrieve(url, model_path)
            print("[HandTracker] Model download completed successfully.")

        # Initialize MediaPipe Tasks HandLandmarker
        from mediapipe.tasks import python
        from mediapipe.tasks.python import vision

        base_options = python.BaseOptions(model_asset_path=model_path)
        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.VIDEO,
            num_hands=2,
            min_hand_detection_confidence=config.MIN_DETECTION_CONFIDENCE,
            min_hand_presence_confidence=config.MIN_TRACKING_CONFIDENCE
        )
        self.detector = vision.HandLandmarker.create_from_options(options)

        self.last_timestamp_ms = 0
        
        # Smoothed coordinates cache for cursor (Left index fingertip)
        self._smoothed_cursor: Optional[Tuple[float, float]] = None
        # Position histories for smoothing/velocity tracking
        self.prev_landmarks: Dict[str, Dict[str, Tuple[float, float]]] = {
            "Left": {},
            "Right": {}
        }

    def process_frame(self, frame: cv2.Mat, draw_landmarks: bool = False) -> Tuple[Dict[str, Dict[str, Tuple[float, float]]], cv2.Mat]:
        """
        Processes a mirrored BGR frame.
        Returns:
            - A dictionary containing coordinate data for 'Left' and 'Right' hands.
            - The frame with optional tracking landmarks drawn.
        """
        h, w, _ = frame.shape
        
        # Downscale frame for fast MediaPipe inference
        scale_w = config.TRACKING_WIDTH
        scale_h = config.TRACKING_HEIGHT
        small_frame = cv2.resize(frame, (scale_w, scale_h), interpolation=cv2.INTER_LINEAR)
        
        # MediaPipe Tasks API expects mp.Image
        rgb_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        
        # Calculate strictly increasing frame timestamp
        timestamp_ms = int(time.time() * 1000)
        if timestamp_ms <= self.last_timestamp_ms:
            timestamp_ms = self.last_timestamp_ms + 1
        self.last_timestamp_ms = timestamp_ms
        
        # Run detection
        results = self.detector.detect_for_video(mp_image, timestamp_ms)
        
        detected_hands = {
            "Left": {},   # Physical Left Hand (Chord selector)
            "Right": {}   # Physical Right Hand (Strummer)
        }
        
        raw_list = []
        if results.hand_landmarks and results.handedness:
            for hand_landmarks in results.hand_landmarks:
                raw_list.append([(lm.x, lm.y) for lm in hand_landmarks])
                
            for hand_landmarks, hand_handedness in zip(results.hand_landmarks, results.handedness):
                # Physical Left Hand = MediaPipe "Right" label in mirrored view
                mp_label = hand_handedness[0].category_name
                physical_side = "Left" if mp_label == "Right" else "Right"
                
                # Extract specific landmarks we need
                landmarks_dict = {}
                
                # Wrist
                wrist = hand_landmarks[0]
                landmarks_dict["wrist"] = (wrist.x * w, wrist.y * h)
                landmarks_dict["wrist_normalized"] = (wrist.x, wrist.y)
                
                # Index Tip (Landmark 8)
                idx_tip = hand_landmarks[8]
                landmarks_dict["index_tip"] = (idx_tip.x * w, idx_tip.y * h)
                landmarks_dict["index_tip_normalized"] = (idx_tip.x, idx_tip.y)
                
                # Middle Tip (Landmark 12)
                mid_tip = hand_landmarks[12]
                landmarks_dict["middle_tip"] = (mid_tip.x * w, mid_tip.y * h)
                
                # Ring Tip (Landmark 16)
                rng_tip = hand_landmarks[16]
                landmarks_dict["ring_tip"] = (rng_tip.x * w, rng_tip.y * h)
                
                # Pinky Tip (Landmark 20)
                pnk_tip = hand_landmarks[20]
                landmarks_dict["pinky_tip"] = (pnk_tip.x * w, pnk_tip.y * h)
                
                # Index MCP
                idx_mcp = hand_landmarks[5]
                landmarks_dict["index_mcp"] = (idx_mcp.x * w, idx_mcp.y * h)
                
                # Pinky MCP
                pinky_mcp = hand_landmarks[17]
                
                # Palm Center calculation (average of wrist, index mcp, and pinky mcp)
                palm_x = (wrist.x + idx_mcp.x + pinky_mcp.x) / 3.0 * w
                palm_y = (wrist.y + idx_mcp.y + pinky_mcp.y) / 3.0 * h
                landmarks_dict["palm"] = (palm_x, palm_y)
                
                # Apply EMA smoothing to physical left index fingertip (cursor)
                if physical_side == "Left":
                    raw_tip = landmarks_dict["index_tip"]
                    if self._smoothed_cursor is None:
                        self._smoothed_cursor = raw_tip
                    else:
                        alpha = config.CURSOR_SMOOTHING
                        self._smoothed_cursor = (
                            alpha * raw_tip[0] + (1 - alpha) * self._smoothed_cursor[0],
                            alpha * raw_tip[1] + (1 - alpha) * self._smoothed_cursor[1]
                        )
                    landmarks_dict["cursor"] = self._smoothed_cursor
                
                detected_hands[physical_side] = landmarks_dict
                
                # Draw standard hand landmarks for feedback (only if draw_landmarks is enabled)
                if draw_landmarks:
                    for connection in HAND_CONNECTIONS:
                        start_idx, end_idx = connection
                        if start_idx < len(hand_landmarks) and end_idx < len(hand_landmarks):
                            pt1 = (int(hand_landmarks[start_idx].x * w), int(hand_landmarks[start_idx].y * h))
                            pt2 = (int(hand_landmarks[end_idx].x * w), int(hand_landmarks[end_idx].y * h))
                            cv2.line(frame, pt1, pt2, (80, 80, 80), 1)
                    for lm in hand_landmarks:
                        pt = (int(lm.x * w), int(lm.y * h))
                        cv2.circle(frame, pt, 2, (120, 120, 120), -1)
                
        else:
            # Clear cursor cache if physical left hand leaves screen
            self._smoothed_cursor = None
            
        detected_hands["_raw_landmarks"] = raw_list
        return detected_hands, frame

    def close(self) -> None:
        """Closes the MediaPipe hands session."""
        self.detector.close()

