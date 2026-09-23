"""
Local TTS functions using Kokoro and Piper.

Install:
    pip install kokoro soundfile          # for Kokoro
    pip install piper-tts                 # for Piper

Piper also needs a voice model (.onnx + .onnx.json), downloadable from:
    https://github.com/rhasspy/piper/blob/master/VOICES.md
e.g. en_US-lessac-medium.onnx
"""

import io
import os
import urllib.request
import wave
from pathlib import Path
import numpy as np
from fileHandling import getAppdataFolderPath
from piperVoices import parsePiperVoiceString

TARGET_SAMPLE_RATE = 48000  # Default standard output sample rate
TARGET_CHANNELS = 2

def set_audio_format(sample_rate: int, channels: int):
    """Call this on app startup to match the active audio device."""
    global TARGET_SAMPLE_RATE, TARGET_CHANNELS
    TARGET_SAMPLE_RATE = sample_rate
    TARGET_CHANNELS = channels

# ---------------------------------------------------------------------------
# Kokoro (82M, Apache 2.0) — GPU optional, runs fine on CPU
# ---------------------------------------------------------------------------

KOKORO_LANGUAGES = {
    "a": "American English",
    "b": "British English",
    "e": "Spanish",
    "f": "French",
    "h": "Hindi",
    "i": "Italian",
    "j": "Japanese",       # requires: pip install misaki[ja]
    "p": "Brazilian Portuguese",
    "z": "Mandarin Chinese",  # requires: pip install misaki[zh]
}

KOKORO_VOICES = {
    "a": ["af_heart", "af_bella", "af_nicole", "am_adam", "am_michael"],
    "b": ["bf_emma", "bf_alice", "bm_george", "bm_daniel"],
    "j": ["jf_alpha", "jm_kumo"],
    "z": ["zf_xiaobei", "zm_yunxi"],
}

KOKORO_SAMPLE_RATE = 48000
_kokoro_pipelines = {}


def _get_kokoro_pipeline(lang_code: str):
    from kokoro import KPipeline
    if lang_code not in _kokoro_pipelines:
        _kokoro_pipelines[lang_code] = KPipeline(lang_code=lang_code)
    return _kokoro_pipelines[lang_code]


def stream_speech_kokoro(text: str, voice: str = "af_heart", lang_code: str = "a", speed: float = 1.0):
    pipeline = _get_kokoro_pipeline(lang_code)
    # Pass speed directly to Kokoro's pipeline
    for _, _, audio in pipeline(text, voice=voice, speed=speed):
        yield audio


def synthesize_kokoro(text: str, voice: str = "af_heart", lang_code: str = "a", speed: float = 1.0) -> bytes:
    chunks = list(stream_speech_kokoro(text, voice=voice, lang_code=lang_code, speed=speed))
    if not chunks:
        return b""
    audio = np.concatenate(chunks)
    audio = _resample_float(audio, KOKORO_SAMPLE_RATE, TARGET_SAMPLE_RATE)
    return _float_to_int16_bytes(audio)


# ---------------------------------------------------------------------------
# Piper (Apache 2.0) — CPU-friendly, very low latency
# ---------------------------------------------------------------------------

_piper_voices = {}

VOICES_DIR = os.path.join(getAppdataFolderPath(), "voices")
PIPER_BASE_URL = "https://huggingface.co/rhasspy/piper-voices/resolve/main"


def ensure_piper_voice(lang: str, region: str, speaker: str, quality: str) -> str:
    if not os.path.exists(VOICES_DIR):
        os.makedirs(VOICES_DIR, exist_ok=True)

    voice_code = f"{lang}_{region}"
    name = f"{voice_code}-{speaker}-{quality}"
    onnx_path = os.path.join(VOICES_DIR, f"{name}.onnx")
    json_path = os.path.join(VOICES_DIR, f"{name}.onnx.json")

    # Correct path structure on Hugging Face: /main/en/en_US/lessac/medium/
    remote_dir = f"{PIPER_BASE_URL}/{lang}/{voice_code}/{speaker}/{quality}"

    for local_path, remote_name in [(onnx_path, f"{name}.onnx"), (json_path, f"{name}.onnx.json")]:
        if not os.path.exists(local_path):
            url = f"{remote_dir}/{remote_name}"
            print(f"Downloading {remote_name} from {url}...")
            urllib.request.urlretrieve(url, local_path)

    return str(onnx_path)


def _get_piper_voice(model_path: str):
    from piper import PiperVoice
    if model_path not in _piper_voices:
        _piper_voices[model_path] = PiperVoice.load(model_path)
    return _piper_voices[model_path]


def stream_speech_piper(text: str, model_path: str, speed: float = 1.0):
    voice = _get_piper_voice(model_path)
    
    # Piper uses length_scale where values < 1.0 make speech faster. 
    # Example: 1.25 speed slider = 1 / 1.25 = 0.8 length_scale
    length_scale = 1.0 / speed if speed > 0 else 1.0

    voice.config.length_scale = length_scale
    
    for chunk in voice.synthesize(text):
        if hasattr(chunk, "audio_int16_array") and chunk.audio_int16_array is not None:
            yield chunk.audio_int16_array
        elif hasattr(chunk, "audio_int16_bytes") and chunk.audio_int16_bytes:
            yield np.frombuffer(chunk.audio_int16_bytes, dtype=np.int16)
        elif isinstance(chunk, np.ndarray):
            yield chunk.astype(np.int16)
        elif isinstance(chunk, (bytes, bytearray)) and len(chunk) > 0:
            yield np.frombuffer(chunk, dtype=np.int16)


def synthesize_piper(text: str, model_path: str, speed: float = 1.0) -> bytes:
    voice = _get_piper_voice(model_path)
    chunks = list(stream_speech_piper(text, model_path, speed=speed))
    if not chunks:
        return b""
    audio = np.concatenate(chunks).astype(np.float32) / 32768.0
    audio = _resample_float(audio, voice.config.sample_rate, TARGET_SAMPLE_RATE)
    return _float_to_int16_bytes(audio)

# ---------------------------------------------------------------------------
# Helpers & Interface
# ---------------------------------------------------------------------------

def _resample_float(audio: np.ndarray, in_rate: int, out_rate: int) -> np.ndarray:
    if in_rate == out_rate or len(audio) == 0:
        return audio
    n_out = int(len(audio) * out_rate / in_rate)
    return np.interp(
        np.linspace(0, len(audio) - 1, n_out),
        np.arange(len(audio)),
        audio,
    )


def _float_to_int16_bytes(audio: np.ndarray, channels: int = None) -> bytes:
    if channels is None:
        channels = TARGET_CHANNELS
        
    audio = np.clip(audio, -1.0, 1.0)
    pcm16 = (audio * 32767).astype(np.int16)
    
    if channels == 2:
        # Duplicate mono signal into stereo (interleaved L, R, L, R)
        stereo = np.column_stack((pcm16, pcm16))
        return stereo.tobytes()
        
    return pcm16.tobytes()

#kokoro model : languageCode_voiceModel
#piper model : language_region_name_pitch
_ENGINE_CONFIG = {
    "engine": "piper",
    "model": "en_US-lessac-medium", #separate parts of model by underscores to be split
    "speed": 1.0  # Added speed variable to global state
}

def set_active_engine(engine: str, **kwargs):
    _ENGINE_CONFIG["engine"] = engine
    _ENGINE_CONFIG.update(kwargs)


def SynthesizeText(text: str) -> bytes:
    speed = _ENGINE_CONFIG.get("speed", 1.0)
    
    if _ENGINE_CONFIG.get("engine", "piper") == "kokoro":
        modelParts = _ENGINE_CONFIG.get("model", "af_heart").split("_")
        return synthesize_kokoro(
            text,
            voice=modelParts[1],
            lang_code=modelParts[0],
            speed=speed
        )
    else:
        lang, region, speaker, quality = parsePiperVoiceString(_ENGINE_CONFIG.get("model", "en_US-lessac-medium"))
        piper_model_path = ensure_piper_voice(lang, region, speaker, quality)
        _ENGINE_CONFIG["piper_model_path"] = piper_model_path
        return synthesize_piper(text, _ENGINE_CONFIG["piper_model_path"], speed=speed)