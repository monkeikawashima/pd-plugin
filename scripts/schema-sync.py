#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ボイスのスキーマが3箇所で一致しているかを見る。

    python3 scripts/schema-sync.py

規約を書いた文書と、判定するコードは別々に育つ。片方だけ変えると
「文書どおりに書いたのに弾かれる」という、原因の分かりにくい事故になる。
人はドキュメントを見て書き、検証器がそれを弾くため、現場にはどちらが
正しいかを判断する材料が無い（skills/analyze/uiux/rules/05-operations.md §6）。

一致を注意力に委ねず、ここで機械的に突き合わせる。

    skills/analyze/uiux/voice-schema.md   人が読む正本
    scripts/voices.mjs               記録するときに弾く
    scripts/validate.py              検証するときに弾く

違反があれば終了コード 1。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# 突き合わせる項目。frequency は範囲（整数）なので enum ではない。
# speaker_role は v1.0.0 で enum をやめた（業種で役割名が変わるため）。
# 値の一致は見られなくなったが、形式の正規表現は3箇所に散るので、それを突き合わせる。
KEYS = ["type", "source", "layer", "severity", "status"]

# speaker_role の許容形式。3箇所すべてにこの文字列が現れること
ROLE_PATTERN = "^[a-z][a-z0-9-]*$"
ROLE_FILES = [
    "skills/analyze/uiux/voice-schema.md",
    "scripts/voices.mjs",
    "scripts/validate.py",
]

errors: list[str] = []


def from_schema_md() -> dict[str, set[str]]:
    """人が読む表から拾う。`| `type` | `a` / `b` | … |` の2列目。"""
    text = (ROOT / "skills/analyze/uiux/voice-schema.md").read_text(encoding="utf-8")
    out: dict[str, set[str]] = {}
    for line in text.split("\n"):
        m = re.match(r"^\|\s*`([a-z_]+)`\s*\|(.+?)\|", line)
        if not m or m.group(1) not in KEYS:
            continue
        out[m.group(1)] = set(re.findall(r"`([^`]+)`", m.group(2)))
    return out


def _block(text: str, start: str) -> str:
    """`start` から対応する閉じ括弧までを粗く切り出す。"""
    i = text.index(start)
    depth, j = 0, i
    for j in range(i, len(text)):
        if text[j] in "{[":
            depth += 1
        elif text[j] in "}]":
            depth -= 1
            if depth == 0:
                break
    return text[i:j + 1]


def from_voices_mjs() -> dict[str, set[str]]:
    text = (ROOT / "scripts/voices.mjs").read_text(encoding="utf-8")
    block = _block(text, "const ENUMS = {")
    out: dict[str, set[str]] = {}
    for key in KEYS:
        m = re.search(rf"{key}:\s*\[(.*?)\]", block, re.S)
        if m:
            out[key] = set(re.findall(r'"([^"]+)"', m.group(1)))
    return out


def from_validate_py() -> dict[str, set[str]]:
    text = (ROOT / "scripts/validate.py").read_text(encoding="utf-8")
    block = _block(text, "VOICE_ENUMS = {")
    out: dict[str, set[str]] = {}
    for key in KEYS:
        m = re.search(rf'"{key}":\s*\{{(.*?)\}}', block, re.S)
        if m:
            out[key] = set(re.findall(r'"([^"]+)"', m.group(1)))
    return out


def main() -> int:
    sources = {
        "voice-schema.md": from_schema_md(),
        "voices.mjs": from_voices_mjs(),
        "validate.py": from_validate_py(),
    }

    for key in KEYS:
        got = {name: s.get(key) for name, s in sources.items()}
        missing = [n for n, v in got.items() if not v]
        if missing:
            errors.append(f"{key}: {' / '.join(missing)} から読み取れない（書式が変わった可能性）")
            continue
        if len({frozenset(v) for v in got.values()}) == 1:
            continue
        detail = "\n".join(f"      {n}: {' '.join(sorted(v))}" for n, v in got.items())
        errors.append(f"{key}: 3箇所で食い違っている\n{detail}")

    # enum ではなくなった speaker_role は、形式が3箇所で揃っているかを見る。
    # 片方だけ緩めると「文書どおりに書いたのに弾かれる」が再発する。
    missing = [f for f in ROLE_FILES
               if ROLE_PATTERN not in (ROOT / f).read_text(encoding="utf-8")]
    if missing:
        errors.append(f"speaker_role の形式 `{ROLE_PATTERN}` が "
                      f"{' / '.join(missing)} に無い")

    if errors:
        print("スキーマが一致していません\n")
        for e in errors:
            print(f"  ✗ {e}")
        print("\n3つすべてを同時に直す。片方だけ変えない。")
        return 1

    print(f"✓ スキーマは一致している（enum {len(KEYS)} 項目 + speaker_role の形式 × 3箇所）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
