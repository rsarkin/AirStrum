# Air Strum 🎸

Air Strum is a webcam-powered virtual acoustic guitar built with HTML5 Canvas, MediaPipe Hands, and Web Audio API. It transforms any web browser into a responsive, 60 FPS digital instrument.

By dividing interactions between your hands:
- **Left Hand**: Points at a chord on a floating radial chord wheel to select it (`C, G, F, Am, Em, Dm`).
- **Right Hand**: Strum the 6 vertical guitar strings or pluck individual notes to trigger instant acoustic guitar sounds.

---

## 🚀 Deploying on Vercel

Air Strum is 100% client-side and pre-configured for **1-click Vercel deployment** with zero backend configuration needed.

### Option 1: Vercel CLI
```bash
npm install -g vercel
vercel
```

### Option 2: GitHub / Vercel Dashboard
1. Push this repository to GitHub.
2. Import the project in your [Vercel Dashboard](https://vercel.com/new).
3. Click **Deploy**. Vercel will automatically detect `index.html` and serve the site globally via CDN.

---

## ⚡ Features

- **60 FPS Performance**: MediaPipe tracking and Canvas drawing run locally in the browser with `requestAnimationFrame`.
- **Zero-Latency Audio**: Pre-loaded acoustic WAV chord samples with a real-time **Karplus-Strong physical modeling Web Audio synthesizer** fallback.
- **Floating Radial Chord Wheel**: 6 chord segments (**C, G, F, Am, Em, Dm**) with interactive selection.
- **Interactive String Plucking**: 6 vertical string lines with glowing wave ripple animations upon being struck.
- **Dark Glassmorphic UI**: High-contrast modern dashboard layout with real-time tracking indicators.

---

## 🎮 How to Play

1. Open `index.html` locally or visit your deployed Vercel URL.
2. Allow webcam permission when prompted by the browser.
3. Sit or stand facing your webcam:
   - **Left Hand**: Point at chord segments on the radial wheel to lock in your active chord.
   - **Right Hand**: Sweep your index finger across the 6 vertical strings on the right to strum or pluck.
4. **Controls**:
   - `D`: Toggle raw MediaPipe tracking skeletons overlay.
