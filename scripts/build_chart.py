#!/usr/bin/env python3
"""生成可独立打开的高清字根图 SVG（与网站 elegant 视觉一致）。

所有文字都转成矢量路径，不依赖字体，在相册 / 图片查看器 / 设计软件里都不会出现方框。
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

# 与网站 :root 同一套配色（elegant 主题）
BG = "#faf9f6"
INK = "#1c1917"
INK_SOFT = "#57534e"
INK_FAINT = "#8c8780"
CARD = "#ffffff"
CARD_STROKE = "#d9d5cd"
HAIRLINE = "#e7e3db"
BLUE = "#25548a"
ACCENT = "#c43c35"
BADGE_BG = "#f9ebeb"

KW, KH, GAP = 116, 140, 12
W, H = 1360, 848


def load(name):
    b64 = (SRC / (name + ".b64")).read_text().strip()
    font = TTFont(io.BytesIO(base64.b64decode(b64)))
    return font.getBestCmap(), font.getGlyphSet(), font["head"].unitsPerEm


PUA_CMAP, PUA_GS, PUA_UPEM = load("jdh_font.woff")
CJK_CMAP, CJK_GS, CJK_UPEM = load("jdh_roots_font.woff")


def resolve(ch):
    cp = ord(ch)
    if cp in PUA_CMAP:
        return PUA_GS, PUA_UPEM, PUA_CMAP[cp]
    if cp in CJK_CMAP:
        return CJK_GS, CJK_UPEM, CJK_CMAP[cp]
    return None, None, None


def advance(ch, size):
    gs, upem, name = resolve(ch)
    if gs is None:
        return size * 0.5
    return gs[name].width * size / upem


def glyph_path(ch, x, baseline, size):
    gs, upem, name = resolve(ch)
    if gs is None:
        print(f"警告：字体缺字 {ch!r} U+{ord(ch):04X}")
        return ""
    s = size / upem
    pen = SVGPathPen(gs, ntos=lambda v: f"{v:.1f}".rstrip("0").rstrip("."))
    gs[name].draw(TransformPen(pen, (s, 0, 0, -s, x, baseline)))
    d = pen.getCommands()
    return f'<path d="{d}"/>' if d else ""


def text_width(text, size):
    return sum(advance(c, size) for c in text)


def text_paths(text, x, baseline, size, color, anchor="start"):
    total = text_width(text, size)
    if anchor == "end":
        x -= total
    elif anchor == "middle":
        x -= total / 2
    out, cursor = [], x
    for ch in text:
        d = glyph_path(ch, cursor, baseline, size)
        if d:
            out.append(d)
        cursor += advance(ch, size)
    body = "".join(out)
    return f'<g fill="{color}">{body}</g>' if body else ""


def build_cards():
    raw = json.loads((SRC / "raw_zigen.json").read_text())
    seen, by_key = set(), {}
    for it in raw:
        dedup = it["name"] + "|" + it["key"]
        if dedup in seen:
            continue
        seen.add(dedup)
        name = it["name"]
        for a in ("（", "("):
            if a in name:
                name = name.split(a)[0]
        parts = [p for p in name.replace("(", " ").replace("（", " ").split() if p]
        by_key.setdefault(it["key"], []).append(parts)
    return by_key


CARDS = build_cards()
STROKE_BADGE = {"d": "横", "p": "竖", "u": "撇", "h": "点", "r": "折"}
ROWS = [
    ("qwertyuiop", 40, 134),
    ("asdfghjkl", 96, 294),
    ("zxcvbnm", 176, 454),
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
    parts = [f'<rect width="{W}" height="{H}" fill="{BG}"/>']

    # 页头：标题 + 副标题 + 右侧规格（不放图标，避免与站点图标不一致）
    parts.append(text_paths("简单鹤字根图 V9", 40, 62, 28, INK))
    parts.append(text_paths("简单鹤 · 极简音形输入方案 · 轻羽落键，意到字成", 40, 90, 13, INK_FAINT))
    parts.append(text_paths("26 键 · 97 组字根", 1320, 60, 13, INK_FAINT, anchor="end"))

    for keys, ox, oy in ROWS:
        for idx, ch in enumerate(keys):
            x = ox + idx * (KW + GAP)
            y = oy
            parts.append(
                f'<rect x="{x}" y="{y}" width="{KW}" height="{KH}" rx="14" '
                f'fill="{CARD}" stroke="{CARD_STROKE}" stroke-width="1"/>'
            )
            parts.append(text_paths(ch.upper(), x + 14, y + 26, 16, BLUE))
            if ch in STROKE_BADGE:
                label = STROKE_BADGE[ch]
                tw = text_width(label, 11)
                bx = x + KW - 12 - (tw + 10)
                parts.append(
                    f'<rect x="{bx:.1f}" y="{y + 12}" width="{tw + 10:.1f}" height="18" rx="5" '
                    f'fill="{BADGE_BG}" stroke="{ACCENT}" stroke-opacity="0.35"/>'
                )
                parts.append(text_paths(label, bx + 5, y + 25, 11, ACCENT))
            for li, card in enumerate(CARDS.get(ch, [])[:5]):
                parts.append(text_paths(" ".join(card), x + 14, y + 52 + li * 19, 14.5, INK))

    parts.append(f'<line x1="40" y1="614" x2="1320" y2="614" stroke="{HAIRLINE}" stroke-width="1"/>')
    parts.append(text_paths("提示与注释", 40, 644, 15, INK))
    for i, note in enumerate(NOTES):
        parts.append(text_paths(note, 40, 672 + i * 24, 13, INK_SOFT))

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