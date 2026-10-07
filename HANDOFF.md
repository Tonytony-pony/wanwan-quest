# HANDOFF

## 目的
わんわんクエスト（さんすうで犬を育てるブラウザゲーム。`index.html` 1ファイル、GitHub Pages）。
詳細な設計メモは `開発メモ.md`。

## 現在の状態（最新コミット d03db87、main にプッシュ済み）
- レベル15の「おやこ」で、子犬に名前を付けるポップアップ（`checkKidName`）
- マップ画面に「おや／おやこ／こ」切り替え（`petArt` / `viewArt`、`dogs[犬種].view` と `.kidName`）
- 毎日最初の起動から3秒後に1回、Discord へ学習記録＋復元用データを送信（`dcDaily` / `dcSend`）
  - 設定は「おうちの人へ｜データの ほぞん」③-2。URLは端末の localStorage のみ

## ぼうけんチケット＋とくべつ2セット（コミット前・index.html と img/plush_F_*, G_* が未コミット）
- 「ぼうけんの こうえん」(`park`) を さいごまで あるくと チケット（`save.craneSp`）+1。1かい1まい、上限99、日が かわっても きえない
- ミニゲーム欄は「クレーンゲーム」1つだけ。クレーン画面の上の「ふつうの だい／🌟チケットの だい」タブ（`crTabs` / `crSwitch`）で きりかえる（あそんでいる さいちゅうは きりかえ不可）。チケットで あそぶ きかいには
  セットF「ゆきの くに」→G「にじの くに」だけが でる（`PLUSH_SETS` の `sp:true`）。ふつうの きかいは A〜E のまま
- `plushCurSet(sp)` / `crSet()` / `crLeftOf(sp)` / `plushNextSet()` が ふつう・とくべつを わける。`cr.sp` が いまの きかいの しゅるい
- F・G の絵は Gemini ではなく、`img/plush_<動物>.png` を Python で いろがえ（hue shift）した もの。元は `イラストぬいぐるみ色違い/F_*.png, G_*.png`
  （`tools_make_dog_png.py plush` は全部を作り直すので重い。F・G は img へ直接コピー済み）
- 手元の確認: チケットで F を取得、F コンプリート後に G が出る、までブラウザで確認済み。`park` クリア時の付与そのものは未プレイ（コードのみ）

## フレンチブルの足元（修正済み）
- 元絵 01〜04 は「いちまつ」背景で、白い体と背景の白マスがくっついて足先が削れていた。lv15(05.png、緑背景)は問題なし
- `tools_fix_frenchbulldog.py` で img の lv1/lv3/lv5/sad を後処理（削れを埋めて足元を白で整える。足の指の線は消える）。
  `tools_make_dog_png.py` を再実行すると元に戻るので、実行後にこちらも再実行する

## 決定事項
- 「トップ画面」＝犬を表示するマップ画面と解釈（違えば移す）
- 「こ」の絵は lv1、「おや」は lv5 を流用（子犬専用の絵は無い）
- 送る内容は、日別の正解/不正解数・その日の不正解問題・全問題の通算/直近1週間の不正解回数のみ
- Webhook URL は公開リポジトリに書かない（リポジトリは PUBLIC。Discord は GitHub に載った Webhook を自動で無効化する）

## Webhook URL の一時公開（かたづけ済み）
タブレットへ URL をコピーさせるため `webhook-local.js` を一時的に公開リポジトリへ置いた（8ee21c2）が、
設定完了後に削除し、タイトル画面の表示＋コピーボタンも撤去した。`index.html` はその機能を入れる前と同一。
**URL は git 履歴（8ee21c2）に残っている**。Discord 側で Webhook を作り直す（古い URL を削除）よう案内済み。

## 次にやること
- 実際の Discord Webhook で送信を確認（テストは XHR を差し替えた確認のみ）
- 子犬専用の絵が用意できたら `tools_make_dog_png.py` に追加して `lv1` 流用をやめる

## 注意点（ハマった点）
- `artForLevel(pet().level)` を直接使うと「おや／こ」切り替えが効かない。`petArt()` を使う
- `save.mistakes` は正解すると減る「にがて度」。集計には `missTotal` / `missLog` / `qlog` を使う
- `loadSave()` は項目を許可リスト方式で読むので、セーブに項目を足したら必ずここにも足す
- `index.html` の関数は IIFE の中。ブラウザのコンソールから直接呼べない
- Bash のヒアドキュメントで長い Python を流すとクォートで失敗することがある。ファイルに書いて実行する
- 動作確認は `.claude/launch.json` の `wanwan`（python http.server 8765）
