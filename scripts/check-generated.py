#!/usr/bin/env python3
"""校验生成物是否与源码一致（供 CI 使用）。

为什么不能直接 `git diff --exit-code index.html`：
`index.html` 内嵌了 `gzip.compress()` 生成的词库 base64。即使固定 `mtime=0`，
不同 Python / zlib 版本压缩出的字节仍可能不同（zlib 1.2.x / 1.3.1 / 1.3.2 各有差异），
于是 CI 会误报「生成物过期」，而解压后的词库内容其实完全一致。

比对方式：
  * `index.html`：把 EMBEDDED_DICT_GZ_B64 的 base64 归一化为固定占位后逐字节比较；
    同时把两侧的 gzip 解压，比较 payload 文本是否一致（真正需要一致的内容）。
  * `zigen-chart.svg`（根目录与 src/ 两份）、`src/assess.json`：精确比较。

用法：
    python3 scripts/check-generated.py <基线目录>
基线目录需包含构建前的 index.html / zigen-chart.svg / src/zigen-chart.svg / src/assess.json。
退出码：0 一致；1 不一致；2 参数错误。
"""
import base64
import gzip
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GZ_RE = re.compile(r'(const EMBEDDED_DICT_GZ_B64 = ")([A-Za-z0-9+/=]+)(")')
FILES = ["index.html", "zigen-chart.svg", "src/zigen-chart.svg", "src/assess.json"]
GZ_FILES = ["assets/dict-search.gz"]


def normalize_html(text):
    return GZ_RE.sub(lambda m: m.group(1) + "<GZIP-B64>" + m.group(3), text)


def payload_of(text):
    m = GZ_RE.search(text)
    if not m:
        return None
    try:
        return gzip.decompress(base64.b64decode(m.group(2))).decode("utf-8")
    except Exception as exc:
        return f"<解压失败: {exc}>"


def main():
    if len(sys.argv) < 2:
        print("用法: check-generated.py <基线目录>")
        return 2
    base = Path(sys.argv[1])

    problems = []

    cur_index = (ROOT / "index.html").read_text(encoding="utf-8")
    old_index = (base / "index.html").read_text(encoding="utf-8")
    if normalize_html(cur_index) != normalize_html(old_index):
        if payload_of(cur_index) == payload_of(old_index):
            problems.append("index.html 有未提交的内容改动（模板/源数据改了但没重新构建）")
        else:
            problems.append("index.html 内容不一致（内嵌词库也不同）")

    for rel in FILES[1:]:
        cur, old = ROOT / rel, base / rel
        if not cur.exists():
            problems.append(f"缺少文件：{rel}")
        elif old.exists() and cur.read_bytes() != old.read_bytes():
            problems.append(f"{rel} 未随源码更新")

    for rel in GZ_FILES:
        cur, old = ROOT / rel, base / rel
        if not cur.exists():
            problems.append(f"缺少文件：{rel}")
        elif old.exists():
            try:
                same = gzip.decompress(cur.read_bytes()) == gzip.decompress(old.read_bytes())
            except Exception:
                same = False
            if not same:
                problems.append(f"{rel} 内容未随源码更新")

    if problems:
        print("生成物校验未通过：")
        for p in problems:
            print("  - " + p)
        return 1

    print("生成物校验通过（index.html 已忽略 gzip 压缩字节的版本差异）")
    return 0


if __name__ == "__main__":
    sys.exit(main())