# -*- coding: utf-8 -*-
"""env.py — 跨平台的浏览器探测与标准输出编码修正（不依赖 PyMuPDF）。

单独成模块的原因：doctor.py 需要在**检查 PyMuPDF 是否安装之前**就能找浏览器，
所以这里不能 import fitz。
"""
import os
import shutil
import sys

CHROME_CANDIDATES = [
    # Windows
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    # macOS
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    # Linux
    "/usr/bin/google-chrome",
    "/usr/bin/google-chrome-stable",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
    "/usr/bin/microsoft-edge",
    "/usr/bin/microsoft-edge-stable",
    "/snap/bin/chromium",
]

WHICH_NAMES = ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser",
               "microsoft-edge", "microsoft-edge-stable", "chrome", "msedge")


def find_browser():
    """返回 Chrome/Edge/Chromium 可执行文件的绝对路径；找不到返回 None。"""
    for p in CHROME_CANDIDATES:
        if p and os.path.exists(p):
            return p
    for name in WHICH_NAMES:
        p = shutil.which(name)
        if p:
            return p
    return None


def utf8_stdio():
    """Windows 控制台默认 cp1252/GBK，直接 print 中文会抛 UnicodeEncodeError。

    在 CI（GitHub Actions Windows runner）上必然踩到，所以每个脚本入口都调一次。
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
