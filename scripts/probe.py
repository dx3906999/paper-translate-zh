# -*- coding: utf-8 -*-
"""probe.py — 翻译前先量一遍 PDF，产出「这是什么文档、怎么抽、怎么切」的计划。

用法:
    python probe.py <paper.pdf> [--outdir DIR] [--target-chars 12000]

输出:
    屏幕摘要 + <outdir>/plan.json
    plan.json: doctype / pages / size / columns / caption / images / chars / headings / chunks

支持的版式判断:
    双栏期刊会议（IEEE/ACM/USENIX） · 单栏报告与 arXiv · 海报 · 幻灯片
"""
import argparse
import json
import os
import re

try:
    import pymupdf as fitz          # PyMuPDF >= 1.24
except ImportError:                 # 旧版本只有 fitz
    import fitz

import env

import pdfcommon as pc

SEC_NUM = re.compile(r"^(?:(?:[IVXLC]+|[A-Z]|[0-9]+)(?:\.[0-9]+)*\.)\s+[A-Z\u4e00-\u9fff]")
SEC_NAME = re.compile(r"^(Abstract|Introduction|Related Work|Background|Preliminaries|"
                      r"Method(s|ology)?|Design|Implementation|Evaluation|Experiments?|Results?|"
                      r"Discussion|Conclusion(s)?|Future Work|References|Acknowledg(e)?ments?|"
                      r"Appendix|摘要|引言|相关工作|背景|方法|实现|实验|评估|讨论|结论|参考文献|致谢|附录)"
                      r"[\s:：]*$", re.I)


def doctype(doc):
    r = doc[0].rect
    w, h = r.width, r.height
    if w / max(h, 1) > 1.45 and h < 800:
        return "slides"
    if w > 1400 or h > 1900:
        return "poster"
    if len(doc) > 40:
        return "report"
    return "paper"


def headings(doc, body_size):
    """节标题。判据优先级：整行正是常见节名 > 编号开头 > 全大写的短行。

    IEEE 的 `I. INTRODUCTION` 与正文同字号、也不一定带 bold flag，所以不能只看字号。
    """
    out = []
    for pno, page in enumerate(doc):
        for b in page.get_text("dict")["blocks"]:
            for line in b.get("lines", []):
                spans = line.get("spans", [])
                if not spans:
                    continue
                text = "".join(s["text"] for s in spans).strip()
                if not text or len(text) > 80:
                    continue
                size = max(round(s["size"], 1) for s in spans)
                bold = any(s.get("flags", 0) & 16 for s in spans)
                named = bool(SEC_NAME.match(text))
                numbered = bool(SEC_NUM.match(text)) and len(text) <= 70
                caps = text.upper() == text and 4 <= len(text) <= 60
                # 常见节名必须整行匹配，避免把 "Abstract—..." 这种正文首行当成标题
                if named or ((numbered or caps) and (size >= body_size or bold)):
                    out.append((pno + 1, text, size))
    seen, dedup = set(), []
    for p, t, s in out:
        k = (p, re.sub(r"\s+", "", t)[:20])
        if k in seen:
            continue
        seen.add(k)
        dedup.append((p, t, s))
    return dedup


def chunk_plan(doc, heads, target=12000):
    """按页累计字符数切块，并把边界对齐到就近的节标题所在页。"""
    per_page = [len(p.get_text()) for p in doc]
    total = sum(per_page)
    cuts, cur = [], 0
    for i, c in enumerate(per_page, 1):
        cur += c
        if cur >= target and i < len(per_page):
            cuts.append(i)
            cur = 0
    head_pages = {p for p, _, _ in heads}
    snapped = []
    for c in cuts:
        cand = [p for p in (c - 1, c, c + 1) if p in head_pages]
        snapped.append(min(cand) if cand else c)
    bounds = [1] + [p + 1 for p in snapped] + [len(per_page) + 1]
    plan = []
    for a, b in zip(bounds, bounds[1:]):
        if a <= b - 1:
            plan.append(dict(pages=f"{a}-{b - 1}", chars=sum(per_page[a - 1:b - 1])))
    return plan, total


def main():
    env.utf8_stdio()
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--outdir", default=None)
    ap.add_argument("--target-chars", type=int, default=12000)
    a = ap.parse_args()

    doc = fitz.open(a.pdf)
    if len(doc) == 0:
        raise SystemExit("PDF 没有页面，无法探测")
    if doc.needs_pass:
        raise SystemExit("PDF 已加密，请先解密")
    body = pc.body_font_size(doc)
    kind = doctype(doc)
    cols = pc.detect_columns(doc)
    cap_name, cap_rx, cap_hits = pc.detect_caption(doc)
    imgs = pc.detect_images(doc)
    heads = [] if kind == "slides" else headings(doc, body)
    plan, total = chunk_plan(doc, heads, a.target_chars)

    print(f"doc      : {kind}   pages={len(doc)}   {pc.page_size_label(doc)}   chars={total}")
    print(f"layout   : {cols} 栏   body={body}pt   embedded images={imgs}")
    print(f"caption  : {cap_name} (命中 {cap_hits})  regex={cap_rx!r}")
    print(f"headings : {len(heads)}")
    for p, t, s in heads[:16]:
        print(f"   p{p:<3} {s:<5} {t[:60]}")

    if kind == "slides":
        print("  ! 这是幻灯片（横版 16:9）：不要走本流水线的排版，产出应为大纲/讲稿，"
              "见 references/pitfalls.md「不适合这套流程的输入」")
    elif kind == "poster":
        print("  ! 这是海报：文字按视觉框散落，抽取顺序会乱，需要模型按语义重组；"
              "图用 --fig-mode image")
    elif cols == 1 and cap_hits == 0:
        print("  ! 单栏且没有 'Fig. N' 图注：图用 --fig-mode image，或 none 只留图注文字")

    print(f"chunks   : {len(plan)}（目标 {a.target_chars} 字/块，已对齐节标题）")
    for c in plan:
        print(f"   pp{c['pages']:<9} {c['chars']:>6} chars")

    outdir = a.outdir or os.path.dirname(os.path.abspath(a.pdf))
    os.makedirs(outdir, exist_ok=True)
    path = os.path.join(outdir, "plan.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(dict(pdf=os.path.abspath(a.pdf), doctype=kind, pages=len(doc),
                       size=pc.page_size_label(doc), columns=cols, body_size=body,
                       caption=dict(mode=cap_name, regex=cap_rx, hits=cap_hits),
                       images=imgs, chars=total,
                       headings=[dict(page=p, text=t, size=s) for p, t, s in heads],
                       chunks=plan), f, ensure_ascii=False, indent=1)
    print("plan     :", path)


if __name__ == "__main__":
    main()
