#!/usr/bin/env python3
"""生成可独立打开的高清字根图 SVG（与新版宣纸墨韵 × 极简工坊官网风格完全统一）。

所有文字均转为矢量路径，不依赖系统字体，在相册 / 浏览器 / 设计软件中均清晰无方框。
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

# 与网站 :root 1:1 同一套宣纸墨韵配色
BG = "#f8f7f4"
SURFACE = "#ffffff"
SURFACE_2 = "#f1efe9"
INK = "#1a1816"
INK_SOFT = "#57534e"
INK_FAINT = "#847e77"
LINE = "#e8e5de"
KEY_STROKE = "#d6d2c9"
BLUE = "#25548a"
ACCENT = "#c23b32"
BADGE_BG = "#f9eceb"

W, H = 1440, 960
KW, KH, GAP = 122, 148, 10


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
ROW_KEYS = ["qwertyuiop", "asdfghjkl", "zxcvbnm"]
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
    parts = [
        "<defs>",
        '  <filter id="cardShadow" x="-4%" y="-4%" width="108%" height="112%">',
        '    <feDropShadow dx="0" dy="6" stdDeviation="12" flood-color="#1a1816" flood-opacity="0.045"/>',
        "  </filter>",
        "</defs>",
        f'<rect width="{W}" height="{H}" fill="{BG}"/>',
    ]

    # 1. 顶部编辑感页头（与官网首屏徽标 & 标题风格统一）
    parts.append(f'<circle cx="58" cy="54" r="3.5" fill="{ACCENT}"/>')
    parts.append(text_paths("简单鹤 · 双拼加形输入法", 70, 59, 13.5, INK_FAINT))
    parts.append(text_paths("简单鹤 26 键字根图", 52, 102, 32, INK))

    # 右上角胶囊规格标签
    pill_txt = "26 键 · 97 字根"
    pill_w = text_width(pill_txt, 13) + 32
    pill_x = W - 52 - pill_w
    parts.append(
        f'<rect x="{pill_x:.1f}" y="72" width="{pill_w:.1f}" height="32" rx="16" '
        f'fill="{SURFACE}" stroke="{LINE}" stroke-width="1"/>'
    )
    parts.append(text_paths(pill_txt, pill_x + pill_w / 2, 93, 13, INK_SOFT, anchor="middle"))

    # 2. 白色宣纸主卡片容器（包裹 26 键键盘，与官网 .card 一致）
    card_x, card_y, card_w, card_h = 52, 128, W - 104, 526
    parts.append(
        f'<rect x="{card_x}" y="{card_y}" width="{card_w}" height="{card_h}" rx="22" '
        f'fill="{SURFACE}" stroke="{LINE}" stroke-width="1" filter="url(#cardShadow)"/>'
    )

    # 三行 QWERTY 居中排布（与官网 .zg-kb-row 居中一致）
    row_y0 = card_y + 30
    row_step = KH + 12
    for ri, keys in enumerate(ROW_KEYS):
        n = len(keys)
        row_w = n * KW + (n - 1) * GAP
        ox = (W - row_w) / 2
        oy = row_y0 + ri * row_step
        for idx, ch in enumerate(keys):
            x = ox + idx * (KW + GAP)
            y = oy
            parts.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{KW}" height="{KH}" rx="13" '
                f'fill="{BG}" stroke="{KEY_STROKE}" stroke-width="1"/>'
            )
            parts.append(text_paths(ch.upper(), x + 12, y + 25, 16, INK))
            if ch in STROKE_BADGE:
                label = STROKE_BADGE[ch]
                bsize = 15
                tw = text_width(label, bsize)
                bw, bh = tw + 14, 26
                bx = x + KW - 10 - bw
                by = y + KH - 10 - bh
                parts.append(
                    f'<rect x="{bx:.1f}" y="{by:.1f}" width="{bw:.1f}" height="{bh}" rx="7" '
                    f'fill="{BADGE_BG}" stroke="{ACCENT}" stroke-opacity="0.45" stroke-width="1.2"/>'
                )
                parts.append(text_paths(label, bx + bw / 2, by + 18.5, bsize, ACCENT, anchor="middle"))

            # 完整渲染该键全部字根分组（最多 6 组，不再截断 E / S 键第 6 组！）
            groups = CARDS.get(ch, [])
            line_h = 18.2 if len(groups) >= 6 else 19.5
            start_y = y + (46 if len(groups) >= 6 else 49)
            fsize = 13.8 if len(groups) >= 6 else 14.5
            for li, card in enumerate(groups):
                parts.append(text_paths(" ".join(card), x + 12, start_y + li * line_h, fsize, INK))

    # 3. 底部补充辨析卡片（朱红左竖线，与官网 .motto-card / 卡片风格一致）
    note_x, note_y, note_w, note_h = 52, 678, W - 104, 232
    parts.append(
        f'<rect x="{note_x}" y="{note_y}" width="{note_w}" height="{note_h}" rx="18" '
        f'fill="{SURFACE}" stroke="{LINE}" stroke-width="1" filter="url(#cardShadow)"/>'
    )
    parts.append(
        f'<rect x="{note_x}" y="{note_y + 18}" width="3.5" height="{note_h - 36}" rx="2" fill="{ACCENT}"/>'
    )
    parts.append(text_paths("提示与注释", note_x + 26, note_y + 38, 15.5, INK))
    for i, note in enumerate(NOTES):
        parts.append(text_paths(note, note_x + 26, note_y + 66 + i * 23.5, 13, INK_SOFT))

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