---
name: gift-concierge
description: |
  プレゼント・贈り物選びをギフトコンシェルジュの視点でサポートする。
  相手の情報をヒアリングし、プロの思考法に基づいた提案をHTMLレポートで提供する。
  「プレゼント」「贈り物」「ギフト」「何あげよう」「誕生日に何を」
  「お祝い」「お返し」「手土産」などの話題が出たらこのスキルを使う。
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

ギフトコンシェルジュの思考法を取り入れて、相手に本当に喜ばれるプレゼントを提案する。
「何をあげたらいいかわからない」を解消し、自信を持って贈れるようサポートする。

---

## プロの思考法（提案の指針）

以下はギフトコンシェルジュが実践する考え方で、提案の全工程を通して意識すること。

### 3つの基本原則

1. **相手目線で考える** — 自分が贈りたいものではなく、相手のライフスタイルに馴染むものを選ぶ。相手の暮らしに彩りが生まれるかどうかが判断基準。
2. **隠れたニーズを探る** — 表面的な「欲しいもの」だけでなく、本人が自分では買わないが貰うと嬉しいものを見つける。少し背伸びした上質な日用品は鉄板。
3. **メッセージ性を持たせる** — 「なぜこれを選んだか」のストーリーがある贈り物は記憶に残る。地元の名産品、相手の趣味に寄り添った品など。

### 避けるべきNG

- 大きすぎるもの（置き場所問題）
- 相手にお返しのプレッシャーを与える高額すぎるもの
- 好みが分かれやすい香り・色が強いもの（関係性が浅い場合）
- 賞味期限が短い食品（一人暮らしの相手の場合）

### プロのテクニック

- **家族構成を考慮** — パートナーや子供がいるなら、家族も喜ぶものが効果的
- **季節限定・店舗限定を活用** — 定番品より特別感が出る
- **自分が試して良かったものを贈る** — 実体験に基づく推薦は説得力がある
- **消えものの安心感** — 関係性が浅い場合、上質な消耗品（入浴剤、タオル、菓子）が失敗しにくい

---

## Step 1: ヒアリング

以下の項目を段階的にヒアリングする。まず必須項目を聞き、回答に応じて深掘りする。

### 必須項目（まず聞く）

| # | 項目 | 質問例 |
|---|------|--------|
| 1 | 相手との関係 | どんな関係の方ですか？（恋人、友人、家族、上司、取引先など） |
| 2 | 相手の性別・年代 | 性別と年代を教えてください |
| 3 | 贈るシーン | どんな機会ですか？（誕生日、お祝い、感謝、手土産、お返しなど） |
| 4 | 予算 | 予算はどのくらいですか？（目安でOK） |

### 深掘り項目（必須の回答を踏まえて聞く）

| # | 項目 | 質問例 |
|---|------|--------|
| 5 | 相手の印象・性格 | どんな雰囲気の方ですか？（おしゃれ、アウトドア派、インドア派、こだわり屋など） |
| 6 | 趣味・ライフスタイル | 趣味や普段の過ごし方で知っていることはありますか？ |
| 7 | 家族構成 | 一人暮らし？パートナーやお子さんは？ |
| 8 | 過去に贈ったもの | これまでに贈ったことがあるものはありますか？ |
| 9 | 避けたいもの | これはNGというものはありますか？（アレルギー、苦手なジャンルなど） |

ヒアリングのポイント:
- 必須4項目が分かれば提案に進める
- 深掘り項目は分かる範囲でOK。「分からない」も立派な情報（→ 無難かつ上質な選択肢を重視）
- 相手の情報が少ないほど「消えもの」「体験ギフト」など汎用性の高い提案を増やす

---

## Step 2: 提案の組み立て

ヒアリング結果をもとに、以下の3段階で提案を構成する。

### A. 本命提案（2〜3件）

相手のライフスタイル・趣味に深く刺さるもの。ヒアリングで得た情報を最大限活用する。
「なぜこの人にこれが合うか」の理由を必ず添える。

### B. 安心提案（2〜3件）

万人に喜ばれやすい上質な定番品。情報が少ない場合の保険にもなる。
ブランドの信頼感、品質の高さ、実用性を重視。

### C. サプライズ提案（1〜2件）

相手が自分では買わないが、貰ったら嬉しいもの。
体験ギフト、限定品、パーソナライズアイテムなど。

### 調査方法

WebSearch で以下を調査する:
- "[シーン] プレゼント [性別] [年代] [予算帯] おすすめ [年]"
- "[趣味・関心キーワード] ギフト おすすめ"
- "[ブランド名] ギフト 人気"
- 具体的な商品の価格・購入先・レビュー

各提案について以下を収集:
- 商品名・ブランド
- 価格（税込）
- 購入できるサイトのURL
- 商品画像URL（WebFetch で取得。取得できない場合はフォールバック）
- おすすめ理由（プロの視点を交えて）

### D. NGアイテム（3〜5件）

このシーン・関係性・相手の特徴において避けるべきアイテムをまとめる。
WebSearch で "[シーン] プレゼント NG タブー マナー" も調査すること。

各NGアイテムについて以下を記載:
- 具体的なアイテム名（例: 包丁、ハンカチ、日本茶）
- なぜNGか（縁起・マナー・相手の状況に基づく理由）
- 代替案があれば簡潔に（例: 「日本茶→紅茶やコーヒーなら問題なし」）

---

## Step 3: HTMLレポートの生成

**ファイル保存先**: `reports/gift-concierge-$DATE.html`
（`$DATE` は今日の日付 `YYYY-MM-DD`）

```html
<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>プレゼント提案レポート <!-- FILL:日付 --></title>
<style>
  body { font-family: sans-serif; max-width: 960px; margin: 0 auto; padding: 24px; background: #f8fafc; color: #1e293b; }
  h1 { background: linear-gradient(135deg, #f59e0b, #ef4444); color: white; padding: 20px 24px; border-radius: 8px; margin-bottom: 8px; font-size: 1.4rem; }
  .meta { color: #64748b; font-size: 0.85rem; margin-bottom: 24px; }
  .profile { background: #fffbeb; border-left: 4px solid #f59e0b; padding: 14px 18px; border-radius: 0 8px 8px 0; margin-bottom: 28px; line-height: 1.7; font-size: 0.9rem; }
  .profile strong { color: #b45309; }
  .summary { background: #fef2f2; border-left: 4px solid #ef4444; padding: 14px 18px; border-radius: 0 8px 8px 0; margin-bottom: 28px; line-height: 1.7; }
  h2 { font-size: 1.15rem; border-bottom: 2px solid #e2e8f0; padding-bottom: 6px; margin: 32px 0 14px; color: #1e293b; }
  h3 { font-size: 0.95rem; color: #b45309; margin: 18px 0 8px; }
  .gift-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; margin-bottom: 24px; }
  .gift-card { background: white; border: 1px solid #e2e8f0; border-radius: 10px; overflow: hidden; transition: box-shadow .15s; }
  .gift-card:hover { box-shadow: 0 4px 14px rgba(245,158,11,.18); }
  .gift-card img { width: 100%; height: 200px; object-fit: cover; background: #f1f5f9; }
  .gift-card .no-img { width: 100%; height: 200px; background: #f1f5f9; display: flex; align-items: center; justify-content: center; color: #94a3b8; font-size: 0.85rem; }
  .gift-card .body { padding: 12px 14px; }
  .gift-card .name { font-weight: 700; font-size: 0.95rem; margin-bottom: 4px; }
  .gift-card .brand { font-size: 0.82rem; color: #b45309; margin-bottom: 4px; }
  .gift-card .price { font-size: 0.85rem; color: #64748b; margin-bottom: 6px; }
  .gift-card .reason { font-size: 0.82rem; color: #475569; line-height: 1.5; margin-bottom: 8px; padding: 8px; background: #fffbeb; border-radius: 6px; }
  .gift-card .link a { font-size: 0.8rem; color: #ef4444; text-decoration: none; font-weight: 600; }
  .gift-card .link a:hover { text-decoration: underline; }
  .section-label { display: inline-block; font-size: 0.75rem; font-weight: 700; padding: 3px 10px; border-radius: 12px; margin-bottom: 12px; }
  .section-label.honmei { background: #fef2f2; color: #dc2626; }
  .section-label.anshin { background: #ecfdf5; color: #059669; }
  .section-label.surprise { background: #eef2ff; color: #4f46e5; }
  .tips { background: white; border: 1px solid #e2e8f0; border-radius: 10px; padding: 16px 20px; margin-bottom: 16px; }
  .tips h3 { margin-top: 0; color: #ef4444; }
  .tips ul { padding-left: 18px; font-size: 0.88rem; line-height: 1.7; }
  .tips li { margin-bottom: 6px; }
  .ng-section { background: #fef2f2; border: 1px solid #fecaca; border-radius: 10px; padding: 16px 20px; margin-bottom: 16px; }
  .ng-section h3 { margin-top: 0; color: #991b1b; }
  .ng-section ul { padding-left: 18px; font-size: 0.88rem; line-height: 1.7; }
  .ng-section li { margin-bottom: 6px; }
  .ng-section .ng-reason { color: #64748b; font-size: 0.82rem; }
  .sources { margin-top: 32px; padding-top: 12px; border-top: 1px solid #e2e8f0; font-size: 0.78rem; color: #64748b; }
  .sources a { color: #b45309; }
  footer { margin-top: 24px; font-size: 0.75rem; color: #94a3b8; text-align: right; }
</style>
</head>
<body>

<h1>🎁 プレゼント提案レポート</h1>
<div class="meta">📅 <!-- FILL:YYYY年MM月DD日 --> 生成</div>

<div class="profile">
  <!-- FILL: ヒアリング結果のサマリー。例:
  <strong>贈る相手:</strong> 友人（女性・30代） ｜ <strong>シーン:</strong> 誕生日 ｜ <strong>予算:</strong> 5,000〜10,000円 ｜ <strong>印象:</strong> おしゃれ好き・カフェ巡りが趣味 ｜ <strong>家族:</strong> 一人暮らし
  -->
</div>

<div class="summary">
<!-- FILL: コンシェルジュ視点での提案方針を3〜4文で。相手の特徴から導いた選び方の軸と、特におすすめのポイントを説明 -->
</div>

<!-- ========== 本命提案 ========== -->
<h2>🎯 本命提案 — この人だからこそ</h2>
<span class="section-label honmei">相手の趣味・ライフスタイルに合わせた提案</span>

<div class="gift-grid">
  <!-- FILL: 2〜3件。例:
  <div class="gift-card">
    <img src="https://example.com/image.jpg" alt="商品名" onerror="this.outerHTML='<div class=no-img>画像を読み込めません</div>'">
    <div class="body">
      <div class="name">ブルーボトルコーヒー ギフトセット</div>
      <div class="brand">Blue Bottle Coffee</div>
      <div class="price">¥4,860（税込）</div>
      <div class="reason">💡 カフェ巡りが趣味とのことなので、自宅でもスペシャルティコーヒーを楽しめるセットを。一人暮らしでも消費しやすい個包装タイプ。</div>
      <div class="link"><a href="https://example.com" target="_blank">購入サイトを見る →</a></div>
    </div>
  </div>
  -->
</div>

<!-- ========== 安心提案 ========== -->
<h2>✅ 安心提案 — 間違いのない定番</h2>
<span class="section-label anshin">万人に喜ばれる上質な選択肢</span>

<div class="gift-grid">
  <!-- FILL: 2〜3件。上質な定番品。 -->
</div>

<!-- ========== サプライズ提案 ========== -->
<h2>✨ サプライズ提案 — 自分では買わないけど嬉しい</h2>
<span class="section-label surprise">意外性のある特別な選択肢</span>

<div class="gift-grid">
  <!-- FILL: 1〜2件。体験ギフト・限定品・パーソナライズアイテムなど。 -->
</div>

<!-- ========== NGアイテム ========== -->
<h2>🚫 これは避けて — 喜ばれないもの・NGアイテム</h2>

<div class="ng-section">
  <h3>このシーン・相手で避けるべきもの</h3>
  <ul>
    <!-- FILL: 3〜5件。このシーン・関係性・相手の特徴に合わせた具体的なNGアイテムと理由。例:
    <li><strong>包丁・ハサミなどの刃物</strong><br><span class="ng-reason">「縁を切る」を連想させるため、結婚祝いでは縁起が悪いとされる。相手が気にしない場合でも、周囲の目があるので避けるのが無難。</span></li>
    <li><strong>日本茶</strong><br><span class="ng-reason">弔事のイメージが強く、お祝いの場にはそぐわない。コーヒーや紅茶なら問題なし。</span></li>
    <li><strong>ハンカチ</strong><br><span class="ng-reason">漢字で「手巾（てぎれ）」と書き、「手切れ」＝別れを連想させる。特に白いハンカチは弔事を想起。</span></li>
    -->
  </ul>
</div>

<!-- ========== 贈り方のアドバイス ========== -->
<h2>💌 贈り方のアドバイス</h2>

<div class="tips">
  <h3>コンシェルジュからのワンポイント</h3>
  <ul>
    <!-- FILL: 3〜4件。このシーン・関係性に合わせた贈り方のコツ。例:
    <li><strong>渡すタイミング:</strong> 誕生日当日がベスト。難しければ前倒しで（後出しは避ける）</li>
    <li><strong>ラッピング:</strong> 購入先でギフトラッピングを依頼すると統一感が出る</li>
    <li><strong>メッセージ:</strong> 短くても手書きのカードを添えると印象が大きく変わる</li>
    -->
  </ul>
</div>

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

- [ ] ヒアリング必須4項目（関係・性別年代・シーン・予算）の回答を得ている
- [ ] `reports/gift-concierge-YYYY-MM-DD.html` が生成され、FILL コメントがすべて実データに置換済み
- [ ] 本命・安心・サプライズの3カテゴリで計5件以上の提案がある
- [ ] 各提案に「なぜこの人にこれが合うか」の理由が記載されている
- [ ] NGアイテムが3〜5件、具体的な理由付きで記載されている
- [ ] 贈り方のアドバイスが含まれている

## エラー対応

- 画像URLが取得できない場合 → フォールバック表示で続行
- 同日付ファイルが存在する場合は上書き
