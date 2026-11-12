# -*- coding: utf-8 -*-
"""doctor.py — 环境自检：Python、依赖、浏览器、中文字体。

用法:
    python doctor.py [--json]

退出码: 0 全部就绪；1 缺必需项（缺 Pillow / 浏览器只警告，不算失败）。
"""
import argparse
import importlib
import json
import os
import platform
import shutil
import subprocess
import sys

import env

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def module_version(name):
    try:
        m = importlib.import_module(name)
    except Exception as e:
        return None, str(e)
    v = getattr(m, "__version__", None)
    if v is None and name == "fitz":
        try:
            v = m.version[0] if isinstance(m.version, (list, tuple)) else m.version
        except Exception:
            v = "?"
    return v or "?", None


def has_cjk_font():
    """尽力而为：Windows 查字体目录，Linux 查 fc-list，macOS 查系统字体目录。"""
    try:
        if platform.system() == "Windows":
            d = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
            return os.path.isdir(d) and any(
                f.lower().endswith((".ttf", ".ttc", ".otf")) for f in os.listdir(d))
        if platform.system() == "Darwin":
            return os.path.isdir("/System/Library/Fonts")
        if shutil.which("fc-list"):
            out = subprocess.run(["fc-list", ":lang=zh"], capture_output=True, text=True,
                                 errors="replace", timeout=10).stdout
            return bool(out.strip())
    except Exception:
        pass
    return None


def main():
    env.utf8_stdio()
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    fitz_v, fitz_err = module_version("pymupdf")
    if not fitz_v:
        fitz_v, fitz_err = module_version("fitz")
    md_v, md_err = module_version("markdown")
    pil_v, pil_err = module_version("PIL")
    browser = env.find_browser()

    info = dict(
        skill_dir=SKILL_DIR,
        python=sys.version.split()[0],
        executable=sys.executable,
        platform=f"{platform.system()} {platform.release()}",
        pymupdf=fitz_v or f"缺失 ({fitz_err})",
        markdown=md_v or f"缺失 ({md_err})",
        pillow=pil_v or f"缺失 ({pil_err})",
        browser=browser or "未找到",
        cjk_font=has_cjk_font(),
    )

    ok = bool(fitz_v and md_v)
    warn = []
    if not pil_v:
        warn.append("Pillow 缺失：qa.py --sheet 缩略图不可用（其余功能正常）")
    if not browser:
        warn.append("未找到 Chrome/Edge：无法渲染 PDF，可在 book.json 里指定 \"chrome\" 绝对路径")
    if info["cjk_font"] is False:
        warn.append("未检测到中文字体：PDF 里可能显示方框（装 Noto CJK 任意字体即可）")

    if a.json:
        print(json.dumps(dict(info, ok=ok, warnings=warn), ensure_ascii=False, indent=1))
    else:
        print(f"skill    : {info['skill_dir']}")
        print(f"python   : {info['python']}  ({info['executable']})")
        print(f"platform : {info['platform']}")
        print(f"pymupdf  : {info['pymupdf']}")
        print(f"markdown : {info['markdown']}")
        print(f"pillow   : {info['pillow']}")
        print(f"browser  : {info['browser']}")
        print(f"cjk font : {info['cjk_font']}")
        for w in warn:
            print(f"  ! {w}")
        print("result   :", "OK" if ok else "缺必需依赖，先 pip install -r requirements.txt")

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
