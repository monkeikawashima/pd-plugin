---
name: user-voice-ledger
description: 利用者の生の声（ペイン・要望・否定的評価・効いている点・使い方の質問）を逐語のまま台帳に記録し、UI を作る/直すときに引き当てるスキル。「ユーザーがこう言っていた」「クレームが来た」「レビューにこう書かれていた」「ヒアリングでこんな話が出た」「問い合わせが来た」と言われたときは必ず記録に使うこと。逆に、UI を新規作成・修正・改善する前には必ず引き当てに使い、対象画面の一次情報を確認してから改善案を出すこと。逐語の編集・要約はせず、重複は統合し、request と pain を取り違えないよう管理する。層の判定・要件化・UI 評価そのものは行わない。
---

# user-voice-ledger — 顧客ボイスの記録と引き当て

**台帳を唯一所有するスキル。** 書式・採番・統合・検索はすべてここが持つ。

## 役割分界（重複させない）

| このスキルがやること | やらないこと（担当スキル） |
|---|---|
| 逐語の記録・採番・重複統合・匿名化 | 層の判定（`ux-layer-triage`） |
| 引き当て（検索）と「一次情報なし」の宣言 | 要件化（`user-story-writer`） |
| `status` の更新 | UI の評価（`ux-design-review`） |
| — | 系統ごとの集計と人物像（`user-persona-builder`） |
| — | 声を取りに行く計画（`ux-research-planner`） |
| — | 検証の実施設計（`ux-validation-planner`） |

## 最初に読む

**書く前に必ず `${CLAUDE_PLUGIN_ROOT}/skills/analyze/uiux/voice-schema.md` を読む。**
必須キー・enum・`speaker_role` の形式は CLI と `/pd:validate` が機械検査する。

**役割（`speaker_role`）は plugin が決めない。** そのプロダクトの役割名を使い、
固まったら `pd/voices/taxonomy.json` に列挙する（列挙した時点で表記ゆれが弾かれる）。

---

## モードA｜記録する（声が入ってきたとき）

### 1. 逐語をそのまま確保する

**編集・要約・敬語化の禁止。** 話し言葉のまま、言い淀みも含めて残す。
外国語の発言は**原文のまま**記録する（訳は `## 解釈` に書く）。

逐語が取れていない場合: `## 逐語` に `> 逐語なし` と書き、**`severity` を一段下げる**。

### 2. `type` を判定する（最重要）

| type | 定義 |
|---|---|
| `pain` | できていない・困っている**事実** |
| `request` | 話者が出した**解決手段の提案** |
| `negative` | 否定的な**評価・感情** |
| `positive` | 効いている点（**消さないために記録する**） |
| `question` | 使い方が分からない＝**理解の失敗** |

> ⚠️ **`request` を `pain` にしない。** 手段を要件に昇格させると上流の判断が飛ぶ。
> `request` は対応する `pain` を特定してから扱う。無ければ本文に「**対応するペイン未特定**」と書く。

### 3. 重複を確認して統合する

```bash
node "${CLAUDE_PLUGIN_ROOT}/scripts/voices.mjs" query --screen <画面名>
node "${CLAUDE_PLUGIN_ROOT}/scripts/voices.mjs" query --type <type>
```

同一趣旨があれば**新規作成せず `frequency` を増やす**。逐語が異なるなら、両方を `## 逐語` に並べる。

### 4. 匿名化する

実名・組織名・電話番号・メールアドレスを匿名化ID（`U-01` / `O-03` など）に置換する。

### 5. 作成して検査する

```bash
node "${CLAUDE_PLUGIN_ROOT}/scripts/voices.mjs" new --product <p> --type <t> --source <s> \
  --speaker_role <r> --speaker_id <id> --captured_at <YYYY-MM-DD> --captured_by <who> --slug <slug>
# 逐語を貼る
node "${CLAUDE_PLUGIN_ROOT}/scripts/voices.mjs" validate
```

> 索引を作るコマンドは無い（v0.6.0 で廃止）。**一覧は `query` / `stats` で取る。**
> 索引ファイルは更新漏れで実態と乖離する。

`captured_at` は**発言された日**（受領日ではない）。

### 6. 層を判定して渡す

`ux-layer-triage` へ。判定できるまで `layer: 未判定` のままでよい。

---

## モードB｜引き当てる（UI を作る／直すとき）

**改善案を出す前に必ず実行する。**

```bash
node "${CLAUDE_PLUGIN_ROOT}/scripts/voices.mjs" query --screen <画面名>
node "${CLAUDE_PLUGIN_ROOT}/scripts/voices.mjs" query --screen <画面名> --type pain --status 未検証
node "${CLAUDE_PLUGIN_ROOT}/scripts/voices.mjs" query --tag <タグ>       # 例: locale:en
node "${CLAUDE_PLUGIN_ROOT}/scripts/voices.mjs" query --principle <n>
```

| 結果 | 扱い |
|---|---|
| ヒットあり | `pain` / `negative` が解消されるか、**`positive` を壊していないか**を1件ずつ突き合わせる |
| **0件** | 「**一次情報なし**」と明示し、改善案には「**デザイナー起案**」と書く |

> `positive` を必ず見ること。**効いているものを壊す改善**が最も見つけにくい事故。

---

## `status` の更新ルール

| status | 付けてよいとき |
|---|---|
| `未検証` | 記録した直後 |
| `検証済み` | 検証（`pd/validations/`）で事実確認した |
| `対応中` | 対応する実装・改善が進行中 |
| **`解消`** | **再検証で再発しないことを確認したときだけ。実装しただけでは付けない** |
| `却下` | 対応しないと決めた（UXDR に理由を残す） |

## 出力形式

```
■ モード: 記録 / 引き当て
■ 対象: <画面名 / 声の出所>
■ 記録した／引き当てたボイス:
   VOICE-xxx  <type>  <severity>  freq=<n>  <status>
   > <逐語の1行目>
■ 一次情報の有無: あり（n件） / なし
■ 未解消の pain / negative: <件数と ID>
■ 壊してはいけない positive: <ID と要点>
■ 次のアクション: <スキル名>
```

## 禁止

- 逐語の書き換え・要約・敬語化・翻訳での置換
- 解釈を `## 逐語` に混ぜる（解釈は `## 解釈` に `[推測]` 付きで）
- 実名・組織名・電話番号の記載
- 出所（`source`）のない声の追加
- 検証していないのに `status: 解消`
- 引き当てずに改善案を出す（出す場合は「デザイナー起案」と明記）
