#!/usr/bin/env python3
"""从 src/ 源文件重新构建单文件静态站点 index.html（无需第三方依赖）。"""
import base64, collections, gzip, json, pathlib, re

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "src"

tpl = (SRC / "jdh-official.tpl.html").read_text(encoding="utf-8")
font_b64 = (SRC / "jdh_font.woff.b64").read_text(encoding="utf-8").strip()
roots_font_b64 = (SRC / "jdh_roots_font.woff.b64").read_text(encoding="utf-8").strip()
raw_zigen_json = (SRC / "raw_zigen.json").read_text(encoding="utf-8").strip()
split_json = (SRC / "split_bank.json").read_text(encoding="utf-8").strip()
chaifen = {}
for line in (SRC / "jde.dict.yaml").read_text(encoding="utf-8").splitlines():
    m = re.fullmatch(r"(.)\t\[([^]]+)\]([a-z]{2})(?:\t.*)?", line)
    if m:
        ch, roots, code = m.groups()
        chaifen[ch] = [roots[0], code[0], roots[-1], code[1]]
chaifen_json = json.dumps(chaifen, ensure_ascii=False, separators=(",", ":"))

cjk_single = re.compile(r"^[\u4e00-\u9fff]$")
cjk_multi = re.compile(r"^[\u4e00-\u9fff]{2,8}$")
code_re = re.compile(r"^[a-z]{1,4}$")

char_freq = collections.Counter()
single4, short2, short3 = {}, {}, {}
single_all_ranked, word_all_ranked = {}, {}
short_code_lookup = {}

def rank_sym(idx):
    if idx == 0: return "␣"
    if idx == 1: return ";"
    if idx == 2: return "'"
    return str(idx + 1)

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
    words = parts[1].strip().split()
    if len(code) == 2 and any(cjk_multi.match(w) for w in words):
        short_code_lookup[code] = {"words": [w for w in words if cjk_multi.match(w)]}
    for r_idx, w in enumerate(words):
        tagged = code + rank_sym(r_idx)
        if len(w) == 1 and cjk_single.match(w):
            single_all_ranked.setdefault(w, [])
            if tagged not in single_all_ranked[w]:
                single_all_ranked[w].append(tagged)
            if len(code) == 1: char_freq[w] += 5000
            elif len(code) == 2: char_freq[w] += 1000
            elif len(code) == 3: char_freq[w] += 100
            elif len(code) == 4:
                single4.setdefault(w, [])
                if code not in single4[w]:
                    single4[w].append(code)
        elif cjk_multi.match(w):
            word_all_ranked.setdefault(w, [])
            if tagged not in word_all_ranked[w]:
                word_all_ranked[w].append(tagged)
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
# Section 4: 单字全部简码+全码（含选重位次 ␣ / ; / '），按码长升序排列
s4 = "\n".join(
    f"{ch}:{','.join(sorted(cs, key=lambda x: (len(x), x)))}"
    for ch, cs in single_all_ranked.items()
)
# Section 5: 词组全部简码+四码全码（含选重位次 ␣ / ; / '）
s5 = "\n".join(
    f"{w}:{','.join(sorted(cs, key=lambda x: (len(x), x)))}"
    for w, cs in word_all_ranked.items()
)
# 首屏只保留 s1/s2/s3（核心单字 + 二简 + 三简）；s4/s5 是查字用的
# 全部编码/选重位次，单独输出 assets/dict-search.gz，首次查字时再加载。
core_payload = "\n===\n".join([s1, s2, s3])
search_payload = "\n===\n".join([s4, s5])

def gzip_bytes(text):
    gz = bytearray(gzip.compress(text.encode("utf-8"), 9, mtime=0))
    # gzip 头第 9 字节 OS 字段跨 Python/zlib 版本可能不同，固定成 0xff。
    gz[9] = 0xFF
    return bytes(gz)

assets_dir = ROOT / "assets"
assets_dir.mkdir(exist_ok=True)
search_gz = gzip_bytes(search_payload)
(assets_dir / "dict-search.gz").write_bytes(search_gz)
print(f"已生成 assets/dict-search.gz：{len(search_gz):,} 字节")

dict_gz_b64 = base64.b64encode(gzip_bytes(core_payload)).decode("ascii")

out = (
    tpl.replace("__JDH_FONT_BASE64__", font_b64)
       .replace("__JDH_ROOTS_FONT_BASE64__", roots_font_b64)
       .replace("__JDH_RAW_JSON__", raw_zigen_json)
       .replace("__JDH_SPLIT_JSON__", split_json)
       .replace("__JDH_CHAIFEN_JSON__", chaifen_json)
       .replace("__JDH_DICT_GZ_B64__", dict_gz_b64)
       .replace("__JDH_SHORT_CODE_LOOKUP__", json.dumps(short_code_lookup, ensure_ascii=False, separators=(",", ":")))
)
assert "__JDH_" not in out, "存在未替换占位符"

# 顺带生成可直接下载的矢量字根图（文字已转路径，不依赖字体）
try:
    import build_chart

    build_chart.main()
    (ROOT / "zigen-chart.svg").write_bytes((SRC / "zigen-chart.svg").read_bytes())
except Exception as exc:  # 缺少 fonttools 时不影响主页面构建
    print(f"跳过字根图生成：{exc}")
(ROOT / "index.html").write_text(out, encoding="utf-8")
print(f"构建完成: index.html ({len(out.encode('utf-8')):,} bytes)")
