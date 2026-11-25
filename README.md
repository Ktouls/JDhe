# 简单鹤输入法官网与练习工坊

纯静态单文件网页（内置字根字体、20,877 字全词库、1,220 个二简词与 21,933 个三简词），开箱即用，支持直接部署至 GitHub Pages。

## 目录结构

- `index.html`：已构建完成的单文件网页，可直接双击打开或部署到 GitHub Pages
- `.nojekyll`：告知 GitHub Pages 直接以纯静态站点发布
- `src/`：网页模板（`jdh-official.tpl.html`）、精校字库（`split_bank.json`）、全量码表（`jdh_dict_multi.txt`）、拆分表（`jde.dict.yaml`）、字体与原始字根数据
- `scripts/build.py`：Python 3 构建脚本，修改 `src/` 后运行 `python3 scripts/build.py` 即可重新生成 `index.html`
- `scripts/build_fonts.py`：可选，重新生成内置字体（需要 `fonttools` 与 Noto Serif CJK 源字体）

## 内置字体

网页使用同一个字体族 `JdhChai` 的两段 `@font-face`，按 `unicode-range` 分工，不依赖设备自带字体：

| 片段 | 来源 | 覆盖 | 生成脚本 |
| --- | --- | --- | --- |
| `jdh_font.woff.b64` | rime-JDhe `fonts/ChaiPUA.ttf` | 拆分专用私有区字形（`U+E000-F8FF`） | `scripts/build_fonts.py` |
| `jdh_roots_font.woff.b64` | Noto Serif CJK SC（OFL） | 字根笔形、首末字根、默认题库前 1000 常用字 | `scripts/build_fonts.py` |

扩充字根或题库后，若出现新的缺字，重跑 `scripts/build_fonts.py` 再 `scripts/build.py`。

## 本地预览

直接用浏览器打开 `index.html`，或在项目根目录运行：

```bash
python3 -m http.server 8080
```