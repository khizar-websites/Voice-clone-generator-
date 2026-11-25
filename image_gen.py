#!/usr/bin/env python3
"""Download story scene images from Pollinations (free, no signup)."""

import json
import os
import random
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
    for attempt in range(7):
        model = "flux" if attempt < 3 else "turbo"
        url = (f"https://image.pollinations.ai/prompt/{prompt}"
               f"?width=768&height=1344&nologo=true&seed={seed + attempt}&model={model}")
        try:
            req = urllib.request.Request(url, headers=UA)
            body = urllib.request.urlopen(req, timeout=240).read()
            if len(body) > 20000 and body[:2] in (b"\xff\xd8", b"\x89"):
                with open(path, "wb") as f:
                    f.write(body)
                return f"ok {path} {len(body)//1024}KB ({model}, try {attempt+1})"
            print(f"scene{i:02d}_v{v} try{attempt}: bad body {len(body)}B {body[:60]!r}", flush=True)
        except Exception as e:
            print(f"scene{i:02d}_v{v} try{attempt}: {str(e)[:100]}", flush=True)
        time.sleep(10 + attempt * 15 + random.uniform(0, 5))
    return None


tasks = [(i, v, scene) for i, scene in enumerate(story["scenes"]) for v in range(NUM_PER_SCENE)]
with ThreadPoolExecutor(max_workers=2) as ex:
    for res in ex.map(fetch, tasks):
        print(res, flush=True)

# last-resort placeholder so assembly never breaks
from PIL import Image, ImageDraw
missing = [t for t in tasks
           if not os.path.exists(os.path.join(OUT, f"scene{t[0]:02d}_v{t[1]}.jpg"))]
for i, v, _ in missing:
    img = Image.new("RGB", (768, 1344))
    d = ImageDraw.Draw(img)
    for y in range(1344):
        d.line([(0, y), (768, y)], fill=(18 + y // 40, 12, 40 - y // 90))
    img.save(os.path.join(OUT, f"scene{i:02d}_v{v}.jpg"), quality=90)
    print(f"placeholder scene{i:02d}_v{v}", flush=True)

print(f"DONE {len(os.listdir(OUT))} images")
