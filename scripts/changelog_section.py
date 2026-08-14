#!/usr/bin/env python3
"""CHANGELOG から1つの版のセクションを切り出し、Release の本文にする。

    python3 scripts/changelog_section.py 1.2.1

先頭に `###` 見出しだけを並べた要約を置き、その下に本文を丸ごと付ける。
理由は、この本文が**2か所**で読まれるため。

  - GitHub の Release ページ  … 全文が読まれる
  - 起動時の更新通知          … 先頭 8 行しか出ない（update_check.py の NOTES_LINES）

要約を先に置かないと、通知には長い箇条書きの途中までが出て切れる。
CHANGELOG の `###` 見出しは「追加 — 〇〇を扱えるようにした」の形で
既に要約になっているので、それを並べ替えるだけで両方が成立する。
"""

from __future__ import annotations

import pathlib
import re
import sys

CHANGELOG = pathlib.Path(__file__).resolve().parent.parent / "CHANGELOG.md"


def section(version: str) -> str:
    """`## [version]` から次の `## [` の手前までを返す（見出し行は含めない）。"""
    text = CHANGELOG.read_text(encoding="utf-8")
    # 見出し行そのものは Release のタイトル（v1.2.1）と重複するので落とす
    pattern = rf"^## \[{re.escape(version)}\].*?$(.*?)(?=^## \[|\Z)"
    found = re.search(pattern, text, re.M | re.S)
    if not found:
        raise SystemExit(f"CHANGELOG.md に「## [{version}]」の項目が無い")
    return found.group(1).strip()


def summary(body: str) -> list[str]:
    """`### 追加 — 〇〇` を `- 追加 — 〇〇` に畳んだ要約を返す。"""
    return [f"- {line[4:].strip()}" for line in body.splitlines()
            if line.startswith("### ")]


def main() -> int:
    if len(sys.argv) != 2:
        print("使い方: changelog_section.py <版>", file=sys.stderr)
        return 2

    body = section(sys.argv[1])
    head = summary(body)

    # 見出しが無い版（PATCH で箇条書きだけ、など）は本文をそのまま出す。
    # 通知の 8 行はその本文の先頭で埋まるが、要約が無いものを捏造しない。
    parts = ["\n".join(head), "---", body] if head else [body]
    sys.stdout.write("\n\n".join(parts) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
