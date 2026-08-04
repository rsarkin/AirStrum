import os
import sys
import time
import threading
import logging
from flask import Flask, render_template, Response, jsonify
import cv2
import numpy as np

# Ensure root directory is in import path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import config
from camera import Camera
from hand_tracker import HandTracker
from gesture_detector import GestureDetector
from chord_wheel import ChordWheel
from audio_engine import AudioEngine
from renderer import UIRenderer

# Disable flask request logging to clean terminal output
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True

# Shared state lock
state_lock = threading.Lock()

# App State
app_state = {
    "left_tracked": False,
    "right_tracked": False,
    "active_chord": "C",
    "hovered_chord": None,
    "hover_progress": 0.0,
    "fps": 0.0,
    "synth_mode": False,
    "current_frame": None,
    "camera_cycle_requested": False,
    "should_run": True
}

def airstrum_loop():
    global app_state
    
    print("[Web Runner] Initializing audio engine...")
    audio_engine = AudioEngine()
    
    camera_index = 0
    print(f"[Web Runner] Starting camera on index {camera_index}...")
    camera = Camera(device_index=camera_index, resolution=(config.WINDOW_WIDTH, config.WINDOW_HEIGHT))
    camera.start()
    
    print("[Web Runner] Initializing tracking modules...")
    hand_tracker = HandTracker()
    gesture_detector = GestureDetector()
    chord_wheel = ChordWheel()
    renderer = UIRenderer()
    
    prev_time = time.time()
    fps = 30.0
    
    print("[Web Runner] Core background thread started successfully.")
    
    while app_state["should_run"]:
        try:
            # Check for camera cycle request
            if app_state["camera_cycle_requested"]:
                print("[Web Runner] Cycling camera source...")
                camera.release()
                camera_index = (camera_index + 1) % 4
                camera = Camera(device_index=camera_index, resolution=(config.WINDOW_WIDTH, config.WINDOW_HEIGHT))
                camera.start()
                with state_lock:
                    app_state["camera_cycle_requested"] = False
                
            # Calculate FPS
            current_time = time.time()
            dt = current_time - prev_time
            if dt > 0.001:
                fps = 0.92 * fps + 0.08 * (1.0 / dt)
            prev_time = current_time
            
            # Read frame
            frame = camera.read()
            if frame is None:
                # Generate black/error frame
                err_frame = np.zeros((config.WINDOW_HEIGHT, config.WINDOW_WIDTH, 3), dtype=np.uint8)
                err_frame[:, :] = config.COLOR_BACKGROUND
                
                msg = "NO CAMERA SOURCE FOUND"
                sub_msg = "Please connect a webcam."
                
                m_size = cv2.getTextSize(msg, cv2.FONT_HERSHEY_SIMPLEX, 1.1, 2)[0]
                cv2.putText(err_frame, msg, (config.WINDOW_WIDTH // 2 - m_size[0] // 2, config.WINDOW_HEIGHT // 2 - 15),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.1, (100, 100, 255), 2, cv2.LINE_AA)
                
                s_size = cv2.getTextSize(sub_msg, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)[0]
                cv2.putText(err_frame, sub_msg, (config.WINDOW_WIDTH // 2 - s_size[0] // 2, config.WINDOW_HEIGHT // 2 + 35),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, config.COLOR_TEXT_MUTED, 1, cv2.LINE_AA)
                
                with state_lock:
                    app_state["current_frame"] = err_frame
                    app_state["left_tracked"] = False
                    app_state["right_tracked"] = False
                    app_state["fps"] = fps
                time.sleep(0.03)
                continue
                
            # Process frame with MediaPipe
            hands_data, processed_frame = hand_tracker.process_frame(frame, draw_landmarks=True)
            
            # Update Chord Wheel (Left hand cursor)
            left_hand = hands_data.get("Left", {})
            cursor_pos = left_hand.get("cursor")
            hovered_chord, hover_progress = chord_wheel.update(cursor_pos)
            
            # Process Strummer (Right Hand crossing strings)
            right_hand = hands_data.get("Right", {})
            plucked_strings = gesture_detector.update_strings(right_hand)
            
            active_chord = chord_wheel.active_chord
            for string_idx in plucked_strings:
                print(f"[Web Runner] String pluck detected! Play: {active_chord} | String: {string_idx}")
                audio_engine.play_string(active_chord, string_idx)
                renderer.trigger_string_pluck(string_idx)
                
            # Render UI
            renderer.update_animations(hovered_chord, chord_wheel.active_chord)
            ui_frame = renderer.draw(
                processed_frame, hands_data, hovered_chord, hover_progress,
                chord_wheel.active_chord, fps, audio_engine.synth_mode_active
            )
            
            with state_lock:
                app_state["current_frame"] = ui_frame
                app_state["frame_version"] = app_state.get("frame_version", 0) + 1
                app_state["left_tracked"] = "cursor" in left_hand
                app_state["right_tracked"] = "index_tip" in right_hand
                app_state["active_chord"] = chord_wheel.active_chord
                app_state["hovered_chord"] = hovered_chord
                app_state["hover_progress"] = hover_progress
                app_state["fps"] = fps
                app_state["synth_mode"] = audio_engine.synth_mode_active
                
            # Dynamic frame rate limiter to match target FPS without static lag overhead
            frame_duration = 1.0 / config.TARGET_FPS
            elapsed = time.time() - current_time
            sleep_time = max(0.001, frame_duration - elapsed)
            time.sleep(sleep_time)
            
        except Exception as e:
            print(f"[Web Runner Exception] error: {e}")
            time.sleep(0.1)
            
    # Cleanup camera/session
    camera.release()
    hand_tracker.close()
    audio_engine.shutdown()
    print("[Web Runner] Core background thread cleaned up.")

@app.route('/')
def index():
    return render_template('index.html')

def gen_frames():
    last_version = -1
    while True:
        frame = None
        version = -1
        with state_lock:
            frame = app_state["current_frame"]
            version = app_state.get("frame_version", 0)
            
        if frame is not None and version != last_version:
            last_version = version
            # Resize frame down slightly to 854x480 (16:9) to optimize network bandwidth
            small_frame = cv2.resize(frame, (854, 480), interpolation=cv2.INTER_AREA)
            # Encode at 70% JPEG quality to drastically reduce CPU rendering time and bandwidth
            ret, buffer = cv2.imencode('.jpg', small_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
            if ret:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        time.sleep(0.005) # Yield thread briefly to prevent high CPU usage

@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/status')
def get_status():
    with state_lock:
        return jsonify({
            "left_tracked": app_state["left_tracked"],
            "right_tracked": app_state["right_tracked"],
            "active_chord": app_state["active_chord"],
            "hovered_chord": app_state["hovered_chord"],
            "hover_progress": app_state["hover_progress"],
            "fps": int(app_state["fps"]),
            "synth_mode": app_state["synth_mode"]
        })

@app.route('/cycle_camera')
def cycle_camera():
    with state_lock:
        app_state["camera_cycle_requested"] = True
    return jsonify({"status": "success"})

if __name__ == '__main__':
    # Start Air Strum thread
    bg_thread = threading.Thread(target=airstrum_loop, daemon=True)
    bg_thread.start()
    
    # Run local server
    print("[Web Runner] Running Flask server on http://127.0.0.1:5000")
    app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)
