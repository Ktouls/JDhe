# 简单鹤输入法官网与练习工坊

纯静态单文件网页（内置字根字体、20,877 字全词库、1,220 个二简词与 21,933 个三简词），开箱即用，支持直接部署至 GitHub Pages。

## 目录结构

- `index.html`：已构建完成的单文件网页，可直接双击打开或部署到 GitHub Pages
- `.nojekyll`：告知 GitHub Pages 直接以纯静态站点发布
- `src/`：网页模板（`jdh-official.tpl.html`）、167 精校字库（`split_bank.json`）、全量码表（`jdh_dict_multi.txt`）、字根字体与原始字根数据
- `scripts/build.py`：Python 3 构建脚本，修改 `src/` 后运行 `python3 scripts/build.py` 即可重新生成 `index.html`

## 本地预览

直接用浏览器打开 `index.html`，或在项目根目录运行：

```bash
python3 -m http.server 8080
```
