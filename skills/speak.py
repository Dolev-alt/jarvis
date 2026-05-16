import asyncio
import edge_tts
import os
import io
import time
import threading
from speech_formatter import format_for_speech
from utils.audio_manager import audio_manager

speech_lock = threading.Lock()

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "").strip()
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "pNInz6obpgDQGcFmaJgB").strip()  # "Adam" — deep British male

HAS_PYGAME = False
try:
    import pygame
    if not pygame.mixer.get_init():
        pygame.mixer.init(frequency=24000)
    import numpy as np
    HAS_PYGAME = True
except ImportError:
    print("[SPEECH] Pygame not found. HUD Pulse mapping disabled. Using pyttsx3 fallback.")


def get_rms(audio_data):
    """Calculate Root Mean Square (volume level) of audio data."""
    if not HAS_PYGAME or len(audio_data) == 0:
        return 0
    return np.sqrt(np.mean(audio_data.astype(float)**2))


def _speak_elevenlabs(clean_text: str):
    """Generate speech via ElevenLabs API. Returns BytesIO buffer or None on failure."""
    if not ELEVENLABS_API_KEY:
        return None
    try:
        import requests
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}/stream"
        headers = {"xi-api-key": ELEVENLABS_API_KEY, "Content-Type": "application/json"}
        payload = {
            "text": clean_text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75, "style": 0.4},
        }
        resp = requests.post(url, json=payload, headers=headers, stream=True, timeout=15)
        if resp.status_code != 200:
            print(f"[SPEECH] ElevenLabs returned {resp.status_code}. Falling back.")
            return None
        buf = io.BytesIO()
        for chunk in resp.iter_content(chunk_size=4096):
            buf.write(chunk)
        buf.seek(0)
        return buf if buf.getbuffer().nbytes > 0 else None
    except Exception as e:
        print(f"[SPEECH] ElevenLabs failed: {e}. Falling back.")
        return None


def _split_sentences(text):
    """Split text into sentences for pipelined TTS."""
    import re as _re
    parts = _re.split(r'(?<=[.!?])\s+', text)
    return [p.strip() for p in parts if p.strip()]


async def _generate_edge_audio(text, voice):
    """Generate Edge-TTS audio into a BytesIO buffer (no disk I/O)."""
    buf = io.BytesIO()
    communicate = edge_tts.Communicate(text, voice)
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            buf.write(chunk["data"])
    buf.seek(0)
    return buf if buf.getbuffer().nbytes > 0 else None


def _play_sound_buf(buf, socketio=None):
    """Play a pygame Sound from a BytesIO buffer with HUD viz. Returns when done."""
    try:
        sound = pygame.mixer.Sound(buf)
    except Exception:
        return False

    samples = None
    try:
        samples = pygame.sndarray.array(sound)
    except Exception:
        pass

    channel = sound.play()
    duration = sound.get_length()

    if samples is not None and socketio:
        num_samples = len(samples)
        chunk_size = max(1, int(num_samples * (0.05 / max(duration, 0.01))))
        for i in range(0, num_samples, chunk_size):
            if audio_manager.should_stop() or not channel.get_busy():
                break
            chunk = samples[i : i + chunk_size]
            level = get_rms(chunk)
            norm_level = min(100, (level / 1500) * 100)
            socketio.emit("voice_level", {"level": norm_level})
            time.sleep(0.05)
    else:
        while channel.get_busy() and not audio_manager.should_stop():
            time.sleep(0.08)

    if audio_manager.should_stop():
        pygame.mixer.stop()
    return True


async def _speak_edge_tts_streaming(clean_text: str, socketio=None, voice="en-GB-RyanNeural") -> bool:
    """Edge-TTS with sentence-level pipelining: first sentence plays while next generates."""
    if not HAS_PYGAME:
        return False

    try:
        sentences = _split_sentences(clean_text)
        if len(sentences) <= 1:
            sentences = [clean_text]

        audio_manager.start_speaking()

        if len(sentences) == 1:
            buf = await _generate_edge_audio(sentences[0], voice)
            if buf:
                _play_sound_buf(buf, socketio)
            audio_manager.stop_speaking()
            return buf is not None

        next_buf_task = asyncio.ensure_future(_generate_edge_audio(sentences[0], voice))

        for i, sentence in enumerate(sentences):
            if audio_manager.should_stop():
                next_buf_task.cancel()
                break

            buf = await next_buf_task
            if buf is None:
                if i + 1 < len(sentences):
                    next_buf_task = asyncio.ensure_future(_generate_edge_audio(sentences[i + 1], voice))
                continue

            if i + 1 < len(sentences):
                next_buf_task = asyncio.ensure_future(_generate_edge_audio(sentences[i + 1], voice))

            _play_sound_buf(buf, socketio)

        audio_manager.stop_speaking()
        return True
    except Exception as e:
        print(f"[SPEECH] Edge-TTS streaming failed: {e}")
        audio_manager.stop_speaking()
        return False


def _play_mp3_with_viz(filepath: str, socketio=None):
    """Play an mp3 file with HUD visualisation if available."""
    if not HAS_PYGAME:
        return
    try:
        sound = pygame.mixer.Sound(filepath)
        samples = None
        try:
            samples = pygame.sndarray.array(sound)
        except Exception:
            pass

        audio_manager.start_speaking()
        channel = sound.play()
        duration = sound.get_length()

        if samples is not None and socketio:
            num_samples = len(samples)
            chunk_size = max(1, int(num_samples * (0.05 / duration)))
            for i in range(0, num_samples, chunk_size):
                if audio_manager.should_stop() or not channel.get_busy():
                    break
                chunk = samples[i : i + chunk_size]
                level = get_rms(chunk)
                norm_level = min(100, (level / 1500) * 100)
                socketio.emit("voice_level", {"level": norm_level})
                time.sleep(0.05)
        else:
            while channel.get_busy() and not audio_manager.should_stop():
                time.sleep(0.1)

        if audio_manager.should_stop():
            pygame.mixer.stop()

        audio_manager.stop_speaking()
    finally:
        try:
            os.remove(filepath)
        except Exception:
            pass


async def generate_and_play(text, socketio=None, voice="en-GB-RyanNeural"):
    """Cascading TTS: ElevenLabs -> Edge-TTS -> pyttsx3 offline."""
    clean_text = format_for_speech(text)
    if not clean_text:
        return

    eleven_buf = _speak_elevenlabs(clean_text)
    if eleven_buf and HAS_PYGAME:
        audio_manager.start_speaking()
        _play_sound_buf(eleven_buf, socketio)
        audio_manager.stop_speaking()
        return

    if await _speak_edge_tts_streaming(clean_text, socketio, voice):
        return

    # Tier 3: pyttsx3 offline fallback
    try:
        import pyttsx3

        def run_offline():
            with speech_lock:
                audio_manager.start_speaking()
                engine = pyttsx3.init()
                engine.setProperty("rate", 175)
                engine.setProperty("volume", 1.0)
                engine.say(clean_text)
                engine.runAndWait()
                audio_manager.stop_speaking()

        threading.Thread(target=run_offline, daemon=True).start()
    except Exception as e:
        print(f"[SPEECH] All TTS engines failed: {e}")
        audio_manager.stop_speaking()


JARVIS_VOICE = "en-GB-RyanNeural"


def execute(params):
    """The entry point called by the ExecutorAgent."""
    text = params.get("text", "")
    socketio = params.get("_socketio")

    if text:
        print(f"[JARVIS] {text}")
        audio_manager.set_last_utterance(text)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(generate_and_play(text, socketio, JARVIS_VOICE))
        finally:
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            if pending:
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            loop.close()
    return f"Speaking: {text}"
