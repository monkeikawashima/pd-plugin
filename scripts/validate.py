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

# 規約の追加より前に書かれた Note。日付では分けられないため明示的に除外する
# （追加日と同じ日に既存と新規が混在するため。理由は pd-skill-blueprint.md §13）
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


def required_segments(product: str) -> list[str]:
    f = PRODUCTS_DIR / f"{product}.md"
    if not f.exists():
        return []
    for line in f.read_text(encoding="utf-8").split("\n"):
        if line.strip().startswith("必須 Segment:"):
            body = line.split(":", 1)[1]
            return [t.strip() for t in re.split(r"[・/／]", body) if t.strip()]
    return []


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
    "validations": re.compile(r"^validations/([a-z0-9-]+)/(\d{4})/VP-(\d{8})-(\d{2})-([a-z][a-z0-9-]*)\.md$"),
    "measurements": re.compile(r"^measurements/([a-z0-9-]+)/(\d{4})/MP-(\d{8})-(\d{2})-([a-z][a-z0-9-]*)\.md$"),
    "reviews": re.compile(r"^reviews/([a-z0-9-]+)/(\d{4})/DR-(\d{8})-(\d{2})-([a-z][a-z0-9-]*)\.md$"),
}

EXPECTED = {
    "analyses": "analyses/{プロダクト}/{年}/YYYYMMDD-NN-{主題1語}.md",
    "voices": "voices/{プロダクト}/{年}/VOICE-NNN-{主題1語}.md",
    "simulations": "simulations/{プロダクト}/{年}/YYYYMMDD-{主題1語}.md",
    "decisions": "decisions/{プロダクト}/{年}/UXDR-YYYYMMDD-NN-{主題1語}.md",
    "validations": "validations/{プロダクト}/{年}/VP-YYYYMMDD-NN-{主題1語}.md",
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
        err(path, "「反証」の節が無い（この結論を最も強く否定する Evidence。箇条書き2〜3行で足りる）")

    # ① 予測値
    for name, body in secs.items():
        if "Experiment" in name and "予測" not in body:
            err(path, f"「{name}」に予測値が無い（事前に「どれくらい動くと思うか」を書く）")

    # ② 棄却条件の閾値（表のヘッダ行は対象外）
    lines = text.split("\n")
    for i, line in enumerate(lines, 1):
        if "棄却条件" not in line or HEDGE_FREE.search(line):
            continue
        nxt = lines[i] if i < len(lines) else ""
        if TABLE_SEPARATOR.match(nxt):
            continue   # 表のヘッダ行
        err(path, "棄却条件に観測可能な閾値が無い（数値・比較で書く。暫定なら明示する）", i)

    # ⑤ 必須 Segment（警告）
    segs = required_segments(fm.get("product", ""))
    if segs and not any(sg in text for sg in segs):
        warn(path, f"必須 Segment（{' / '.join(segs)}）での分解が見当たらない")

    # ⑦ 出典と分量（警告）
    for name, body in secs.items():
        if name.startswith("Evidence") and re.search(r"[0-9０-９]", body) \
                and not re.search(r"出典|期間|条件|テーブル|集計", body):
            warn(path, f"「{name}」に数値があるが、出典（テーブル / 期間 / 条件）が無い")
    if len(text.split("\n")) > 300:
        warn(path, "Note が 300 行を超えている（1回の分析として大きすぎる可能性）")


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


def check_review(path: Path) -> None:
    """レビュー結果。見れば分かる課題と、検証しないと決まらない仮説を分ける。"""
    check_path(path, "reviews")
    text = path.read_text(encoding="utf-8")
    secs = sections(text)
    if not any("課題" in k for k in secs) or not any("仮説" in k for k in secs):
        err(path, "「見れば分かる課題」と「検証しないと決まらない仮説」に分かれていない")
    if "デザイナー起案" not in text and "VOICE-" not in text:
        err(path, "根拠のボイス（VOICE-…）が無い指摘に「デザイナー起案」の明記が無い")


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
    "scripts/validate.py",
    "scripts/hook.py",
    "scripts/update_check.py",
    "scripts/selftest.sh",
    "scripts/release.sh",
    "skills/analyze/SKILL.md",
    "skills/analyze/products/_template.md",
    ".github/workflows/validate.yml",
    "CHANGELOG.md",
]


def check_plugin_guards() -> None:
    """配布物として欠けているものが無いか（plugin リポジトリ自身の検証）。"""
    for name in PLUGIN_FILES:
        if not (PLUGIN_ROOT / name).exists():
            errors.append(f"{name}: 無い（検証の仕組みが不完全）")

    check_version_consistency()

    hooks_file = PLUGIN_ROOT / "hooks/hooks.json"
    if hooks_file.exists():
        try:
            hooks = json.loads(hooks_file.read_text(encoding="utf-8")).get("hooks", {})
        except json.JSONDecodeError as e:
            err(hooks_file, f"JSON として壊れている（hook が全て無効になる）: {e}")
            hooks = {}
        for event in ("PostToolUse", "Stop", "SessionStart"):
            body = json.dumps(hooks.get(event, []), ensure_ascii=False)
            if "hook.py" not in body:
                err(hooks_file, f"{event} の hook が消えている（hook.py）")
        check_hook_portability(hooks_file)

    check_hook_entrypoint()
    check_command_names()
    check_plugin_is_generic()
    check_documented_paths()


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

DOCS = ["README.md", "CLAUDE.md", "pd-skill-blueprint.md",
        "commands/init.md", "commands/validate.md",
        "commands/uninstall.md", "commands/update.md",
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
    if "pd-skill-blueprint.md" not in body:
        err(entry, "blueprint / README 同期の促しが消えている")
    # 更新は放っておくと届かない（サードパーティの配布元は既定で自動更新されない）。
    # 起動時に知らせないと、手元だけ古いまま CI と判定が食い違う。
    if "update_check" not in body:
        err(entry, "起動時の更新の案内が消えている（利用者に新しい版が届かない）")


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

    # pd-init が利用プロジェクトの CI に焼き込む版。古いまま配ると、
    # 初期状態から手元（最新）と CI（旧版）で判定が食い違う。
    init = PLUGIN_ROOT / "commands/init.md"
    if init.exists():
        refs = re.findall(r"ref:\s*v([\d.]+)", init.read_text(encoding="utf-8"))
        for ref in refs:
            if ref != version:
                err(init, f"CI に焼き込む ref が古い（v{ref} ≠ v{version}）。"
                          "新しいプロジェクトが旧版の判定器で CI を回すことになる")


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


def check_product(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
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
            check_validation(path)
        elif rel.startswith("reviews/") and path.suffix == ".md":
            check_review(path)
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
