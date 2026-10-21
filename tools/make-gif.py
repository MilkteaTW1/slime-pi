#!/usr/bin/env python3
"""Record docs/demo.<lang>.gif from the web page's ?demo mode.

Needs: playwright (pip install playwright; a Chrome/Edge install), ffmpeg on PATH.
Usage: python tools/make-gif.py [lang ...]     (default: en zh-TW)
"""
import http.server
import os
import shutil
import subprocess
import sys
import tempfile
import threading
from playwright.sync_api import sync_playwright

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SECONDS = 22  # about two laps of the demo script


class H(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path):
        path = path.split("?")[0]
        base = ROOT if path.startswith("/locales/") else os.path.join(ROOT, "web")
        return os.path.join(base, path.lstrip("/") or "index.html")

    def log_message(self, *a):
        pass


def record(lang, port):
    tmp = tempfile.mkdtemp()
    with sync_playwright() as p:
        try:
            b = p.chromium.launch(channel="chrome")
        except Exception:
            b = p.chromium.launch(channel="msedge")
        ctx = b.new_context(viewport={"width": 680, "height": 740}, record_video_dir=tmp,
                            record_video_size={"width": 680, "height": 740})
        page = ctx.new_page()
        page.goto(f"http://127.0.0.1:{port}/?demo={lang}")
        page.wait_for_timeout(SECONDS * 1000)
        ctx.close(); b.close()
    video = [os.path.join(tmp, f) for f in os.listdir(tmp)][0]
    out = os.path.join(ROOT, "docs", f"demo.{lang}.gif")
    vf = "fps=10,scale=480:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=96[p];[b][p]paletteuse=dither=bayer:bayer_scale=4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "1", "-i", video, "-vf", vf, out], check=True)
    shutil.rmtree(tmp, ignore_errors=True)
    print(out, round(os.path.getsize(out) / 1024), "KB")


if __name__ == "__main__":
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    for lang in sys.argv[1:] or ["en", "zh-TW"]:
        record(lang, srv.server_address[1])
