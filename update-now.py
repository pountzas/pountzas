#!/usr/bin/env python3
"""Refresh the Now section in README.md from public Reach Panel releases.

Reads https://api.github.com/repos/pountzas/reach-Panel/releases (public).
Writes only the block between <!-- NOW:START --> and <!-- NOW:END -->.
Exits non-zero if the API fails, markers are missing, or no stable releases exist,
leaving README.md unchanged.
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

README = Path(__file__).resolve().parents[2] / "README.md"
START = "<!-- NOW:START -->"
END = "<!-- NOW:END -->"
API = "https://api.github.com/repos/pountzas/reach-Panel/releases?per_page=10"
ALLOWED_URL_PREFIX = "https://github.com/pountzas/reach-Panel/releases/"
MAX_ITEMS = 3


def fetch_releases() -> list[dict]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "pountzas-profile-readme",
    }
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(API, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.load(response)
    except urllib.error.URLError as exc:
        raise SystemExit(f"Failed to fetch Reach Panel releases: {exc}") from exc
    if not isinstance(data, list):
        raise SystemExit("Unexpected API response for Reach Panel releases")
    return data


def format_date(iso: str) -> str:
    # published_at is UTC; use the UTC calendar date so we don't invent a timezone.
    stamp = datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(timezone.utc)
    return f"{stamp.day} {stamp.strftime('%b')} {stamp.year}"


def safe_label(tag_name: str, release_name: str) -> str:
    raw = (release_name or tag_name or "release").strip()
    cleaned = re.sub(r"[\[\]()<>|`]", "", raw).strip() or "release"
    if re.search(r"reach\s*panel", cleaned, re.I):
        return cleaned
    return f"Reach Panel {cleaned}"


def build_block(releases: list[dict]) -> str:
    lines: list[str] = []
    for release in releases:
        if release.get("draft") or release.get("prerelease"):
            continue
        url = str(release.get("html_url") or "")
        if not url.startswith(ALLOWED_URL_PREFIX):
            continue
        published = release.get("published_at") or ""
        if not published:
            continue
        label = safe_label(str(release.get("tag_name") or ""), str(release.get("name") or ""))
        lines.append(f"- [{label}]({url}) — {format_date(str(published))}")
        if len(lines) == MAX_ITEMS:
            break
    if not lines:
        raise SystemExit("No stable public Reach Panel releases found")
    return "\n".join(lines) + "\n"


def replace_block(text: str, block: str) -> str:
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.DOTALL)
    if not pattern.search(text):
        raise SystemExit("NOW markers missing from README.md")
    return pattern.sub(START + "\n" + block + END, text)


def main() -> int:
    if not README.is_file():
        raise SystemExit(f"README.md not found at {README}")
    original = README.read_text(encoding="utf-8")
    updated = replace_block(original, build_block(fetch_releases()))
    if updated == original:
        print("Now section already up to date")
        return 0
    README.write_text(updated, encoding="utf-8")
    print(f"Updated {README}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
