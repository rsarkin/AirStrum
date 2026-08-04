# Air Strum 🎸

Air Strum is a webcam-powered virtual acoustic guitar built with Python, OpenCV, and MediaPipe. It transforms a standard webcam feed into a responsive, playful digital instrument.

By dividing interactions between your hands:
- **Left Hand**: Points at a chord on a floating radial chord wheel to select it.
- **Right Hand**: Strum the air up or down to trigger realistic acoustic guitar chord sounds.

---

## Features

- **Floating Radial Chord Wheel**: Floating circular overlay featuring 6 chord segments (**C, G, F, Am, Em, Dm**).
- **Hover Selection**: Hover the left index fingertip cursor over a chord segment for 300ms to select it, accompanied by a circular visual progress loader.
- **Natural Strum Detection**: Automatically tracks right wrist vertical velocity to detect rapid **downstrokes** and **upstrokes**.
- **Automated Physical Audio Synthesis**: If WAV recordings are not found in the assets folder, Air Strum automatically generates a high-quality physical modeling sound pack (using the **Karplus-Strong string-excitation algorithm**) at boot.
- **Sleek UI & Micro-animations**: Glassmorphic UI layout, neon Gaussian selection glow, active chord expansion pulses, and strum wave ripples.

---

## Requirements & Setup

Air Strum requires Python 3.12+.

### Installation

1. Clone or copy the files into your workspace directory.
2. Install the dependencies listed in `requirements.txt`:
   ```bash
   pip install -r requirements.txt
   ```
   *(Note: The audio engine leverages `sounddevice` which wraps PortAudio for low-latency playback).*

---

## How to Play

1. Run the application:
   ```bash
   python app.py
   ```
2. On first run, wait 1-2 seconds for the synthesizer to pre-generate and save the default audio chord pack (`assets/audio/acoustic/*.wav`).
3. Sit or stand facing your webcam:
   - **Hold up your Left Hand**: Use your index finger to point at chord segments. Hover for 300ms to lock it in. The selected chord will glow green and scale up.
   - **Hold up your Right Hand**: Perform a quick vertical sweep (down or up) to play the active chord.
4. **Controls**:
   - `ESC` or `Q`: Exit the application.
   - `D`: Toggle raw MediaPipe tracking skeletons (debug overlay).
   - `C`: Cycle camera sources (if you have multiple webcams).
