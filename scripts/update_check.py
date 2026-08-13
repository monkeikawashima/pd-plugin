#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""配布元に新しい版が出ていないかを見て、起動時に知らせる。

    python3 <plugin>/scripts/update_check.py notify   通知文を stdout（無ければ何も出さない）
    python3 <plugin>/scripts/update_check.py fetch    配布元に問い合わせてキャッシュを更新

**起動を止めない。** notify はキャッシュを読むだけで、ネットワークには触らない。
キャッシュが古ければ fetch を裏で起動して、結果は次の起動から使う。
SessionStart は利用者が待たされる場所なので、ここで数秒使ってはいけない。

**失敗しても黙る。** 圏外・社内プロキシ・API の制限で取れないことは普通にある。
更新の案内が出ないだけで、作業は何も妨げない。

判定（規約）はここに書かない。判定者は validate.py 1つ。ここがやるのは
「配布元の版と手元の版を比べる」ことだけ。
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
MANIFEST = PLUGIN_ROOT / ".claude-plugin/plugin.json"

# 問い合わせる間隔。毎起動で叩くと API の制限に当たるうえ、版はそう頻繁には出ない。
TTL_SECONDS = 6 * 60 * 60
TIMEOUT_SECONDS = 8

# 通知に載せるリリース本文の行数。長い履歴を丸ごと出すと起動画面が埋まる。
NOTES_LINES = 8


# ---------------------------------------------------------------- 置き場所

def cache_file() -> Path:
    """キャッシュの置き場所。plugin 配下には置かない。

    plugin は `/plugin update` で丸ごと入れ替わる。中に置くと更新のたびに
    消え、更新直後に必ず1回ネットワークを叩くことになる。
    """
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData/Local")
    else:
        base = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache")
    return base / "pd-plugin" / "update-check.json"


def read_cache() -> dict:
    try:
        return json.loads(cache_file().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def write_cache(data: dict) -> None:
    path = cache_file()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass


# ---------------------------------------------------------------- 手元の版

def manifest() -> dict:
    try:
        return json.loads(MANIFEST.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def repo_slug() -> str | None:
    """`owner/name` を plugin.json の repository から取る（URL を直書きしない）。"""
    url = (manifest().get("repository") or "")
    if isinstance(url, dict):
        url = url.get("url") or ""
    m = re.search(r"github\.com[:/]+([^/]+/[^/#?]+?)(?:\.git)?/?$", url.strip())
    return m.group(1) if m else None


def as_tuple(version: str) -> tuple[int, ...]:
    """`v1.2.3` → `(1, 2, 3)`。文字列比較だと 1.10.0 < 1.9.0 になる。"""
    nums = re.findall(r"\d+", version or "")
    return tuple(int(n) for n in nums[:3]) or (0,)


# ---------------------------------------------------------------- 問い合わせ

def get_json(url: str) -> dict | list | None:
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "pd-plugin-update-check",
    })
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as res:
            return json.loads(res.read().decode("utf-8"))
    except Exception:  # noqa: BLE001 — 取れないことは普通にある。黙って諦める
        return None


def fetch() -> None:
    """配布元の最新版をキャッシュに書く。失敗しても時刻だけは進める。

    時刻を進めるのは、圏外のときに起動のたび問い合わせを撃ち続けないため。
    """
    data = read_cache()
    data["checked_at"] = int(time.time())

    slug = repo_slug()
    if slug:
        latest = get_json(f"https://api.github.com/repos/{slug}/releases/latest")
        if isinstance(latest, dict) and latest.get("tag_name"):
            data["latest"] = latest["tag_name"].lstrip("v")
            data["url"] = latest.get("html_url") or ""
            data["notes"] = (latest.get("body") or "").strip()
        else:
            # リリースを作っていない配布元もある。タグだけで判断する。
            tags = get_json(f"https://api.github.com/repos/{slug}/tags")
            if isinstance(tags, list) and tags:
                newest = max((t.get("name", "") for t in tags), key=as_tuple)
                data["latest"] = newest.lstrip("v")
                data["url"] = f"https://github.com/{slug}/releases/tag/{newest}"
                data["notes"] = ""
    write_cache(data)


def spawn_fetch() -> None:
    """fetch を裏で起動する。待たない。"""
    kwargs = {}
    if os.name == "posix":
        kwargs["start_new_session"] = True   # 親の終了に巻き込まれないように
    try:
        subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()), "fetch"],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, **kwargs,
        )
    except Exception:  # noqa: BLE001
        pass


# ---------------------------------------------------------------- 通知

def notice() -> str | None:
    """新しい版があるときだけ、そのまま画面に出せる文面を返す。"""
    current = manifest().get("version")
    if not current:
        return None

    data = read_cache()
    if int(time.time()) - int(data.get("checked_at") or 0) > TTL_SECONDS:
        spawn_fetch()

    latest = data.get("latest")
    if not latest or as_tuple(latest) <= as_tuple(current):
        return None

    slug = repo_slug() or ""
    changelog = f"https://github.com/{slug}/blob/main/CHANGELOG.md" if slug else ""
    release = data.get("url") or (
        f"https://github.com/{slug}/releases/tag/v{latest}" if slug else "")

    # 案内は1つに絞る。`/plugin update` だけでは上がらない（手元のカタログしか
    # 見ないため、古いカタログのときは**古い版へ戻す**）。取り直しと更新を
    # まとめた /pd:update を用意してあるので、利用者に順序を覚えさせない。
    lines = [
        f"🔔 pd plugin に更新があります — v{current} → v{latest}",
        "",
        "更新するには、これを実行してください:",
        "    /pd:update",
    ]

    notes = (data.get("notes") or "").splitlines()
    if notes:
        lines += ["", "この版の変更:"]
        lines += [f"    {line}" for line in notes[:NOTES_LINES] if line.strip()]
        if len(notes) > NOTES_LINES:
            lines.append("    …")

    if changelog:
        lines += ["", f"変更履歴   {changelog}"]
    if release:
        lines.append(f"リリース   {release}")
    lines += ["", "**判定のルールが変わった版では、昨日まで通っていたファイルが"
              "落ちることがあります。** 変更履歴を見てから更新してください。"]
    return "\n".join(lines)


def main() -> int:
    action = sys.argv[1] if len(sys.argv) > 1 else "notify"
    if action == "fetch":
        fetch()
    elif action == "notify":
        text = notice()
        if text:
            sys.stdout.write(text)
    else:
        print("使い方: update_check.py {notify | fetch}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
