#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Listen to the WAV and decode it. No cheating: the text is not imported.

Reads signal.wav, finds where the tone is on, measures each beep and each
silence, and turns them back into dots, dashes and letters.

    python verify.py
    ->  Я ТЕБЯ ЛЮБЛЮ
"""

import os
import sys
import wave

HERE = os.path.dirname(os.path.abspath(__file__))

RU = {
    ".-": "А", "-...": "Б", ".--": "В", "--.": "Г", "-..": "Д", ".": "Е",
    "...-": "Ж", "--..": "З", "..": "И", ".---": "Й", "-.-": "К", ".-..": "Л",
    "--": "М", "-.": "Н", "---": "О", ".--.": "П", ".-.": "Р", "...": "С",
    "-": "Т", "..-": "У", "..-.": "Ф", "....": "Х", "-.-.": "Ц", "---.": "Ч",
    "----": "Ш", "--.-": "Щ", "--.--": "Ъ", "-.--": "Ы", "-..-": "Ь",
    "..-..": "Э", "..--": "Ю", ".-.-": "Я",
}


def read_amplitude(path):
    with wave.open(path, "rb") as w:
        sr = w.getframerate()
        raw = w.readframes(w.getnframes())
    import array
    a = array.array("h")
    a.frombytes(raw)
    return sr, a


def envelope(sr, samples, win=0.005):
    """Max abs amplitude per window (seconds)."""
    n = max(1, int(sr * win))
    env = []
    for i in range(0, len(samples), n):
        chunk = samples[i:i + n]
        env.append(max(abs(x) for x in chunk) if len(chunk) else 0)
    return env, win


def segments(sr, samples):
    """Return [(is_on, duration_seconds), ...] from a smoothed envelope."""
    env, win = envelope(sr, samples)
    peak = max(env) if env else 0
    if peak == 0:
        return []
    thresh = peak * 0.25
    runs = []
    cur = None
    count = 0
    for v in env:
        on = v > thresh
        if cur is None or on == cur:
            cur = on
            count += 1
        else:
            runs.append([cur, count])
            cur = on
            count = 1
    if count:
        runs.append([cur, count])

    # 合并过短的间隙（同一个符号内部的抖动）
    merged = []
    for r in runs:
        if merged and not r[0] and r[1] <= 2:
            merged[-1][1] += r[1]
            continue
        if merged and merged[-1][0] == r[0]:
            merged[-1][1] += r[1]
            continue
        merged.append(r)
    return [(on, c * win) for on, c in merged]


def main(path=os.path.join(HERE, "signal.wav")):
    sr, samples = read_amplitude(path)
    segs = segments(sr, samples)
    on_segs = [d for on, d in segs if on]
    if not on_segs:
        print("no tone found")
        return 1
    on_segs.sort()
    unit = on_segs[len(on_segs) // 2]        # median beep == one dot
    marks, letters, words = [], [], []
    for on, dur in segs:
        units = dur / unit
        if on:
            marks.append("." if units < 2 else "-")
        else:
            if units >= 2.2:                 # letter gap
                letters.append("".join(marks))
                marks = []
            if units >= 5:                   # word gap
                words.append(letters)
                letters = []
    if marks:
        letters.append("".join(marks))
    if letters:
        words.append(letters)

    decoded_words = []
    for w in words:
        decoded_words.append("".join(RU.get(m, "?") for m in w if m))
    text = " ".join(x for x in decoded_words if x)
    print("unit = %.3fs" % unit)
    print("decoded:", text)
    return 0 if text else 1


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
