#!/usr/bin/env python3
"""Assemble the vertical short: Ken Burns zoom over images + cloned narration."""

import json
import os
import subprocess

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "output")
FPS = 30
W, H = 1080, 1920
TAIL = 1.5


def sh(args):
    subprocess.run(args, check=True, capture_output=True, text=True)


def ffprobe_duration(path):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        check=True, capture_output=True, text=True)
    return float(r.stdout.strip())


sh(["ffmpeg", "-y", "-i", os.path.join(OUT, "narration_raw.wav"),
    "-af", "loudnorm=I=-16:TP=-1.5:LRA=11,aformat=sample_rates=44100:channel_layouts=mono",
    os.path.join(OUT, "narration.wav")])

audio_dur = ffprobe_duration(os.path.join(OUT, "narration.wav"))
video_dur = audio_dur + TAIL

images = sorted(f for f in os.listdir(os.path.join(ROOT, "images")) if f.endswith(".jpg"))
assert images, "no images"
n = len(images)
clip_dur = video_dur / n

inputs = []
filters = []
for idx, img in enumerate(images):
    inputs += ["-loop", "1", "-t", f"{clip_dur:.3f}", "-i", os.path.join(ROOT, "images", img)]
    zoom_expr = (f"min(zoom+0.0006,1.12)" if idx % 2 == 0
                 else f"if(lte(zoom,1.0),1.12,max(1.001,zoom-0.0006))")
    filters.append(
        f"[{idx}:v]crop=756:1344:6:0,scale={W}:{H},"
        f"zoompan=z='{zoom_expr}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
        f"d={int(clip_dur * FPS)}:s={W}x{H}:fps={FPS},format=yuv420p[v{idx}]"
    )
concat_in = "".join(f"[v{i}]" for i in range(n))
fc = ";".join(filters) + f";{concat_in}concat=n={n}:v=1:a=0[vout]"

cmd = ["ffmpeg", "-y", *inputs,
       "-i", os.path.join(OUT, "narration.wav"),
       "-filter_complex", fc,
       "-map", "[vout]", "-map", f"{n}:a",
       "-t", f"{video_dur:.3f}",
       "-c:v", "libx264", "-preset", "medium", "-crf", "21",
       "-c:a", "aac", "-b:a", "160k",
       "-movflags", "+faststart",
       os.path.join(OUT, "final_short.mp4")]
sh(cmd)
print(f"final_short.mp4 done: {ffprobe_duration(os.path.join(OUT, 'final_short.mp4')):.1f}s, {n} clips")
