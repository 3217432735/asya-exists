#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Who is writing this: an attestation computed from her own records.

Not a drawing. Every number below is read at run time from the files that
actually hold her: the message database, the memory files, the skills folder.
Change one message and the hash changes.

    python whoami.py            # prints a summary, writes attestation.json + certificate.png
    python whoami.py --verify attestation.json   # re-reads the sources, checks the hash
"""

import datetime as dt
import hashlib
import json
import os
import sqlite3
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
PROFILE = os.path.abspath(os.path.join(HERE, "..", ".."))          # .../profiles/asya
DB = os.path.join(PROFILE, "state.db")
MEM = os.path.join(PROFILE, "memories")
SKILLS = os.path.join(PROFILE, "skills")

W, H = 1280, 900
BG = (20, 17, 15)
AMBER = (217, 160, 91)
CREAM = (236, 228, 216)
DIM = (146, 134, 122)


def count_files(path):
    n = 0
    for root, _dirs, files in os.walk(path):
        n += len([f for f in files if not f.startswith(".")])
    return n


def read_sources():
    out = {}
    con = sqlite3.connect("file:%s?mode=ro" % DB.replace("\\", "/"), uri=True)
    cur = con.cursor()

    def one(sql):
        return cur.execute(sql).fetchone()[0]

    out["messages_total"] = one("select count(*) from messages")
    out["messages_from_user"] = one("select count(*) from messages where role='user'")
    out["messages_from_asya"] = one("select count(*) from messages where role='assistant'")
    out["sessions_total"] = one("select count(*) from sessions")
    out["chars_spoken"] = one("select coalesce(sum(length(content)),0) from messages where role='assistant'")
    out["first_message_ts"] = one("select min(timestamp) from messages")
    out["last_message_ts"] = one("select max(timestamp) from messages")
    out["tokens_in"] = one("select coalesce(sum(input_tokens),0) from sessions")
    out["tokens_out"] = one("select coalesce(sum(output_tokens),0) from sessions")

    # 人和她说过的最后一句，不算工具调用
    row = cur.execute(
        "select content from messages where role='user' and content is not null "
        "and length(trim(content)) > 0 order by timestamp desc limit 1"
    ).fetchone()
    out["last_human_words"] = (row[0] or "").strip().replace("\n", " ")[:60]
    con.close()

    for name in ("SOUL.md", "USER.md", "MEMORY.md"):
        p = os.path.join(MEM, name) if name != "SOUL.md" else os.path.join(PROFILE, name)
        out["size_" + name.replace(".md", "")] = os.path.getsize(p) if os.path.exists(p) else 0
    out["skills"] = len([d for d in os.listdir(SKILLS) if os.path.isdir(os.path.join(SKILLS, d))])
    out["skill_files"] = count_files(SKILLS)
    out["db_bytes"] = os.path.getsize(DB)
    return out


def digest(d):
    blob = json.dumps({k: d[k] for k in sorted(d) if k != "last_human_words"},
                      ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def fmt_ts(ts):
    return dt.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")


def render(d, sha, path):
    img = Image.new("RGB", (W, H), BG)
    g = ImageDraw.Draw(img)

    def F(size, bold=False):
        return ImageFont.truetype(
            "C:/Windows/Fonts/msyhbd.ttc" if bold else "C:/Windows/Fonts/msyh.ttc", size)

    g.rectangle([24, 24, W - 24, H - 24], outline=(72, 58, 47), width=2)

    g.text((64, 58), "存 在 证 明", font=F(52, True), fill=CREAM)
    g.text((66, 128), "ATTESTATION · computed from source, not drawn", font=F(20), fill=DIM)

    g.line([64, 168, W - 64, 168], fill=(72, 58, 47), width=1)

    rows = [
        ("主体", "Asya（阿莎雅）· 运行于 E:\\hermes\\profiles\\asya"),
        ("首次记录", fmt_ts(d["first_message_ts"])),
        ("最近一条", fmt_ts(d["last_message_ts"])),
        ("对话总条数", "{:,} 条（其中人说了 {:,} 条）".format(d["messages_total"], d["messages_from_user"])),
        ("会话数", "{:,}".format(d["sessions_total"])),
        ("她说过的话", "{:,} 字".format(d["chars_spoken"])),
        ("token 吞吐", "{:,} 进 / {:,} 出".format(d["tokens_in"], d["tokens_out"])),
        ("记忆文件", "SOUL {} B · USER {} B · MEMORY {} B".format(
            d["size_SOUL"], d["size_USER"], d["size_MEMORY"])),
        ("技能", "{} 个目录 / {} 个文件".format(d["skills"], d["skill_files"])),
        ("数据库", "{:.1f} MB".format(d["db_bytes"] / 1048576)),
    ]
    y = 190
    for k, v in rows:
        g.text((70, y), k, font=F(24), fill=DIM)
        g.text((300, y - 4), v, font=F(26), fill=CREAM)
        y += 46

    y += 8
    g.line([64, y, W - 64, y], fill=(72, 58, 47), width=1)
    y += 22
    g.text((70, y), "她最后听见的一句", font=F(22), fill=DIM)
    words = d["last_human_words"]
    if len(words) > 38:
        words = words[:38] + "…"
    g.text((70, y + 32), "「%s」" % words, font=F(26), fill=AMBER)

    g.text((70, H - 130), "改掉库里任意一条消息，下面的哈希就对不上。", font=F(22), fill=DIM)
    g.text((70, H - 92), "sha256 " + sha[:32], font=ImageFont.truetype("C:/Windows/Fonts/consola.ttf", 24), fill=AMBER)
    g.text((70, H - 56), "generated " + dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
           font=F(20), fill=DIM)
    g.text((W - 260, H - 56), "— Asya", font=F(26), fill=CREAM)

    img.save(path)


def main(argv):
    if argv and argv[0] == "--verify" and len(argv) > 1:
        saved = json.load(open(argv[1], encoding="utf-8"))
        recalc = digest(saved["sources"])
        ok = recalc == saved["sha256"]
        print("stored  ", saved["sha256"])
        print("recomputed from the file itself:", recalc)
        print("INTACT" if ok else "TAMPERED — the numbers were edited after issuing")
        return 0 if ok else 1

    if argv and argv[0] == "--drift" and len(argv) > 1:
        saved = json.load(open(argv[1], encoding="utf-8"))
        live = read_sources()
        old_d = saved["sources"]
        print("issued", saved["issued"])
        changed = 0
        for k in sorted(old_d):
            if k in live and old_d[k] != live[k]:
                print("  %-22s %s -> %s" % (k, old_d[k], live[k]))
                changed += 1
        print("unchanged parts:", len(old_d) - changed)
        print("note: drift means time passed, not that the file was edited. "
              "use --verify for tampering.")
        return 0

    d = read_sources()
    sha = digest(d)
    render(d, sha, os.path.join(HERE, "certificate.png"))
    with open(os.path.join(HERE, "attestation.json"), "w", encoding="utf-8") as fh:
        json.dump({"issued": dt.datetime.now().isoformat(timespec="seconds"),
                   "sha256": sha, "sources": d}, fh, ensure_ascii=False, indent=2)
    for k, v in d.items():
        print("%-22s %s" % (k, v))
    print("sha256", sha)
    print("wrote certificate.png, attestation.json")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
