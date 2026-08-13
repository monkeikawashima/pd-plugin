---
description: pd の規約を検証する（--accept で過去の記録の変更を承認）
argument-hint: "[--accept] [path...]"
allowed-tools: Bash(python3 *)
---

# pd-validate

規約の唯一の判定者を実行する。**人の解釈で合否を決めない。**

```bash
PD_PROJECT_DIR="$CLAUDE_PROJECT_DIR" python3 "$CLAUDE_PLUGIN_ROOT/scripts/validate.py" $ARGUMENTS
```

## 出力の読み方

| 記号 | 意味 | 対応 |
|---|---|---|
| `✗` | 違反。終了コード 1 | 直してから先に進む |
| `⚠` | 警告。止めない | 直すかは作業者の判断 |

## `--accept` の扱い

`--accept` は**過去の記録の変更を承認する**もので、承認は `pd/ledger-log.md` に残る。

- 使ってよいのは、見出しへの言い換えの追記・凡例ブロックの挿入・frontmatter の項目追加といった**表記の統一だけ**
- **判断・数値・Evidence のラベル・結論を変えた場合は承認しない。** 新しい Note を書き、前回との差分として残す

ユーザーが `--accept` を指定した場合でも、変更内容が表記の統一を超えていると分かるときは、実行前にその点を伝える。
