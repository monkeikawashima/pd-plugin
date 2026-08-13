#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""hook の入口。hooks.json からはこのファイルだけを呼ぶ。

    python3 <plugin>/scripts/hook.py post-tool-use   < 入力JSON
    python3 <plugin>/scripts/hook.py stop            < 入力JSON
    python3 <plugin>/scripts/hook.py session-start   < 入力JSON

**判定は書かない。** 判定者は validate.py 1つで、ここがやるのは
「動くべき場面か」を決めて、その結果を hook の出力形式に整えることだけ。

hooks.json にシェルの構文（case / read / printf）や jq を書かない。
Windows では sh も jq も無く、hook が丸ごと動かなくなる。依存は
python3 のみに寄せる（validate.py が既に python3 を要求している）。
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
VALIDATE = PLUGIN_ROOT / "scripts" / "validate.py"

# plugin の hook は有効化した全プロジェクトで動く。pd を使わないリポジトリで
# 検証器が走ると毎回違反を出すため、この目印が無ければ何もしない。
MARKER = Path("pd") / "ledger.json"

# 検証の対象になるディレクトリ（プロジェクト側）。v1.4.0 から `pd/` 配下に
# 畳んだが、root 直下で運用している既存プロジェクトもそのまま拾う。
WATCHED = ("analyses", "voices", "simulations", "products")
BASE_DIR = "pd"

# 変更したら pd-skill-blueprint.md の同期が要るファイル（plugin 側）
SKILL_PARTS = (
    "skills/pd/SKILL.md",
    "skills/pd/framework/",
    "skills/pd/products/_template.md",
)

SYNC_MESSAGE = (
    "pd Skill を変更しました。同じターン内で pd-skill-blueprint.md の該当セクション"
    "（該当ファイルの「書くこと」/ §13 論点表 / §17 Acceptance Criteria）を更新して"
    "ください。加えて、利用者の操作・置き場所・守るべきルール・用語が変わった場合は"
    "README.md も更新してください。ユーザー確認は不要です。"
)


def project_dir() -> Path | None:
    value = os.environ.get("CLAUDE_PROJECT_DIR")
    return Path(value).resolve() if value else None


def is_pd_project(root: Path | None) -> bool:
    return bool(root) and (root / MARKER).exists()


def run_validate(*args: str) -> tuple[int, str]:
    """validate.py を別プロセスで実行する。

    import せず subprocess にするのは、CLI と同じ経路を通すため。
    python3 が PATH に無い環境でも動くよう sys.executable を使う。
    """
    proc = subprocess.run(
        [sys.executable, str(VALIDATE), *args],
        capture_output=True, text=True, env=os.environ.copy(),
    )
    return proc.returncode, (proc.stdout + proc.stderr).strip()


def emit(payload: dict) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False))


def edited_path(event: dict) -> str:
    tool_input = event.get("tool_input") or {}
    tool_response = event.get("tool_response") or {}
    return tool_input.get("file_path") or tool_response.get("filePath") or ""


def post_tool_use(event: dict) -> None:
    raw = edited_path(event)
    if not raw:
        return
    # Windows の区切りを吸収してから照合する
    posix = Path(raw).as_posix()

    if any(posix.endswith(p) or p in posix for p in SKILL_PARTS):
        emit({"hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": SYNC_MESSAGE,
        }})
        return

    root = project_dir()
    if not is_pd_project(root):
        return
    try:
        rel = Path(raw).resolve().relative_to(root)
    except ValueError:
        return
    parts = rel.parts
    if parts and parts[0] == BASE_DIR:
        parts = parts[1:]        # pd/analyses/… → analyses/…
    if not parts or parts[0] not in WATCHED:
        return

    code, out = run_validate(raw)
    if code != 0:
        emit({"decision": "block",
              "reason": "規約違反です。修正してから続けてください"
                        "（判定: pd plugin の validate.py）\n" + out})


def whole_project(_: dict) -> None:
    root = project_dir()
    if not is_pd_project(root):
        return
    code, out = run_validate()
    if code != 0:
        emit({"systemMessage": "⚠ 規約違反が残っています\n" + out})


EVENTS = {
    "post-tool-use": post_tool_use,
    "stop": whole_project,
    "session-start": whole_project,
}


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] not in EVENTS:
        print(f"使い方: hook.py {{{' | '.join(EVENTS)}}}", file=sys.stderr)
        return 2
    try:
        event = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        event = {}
    # hook 自身の失敗で作業を止めない。止めてよいのは規約違反だけ。
    try:
        EVENTS[sys.argv[1]](event)
    except Exception as e:  # noqa: BLE001
        print(f"pd hook: {e}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
