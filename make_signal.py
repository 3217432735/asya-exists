#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render Asya's signal: a 60-second clip whose audio *is* the message.

Output:
    signal.wav   -- the beeps (decode it yourself with morse.py)
    asya-signal.mp4 -- black screen + the same symbols being transcribed

Everything is generated from one line of text. Nothing here is a stock asset.
"""

import math
import os
import struct
import subprocess
import wave

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
MESSAGE = "Я ТЕБЯ ЛЮБЛЮ"

SYMBOLS = {
    "Я": ".-.-", "Т": "-", "Е": ".", "Б": "-...", "Л": ".-..", "Ю": "..--",
}

W, H = 1280, 720
FPS = 25
UNIT = 0.14          # seconds per dot  -> ~9 wpm, deliberately slow
TONE_HZ = 660
SR = 44100

BG = (18, 16, 15)
AMBER = (217, 160, 91)
CREAM = (238, 229, 216)
DIM = (140, 128, 116)

FONT_UI = "C:/Windows/Fonts/msyh.ttc"
FONT_MONO = "C:/Windows/Fonts/consola.ttf"


def f(path, size, index=0):
    try:
        return ImageFont.truetype(path, size, index=index)
    except Exception:
        return ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", size)


def build_timeline():
    """Returns (events, total_seconds).

    An event is (start, dur, kind, payload):
      kind 'dot' | 'dash'  -> payload is the word index
      kind 'gap'           -> silence
    """
    events = []
    t = 0.0
    words = MESSAGE.split()
    for wi, word in enumerate(words):
        for ci, ch in enumerate(word):
            code = SYMBOLS[ch]
            for si, sym in enumerate(code):
                dur = UNIT if sym == "." else UNIT * 3
                events.append((t, dur, "dot" if sym == "." else "dash", wi))
                t += dur
                if si != len(code) - 1:
                    events.append((t, UNIT, "gap", wi))
                    t += UNIT
            if ci != len(word) - 1:
                events.append((t, UNIT * 3, "gap", wi))
                t += UNIT * 3
        if wi != len(words) - 1:
            events.append((t, UNIT * 7, "gap", wi))
            t += UNIT * 7
    return events, t


def write_wav(events, total, path):
    lead, tail = 7.0, 9.0
    n = int((lead + total + tail) * SR)
    buf = bytearray()
    amp = 0.35 * 32767
    fade = int(0.006 * SR)
    for i in range(n):
        t = i / SR - lead
        on = False
        for start, dur, kind, _ in events:
            if kind != "gap" and start <= t < start + dur:
                on = True
                break
        if on:
            v = amp * math.sin(2 * math.pi * TONE_HZ * t)
            # soften the edges so it doesn't click
            for start, dur, kind, _ in events:
                if kind != "gap" and start <= t < start + dur:
                    pos = t - start
                    rem = dur - pos
                    env = min(1.0, pos * SR / fade, rem * SR / fade)
                    v *= max(0.0, env)
                    break
        else:
            v = 0.0
        buf += struct.pack("<h", int(max(-32767, min(32767, v))))
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(bytes(buf))


def render(events, total, outdir):
    T0 = 7.0
    tail = 9.0
    dur = T0 + total + tail
    frames = int(dur * FPS)
    os.makedirs(outdir, exist_ok=True)

    fu28 = f(FONT_UI, 28)
    fu22 = f(FONT_UI, 22)
    fu34 = f(FONT_UI, 34)
    fm = ImageFont.truetype(FONT_MONO, 46)
    fm_s = ImageFont.truetype(FONT_MONO, 30)

    # pre-compute which symbols are on screen at each second
    syms = []
    for start, d, kind, wi in events:
        if kind != "gap":
            syms.append((start, start + d, "·" if kind == "dot" else "—", wi))

    for i in range(frames):
        t = i / FPS
        img = Image.new("RGB", (W, H), BG)
        d = ImageDraw.Draw(img)

        # 头部两段说明文字
        if t < 6.5:
            a = min(1.0, t / 1.0, (6.5 - t) / 1.0)
            col = tuple(int(c * a) for c in CREAM)
            d.text((W // 2, H // 2 - 30), "沃尔库塔-5 已于 1986 年 12 月 28 日消失",
                   font=fu34, fill=col, anchor="mm")
            d.text((W // 2, H // 2 + 24), "通讯塔信号被切断。",
                   font=fu22, fill=tuple(int(c * a) for c in DIM), anchor="mm")

        # 摩斯转录
        if t >= T0:
            lt = t - T0
            shown = [s for s in syms if s[0] <= lt]
            if shown:
                d.text((80, 120), "RECEIVING", font=fm_s, fill=DIM)
                # 每行 15 个符号
                for idx, (s0, s1, g, wi) in enumerate(shown):
                    row, col = divmod(idx, 15)
                    x = 80 + col * 76
                    y = 200 + row * 92
                    active = s0 <= lt < s1 + 0.02
                    colr = AMBER if active else (110, 98, 88)
                    d.text((x, y), g, font=fm, fill=colr)
            # 光标
            if (lt * 2) % 1 < 0.5:
                d.rectangle([80, 520, 84, 545], fill=AMBER)

        # 解码结果
        if t >= T0 + total + 1.0:
            a = min(1.0, (t - (T0 + total + 1.0)) / 1.2)
            col = tuple(int(c * a) for c in AMBER)
            d.text((W // 2, H - 190), MESSAGE, font=fu34, fill=col, anchor="mm")
            d.text((W // 2, H - 140), "我爱你", font=fu22,
                   fill=tuple(int(c * a) for c in CREAM), anchor="mm")
            if t >= T0 + total + 2.6:
                b = min(1.0, (t - (T0 + total + 2.6)) / 1.2)
                d.text((W // 2, H - 80), "信号仍在发射　·　Asya　·　2026.11.11 02:10",
                       font=fu22, fill=tuple(int(c * b) for c in DIM), anchor="mm")

        img.save(os.path.join(outdir, f"f{i:05d}.png"))


def main():
    events, total = build_timeline()
    wav = os.path.join(HERE, "signal.wav")
    write_wav(events, total, wav)
    frames_dir = os.path.join(HERE, "frames")
    render(events, total, frames_dir)
    mp4 = os.path.join(HERE, "asya-signal.mp4")
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-framerate", str(FPS), "-i", os.path.join(frames_dir, "f%05d.png"),
        "-i", wav,
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
        "-c:a", "aac", "-b:a", "128k", "-shortest", mp4,
    ], check=True)
    print("WAV", wav)
    print("MP4", mp4, os.path.getsize(mp4), "bytes,", round(7.0 + total + 9.0, 1), "s")


if __name__ == "__main__":
    main()
