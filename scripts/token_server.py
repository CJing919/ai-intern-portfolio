# -*- coding: utf-8 -*-
"""Tiny localhost-only token setup page.

Open http://127.0.0.1:8765, paste a GitHub token, and the server validates it
against api.github.com before writing .secrets/github_token.txt. The token is
never printed or sent anywhere except GitHub's API.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import stat
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SECRETS = ROOT / ".secrets"
TOKEN_PATH = SECRETS / "github_token.txt"

PAGE = """<!doctype html>
<html lang="zh-CN"><meta charset="utf-8">
<title>GitHub Token Setup</title>
<style>
body{{font:15px/1.6 "Microsoft YaHei",system-ui,sans-serif;background:#f7faf8;color:#16241e;max-width:680px;margin:48px auto;padding:0 18px}}
.card{{background:#fff;border:1px solid #d9e5df;border-radius:14px;padding:24px;box-shadow:0 8px 24px rgba(20,50,38,.06)}}
h1{{font-size:22px;margin:0 0 8px}}p{{color:#65736c}}code{{background:#eaf4ef;padding:2px 6px;border-radius:4px}}
input{{width:100%;padding:11px;border:1px solid #cbd9d2;border-radius:8px;font:inherit}}
button{{margin-top:12px;background:#0e5a43;color:#fff;border:0;border-radius:8px;padding:10px 18px;font:inherit;cursor:pointer}}
.ok{{color:#0e5a43}}.err{{color:#a33}}
</style>
<div class="card">
<h1>GitHub Token Setup</h1>
<p>粘贴仅限 <code>ai-intern-portfolio</code> 仓库的 token。服务器只绑定 <code>127.0.0.1</code>，校验通过后写入 <code>.secrets/github_token.txt</code>，不会打印 token。</p>
{message}
<form method="post" action="/save">
  <input type="password" name="token" placeholder="github_pat_... 或 ghp_..." autocomplete="off" required>
  <button type="submit">校验并保存</button>
</form>
<p>权限：Contents = Read and write；Metadata = Read。发布后请撤销 token。</p>
</div>
</html>"""


def validate_token(token: str) -> tuple[bool, str]:
    request = urllib.request.Request(
        "https://api.github.com/user",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "ai-intern-portfolio-token-setup",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            data = json.loads(response.read().decode("utf-8"))
            return True, data.get("login", "unknown")
    except urllib.error.HTTPError as exc:
        return False, f"GitHub API 返回 {exc.code}，token 可能无效或权限不足。"
    except Exception as exc:
        return False, f"校验失败：{exc}"


def create_handler() -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "TokenSetup/1.0"

        def _send(self, status: int, body: str, content_type: str = "text/html; charset=utf-8") -> None:
            encoded = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(encoded)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(encoded)

        def do_GET(self) -> None:  # noqa: N802
            if self.path in ("/", "/index.html"):
                self._send(200, PAGE.format(message=""))
            else:
                self._send(404, "not found", "text/plain; charset=utf-8")

        def do_POST(self) -> None:  # noqa: N802
            if self.path != "/save":
                self._send(404, "not found", "text/plain; charset=utf-8")
                return
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length).decode("utf-8", "replace")
            token = urllib.parse.parse_qs(body).get("token", [""])[0].strip()
            if not token:
                self._send(400, PAGE.format(message='<p class="err">Token 为空。</p>'))
                return
            ok, detail = validate_token(token)
            if not ok:
                self._send(400, PAGE.format(message=f'<p class="err">{html.escape(detail)}</p>'))
                return
            SECRETS.mkdir(parents=True, exist_ok=True)
            TOKEN_PATH.write_text(token, encoding="utf-8")
            try:
                os.chmod(TOKEN_PATH, stat.S_IRUSR | stat.S_IWUSR)
            except OSError:
                pass
            message = (
                f'<p class="ok">已保存，授权账号：<b>{html.escape(detail)}</b>。'
                "可以关闭本页，回到对话回复“好了”。</p>"
            )
            self._send(200, PAGE.format(message=message))

        def log_message(self, fmt: str, *args: object) -> None:
            print(f"[token-setup] {self.address_string()} - {fmt % args}", flush=True)

    return Handler


def main() -> int:
    parser = argparse.ArgumentParser(description="Localhost GitHub token setup page")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), create_handler())
    print(f"Token setup: http://127.0.0.1:{args.port}", flush=True)
    print("Paste a repo-scoped token in the browser. Ctrl+C to stop.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping...", flush=True)
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
