import threading
import time
import config

class TrackingRunner:
    """
    Runs hand tracking in a background thread to prevent MediaPipe inference
    from blocking the main rendering loop, allowing for a target 120 FPS.
    """
    def __init__(self, camera, hand_tracker):
        self.camera = camera
        self.hand_tracker = hand_tracker
        self.running = False
        self.thread = None
        self.lock = threading.Lock()
        
        # Thread-safe shared state
        self.hands_data = {"Left": {}, "Right": {}}
        self.raw_landmarks = []
        
    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._run, name="TrackingThread", daemon=True)
        self.thread.start()
        print("[TrackingRunner] Background tracking thread started.")
        
    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
        print("[TrackingRunner] Background tracking thread stopped.")
        
    def _run(self):
        while self.running:
            frame = self.camera.read()
            if frame is None:
                time.sleep(0.005)
                continue
                
            try:
                # Run the hand tracker on the latest frame (no debug drawing in background thread)
                hands_data, _ = self.hand_tracker.process_frame(frame, draw_landmarks=False)
                
                # Extract and clear raw landmarks metadata from hands_data
                raw_landmarks = hands_data.pop("_raw_landmarks", [])
                
                with self.lock:
                    self.hands_data = hands_data
                    self.raw_landmarks = raw_landmarks
            except Exception as e:
                print(f"[TrackingRunner Exception] {e}")
                
            # yield briefly to avoid hogging core, but keep it high performance
            time.sleep(0.001)
            
    def get_latest_data(self):
        with self.lock:
            return self.hands_data.copy(), list(self.raw_landmarks)
