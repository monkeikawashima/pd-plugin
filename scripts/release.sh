#!/bin/sh
# 版を上げて配る。3つのコマンドを1つに畳み、順序を間違えられなくする。
#
#     sh scripts/release.sh                   CHANGELOG の最新の見出しの版を配る
#     sh scripts/release.sh 0.4.0             版を直接指定する
#     sh scripts/release.sh --no-push         手元で止める（確認用）
#
# 未コミットのままタグを打つと、タグが古い内容を指す。これを3回続けたため、
# 手順ではなく仕組みで止める。CHANGELOG は**実行前に**手で書いておくこと
# （何が変わったかは機械には書けない）。
#
# 開発者向けの道具。利用者の環境では動かない（hook とは無関係）。

set -e
ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"

die() { printf '\n✗ %s\n' "$1" >&2; exit 1; }
step() { printf '\n▶ %s\n' "$1"; }

# 版を省略できる。CHANGELOG の一番新しい見出しを採る。
# どの版にするかは CHANGELOG を書いた時点で人が決めている。
# 同じ判断を2回させると、片方だけ間違える。
VERSION=$1
NOPUSH=$2
case "$VERSION" in
    --no-push) NOPUSH=--no-push; VERSION="" ;;
esac

if [ -z "$VERSION" ]; then
    VERSION=$(python3 - <<'PY'
import pathlib, re
text = pathlib.Path("CHANGELOG.md").read_text(encoding="utf-8")
found = re.findall(r"^## \[(\d+\.\d+\.\d+)\]", text, re.M)
print(max(found, key=lambda v: tuple(int(n) for n in v.split("."))) if found else "")
PY
)
    [ -n "$VERSION" ] || die "CHANGELOG.md に「## [x.y.z]」の見出しが無い。
   配る版を決められない。先に CHANGELOG を書くか、版を直接渡す
   （例: sh scripts/release.sh 1.2.0）"
    printf 'CHANGELOG の最新の見出しから版を決めた: %s\n' "$VERSION"
fi

case "$VERSION" in
    [0-9]*.[0-9]*.[0-9]*) ;;
    *) die "使い方: sh scripts/release.sh [版] [--no-push]
   版を省くと CHANGELOG の最新の見出しを使う" ;;
esac

CURRENT=$(python3 -c "import json;print(json.load(open('.claude-plugin/plugin.json'))['version'])")
# 変数の直後に全角文字を置かない（変数名の一部として解釈され、値が消える）
[ "$VERSION" != "$CURRENT" ] || die "版が現在と同じ（${CURRENT}）。上げる版を指定する"

# ここが本題。汚れた作業ツリーでタグを打つと、タグが古い内容を指す。
if [ -n "$(git status --porcelain)" ]; then
    git status --short
    die "未コミットの変更がある。先にコミットするか元に戻す
   （版の書き換えはこのスクリプトが行うので、手で変更しない）"
fi

git rev-parse -q --verify "refs/tags/v$VERSION" >/dev/null 2>&1 \
    && die "タグ v$VERSION が既にある。付け替えるなら手動で行う"

grep -q "^## \[$VERSION\]" CHANGELOG.md \
    || die "CHANGELOG.md に「## [$VERSION]」の項目が無い。
   何が変わったかは機械には書けない。実行前に手で書く
   （判定が変わった版は、利用者側で今まで通っていたファイルが落ちる）"

printf '版 %s → %s\n' "$CURRENT" "$VERSION"

# ------------------------------------------------------------------ 書き換え

step "版を書き換える（plugin.json / marketplace.json / commands/init.md の ref）"
python3 - "$VERSION" <<'PY'
import json, pathlib, re, sys
version = sys.argv[1]

p = pathlib.Path(".claude-plugin/plugin.json")
d = json.loads(p.read_text(encoding="utf-8"))
d["version"] = version
p.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

p = pathlib.Path(".claude-plugin/marketplace.json")
d = json.loads(p.read_text(encoding="utf-8"))
for entry in d.get("plugins", []):
    entry["version"] = version
p.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

# 利用プロジェクトの CI が checkout する版。古いまま配ると、新しく始めた
# プロジェクトが初期状態から旧版の判定器で CI を回すことになる。
p = pathlib.Path("commands/init.md")
p.write_text(re.sub(r"ref:\s*v[\d.]+", f"ref: v{version}", p.read_text(encoding="utf-8")),
             encoding="utf-8")
PY
git --no-pager diff --stat

# ------------------------------------------------------------------ 検証

step "配布物を検証する（validate.py）"
python3 scripts/validate.py || { git checkout -- .; die "検証に落ちた。書き換えは元に戻した"; }

step "スキーマの三者一致を確かめる（schema-sync.py）"
python3 scripts/schema-sync.py || { git checkout -- .; die "スキーマが一致していない。書き換えは元に戻した"; }

step "検証器を検証する（selftest.sh）"
sh scripts/selftest.sh || { git checkout -- .; die "自己テストに落ちた。書き換えは元に戻した"; }

# ------------------------------------------------------------------ 配る

step "コミットしてタグを打つ"
git add -A
git commit -q -m "v$VERSION"
git tag "v$VERSION"
git --no-pager log --oneline -1

if [ "$NOPUSH" = "--no-push" ]; then
    printf '\n手元で止めた（--no-push）。配るには次を実行する:\n'
    printf '    git push && git push origin v%s\n' "$VERSION"
    exit 0
fi

step "push する"
git push
git push origin "v$VERSION"

# ------------------------------------------------------------------ 知らせる
#
# Release を作ると、その本文が起動時の更新通知に出る（update_check.py）。
# 無くてもタグへフォールバックするので、ここで失敗しても配布は完了している。
# `set -e` に巻き込まれないよう、失敗は警告に留める。
step "GitHub Release を作る"
NOTES=$(mktemp)
trap 'rm -f "$NOTES"' EXIT
if python3 scripts/changelog_section.py "$VERSION" > "$NOTES" 2>/dev/null \
   && gh release create "v$VERSION" --title "v$VERSION" --notes-file "$NOTES" 2>/dev/null; then
    printf '  作成した\n'
else
    printf '⚠ Release を作れなかった（gh が無い／認証切れ／既にある）。\n'
    printf '  配布は完了している。通知はタグから出るので、作らなくても壊れない。\n'
    printf '  手で作る場合: python3 scripts/changelog_section.py %s | gh release create v%s --title v%s --notes-file -\n' \
        "$VERSION" "$VERSION" "$VERSION"
fi

printf '\n✓ v%s を配った\n' "$VERSION"
printf '  利用者に届くのは /plugin update を実行した人だけ（自動更新は既定で無効）\n'
