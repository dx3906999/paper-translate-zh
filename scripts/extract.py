# -*- coding: utf-8 -*-
"""extract.py — 从 PDF 里抽出「可翻译的正文」和「可回贴的插图」。

用法:
    python extract.py <paper.pdf> <outdir> [--cols auto|1|2] [--cap-regex R]
                      [--fig-mode caption|image|none] [--dpi 300]

产物:
    <outdir>/raw.txt        重排后的正文，块首带 [[L]]/[[R]]/[[COLS]] 标记
    <outdir>/figs/figNN.png 插图
    <outdir>/manifest.json  {pdf, pages, chars, columns, figs:[{fig,page,file,px,caption}]}

三种取图模式:
    caption  按 `Fig. N:` 图注反推图区裁剪（IEEE/ACM 双栏最准，默认）
    image    直接取页面里嵌入的位图块（单栏、报告、图注格式不统一时用）
    none     不取图，只留文字（扫描件/海报，图注改由译者写成"见原 PDF 图 N"）
"""
import argparse
import json
import os
import re
import sys

import fitz

import env

import pdfcommon as pc

DEFAULT_CAP = r"^Fig(?:ure)?\.?\s*(\d+)\s*[:.]"
NOISE = [
    re.compile(r'^Authorized licensed use limited to'),
    re.compile(r'^\d{4} IEEE International Symposium'),
    re.compile(r'^Proc\. of '),
    re.compile(r'^\s*$'),
]
SUBCAP = re.compile(r'^\([a-zA-Z]\)\s')


def ordered_lines(page, cols):
    W = page.rect.width
    mid = W / 2.0
    rows = []
    for b in pc.text_blocks(page):
        if cols == 2:
            spans = (b["x0"] < mid - 12) and (b["x1"] > mid + 12)
            col = -1 if spans else (0 if b["x0"] < mid else 1)
        else:
            col = -1
        rows.append((col, round(b["y0"], 1), b["x0"], b["text"]))
    rows.sort(key=lambda t: (t[0], t[1], t[2]))
    out = []
    for col, _, _, text in rows:
        if any(p.search(text) for p in NOISE):
            continue
        tag = "COLS" if col == -1 else ("L" if col == 0 else "R")
        out.append((tag, text))
    return out


def clip_by_caption(doc, outdir, rx, dpi, min_h, header_cut=40):
    os.makedirs(outdir, exist_ok=True)
    found, seen = [], set()
    for pno, page in enumerate(doc):
        H, W = page.rect.height, page.rect.width
        mid = W / 2.0
        bl = pc.text_blocks(page)
        for b in bl:
            m = rx.match(b["text"])
            if not m:
                continue
            try:
                fig = int(m.group(1))
            except (ValueError, IndexError):
                continue
            if fig in seen or b["y1"] > H - 30 or b["y0"] < 30:
                continue
            if b["x0"] < mid and b["x1"] < mid + 20:
                cx0, cx1 = 45.0, mid - 8
            elif b["x0"] > mid - 20:
                cx0, cx1 = mid + 6, W - 45.0
            else:
                cx0, cx1 = 45.0, W - 45.0

            def in_col(o):
                return not (o["x1"] < cx0 + 20 or o["x0"] > cx1 - 20)

            above = [o for o in bl if o is not b and o["y1"] <= b["y0"] + 2
                     and o["y1"] >= header_cut and o["y0"] < H - 30
                     and in_col(o) and not SUBCAP.match(o["text"])]
            top = max([o["y1"] for o in above], default=header_cut)
            y0, y1 = max(top + 2, header_cut), b["y0"] - 1
            if y1 - y0 < min_h:
                below = [o for o in bl if o is not b and o["y0"] >= b["y1"] - 2
                         and o["y1"] < H - 30 and in_col(o)]
                nxt = min([o["y0"] for o in below], default=H - header_cut)
                if nxt - b["y1"] <= min_h:
                    continue
                y0, y1 = b["y1"] + 2, nxt - 2
            pix = page.get_pixmap(clip=fitz.Rect(cx0, y0, cx1, y1), dpi=dpi)
            name = f"fig{fig:02d}.png"
            pix.save(os.path.join(outdir, name))
            seen.add(fig)
            found.append(dict(fig=fig, page=pno + 1, file=f"figs/{name}",
                              px=[pix.width, pix.height], caption=b["text"][:160]))
    found.sort(key=lambda d: d["fig"])
    return found


def clip_by_image(doc, outdir, dpi):
    """直接取嵌入位图（按页内包围盒合并，避免同一图被切成碎片）。"""
    os.makedirs(outdir, exist_ok=True)
    found, n = [], 0
    for pno, page in enumerate(doc):
        rects = []
        for info in page.get_images(full=True):
            try:
                for r in page.get_image_rects(info[0]):
                    if r.width > 60 and r.height > 40:
                        rects.append(r)
            except Exception:
                continue
        if not rects:
            continue
        # 合并重叠/相邻的框
        rects.sort(key=lambda r: (r.y0, r.x0))
        merged = [rects[0]]
        for r in rects[1:]:
            last = merged[-1]
            if r.y0 <= last.y1 + 8 and not (r.x1 < last.x0 - 8 or r.x0 > last.x1 + 8):
                merged[-1] = last | r
            else:
                merged.append(r)
        for r in merged:
            n += 1
            pix = page.get_pixmap(clip=r, dpi=dpi)
            name = f"fig{n:02d}.png"
            pix.save(os.path.join(outdir, name))
            found.append(dict(fig=n, page=pno + 1, file=f"figs/{name}",
                              px=[pix.width, pix.height], caption=""))
    return found


def main():
    env.utf8_stdio()
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("outdir")
    ap.add_argument("--cols", default="auto", choices=["auto", "1", "2"])
    ap.add_argument("--cap-regex", default=None,
                    help="第一组必须是图号；不给就自动探测（IEEE: '^Fig\\\\.?\\\\s*(\\\\d+)'）")
    ap.add_argument("--fig-mode", default="caption", choices=["caption", "image", "none"])
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--min-fig-h", type=int, default=55)
    a = ap.parse_args()

    doc = fitz.open(a.pdf)
    if len(doc) == 0:
        raise SystemExit("PDF 没有页面，无法抽取")
    if doc.needs_pass:
        raise SystemExit("PDF 已加密，请先解密")
    cols = pc.detect_columns(doc) if a.cols == "auto" else int(a.cols)
    os.makedirs(a.outdir, exist_ok=True)

    chunks, chars = [], 0
    for i, page in enumerate(doc):
        chunks.append(f"\n\n========== PAGE {i + 1} / {len(doc)} ==========\n")
        for tag, text in ordered_lines(page, cols):
            chunks.append(f"[[{tag}]]\n{text}\n")
            chars += len(text)
    raw_path = os.path.join(a.outdir, "raw.txt")
    with open(raw_path, "w", encoding="utf-8") as f:
        f.write("".join(chunks))

    figs = []
    if a.fig_mode == "caption":
        pat = a.cap_regex
        if not pat:
            name, pat, hits = pc.detect_caption(doc)
            if not hits:
                pat = DEFAULT_CAP
            print(f"caption regex: {name} ({hits} hits) -> {pat}")
        figs = clip_by_caption(doc, os.path.join(a.outdir, "figs"), re.compile(pat, re.I),
                               a.dpi, a.min_fig_h)
    elif a.fig_mode == "image":
        figs = clip_by_image(doc, os.path.join(a.outdir, "figs"), a.dpi)

    manifest = dict(pdf=os.path.abspath(a.pdf), pages=len(doc), chars=chars,
                    columns=cols, raw=raw_path, figs=figs)
    with open(os.path.join(a.outdir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)

    print(f"pages={len(doc)} cols={cols} chars={chars} figures={len(figs)} -> {a.outdir}")
    for d in figs:
        print(f"  fig{d['fig']:>2}  p{d['page']:<3} {d['px']}  {d['caption'][:60]}")
    if not figs and a.fig_mode != "none":
        print("  ! 没抽到图：换 --fig-mode image，或 --cap-regex，或改成 none 只留图注"
              "（见 references/pitfalls.md 第 3–5 条）", file=sys.stderr)


if __name__ == "__main__":
    main()
