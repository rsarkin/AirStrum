"""
Air Strum — Camera Module
Handles threaded, low-latency webcam frame capture and horizontal mirroring.
"""

import cv2
import threading
import time
from typing import Optional, Tuple

class Camera:
    """
    Manages webcam capture in a separate thread to prevent frame reading
    from blocking the main rendering and gesture detection loop.
    """
    def __init__(self, device_index: int = 0, resolution: Tuple[int, int] = (1280, 720)):
        self.device_index = device_index
        self.resolution = resolution
        self.cap = cv2.VideoCapture(self.device_index)
        
        # Set preferred resolution
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, resolution[0])
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, resolution[1])
        
        self.frame = None
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.lock = threading.Lock()
        
        self.is_opened = self.cap.isOpened()
        if not self.is_opened:
            print(f"[Camera] Error: Camera index {device_index} could not be opened.")
        else:
            # Get actual resolution set by camera
            actual_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            print(f"[Camera] Initialized successfully. Resolution: {actual_w}x{actual_h}")

    def start(self) -> bool:
        """Starts the background capture thread."""
        if not self.is_opened:
            return False
        self.running = True
        self.thread = threading.Thread(target=self._update, name="CameraCaptureThread", daemon=True)
        self.thread.start()
        return True

    def _update(self) -> None:
        """Continuously pulls frames from the device and mirrors them."""
        while self.running:
            ret, frame = self.cap.read()
            if ret:
                # Mirror horizontally for natural interactive alignment
                mirrored_frame = cv2.flip(frame, 1)
                
                with self.lock:
                    self.frame = mirrored_frame
            else:
                # Brief sleep to avoid CPU spinning if frame capture drops
                time.sleep(0.005)

    def read(self) -> Optional[cv2.Mat]:
        """Thread-safe read of the latest frame."""
        with self.lock:
            return self.frame.copy() if self.frame is not None else None

    def release(self) -> None:
        """Stops the thread and releases the webcam hardware."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
        if self.cap.isOpened():
            self.cap.release()
        print("[Camera] Camera released.")
