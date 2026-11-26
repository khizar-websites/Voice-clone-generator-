#!/usr/bin/env python3
"""Generate narration audio by cloning the speaker voice via XTTS-v2."""

import json
import os

from TTS.api import TTS

os.environ.setdefault("COQUI_TOS_AGREED", "1")

ROOT = os.path.dirname(os.path.abspath(__file__))
os.makedirs(os.path.join(ROOT, "output"), exist_ok=True)

with open(os.path.join(ROOT, "story.json")) as f:
    story = json.load(f)

sample = os.path.join(ROOT, "samples", "voice_sample.mp3")
assert os.path.exists(sample), "voice sample missing"

tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2")
tts.to("cuda" if os.environ.get("USE_GPU") == "1" else "cpu")

tts.tts_to_file(
    text=story["narration"],
    speaker_wav=sample,
    language="hi",
    file_path=os.path.join(ROOT, "output", "narration_raw.wav"),
    split_sentences=True,
)
print("narration written")
