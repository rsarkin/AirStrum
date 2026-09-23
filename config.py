"""
Air Strum — Configuration Module
Contains all constants, UI layout parameters, colors, and tuning tables.
"""

# Window settings
WINDOW_NAME = "Air Strum"
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
TARGET_FPS = 120

# Camera settings
CAMERA_WIDTH = 1280
CAMERA_HEIGHT = 720
CAMERA_FOURCC = "MJPG"  # Use MJPG compression to unlock high FPS without saturating USB bandwidth

TRACKING_WIDTH = 256
TRACKING_HEIGHT = 144

# OpenCV Color Palettes (BGR format)
COLOR_BACKGROUND = (17, 17, 17)      # Hex #111111 (Dark background)
COLOR_ACCENT = (255, 194, 0)         # Hex #00C2FF (Vibrant Cyan)
COLOR_SELECTED = (79, 213, 255)      # Hex #FFD54F (Soft Yellow)
COLOR_SUCCESS = (80, 175, 76)        # Hex #4CAF50 (Leaf Green)
COLOR_TEXT_PRIMARY = (245, 245, 245)  # Hex #F5F5F5 (Off-white)
COLOR_TEXT_MUTED = (130, 130, 130)    # Hex #828282 (Gray)
COLOR_GLASS_BG = (35, 35, 35)        # Hex #232323 (Base for transparent panel overlays)
COLOR_GLOW_L_HAND = (255, 100, 100)  # Hex #6464FF (Soft Red/Pink for cursor)
COLOR_GLOW_R_HAND = (100, 255, 100)  # Hex #64FF64 (Soft Green for pick)

# Hand tracking settings
MIN_DETECTION_CONFIDENCE = 0.6
MIN_TRACKING_CONFIDENCE = 0.6
CURSOR_SMOOTHING = 0.30              # EMA alpha (lower = smoother cursor, higher = more responsive)

# Chord Wheel settings
CHORD_WHEEL_RADIUS_INNER = 45
CHORD_WHEEL_RADIUS_OUTER = 120
CHORD_WHEEL_CENTER_X = 220
CHORD_WHEEL_CENTER_Y = 500
CHORD_LIST = ["C", "G", "F", "Am", "Em", "Dm"]
HOVER_SELECTION_TIME = 0.30          # 300 ms hover threshold

# Strumming settings
STRUM_SPEED_THRESHOLD = 1.0         # Minimum velocity (normalized screen heights per second) to trigger a strum
STRUM_COOLDOWN = 0.35               # 350 ms between strums to prevent double triggers
STRUM_HISTORY_LEN = 4               # Number of frames to track motion history

# Virtual Guitar Strings settings
STRINGS_X_START = 900
STRINGS_X_END = 1180
STRINGS_Y_START = 200
STRINGS_Y_END = 520
NUM_STRINGS = 6
STRING_COOLDOWN = 0.08              # 80 ms cooldown per string to prevent double triggers

# Audio synthesis settings (Karplus-Strong Fallback)
AUDIO_SAMPLE_RATE = 44100
AUDIO_CHANNELS = 2                  # Stereo
AUDIO_ASSET_DIR = "assets/audio/acoustic"
AUDIO_LATENCY = "low"

# Tuning tables (Guitar Chord Note Frequencies)
# E2 = 82.41, A2 = 110.00, D3 = 146.83, G3 = 196.00, B3 = 246.94, E4 = 329.63
CHORD_TUNINGS = {
    "C": [130.81, 164.81, 196.00, 261.63, 329.63, 523.25],         # C3, E3, G3, C4, E4, C5 (6 strings)
    "G": [98.00, 123.47, 146.83, 196.00, 246.94, 392.00],  # G2, B2, D3, G3, B3, G4
    "F": [87.31, 130.81, 174.61, 220.00, 261.63, 349.23],  # F2, C3, F3, A3, C4, F4
    "Am": [110.00, 146.83, 164.81, 220.00, 261.63, 329.63],        # A2, D3, E3, A3, C4, E4
    "Em": [82.41, 123.47, 164.81, 196.00, 246.94, 329.63], # E2, B2, E3, G3, B3, E4
    "Dm": [110.00, 146.83, 220.00, 293.66, 349.23, 440.00]         # A2, D3, A3, D4, F4, A4
}
