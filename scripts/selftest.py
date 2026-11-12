# -*- coding: utf-8 -*-
"""selftest.py — 不用真实论文，现场合成一份双栏 PDF，跑通整条流水线。

用法:
    python selftest.py [--keep]

覆盖: probe（版式/图注探测）→ extract（重排+裁图）→ build_pdf（排版+书签）→ qa（页数比）
无浏览器时跳过 PDF 渲染，其余步骤仍校验。任何一步不符合预期则退出码 1。
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile

import fitz  # PyMuPDF

import env

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable

BODY = ("Verification of modern processors requires a large amount of stimulus. "
        "A coverage-guided approach improves efficiency by focusing on new states. ")


def make_synthetic_pdf(path):
    """两页 A4：双栏、每栏 5 个独立文本块；第 2 页有节标题；第 1 页右下有矢量图 + 图注。"""
    doc = fitz.open()
    for pno in range(2):
        page = doc.new_page(width=595, height=842)
        page.insert_text((45, 28),
                         "Authorized licensed use limited to: SELFTEST. Downloaded on 2026.",
                         fontsize=6.5)          # 页眉噪声，抽取时必须被过滤
        if pno == 0:
            page.insert_textbox(fitz.Rect(50, 45, 545, 80),
                                "A Synthetic Two-Column Document for Pipeline Self-Test",
                                fontsize=15, fontname="helv")
        top = 95
        if pno == 1:
            page.insert_text((45, 100), "I. INTRODUCTION", fontsize=10.5, fontname="hebo")
            top = 112
        for x0, x1 in [(45, 285), (305, 545)]:
            for k in range(5):
                y0 = top + k * 100
                page.insert_textbox(fitz.Rect(x0, y0, x1, y0 + 92),
                                    (BODY * 3)[:240], fontsize=9, fontname="helv")
        if pno == 0:
            page.draw_rect(fitz.Rect(320, 640, 530, 720), color=(0.2, 0.3, 0.6), width=1.2)
            page.insert_text((320, 740), "Fig. 1: Synthetic figure caption for the self-test.",
                             fontsize=8)
    doc.save(path)
    doc.close()


def run(*args, **kw):
    r = subprocess.run([PY, *args], capture_output=True, text=True, errors="replace",
                       timeout=300, **kw)
    if r.returncode != 0:
        print(r.stdout[-1500:])
        print(r.stderr[-1500:], file=sys.stderr)
        raise SystemExit(f"FAILED: {os.path.basename(args[0])} rc={r.returncode}")
    return r.stdout


def main():
    env.utf8_stdio()
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep", action="store_true", help="保留临时目录便于排查")
    a = ap.parse_args()

    tmp = tempfile.mkdtemp(prefix="ptz-selftest-")
    src = os.path.join(tmp, "synthetic.pdf")
    make_synthetic_pdf(src)
    print(f"[1/4] 合成双栏 PDF: {src}")

    run(os.path.join(HERE, "probe.py"), src, "--outdir", tmp)
    plan = json.load(open(os.path.join(tmp, "plan.json"), encoding="utf-8"))
    print(f"      probe  : doctype={plan['doctype']} columns={plan['columns']} "
          f"caption={plan['caption']['mode']}({plan['caption']['hits']}) "
          f"headings={len(plan['headings'])} chunks={len(plan['chunks'])}")
    assert plan["columns"] in (1, 2), "栏数探测异常"
    assert plan["caption"]["hits"] >= 1, "没探测到 Fig. N 图注"
    print("[2/4] probe 通过")

    run(os.path.join(HERE, "extract.py"), src, tmp, "--fig-mode", "caption")
    man = json.load(open(os.path.join(tmp, "manifest.json"), encoding="utf-8"))
    raw = open(os.path.join(tmp, "raw.txt"), encoding="utf-8").read()
    print(f"      extract: chars={man['chars']} figures={len(man['figs'])}")
    assert man["chars"] > 500, "抽取字符数过少"
    assert len(man["figs"]) >= 1, "没裁出图"
    assert "Authorized licensed" not in raw, "页眉噪声没过滤掉"
    print("[3/4] extract 通过")

    md = os.path.join(tmp, "zh.md")
    open(md, "w", encoding="utf-8").write(
        "## I 引言\n> INTRODUCTION\n\n"
        "这是自测用的中文正文，用来验证排版、图注绑定和书签生成。\n\n"
        "[[FIG:1]]\n**图 1**：自测插图。\n\n"
        "| 模块 | 数值 |\n|---|---|\n| 加速比 | 2.23× |\n\n"
        "## 参考文献\n> REFERENCES\n\n"
        "[1] A. Author, “A Synthetic Reference,” in Proc. Self-Test, 2026, pp. 1–2.\n")
    book = os.path.join(tmp, "book.json")
    json.dump(dict(out=os.path.join(tmp, "out.pdf"), workdir=tmp,
                   title="自测文档", title_en="Self-Test Document",
                   authors="A · B", affil="¹ 某大学", badge="中文翻译版", lang="zh-CN",
                   parts=[{"md": "zh.md"}],
                   figs={"1": os.path.join(tmp, "figs", "fig01.png")}),
              open(book, "w", encoding="utf-8"), ensure_ascii=False)

    sys.path.insert(0, HERE)
    import doctor
    if not doctor.find_browser():
        print("[4/4] 跳过 PDF 渲染：未找到 Chrome/Edge（抽取链路已验证）")
    else:
        run(os.path.join(HERE, "build_pdf.py"), book)
        pdf = os.path.join(tmp, "out.pdf")
        d = fitz.open(pdf)
        print(f"      build  : pages={len(d)} toc={len(d.get_toc())}")
        assert len(d) >= 1, "PDF 未生成"
        assert len(d.get_toc()) >= 2, "书签异常"
        qa = run(os.path.join(HERE, "qa.py"), pdf, "--src", src)
        print("      qa     : " + " | ".join(
            l for l in qa.splitlines() if l.startswith(("pages", "toc", "vs src"))))
        print("[4/4] build + qa 通过")

    if a.keep:
        print("临时目录:", tmp)
    else:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\nSELFTEST PASS")


if __name__ == "__main__":
    main()
