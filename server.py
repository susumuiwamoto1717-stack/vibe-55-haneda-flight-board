#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
羽田時刻表アプリのローカルサーバー。
これ経由で開くと、画面の「🔄 更新」ボタンから最新ダイヤを取得できる。

使い方:
    python3 server.py
    → ブラウザで http://localhost:8787 を開く
    停止は Ctrl+C

ボタンを押すと POST /api/update が fetch_haneda.py（＋キーがあれば fetch_aircraft.py）を
実行して flights_data.js を再生成し、ページが最新を読み直す。
公式APIへの負荷配慮のため、更新は最短 UPDATE_INTERVAL 秒に1回まで（超過は 429）。
"""
import http.server, socketserver, subprocess, json, os, sys, time, threading

PORT = 8787
ROOT = os.path.dirname(os.path.abspath(__file__)) or "."
os.chdir(ROOT)

UPDATE_INTERVAL = 60  # 秒。これ未満の間隔での再更新は 429 で拒否
_lock = threading.Lock()
_last_update = 0.0


def run_update():
    """ダイヤ+機材を更新。戻り値: 警告メッセージのリスト（空なら完全成功）"""
    warnings = []
    subprocess.run([sys.executable, "fetch_haneda.py"], check=True, cwd=ROOT)
    if os.environ.get("AERODATABOX_KEY") or os.path.exists("aerodatabox_key.txt"):
        r = subprocess.run(
            [sys.executable, "fetch_aircraft.py"],
            cwd=ROOT, capture_output=True, text=True,
        )
        if r.returncode != 0:
            msg = (r.stderr or r.stdout or "").strip().splitlines()
            tail = msg[-1] if msg else f"exit code {r.returncode}"
            print(f"⚠ fetch_aircraft.py 失敗: {tail}", file=sys.stderr)
            warnings.append(f"機材情報の更新に失敗しました: {tail}")
    return warnings


class Handler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # 常に最新を読ませる（flights_data.js のキャッシュ防止）
        self.send_header("Cache-Control", "no-store, max-age=0")
        super().end_headers()

    def _send_json(self, code, payload):
        body = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        global _last_update
        if self.path.split("?")[0] != "/api/update":
            self._send_json(404, {"ok": False, "error": "not found"})
            return
        if not _lock.acquire(blocking=False):
            self._send_json(429, {"ok": False, "error": "更新処理が実行中です。"})
            return
        try:
            wait = UPDATE_INTERVAL - (time.time() - _last_update)
            if wait > 0:
                self._send_json(429, {
                    "ok": False,
                    "error": f"公式APIへの負荷配慮のため、更新は{UPDATE_INTERVAL}秒に1回までです。あと{int(wait) + 1}秒お待ちください。",
                })
                return
            try:
                warnings = run_update()
                _last_update = time.time()
                self._send_json(200, {"ok": True, "warnings": warnings})
            except Exception as e:
                self._send_json(500, {"ok": False, "error": f"{type(e).__name__}: {e}"})
        finally:
            _lock.release()

    def do_GET(self):
        # /api/update は POST 限定（<img> やプリフェッチ等での意図しない起動を防ぐ）
        if self.path.split("?")[0] == "/api/update":
            self._send_json(405, {"ok": False, "error": "POST を使ってください。"})
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
