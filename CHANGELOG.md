# 変更履歴

pd plugin の版ごとの変更。**判定（`validate.py` のルール）が変わった版は、更新すると今まで通っていたファイルが落ちることがある。** 更新前にここを読む。

形式は [Keep a Changelog](https://keepachangelog.com/ja/1.1.0/)、版番号は [セマンティックバージョニング](https://semver.org/lang/ja/)。

- **MAJOR** — 既存の分析データを書き換えないと通らなくなる変更
- **MINOR** — 判定・Skill・コマンドの追加。既存データはそのまま通る
- **PATCH** — 文言修正・不具合修正

## [2.0.0] — 2026-08-13

**UI/UX の作業を pd に統合した。**これまで UI/UX の規律（層の判定・顧客ボイス台帳・デザインレビュー・アクセシビリティ検算）は各プロジェクトが `uiux/` のような独自ディレクトリで持っていた。pd と併用すると**同じ事実を二箇所に書く**ことになり、必ず片方が古くなる。plugin を入れるだけで UI/UX の改善まで回せるようにした。

### 破壊的変更

- **ボイスの書式を全面的に変えた。** 1ファイル = 1機会（面談単位）から **1ファイル = 1声**（論点単位）へ。

  ```
  旧: pd/voices/{product}/{年}/YYYYMMDD-{取得経路}.md   frontmatter 4キー
  新: pd/voices/{product}/{年}/VOICE-NNN-{slug}.md      frontmatter 12キー必須
  ```

  変えた理由は**引き当て**。UI を直すときに必要なのは「その画面について誰が何と言ったか」で、機会単位でまとめると `screen` で引けない。**引けない台帳は無いのと同じ。**

  ⚠️ **既存の voices は通らなくなる。**移行するか、取り直す。新しい書式は `skills/pd/uiux/voice-schema.md`。

- **`voices.mjs index` を廃止した。**索引ファイルは更新漏れで実態と乖離する（pd の既存規約）。一覧は `query` / `stats` で取る。

### 追加

- **UI/UX スキル10種** — `ux-layer-triage`（層の判定。UI の話が出たら最初に使う）/ `user-voice-ledger` / `user-story-writer` / `object-model-reviewer` / `a11y-contrast-guard` / `ux-design-review` / `ux-validation-planner` / `ux-measurement` / `ux-decision-record` / `ux-update-cascade`

- **ボイス台帳 CLI** — `scripts/voices.mjs`。依存パッケージ0（Node 標準モジュールのみ）。

  ```
  node "${CLAUDE_PLUGIN_ROOT}/scripts/voices.mjs" query --screen <画面名>
  ```

  **UI を作る・直す前に必ず実行する。**0件は「問題が無い」ではなく「記録されていない」。

- **置き場所を5つ追加** — `pd/specs/`（層ごとの現在値。上書き）/ `pd/decisions/`（UXDR）/ `pd/validations/`（VP）/ `pd/measurements/`（MP）/ `pd/reviews/`（DR）。後ろ4つは**追記のみ**。そのとき何を決めたかを後から書き換えると、判断の経緯が消えるため。

- **判定の追加** — UXDR に「決めなかったこと」（何が分かれば決まるか／いつまでに／誰が の3列）と「影響範囲の変わらなかったもの」を必須にした。作業仮説には**観測可能な閾値を持つ棄却条件**を必須にした。レビュー結果には根拠ボイスか「デザイナー起案」の明記を必須にした。

- **規律とテンプレート** — `skills/pd/uiux/rules/`（共通言語・層の規律・決定規則・証拠規則・アクセシビリティ）、`skills/pd/uiux/templates/`（画面仕様・ユーザーストーリー・UXDR・検証計画）、`glossary.md`。

### 設計上の注意

pd（問題 → 原因 → 仮説 → 検証 → 決定）と UI/UX の5段階（戦略 → 要件 → 構造 → 骨格 → 表層）は**直交する**。前者は推論の流れ、後者は抽象度の階層。同じ事実を両方に書かないため、**層ごとの現在値は `pd/specs/`、推論の履歴は `pd/analyses/`** と置き場所で分けている。

## [1.4.0] — 2026-08-13

### 変更

- **プロジェクト側の置き場所を `pd/` 配下にまとめた。** `products/` `analyses/` `voices/` `simulations/` `.local/` が root 直下に散っていたため、**やめたいときにどれが pd のものか判別できなかった**。今後 `/pd:pd-init` は `pd/` の中だけに作る（`pd/products/` `pd/analyses/` …）。`pd/` の外に出るのは `CLAUDE.md` と `.github/workflows/validate.yml` の2つだけ

  **既に使っているプロジェクトは、そのままで通る。移動は不要。** 検証器が root 直下の旧レイアウトも読み続ける。移したい場合の手順は README の「置き場所を移す」にある。**移しても台帳の承認は要らない**（記録のキーを根からの相対パスにしたため）

  ⚠️ 新旧を混在させないこと。`pd/analyses/` と `analyses/` が両方あると、`pd/` 側だけが検証対象になり、root 直下は素通りする

- `/pd:pd-init` が `.gitignore` に書く行が `.local/` から `pd/.local/` になった。旧レイアウトのプロジェクトで書き換える必要は無い

### 追加

- **`/pd:pd-uninstall`** — プロジェクトに作ったものを一覧・削除する。plugin のアンインストール（`/plugin uninstall`）はプロジェクト側のファイルに触れないため、片付けはこのコマンドが受け持つ

  ```
  /pd:pd-uninstall                一覧表示のみ（何も削除しない）
  /pd:pd-uninstall --keep-data    仕組みだけ消す。分析結果は残す
  /pd:pd-uninstall --purge        分析結果ごと全部消す
  ```

  **plugin より先に実行する**（plugin を外すとこのコマンドも消える）。`CLAUDE.md` / `.gitignore` / CI は pd が足した行・節だけを消し、ファイルごとは削除しない

- `validate.py` の判定: `commands/pd-uninstall.md` が配布物に含まれていること
- `selftest.sh` に旧レイアウトの検証を追加（root 直下でも通ること・hook が動くこと）。61 → 63 件

## [1.3.0] — 2026-08-13

### 追加

- `scripts/release.sh` — 版を上げて配る手順を1コマンドに畳んだ。**未コミットのままタグを打つとタグが古い内容を指す**事故が3回続いたため、手順ではなく仕組みで止める。作業ツリーが汚れていれば中止し、版の書き換え（`plugin.json` / `marketplace.json` / `pd-init` の `ref`）と検証を済ませてからコミット・タグ・push まで行う
- `validate.py` の判定: `scripts/release.sh` が配布物に含まれていること

## [1.2.0] — 2026-08-13

### 修正

- **文書のコマンド名が誤っていた。** 正しくは `/pd:pd` / `/pd:pd-init` / `/pd:pd-validate`。plugin のスキルは Claude Code が必ず「plugin名:スキル名」に名前空間化するため、**文書どおりに `/pd-init` と打った利用者は「コマンドが無い」で終わっていた**
- `validate.py` の判定を追加: 文書に名前空間の無いコマンド名が書かれていないこと
- **`/pd:pd-init` が生成する CI の `ref` が `v1.0.0` のままだった。** 新しいプロジェクトが初期状態から旧版の判定器で CI を回していた。あわせて `ref` が現在の版と一致することを `validate.py` の判定に追加

### 変更

- **hook を OS 非依存にした。** `hooks.json` からシェル構文（`case` / `read` / `printf`）と `jq` を排除し、`scripts/hook.py` を呼ぶだけにした。**Windows では sh も jq も無く、hook が丸ごと動かなかった。** 依存は `python3` のみ（`validate.py` が既に要求している）

### 追加

- `scripts/hook.py` — hook の入口。動くべき場面の判定と出力の整形だけを行う。**判定は書かない**（判定者は `validate.py` のまま）
- `validate.py` の判定: `hooks.json` にシェル依存の記述が混ざっていないこと、`hook.py` に目印（`pd/ledger.json`）と blueprint 同期の促しが残っていること
- `selftest.sh` に hook の**挙動**テストを追加（形が揃っていても止められなければ意味がないため）。50 → 58 件

## [1.1.0] — 2026-08-13

### 追加

- `CHANGELOG.md`（このファイル）。版ごとの変更を追えるようにした
- `validate.py` の判定: `CHANGELOG.md` が存在し、`plugin.json` の現在の版が記載されていること。**版を上げて履歴を書き忘れると落ちる**

### 変更

- `README.md` を書き直した。「誰のためのものか」「更新方法」を追加。**更新は自動では届かない**（Claude Code はサードパーティの配布元を既定で自動更新しない）点を明記

## [1.0.0] — 2026-08-12

### 追加

- Product Discovery Skill（`/pd`）を Claude Code plugin として配布開始
- `/pd-init` — 利用プロジェクト側の置き場所・台帳・CI を作る
- `/pd-validate` — 規約違反を手動で確認する
- `validate.py` — 規約の唯一の判定者。置き場所・命名・必須項目・匿名化・元データの混入・過去記録の書き換えを機械的に判定する
- `selftest.sh` — 検証器が本当に違反を検出するかを確かめる自己テスト
- hook（PostToolUse / Stop / SessionStart）— 編集の時点で違反を止め、セッションの開始と終了に残存を通知する
- `pd-skill-blueprint.md` — Skill を別プロジェクトで再構築するための指示書
