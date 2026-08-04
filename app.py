"""
Air Strum — Main Application Entry Point
Orchestrates loading, the main frame loop, user inputs, and module coordination.
"""

import cv2
import time
import numpy as np
import config
from camera import Camera
from hand_tracker import HandTracker
from gesture_detector import GestureDetector
from chord_wheel import ChordWheel
from audio_engine import AudioEngine
from renderer import UIRenderer

class AirStrumApp:
    """
    Main application controller that binds webcam input, MediaPipe tracking,
    gestural triggers, audio engine playbacks, and visual updates together.
    """
    def __init__(self):
        self.debug_mode = False
        
        # Initialize OpenCV window immediately to provide rapid startup feedback
        cv2.namedWindow(config.WINDOW_NAME, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(config.WINDOW_NAME, config.WINDOW_WIDTH, config.WINDOW_HEIGHT)
        
        self.show_loading_screen("Initializing audio engine...")
        
        # Load audio player (which triggers physical synthesis on first run)
        self.audio_engine = AudioEngine()
        
        self.show_loading_screen("Starting camera source...")
        
        # Initialize Camera
        self.camera_index = 0
        self.camera = Camera(device_index=self.camera_index, resolution=(config.WINDOW_WIDTH, config.WINDOW_HEIGHT))
        self.camera.start()
        
        # Initialize tracking and rendering modules
        self.hand_tracker = HandTracker()
        self.gesture_detector = GestureDetector()
        self.chord_wheel = ChordWheel()
        self.renderer = UIRenderer()
        
        self.prev_time = time.time()
        self.fps = 30.0  # Base FPS placeholder

    def show_loading_screen(self, status_msg: str) -> None:
        """Displays a clean premium splash screen during startup processing."""
        canvas = np.zeros((config.WINDOW_HEIGHT, config.WINDOW_WIDTH, 3), dtype=np.uint8)
        canvas[:, :] = config.COLOR_BACKGROUND
        
        # Renders "AIR STRUM" title
        title = "AIR STRUM"
        t_size = cv2.getTextSize(title, cv2.FONT_HERSHEY_SIMPLEX, 1.8, 4)[0]
        tx = config.WINDOW_WIDTH // 2 - t_size[0] // 2
        ty = config.WINDOW_HEIGHT // 2 - 20
        cv2.putText(canvas, title, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, 1.8, config.COLOR_ACCENT, 4, cv2.LINE_AA)
        
        # Renders Status subtitle
        s_size = cv2.getTextSize(status_msg, cv2.FONT_HERSHEY_SIMPLEX, 0.65, 1)[0]
        sx = config.WINDOW_WIDTH // 2 - s_size[0] // 2
        sy = config.WINDOW_HEIGHT // 2 + 45
        cv2.putText(canvas, status_msg, (sx, sy), cv2.FONT_HERSHEY_SIMPLEX, 0.65, config.COLOR_TEXT_MUTED, 1, cv2.LINE_AA)
        
        cv2.imshow(config.WINDOW_NAME, canvas)
        cv2.waitKey(1)

    def cycle_camera(self) -> None:
        """Releases the current camera and attempts to open the next index source."""
        self.show_loading_screen("Cycling camera source...")
        self.camera.release()
        
        # Cycle through standard indexes [0, 1, 2, 3]
        self.camera_index = (self.camera_index + 1) % 4
        print(f"[App] Cycling camera. Trying index {self.camera_index}...")
        
        self.camera = Camera(device_index=self.camera_index, resolution=(config.WINDOW_WIDTH, config.WINDOW_HEIGHT))
        if not self.camera.start():
            # If failed, fallback to default index 0
            print(f"[App] Index {self.camera_index} failed to open. Reverting to index 0.")
            self.camera_index = 0
            self.camera = Camera(device_index=self.camera_index, resolution=(config.WINDOW_WIDTH, config.WINDOW_HEIGHT))
            self.camera.start()

    def run(self) -> None:
        """Main execution frame loop."""
        print("[App] Entering main application loop...")
        while True:
            # 1. Calculate FPS
            current_time = time.time()
            dt = current_time - self.prev_time
            if dt > 0.001:
                # Soft exponential filter to smooth FPS readout
                self.fps = 0.92 * self.fps + 0.08 * (1.0 / dt)
            self.prev_time = current_time
            
            # 2. Get frame
            frame = self.camera.read()
            
            if frame is None:
                # Camera unavailable error screen
                err_frame = np.zeros((config.WINDOW_HEIGHT, config.WINDOW_WIDTH, 3), dtype=np.uint8)
                err_frame[:, :] = config.COLOR_BACKGROUND
                
                msg = "NO CAMERA SOURCE FOUND"
                sub_msg = "Connect a webcam. Press 'C' to cycle ports, or 'Q' to quit."
                
                # Draw error labels
                m_size = cv2.getTextSize(msg, cv2.FONT_HERSHEY_SIMPLEX, 1.1, 2)[0]
                cv2.putText(err_frame, msg, (config.WINDOW_WIDTH // 2 - m_size[0] // 2, config.WINDOW_HEIGHT // 2 - 15),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.1, (100, 100, 255), 2, cv2.LINE_AA)
                
                s_size = cv2.getTextSize(sub_msg, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)[0]
                cv2.putText(err_frame, sub_msg, (config.WINDOW_WIDTH // 2 - s_size[0] // 2, config.WINDOW_HEIGHT // 2 + 35),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, config.COLOR_TEXT_MUTED, 1, cv2.LINE_AA)
                
                cv2.imshow(config.WINDOW_NAME, err_frame)
            else:
                # 3. Process frame with MediaPipe
                hands_data, processed_frame = self.hand_tracker.process_frame(frame, draw_landmarks=self.debug_mode)
                
                # 4. Update chord selector (Left Hand index cursor)
                left_hand = hands_data.get("Left", {})
                cursor_pos = left_hand.get("cursor")
                hovered_chord, hover_progress = self.chord_wheel.update(cursor_pos)
                
                # 5. Process Strummer (Right Hand crossing strings)
                right_hand = hands_data.get("Right", {})
                plucked_strings = self.gesture_detector.update_strings(right_hand)
                
                active_chord = self.chord_wheel.active_chord
                for string_idx in plucked_strings:
                    print(f"[App] String pluck detected! Play: {active_chord} | String: {string_idx}")
                    
                    # Play sound
                    self.audio_engine.play_string(active_chord, string_idx)
                    
                    # Trigger visual string pluck animation
                    self.renderer.trigger_string_pluck(string_idx)
                
                # 6. Animate and render UI
                self.renderer.update_animations(hovered_chord, self.chord_wheel.active_chord)
                ui_frame = self.renderer.draw(
                    processed_frame, hands_data, hovered_chord, hover_progress,
                    self.chord_wheel.active_chord, self.fps, self.audio_engine.synth_mode_active
                )
                
                cv2.imshow(config.WINDOW_NAME, ui_frame)
                
            # 7. Listen for keyboard triggers
            key = cv2.waitKey(1) & 0xFF
            if key == 27 or key == ord('q'): # ESC or Q to quit
                break
            elif key == ord('d'): # D to toggle MediaPipe debug bones
                self.debug_mode = not self.debug_mode
                print(f"[App] Debug bones: {self.debug_mode}")
            elif key == ord('c'): # C to cycle camera sources
                self.cycle_camera()
                
        self.cleanup()

    def cleanup(self) -> None:
        """Closes all hardware streams and shuts down libraries."""
        print("[App] Beginning shutdown sequence...")
        self.camera.release()
        self.hand_tracker.close()
        self.audio_engine.shutdown()
        cv2.destroyAllWindows()
        print("[App] Shutdown complete.")

if __name__ == "__main__":
    app = AirStrumApp()
    app.run()
