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
4. **`.github/workflows/validate.yml` の `ref` が移動タグ（`v1`）になっているかを見る。**

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/validate.py"
   ```

   `ref: v1` なら**何も出ない。以後この作業は要らない** — 1.x の最新に自動で追従する。

   版を焼き込んでいるプロジェクト（`ref: v1.8.0` など）では警告が出る。`Edit` で `ref: v1` に直し、もう一度 `validate.py` を実行して消えたことを確かめる。**一度直せば終わり。**

   ここを人の記憶に委ねると必ず忘れる（実際に v1.0.1 のまま v1.3.0 まで放置された）。忘れれば手元と CI で違う判定器が動く。**忘れられる作業にしたのが移動タグ。**

5. **`CLAUDE.md` の規約が、今の版の推奨と食い違っていないかを見る。**

   推奨規約の**唯一の出どころは `${CLAUDE_PLUGIN_ROOT}/commands/init.md` の step 6 の一覧**。これを `Read` で読み、このプロジェクトの `CLAUDE.md` の「pd の規約」節と突き合わせる。

   **一覧をこのファイルに写さない。** 写した瞬間、どちらかが古くなる（`/pd:init` が規約を1行足しても、こちらは気づけない）。

   - **意味が欠けている項目だけ**を差分として列挙する。言い回しが違うだけのものは挙げない
   - **黙って書き換えない。** 足すかどうかは利用者が決める。`CLAUDE.md` は pd より前から存在しうるファイルで、`/pd:init` も既存の節には触らない設計になっている
   - 「pd の規約」節そのものが無いプロジェクトでは、節ごと提案する
   - 差分が無ければ**何も言わない**。毎回同じ確認結果を報告すると、読まれなくなる

   **`/pd:init` は既存の節を上書きしないので、規約の更新は初期化済みのプロジェクトには永久に届かない。** ここで差分を見せるのが、届く唯一の経路になる。

## うまくいかないとき

| 症状 | 原因 | 対応 |
|---|---|---|
| `claude: command not found` | CLI の無い環境（デスクトップアプリなど） | `/plugin marketplace update pd-plugin` → `/plugin update pd@pd-plugin` を順に実行してもらう |
| 版が変わらない | 配布元にまだ新しいタグが無い | 変更履歴を見て、出ている版を確認する |
| 更新後も古い挙動 | セッションに未反映 | `/reload-plugins`（警告が出たら `/reload-plugins --force`） |

分析データ（`pd/` 配下）は更新で消えない。入れ替わるのは plugin 側だけ。
