---
description: pd plugin を最新版に更新する（配布元の取り直しと更新をまとめて行う）
allowed-tools: Bash(claude plugin *), Bash(python3 *), Read, Edit
---

# pd-update

**まず、起動時の更新確認が止められていないかを見る。**

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/update_check.py" status
```

何か出力されたら、そのまま利用者に伝えてから先へ進む。**止めていること自体は妨げない** — 手動更新はできる。黙って進めると、案内が出ない理由が分からないままになる。

**配布元の一覧を取り直してから更新する。** この順序でないと更新されない。

`claude plugin update` は**手元にあるカタログしか見ない**。取り直さずに実行すると、新しい版が出ていても「already at the latest version」と言われる。手元のカタログが古い版を指していれば、**古い版へ戻してしまう**（実測: カタログが v1.0.0 のとき、v1.0.1 から v1.0.0 に「更新」された）。

```bash
claude plugin marketplace update pd-plugin && claude plugin update pd@pd-plugin
```

## 実行後にやること

1. 出力の版番号を利用者に伝える（`updated from X to Y` / `already at the latest version`）
2. 版が上がっていたら、**変更履歴を必ず案内する**
   https://github.com/monkeikawashima/pd-plugin/blob/main/CHANGELOG.md

   **判定のルールが変わった版では、昨日まで通っていたファイルが落ちる。** 更新は無条件に良いことではない。何が変わったかを読む機会を必ず渡す。
3. 今のセッションに反映するため `/reload-plugins` を実行するよう伝える（実行するのは利用者）
4. **`.github/workflows/validate.yml` の `ref` を、その場で新しい版に書き換える。** 伝えるだけにしない

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/validate.py"
   ```

   `CI が固定している plugin の版が古い` と出たら、`Edit` でその `ref:` を新しい版に直し、もう一度 `validate.py` を実行して消えたことを確かめる。**警告が消えるまでが更新。**

   ここを人の記憶に委ねると必ず忘れる（実際に v1.0.1 のまま v1.3.0 まで放置された）。忘れれば手元と CI で違う判定器が動く。

## うまくいかないとき

| 症状 | 原因 | 対応 |
|---|---|---|
| `claude: command not found` | CLI の無い環境（デスクトップアプリなど） | `/plugin marketplace update pd-plugin` → `/plugin update pd@pd-plugin` を順に実行してもらう |
| 版が変わらない | 配布元にまだ新しいタグが無い | 変更履歴を見て、出ている版を確認する |
| 更新後も古い挙動 | セッションに未反映 | `/reload-plugins`（警告が出たら `/reload-plugins --force`） |

分析データ（`pd/` 配下）は更新で消えない。入れ替わるのは plugin 側だけ。
