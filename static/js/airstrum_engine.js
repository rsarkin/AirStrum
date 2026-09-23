/**
 * Air Strum — Client-Side 60 FPS Web Engine
 * Powered by MediaPipe Hands, Web Audio API, and HTML5 Canvas.
 */

class AirStrumEngine {
    constructor() {
        // Configuration Parameters
        this.WIDTH = 1280;
        this.HEIGHT = 720;

        // Chord Wheel Parameters
        this.wheelCenterX = 220;
        this.wheelCenterY = 500;
        this.wheelRadiusIn = 45;
        this.wheelRadiusOut = 120;
        this.chords = ["C", "F", "Em", "Dm", "Am", "G"];
        this.activeChord = "C";
        this.hoveredChord = null;
        this.hoverProgress = 1.0;

        // Virtual Strings (Vertical Strings on Right Side)
        this.stringsXStart = 900;
        this.stringsXEnd = 1180;
        this.stringsYStart = 200;
        this.stringsYEnd = 520;
        this.numStrings = 6;
        this.stringCooldownTime = 80; // ms
        this.stringCooldowns = new Array(6).fill(0);
        this.stringPluckAnim = new Array(6).fill(0); // 0.0 to 1.0 pulse decay

        // Calculate X coordinate for each vertical string
        this.stringXs = [];
        const xSpan = this.stringsXEnd - this.stringsXStart;
        const xSpacing = xSpan / (this.numStrings - 1);
        for (let i = 0; i < this.numStrings; i++) {
            this.stringXs.push(this.stringsXStart + i * xSpacing);
        }

        // Chord Note Frequencies (E2 to C5 range)
        this.chordTunings = {
            "C": [130.81, 164.81, 196.00, 261.63, 329.63, 523.25],
            "G": [98.00, 123.47, 146.83, 196.00, 246.94, 392.00],
            "F": [87.31, 130.81, 174.61, 220.00, 261.63, 349.23],
            "Am": [110.00, 146.83, 164.81, 220.00, 261.63, 329.63],
            "Em": [82.41, 123.47, 164.81, 196.00, 246.94, 329.63],
            "Dm": [110.00, 146.83, 220.00, 293.66, 349.23, 440.00]
        };

        // Hand Tracking State
        this.leftHandTracked = false;
        this.rightHandTracked = false;
        this.leftCursor = null;     // {x, y} smoothed
        this.rightIndexTip = null;  // {x, y} smoothed
        this.prevRightIndexTip = null;
        this.cursorAlpha = 0.35;    // Smoothing factor

        // Performance & Timing
        this.lastFrameTime = performance.now();
        this.fps = 60.0;
        this.debugBones = false;

        // DOM Elements & Canvas Setup
        this.videoElement = document.getElementById('webcam-input');
        this.canvasElement = document.getElementById('airstrum-canvas');
        this.canvasElement.width = this.WIDTH;
        this.canvasElement.height = this.HEIGHT;
        this.ctx = this.canvasElement.getContext('2d');

        // Web Audio Context & Sound Buffers
        this.audioCtx = null;
        this.audioBuffers = {}; // Key: "C_string_0", "C_down", etc.
        this.initAudioContext();
        this.preloadAudioSamples();

        // Bind Keyboard Controls
        window.addEventListener('keydown', (e) => {
            if (e.key === 'd' || e.key === 'D') {
                this.debugBones = !this.debugBones;
                console.log("[AirStrum] Toggle Debug Bones:", this.debugBones);
            }
        });
    }

    initAudioContext() {
        const AudioCtxClass = window.AudioContext || window.webkitAudioContext;
        if (AudioCtxClass) {
            this.audioCtx = new AudioCtxClass();
            // Unlock AudioContext on first user click if suspended by browser policy
            const unlockAudio = () => {
                if (this.audioCtx && this.audioCtx.state === 'suspended') {
                    this.audioCtx.resume();
                }
                window.removeEventListener('click', unlockAudio);
                window.removeEventListener('touchstart', unlockAudio);
            };
            window.addEventListener('click', unlockAudio);
            window.addEventListener('touchstart', unlockAudio);
        }
    }

    async preloadAudioSamples() {
        if (!this.audioCtx) return;
        const chords = ["C", "G", "F", "Am", "Em", "Dm"];
        for (const chord of chords) {
            for (let i = 0; i < 6; i++) {
                const sampleKey = `${chord}_string_${i}`;
                const sampleUrl = `/assets/audio/acoustic/${chord}_string_${i}.wav`;
                try {
                    const response = await fetch(sampleUrl);
                    if (response.ok) {
                        const arrayBuffer = await response.arrayBuffer();
                        const audioBuffer = await this.audioCtx.decodeAudioData(arrayBuffer);
                        this.audioBuffers[sampleKey] = audioBuffer;
                    }
                } catch (e) {
                    // Fail silently to Karplus-Strong physical modeling fallback
                }
            }
        }
        console.log("[AirStrum] Audio sample preloading complete.");
    }

    playString(chord, stringIdx) {
        if (!this.audioCtx) return;
        if (this.audioCtx.state === 'suspended') {
            this.audioCtx.resume();
        }

        const sampleKey = `${chord}_string_${stringIdx}`;

        // 1. Play preloaded WAV audio sample if available
        if (this.audioBuffers[sampleKey]) {
            try {
                const source = this.audioCtx.createBufferSource();
                source.buffer = this.audioBuffers[sampleKey];
                const gainNode = this.audioCtx.createGain();
                gainNode.gain.value = 0.85;
                source.connect(gainNode);
                gainNode.connect(this.audioCtx.destination);
                source.start(0);
                return;
            } catch (err) {
                console.error("WAV playback error, using synth fallback:", err);
            }
        }

        // 2. Real-Time Karplus-Strong Physical String Synthesis Fallback (0ms Latency)
        this.synthesizeStringSound(chord, stringIdx);
    }

    synthesizeStringSound(chord, stringIdx) {
        const freqs = this.chordTunings[chord] || this.chordTunings["C"];
        const freq = freqs[stringIdx] || 220;
        const sampleRate = this.audioCtx.sampleRate;
        const duration = 2.0; // seconds decay
        const totalSamples = Math.floor(sampleRate * duration);
        const period = Math.round(sampleRate / freq);

        const audioBuffer = this.audioCtx.createBuffer(1, totalSamples, sampleRate);
        const channelData = audioBuffer.getChannelData(0);

        // Seed with noise burst
        for (let i = 0; i < period; i++) {
            channelData[i] = Math.random() * 2 - 1;
        }

        // Karplus-Strong ring buffer delay line feedback algorithm
        const damping = 0.992;
        for (let i = period; i < totalSamples; i++) {
            channelData[i] = ((channelData[i - period] + channelData[i - period + 1]) / 2) * damping;
        }

        const source = this.audioCtx.createBufferSource();
        source.buffer = audioBuffer;
        const gainNode = this.audioCtx.createGain();
        gainNode.gain.value = 0.75;
        source.connect(gainNode);
        gainNode.connect(this.audioCtx.destination);
        source.start(0);
    }

    startCamera() {
        console.log("[AirStrum] Initializing MediaPipe Hands & Camera...");
        const hands = new Hands({
            locateFile: (file) => `https://cdn.jsdelivr.net/npm/@mediapipe/hands/${file}`
        });

        hands.setOptions({
            maxNumHands: 2,
            modelComplexity: 1,
            minDetectionConfidence: 0.55,
            minTrackingConfidence: 0.55
        });

        hands.onResults((results) => this.processHandResults(results));

        const camera = new Camera(this.videoElement, {
            onFrame: async () => {
                await hands.send({ image: this.videoElement });
            },
            width: 1280,
            height: 720
        });

        camera.start();
    }

    processHandResults(results) {
        // Compute FPS
        const now = performance.now();
        const dt = now - this.lastFrameTime;
        if (dt > 0) {
            this.fps = 0.9 * this.fps + 0.1 * (1000 / dt);
        }
        this.lastFrameTime = now;

        // Reset tracking states
        this.leftHandTracked = false;
        this.rightHandTracked = false;

        let rawLandmarksList = results.multiHandLandmarks || [];
        let handednessList = results.multiHandedness || [];

        let currentLeftRaw = null;
        let currentRightRaw = null;

        for (let i = 0; i < rawLandmarksList.length; i++) {
            const landmarks = rawLandmarksList[i];
            const handednessLabel = handednessList[i] ? handednessList[i].label : null;

            // Note: Webcam video is mirrored visually, so MediaPipe "Left" corresponds to video left
            if (handednessLabel === "Left" || (i === 0 && !currentLeftRaw)) {
                currentLeftRaw = landmarks;
            } else if (handednessLabel === "Right" || (i === 1 && !currentRightRaw)) {
                currentRightRaw = landmarks;
            }
        }

        // Process Left Hand (Chord Selector Cursor)
        if (currentLeftRaw) {
            this.leftHandTracked = true;
            const indexTip = currentLeftRaw[8];
            // Mirror X coordinate for intuitive mirror-mode interaction
            const rawX = (1.0 - indexTip.x) * this.WIDTH;
            const rawY = indexTip.y * this.HEIGHT;

            if (!this.leftCursor) {
                this.leftCursor = { x: rawX, y: rawY };
            } else {
                this.leftCursor.x = this.cursorAlpha * rawX + (1 - this.cursorAlpha) * this.leftCursor.x;
                this.leftCursor.y = this.cursorAlpha * rawY + (1 - this.cursorAlpha) * this.leftCursor.y;
            }

            this.updateChordWheel(this.leftCursor);
        } else {
            this.leftCursor = null;
        }

        // Process Right Hand (Virtual String Strummer)
        if (currentRightRaw) {
            this.rightHandTracked = true;
            const indexTip = currentRightRaw[8];
            const rawX = (1.0 - indexTip.x) * this.WIDTH;
            const rawY = indexTip.y * this.HEIGHT;

            this.prevRightIndexTip = this.rightIndexTip ? { ...this.rightIndexTip } : null;

            if (!this.rightIndexTip) {
                this.rightIndexTip = { x: rawX, y: rawY };
            } else {
                this.rightIndexTip.x = this.cursorAlpha * rawX + (1 - this.cursorAlpha) * this.rightIndexTip.x;
                this.rightIndexTip.y = this.cursorAlpha * rawY + (1 - this.cursorAlpha) * this.rightIndexTip.y;
            }

            this.updateStringPlucks(this.rightIndexTip, this.prevRightIndexTip);
        } else {
            this.rightIndexTip = null;
            this.prevRightIndexTip = null;
        }

        // Render Frame
        this.renderFrame(results);
        this.updateDashboardUI();
    }

    updateChordWheel(cursor) {
        if (!cursor) return;

        const dx = cursor.x - this.wheelCenterX;
        const dy = cursor.y - this.wheelCenterY;
        const dist = Math.hypot(dx, dy);

        if (dist < this.wheelRadiusIn) {
            this.activeChord = "C";
        } else {
            let angleRad = Math.atan2(dy, dx);
            let angleDeg = (angleRad * (180 / Math.PI) + 360) % 360;
            let rotatedAngle = (angleDeg + 90) % 360;
            let segmentIdx = Math.floor(((rotatedAngle + 30) % 360) / 60);

            if (segmentIdx >= 0 && segmentIdx < this.chords.length) {
                this.activeChord = this.chords[segmentIdx];
            }
        }
    }

    updateStringPlucks(currentPos, prevPos) {
        if (!currentPos || !prevPos) return;

        const now = performance.now();

        // Check horizontal string region
        const inYBounds = (currentPos.y >= this.stringsYStart && currentPos.y <= this.stringsYEnd) ||
                          (prevPos.y >= this.stringsYStart && prevPos.y <= this.stringsYEnd);

        if (inYBounds) {
            for (let i = 0; i < this.numStrings; i++) {
                const strX = this.stringXs[i];

                // Check horizontal crossing across string X
                const crossed = (prevPos.x < strX && currentPos.x >= strX) ||
                                (currentPos.x <= strX && prevPos.x > strX);

                if (crossed) {
                    if (now - this.stringCooldowns[i] > this.stringCooldownTime) {
                        this.stringCooldowns[i] = now;
                        this.stringPluckAnim[i] = 1.0; // Trigger visual wave ripple pulse
                        this.playString(this.activeChord, i);
                    }
                }
            }
        }
    }

    renderFrame(results) {
        const ctx = this.ctx;
        ctx.clearRect(0, 0, this.WIDTH, this.HEIGHT);

        // 1. Draw Mirrored Video Feed Background
        ctx.save();
        ctx.translate(this.WIDTH, 0);
        ctx.scale(-1, 1);
        ctx.drawImage(this.videoElement, 0, 0, this.WIDTH, this.HEIGHT);
        ctx.restore();

        // 2. Subtle Dark Glass Overlay Tint
        ctx.fillStyle = 'rgba(11, 11, 11, 0.40)';
        ctx.fillRect(0, 0, this.WIDTH, this.HEIGHT);

        // 3. Draw Debug Hand Skeletons if toggled
        if (this.debugBones && results.multiHandLandmarks) {
            this.drawDebugLandmarks(results.multiHandLandmarks);
        }

        // 4. Draw Radial Chord Wheel
        this.drawChordWheel(ctx);

        // 5. Draw 6 Interactive Vertical Guitar Strings
        this.drawVirtualStrings(ctx);

        // 6. Draw Left & Right Fingertip Glowing Cursors
        if (this.leftCursor) {
            this.drawGlowCursor(ctx, this.leftCursor.x, this.leftCursor.y, '#00C2FF', 'CHORD');
        }
        if (this.rightIndexTip) {
            this.drawGlowCursor(ctx, this.rightIndexTip.x, this.rightIndexTip.y, '#4CAF50', 'STRUM');
        }
    }

    drawChordWheel(ctx) {
        ctx.save();
        const cx = this.wheelCenterX;
        const cy = this.wheelCenterY;
        const rIn = this.wheelRadiusIn;
        const rOut = this.wheelRadiusOut;

        // Outer Glass Base Ring
        ctx.beginPath();
        ctx.arc(cx, cy, rOut + 10, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(25, 25, 25, 0.65)';
        ctx.fill();
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.12)';
        ctx.lineWidth = 2;
        ctx.stroke();

        // Draw 6 Chord Sectors
        const sliceAngle = (Math.PI * 2) / 6;
        const startOffset = -Math.PI / 2 - Math.PI / 6;

        for (let i = 0; i < this.chords.length; i++) {
            const chordName = this.chords[i];
            const aStart = startOffset + i * sliceAngle;
            const aEnd = aStart + sliceAngle;
            const isSelected = (chordName === this.activeChord);

            ctx.beginPath();
            ctx.arc(cx, cy, rOut, aStart, aEnd);
            ctx.arc(cx, cy, rIn, aEnd, aStart, true);
            ctx.closePath();

            if (isSelected) {
                ctx.fillStyle = 'rgba(76, 175, 80, 0.75)';
                ctx.shadowColor = '#4CAF50';
                ctx.shadowBlur = 20;
            } else {
                ctx.fillStyle = 'rgba(40, 40, 40, 0.55)';
                ctx.shadowBlur = 0;
            }
            ctx.fill();

            ctx.strokeStyle = isSelected ? '#4CAF50' : 'rgba(255, 255, 255, 0.15)';
            ctx.lineWidth = isSelected ? 3 : 1;
            ctx.stroke();

            // Label Text Position
            const midAngle = aStart + sliceAngle / 2;
            const textRadius = (rIn + rOut) / 2;
            const tx = cx + Math.cos(midAngle) * textRadius;
            const ty = cy + Math.sin(midAngle) * textRadius;

            ctx.save();
            ctx.shadowBlur = 0;
            ctx.font = isSelected ? 'bold 22px Outfit, sans-serif' : '600 18px Outfit, sans-serif';
            ctx.fillStyle = isSelected ? '#FFFFFF' : '#D0D0D0';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText(chordName, tx, ty);
            ctx.restore();
        }

        // Inner Circle Center Core
        ctx.beginPath();
        ctx.arc(cx, cy, rIn, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(15, 15, 15, 0.85)';
        ctx.shadowBlur = 0;
        ctx.fill();
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.2)';
        ctx.lineWidth = 2;
        ctx.stroke();

        // Active Chord Label in Center
        ctx.font = '800 24px Outfit, sans-serif';
        ctx.fillStyle = '#00C2FF';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(this.activeChord, cx, cy);

        ctx.restore();
    }

    drawVirtualStrings(ctx) {
        ctx.save();
        const yStart = this.stringsYStart;
        const yEnd = this.stringsYEnd;

        // Container Panel Background
        const boxX = this.stringsXStart - 30;
        const boxW = (this.stringsXEnd - this.stringsXStart) + 60;
        ctx.fillStyle = 'rgba(20, 20, 20, 0.40)';
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.08)';
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.roundRect(boxX, yStart - 20, boxW, (yEnd - yStart) + 40, 16);
        ctx.fill();
        ctx.stroke();

        // Draw 6 Vertical Guitar Strings
        for (let i = 0; i < this.numStrings; i++) {
            const x = this.stringXs[i];
            const pluck = this.stringPluckAnim[i];

            ctx.beginPath();
            ctx.moveTo(x, yStart);

            if (pluck > 0.01) {
                // Pluck Wave Distortion Animation
                const offset = Math.sin(pluck * Math.PI * 6) * 14 * pluck;
                const midY = (yStart + yEnd) / 2;
                ctx.quadraticCurveTo(x + offset, midY, x, yEnd);
                this.stringPluckAnim[i] *= 0.88; // Decay animation
            } else {
                ctx.lineTo(x, yEnd);
            }

            if (pluck > 0.05) {
                ctx.strokeStyle = '#4CAF50';
                ctx.lineWidth = 4;
                ctx.shadowColor = '#4CAF50';
                ctx.shadowBlur = 18;
            } else {
                ctx.strokeStyle = 'rgba(255, 255, 255, 0.65)';
                ctx.lineWidth = 2;
                ctx.shadowBlur = 0;
            }
            ctx.stroke();
        }

        ctx.restore();
    }

    drawGlowCursor(ctx, x, y, colorHex, label) {
        ctx.save();
        // Inner Dot
        ctx.beginPath();
        ctx.arc(x, y, 9, 0, Math.PI * 2);
        ctx.fillStyle = colorHex;
        ctx.shadowColor = colorHex;
        ctx.shadowBlur = 20;
        ctx.fill();

        // Outer Pulse Ring
        ctx.beginPath();
        ctx.arc(x, y, 18, 0, Math.PI * 2);
        ctx.strokeStyle = colorHex;
        ctx.lineWidth = 2;
        ctx.stroke();

        ctx.restore();
    }

    drawDebugLandmarks(landmarksList) {
        const ctx = this.ctx;
        ctx.save();
        ctx.fillStyle = 'rgba(255, 255, 255, 0.7)';
        for (const landmarks of landmarksList) {
            for (const lm of landmarks) {
                const x = (1.0 - lm.x) * this.WIDTH;
                const y = lm.y * this.HEIGHT;
                ctx.beginPath();
                ctx.arc(x, y, 3, 0, Math.PI * 2);
                ctx.fill();
            }
        }
        ctx.restore();
    }

    updateDashboardUI() {
        // Update DOM Indicators
        const fpsEl = document.getElementById('fps-val');
        if (fpsEl) fpsEl.textContent = Math.round(this.fps);

        const leftDot = document.getElementById('left-dot');
        const leftStatus = document.getElementById('left-status');
        if (leftDot && leftStatus) {
            if (this.leftHandTracked) {
                leftDot.className = 'indicator-dot active';
                leftStatus.textContent = 'Tracked';
            } else {
                leftDot.className = 'indicator-dot';
                leftStatus.textContent = 'Searching';
            }
        }

        const rightDot = document.getElementById('right-dot');
        const rightStatus = document.getElementById('right-status');
        if (rightDot && rightStatus) {
            if (this.rightHandTracked) {
                rightDot.className = 'indicator-dot active';
                rightStatus.textContent = 'Tracked';
            } else {
                rightDot.className = 'indicator-dot';
                rightStatus.textContent = 'Searching';
            }
        }

        const chordValEl = document.getElementById('chord-val');
        if (chordValEl && chordValEl.textContent !== this.activeChord) {
            chordValEl.textContent = this.activeChord;
            chordValEl.classList.add('pulse-chord');
            setTimeout(() => chordValEl.classList.remove('pulse-chord'), 150);
        }
    }
}

// Instantiate and boot engine when DOM loads
window.addEventListener('DOMContentLoaded', () => {
    window.airStrumApp = new AirStrumEngine();
    window.airStrumApp.startCamera();
});
