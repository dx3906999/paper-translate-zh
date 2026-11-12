# -*- coding: utf-8 -*-
"""qa.py — 交付前的三道机械检查 + 一页纸目视缩略图。

用法:
    python qa.py <translated.pdf> [--src 原文.pdf] [--sheet sheet.png] [--dpi 95]

打印:
    pages / toc / chars / 每页末行（找孤立标题）/ 页数比（对比原文）
产出:
    --sheet 指定的 PNG：每页缩略图拼成一张 contact sheet，用来目视版式
"""
import argparse
import os
import re

import fitz

import env


def main():
    env.utf8_stdio()
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--src", help="原文 PDF，用来算页数比")
    ap.add_argument("--sheet")
    ap.add_argument("--dpi", type=int, default=95)
    ap.add_argument("--cols", type=int, default=7)
    a = ap.parse_args()

    doc = fitz.open(a.pdf)
    toc = doc.get_toc()
    texts = [p.get_text() for p in doc]
    chars = sum(len(t) for t in texts)

    print(f"pages : {len(doc)}")
    print(f"toc   : {len(toc)} entries")
    print(f"chars : {chars}")

    if a.src:
        src_pages = len(fitz.open(a.src))
        ratio = len(doc) / max(src_pages, 1)
        flag = "OK" if 0.8 <= ratio <= 2.2 else "CHECK"
        print(f"vs src: {src_pages} -> {len(doc)}  ratio={ratio:.2f}  [{flag}]")

    # 孤立标题：某页最后一行很短且不带句末标点，下一页多半才是正文
    print("--- 页末检查（可能的孤立标题）---")
    for i, t in enumerate(texts):
        lines = [l.strip() for l in t.splitlines() if l.strip()]
        if not lines:
            continue
        last = lines[-1]
        suspicious = len(last) < 26 and not re.search(r"[。；：，、）】》.!?;:]$", last)
        if suspicious:
            print(f"  p{i + 1}: {last[:40]!r}")

    # 图/表/参考文献落点，便于人工抽检
    print("--- 结构落点 ---")
    for i, t in enumerate(texts):
        for kind, pat in (("图", r"^图\s?\d+\s?[：:]"), ("表", r"^表\s?[IVXivx0-9]+\s?[：:]"),
                          ("节", r"^(摘要|引言|结论|参考文献|附录|致谢)\s*$")):
            for m in re.finditer(pat, t, re.M):
                print(f"  p{i + 1:<3} {kind} {m.group(0)[:30]}")

    if a.sheet:
        from PIL import Image
        imgs = []
        for p in doc:
            pix = p.get_pixmap(dpi=a.dpi)
            imgs.append(Image.frombytes("RGB", (pix.width, pix.height), pix.samples))
        w = 300
        h = int(w * imgs[0].height / imgs[0].width)
        rows = (len(imgs) + a.cols - 1) // a.cols
        sheet = Image.new("RGB", (a.cols * w, rows * h), "white")
        for i, im in enumerate(imgs):
            sheet.paste(im.resize((w, h)), ((i % a.cols) * w, (i // a.cols) * h))
        sheet.save(a.sheet)
        print(f"sheet : {a.sheet}  {sheet.size}")


if __name__ == "__main__":
    main()
