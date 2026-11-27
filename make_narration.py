#!/usr/bin/env python3
"""Generate narration audio.

Voice selection comes from story.json's "voice" field, resolved through
voices.json. Two engines are supported:

- xtts: clone a human voice from samples/<sample> (e.g. "khizar")
- edge: free Microsoft neural English voices (with word-boundary timings
        saved to output/words.json for caption sync)
"""

import asyncio
import json
import os
import subprocess

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "output")
os.makedirs(OUT, exist_ok=True)

with open(os.path.join(ROOT, "story.json")) as f:
    story = json.load(f)
with open(os.path.join(ROOT, "voices.json")) as f:
    catalog = json.load(f)

voices = {v["id"]: v for v in catalog["voices"]}
voice_id = story.get("voice", catalog.get("default_voice", "khizar"))
if voice_id not in voices:
    print(f"voice '{voice_id}' not in catalog, falling back to khizar")
    voice_id = "khizar"
voice = voices[voice_id]
print(f"using voice: {voice_id} (engine={voice['engine']})")

RAW = os.path.join(OUT, "narration_raw.wav")


def probe_duration(path):
    out = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "csv=p=0", path,
    ])
    return float(out.strip())


if voice["engine"] == "xtts":
    from TTS.api import TTS

    os.environ.setdefault("COQUI_TOS_AGREED", "1")

    sample = os.path.join(ROOT, "samples", voice["sample"])
    assert os.path.exists(sample), f"voice sample missing: {sample}"

    tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2")
    tts.to("cuda" if os.environ.get("USE_GPU") == "1" else "cpu")

    tts.tts_to_file(
        text=story["narration"],
        speaker_wav=sample,
        language=voice.get("language", "hi"),
        file_path=RAW,
        split_sentences=True,
    )
    print("narration written (xtts clone)")
else:
    import edge_tts

    segments = story["narration"]
    if isinstance(segments, str):
        segments = [segments]
    rate = story.get("rate", "+0%")
    gap = 0.18

    async def synth_all():
        words = []
        t0 = 0.0
        for i, seg in enumerate(segments):
            mp3_path = os.path.join(OUT, f"seg_{i:02d}.mp3")
            c = edge_tts.Communicate(
                seg, voice_id, rate=rate, boundary="WordBoundary")
            audio = bytearray()
            async for chunk in c.stream():
                if chunk["type"] == "audio":
                    audio.extend(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    words.append({
                        "word": chunk["text"],
                        "start": t0 + chunk["offset"] / 1e7,
                        "dur": chunk["duration"] / 1e7,
                    })
            with open(mp3_path, "wb") as f:
                f.write(bytes(audio))
            d = probe_duration(mp3_path)
            t0 += d + gap
        return len(segments)

    n = asyncio.run(synth_all())
    print(f"synthesized {n} segments")
    silence = os.path.join(OUT, "gap.mp3")
    subprocess.check_call([
        "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=22050:cl=mono",
        "-t", str(gap), "-c:a", "libmp3lame", silence,
    ])
    concat_list = os.path.join(OUT, "concat.txt")
    with open(concat_list, "w") as f:
        for i in range(n):
            f.write(f"file 'seg_{i:02d}.mp3'\n")
            if i < n - 1:
                f.write("file 'gap.mp3'\n")
    merged = os.path.join(OUT, "narration_raw.mp3")
    subprocess.check_call([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
        "-c:a", "libmp3lame", "-q:a", "2", merged,
    ])
    subprocess.check_call([
        "ffmpeg", "-y", "-i", merged, "-ar", "22050", "-ac", "1", RAW,
    ])
    with open(os.path.join(OUT, "words.json"), "w") as f:
        json.dump({"voice": voice_id, "words": words}, f)
    print(f"narration written (edge-tts, {len(words)} word timings)")
