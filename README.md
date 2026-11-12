# paper-translate-zh

[![selftest](https://github.com/dx3906999/paper-translate-zh/actions/workflows/selftest.yml/badge.svg)](https://github.com/dx3906999/paper-translate-zh/actions/workflows/selftest.yml)
[![license: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

把学术论文 PDF 翻成中文（或任何目标语言），并排成一份**可读的 A4 文档**：正文重排、插图回贴、表格重建、参考文献保留、自动生成书签。可选归档到文献管理器（Zotero 等）。

一个 `SKILL.md` + 7 个脚本，既能给 AI agent 当 skill 用，也能当纯命令行工具跑。

```
PDF ──probe──▶ 版式/图注/切块计划
     └─extract─▶ 分栏重排正文 + 裁好的插图
        └─(模型并行翻译)─▶ 中文 Markdown
              └─build_pdf─▶ A4 PDF（图/表/参考文献/书签）
                    └─qa─▶ 页数比 / 书签 / 孤立标题 / 缩略图
```

## 为什么不是"保留原版式"

把译文塞回原来的栏宽、图框和位置，需要做版面求解——断行点全变、中文字宽不同、文本溢出要仲裁。这类工具通常死在"图块与正文边界冲突"上，且失败后无法交付。

本项目走另一条路线：**重排版式**。产出是一份干净的阅读版（单栏、图表按原样回贴、表格重建），换来的是可复现、可验收、几乎不会失败的流水线。要求"看起来和原文一模一样"的场景（作业、存档、期刊回稿）不在范围内。

## 快速开始

```bash
git clone https://github.com/dx3906999/paper-translate-zh.git
cd paper-translate-zh
python -m pip install -r requirements.txt

python scripts/doctor.py      # 环境自检：依赖 / 浏览器 / 中文字体
python scripts/selftest.py    # 现场合成 PDF 跑通全链路，不需要任何论文
```

跑一篇真的：

```bash
python scripts/probe.py  paper.pdf --outdir work        # 看版式探测结果
python scripts/extract.py paper.pdf work --fig-mode caption
#   → work/raw.txt、work/figs/、work/manifest.json
#   → 这一步之后由人/模型把 raw.txt 切块翻译成 work/zh/*.md
python scripts/build_pdf.py work/book.json               # → work/out.pdf + 书签
python scripts/qa.py work/out.pdf --src paper.pdf --sheet work/sheet.png
```

`work/book.json` 是最小清单：标题、作者、`parts`（按顺序拼的 Markdown 文件）、`figs`（图号→图片路径）。完整字段见 `SKILL.md` 第 6 节。

## 当 skill 用

`SKILL.md` 是给 agent 的执行手册：先 `probe` 判版式，再按决策表选取图模式，按 `plan.json` 的切块计划并行派子代理翻译（`references/translator-brief.md` 是固定契约），最后装配 + 三道验收门。任何支持 `SKILL.md` 约定的 agent 都能读；不绑定特定模型或平台。

## 目录

```
SKILL.md                  agent 执行手册（流程 + 决策表 + 验收标准）
references/
  setup.md                依赖、安装、许可、跨平台注意
  translator-brief.md     翻译子代理契约（可直接当 prompt）
  glossary-core.md        通用学术措辞规范
  glossary-example-cs.md  领域表示例（复制改成自己的领域）
  pitfalls.md             20 条实战踩坑
assets/style.css          A4 单栏排版样式（可换）
scripts/
  doctor.py               环境自检
  probe.py                版式探测 → plan.json
  extract.py              分栏重排 + 三种取图模式
  build_pdf.py            Markdown → HTML → PDF + 书签
  qa.py                   验收检查 + 缩略图
  selftest.py             合成 PDF 跑全链路（CI 用）
```

## 设计原则

1. **模型做判断，脚本做渲染**。切块、术语、图注归属需要判断，写成脚本只会僵化；抽取、裁图、排版、写书签是确定性的，写成脚本才可复现。
2. **先量后切**。`probe.py` 不假设 IEEE 双栏：栏数、图注格式、字号、嵌入图都是量出来的，判错还能命令行覆盖。
3. **可验收**。页数比、书签匹配率、孤立标题、缩略图目视——四道门，任何一道不过就不交付。
4. **失败要可诊断**。每个脚本打印它做了什么、跳过了什么，错误信息指向 `pitfalls.md` 的具体条目。

## 适用范围

| 支持 | 不支持（会明确拒绝或降级） |
|---|---|
| 双栏期刊/会议论文（IEEE、ACM、USENIX、arXiv 双栏） | 扫描件 / 纯图片 PDF（需先 OCR） |
| 单栏报告、白皮书、arXiv 单栏 | 公式密集的理论论文（上下标会丢，需人工核对） |
| 多页 poster（文字按语义重组） | 幻灯片（应产出讲稿，不是重排 PDF） |
| 中文、英文及常见语言对 | 要求保留原版式 |

## 依赖与许可

- 代码：**MIT**（见 `LICENSE`）
- 依赖：Python ≥ 3.9、[PyMuPDF](https://pymupdf.readthedocs.io/)（AGPL-3.0）、markdown、Pillow，排版需要 Chromium 内核浏览器
- ⚠️ **PyMuPDF 是 AGPL-3.0**。分发**源码**让别人自己装依赖没问题；把 PyMuPDF **打包进**你的二进制/镜像/在线服务再分发，会触发 AGPL 的传染性，需要商业许可或整体 AGPL。细节见 `references/setup.md`。

## 贡献

欢迎补：

- 新的领域术语表（`references/glossary-<domain>.md`）
- 新的版式探测规则（`pdfcommon.py` 的 `detect_columns` / `CAP_PATTERNS`）
- 更多 `doctype`（期刊双栏、双语文档、目录页）
- 真实踩坑（`pitfalls.md` 每条都请附触发条件）

改完跑 `python scripts/selftest.py`，应当全绿。
