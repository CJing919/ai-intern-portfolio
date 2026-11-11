# -*- coding: utf-8 -*-
"""Publish the repository to GitHub using the Git Data API.

No local git installation is required. The script:
1. Reads a token from GITHUB_TOKEN or .secrets/github_token.txt.
2. Creates a new public/private repository (or uses an existing empty one).
3. Uploads every text/binary file as a blob in one initial commit.
4. Creates refs/heads/main.

This is intentionally a one-shot bootstrap publisher, not a general git client.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SECRETS = ROOT / ".secrets" / "github_token.txt"
API = "https://api.github.com"

EXCLUDED_DIRS = {
    ".git", ".secrets", "__pycache__", ".venv", "venv", "env", "node_modules",
    ".pytest_cache", ".mypy_cache", ".ruff_cache", "dist", "build",
}
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".log", ".zip"}
EXCLUDED_NAMES = {".DS_Store", "Thumbs.db"}


def load_token() -> str:
    token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    if token:
        return token.strip()
    if SECRETS.exists():
        return SECRETS.read_text(encoding="utf-8").strip()
    raise SystemExit("No token found. Set GITHUB_TOKEN or run scripts/github_device_login.py first.")


def api(method: str, path: str, token: str, payload: dict | None = None) -> tuple[int, dict]:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(
        API + path,
        data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "ai-intern-portfolio-publisher",
            "Content-Type": "application/json",
        },
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            body = response.read().decode("utf-8")
            return response.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        try:
            parsed = json.loads(detail)
            message = parsed.get("message", detail)
        except json.JSONDecodeError:
            message = detail
        raise RuntimeError(f"GitHub API {method} {path} -> {exc.code}: {message}") from exc


def iter_files(skip_workflows: bool = False) -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT)
        if any(part in EXCLUDED_DIRS for part in rel.parts):
            continue
        if skip_workflows and rel.as_posix().startswith(".github/workflows/"):
            continue
        if path.name in EXCLUDED_NAMES:
            continue
        if path.suffix.lower() in EXCLUDED_SUFFIXES:
            continue
        files.append(path)
    return sorted(files, key=lambda p: p.relative_to(ROOT).as_posix())


def create_or_get_repo(owner: str, repo: str, private: bool, token: str, description: str) -> tuple[str, str]:
    _, user = api("GET", "/user", token)
    login = user["login"]
    target_owner = owner if owner and owner.lower() != login.lower() else login

    # Prefer an existing empty repo. This lets a fine-grained token work without
    # the Administration permission needed to create a repository.
    try:
        _, existing = api("GET", f"/repos/{target_owner}/{repo}", token)
        if existing.get("size", 0) > 0:
            raise SystemExit(
                f"Repository {target_owner}/{repo} already has content. "
                "Choose another repo name or empty it first."
            )
        return target_owner, existing["html_url"]
    except RuntimeError as exc:
        if "-> 404" not in str(exc):
            raise

    payload = {
        "name": repo,
        "description": description,
        "private": private,
        "auto_init": False,
        "has_issues": True,
        "has_projects": False,
        "has_wiki": False,
    }
    _, created = api("POST", "/user/repos", token, payload)
    return target_owner, created["html_url"]


def ensure_base_commit(owner: str, repo: str, token: str) -> str:
    """Return the current main commit, bootstrapping an empty repo if needed.

    GitHub's Git Data API returns 409 "Git Repository is empty" when creating
    blobs in a repo with no commits. A single Contents API write creates the
    initial commit and makes the Git Data API usable.
    """
    try:
        _, ref = api("GET", f"/repos/{owner}/{repo}/git/ref/heads/main", token)
        return ref["object"]["sha"]
    except RuntimeError as exc:
        message = str(exc)
        if "-> 409" not in message and "-> 404" not in message:
            raise

    placeholder = "# ai-intern-portfolio\n\nInitializing the portfolio repository.\n"
    api(
        "PUT",
        f"/repos/{owner}/{repo}/contents/README.md",
        token,
        {
            "message": "chore: initialize repository",
            "content": base64.b64encode(placeholder.encode("utf-8")).decode("ascii"),
            "branch": "main",
        },
    )
    _, ref = api("GET", f"/repos/{owner}/{repo}/git/ref/heads/main", token)
    return ref["object"]["sha"]


def publish_via_contents(owner: str, repo: str, private: bool, token: str, description: str, skip_workflows: bool = False) -> str:
    """Fallback publisher using the Contents API, one file per commit.

    Some fine-grained tokens can create blobs but receive 403 on git/trees.
    The Contents API uses the same Contents permission and is more widely
    supported, at the cost of one commit per file.
    """
    target_owner, html_url = create_or_get_repo(owner, repo, private, token, description)
    ensure_base_commit(target_owner, repo, token)
    files = iter_files(skip_workflows=skip_workflows)
    print(f"Publishing {len(files)} files via Contents API to {target_owner}/{repo} ...")
    for index, path in enumerate(files, start=1):
        rel = path.relative_to(ROOT).as_posix()
        encoded_path = urllib.parse.quote(rel, safe="/")
        payload = {
            "message": f"Add {rel}",
            "content": base64.b64encode(path.read_bytes()).decode("ascii"),
            "branch": "main",
        }
        try:
            api("PUT", f"/repos/{target_owner}/{repo}/contents/{encoded_path}", token, payload)
        except RuntimeError as exc:
            if "-> 422" not in str(exc):
                raise
            _, existing = api("GET", f"/repos/{target_owner}/{repo}/contents/{encoded_path}?ref=main", token)
            payload["sha"] = existing["sha"]
            api("PUT", f"/repos/{target_owner}/{repo}/contents/{encoded_path}", token, payload)
        if index % 10 == 0 or index == len(files):
            print(f"  uploaded {index}/{len(files)}")
    return html_url


def publish(owner: str, repo: str, private: bool, token: str, description: str) -> str:
    target_owner, html_url = create_or_get_repo(owner, repo, private, token, description)
    files = iter_files()
    if not files:
        raise SystemExit("No files to publish.")

    base_sha = ensure_base_commit(target_owner, repo, token)
    print(f"Publishing {len(files)} files to {target_owner}/{repo} ...")
    tree_entries = []
    for index, path in enumerate(files, start=1):
        rel = path.relative_to(ROOT).as_posix()
        content = base64.b64encode(path.read_bytes()).decode("ascii")
        _, blob = api("POST", f"/repos/{target_owner}/{repo}/git/blobs", token, {"content": content, "encoding": "base64"})
        tree_entries.append({"path": rel, "mode": "100644", "type": "blob", "sha": blob["sha"]})
        if index % 10 == 0 or index == len(files):
            print(f"  uploaded {index}/{len(files)}")

    _, tree = api("POST", f"/repos/{target_owner}/{repo}/git/trees", token, {"tree": tree_entries})
    _, commit = api(
        "POST",
        f"/repos/{target_owner}/{repo}/git/commits",
        token,
        {
            "message": "Initial commit: AI product / Agent portfolio (synthetic data)",
            "tree": tree["sha"],
            "parents": [base_sha],
        },
    )
    try:
        api("POST", f"/repos/{target_owner}/{repo}/git/refs", token, {"ref": "refs/heads/main", "sha": commit["sha"]})
    except RuntimeError:
        api("PATCH", f"/repos/{target_owner}/{repo}/git/refs/heads/main", token, {"sha": commit["sha"], "force": False})
    try:
        api("PATCH", f"/repos/{target_owner}/{repo}", token, {"default_branch": "main"})
    except RuntimeError:
        pass
    return html_url


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish the portfolio to a new GitHub repository")
    parser.add_argument("--owner", default="", help="GitHub user or org; default authenticated user")
    parser.add_argument("--repo", default="ai-intern-portfolio")
    parser.add_argument("--visibility", choices=["public", "private"], default="public")
    parser.add_argument("--description", default="AI 产品 / Agent / 工作流自动化作品集（合成数据 Demo）")
    parser.add_argument("--via-contents", action="store_true", help="Use Contents API fallback (one commit per file)")
    parser.add_argument("--skip-workflows", action="store_true", help="Skip .github/workflows (needs Workflows permission)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    files = iter_files(skip_workflows=args.skip_workflows)
    print(f"Repository: {args.repo} ({args.visibility})")
    print(f"Files: {len(files)}")
    if args.dry_run:
        for path in files:
            print(" ", path.relative_to(ROOT).as_posix())
        return 0

    token = load_token()
    login = api("GET", "/user", token)[1]["login"]
    target_owner = args.owner or login
    print(f"Authenticated as: {login}")
    if args.via_contents:
        url = publish_via_contents(
            target_owner, args.repo, args.visibility == "private", token, args.description,
            skip_workflows=args.skip_workflows,
        )
    else:
        url = publish(target_owner, args.repo, args.visibility == "private", token, args.description)
    print(f"Published: {url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
