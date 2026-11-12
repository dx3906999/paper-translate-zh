# -*- coding: utf-8 -*-
"""pdfcommon.py — extract.py / probe.py 共用的版式探测。

目标：不预设「IEEE 双栏 + Fig. N: 图注」，而是先量一遍 PDF 再决定怎么切。
"""
import re

try:
    import pymupdf as fitz          # PyMuPDF >= 1.24
except ImportError:                 # 旧版本只有 fitz
    import fitz

CAP_PATTERNS = [
    ("fig-dot", r"^Fig(?:ure)?\.?\s*(\d+)\s*[:.]"),      # Fig. 1: / Figure 1.
    ("fig-space", r"^Figure\s+(\d+)\s"),                 # Figure 1 The ...
    ("zh", r"^图\s*(\d+)\s*[：:. ]"),                     # 图 1：...
    ("table", r"^TABLE\s+([IVXivx0-9]+)"),                # 仅用于识别表题
]


def text_blocks(page):
    out = []
    for b in page.get_text("blocks"):
        if b[6] != 0:
            continue
        out.append(dict(x0=b[0], y0=b[1], x1=b[2], y1=b[3], text=b[4].strip()))
    return out


def detect_columns(doc, sample_pages=8):
    """返回 1 / 2（列数）。判据：多数窄块完整落在中线一侧，且两侧都有块。"""
    W = doc[0].rect.width
    mid = W / 2.0
    left = right = span = 0
    for page in list(doc)[:sample_pages]:
        for b in text_blocks(page):
            w = b["x1"] - b["x0"]
            if w > 0.45 * W:
                span += 1
            elif b["x1"] < mid + 8:
                left += 1
            elif b["x0"] > mid - 8:
                right += 1
    if left >= 3 and right >= 3 and min(left, right) >= 0.25 * (left + right + span):
        return 2
    return 1


def detect_caption(doc, sample_pages=12):
    """挑命中数最多的图注模式，返回 (name, regex, hits)。"""
    best = ("none", None, 0)
    for name, pat in CAP_PATTERNS[:3]:
        rx = re.compile(pat, re.I)
        hits = 0
        for page in list(doc)[:sample_pages]:
            for b in text_blocks(page):
                if rx.match(b["text"]):
                    hits += 1
        if hits > best[2]:
            best = (name, pat, hits)
    return best


def detect_images(doc, sample_pages=8):
    """统计真正嵌进页面的位图块数量（不含 logo 级小图）。"""
    n = 0
    for page in list(doc)[:sample_pages]:
        for info in page.get_images(full=True):
            try:
                rects = page.get_image_rects(info[0])
            except Exception:
                continue
            if any(r.width > 60 and r.height > 40 for r in rects):
                n += 1
    return n


def page_size_label(doc):
    r = doc[0].rect
    w, h = r.width, r.height
    if abs(w - 595) < 12 and abs(h - 842) < 12:
        return "A4"
    if abs(w - 612) < 12 and abs(h - 792) < 12:
        return "Letter"
    return f"{w:.0f}x{h:.0f}pt"


def body_font_size(doc, sample_pages=6):
    """正文最常见字号，用来猜标题（更大号的短块）。"""
    from collections import Counter
    c = Counter()
    for page in list(doc)[:sample_pages]:
        for b in page.get_text("dict")["blocks"]:
            for line in b.get("lines", []):
                for s in line.get("spans", []):
                    c[round(s["size"], 1)] += len(s["text"])
    return c.most_common(1)[0][0] if c else 10.0
