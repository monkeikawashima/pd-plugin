#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pd（Product Discovery）の規約検証。

使い方:
    /pd:validate                                      Claude 経由（推奨）
    python3 <plugin>/scripts/validate.py              全体を検証
    python3 <plugin>/scripts/validate.py <path>...    指定ファイルだけ検証

検証対象のプロジェクトは次の順で決まる。

    1. 環境変数 PD_PROJECT_DIR
    2. 環境変数 CLAUDE_PROJECT_DIR（hook から渡る）
    3. カレントディレクトリ

このスクリプトは plugin 側にあり、判定される Note / Voice / Context は
プロジェクト側にある。両者は別のリポジトリになりうる。

規約の出典は skills/analyze/SKILL.md と、プロジェクト側の CLAUDE.md。
このスクリプトが唯一の判定者であり、規約を変えたらここも変える。
違反があれば終了コード 1。
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

# plugin 本体（skills/ hooks/ commands/ scripts/ を含む）
PLUGIN_ROOT = Path(__file__).resolve().parent.parent


def _project_root() -> Path:
    for key in ("PD_PROJECT_DIR", "CLAUDE_PROJECT_DIR"):
        value = os.environ.get(key)
        if value:
            return Path(value).resolve()
    return Path.cwd().resolve()


def _plugin_name(root: Path) -> str | None:
    """`.claude-plugin/plugin.json` の name。plugin のソースでなければ None。"""
    manifest = root / ".claude-plugin/plugin.json"
    if not manifest.exists():
        return None
    try:
        return json.loads(manifest.read_text(encoding="utf-8")).get("name")
    except (json.JSONDecodeError, OSError):
        return None


# 検証対象のプロジェクト。plugin リポジトリ自身を指すこともある（自己検証）
ROOT = _project_root()

# 自己検証かどうかを「パスが同じか」で決めない。
# hook 経由では PLUGIN_ROOT が ~/.claude/plugins/… （インストール済みの複製）を
# 指すため、plugin のソースを開いていてもパスは一致しない。その結果このリポジトリが
# 「pd を使うプロジェクト」と誤認され、**plugin 自身の CI に不要な checkout を要求する**
# 違反が毎ターン出ていた（v1.0.0 で修正）。**誤検知する判定は無視されるようになる。**
#
# 同じ plugin の別の複製かどうかは、マニフェストの name で見る。
SELF_CHECK = ROOT == PLUGIN_ROOT or (
    _plugin_name(ROOT) is not None and _plugin_name(ROOT) == _plugin_name(PLUGIN_ROOT)
)

# 自己検証のときは、インストール済みの複製ではなく**いま開いているソース**を見る
if SELF_CHECK:
    PLUGIN_ROOT = ROOT


# 分析データの置き場所（プロジェクト側）
# v0.6.0 で UI/UX の成果物（specs / decisions / validations / measurements / reviews）を
# ここに統合した。UI/UX 専用の別ディレクトリを作らない（二重管理になるため）。
DATA_DIRS = ("products", "analyses", "voices", "simulations",
             "specs", "decisions", "validations", "measurements", "reviews")


def _base_dir() -> Path:
    """分析データの根。v0.5.0 から `pd/` 配下に畳んだ。

    畳んだ理由は、消したいときに「どれが pd のものか」が分からなかったこと。
    root 直下の `products/` `analyses/` は名前から出所が読めない。

    既に root 直下で運用しているプロジェクトはそのまま読み続ける。移行を
    強制しない（台帳のキーはこの根からの相対パスなので、移動しても壊れない）。
    """
    new = ROOT / "pd"
    if any((new / d).exists() for d in DATA_DIRS):
        return new
    if any((ROOT / d).exists() for d in DATA_DIRS):
        return ROOT
    if LEGACY_PRODUCTS.exists():   # plugin 化より前のレイアウト
        return ROOT
    return new


# plugin 化より前は Context を skill の中に置いていた
LEGACY_PRODUCTS = ROOT / ".claude/skills/analyze/products"

BASE = _base_dir()
# 表示用の接頭辞。旧レイアウトでは空になる
BASE_REL = "" if BASE == ROOT else str(BASE.relative_to(ROOT)) + "/"


def _products_dir() -> Path:
    """Context の置き場所。plugin 化より前のレイアウトも読めるようにする。"""
    if not (BASE / "products").exists() and LEGACY_PRODUCTS.exists():
        return LEGACY_PRODUCTS
    return BASE / "products"


PRODUCTS_DIR = _products_dir()
PRODUCTS_REL = str(PRODUCTS_DIR.relative_to(BASE))
FRAMEWORK_DIR = PLUGIN_ROOT / "skills/analyze/framework"

RAW_EXT = {".csv", ".tsv", ".xlsx", ".sql", ".dump", ".sqlite", ".sqlite3",
           ".png", ".jpg", ".jpeg", ".pdf", ".mp3", ".m4a", ".wav"}

NOTE_KEYS = ["product", "date", "author", "question", "framework", "status"]
LABELS = ["Fact", "Interpretation", "Hypothesis", "Unknown"]

# 日本語の言い換えを必須とする見出し語
GLOSS_TERMS = ["Evidence", "Driver", "Root Cause", "Hypothesis",
               "Improvement Lever", "Experiment", "Decision", "Voice"]

PII_PATTERNS = [
    (r"[\w.+-]+@[\w-]+\.[\w.]+", "メールアドレス"),
    (r"0\d{1,4}-\d{1,4}-\d{3,4}", "電話番号"),
    (r"0[789]0\d{8}", "携帯番号"),
    (r"[^\w]@[A-Za-z0-9_]{3,}", "アカウント名（@）"),
    (r"[一-龥ぁ-んァ-ヶA-Za-z]{2,}(さん|様|氏|君|ちゃん)[^\w]", "実名らしい呼称"),
    (r"[一-龥ァ-ヶ]{2,4}(社長|部長|課長|店長|代表|専務|常務|主任|マネージャー)", "実名＋役職"),
]

# 日本の頻出姓（voices/ 内に現れたら匿名化漏れとみなす）
SURNAMES = """佐藤 鈴木 高橋 田中 伊藤 渡辺 山本 中村 小林 加藤 吉田 山田 佐々木 山口 松本
斎藤 斉藤 木村 清水 山崎 阿部 森 池田 橋本 石川 山下 小川 石井 長谷川 藤田 後藤 岡田
近藤 前田 村上 遠藤 青木 坂本 太田 藤井 福田 西村 三浦 藤原 岡本 松田 中川 中野 原田 小野
田村 竹内 金子 和田 中山 石田 上田 森田 柴田 宮崎 酒井 工藤 横山 宮本 内田 高木 安藤
島田 谷口 大野 高田 丸山 今井 河野 藤本 村田 武田 上野 杉山 増田 小島 平野 大塚 久保
松井 岩崎 桜井 野口 松尾 野村 渡部 菊地 木下 佐野 市川 水野 新井 小山 大西""".split()

# 台帳はプロジェクトごと。plugin 側には置かない（更新で消えるため）。
# 位置は両レイアウトで同じ（新: BASE 直下 / 旧: root 直下の pd/）。
# hook.py もこの位置を「pd を使うプロジェクトか」の目印にしている。
LEDGER = ROOT / "pd/ledger.json"
LEDGER_LOG = ROOT / "pd/ledger-log.md"
ACCEPT_HINT = "/pd:validate --accept で承認する"
# 追記のみ（過去の記録を書き換えない）。specs は現在値なので含めない。
# decisions / validations / measurements / reviews は「そのとき何を決めたか」の
# 記録であり、後から書き換えると判断の経緯が消えるため追記のみに含める。
IMMUTABLE_DIRS = ("analyses", "voices", "simulations",
                  "decisions", "validations", "measurements", "reviews")

# 新しい規約（反証 / 予測値 / 棄却条件の閾値）の適用開始日
RULES_FROM = "2026-08-12"

# 判定ごとの適用開始日。
#
# **`RULES_FROM` は「規約の運用を始めた日」であって、あとから足した判定を遡って
# 効かせるための日付ではない。** ここを分けていなかったため、判定を1つ足すたびに
# 運用開始日以降の全 Note がその判定の対象になっていた。DECISIONS.md §2 に
# 「新しい規約を既存の記録には適用しない」と決めてあるのに、**判定を足すたびに
# その原則が破れる構造**になっていた（v1.5.0 で実際に起き、書いた時点で存在しない
# 判定によって既存 Note が警告された）。
#
# 遡って効かせると、通すために過去を書き換えることになる。**追記のみの記録に
# 後付けの規約を適用しない。** 判定を足したら、その版の日付をここに書く。
# **書き忘れは検出される。** `check_new_rules` の中で `err(` / `warn(` を直に呼ぶと
# `check_rule_registry()` が違反にする。判定を足すには `note_err` / `note_warn` を
# 使うしかなく、そこには rule 名が要り、rule 名はこの表に無ければ違反になる。
# 規律ではなく仕組みで塞ぐ（v1.5.0 は「気をつける」で失敗した）。
RULE_SINCE = {
    # v1.0.0 以前からある判定（規約の運用開始と同時）
    "counter-evidence": "2026-08-12",
    "prediction": "2026-08-12",
    "rejection-threshold": "2026-08-12",
    "source-citation": "2026-08-12",
    "note-length": "2026-08-12",
    # あとから足した判定
    "segment-declaration": "2026-08-14",   # v1.5.0
}

# 規約の追加より前に書かれた Note。日付では分けられないため明示的に除外する
# （追加日と同じ日に既存と新規が混在するため。理由は DECISIONS.md §2）
# 現在は対象なし（該当した Note は削除済み）
LEGACY_NOTES: set[str] = set()

errors: list[str] = []
warnings: list[str] = []
notices: list[str] = []


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def load_ledger() -> dict[str, dict[str, str]]:
    """台帳。値は {"hash": ..., "seen": "YYYY-MM-DD"}。旧形式（文字列）も読める。"""
    if not LEDGER.exists():
        return {}
    try:
        raw = json.loads(LEDGER.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        errors.append("pd/ledger.json: JSON として壊れている")
        return {}
    out = {}
    for k, v in raw.items():
        out[k] = v if isinstance(v, dict) else {"hash": v, "seen": ""}
    return out


def save_ledger(data: dict[str, str]) -> None:
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    LEDGER.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                      encoding="utf-8")


def immutable_files() -> list[Path]:
    out = []
    for d in IMMUTABLE_DIRS:
        base = BASE / d
        if base.exists():
            out += sorted(base.rglob("*.md"))
    return out


def check_ledger(paths: list[Path], accept: bool, full: bool) -> None:
    """追記のみのファイルが書き換え・削除されていないかを見る（git の履歴の代わり）。"""
    ledger = load_ledger()
    today = datetime.now().strftime("%Y-%m-%d")
    changed, added, missing = [], [], []
    for path in paths:
        # 台帳のキーは分析データの根（BASE）からの相対パス。root 直下から
        # `pd/` 配下へ移しても、キーが変わらず既存の台帳がそのまま使える。
        rel = str(path.relative_to(BASE))
        h = digest(path)
        entry = ledger.get(rel)
        if entry is None:
            added.append(rel)
            ledger[rel] = {"hash": h, "seen": today}
        elif not entry.get("seen"):
            ledger[rel] = {"hash": entry.get("hash", h), "seen": today}
        elif entry.get("hash") != h:
            if entry.get("seen") in (today, ""):   # "" は旧形式からの移行分
                # 書いた当日の仕上げは許す（まだ「過去の記録」になっていない）
                ledger[rel] = {"hash": h, "seen": today}
            else:
                changed.append(rel)
                if accept:
                    ledger[rel] = {"hash": h, "seen": entry.get("seen", today)}

    if full:
        present = {str(p.relative_to(BASE)) for p in paths}
        missing = [rel for rel in ledger if rel not in present]
        if accept:
            for rel in missing:
                ledger.pop(rel, None)

    if changed and not accept:
        for rel in changed:
            errors.append(f"{BASE_REL}{rel}: 過去の記録が変更されている（追記のみのルール違反）。"
                          f"表記統一などの正当な変更なら {ACCEPT_HINT}")
    if missing and not accept:
        for rel in missing:
            errors.append(f"{BASE_REL}{rel}: 台帳にあるが存在しない（削除またはリネーム）。"
                          f"意図した操作なら {ACCEPT_HINT}")
    if accept or (full and not errors):
        save_ledger(ledger)
    if accept:
        if changed or missing:
            today = datetime.now().strftime("%Y-%m-%d")
            LEDGER_LOG.parent.mkdir(parents=True, exist_ok=True)
            LEDGER_LOG.touch(exist_ok=True)
            with LEDGER_LOG.open("a", encoding="utf-8") as f:
                if LEDGER_LOG.stat().st_size == 0:
                    f.write("# 承認の記録（追記のみ）\n\n"
                            "`--accept` で過去の記録の変更を承認したときに1行追加される。\n"
                            "承認は「表記の統一だけ」に限る。判断・数値・結論を変えた場合は、"
                            "承認せず新しい Note を書く。\n\n")
                for rel in changed:
                    f.write(f"- {today}  {BASE_REL}{rel}  変更を承認\n")
                for rel in missing:
                    f.write(f"- {today}  {BASE_REL}{rel}  削除/リネームを承認\n")
        for rel in changed:
            notices.append(f"変更を承認: {BASE_REL}{rel}")
        for rel in added:
            notices.append(f"台帳に追加: {BASE_REL}{rel}")
        for rel in missing:
            notices.append(f"台帳から削除: {BASE_REL}{rel}")


def rel_to_root(path: Path) -> str:
    """表示用の相対パス。plugin 側のファイルは plugin 基準で出す。"""
    for base in (ROOT, PLUGIN_ROOT):
        try:
            return str(path.relative_to(base))
        except ValueError:
            continue
    return str(path)


def rel_to_base(path: Path) -> str:
    """照合用の相対パス。分析データの根（BASE）から見る。

    命名規則や Note 本文の出典表記は、どちらのレイアウトでも
    `analyses/{プロダクト}/…` と書く。表示だけ `pd/` を前置する。
    """
    try:
        return str(path.relative_to(BASE)).replace("\\", "/")
    except ValueError:
        return rel_to_root(path)


def err(path: Path, msg: str, line: int | None = None) -> None:
    loc = rel_to_root(path) + (f":{line}" if line else "")
    errors.append(f"{loc}: {msg}")


def warn(path: Path, msg: str, line: int | None = None) -> None:
    loc = rel_to_root(path) + (f":{line}" if line else "")
    warnings.append(f"{loc}: {msg}")


def applies(path: Path, fm: dict[str, str]) -> bool:
    """新しい規約の対象か。明示的に除外された Note と、基準日より前のものは対象外。"""
    if rel_to_root(path) in LEGACY_NOTES:
        return False
    return fm.get("date", "") >= RULES_FROM


def applies_since(fm: dict[str, str], rule: str) -> bool:
    """あとから足した判定の対象か。書かれた時点で存在しない判定は適用しない。"""
    return fm.get("date", "") >= RULE_SINCE.get(rule, RULES_FROM)


def note_err(path: Path, fm: dict[str, str], rule: str,
             msg: str, line: int | None = None) -> None:
    """Note への違反。**適用開始日を通ったものだけ**を記録する。"""
    if applies_since(fm, rule):
        err(path, msg, line)


def note_warn(path: Path, fm: dict[str, str], rule: str,
              msg: str, line: int | None = None) -> None:
    """Note への警告。同上。"""
    if applies_since(fm, rule):
        warn(path, msg, line)


OPEN_CLOSE = {"（": "）", "(": ")", "「": "」", "『": "』", "[": "]", "{": "}"}


def _split_top_level(body: str) -> list[str]:
    """旧形式の1行定義を軸ごとに切る。**括弧の内側では切らない。**

    切るのは `・` `、` `／` だけ。**ASCII の `/` では切らない** — `新規/既存` のように
    軸の名前そのものに含まれるのが普通で、切ると「新規」「既存」という別々の軸に
    なってしまう（旧実装はこれをやっていた）。

    括弧を無視した分割も同じ壊れ方をする。`店舗セグメント（A 小規模 / B 比率高）` が
    「店舗セグメント（A 小規模」と「B 比率高）」に割れる。**割れた文字列は本文の
    どこにも現れないので、この書き方をした定義は原理的に通らなくなる。**

    そもそも区切り文字を推測しているのが弱点なので、新しくは frontmatter の
    構造化リストで宣言する（_segments_from_frontmatter）。
    """
    out, buf, stack = [], "", []
    for ch in body:
        if ch in OPEN_CLOSE:
            stack.append(OPEN_CLOSE[ch])
        elif stack and ch == stack[-1]:
            stack.pop()
        if not stack and ch in "・、／":
            out.append(buf)
            buf = ""
            continue
        buf += ch
    out.append(buf)
    return [t.strip() for t in out if t.strip()]


def _segments_from_frontmatter(text: str) -> list[dict[str, str]]:
    """frontmatter の構造化リストから読む（v1.5.0〜）。

        segments:
          - id: store_segment
            label: 店舗セグメント
            values: [A 小規模, B インバウンド比率高]

    区切り文字を推測しなくてよくなるのが本質。`values` に `/` が入っていても壊れない。
    """
    if not text.startswith("---"):
        return []
    end = text.find("\n---", 3)
    if end == -1:
        return []
    out: list[dict[str, str]] = []
    inside = False
    for line in text[3:end].split("\n"):
        stripped = line.strip()
        if not inside:
            if stripped == "segments:":
                inside = True
            continue
        if stripped and not line.startswith((" ", "\t", "-")):
            break                      # 次のキーに移った
        if stripped.startswith("- "):
            out.append({"id": "", "label": ""})
            stripped = stripped[2:].strip()
        if out and ":" in stripped:
            k, v = stripped.split(":", 1)
            if k.strip() in ("id", "label"):
                out[-1][k.strip()] = v.strip()
    return [s for s in out if s["label"] or s["id"]]


def required_segments(product: str) -> list[dict[str, str]]:
    """この Note が分解を宣言すべき Segment。id と label の組で返す。"""
    f = PRODUCTS_DIR / f"{product}.md"
    if not f.exists():
        return []
    text = f.read_text(encoding="utf-8")
    segs = _segments_from_frontmatter(text)
    if segs:
        for s in segs:
            s.setdefault("id", "")
            s["label"] = s["label"] or s["id"]
        return segs
    # 旧形式（`必須 Segment: A・B・C` の1行）。既存プロジェクトを読めなくしない。
    for line in text.split("\n"):
        if line.strip().startswith("必須 Segment:"):
            body = line.split(":", 1)[1]
            return [{"id": "", "label": t} for t in _split_top_level(body)]
    return []


# 分解できなかったことを宣言する語。**「引けない」を正規の状態として認める。**
# ペルソナ（未取得）・ジャーニー（一次情報なし）・画面仕様（デザイナー起案）に
# 既にある考え方で、Segment だけこれが無かった。
SEGMENT_UNKNOWN = ("Unknown", "未計測", "未取得", "不明", "引けない",
                   "分解できな", "分解していな")


def segment_declarations(text: str) -> list[tuple[str, str]]:
    """「宣言の位置」だけを拾う。

    散文の substring マッチをやめる理由。あれが測っていたのは**語が本文のどこかに
    出現するか**であって、分解されたかではない。だから両方向に外れた。

    - 偽陰性 — 「経過月数では分解できていない」という否定文でも通ってしまう
    - 偽陽性 — 誠実に「データが無いので分解できない」と書いた Note が落ちる

    後者が起きると、語を1つ本文に置けば警告が消える。**それは規律ではなく作文になる。**

    宣言と認めるのは**状態を伴う表の行だけ**。見出しや、たまたま語を含む無関係な
    表の行は数えない。状態の無い行を認めると、語をどこかの表に置けば消えてしまい、
    散文の substring マッチと同じ抜け道が残る。
    """
    out: list[tuple[str, str]] = []
    lines = text.split("\n")
    header = ""
    for i, line in enumerate(lines):
        s = line.strip()
        if not s.startswith("|"):
            header = ""
            continue
        if TABLE_SEPARATOR.match(line):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if len(cells) < 2:
            continue
        # 見出し行（次の行が区切り）は宣言ではなく、その表の性格を決める
        if i + 1 < len(lines) and TABLE_SEPARATOR.match(lines[i + 1]):
            header = " ".join(cells)
            continue
        rest = " ".join(cells[1:])
        if _is_declaration_table(header) or _states_something(rest):
            out.append((cells[0], rest))
    return out


def _is_declaration_table(header: str) -> bool:
    """その表は Segment の宣言表か。**見出しで見る。**

    行の中身の書き方（「分解済み」「74%」…）だけで判定すると、`取得済み` のように
    定型語も数値も使わない正しい宣言が落ちる。**誤検知が出た時点で「validate を
    通すための記述」が書かれ始める** ので、表の性格は見出しから読む。
    """
    return "Segment" in header or "セグメント" in header


def _states_something(rest: str) -> bool:
    """宣言表の外でも、状態を述べていれば宣言と認める。"""
    return (any(u in rest for u in SEGMENT_UNKNOWN)
            or "分解" in rest
            or re.search(r"[0-9０-９]", rest) is not None)


def check_segment_definition(path: Path, text: str) -> None:
    """必須 Segment の定義が、区切りを読み違えられる形で書かれていないか。

    v1.5.0 で旧形式の分割から ASCII の `/` を外した（`新規/既存` が2つの軸に
    割れていたため）。**その結果、`/` を区切りとして使っていた定義は、1つの長い
    軸名として扱われ、以後の Note が必ず警告される。** 黙って壊れる側に倒さない。
    """
    if _segments_from_frontmatter(text):
        return
    for i, line in enumerate(text.split("\n"), 1):
        if not line.strip().startswith("必須 Segment:"):
            continue
        body = line.split(":", 1)[1]
        if "/" in body and not any(c in body for c in "・、／"):
            warn(path, "必須 Segment の区切りが読み取れない（`/` は軸名の一部として"
                       "扱うため、全体が1つの軸になる）。frontmatter の "
                       "`segments:` で宣言する", i)
        return


def _has_reason(rest: str) -> bool:
    """「引けない」の宣言に、理由が添えられているか。"""
    for word in SEGMENT_UNKNOWN:
        rest = rest.replace(word, "")
    return len(rest.strip(" 　-—–|/・:：")) > 0


def known_products() -> set[str]:
    if not PRODUCTS_DIR.exists():
        return set()
    return {p.stem for p in PRODUCTS_DIR.glob("*.md")
            if p.stem not in {"_template", "other-product"}}


def frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    out = {}
    for line in text[3:end].strip().split("\n"):
        if ":" in line:
            k, v = line.split(":", 1)
            out[k.strip()] = v.strip()
    return out


# ---------------------------------------------------------------- パスと命名

PATTERNS = {
    "analyses": re.compile(r"^analyses/([a-z0-9-]+)/(\d{4})/(\d{8})-(\d{2})-([a-z][a-z0-9]*)\.md$"),
    # v0.6.0: 1ファイル = 1声。ID で引き当てるため VOICE-NNN を名前に持つ。
    # 年フォルダは captured_at（発言された日）の年。
    "voices": re.compile(r"^voices/([a-z0-9-]+)/(\d{4})/VOICE-(\d{3,})-([a-z][a-z0-9-]*)\.md$"),
    "simulations": re.compile(r"^simulations/([a-z0-9-]+)/(\d{4})/(\d{8})-([a-z][a-z0-9]*)\.md$"),
    "decisions": re.compile(r"^decisions/([a-z0-9-]+)/(\d{4})/UXDR-(\d{8})-(\d{2})-([a-z][a-z0-9-]*)\.md$"),
    # VP- は検証計画（仮説の採否）、RP- は探索計画（まだ仮説が無い段階）。
    # 別物だが置き場所は分けない。分けると片方が忘れられる。
    "validations": re.compile(r"^validations/([a-z0-9-]+)/(\d{4})/(?:VP|RP)-(\d{8})-(\d{2})-([a-z][a-z0-9-]*)\.md$"),
    "measurements": re.compile(r"^measurements/([a-z0-9-]+)/(\d{4})/MP-(\d{8})-(\d{2})-([a-z][a-z0-9-]*)\.md$"),
    "reviews": re.compile(r"^reviews/([a-z0-9-]+)/(\d{4})/DR-(\d{8})-(\d{2})-([a-z][a-z0-9-]*)\.md$"),
}

EXPECTED = {
    "analyses": "analyses/{プロダクト}/{年}/YYYYMMDD-NN-{主題1語}.md",
    "voices": "voices/{プロダクト}/{年}/VOICE-NNN-{主題1語}.md",
    "simulations": "simulations/{プロダクト}/{年}/YYYYMMDD-{主題1語}.md",
    "decisions": "decisions/{プロダクト}/{年}/UXDR-YYYYMMDD-NN-{主題1語}.md",
    "validations": "validations/{プロダクト}/{年}/VP-YYYYMMDD-NN-{主題1語}.md（探索は RP-）",
    "measurements": "measurements/{プロダクト}/{年}/MP-YYYYMMDD-NN-{主題1語}.md",
    "reviews": "reviews/{プロダクト}/{年}/DR-YYYYMMDD-NN-{主題1語}.md",
}


def check_path(path: Path, kind: str) -> tuple[str, str, str] | None:
    rel = rel_to_base(path)
    m = PATTERNS[kind].match(rel)
    if not m:
        err(path, f"命名規則に合わない。期待: {BASE_REL}{EXPECTED[kind]}")
        return None
    product, year, third = m.group(1), m.group(2), m.group(3)
    if product not in known_products():
        err(path, f"{BASE_REL}{PRODUCTS_REL}/{product}.md が存在しない（Context のないプロダクト）")
    # voices の3番目は ID の数字。日付ではないので突き合わせは check_voice が
    # frontmatter の captured_at に対して行う。
    if kind != "voices" and not third.startswith(year):
        err(path, f"年フォルダ {year} とファイル名の日付 {third} が一致しない")
    return product, year, third


# ------------------------------------------------------------------ 各種検証

def check_note(path: Path) -> None:
    got = check_path(path, "analyses")
    text = path.read_text(encoding="utf-8")
    fm = frontmatter(text)

    for key in NOTE_KEYS:
        if key not in fm:
            err(path, f"frontmatter に {key} が無い")
    if got:
        product, _, date = got
        if fm.get("product") and fm["product"] != product:
            err(path, f"frontmatter の product（{fm['product']}）がフォルダ（{product}）と違う")
        iso = f"{date[:4]}-{date[4:6]}-{date[6:]}"
        if fm.get("date") and fm["date"] != iso:
            err(path, f"frontmatter の date（{fm['date']}）がファイル名（{iso}）と違う")

    if "記述のラベル" not in text:
        err(path, "凡例ブロックが無い（H1 直後に「記述のラベル」の凡例を入れる）")
    else:
        missing = [l for l in LABELS if f"`{l}`" not in text.split("##")[0]]
        if missing:
            err(path, f"凡例に {' / '.join(missing)} の説明が無い")

    if not any(f"`{l}`" in text for l in LABELS):
        err(path, "Evidence のラベルが1つも使われていない")

    for i, line in enumerate(text.split("\n"), 1):
        if (line.startswith("## ") or line.startswith("### ")) \
                and any(t in line for t in GLOSS_TERMS):
            if "（" not in line:
                err(path, f"見出しに日本語の言い換えが無い: {line.strip()}", i)
        if "simulations/" in line:
            err(path, "予測データ（simulations/）を分析で参照している", i)
        if "`Fact`" in line:
            for word in HEDGES:
                if word in line:
                    err(path, f"`Fact` の行に推測を表す語「{word}」がある。"
                              f"Interpretation か Hypothesis にする", i)
                    break

    check_sections(path, text)
    if applies(path, fm):
        check_new_rules(path, text, fm)


HEDGE_FREE = re.compile(r"[0-9０-９]|≧|≦|以上|以下|％|%")
TABLE_SEPARATOR = re.compile(r"^\s*\|[\s\-:|]+\|\s*$")


def check_new_rules(path: Path, text: str, fm: dict[str, str]) -> None:
    """基準日以降の Note に適用する規約。"""
    secs = sections(text)

    # ③ 反証の節（Decision がある分析には必須）
    if any("Decision" in k for k in secs) and not any("反証" in k for k in secs):
        note_err(path, fm, "counter-evidence",
                 "「反証」の節が無い（この結論を最も強く否定する Evidence。箇条書き2〜3行で足りる）")

    # ① 予測値
    for name, body in secs.items():
        if "Experiment" in name and "予測" not in body:
            note_err(path, fm, "prediction",
                     f"「{name}」に予測値が無い（事前に「どれくらい動くと思うか」を書く）")

    # ② 棄却条件の閾値（表のヘッダ行は対象外）
    lines = text.split("\n")
    for i, line in enumerate(lines, 1):
        if "棄却条件" not in line or HEDGE_FREE.search(line):
            continue
        nxt = lines[i] if i < len(lines) else ""
        if TABLE_SEPARATOR.match(nxt):
            continue   # 表のヘッダ行
        note_err(path, fm, "rejection-threshold",
                 "棄却条件に観測可能な閾値が無い（数値・比較で書く。暫定なら明示する）", i)

    # ⑤ 必須 Segment（警告）
    # 沈黙している Note だけを警告する。分解できないことを理由つきで宣言した Note は
    # 通す — 誠実な文書と手抜きの文書を、判定器が区別できるようにするため。
    for sg in required_segments(fm.get("product", "")):
        keys = [k for k in (sg["label"], sg.get("id", "")) if k]
        hit = next(((head, rest) for head, rest in segment_declarations(text)
                    if any(k in head for k in keys)), None)
        if hit is None:
            note_warn(path, fm, "segment-declaration",
                      f"必須 Segment「{sg['label']}」の宣言が無い"
                      f"（分解した結果か、引けない理由かを表の行として書く。"
                      f"書き方は framework/kpi.md の「必須 Segment」を見る）")
        elif any(u in hit[1] for u in SEGMENT_UNKNOWN) and not _has_reason(hit[1]):
            note_warn(path, fm, "segment-declaration",
                      f"必須 Segment「{sg['label']}」が引けないとだけ書かれている"
                      f"（なぜ引けないか / いつ引けるようになるかを添える。"
                      f"理由の無い Unknown は、次に誰も追えない）")

    # ⑦ 出典と分量（警告）
    for name, body in secs.items():
        if name.startswith("Evidence") and re.search(r"[0-9０-９]", body) \
                and not re.search(r"出典|期間|条件|テーブル|集計", body):
            note_warn(path, fm, "source-citation",
                      f"「{name}」に数値があるが、出典（テーブル / 期間 / 条件）が無い")
    if len(text.split("\n")) > 300:
        note_warn(path, fm, "note-length",
                  "Note が 300 行を超えている（1回の分析として大きすぎる可能性）")


HEDGES = ["かもしれない", "と思われる", "だろう", "おそらく", "ように見える",
          "はず", "気がする", "recommend", "should"]

# 節があれば、その中に必須の語が含まれていること（規約の出典は framework/experiment.md）
SECTION_REQUIREMENTS = [
    ("Decision", [(["見直し", "再検討"], "見直し条件"),
                  (["確認者", "誰が"], "確認者（誰がいつ確認するか）"),
                  (["Confidence", "確からしさ"], "確からしさ（High / Medium / Low）")]),
    ("Experiment", [(["Success Criteria", "成功"], "Success Criteria"),
                    (["Decision Rule", "結果に対して", "→"], "Decision Rule")]),
    ("不足情報", [(["取得", "取り"], "どう取得できるか")]),
]


def sections(text: str) -> dict[str, str]:
    out, cur, buf = {}, None, []
    for line in text.split("\n"):
        if line.startswith("## "):
            if cur:
                out[cur] = "\n".join(buf)
            cur, buf = line[3:].strip(), []
        else:
            buf.append(line)
    if cur:
        out[cur] = "\n".join(buf)
    return out


def check_sections(path: Path, text: str) -> None:
    secs = sections(text)
    for key, requirements in SECTION_REQUIREMENTS:
        for name, body in secs.items():
            if key not in name:
                continue
            for words, label in requirements:
                if not any(w in body for w in words):
                    err(path, f"「{name}」に {label} が無い")


# v0.6.0: 1ファイル = 1声。UI を直す前に screen で引き当てられるようにするため、
# 分類キーを frontmatter に持たせる。書式の正本は skills/analyze/uiux/voice-schema.md。
# **この2つは必ず一致させること**（人は文書を見て書き、ここが弾く、という事故を避ける）。
VOICE_KEYS = ["id", "product", "type", "source", "speaker_role", "speaker_id",
              "captured_at", "captured_by", "layer", "severity", "frequency", "status"]
VOICE_OPTIONAL = {"object", "phase", "screen", "principles",
                  "linked_stories", "linked_uxdr", "tags", "context"}
VOICE_ENUMS = {
    "type": {"pain", "request", "negative", "positive", "question"},
    "source": {"interview", "in-app-feedback", "review", "support-ticket",
               "sales-call", "meeting", "user-validation"},
    "layer": {"戦略", "要件", "構造", "骨格", "表層", "未判定"},
    "severity": {"high", "medium", "low"},
    "status": {"未検証", "検証済み", "対応中", "解消", "却下"},
}
# v1.0.0: speaker_role は enum をやめた。役割の呼び名は業種で変わる（利用者 / 現場 / 管理者、
# 患者 / 医師、受講者 / 講師 …）。plugin 側で固定すると特定業種の語彙を全利用者に強制する。
# 値は pd/voices/taxonomy.json で各プロジェクトが宣言する。ここで見るのは形式だけ。
ROLE_RE = re.compile(r"^[a-z][a-z0-9-]*$")
# taxonomy.json が非空の項目だけ、その中の値に縛る（プロダクト固有語彙）
TAXONOMY_KEYS = ["object", "phase", "speaker_role"]

_taxonomy_cache: dict[str, list[str]] | None = None


def load_taxonomy() -> dict[str, list[str]]:
    """`pd/voices/taxonomy.json`。無ければ空（＝縛らない）。

    固有語彙は plugin ではなくプロジェクトが持つ。宣言されたときだけ縛る。
    """
    global _taxonomy_cache
    if _taxonomy_cache is None:
        _taxonomy_cache = {}
        path = BASE / "voices/taxonomy.json"
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                err(path, "JSON として読めない")
                data = {}
            for key in TAXONOMY_KEYS:
                val = data.get(key)
                if isinstance(val, list):
                    _taxonomy_cache[key] = [str(v) for v in val]
    return _taxonomy_cache
SPEAKER_ID = re.compile(r"[^\s（(]+[A-Z]-\d+")
QUOTE_FORM = re.compile(r"^[^\s:：]*[A-Za-z]-\d+[^:：]*[:：]")
VOICE_ID = re.compile(r"^VOICE-(\d{3,})$")


def check_voice(path: Path) -> None:
    got = check_path(path, "voices")
    text = path.read_text(encoding="utf-8")
    fm = frontmatter(text)

    for key in VOICE_KEYS:
        if key not in fm:
            err(path, f"frontmatter に {key} が無い")
    for key in fm:
        if key not in VOICE_KEYS and key not in VOICE_OPTIONAL:
            err(path, f"未知の frontmatter キー「{key}」。"
                      f"スキーマを勝手に増やさない（正本: skills/analyze/uiux/voice-schema.md）")

    for key, allowed in VOICE_ENUMS.items():
        val = fm.get(key)
        if val and val not in allowed:
            err(path, f"{key} が不正: 「{val}」（許容: {' / '.join(sorted(allowed))}）")

    role = fm.get("speaker_role", "")
    if role and not ROLE_RE.match(role):
        err(path, f"speaker_role の形式が不正: 「{role}」"
                  f"（英小文字・数字・ハイフンのみ。例: end-user）")

    taxonomy = load_taxonomy()
    for key in TAXONOMY_KEYS:
        allowed = taxonomy.get(key) or []
        val = fm.get(key)
        if allowed and val and val not in allowed:
            err(path, f"{key} が taxonomy.json にない: 「{val}」"
                      f"（許容: {' / '.join(allowed)}）")

    if got:
        product, year, num = got
        if fm.get("product") and fm["product"] != product:
            err(path, f"frontmatter の product（{fm['product']}）がフォルダ（{product}）と違う")
        m = VOICE_ID.match(fm.get("id", ""))
        if not m:
            err(path, f"id が VOICE-NNN の形式でない: 「{fm.get('id', '')}」")
        elif m.group(1) != num:
            err(path, f"id（{fm['id']}）がファイル名の番号（{num}）と違う")
        cap = fm.get("captured_at", "")
        if cap and not cap.startswith(year):
            err(path, f"年フォルダ {year} と captured_at {cap} が一致しない")

    freq = fm.get("frequency", "")
    if freq and (not freq.isdigit() or int(freq) < 1):
        err(path, f"frequency は 1 以上の整数: 「{freq}」")

    # frontmatter の speaker_id を数えないよう、本文だけを見る
    body = text.split("---", 2)[2] if text.startswith("---") and text.count("---") >= 2 else text
    if not SPEAKER_ID.search(body):
        err(path, "発話者が ID 形式で書かれていない（例: 利用者A-1 / 運用者B-2）")

    for i, line in enumerate(text.split("\n"), 1):
        t = line.strip()
        if ("「" in t or "『" in t) and not t.startswith(("#", ">", "|", "-", "*")):
            if not QUOTE_FORM.match(t):
                err(path, "発話行は「ID: 「発話」」の形で書く（例: 利用者A-1: 「…」）", i)

    for i, line in enumerate(text.split("\n"), 1):
        for pat, label in PII_PATTERNS:
            if re.search(pat, line):
                err(path, f"匿名化されていない可能性（{label}）。役割と ID で書く", i)
                break
        else:
            for name in SURNAMES:
                if name in line:
                    err(path, f"実名らしい語「{name}」が含まれている。役割と ID で書く", i)
                    break


# ------------------------------------------------------- UI/UX の成果物（v0.6.0）

UXDR_KEYS = ["product", "date", "layer", "kind", "status"]
UXDR_KINDS = {"決定", "未決定", "作業仮説", "棄却"}
LAYERS = {"戦略", "要件", "構造", "骨格", "表層"}


def check_uxdr(path: Path) -> None:
    """決定記録。決めなかったことと、作業仮説の棄却条件を必須にする。"""
    got = check_path(path, "decisions")
    text = path.read_text(encoding="utf-8")
    fm = frontmatter(text)

    for key in UXDR_KEYS:
        if key not in fm:
            err(path, f"frontmatter に {key} が無い")
    if got and fm.get("product") and fm["product"] != got[0]:
        err(path, f"frontmatter の product（{fm['product']}）がフォルダ（{got[0]}）と違う")
    if fm.get("layer") and fm["layer"] not in LAYERS:
        err(path, f"layer が不正: 「{fm['layer']}」（許容: {' / '.join(sorted(LAYERS))}）")
    if fm.get("kind") and fm["kind"] not in UXDR_KINDS:
        err(path, f"kind が不正: 「{fm['kind']}」（許容: {' / '.join(sorted(UXDR_KINDS))}）")

    secs = sections(text)
    if not any("決めなかった" in k for k in secs):
        err(path, "「決めなかったこと」の節が無い（決めたことだけ書いて終わらない）")
    else:
        body = next(v for k, v in secs.items() if "決めなかった" in k)
        if "無し" not in body and "なし" not in body:
            for label in ("何が分かれば", "いつまでに", "誰が"):
                if label not in body:
                    err(path, f"「決めなかったこと」に「{label}」の列が無い"
                              f"（3列すべて埋まらない未決定は、未決定ですらない）")

    if fm.get("kind") == "作業仮説":
        named = [v for k, v in secs.items() if "棄却条件" in k]
        # 表の見出し行（次行が区切り線）は列名であって条件ではない。
        # 「| 作業仮説 | 棄却条件 |」に閾値を求めると、正しい記録が落ちる。
        lines = text.split("\n")
        inline = []
        for i, line in enumerate(lines):
            if "棄却条件" not in line or line.strip().startswith("#"):
                continue
            if TABLE_SEPARATOR.match(line):
                continue
            if i + 1 < len(lines) and TABLE_SEPARATOR.match(lines[i + 1]):
                continue   # 見出し行
            inline.append(line)
        if not named and not inline:
            err(path, "kind が 作業仮説 だが棄却条件が無い（棄却条件のない仮説は記録しても意味がない）")
        # 節にまとめて書く形と、表の行に書く形の両方を許す。
        # どちらも「いつ棄却するか」を観測可能な量で示していなければ意味がない。
        for chunk in named + inline:
            if not HEDGE_FREE.search(chunk):
                err(path, "棄却条件に観測可能な閾値が無い（数値・比較で書く。暫定なら明示する）")

    if not any("根拠" in k for k in secs):
        err(path, "「根拠」の節が無い（一次情報 / 上位層 / 計測値。無いなら「なし」「未取得」と書く）")
    if not any("影響範囲" in k for k in secs):
        err(path, "「影響範囲」の節が無い（変わらなかったものも書く）")
    else:
        body = next(v for k, v in secs.items() if "影響範囲" in k)
        if "変わらなかった" not in body:
            err(path, "「影響範囲」に「変わらなかったもの」が無い"
                      "（次の人が同じ確認を繰り返す）")


def check_measurement(path: Path) -> None:
    """計測計画。時間側だけの報告を防ぎ、未取得を明示させる。"""
    check_path(path, "measurements")
    text = path.read_text(encoding="utf-8")
    if "未取得" not in text and not re.search(r"[0-9０-９]", text):
        err(path, "指標に値も「未取得」も無い（それらしい数字を置かず、未取得と書く）")
    if "品質" not in text:
        err(path, "品質側の軸が無い（時間側だけの改善報告をしない）")


def check_validation(path: Path) -> None:
    """検証計画。棄却しうる形になっているかだけを見る。"""
    check_path(path, "validations")
    text = path.read_text(encoding="utf-8")
    if "棄却" not in text:
        err(path, "棄却条件が無い（棄却しうる形でない仮説は検証できない）")
    if "観察" not in text and "行動" not in text:
        err(path, "行動観察の設計が無い（意見聴取だけで仮説を採否しない）")


def check_research(path: Path) -> None:
    """探索計画。検証（VP）と取り違えないための3点だけを見る。

    探索の失敗は「仮説の採否が決まらない」ではなく「**何も新しく分からない**」。
    最も多い原因は、答えを自分で言ってしまうこと（誘導質問）。
    """
    check_path(path, "validations")
    text = path.read_text(encoding="utf-8")
    if "対象者" not in text:
        err(path, "対象者の欄が無い（人数・役割は人間が決める。未定なら"
                  "「未定」と決める人・期限を書く）")
    if "聞かない" not in text:
        err(path, "「聞かないこと」が無い（誘導質問を先に排さないと、"
                  "知りたかったことが最初から答えの中に無い）")
    if "voices" not in text and "逐語" not in text:
        err(path, "逐語の記録先が無い（発話は要約せず pd/voices/ へ流す）")


def check_review(path: Path) -> None:
    """レビュー結果。見れば分かる課題と、検証しないと決まらない仮説を分ける。"""
    check_path(path, "reviews")
    text = path.read_text(encoding="utf-8")
    secs = sections(text)
    if not any("課題" in k for k in secs) or not any("仮説" in k for k in secs):
        err(path, "「見れば分かる課題」と「検証しないと決まらない仮説」に分かれていない")
    if "デザイナー起案" not in text and "VOICE-" not in text:
        err(path, "根拠のボイス（VOICE-…）が無い指摘に「デザイナー起案」の明記が無い")


# ------------------------------------------------------- 層の成果物（v1.2.0）
#
# specs/ は「現在値」であり追記のみではない。台帳は見ないが、**中身の空白の書き方**
# だけを見る。埋めれば進むが、埋めた瞬間に「誰も決めていないこと」が決定として
# 流通する箇所を、層ごとに1〜4個だけ固定する。
#
# 判定を増やしすぎない。specs は人が手で直すファイルであり、誤検知が出た時点で
# 「validate を通すための記述」が書かれ始める。**それは規律ではなく作文になる。**

# 反例として並べている行は対象外にする（禁止例を書いた文書が落ちるため）。
# COUNTER_EXAMPLE と同じ役割だが、あちらは配布物向けで定義がこの下にあるため分ける。
#
# **これは値の検査（HEX）専用の除外にする。** 語彙の検査（呼称・装飾属性）では
# use/mention（下）で判定する。理由は _is_mention の説明を見る。
SPEC_COUNTER = ("✗", "❌", "書かない", "書かず", "禁止",
                "記載しない", "持たせない", "混ぜない")


# 反例であることを示す印。**記号は閉じた集合なので、ここに足しても増え続けない。**
# 語彙リスト（SPEC_COUNTER）を捨てたとき、この2つまで一緒に捨てたのが v1.5.0 の誤り。
# 引用せずに `✗ ユーザーが迷う` と書いた反例行が、そのまま違反として拾われていた。
COUNTER_MARK = ("✗", "❌")


def _is_counter_example(line: str, word: str) -> bool:
    """その行は、対象語を使っている実例ではなく**反例**か。"""
    return any(c in line for c in COUNTER_MARK) or _is_mention(line, word)


def _is_mention(line: str, word: str) -> bool:
    """その行は語を「使って」いるのか、「言及して」いるだけか。

    規約文・用語定義・反例は、対象語を**引用して**書く（「ユーザー」を単独で使わない）。
    実際に曖昧な使い方をしている文は引用しない（ユーザーが不便）。**この非対称性は
    語尾の表現に依存しない。**

    かつては禁止表現の語彙（SPEC_COUNTER）を当てにいっていたが、日本語の否定表現は
    閉じた集合ではない。「書かない」を入れても「使わない」で漏れ、次は「用いない」
    「避ける」「控える」「非推奨」で漏れる。**リストに1語足す対処はモグラ叩きになる。**
    実際に glossary.md（呼称を決める当のファイル）が「使わない」で漏れて落ちていた。

    値の検査には持ち込まない。design-tokens.md では `#7c3aed` とバッククォート付きで
    色値を書くのが普通で、HEX の検査に引用除外を入れると検査が効かなくなる。
    """
    return re.search(rf"[「『\"'`]\s*{re.escape(word)}\s*[」』\"'`]", line) is not None

# 検証されていない断定が、検証済みの記述と同じ見た目で混ざる属性。
# **警告に留める**（業種によっては正当な分解軸になりうる。誤検知で判定器全体が
# 信用を失うより、判断を人に残すほうがよい）
DECORATION = ["年齢", "性別", "趣味", "家族構成", "年収"]


def _has_evidence(text: str, *escapes: str) -> bool:
    """根拠が引かれているか、引けないことが宣言されているか。"""
    return "VOICE-" in text or any(e in text for e in escapes)


def check_personas(path: Path) -> None:
    """利用者像。創作を防ぎ、件数0の系統に像を書かせない。"""
    text = path.read_text(encoding="utf-8")

    if "確信度" not in text:
        err(path, "確信度（実証 / 作業仮説 / 未取得）が無い。"
                  "検証を通った像と、そうでない像が同じ見た目で混ざる")
    if not _has_evidence(text, "未取得"):
        err(path, "根拠（VOICE-…）も「未取得」も無い。"
                  "台帳を引かずに書いた像は、集計ではなく創作")
    if "作業仮説" in text and "棄却条件" not in text:
        err(path, "確信度に「作業仮説」があるのに棄却条件が無い"
                  "（棄却条件のない仮説は、記録しても捨てられない）")
    if "非対象" not in text:
        err(path, "「非対象」（この像に含めない人）が無い。"
                  "非対象が空のペルソナは、全員を指しているのと同じ")

    for i, line in enumerate(text.split("\n"), 1):
        for word in DECORATION:
            if word in line and not _is_counter_example(line, word):
                warn(path, f"装飾属性「{word}」がある（判断に効かず、"
                           f"検証されていない断定が混ざる）", i)
                break


def check_journeys(path: Path) -> None:
    """ジャーニー。計測の分解式と切り離された「絵」にしない。"""
    text = path.read_text(encoding="utf-8")

    if "主要タスク時間" not in text:
        err(path, "主要タスク時間との対応が無い。ステップは計測の構成要素と"
                  "同一物として扱う（二重に定義すると必ず食い違う）")
    if "ペルソナ" not in text:
        err(path, "対象ペルソナの指定が無い（誰の流れか分からない）")
    if not _has_evidence(text, "一次情報なし"):
        err(path, "根拠（VOICE-…）も「一次情報なし」も無い")
    if "未取得" not in text and not re.search(r"[0-9０-９]", text):
        err(path, "所要時間に値も「未取得」も無い（それらしい数字を置かず、未取得と書く）")


SCREEN_STATES = ["初期", "処理中", "成功", "空振り", "エラー"]
HEX_LITERAL = re.compile(r"#[0-9a-fA-F]{3,8}\b")


def check_screen_spec(path: Path) -> None:
    """画面仕様。空振りの欠落と、表層の値の直書きを止める。"""
    text = path.read_text(encoding="utf-8")

    missing = [s for s in SCREEN_STATES if s not in text]
    if missing:
        err(path, f"状態設計に {' / '.join(missing)} が無い"
                  f"（特に**空振り**＝処理は成功したが有効な結果が無い状態を省略しない）")
    if not _has_evidence(text, "一次情報なし", "デザイナー起案"):
        err(path, "根拠のボイス（VOICE-…）も「デザイナー起案」の明記も無い")
    for i, line in enumerate(text.split("\n"), 1):
        if any(c in line for c in SPEC_COUNTER):
            continue
        m = HEX_LITERAL.search(line)
        if m:
            err(path, f"色の値を画面仕様に直書きしている: {m.group(0)}"
                      f"（トークン名で書く。値は {BASE_REL}specs/05-surface/"
                      f"design-tokens.md が持つ）", i)


def check_design_tokens(path: Path) -> None:
    """トークン台帳。定義の正が決まっているか、期限の無い例外が無いか。"""
    text = path.read_text(encoding="utf-8")

    if "真実の源" not in text:
        err(path, "「真実の源」（どのファイルが定義の正か）が無い。"
                  "2箇所で定義された状態を検出できない")
    if "逸脱" not in text:
        err(path, "逸脱一覧が無い（表層の成果物はトークンと逸脱の2つ）")
    for i, line in enumerate(text.split("\n"), 1):
        if line.lstrip().startswith("|") and "未定" in line:
            err(path, "逸脱の行に「未定」がある。**期限の無い例外は恒久化する**。"
                      "期限を決められないなら UXDR へ回し、棄却条件つきの作業仮説にする", i)


# デザインシステムの参照先。UI・モックを作る前に読む1枚。
#
# **無いこと自体は違反にしない。** 導入直後や PoC では決まっていないほうが普通で、
# そこで落とすと `/pd:init` の直後から赤くなる（hook が促す側で受け持つ）。
# 見るのは「**書いたのに実物を指していない**」状態だけ — 乗り換えたのに台帳が
# 取り残されると、全員が存在しないディレクトリを参照しに行く。
DS_REF_SECTION = "参照先"
DS_BACKTICK = re.compile(r"`([^`]+)`")


def _ds_checkable(ref: str) -> bool:
    """参照先のうち、実在を確かめられるものか。"""
    if not ref or ref.startswith(("http://", "https://", "@", "<")):
        return False          # URL / パッケージ名 / 未記入の雛形
    if " " in ref:
        return False          # 起動コマンド（`npm run storybook` 等）
    return "/" in ref or "." in ref


def check_design_system(path: Path) -> None:
    """デザインシステムの参照先。書いた参照先が実物を指しているか。"""
    text = path.read_text(encoding="utf-8")

    if "種別" not in text:
        err(path, "「種別」が無い（既製 / 自前 / Figma ライブラリ / 併用 / 無し）。"
                  "**未記入と「無いと決めた」を区別できないと、UI の作業のたびに"
                  "同じ確認が繰り返される**")
    if "真実の源" not in text:
        err(path, "「真実の源」（どこを見れば正解が分かるか）が無い。"
                  "参照先の書かれていないデザインシステムは、無いのと同じ")

    in_refs = False
    for i, line in enumerate(text.split("\n"), 1):
        if line.startswith("#"):
            in_refs = DS_REF_SECTION in line
            continue
        if line.lstrip().startswith("|") and "未定" in line:
            err(path, "適用しない範囲に「未定」がある。**期限の無い例外は恒久化する**。"
                      "期限を決められないなら UXDR へ回し、棄却条件つきの作業仮説にする", i)
        if not in_refs:
            continue
        for ref in DS_BACKTICK.findall(line):
            if ref.startswith("<") and ref.endswith(">"):
                err(path, f"参照先が雛形のまま: {ref!r}"
                          f"（決まっていないなら種別を「無し」にする。"
                          f"埋めない雛形は、決めたつもりだけを残す）", i)
            elif _ds_checkable(ref) and not (ROOT / ref).exists():
                err(path, f"参照先が存在しない: {ref!r}"
                          f"（乗り換えたのに台帳が取り残されている。"
                          f"変更は /pd:design-system で反映する）", i)


# ------------------------------------------- モックと実装のズレを機械が見つける
#
# モックで合意したのに、実装で要素が落ち、色がトークンから外れ、文言が言い換わる。
# 原因は「モックの中身を覚えているのは会話だけ」であること。**会話は次の日には
# 残っていない**し、落ちたことは落ちた側からは見えない。
#
# 間に機械が読める1枚（モック台帳）を挟む。抽出は mock_capture.py が行い、
# **ここが実装と突き合わせる**。捨てるなら台帳の上で理由つきで捨てさせる。
#
# **無いこと自体は違反にしない。** モックを作らない画面もある。見るのは
# 「台帳を作ったのに実装が追いついていない」状態だけ。
MOCK_STATE_DONE = "実装"
MOCK_STATE_SKIP = ("見送り", "動的", "対象外")
MOCK_NOT_STARTED = ("未着手", "これから", "無し", "なし")
MOCK_PLACEHOLDER = re.compile(r"<[^>|]+>")

# 実装を読みにいく拡張子。ここに無いものは黙って飛ばす（画像・ロックファイル）
IMPL_SUFFIX = (".tsx", ".ts", ".jsx", ".js", ".mjs", ".vue", ".svelte", ".astro",
               ".html", ".css", ".scss", ".sass", ".less", ".py", ".rb", ".php",
               ".kt", ".swift", ".dart", ".java", ".cs", ".go", ".erb", ".haml",
               ".json", ".yml", ".yaml", ".md")
IMPL_SKIP_DIRS = {"node_modules", ".git", "dist", "build", ".next", ".nuxt",
                  "vendor", "coverage", "__pycache__", ".venv"}


def _table_rows(text: str, heading: str) -> list[tuple[int, list[str]]]:
    """見出しの下にある表の中身。区切り行と見出し行は返さない。"""
    rows, inside = [], False
    for i, line in enumerate(text.split("\n"), 1):
        if line.startswith("#"):
            inside = heading in line
            continue
        if not inside:
            continue
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if not cells or set("".join(cells)) <= set("-: "):
            continue
        if cells[0] in ("#", "No"):
            continue
        rows.append((i, cells))
    return rows


def _field(text: str, name: str) -> str:
    m = re.search(rf"^\s*[-*]\s*\**{name}\**\s*[:：]\s*(.+)$", text, re.M)
    return m.group(1).strip() if m else ""


def _impl_source(target: str) -> str | None:
    """実装先のテキストを1つに連結して返す。読めなければ None。"""
    root = ROOT / target.strip().strip("`")
    if root.is_file():
        return root.read_text(encoding="utf-8", errors="replace")
    if not root.is_dir():
        return None
    chunks, budget = [], 4_000_000
    for p in sorted(root.rglob("*")):
        if not p.is_file() or p.suffix.lower() not in IMPL_SUFFIX:
            continue
        if IMPL_SKIP_DIRS & set(p.parts):
            continue
        chunks.append(p.read_text(encoding="utf-8", errors="replace"))
        budget -= len(chunks[-1])
        if budget <= 0:
            break
    return "\n".join(chunks)


def _squeeze(s: str) -> str:
    """空白を落として比べる。実装では長い文言が行をまたいで折り返される。"""
    return "".join(s.split())


def _mock_state(cell: str) -> str:
    """行の状態。`実装` / `skip` / `""`（未記入・不正）。"""
    if any(word in cell for word in MOCK_STATE_SKIP):
        return "skip"
    if cell.startswith(MOCK_STATE_DONE):
        return MOCK_STATE_DONE
    return ""


def check_mock_ledger(path: Path) -> None:
    """モック台帳。モックにあったものが実装から落ちていないかを見る。"""
    text = path.read_text(encoding="utf-8")

    mock = _field(text, "モック")
    impl = _field(text, "実装")
    published = _field(text, "公開")

    if not mock:
        err(path, "「モック」（元にした HTML）が無い。"
                  "**どのモックの台帳か分からない台帳は、照合できない**")
    else:
        ref = mock.strip("`")
        if MOCK_PLACEHOLDER.fullmatch(ref):
            err(path, "「モック」が雛形のまま")
        elif not (ROOT / ref).exists():
            err(path, f"モックが存在しない: {ref!r}"
                      f"（消したなら台帳も畳む。残すなら置き場所を直す）")
    if not published:
        err(path, "「公開」が無い（モックはリンクで渡す。"
                  "渡していないなら `公開しない: 理由` と書く）")
    elif "http" not in published and not published.startswith("公開しない"):
        err(path, "「公開」が URL でも `公開しない: 理由` でもない")
    if not impl:
        err(path, "「実装」が無い。**実装先を書かない台帳は、ズレを検出できない**"
                  "（まだ実装していないなら `未着手`）")

    texts = _table_rows(text, "文言")
    elements = _table_rows(text, "要素")
    colors = _table_rows(text, "色")
    if not texts:
        err(path, "文言の表が空。"
                  "**抽出は手で数えない** — `scripts/mock_capture.py` で作り直す")
    if not elements:
        err(path, "要素の表が空（何が実装されるべきかが決まっていない）")

    # 色は、生の値のままでは実装に持ち込めない。対応づけの欠落を先に見る
    raw_values = []
    for i, cells in colors:
        if len(cells) < 4:
            continue
        raw, token = cells[1], cells[3]
        if raw in ("—", "-", ""):
            continue
        if not token or token in ("—", "-", "不明", "未定") or MOCK_PLACEHOLDER.fullmatch(token):
            err(path, f"色 {raw} がトークンに対応づいていない。"
                      f"**「赤」で合意したものが実装で別の赤になる**のはここが空だから。"
                      f"近い既存トークンに寄せるか、足してから実装する", i)
        raw_values.append((i, raw, token))

    # 台帳に書いたトークンが、値の正（design-tokens.md）に無い
    tokens_file = BASE / "specs/05-surface/design-tokens.md"
    if tokens_file.exists():
        defined = tokens_file.read_text(encoding="utf-8")
        for i, raw, token in raw_values:
            # `--danger` のような CSS 変数名を `-` を落として比べない。
            # 落とすと `color.status.danger` に部分一致してしまい、
            # **モック側の変数名が、そのままトークンとして通る**
            name = token.strip("`")
            if name and not MOCK_PLACEHOLDER.fullmatch(token) and name not in defined:
                err(path, f"トークン {token!r} が {BASE_REL}specs/05-surface/"
                          f"design-tokens.md に無い（台帳にしか無い名前は、"
                          f"実装した人には見えない）", i)

    # 状態の書き方。空欄や TODO を許すと、埋めないまま「実装済み」に見える
    for label, rows, col in (("文言", texts, 2), ("要素", elements, 3)):
        for i, cells in rows:
            if len(cells) <= col:
                err(path, f"{label}の行に状態の欄が無い", i)
                continue
            if not _mock_state(cells[col]):
                err(path, f"{label}の状態が `実装` / `見送り: UXDR-…` / `動的: 理由` "
                          f"のいずれでもない: {cells[col]!r}"
                          f"（**未記入は「まだ決めていない」であって「実装した」ではない**）", i)
            elif "見送り" in cells[col] and "UXDR" not in cells[col]:
                err(path, "見送るなら UXDR を参照する"
                          "（記録の無い見送りは、次の人には欠落に見える）", i)

    if not impl or impl.startswith(MOCK_NOT_STARTED):
        return                      # まだ実装していない。照合するものが無い

    source = _impl_source(impl)
    if source is None:
        err(path, f"実装先が存在しない: {impl!r}"
                  f"（動かしたなら台帳も直す。**指していない台帳は誰も直さない**）")
        return
    flat = _squeeze(source)

    for i, cells in texts:
        if len(cells) < 3 or _mock_state(cells[2]) != MOCK_STATE_DONE:
            continue
        word = cells[1]
        if MOCK_PLACEHOLDER.fullmatch(word):
            continue
        if _squeeze(word) not in flat:
            err(path, f"モックの文言が実装に無い: {word!r}"
                      f"（言い換えたなら台帳を書き換えてから実装する。"
                      f"組み立てているなら `動的: 理由`）", i)

    for i, cells in elements:
        if len(cells) < 4 or _mock_state(cells[3]) != MOCK_STATE_DONE:
            continue
        mark = cells[2].strip("`")
        if not mark or MOCK_PLACEHOLDER.fullmatch(mark):
            err(path, f"要素 {cells[1]!r} に実装の目印が無い"
                      f"（目印の無い行は、落ちても機械が気づけない）", i)
        elif _squeeze(mark) not in flat:
            err(path, f"モックの要素が実装に無い: {cells[1]!r}（目印 {mark!r}）"
                      f"（落としたなら `見送り: UXDR-…`）", i)

    for i, raw, _token in raw_values:
        if raw.startswith("#") and raw.lower() in source.lower():
            err(path, f"実装が色を直書きしている: {raw}"
                      f"（モックの生値をそのまま持ち込まない。トークンを参照する）", i)


def check_navigation(path: Path) -> None:
    """ナビゲーション。到達できない画面と、根拠のない項目を検出する。"""
    text = path.read_text(encoding="utf-8")

    if "到達経路" not in text:
        err(path, "到達経路が無い（どの入口から辿り着けるかを書かない情報設計は、"
                  "迷子＝どこからも辿り着けない画面を検出できない）")
    if "対象物" not in text and "ステップ" not in text:
        err(path, "各項目の対応先（対象物 / ジャーニーのステップ）が無い。"
                  "どちらにも対応しない項目は、誰の関心でもない")


def check_spec(path: Path) -> None:
    """specs/ 配下の成果物。ファイルの置き場所で担当を決める。"""
    rel = rel_to_base(path)
    if rel == "specs/01-strategy/personas.md":
        check_personas(path)
    elif rel == "specs/02-requirements/journeys.md":
        check_journeys(path)
    elif rel.startswith("specs/04-skeleton/screens/"):
        check_screen_spec(path)
    elif rel == "specs/04-skeleton/navigation.md":
        check_navigation(path)
    elif rel == "specs/05-surface/design-tokens.md":
        check_design_tokens(path)
    elif rel == "specs/05-surface/design-system.md":
        check_design_system(path)
    elif rel.startswith("specs/05-surface/mocks/"):
        check_mock_ledger(path)
    check_naming(path)


# 「ユーザー」を単独で使わない、は v0.6.0 から規約にあるが、これまで誰も見ていなかった。
# 系統をまたいだ「ユーザーが不便」は、**誰の何が不便なのか分からないまま合意が成立する。**
#
# 複合語（ユーザーストーリー / ユーザー検証 / エンドユーザー…）は正当なので、
# **直後が助詞・句読点・行末のときだけ**拾う。判定は警告に留める
# （文脈によっては一般論として正しく、誤検知で判定器全体が無視されるほうが損失が大きい）。
BARE_USER = re.compile(r"ユーザー(?=[はがをにのもとやへ、。）」\]]|\s|$)")

# 呼称を定義する当のファイル。定義には対象語そのものの記載が要る。
# **規約を所有するファイルを、その規約で裁かない。** 警告文自身がこのファイルを
# 「呼称を決める場所」と名指ししており、そこが落ちるのは自己言及の矛盾になる。
NAMING_AUTHORITY = "specs/01-strategy/glossary.md"


def check_naming(path: Path) -> None:
    """呼称。どの利用者系統の話かを省いていないか。"""
    if rel_to_base(path) == NAMING_AUTHORITY:
        return
    for i, line in enumerate(path.read_text(encoding="utf-8").split("\n"), 1):
        if _is_counter_example(line, "ユーザー"):
            continue
        if BARE_USER.search(line):
            warn(path, "「ユーザー」を単独で使っている。どの利用者系統かを指定する"
                       f"（呼称は {BASE_REL}specs/01-strategy/glossary.md で決める）", i)


def check_simulation(path: Path) -> None:
    check_path(path, "simulations")
    text = path.read_text(encoding="utf-8")
    fm = frontmatter(text)
    if fm.get("synthetic") != "true":
        err(path, "frontmatter に synthetic: true が無い")
    head = text.split("##")[0]
    if "予測データ" not in head:
        err(path, "冒頭に「これは予測データです」の警告ブロックが無い")
    if "Evidence として引用" not in head:
        err(path, "冒頭の警告に「Evidence として引用しない」旨が無い")


def check_guards() -> None:
    """検証の仕組み自体が外されていないかを見る。

    plugin リポジトリ自身を検証しているのか、plugin を使うプロジェクトを
    検証しているのかで、揃っているべきものが違う。
    """
    if SELF_CHECK:
        check_plugin_guards()
    else:
        check_project_guards()


PLUGIN_FILES = [
    ".claude-plugin/plugin.json",
    ".claude-plugin/marketplace.json",
    "hooks/hooks.json",
    "commands/init.md",
    "commands/validate.md",
    "commands/uninstall.md",
    "commands/update.md",
    "commands/design-system.md",
    "commands/mock-ledger.md",
    "scripts/validate.py",
    "scripts/hook.py",
    "scripts/mock_capture.py",
    "scripts/update_check.py",
    "scripts/selftest.sh",
    "scripts/release.sh",
    "skills/analyze/SKILL.md",
    "skills/analyze/products/_template.md",
    ".github/workflows/validate.yml",
    # タグの push で Release を作る。無いと、`--no-push` や手動 push で配った版の
    # 本文が起動時の更新通知に出ない（v1.4.0 で実際に漏れた）
    ".github/workflows/release.yml",
    "CHANGELOG.md",
]


def check_plugin_guards() -> None:
    """配布物として欠けているものが無いか（plugin リポジトリ自身の検証）。"""
    for name in PLUGIN_FILES:
        if not (PLUGIN_ROOT / name).exists():
            errors.append(f"{name}: 無い（検証の仕組みが不完全）")

    check_version_consistency()
    check_rule_registry()
    check_selftest_coverage()

    hooks_file = PLUGIN_ROOT / "hooks/hooks.json"
    if hooks_file.exists():
        try:
            hooks = json.loads(hooks_file.read_text(encoding="utf-8")).get("hooks", {})
        except json.JSONDecodeError as e:
            err(hooks_file, f"JSON として壊れている（hook が全て無効になる）: {e}")
            hooks = {}
        for event in ("PostToolUse", "Stop", "SessionStart", "UserPromptSubmit"):
            body = json.dumps(hooks.get(event, []), ensure_ascii=False)
            if "hook.py" not in body:
                err(hooks_file, f"{event} の hook が消えている（hook.py）")
        check_hook_portability(hooks_file)

    check_hook_entrypoint()
    check_update_optout()
    check_command_names()
    check_plugin_is_generic()
    check_documented_paths()
    check_skill_shape()


# スキルが増えるほど、担当の重なりが事故になる。「どのスキルを呼べばよいか」が
# 判断できなくなり、結局いつも同じ1つだけが使われる。
# 個々のスキル名を列挙して守るのではなく、**形**を守る（列挙は必ず取り残される）。
SKILL_SHAPE_EXEMPT = {"analyze"}   # analyze はオーケストレーション側で、層を持たない


def check_skill_shape() -> None:
    """各スキルが SKILL.md と役割分界の表を持っているか。"""
    skills_dir = PLUGIN_ROOT / "skills"
    if not skills_dir.exists():
        return
    for d in sorted(p for p in skills_dir.iterdir() if p.is_dir()):
        entry = d / "SKILL.md"
        if not entry.exists():
            errors.append(f"skills/{d.name}/SKILL.md: 無い"
                          f"（ディレクトリはあるがスキルとして読み込まれない）")
            continue
        text = entry.read_text(encoding="utf-8")
        fm = frontmatter(text)
        if fm.get("name") != d.name:
            err(entry, f"frontmatter の name（{fm.get('name')}）が"
                       f"ディレクトリ名（{d.name}）と違う")
        if not fm.get("description"):
            err(entry, "description が無い（呼び出される場面を判定できない）")
        if d.name in SKILL_SHAPE_EXEMPT:
            continue
        if "役割分界" not in text:
            err(entry, "役割分界の表が無い（何をやらないか・誰の担当かが不明だと、"
                       "スキルが増えるほど担当が重なって事故になる）")


# 記録ファイルの置き場所は「pd/{種別}/{プロダクト}/{年}/{接頭辞}-…」で統一されている。
# 文書がこれを省いた形（pd/decisions/UXDR-… ）で案内すると、そのとおりに書いた
# ファイルが検証器に落ちる。**書いた人には、どちらが正しいか判断する材料が無い。**
#
# v0.6.0 で置き場所を変えたとき、検証器と SKILL.md は直ったが UI/UX 側のスキル5本と
# テンプレート2本が取り残された（v1.0.0 で発見）。注意力では防げないのでここで見る。
FLAT_RECORD_PATH = re.compile(
    r"pd/(analyses|voices|simulations|decisions|validations|measurements|reviews)/"
    r"(UXDR-|VP-|MP-|DR-|VOICE-|\d{4})"
)


def check_documented_paths() -> None:
    """文書が案内する記録の置き場所が、検証器の期待と揃っているか。"""
    targets = sorted((PLUGIN_ROOT / "skills").rglob("*.md")) \
        + sorted((PLUGIN_ROOT / "commands").glob("*.md"))
    for path in targets:
        rel = path.relative_to(PLUGIN_ROOT)
        for i, line in enumerate(path.read_text(encoding="utf-8").split("\n"), 1):
            m = FLAT_RECORD_PATH.search(line)
            if m:
                kind = m.group(1)
                err(rel, f"案内している置き場所に {{プロダクト}}/{{年}} が無い: "
                         f"{m.group(0)!r}（期待: {BASE_REL}{EXPECTED[kind]}）", i)


# 配布物に混ざってはいけないもの。plugin は「思考の型」を配る。特定プロダクトの
# 語彙や、元プロジェクトの実装パスが残っていると、他のプロダクトで
# 間違った言葉と存在しないファイルを強制することになる（v1.0.0 で一度混入した）。
#
# ここが空振りしても「固有物が無い」証明にはならない。辞書は当たった分しか見えない。
# 判定を足すのは、実際に混入を見つけたとき。

# 元プロジェクトの実装に依存する参照。これは網羅的に効く（存在しないパスは必ず壊れる）
FOREIGN_PATHS = [
    (".devin/", "元プロジェクトの規約ディレクトリ"),
    ("src/", "利用プロジェクトのソース構成に依存する"),
    (".next", "特定フレームワークのビルド出力"),
    ("pnpm ", "plugin に package.json は無い。node で直接呼ぶ"),
    (".claude/skills/", "plugin のスキルはここには置かれない"),
]

# 業種の語彙。反例として並べている行（✗ / ❌ / 「書かない」）は対象外
INDUSTRY_WORDS = [
    "店舗", "来店", "飲食", "小売", "客席", "宿泊", "患者", "受講",
    "予約完了時間", "予約対応時間", "訪日",
]
COUNTER_EXAMPLE = ("✗", "❌", "書かない", "書き込まない", "禁止")


def check_plugin_is_generic() -> None:
    """skills/ に固有プロダクトの語彙・実装パスが残っていないか。

    この判定が無かったため、飲食予約サービスの業務定義が配布物に
    そのまま入り、他プロダクトで使えない状態が v0.7.0 まで残った。
    """
    for path in sorted((PLUGIN_ROOT / "skills").rglob("*.md")):
        rel = path.relative_to(PLUGIN_ROOT)
        for i, line in enumerate(path.read_text(encoding="utf-8").split("\n"), 1):
            for token, why in FOREIGN_PATHS:
                if token in line:
                    err(rel, f"配布物に外部プロジェクトの参照がある: {token!r}"
                             f"（{why}）", i)
            if any(c in line for c in COUNTER_EXAMPLE):
                continue
            for word in INDUSTRY_WORDS:
                if word in line:
                    err(rel, f"配布物に業種固有の語がある: 「{word}」"
                             f"（固有の語彙は利用プロジェクト側の "
                             f"pd/specs/01-strategy/glossary.md に置く）", i)


# plugin のスキルは必ず「plugin名:スキル名」に名前空間化される。素の `/init`
# と書くと、そのとおり打った利用者は「コマンドが無い」で終わる。
#
# v1.0.0 でコマンド名から `pd-` の接頭辞を外した（`/pd:pd-init` → `/pd:init`）。
# 素の名前が `init` / `validate` のような普通の英単語になったため、
# **直前が語・`/`・`:` のときは対象外にする**（`scripts/validate.py` や
# `pd/validations/` を誤検知させない）。旧名も残骸として拾う。
BARE_COMMAND = re.compile(
    r"(?<![\w:/])/(analyze|init|validate|uninstall|update"
    r"|pd|pd-init|pd-validate|pd-uninstall)(?![\w:\-/])"
)

# 旧名で書かれていたときに、何と書き直せばよいかを示す
RENAMED = {"pd": "analyze", "pd-init": "init",
           "pd-validate": "validate", "pd-uninstall": "uninstall"}

DOCS = ["README.md", "CLAUDE.md", "DECISIONS.md",
        "commands/init.md", "commands/validate.md",
        "commands/uninstall.md", "commands/update.md",
        "commands/design-system.md", "commands/mock-ledger.md",
        "skills/analyze/SKILL.md"]


def check_command_names() -> None:
    for name in DOCS:
        path = PLUGIN_ROOT / name
        if not path.exists():
            continue
        for i, line in enumerate(path.read_text(encoding="utf-8").split("\n"), 1):
            m = BARE_COMMAND.search(line)
            if m:
                got = m.group(1)
                err(path, f"コマンド名に名前空間が無い: {m.group(0)!r} "
                          f"（実際に使えるのは /pd:{RENAMED.get(got, got)}）", i)


# hooks.json に書くとシェルに依存するもの。Windows には sh も jq も無いため、
# ここに1つでも混ざると hook が丸ごと動かない環境が生まれる。
SHELL_ISMS = ("jq ", "jq -", "case ", "esac", "printf ", "read -r", "[ -f", "$(")


def check_hook_portability(hooks_file: Path) -> None:
    body = hooks_file.read_text(encoding="utf-8")
    for token in SHELL_ISMS:
        if token in body:
            err(hooks_file, f"シェル依存の記述がある: {token.strip()!r}"
                            "（Windows で hook が動かない。判定は hook.py に書く）")


def check_hook_entrypoint() -> None:
    """hook の入口に、動くべき場面の判定が残っているか。"""
    entry = PLUGIN_ROOT / "scripts/hook.py"
    if not entry.exists():
        return
    body = entry.read_text(encoding="utf-8")
    # plugin は全プロジェクトで有効になる。pd を使わないプロジェクトで
    # 動くと毎回違反を出すため、目印が無ければ何もしないこと。
    if "ledger.json" not in body:
        err(entry, "pd プロジェクトの目印の判定が無い"
                   "（pd を使わないプロジェクトでも動いてしまう）")
    if "DECISIONS.md" not in body:
        err(entry, "設計判断の記録（DECISIONS.md）の促しが消えている")
    # 更新は放っておくと届かない（サードパーティの配布元は既定で自動更新されない）。
    # 起動時に知らせないと、手元だけ古いまま CI と判定が食い違う。
    if "update_check" not in body:
        err(entry, "起動時の更新の案内が消えている（利用者に新しい版が届かない）")
    # モックを頼まれたら公開されたページで返す。ここが消えると、同じ頼み方でも
    # 公開されたりローカルの HTML で終わったりに戻る（利用者から見て条件が読めない）。
    if "Artifact" not in body:
        err(entry, "モックを Artifact で publish させる仕組みが消えている"
                   "（ローカルにファイルを書いただけで終わる状態に戻る）")
    if "stop_hook_active" not in body:
        err(entry, "差し戻しの打ち切りが無い"
                   "（publish できない環境で終われなくなる）")
    # UI を作る前に参照先を指す。ここが消えると、同じプロジェクトで作った UI が
    # 揃わない状態（参照するかどうかがその場の判断）に戻る。
    if "design-system.md" not in body:
        err(entry, "UI を作る前にデザインシステムを指す仕組みが消えている"
                   "（参照するかどうかが、その場の判断に戻る）")
    # モックを実装に落とす直前に台帳を指す。ここが消えると、照合する1枚が
    # 作られないまま実装が始まり、欠落・色ズレ・文言の言い換えが元に戻る
    if "mocks" not in body:
        err(entry, "モックを実装に落とすときに台帳を指す仕組みが消えている"
                   "（モックの中身を覚えているのが会話だけの状態に戻る）")


def check_update_optout() -> None:
    """起動時の外部通信を、利用者が恒久的に止められるか。

    plugin の外に入口が無いと、止める手段は hooks.json の編集しか残らず
    `/plugin update` のたびに黙って復活する。SECURITY.md はこの入口を
    利用者に約束しているため、消えると文書が嘘になる。
    """
    checker = PLUGIN_ROOT / "scripts/update_check.py"
    if not checker.exists():
        return
    if "PD_UPDATE_CHECK" not in checker.read_text(encoding="utf-8"):
        err(checker, "更新確認を止める入口が無い"
                     "（plugin の外から止められないと /plugin update で復活する）")
    security = PLUGIN_ROOT / "SECURITY.md"
    if security.exists() and "PD_UPDATE_CHECK" not in security.read_text(encoding="utf-8"):
        err(security, "更新確認の止め方が書かれていない"
                      "（止められることを知らせないと、無いのと同じ）")


def check_version_consistency() -> None:
    """版の記載が3箇所で食い違っていないか。

    Claude Code は plugin.json の version を更新の判定キーにする。上げ忘れると
    利用者に更新が届かず、marketplace.json だけ上げても効かない。
    履歴が無ければ、利用者は更新して何が変わるのかを判断できない。
    """
    manifest = PLUGIN_ROOT / ".claude-plugin/plugin.json"
    market = PLUGIN_ROOT / ".claude-plugin/marketplace.json"
    changelog = PLUGIN_ROOT / "CHANGELOG.md"
    if not manifest.exists():
        return

    try:
        version = json.loads(manifest.read_text(encoding="utf-8")).get("version")
    except json.JSONDecodeError as e:
        err(manifest, f"JSON として壊れている: {e}")
        return
    if not version:
        err(manifest, "version が無い（利用者に更新が届かない）")
        return

    if market.exists():
        try:
            entries = json.loads(market.read_text(encoding="utf-8")).get("plugins", [])
        except json.JSONDecodeError as e:
            err(market, f"JSON として壊れている: {e}")
            entries = []
        for entry in entries:
            if entry.get("name") == "pd" and entry.get("version") != version:
                err(market, f"version が plugin.json と違う "
                            f"（{entry.get('version')} ≠ {version}）")

    if changelog.exists() and version not in changelog.read_text(encoding="utf-8"):
        err(changelog, f"{version} の項目が無い"
                       "（利用者が更新の内容を判断できない）")

    # 逆向きの食い違い。履歴に新しい版を書いたのに plugin.json を上げていない状態は、
    # 「書いたのに配っていない」。/plugin update しても "already at the latest version"
    # で止まり、利用者には何も届かない。見た目は完成しているので気づけない。
    if changelog.exists():
        headings = re.findall(r"^## \[(\d+\.\d+\.\d+)\]",
                              changelog.read_text(encoding="utf-8"), re.M)
        if headings:
            def parts(v: str) -> tuple:
                return tuple(int(n) for n in v.split("."))
            newest = max(headings, key=parts)
            if parts(newest) > parts(version):
                err(changelog, f"{newest} の項目があるのに plugin.json は {version} のまま"
                               f"（書いたが配っていない）。"
                               f"配るには sh scripts/release.sh を実行する")

    # pd-init が利用プロジェクトの CI に焼き込む版。古いまま配ると、
    # 初期状態から手元（最新）と CI（旧版）で判定が食い違う。
    init = PLUGIN_ROOT / "commands/init.md"
    if init.exists():
        refs = re.findall(r"ref:\s*v([\d.]+)", init.read_text(encoding="utf-8"))
        for ref in refs:
            if ref != version:
                err(init, f"CI に焼き込む ref が古い（v{ref} ≠ v{version}）。"
                          "新しいプロジェクトが旧版の判定器で CI を回すことになる")


def _function_body(src: str, name: str) -> str | None:
    """ソースから関数1つ分を切り出す。無ければ None。"""
    parts = src.split(f"\ndef {name}", 1)
    if len(parts) != 2:
        return None
    return re.split(r"\n(?=def |# -)", parts[1], maxsplit=1)[0]


def check_selftest_coverage() -> None:
    """判定に対して「**正しい書き方の例**」が置かれているか。

    自己テストは「壊れた例を検出できること」ばかりを確かめていて、
    「**正しく書いたものを落とさないこと**」をほとんど確かめていなかった
    （壊れた例 75 に対して正しい例 11）。判定を締めるたびに正しい書き方の一部を
    巻き込み、v1.5.2 と v1.5.3 で連続して誤検知を出した。

    **誤検知が出ると、利用者は原因を追う代わりに「通る書き方」を探す。**
    それは規律ではなく作文で、この plugin が防ごうとしているものそのもの。

    要求する対象は**振り分け（`validate` / `check_spec`）から機械で数え上げる**。
    一覧を手で持つと、文書の種類を足した人が一覧に書き忘れて終わる。
    振り分けに繋がない限りその判定は動かないので、数え上げの漏れは起きない。
    """
    vp = PLUGIN_ROOT / "scripts/validate.py"
    sp = PLUGIN_ROOT / "scripts/selftest.sh"
    if not vp.exists() or not sp.exists():
        return
    src = vp.read_text(encoding="utf-8")
    tests = sp.read_text(encoding="utf-8")

    required: set[str] = set()
    for entry in ("validate", "check_spec"):
        body = _function_body(src, entry)
        if body:
            required |= set(re.findall(r"\b(check_[a-z_]+)\(path", body))
    required.discard("check_path")

    covered: set[str] = set()
    # 行をまたがせない。`\s` は改行も食うため、タグの無い expect_ok が
    # 次の行の語をタグとして拾ってしまう（実際に起きた）
    for tag in re.findall(r'expect_ok[^\S\n]+"[^"]*"[^\S\n]+([a-z_][a-z_ ]*)', tests):
        covered |= set(tag.split())
    for name in sorted(required - covered):
        err(sp, f"{name} に正しい書き方の例が無い。"
                f"`expect_ok \"正しい…は通る\" {name}` を置く"
                f"（壊れた例だけでは、判定を締めたときに正しい文書を"
                f"巻き込んだことに気づけない）")

    # Note の判定は、壊れた例と正しい例の両方を持つ（rule 名で対応づける）
    for rule in sorted(RULE_SINCE):
        if f"expect_rule {rule} " not in tests:
            err(sp, f"判定「{rule}」の壊れた例が無い（expect_rule {rule} …）")
        if f"expect_no_rule {rule} " not in tests:
            err(sp, f"判定「{rule}」の正しい例が無い（expect_no_rule {rule} …）。"
                    f"**締めたときに正しい書き方を巻き込んでいないか**を見る")


def check_rule_registry() -> None:
    """Note への判定が、適用開始日を持たずに足されていないか。

    v1.5.0 で判定を1つ足したとき、`RULE_SINCE` に相当するものが無かったため
    **書いた時点で存在しない判定が既存の記録に遡って適用された**。v1.5.1 で表を
    足したが、表に書き忘れても何も起きないままだった。**「気をつける」に戻っていた。**

    ここで塞ぐ。`check_new_rules` の中で `err(` / `warn(` を直に呼べば違反になり、
    `note_err` / `note_warn` を使えば rule 名が要り、rule 名は `RULE_SINCE` に
    無ければ違反になる。**判定を足す道が、日付を書く道しか無くなる。**
    """
    src = PLUGIN_ROOT / "scripts/validate.py"
    if not src.exists():
        return
    body = _function_body(src.read_text(encoding="utf-8"), "check_new_rules")
    if body is None:
        errors.append("scripts/validate.py: check_new_rules が無い"
                      "（Note への判定の入口が失われている）")
        return

    for line in body.split("\n"):
        m = re.search(r"(?<![_a-zA-Z])(err|warn)\(", line)
        if m:
            err(src, f"check_new_rules で {m.group(1)}() を直に呼んでいる。"
                     f"**適用開始日を通らないため、書いた時点で存在しない判定が"
                     f"過去の Note に遡って効く。** note_err / note_warn を使う")

    # 適用開始日は「その判定を配った版の日付」でなければならない。
    # 打ち間違いや、どの版にも対応しない日付を書くと、**遡及の判定が静かに狂う**
    # （早すぎれば過去の Note を巻き込み、遅すぎれば当分どの Note にも効かない）。
    changelog = PLUGIN_ROOT / "CHANGELOG.md"
    if changelog.exists():
        released = set(re.findall(r"^## \[\d+\.\d+\.\d+\]\s*[—-]\s*(\d{4}-\d{2}-\d{2})",
                                  changelog.read_text(encoding="utf-8"), re.M))
        if released:
            for rule, date in sorted(RULE_SINCE.items()):
                if date != RULES_FROM and date not in released:
                    err(src, f"判定「{rule}」の適用開始日 {date} が、どの版の日付とも"
                             f"一致しない（配った日を書く。CHANGELOG の見出しの日付）")

    used = set(re.findall(r'note_(?:err|warn)\(path, fm, "([a-z0-9-]+)"', body))
    for rule in sorted(used - set(RULE_SINCE)):
        err(src, f"判定「{rule}」が RULE_SINCE に無い"
                 f"（いつからの Note に適用するかが決まっていない。"
                 f"その判定を入れた版の日付を書く）")
    if not used:
        err(src, "check_new_rules に rule 付きの判定が1つも無い"
                 "（適用開始日の仕組みが外されている）")


def check_project_guards() -> None:
    """plugin を使うプロジェクト側に、検証を成り立たせるものが揃っているか。"""
    hooks_file = PLUGIN_ROOT / "hooks/hooks.json"
    if not hooks_file.exists():
        errors.append("hooks/hooks.json: 無い（plugin 側の hook が失われている）")

    # 履歴の代わりに台帳が必須（版管理を前提にしない）
    if not LEDGER.exists() and "--accept" not in sys.argv:
        errors.append("pd/ledger.json: 無い（過去の記録の書き換えを検出できない）。"
                      "/pd:init で作成する")

    ci = ROOT / ".github/workflows/validate.yml"
    if not ci.exists():
        errors.append(".github/workflows/validate.yml: 無い（検証の仕組みが不完全）。"
                      "/pd:init で作成する")
    else:
        # runner の既定は UTC。台帳の「当日」判定がずれ、手元で通る同日の修正が
        # CI でだけ落ちる。
        body = ci.read_text(encoding="utf-8")
        if "TZ: Asia/Tokyo" not in body:
            err(ci, "TZ: Asia/Tokyo が無い（台帳の当日判定が手元とずれる）")
        # {owner}/pd-plugin を checkout していること
        # （作業用パスの .pd-plugin と紛れないよう、スラッシュ込みで見る）
        if "/pd-plugin" not in body:
            err(ci, "plugin を取得する手順が無い（CI で validate.py を実行できない）")
        check_ci_ref(ci, body)


def check_ci_ref(ci: Path, body: str) -> None:
    """CI が固定している plugin の版と、いま動いている plugin の版を突き合わせる。

    `ref:` は `/pd:init` が走った時点の版を焼き込む文字列で、以後は誰も触らない。
    `/pd:update` は「ref も上げるように伝える」だけで、実際に上げるのは人間の記憶に
    委ねられていた。忘れれば手元（更新済み）と CI（旧版）で違う判定器が動く。
    **判定者は1つ**という前提が、判定者自身の版で崩れていた。

    ここで比較できるのは、CI 実行時には ref で checkout した plugin が手元にあり、
    手元実行時にはインストール済みの plugin が手元にあるため。つまり
    `PLUGIN_ROOT` の版が「いま判定している版」そのものになる。

    止めない（警告）。版がズレていても分析そのものは行えるし、更新直後に全プロジェクトが
    一斉に落ちると、直す前に検証器を外される。
    """
    manifest = PLUGIN_ROOT / ".claude-plugin/plugin.json"
    try:
        version = json.loads(manifest.read_text(encoding="utf-8")).get("version")
    except (json.JSONDecodeError, OSError):
        return
    if not version:
        return

    # **版として読めるのは semver のタグだけ。** `[\d.]+` で拾うと、commit SHA を
    # 指した `ref: 4762a00` が「v4762」という版として比較され、
    # 「手元より新しい」という意味の通らない警告が出ていた。
    # **コメント行は読まない。** `# 以前は ref: v1.0.0 だった` のような注記を
    # 実際の指定と取り違えると、正しく上げてあるのに警告が出続ける。
    raw = []
    for line in body.split("\n"):
        code = line.split("#", 1)[0]
        m = re.search(r"ref:\s*(\S+)", code)
        if m:
            raw.append(m.group(1).strip())
    refs = [r.lstrip("v") for r in raw if re.fullmatch(r"v?\d+\.\d+\.\d+", r)]
    if not refs:
        # 版を固定していない = CI が既定ブランチや commit を追う。判定が予告なく
        # 変わり、手元を更新していないのに CI だけ落ちる日が来る。
        fixed = "・".join(raw) if raw else "ref が無い"
        warn(ci, f"plugin の版を固定していない（{fixed}）。"
                 f"commit やブランチではなく、`ref: v{version}` のようにタグで指定する"
                 f"（版が読めないと、手元との食い違いを検出できない）")
        return

    for ref in set(refs):
        if ref == version:
            continue
        if _parts(ref) < _parts(version):
            warn(ci, f"CI が固定している plugin の版が古い（v{ref} ≠ v{version}）。"
                     f"手元と CI で違う判定器が動く。ref を v{version} に上げる")
        else:
            warn(ci, f"CI が固定している plugin の版が手元より新しい"
                     f"（v{ref} ≠ v{version}）。`/pd:update` で手元を更新する")


def _parts(v: str) -> tuple:
    return tuple(int(n) for n in v.split(".") if n.isdigit())


def check_product(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    check_segment_definition(path, text)
    for heading in ["## Available Evidence", "## Past Experiments",
                    "## Decisions", "### 保留中の見直し", "## Unknowns"]:
        if heading not in text:
            err(path, f"必須の節が無い: {heading}")
    pending = text.split("### 保留中の見直し", 1)
    if len(pending) == 2:
        body = pending[1].split("\n## ", 1)[0]
        if "無し" not in body and "なし" not in body and "確認者" not in body:
            err(path, "「保留中の見直し」に確認者・時期の欄が無い")
    for i, line in enumerate(text.split("\n"), 1):
        if "simulations/" in line and "予測" not in line:
            err(path, "予測データを参照する行に「予測」の明示が無い", i)
        if re.search(r"voices/[^\s`]*\.md", line):
            err(path, "Voice のファイル名を列挙している（ディレクトリが正。"
                      "ここには取得済みの範囲・得られている論点・欠けている声を書く）", i)


def check_framework_leakage() -> None:
    products = known_products()
    targets = list(FRAMEWORK_DIR.glob("*.md"))
    for base in {ROOT, PLUGIN_ROOT}:
        if (base / "README.md").exists():
            targets.append(base / "README.md")
    for path in targets:
        for i, line in enumerate(path.read_text(encoding="utf-8").split("\n"), 1):
            for name in products:
                if re.search(rf"\b{re.escape(name)}\b", line) and ".local/" not in line:
                    err(path, f"プロダクト固有名「{name}」が含まれている", i)


NOISE = {".DS_Store", "Thumbs.db", "desktop.ini"}


def check_duplicate_numbers() -> None:
    """同じ日に同じ連番の Note が2つ以上ないか。"""
    seen: dict[tuple[str, str, str], list[str]] = {}
    base = BASE / "analyses"
    if not base.exists():
        return
    for path in sorted(base.rglob("*.md")):
        m = PATTERNS["analyses"].match(rel_to_base(path))
        if not m:
            continue
        key = (m.group(1), m.group(3), m.group(4))
        seen.setdefault(key, []).append(rel_to_root(path))
    for (product, date, nn), files in seen.items():
        if len(files) > 1:
            errors.append(f"{product} {date} の連番 {nn} が重複している: "
                          f"{' / '.join(files)}（後から気づいた側がリネームする）")


def check_repo_layout() -> None:
    skip = (".git/", ".local/", "node_modules/", f"{BASE_REL}.local/")
    # pd を `pd/` に畳んでいるプロジェクトでは、走査するのは `pd/` の中だけ。
    #
    # アプリのソースと同居している場合（pd 専用リポジトリでない場合）、ROOT 全体を
    # 舐めると `public/` の画像や `supabase/migrations/*.sql` まで「生データ」と
    # 判定され、pd とは無関係の数百件で CI が常時赤になる。**常に赤い判定器は
    # 誰も見なくなる。** pd が責任を持つのは pd が作ったものだけ。
    #
    # 旧レイアウト（root 直下に products/ analyses/）と plugin 自身の検証では
    # BASE == ROOT / SELF_CHECK となり、従来どおり全体を走査する。
    scan_root = ROOT if SELF_CHECK else BASE
    for path in scan_root.rglob("*"):
        rel = str(path.relative_to(ROOT)).replace("\\", "/")
        if rel.startswith(skip) or not path.is_file():
            continue
        top = rel_to_base(path).split("/")[0]
        if path.name in NOISE or path.name.startswith("._"):
            err(path, "OS が作る不要ファイル。削除する")
        if path.suffix.lower() in RAW_EXT:
            err(path, f"生データ・画像はリポジトリに置かない（{BASE_REL}.local/{{プロダクト}}/ へ）")
        if path.name.lower() in {"index.md"} and top in IMMUTABLE_DIRS:
            err(path, f"索引ファイルを作らない（一覧はディレクトリ、未決は {BASE_REL}products/ が正）")
        if path.name == "README.md" and top in IMMUTABLE_DIRS:
            err(path, "索引・説明ファイルを作らない（規約は CLAUDE.md と README.md に集約）")


# ---------------------------------------------------------------------- main

def validate(paths: list[Path]) -> None:
    for path in paths:
        rel = rel_to_base(path)
        if rel.startswith("analyses/") and path.suffix == ".md":
            check_note(path)
        elif rel.startswith("voices/") and path.suffix == ".md":
            check_voice(path)
        elif rel.startswith("simulations/") and path.suffix == ".md":
            check_simulation(path)
        elif rel.startswith("decisions/") and path.suffix == ".md":
            check_uxdr(path)
        elif rel.startswith("measurements/") and path.suffix == ".md":
            check_measurement(path)
        elif rel.startswith("validations/") and path.suffix == ".md":
            if path.name.startswith("RP-"):
                check_research(path)
            else:
                check_validation(path)
        elif rel.startswith("reviews/") and path.suffix == ".md":
            check_review(path)
        elif rel.startswith("specs/") and path.suffix == ".md":
            check_spec(path)
        elif rel.startswith(f"{PRODUCTS_REL}/") and path.stem not in {"_template"}:
            check_product(path)


def main() -> int:
    accept = "--accept" in sys.argv
    args = [Path(a).resolve() for a in sys.argv[1:] if not a.startswith("--")]
    if args:
        files = [p for p in args if p.exists() and p.is_file() and p.is_relative_to(ROOT)]
        validate(files)
        check_ledger([p for p in files
                      if p.is_relative_to(BASE)
                      and rel_to_base(p).startswith(IMMUTABLE_DIRS)],
                     accept, full=False)
    else:
        targets = []
        dirs = ["analyses", "voices", "simulations", "specs", "decisions",
                "validations", "measurements", "reviews", PRODUCTS_REL]
        for d in dirs:
            targets += sorted((BASE / d).rglob("*.md")) if (BASE / d).exists() else []
        validate(targets)
        check_framework_leakage()
        check_repo_layout()
        check_duplicate_numbers()
        check_guards()
        check_ledger(immutable_files(), accept, full=True)
        notices.append(f"検証対象 {len(targets)} ファイル")

    if errors:
        print("規約違反が見つかりました\n")
        for e in errors:
            print(f"  ✗ {e}")
        print(f"\n{len(errors)} 件。規約の出典: CLAUDE.md / pd plugin の skills/analyze/SKILL.md")
        if warnings:
            print(f"\n警告 {len(warnings)} 件（止めません）")
            for w in warnings:
                print(f"  ⚠ {w}")
        return 1

    print("✓ 規約違反なし" + (f"（{notices[0]}）" if notices else ""))
    for n in notices[1:]:
        print(f"  {n}")
    if warnings:
        print(f"\n警告 {len(warnings)} 件（止めません。直すかは判断に任せます）")
        for w in warnings:
            print(f"  ⚠ {w}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
