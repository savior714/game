"""
serve_game.py — 게임 로컬 개발 서버
====================================
게임 디렉터리를 HTTP로 서빙하고 브라우저를 자동으로 엽니다.

사용법:
  python serve_game.py            → 메인 페이지 (index.html)
  python serve_game.py math       → 수학 게임 (math/index.html)
  python serve_game.py english    → 영어 게임 (english/index.html)
  python serve_game.py korean     → 국어 게임 (korean/index.html)
  python serve_game.py admin      → 관리자 대시보드 (admin/index.html)

배경 실행 (터미널 비점령):
  python serve_game.py math --no-browser   → 브라우저 없이 서버만 구동
"""

import http.server
import socketserver
import webbrowser
import sys
import os
import signal
import threading
import time

# ── SDD Config ───────────────────────────────────────────
PORT      = 3000
DIRECTORY = os.path.dirname(os.path.abspath(__file__))  # 스크립트 위치 기준

PATHS = {
    "":        "index.html",
    "math":    "math/index.html",
    "english": "english/index.html",
    "korean":  "korean/index.html",
    "marble":  "marble/index.html",
    "admin":   "admin/index.html",
}

# ── Handler ──────────────────────────────────────────────
class SilentHandler(http.server.SimpleHTTPRequestHandler):
    """액세스 로그를 INFO만 표시하는 핸들러."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def log_message(self, fmt, *args):
        # 404/500 등 에러만 출력, 정상 요청은 조용히
        if args and len(args) >= 2 and str(args[1]).startswith(('4', '5')):
            super().log_message(fmt, *args)

# ── Entry Point ──────────────────────────────────────────
def main():
    args         = [a for a in sys.argv[1:] if not a.startswith('--')]
    flags        = [a for a in sys.argv[1:] if a.startswith('--')]
    open_browser = '--no-browser' not in flags

    target_key  = args[0].strip('/') if args else ''
    target_path = PATHS.get(target_key, f"{target_key}/index.html")
    url         = f"http://localhost:{PORT}/{target_path}"

    try:
        with socketserver.TCPServer(("", PORT), SilentHandler) as httpd:
            httpd.allow_reuse_address = True
            print(f"")
            print(f"  🚀 Game Dev Server")
            print(f"  ─────────────────────────────────")
            print(f"  URL  : {url}")
            print(f"  Root : {DIRECTORY}")
            print(f"  Port : {PORT}")
            print(f"  ─────────────────────────────────")
            print(f"  Ctrl+C 로 서버 종료")
            print(f"")

            if open_browser:
                # 100ms 지연 후 브라우저 오픈 (서버 완전 기동 후)
                threading.Timer(0.1, lambda: webbrowser.open(url)).start()

            httpd.serve_forever()

    except OSError as e:
        if e.errno == 10048:  # Windows: Address already in use
            print(f"  ⚠️  포트 {PORT}이 이미 사용 중입니다.")
            print(f"  이미 실행 중인 서버의 URL: {url}")
            if open_browser:
                webbrowser.open(url)
        else:
            raise
    except KeyboardInterrupt:
        print(f"\n  서버 종료")


if __name__ == "__main__":
    main()
