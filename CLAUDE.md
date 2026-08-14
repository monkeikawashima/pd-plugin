# pd-plugin

Product Discovery Skill（`/pd:analyze`）の**配布物**。

```
.claude-plugin/   marketplace / plugin 定義
skills/           analyze（/pd:analyze）と UI/UX の各スキル
hooks/            PostToolUse / Stop / SessionStart
commands/         /pd:init  /pd:validate  /pd:uninstall  /pd:update
scripts/          validate.py（唯一の判定者）/ selftest.sh
DECISIONS.md      設計判断の記録。なぜそう決めたかだけを書く
README.md         人が読む入口
```

**分析データはここに置かない。** Note・Voice・Context は利用プロジェクト側にあり、`/plugin update` で上書きされるこの場所に置くと消える。

---

## 0. 変更したら必ず両方を実行する

```bash
python3 scripts/validate.py     # 配布物が揃っているか
sh scripts/selftest.sh          # 検証器が本当に違反を検出するか
```

**常に成功する検証器は、無いのと同じ。** 判定を追加したら `selftest.sh` にも壊れた例を1つ追加する。緩める場合は理由を `DECISIONS.md` §2 に残す。

`validate.py` は配布物の欠落も見ている（`plugin.json` / `marketplace.json` / `hooks.json` / 各コマンド / CI）。仕組みごと外される穴を塞ぐため。

---

## 1. 判断を変えたら `DECISIONS.md` に理由を残す（必須・確認不要）

次の3つが起きたときだけ、**同じ作業内で** `DECISIONS.md` に追記する。ユーザーへの確認を取らずに行う。

| 起きたこと | 書く場所 |
|---|---|
| 置き場所が分かれうる論点を決めた | §2 の論点表に、決定と理由を1行 |
| 判定を緩めた / 例外を作った | §2 の論点表に、なぜ緩めたか |
| 実際に失敗を踏んで、仕組みで塞いだ | §3 に、何が起きたか |

**それ以外は書かない。** ファイル構成・各スキルの中身・実行手順・受け入れ条件は `DECISIONS.md` に持たせない。

**なぜ:** 実物（`skills/` `scripts/` `commands/`）を見れば分かることを二重に持つと、必ず片方が古くなる。実際に v1.2.0 で UI/UX の22スキルを足したとき、当時の blueprint は `/pd:analyze` 1つ分のまま取り残された。しかも同期表も hook もその3ファイルしか見ていなかったため、規約どおり作業しても埋まらなかった。**実物から復元できないもの（なぜそう決めたか）だけを残す。**

`hooks/hooks.json` の PostToolUse hook が `scripts/validate.py` などの変更を検知して促すが、**判断は作業者に残す**（hook はブロックしない）。実装の整理や typo なら追記は不要。

---

## 2. `framework/` にプロダクト固有情報を書かない

`framework/` は共通の思考方法のみ。特定の KPI 名・プロダクト名・業界固有の指標を書き込まない。固有情報は利用プロジェクトの `products/{product-name}.md` 側で扱う。

例外は `kpi.md` 冒頭の「これらを書かない」という禁止例の列挙のみ。

`framework/` を変更したくなった場合、それは「共通フレームワークに固有事情が漏れている」か「`_template.md` の Schema が足りない」かのどちらか。まず `_template.md` 側を見直す。

**この判定は利用プロジェクト側でしか完全には働かない。** 禁止語は `products/*.md` のファイル名から自動生成しており、plugin 単体には products が無いため照合対象が空になる。plugin だけを見て「通った」と判断しない。

---

## 2.5 プロジェクト側に置くものは `pd/` から出さない

利用プロジェクトに作るものは `pd/` 配下に収める（v0.5.0〜）。**やめるときに「どれが pd のものか」を判別できるようにするため。** 例外は `.github/workflows/validate.yml` と `CLAUDE.md` の2つだけ（置き場所が決まっているため動かせない）。

置き場所を増やすときは `/pd:uninstall` の対象一覧にも足す。**片付けられないものを作らない。**

### 旧レイアウトを読めなくしない

v0.5.0 より前は root 直下だった。`validate.py` の `BASE`（`_base_dir()`）が両方を読む。**この分岐を消すと、既存プロジェクトが更新した瞬間に全ファイル「台帳にあるが存在しない」で落ちる。**

台帳のキーは `BASE` からの相対パス。だから `pd/` へ移しても承認なしで通る。`ROOT` 相対に戻さないこと。`selftest.sh` の「旧レイアウトでも通る」がこれを見ている。

---

## 3. hook は無関係なプロジェクトで動かさない

plugin の hook は、有効化した**全プロジェクト**で走る。pd と無関係なリポジトリで検証器が動くと、毎ターン違反通知が出て使い物にならない。

目印（`$CLAUDE_PROJECT_DIR/pd/ledger.json`）が無ければ何もしないこと。判定は `scripts/hook.py` にあり、消すと `validate.py` が違反にする。

### `hooks.json` にシェルを書かない

`hooks.json` は `python3 scripts/hook.py {event}` を呼ぶだけにする。`jq` や `case` / `read` / `printf` を書くと、**Windows で hook が丸ごと動かない**（sh も jq も無い）。依存は `python3` 1つに寄せる — `validate.py` が既に要求しているため、これ以上増やさない。この判定も `validate.py` が見ている。

`hook.py` に**規約の判定を書かない。** 判定者は `validate.py` 1つ。`hook.py` がやるのは「動くべき場面か」を決めて、結果を hook の出力形式に整えることだけ。

---

## 4. 版を上げるときの手順

判定を追加・変更したら、次の2つだけを行う。

1. `CHANGELOG.md` に新しい版の項目を書く（**判定が変わった版は、利用者側で今まで通っていたファイルが落ちる**。何が変わったかは機械には書けない）
2. 変更をコミットしてから配る

```bash
sh scripts/release.sh 0.4.0             # 版の書き換え → 検証 → コミット → タグ → push
sh scripts/release.sh 0.4.0 --no-push   # 手元で止めて確認する
```

**版を手で書き換えない。** `plugin.json` / `marketplace.json` / `commands/init.md` の `ref` の3箇所を release.sh が揃えて書き換える。手でやると必ずどれかが取り残される。

**未コミットのままタグを打たない。** タグが古い内容を指し、手元と CI で判定が食い違う。release.sh は作業ツリーが汚れていれば中止する（この事故が3回続いたため仕組みで止めている）。

**Claude Code は `plugin.json` の `version` を更新の判定キーにする。** 上げなければ `/plugin update` しても「already at the latest version」で何も起きず、利用者に届かない。

既に稼働している利用プロジェクトがある場合は、その `.github/workflows/validate.yml` の `ref` も上げる。**忘れると、手元（`/plugin update` 済み）と CI（旧タグ）で判定が食い違う。**

### 更新は自動では届かない

サードパーティの marketplace は Claude Code の既定で auto-update が**無効**。利用者が `/plugin` → Marketplaces → **Enable auto-update** を自分で有効にしない限り、版を上げても手元は古いままになる。README の導入手順でこの選択を促している。**「上げたから全員に届いた」と考えない。**
