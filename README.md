# 简单鹤输入法官网与练习工坊

纯静态网页（内置字根字体与核心词库；查字索引在首次查询时加载 `assets/dict-search.gz`），支持直接部署至 GitHub Pages。

## 目录结构

- `index.html`：已构建完成的首屏网页，可直接双击打开或部署到 GitHub Pages
- `.nojekyll`：告知 GitHub Pages 直接以纯静态站点发布
- `src/`：网页模板（`jdh-official.tpl.html`）、精校字库（`split_bank.json`）、全量码表（`jdh_dict_multi.txt`）、拆分表（`jde.dict.yaml`）、字体与原始字根数据
- `scripts/build.py`：Python 3 构建脚本，修改 `src/` 后运行 `python3 scripts/build.py` 即可重新生成 `index.html`
- `scripts/build_fonts.py`：可选，重新生成内置字体（需要 `fonttools` 与 Noto Serif CJK 源字体）
- `scripts/build_chart.py`：生成 `zigen-chart.svg`（高清字根图，文字全部转路径，不依赖字体）
- `zigen-chart.svg`：站点根目录的可下载高清字根图，由 `build.py` 自动生成

## 高清字根图

「下载高清字根图 SVG」按钮直接下载站点根目录的 `zigen-chart.svg`。该文件的所有文字（包括私有区字形、部首、标点和注释）都已转成矢量路径，所以用相册、图片查看器或设计软件打开都不会出现方框，也不依赖设备字体。

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
## 性能实测

`scripts/measure.py` 用统一字频表做单字测算（输出 `metrics.json`）：

- 评测集：本仓库 `src/jde.dict.yaml` 的字频权重，所有方案共用，保证可比。
- 对比方案：简单鹤 4 码、虎码、小鹤音形、魔然、小鹤双拼、全拼 26 键、全拼 9 键。
- 外部码表来自 GitHub：`cubercsl/rime-flypy`、`rimeinn/rime-moran`、`LukNg/Rime-tiger_code`，首次运行自动下载到 `.cache/`。
- 口径：每字只与同码单字比较（不含词组），按字频加权；输出首选准确率、平均候选位次、平均码长、全码重码。

重跑：`python3 scripts/measure.py`

## 单字测评

`scripts/assess.py` 按字频分 12 档（前 500 ~ 前 8000 字）统计 `简单鹤` 的单字表现，输出 `src/assess.json`：

- 全码重码字数、全码首选率
- 出简重码字数、出简首选率、出简码长

口径：字频取 `src/jde.dict.yaml`，码表取 `src/jdh_dict_multi.txt`，每字只与同码单字比较（不含词组）。
复算：`python3 scripts/assess.py`，页面路由 `#assess`。
