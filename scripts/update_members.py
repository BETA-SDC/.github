#!/usr/bin/env python3

from __future__ import annotations

import json
import math
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path


ORG = os.environ.get("GITHUB_ORG", "BETA-SDC")
ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "profile"
MEMBERS_FILE = ROOT / "data" / "members.json"
FILES = [
    (PROFILE / "README.md", "Members"),
    (PROFILE / "README.zh.md", "成员"),
]


def fetch_members() -> list[str]:
    members: list[str] = []
    seen: set[str] = set()
    token = os.environ.get("GITHUB_TOKEN", "")
    page = 1

    while True:
        url = f"https://api.github.com/orgs/{ORG}/members?per_page=100&page={page}"
        request = urllib.request.Request(
            url,
            headers={
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "BETA-SDC-members-updater",
                **({"Authorization": f"Bearer {token}"} if token else {}),
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                payload = response.read().decode("utf-8")
        except urllib.error.URLError as exc:
            raise SystemExit(f"Failed to fetch members: {exc}") from exc

        chunk = json.loads(payload)
        if not isinstance(chunk, list):
            raise SystemExit(f"Unexpected API response on page {page}")
        if not chunk:
            break

        for item in chunk:
            login = item.get("login")
            if isinstance(login, str) and login not in seen:
                seen.add(login)
                members.append(login)

        page += 1

    return sorted(members, key=str.casefold)


def load_members() -> list[str]:
    if not MEMBERS_FILE.exists():
        raise SystemExit(f"Missing members data file: {MEMBERS_FILE}")
    data = json.loads(MEMBERS_FILE.read_text(encoding="utf-8"))
    if not isinstance(data, list) or not all(isinstance(item, str) for item in data):
        raise SystemExit(f"Invalid members data file: {MEMBERS_FILE}")
    return data


def save_members(members: list[str]) -> None:
    MEMBERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    MEMBERS_FILE.write_text(
        json.dumps(members, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def render_block(title: str, members: list[str]) -> str:
    cols = 4
    rows = math.ceil(len(members) / cols)
    cells = []
    index = 0
    for _ in range(rows):
        row = ["  <tr>"]
        for _ in range(cols):
            if index < len(members):
                login = members[index]
                row.append(
                    "    <td align=\"center\">\n"
                    f"      <a href=\"https://github.com/{login}\">\n"
                    f"        <img src=\"https://github.com/{login}.png?size=96\" width=\"72\" alt=\"{login}\" />\n"
                    f"        <br><sub>{login}</sub>\n"
                    "      </a>\n"
                    "    </td>"
                )
                index += 1
        row.append("  </tr>")
        cells.append("\n".join(row))

    return "\n".join(
        [
            "<!-- MEMBERS START -->",
            f'<h3 align="center">{title}</h3>',
            "",
            '<table align="center">',
            *cells,
            "</table>",
            "<!-- MEMBERS END -->",
        ]
    )


def update_file(path: Path, title: str, members: list[str]) -> bool:
    original = path.read_text(encoding="utf-8")
    pattern = re.compile(r"<!-- MEMBERS START -->.*?<!-- MEMBERS END -->", re.S)
    replacement = render_block(title, members)
    updated, count = pattern.subn(replacement, original)
    if count != 1:
        raise SystemExit(f"Could not find members block in {path}")
    if updated == original:
        return False
    path.write_text(updated, encoding="utf-8")
    return True


def main() -> int:
    refresh = "--refresh" in sys.argv[1:]
    if refresh:
        members = fetch_members()
        save_members(members)
    else:
        members = load_members()

    changed = False
    for path, title in FILES:
        changed |= update_file(path, title, members)

    print(f"Updated {len(members)} members in {len(FILES)} file(s).")
    return 0 if changed or refresh else 0


if __name__ == "__main__":
    raise SystemExit(main())
