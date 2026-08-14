# Product Discovery Skill 構築指示書

このファイルは、**任意のプロジェクトで Product Discovery Skill（`/pd:analyze`）を再構築するための指示書**です。

## 使い方

構築したいプロジェクトのルートで Claude Code を起動し、このファイルを渡して次のように指示します。

```
このファイルの通りに Product Discovery Skill を構築してください
```

このファイル自体は Skill の一部ではありません。`.claude/skills/analyze/` の**外**に置いてください。Skill ディレクトリ内に置くと supporting file として読み込まれ、Skill の責務が濁ります。

---

## 1. 目的

特定のプロダクト・業界・KPI に依存しない、汎用の Product Discovery Skill を構築する。
共通フレームワークを保持し、プロダクト固有情報だけを差し替えることで、どのプロダクトにも適応できる状態にする。

一貫して実行できるようにする流れ:

```
プロダクト理解 → 現状把握 → 問題定義 → Evidence整理 → KPI / Driver分析
→ Root Cause特定 → 改善レバー特定 → 仮説構築 → Experiment設計 → 意思決定
```

---

## 2. 最重要要件 — 共通とプロダクト固有の分離

次の2つを混在させない。

| 区分 | 内容 | 置き場所 |
|---|---|---|
| **共通** | Product Discovery / KPI分析 / UX分析 / Root Cause Analysis / Driver Analysis / Hypothesis / Experiment / Decision | `framework/` |
| **プロダクト固有** | プロダクト概要 / ユーザー / 利用シーン / Business Goal / User Goal / KPI / 業務フロー / User Journey / 現状 / 課題 / 制約 / 利用可能なデータ / 過去の検証 | `products/` |

**Product Context を追加するだけで、`framework/` を一切変更せずに使えること。** これが構造の合否判定になる。

**この分離は `uiux/` にも同じく効く**（v1.0.0）。用語集・スキーマ・テンプレートに書いてよいのは
**書き方**だけで、利用者の呼称・業務用語・話者の役割といった**中身**は配布物に持たない。
中身の置き場所は利用プロジェクト側（`pd/specs/01-strategy/glossary.md` / `pd/voices/taxonomy.json`）。

> ⚠️ **用語集は特に漏れやすい。** 「唯一の定義」を名乗る文書に固有の語が入ると、
> 他プロダクトで**間違った言葉が唯一の定義として強制される**。
> 実際に v0.7.0 まで、飲食予約サービスの業務定義が配布物に残っていた。

---

## 3. 言語ルール

Markdown の説明本文はすべて日本語で記述する。見出し・本文・ルール・テンプレートの説明・注意事項・出力フォーマットの説明、すべて。

英語のまま残してよいのは以下だけ。

- ファイル名（`SKILL.md`、`discovery.md` など）
- 一般的な専門用語（Product Discovery、KPI、Driver、Evidence、Hypothesis、Experiment、User Journey、Root Cause など）
- 表の項目名、コードブロック内の用語列挙

禁止: 本文が英語のみ、英語だけの説明・ルール・テンプレート・指示。

---

## 4. ディレクトリ構成

**配布物（plugin）と、それを使うプロジェクトは別のリポジトリに置く。** 共通の方法論は全プロジェクトで同じものを使い、分析データはプロジェクトごとに閉じるため。

```
pd-plugin/                          配布物。Public
├── .claude-plugin/
│   ├── plugin.json                 plugin 定義
│   └── marketplace.json            marketplace 定義（install の入口）
├── skills/analyze/                 メインスキル（`/pd:analyze`）。v1.0.0 で `pd/` から改名
│   ├── SKILL.md                    frontmatter の `name:` はディレクトリ名と揃える
│   ├── framework/
│   │   ├── discovery.md
│   │   ├── kpi.md
│   │   └── experiment.md
│   ├── uiux/                       UI/UX の規律（v0.6.0）
│   │   ├── rules/                  共通言語・層の規律・決定規則・証拠規則・a11y・運用
│   │   ├── templates/              画面仕様・ストーリー・UXDR・検証計画・ペルソナ・
│   │   │                           ジャーニー・トークン・探索計画・ナビ（v1.2.0）
│   │   ├── voice-schema.md         ボイス台帳のスキーマ（正本）
│   │   ├── voice-template.md       ボイスの雛形
│   │   └── glossary.md             共通の用語**のみ**。業種の言葉は書かない（v1.0.0）
│   └── products/
│       ├── _template.md
│       └── other-product.md        記述例
├── skills/ux-*/ ほか19種            UI/UX スキル。**5層すべてに担当がある**（v1.2.0）
│                                  戦略 ux-research-planner（探索）/ strategy-insight-writer /
│                                       user-persona-builder
│                                  要件 user-story-writer / ux-journey-mapper
│                                  構造 object-model-reviewer
│                                  骨格 ia-navigation-reviewer / ux-screen-spec-writer（作る前）/
│                                       ux-writing-guard / a11y-interaction-guard /
│                                       ux-design-review（作った後）
│                                  表層 design-token-keeper / a11y-contrast-guard
│                                  横断 ux-layer-triage / user-voice-ledger / ux-decision-record /
│                                       ux-validation-planner（検証）/ ux-measurement /
│                                       ux-update-cascade
├── hooks/hooks.json                PostToolUse / Stop / SessionStart（§19）
├── commands/
│   ├── init.md                     プロジェクト側の置き場所・台帳・CI・規約を作る
│   ├── validate.md                 規約検証の入口
│   ├── uninstall.md                プロジェクト側に作ったものを一覧・削除する
│   └── update.md                   一覧の取り直しと更新をまとめて実行する（§19）
├── scripts/
│   ├── validate.py                 規約の機械検証（唯一の判定者）
│   ├── update_check.py             新しい版が出ていれば起動時に知らせる（§19）
│   ├── selftest.sh                 検証器が違反を検出できるかのテスト
│   ├── schema-sync.py              ボイスのスキーマが3箇所で一致しているか
│   └── voices.mjs                  ボイス台帳 CLI（依存0）
├── .github/workflows/validate.yml  配布物の欠落と自己テスト
├── pd-skill-blueprint.md           この指示書
└── README.md                       人間向けの入口
```

これが初期の最小構成。不要なファイル・ディレクトリを追加しない。

**plugin 配下に分析データを置かない。** `/plugin update` で上書きされる場所であり、利用者が書き換えるものを置くと消える。

`products/` に実プロダクトのファイル（`products/{product-name}.md`）が増えるのは正常な運用（§18）。**初期構築時には作らない** — Context が無い状態で作ると推測で埋まる。既存リポジトリを再構築する場合、実プロダクトのファイルは移行対象であって、雛形として複製する対象ではない。

分析結果は plugin の**外**、利用プロジェクト側に置く。ここは `/pd:init` が作る。

```
{利用プロジェクト}/                 分析データ。通常は Private
├── README.md                      人間向けの入口（何ができるか・使い方・フォルダの意味）
├── CLAUDE.md                      プロジェクト共通ルール（§19）
├── .github/workflows/validate.yml plugin を取得して検証する（§19）
└── pd/                            pd が作るものは全てこの下（§13「置き場所の集約」）
    ├── ledger.json                過去の記録のハッシュ台帳（履歴の代わり）
    │                              このファイルの有無が「pd を使うプロジェクト」の目印
    ├── ledger-log.md              承認の記録（追記のみ）
    ├── products/
    │   └── {product-name}.md      Context（現在値）。上書きで更新する
    ├── .local/
    │   ├── README.md              ここだけ共有する（clone 後もフォルダが存在するように）
    │   └── {product-name}/        元データの一時置き場。中でフォルダを掘らない
    ├── analyses/
    │   └── {product-name}/
    │       └── {YYYY}/
    │           └── YYYYMMDD-NN-{slug}.md  Discovery Note（分析1回 = 1ファイル）
    ├── voices/
    │   ├── taxonomy.json                  固有語彙（speaker_role / object / phase）。v1.0.0
    │   └── {product-name}/
    │       └── {YYYY}/
    │           └── VOICE-NNN-{slug}.md    Voice（逐語。**1ファイル = 1声**。v0.6.0）
    ├── simulations/
    │   └── {product-name}/
    │       └── {YYYY}/
    │           └── YYYYMMDD-{slug}.md     予測データ（設計検証用。Evidence ではない）
    ├── specs/                             層ごとの現在値（上書き。v0.6.0）
    │   ├── 00-status.md                   各 spec のステータス一覧
    │   ├── 01-strategy/glossary.md        **このプロダクトの用語**（呼称・主要タスク時間）。v1.0.0
    │   ├── 01-strategy/ … 05-surface/
    ├── decisions/{product}/{YYYY}/UXDR-YYYYMMDD-NN-{slug}.md   決定記録（追記のみ）
    ├── validations/{product}/{YYYY}/VP-YYYYMMDD-NN-{slug}.md   検証計画（追記のみ）
    ├── measurements/{product}/{YYYY}/MP-YYYYMMDD-NN-{slug}.md  計測計画（追記のみ）
    └── reviews/{product}/{YYYY}/DR-YYYYMMDD-NN-{slug}.md       レビュー結果（追記のみ）
```

**UI/UX 専用のディレクトリ（`uiux/` 等）をプロジェクト側に作らない。** pd と並列に置くと、同じ事実を二箇所に書くことになり必ず片方が古くなる。層ごとの現在値は `pd/specs/`、推論の履歴は `pd/analyses/` と、**置き場所で役割を分ける**。

**pd が作るものは `pd/` から出さない。** 例外は `CLAUDE.md` と `.github/workflows/validate.yml` の2つだけで、これらは置き場所が外部に決められている。**やめるときに「どれが pd のものか」を判別できる状態を保つため**（`/pd:uninstall` の対象一覧が成立する条件でもある）。

**root 直下に置く旧レイアウトも読めるようにする。** v0.5.0 より前は `products/` `analyses/` … が root 直下にあった。検証器は分析データの根（`BASE`）を「`pd/` 配下にデータがあればそこ、無く root 直下にあれば root」と決める。**台帳のキーはこの根からの相対パスにする** — `ROOT` 相対にすると、`pd/` へ移した瞬間に全ファイルが「台帳にあるが存在しない」で落ちる。

**年フォルダで分ける。** 件数が増えたときに年単位で畳めるようにする。ファイル名には年を含んだ日付をそのまま残す（単体で共有されても、いつのものか分かる）。

**`{slug}` は1語。** `kpi` / `voice` / `adoption` / `churn` のように主題だけを置き、説明を詰め込まない（`20260812-01-kpi-driver-analysis-and-fee-structure.md` のような名前にしない）。内容は Note の中に書く。ファイル名は探すためのもの。

**同じテーマの続きには同じ slug を使わせる**（`01-kpi` → `03-kpi`）。問いごとに新しい主題名を作ると、系譜が追えなくなり「テーマごとに1ファイルにすべきでは」という混乱が生まれる。新しい slug は、既存のどのテーマにも属さない問いのときだけ。

`analyses/` `voices/` `simulations/` を `.claude/skills/analyze/` の中に置いてはならない。supporting file として読み込まれ、Skill が過去の分析結果や全発話を毎回抱えることになる。

**`simulations/` を `voices/` の下や、名前の似たディレクトリに置いてはならない。** 予測が一次情報に1件混ざると、以後どれが実データか区別できない。初期構築では作らず、必要になった時点で作る。

---

## 5. 設計思想（3層）

```
SKILL.md    実行方法・オーケストレーション
    ↓
products/   対象プロダクトの Context
    ↓
framework/  共通の思考方法（必要なものだけ）
    ↓
プロダクト固有の分析
```

順序が本質。フレームワークは共通、分析は共通ではない。
KPI Tree・User Journey・Driver は対象プロダクトの Context から毎回組み立てる。他プロダクトのものを流用しない。Context が揃う前に組み立てない。

**この図を SKILL.md の冒頭に必ず入れること。** 3ファイルに分散した記述からは、なぜこの順序なのかが読み取れない。

---

## 6. ファイル責務

| ファイル | 責務 |
|---|---|
| `SKILL.md` | 実行・オーケストレーション。何を、どの順番で使うか |
| `framework/discovery.md` | Discovery・UX・問題・原因分析 |
| `framework/kpi.md` | KPI・Driver・定量分析 |
| `framework/experiment.md` | 仮説検証・Experiment・Decision |
| `products/_template.md` | Product Context の共通 Schema |
| `products/other-product.md` | Product Context の最小記述例 |
| `products/{product-name}.md` | 実プロダクトの Context。初期構築では作らない（§18 で追加） |
| `analyses/{product}/*.md` | Discovery Note（分析の履歴）。Skill の外に置く |
| `voices/{product}/*.md` | Voice（発話の逐語）。Skill の外に置く |
| `CLAUDE.md` / `.claude/settings.json` | 運用ルールと同期 hook（§19） |

`products/{name}.md` と `analyses/{name}/` の違い:

| | 役割 | 更新のされ方 |
|---|---|---|
| `products/{name}.md` | **現在値**。プロダクトの Context | 分析のたびに上書き更新される |
| `analyses/{name}/*.md` | **履歴**。その時点で何を根拠に何を判断したか | 追記のみ。過去の Note を書き換えない |
| `voices/{name}/*.md` | **一次情報**。発話の逐語 | 追記のみ。要約に置き換えない |

役割を混ぜない。Context を履歴代わりにすると、いつ何を根拠に決めたかが失われる。逐語を要約で置き換えると、後から別の読み方を試せなくなる。

---

## 7. `SKILL.md` に書くこと

Frontmatter:

```yaml
---
name: pd
description: >
  プロダクトの課題、KPI、利用状況、UX、効果検証を分析し、
  Root Cause、改善Driver、仮説、Experiment、意思決定まで導く
  Product Discovery Skill。
---
```

`/pd:analyze` で人間が起動でき、Claude 自身も description から利用判断できる状態にする。

本文に含めるもの:

1. **Skill の目的**（数行）
2. **この Skill の構造** — §5 の3層図
3. **使う場面 / 使わない場面**
4. **実行フロー13段**（下記）
5. **Step 1 対象プロダクトの特定** — `/pd:analyze product-a` → `products/product-a.md` を参照。無ければ `_template.md` を Schema として実行時に構築。情報源の統合と信頼順序
6. **Step 2 過去の分析の確認** — 分析前に `analyses/{product}/` の既存 Note、`products/{product}.md` の Past Experiments（**棄却された仮説**）と Decisions（見直し条件が未確認のもの）を確認する。規則: 棄却済み仮説を新しい発見として再提出しない（する場合は棄却根拠が覆った理由を示す）／確立した Fact を再導出しない／見直し条件が満たされている決定はそれ自体を論点にする／過去の Note を書き換えず、差分として新しい Note に書く。Note が無ければ不要。全件読まず、問いに関係するものだけ読む
7. **Framework の選択表** — 状況 → 参照先。各 framework の担当節も列挙する（節を追加したらここも更新）
8. **Evidence の扱い** — 4ラベルを必ず付けるという規則のみ（定義は書かない）
9. **禁止事項9項目**
10. **出力** — 構成と、不足情報の書き方。**見出しには日本語の言い換えを必ず併記させる**（`Evidence（根拠）` / `主要 Driver（成果を動かしている要因）` / `Root Cause（根っこの原因）` / `Hypothesis（仮説）` / `Improvement Lever（改善の効きどころ）` / `Recommended Experiment（検証の設計）` / `Decision（判断）`）。**Note 単体で読めることを要件にする** — 読み手が README や framework を開かないと用語が分からない状態を許さない
11. **分析結果の保存** — 保存先 `analyses/{product-name}/{YYYY}/YYYYMMDD-NN-{slug}.md`、Note の frontmatter（product / date / author / question / framework / status のみ。状態を持つ項目を増やさない）。**索引ファイルを作らせない**（一覧はディレクトリが正、未決は Context が正。索引は乖離する）。同日の連番衝突は後から気づいた側がリネームする。`{slug}` は**1語**（`kpi` / `voice` / `adoption` など。説明を詰め込ませない）。末尾に「この分析で更新した Context」「次のアクション」。**H1 直後に凡例ブロックを必ず入れる**（`Fact` 実際に確認できた ／ `Interpretation` そこから読み取れること ／ `Hypothesis` まだ確かめていない考え ／ `Unknown` 分からない）。省略させない。1回の分析を1ファイルに収め、種類別に分割しない。軽い問い合わせでは保存しない。見直し条件は Note 本文の Decision に書き、**未確認の決定の一覧は `products/{product}.md` の「保留中の見直し」だけで管理する**（Note は追記のみで状態を持てないため、一覧や進捗を Note 側に置かない）
12. **Voice の保存**（「分析結果の保存」とは別の節にする） — 保存先 `voices/{product-name}/{YYYY}/YYYYMMDD-{source}.md`（`{source}` は `interview` / `sales` / `support` / `onboarding` / `observation` など）。**frontmatter 4項目**（product / date / source / context）を必須にする。発話者は **`役割 + 英大文字 + ハイフン + 数字`** の ID（`利用者A-1`）。同一機会の発話を1ファイルにまとめ、**逐語で記録して要約に置き換えない**。Note 側には引用と出典ファイル名だけを書き、全文は `voices/` に残す。`voices/` を Skill 内に置かない。Context 側にファイル名を列挙させない
13. **元データの扱い** — 集計結果の CSV / エクスポート / DB ダンプ / スクリーンショット / 個人情報を**リポジトリに置かせない**。残すのは①集計結果の数値（出典＝テーブル / 期間 / 条件つき）②**実行した集計クエリ**（生データを置く代わりに、再取得できる状態を残す）。取得できなかった事実（権限で拒否・計測が未実装）も `Fact` として書く。指標名だけを書いて出典を省略させない — 集計条件が変われば同じ指標名でも数値が変わる。**置き場所を3段で明示する**（禁止だけを書くと、行き場が無くなって結局コミットされる） — ①原則保存しない（マスターは DB / 解析ツール側。クエリで取り直す）②一時的に必要なら `.local/{product-name}/`（作業後に中身を削除。**ここにしか無いデータを作らない**。**中で年別・用途別のフォルダを掘らせない** — 分類を整えるほど「保管庫」に見えて削除されなくなる。分けるのはプロダクト単位まで、あとは日付プレフィックスのファイル名で足りる。プロダクトの Context を新規作成するとき `.local/{product-name}/` も作る）③共有が必要なら権限管理されたストレージ（Note には参照と取得条件のみ）。個人情報を含む一次資料（録音・文字起こし・氏名の対応表）も同じ扱いで、`voices/` に置くのは匿名化後の逐語だけ
14. **予測データでの試行** — 保存先 `simulations/{product-name}/{YYYY}/YYYYMMDD-{slug}.md`。frontmatter に `synthetic: true`、冒頭に警告ブロック。**`voices/` に置かない**。Evidence として引用させない（`Fact` にも `Interpretation` にもしない。Note へ持ち込むラベルは `Hypothesis` のみ）。使い道は2つに限る — ①**質問設計の検証**（対立する複数シナリオを置き、どのシナリオでも仮説の採否が分かれるかを見る。分かれないなら質問が仮説を分離していない）②実施前の練習。**確認バイアスの生成装置として扱い、結果の予測自体を成果にしない。** 得ていいのは設計の修正点だけ

実行フロー:

```
1.  対象プロダクトを理解する      8.  Driver を分析する
2.  過去の分析を確認する          9.  Root Cause 候補を整理する
3.  Product Context を取得する    10. Hypothesis を作る
4.  Current State を整理する      11. Improvement Lever を特定する
5.  Problem を定義する            12. Experiment を設計する
6.  Evidence を整理する           13. Decision につなげる
7.  必要な Framework を選ぶ
```

すでに十分な情報がある工程は繰り返さない。

情報源の信頼順序（競合時）:

```
1. ユーザーから直接指定された最新情報   5. 実装・コード
2. 最新の Product / PRD / 仕様書        6. 古い資料
3. 最新の Analytics / Data              7. 推測
4. User Research
```

推測を Fact として扱わない。不足は `未確認` / `不明` / `情報不足` と明示する。
探索そのものを目的にしない。問いに対して Context が十分になった時点で分析へ進む。

Framework 選択表:

| 状況 | 参照先 |
|---|---|
| インタビュー・発話を分析に使いたい | `discovery.md`（Voice） |
| 導入・継続を判断したい | `kpi.md`（成果指標に載らない価値）+ `experiment.md` |
| プロダクトの問題を整理したい | `discovery.md` |
| KPI が改善しない / KPI が動いた / 横ばいで動かない | `kpi.md` |
| 利用率が低い | `discovery.md` + `kpi.md` |
| UX 課題を特定したい | `discovery.md` |
| Root Cause を探したい | `discovery.md`（必要に応じて `kpi.md`） |
| 仮説を検証したい | `experiment.md` |
| 改善施策の効果検証をしたい | `kpi.md` + `experiment.md` |

### 外部ソース（URL / MCP 経由）の扱い

MCP 連携がある環境では、Notion / Drive / Slack の URL を渡されたらその場で読んで情報源に加える。**その場限りで消える情報**なので、2箇所に規定を置く。

**取得時（Step 1 側）**

- 出典を控える — 題名・URL・種別と、**資料に書かれている更新日**。読み取った日を更新日にしない
- 更新日が確認できない外部ページは信頼順序の「6. 古い資料」。ユーザーが「これが最新」と言った場合のみ「1」へ上げる
- 外部ページの数字は「その資料にそう書いてある」ことが Fact であり、現在値の根拠ではない。実測と食い違えば実測を採る

**反映時（Note 保存側）**

会話・実測・リポジトリ由来の変化はそのまま Context に反映してよい。**外部ソース由来の値で `products/{product-name}.md` を書き換える場合だけ、差分を提示して選ばせる**（ユーザーの申し出を待たない）。選択肢は「すべて反映 / 選んで反映 / 反映しない」の3つ。

- 上書きと追記を分けて示し、上書きには変更前の値を併記する
- 反映した値には出典（資料名・時点）を残す。書けないなら反映しない
- 既存の実測値を、更新日が不明な外部ページの値で上書きしない（提示はするが既定で選択済みにしない）
- `Past Experiments` / `Decisions` は追記のみ。外部ソースを根拠に過去の決定・棄却結果を書き換えない
- 反映しなかった項目もその回の Note には残る（Context に載らないだけ）

---

## 8. `framework/discovery.md` に書くこと

基本モデル `Context → Problem → Evidence → Driver → Hypothesis → Experiment → Decision`（内部手順。毎回表示しない）

- **Problem Definition** — 現象 / 問題 / 原因候補の分離。確認事項（現象を原因扱いしていないか、どのセグメント・工程か、何との比較か、計測自体が変わっていないか）
- **Evidence** — 4状態（`Fact` / `Interpretation` / `Hypothesis` / `Unknown`）の**定義**。3種類（Quantitative / Qualitative / Behavioral）＋**画面**（3種のどれとも違うので別立てにする）。品質確認（平均は分布を隠す、少数サンプルは方向性まで、自己申告は行動ではない、データが無いことは事象が無いことの証明ではない、計測実装の変更確認）
- **Voice** — インタビュー・商談・サポート等の発話の扱い。①記録: 逐語で残し要約しない、1件 = 1発話者の1トピック、発話者 / 日付 / 文脈 / どう聞いたかを添える、問いの立て方が答えを作る（誘導への同意は弱い Evidence）。**匿名化**: 発話者は役割・立場と ID で書き（形は `役割 + 英大文字 + ハイフン + 数字`。例 `店舗A-1`）、実名・店名・連絡先・アカウント名を書かない。**敬称の有無は関係なく、姓だけでも書かない**（発話内の言及も置き換える）。ID と実名の対応表はリポジトリ外。必要なのは「誰が」ではなく「どの立場の人が」言ったか。**この規約は検証器が機械的に判定する**（敬称・メール・電話・@・頻出姓・ID 形式の有無）②ラベル付け: `Fact` = そう述べたこと / `Interpretation` = 問題の所在 / `Hypothesis` = 成果への影響。要望をそのまま Solution にしない ③件数と偏り: 固定の目標件数ではなく**飽和**で判断、少数は論点の発見には十分だが頻度・効果量には使えない、最も欠けやすいのは非利用者・離脱者・解約者・沈黙している多数 ④使いどころの対比表（使える: Hypothesis 生成 / Root Cause 候補 / 機構の説明 / UX 観点の特定。使えない: 効果量 / 頻度 / Driver の優先順位確定 / 効果の証明）⑤Voice が0件なら Qualitative を「あり」としない
- **画面から得られる Evidence** — スクリーンショット / 画面録画 / 実機の操作観察。原則: **画面は「何ができる状態か」を示すが「実際にどうされたか」は示さない**。①型の表（それぞれ取れるもの・取れないもの。いずれも1件の観測で母集団の性質ではない）②ラベルの切り分け（`Fact` = 画面上に観測できるもの＝**数えられる形**で書く「入力項目9件・うち必須6件」／`Interpretation` = それをどう読むか／`Hypothesis` = 成果への影響）。**「分かりにくい」は Fact にならない**。数えられない記述は Interpretation ③判定できる UX 観点（Learning / Usability / Accuracy / Workflow の一部）と**できない観点**（Awareness / Trigger / Adoption / Value — 画面を見て埋めない）④記録の仕方（画像を Note に貼らず文章化。出典に**どの画面 / いつ / どの版 / どの条件**。個人情報は転記時に落とす。1画面で Journey を語らない）⑤限界（頻度も影響量も画面には無い。構造の問題を見つけたことは、それが成果を動かしている証明ではない）。画面 → そのまま改善案は `Solution Jumping`
- **定量と定性の突き合わせ** — 定量は「どこで」、定性は「なぜ」。**画面から始める場合**も含める（観測できる Fact を数えて書く → 真ならどの指標がどう出るはずかを書く → 指標を確認 → 当事者の Voice で機構を確かめる。画面 → 改善案の直行を禁じる）。往復の図（定量で局在 → その Segment の当事者の Voice → 機構の仮説 → その機構が真なら出るはずの指標で確認）。Voice から始める場合は**先に「どの指標がどう出るはずか」を書く**（「言われたので対応する」は頻度も影響も不明なまま優先順位を決めている）。定量から始める場合は**分解結果が指している当事者**の Voice を読む（全体の Voice ではない）。説明が見つからないなら機構を創作せず `Unknown`。食い違いの読み方の表（母集団の違い / 指標が捉えていない / 認識されていない / 聞き方が届いていない / 期間・範囲のずれ）。どちらかを誤りと決めず、食い違い自体を Evidence として扱う
- **User Behavior 分析** — Funnel / 順序 / 頻度 / 回避行動 / 比較。「使われていない機能」と「使われて失敗している機能」は成果指標上は同じに見える
- **UX 分析** — Awareness / Trigger / Adoption / Learning / Usability / Accuracy / Trust / Value / Workflow の9観点。全項目を毎回埋めない。前段が失敗していると後段は測定できない
- **User Journey / Task Flow**
- **Root Cause Analysis** — 手法選択表（5 Whys / Funnel / Journey / Task / Segmentation / Cohort / Before-After / User-Non-user / Heavy-Light）。各候補に**棄却条件**を書かせる。何によっても棄却されない候補は Root Cause ではない
- **Driver** — 定義と4評価軸（Impact / Evidence / Confidence / Controllability）。Impact は高いが誰も動かせない Driver は制約として扱う
- **Hypothesis** — 原因仮説の因果構造の書式のみ
- **Improvement Lever** — `Driver → Improvement Lever → Intervention` の3段。施策を Driver として扱わない

---

## 9. `framework/kpi.md` に書くこと

**特定プロダクトの KPI を固定しない。** AHT / ACW / 予約数 / GMV / CVR / 特定商品の売上 などは Product Context 側で扱う。ここに書くのは「これらを書かない」という禁止の明示だけ。

- **KPI Driver Analysis** — 5階層分解（Business Outcome → Product Outcome → User Behavior → UX / Workflow → Product Capability）と手順（構成式で表す → 動いた項を特定 → 局在するまで分割 → 一段降りて繰り返す）。変えられるものに到達したら止める
- **KPI Tree** — 動的構築。固定テンプレートに当てはめない
- **Leading / Lagging** — `Input → Behavior → Leading Indicator → Product Outcome → Business KPI`。どの接続が観測でどれが仮定かを明示
- **定量指標の型** — Funnel / Conversion / Adoption / Frequency / Retention / Task Success。指標名ではなく型
- **成果指標に載らない価値** — Primary KPI が動かないことは価値が無いことと同じではない。型の表（Quality / Variance / Ramp-up / Operational Cost / Experience / Risk）と、それぞれの観測の例。原則3点: ①Primary KPI と同じ厳しさで扱い、観測方法が無いものは `Unknown` として価値の主張に使わない ②Before / After の比較対象を先に決める（事後に有利な指標を探さない）③コストと対で示す（導入判断は比較であって列挙ではない）。**「KPI が動かなかった」の言い換えとして使わない**。逆に、これらを確認せず `NO GO` を出す判断は根拠不足
- **Segment 分析** — 利用者/非利用者、Heavy/Light、Before/After、新規/継続、習熟度、Cohort ほか。打ち消し合い・母集団構成変化・Before/After の交絡に注意
- **変化が観測されないときの読み方** — 「横ばい」を `(a) 差が無い` と `(b) 差が見えていない` に切り分ける。(b) の要因表（検出力不足 / 分散 / 希釈 / 打ち消し合い / 構成変化 / 計測の変更）と確認方法。(b) を潰す前の「効果なし」は `Fact` ではなく `Unknown`。必要な対象数を概算できないなら「この規模では検出できない」と書く。あわせて**介入の到達で層別する**（全体 / 到達層 / 非到達層 / 到達の分布）。到達層の差をそのまま介入の効果として報告しない（無作為割付ではない。効果の上限を示す弱い Evidence として扱い、`experiment.md` の「検証できない場合」を参照）
- **KPI と UX の接続** — KPI 分解を UX 観点まで降ろす経路

---

## 10. `framework/experiment.md` に書くこと

- **Hypothesis Priority** — Impact / Confidence / Evidence / Testability / Effort。High / Medium / Low で可。数値を創作しない
- **Experiment Schema** — Hypothesis / Intervention / Target / Leading Indicator / Outcome KPI / Success Criteria / Required Evidence / Duration / Sample / Decision Rule
- **事前に決めること** — Success Criteria と Decision Rule は結果を見る前に決める。結果を見てから成功の定義を決めるのは Experiment ではない
- **検証できない場合** — 理由を明示し、代わりに得られる弱い Evidence を示す
- **Experiment Result** — 観測（Fact）/ 読み取れること（Interpretation）/ 説明できていないこと（Unknown）。棄却された仮説は記録する。想定外の結果に事後説明を作らない
- **Decision** — `Continue / Improve / Re-test / Scale / Stop`、導入判断なら `GO / CONDITIONAL GO / ITERATE / NO GO`。各 Decision に根拠 Evidence とその状態、確からしさ、見直す条件を添える。見直し条件には**誰が・いつ確認するか**まで書く（確認者と時期が無い条件は実行されない）。導入・継続の判断では成果指標に載らない価値（`kpi.md`）とコストを対で示し、比較した結論を書く。Decision は `analyses/` の Note に記録し、有効な決定と見直し条件は `products/{product}.md` の Decisions へ反映する
- **期限のある判断** — 期限が決まっている場合、`Re-test` / `ITERATE` は先送りとして機能しない。手順（変えられないことを先に確定 → 残り期間で取得できる Evidence を判断を分岐させる力の順に並べる → 取得しても判断が変わらないものは取りに行かない → 取得できないものは Unknown として固定）。判断は「判断 / 根拠（何を Fact とし何を Unknown に置いたか）/ 判断が変わる条件」の3点に分けて書く。`CONDITIONAL GO` は条件を**期間・閾値・観測手段**に落とす（3点が揃わない条件は実質 `GO`）。観測が介入の効果ではなく前段の状態（到達 / 習熟 / 運用の定着）を測っていた場合は、期間の結果を効果の検証結果として読まず、前段の不成立自体を Evidence として次期へ渡す。ただしこれを毎回の逃げ道にしない — 前段が成立しない理由が介入の設計側にあるなら、それは効果の検証結果である

---

## 11. `products/_template.md` の構成

見出し構造は次の通り。各見出しの下に「何を書くか」を1行の日本語で示す。

```
基本情報          プロダクト名 / プロダクト概要 / プロダクトの目的
ユーザー          Primary User / Secondary User / 利用シーン / Jobs / Use Cases
Goal              Business Goal / User Goal
KPI               Primary KPI / Secondary KPI / Leading Indicator
User Journey      主要なユーザーフロー
Workflow          現在の業務フロー
Current State     現在の状況 / Expected State / Gap
Known Issues      確認されている問題
Constraints       Business / Operation / Technical / Organization
Available Evidence Quantitative / Qualitative / Behavioral
Past Experiments  実施済みの検証 / 結果
Decisions         決定事項 / 保留中の見直し
Unknowns          現時点で不足している情報
```

`Past Experiments` と `Decisions` は、Step 2（過去の分析の確認）の参照先になる。次を書かせる。

- **Past Experiments** — 出典として `analyses/{product}/` の Note 名。棄却された仮説には、**何によって棄却されたか**を併記
- **Decisions / 決定事項** — 決定 / 決定日 / 根拠（Note 名と Evidence の状態）/ 見直し条件 / 確認者・時期
- **Decisions / 保留中の見直し** — 見直し条件が未確認のまま残っている決定。確認されたら決定事項側を更新して外す。確認者と時期が無い項目は実行されないものとして扱う

補足として入れておくと効く注記:

- Business Goal と User Goal の衝突は、それ自体が分析上の発見
- KPI には「現在計測されているか」も書く。未計測なら「未取得」
- Known Issues は Evidence があるものだけ。無いものは Unknowns へ
- Available Evidence は「取得できるはず」ではなく「実際に到達できる」もの
- Qualitative に **Voice のファイル名を列挙させない**（`voices/{product-name}/` が正。列挙は追加のたびに乖離する）。代わりに Voice 全体から見えている状態を書かせる — ①取得済みの範囲（どの立場・どの経路が、いつまで）②得られている論点（飽和しているか）③**欠けている声**（非利用者 / 離脱者 / 解約者 / 沈黙している多数）。Voice が0件なら `情報不足` と書き「あり」としない
- 空欄で残さず `未確認` / `不明` / `情報不足` と明示する

---

## 12. `products/other-product.md`

`_template.md` の使い方が分かる**最小のサンプル**。実在しない詳細なプロダクトを作り込まない。

冒頭に必ず記載:

```
※これは記述例です。実際の分析では対象プロダクトの情報へ置き換えてください。
```

意図的に大半の項目を「未取得」「不明」「情報不足」にしておく。Context が埋まらないこと自体が発見である、という扱い方を例で示せる。

---

## 13. 実装時に判断が必要な論点と、その決定

**このセクションが再現時に最も迷う箇所です。** 元の指示ではどちらのファイルに置くか一意に決まらず、放置すると重複します。

| 論点 | 決定 | 理由 |
|---|---|---|
| Hypothesis を discovery / experiment のどちらに書くか | **両方だが分割**。discovery = 原因仮説の因果構造の書式。experiment = 優先順位付けと検証設計への変換。相互参照する | 元の指示では両ファイルの担当項目に Hypothesis が含まれ、そのまま書くと全面重複する |
| Driver を discovery / kpi のどちらに書くか | **discovery に定義と4評価軸**。kpi は「KPI から Driver を分解する手順」のみで、評価軸は discovery を参照 | 両方に評価表を置くと重複する |
| 禁止事項9項目の置き場所 | **SKILL.md に一本化** | 常時適用のガードレール。`framework/` は必要な節しか読まれないため、そこに置くと適用漏れが起きる |
| Evidence の4状態の定義 | **discovery.md のみ**。SKILL.md には「必ずラベルを付ける」規則だけ | 定義の重複を避ける |
| 不足情報（Missing Evidence）の書式 | **SKILL.md の出力ルール** | 出力の話であってフレームワークの話ではない |
| Product Context の取得方法 | **SKILL.md の Step 1**。Schema は `products/_template.md` | 取得方法を独立ファイルにすると、プロダクト追加のたびに参照先が増える |
| Decision の一覧 | **experiment.md のみ**。SKILL.md には使う場面の列挙のみ | 同上 |
| Context（`products/{name}.md`）を plugin / プロジェクトのどちらに置くか | **プロジェクト側**。plugin には `_template.md` と記述例だけ | plugin 配下は `/plugin update` で上書きされる。利用者が書き換えるものを置くと、更新のたびに Context が消える |
| 検証器が「hook が外されていないか」を何で見るか | **plugin 側の `hooks/hooks.json`**。プロジェクトの `.claude/settings.json` は必須にしない | plugin 経由では hook が settings.json に現れない。必須のままにすると全プロジェクトで誤検知になる。**判定を1つ緩めている**（プロジェクト単位で hook を消されても検出できない）が、hook の供給元が plugin に一本化されたため、消す操作は plugin 側の改変になり別の判定で捕まる |
| plugin の hook を無関係なプロジェクトで動かさない方法 | **目印ファイル（`pd/ledger.json`）が無ければ即 `exit 0`** | plugin を有効にすると全プロジェクトで hook が走る。目印が無いと、pd と無関係なリポジトリで毎ターン違反通知が出る。台帳を目印に兼ねると、増やすファイルが1つも増えない |
| plugin を Public にするか | **Public**。分析データは含めない | 利用プロジェクトの CI が plugin を checkout する。Private だとトークンの配布・更新が全利用者に必要になる。方法論のみで固有情報を含まないことは、`framework/` への固有名混入を検証器が禁じているため構造的に保証されている |
| CI の実行時刻 | **`TZ: Asia/Tokyo` を必須**（検証器が確認する） | 台帳の「書いた当日の修正は通す」判定は実行マシンのローカル時刻。runner の既定 UTC のままだと、JST 早朝に書いた記録が「前日」と見なされ、手元で通る修正が CI でだけ落ちる |
| 分析結果をファイル化するか | **する**。`analyses/{product}/{YYYY}/YYYYMMDD-NN-{slug}.md` に Discovery Note として保存 | 元の指示書には出力の永続化が無く、分析がチャットに出て消える。積み上げも前回との比較もできない |
| Note の粒度 | **分析1回 = 1ファイル**。Context更新 / Experiment / Decision に分割しない | 分割すると運用が重く、1回の分析の文脈が分断される |
| Note と Context の関係 | Note は履歴（追記のみ）、Context は現在値（上書き） | 混ぜると、いつ何を根拠に決めたかが失われる |
| 新しい規約を既存の記録にも適用するか | **しない。** 検証器に適用開始日（`RULES_FROM`）を持ち、それ以降の Note にだけ適用する | 追記のみの記録に後付けの規約を適用すると、①既存が永久に落ちる ②通すために過去を書き換える、のどちらかになる。どちらも「履歴を守る」という前提を壊す |
| 検証器の誤検知が出たときの扱い | **即座に検証器を直す。** 規約側を緩めない | 実際に2件出た（表のヘッダ行を棄却条件の欠落と誤認／`反証（…Evidence）` を Evidence 節と誤認）。誤検知を放置すると検証器が無効化される。**節名の判定は `startswith` を使い、`in` で部分一致させない** |
| 新しい判定を violation にするか warning にするか | **データが無い状態で埋められない項目は warning。** 必須 Segment / 出典 / 分量は warning、反証 / 予測値 / 閾値は violation | 埋められないものを必須にすると「埋めるための埋め」が生まれ、`Framework Theater` になる。精度は上がらず下がる |
| 画面（スクショ・録画）の扱いをどこに書くか | **discovery.md に独立した節**。Evidence の3種類の中に混ぜず、別立てにする。`SKILL.md` は保存の扱い（画像を残さず文章化）だけ | Quantitative でも Qualitative でも Behavioral でもない。「何ができる状態か」しか示さないという限界が固有で、3種のどれかに入れると限界が消える。ルール化しないと、読む人ごとに Fact の範囲が変わる |
| 検証器に入れる判定と、文書だけに書く判定の線引き | **形式・存在・パターンは検証器に入れる。内容の真偽は入れない**。検証器に入れた項目は、必ず規約文書側にも明記する | 検証されない規約は守られない。逆に、文書に無い判定を検証器だけが持つと「なぜ落ちたか分からない」状態になる（新たな揺れ） |
| 用語の説明を Note に持たせるか README に置くか | **両方。Note に凡例と見出しの言い換えを必ず入れる**。README の用語表は補助 | Note は単体で共有・引用される（PR・Slack・資料）。README を開かないと読めない Note は、時間が経つほど読まれなくなる |
| 過去の Note の書き換え禁止の例外 | **表記の統一のみ**（見出しへの言い換え追記・凡例挿入・frontmatter の項目追加）。判断・数値・ラベル・結論には触れない | 用語規約を後から変えたとき、過去の Note が読めないまま残る。読めるようにする作業と、過去をなかったことにする作業は別物 |
| 対象リポジトリに既存の成果物置き場がある場合 | **それには乗せず `analyses/` に集約**（今回の判断） | 置き場所と命名がプロダクトごとに変わると、横断して振り返れなくなる |
| 「横ばい」の読み方を kpi / experiment のどちらに書くか | **kpi.md**。指標の観測の話であって検証設計の話ではない。experiment 側からは「検証できない場合」で受ける | 両方に置くと、検出力・希釈の話が Experiment Schema と混ざる |
| 期限制約下の判断を experiment / SKILL のどちらに書くか | **experiment.md の Decision 直後**。SKILL.md には追記しない | Decision の変種であり、常時適用のガードレールではない |
| Voice の扱いをどこに書くか | **discovery.md に扱い方（記録・ラベル・偏り・使いどころ）**、**SKILL.md に保存先の規約のみ**。`_template.md` の Qualitative から `voices/` を参照 | 扱い方はフレームワーク、保存先は出力ルール。既存の Evidence 節（3種類・品質確認）と重複させず、Voice 固有の論点だけを足す |
| 成果指標に載らない価値を kpi / discovery のどちらに書くか | **kpi.md**（「定量指標の型」の直後）。experiment.md の Decision から参照する | 指標の型の話。discovery の UX 観点（Value）は原因分析の観点であって、判断に使う価値の型ではない |
| 定量と定性の突き合わせをどこに書くか | **discovery.md**（Voice と User Behavior 分析の間）。kpi.md には置かない | Evidence の統合の話であり、KPI 分解の手順ではない。Voice 節の直後に置くことで往復が読み取れる |
| 見直し条件の追跡先 | **`products/{product}.md` の Decisions / 保留中の見直しだけ**。Note には本文の Decision として書き、frontmatter に `review:` のような項目を作らない | Note は追記のみで状態を持てない。frontmatter に置くと決定時点で凍結された値が「現在の未確認一覧」として誤読される。索引として grep できても得られるのは「条件が設定された Note の一覧」で、欲しい「今どれが未確認か」は取れない |
| 過去分析の確認をフローのどこに置くか | **Step 2（対象プロダクト特定の直後、Context 取得の前）**。実行フローは13段になる | Context を取得してから過去を見ると、既に棄却された仮説を再導出する時間が発生する |
| Voice の置き場所 | **`voices/{product-name}/{YYYY}/YYYYMMDD-{source}.md`**。`products/` の中にも `analyses/` の中にも入れない | Context（現在値）でも分析履歴でもなく、独立した一次情報。Skill 内に置くと毎回読み込まれる |
| 予測データ（想定インタビュー等）をどこに置くか | **`simulations/{product}/` という独立した木**。`voices/` の下・`voices_draft/` のような名前・Note 内への直書きはいずれも禁止 | 一次情報に予測が1件混ざると、以後どれが実データか区別できない。名前が似ているだけでも将来コピーされる。用途も違う（Evidence ではなく設計の検証） |
| 分析の粒度（問いごと / テーマごと） | **問いごとに1ファイル。ただし slug はテーマ名を再利用する** | テーマごとに1ファイルで上書きすると履歴が消える（版管理を使わない構成では復元不能）。一方で問いごとに新しい主題名を作ると系譜が見えない。slug の再利用で両方を満たす。最新の理解は Context（`products/`）が持つ |
| 分析を種類別に分割するか / 索引を置くか | **どちらもしない**。1回の分析 = 1ファイル、一覧はディレクトリ、未決は Context | 分割は1回の分析の文脈を分断する。索引は更新漏れで乖離する（Voice のファイル名列挙と同じ失敗） |
| ファイルを年で分けるか / slug をどこまで詳しくするか | **年フォルダで分け、slug は1語**。日付はファイル名にも残す | 年で畳めないと数年で一覧が破綻する。slug に説明を入れると引用・共有時に読みにくく、しかも内容が変わっても名前は直せない（過去の Note はリネームしない）。ファイル名は探すためのもので、説明は中身の役割 |
| プロジェクト側の置き場所を root 直下に散らすか集約するか | **`pd/` 1つに集約**（v0.5.0）。例外は `CLAUDE.md` と `.github/workflows/validate.yml` の2つだけ | `products/` `analyses/` は汎用的な名前で、root 直下にあると pd のものか判別できない。**やめるときに何を消せばいいか分からない**状態は、導入の心理的コストを上げる。集約すると `/pd:uninstall` の対象一覧も自明になる |
| 旧レイアウト（root 直下）を切るか読み続けるか | **読み続ける。** 検証器が根（`BASE`）を自動判定し、移行は任意 | 更新は利用者の操作なしに届きうる（auto-update）。移行を強制すると、更新した瞬間に既存プロジェクトの CI が落ちる。移行の判断は利用者に残す |
| 台帳のキーを何からの相対パスにするか | **分析データの根（`BASE`）から。** `ROOT` 相対にしない | `ROOT` 相対だと `pd/` へ移した瞬間に全ファイルが「台帳にあるが存在しない」になり、移行のたびに一括承認が必要になる。一括承認は「過去の記録の書き換え検出」そのものを formality にする |
| アンインストール時のデータ削除を既定にするか | **しない。** 引数なしは一覧表示のみ、`--keep-data` / `--purge` を明示的に選ばせる | 追記のみで積み上げた記録は復元できない。また `CLAUDE.md` / `.gitignore` / CI は pd より前から存在しうるため、ファイルごと消すと pd と無関係な内容が失われる（消すのは pd が足した行・節だけ） |
| Context 側に Voice の一覧を持たせるか | **持たせない**。ディレクトリが正。Context には「取得済みの範囲 / 得られている論点 / 欠けている声」を書く | ファイル名の列挙は追加のたびに乖離し、しかも `ls` で得られる情報。Context として価値があるのは何が分かっていて誰の声が無いか。Note（履歴）から個別ファイルを出典として引くのは可 — 凍結された記録なので乖離しない |
| UI/UX の規律を pd に統合するか、別の道具として並べるか | **統合する**（v0.6.0）。プロジェクト側に `uiux/` 等を並置しない | 並置すると同じ事実（KPI のベースライン、判断、顧客の声）を二箇所に書くことになり、必ず片方が古くなる。実際に併用したプロジェクトで、KPI の状態と決定記録が両方に重複した。統合しても衝突しないのは、pd が**推論の流れ**、UI/UX が**抽象度の階層**という直交する軸だから — 置き場所を `analyses/`（履歴）と `specs/`（現在値）で分ければ役割が重ならない |
| Voice を機会単位でまとめるか、声単位に割るか | **1ファイル = 1声**（v0.6.0 の破壊的変更）。frontmatter に `screen` / `type` / `severity` / `status` を持たせる | 機会単位でまとめると「その画面について誰が何と言ったか」で引けない。UI を直す前に引き当てられない台帳は、無いのと同じ。一方で pd 側の PII 検査と発話行の形式強制（`ID: 「逐語」`）は残す — 匿名化を人の注意力ではなく形式で担保するため。**両者の強い部分だけを採る** |
| 索引ファイル（`index.md`）を生成するか | **しない**（`voices.mjs index` を廃止）。一覧は `query` / `stats` で取る | 生成物であっても再実行を忘れれば乖離する。既存の「索引を作らない」規約と衝突し、検証器が自分の生成物を弾く状態になっていた |
| plugin 名とコマンド名のどちらを直すか | **コマンド名だけ**（v1.0.0）。`pd` はそのまま、`/pd:pd` → `/pd:analyze` / `/pd:init` / `/pd:validate` / `/pd:uninstall` | plugin 名を変えると**別 plugin 扱いになり、既存利用者に `/plugin update` で更新が届かない**（手動で入れ直しが要る）。名前空間が読みやすくなる利益より、更新経路を切らないことが重い。書き換え量はどちらも同程度（`/pd:` 66箇所 対 `skills/pd/` 74箇所）なので、**高いのは編集ではなく利用者の入れ直しのほう**。marketplace での見つけやすさが問題になったときに、改めて plugin 名だけ変えれば1回で済む |
| コマンド名から接頭辞を外すと、名前空間の付け忘れ判定が誤検知しないか | **する。だから判定を作り直す。** 直前が語・`/`・`:` のときは対象外にし、接頭辞つきの旧名も残骸として拾う | 素の名前が `init` / `validate` という普通の英単語になり、`scripts/validate.py` や `pd/validations/` への言及だけで毎回赤くなる。**誤検知する判定は無視されるようになる**（`rules/05-operations.md` §5「検証が常に赤い」）ので、名前を短くするなら判定側の作り替えが対になる |
| 話者の役割（`speaker_role`）を enum で固定するか | **しない**（v1.0.0 の破壊的変更）。**形式だけ**を縛り（`^[a-z][a-z0-9-]*$`）、値は `pd/voices/taxonomy.json` で各プロジェクトが宣言する。宣言されていれば検証器がその中に縛る | 役割の呼び名は業種で変わる（利用者/現場/管理者、患者/医師、受講者/講師…）。plugin 側で固定すると**特定業種の語彙を全利用者に強制する**。一方で完全な自由記述にすると `Staff` / `店舗スタッフ` / `store staff` が同居し `query` で引けなくなる — 台帳は引けなければ無いのと同じ。**値の自由と表記の一貫性は両立できる**。既に `object` / `phase` が同じ仕組みを持っており、新しい概念を増やさない |
| 業務用語（利用者の呼称・主要タスク時間）を plugin / プロジェクトのどちらに置くか | **プロジェクト側**（`pd/specs/01-strategy/glossary.md`。`/pd:init` が雛形を作る）。plugin の `uiux/glossary.md` には**書き方だけ**を残す | v0.7.0 まで、飲食予約サービスの業務定義（ゲスト/店舗スタッフ、予約完了時間、予約対応時間）が配布物に入っていた。用語集は「唯一の定義」であるがゆえに、固有の語が入ると他プロダクトで**間違った言葉が唯一の定義として強制される**。方法（系統ごとに定義する / 必ず要素に分解する）は共通、中身は固有 |
| 置き場所を変えたとき、文書側の追随をどう担保するか | **検証器が見る**（`check_documented_paths`）。文書が案内する記録のパスに `{プロダクト}/{年}` が入っているかを機械的に照合する | v0.6.0 で置き場所を `{プロダクト}/{年}/` に変えたとき、検証器と `SKILL.md` は直ったが UI/UX 側のスキル5本とテンプレ2本が取り残された。**案内どおりに書いた UXDR が検証器に落ち、書いた人にはどちらが正しいか判断する材料が無い**状態が v0.7.0 まで残った。置き場所の変更は必ず複数の文書に散るので、注意力では追随できない |
| 配布物への固有物の混入を検証器で見るか | **見る**（`check_plugin_is_generic`）。①外部プロジェクトのパス参照（`src/` `.devin/` `.next` `pnpm ` `.claude/skills/`）②業種語の辞書。反例の行（`✗` `❌` 「書かない」を含む行）は対象外 | ①は網羅的に効く（存在しないパスは必ず壊れる）。②は辞書であり**当たった分しか見えない** — 空振りしても「固有物が無い」証明にはならない。それでも入れるのは、一度混入した語（店舗・予約完了時間 等）が再び入るのを止めるため。**判定を足すのは実際に混入を見つけたとき**で、想像で業種を増やさない |
| ペルソナを創作させるか、台帳から集計させるか | **集計のみ**（v1.2.0）。`speaker_role` 単位で `pd/voices/` を引き、根拠件数 `n` と期間・確信度・非対象を必須にする。`n = 0` の系統は像を書かず「未取得」で停止する | ペルソナは、検証されていない断定が**検証済みの記述と同じ見た目で**下流すべての根拠になる唯一の成果物。創作を許すと「停止してよい6箇所」の規律が戦略層だけ素通りする。年齢・性別などの装飾属性を持たせないのも同じ理由 — 判断に効かないうえ、像に「実在感」を与えて検証を止める。ただし装飾属性の検出は**警告**に留める（業種によっては正当な分解軸になりうる。誤検知で判定器全体が無視されるほうが損失が大きい） |
| ジャーニーを独立した成果物にするか、計測の分解式と同一物にするか | **同一物**（v1.2.0）。ジャーニーのステップ名は `kpi.md` の主要タスク時間の構成要素と同じ語を使い、二重に定義しない | 5層は静的な断面で時間軸を持たない。時間軸を足すこと自体は必要だが、**別管理にすると必ず食い違い、どちらが正か誰にも分からなくなる**。同一物にすると副産物として「部分の改善を全体の改善と呼ばない」既存の禁止事項がジャーニー上で可視化され、`ux-measurement` の設計がそのまま出てくる。裏側（バックステージ）は**任意の行**にする — 必須にすると、裏の無いプロダクトで空欄が量産され、空欄が「無い」と読まれる |
| 骨格層の担当を `ux-design-review` に兼ねさせるか、分けるか | **分ける**（v1.2.0）。`ux-screen-spec-writer` が**作る前**、`ux-design-review` が**作った後** | v1.1.0 まで骨格層には起草の担当が居らず、`templates/screen-spec.md` だけが所有者不在で置かれていた。結果、これから作る画面もレビューのスキルに流れ、**作り直しの指摘しか出せない**（空振り状態の欠落は、実装後に指摘しても作り直しになる）。テンプレートがあるのに担当スキルが無い状態は、そのテンプレートが使われないことと同義 |
| 表層のトークンを誰が所有するか | **`design-token-keeper`**（v1.2.0）。`a11y-contrast-guard` は下限の算出だけを持ち、台帳は持たない | 表層の成果物は「トークン」と「逸脱一覧」の2つだが、v1.1.0 まで所有者が居らず、逸脱表だけが a11y スキルの副作用として存在していた。**値の最終決定は DESIGN** という既存の線引きは動かさない — このスキルがやるのは台帳への登録・命名衝突の確認・期限の管理まで。「期限の無い例外は恒久化する」ため、逸脱の行の「未定」を検証器が弾く |
| スキルが増えたとき、担当の重なりをどう防ぐか | **形を検証器が見る**（`check_skill_shape`）。各 `skills/*/SKILL.md` に `name` とディレクトリ名の一致・`description`・**役割分界の表**を要求する | スキル名を列挙して守る方式は必ず取り残される（置き場所の追随と同じ失敗）。役割分界の表が無いスキルが1つ増えるたび「どれを呼べばよいか」が判断できなくなり、結局いつも同じ1つだけが使われる。**形だけを縛れば、スキルが何本になっても効く** |
| `specs/` の中身を検証器で見るか | **層ごとに1〜4個だけ見る**（v1.2.0）。空白の**書き方**（未取得 / 一次情報なし / 棄却条件 / 非対象）に限り、内容の真偽は見ない | `specs/` は人が手で直す現在値であり、判定を増やすと「validate を通すための記述」が書かれ始める。**それは規律ではなく作文**。既存の「形式・存在・パターンは検証器、内容の真偽は入れない」線引きをそのまま適用し、埋めた瞬間に誰も決めていないことが決定として流通する箇所だけを固定した |
| a11y を1スキルに束ねるか、色と操作で分けるか | **分ける**（v1.2.0）。`a11y-contrast-guard` は**値**を計算し、`a11y-interaction-guard` は**動かして**確かめる | 呼ばれる場面が違う（色に触るとき / 操作要素を作るとき）、入力が違う（hex / 実機・実装）、判定方法が違う（計算 / 実行）。1つに束ねると、色を変えるだけの場面で操作の検査項目が並び、**毎回スキップされるようになる**。既存名を改名しない理由は plugin 名と同じ — 参照している文書・規約が壊れる |
| 探索の計画をどこに置くか | **`validations/` に `RP-` 接頭辞で同居**（v1.2.0）。ディレクトリは増やさない | 探索（まだ仮説が無い）と検証（仮説の採否）は別物だが、**置き場所を分けると片方が忘れられる**。新しいディレクトリを増やすと `/pd:uninstall` の対象も増え、「片付けられないものを作らない」に反する。判定は接頭辞で分岐する（RP は対象者・聞かないこと・記録先、VP は棄却条件・行動観察） |
| 「聞かないこと」を必須にするか | **必須**（`check_research`） | 探索の失敗は「仮説が決まらない」ではなく**何も新しく分からない**こと。最大の原因は誘導質問（「◯◯があったら使いますか」）で、ほぼ全員が肯定するため情報量が0になる。**書く場所が無ければ、誰も先に決めない** |
| ナビゲーションを構造層と骨格層のどちらに置くか | **骨格層**（`pd/specs/04-skeleton/navigation.md`）。ただし各項目は**構造層の対象物か要件層のステップに対応させる** | 「何を対象物とするか」は構造、「それをどう並べ、どこから辿り着かせるか」は骨格。対応先を必須にするのは、どちらにも紐づかない項目＝**誰の関心でもないもの**が「その他」「設定」の下に溜まるのを止めるため。到達経路を必須にするのは、**迷子（どこからも辿り着けない画面）は書かせないと検出できない**から |
| 文言の点検を独立させるか、レビューに含めるか | **独立**（`ux-writing-guard`）。ただし記録先は `reviews/` を共用する | 文言は「表層の仕上げ」に見えて、実際は**要件と構造の露出**（名前が無いものは、まだ設計されていない）。レビューに含めると実装後にしか点検されず、そのときには文言が仕様として固まっている。一方で記録の種類を増やす理由は無いので DR を共用する |
| 「ユーザー」の単独使用を検証器で見るか | **見る。ただし警告**（`check_naming`）。複合語（ユーザーストーリー / ユーザー検証…）を弾かないよう、**直後が助詞・句読点・行末のときだけ**拾う | v0.6.0 から規約にあったが誰も見ていなかった。系統をまたいだ「ユーザーが不便」は**誰の何が不便か分からないまま合意が成立する**。一方で一般論として正しい文脈もあるため違反にはしない。**誤検知する判定は無視されるようになる**（`rules/05-operations.md` §5） |

---

## 14. 禁止事項

Skill 本文にも記載し、構築時にも守る。

| 禁止 | 内容 |
|---|---|
| Solution Jumping | 問題を理解する前に改善案を出す |
| Framework Theater | フレームワークを使うこと自体が目的になる |
| Generic Advice | どのプロダクトにも当てはまる一般論で終わる |
| False Causality | 相関を因果として断定する |
| KPI Only | 最終 KPI だけで Product Value を判断する |
| Average Only | 平均値だけで判断し、Segment / Behavior へ分解しない |
| Hallucination | Product Context を推測して Fact 扱いする |
| Product Leakage | プロダクト固有情報を `framework/` **および `uiux/`** に書き込む（v1.0.0 で `uiux/` を追加） |
| Foreign Path | 配布物から、利用プロジェクトの実装パス（`src/` `.devin/` `.next/` 等）や存在しないコマンド（`pnpm voices` 等）を参照する |
| Solution = Driver | 施策そのものを改善 Driver として扱う |

---

## 15. 構築手順

1. `.claude/skills/analyze/framework/` と `.claude/skills/analyze/products/` を作成
2. `SKILL.md` を作成
3. `framework/discovery.md` / `kpi.md` / `experiment.md` を作成
4. `products/_template.md` / `other-product.md` を作成
5. `README.md` / `CLAUDE.md` / `.local/README.md` を作成（§19）
6. **`scripts/` を作成（§19）** — `validate.py` / `selftest.sh` / `pre-commit` / `install-hooks.sh`
7. `.claude/settings.json` の hook を作成（同期の促し ＋ 規約チェック）（§19）
8. 検証（§16）を実行 — **`sh scripts/selftest.sh` と `python3 scripts/validate.py` が通ることを含む**
9. 必要な修正を行い、最終ファイルツリーを報告

説明だけで終わらせず、実際にファイルを作成すること。

---

## 16. 検証

作成後、次を確認する。

**規約の機械検証（最初に実行）**

```bash
python3 scripts/validate.py
```

`✓ 規約違反なし` になること。**さらに、検証器が実際に違反を捕まえるかを確かめる。**

```bash
sh scripts/selftest.sh
```

全項目が検出され、かつ**正常時には誤検知が出ない**こと。**常に成功する検証器は無いのと同じ。**

hook の発火も確認する。

```bash
export CLAUDE_PROJECT_DIR="$PWD"
echo '{"tool_input":{"file_path":"'$PWD'/analyses/{product}/{年}/壊れたファイル.md"}}' \
  | eval "$(jq -r '.hooks.PostToolUse[1].hooks[0].command' .claude/settings.json)"
```

`decision: block` が返ること。pre-commit は一時 git リポジトリでコミットが中止されることを確認する。

**ファイル構成** — §4 と一致し、余分なファイルが無いこと。

**配布物へのプロダクト固有情報の混入**

`validate.py` の `check_plugin_is_generic()` が `skills/` 全体を見る（v1.0.0）。
①外部プロジェクトのパス参照 ②業種語の辞書 の2つ。反例の行（`✗` `❌`「書かない」を含む行）は対象外。

```bash
grep -rniE "固有名詞|固有KPI名" skills/analyze/framework/ skills/analyze/uiux/
```

ヒットしてよいのは、§9 の「これらを書かない」という禁止例の列挙だけ。

> ⚠️ **`framework/` だけを見ても足りない。** v0.7.0 まで、`uiux/glossary.md` に
> 特定サービスの業務定義がそのまま入っていた。**用語集は「唯一の定義」なので、
> 固有の語が混ざると他プロダクトで間違った言葉が強制される。**
>
> ⚠️ **辞書は当たった分しか見えない。** この検査が空振りしても
> 「固有物が無い」ことの証明にはならない。判定を足すのは実際に混入を見つけたときで、
> 想像で業種を増やさない。

**日本語**

```bash
grep -rnE '^[A-Za-z][A-Za-z0-9 ,.:;()/&-]{30,}$' .claude/skills/analyze/
```

ヒットしてよいのは、コードブロック内の用語列挙だけ。英文の説明行が残っていたら書き直す。

**重複** — 主要概念の定義が1ファイルにのみ存在することを確認する。

```bash
for k in Controllability Interpretation Continue "Improvement Lever" "Leading Indicator" Voice "検出力" "見直し条件"; do
  printf '%-20s : ' "$k"; grep -rl "$k" .claude/skills/analyze/ | xargs -n1 basename | tr '\n' ' '; echo
done
```

複数ファイルにヒットする場合、**定義**が1箇所で残りが**参照**になっているかを目視で確認する。

---

## 17. Acceptance Criteria

すべて満たした場合のみ完成とする。

- [ ] `SKILL.md` / `framework/discovery.md` / `framework/kpi.md` / `framework/experiment.md` / `products/_template.md` / `products/other-product.md` が存在する
- [ ] 特定プロダクトへ依存していない
- [ ] 特定 KPI へ依存していない
- [ ] Framework と Product Context が分離されている
- [ ] Product 追加時に Framework を変更する必要がない
- [ ] `Context → Problem → Evidence → Driver → Hypothesis → Experiment → Decision` の流れを持つ
- [ ] `Fact` / `Interpretation` / `Hypothesis` / `Unknown` を区別する
- [ ] KPI Driver Analysis / UX Analysis / Root Cause Analysis が可能
- [ ] Improvement Lever を特定できる
- [ ] Experiment を設計できる
- [ ] Decision までつなげられる
- [ ] Missing Evidence を明示できる
- [ ] 「KPI が横ばい」を「効果なし」と「検出できていない」に切り分けられる
- [ ] 期限が決まっている状況で、Evidence 不足を明示したまま判断を出せる
- [ ] Voice を逐語で記録し、発話（`Fact`）と問題の所在（`Interpretation`）を分けて扱える
- [ ] Voice の偏り（非利用者・離脱者の不在）を解釈に持ち越せる
- [ ] 定量と定性を往復させて機構を特定できる（片方だけで結論を出さない）
- [ ] Primary KPI 以外の価値をコストと対で示し、導入判断につなげられる
- [ ] 見直し条件に確認者と時期があり、未確認の決定を追跡できる
- [ ] 棄却済みの仮説を再提出しない（過去の Note と Past Experiments を確認する）
- [ ] 予測データを実データと分離して扱える（Evidence にしない）
- [ ] 反証の節が必須になっており、確証バイアスを点検できる
- [ ] Experiment に予測値があり、予測と実測を積める（Confidence の校正）
- [ ] 棄却条件が観測可能な閾値で書かれている
- [ ] 新しい規約が既存の記録を巻き込まない（適用開始日を持つ）
- [ ] 生データと個人情報をリポジトリに残さず、数値と取得クエリだけを残せる
- [ ] Note を単体で開いても、用語（見出し・ラベル）の意味が分かる
- [ ] 画面（スクショ・録画）から、誰がやっても同じ範囲の `Fact` を切り出せる
- [ ] `python3 scripts/validate.py` が規約違反を検出し、正常時は通る
- [ ] 検証が5層（セッション開始 / 編集直後 / commit 実行前 / ターン終了 / git hook）で自動実行される
- [ ] git hook の導入が自動化され、手動コマンドを前提にしていない
- [ ] `--no-verify` による迂回が拒否される
- [ ] 外部サービス（CI）なしで完結している
- [ ] `sh scripts/selftest.sh` が全項目の検出と誤検知ゼロを確認できる
- [ ] hook や検証スクリプト・台帳を外すと検証器が気づく
- [ ] プロジェクト側に作るものが `pd/` 配下にまとまっている（例外は `CLAUDE.md` と CI の2つだけ）
- [ ] root 直下の旧レイアウトでも検証が通り、hook が動く（既存プロジェクトを壊さない）
- [ ] 置き場所を `pd/` へ移しても台帳の承認が要らない（キーが根からの相対パス）
- [ ] `/pd:uninstall` が、引数なしでは何も削除せずに対象を一覧できる
- [ ] 削除時に、pd より前からある `CLAUDE.md` / `.gitignore` / CI の内容を巻き込まない
- [ ] 手で編集した場合もコミット前に止まる
- [ ] 複数人で運用しても、最新の状態と未決事項が1箇所で分かる
- [ ] plugin をインストールし `/pd:init` を実行するだけで、UI/UX の改善まで回せる（別の道具を足さずに済む）
- [ ] UI/UX の話が出たとき、層の判定から始まる（好みの応酬にならない）
- [ ] UI を作る・直す前に、対象画面の Voice を引き当てる手順が組み込まれている
- [ ] 引き当てずに出した改善案に「デザイナー起案」が明記される
- [ ] Voice が `screen` で引ける（1ファイル = 1声）
- [ ] Voice の匿名化が形式で担保される（PII 検査と発話行の形式強制が新スキーマでも働く）
- [ ] UXDR が「決めなかったこと」を3列（何が分かれば決まるか / いつまでに / 誰が）で持つ
- [ ] 作業仮説に観測可能な閾値を持つ棄却条件がある
- [ ] 影響範囲に「変わらなかったもの」が書かれる
- [ ] プロジェクト側に UI/UX 専用の並列ディレクトリ（`uiux/` 等）を作らせない
- [ ] 配布物に特定業種の語彙が無い（利用者の呼称・業務用語・主要タスク時間の中身を持たない）
- [ ] 配布物が外部プロジェクトのパス（`src/` `.devin/` `.next/` 等）を参照していない
- [ ] 文書に書かれたコマンドがそのまま実行できる（存在しない npm script を案内しない）
- [ ] スキルの案内どおりに書いた UXDR / VP / MP / DR が、そのまま検証器を通る
- [ ] テンプレートをコピーして埋めるだけで、必須の frontmatter が揃う
- [ ] 話者の役割を各プロジェクトが決められ、決めた値以外が弾かれる（`taxonomy.json`）
- [ ] 役割名の表記ゆれ（大文字・日本語・空白）が形式で弾かれる
- [ ] 固有物の混入を検証器が検出する（`sh scripts/selftest.sh` が確認する）
- [ ] 5層すべてに担当スキルがある（戦略から表層まで、判定後の行き先が空にならない）
- [ ] ペルソナが台帳からの集計になっており、根拠件数・確信度・非対象を持つ
- [ ] 一次情報が0件の利用者系統に、像が書かれない
- [ ] ジャーニーのステップが主要タスク時間の構成要素と同一の語で書かれる
- [ ] 所要時間の空欄に、それらしい数字が入らない（未取得と書かれる）
- [ ] 画面仕様が実装より前に書かれ、空振り状態が必ず設計される
- [ ] 画面仕様に色の値が直書きされない（トークン名で書かれる）
- [ ] トークン台帳が定義の真実の源を持ち、期限の無い逸脱を残さない
- [ ] 各スキルが役割分界の表を持ち、担当の重なりが検証器で検出される
- [ ] 仮説が無い段階（探索）と、仮説がある段階（検証）が別のスキルとして扱える
- [ ] 探索計画に「聞かないこと」があり、誘導質問が実施前に排される
- [ ] 色以外の a11y（キーボード・フォーカス・読み上げ・寸法・動き）に下限がある
- [ ] 確かめられなかった a11y 項目が「未確認」として残る
- [ ] ナビ項目が対象物かステップに対応し、到達経路0本の画面が検出できる
- [ ] UI 文言が用語集と突き合わされ、用語集に無い語が構造層へ返される
- [ ] Solution Jumping を防止している
- [ ] 必要な Framework のみ利用する設計になっている
- [ ] ファイル間で不要な重複がない
- [ ] Markdown 本文が日本語である
- [ ] `/pd:analyze` で利用可能である

---

## 18. 新しいプロダクトの追加

```
plugin の products/_template.md を複製
    ↓
利用プロジェクトの pd/products/{product-name}.md にプロダクト固有情報を記載
    ↓
/pd:analyze {product-name} で分析
```

`framework/` は変更しない。変更が必要になった場合、それは「共通フレームワークに固有事情が漏れている」か「テンプレートの Schema が足りない」かのどちらかなので、`framework/` ではなく `_template.md` 側を見直す。

---

## 19. プロジェクトルールと hook

Skill の中身だけでは、**運用のルール**（誰がやっても守られるべき手順）は担保されない。次の2つを合わせて置く。

### `CLAUDE.md`（ワークスペース直下）

セッションごとに自動で読み込まれる。ここに書くのは、Skill の使い方ではなく**このリポジトリで作業する全員が守る手順**。

- `.claude/skills/analyze/` を変更したら `pd-skill-blueprint.md` の該当セクションも同じ作業内で更新する（ユーザー確認は不要）
- `framework/` にプロダクト固有情報を書かない
- **pd が作るものは `pd/` 配下から出さない**（例外は `CLAUDE.md` と CI の2つだけ）。やめるときに何を消せばいいかが分かる状態を保つ
- `pd/analyses/` は追記のみ、`pd/products/` は上書き
- `pd/voices/` は逐語のみ。要約で置き換えない
- `pd/simulations/` は Evidence ではない。引用は検証器が検出する
- Evidence には必ず4ラベルを付ける

チームで使う場合、次も入れる。

- **Note と Context は同じ作業内で一緒に更新する**（分けると、どの分析が Context を動かしたか追えない）
- Note の frontmatter に `author` を入れる
- **索引ファイルを作らない**（一覧はディレクトリ、未決は Context が正）
- 過去の Note を修正しない。認識が変わったら新しい Note を追加し、差分として書く

### `README.md`（ワークスペース直下）

`CLAUDE.md` は Claude 向けのルール、`README.md` は**人間向けの入口**。役割を分ける。

- 専門用語を前提にしない。`Fact` / `Interpretation` などのラベルは意味と例を添えて説明する
- 冒頭に**「まずどこを読めばいいか」の案内**を置く（目的別に4行）。README が長くなると通読前提の構成では読まれない
- 含めるもの: 何ができるか / 使い方（`/pd:analyze` の打ち方と**聞き方のコツ**）/ **新しいプロダクトの追加手順**（§18 を素人向けに書き直したもの）/ **元データの用意の仕方**（3種類・4つの渡し方・置かないもの・匿名化・データが無い場合）/ フォルダの意味と「書き換えていいか」/ ラベルの考え方 / **分析結果の読み方**（Driver・Root Cause 等の用語を平易な言い換えで対応表に）/ 実際の分析例1つ / チームでの約束 / **やめ方**（プロジェクトからの片付けと plugin のアンインストール、その順序）/ FAQ
- 素人が踏むと取り返しがつかない項目（**個人情報・生データの取り扱い**）は、ルール側（`CLAUDE.md` / `SKILL.md`）と README の両方に書く。ここだけは重複を許す
- **固有名詞を入れない** — 実在のプロダクト名、ベンダー名・製品名（DB / 解析 / 決済 / ホスティング等）、業種特有の語を書かない。「データベース」「アクセス解析ツール」「決済の管理画面」のように役割で書く。例も業種に寄せず、`申込` / `利用者` のような中立な語にする
- README は Skill と一緒に他プロジェクトへ持ち出される。固有名詞が入っていると、別業種・別スタックの読み手が「自分向けではない」と判断して読まなくなる
- 含めないもの: フレームワークの中身の再掲（`framework/` にある）、ルールの完全な列挙（`CLAUDE.md` にある）

README を「ルールの一覧」にしない。読む気を失わせ、かつ `CLAUDE.md` と二重管理になる。

**素人が読んで詰まる典型を、構築後に必ず点検する。** 実際に踏んだもの:

| 種類 | 例 | 対策 |
|---|---|---|
| 自己矛盾 | 「一覧ファイル（README や index）を作らない」と README に書く | 具体名で書く（`analyses/index.md` のようなもの）。README 自身が該当しないか確認 |
| 場所の矛盾 | 「このフォルダに保存しない」の直後に「このフォルダ内の `.local/` に置く」 | 主語を「共有されるファイルとして」に変える |
| 設定との不一致 | 「`.local/` を除外」と書くが、実際は中身だけ除外で説明ファイルは共有 | 実装を読んでから書く |
| 専門用語 | `PR` / `コミット` / `クエリ` / `離脱` | 平易な語に置換、または初出で括弧内に定義 |
| 形式の混在 | `/pd:analyze 名前` と `/pd:analyze 〜を分析したい` が別々に登場し、正解が分からない | 「書き方は自由」と1回で示し、例を並べる |
| 内部説明の混入 | 内部のファイルパスや処理順を本文に書く | 見出しに「（知らなくても使えます）」と付ける |

**README とルール（`CLAUDE.md`）の同期を運用ルールにする。** Skill の変更で利用者の操作・置き場所・守るべきルール・用語が変わったら、README も同じ作業内で更新する。対応表を `CLAUDE.md` に置き、hook の文面にも README を含める（`.claude/skills/analyze/` 配下の変更を検知した時点で両方を促す）。

### `scripts/validate.py` — 規約の機械検証（最重要）

**まず版管理を使うかを決める。** 使わない場合、git 前提の層（`pre-commit` / `pre-push` / コミット前のコマンド検査 / CI）は**作らない**。動かないコードが残ると「動いているつもり」の誤解を生む。代わりに台帳（後述）を必須にする。

**ドキュメントだけの規約は守られない。** チームで実務に使うなら、合否を判定するコマンドを1つ用意し、それを唯一の判定者にする。

検証項目（`analyses` / `voices` / `simulations` / `products` / `framework` / リポジトリ全体）:

```
パスと命名        年フォルダ、YYYYMMDD-NN-{1語}、products/{name}.md の存在、年と日付の一致
                 **同日連番の重複**（複数人が同じ日に作業すると必ず起きる）
frontmatter      必須6項目、ファイル名との一致（product / date）
Note の可読性     凡例ブロックの有無、英語見出しへの日本語併記（`##` だけでなく `###` も）、ラベルの使用
分析の質          反証の節（Decision があるとき必須）、Experiment の予測値、棄却条件の閾値
警告（止めない）   必須 Segment での分解、数値の出典、Note の分量
分離の保証        Note が simulations/ を参照していない、products は参照時に「予測」明示
削除・リネーム     台帳にあるファイルが存在しない場合は違反（履歴の消失を検出。--accept で承認）
匿名化            メール / 電話 / @アカウント / 敬称 / 頻出姓の検出、発話者の ID 形式
取得経路          voices の source を許可リストで検証（表記が揺れると後から集計できない）
予測データ         synthetic: true、警告ブロック
Context           必須節（Available Evidence / Past Experiments / Decisions / 保留中の見直し / Unknowns）
                 Voice のファイル名を列挙していないか（ディレクトリが正）
固有名の混入       products/*.md のファイル名から**自動生成**して framework/ と README.md を照合
リポジトリ         生データ・画像の混入、索引ファイルの存在、OS のノイズファイル（`.DS_Store` 等）
```

設計上の要点:

- **プロダクト名をハードコードしない。** `products/*.md` のファイル名から動的に作る。プロダクトが増えても検証器を直さなくて済む
- 標準ライブラリのみ（依存を増やすと導入されない）
- 引数でファイルを渡せるようにする（編集直後の1件だけ検証したい）
- 違反は `file:line: 内容` の形式で出す。修正できない指摘は出さない

**中身の規約も検証する**（形式だけでは不十分）。

```
Decision 節      見直し条件 / 確認者 / 確からしさ
Experiment 節    Success Criteria / Decision Rule
不足情報 節       どう取得できるか
`Fact` の行      推測語（「かもしれない」「はず」「おそらく」等）を含まない
```

**版管理の有無で層が変わる。** git を使わない運用が普通にあるため、git 前提の規約（追記のみ・過去を書き換えない）には代替を用意する。

### `scripts/ledger.json` — 履歴の代わり（git を使わない場合の必須）

`analyses/` `voices/` `simulations/` の各ファイルのハッシュを持ち、**書き換えを検出する**。

- 新規ファイルは自動で台帳に載る（載せた日付も持つ）／**当日の修正は通し、後日の書き換えを違反にする**（書いた当日の仕上げまで止めると使われなくなる）
- 台帳の値は `{hash, seen}`。ハッシュだけでは「いつ載ったか」が分からず、当日の猶予を判定できない
- `--accept` で正当な変更（表記統一など）を承認して台帳を更新する。**承認は `ledger-log.md` に追記する**（何を承認したか残さないと、ルールが守られたか検証できない）
- **改ざん耐性は無い**（台帳を書き換えれば回避できる）。この限界を必ず明記し、バックアップを別手段で用意させる
- **検出だけで復元はできない。** バックアップは別手段（この限界を必ず明記する）
- git を使う場合は履歴があるため必須ではないが、併用してよい

### 自動実行の層

**外部サービス（CI）に依存させない。** git 非使用でも4層で閉じる。

| 層 | 仕組み | 何を守るか | git 必要 |
|---|---|---|---|
| セッション開始 | `SessionStart` hook | 残存違反の通知 ＋ **新しい版の案内**。git があれば hook も自動導入・自己修復 | 不要 |
| 編集直後 | `PostToolUse` hook → `decision: block` | Claude の作業。その場で差し戻して自己修復させる | 不要 |
| ターン終了 | `Stop` hook → `systemMessage` で通知 | 取りこぼしの可視化（ブロックしない。デッドロックを避ける） | 不要 |
| 常時 | 台帳（`ledger.json`） | 過去の記録の書き換え | 不要 |
| commit / push 実行前 | `PreToolUse`(Bash) hook → `scripts/commit-gate.sh` | `--no-verify` の拒否と違反時のコマンド拒否 | 必要 |
| git の commit / push | `scripts/githooks/pre-commit` `pre-push` | **Claude を使わず手で編集した場合** | 必要 |

設計の要点:

- **`core.hooksPath` を使う**（`git config core.hooksPath scripts/githooks`）。`.git/hooks` へコピーしないので hook 自体がバージョン管理され、内容の更新が全員に届く
- 設定は `SessionStart` hook が毎回確認して直す。**手動導入を前提にしない**（誰かが忘れた時点で穴になる）
- commit / push の検査は**インラインコマンドにせずスクリプトに切り出す**。インラインの多重クォートは壊れやすい（実際に jq のクォートで壊れた）
- **GitHub は不要。** CI を足すかは版管理を使う場合の選択肢にすぎず、初期構築では作らない
- **存在しない層を必須にしない。** 版管理を使わないなら、必須は「検証スクリプト＋台帳＋hook」だけにする。使わない仕組みを必須にすると、永久に落ち続ける検証器になる
- **`.local/` の安全性は自動では保証されない。** 版管理を使わない場合、除外設定という概念自体が無い。フォルダ同期で個人情報が渡るため、同期除外かプロジェクト外配置を規約に明記する

**更新は放っておくと届かない。** サードパーティの配布元は既定で自動更新されないため、版を上げても利用者の手元は古いままになり、手元と CI で判定が食い違う。`SessionStart` で「配布元の最新版 vs 手元の版」を比べ、新しければ**変更履歴・リリース・実行するコマンド**を出す（`scripts/update_check.py`）。守ること:

- **起動を止めない。** 起動時はキャッシュを読むだけにし、問い合わせは裏で走らせて結果は次の起動から使う。SessionStart は利用者が待たされる場所で、ここで数秒使ってはいけない
- **失敗しても黙る。** 圏外・社内プロキシ・API 制限で取れないのは普通のこと。案内が出ないだけで作業は妨げない。取れなかった場合も最終確認時刻は進める（起動のたび問い合わせを撃ち続けないため）
- **キャッシュを plugin 配下に置かない。** `/plugin update` で丸ごと入れ替わり、更新直後に必ず1回ネットワークを叩くことになる（`~/.cache/pd-plugin/` 等に置く）
- **版の比較は数値のタプルで行う。** 文字列比較だと `1.10.0 < 1.9.0` になる
- **配布元の URL を直書きしない。** `plugin.json` の `repository` から導く
- 案内文には「判定のルールが変わった版では今まで通っていたファイルが落ちる」ことを添える。**更新は無条件に善ではない**
- **案内するコマンドは1つにする。** Claude Code の更新は2段階（配布元の一覧の取り直し → plugin の更新）で、`plugin update` は**手元にある一覧しか見ない**。順序を守らないと更新されないばかりか、**一覧が古い場合は古い版へ降格する**（実測: 一覧が v1.0.0 のとき v1.0.1 → v1.0.0 と「更新」された）。順序を利用者に覚えさせず、両方を実行するコマンド（`/pd:update`）を配布物に含める

### `scripts/selftest.sh` — 検証器を守る

**常に成功する検証器は、無いのと同じ。** 一時コピーに壊したファイルを作り、各項目が検出されることを確認する。

```
命名違反 / frontmatter 欠落 / 凡例なし / 見出しの言い換え漏れ / Fact への推測語
Decision の必須項目欠落 / 匿名化漏れ（敬称・メール・姓・ID 形式なし）
synthetic フラグ・警告の欠落 / 生データ・索引ファイル / framework への固有名混入
hook の削除 / 台帳の削除 / 検証スクリプトの削除 / **正常時に通ること（誤検知の検出）**
**旧レイアウト（root 直下）でも通り、hook が動くこと**
```

最後の2項目が最も重要。誤検知を出す検証器は、いずれ無効化される。置き場所を変えた版では、**旧レイアウトを実際に作って通るところまで確かめる** — ここが壊れると、更新した既存プロジェクトが全ファイル違反になる。

連動:

- `validate.py` を変更するコミットでは、pre-commit が自己テストを自動実行する
- CI は「自己テスト → 検証 → hook 導入可否」の順に走らせる
- 判定を追加したら、自己テストに壊れた例を1つ追加する

### `commands/uninstall.md` — 片付けられる状態を保つ

**入れる手段だけを用意して、やめる手段を用意しないのは不誠実。** どこに何ができたか分からない道具は、試すこと自体の心理的コストが高い。

- plugin のアンインストール（`/plugin uninstall`）は**プロジェクト側のファイルに触れない**。だから片付けはコマンド側で用意する。自動連動は作れない
- **順序を明記する。** plugin を先に外すとこのコマンドも消え、後から実行できない
- 既定（引数なし）は**一覧表示のみで何も削除しない**。`--keep-data`（仕組みだけ）/ `--purge`（分析結果ごと）を明示的に選ばせる
- **既存ファイルへの追記は、行・節の単位で消す。** `CLAUDE.md` / `.gitignore` / CI は pd より前から存在しうる。ファイルごと削除すると無関係な内容が失われる
- CI は中身に plugin の checkout があるかを確認してから消す（同名の他人の CI を消さない）
- `--purge` の前に、消える件数を示して確認を取る。追記のみで積み上げた記録は復元できない

### 仕組みごと外される穴を塞ぐ

`validate.py` 自身が次を検証する。

- `.claude/settings.json` の hook が消えていないか（**イベント単位**で見る。テキスト検索では片方の削除を見逃す）
- `scripts/` の4ファイルが揃っているか
- CI を置いた場合、そのワークフローが消えていないか（後述の `TZ` 指定を含む）

**規約を変えたら検証器も変える。** 検証されない規約は、遅かれ早かれ守られなくなる。判定を緩める場合は理由を §13 に残す。

### 版管理を使う場合の追加（任意）

版管理を併用するなら、次を足せる。**使わないなら作らない。**

```
.gitignore                      .local/* と生データ・個人情報の拡張子を除外
                                （.local/README.md だけ !.local/README.md で共有する）
scripts/githooks/pre-commit     コミット前チェック（core.hooksPath で参照）
scripts/githooks/pre-push       push 前チェック
scripts/ensure-hooks.sh         SessionStart から呼び、core.hooksPath を設定して自己修復
scripts/commit-gate.sh          PreToolUse(Bash) から呼び、commit / push を検査し --no-verify を拒否
CI                              上記を飛ばされた場合の最後の砦
```

### plugin として配る場合（現在の構成）

Skill を複数プロジェクトで使うなら、配布物を plugin にする。install だけで使える状態になり、Skill の改善が `/plugin update` で全プロジェクトへ届く。

```
/plugin marketplace add {owner}/pd-plugin
/plugin install pd@pd-plugin
/pd:init                                  利用プロジェクトで1回だけ
```

ただし `/plugin update` は**自動では走らない**。次項の「版を配る」を参照。

このとき次の4点が要る。**どれか1つでも欠けると、install しても動かないか、無関係なプロジェクトを壊す。**

1. **hook の no-op 条件** — plugin の hook は有効化した全プロジェクトで動く。pd を使わないプロジェクトで検証器が走ると毎回違反を出すため、目印（`pd/ledger.json`）が無ければ何もしない
2. **プロジェクトの決め方** — 検証器は plugin 側にあり、対象は別リポジトリにある。`PD_PROJECT_DIR` → `CLAUDE_PROJECT_DIR` → カレントの順で解決する
3. **Context の置き場所** — `products/{product-name}.md` は利用者が書き換えるものなので、plugin 配下に置かない（更新で消える）
4. **CI からの取得** — runner に plugin は入っていない。利用プロジェクトの CI では plugin リポジトリを checkout する。**このため plugin 側は Public にする**（Private だとトークンが要る）

### hook は1つの入口に集約する

`hooks.json` には**判定を書かない。** `python3 {plugin}/scripts/hook.py {event}` を呼ぶだけにし、「動くべき場面か」の判断と出力の整形は `hook.py` が持つ。

```
hooks.json   どの event で何を呼ぶか（それだけ）
hook.py      動くべき場面か / 出力形式への整形
validate.py  規約の判定（唯一の判定者）
```

理由は2つ。

- **移植性** — `hooks.json` に `jq` やシェル構文（`case` / `read` / `printf`）を書くと、**Windows では sh も jq も無いため hook が丸ごと動かない**。「間違いは自動で見つかる」という前提が環境によって崩れる。依存は `python3` 1つに寄せる（`validate.py` が既に要求しているので増えない）
- **可読性** — JSON 文字列の中にエスケープされたシェルを書くと、変更のたびに壊れる。テストも書けない

`hook.py` に規約の判定を書かない。判定が2箇所に分かれると、どちらが正か分からなくなる。

**hook は「形」ではなく「挙動」を検証する。** `hooks.json` に名前が載っていても、実際に止められなければ意味がない。自己テストから `hook.py` を直接呼び、違反を block するか・無関係なプロジェクトで沈黙するか・壊れた入力で異常終了しないかを確かめる。

検証器の guard は、plugin 自身を見ているのか利用プロジェクトを見ているのかで分岐する。前者では配布物の欠落（`plugin.json` / `marketplace.json` / `hooks.json` / コマンド / `CHANGELOG.md`）と版の整合を、後者では台帳と CI を見る。

### 版を配る

**Claude Code は `plugin.json` の `version` を更新の判定キーにする。** 上げなければ、コミットを push しても `/plugin update` は「already at the latest version」を返し、利用者に届かない。逆に `version` を省けば commit SHA が版になり、push のたびに届く（開発中のチーム内配布向け）。**判定器を含む plugin では明示版を使う** — 意図しないタイミングで判定が変わると、利用者の CI が理由なく落ちる。

さらに、**サードパーティの marketplace は auto-update が既定で無効**。利用者が `/plugin` → Marketplaces → Enable auto-update を自分で有効にしない限り、版を上げても手元は古いままになる。**README の導入手順に「更新の受け取り方を決める」段を置く。** 置かないと、利用者は更新の存在自体を知らないまま使い続ける。

このため配布側は次の4つを揃える必要がある。**検証器で強制し、手順は1コマンドに畳む。**

```
plugin.json と marketplace.json の version      ← 食い違いを検出する
CHANGELOG.md の該当版の項目                     ← 現在の版が無ければ落とす
pd-init が CI に焼き込む ref                    ← 古いと新規プロジェクトが旧判定器で回る
git tag v{version}                              ← その ref の実体
```

**手順を人手に残さない。** 「版を3箇所書き換えて、CHANGELOG を書いて、検証して、コミットして、タグを打って、push する」を順番に実行させると、必ずどこかが抜ける。実際に**未コミットのままタグを打つ事故が3回続いた**（タグが古い内容を指し、直したはずの不具合がそのままリリースされた）。

`scripts/release.sh <版>` に畳み、**作業ツリーが汚れていれば中止する**。版の書き換えはスクリプトが行い、人が触るのは CHANGELOG だけにする（何が変わったかは機械には書けないため、ここだけは人が書く）。

この種の失敗に「気をつける」で対処しない。**順序を間違えられる形にしているほうが原因**である。

`CHANGELOG.md` は体裁の問題ではない。**判定を変える plugin では、更新が既存データを落としうる。** 何が変わったかを書かなければ、利用者は更新の可否を判断できず、結果として誰も更新しなくなる。存在チェックだけでは版ごとの追記が抜けるため、`plugin.json` の現在の版が本文に現れるかまで見る。

**このリポジトリでは `.gitignore` と CI（`.github/workflows/validate.yml`）だけを採用している。** git hook 系（`pre-commit` / `pre-push` / `commit-gate.sh` / `ensure-hooks.sh`）は入れていない。PostToolUse hook が編集の時点で止めているため、同じ判定を段数だけ増やしても検出は増えず、`--no-verify` の抜け道を塞ぐ仕組みの維持コストだけが残るため。

CI を置く場合の注意が2つある。

- **`TZ` を明示する。** runner の既定は UTC。台帳の「書いた当日の修正は通す」判定は実行マシンのローカル時刻（`datetime.now()`）で行うため、JST 00:00〜09:00 に書いた記録が「前日のもの」と見なされ、**手元では通る同日の修正が CI でだけ落ちる**
- **判定をワークフロー側に書かない。** `validate.py` を呼ぶだけにする。判定が2箇所に分かれると、どちらが正か分からなくなる

**CI は改ざん耐性を上げない。** 台帳自体を書き換えれば検出は回避できる点は変わらない。上がるのは「検証を実行し忘れた push を捕まえる」確率だけ。

複数人で並行して作業する段階に入ったら、次の2つが新たに問題になる。**先回りして入れない**（1人運用では起きない）。

- `scripts/ledger.json` は検証のたびに更新されるため、ブランチをまたぐと**マージのたびに衝突する**。中身がハッシュなので手作業では正解を判断できない
- ブランチ保護（直 push 禁止・PR 必須）を入れると、Note 1本ごとに PR が必要になる。追記が主な作業であるこのリポジトリでは手数が重い

追加した場合、**検証器の必須ファイル判定と自己テストにも同時に追加する**（片方だけ増やすと形骸化する）。

### `.claude/settings.json` の PostToolUse hook

`CLAUDE.md` は読み飛ばされうるので、機械的な検知で補強する。`Write|Edit` の対象が `.claude/skills/analyze/` 配下だった場合に、blueprint の同期を促す文脈を注入する。

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "jq -r '.tool_input.file_path // .tool_response.filePath // empty' | { read -r f; case \"$f\" in */.claude/skills/analyze/*) printf '%s' '{\"hookSpecificOutput\":{\"hookEventName\":\"PostToolUse\",\"additionalContext\":\"（blueprint 同期を促す文面）\"}}';; esac; }",
            "statusMessage": "blueprint 同期チェック"
          }
        ]
      }
    ]
  }
}
```

`.claude/settings.json`（コミット対象）に置くこと。`settings.local.json` はローカル専用なので、他のメンバーに適用されない。

**対象は Skill のロジックだけに絞る** — `SKILL.md` / `framework/*` / `products/_template.md`。`products/{product-name}.md` は分析ごとに更新される Context データであり、blueprint とは無関係なので除外する。ここを `pd/*` で一括にすると、分析のたびに誤検知が出る。

**hook は「促す」だけで、ブロックはしない。** blueprint 更新が必要ない変更（typo 修正など）もあるため、判断は作業者に残す。

---

## 20. 最終ゴール

このSkillの目的は、UX分析やKPIレポートの作成ではありません。対象プロダクトの Context を理解し、

```
何が起きているか → なぜ起きているか → どの Driver が成果へ影響しているか
→ どの Driver を改善すべきか → 何を Experiment すべきか → 次に何を意思決定すべきか
```

まで一貫して考えられる基盤を作ることです。

最重要の設計原則:

> 共通 Framework は再利用可能にし、Product Context だけを差し替えることで、どのプロダクトにも適応できること。
