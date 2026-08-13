# 顧客ボイス台帳 — スキーマ

`pd/voices/{プロダクト}/{年}/VOICE-NNN-<slug>.md` の書式。
**この文書と `scripts/voices.mjs` と `scripts/validate.py` の3つは完全に一致する。**
1つだけ変更しない（人はこの文書を見て書き、検証器がそれを弾く、という事故になる）。

年フォルダは `captured_at`（発言された日）の年。ID はプロダクトをまたいで一意。

---

## ファイル名

```
pd/voices/{プロダクト}/{年}/VOICE-<3桁以上の数字>-<slug>.md
```

`id` と数字部分が一致していること。

---

## frontmatter — 必須キー（12個）

| キー | 値 | 補足 |
|---|---|---|
| `id` | `VOICE-\d{3,}` | ファイル名と一致。重複禁止 |
| `product` | `pd/products/<name>.md` の名前 | フォルダ名と一致 |
| `type` | `pain` / `request` / `negative` / `positive` / `question` | 下表参照。**取り違え厳禁** |
| `source` | `interview` / `in-app-feedback` / `review` / `support-ticket` / `sales-call` / `meeting` / `user-validation` | 取得経路 |
| `speaker_role` | 形式 `^[a-z][a-z0-9-]*$`（例: `end-user` / `operator` / `admin` / `unknown`） | **enum ではない。**下の「役割はプロダクトが決める」を読む |
| `speaker_id` | 匿名化ID（例: `U-01` / `O-03`） | **実名・組織名・電話番号を書かない** |
| `captured_at` | `YYYY-MM-DD` | **発言された日**（受領日ではない） |
| `captured_by` | 記録者 | |
| `layer` | `戦略` / `要件` / `構造` / `骨格` / `表層` / `未判定` | 判定前は `未判定` |
| `severity` | `high` / `medium` / `low` | **逐語が無い声は一段下げる** |
| `frequency` | 1 以上の整数 | 同一趣旨の声は統合してここを増やす |
| `status` | `未検証` / `検証済み` / `対応中` / `解消` / `却下` | |

## frontmatter — 任意キー

| キー | 値 | 補足 |
|---|---|---|
| `object` | 文字列 | `taxonomy.json` の `object` が非空なら、その中の値のみ |
| `phase` | 文字列 | `taxonomy.json` の `phase` が非空なら、その中の値のみ |
| `screen` | 文字列 | **UI 実装時の引き当てキー**。表記を揺らさない |
| `principles` | 整数配列 | 体験の原則の番号 |
| `linked_stories` | 文字列配列 | `US-xx` |
| `linked_uxdr` | 文字列配列 | `UXDR-…` |
| `tags` | 文字列配列 | 分類軸を増やしたくなったらキーではなくここへ（例: `locale:en`） |

> **上記以外のキーは書けない**（validate がエラーにする）。スキーマを勝手に増やさないため。

---

## 役割（`speaker_role`）はプロダクトが決める

役割の呼び名は業種で変わる。ここで固定すると、特定業種の語彙を全利用者に強制することになる。
**plugin は形式だけを縛り、値は決めない。**

```
✅ end-user / operator / manager / admin / unknown
✅ patient / physician / admin        （医療）
✅ learner / instructor / admin       （教育）
✗ Staff        大文字を混ぜない
✗ 店舗スタッフ   日本語で書かない（query の引数になるため）
✗ store staff  空白をハイフンに
```

決めた役割は `pd/voices/taxonomy.json` に列挙する。**列挙した時点で、そこに無い値は弾かれる。**

```json
{
  "speaker_role": ["end-user", "operator", "admin", "unknown"],
  "object": [],
  "phase": []
}
```

列挙しなければ形式チェックだけが働く（導入直後に赤くしないため）。
ただし**列挙するまで表記ゆれは防げない**。役割が固まった時点で埋めること。

---

## `type` の定義（最重要）

| type | 定義 |
|---|---|
| `pain` | 業務・利用の上でできていない、困っている**事実** |
| `request` | 話者が出した**解決手段の提案** |
| `negative` | プロダクト・UI への否定的な**評価・感情** |
| `positive` | 効いている点。**消さないために記録する** |
| `question` | 使い方が分からない＝**理解の失敗** |

> ⚠️ **`request` を `pain` として記録しない。**
> 手段をそのまま要件に昇格させると、上流（本当は何に困っているか）の判断が飛ぶ。
> `request` は対応する `pain` を特定してから扱う。見つからなければ本文に「**対応するペイン未特定**」と書く。

---

## 本文（見出し固定・4節すべて必須）

```markdown
## 逐語

> <話者の言葉をそのまま。編集・要約・敬語化の禁止>

## 文脈

<いつ・どこで・何をしていたときの発言か。一次情報のみ>

## 解釈

<記録者の読み取り。[推測] を必ず付ける>

## 派生

<層の判定 / 起票したストーリー・UXDR / 次のアクション>
```

- **`## 逐語` には `>` で始まる引用行が1つ以上必要**（無いと validate が落ちる）
- 逐語が取れなかった場合は `> 逐語なし` と明記し、**`severity` を一段下げる**

---

## 禁止

- 逐語の書き換え・要約・敬語化
- 解釈を逐語に混ぜる
- 実名・組織名・電話番号・メールアドレスの記載
- 出所（`source`）のない声の追加
- **検証していないのに `status: 解消`**（実装しただけでは付けない。再検証で再発しないと確認したときだけ）

---

## 関連

- 雛形: `${CLAUDE_PLUGIN_ROOT}/skills/analyze/uiux/voice-template.md`（`voices.mjs new` がこれを使う）
- 語彙: `pd/voices/taxonomy.json`（プロジェクト側。`/pd:init` が空で作る）
- 運用: `${CLAUDE_PLUGIN_ROOT}/skills/user-voice-ledger/SKILL.md`
