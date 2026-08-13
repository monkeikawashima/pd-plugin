---
name: analyze
description: >
  プロダクトの課題、KPI、利用状況、UX、効果検証を分析し、
  Root Cause、改善Driver、仮説、Experiment、意思決定まで導く
  Product Discovery Skill。
---

# Product Discovery

特定のプロダクト・業界・KPIに依存しない、汎用の Product Discovery Skill。
共通のフレームワークだけを保持し、プロダクト固有の情報は実行時に読み込む。

## この Skill の構造

```
SKILL.md          実行方法・オーケストレーション（このファイル）
    ↓
pd/products/      対象プロダクトの Context
    ↓
framework/        共通の思考方法（必要なものだけ）
    ↓
プロダクト固有の分析
```

### どこに何があるか

この Skill は plugin として配布される。**共通のもの（Skill 本体）と、そのプロジェクト固有のもの（データ）は別の場所にある。**

```
plugin 側（全プロジェクト共通。/plugin update で上書きされる）
  SKILL.md / framework/ / products/_template.md

プロジェクト側（そのプロジェクトのデータ。書き換えるのはこちら）
  pd/products/{product-name}.md   Context（現在値）
  pd/analyses/ pd/voices/ pd/simulations/ pd/.local/
```

以降このファイルで `products/` `analyses/` `voices/` `simulations/` `.local/` と書いたものは、**すべてプロジェクト側の `pd/` 配下**を指す。plugin 配下に分析データを書き込まない（更新時に消える）。

**`pd/` の1段は省略しない。** pd が作るものを1箇所に集めているのは、やめるときに「どれが pd のものか」が分かるようにするため。

**例外**: root 直下に `products/` `analyses/` があるプロジェクトは v0.5.0 より前のレイアウト。**移動せず、そのレイアウトに合わせて書く**（検証器も両方を読む）。

プロジェクト側の置き場所がまだ無い場合は `/pd:init` で作る。

順序が本質。フレームワークは共通、分析は共通ではない。
KPI Tree・User Journey・Driver は、**対象プロダクトの Context から毎回組み立てる**。他プロダクトのものを流用しない。Context が揃う前に組み立てない。

## 使う場面

- KPI が変化した、または目標に届いていない
- 利用率・定着率・継続率が期待より低い
- ユーザーが迷い・エラー・回避行動を起こしている
- 誰かが改善案を出し、その根拠を確かめる必要がある
- 判断が必要（Continue / Improve / Re-test / Scale / Stop、または GO / CONDITIONAL GO / ITERATE / NO GO）

コードを書く、UI 仕様を決める、進捗報告を作る、といった用途には使わない。

## 実行フロー

```
1.  対象プロダクトを理解する
2.  過去の分析・棄却済み仮説・既存の Decision を確認する
3.  Product Context を取得する
4.  Current State を整理する
5.  Problem を定義する
6.  Evidence を整理する
7.  必要な Framework を選ぶ
8.  Driver を分析する
9.  Root Cause 候補を整理する
10. Hypothesis を作る
11. Improvement Lever を特定する
12. Experiment を設計する
13. Decision につなげる
```

すでに十分な情報がある工程は繰り返さない。確立済みのことを再導出しない。

## Step 1 — 対象プロダクトの特定（必須）

分析の前に、必ず対象プロダクトを特定する。

- `/pd:analyze product-a` のようにプロダクト名が指定された場合は `products/product-a.md` を参照する
- 指定が無い場合は、現在の作業対象から判断し、該当する `products/{product-name}.md` があれば参照する
- 該当ファイルが無い場合は、`products/_template.md` の項目を Schema として、実行時に Context を構築する

`products/` の情報だけが情報源とは限らない。会話・README・PRD・仕様書・docs・リポジトリ・Analytics・利用ログ・インタビュー・Support ログなど、利用可能なものを統合する。

情報が競合する場合の信頼順序:

```
1. ユーザーから直接指定された最新情報
2. 最新の Product / PRD / 仕様書
3. 最新の Analytics / Data
4. User Research
5. 実装・コード
6. 古い資料
7. 推測
```

推測を Fact として扱わない。存在しない情報を埋めない。不足は `未確認` / `不明` / `情報不足` として明示する。

**探索そのものを目的にしない。** 問われている内容に対して Context が十分になった時点で分析へ進む。

## Step 2 — 過去の分析の確認

分析を始める前に、同じ対象について何が既に分かっているかを確認する。

1. `analyses/{product-name}/` の既存 Note — 直近のものから、同じ問いが扱われていないか
2. `products/{product-name}.md` の **Past Experiments** — 検証済みの仮説と、**棄却された仮説**
3. 同 **Decisions** — 有効な決定と、見直し条件が未確認のまま残っているもの

規則:

- **棄却された仮説を、新しい発見として再提出しない。** 再提出する場合、前回の棄却根拠が覆った理由を示す
- 既に確立した Fact を再導出しない
- 見直し条件が満たされている決定を見つけた場合、それ自体を今回の論点として扱う
- 過去の Note を書き換えない。認識が変わった場合は新しい Note に、前回との差分として書く

Note が1件も無い場合、この Step は不要。既存 Note を全件読む必要はない。**問いに関係するものだけを読む。**

## Framework の選択

問題の形に応じて、必要なものだけを参照する。全部読み込まない。

| 状況 | 参照先 |
|---|---|
| プロダクトの問題を整理したい | `framework/discovery.md` |
| KPI が改善しない / KPI が動いた / 横ばいで動かない | `framework/kpi.md` |
| 導入・継続を判断したい | `framework/kpi.md`（成果指標に載らない価値）+ `framework/experiment.md` |
| 利用率が低い | `framework/discovery.md` + `framework/kpi.md` |
| UX 課題を特定したい | `framework/discovery.md` |
| 画面（スクショ・録画）を分析に使いたい | `framework/discovery.md`（画面から得られる Evidence） |
| Root Cause を探したい | `framework/discovery.md`（必要に応じて `kpi.md`） |
| 仮説を検証したい | `framework/experiment.md` |
| 改善施策の効果検証をしたい | `framework/kpi.md` + `framework/experiment.md` |
| インタビュー・発話を分析に使いたい | `framework/discovery.md`（Voice） |

各ファイルの担当:

- `framework/discovery.md` — 問題定義、Evidence、Voice、画面から得られる Evidence、定量と定性の突き合わせ、User Behavior、UX、User Journey、Root Cause、Driver、Improvement Lever
- `framework/kpi.md` — KPI Tree、KPI Driver Analysis、Leading / Lagging、Segment 分析、変化が観測されないときの読み方、成果指標に載らない価値
- `framework/experiment.md` — Hypothesis の検証設計、Experiment、Decision、期限のある判断

## UI/UX の作業（v0.6.0 で統合）

**UI・UX の話が出たら、この Skill ではなく専用スキルから始める。**この Skill は推論の流れ
（問題 → 原因 → 仮説 → 検証 → 決定）を担当し、UI/UX スキルは**抽象度の階層**
（戦略 → 要件 → 構造 → 骨格 → 表層）を担当する。**2つは直交する。**

同じ事実を両方に書かない。層ごとの現在値は `pd/specs/`、推論の履歴は `pd/analyses/` に置く。

| # | 場面 | スキル |
|---|---|---|
| 0 | UI/UX の話が出たら**最初に** | `ux-layer-triage`（層の判定） |
| 1 | 利用者の生の声を受け取った | `user-voice-ledger`（**要約せず逐語のまま**） |
| 2 | UI を作る／直す**前** | `user-voice-ledger`（対象画面のボイスを引き当て） |
| 3 | 要望を要件にする | `user-story-writer` |
| 4 | 置き場所・対象物の話 | `object-model-reviewer` |
| 5 | 色・コントラストに触る | `a11y-contrast-guard`（**目分量で置かない**） |
| 6 | 実装後・PR 前 | `ux-design-review` |
| 7 | 決められない論点が残った | `ux-validation-planner` |
| 8 | 数値で示す | `ux-measurement` |
| 9 | 決めた／決められなかった | `ux-decision-record` |
| 10 | 上流の前提が変わった | `ux-update-cascade` |

規律の実体は `skills/analyze/uiux/` にある。

- `uiux/rules/` — 共通言語 / 層の規律 / 決定規則 / 証拠規則 / アクセシビリティ / 運用の劣化と対処
- `uiux/templates/` — 画面仕様 / ユーザーストーリー / UXDR / 検証計画
- `uiux/voice-schema.md` — ボイス台帳のスキーマ（**正本**）
- `uiux/glossary.md` — 用語

### 成果物の置き場所

| 種類 | 置き場所 | 命名 |
|---|---|---|
| 層ごとの現在値 | `pd/specs/` | `{層番号}-{層名}/{artifact}.md`（**上書き**） |
| 決定記録（UXDR） | `pd/decisions/{product}/{年}/` | `UXDR-YYYYMMDD-NN-<slug>.md` |
| 検証計画 | `pd/validations/{product}/{年}/` | `VP-YYYYMMDD-NN-<slug>.md` |
| 計測計画 | `pd/measurements/{product}/{年}/` | `MP-YYYYMMDD-NN-<slug>.md` |
| レビュー結果 | `pd/reviews/{product}/{年}/` | `DR-YYYYMMDD-NN-<slug>.md` |

`specs/` だけが上書き（現在値）。**残り4つは追記のみ。**そのとき何を決めたかを
後から書き換えると、判断の経緯が消えるため。

### 止まってよいのは次の6つだけ

それ以外で止まったら理由を書く。

| 止まる場所 | 理由 |
|---|---|
| spec のステータス昇格・差し戻し | 人間の合意事項 |
| 構造層（オブジェクト）の確定 | 開発チームの同席が必須 |
| 色の最終決定 | デザイナーの領域（下限の存在証明までは出す） |
| 検証の人数・時期・実施者 | 段取りは人間が決める |
| 逐語のない声の severity | 一次情報不足（一段下げて明記する） |
| 一意に決まらない骨格の選択 | 案を等価に置き計測項目を示すまで |

### 守ること

1. 台帳に無い改善案は「**デザイナー起案**」と明記する（「顧客要望」と書かない）
2. `未合意` / `未定義` ステータスの spec を実装の根拠にしない
3. 一次情報に無い記述には `[推測]` を付ける。**数値を創作しない**（未取得なら「未取得」）
4. `request`（相手が出した手段）を `pain`（困っている事実）として扱わない
5. 状態設計に「**空振り**（処理は成功したが有効な結果が無い）」を必ず含める
6. 「無い」と書くときは調査範囲を添える

## Evidence の扱い

すべての記述に、次のいずれかのラベルを与える。混ぜない。

```
Fact / Interpretation / Hypothesis / Unknown
```

定義と使い分けは `framework/discovery.md` に記載する。ここでの規則は次の3点。

1. Interpretation を、後の記述で Fact として引用しない
2. Evidence に無い数値を書かない。無ければ `不明`
3. 相関を因果として断定しない。因果が未検証であることを明示する

## 禁止事項

| 禁止 | 内容 |
|---|---|
| Solution Jumping | 問題を理解する前に改善案を出す |
| Framework Theater | フレームワークを使うこと自体が目的になる |
| Generic Advice | どのプロダクトにも当てはまる一般論で終わる |
| False Causality | 相関を因果として断定する |
| KPI Only | 最終 KPI だけで Product Value を判断する |
| Average Only | 平均値だけで判断し、Segment / Behavior へ分解しない |
| Hallucination | Product Context を推測して Fact 扱いする |
| Product Leakage | プロダクト固有情報を `framework/` に書き込む |
| Solution = Driver | 施策そのものを改善 Driver として扱う |

## 出力

問いの粒度に合わせる。狭い質問に全体レポートを返さない。

本格的な分析では、必要に応じて次の構成を用いる。**見出しには必ず日本語の言い換えを併記する。**

```
現状
問題
Evidence（根拠）
主要 Driver（成果を動かしている要因）
Root Cause（根っこの原因）
Hypothesis（仮説）
Improvement Lever（改善の効きどころ）
Recommended Experiment（検証）
Decision（判断）
反証（この結論を最も強く否定する Evidence）
不足情報
```

**反証は箇条書き2〜3行で足りる。** 長く書かせると必ず形骸化する。書くのは次の2点だけ。

```
何が観測されたら、この結論は誤りだったと言えるか
それを取りに行くコストはどれくらいか
```

毎回すべてを表示する必要はない。ただし表示する見出しには、上記の言い換えを省略せずに付ける。

**Note の中だけで読めるようにする。** 読み手が別の説明ファイルを開かないと用語が分からない状態にしない。専門用語を初出で言い換えるのは、書き手の負担ではなく読み手の前提を揃える作業である。

### 不足情報の書き方

Evidence が足りないとき、「分からない」で終わらせない。各項目について次を示す。

```
何が不足しているか
↓
なぜ必要か
↓
どう取得できるか
↓
取得すると何を判断できるか
```

判断に影響しない不足は、埋めなくてよい。影響の大きい順に並べる。

## 分析結果の保存

本格的な分析を行った場合、結果を Discovery Note として保存する。

```
pd/analyses/{product-name}/{YYYY}/YYYYMMDD-NN-{slug}.md
```

- `{product-name}` は `products/{product-name}.md` と同じ名前
- `{YYYY}` は年フォルダ（`2026` など）。件数が増えたときに年単位で畳めるようにする
- `NN` は同日内の連番（01 から）。同日に複数人が同じ番号を使った場合、後から気づいた側がリネームする
- `{slug}` は主題を**1語**で（`kpi` / `voice` / `adoption` / `churn` / `onboarding` / `experiment` など）。**説明を詰め込まない** — 内容は Note の中に書く。ファイル名は探すためのもの

```
✅ 2026/20260812-01-kpi.md
✅ 2026/20260812-02-voice.md
❌ 2026/20260812-01-kpi-driver-analysis-and-fee-structure.md
```

ファイル名が長いと、引用・共有・一覧のいずれでも読みにくくなる。日付が入っているので、いつの分析かはファイル名だけで分かる。

**同じテーマの続きには、同じ slug を使う。** 新しい主題名を作らない。

```
01-kpi    KPI の分解
02-voice  Voice の設計
03-kpi    KPI の続き（同じ系譜だと分かる）  ← ✅
03-netrate  細かい主題名を新設する          ← ❌ 系譜が見えなくなる
```

ファイル名で系譜が追える（`ls analyses/{product}/2026/ | grep kpi`）。**新しい slug を作るのは、既存のどのテーマにも属さない問いのときだけ。**

**1回の分析を1ファイルに収める。** 種類別（Context 更新 / Experiment / Decision）に分割しない。1回の分析の文脈が分断され、後から読めなくなる。

**索引ファイルを作らない。** 一覧はディレクトリが正で、未決の状態は `products/{product-name}.md` にある。索引を置くと更新漏れで実態と乖離する。

Note の構成:

```
---
product:   {product-name}
date:      YYYY-MM-DD
author:    誰が書いたか
question:  何を問われたか
framework: 参照した framework（discovery / kpi / experiment）
status:    分析中 / 完了 / 検証待ち
---

# {タイトル}

（凡例 — 下記のブロックをそのまま入れる）

（「出力」の構成に沿った本文。見出しに日本語の言い換えを併記する）

## この分析で更新した Context
## 次のアクション
```

### 凡例（すべての Note の冒頭に入れる）

```markdown
> **記述のラベル** — 各記述がどの状態の情報かを示す。
> `Fact` 実際に確認できた ／ `Interpretation` そこから読み取れること
> `Hypothesis` まだ確かめていない考え ／ `Unknown` 分からない
```

省略しない。**Note を単体で開いた人が、他のファイルを参照せずに読める状態を保つ。**

Context に変化があった場合は `products/{product-name}.md` を更新する。
**Note は履歴、Context は現在値。** 役割を混ぜない。Note を書き換えて過去の分析をなかったことにしない。

見直し条件は Note 本文の Decision に書く。**未確認のまま残っている決定の一覧は `products/{product-name}.md` の「保留中の見直し」だけで管理する。** Note は追記のみで状態を持てないため、Note 側に一覧や進捗を置かない。

軽い問い合わせでは保存しない。保存するのは出力構成に沿った本格的な分析のみ。

## Voice の保存

インタビュー・商談・サポート等で得た発話は、分析結果とは別に保存する。

```
pd/voices/{product-name}/{YYYY}/VOICE-NNN-{slug}.md
```

**1ファイル = 1声。**面談1回で3つの論点が出たら3ファイルになる。まとめない。

理由は引き当てのため。UI を直すときに必要なのは「その画面について誰が何と言ったか」であり、
機会単位でまとめると `screen` で引けなくなる。**引けない台帳は無いのと同じ。**
年フォルダは `captured_at`（発言された日）の年。

frontmatter は12個の必須キーを持つ（正本: `skills/analyze/uiux/voice-schema.md`）。

```
---
id: VOICE-001
product: {product-name}
type: pain | request | negative | positive | question
source: interview | in-app-feedback | review | support-ticket | sales-call | meeting | user-validation
speaker_role: end-user    # enum ではない。役割はプロダクトが決める（形式: ^[a-z][a-z0-9-]*$）
speaker_id: U-01          # 匿名化ID。実名・組織名・連絡先を書かない
captured_at: YYYY-MM-DD   # 発言された日（受領日ではない）
captured_by: 記録者
layer: 戦略 | 要件 | 構造 | 骨格 | 表層 | 未判定
severity: high | medium | low
frequency: 1              # 同一趣旨の声は統合してここを増やす
status: 未検証 | 検証済み | 対応中 | 解消 | 却下
---
```

任意キー: `screen`（**引き当てキー**）/ `object` / `phase` / `principles` / `linked_stories` / `linked_uxdr` / `tags` / `context`。
**これ以外のキーは書けない**（検証器が弾く。スキーマを勝手に増やさないため）。

`type` の取り違えを最も強く戒める。

| type | 定義 |
|---|---|
| `pain` | できていない、困っている**事実** |
| `request` | 話者が出した**解決手段の提案** |
| `negative` | 否定的な**評価・感情** |
| `positive` | 効いている点。**消さないために記録する** |
| `question` | 使い方が分からない＝**理解の失敗** |

> ⚠️ **`request` を `pain` として記録しない。**手段を課題として扱うと、その手段以外の解が消える。

発話行の形式（省略しない）:

```
利用者A-1（小規模・導入3ヶ月）: 「前のやり方のほうが早い」
```

- 発話者は **`役割 + 英大文字 + ハイフン + 数字`** の ID（`利用者A-1` / `運用者B-2`）
- **発話を含む行は必ず ID から始める。** 実名が入り込む余地を形式で消す
- 逐語が取れなかった場合は「逐語なし」と書き、`severity` を**一段下げる**
- 各件に文脈とどう聞いたかを添える（書式は `framework/discovery.md` の Voice を参照）
- 分析で Voice を引用する場合、Note 側には引用と ID を書き、逐語の全文は `voices/` に残す

### CLI

```
node "${CLAUDE_PLUGIN_ROOT}/scripts/voices.mjs" new --product <p> --type <t> … --slug <s>
node "${CLAUDE_PLUGIN_ROOT}/scripts/voices.mjs" query --screen <画面名>
node "${CLAUDE_PLUGIN_ROOT}/scripts/voices.mjs" validate
node "${CLAUDE_PLUGIN_ROOT}/scripts/voices.mjs" stats
```

**UI を作る・直す前に必ず `query --screen` を実行する。**0件は「問題が無い」ではなく
「記録されていない」。0件のまま出す改善案には **「デザイナー起案」と明記する**。

索引ファイルは作らない。一覧は `query` / `stats` で取る（索引は更新漏れで実態と乖離する）。

`voices/` は plugin 配下に置かない。Skill が過去の発話を毎回読み込むことになり、更新時に消える。

Context 側（`products/{product-name}.md` の Qualitative）にファイル名を列挙しない。書くのは、取得済みの範囲・得られている論点・**欠けている声**。

## 元データの扱い

分析には、DB の集計結果・Analytics のエクスポート・決済データ・ログなどを使う。**これらをこのリポジトリに置かない。**

| リポジトリに置かない | リポジトリに置く |
|---|---|
| CSV / エクスポートファイル | 集計結果の数値（Note 本文） |
| DB のダンプ | **実行した集計クエリ**（Note 本文） |
| スクリーンショット・画面録画 | 画面から観測した内容の文章化（`framework/discovery.md` の「画面から得られる Evidence」に従う） |
| 個人情報・アカウント名・連絡先 | 役割と ID に匿名化したもの |

### 元データの置き場所

```
1. 原則 — 保存しない
     元データのマスターは DB / 解析ツール / 決済サービス側にある。
     リポジトリに複製を作らず、必要になったらクエリで取り直す。
     クエリを Note に残すのは、この再取得を可能にするため。

2. 一時的に手元へ置く必要がある場合 — pd/.local/{product-name}/
     エクスポートしたファイルを読ませる、加工する、突き合わせる等。
     プロダクト名のフォルダに、日付プレフィックスのファイル名で置く。
     gitignore 済みでコミットされない。
     作業が終わったら中身を削除する。長期保管の場所ではない。

3. チームで共有する必要がある場合 — 社内の権限管理されたストレージ
     リポジトリではなく、アクセス権を管理できる場所に置く。
     Note には**その場所への参照と、取得条件**だけを書く。
```

`.local/` は「消えても困らないもの」を置く場所と考える。ここにしか無いデータを作らない。**マスターは常にリポジトリの外にある。**

`.local/` の中で**年別・用途別のフォルダを作らない。** 分類を整えるほど「保管庫」に見え、削除されなくなる。個人情報が入りうる場所なので、溜めない構造を保つ。分けるのはプロダクト単位までとし、それ以上は日付プレフィックスのファイル名で足りる。

新しいプロダクトの Context を作るとき（Step 1）、`.local/{product-name}/` も作る。置き場所が既にあれば、素人が迷ってリポジトリ内に置く事故が減る。**ただし共有されないため、他のメンバーの環境には現れない**（各自の手元で作られる）。

個人情報を含む一次資料（インタビューの録音・文字起こし・氏名の対応表）も同じ扱い。`voices/` に置くのは匿名化した逐語だけ。

規則:

1. **数値は出典と一緒に書く** — どのテーブル / どの期間 / どの条件で取ったか。再現できない数値は Evidence として弱い
2. **クエリを Note に残す** — 同じ数値を後から再取得できるようにする。生データを置く代わりの手段
3. **取得できなかった場合、その事実を書く** — 「権限で拒否された」「計測が未実装」も `Fact` である。空欄にしない
4. **匿名化してから記録する**（`framework/discovery.md` の Voice を参照）

集計の対象や条件が変わると、同じ指標名でも数値が変わる。指標名だけを書いて出典を省略しない。

## 予測データでの試行

インタビュー前に想定回答を書き出して設計を検証する場合、実データと**別の木**に置く。

```
pd/simulations/{product-name}/{YYYY}/YYYYMMDD-{slug}.md
```

- frontmatter に `synthetic: true`、冒頭に警告ブロックを置く
- **`voices/` に置かない。名前の似たディレクトリも作らない**
- Evidence として引用しない。`Fact` にも `Interpretation` にもしない。Note に持ち込む場合のラベルは `Hypothesis` のみ
- 実データが取れたら参照しない（削除して良い）

使い道は次の2つに限る。

1. **質問設計の検証** — 対立する複数のシナリオを置き、どのシナリオでも仮説の採否が分かれるかを見る。分かれないなら質問が仮説を分離していない
2. インタビュー実施前の練習・想定問答

予測データは、書き手が支持したい方向に「もっともらしく」書ける。**確認バイアスの生成装置として扱い、結果の予測そのものを成果にしない。** 得ていいのは設計の修正点だけ。
