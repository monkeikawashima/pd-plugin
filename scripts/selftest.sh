#!/bin/sh
# validate.py が本当に違反を検出するかを確かめる。
#
#     sh scripts/selftest.sh
#
# 常に成功する検証器は、無いのと同じ。
# 検証項目を追加したら、ここにも壊れた例を1つ追加する。
#
# plugin 本体とプロジェクトは別物なので、一時コピーに両方を作って検証する。
#   $WORK/plugin  配布物の複製（framework / hooks / scripts）
#   $WORK/proj    pd を使うプロジェクト（products / analyses / 台帳 / CI）
# 実在のプロダクトには依存しない（検証用の testprod を作る）。

set -e
ROOT=$(cd "$(dirname "$0")/.." && pwd)
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

cp -R "$ROOT" "$WORK/plugin"
rm -rf "$WORK/plugin/.git"
PLUGIN="$WORK/plugin"
PROJ="$WORK/proj"
VALIDATE="$PLUGIN/scripts/validate.py"

fail=0
pass=0

# プロジェクト側の検証
expect() {   # $1 = ラベル / $2 = 期待する検出メッセージ（部分一致）
    if PD_PROJECT_DIR="$PROJ" python3 "$VALIDATE" 2>&1 | grep -q "$2"; then
        printf '  ✓ %s\n' "$1"; pass=$((pass + 1))
    else
        printf '  ✗ %s — 検出されなかった（期待: %s）\n' "$1" "$2"; fail=$((fail + 1))
    fi
}

# plugin 自身の検証（配布物として欠けていないか）
expect_plugin() {
    if PD_PROJECT_DIR="$PLUGIN" python3 "$VALIDATE" 2>&1 | grep -q "$2"; then
        printf '  ✓ %s\n' "$1"; pass=$((pass + 1))
    else
        printf '  ✗ %s — 検出されなかった（期待: %s）\n' "$1" "$2"; fail=$((fail + 1))
    fi
}

prune() { PD_PROJECT_DIR="$PROJ" python3 "$VALIDATE" --accept >/dev/null 2>&1 || true; }

# ------------------------------------------------------------ プロジェクトを作る

mkdir -p "$PROJ/products" "$PROJ/analyses/testprod/2026" "$PROJ/pd" \
         "$PROJ/.github/workflows"
printf '{}\n' > "$PROJ/pd/ledger.json"

cat > "$PROJ/.github/workflows/validate.yml" <<'EOF'
name: validate
on: [push]
jobs:
  validate:
    runs-on: ubuntu-latest
    env:
      TZ: Asia/Tokyo
    steps:
      - uses: actions/checkout@v4
      - uses: actions/checkout@v4
        with:
          repository: monkeikawashima/pd-plugin
          path: .pd-plugin
      - run: python3 .pd-plugin/scripts/validate.py
EOF

cat > "$PROJ/products/testprod.md" <<'EOF'
# プロダクトコンテキスト（検証用）

## KPI

### 必須 Segment

```
必須 Segment: 新規/既存 ・ 利用頻度
```

## Available Evidence
### Qualitative
情報不足。

## Past Experiments
### 結果
無し。

## Decisions
### 決定事項
無し。
### 保留中の見直し
無し。

## Unknowns
### 現時点で不足している情報
不明。
EOF

write_ok_note() {   # $1 = ファイル名 / $2 = 日付
cat > "$PROJ/analyses/testprod/2026/$1" <<EOF
---
product:   testprod
date:      $2
author:    selftest
question:  検証用
framework: discovery
status:    完了
---

# 検証用

> **記述のラベル** — 各記述がどの状態の情報かを示す。
> \`Fact\` 実際に確認できた ／ \`Interpretation\` そこから読み取れること
> \`Hypothesis\` まだ確かめていない考え ／ \`Unknown\` 分からない

## 現状
新規/既存 の別で見た（\`Fact\`）。
EOF
}

write_ok_note "20260901-01-base.md" "2026-09-01"
prune

echo "検証器の自己テスト"
echo ""

# ---------------------------------------------------------------- 形式

printf '# x\n' > "$PROJ/analyses/testprod/wrong-name.md"
expect "命名規則の違反" "命名規則に合わない"
rm "$PROJ/analyses/testprod/wrong-name.md"

cat > "$PROJ/analyses/testprod/2026/20260902-01-t.md" <<'EOF'
---
product: testprod
date: 2026-09-02
---
# テスト
## Evidence
本文。
EOF
expect "frontmatter の欠落" "frontmatter に author が無い"
expect "凡例ブロックの欠落" "凡例ブロックが無い"
expect "見出しの言い換え漏れ" "見出しに日本語の言い換えが無い"
rm "$PROJ/analyses/testprod/2026/20260902-01-t.md"
prune

cp "$PROJ/analyses/testprod/2026/20260901-01-base.md" \
   "$PROJ/analyses/testprod/2026/20260901-01-dup.md"
expect "同日連番の重複" "連番 01 が重複している"
rm "$PROJ/analyses/testprod/2026/20260901-01-dup.md"
prune

# Context の無いプロダクト
mkdir -p "$PROJ/analyses/nocontext/2026"
printf -- '---\nproduct: nocontext\n---\n# x\n' \
    > "$PROJ/analyses/nocontext/2026/20260901-01-t.md"
expect "Context の無いプロダクト" "products/nocontext.md が存在しない"
rm -r "$PROJ/analyses/nocontext"
prune

# ---------------------------------------------------------------- 中身

new_note() {   # $1 = 本文
cat > "$PROJ/analyses/testprod/2026/20260903-01-t.md" <<EOF
---
product:   testprod
date:      2026-09-03
author:    selftest
question:  検証用
framework: discovery / experiment
status:    完了
---

# テスト

> **記述のラベル** — 各記述がどの状態の情報かを示す。
> \`Fact\` 実際に確認できた ／ \`Interpretation\` そこから読み取れること
> \`Hypothesis\` まだ確かめていない考え ／ \`Unknown\` 分からない

$1
EOF
}

new_note '## Evidence（根拠）
新規/既存 で見た。利用が減っている（`Fact`。おそらく告知が届いていない）。'
expect "Fact への推測語の混入" "推測を表す語"

new_note '## Decision（判断）
Improve。'
expect "Decision の見直し条件の欠落" "見直し条件 が無い"
expect "Decision の確認者の欠落" "確認者"
expect "反証の節の欠落" "「反証」の節が無い"

new_note '## Recommended Experiment（検証の設計）
Success Criteria: 完了率が上がる。Decision Rule: 上がれば → 展開する。'
expect "予測値の欠落" "予測値が無い"

new_note '## Hypothesis（仮説）
棄却条件: 比率が高い実測が出れば棄却'
expect "棄却条件の閾値の欠落" "観測可能な閾値が無い"

new_note '## Evidence（根拠）
### Voice の取得
新規/既存 で見た（`Fact`）。'
expect "### 見出しの言い換え漏れ" "見出しに日本語の言い換えが無い"

new_note '## Evidence（根拠）
全体の平均だけを見た（`Fact`。出典: 集計）。'
expect "必須 Segment の未分解（警告）" "必須 Segment"

new_note '## Evidence（根拠）
新規/既存 で見た。申込は 120 件だった（`Fact`）。'
expect "数値の出典欠落（警告）" "出典（テーブル"

new_note '## Evidence（根拠）
新規/既存 で見た（`Fact`）。simulations/testprod/2026/20260901-x.md を参照した。'
expect "予測データの参照" "予測データ（simulations/）を分析で参照している"

rm "$PROJ/analyses/testprod/2026/20260903-01-t.md"
prune

# 適用開始日より前の Note には新しい規約を適用しない
write_ok_note "20260801-01-old.md" "2026-08-01"
cat >> "$PROJ/analyses/testprod/2026/20260801-01-old.md" <<'EOF'

## Decision（判断）
Improve。
EOF
if PD_PROJECT_DIR="$PROJ" python3 "$VALIDATE" 2>&1 | grep -q "「反証」の節が無い"; then
    printf '  ✗ 適用開始日より前の Note が新規約で落ちている\n'; fail=$((fail + 1))
else
    printf '  ✓ 適用開始日より前の Note は新規約の対象外\n'; pass=$((pass + 1))
fi
rm "$PROJ/analyses/testprod/2026/20260801-01-old.md"
prune

# ---------------------------------------------------------------- Voice

mkdir -p "$PROJ/voices/testprod/2026"
cat > "$PROJ/voices/testprod/2026/20260901-interview.md" <<'EOF'
---
product: testprod
date: 2026-09-01
source: interview
context: 商談
---
田中さん: 「使いにくい」
連絡先: taro@example.com
EOF
expect "敬称つき実名の検出" "実名らしい呼称"
expect "メールアドレスの検出" "メールアドレス"
expect "発話者 ID 形式の欠落" "ID 形式で書かれていない"

cat > "$PROJ/voices/testprod/2026/20260901-interview.md" <<'EOF'
---
product: testprod
date: 2026-09-01
source: interview
context: 商談
---
利用者A-1（小規模）: 「担当の高橋に確認します」
EOF
expect "敬称なし実名（姓）の検出" "実名らしい語"

cat > "$PROJ/voices/testprod/2026/20260901-interview.md" <<'EOF'
---
product: testprod
date: 2026-09-01
source: interview
context: 商談
---
利用者A-1: 「速い」
「前のやり方のほうが早い」
EOF
expect "発話行の形式違反" "発話行は"

cat > "$PROJ/voices/testprod/2026/20260901-random.md" <<'EOF'
---
product: testprod
date: 2026-09-01
source: random
context: 雑談
---
利用者A-1: 「速い」
EOF
rm "$PROJ/voices/testprod/2026/20260901-interview.md"
expect "取得経路が許可外" "許可されていない"
rm -r "$PROJ/voices/testprod"
prune

# ---------------------------------------------------------------- 予測データ

mkdir -p "$PROJ/simulations/testprod/2026"
printf -- '---\nproduct: testprod\n---\n# 予測\n' \
    > "$PROJ/simulations/testprod/2026/20260901-test.md"
expect "synthetic フラグの欠落" "synthetic: true が無い"
expect "警告ブロックの欠落" "警告ブロックが無い"
rm -r "$PROJ/simulations/testprod"
prune

# ---------------------------------------------------------------- Context

printf '\n出典: voices/testprod/2026/20260901-interview.md\n' >> "$PROJ/products/testprod.md"
expect "Voice のファイル名の列挙" "ファイル名を列挙している"
python3 - "$PROJ/products/testprod.md" <<'PY'
import pathlib, sys
p = pathlib.Path(sys.argv[1])
s = p.read_text(encoding='utf-8')
p.write_text(s.replace('\n出典: voices/testprod/2026/20260901-interview.md\n', ''),
             encoding='utf-8')
PY

# ---------------------------------------------------------------- リポジトリ

touch "$PROJ/analyses/testprod/2026/export.csv" "$PROJ/analyses/testprod/index.md"
expect "生データの混入" "生データ・画像はリポジトリに置かない"
expect "索引ファイルの作成" "索引ファイルを作らない"
rm "$PROJ/analyses/testprod/2026/export.csv" "$PROJ/analyses/testprod/index.md"

touch "$PROJ/.DS_Store"
expect "OS のノイズファイル" "OS が作る不要ファイル"
rm -f "$PROJ/.DS_Store"

printf '\ntestprod のケースでは\n' >> "$PLUGIN/skills/pd/framework/kpi.md"
expect "framework への固有名の混入" "プロダクト固有名"
cp "$ROOT/skills/pd/framework/kpi.md" "$PLUGIN/skills/pd/framework/kpi.md"

# ---------------------------------------------------------------- 履歴（台帳）

# 書いた当日の仕上げは通る（まだ「過去の記録」ではない）
python3 - "$PROJ/analyses/testprod/2026/20260901-01-base.md" <<'PY'
import pathlib, sys
p = pathlib.Path(sys.argv[1])
p.write_text(p.read_text(encoding='utf-8') + '\n当日の仕上げ\n', encoding='utf-8')
PY
if PD_PROJECT_DIR="$PROJ" python3 "$VALIDATE" >/dev/null 2>&1; then
    printf '  ✓ 書いた当日の仕上げは通る\n'; pass=$((pass + 1))
else
    printf '  ✗ 書いた当日の仕上げが止められている\n'; fail=$((fail + 1))
fi

# 台帳に載った日より後の書き換えは止まる
python3 - "$PROJ" <<'PY'
import json, pathlib, sys
proj = pathlib.Path(sys.argv[1])
led = proj / 'pd/ledger.json'
d = json.loads(led.read_text(encoding='utf-8'))
for k in d:
    d[k]['seen'] = '2026-01-01'
led.write_text(json.dumps(d, ensure_ascii=False, indent=2, sort_keys=True), encoding='utf-8')
p = proj / 'analyses/testprod/2026/20260901-01-base.md'
p.write_text(p.read_text(encoding='utf-8') + '\n後日の書き換え\n', encoding='utf-8')
PY
expect "後日の書き換え" "過去の記録が変更されている"
PD_PROJECT_DIR="$PROJ" python3 "$VALIDATE" --accept >/dev/null 2>&1
if grep -q "20260901-01-base.md" "$PROJ/pd/ledger-log.md"; then
    printf '  ✓ 承認ログへの記録\n'; pass=$((pass + 1))
else
    printf '  ✗ 承認ログへの記録 — 残らなかった\n'; fail=$((fail + 1))
fi

mv "$PROJ/analyses/testprod/2026/20260901-01-base.md" "$WORK/moved.md"
expect "記録の削除・リネーム" "台帳にあるが存在しない"
mv "$WORK/moved.md" "$PROJ/analyses/testprod/2026/20260901-01-base.md"
prune

# ------------------------------------------------------- 仕組みの無効化（プロジェクト側）

mv "$PROJ/pd/ledger.json" "$WORK/ledger.json"
expect "台帳の削除" "pd/ledger.json: 無い"
mv "$WORK/ledger.json" "$PROJ/pd/ledger.json"

mv "$PROJ/.github/workflows/validate.yml" "$WORK/ci.yml"
expect "CI の削除" "検証の仕組みが不完全"
mv "$WORK/ci.yml" "$PROJ/.github/workflows/validate.yml"

sed_replace() {   # $1 = ファイル / $2 = 置換前 / $3 = 置換後
python3 - "$1" "$2" "$3" <<'PY'
import pathlib, sys
p = pathlib.Path(sys.argv[1])
p.write_text(p.read_text(encoding='utf-8').replace(sys.argv[2], sys.argv[3]),
             encoding='utf-8')
PY
}

CI="$PROJ/.github/workflows/validate.yml"
sed_replace "$CI" "TZ: Asia/Tokyo" "TZ: UTC"
expect "CI のタイムゾーン指定の消失" "台帳の当日判定が手元とずれる"
sed_replace "$CI" "TZ: UTC" "TZ: Asia/Tokyo"

sed_replace "$CI" "monkeikawashima/pd-plugin" "octocat/hello"
expect "CI が plugin を取得しない" "plugin を取得する手順が無い"
sed_replace "$CI" "octocat/hello" "monkeikawashima/pd-plugin"

# ------------------------------------------------------- 仕組みの無効化（plugin 側）

python3 - "$PLUGIN/hooks/hooks.json" <<'PY'
import json, pathlib, sys
p = pathlib.Path(sys.argv[1])
d = json.loads(p.read_text(encoding='utf-8'))
d['hooks']['PostToolUse'] = [h for h in d['hooks']['PostToolUse']
                             if 'validate.py' not in json.dumps(h)]
d['hooks'].pop('SessionStart', None)
d['hooks'].pop('Stop', None)
p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')
PY
expect_plugin "PostToolUse hook の削除" "PostToolUse の hook が消えている"
expect_plugin "SessionStart hook の削除" "SessionStart の hook が消えている"
expect_plugin "Stop hook の削除" "Stop の hook が消えている"
cp "$ROOT/hooks/hooks.json" "$PLUGIN/hooks/hooks.json"

sed_replace "$PLUGIN/hooks/hooks.json" "pd/ledger.json" "pd/marker.json"
expect_plugin "pd プロジェクト判定の消失" "pd プロジェクトの判定が無い"
cp "$ROOT/hooks/hooks.json" "$PLUGIN/hooks/hooks.json"

mv "$PLUGIN/commands/pd-init.md" "$WORK/pd-init.md"
expect_plugin "配布物（コマンド）の欠落" "commands/pd-init.md: 無い"
mv "$WORK/pd-init.md" "$PLUGIN/commands/pd-init.md"

mv "$PLUGIN/.claude-plugin/marketplace.json" "$WORK/marketplace.json"
expect_plugin "marketplace 定義の欠落" "marketplace.json: 無い"
mv "$WORK/marketplace.json" "$PLUGIN/.claude-plugin/marketplace.json"

mv "$PLUGIN/scripts/selftest.sh" "$WORK/selftest.sh"
expect_plugin "selftest.sh の削除" "検証の仕組みが不完全"
mv "$WORK/selftest.sh" "$PLUGIN/scripts/selftest.sh"

# ---------------------------------------------------------------- 誤検知の確認（最重要）

prune
if PD_PROJECT_DIR="$PROJ" python3 "$VALIDATE" >/dev/null 2>&1; then
    printf '  ✓ 正常なプロジェクトでは通る\n'; pass=$((pass + 1))
else
    printf '  ✗ 正常なプロジェクトで違反を出している（誤検知）\n'
    PD_PROJECT_DIR="$PROJ" python3 "$VALIDATE" 2>&1 | sed 's/^/      /'
    fail=$((fail + 1))
fi

if PD_PROJECT_DIR="$PLUGIN" python3 "$VALIDATE" >/dev/null 2>&1; then
    printf '  ✓ 正常な plugin では通る\n'; pass=$((pass + 1))
else
    printf '  ✗ 正常な plugin で違反を出している（誤検知）\n'
    PD_PROJECT_DIR="$PLUGIN" python3 "$VALIDATE" 2>&1 | sed 's/^/      /'
    fail=$((fail + 1))
fi

echo ""
if [ "$fail" -gt 0 ]; then
    echo "自己テスト失敗: $fail 件（成功 $pass 件）"
    echo "検証器が期待どおりに機能していません。"
    exit 1
fi
echo "✓ 自己テスト成功: $pass 件すべて検出できました"
