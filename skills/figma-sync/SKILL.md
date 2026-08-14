---
name: figma-sync
description: pd の仕様（トークン台帳・画面仕様）と Figma のファイルを突き合わせ、ズレを一覧にして、どちらを正とするかを決めてから片方へ反映するスキル。「Figma と実装がズレている」「Figma に反映して」「デザインデータを最新にして」「Figma の色をトークンに取り込みたい」と言われたとき、画面仕様を書いたあとデザインを起こす前、トークンを変更したときに使うこと。同期の方向を決めずに書き込まない。書き込んだら必ずスクリーンショットで確認する。色や配置の良し悪しの判断・画面仕様の起草・トークンの値の決定は行わない。
---

# figma-sync — 仕様と Figma の突き合わせ

**Figma と仕様がズレたとき、危ないのは「どちらが正か決めずに上書きすること」。**
片方向に流すだけの同期は、決定を消す。このスキルは**ズレを見せて、方向を決めさせてから**動かす。

## 実行前に必ず読むもの（省略不可）

| いつ | 何を |
|---|---|
| **Figma に書き込む前**（毎回） | `figma:figma-use` スキル |
| FigJam に書き込む前 | `figma:figma-use-figjam` |
| ページ全体を起こす場合 | `figma:figma-generate-design` |

**`use_figma` を直接呼ばない。** 先に `figma-use` を読み込む。これは利用者の global ルールでもあり、省くと落ちにくい失敗（フォント未ロード・Auto Layout 破壊）が出る。

## 役割分界（重複させない）

| このスキルがやること | やらないこと（担当スキル） |
|---|---|
| 仕様と Figma のズレの検出 | トークンの値の決定（`design-token-keeper` / DESIGN） |
| 同期の方向の確定 | 画面仕様の起草（`ux-screen-spec-writer`） |
| 反映と、反映後の確認 | UI の良し悪しの評価（`ux-design-review`） |
| 取り込めなかったものの記録 | コントラストの検算（`a11y-contrast-guard`） |
| — | 決定の記録（`ux-decision-record`） |

## 最初に読む

| ファイル | 何のために |
|---|---|
| `pd/specs/05-surface/design-tokens.md` | トークン台帳。**定義の真実の源はここに書いてある** |
| `pd/specs/04-skeleton/screens/` | 画面仕様（5状態を含む） |
| `pd/specs/01-strategy/glossary.md` | 画面に出す呼称 |

## 手順

### 1. 方向を決める（先に。例外なし）

| 方向 | 使う場面 | 注意 |
|---|---|---|
| **仕様 → Figma** | 仕様を先に書いた。デザインを起こす | Figma 側の手直しを消す可能性がある |
| **Figma → 仕様** | Figma で先に決まった。台帳へ取り込む | 台帳の承認済みの値を壊す可能性がある |
| **突き合わせのみ** | どちらが正か分からない | **既定はこれ。** 書き込まない |

**分からないときは「突き合わせのみ」で止める。** ズレの一覧を出して、方向を聞く。

### 2. ズレを出す

```
■ 対象: <Figma ファイル / ページ>   台帳: pd/specs/05-surface/design-tokens.md

┌ トークン
│ color/text/primary     台帳 #1A1A1A   Figma #212121   ← 値が違う
│ space/md               台帳 16        Figma 16        ✓
│ color/accent/warn      台帳 有        Figma 無し      ← Figma に variable が無い
│ color/brand/old        台帳 無し      Figma 有        ← 台帳にない（誰が足したか不明）
└

┌ 画面
│ 検索結果（空振り）      仕様 有       Figma 無し      ← 空状態のアートボードが無い
│ 検索結果（エラー）      仕様 有       Figma 無し
└
```

**「Figma に無い状態」を必ず見る。** 空振り・エラー・処理中は、Figma 側で最も抜けやすく、抜けたまま実装へ渡ると沈黙する画面になる。

### 3. 反映する

守る規則（利用者の global ルールと同じ。破らない）:

| 項目 | 規則 |
|---|---|
| 色・数値・文字 | 生の値を直書きせず、**variable / style を束縛**する。無い variable を勝手に作らない |
| モード | **Light mode で作る。** 全体を反転させた dark 版を増やさない |
| フォント | `characters` を触る前に `loadFontAsync`。`Inter` は `"Semi Bold"`（スペース有り） |
| Auto Layout | 既存の `layoutMode` を理由なく `NONE` にしない。spacer の矩形を挿さない |
| Instance | `detachInstance()` を使わない。`setProperties()` / overrides で済ませる |
| 画像 | プレースホルダー禁止。`createImage` / `createNodeFromSvg` で**実画像**を置く |
| ページ切替 | `figma.currentPage = ...` ではなく `await figma.setCurrentPageAsync(...)` |

**台帳に無い値を Figma に書かない。** 必要なら先に `design-token-keeper` へ戻して台帳に載せる。

### 4. 確認する（省略不可）

書き込みスクリプトの最後で、作った／変えた最上位ノードの `id` を返す。`get_screenshot` で撮り、**期待どおりか目で確かめてから**報告する。

崩れていたら直して撮り直す。**「書き込みは成功した」を完了の根拠にしない。**

## 出力

```
■ 方向: 仕様 → Figma   対象: <ファイル / ページ>

■ 反映した
  - color/text/primary  #212121 → #1A1A1A（variable 束縛）
  - 検索結果（空振り）のアートボードを追加

■ 反映しなかった
  - color/brand/old: 台帳に無い。誰が何のために足したか不明 → 台帳側で扱いを決めるまで触らない

■ 確認
  - スクリーンショット取得済み。空振り画面の文言が仕様どおりであることを確認

■ 台帳へ戻すもの
  - Figma にのみ存在するトークン 1 件（design-token-keeper へ）
```

## やってはいけないこと

- 方向を決めずに書き込む
- `figma-use` スキルを読まずに `use_figma` を呼ぶ
- 台帳に無い色・数値を Figma に足す／Figma にあるものを黙って台帳へ入れる
- 生の hex / px を直書きする（variable を束縛する）
- dark mode 版を増やす
- プレースホルダー（グレーの矩形・ダミー塗り）で画像を代用する
- Auto Layout を解除する。Instance を detach する
- スクリーンショットを撮らずに完了と報告する
- Figma 上の見た目から UI の良し悪しを判断する（`ux-design-review` の担当）
