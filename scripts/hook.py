#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""hook の入口。hooks.json からはこのファイルだけを呼ぶ。

    python3 <plugin>/scripts/hook.py post-tool-use      < 入力JSON
    python3 <plugin>/scripts/hook.py stop               < 入力JSON
    python3 <plugin>/scripts/hook.py session-start      < 入力JSON
    python3 <plugin>/scripts/hook.py user-prompt-submit < 入力JSON

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

# 検証の対象になるディレクトリ（プロジェクト側）。v0.5.0 から `pd/` 配下に
# 畳んだが、root 直下で運用している既存プロジェクトもそのまま拾う。
WATCHED = ("analyses", "voices", "simulations", "products")
BASE_DIR = "pd"

# 判断そのものを変えうるファイル（plugin 側）。ここを触ったときだけ
# DECISIONS.md を促す。**中身の再掲は促さない** — 実物と重複する記述を
# 持たせると、必ず片方が古くなる（v1.2.0 で実際に起きた。DECISIONS.md 冒頭）。
DECISION_PARTS = (
    "scripts/validate.py",
    "scripts/hook.py",
    "hooks/hooks.json",
    "scripts/release.sh",
)

# 利用者から見える振る舞いが変わりうるファイル。README の同期を促す。
README_PARTS = (
    "skills/",
    "commands/",
)

DECISION_MESSAGE = (
    "pd の判定・仕組みを変更しました。次のどれかに当たる場合、同じターン内で "
    "DECISIONS.md に理由を追記してください — ①置き場所が分かれうる論点を決めた "
    "②判定を緩めた / 例外を作った ③実際に失敗を踏んで仕組みで塞いだ。"
    "どれにも当たらない変更（実装の整理・typo）なら追記は不要です。"
    "判定を追加したなら scripts/selftest.sh に壊れた例を1つ足してください。"
    "ユーザー確認は不要です。"
)

README_MESSAGE = (
    "pd の配布物を変更しました。利用者の操作・置き場所・守るべきルール・用語が"
    "変わった場合は、同じターン内で README.md も更新してください。"
    "変わっていなければ不要です。ユーザー確認は不要です。"
)


# ---------------------------------------------------- モックは必ず公開して渡す
#
# 「モックを作って」に対して、公開されたページ（Artifact）で返すか、ローカルに
# HTML を書いて終わるかは、これまでその場の判断に委ねられていた。**同じ頼み方を
# しても結果が変わる。** 利用者から見ると「やってくれたりやってくれなかったり」で、
# 何が条件なのか分からない。
#
# ここで場面の判定を機械にやらせる。要求の検知（入口）と、公開せずに終わろうと
# したときの差し戻し（出口）の2箇所で挟む。
#
# **この2つだけは `pd/ledger.json` を見ない**（DECISIONS.md §2）。他の hook と違い
# 当たったときしか何も出さないため、pd と無関係なリポジトリでも邪魔にならない。

# 印。注入した文そのものが会話に残り、次のターンで「モックの要求」として
# 読み返されるのを防ぐ（自分の出力を自分で検知する堂々巡りになる）。
MOCK_MARK = "[pd:mock-artifact]"

MOCK_WORDS = (
    "モック", "もっく", "mock",
    "ワイヤー", "wireframe",
    "画面イメージ", "画面案", "ui案", "ui 案", "デザイン案", "たたき台",
    "プロトタイプ", "prototype",
)

# 利用者が公開を望まないと明示した場合。ここを見ないと、断っても毎回促される。
MOCK_OPT_OUT = (
    "publishしない", "パブリッシュしない", "公開しない", "共有しない",
    "artifact不要", "artifactなし", "artifactはいらない", "artifactはやめて",
    "ローカルだけ", "ローカルのみ", "ファイルだけ", "ファイルで",
)

MOCK_MESSAGE = (
    f"{MOCK_MARK} モック／画面案の要求を検知しました。次の順で進めてください。"
    "① `artifact-design` skill を読み込む "
    "② HTML を書く "
    "③ **Artifact ツールで publish し、URL を返す**。"
    "ローカルにファイルを書いただけでは未完了です — 利用者はリンクで受け取ります。"
    "既に publish 済みのものへの修正なら、同じファイルパスで publish し直してください"
    "（同じ URL に上書きされます）。"
    "Artifact ツールが使えない環境なら、その旨を1行伝えてからファイルのパスを返してください。"
    "API のモック・テストダブルの話であれば、この指示は関係ありません。"
)

MOCK_BLOCK = (
    f"{MOCK_MARK} モックの HTML を書きましたが、Artifact で publish していません。"
    "**この状態は未完了です。** Artifact ツールで publish し、URL を返してから終えてください。"
    "利用者が公開を望んでいない場合、または Artifact ツールが使えない場合は、"
    "その理由を1行伝えたうえで終えて構いません。"
)

# publish の対象になる成果物。ここを広げると、モックの話をしながら書いた
# 無関係なファイルで差し戻すことになる。
MOCK_SUFFIX = (".html", ".htm")
ARTIFACT_TOOL = "Artifact"
WRITE_TOOLS = ("Write", "Edit", "MultiEdit")


def normalize(text: str) -> str:
    return "".join(text.split()).lower()


def wants_mock(text: str) -> bool:
    if MOCK_MARK in text:
        return False           # 自分が注入した文
    flat = normalize(text)
    if any(word in flat for word in MOCK_OPT_OUT):
        return False
    return any(word in flat for word in MOCK_WORDS)


def transcript_records(path: str) -> list[dict]:
    """会話の記録を読む。読めなければ空（差し戻さない側に倒す）。"""
    if not path:
        return []
    records = []
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except OSError:
        return []
    return records


def mock_left_unpublished(records: list[dict]) -> bool:
    """モックを頼まれ、HTML を書き、publish していない状態か。

    3つ揃ったときだけ差し戻す。「モックの話をした」だけでは止めない
    （この判定自体の相談で止まると使い物にならない）。
    """
    asked = wrote = published = False
    for rec in records:
        message = rec.get("message") or {}
        role = message.get("role") or rec.get("type")
        content = message.get("content")
        if isinstance(content, str):
            if role == "user" and wants_mock(content):
                asked = True
            continue
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            kind = block.get("type")
            if kind == "text":
                if role == "user" and wants_mock(block.get("text") or ""):
                    asked = True
            elif kind == "tool_use":
                name = block.get("name") or ""
                if name == ARTIFACT_TOOL:
                    published = True
                elif name in WRITE_TOOLS:
                    target = (block.get("input") or {}).get("file_path") or ""
                    if target.lower().endswith(MOCK_SUFFIX):
                        wrote = True
    return asked and wrote and not published


def user_prompt_submit(event: dict) -> None:
    """発言のたびに走る。モックの要求に当たったときだけ指示を足す。"""
    if not wants_mock(event.get("prompt") or ""):
        return
    emit({"hookSpecificOutput": {
        "hookEventName": "UserPromptSubmit",
        "additionalContext": MOCK_MESSAGE,
    }})


def plugin_relative(raw: str) -> str | None:
    """編集されたファイルが plugin 自身のものなら、plugin からの相対パスを返す。"""
    try:
        return Path(raw).resolve().relative_to(PLUGIN_ROOT).as_posix()
    except (ValueError, OSError):
        return None


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

    # 促しの対象は plugin 自身を編集したときだけ。利用プロジェクトにも
    # `skills/` や `commands/` はありうるため、部分一致では誤検知する。
    inside = plugin_relative(raw)
    if inside:
        if any(inside.startswith(p) for p in DECISION_PARTS):
            emit({"hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": DECISION_MESSAGE,
            }})
            return
        if any(inside.startswith(p) for p in README_PARTS):
            emit({"hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": README_MESSAGE,
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


def whole_project(event: dict) -> None:
    payload: dict = {}

    root = project_dir()
    if is_pd_project(root):
        code, out = run_validate()
        if code != 0:
            payload["systemMessage"] = "⚠ 規約違反が残っています\n" + out

    # 差し戻しは1回だけ。`stop_hook_active` は差し戻しから再開した合図で、
    # ここを見ないと publish できない環境で永久に終われなくなる。
    if not event.get("stop_hook_active"):
        records = transcript_records(event.get("transcript_path") or "")
        if mock_left_unpublished(records):
            payload["decision"] = "block"
            payload["reason"] = MOCK_BLOCK

    if payload:
        emit(payload)


def update_notice() -> str:
    """新しい版が出ていれば、その案内文。無ければ空。

    更新は放っておくと届かない（サードパーティの配布元は既定で自動更新されない）。
    起動時に知らせないと、手元だけ古いまま CI と判定が食い違う事故になる。
    """
    sys.path.insert(0, str(PLUGIN_ROOT / "scripts"))
    try:
        import update_check
        return update_check.notice() or ""
    except Exception:  # noqa: BLE001 — 案内が出ないだけ。作業は止めない
        return ""


def session_start(_: dict) -> None:
    """起動時: 残っている違反と、配布元の新しい版をまとめて1度だけ出す。"""
    root = project_dir()
    if not is_pd_project(root):
        return
    blocks = []
    code, out = run_validate()
    if code != 0:
        blocks.append("⚠ 規約違反が残っています\n" + out)
    notice = update_notice()
    if notice:
        blocks.append(notice)
    if blocks:
        emit({"systemMessage": "\n\n".join(blocks)})


EVENTS = {
    "post-tool-use": post_tool_use,
    "stop": whole_project,
    "session-start": session_start,
    "user-prompt-submit": user_prompt_submit,
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
