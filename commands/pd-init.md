---
description: pd を使うプロジェクトの置き場所・台帳・CI・規約を作る（1回だけ）
---

# pd-init

このプロジェクトで `/pd` を使えるようにする。**既にあるものは上書きしない。**

## 手順

1. **既存の確認** — `products/` `analyses/` `pd/ledger.json` が既にあれば、その旨を伝えて**何も壊さない**。不足しているものだけ足す

2. **置き場所を作る**

```
products/          プロダクトの Context（現在値）
analyses/          分析の履歴（追記のみ）
voices/            発話の逐語（匿名化済み・追記のみ）
simulations/       予測データ（Evidence ではない）
.local/            元データの一時置き場（共有しない）
pd/                台帳（過去の記録の書き換えを検出する）
```

空ディレクトリは残らないので、`.local/README.md` に「ここに置いた元データは共有しない。作業後に消す」旨を書いて作る。他は最初のファイルが書かれた時点でできるため、**先に空フォルダを作らない**。

3. **台帳を作る** — `pd/ledger.json` に `{}` を書く。このファイルの有無が「pd を使うプロジェクトか」の目印になり、無いと hook が動かない

4. **`.gitignore`** — 無ければ作る。あれば次の行が無い場合だけ追記する

```
.local/
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
          ref: v1.0.0
          path: .pd-plugin
      - name: 規約を検証する
        run: python3 .pd-plugin/scripts/validate.py
        env:
          PD_PROJECT_DIR: ${{ github.workspace }}
```

6. **CLAUDE.md** — 無ければ作り、あれば「pd の規約」節を追記する（既にあれば触らない）。内容は次を含める

- 判定者は1つ。`/pd-validate` が唯一の判定者で、人の解釈で合否を決めない
- `products/` は上書き、`analyses/` `voices/` `simulations/` は追記のみ
- Evidence には `Fact` / `Interpretation` / `Hypothesis` / `Unknown` のいずれかを付ける
- 元データ・個人情報を置かない。`voices/` は匿名化してから記録する
- 索引ファイルを作らない
- 過去の Note を修正しない。認識が変わったら新しい Note を追加する

7. **最初の Context** — 対象プロダクトが分かっていれば、plugin の `skills/pd/products/_template.md` を Schema として `products/{product-name}.md` を作る。分からなければ作らず、`/pd` の初回実行時に作ると伝える

8. **検証** — `/pd-validate` を実行し、違反が出ないことを確認してから完了を報告する

## 報告

作ったものと、作らなかったもの（既にあったため）を分けて伝える。最後に「`/pd {プロダクト名}` で分析を始められる」ことを1行で示す。
