"""
Air Strum — Audio Engine Module
Handles low-latency WAV playback using a real-time polyphonic callback mixer.
Includes a Karplus-Strong physical modeling synthesizer fallback for missing assets.
"""

import os
import wave
import time
import threading
import numpy as np
import sounddevice as sd
from typing import Dict, Tuple, Optional, List
import config

class AudioEngine:
    """
    Manages low-latency audio loading and playback using a real-time callback mixer.
    Automatically generates synthetic acoustic chords and string plucks if WAV assets are missing.
    """
    def __init__(self):
        self.sample_rate = config.AUDIO_SAMPLE_RATE
        self.sounds: Dict[str, Dict[str, np.ndarray]] = {}
        self.string_sounds: Dict[str, List[np.ndarray]] = {}
        self.synth_mode_active = False
        
        # Mixer state for polyphonic playback
        self.lock = threading.Lock()
        self.active_sounds: List[Dict] = []
        
        # Start sounddevice OutputStream for real-time mixing
        try:
            self.stream = sd.OutputStream(
                samplerate=self.sample_rate,
                channels=2,
                callback=self._audio_callback,
                blocksize=256  # Low latency block size
            )
            self.stream.start()
            print("[AudioEngine] Real-time mixer stream started successfully.")
        except Exception as e:
            print(f"[AudioEngine] Failed to start OutputStream mixer: {e}. Falling back to standard playback.")
            self.stream = None
        
        # Ensure directories exist
        os.makedirs(config.AUDIO_ASSET_DIR, exist_ok=True)
        
        # Check and load assets
        self._initialize_audio_assets()

    def _audio_callback(self, outdata: np.ndarray, frames: int, time_info, status) -> None:
        """Mixes all active playing sound buffers into the output stream."""
        if status:
            print(f"[AudioEngine] Stream status: {status}")
            
        # Initialize output buffer to silence (zeros)
        outdata.fill(0.0)
        
        with self.lock:
            remaining_sounds = []
            for sound in self.active_sounds:
                data = sound["data"]
                ptr = sound["pointer"]
                
                # Calculate how many frames can be copied
                chunk_len = min(frames, len(data) - ptr)
                if chunk_len > 0:
                    outdata[:chunk_len] += data[ptr : ptr + chunk_len]
                    sound["pointer"] += chunk_len
                    
                # If the sound has not finished playing, keep it
                if sound["pointer"] < len(data):
                    remaining_sounds.append(sound)
                    
            self.active_sounds = remaining_sounds

    def _initialize_audio_assets(self) -> None:
        """Checks for WAV files, generates them if missing, and loads them into memory."""
        missing_any = False
        
        # Check chord strums
        for chord in config.CHORD_LIST:
            for direction in ["down", "up"]:
                filename = f"{chord}_{direction}.wav"
                filepath = os.path.join(config.AUDIO_ASSET_DIR, filename)
                if not os.path.exists(filepath):
                    missing_any = True
                    break
            if missing_any:
                break
                
        # Check individual strings
        if not missing_any:
            for chord in config.CHORD_LIST:
                for idx in range(config.NUM_STRINGS):
                    filename = f"{chord}_string_{idx}.wav"
                    filepath = os.path.join(config.AUDIO_ASSET_DIR, filename)
                    if not os.path.exists(filepath):
                        missing_any = True
                        break
                if missing_any:
                    break
        
        if missing_any:
            print("[AudioEngine] Some or all audio assets are missing. Synthesizing default pack...")
            self.synth_mode_active = True
            t_start = time.time()
            self._generate_default_audio_pack()
            print(f"[AudioEngine] Synthesis completed in {time.time() - t_start:.2f} seconds.")
            
        # Load all WAV files into memory
        print("[AudioEngine] Loading audio assets into RAM...")
        for chord in config.CHORD_LIST:
            self.sounds[chord] = {}
            for direction in ["down", "up"]:
                filename = f"{chord}_{direction}.wav"
                filepath = os.path.normpath(os.path.join(config.AUDIO_ASSET_DIR, filename))
                
                try:
                    data, rate = self._load_wav(filepath)
                    self.sounds[chord][direction] = data
                except Exception as e:
                    print(f"[AudioEngine] Failed to load {filename}: {e}")
                    # Create an empty silent buffer as fallback to prevent crashes
                    self.sounds[chord][direction] = np.zeros((44100, 2), dtype=np.float32)
                    
            self.string_sounds[chord] = []
            for idx in range(config.NUM_STRINGS):
                filename = f"{chord}_string_{idx}.wav"
                filepath = os.path.normpath(os.path.join(config.AUDIO_ASSET_DIR, filename))
                
                try:
                    data, rate = self._load_wav(filepath)
                    self.string_sounds[chord].append(data)
                except Exception as e:
                    print(f"[AudioEngine] Failed to load {filename}: {e}")
                    self.string_sounds[chord].append(np.zeros((44100, 2), dtype=np.float32))
                    
        print("[AudioEngine] Audio Engine ready.")

    def play(self, chord: str, direction: str) -> None:
        """Plays the specified chord and direction asynchronously with low latency."""
        if chord not in self.sounds or direction not in self.sounds[chord]:
            print(f"[AudioEngine] Error: Sound not found for {chord} ({direction})")
            return
            
        sound_data = self.sounds[chord][direction]
        self.play_buffer(sound_data)

    def play_string(self, chord: str, string_idx: int) -> None:
        """Plays the specified individual string note asynchronously."""
        if chord not in self.string_sounds or string_idx >= len(self.string_sounds[chord]):
            print(f"[AudioEngine] Error: String sound not found for {chord} (string {string_idx})")
            return
            
        sound_data = self.string_sounds[chord][string_idx]
        self.play_buffer(sound_data)

    def play_buffer(self, sound_data: np.ndarray) -> None:
        """Enqueues a sound buffer into the active mixer channels."""
        if self.stream is None:
            # Fallback if stream failed to open: play directly (blocks previous)
            try:
                sd.play(sound_data, self.sample_rate)
            except Exception as e:
                print(f"[AudioEngine] Playback error: {e}")
            return
            
        with self.lock:
            self.active_sounds.append({"data": sound_data, "pointer": 0})

    def _load_wav(self, filepath: str) -> Tuple[np.ndarray, int]:
        """Loads a WAV file and converts it to a stereo float32 NumPy array."""
        with wave.open(filepath, 'rb') as wf:
            nchannels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            framerate = wf.getframerate()
            nframes = wf.getnframes()
            
            raw_bytes = wf.readframes(nframes)
            
            # Decode based on bit depth
            if sampwidth == 2:
                data = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32) / 32768.0
            elif sampwidth == 1:
                data = (np.frombuffer(raw_bytes, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
            elif sampwidth == 3:
                # Handle 24-bit manual decoding
                raw_ints = np.frombuffer(raw_bytes, dtype=np.uint8)
                reshaped = raw_ints.reshape(-1, 3)
                # Pad to 32-bit little endian
                padded = np.column_stack((np.zeros(len(reshaped), dtype=np.uint8), reshaped))
                data = padded.view(dtype=np.int32).flatten().astype(np.float32) / 2147483648.0
            elif sampwidth == 4:
                data = np.frombuffer(raw_bytes, dtype=np.int32).astype(np.float32) / 2147483648.0
            else:
                raise ValueError(f"Unsupported sample width: {sampwidth}")
            
            # Reshape to stereo
            if nchannels > 1:
                data = data.reshape(-1, nchannels)
            else:
                # Convert mono to stereo
                data = np.column_stack((data, data))
                
            return data, framerate

    def _generate_default_audio_pack(self) -> None:
        """Generates WAV files using Karplus-Strong physical string modeling."""
        duration = 2.0  # 2.0 seconds decay per chord
        
        # 1. Synthesize Chord Strums
        for chord, freqs in config.CHORD_TUNINGS.items():
            for direction in ["down", "up"]:
                filename = f"{chord}_{direction}.wav"
                filepath = os.path.join(config.AUDIO_ASSET_DIR, filename)
                
                if not os.path.exists(filepath):
                    if direction == "down":
                        chord_audio = self._synthesize_chord(freqs, duration, is_downstroke=True)
                    else:
                        chord_audio = self._synthesize_chord(freqs, duration, is_downstroke=False)
                    
                    self._save_wav(filepath, chord_audio)
                    print(f"[AudioEngine] Synthesized and saved: {filename}")
                    
        # 2. Synthesize Individual Strings
        for chord, freqs in config.CHORD_TUNINGS.items():
            for idx, freq in enumerate(freqs):
                filename = f"{chord}_string_{idx}.wav"
                filepath = os.path.join(config.AUDIO_ASSET_DIR, filename)
                
                if not os.path.exists(filepath):
                    # Slightly adjust decay to give higher strings a faster decay (natural physics)
                    decay_factor = 0.995 + (0.001 * (idx / len(freqs)))
                    if decay_factor > 0.998:
                        decay_factor = 0.998
                        
                    string_audio = self._synthesize_string(freq, duration, decay=decay_factor)
                    
                    # Normalize peak to 0.80 to leave headroom for mixing multiple strings
                    max_val = np.max(np.abs(string_audio))
                    if max_val > 0.0:
                        string_audio = string_audio / max_val * 0.80
                        
                    self._save_wav(filepath, string_audio)
                    print(f"[AudioEngine] Synthesized and saved string: {filename}")

    def _synthesize_string(self, frequency: float, duration: float, decay: float = 0.996) -> np.ndarray:
        """Synthesizes a single string pluck using Karplus-Strong."""
        num_samples = int(duration * self.sample_rate)
        # Delay line size (period of the frequency)
        n = int(self.sample_rate / frequency)
        
        # White noise pluck
        x = np.random.uniform(-1.0, 1.0, n)
        
        # Simple low-pass filter to warm up the pluck (attenuate harsh digital clicks)
        x = np.convolve(x, [0.5, 0.5], mode='same')
        
        # Generate the pluck samples
        out = np.zeros(num_samples, dtype=np.float32)
        out[:n] = x
        
        # Main Karplus-Strong feedforward loop
        for i in range(n, num_samples):
            # Average current and next sample to filter, damp with decay feedback
            out[i] = 0.5 * (out[i - n] + out[i - n + 1]) * decay
            
        # Add a smooth fade-out at the end to prevent clicking
        fade_len = int(self.sample_rate * 0.15)
        if fade_len < num_samples:
            fade_curve = np.linspace(1.0, 0.0, fade_len)
            out[-fade_len:] *= fade_curve
            
        return out

    def _synthesize_chord(self, freqs: list, duration: float, is_downstroke: bool) -> np.ndarray:
        """Mixes individual plucked strings with strum delays to construct a full chord."""
        # 35ms delay between string plucks for downstroke, 25ms for upstroke
        string_delay = 0.035 if is_downstroke else 0.025
        total_duration = duration + (len(freqs) * string_delay)
        total_samples = int(total_duration * self.sample_rate)
        
        chord_audio = np.zeros(total_samples, dtype=np.float32)
        
        # Downstroke = low to high frequencies
        # Upstroke = high to low frequencies
        chord_freqs = freqs if is_downstroke else list(reversed(freqs))
        
        for idx, freq in enumerate(chord_freqs):
            # Slightly adjust decay to give higher strings a faster decay (natural physics)
            decay_factor = 0.995 + (0.001 * (idx / len(chord_freqs)))
            if decay_factor > 0.998:
                decay_factor = 0.998
                
            string_wav = self._synthesize_string(freq, duration, decay=decay_factor)
            
            # Calculate start sample based on strum delay
            start_sample = int(idx * string_delay * self.sample_rate)
            
            # Gain adjustment: lower strings pack more power, upstrokes are lighter
            gain = 0.70 if is_downstroke else 0.50
            # Apply slight volume variance across strings
            gain *= (0.96 ** idx)
            
            chord_audio[start_sample : start_sample + len(string_wav)] += string_wav * gain
            
        # Peak normalization to prevent clipping
        max_val = np.max(np.abs(chord_audio))
        if max_val > 0.0:
            target_peak = 0.85 if is_downstroke else 0.75
            chord_audio = chord_audio / max_val * target_peak
            
        return chord_audio

    def _save_wav(self, filepath: str, data: np.ndarray) -> None:
        """Saves a float32 mono array to a 16-bit PCM stereo WAV file."""
        # Convert float32 [-1.0, 1.0] to 16-bit signed PCM
        pcm_data = (data * 32767.0).astype(np.int16)
        
        # Duplicate to stereo channels
        stereo_pcm = np.column_stack((pcm_data, pcm_data))
        
        with wave.open(filepath, 'wb') as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)  # 2 bytes = 16 bit
            wf.setframerate(self.sample_rate)
            wf.writeframes(stereo_pcm.tobytes())
            
    def shutdown(self) -> None:
        """Stop any playing audio and close the stream."""
        if self.stream is not None:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception as e:
                print(f"[AudioEngine] Stream shutdown error: {e}")
        sd.stop()
