#!/usr/bin/env python3
"""从 src/ 源文件重新构建单文件静态站点 index.html（无需第三方依赖）。"""
import base64, collections, gzip, pathlib, re

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "src"

tpl = (SRC / "jdh-official.tpl.html").read_text(encoding="utf-8")
font_b64 = (SRC / "jdh_font.woff.b64").read_text(encoding="utf-8").strip()
raw_zigen_json = (SRC / "raw_zigen.json").read_text(encoding="utf-8").strip()
split_json = (SRC / "split_bank.json").read_text(encoding="utf-8").strip()

cjk_single = re.compile(r"^[\u4e00-\u9fff]$")
cjk_multi = re.compile(r"^[\u4e00-\u9fff]{2,8}$")
code_re = re.compile(r"^[a-z]{1,4}$")

char_freq = collections.Counter()
single4, short2, short3 = {}, {}, {}

for raw in (SRC / "jdh_dict_multi.txt").read_text(encoding="utf-8").splitlines():
    line = raw.strip()
    if not line:
        continue
    parts = line.split("\t")
    if len(parts) < 2:
        continue
    code = parts[0].strip().lower()
    if not code_re.match(code):
        continue
    for w in parts[1].strip().split():
        if len(w) == 1 and cjk_single.match(w):
            if len(code) == 1: char_freq[w] += 5000
            elif len(code) == 2: char_freq[w] += 1000
            elif len(code) == 3: char_freq[w] += 100
            elif len(code) == 4:
                single4.setdefault(w, [])
                if code not in single4[w]:
                    single4[w].append(code)
        elif cjk_multi.match(w):
            for ch in w:
                char_freq[ch] += 1
            if len(code) == 2:
                short2.setdefault(w, [])
                if code not in short2[w]:
                    short2[w].append(code)
            elif len(code) == 3:
                short3.setdefault(w, [])
                if code not in short3[w]:
                    short3[w].append(code)

ranked_single4 = sorted(single4.items(), key=lambda kv: (-char_freq[kv[0]], kv[0]))
s1 = "\n".join(f"{ch}:{','.join(cs)}" for ch, cs in ranked_single4)
s2 = "\n".join(f"{w}:{','.join(cs)}" for w, cs in short2.items())
s3 = "\n".join(f"{w}:{','.join(cs)}" for w, cs in short3.items())
payload = s1 + "\n===\n" + s2 + "\n===\n" + s3
dict_gz_b64 = base64.b64encode(gzip.compress(payload.encode("utf-8"), 9)).decode("ascii")

out = (
    tpl.replace("__JDH_FONT_BASE64__", font_b64)
       .replace("__JDH_RAW_JSON__", raw_zigen_json)
       .replace("__JDH_SPLIT_JSON__", split_json)
       .replace("__JDH_DICT_GZ_B64__", dict_gz_b64)
)
assert "__JDH_" not in out, "存在未替换占位符"
(ROOT / "index.html").write_text(out, encoding="utf-8")
print(f"构建完成: index.html ({len(out.encode('utf-8')):,} bytes)")
