import contextlib
import threading
import winsound

try:
    import pyttsx3

    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False


class TTSEngine:
    def __init__(self):
        self.tts_available = False
        if PYTTSX3_AVAILABLE:
            try:
                self.engine = pyttsx3.init()
                # Set speaking speed (170 words per minute is optimal for visually impaired users)
                self.engine.setProperty("rate", 170)
                self.tts_available = True
                print("[INFO] pyttsx3 TTS Engine initialized successfully.")
            except Exception as e:
                print(
                    f"[WARNING] Local TTS engine initialization failed: {e}. Falling back to text-log and Beep."
                )
                self.engine = None
        else:
            print("[WARNING] pyttsx3 library not found. Falling back to text-log and Beep.")
            self.engine = None

        self.current_thread = None

    def speak(self, text, is_danger=False, volume=1.0):
        """
        Speak the guidance text out loud.
        Uses threading to prevent blocking the main loop (meeting latency requirements).
        """
        # Log to terminal immediately
        print(f'\n[TTS VOICE OUTPUT]: "{text}" (Volume: {volume*100:.0f}%)')

        # Immediate warning tone if high danger (Proposed Feature 1 & 2)
        if is_danger:
            # High pitch, short beep for immediate physical stopping cue
            threading.Thread(target=lambda: winsound.Beep(1200, 150), daemon=True).start()

        if self.tts_available and self.engine:
            # Set volume dynamically based on noise sensor
            self.engine.setProperty("volume", volume)

            # Start speech in a separate thread so it doesn't block the 500ms loop
            # Note: pyttsx3 runAndWait needs careful threading
            def speech_worker():
                with contextlib.suppress(Exception):
                    self.engine.say(text)
                    self.engine.runAndWait()

            if self.current_thread and self.current_thread.is_alive():
                # Simulating audio interrupt (Proposed Feature 2)
                # In pyttsx3 we stop the engine and re-speak
                with contextlib.suppress(Exception):
                    self.engine.stop()

            self.current_thread = threading.Thread(target=speech_worker, daemon=True)
            self.current_thread.start()
        else:
            # Simple text log fallback
            pass

    def stop(self):
        """
        Stop any active speech (for urgent interrupts)
        """
        if self.tts_available and self.engine:
            with contextlib.suppress(Exception):
                self.engine.stop()
