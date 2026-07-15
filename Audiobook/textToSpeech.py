from pathlib import Path
from piper import PiperVoice
from piper.config import SynthesisConfig
from piper.download_voices import download_voice
import numpy as np, sounddevice as sd

voiceType = "en_GB-alan-medium"
download_voice(voiceType, Path("voices/"))

speed = 1.0
voice = PiperVoice.load(f"voices/{voiceType}.onnx", config_path=f"voices/{voiceType}.onnx.json")

cfg = SynthesisConfig(length_scale=speed)
chunks = [np.frombuffer(c.audio_int16_bytes, dtype=np.int16) for c in voice.synthesize("Hello there my name is Aidan.", syn_config=cfg)]
audio = np.concatenate(chunks)
sd.play(audio, samplerate=voice.config.sample_rate)
sd.wait()