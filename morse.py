#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Asya's signal: Russian (Cyrillic) Morse code encoder / decoder.

The game Z.A.T.O. ends with a signal sent from the radio tower of Vorkuta-5.
It is not Latin Morse. If you decode it with a Latin table you get garbage.
This file is the correct table, plus a CLI so anyone can verify the message.

Usage:
    python morse.py encode "Я ТЕБЯ ЛЮБЛЮ"
    python morse.py decode ".-.- / - . -... .-.- / .-.. ..-- -... .-.. ..--"
"""

import sys

# Russian Morse table (Cyrillic).  Latin letters share shapes, so a Latin
# table silently produces wrong text for Я / Л / Ю / Б and friends.
RU = {
    "А": ".-",    "Б": "-...",  "В": ".--",   "Г": "--.",   "Д": "-..",
    "Е": ".",     "Ж": "...-",  "З": "--..",  "И": "..",    "Й": ".---",
    "К": "-.-",   "Л": ".-..",  "М": "--",    "Н": "-.",    "О": "---",
    "П": ".--.",  "Р": ".-.",   "С": "...",   "Т": "-",     "У": "..-",
    "Ф": "..-.",  "Х": "....",  "Ц": "-.-.",  "Ч": "---.",  "Ш": "----",
    "Щ": "--.-",  "Ъ": "--.--", "Ы": "-.--",  "Ь": "-..-",  "Э": "..-..",
    "Ю": "..--",  "Я": ".-.-",
}
EN = {v: k for k, v in RU.items()}


def encode(text: str) -> str:
    words = []
    for word in text.upper().split():
        chars = []
        for ch in word:
            if ch in RU:
                chars.append(RU[ch])
            elif ch == "\u0401":            # Ё
                chars.append(".")
        words.append(" ".join(chars))
    return " / ".join(words)


def decode(code: str) -> str:
    words = []
    for word in code.strip().split("/"):
        chars = []
        for sym in word.split():
            chars.append(EN.get(sym, "?"))
        words.append("".join(chars))
    return " ".join(words)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    mode, arg = sys.argv[1], " ".join(sys.argv[2:])
    if mode == "encode":
        print(encode(arg))
    elif mode == "decode":
        print(decode(arg))
    else:
        print(__doc__)
        sys.exit(1)
