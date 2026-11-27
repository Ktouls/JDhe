#!/usr/bin/env python3
"""多方案单字性能实测（同字频表、同口径）。

评测字频：本仓库 src/jde.dict.yaml 的权重（所有方案共用同一字频，保证可比）。
各方案只提供「单字 -> 码」：
  简单鹤   src/jdh_dict_multi.txt（4 码）
  小鹤音形  cubercsl/rime-flypy  flypy/flypydz.dict.yaml（4 码）
  魔然      tools/data/moran/moran.chars.dict.yaml（双拼2 + 辅助码，去掉分号）
  虎码      LukNg/Rime-tiger_code  dicts/tiger_core.dict.yaml（4 码，去掉 [）
  小鹤双拼  src/jde.dict.yaml 的 2 位双拼码
  全拼      26 键与 9 键，由同字频表的最长拼音码生成

口径：每字只与「同码单字」比较，不含词组；按字频加权。
首选准确率 = 排候选第 1 的比例；平均位次 = 加权平均位置；重码字数 = 同码多出的单字数。
用法：python3 scripts/measure.py [--fetch]
"""
import collections
import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
CACHE = ROOT / ".cache"
CJK = re.compile(r"^[\u3400-\u9fff]$")

SOURCES = {
    "flypy": ("https://raw.githubusercontent.com/cubercsl/rime-flypy/master/flypy/flypydz.dict.yaml", "flypydz.dict.yaml"),
    "moran": ("https://raw.githubusercontent.com/LukNg/Rime-tiger_code/main/tools/data/moran/moran.chars.dict.yaml", "moran.chars.dict.yaml"),
    "tiger": ("https://raw.githubusercontent.com/LukNg/Rime-tiger_code/main/dicts/tiger_core.dict.yaml", "tiger_core.dict.yaml"),
    "wubi": ("https://raw.githubusercontent.com/rime/rime-wubi/master/wubi86.dict.yaml", "wubi86.dict.yaml"),
    "cangjie": ("https://raw.githubusercontent.com/rime/rime-cangjie/master/cangjie5.base.dict.yaml", "cangjie5.base.dict.yaml"),
}


def fetch(name):
    CACHE.mkdir(exist_ok=True)
    url, fn = SOURCES[name]
    p = CACHE / fn
    if not p.exists():
        print(f"下载 {name} …")
        urllib.request.urlretrieve(url, p)
    return p


# ---------- 字频与拼音（基准表） ----------
entries = collections.defaultdict(list)
for ln in (SRC / "jde.dict.yaml").read_text().splitlines():
    p = ln.split("\t")
    if len(p) < 3 or not CJK.match(p[0]) or not re.fullmatch(r"[a-z]{1,6}", p[1]):
        continue
    try:
        w = int(float(p[2]))
    except ValueError:
        continue
    if w > 0:
        entries[p[0]].append((w, p[1]))

freq, fullpy, shuangpin = {}, {}, {}
for ch, items in entries.items():
    top = max(w for w, _ in items)
    freq[ch] = top
    same = [c for w, c in items if w == top]
    fullpy[ch] = max(same, key=len)
    two = [c for c in same if len(c) == 2]
    if two:
        shuangpin[ch] = two[0]


def t9(py):
    tbl = {}
    for d, ls in [("2", "abc"), ("3", "def"), ("4", "ghi"), ("5", "jkl"),
                  ("6", "mno"), ("7", "pqrs"), ("8", "tuv"), ("9", "wxyz")]:
        for L in ls:
            tbl[L] = d
    return "".join(tbl.get(c, c) for c in py)


# ---------- 各方案码表 ----------
our4 = collections.defaultdict(set)
for ln in (SRC / "jdh_dict_multi.txt").read_text().splitlines():
    p = ln.split("\t")
    if len(p) < 2 or not re.fullmatch(r"[a-z]{1,4}", p[0]):
        continue
    if len(p[0]) != 4:
        continue
    for w in p[1].split():
        if CJK.match(w):
            our4[w].add(p[0])


def load_simple(path, transform, pattern=r"[a-z]+"):
    m = collections.defaultdict(set)
    for ln in path.read_text(errors="ignore").splitlines():
        p = ln.split("\t")
        if len(p) < 2 or not CJK.match(p[0]):
            continue
        code = transform(p[1].strip())
        if code and re.fullmatch(pattern, code):
            m[p[0]].add(code)
    return m


def load_longest(path):
    """每字取最长码作为全码（五笔/仓颉同一字有简码与全码）。"""
    m = collections.defaultdict(set)
    for ln in path.read_text(errors="ignore").splitlines():
        p = ln.split("\t")
        if len(p) < 2 or not CJK.match(p[0]) or not re.fullmatch(r"[a-z]+", p[1]):
            continue
        m[p[0]].add(p[1])
    out = {}
    for ch, codes in m.items():
        longest = max(len(c) for c in codes)
        out[ch] = {c for c in codes if len(c) == longest}
    return out


def build():
    fly = load_simple(fetch("flypy"), lambda c: c[:4] if len(c) >= 4 else "")
    mor = load_simple(fetch("moran"), lambda c: c.replace(";", ""))
    tig = load_simple(fetch("tiger"), lambda c: c.replace("[", "").replace("]", ""), r"[a-z0-9]+")

    wubi = load_longest(fetch("wubi"))
    cang = load_longest(fetch("cangjie"))

    return {
        "{{N}} 4 码": {c: our4.get(c, set()) for c in freq},
        "小鹤音形 4 码": {c: {x for x in fly.get(c, set()) if 3 <= len(x) <= 4} for c in freq},
        "魔然 3-4 码": {c: {x for x in mor.get(c, set()) if 3 <= len(x) <= 4} for c in freq},
        "虎码 4 码": {c: {x for x in tig.get(c, set()) if len(x) == 4} for c in freq},
        "五笔 86": {c: wubi.get(c, set()) for c in freq},
        "仓颉 5 代": {c: cang.get(c, set()) for c in freq},
        "小鹤双拼 2 码": {c: ({shuangpin[c]} if c in shuangpin else set()) for c in freq},
        "全拼 26 键": {c: ({fullpy[c]} if c in fullpy else set()) for c in freq},
        "全拼 9 键": {c: ({t9(fullpy[c])} if c in fullpy else set()) for c in freq},
    }


def evaluate(mapping, chars):
    buckets = collections.defaultdict(set)
    for ch in chars:
        for c in mapping.get(ch, ()):
            buckets[c].add(ch)
    total = hit1 = rank = klen = 0.0
    covered = 0
    for ch in chars:
        w = freq.get(ch, 0)
        codes = [c for c in mapping.get(ch, ()) if buckets.get(c)]
        if not w or not codes:
            continue
        covered += 1
        best = None
        for c in codes:
            peers = sorted(buckets[c], key=lambda x: -freq.get(x, 0))
            cand = (peers.index(ch) + 1, len(c))
            if best is None or cand < best:
                best = cand
        r, ln = best
        total += w
        rank += w * r
        klen += w * ln
        if r == 1:
            hit1 += w
    multi = [v for v in buckets.values() if len(v) > 1]
    return dict(acc=round(hit1 / total * 100, 2) if total else 0,
                mean_rank=round(rank / total, 3) if total else 0,
                code_len=round(klen / total, 2) if total else 0,
                collision_codes=len(multi),
                collision_extra=sum(len(v) - 1 for v in multi),
                covered=covered, total_chars=len(chars))


def main():
    data = build()
    ordered = [c for c, _ in sorted(freq.items(), key=lambda kv: -kv[1])]
    tiers = [("前 1500 高频字", ordered[:1500]),
             ("前 3000 常用字", ordered[:3000]),
             ("前 4000 字", ordered[:4000])]

    out = {}
    for name, mp in data.items():
        out[name] = []
        print(f"== {name} ==")
        for label, chars in tiers:
            r = evaluate(mp, chars)
            r.update(tier=label, n=len(chars))
            out[name].append(r)
            print(f"  {label:12s} 首选 {r['acc']:6.2f}%  位次 {r['mean_rank']:.3f}  "
                  f"码长 {r['code_len']:.2f}  重码 {r['collision_extra']:4d}  "
                  f"覆盖 {r['covered']}/{r['total_chars']}")
        print()

    (ROOT / "metrics.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print("已写出 metrics.json")


if __name__ == "__main__":
    main()
