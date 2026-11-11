# -*- coding: utf-8 -*-
"""GitHub OAuth device-flow helper.

This uses GitHub's public device-flow endpoint. The user opens the verification
URL, enters the one-time code, and approves access. The resulting token is
written to .secrets/github_token.txt (gitignored) and never printed.

The default client_id is the public GitHub CLI OAuth app id. The consent screen
will show "GitHub CLI"; this is expected. If you prefer your own OAuth app, set
GITHUB_OAUTH_CLIENT_ID.
"""

from __future__ import annotations

import argparse
import json
import os
import stat
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SECRETS = ROOT / ".secrets"
TOKEN_PATH = SECRETS / "github_token.txt"
DEVICE_INFO_PATH = SECRETS / "device_login.json"
DEFAULT_CLIENT_ID = "Iv1.b507a08c87ecfe98"
DEVICE_CODE_URL = "https://github.com/login/device/code"
TOKEN_URL = "https://github.com/login/oauth/access_token"
SCOPE = "repo read:user"


def post_form(url: str, data: dict[str, str]) -> dict:
    body = urllib.parse.urlencode(data).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "ai-intern-portfolio",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        raise RuntimeError(f"GitHub OAuth HTTP {exc.code}: {detail}") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description="GitHub device-flow login for the portfolio publisher")
    parser.add_argument("--client-id", default=os.getenv("GITHUB_OAUTH_CLIENT_ID", DEFAULT_CLIENT_ID))
    parser.add_argument("--scope", default=SCOPE)
    args = parser.parse_args()

    code = post_form(DEVICE_CODE_URL, {"client_id": args.client_id, "scope": args.scope})
    if "device_code" not in code:
        print("Failed to start device flow:", code, file=sys.stderr)
        return 1

    verification_uri = code.get("verification_uri", "https://github.com/login/device")
    SECRETS.mkdir(parents=True, exist_ok=True)
    DEVICE_INFO_PATH.write_text(
        json.dumps(
            {
                "verification_uri": verification_uri,
                "user_code": code["user_code"],
                "expires_in": int(code.get("expires_in", 900)),
                "started_at": int(time.time()),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print("=" * 64, flush=True)
    print("请在浏览器打开：", verification_uri, flush=True)
    print("输入一次性代码：", code["user_code"], flush=True)
    print("授权后回到这里等待，脚本会自动继续。", flush=True)
    print("=" * 64, flush=True)
    print("注意：授权页显示 GitHub CLI 是正常的；不会读取你的密码。", flush=True)

    interval = int(code.get("interval", 5))
    expires_in = int(code.get("expires_in", 900))
    deadline = time.time() + expires_in

    while time.time() < deadline:
        time.sleep(interval)
        result = post_form(
            TOKEN_URL,
            {
                "client_id": args.client_id,
                "device_code": code["device_code"],
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            },
        )
        error = result.get("error")
        if result.get("access_token"):
            SECRETS.mkdir(parents=True, exist_ok=True)
            TOKEN_PATH.write_text(result["access_token"], encoding="utf-8")
            try:
                os.chmod(TOKEN_PATH, stat.S_IRUSR | stat.S_IWUSR)
            except OSError:
                pass
            try:
                DEVICE_INFO_PATH.unlink(missing_ok=True)
            except OSError:
                pass
            print("授权成功，token 已写入 .secrets/github_token.txt（已 gitignore）。", flush=True)
            return 0
        if error == "authorization_pending":
            continue
        if error == "slow_down":
            interval += 5
            continue
        if error in {"expired_token", "access_denied", "incorrect_device_code"}:
            print("授权未完成：", error, file=sys.stderr)
            return 1
        print("未知错误：", result, file=sys.stderr)
        return 1

    print("授权超时，请重新运行。", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
