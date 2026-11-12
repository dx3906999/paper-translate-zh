---
name: paper-translate-zh
description: 把论文/报告/白皮书 PDF 翻成中文（或其他语言）并排成可交付的 A4 PDF——自动识别双栏/单栏/海报等版式，回贴插图、重建表格、保留参考文献、生成书签，可选归档到文献管理器。当用户要求「翻译论文/文献/报告」「要中文版 PDF」「译成中文」「paper translation」时使用；不适用于扫描件（需先 OCR）和幻灯片（应产出讲稿而非重排 PDF）。
---

# 论文翻译流水线（重排路线，版式自适应）

把一篇 PDF 变成一份**可读的中文 A4 文档**：正文重排、插图回贴、表格重建、参考文献保留、带书签。

**分工**：模型做判断（切块边界、术语、图注归属、装配顺序、验收），脚本做确定性渲染（探测、抽取、裁图、排版、书签）。

**路线**：不复刻原始版式。把译文塞回原栏宽/图框需要版面求解（断行、字号、溢出仲裁），失败率高；本 skill 产出**阅读版**。用户明确要"看起来和原文一样"时，先说明这是另一条路线，别在这里硬凑。

---

## 0. 定位 skill 目录

下面命令里的 `$SKILL` 指**本文件所在目录**。加载 skill 后先把它确定下来，之后所有脚本都用绝对路径调用：

```bash
# 任选一种
SKILL=$(dirname "$(realpath path/to/paper-translate-zh/SKILL.md)")
# 或直接 glob：**/paper-translate-zh/SKILL.md
```

```powershell
# Windows
$SKILL = (Resolve-Path "path\to\paper-translate-zh").Path
```

环境自检（依赖、Chrome/Edge、字体）：

```bash
python "$SKILL/scripts/doctor.py"
```

## 1. 先定四件事（写进 `job.json`，后面全从这里读）

```json
{
  "src":      "<原文.pdf>",
  "workdir":  "<工作目录，放中间产物>",
  "out":      "<输出.pdf>",
  "lang":     "zh-CN",
  "domain":   "example-cs",
  "fig_mode": "auto",
  "zotero":   {"collection": "<可选>"}
}
```

- `lang`：默认 `zh-CN`；换语言见第 8 节。
- `domain`：决定用哪份术语表。**没有对应领域表就现建一份**（`references/glossary-<domain>.md`），别拿别的领域表硬套。
- `fig_mode`：`auto` 时按第 2 步的探测结果选。

## 2. 探测：先量一遍，别假设版式

```bash
python "$SKILL/scripts/probe.py" "$src" --outdir "$workdir"
```

输出 `plan.json`：

| 字段 | 含义 | 怎么用 |
|---|---|---|
| `doctype` | `paper` / `report` / `poster` / `slides` | slides → 停，改做讲稿；poster → 走语义重组 |
| `columns` | 1 或 2 | 传给 `extract.py --cols` |
| `caption` | 命中的图注正则与命中数 | 传给 `--cap-regex`；`hits=0` 说明没有这种图注 |
| `images` | 嵌入位图数量 | 与 `caption.hits` 对比，选取图模式 |
| `headings` | 节标题（页码 + 文本） | 切块边界参考、译文标题对照 |
| `chunks` | 按字数 + 节边界切好的页范围 | 第 3 步直接用 |

**取图模式决策**（`fig_mode=auto`）：

| 探测结果 | 模式 |
|---|---|
| 双栏 且 `caption.hits ≥ 2` | `caption`（按图注反推裁剪，最准） |
| 单栏 / `caption.hits=0` / `images` 明显多于 `caption.hits` | `image`（直接取嵌入位图） |
| 扫描件、复杂矢量图 | `none`（只留中文图注 + "见原 PDF 图 N"） |

## 3. 抽取

```bash
python "$SKILL/scripts/extract.py" "$src" "$workdir" \
    --cols "$columns" --fig-mode "$fig_mode"
# 需要时补 --cap-regex "$regex" / --dpi 300
```

产物：`raw.txt`（分栏重排正文）、`figs/figNN.png`、`manifest.json`。

**抽完立刻核对**：`figures=` 是否对得上正文最大图号；`raw.txt` 前几页顺序是否正常（乱序 = 列数判错，改 `--cols`）。

## 4. 切块

`plan.json` 的 `chunks` 已按目标字数（默认 12k）切好并对齐节标题。**仍需人工确认三点**：

1. 不切开一张表、一条图注、一个算法块；
2. 第一块开头的标题/作者/单位剔除（封面由 `book.json` 统一渲染，装配时用 `start_at` 裁）；
3. 参考文献不交给译者——按 `[n]` 切条、拼行、保留原文语种，单独一个 part。

块数 5–8 为宜；更多说明目标字数太小或文档太长（分两批，别一次开十几个子代理）。

## 5. 并行翻译

**一个 chunk 一个子代理，同一条消息里全部发出去。** prompt 用 `references/translator-brief.md` 整段，替换 `{{CHUNK}}` / `{{OUT}}` / `{{SECTION}}` / `{{GLOSSARY}}`，其中：

```
{{GLOSSARY}} = references/glossary-core.md + references/glossary-<domain>.md
```

契约里写死了：逐段完整、断词拼接、数字照抄、`## 中文` + `> EN`、`[[FIG:n]]` + `**图 n**：`、管道表、参考文献不译、完成后只回一行。**不要逐块改契约**——改一处，各块术语和格式就分叉。

子代理跑的同时并行做：查 Crossref 拿准确元数据（DOI/会议/页码/日期）、按需微调 `assets/style.css`、写 `book.json`。

收尾把各块回报的"原文笔误 / 拼写不一致"统一掉再装配。

## 6. 装配

```json
{
  "out": "<输出.pdf>", "workdir": "<工作目录>", "lang": "zh-CN",
  "title": "<译名>", "title_en": "<原名>",
  "authors": "A<sup>1</sup> · B<sup>2</sup>", "affil": "¹ …　² …", "note": "…",
  "source": "原文：<会议/期刊 年份> · pp.… · DOI <b>…</b>",
  "badge": "中文翻译版",
  "parts": [
    {"md": "zh/part01.md", "start_at": "## 摘要"},
    {"md": "zh/part02.md", "drop_fig": [2]},
    {"md": "zh/refs.md"},
    {"md": "zh/appendix.md", "break": true}
  ],
  "figs": {"1": "figs/fig01.png", "2": "figs/fig02.png"}
}
```

```bash
python "$SKILL/scripts/build_pdf.py" "$workdir/book.json"
# 换版式：--style "$SKILL/assets/style-compact.css"
```

脚本做四件事：Markdown 方言 → HTML（双行标题、`[[FIG:n]]`、表注绑表、`[n]` 悬挂缩进、标题与后续块捆绑防孤立）→ Chrome/Edge headless 打 A4 → 按标题回填书签 + 写元数据。打印 `toc : N/N headings matched`，**必须相等**。

## 7. 验收（三道机械门 + 一道目视）

```bash
python "$SKILL/scripts/qa.py" "$out" --src "$src" --sheet "$workdir/sheet.png"
```

| 门 | 通过标准 | 不通过时 |
|---|---|---|
| 页数比 | 0.8–2.2 | 字体没生效 / 图尺寸失控 / part 漏装配 |
| 书签 | `toc` = 标题数 | 标题含特殊字符被转义 |
| 孤立标题 | "页末检查"无短行结尾 | 标题没被 `.hkeep` 包住（pitfalls 19） |
| 目视 | 看 `--sheet` 缩略图 | 图注贴错图、表被切开、页底大片空白 |

## 8. 归档

**文献管理器**（如宿主提供 Zotero 工具）：先查重 → 建条目（字段用 Crossref 的准确值）→ 挂原文 + 译文附件 → 加入分类 → 复核附件数。**不要**用 shell/curl 直连文献管理器的本地 API，那会触发授权弹窗；有插件工具就走插件。

**只要本地**：把 `out` 放到用户指定位置，工作目录留 `raw.txt`/`zh/`/`book.json` 以便重排。

## 9. 适配点

| 要改的 | 改哪里 |
|---|---|
| 目标语言 | `job.lang` + `book.json.lang` + 契约里的"中文"及标点规则 |
| 术语 | 新建 `references/glossary-<domain>.md`；`glossary-core.md` 是通用措辞，任何领域都用 |
| 版式 | 不用改：`probe.py` 判栏数与图注；判错就手工 `--cols` / `--cap-regex` |
| 排版风格 | 复制 `assets/style.css` 改字号/字体/分栏，`--style` 指过去 |
| 文档类型 | slides → 出大纲/讲稿；poster → 先按视觉块重组文本，再走 4–6 步 |

## 10. 不适用

- 扫描件 / 图片 PDF：先 OCR，否则没有图注 bbox。
- 公式密集的理论论文：上下标会丢，必须人工核对或保留原页截图对照。
- 要求原版式交付（作业、存档、期刊回稿）：这是另一条更难的路线。

## 文件

```
paper-translate-zh/
├── README.md / LICENSE / requirements.txt
├── SKILL.md
├── references/
│   ├── setup.md              依赖、自检、跨平台注意事项
│   ├── translator-brief.md   子代理契约（原样发）
│   ├── glossary-core.md      通用学术措辞
│   ├── glossary-example-cs.md 领域表示例（复制改造成自己的领域）
│   └── pitfalls.md           20 条踩坑
├── assets/style.css          A4 单栏中文样式
└── scripts/
    ├── doctor.py              环境自检
    ├── pdfcommon.py           栏数/图注/字号探测
    ├── probe.py               生成 plan.json（含切块计划）
    ├── extract.py             重排抽取 + 三种取图模式
    ├── build_pdf.py           manifest → PDF + 书签
    ├── qa.py                  页数比/书签/孤立标题/缩略图
    └── selftest.py            合成 PDF 跑全链路（CI 用）
```
