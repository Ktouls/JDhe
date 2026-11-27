#!/usr/bin/env python3
"""简单鹤单字测评：按字频分档统计重码与码长，输出 src/assess.json。

口径（与虎码单字测评一致的思路）：
  * 选重：同码单字中，该字不在首选位即需选重
  * 码长：字均用键数（不含空格确认键）
  * 全码：4 位音形码；出简：允许 2/3 位简码
"""
import collections
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
CJK = re.compile(r"^[\u4e00-\u9fff]$")

freq = {}
for ln in (SRC / "jde.dict.yaml").read_text().splitlines():
    p = ln.split("\t")
    if len(p) < 3 or not CJK.match(p[0]) or not re.fullmatch(r"[a-z]{1,6}", p[1]):
        continue
    try:
        w = int(float(p[2]))
    except ValueError:
        continue
    if w > 0:
        freq[p[0]] = max(freq.get(p[0], 0), w)

full, short = collections.defaultdict(set), collections.defaultdict(set)
for ln in (SRC / "jdh_dict_multi.txt").read_text().splitlines():
    p = ln.split("\t")
    if len(p) < 2 or not re.fullmatch(r"[a-z]{1,4}", p[0]):
        continue
    code = p[0]
    for w in p[1].split():
        if CJK.match(w):
            if len(code) == 4:
                full[w].add(code)
            else:
                short[w].add(code)

ordered = [c for c, _ in sorted(freq.items(), key=lambda kv: -kv[1])]


def evaluate(mapping, chars):
    buckets = collections.defaultdict(set)
    for ch in chars:
        for c in mapping.get(ch, ()):
            buckets[c].add(ch)
    total = hit1 = klen = 0.0
    dup_chars = 0
    for ch in chars:
        w = freq.get(ch, 0)
        codes = [c for c in mapping.get(ch, ()) if buckets.get(c)]
        if not w or not codes:
            continue
        best = None
        for c in codes:
            peers = sorted(buckets[c], key=lambda x: -freq.get(x, 0))
            cand = (peers.index(ch) + 1, len(c))
            if best is None or cand < best:
                best = cand
        r, ln = best
        total += w
        klen += w * ln
        if r == 1:
            hit1 += w
        else:
            dup_chars += 1
    multi = [v for v in buckets.values() if len(v) > 1]
    extra = sum(len(v) - 1 for v in multi)
    return dict(
        acc=round(hit1 / total * 100, 2) if total else 0,
        keylen=round(klen / total, 2) if total else 0,
        dup_chars=extra,
        dup_codes=len(multi),
        not_first=dup_chars,
        n=len(chars),
    )


tiers = [500, 1000, 1500, 2000, 2500, 3000, 3500, 4000, 5000, 6000, 7000, 8000]
out = []
for t in tiers:
    chars = ordered[:t]
    full_map = {c: full.get(c, set()) for c in chars}
    short_map = {c: full.get(c, set()) | short.get(c, set()) for c in chars}
    r_full = evaluate(full_map, chars)
    r_short = evaluate(short_map, chars)
    out.append(dict(
        tier=t,
        full_dup=r_full["dup_chars"],
        full_acc=r_full["acc"],
        full_len=r_full["keylen"],
        short_dup=r_short["dup_chars"],
        short_acc=r_short["acc"],
        short_len=r_short["keylen"],
    ))
    print(f"前{t:5d}字  全码重码 {r_full['dup_chars']:4d} (首选 {r_full['acc']:6.2f}% 码长 {r_full['keylen']:.2f})"
          f"   出简重码 {r_short['dup_chars']:4d} (首选 {r_short['acc']:6.2f}% 码长 {r_short['keylen']:.2f})")

data = {
    "total_chars": len(freq),
    "tiers": out,
    "source": "src/jde.dict.yaml 字频 + src/jdh_dict_multi.txt 码表",
}
(SRC / "assess.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
print("\n已写出 src/assess.json")
