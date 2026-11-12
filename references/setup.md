# 依赖与环境

## 必需

| 依赖 | 用途 | 备注 |
|---|---|---|
| Python ≥ 3.9 | 全部脚本 | 只用标准库 + 下面三个包 |
| [PyMuPDF](https://pymupdf.readthedocs.io/) | 读 PDF、抽文字/图、写书签 | 导入名是 `fitz`；**AGPL-3.0**，见下方许可说明 |
| markdown | Markdown → HTML | `python -m pip install markdown` |
| Pillow | 生成 contact sheet | 仅 `qa.py --sheet` 用到，缺失只影响缩略图 |

## 排版

需要一个 **Chromium 内核的浏览器**做 `--print-to-pdf`：

- Windows：Chrome / Edge 默认安装路径
- macOS：`/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`
- Linux：`google-chrome` / `chromium` / `chromium-browser` / `microsoft-edge`

`build_pdf.py` 会自动探测（顺序：Chrome → Edge → 各平台常见路径）；探测不到就用 `book.json` 里的 `"chrome": "<可执行文件绝对路径>"` 显式指定。

中文排版依赖系统字体，CSS 已按优先级回退：`Noto Serif SC` → `Source Han Serif SC` → `SimSun`。三者都没有会出现方框，装任一中文字体即可（Linux 上 `fonts-noto-cjk`）。

## 安装与自检

```bash
python -m pip install -r requirements.txt
python scripts/doctor.py          # 打印 Python/依赖/浏览器/字体检测结果
python scripts/selftest.py        # 合成 PDF 跑一遍全链路（不需要真实论文、无版权问题）
```

`doctor.py` 缺必需依赖时返回非 0；`selftest.py` 在无浏览器时会跳过 PDF 渲染步骤但仍验证抽取与解析。

## 许可注意

本仓库代码用 MIT。但它**运行时依赖 PyMuPDF**（AGPL-3.0）：

- 只是本地用、或分发给别人**源码**（让对方自己 `pip install`）：没问题；
- 把 PyMuPDF **打包进**你的可执行文件/容器/在线服务再分发：AGPL 的传染性会作用到你的整个分发物，需要商业许可或改成 AGPL。

替代方案（若你不想碰 AGPL）：`pypdf`（纯 Python，无渲染）、`pypdfium2`（PDFium 绑定，Apache/BSD 许可，渲染快但编辑能力弱）。本项目的抽取逻辑依赖 PyMuPDF 的 block bbox 与裁剪渲染，换库需要改 `pdfcommon.py` / `extract.py`。

## 跨平台注意

- 脚本内部路径全用 `os.path` / `pathlib`，Windows 反斜杠与 POSIX 斜杠都能跑；
- `SKILL.md` 里的命令给了 bash 与 PowerShell 两种写法；
- 子进程输出统一 `errors="replace"`，避免中文 Windows 的 GBK 解码崩溃（见 `references/pitfalls.md` 第 7 条）。
