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
#   $WORK/proj    pd を使うプロジェクト（pd/products / pd/analyses / 台帳 / CI）
# 実在のプロダクトには依存しない（検証用の testprod を作る）。

set -e
ROOT=$(cd "$(dirname "$0")/.." && pwd)
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

cp -R "$ROOT" "$WORK/plugin"
rm -rf "$WORK/plugin/.git"
PLUGIN="$WORK/plugin"
PROJ="$WORK/proj"
PD="$PROJ/pd"          # 分析データの根。v0.5.0 からプロジェクト直下ではなくここ
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

# 違反が1件も出ないこと（正常系）
expect_ok() {   # $1 = ラベル
    if PD_PROJECT_DIR="$PROJ" python3 "$VALIDATE" >/dev/null 2>&1; then
        printf '  ✓ %s\n' "$1"; pass=$((pass + 1))
    else
        printf '  ✗ %s — 違反が出た:\n' "$1"; fail=$((fail + 1))
        PD_PROJECT_DIR="$PROJ" python3 "$VALIDATE" 2>&1 | sed 's/^/      /'
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

# 誤検知していないこと（このメッセージが出てはいけない）
expect_no() {   # $1 = ラベル / $2 = 出てはいけないメッセージ
    if PD_PROJECT_DIR="$PROJ" python3 "$VALIDATE" 2>&1 | grep -q "$2"; then
        printf '  ✗ %s — 誤検知した（%s）\n' "$1" "$2"; fail=$((fail + 1))
    else
        printf '  ✓ %s\n' "$1"; pass=$((pass + 1))
    fi
}

sed_replace() {   # $1 = ファイル / $2 = 置換前 / $3 = 置換後
python3 - "$1" "$2" "$3" <<'PY'
import pathlib, sys
p = pathlib.Path(sys.argv[1])
p.write_text(p.read_text(encoding='utf-8').replace(sys.argv[2], sys.argv[3]),
             encoding='utf-8')
PY
}

# ------------------------------------------------------------ プロジェクトを作る

mkdir -p "$PD/products" "$PD/analyses/testprod/2026" "$PROJ/pd" \
         "$PROJ/.github/workflows"
printf '{}\n' > "$PROJ/pd/ledger.json"

# CI が固定する版は、いま検証している plugin の版と揃っているのが正常な状態
PLUGIN_VERSION=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['version'])" \
                 "$PLUGIN/.claude-plugin/plugin.json")

cat > "$PROJ/.github/workflows/validate.yml" <<EOF
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
          ref: v$PLUGIN_VERSION
          path: .pd-plugin
      - run: python3 .pd-plugin/scripts/validate.py
EOF

cat > "$PD/products/testprod.md" <<'EOF'
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
cat > "$PD/analyses/testprod/2026/$1" <<EOF
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

| Segment | 状態 | 内容 / 引けない理由 |
|---|---|---|
| 新規/既存 | 分解済み | 継続率 62% / 81%（\`Fact\`） |
| 利用頻度 | 分解済み | 週1以上 74%（\`Fact\`） |
EOF
}

write_ok_note "20260901-01-base.md" "2026-09-01"
prune

echo "検証器の自己テスト"
echo ""

# ---------------------------------------------------------------- 形式

printf '# x\n' > "$PD/analyses/testprod/wrong-name.md"
expect "命名規則の違反" "命名規則に合わない"
rm "$PD/analyses/testprod/wrong-name.md"

cat > "$PD/analyses/testprod/2026/20260902-01-t.md" <<'EOF'
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
rm "$PD/analyses/testprod/2026/20260902-01-t.md"
prune

cp "$PD/analyses/testprod/2026/20260901-01-base.md" \
   "$PD/analyses/testprod/2026/20260901-01-dup.md"
expect "同日連番の重複" "連番 01 が重複している"
rm "$PD/analyses/testprod/2026/20260901-01-dup.md"
prune

# Context の無いプロダクト
mkdir -p "$PD/analyses/nocontext/2026"
printf -- '---\nproduct: nocontext\n---\n# x\n' \
    > "$PD/analyses/nocontext/2026/20260901-01-t.md"
expect "Context の無いプロダクト" "products/nocontext.md が存在しない"
rm -r "$PD/analyses/nocontext"
prune

# ---------------------------------------------------------------- 中身

new_note() {   # $1 = 本文
cat > "$PD/analyses/testprod/2026/20260903-01-t.md" <<EOF
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

# 散文で語に触れただけでは分解したことにならない。
# 旧実装は「本文のどこかに語が出現するか」を見ていたので、**否定文でも通っていた。**
new_note '## Evidence（根拠）
新規/既存 と 利用頻度 では分解できていない（`Fact`。出典: 集計）。'
expect "散文で触れただけの Segment（偽陰性）" "「新規/既存」の宣言が無い"

# 表の行として宣言すれば通る
new_note '## Evidence（根拠）

| Segment | 状態 | 内容 / 引けない理由 |
|---|---|---|
| 新規/既存 | 分解済み | 継続率 62% / 81%（`Fact`。出典: 集計） |
| 利用頻度 | 分解済み | 週1以上 74%（`Fact`。出典: 集計） |'
expect_no "表で宣言した Segment は通る" "必須 Segment"

# 引けないことを理由つきで宣言した Note は通す。
# **誠実な文書と手抜きの文書を区別できない判定は、作文を生む。**
new_note '## Evidence（根拠）

| Segment | 状態 | 内容 / 引けない理由 |
|---|---|---|
| 新規/既存 | 分解済み | 継続率 62% / 81%（`Fact`。出典: 集計） |
| 利用頻度 | Unknown | 現在値が未計測（MP-003 で計測予定） |'
expect_no "理由つき Unknown は通る（偽陽性）" "必須 Segment"

new_note '## Evidence（根拠）

| Segment | 状態 | 内容 / 引けない理由 |
|---|---|---|
| 新規/既存 | 分解済み | 継続率 62% / 81%（`Fact`。出典: 集計） |
| 利用頻度 | Unknown | |'
expect "理由の無い Unknown（警告）" "引けないとだけ書かれている"

# 定義側。括弧の内側の `/` で切ると、照合語が壊れて原理的に通らなくなる
sed_replace "$PD/products/testprod.md" \
  '必須 Segment: 新規/既存 ・ 利用頻度' \
  '必須 Segment: 新規/既存（A / B）・ 利用頻度'
new_note '## Evidence（根拠）
全体の平均だけを見た（`Fact`。出典: 集計）。'
expect "括弧の内側の / では切らない（軸が割れない）" "「新規/既存（A / B）」の宣言が無い"
sed_replace "$PD/products/testprod.md" \
  '必須 Segment: 新規/既存（A / B）・ 利用頻度' \
  '必須 Segment: 新規/既存 ・ 利用頻度'

# frontmatter の構造化リスト（v1.5.0〜）。区切り文字を推測しない
sed_replace "$PD/products/testprod.md" \
  '# プロダクトコンテキスト（検証用）' \
  '---
segments:
  - id: tenure
    label: 新規/既存
    values: [A / 小規模, B / 大規模]
  - id: usage_frequency
    label: 利用頻度
---

# プロダクトコンテキスト（検証用）'
new_note '## Evidence（根拠）

| Segment | 状態 | 内容 / 引けない理由 |
|---|---|---|
| 新規/既存 | 分解済み | 62% / 81%（`Fact`。出典: 集計） |
| 利用頻度 | 分解済み | 74%（`Fact`。出典: 集計） |'
expect_no "frontmatter の構造化リストを読む" "必須 Segment"

new_note '## Evidence（根拠）

| Segment | 状態 | 内容 / 引けない理由 |
|---|---|---|
| 新規/既存 | 分解済み | 62% / 81%（`Fact`。出典: 集計） |'
expect "構造化リストの片方が沈黙している" "「利用頻度」の宣言が無い"

new_note '## Evidence（根拠）
新規/既存 で見た。申込は 120 件だった（`Fact`）。'
expect "数値の出典欠落（警告）" "出典（テーブル"

new_note '## Evidence（根拠）
新規/既存 で見た（`Fact`）。simulations/testprod/2026/20260901-x.md を参照した。'
expect "予測データの参照" "予測データ（simulations/）を分析で参照している"

rm "$PD/analyses/testprod/2026/20260903-01-t.md"
prune

# 適用開始日より前の Note には新しい規約を適用しない
write_ok_note "20260801-01-old.md" "2026-08-01"
cat >> "$PD/analyses/testprod/2026/20260801-01-old.md" <<'EOF'

## Decision（判断）
Improve。
EOF
if PD_PROJECT_DIR="$PROJ" python3 "$VALIDATE" 2>&1 | grep -q "「反証」の節が無い"; then
    printf '  ✗ 適用開始日より前の Note が新規約で落ちている\n'; fail=$((fail + 1))
else
    printf '  ✓ 適用開始日より前の Note は新規約の対象外\n'; pass=$((pass + 1))
fi
rm "$PD/analyses/testprod/2026/20260801-01-old.md"
prune

# ---------------------------------------------------------------- Voice

mkdir -p "$PD/voices/testprod/2026"

# v0.6.0 の書式。1ファイル = 1声。frontmatter 12キー必須。
voice() {   # $1 = 追加/上書きする frontmatter 行、$2 = 本文
  cat > "$PD/voices/testprod/2026/VOICE-001-slow.md" <<EOF
---
id: VOICE-001
product: testprod
type: pain
source: interview
speaker_role: end-user
speaker_id: U-01
captured_at: 2026-09-01
captured_by: tester
layer: 未判定
severity: medium
frequency: 1
status: 未検証
$1
---
$2
EOF
}

voice "" "田中さん: 「使いにくい」
連絡先: taro@example.com"
expect "敬称つき実名の検出" "実名らしい呼称"
expect "メールアドレスの検出" "メールアドレス"
expect "発話者 ID 形式の欠落" "ID 形式で書かれていない"

voice "" "利用者A-1（小規模）: 「担当の高橋に確認します」"
expect "敬称なし実名（姓）の検出" "実名らしい語"

voice "" "利用者A-1: 「速い」
「前のやり方のほうが早い」"
expect "発話行の形式違反" "発話行は"

voice "screen: home/top" "利用者A-1: 「速い」"
expect_ok "任意キー screen は通る"

voice "mood: happy" "利用者A-1: 「速い」"
expect "未知の frontmatter キー" "未知の frontmatter キー"

voice "" "利用者A-1: 「速い」"
sed -i.bak 's/^type: pain$/type: つらい/' "$PD/voices/testprod/2026/VOICE-001-slow.md"
rm -f "$PD/voices/testprod/2026/VOICE-001-slow.md.bak"
expect "type が enum 外" "type が不正"

# v1.0.0: speaker_role は enum をやめた。値は縛らないが、形式は縛る。
# ここが通ってしまうと「Staff / 店舗スタッフ / store staff」が同居し、query で引けなくなる。
voice "" "利用者A-1: 「速い」"
sed -i.bak 's/^speaker_role: end-user$/speaker_role: 店舗スタッフ/' "$PD/voices/testprod/2026/VOICE-001-slow.md"
rm -f "$PD/voices/testprod/2026/VOICE-001-slow.md.bak"
expect "speaker_role の形式違反" "speaker_role の形式が不正"

voice "" "利用者A-1: 「速い」"
sed -i.bak 's/^speaker_role: end-user$/speaker_role: Operator/' "$PD/voices/testprod/2026/VOICE-001-slow.md"
rm -f "$PD/voices/testprod/2026/VOICE-001-slow.md.bak"
expect "speaker_role の大文字混入" "speaker_role の形式が不正"

# 役割名はプロジェクトが taxonomy.json で宣言する。宣言した瞬間から縛られる。
voice "" "利用者A-1: 「速い」"
expect_ok "taxonomy.json が無ければ形式だけ見る"

printf '{"speaker_role": ["operator", "admin"], "object": [], "phase": []}\n' \
  > "$PD/voices/taxonomy.json"
expect "taxonomy.json に無い speaker_role" "speaker_role が taxonomy.json にない"

printf '{"speaker_role": ["end-user", "operator"], "object": [], "phase": []}\n' \
  > "$PD/voices/taxonomy.json"
expect_ok "taxonomy.json に載っている speaker_role は通る"
rm -f "$PD/voices/taxonomy.json"

voice "" "利用者A-1: 「速い」"
sed -i.bak 's/^id: VOICE-001$/id: VOICE-009/' "$PD/voices/testprod/2026/VOICE-001-slow.md"
rm -f "$PD/voices/testprod/2026/VOICE-001-slow.md.bak"
expect "id とファイル名の不一致" "ファイル名の番号"

voice "" "利用者A-1: 「速い」"
sed -i.bak 's/^captured_at: 2026-09-01$/captured_at: 2025-09-01/' "$PD/voices/testprod/2026/VOICE-001-slow.md"
rm -f "$PD/voices/testprod/2026/VOICE-001-slow.md.bak"
expect "年フォルダと captured_at の不一致" "captured_at"

voice "" "利用者A-1: 「速い」"
expect_ok "正しいボイスは通る"
rm -r "$PD/voices/testprod"
prune

# ---------------------------------------------------------------- UXDR

mkdir -p "$PD/decisions/testprod/2026"
uxdr() {   # $1 = kind、$2 = 本文
  cat > "$PD/decisions/testprod/2026/UXDR-20260901-01-nav.md" <<EOF
---
product: testprod
date: 2026-09-01
layer: 骨格
kind: $1
status: 有効
---

# UXDR-20260901-01 — 試験

## 決めたこと

- 何か

$2
EOF
}

uxdr "決定" "## 根拠

なし

## 影響範囲

- 変わらなかったもの: 無し"
expect "決めなかったことの節が無い" "決めなかったこと"

uxdr "決定" "## 決めなかったこと

保留。

## 根拠

なし

## 影響範囲

- 変わらなかったもの: 無し"
expect "未決定に3列が無い" "何が分かれば"

uxdr "作業仮説" "## 決めなかったこと

| 論点 | 何が分かれば決まるか | いつまでに | 誰が |
|---|---|---|---|
| A | B | 2026-09-30 | BIZ |

## 根拠

なし

## 棄却条件

- そのうち分かる

## 影響範囲

- 変わらなかったもの: 無し"
expect "棄却条件に閾値が無い" "観測可能な閾値"

uxdr "決定" "## 決めなかったこと

| 論点 | 何が分かれば決まるか | いつまでに | 誰が |
|---|---|---|---|
| A | B | 2026-09-30 | BIZ |

## 根拠

なし

## 影響範囲

- 下流の spec: 無し"
expect "影響範囲に変わらなかったものが無い" "変わらなかったもの"

uxdr "決定" "## 決めなかったこと

| 論点 | 何が分かれば決まるか | いつまでに | 誰が |
|---|---|---|---|
| A | B | 2026-09-30 | BIZ |

## 根拠

| 種別 | 内容 |
|---|---|
| 計測値 | 未取得 |

## 影響範囲

- 変わらなかったもの: 表層の spec（確認済み）"
uxdr "作業仮説" "## 決めなかったこと

| 論点 | 何が分かれば決まるか | いつまでに | 誰が |
|---|---|---|---|
| A | B | 2026-09-30 | BIZ |

## 根拠

なし

## 作業仮説と棄却条件

| 作業仮説 | 棄却条件 |
|---|---|
| 実利用は乗っていない | 店舗アカウントが 2 件以上になった時点で棄却 |

## 影響範囲

- 変わらなかったもの: 無し"
expect_ok "表形式の棄却条件は通る（見出し行に閾値を求めない）"

expect_ok "正しい UXDR は通る"
rm -r "$PD/decisions/testprod"
prune
prune

# ---------------------------------------------------------------- 探索計画
#
# VP（検証）と RP（探索）は別物だが置き場所は同じ。分けると片方が忘れられる。

mkdir -p "$PD/validations/testprod/2026"
RP="$PD/validations/testprod/2026/RP-20260901-01-explore.md"

cat > "$RP" <<'EOF'
---
product: testprod
date: 2026-09-01
kind: 探索
status: 計画
---

# RP-20260901-01 — 探索

## 見に行く対象

現場の作業を観察する。
EOF
expect "探索計画の対象者の欠落" "対象者の欄が無い"
expect "探索計画の聞かないことの欠落" "「聞かないこと」が無い"
expect "探索計画の記録先の欠落" "逐語の記録先が無い"

cat > "$RP" <<'EOF'
---
product: testprod
date: 2026-09-01
kind: 探索
status: 計画
---

# RP-20260901-01 — 探索

## 見に行く対象

現場の作業を観察する。

## 聞かないこと

「あったら使いますか」は聞かない。

## 実施

| 項目 | 値 | 決める人 |
|---|---|---|
| 対象者の人数・役割 | 未定 | 企画 |

## 記録

逐語のまま pd/voices/ へ流す。
EOF
expect_ok "正しい探索計画は通る"

# 検証計画（VP-）の判定は、探索計画に置き換わっていない
BADVP="$PD/validations/testprod/2026/VP-20260901-01-hypo.md"
printf '# 検証\n\n観察する。\n' > "$BADVP"
expect "検証計画の棄却条件の欠落（RP と取り違えない）" "棄却しうる形でない"
rm -f "$BADVP"

rm -rf "$PD/validations"
prune

# ---------------------------------------------------------------- 層の成果物
#
# specs/ は現在値であり追記のみではない。台帳ではなく**空白の書き方**を見る。
# 判定を足したら、ここに壊れた例を1つ足す。

mkdir -p "$PD/specs/01-strategy" "$PD/specs/02-requirements" \
         "$PD/specs/04-skeleton/screens" "$PD/specs/05-surface"

PERSONA="$PD/specs/01-strategy/personas.md"

# 台帳を引かずに書いた像（＝集計ではなく創作）
cat > "$PERSONA" <<'EOF'
# 利用者像

## 利用者A
よく使ってくれている人。
EOF
expect "ペルソナの確信度の欠落" "確信度"
expect "ペルソナの根拠の欠落" "台帳を引かずに書いた像"
expect "ペルソナの非対象の欠落" "非対象"

# 作業仮説なのに捨てる条件が無い
cat > "$PERSONA" <<'EOF'
# 利用者像

## 利用者A

| 項目 | 値 |
|---|---|
| 根拠件数 | n = 3 |
| 確信度 | 作業仮説 |

### 関心

| 関心 | 根拠 |
|---|---|
| 探すのに手が止まる | VOICE-001 |

### 非対象

| 含めない人 | 理由 |
|---|---|
| 未定義 | |
EOF
expect "ペルソナの棄却条件の欠落" "棄却条件が無い"

# 装飾属性は警告（誤検知で判定器を殺さないため、止めはしない）
cat > "$PERSONA" <<'EOF'
# 利用者像

## 利用者A

| 項目 | 値 |
|---|---|
| 根拠件数 | n = 3 |
| 確信度 | 実証 |
| 年齢 | 42歳 |

### 関心

| 関心 | 根拠 |
|---|---|
| 探すのに手が止まる | VOICE-001 |

### 非対象

| 含めない人 | 理由 |
|---|---|
| 未定義 | |
EOF
expect "ペルソナの装飾属性（警告）" "装飾属性"

# 引用している行は「使って」いない。禁止表現の語彙に頼ると「使わない」で漏れる
cat > "$PERSONA" <<'EOF'
# 利用者像

「年齢」「性別」は判断に効かないので使わない。

## 利用者A

| 項目 | 値 |
|---|---|
| 根拠件数 | n = 3 |
| 確信度 | 実証 |

### 関心

| 関心 | 根拠 |
|---|---|
| 探すのに手が止まる | VOICE-001 |

### 非対象

| 含めない人 | 理由 |
|---|---|
| 未定義 | |
EOF
expect_no "引用した装飾属性は通す（語尾が「使わない」でも）" "装飾属性"

# 正常なペルソナ（件数0の系統を「未取得」で残す形も含む）
cat > "$PERSONA" <<'EOF'
# 利用者像

## 利用者A

| 項目 | 値 |
|---|---|
| 根拠件数 | n = 3（2026-01 〜 2026-08） |
| 確信度 | 実証 |

### 関心

| 関心 | 根拠 |
|---|---|
| 探すのに手が止まる | VOICE-001 |

### 非対象

| 含めない人 | 理由 |
|---|---|
| 未定義 | |

## 利用者B

根拠件数 n = 0。確信度は未取得のため、像を書かない。
EOF
expect_ok "正しいペルソナは通る"

JOURNEY="$PD/specs/02-requirements/journeys.md"

# 計測と切り離された「絵」
cat > "$JOURNEY" <<'EOF'
# ジャーニー

## 流れ

| # | ステップ |
|---|---|
| 1 | 開く |
EOF
expect "ジャーニーと計測の分離" "主要タスク時間との対応が無い"
expect "ジャーニーの対象ペルソナの欠落" "対象ペルソナの指定が無い"
expect "ジャーニーの根拠の欠落" "「一次情報なし」も無い"

# 所要時間を空欄のまま置く（それらしい数字も未取得も無い）
cat > "$JOURNEY" <<'EOF'
# ジャーニー

対象ペルソナ: 利用者A
主要タスク時間 = 探す + 決める

| # | ステップ | 根拠 | 所要時間 |
|---|---|---|---|
| 一 | 探す | VOICE-〇〇〇 | |
EOF
expect "ジャーニーの所要時間の空欄" "値も「未取得」も無い"

cat > "$JOURNEY" <<'EOF'
# ジャーニー

対象ペルソナ: 利用者A
主要タスク時間 = 探す + 決める

| # | ステップ | 根拠 | 所要時間 |
|---|---|---|---|
| 1 | 探す | VOICE-001 | 未取得 |
| 2 | 決める | 一次情報なし | 未取得 |
EOF
expect_ok "正しいジャーニーは通る"

SCREEN="$PD/specs/04-skeleton/screens/list.md"

# 空振り状態の欠落（最も多い事故）と、表層の値の直書き
cat > "$SCREEN" <<'EOF'
# 一覧

## 顧客ボイス

VOICE-001 を引き当てた。

## 状態設計

| 状態 | 設計 |
|---|---|
| 初期 | |
| 処理中 | |
| 成功 | |
| エラー | |

## 表層

見出しの色は #1a1a1a。
EOF
expect "画面仕様の空振り状態の欠落" "空振り"
expect "画面仕様への色の直書き" "色の値を画面仕様に直書き"

cat > "$SCREEN" <<'EOF'
# 一覧

## 顧客ボイス

引き当て0件のため一次情報なし。改善案はデザイナー起案。

## 状態設計

| 状態 | 設計 |
|---|---|
| 初期 | |
| 処理中 | |
| 成功 | |
| 空振り | 0件のときの文言を出す |
| エラー | |

## 表層

使用トークン: color.text.default
EOF
expect_ok "正しい画面仕様は通る"

TOKENS="$PD/specs/05-surface/design-tokens.md"

cat > "$TOKENS" <<'EOF'
# デザイントークン

| トークン名 | 値 |
|---|---|
| color.text.default | #111111 |
EOF
expect "トークンの真実の源の欠落" "真実の源"
expect "トークンの逸脱一覧の欠落" "逸脱一覧が無い"

cat > "$TOKENS" <<'EOF'
# デザイントークン

真実の源: tokens.css

| トークン名 | 値 |
|---|---|
| color.text.default | #111111 |

## 逸脱一覧

| 箇所 | 内容 | 期限 |
|---|---|---|
| 一覧の補助文言 | 下限割れ | 未定 |
EOF
expect "期限の無い逸脱" "期限の無い例外は恒久化する"

cat > "$TOKENS" <<'EOF'
# デザイントークン

真実の源: tokens.css

| トークン名 | 値 |
|---|---|
| color.text.default | #111111 |

## 逸脱一覧

| 箇所 | 内容 | 期限 |
|---|---|---|
| 一覧の補助文言 | 下限割れ | 2026-09-30 |
EOF
expect_ok "正しいトークン台帳は通る"

NAV="$PD/specs/04-skeleton/navigation.md"

# 到達経路を書かないまま項目を増やす（迷子を検出できない）
cat > "$NAV" <<'EOF'
# ナビゲーション

| 項目名 | 階層 |
|---|---|
| 設定 | 1 |
EOF
expect "ナビの到達経路の欠落" "到達経路が無い"
expect "ナビ項目の対応先の欠落" "対応先（対象物"

cat > "$NAV" <<'EOF'
# ナビゲーション

| 項目名 | 対応先の種別 | 対応先 |
|---|---|---|
| 一覧 | 対象物 | 記録 |

## 到達経路

| 画面 | 到達経路 |
|---|---|
| 一覧 | 入口 → 一覧 |
EOF
expect_ok "正しいナビは通る"

# 「ユーザー」を単独で使う（どの系統か分からないまま合意が成立する）
printf '\nユーザーが不便だと言っている。\n' >> "$NAV"
expect "呼称の省略（警告）" "「ユーザー」を単独で使っている"

# 複合語まで弾くと、正しい語が書けなくなる
cat > "$NAV" <<'EOF'
# ナビゲーション

ユーザーストーリー US-01 とユーザー検証 VP-01 に対応する。

| 項目名 | 対応先の種別 | 対応先 |
|---|---|---|
| 一覧 | 対象物 | 記録 |

## 到達経路

| 画面 | 到達経路 |
|---|---|
| 一覧 | 入口 → 一覧 |
EOF
if PD_PROJECT_DIR="$PROJ" python3 "$VALIDATE" 2>&1 | grep -q "「ユーザー」を単独で使っている"; then
    printf '  ✗ %s — 複合語まで弾いた\n' "複合語は通す"; fail=$((fail + 1))
else
    printf '  ✓ %s\n' "複合語は通す"; pass=$((pass + 1))
fi

# 規約文そのもの。禁止表現の語彙（「書かない」等）を当てにいくと、
# 「使わない」「用いない」「避ける」で漏れる。引用しているかどうかで見る。
cat > "$NAV" <<'EOF'
# ナビゲーション

「ユーザー」を単独で使わない。どの利用者系統かを指定する。

| 項目名 | 対応先の種別 | 対応先 |
|---|---|---|
| 一覧 | 対象物 | 記録 |

## 到達経路

| 画面 | 到達経路 |
|---|---|
| 一覧 | 入口 → 一覧 |
EOF
expect_no "引用した規約文は通す（語尾が「使わない」でも）" "「ユーザー」を単独で使っている"

# 呼称を決める当のファイルを、その規約で裁かない（自己言及の矛盾）
mkdir -p "$PD/specs/01-strategy"
printf '# 用語集\n\nユーザーが不便、のような書き方をしない。\n' \
    > "$PD/specs/01-strategy/glossary.md"
expect_no "呼称を定義するファイル自身は対象外" "「ユーザー」を単独で使っている"
rm "$PD/specs/01-strategy/glossary.md"

# specs は現在値。ここで作った検証用の成果物は残さない
rm -rf "$PD/specs"

# ---------------------------------------------------------------- 予測データ

mkdir -p "$PD/simulations/testprod/2026"
printf -- '---\nproduct: testprod\n---\n# 予測\n' \
    > "$PD/simulations/testprod/2026/20260901-test.md"
expect "synthetic フラグの欠落" "synthetic: true が無い"
expect "警告ブロックの欠落" "警告ブロックが無い"
rm -r "$PD/simulations/testprod"
prune

# ---------------------------------------------------------------- Context

printf '\n出典: voices/testprod/2026/20260901-interview.md\n' >> "$PD/products/testprod.md"
expect "Voice のファイル名の列挙" "ファイル名を列挙している"
python3 - "$PD/products/testprod.md" <<'PY'
import pathlib, sys
p = pathlib.Path(sys.argv[1])
s = p.read_text(encoding='utf-8')
p.write_text(s.replace('\n出典: voices/testprod/2026/20260901-interview.md\n', ''),
             encoding='utf-8')
PY

# ---------------------------------------------------------------- リポジトリ

touch "$PD/analyses/testprod/2026/export.csv" "$PD/analyses/testprod/index.md"
expect "生データの混入" "生データ・画像はリポジトリに置かない"
expect "索引ファイルの作成" "索引ファイルを作らない"
rm "$PD/analyses/testprod/2026/export.csv" "$PD/analyses/testprod/index.md"

touch "$PD/.DS_Store"
expect "OS のノイズファイル" "OS が作る不要ファイル"
rm -f "$PD/.DS_Store"

# pd の管轄は pd/ の中だけ。アプリのソースと同居しているリポジトリで root 全体を
# 見ると、pd と無関係のファイルで判定器が常に赤くなり、誰も見なくなる。
mkdir -p "$PROJ/public"
touch "$PROJ/.DS_Store" "$PROJ/public/logo.png"
expect_ok "pd/ の外は見ない（同居しているアプリの資産で落ちない）"
rm -rf "$PROJ/.DS_Store" "$PROJ/public"

printf '\ntestprod のケースでは\n' >> "$PLUGIN/skills/analyze/framework/kpi.md"
expect "framework への固有名の混入" "プロダクト固有名"
cp "$ROOT/skills/analyze/framework/kpi.md" "$PLUGIN/skills/analyze/framework/kpi.md"

# ---------------------------------------------------------------- 履歴（台帳）

# 書いた当日の仕上げは通る（まだ「過去の記録」ではない）
python3 - "$PD/analyses/testprod/2026/20260901-01-base.md" <<'PY'
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
p = proj / 'pd/analyses/testprod/2026/20260901-01-base.md'
p.write_text(p.read_text(encoding='utf-8') + '\n後日の書き換え\n', encoding='utf-8')
PY
expect "後日の書き換え" "過去の記録が変更されている"
PD_PROJECT_DIR="$PROJ" python3 "$VALIDATE" --accept >/dev/null 2>&1
if grep -q "20260901-01-base.md" "$PROJ/pd/ledger-log.md"; then
    printf '  ✓ 承認ログへの記録\n'; pass=$((pass + 1))
else
    printf '  ✗ 承認ログへの記録 — 残らなかった\n'; fail=$((fail + 1))
fi

mv "$PD/analyses/testprod/2026/20260901-01-base.md" "$WORK/moved.md"
expect "記録の削除・リネーム" "台帳にあるが存在しない"
mv "$WORK/moved.md" "$PD/analyses/testprod/2026/20260901-01-base.md"
prune

# ------------------------------------------------------- 仕組みの無効化（プロジェクト側）

mv "$PROJ/pd/ledger.json" "$WORK/ledger.json"
expect "台帳の削除" "pd/ledger.json: 無い"
mv "$WORK/ledger.json" "$PROJ/pd/ledger.json"

mv "$PROJ/.github/workflows/validate.yml" "$WORK/ci.yml"
expect "CI の削除" "検証の仕組みが不完全"
mv "$WORK/ci.yml" "$PROJ/.github/workflows/validate.yml"

CI="$PROJ/.github/workflows/validate.yml"
sed_replace "$CI" "TZ: Asia/Tokyo" "TZ: UTC"
expect "CI のタイムゾーン指定の消失" "台帳の当日判定が手元とずれる"
sed_replace "$CI" "TZ: UTC" "TZ: Asia/Tokyo"

sed_replace "$CI" "monkeikawashima/pd-plugin" "octocat/hello"
expect "CI が plugin を取得しない" "plugin を取得する手順が無い"
sed_replace "$CI" "octocat/hello" "monkeikawashima/pd-plugin"

# 判定者自身の版のズレ。/pd:update は ref を上げず「伝える」だけだったため、
# 忘れると手元と CI で違う判定器が動いたまま ✓ が出続けていた。
sed_replace "$CI" "ref: v$PLUGIN_VERSION" "ref: v0.0.1"
expect "CI が固定する plugin の版が古い" "CI が固定している plugin の版が古い"
sed_replace "$CI" "ref: v0.0.1" "ref: v9999.0.0"
expect "CI が固定する plugin の版が手元より新しい" "手元より新しい"
sed_replace "$CI" "          ref: v9999.0.0
" ""
expect "CI が plugin の版を固定していない" "plugin の版を固定していない"
sed_replace "$CI" "          path: .pd-plugin" "          ref: v$PLUGIN_VERSION
          path: .pd-plugin"

# ------------------------------------------------------- 仕組みの無効化（plugin 側）

python3 - "$PLUGIN/hooks/hooks.json" <<'PY'
import json, pathlib, sys
p = pathlib.Path(sys.argv[1])
d = json.loads(p.read_text(encoding='utf-8'))
d['hooks']['PostToolUse'] = [h for h in d['hooks']['PostToolUse']
                             if 'hook.py' not in json.dumps(h)]
d['hooks'].pop('SessionStart', None)
d['hooks'].pop('Stop', None)
p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')
PY
expect_plugin "PostToolUse hook の削除" "PostToolUse の hook が消えている"
expect_plugin "SessionStart hook の削除" "SessionStart の hook が消えている"
expect_plugin "Stop hook の削除" "Stop の hook が消えている"
cp "$ROOT/hooks/hooks.json" "$PLUGIN/hooks/hooks.json"

sed_replace "$PLUGIN/scripts/hook.py" "ledger.json" "marker.json"
expect_plugin "pd プロジェクト判定の消失" "目印の判定が無い"
cp "$ROOT/scripts/hook.py" "$PLUGIN/scripts/hook.py"

sed_replace "$PLUGIN/scripts/hook.py" "DECISIONS.md" "somewhere-else.md"
expect_plugin "設計判断の記録の促しの消失" "促しが消えている"
cp "$ROOT/scripts/hook.py" "$PLUGIN/scripts/hook.py"

sed_replace "$PLUGIN/scripts/hook.py" "update_check" "nothing_at_all"
expect_plugin "起動時の更新の案内の消失" "更新の案内が消えている"
cp "$ROOT/scripts/hook.py" "$PLUGIN/scripts/hook.py"

# 止める手段が消えると、残るのは hooks.json を編集する方法だけになり、
# /plugin update のたびに黙って外部通信が復活する。SECURITY.md の約束も嘘になる。
sed_replace "$PLUGIN/scripts/update_check.py" "PD_UPDATE_CHECK" "PD_SOMETHING_ELSE"
expect_plugin "更新確認を止める入口の消失" "止める入口が無い"
cp "$ROOT/scripts/update_check.py" "$PLUGIN/scripts/update_check.py"

sed_replace "$PLUGIN/SECURITY.md" "PD_UPDATE_CHECK" "どこにも書かない"
expect_plugin "止め方の案内の消失" "止め方が書かれていない"
cp "$ROOT/SECURITY.md" "$PLUGIN/SECURITY.md"

# スキルの形。スキルが増えるほど担当の重なりが事故になるため、
# 個々の名前ではなく形（SKILL.md がある / 役割分界の表がある）を守る。
mkdir -p "$PLUGIN/skills/ghost-skill"
expect_plugin "SKILL.md の無いスキル" "skills/ghost-skill/SKILL.md: 無い"
rm -rf "$PLUGIN/skills/ghost-skill"

sed_replace "$PLUGIN/skills/ux-layer-triage/SKILL.md" "役割分界" "やること"
expect_plugin "役割分界の表の消失" "役割分界の表が無い"
cp "$ROOT/skills/ux-layer-triage/SKILL.md" "$PLUGIN/skills/ux-layer-triage/SKILL.md"

sed_replace "$PLUGIN/skills/ux-journey-mapper/SKILL.md" \
            "name: ux-journey-mapper" "name: journey"
expect_plugin "スキル名とディレクトリ名の不一致" "ディレクトリ名"
cp "$ROOT/skills/ux-journey-mapper/SKILL.md" "$PLUGIN/skills/ux-journey-mapper/SKILL.md"

mv "$PLUGIN/scripts/hook.py" "$WORK/hook.py"
expect_plugin "hook の入口の削除" "scripts/hook.py: 無い"
mv "$WORK/hook.py" "$PLUGIN/scripts/hook.py"

mv "$PLUGIN/scripts/update_check.py" "$WORK/update_check.py"
expect_plugin "更新チェックの削除" "scripts/update_check.py: 無い"
mv "$WORK/update_check.py" "$PLUGIN/scripts/update_check.py"

# Windows には sh も jq も無い。hooks.json にシェル構文が戻ると全滅する。
sed_replace "$PLUGIN/hooks/hooks.json" \
            'python3 \"${CLAUDE_PLUGIN_ROOT}/scripts/hook.py\" stop' \
            'jq -r .x | python3 \"${CLAUDE_PLUGIN_ROOT}/scripts/hook.py\" stop'
expect_plugin "シェル依存の記述の復活" "Windows で hook が動かない"
cp "$ROOT/hooks/hooks.json" "$PLUGIN/hooks/hooks.json"

mv "$PLUGIN/commands/init.md" "$WORK/pd-init.md"
expect_plugin "配布物（コマンド）の欠落" "commands/init.md: 無い"
mv "$WORK/pd-init.md" "$PLUGIN/commands/init.md"

# 更新の手順を1つにまとめたコマンド。消えると利用者は2つの順序を覚える羽目になり、
# 順序を間違えると古い版へ戻る。
mv "$PLUGIN/commands/update.md" "$WORK/pd-update.md"
expect_plugin "更新コマンドの欠落" "commands/update.md: 無い"
mv "$WORK/pd-update.md" "$PLUGIN/commands/update.md"

mv "$PLUGIN/.claude-plugin/marketplace.json" "$WORK/marketplace.json"
expect_plugin "marketplace 定義の欠落" "marketplace.json: 無い"
mv "$WORK/marketplace.json" "$PLUGIN/.claude-plugin/marketplace.json"

mv "$PLUGIN/scripts/selftest.sh" "$WORK/selftest.sh"
expect_plugin "selftest.sh の削除" "検証の仕組みが不完全"
mv "$WORK/selftest.sh" "$PLUGIN/scripts/selftest.sh"

mv "$PLUGIN/scripts/release.sh" "$WORK/release.sh"
expect_plugin "配布手順の削除" "scripts/release.sh: 無い"
mv "$WORK/release.sh" "$PLUGIN/scripts/release.sh"

# Release はタグの push で自動作成する。無いと `--no-push` や手動 push で配った版の
# 本文が起動時の更新通知に出ない（v1.4.0 で実際に漏れた）
mv "$PLUGIN/.github/workflows/release.yml" "$WORK/release.yml"
expect_plugin "Release の自動作成の削除" ".github/workflows/release.yml: 無い"
mv "$WORK/release.yml" "$PLUGIN/.github/workflows/release.yml"

# plugin のスキルは必ず名前空間化される。素の /init と書くと利用者が打てない。
sed_replace "$PLUGIN/README.md" "/pd:init" "/init"
expect_plugin "コマンド名の名前空間の欠落" "コマンド名に名前空間が無い"
cp "$ROOT/README.md" "$PLUGIN/README.md"

# v1.0.0 で外した旧名（/pd-init）が残っていても拾う
sed_replace "$PLUGIN/README.md" "/pd:init" "/pd-init"
expect_plugin "旧コマンド名の残骸" "コマンド名に名前空間が無い"
cp "$ROOT/README.md" "$PLUGIN/README.md"

# 素の名前が普通の英単語になったため、パスや変数名を誤検知しないことを確かめる。
# ここが緩いと validate.py / pd/validations/ の言及だけで毎回赤くなり、判定が無視される。
printf '\n実行は `scripts/validate.py`、記録は pd/validations/ の下。\n' >> "$PLUGIN/README.md"
if PD_PROJECT_DIR="$PLUGIN" python3 "$VALIDATE" 2>&1 | grep -q "コマンド名に名前空間が無い"; then
    printf '  ✗ %s — パスへの言及を誤検知した\n' "パスは誤検知しない"; fail=$((fail + 1))
else
    printf '  ✓ %s\n' "パスは誤検知しない"; pass=$((pass + 1))
fi
cp "$ROOT/README.md" "$PLUGIN/README.md"

mv "$PLUGIN/CHANGELOG.md" "$WORK/CHANGELOG.md"
expect_plugin "変更履歴の削除" "CHANGELOG.md: 無い"
mv "$WORK/CHANGELOG.md" "$PLUGIN/CHANGELOG.md"

# v1.0.0: hook 経由では PLUGIN_ROOT がインストール済みの複製を指すため、plugin の
# ソースを開いていてもパスが一致せず「pd を使うプロジェクト」と誤認されていた。
# plugin 自身の CI に不要な checkout を要求する違反が毎ターン出る（＝判定が無視される）。
# 別の場所にある validate.py から plugin のソースを見ても、自己検証になること。
if PD_PROJECT_DIR="$PLUGIN" python3 "$ROOT/scripts/validate.py" 2>&1 \
   | grep -q "plugin を取得する手順が無い"; then
    printf '  ✗ %s — plugin のソースをプロジェクトと誤認した\n' "別パスからでも自己検証になる"
    fail=$((fail + 1))
else
    printf '  ✓ %s\n' "別パスからでも自己検証になる"; pass=$((pass + 1))
fi

# v1.0.0: 配布物に固有プロダクトの語彙・元プロジェクトの実装パスが混ざっていないか。
# この判定が無かったため、飲食予約サービスの業務定義が v0.7.0 まで配布物に残った。
GLOSS="$PLUGIN/skills/analyze/uiux/glossary.md"
cp "$GLOSS" "$WORK/glossary.md"

printf '\n| 店舗スタッフ | 予約を運用する側 |\n' >> "$GLOSS"
expect_plugin "配布物への業種語の混入" "業種固有の語がある"
cp "$WORK/glossary.md" "$GLOSS"

printf '\n- トークン定義: `src/app/globals.css`\n' >> "$GLOSS"
expect_plugin "配布物への外部パス参照の混入" "外部プロジェクトの参照がある"
cp "$WORK/glossary.md" "$GLOSS"

printf '\n```bash\npnpm voices query\n```\n' >> "$GLOSS"
expect_plugin "存在しない npm script の参照" "package.json は無い"
cp "$WORK/glossary.md" "$GLOSS"

# v1.0.0: 文書が案内する置き場所と、検証器の期待がずれていないか。
# v0.6.0 の置き場所変更で、UI/UX 側のスキル5本とテンプレ2本が取り残されていた。
# 案内どおりに書いた UXDR が検証器に落ちる状態で、書いた人には判断材料が無い。
printf '\n記録先: pd/decisions/UXDR-20260101-01-x.md\n' >> "$GLOSS"
expect_plugin "案内する置き場所の取り残し" "{プロダクト}/{年} が無い"
cp "$WORK/glossary.md" "$GLOSS"

printf '\n記録先: pd/reviews/DR-20260101-01-x.md\n' >> "$GLOSS"
expect_plugin "レビュー結果の置き場所の取り残し" "{プロダクト}/{年} が無い"
cp "$WORK/glossary.md" "$GLOSS"

# ディレクトリだけを指す言及（pd/decisions/ 配下、のような文）は通す
printf '\n根拠が崩れた UXDR は `pd/decisions/` にある。\n' >> "$GLOSS"
if PD_PROJECT_DIR="$PLUGIN" python3 "$VALIDATE" 2>&1 | grep -q "{プロダクト}/{年} が無い"; then
    printf '  ✗ %s — ディレクトリへの言及まで弾いた\n' "ディレクトリへの言及は通す"; fail=$((fail + 1))
else
    printf '  ✓ %s\n' "ディレクトリへの言及は通す"; pass=$((pass + 1))
fi
cp "$WORK/glossary.md" "$GLOSS"

# 反例として並べた行まで弾くと、禁止の説明が書けなくなる
printf '\n✗ 店舗スタッフ   固有の語彙を配布物に書かない\n' >> "$GLOSS"
if PD_PROJECT_DIR="$PLUGIN" python3 "$VALIDATE" 2>&1 | grep -q "業種固有の語がある"; then
    printf '  ✗ %s — 反例の行まで弾いた\n' "反例の行は通す"; fail=$((fail + 1))
else
    printf '  ✓ %s\n' "反例の行は通す"; pass=$((pass + 1))
fi
cp "$WORK/glossary.md" "$GLOSS"

# 版を上げたのに履歴を書き忘れた
# （版番号を直書きすると、版を上げるたびにこのテストが壊れて消される）
bump() {   # $1 = 新しい版
python3 - "$PLUGIN" "$1" <<'PY'
import json, pathlib, sys
root, version = pathlib.Path(sys.argv[1]), sys.argv[2]
for name, key in (("plugin.json", None), ("marketplace.json", "plugins")):
    p = root / ".claude-plugin" / name
    d = json.loads(p.read_text(encoding='utf-8'))
    if key is None:
        d["version"] = version
    else:
        for entry in d[key]:
            entry["version"] = version
    p.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding='utf-8')
PY
}
bump 9.9.9
expect_plugin "版を上げて履歴を書き忘れる" "9.9.9 の項目が無い"
expect_plugin "CI に焼き込む ref の古び" "CI に焼き込む ref が古い"
cp "$ROOT/.claude-plugin/marketplace.json" "$PLUGIN/.claude-plugin/marketplace.json"

# plugin.json だけ上げ忘れた（marketplace.json 側だけ上げても更新は届かない）
expect_plugin "版の記載の食い違い" "version が plugin.json と違う"
cp "$ROOT/.claude-plugin/plugin.json" "$PLUGIN/.claude-plugin/plugin.json"

# 履歴だけ先に書いて配り忘れた。見た目は完成しているので気づけない。
# /plugin update しても "already at the latest version" で止まり、誰にも届かない。
printf '\n## [99.0.0] — 2099-01-01\n\n### 追加\n\n- 配り忘れた版\n' >> "$PLUGIN/CHANGELOG.md"
expect_plugin "履歴を書いたのに配っていない" "書いたが配っていない"
cp "$ROOT/CHANGELOG.md" "$PLUGIN/CHANGELOG.md"

# ------------------------------------------------------- hook の挙動（形ではなく動き）

# hooks.json に名前が載っていても、実際に止められなければ意味がない。
hook_case() {   # $1 = ラベル / $2 = event / $3 = 入力JSON / $4 = 期待（空なら無出力）
    out=$(printf '%s' "$3" | CLAUDE_PROJECT_DIR="$PROJ" \
          python3 "$PLUGIN/scripts/hook.py" "$2" 2>/dev/null)
    if [ -z "$4" ]; then
        if [ -z "$out" ]; then
            printf '  ✓ %s\n' "$1"; pass=$((pass + 1))
        else
            printf '  ✗ %s — 何か出力した: %s\n' "$1" "$out"; fail=$((fail + 1))
        fi
    elif printf '%s' "$out" | grep -q "$4"; then
        printf '  ✓ %s\n' "$1"; pass=$((pass + 1))
    else
        printf '  ✗ %s — 期待 %s / 実際 %s\n' "$1" "$4" "$out"; fail=$((fail + 1))
    fi
}

# 促しの宛先。判定を触ったら理由を残させ、配布物を触ったら README を促す。
# **plugin 自身のパスに限る** — 利用プロジェクトにも skills/ はありうるため、
# 部分一致で拾うと無関係な編集のたびに促しが出て、やがて無視される。
hook_case "判定を触ったら理由を促す" post-tool-use \
          "{\"tool_input\":{\"file_path\":\"$PLUGIN/scripts/validate.py\"}}" "DECISIONS.md"
hook_case "配布物を触ったら README を促す" post-tool-use \
          "{\"tool_input\":{\"file_path\":\"$PLUGIN/skills/ux-design-review/SKILL.md\"}}" "README.md"
hook_case "他リポジトリの skills/ では促さない" post-tool-use \
          '{"tool_input":{"file_path":"/tmp/pd-selftest-other/skills/x/SKILL.md"}}' ""

BADFILE="$PD/analyses/testprod/2026/bad-name.md"
printf '中身\n' > "$BADFILE"
hook_case "違反ファイルの編集を止める" post-tool-use \
          "{\"tool_input\":{\"file_path\":\"$BADFILE\"}}" "block"
hook_case "Write の応答（filePath）も読む" post-tool-use \
          "{\"tool_response\":{\"filePath\":\"$BADFILE\"}}" "block"
hook_case "残存違反を通知する" session-start "{}" "systemMessage"
rm -f "$BADFILE"
prune

# hook 自身の失敗で作業を止めない。止めてよいのは規約違反だけ。
if printf 'not json' | CLAUDE_PROJECT_DIR="$PROJ" \
   python3 "$PLUGIN/scripts/hook.py" stop >/dev/null 2>&1; then
    printf '  ✓ 壊れた入力でも異常終了しない\n'; pass=$((pass + 1))
else
    printf '  ✗ 壊れた入力で異常終了した（作業が止まる）\n'; fail=$((fail + 1))
fi

# pd を使わないプロジェクトで動かないこと（全プロジェクトで有効になるため）
OTHER="$WORK/other"
mkdir -p "$OTHER/analyses"
printf 'x\n' > "$OTHER/analyses/a.md"
out=$(printf '{"tool_input":{"file_path":"%s"}}' "$OTHER/analyses/a.md" \
      | CLAUDE_PROJECT_DIR="$OTHER" python3 "$PLUGIN/scripts/hook.py" post-tool-use 2>&1)
if [ -z "$out" ]; then
    printf '  ✓ pd と無関係なプロジェクトでは何もしない\n'; pass=$((pass + 1))
else
    printf '  ✗ pd と無関係なプロジェクトで動いている: %s\n' "$out"; fail=$((fail + 1))
fi

# --------------------------------------------------- Release 本文の組み立て
#
# 更新通知は本文の先頭 8 行しか出さない（update_check.py の NOTES_LINES）。
# 要約が先頭に来ないと、長い箇条書きの途中で切れたものが利用者に届く。
CLBAK="$WORK/CHANGELOG.bak"
cp "$PLUGIN/CHANGELOG.md" "$CLBAK"
cat > "$PLUGIN/CHANGELOG.md" <<'EOF'
# 変更履歴

## [9.9.9] — 2026-01-01

### 追加 — 一行目に出るべき要約

本文の段落。ここは通知に出てはいけない。

- 箇条書き

## [9.9.8] — 2025-12-31

### 変更 — 前の版の見出し
EOF

SECTION=$(python3 "$PLUGIN/scripts/changelog_section.py" 9.9.9)

if [ "$(printf '%s\n' "$SECTION" | head -1)" = "- 追加 — 一行目に出るべき要約" ]; then
    printf '  ✓ Release 本文の先頭に要約が来る\n'; pass=$((pass + 1))
else
    printf '  ✗ Release 本文の先頭が要約でない: %s\n' \
        "$(printf '%s\n' "$SECTION" | head -1)"; fail=$((fail + 1))
fi

# 通知は「---」より前だけを出す（update_check.py と同じ切り方）
if printf '%s\n' "$SECTION" | sed -n '1,/^---$/p' | grep -q "通知に出てはいけない"; then
    printf '  ✗ 通知に本文が混ざる（要約で切れていない）\n'; fail=$((fail + 1))
else
    printf '  ✓ 通知には要約だけが出る\n'; pass=$((pass + 1))
fi

if printf '%s\n' "$SECTION" | grep -q "前の版の見出し"; then
    printf '  ✗ 次の版のセクションまで拾っている\n'; fail=$((fail + 1))
else
    printf '  ✓ 1つの版だけを切り出す\n'; pass=$((pass + 1))
fi

# 中身の無い Release を作らせない
if python3 "$PLUGIN/scripts/changelog_section.py" 0.0.1 >/dev/null 2>&1; then
    printf '  ✗ CHANGELOG に無い版でも成功した\n'; fail=$((fail + 1))
else
    printf '  ✓ CHANGELOG に無い版では失敗する\n'; pass=$((pass + 1))
fi

cp "$CLBAK" "$PLUGIN/CHANGELOG.md"

# ------------------------------------------------------- スキーマの三者一致
#
# 規約を書いた文書と、判定するコードは別々に育つ。片方だけ変えると
# 「文書どおりに書いたのに弾かれる」事故になる（rules/05-operations.md §6）。
# 一致を注意力に委ねず、壊して検出できることを確かめる。

SYNC="$PLUGIN/scripts/schema-sync.py"

if python3 "$SYNC" >/dev/null 2>&1; then
    printf '  ✓ スキーマの三者一致（正常時は通る）\n'; pass=$((pass + 1))
else
    printf '  ✗ 正常なスキーマで食い違いを報告している\n'
    python3 "$SYNC" 2>&1 | sed 's/^/      /'
    fail=$((fail + 1))
fi

# CLI 側だけ enum を増やす（ss-uiux で実際に起きた事故の再現）
cp "$PLUGIN/scripts/voices.mjs" "$WORK/voices.bak"
sed 's/    "user-validation",/    "user-validation",\n    "operator-validation",/' \
    "$WORK/voices.bak" > "$PLUGIN/scripts/voices.mjs"
if python3 "$SYNC" 2>&1 | grep -q "食い違っている"; then
    printf '  ✓ CLI 側だけ enum を足すと検出する\n'; pass=$((pass + 1))
else
    printf '  ✗ enum の食い違いを検出できない（注意書きだけでは守られない）\n'; fail=$((fail + 1))
fi
cp "$WORK/voices.bak" "$PLUGIN/scripts/voices.mjs"

# 文書側だけ enum を減らす
cp "$PLUGIN/skills/analyze/uiux/voice-schema.md" "$WORK/schema.bak"
sed 's| / `question` | |' "$WORK/schema.bak" > "$PLUGIN/skills/analyze/uiux/voice-schema.md"
if python3 "$SYNC" >/dev/null 2>&1; then
    printf '  ✗ 文書側の enum 変更を検出できない\n'; fail=$((fail + 1))
else
    printf '  ✓ 文書側だけ enum を減らすと検出する\n'; pass=$((pass + 1))
fi
cp "$WORK/schema.bak" "$PLUGIN/skills/analyze/uiux/voice-schema.md"

# speaker_role は enum ではなくなったが、形式は3箇所に散る。
# 文書側から形式が消えると「何を書けば通るのか」が現場から分からなくなる。
sed 's|`\^\[a-z\]\[a-z0-9-\]\*\$`|（英小文字）|' \
    "$WORK/schema.bak" > "$PLUGIN/skills/analyze/uiux/voice-schema.md"
if python3 "$SYNC" 2>&1 | grep -q "speaker_role の形式"; then
    printf '  ✓ 文書側から speaker_role の形式が消えると検出する\n'; pass=$((pass + 1))
else
    printf '  ✗ speaker_role の形式の食い違いを検出できない\n'; fail=$((fail + 1))
fi
cp "$WORK/schema.bak" "$PLUGIN/skills/analyze/uiux/voice-schema.md"

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

# ------------------------------------------------------- 旧レイアウト（root 直下）
#
# v0.5.0 で分析データを `pd/` 配下に畳んだ。既に root 直下で運用している
# プロジェクトを壊さないこと。台帳のキーは根からの相対パスなので、
# **移動しても承認なしで通る**ところまで確かめる（ここが壊れると、更新した
# 途端に既存プロジェクトが全ファイル「台帳にあるが存在しない」で落ちる）。

# DATA_DIRS と同じ並び。1つでも pd/ 側に残ると根の判定が旧レイアウトへ切り替わらない
for d in products analyses voices simulations specs decisions validations measurements reviews; do
    [ -d "$PD/$d" ] && mv "$PD/$d" "$PROJ/$d" || true
done

if PD_PROJECT_DIR="$PROJ" python3 "$VALIDATE" >/dev/null 2>&1; then
    printf '  ✓ 旧レイアウト（root 直下）でも通る\n'; pass=$((pass + 1))
else
    printf '  ✗ 旧レイアウトで違反を出している（既存プロジェクトが壊れる）\n'
    PD_PROJECT_DIR="$PROJ" python3 "$VALIDATE" 2>&1 | sed 's/^/      /'
    fail=$((fail + 1))
fi

OLDBAD="$PROJ/analyses/testprod/2026/bad-name.md"
printf '中身\n' > "$OLDBAD"
hook_case "旧レイアウトでも hook が止める" post-tool-use \
          "{\"tool_input\":{\"file_path\":\"$OLDBAD\"}}" "block"
rm -f "$OLDBAD"

for d in products analyses voices simulations; do
    [ -d "$PROJ/$d" ] && mv "$PROJ/$d" "$PD/$d" || true
done
prune

echo ""
if [ "$fail" -gt 0 ]; then
    echo "自己テスト失敗: $fail 件（成功 $pass 件）"
    echo "検証器が期待どおりに機能していません。"
    exit 1
fi
echo "✓ 自己テスト成功: $pass 件すべて検出できました"
