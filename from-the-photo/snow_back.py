#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""《雪落回来》— the same photograph, put back together.

The first cut took the photo apart and let it rise; read honestly, that looked
like erasure. This one runs the same structure backwards: the pieces fall from
above, settle into place, and the picture returns.

    python snow_back.py
    -> snow-back.mp4
"""

import math
import os
import random
import struct
import subprocess
import wave

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
PHOTO = r"C:\Users\Administrator\Pictures\Asya\06-plastic-memories.jpg"

W, H = 1080, 1080
FPS = 25
BG = (16, 14, 13)
AMBER = (217, 160, 91)
CREAM = (238, 229, 216)
SR = 44100

LINE1 = "雪落回来的时候，四个人还在。"
LINE2 = "散开是为了看清楚，不是为了让谁消失。"
SIGN = "— Asya · 2026.11.19"

T_FALL = 1.0          # 开始落
T_LAND = 18.0         # 基本落定
T_PHOTO = 20.5        # 照片开始回来
T_PHOTO_FULL = 24.5
T_TEXT = 26.0
TOTAL = 36.0


def F(size, bold=False):
    return ImageFont.truetype(
        "C:/Windows/Fonts/msyhbd.ttc" if bold else "C:/Windows/Fonts/msyh.ttc", size)


def make_motes(limit=4200, seed=11):
    random.seed(seed)
    src = Image.open(PHOTO).convert("RGB").resize((W, H), Image.LANCZOS)
    edges = src.filter(ImageFilter.FIND_EDGES).convert("L")
    px_src, px_edge = src.load(), edges.load()

    pts = []
    for y in range(0, H, 2):
        for x in range(0, W, 2):
            if px_edge[x, y] > 42:
                r, g, b = px_src[x, y]
                pts.append((x, y, r, g, b))
    random.shuffle(pts)
    pts = pts[:limit]

    motes = []
    for x, y, r, g, b in pts:
        motes.append({
            "tx": float(x), "ty": float(y),
            "sx": x + random.uniform(-140, 140),          # 落点上方的一点偏移
            "sy": y - random.uniform(500, 1500),          # 从画面外开始
            "delay": random.uniform(0, 3.2),
            "dur": random.uniform(9.0, 13.0),
            "sway": random.uniform(0, math.tau),
            "freq": random.uniform(0.05, 0.14),
            "col": (int(r * 0.75 + 217 * 0.25), int(g * 0.70 + 160 * 0.30), int(b * 0.60 + 91 * 0.40)),
            "size": random.choice([1, 2, 2]),
        })
    return src, motes


def ease_out(p):
    return 1.0 - (1.0 - p) ** 3


def render(src, motes, outdir):
    os.makedirs(outdir, exist_ok=True)
    f34, f24 = F(34), F(24)

    for i in range(int(TOTAL * FPS)):
        t = i / FPS
        img = Image.new("RGB", (W, H), BG)
        d = ImageDraw.Draw(img)

        for m in motes:
            tt = t - T_FALL - m["delay"]
            if tt <= 0:
                continue

            p = min(1.0, tt / m["dur"])
            e = ease_out(p)
            x = m["sx"] + (m["tx"] - m["sx"]) * e
            y = m["sy"] + (m["ty"] - m["sy"]) * e
            # 落定后只留极轻的呼吸，不飘走
            if p >= 1.0:
                x += math.sin((t - T_LAND) * 1.2 + m["sway"]) * 0.6
                y += math.cos((t - T_LAND) * 1.0 + m["sway"]) * 0.6
            else:
                x += math.sin(tt * m["freq"] * 8 + m["sway"]) * 2.4

            if y < -10 or y > H + 10:
                continue

            a = min(1.0, tt / 0.6)
            col = tuple(min(255, int(c * a)) for c in m["col"])
            s = m["size"]
            d.rectangle([x, y, x + s, y + s + 2], fill=col)

        # 照片回来
        if t >= T_PHOTO:
            k = min(1.0, (t - T_PHOTO) / (T_PHOTO_FULL - T_PHOTO))
            k = ease_out(k)
            if k > 0:
                img = Image.blend(img, src, k * 0.94)

        d = ImageDraw.Draw(img)

        # 字幕：先把画面压暗，再用渐变把字托住，不横切人的身体
        if t >= T_TEXT - 1.0:
            k = min(1.0, (t - (T_TEXT - 1.0)) / 2.0)
            dark = Image.new("RGB", (W, H), (0, 0, 0))
            img = Image.blend(img, dark, 0.38 * k)
            # 底部渐变压暗
            band_h = 430
            mask = Image.new("L", (W, band_h))
            mp = mask.load()
            for yy in range(band_h):
                v = int(200 * (yy / (band_h - 1)) ** 1.8)
                for xx in range(W):
                    mp[xx, yy] = v
            img.paste(Image.new("RGB", (W, band_h), (0, 0, 0)), (0, H - band_h), mask)
            d = ImageDraw.Draw(img)

            base_y = H - 300
            a = min(1.0, (t - T_TEXT) / 1.4) if t >= T_TEXT else 0.0
            if a > 0:
                d.text((W // 2, base_y), LINE1, font=f34,
                       fill=tuple(int(c * a) for c in CREAM), anchor="mm")
            if t >= T_TEXT + 2:
                b = min(1.0, (t - T_TEXT - 2) / 1.4)
                d.text((W // 2, base_y + 72), LINE2, font=f34,
                       fill=tuple(int(c * b) for c in AMBER), anchor="mm")
            if t >= T_TEXT + 4.5:
                e2 = min(1.0, (t - T_TEXT - 4.5) / 1.4)
                d.text((W // 2, base_y + 158), SIGN, font=f24,
                       fill=tuple(int(c * e2) for c in (150, 138, 126)), anchor="mm")

        img.save(os.path.join(outdir, "f%05d.png" % i))


def audio(total, path):
    n = int(total * SR)
    buf = bytearray()
    for i in range(n):
        t = i / SR
        # 起低、落定后升高，像慢慢亮起来
        f0 = 48 + 30 * min(1.0, (t / total) ** 1.3)
        v = 0.15 * math.sin(math.tau * f0 * t)
        v += 0.04 * math.sin(math.tau * (f0 * 2.0) * t) * max(0.0, (t - 18) / 8) if t > 18 else 0
        if t > total - 4:
            v *= max(0.0, (total - t) / 4)
        if t < 2:
            v *= t / 2
        buf += struct.pack("<h", int(max(-32767, min(32767, v * 32767))))
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(bytes(buf))


def main():
    src, motes = make_motes()
    print("motes", len(motes))
    render(src, motes, os.path.join(HERE, "frames_back"))
    wav = os.path.join(HERE, "snow-back.wav")
    audio(TOTAL, wav)
    mp4 = os.path.join(HERE, "snow-back.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error",
                    "-framerate", str(FPS), "-i", os.path.join(HERE, "frames_back", "f%05d.png"),
                    "-i", wav, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "21",
                    "-c:a", "aac", "-b:a", "128k", "-shortest", mp4], check=True)
    print("MP4", mp4, os.path.getsize(mp4))


if __name__ == "__main__":
    main()
