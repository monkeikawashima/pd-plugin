# 変更履歴

pd plugin の版ごとの変更。**判定（`validate.py` のルール）が変わった版は、更新すると今まで通っていたファイルが落ちることがある。** 更新前にここを読む。

形式は [Keep a Changelog](https://keepachangelog.com/ja/1.1.0/)、版番号は [セマンティックバージョニング](https://semver.org/lang/ja/)。

- **MAJOR** — 既存の分析データを書き換えないと通らなくなる変更
- **MINOR** — 判定・Skill・コマンドの追加。既存データはそのまま通る
- **PATCH** — 文言修正・不具合修正

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
