"""
Speaker Verification for JARVIS.
Lightweight voice-print enrollment and verification using MFCC embeddings.
No heavy dependencies (PyTorch etc.) — uses only numpy + scipy.
"""

import os
import numpy as np
import logging

_log = logging.getLogger("JARVIS_VOICE")

VOICE_PRINT_DIR = os.path.join(os.path.dirname(__file__), "..", "voice_prints")
OWNER_PRINT_FILE = os.path.join(VOICE_PRINT_DIR, "owner.npy")
VERIFY_THRESHOLD = float(os.getenv("JARVIS_VOICE_THRESHOLD", "0.78"))

_owner_embedding = None


def _ensure_dir():
    os.makedirs(VOICE_PRINT_DIR, exist_ok=True)


def _extract_mfcc(audio_np, sr=16000, n_mfcc=20):
    """Extract MFCC features from raw int16 audio."""
    audio = audio_np.astype(np.float64) / 32768.0

    if len(audio) < sr * 0.3:
        return None

    emphasized = np.append(audio[0], audio[1:] - 0.97 * audio[:-1])

    frame_size = int(0.025 * sr)
    frame_step = int(0.01 * sr)
    num_frames = max(1, (len(emphasized) - frame_size) // frame_step + 1)

    indices = np.arange(frame_size)[None, :] + np.arange(num_frames)[:, None] * frame_step
    indices = np.clip(indices, 0, len(emphasized) - 1)
    frames = emphasized[indices] * np.hamming(frame_size)

    nfft = 512
    mag = np.abs(np.fft.rfft(frames, nfft))
    pow_spec = (mag ** 2) / nfft

    n_filters = 40
    high_freq = sr / 2
    low_mel = 2595 * np.log10(1 + 0 / 700)
    high_mel = 2595 * np.log10(1 + high_freq / 700)
    mel_pts = np.linspace(low_mel, high_mel, n_filters + 2)
    hz_pts = 700 * (10 ** (mel_pts / 2595) - 1)
    bins = np.floor((nfft + 1) * hz_pts / sr).astype(int)

    fbank = np.zeros((n_filters, nfft // 2 + 1))
    for i in range(n_filters):
        left, center, right = bins[i], bins[i + 1], bins[i + 2]
        for j in range(left, center):
            fbank[i, j] = (j - left) / max(center - left, 1)
        for j in range(center, right):
            fbank[i, j] = (right - j) / max(right - center, 1)

    fb = np.dot(pow_spec, fbank.T)
    fb = np.where(fb == 0, np.finfo(float).eps, fb)
    fb = 20 * np.log10(fb)

    try:
        from scipy.fft import dct
    except ImportError:
        from numpy.fft import rfft
        N = fb.shape[1]
        n = np.arange(N)
        k = np.arange(n_mfcc)
        dct_matrix = np.cos(np.pi * k[:, None] * (2 * n + 1) / (2 * N))
        mfcc = np.dot(fb, dct_matrix.T)
        mfcc -= np.mean(mfcc, axis=0)
        return mfcc

    mfcc = dct(fb, type=2, axis=1, norm='ortho')[:, :n_mfcc]
    mfcc -= np.mean(mfcc, axis=0)
    return mfcc


def _get_embedding(audio_np, sr=16000):
    """Compute a fixed-size speaker embedding from raw int16 audio."""
    mfcc = _extract_mfcc(audio_np, sr)
    if mfcc is None or len(mfcc) < 5:
        return None
    mean = np.mean(mfcc, axis=0)
    std = np.std(mfcc, axis=0)
    delta = np.mean(np.diff(mfcc, axis=0), axis=0) if len(mfcc) > 1 else np.zeros_like(mean)
    return np.concatenate([mean, std, delta])


def _cosine_sim(a, b):
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-10))


def is_enrolled() -> bool:
    """Check if an owner voice print exists on disk."""
    return os.path.exists(OWNER_PRINT_FILE)


def load_owner_print():
    """Load the stored owner voice print into memory."""
    global _owner_embedding
    if os.path.exists(OWNER_PRINT_FILE):
        try:
            _owner_embedding = np.load(OWNER_PRINT_FILE)
            _log.info("Owner voice print loaded from disk.")
            return True
        except Exception as e:
            _log.error(f"Failed to load voice print: {e}")
    return False


def enroll(audio_samples: list, sr=16000) -> bool:
    """
    Enroll the owner's voice from one or more raw int16 numpy arrays.
    Averages embeddings from multiple samples for robustness.
    """
    _ensure_dir()
    global _owner_embedding

    embeddings = []
    for sample in audio_samples:
        emb = _get_embedding(sample, sr)
        if emb is not None:
            embeddings.append(emb)

    if not embeddings:
        _log.warning("Enrollment failed — no valid audio samples.")
        return False

    _owner_embedding = np.mean(embeddings, axis=0)
    np.save(OWNER_PRINT_FILE, _owner_embedding)
    _log.info(f"Owner voice enrolled ({len(embeddings)} sample(s)). Saved to {OWNER_PRINT_FILE}")
    return True


def verify(audio_np, sr=16000) -> tuple:
    """
    Verify if the speaker matches the enrolled owner.
    Returns: (is_owner: bool, confidence: float)
    """
    global _owner_embedding

    if _owner_embedding is None:
        if not load_owner_print():
            return True, 1.0

    emb = _get_embedding(audio_np, sr)
    if emb is None:
        return False, 0.0

    similarity = _cosine_sim(_owner_embedding, emb)
    is_match = similarity >= VERIFY_THRESHOLD
    _log.info(f"Voice verification: similarity={similarity:.3f}, threshold={VERIFY_THRESHOLD}, match={is_match}")
    return is_match, similarity


load_owner_print()
