# -*- coding: utf-8 -*-
"""build_pdf.py — 把「中文 Markdown 分块」排成一份可交付的 A4 PDF（带书签）。

用法:
    python build_pdf.py <manifest.json>

manifest.json 示例:
{
  "out":  "/path/to/out.pdf",
  "title": "<中文标题>",
  "title_en": "<Original Title>",
  "authors": "A<sup>1</sup> · B<sup>2</sup>",   // 允许内联 HTML
  "affil":   "¹ 中国科学院计算技术研究所　² 中国科学院大学",
  "note":    "‡ 共同第一作者。",
  "source":  "原文：<会议/期刊 年份> · pp.… · DOI <b>…</b>",   // 允许 <b>
  "badge":   "中文翻译版",
  "footnote":"<页脚文字>",
  "parts": [
     {"md": "zh/part01.md", "start_at": "## 摘要"},
     {"md": "zh/part02.md", "drop_fig": [2]},
     {"md": "zh/refs.md"},
     {"md": "zh/appendix.md", "break": true}
  ],
  "figs": {"1": "figs/fig01.png", "2": "figs/fig02.png"},   // 或用 "figdir": "figs"
  "chrome": "C:/Program Files/Google/Chrome/Application/chrome.exe"        // 可选
}

Markdown 方言（翻译分块必须按这个写）:
    ## III 框架总览          -> 一级节，下一行 `> FRAMEWORK OVERVIEW` 作为英文副题
    ### A 概念定义           -> 二级节，同样可带 `> Notions`
    [[FIG:3]]                -> 插图占位，下一行 `**图 3**：中文图注` 自动并进 <figcaption>
    | a | b |                -> 管道表格，`**表 I**：…` 起头的段落会自动和表格绑在一起避免跨页
    <p>[12] ...</p>          -> 以 [数字] 起头的段落自动识别为参考文献，用悬挂缩进
"""

import argparse
import glob
import json
import os
import re
import subprocess
import sys

import markdown

HERE = os.path.dirname(os.path.abspath(__file__))
STYLE = os.path.join(HERE, "..", "assets", "style.css")

BLOCK = markdown.Markdown(extensions=["tables", "md_in_html", "fenced_code"])
INLINE = markdown.Markdown(extensions=["tables", "md_in_html"])

TBL_RE = re.compile(r'<p>(<strong>表\s?[0-9IVXivx]+</strong>[^<]*?)</p>\s*(<table>.*?</table>)', re.S)
REF_RE = re.compile(r"<p>(\[\d+\])")
KEEP_RE = re.compile(
    r'(<h[23] class="sh">.*?</h[23]>)\s*'
    r'((?:<p>.*?</p>|<ul>.*?</ul>|<ol>.*?</ol>|<figure class="fig">.*?</figure>'
    r'|<div class="tblwrap">.*?</div>))', re.S)
FIG_RE = re.compile(r"^\[\[(P?FIG):(\d+)\]\]$")


def inline(s):
    INLINE.reset()
    return INLINE.convert(s).strip().removeprefix("<p>").removesuffix("</p>")


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def group_tables(html):
    return TBL_RE.sub(lambda m: '<div class="tblwrap"><p class="tblcap">'
                      + m.group(1) + "</p>" + m.group(2) + "</div>", html)


def keep_with_next(html):
    """标题与紧随的第一个内容块绑在一起：Chrome 不认 break-after: avoid，
    只能靠 break-inside: avoid 的包裹块兜住孤立标题。"""
    return KEEP_RE.sub(lambda m: '<div class="hkeep">' + m.group(1) + m.group(2) + '</div>', html)


def mark_refs(html):
    return REF_RE.sub(r'<p class="ref">\1', html)


def render_body(text, figmap):
    text = re.sub(r"(?m)^ {2}(?=[-*] )", "    ", text)   # python-markdown 只认 4 空格嵌套
    lines = text.splitlines()
    out, buf = [], []

    def flush():
        if buf:
            seg = "\n".join(buf).strip()
            if seg:
                BLOCK.reset()
                out.append(BLOCK.convert(seg))
            buf.clear()

    i = 0
    while i < len(lines):
        ln = lines[i]

        m = re.match(r"^(#{1,3})\s+(.*)$", ln)
        if m:
            level, rest = len(m.group(1)), m.group(2).strip()
            en = ""
            if i + 1 < len(lines) and lines[i + 1].startswith("> "):
                en = lines[i + 1][2:].strip()
                i += 1
            flush()
            if en:
                sub = f'<span class="sh-en">{esc(en)}</span>'
            else:
                sub = ""
            if level == 1:
                out.append(f'<h1 class="doctitle">{inline(rest)}</h1>'
                           + (f'<div class="doctitle-en">{esc(en)}</div>' if en else ""))
            else:
                out.append(f'<h{level} class="sh">{inline(rest)}{sub}</h{level}>')
            i += 1
            continue

        m = FIG_RE.match(ln.strip())
        if m:
            flush()
            fid = int(m.group(2))
            src = figmap.get(m.group(1) + str(fid)) or figmap.get(str(fid))
            cap, j = "", i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines) and not re.match(r"^(#{1,3}\s|\[\[)", lines[j]):
                cap = inline(lines[j].strip())
                i = j
            if src:
                out.append(f'<figure class="fig"><img src="file:///{src}" alt="figure {fid}">'
                           f'<figcaption>{cap}</figcaption></figure>')
            else:
                # 没图时只留图注，别留红框
                out.append(f'<p class="figcap-only">{cap}</p>')
            i += 1
            continue

        buf.append(ln)
        i += 1
    flush()
    return keep_with_next(mark_refs(group_tables("\n".join(out))))


def prepare_part(part):
    md_path = part["md"]
    text = open(md_path, encoding="utf-8").read()
    start = part.get("start_at")
    if start:
        if start not in text:
            raise SystemExit(f"start_at marker not found in {md_path}: {start!r}")
        text = text[text.index(start):]
    for fid in part.get("drop_fig", []):
        lines, out, i, dropped = text.splitlines(), [], 0, False
        while i < len(lines):
            if not dropped and re.match(rf"^\[\[P?FIG:{fid}\]\]$", lines[i].strip()):
                dropped = True
                i += 1
                while i < len(lines) and not lines[i].strip():
                    i += 1
                if i < len(lines) and lines[i].startswith("**图"):
                    i += 1
                continue
            out.append(lines[i])
            i += 1
        text = "\n".join(out)
    return text


def find_chrome(explicit=None):
    if explicit and os.path.exists(explicit):
        return explicit
    for p in (r"C:\Program Files\Google\Chrome\Application\chrome.exe",
              r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
              r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
              r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"):
        if os.path.exists(p):
            return p
    raise SystemExit("找不到 Chrome/Edge，请在 manifest 里给 chrome 路径")


def add_toc(pdf_path, headings, meta):
    import fitz
    doc = fitz.open(pdf_path)
    pages = [p.get_text().replace("\n", "") for p in doc]
    toc, cursor = [], 0
    for lvl, text in headings:
        key = re.sub(r"\s+", "", text)[:12]
        if not key:
            continue
        for pno in range(cursor, len(doc)):
            if key in re.sub(r"\s+", "", pages[pno]):
                toc.append([lvl, text, pno + 1])
                cursor = pno
                break
    doc.set_toc(toc)
    doc.set_metadata(meta)
    doc.saveIncr()
    return len(toc)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest")
    ap.add_argument("--style", default=None, help="覆盖默认样式表（如 assets/style-compact.css）")
    ap.add_argument("--html-only", action="store_true")
    a = ap.parse_args()

    mf = json.load(open(a.manifest, encoding="utf-8"))
    out_pdf = mf["out"]
    workdir = mf.get("workdir") or os.path.dirname(a.manifest)

    figmap = dict(mf.get("figs") or {})
    figdir = mf.get("figdir")
    for part in mf["parts"]:                       # md 路径相对 manifest 所在目录解析
        if not os.path.isabs(part["md"]):
            part["md"] = os.path.join(workdir, part["md"])
    if figdir:
        for f in glob.glob(os.path.join(workdir, figdir, "fig*.png")):
            n = re.search(r"fig(\d+)", os.path.basename(f))
            if n:
                figmap.setdefault(str(int(n.group(1))), os.path.abspath(f))
    figmap = {k: os.path.abspath(v if os.path.isabs(v) else os.path.join(workdir, v))
              for k, v in figmap.items()}

    style_path = os.path.abspath(a.style) if a.style else STYLE
    css = open(style_path, encoding="utf-8").read()
    heads, body = [], []
    for k, part in enumerate(mf["parts"]):
        text = prepare_part(part)
        for hm in re.finditer(r'^(#{2,3})\s+(.*)$', text, re.M):
            heads.append((len(hm.group(1)) - 1, re.sub(r"\s+", " ", hm.group(2)).strip()))
        html = render_body(text, figmap)
        body.append(f'<div class="part">{html}</div>' if (k and part.get("break")) else html)

    meta_html = []
    if mf.get("title"):
        meta_html.append(f'<div class="doctitle">{mf["title"]}</div>')
    if mf.get("title_en"):
        meta_html.append(f'<div class="doctitle-en">{esc(mf["title_en"])}</div>')
    info = []
    if mf.get("authors"):
        info.append(f'<span class="authors">{mf["authors"]}</span>')
    if mf.get("affil"):
        info.append(str(mf["affil"]))
    if mf.get("note"):
        info.append(f'<span class="fn">{mf["note"]}</span>')
    if mf.get("source"):
        info.append(f'<span class="src">{mf["source"]}</span>')
    if mf.get("badge"):
        info.append(f'<span class="badge">{esc(mf["badge"])}</span>')
    if info:
        meta_html.append('<div class="meta">' + "<br>".join(info) + "</div>")

    lang = mf.get("lang", "zh-CN")
    doc_html = f"""<!DOCTYPE html><html lang="{lang}"><head><meta charset="utf-8">
<title>{esc(mf.get("title", ""))}</title><style>{css}</style></head><body>
<div class="titlewrap">{''.join(meta_html)}</div>
{''.join(body)}
</body></html>"""

    os.makedirs(os.path.dirname(out_pdf), exist_ok=True)
    html_path = os.path.splitext(out_pdf)[0] + ".html"
    open(html_path, "w", encoding="utf-8").write(doc_html)
    print("html:", html_path)

    if a.html_only:
        return

    chrome = find_chrome(mf.get("chrome"))
    cmd = [chrome, "--headless=new", "--disable-gpu", "--no-sandbox",
           "--no-pdf-header-footer", "--virtual-time-budget=20000",
           f"--print-to-pdf={out_pdf}", "file:///" + html_path.replace(os.sep, "/")]
    r = subprocess.run(cmd, capture_output=True, text=True, errors="replace", timeout=300)
    if r.returncode != 0:
        print(r.stderr[-1500:], file=sys.stderr)
        raise SystemExit(f"chrome print failed rc={r.returncode}")
    print("pdf :", out_pdf)

    n = add_toc(out_pdf, heads, dict(
        title=mf.get("title", ""), author=mf.get("author_meta", mf.get("authors", "")),
        subject=mf.get("subject", ""), keywords=mf.get("keywords", "中文翻译")))
    print(f"toc : {n}/{len(heads)} headings matched")


if __name__ == "__main__":
    main()
