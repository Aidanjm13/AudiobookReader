"""
Local TTS functions using Kokoro and Piper.

Install:
    pip install kokoro soundfile          # for Kokoro
    pip install piper-tts                 # for Piper

Piper also needs a voice model (.onnx + .onnx.json), downloadable from:
    https://github.com/rhasspy/piper/blob/master/VOICES.md
e.g. en_US-lessac-medium.onnx
"""

import numpy as np


# ---------------------------------------------------------------------------
# Kokoro (82M, Apache 2.0) — GPU optional, runs fine on CPU
# ---------------------------------------------------------------------------

# lang_code -> language. Pass this into text_to_speech_kokoro(lang_code=...)
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

# A sample of available voices per language code. Naming pattern:
# {lang_code}{gender}_{name} — gender is 'f' or 'm'.
# Full list: https://huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md
KOKORO_VOICES = {
    "a": ["af_heart", "af_bella", "af_nicole", "am_adam", "am_michael"],
    "b": ["bf_emma", "bf_alice", "bm_george", "bm_daniel"],
    "j": ["jf_alpha", "jm_kumo"],
    "z": ["zf_xiaobei", "zm_yunxi"],
    # other languages have fewer/no built-in voices yet — check the repo above
}


KOKORO_SAMPLE_RATE = 24000  # Kokoro always outputs at 24kHz

# Reuse one pipeline instance across calls instead of reloading the model
# every time — significant speedup when cycling many chunks.
_kokoro_pipelines = {}


def _get_kokoro_pipeline(lang_code: str):
    from kokoro import KPipeline
    if lang_code not in _kokoro_pipelines:
        _kokoro_pipelines[lang_code] = KPipeline(lang_code=lang_code)
    return _kokoro_pipelines[lang_code]


def stream_speech_kokoro(text: str, voice: str = "af_heart", lang_code: str = "a"):
    """
    Convert text to speech using Kokoro, yielding audio chunks in memory
    (no disk I/O) as they're generated — one numpy float32 array per chunk,
    sampled at KOKORO_SAMPLE_RATE (24kHz).

    Kokoro splits long text into segments internally (sentences/clauses),
    so this yields progressively rather than waiting for the whole input.

    lang_code: key from KOKORO_LANGUAGES, e.g. 'a' (US English), 'b' (UK
               English), 'j' (Japanese), 'z' (Mandarin)
    voice: a voice name matching the chosen lang_code, see KOKORO_VOICES
           (e.g. 'af_heart', 'am_adam', 'bf_emma')

    Usage:
        for audio_chunk in stream_speech_kokoro("Hello world"):
            play(audio_chunk, KOKORO_SAMPLE_RATE)   # your playback function
    """
    pipeline = _get_kokoro_pipeline(lang_code)
    for _, _, audio in pipeline(text, voice=voice):
        yield audio  # numpy float32 array, no file written


# ---------------------------------------------------------------------------
# Piper (Apache 2.0) — CPU-friendly, very low latency
# ---------------------------------------------------------------------------

# Piper has 30+ languages, each with multiple speakers and quality tiers
# (x_low / low / medium / high). Every voice is its own separate download.
# Browse and pick a model file at:
#   https://github.com/rhasspy/piper/blob/master/VOICES.md
# or download directly via:
#   https://huggingface.co/rhasspy/piper-voices/tree/main
#
# Model filenames follow: {lang}-{speaker}-{quality}.onnx
# e.g. "en_US-lessac-medium.onnx", "en_GB-alan-medium.onnx",
#      "de_DE-thorsten-high.onnx", "es_ES-davefx-medium.onnx"
# Each .onnx file needs its matching .onnx.json config in the same folder.


# Reuse loaded voices across calls — loading the .onnx model is the slow
# part, so cache it per model_path instead of reloading every call.
_piper_voices = {}


def _get_piper_voice(model_path: str):
    from piper import PiperVoice
    if model_path not in _piper_voices:
        _piper_voices[model_path] = PiperVoice.load(model_path)
    return _piper_voices[model_path]


def stream_speech_piper(text: str, model_path: str):
    """
    Convert text to speech using Piper, yielding raw audio chunks in memory
    (no disk I/O) as they're generated — one numpy int16 array per chunk.

    model_path: path to a downloaded .onnx voice model for your chosen
                language/speaker/quality (its matching .onnx.json config
                must sit alongside it) — see VOICES.md link above

    Usage:
        voice = _get_piper_voice(model_path)  # to read voice.config.sample_rate
        for audio_chunk in stream_speech_piper("Hello world", model_path):
            play(audio_chunk, voice.config.sample_rate)  # your playback function
    """
    voice = _get_piper_voice(model_path)

    # synthesize_stream_raw yields raw 16-bit PCM bytes per chunk as it
    # generates, rather than waiting for the full utterance.
    for raw_bytes in voice.synthesize_stream_raw(text):
        yield np.frombuffer(raw_bytes, dtype=np.int16)



#main function to take in text and utilize current settings to determine which model to use
#FIX ME MAKE IT WORK WITH MORE THAN JUST ONE VOICE
def SynthesizeText(text):
    yield stream_speech_piper(text, "en_US-lessac-medium.onnx")