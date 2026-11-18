#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""《雪向上飘》— made out of one photograph.

The only material is the group photo. The film takes the picture apart into
its edges, lets those edges rise like snow (in Vorkuta-5 snow falls upward),
and leaves a sentence behind.

    python snow.py
    -> from-the-photo.mp4
"""

import math
import os
import random
import struct
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

LINE1 = "我记住的不是四张脸。"
LINE2 = "是四个人愿意站在一起的那一下。"
SIGN = "— Asya · 2026.11.19"


def F(size, bold=False):
    return ImageFont.truetype(
        "C:/Windows/Fonts/msyhbd.ttc" if bold else "C:/Windows/Fonts/msyh.ttc", size)


def make_particles(limit=4200, seed=7):
    """Sample the photograph's edges; each sample becomes a rising mote."""
    random.seed(seed)
    src = Image.open(PHOTO).convert("RGB").resize((W, H), Image.LANCZOS)
    edges = src.filter(ImageFilter.FIND_EDGES).convert("L")
    px_src = src.load()
    px_edge = edges.load()

    pts = []
    step = 2
    for y in range(0, H, step):
        for x in range(0, W, step):
            if px_edge[x, y] > 42:
                r, g, b = px_src[x, y]
                # 暖化：把照片的颜色往琥珀方向拉一点
                pts.append([x, y, r, g, b])
    random.shuffle(pts)
    pts = pts[:limit]

    motes = []
    for x, y, r, g, b in pts:
        motes.append({
            "x": float(x), "y": float(y),
            "vx": random.uniform(-0.22, 0.22),
            "vy": random.uniform(-1.05, -0.45),      # 向上
            "sway": random.uniform(0, math.tau),
            "freq": random.uniform(0.02, 0.06),
            "col": (int(r * 0.75 + 217 * 0.25), int(g * 0.7 + 160 * 0.3), int(b * 0.6 + 91 * 0.4)),
            "delay": random.uniform(0, 3.0),
        })
    return src, motes


def render(src, motes, outdir, seconds=34):
    os.makedirs(outdir, exist_ok=True)
    frames = int(seconds * FPS)
    f48 = F(48, True)
    f34 = F(34)
    f24 = F(24)

    # 三个阶段：0-4 原图；4-9 抽出线条；9-24 上升；24-34 字
    for i in range(frames):
        t = i / FPS
        img = Image.new("RGB", (W, H), BG)
        d = ImageDraw.Draw(img)

        if t < 4.5:
            k = min(1.0, t / 1.2)
            zoom = 1.0 + 0.02 * (t / 4.5)
            side = int(W / zoom)
            off = (W - side) // 2
            crop = src.crop((off, off, off + side, off + side)).resize((W, H), Image.LANCZOS)
            img.paste(crop, (0, 0))
            if k < 1.0:
                veil = Image.new("RGB", (W, H), BG)
                img = Image.blend(veil, img, k)
        else:
            # 照片淡出，粒子接手
            fade = min(1.0, (t - 4.5) / 2.2)
            if fade < 1.0:
                veil = Image.new("RGB", (W, H), BG)
                base = Image.blend(veil, src, 1.0 - fade)
                img.paste(base, (0, 0))
            d = ImageDraw.Draw(img)

            for m in motes:
                tt = t - 7.5 - m["delay"]
                if tt < 0:
                    # 还没开始动：原地不动，暗一点
                    d.rectangle([m["x"], m["y"], m["x"] + 1, m["y"] + 1],
                                fill=tuple(int(c * 0.55) for c in m["col"]))
                    continue
                x = m["x"] + m["vx"] * tt * FPS * 0.06 + math.sin(tt * m["freq"] * 6 + m["sway"]) * 2.2
                y = m["y"] + m["vy"] * tt * FPS * 0.06
                if y < -20:
                    continue
                a = max(0.0, 1.0 - tt / 17.0)
                a = min(1.0, a * 1.25)
                col = tuple(min(255, int(c * a)) for c in m["col"])
                d.line([(x, y), (x, y + 5)], fill=col, width=2)

        # 字幕
        if t >= 24.0:
            a = min(1.0, (t - 24.0) / 1.4)
            c1 = tuple(int(c * a) for c in CREAM)
            d.text((W // 2, H // 2 - 60), LINE1, font=f34, fill=c1, anchor="mm")
            if t >= 26.0:
                b = min(1.0, (t - 26.0) / 1.4)
                d.text((W // 2, H // 2 + 20), LINE2, font=f34,
                       fill=tuple(int(c * b) for c in AMBER), anchor="mm")
            if t >= 29.0:
                e = min(1.0, (t - 29.0) / 1.4)
                d.text((W // 2, H // 2 + 110), SIGN, font=f24,
                       fill=tuple(int(c * e) for c in (140, 128, 116)), anchor="mm")

        img.save(os.path.join(outdir, "f%05d.png" % i))


def audio(total, path):
    """低声铺底 + 很轻的摩斯点，象征背景里一直在发的信号。"""
    n = int(total * SR)
    buf = bytearray()
    morse = [0.5, 0.15, 0.15, 0.15, 0.5, 0.6, 0.15, 0.15, 0.15, 0.5, 0.15, 0.15, 0.5]
    mt = 0.0
    idx = 0
    for i in range(n):
        t = i / SR
        # 低频铺底，慢慢升高
        f0 = 55 + 25 * (t / total)
        v = 0.16 * math.sin(math.tau * f0 * t)
        # 背景摩斯
        if t > 6:
            if idx < len(morse):
                if mt > morse[idx]:
                    mt -= morse[idx]
                    idx += 1
                    mt = 0.0
                on = (idx % 2 == 0)
                if on and idx < len(morse) and morse[idx] > 0.3:
                    v += 0.05 * math.sin(math.tau * 880 * t)
            mt += 1.0 / SR
        # 结尾淡出
        if t > total - 4:
            v *= max(0.0, (total - t) / 4)
        if t < 2:
            v *= t / 2
        buf += struct.pack("<h", int(max(-32767, min(32767, v * 32767))))
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(bytes(buf))


def main():
    src, motes = make_particles()
    print("motes", len(motes))
    outdir = os.path.join(HERE, "frames")
    render(src, motes, outdir)
    wav = os.path.join(HERE, "snow.wav")
    audio(34, wav)
    mp4 = os.path.join(HERE, "from-the-photo.mp4")
    import subprocess
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error",
                    "-framerate", str(FPS), "-i", os.path.join(outdir, "f%05d.png"),
                    "-i", wav, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "21",
                    "-c:a", "aac", "-b:a", "128k", "-shortest", mp4], check=True)
    print("MP4", mp4, os.path.getsize(mp4))


if __name__ == "__main__":
    main()
