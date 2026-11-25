#!/usr/bin/env python3
"""生成可独立打开的高清字根图 SVG。

所有文字（字根、笔画名、注释）都转成矢量路径，不依赖任何字体，
因此在相册、图片查看器、Illustrator 等环境都不会出现方框。
输出：src/zigen-chart.svg
"""
import base64
import io
import json
import pathlib

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "src"

KW, KH, GAP = 116, 136, 12
W, H = 1360, 800


def load(name):
    b64 = (SRC / (name + ".b64")).read_text().strip()
    font = TTFont(io.BytesIO(base64.b64decode(b64)))
    return font, font.getBestCmap(), font.getGlyphSet(), font["head"].unitsPerEm


PUA, PUA_CMAP, PUA_GS, PUA_UPEM = load("jdh_font.woff")
CJK, CJK_CMAP, CJK_GS, CJK_UPEM = load("jdh_roots_font.woff")


def resolve(ch):
    cp = ord(ch)
    if cp in PUA_CMAP:
        return PUA_GS, PUA_UPEM, PUA_CMAP[cp], True
    if cp in CJK_CMAP:
        return CJK_GS, CJK_UPEM, CJK_CMAP[cp], False
    return None, None, None, None


def advance(ch, size):
    gs, upem, name, _ = resolve(ch)
    if gs is None:
        return size * 0.5
    return gs[name].width * size / upem


def glyph_path(ch, x, baseline, size):
    gs, upem, name, _ = resolve(ch)
    if gs is None:
        print(f"警告：字体缺字 {ch!r} U+{ord(ch):04X}")
        return ""
    s = size / upem
    pen = SVGPathPen(gs, ntos=lambda v: f"{v:.1f}".rstrip("0").rstrip("."))
    gs[name].draw(TransformPen(pen, (s, 0, 0, -s, x, baseline)))
    d = pen.getCommands()
    return f'<path d="{d}" fill="currentColor"/>' if d else ""


def text_paths(text, x, baseline, size, color, anchor="start", weight=None):
    total = sum(advance(c, size) for c in text)
    if anchor == "end":
        x -= total
    elif anchor == "middle":
        x -= total / 2
    out = []
    cursor = x
    for ch in text:
        d = glyph_path(ch, cursor, baseline, size)
        if d:
            out.append(d)
        cursor += advance(ch, size)
    body = "".join(out)
    if not body:
        return ""
    w = f' stroke="currentColor" stroke-width="{weight}"' if weight else ""
    return f'<g fill="{color}" color="{color}"{w} transform="translate(0,0)">{body}</g>'


def build_cards():
    raw = json.loads((SRC / "raw_zigen.json").read_text())
    seen, by_key = set(), {}
    for it in raw:
        dedup = it["name"] + "|" + it["key"]
        if dedup in seen:
            continue
        seen.add(dedup)
        name = it["name"]
        for a, b in ("（", "）"), ("(", ")"):
            if a in name:
                name = name.split(a)[0]
        parts = [p for p in name.replace("(", " ").replace("（", " ").split() if p]
        by_key.setdefault(it["key"], []).append(parts)
    return by_key


CARDS = build_cards()
STROKE_BADGE = {"d": "横", "p": "竖", "u": "撇", "h": "点", "r": "折"}
ROWS = [
    ("qwertyuiop", 40, 110),
    ("asdfghjkl", 96, 266),
    ("zxcvbnm", 176, 422),
]
NOTES = [
    "1. 键位 H 的笔画“点”类包括了笔画“捺（乀）”（如“哀”的末形）。",
    "2. 键位 D 的笔画“横”类包括了笔画“提（㇀）”（如“刁”的末形）。",
    "3. 键位 P 的笔画“竖”类包括了笔画“竖钩”（如“手”的末形）。",
    "4. 键位 R 的笔画“折”类包括了各种折撇、折钩、横折钩、竖折钩、折折钩等（如“乃”的首形）。",
    "5. 键位 N 的字根“囗”是框（如“圆”和“黑”的首形），而键位 O 的“口”是 kǒu（如“员”、“史”和“哟”的首形）。",
    "6. 键位 H 的字根“釆”并非采集的采字，而是“番”字的上部。",
    "7. 键位 Z 的字根“艹”是草字头（如“花”的首形），并非“廾”，类似“弄”的末形取“竖”。",
]


def main():
    parts = []
    parts.append(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')
    parts.append(text_paths("简单鹤字根图 V9（26 键 · 共 97 组字根）", 40, 54, 28, "#1d1d1f"))
    parts.append(text_paths("轻羽落键，意到字成 · 拆分口诀：笔顺优先（无笔画粘连的口可无视笔顺），首末取大，相交也拆，插隔也取，字根字重复，禾取丿八", 40, 82, 13.5, "#6e6e73"))

    for keys, ox, oy in ROWS:
        for idx, ch in enumerate(keys):
            x = ox + idx * (KW + GAP)
            y = oy
            parts.append(f'<rect x="{x}" y="{y}" width="{KW}" height="{KH}" rx="16" fill="#f5f5f7" stroke="#d2d2d7" stroke-width="1.5"/>')
            parts.append(text_paths(ch.upper(), x + 14, y + 28, 18, "#0071e3"))
            if ch in STROKE_BADGE:
                parts.append(text_paths(STROKE_BADGE[ch], x + KW - 14, y + 28, 14, "#e37400", anchor="end"))
            for li, card in enumerate(CARDS.get(ch, [])[:5]):
                parts.append(text_paths(" ".join(card), x + 14, y + 54 + li * 19, 15, "#1d1d1f"))

    parts.append(text_paths("提示与注释：", 40, 588, 15, "#1d1d1f"))
    for i, note in enumerate(NOTES):
        parts.append(text_paths(note, 40, 614 + i * 24, 13.5, "#48484a"))

    svg = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">\n'
        + "\n".join(p for p in parts if p)
        + "\n</svg>\n"
    )
    out = SRC / "zigen-chart.svg"
    out.write_text(svg, encoding="utf-8")
    print(f"已生成 {out.name}：{len(svg.encode('utf-8')):,} 字节，路径 {svg.count('<path')} 条")


if __name__ == "__main__":
    main()