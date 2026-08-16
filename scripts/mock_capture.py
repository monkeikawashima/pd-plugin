#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""モックの HTML から「文言・色・要素」を抜き出して、モック台帳の雛形を作る。

    python3 <plugin>/scripts/mock_capture.py pd/mocks/dashboard.html
    python3 <plugin>/scripts/mock_capture.py mock.html --name 検索結果 --out -

**抽出をモデルにやらせない。** モックを読んで要約させると、そのたびに拾う量が
変わる。落ちた1行は「落ちた」と気づけないまま実装に渡り、あとから
「モックにはあったのに」になる。ここで機械的に全部出し、**捨てるなら台帳の上で
理由つきで捨てさせる**（`見送り` / `動的`）。

**判定はしない。** 判定者は validate.py 1つ。ここがやるのは抽出と、
validate.py が読める形に整えることだけ。既にある台帳は上書きしない
（`実装の目印` やトークンの対応づけを手で埋めたものが消えるため）。
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import unicodedata
from html.parser import HTMLParser
from pathlib import Path

# 中身を文言として拾わないタグ。ここを広げると本文が落ちる
SKIP_TAGS = {"script", "style", "noscript", "svg", "head", "title"}

# 文言を持つ属性。画面に出るが本文には現れないもの（空欄の案内・読み上げ名）。
# **ここを削ると、空状態やアイコンボタンの文言が丸ごと落ちる。**
TEXT_ATTRS = ("placeholder", "aria-label", "alt", "title", "value", "aria-placeholder")

# 要素として記録するタグ。「実装で落ちたら気づきたい単位」だけを持つ。
# div / span を入れると台帳が数百行になり、読まれなくなる
ELEMENT_TAGS = {
    "h1", "h2", "h3", "h4", "h5", "h6",
    "button", "a", "input", "select", "textarea", "label",
    "table", "th", "form", "nav", "dialog", "details", "summary",
    "img", "video", "canvas", "progress", "meter",
}

# 閉じタグの来ない要素
VOID_TAGS = {"input", "img", "br", "hr", "source", "track"}

COLOR_RE = re.compile(
    r"#[0-9a-fA-F]{3,8}\b"
    r"|\brgba?\([^)]{1,80}\)"
    r"|\bhsla?\([^)]{1,80}\)"
)

# CSS 変数の定義。既にトークン化されている色は、対応づけの手がかりになる
VAR_DEF_RE = re.compile(r"(--[A-Za-z0-9_-]+)\s*:\s*([^;}\n]+)")


def is_noise(text: str) -> bool:
    """文言として台帳に載せない文字列か。

    記号・数字だけの断片を載せると、実装との照合が「1」や「/」の有無を
    見にいくことになり、当たり前に当たる判定で台帳が埋まる。
    """
    if len(text) < 2:
        return True
    return not any(unicodedata.category(c)[0] == "L" for c in text)


class Extract(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.skip_depth = 0
        self.texts: list[str] = []          # 出現順。重複は後で潰す
        self.elements: list[tuple[str, str]] = []
        self._pending: list[list] = []      # [tag, ラベル] — 閉じるまで本文を待つ

    # -- 文言 ---------------------------------------------------------
    def _add_text(self, raw: str) -> None:
        for line in raw.splitlines():
            text = " ".join(line.split())
            if text and not is_noise(text):
                self.texts.append(text)

    def handle_data(self, data: str) -> None:
        if self.skip_depth:
            return
        self._add_text(data)
        if self._pending:
            label = " ".join(data.split())
            if label:
                self._pending[-1][1] = (self._pending[-1][1] + " " + label).strip()

    # -- タグ ---------------------------------------------------------
    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag in SKIP_TAGS:
            self.skip_depth += 1
            return
        if self.skip_depth:
            return
        values = dict(attrs)
        for name in TEXT_ATTRS:
            self._add_text(values.get(name) or "")
        if tag in ELEMENT_TAGS:
            label = ""
            for name in ("aria-label", "placeholder", "alt", "value", "name", "id"):
                if values.get(name):
                    label = " ".join(str(values[name]).split())
                    break
            # 閉じタグの来ない要素（input / img）は、待たずにその場で確定させる。
            # 待たせると親が閉じたときにまとめて捨てられ、**入力欄と画像が
            # 台帳から丸ごと落ちる**
            if tag in VOID_TAGS:
                self.elements.append((tag, label[:60]))
            else:
                self._pending.append([tag, label])

    def handle_startendtag(self, tag: str, attrs: list) -> None:
        self.handle_starttag(tag, attrs)
        if self._pending and self._pending[-1][0] == tag:
            self._close(tag)

    def handle_endtag(self, tag: str) -> None:
        if tag in SKIP_TAGS:
            self.skip_depth = max(0, self.skip_depth - 1)
            return
        if self.skip_depth:
            return
        self._close(tag)

    def _close(self, tag: str) -> None:
        for i in range(len(self._pending) - 1, -1, -1):
            if self._pending[i][0] == tag:
                _, label = self._pending.pop(i)
                self.elements.append((tag, label[:60]))
                del self._pending[i:]
                return


def dedupe(items: list) -> list:
    seen, out = set(), []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def colors(source: str) -> list[tuple[str, str]]:
    """色の生値と、既にトークン化されていれば その CSS 変数名。"""
    by_value: dict[str, str] = {}
    for name, value in VAR_DEF_RE.findall(source):
        found = COLOR_RE.search(value)
        if found:
            by_value.setdefault(found.group(0).lower(), name)
    out = []
    for raw in dedupe(m.group(0) for m in COLOR_RE.finditer(source)):
        out.append((raw, by_value.get(raw.lower(), "")))
    return out


def slug_of(path: Path, given: str | None) -> str:
    return given or path.stem


def render(name: str, mock_ref: str, data: Extract, source: str) -> str:
    texts = dedupe(data.texts)
    elements = dedupe(data.elements)
    lines = [
        f"# モック台帳: {name}",
        "",
        "モックと実装をつなぐ1枚。**実装はここに書かれたものを落とさずに写す。**",
        f"抽出は `scripts/mock_capture.py` が行った（手で数えない）。",
        "",
        f"- **モック**: `{mock_ref}`",
        "- **公開**: <Artifact の URL>",
        "- **実装**: 未着手",
        "",
        "## 1. 文言",
        "",
        "**一字一句そのまま実装する。** 変えるなら、変えた文言に書き換えてから"
        "実装する（台帳が現在の正）。",
        "状態は `実装` / `見送り: UXDR-xxx` / `動的: 理由` のいずれか。",
        "",
        "| # | 文言 | 状態 |",
        "|---|---|---|",
    ]
    for i, text in enumerate(texts, 1):
        lines.append(f"| {i} | {text.replace('|', '｜')} | 実装 |")
    if not texts:
        lines.append("| 1 | <文言> | 実装 |")

    lines += [
        "",
        "## 2. 色",
        "",
        "**モックの生値は実装に持ち込まない。** どのトークンに対応するかを埋める。"
        "対応するトークンが無い場合は、足すか、近い既存トークンに寄せる"
        "（`pd/specs/05-surface/design-tokens.md` が値の正）。",
        "",
        "| # | モックの値 | 使いどころ | トークン |",
        "|---|---|---|---|",
    ]
    found = colors(source)
    for i, (raw, var) in enumerate(found, 1):
        lines.append(f"| {i} | {raw} | <どこの色か> | {var or '<トークン名>'} |")
    if not found:
        lines.append("| 1 | — | 色を使っていない | — |")

    lines += [
        "",
        "## 3. 要素",
        "",
        "**実装の目印**には、実装側で検索して見つかる文字列を書く"
        "（コンポーネント名・`data-testid`・関数名）。ここが埋まっていないと、"
        "欠落を機械が見つけられない。",
        "",
        "| # | 要素 | 実装の目印 | 状態 |",
        "|---|---|---|---|",
    ]
    for i, (tag, label) in enumerate(elements, 1):
        shown = f"{tag}: {label.replace('|', '｜')}" if label else tag
        lines.append(f"| {i} | {shown} | <目印> | 実装 |")
    if not elements:
        lines.append("| 1 | <要素> | <目印> | 実装 |")
    lines.append("")
    return "\n".join(lines)


def project_root() -> Path:
    for key in ("PD_PROJECT_DIR", "CLAUDE_PROJECT_DIR"):
        value = os.environ.get(key)
        if value:
            return Path(value).resolve()
    return Path.cwd().resolve()


def default_out(root: Path, slug: str) -> Path:
    base = root / "pd" if (root / "pd").exists() else root
    return base / "specs" / "05-surface" / "mocks" / f"{slug}.md"


def main() -> int:
    ap = argparse.ArgumentParser(description="モックの HTML から台帳の雛形を作る")
    ap.add_argument("html", help="モックの HTML")
    ap.add_argument("--name", help="台帳の名前（既定: ファイル名）")
    ap.add_argument("--out", help="出力先。`-` で標準出力")
    ap.add_argument("--force", action="store_true",
                    help="既存の台帳を上書きする（手で埋めた対応づけは消える）")
    args = ap.parse_args()

    src = Path(args.html).resolve()
    if not src.exists():
        print(f"モックが見つからない: {args.html}", file=sys.stderr)
        return 2
    source = src.read_text(encoding="utf-8", errors="replace")

    parser = Extract()
    parser.feed(source)
    parser.close()

    root = project_root()
    try:
        mock_ref = src.relative_to(root).as_posix()
    except ValueError:
        mock_ref = src.as_posix()

    slug = slug_of(src, args.name)
    body = render(slug, mock_ref, parser, source)

    if args.out == "-":
        sys.stdout.write(body)
        return 0
    out = Path(args.out).resolve() if args.out else default_out(root, slug)
    if out.exists() and not args.force:
        print(f"既にある: {out}\n"
              f"上書きすると、手で埋めた対応づけ（実装の目印・トークン）が消える。"
              f"作り直すなら --force", file=sys.stderr)
        return 3
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(body, encoding="utf-8")
    print(f"✓ 台帳を作った: {out}")
    print("  文言 %d / 色 %d / 要素 %d"
          % (len(dedupe(parser.texts)), len(colors(source)), len(dedupe(parser.elements))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
