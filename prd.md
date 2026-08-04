# Product Requirements Document (PRD)

# Air Strum

**Version:** 1.0 MVP
**Platform:** Desktop (Python)
**Status:** Hobby Project
**Author:** AK

---

# 1. Overview

Air Strum is a webcam-powered virtual instrument that allows users to play beautiful guitar chords without owning a guitar.

Using only hand tracking, users select a chord from a floating radial menu with one hand and perform a natural strumming motion with the other to hear high-quality acoustic guitar recordings.

Air Strum is designed to feel playful, responsive, and visually satisfying rather than technically complex.

The experience should encourage anyone to create music within seconds.

---

# 2. Vision

> Make playing guitar as simple as pointing and strumming.

Air Strum is not a guitar simulator.

It is a digital musical instrument inspired by modern game interfaces and gesture-based interaction.

The emphasis is on:

* Beautiful sound
* Minimal interaction
* Instant feedback
* Zero learning curve

---

# 3. Problem Statement

Learning guitar requires:

* Expensive equipment
* Finger strength
* Practice
* Music theory

Many people simply want to experience creating music without spending months learning chords.

Air Strum removes the learning barrier while keeping the satisfying feeling of selecting chords and strumming.

---

# 4. Goals

### Primary Goals

* Create a fun musical experience
* Detect hands accurately
* Play realistic guitar sounds
* Maintain smooth performance (30–60 FPS)
* Require no keyboard interaction while playing

---

### Non Goals

Air Strum is NOT intended to:

* Teach proper guitar technique
* Replace a real guitar
* Simulate strings or frets
* Produce studio-quality recordings

---

# 5. Target Users

* Music lovers
* Beginners
* Hobbyists
* Developers
* Hackathon demos
* Interactive installations

---

# 6. Core Experience

The user launches Air Strum.

The webcam opens.

A radial chord wheel appears.

The user points at a chord.

The selected chord becomes active.

The user strums the air.

The application instantly plays a realistic guitar recording.

The interaction repeats naturally.

---

# 7. User Flow

```text
Launch App
      │
      ▼
Camera Starts
      │
      ▼
Hands Detected
      │
      ▼
Chord Wheel Appears
      │
      ▼
Point at Chord
      │
      ▼
Chord Selected
      │
      ▼
Air Strum Motion
      │
      ▼
Play Guitar Audio
      │
      ▼
Continue Playing
```

---

# 8. Functional Requirements

## Camera

* Access webcam
* Display live preview
* Detect one or two hands
* Mirror camera feed

---

## Hand Tracking

Track:

* Left hand
* Right hand
* Index fingertip
* Wrist position

Powered by MediaPipe Hands.

---

## Chord Wheel

Display a radial wheel containing six chords.

Example:

```
          C

      G       F

    Am         Em

         Dm
```

Requirements:

* Hover selection
* Visual highlight
* Smooth transitions
* Active chord indicator

---

## Chord Selection

Selecting a chord requires:

* Cursor enters slice
* Cursor remains for 250–300 ms

This prevents accidental selection.

---

## Strum Detection

The right hand controls playback.

Supported:

* Downstroke
* Upstroke

Detect:

* Motion direction
* Motion speed

Ignore:

* Small jitter
* Random movement

---

## Audio

Each chord contains:

```
Downstroke

Upstroke
```

Example:

```
C_down.wav

C_up.wav
```

Playback must begin within 50 ms after a detected strum.

---

## UI

Display:

* Webcam
* Chord wheel
* Current chord
* Detection status
* FPS (debug mode)

---

# 9. Interaction Design

## Left Hand

Purpose:

Select chord.

Interaction:

Move index finger over radial wheel.

Hover.

Chord selected.

---

## Right Hand

Purpose:

Play sound.

Interaction:

Move hand downward.

↓

Play downstroke.

Move upward.

↑

Play upstroke.

---

# 10. Visual Design

Style:

Minimal

Modern

Dark Theme

Glassmorphism

Soft shadows

Rounded elements

No unnecessary buttons.

Color palette:

Background

```
#111111
```

Accent

```
#00C2FF
```

Selected

```
#FFD54F
```

Success

```
#4CAF50
```

---

# 11. Audio Design

Requirements:

* Real acoustic guitar recordings
* High-quality WAV files
* Low latency
* Natural volume
* Clean decay

Future:

* Multiple sound packs
* Electric guitar
* Nylon
* Lo-fi

---

# 12. Performance Requirements

Startup:

< 3 seconds

Camera:

30–60 FPS

Gesture latency:

<100 ms

Audio latency:

<50 ms

Memory:

<300 MB

---

# 13. Folder Structure

```
AirStrum/

app.py

camera.py

tracker.py

wheel.py

gesture.py

audio.py

renderer.py

config.py

assets/

    audio/

        acoustic/

    fonts/

    icons/

README.md

requirements.txt
```

---

# 14. Technical Stack

| Component     | Technology          |
| ------------- | ------------------- |
| Language      | Python              |
| Camera        | OpenCV              |
| Hand Tracking | MediaPipe           |
| Audio         | pygame.mixer        |
| Math          | NumPy               |
| UI Rendering  | OpenCV Drawing APIs |

---

# 15. MVP Scope

Included:

* Webcam
* Hand tracking
* Radial chord wheel
* Hover selection
* Downstroke detection
* Upstroke detection
* Acoustic guitar playback

Excluded:

* Recording
* Song mode
* MIDI
* Multiple instruments
* Multiplayer
* AI-generated music

---

# 16. Success Metrics

The MVP is successful if:

* Users can start playing within 30 seconds.
* Chord selection accuracy exceeds 95%.
* Strum detection feels natural with minimal false triggers.
* Audio plays without noticeable delay.
* The application maintains at least 30 FPS on a typical laptop.
* The interface feels clean and enjoyable rather than like a computer vision demo.

---

# 17. Future Roadmap

### v1.1

* Multiple chord layouts
* Adjustable hover sensitivity
* Audio settings

### v1.2

* Song mode with guided chord progression
* Metronome
* Recording and playback

### v1.3

* Multiple guitar sound packs
* Capo support
* Chord progression recommendations

### v2.0

* Gesture customization
* Keyboard and MIDI support
* Multiplayer jam sessions
* Plugin architecture for new instruments

---

## Guiding Principle

> **Air Strum should feel less like software and more like picking up an instrument. Every interaction should be immediate, expressive, and rewarding, allowing users to focus on making music rather than learning controls.**
