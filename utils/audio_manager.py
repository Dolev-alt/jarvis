import threading
import time
import subprocess

class AudioManager:
    def __init__(self):
        self.is_speaking = False
        self._stop_event = threading.Event()
        self.last_utterance = ""
        self.last_speak_end = 0
        self._music_playing_cache = False
        self._music_check_time = 0
        self.last_raw_audio = None

    def start_speaking(self):
        self.is_speaking = True
        self._stop_event.clear()

    def stop_speaking(self):
        self._stop_event.set()
        self.is_speaking = False
        self.last_speak_end = time.time()

    def should_stop(self):
        return self._stop_event.is_set()

    def set_last_utterance(self, text):
        self.last_utterance = text.lower().strip()

    def is_music_playing(self):
        now = time.time()
        if now - self._music_check_time < 5:
            return self._music_playing_cache
        self._music_check_time = now
        try:
            r = subprocess.run(
                ["osascript", "-e", 'tell application "Music" to player state as string'],
                capture_output=True, text=True, timeout=3
            )
            self._music_playing_cache = r.stdout.strip() == "playing"
        except Exception:
            self._music_playing_cache = False
        return self._music_playing_cache

    def is_echo(self, text):
        elapsed = time.time() - self.last_speak_end
        if elapsed > 8:
            return False
        heard = text.lower().strip()
        last = self.last_utterance
        if not last:
            return False
        if heard == last or heard in last or last in heard:
            return True
        heard_words = set(heard.split())
        last_words = set(last.split())
        if not heard_words:
            return False
        overlap = len(heard_words & last_words) / len(heard_words)
        if overlap > 0.5:
            return True
        return False

audio_manager = AudioManager()