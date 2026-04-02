---
name: fashion-report
description: |
  ユーザーにファッションの好みをヒアリングしたうえで、最新トレンドを調査し、
  おすすめアイテムやコーディネートを画像付きHTMLレポートで提供する。
  ファッション、服、コーデ、着こなし、今季のトレンド、何を着ればいい、
  おすすめの服、買い物リストなどの話題が出たらこのスキルを使う。
disable-model-invocation: false
user-invocable: true
allowed-tools:
  - WebSearch
  - WebFetch
  - Write
  - Read
  - Bash
  - AskUserQuestion
---

## 目的

ユーザーの好みや体型、利用シーンに合わせて、今シーズンのファッショントレンドを
調査し、おすすめアイテムとコーディネートを画像付きHTMLレポートにまとめる。

パーソナライズされた提案をするために、まずヒアリングを行い、
十分な情報が揃ってから調査・レポート生成に進む。

---

## Step 1: ヒアリング

以下の6項目をユーザーに質問する。
一度にまとめて聞いてOK。ユーザーが既に情報を提供している場合はスキップする。

| # | 項目 | 質問例 |
|---|------|--------|
| 1 | 性別 | メンズ・レディースどちらですか？ |
| 2 | 年齢 | 年代を教えてください（20代、30代など） |
| 3 | 体型 | 体型の特徴はありますか？（身長、がっちり/細身など） |
| 4 | 好みのスタイル | どんな雰囲気が好きですか？（カジュアル、きれいめ、モード、ストリートなど） |
| 5 | 利用シーン | 主にどんな場面で着ますか？（通勤、デート、休日、旅行など） |
| 6 | 気になるアイテム | 特に探しているアイテムはありますか？（ジャケット、スニーカーなど。なければ「特になし」でOK） |

ヒアリング時のポイント:
- 回答が曖昧な項目があっても、最低限「性別」「好みのスタイル」「利用シーン」の3つが分かれば次に進める
- ユーザーが「おまかせ」と言った場合は、性別だけ確認して残りは幅広く提案する方針で進める

---

## Step 2: トレンド調査

ヒアリング結果をもとに、WebSearch で以下を調査する。

### 検索の方針

ユーザーの属性（性別・年齢・スタイル）に合わせて検索キーワードを組み立てる。

検索キーワード例:
- "[メンズ/レディース] ファッション トレンド [現在の季節] [年]"
- "[スタイル名] コーディネート [季節] [年]"
- "[アイテム名] おすすめ [年] [ブランド]"
- "[メンズ/レディース] [シーン] コーデ [季節]"

### 調査する内容

**A. 今季のトレンドキーワード**
- 注目カラー（2〜3色）
- 注目素材・柄
- シルエットのトレンド（オーバーサイズ、タイトなど）

**B. おすすめアイテム（5〜8件）**
各アイテムについて以下を収集:
- アイテム名・カテゴリ
- おすすめブランド（国内・海外どちらも。ユーザーの予算感に合わせる）
- 価格帯の目安
- 画像URL（ブランド公式サイト・ファッションメディアから取得）
- 購入できるサイトのURL

**C. コーディネート例（3〜5件）**
- コーデのテーマ（「休日カジュアル」「オフィスきれいめ」など）
- 使用アイテムの組み合わせ
- コーディネート画像URL（ファッションメディア・WEAR等から取得）

画像URLの取得について:
- WebSearch で画像を含むページを見つけ、WebFetch でページを取得して `<img>` タグから画像URLを抽出する
- 画像が取得できなかったアイテムは画像なしで掲載する（レポート生成をブロックしない）
- 画像URLは `https://` で始まる絶対URLであること

---

## Step 3: HTMLレポートの生成

**ファイル保存先**: `reports/fashion-report-$DATE.html`
（`$DATE` は今日の日付 `YYYY-MM-DD`）

以下のテンプレートを使い、`<!-- FILL -->` をすべて実データで置き換えること。

```html
<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ファッションレポート <!-- FILL:日付 --></title>
<style>
  body { font-family: sans-serif; max-width: 960px; margin: 0 auto; padding: 24px; background: #f8fafc; color: #1e293b; }
  h1 { background: linear-gradient(135deg, #ec4899, #8b5cf6); color: white; padding: 20px 24px; border-radius: 8px; margin-bottom: 8px; font-size: 1.4rem; }
  .meta { color: #64748b; font-size: 0.85rem; margin-bottom: 24px; }
  .profile { background: #fdf2f8; border-left: 4px solid #ec4899; padding: 14px 18px; border-radius: 0 8px 8px 0; margin-bottom: 28px; line-height: 1.7; font-size: 0.9rem; }
  .profile strong { color: #9d174d; }
  .summary { background: #f5f3ff; border-left: 4px solid #8b5cf6; padding: 14px 18px; border-radius: 0 8px 8px 0; margin-bottom: 28px; line-height: 1.7; }
  h2 { font-size: 1.15rem; border-bottom: 2px solid #e2e8f0; padding-bottom: 6px; margin: 32px 0 14px; color: #1e293b; }
  h3 { font-size: 0.95rem; color: #8b5cf6; margin: 18px 0 8px; }
  .trend-tags { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 16px; }
  .trend-tag { background: #ede9fe; color: #5b21b6; font-size: 0.82rem; padding: 4px 12px; border-radius: 16px; font-weight: 600; }
  .trend-tag.color-tag { background: #fce7f3; color: #9d174d; }
  .item-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; margin-bottom: 24px; }
  .item-card { background: white; border: 1px solid #e2e8f0; border-radius: 10px; overflow: hidden; transition: box-shadow .15s; }
  .item-card:hover { box-shadow: 0 4px 14px rgba(139,92,246,.15); }
  .item-card img { width: 100%; height: 220px; object-fit: cover; background: #f1f5f9; }
  .item-card .no-img { width: 100%; height: 220px; background: #f1f5f9; display: flex; align-items: center; justify-content: center; color: #94a3b8; font-size: 0.85rem; }
  .item-card .body { padding: 12px 14px; }
  .item-card .name { font-weight: 700; font-size: 0.95rem; margin-bottom: 4px; }
  .item-card .brand { font-size: 0.82rem; color: #8b5cf6; margin-bottom: 4px; }
  .item-card .price { font-size: 0.85rem; color: #64748b; margin-bottom: 8px; }
  .item-card .link a { font-size: 0.8rem; color: #ec4899; text-decoration: none; font-weight: 600; }
  .item-card .link a:hover { text-decoration: underline; }
  .coord-section { margin-bottom: 28px; }
  .coord-section .coord-img { width: 100%; max-height: 400px; object-fit: contain; border-radius: 8px; background: #f1f5f9; margin-bottom: 12px; }
  .coord-section .coord-no-img { width: 100%; height: 200px; background: #f1f5f9; border-radius: 8px; display: flex; align-items: center; justify-content: center; color: #94a3b8; margin-bottom: 12px; }
  .coord-items { font-size: 0.88rem; line-height: 1.7; }
  .coord-items li { margin-bottom: 4px; }
  .tag { display: inline-block; font-size: 0.72rem; padding: 2px 8px; border-radius: 3px; margin-right: 4px; font-weight: 600; }
  .tag.scene { background: #dbeafe; color: #1e40af; }
  .tag.style { background: #ede9fe; color: #5b21b6; }
  .sources { margin-top: 32px; padding-top: 12px; border-top: 1px solid #e2e8f0; font-size: 0.78rem; color: #64748b; }
  .sources a { color: #8b5cf6; }
  footer { margin-top: 24px; font-size: 0.75rem; color: #94a3b8; text-align: right; }
</style>
</head>
<body>

<h1>👗 ファッショントレンドレポート</h1>
<div class="meta">📅 <!-- FILL:YYYY年MM月DD日 --> 生成</div>

<div class="profile">
  <!-- FILL: ヒアリング結果のサマリー。例:
  <strong>性別:</strong> メンズ ｜ <strong>年代:</strong> 30代 ｜ <strong>体型:</strong> 標準（172cm） ｜ <strong>スタイル:</strong> きれいめカジュアル ｜ <strong>シーン:</strong> 通勤・休日 ｜ <strong>気になるアイテム:</strong> ジャケット
  -->
</div>

<div class="summary">
<!-- FILL: このレポートの概要を3〜4文で。今季のトレンドの要点と、このユーザーに特におすすめのポイントを含める -->
</div>

<!-- ========== トレンドキーワード ========== -->
<h2>🎨 今季のトレンドキーワード</h2>

<h3>注目カラー</h3>
<div class="trend-tags">
  <!-- FILL: 2〜3色。例:
  <span class="trend-tag color-tag">バーガンディ</span>
  <span class="trend-tag color-tag">セージグリーン</span>
  -->
</div>

<h3>注目素材・シルエット</h3>
<div class="trend-tags">
  <!-- FILL: 3〜4件。例:
  <span class="trend-tag">リネン混</span>
  <span class="trend-tag">リラックスフィット</span>
  -->
</div>

<!-- ========== おすすめアイテム ========== -->
<h2>🛍️ おすすめアイテム</h2>

<div class="item-grid">
  <!-- FILL: 5〜8件のアイテムカード。例:
  <div class="item-card">
    <img src="https://example.com/image.jpg" alt="アイテム名" onerror="this.outerHTML='<div class=no-img>画像を読み込めません</div>'">
    <div class="body">
      <div class="name">リネンテーラードジャケット</div>
      <div class="brand">UNITED ARROWS</div>
      <div class="price">¥25,000〜¥35,000</div>
      <div class="link"><a href="https://example.com/item" target="_blank">商品を見る →</a></div>
    </div>
  </div>
  -->
</div>

<!-- ========== コーディネート例 ========== -->
<h2>👔 コーディネート例</h2>

<!-- FILL: 3〜5件のコーディネートセクション。例:
<div class="coord-section">
  <h3>オフィスカジュアル — きれいめ通勤スタイル <span class="tag scene">通勤</span><span class="tag style">きれいめ</span></h3>
  <img class="coord-img" src="https://example.com/coord.jpg" alt="コーデ画像" onerror="this.outerHTML='<div class=coord-no-img>画像を読み込めません</div>'">
  <ul class="coord-items">
    <li><strong>アウター:</strong> ネイビーテーラードジャケット</li>
    <li><strong>トップス:</strong> 白カットソー</li>
    <li><strong>ボトムス:</strong> グレースラックス</li>
    <li><strong>シューズ:</strong> ブラウンレザーシューズ</li>
  </ul>
</div>
-->

<!-- ========== 参照元 ========== -->
<div class="sources">
  <strong>参照元：</strong>
  <!-- FILL: <a href="URL">サイト名</a> をカンマ区切りで列挙 -->
</div>

<footer>Generated by Claude Code / AutoDailyTask ｜ <!-- FILL:YYYY-MM-DD HH:MM JST --></footer>
</body>
</html>
```

---

## 完了条件

- [ ] ヒアリング6項目のうち最低3項目（性別・好みのスタイル・利用シーン）の回答を得ている
- [ ] `reports/fashion-report-YYYY-MM-DD.html` が生成され、FILL コメントがすべて実データに置換済み
- [ ] おすすめアイテムに画像が含まれている（取得できなかったものはフォールバック表示）
- [ ] レポート生成後、ファイルパスをユーザーに案内する

## エラー対応

- 画像URLが取得できない場合 → `<div class="no-img">` のフォールバックを使用し、レポート生成は続行する
- 同日付ファイルが存在する場合は上書き
