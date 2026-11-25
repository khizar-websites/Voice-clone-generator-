#!/usr/bin/env python3
"""Download story scene images from Pollinations (free, no signup)."""

import json
import os
import time
import urllib.request
import urllib.parse
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "images")
os.makedirs(OUT, exist_ok=True)

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/158.0.0.0 Safari/537.36"}
NUM_PER_SCENE = 2

with open(os.path.join(ROOT, "story.json")) as f:
    story = json.load(f)


def fetch(task):
    i, v, scene = task
    path = os.path.join(OUT, f"scene{i:02d}_v{v}.jpg")
    if os.path.exists(path) and os.path.getsize(path) > 20000:
        return f"skip {path}"
    seed = 1000 + i * 10 + v
    prompt = urllib.parse.quote(scene)
    url = (f"https://image.pollinations.ai/prompt/{prompt}"
           f"?width=768&height=1344&nologo=true&seed={seed}&model=flux")
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers=UA)
            body = urllib.request.urlopen(req, timeout=180).read()
            if len(body) > 20000 and body[:2] in (b"\xff\xd8", b"\x89"):
                with open(path, "wb") as f:
                    f.write(body)
                return f"ok {path} {len(body)//1024}KB"
        except Exception as e:
            time.sleep(3 + attempt * 3)
    raise RuntimeError(f"failed {path}")


tasks = [(i, v, scene) for i, scene in enumerate(story["scenes"]) for v in range(NUM_PER_SCENE)]
with ThreadPoolExecutor(max_workers=4) as ex:
    for res in ex.map(fetch, tasks):
        print(res, flush=True)
print(f"DONE {len(os.listdir(OUT))} images")
