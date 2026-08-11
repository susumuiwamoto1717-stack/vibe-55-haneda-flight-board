#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
羽田時刻表アプリのローカルサーバー。
これ経由で開くと、画面の「🔄 更新」ボタンから最新ダイヤを取得できる。

使い方:
    python3 server.py
    → ブラウザで http://localhost:8787 を開く
    停止は Ctrl+C

ボタンを押すと /api/update が fetch_haneda.py（＋キーがあれば fetch_aircraft.py）を
実行して flights_data.js を再生成し、ページが最新を読み直す。
"""
import http.server, socketserver, subprocess, json, os, sys

PORT = 8787
ROOT = os.path.dirname(os.path.abspath(__file__)) or "."
os.chdir(ROOT)


def run_update():
    subprocess.run([sys.executable, "fetch_haneda.py"], check=True, cwd=ROOT)
    if os.environ.get("AERODATABOX_KEY") or os.path.exists("aerodatabox_key.txt"):
        subprocess.run([sys.executable, "fetch_aircraft.py"], cwd=ROOT)


class Handler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # 常に最新を読ませる（flights_data.js のキャッシュ防止）
        self.send_header("Cache-Control", "no-store, max-age=0")
        super().end_headers()

    def do_GET(self):
        if self.path.split("?")[0] == "/api/update":
            try:
                run_update()
                payload = {"ok": True}
                code = 200
            except Exception as e:
                payload = {"ok": False, "error": f"{type(e).__name__}: {e}"}
                code = 500
            body = json.dumps(payload, ensure_ascii=False).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(body)
            return
        return super().do_GET()

    def log_message(self, fmt, *args):
        pass  # 静音


if __name__ == "__main__":
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", PORT), Handler) as httpd:
        print(f"▶ 起動しました → http://localhost:{PORT}  （停止=Ctrl+C）")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n停止しました")
