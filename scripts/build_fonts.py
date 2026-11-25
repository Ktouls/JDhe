#!/usr/bin/env python3
"""生成网页内置的两段字体（可选，日常改内容不需要跑）。

1. `src/jdh_font.woff.b64`：拆分专用私有区字形，取自 rime-JDhe 的 `fonts/ChaiPUA.ttf`；
2. `src/jdh_roots_font.woff.b64`：字根/拆字/默认题库用到的汉字子集，取自 Noto Serif CJK SC。

依赖 fonttools，并需要一个 Noto Serif CJK 的 .ttc/.otf 源文件：
    python3 -m pip install fonttools
    NOTO_CJK=/path/to/NotoSerifCJK-Regular.ttc python3 scripts/build_fonts.py
"""
import base64
import json
import os
import pathlib
import re

from fontTools.subset import Options, Subsetter
from fontTools.ttLib import TTCollection, TTFont

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
CHAI = os.environ.get("CHAI_PUA", "/workspace/rime-JDhe-CyIME/fonts/ChaiPUA.ttf")
NOTE = "参见 README 的「内置字体」一节"


def subset(font, text=None, unicodes=None):
    opts = Options()
    opts.flavor = "woff"
    opts.layout_features = []
    opts.name_IDs = [1, 2]
    opts.notdef_outline = True
    opts.desubroutinize = True
    opts.hinting = False
    opts.drop_tables += ["DSIG"]
    sub = Subsetter(options=opts)
    if text:
        sub.populate(text=text)
    else:
        sub.populate(unicodes=unicodes)
    sub.subset(font)
    return font


def write_b64(font, name):
    out = SRC / name
    font.flavor = "woff"
    font.save(out)
    data = out.read_bytes()
    (SRC / (name + ".b64")).write_text(base64.b64encode(data).decode("ascii") + "\n")
    print(f"{name}: {len(data):,} 字节")


def main():
    pua = TTFont(CHAI)
    subset(pua, unicodes=sorted(pua.getBestCmap()))
    write_b64(pua, "jdh_font.woff")

    chars = set()
    for it in json.loads((SRC / "raw_zigen.json").read_text()):
        chars |= {c for c in it["name"] if not (0xE000 <= ord(c) <= 0xF8FF)}
    for it in json.loads((SRC / "split_bank.json").read_text()):
        chars |= {c for c in it["parts"] if c not in "()+ "}
    for line in (SRC / "jde.dict.yaml").read_text().splitlines():
        m = re.fullmatch(r"(.)\t\[([^]]+)\]([a-z]{2})(?:\t.*)?", line)
        if m:
            chars |= set(re.sub(r"[a-z]", "", m.group(2)))
    chars |= {c for c in (SRC / "jdh-official.tpl.html").read_text() if "\u4e00" <= c <= "\u9fff"}

    top, count = set(), 0
    for line in (SRC / "jdh_dict_multi.txt").read_text().splitlines():
        parts = line.split("\t")
        if len(parts) < 2 or not re.fullmatch(r"[a-z]{4}", parts[0]):
            continue
        for w in parts[1].split():
            if re.fullmatch(r"[\u4e00-\u9fff]", w) and w not in top:
                top.add(w)
                count += 1
                if count >= 1000:
                    break
        if count >= 1000:
            break
    chars |= top
    # 字根图导出脚本里的标题、注释用字（含中文标点、笔画符号）
    chart = (ROOT / "scripts" / "build_chart.py").read_text(encoding="utf-8")
    chars |= {c for c in chart if not c.isascii()}

    # 字根图注释里的拉丁字母、数字与带调韵母（如 kǒu）也需要覆盖
    chars |= {chr(c) for c in range(0x20, 0x7F)}
    chars |= {chr(c) for c in range(0xA0, 0x250)}
    chars = {c for c in chars if ord(c) > 0x2000 or 0x20 <= ord(c) <= 0x7E or 0xA0 <= ord(c) <= 0x24F}

    cjk_path = os.environ.get("NOTO_CJK", "/workspace/NotoSerifCJK.ttc")
    coll = TTCollection(cjk_path)
    face = next(f for f in coll.fonts if "SC" in (f["name"].getDebugName(1) or ""))
    missing = sorted(c for c in chars if ord(c) not in face.getBestCmap())
    subset(face, text="".join(sorted(c for c in chars if ord(c) in face.getBestCmap())))
    write_b64(face, "jdh_roots_font.woff")
    print(f"汉字子集 {len(chars)} 个；源字体缺失 {len(missing)} 个（多为私有区，已由 ChaiPUA 段覆盖）")

    for name in ("jdh_font.woff", "jdh_roots_font.woff"):
        (SRC / name).unlink(missing_ok=True)
    print(NOTE)


if __name__ == "__main__":
    main()