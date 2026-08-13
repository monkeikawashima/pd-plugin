#!/bin/sh
# 版を上げて配る。3つのコマンドを1つに畳み、順序を間違えられなくする。
#
#     sh scripts/release.sh 1.3.0             コミット → タグ → push まで
#     sh scripts/release.sh 1.3.0 --no-push   手元で止める（確認用）
#
# 未コミットのままタグを打つと、タグが古い内容を指す。これを3回続けたため、
# 手順ではなく仕組みで止める。CHANGELOG は**実行前に**手で書いておくこと
# （何が変わったかは機械には書けない）。
#
# 開発者向けの道具。利用者の環境では動かない（hook とは無関係）。

set -e
ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"

VERSION=$1
NOPUSH=$2

die() { printf '\n✗ %s\n' "$1" >&2; exit 1; }
step() { printf '\n▶ %s\n' "$1"; }

# ------------------------------------------------------------------ 事前確認

case "$VERSION" in
    [0-9]*.[0-9]*.[0-9]*) ;;
    *) die "使い方: sh scripts/release.sh <版> [--no-push]   例) sh scripts/release.sh 1.3.0" ;;
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

step "版を書き換える（plugin.json / marketplace.json / pd-init の ref）"
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
p = pathlib.Path("commands/pd-init.md")
p.write_text(re.sub(r"ref:\s*v[\d.]+", f"ref: v{version}", p.read_text(encoding="utf-8")),
             encoding="utf-8")
PY
git --no-pager diff --stat

# ------------------------------------------------------------------ 検証

step "配布物を検証する（validate.py）"
python3 scripts/validate.py || { git checkout -- .; die "検証に落ちた。書き換えは元に戻した"; }

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

printf '\n✓ v%s を配った\n' "$VERSION"
printf '  利用者に届くのは /plugin update を実行した人だけ（自動更新は既定で無効）\n'
