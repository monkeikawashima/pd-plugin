---
description: pd を使うプロジェクトの置き場所・台帳・CI・規約を作る（1回だけ）
---

# pd-init

このプロジェクトで `/pd:analyze` を使えるようにする。**既にあるものは上書きしない。**

## 手順

1. **既存の確認** — `pd/` または root 直下の `products/` `analyses/` が既にあれば、その旨を伝えて**何も壊さない**。不足しているものだけ足す

   **root 直下に `products/` `analyses/` がある場合は旧レイアウト。** 移動しない。検証器がそのまま読む

   利用者が `pd/` へ移したいと言った場合のみ、この順で案内する。**台帳の作り直しは不要**（記録の場所は `pd/` から見た相対位置で覚えているため）
   1. 共有できていない変更が無いことを確認する（途中で失敗しても戻せるように）
   2. `products` / `analyses` / `voices` / `simulations` を `pd/` の中へ移す
   3. `.gitignore` の `.local/` を `pd/.local/` に直す
   4. `/pd:validate` で違反が出なければ完了

2. **置き場所を作る** — pd が作るものは `pd/` 1つに収める。**消したいときに、どれが pd のものか分かるようにするため**

```
pd/
├── products/       プロダクトの Context（現在値）
├── analyses/       分析の履歴（追記のみ）
├── voices/         発話の逐語（匿名化済み・追記のみ）
├── simulations/    予測データ（Evidence ではない）
├── specs/          層ごとの現在値（戦略〜表層。上書き）
├── decisions/      決定記録 UXDR（追記のみ）
├── validations/    検証計画 VP（追記のみ）
├── measurements/   計測計画 MP（追記のみ）
├── reviews/        レビュー結果 DR（追記のみ）
├── .local/         元データの一時置き場（共有しない）
└── ledger.json     台帳（過去の記録の書き換えを検出する）
```

`specs/` 以降は v0.6.0 で UI/UX の成果物を統合したもの。**UI/UX 専用の別ディレクトリを作らない**（`uiux/` のような並列の置き場所を作ると、同じ事実を二箇所に書くことになる）。

空ディレクトリは残らないので、`pd/.local/README.md` に「ここに置いた元データは共有しない。作業後に消す」旨を書いて作る。他は最初のファイルが書かれた時点でできるため、**先に空フォルダを作らない**。

3. **台帳を作る** — `pd/ledger.json` に `{}` を書く。このファイルの有無が「pd を使うプロジェクトか」の目印になり、無いと hook が動かない

3.5 **固有の語彙の置き場所を作る** — plugin は業種の言葉を持たない。**このプロジェクトの言葉はここで決める**

- `pd/voices/taxonomy.json` を**空の配列で**作る。埋まるまでは形式チェックだけが働く（導入直後を赤くしないため）

```json
{
  "speaker_role": [],
  "object": [],
  "phase": []
}
```

- `pd/specs/01-strategy/glossary.md` を雛形として作る。**中身は埋めない**（分かっていないことを埋めると、誰も決めていない定義が流通する）

```markdown
# 用語集（このプロダクト固有）

共通の用語は plugin 側（`skills/analyze/uiux/glossary.md`）。ここには**このプロダクトの言葉だけ**を書く。

## 1. 利用者の呼称

| 呼称 | 定義 | `speaker_role` |
|---|---|---|
| 未定義 | | |

> 「ユーザー」を単独で使わない。必ずどの系統かを指定する。
> 決めた呼称は `pd/voices/taxonomy.json` の `speaker_role` に入れる。

## 2. 主要タスク時間

利用者系統ごとに1つ定義し、**必ず要素に分解する**。

| 系統 | 主要タスク時間 | 要素 |
|---|---|---|
| 未定義 | | |

> 部分の改善を全体の改善と呼ばない。

## 3. 業務用語

| 用語 | 定義 |
|---|---|
| 未定義 | |
```

4. **`.gitignore`** — 無ければ作る。あれば次の行が無い場合だけ追記する

```
pd/.local/
.DS_Store
```

5. **CI** — `.github/workflows/validate.yml` を作る（既にあれば触らない）。`TZ` と plugin の取得は必須。`ref` は plugin の版を固定する

```yaml
name: validate

on:
  push:
  pull_request:
  workflow_dispatch:

jobs:
  validate:
    runs-on: ubuntu-latest
    env:
      # runner の既定は UTC。台帳の「書いた当日の修正は通す」判定が
      # 日本時間とずれ、手元では通る修正が CI でだけ落ちる。
      TZ: Asia/Tokyo
    steps:
      - uses: actions/checkout@v4
      - uses: actions/checkout@v4
        with:
          repository: monkeikawashima/pd-plugin
          ref: v1.4.0
          path: .pd-plugin
      - name: 規約を検証する
        run: python3 .pd-plugin/scripts/validate.py
        env:
          PD_PROJECT_DIR: ${{ github.workspace }}
```

6. **CLAUDE.md** — 無ければ作り、あれば「pd の規約」節を追記する（既にあれば触らない）。内容は次を含める

- 判定者は1つ。`/pd:validate` が唯一の判定者で、人の解釈で合否を決めない
- pd が作るものは `pd/` 配下に置く。やめるときは `/pd:uninstall`
- `pd/products/` と `pd/specs/` は上書き、`pd/analyses/` `pd/voices/` `pd/simulations/` `pd/decisions/` `pd/validations/` `pd/measurements/` `pd/reviews/` は追記のみ
- Evidence には `Fact` / `Interpretation` / `Hypothesis` / `Unknown` のいずれかを付ける
- 元データ・個人情報を置かない。`pd/voices/` は匿名化してから記録する
- 索引ファイルを作らない。ボイスの一覧は `voices.mjs query` / `stats` で取る
- 利用者の呼称・オブジェクト名・業務用語は `pd/specs/01-strategy/glossary.md` で決める。plugin 側には無い
- UI/UX の作業は `ux-layer-triage` から始める。UI を作る/直す前に対象画面のボイスを引き当てる
- 台帳に無い改善案は「デザイナー起案」と明記する
- 利用者像（ペルソナ）は創作せず、`pd/voices/` を役割ごとに集計して作る。0件の役割には像を書かない
- ジャーニーのステップは、主要タスク時間の構成要素と同じ語で書く（二重に定義しない）
- 画面は実装より前に仕様を書く。空振り（結果が0件）の状態設計を省略しない
- 探索（まだ仮説が無い）と検証（仮説の採否）を混ぜない。探索では「聞かないこと」を先に決める
- ナビゲーションの各項目は、対象物かジャーニーのステップに対応させる。到達経路を書かずに増やさない
- 色以外の a11y（キーボード・フォーカス・読み上げ・44px・動き）も下限を確認する。確かめていない項目は「未確認」と書く
- 過去の Note を修正しない。認識が変わったら新しい Note を追加する

7. **最初の Context** — 対象プロダクトが分かっていれば、plugin の `skills/analyze/products/_template.md` を Schema として `pd/products/{product-name}.md` を作る。分からなければ作らず、`/pd:analyze` の初回実行時に作ると伝える

8. **検証** — `/pd:validate` を実行し、違反が出ないことを確認してから完了を報告する

## 報告

作ったものと、作らなかったもの（既にあったため）を分けて伝える。最後に「`/pd:analyze {プロダクト名}` で分析を始められる」ことを1行で示す。
