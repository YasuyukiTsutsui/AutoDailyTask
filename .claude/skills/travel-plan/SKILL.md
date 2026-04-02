---
name: travel-plan
description: |
  国内旅行プランを提案する。行き先の提案、松竹梅グレード別の楽しみ方、
  予算別ホテル提案までをHTMLレポートで提供する。
  引数に行き先・時期・人数・予算などを渡せる。引数なしの場合はヒアリングから開始する。
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

国内旅行の計画をトータルサポートする。
行き先が未定ならヒアリングで提案し、松竹梅3グレードのプランとホテルを提示する。

---

## Step 0: ヒアリング（情報が不足している場合）

$ARGUMENTS が空、または以下の情報が不足している場合は AskUserQuestion で確認する。
すでに十分な情報があればこのステップはスキップする。

確認する項目（未指定のもののみ聞く）:
1. **行き先**: 決まっている場合は具体的な地域。未定なら「おまかせ」でOK
2. **時期・日数**: いつ頃、何泊何日か（例: 5月GW、1泊2日）
3. **人数・構成**: 何人で誰と行くか（例: カップル、家族4人、友人3人）
4. **予算感**: 一人あたりの総予算目安（例: 3万円、5万円、上限なし）
5. **重視するポイント**: グルメ / 温泉 / 観光名所 / アクティビティ / のんびり など
6. **出発地**: どこから出発するか（例: 東京、大阪）

一度にまとめて聞く。個別に何度も質問しない。

---

## Step 1: 行き先の提案（行き先が未定の場合）

ヒアリング結果をもとに、おすすめの行き先を **3候補** 提案する。
各候補について以下を簡潔に示す:
- 地域名とキャッチコピー（一行）
- おすすめ理由（2〜3文）
- その時期ならではの魅力

AskUserQuestion で候補から選んでもらう。

行き先が最初から決まっている場合はこのステップをスキップする。

---

## Step 2: 詳細情報の調査

WebSearch で以下を調査する:
- 観光スポット（定番＋穴場）
- グルメ・名物料理
- 温泉・宿泊施設（価格帯別）
- アクセス方法と所要時間・交通費
- 季節限定のイベント・見どころ
- 実際の宿泊プラン・料金（じゃらん、楽天トラベル、一休.com 等）

---

## Step 3: HTMLレポートの生成

**ファイル保存先**: `reports/travel-plan-YYYY-MM-DD.html`
（`YYYY-MM-DD` は今日の日付）

以下のテンプレートを使い、`<!-- FILL -->` をすべて実データで置き換えること。

```html
<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<title>国内旅行プラン <!-- FILL:行き先 --> <!-- FILL:日付 --></title>
<style>
  body { font-family: sans-serif; max-width: 960px; margin: 0 auto; padding: 24px; background:#f8fafc; color:#1e293b; }
  h1 { background: linear-gradient(135deg, #059669, #0d9488); color: white; padding: 20px 24px; border-radius: 8px; margin-bottom: 8px; font-size: 1.4rem; }
  .meta { color: #64748b; font-size: 0.85rem; margin-bottom: 24px; }
  .summary { background: #ecfdf5; border-left: 4px solid #059669; padding: 14px 18px; border-radius: 0 8px 8px 0; margin-bottom: 28px; line-height: 1.7; }
  h2 { font-size: 1.15rem; border-bottom: 2px solid #e2e8f0; padding-bottom: 6px; margin: 32px 0 14px; color: #1e293b; }
  h3 { font-size: 0.95rem; color: #059669; margin: 18px 0 8px; }

  /* グレード別カード */
  .plan-card { border: 1px solid #e2e8f0; border-radius: 12px; padding: 20px; margin-bottom: 20px; }
  .plan-card.matsu { border-left: 5px solid #b45309; background: linear-gradient(135deg, #fffbeb, #fef3c7); }
  .plan-card.take  { border-left: 5px solid #059669; background: linear-gradient(135deg, #ecfdf5, #d1fae5); }
  .plan-card.ume   { border-left: 5px solid #6366f1; background: linear-gradient(135deg, #eef2ff, #e0e7ff); }
  .plan-card .grade { font-size: 1.1rem; font-weight: 700; margin-bottom: 4px; }
  .plan-card .grade .label { font-size: 0.75rem; padding: 2px 8px; border-radius: 10px; color: white; margin-left: 8px; vertical-align: middle; }
  .plan-card.matsu .label { background: #b45309; }
  .plan-card.take  .label { background: #059669; }
  .plan-card.ume   .label { background: #6366f1; }
  .plan-card .budget { font-size: 0.85rem; color: #64748b; margin-bottom: 12px; }

  /* スケジュール */
  .schedule { margin: 12px 0; }
  .schedule .time-block { display: flex; gap: 12px; margin-bottom: 10px; }
  .schedule .time { min-width: 60px; font-weight: 700; color: #059669; font-size: 0.85rem; }
  .schedule .activity { font-size: 0.88rem; line-height: 1.6; }

  /* ホテル */
  .hotel-section { margin-top: 16px; }
  .hotel { background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px 16px; margin-bottom: 10px; }
  .hotel .hotel-name { font-weight: 700; font-size: 0.95rem; }
  .hotel .hotel-meta { font-size: 0.8rem; color: #64748b; margin-top: 4px; }
  .hotel .hotel-price { font-size: 0.9rem; font-weight: 700; color: #059669; margin-top: 4px; }

  table { width: 100%; border-collapse: collapse; font-size: 0.88rem; margin-bottom: 12px; }
  th { background: #e2e8f0; padding: 8px 10px; text-align: left; font-weight: 600; }
  td { padding: 8px 10px; border-bottom: 1px solid #e2e8f0; vertical-align: top; }
  tr:hover td { background: #f1f5f9; }
  ul { padding-left: 18px; font-size: 0.9rem; line-height: 1.7; }
  li { margin-bottom: 6px; }
  .tip { background: #fffbeb; border-left: 3px solid #f59e0b; padding: 10px 14px; border-radius: 0 6px 6px 0; font-size: 0.85rem; margin: 12px 0; }
  .sources { margin-top: 32px; padding-top: 12px; border-top: 1px solid #e2e8f0; font-size: 0.78rem; color: #64748b; }
  .sources a { color: #059669; }
  footer { margin-top: 24px; font-size: 0.75rem; color: #94a3b8; text-align: right; }
</style>
</head>
<body>

<h1>✈️ 国内旅行プラン</h1>
<div class="meta">📅 <!-- FILL:YYYY年MM月DD日 --> 生成 ｜ <!-- FILL:行き先 --> <!-- FILL:日数 --> ｜ <!-- FILL:人数構成 --></div>

<div class="summary">
<!-- FILL: この旅行プランの概要を3〜4文でまとめる。行き先の魅力、ベストシーズンの理由、プランのポイントを含める -->
</div>

<!-- ========== 基本情報 ========== -->
<h2>📍 基本情報</h2>
<table>
  <tr><th style="width:140px">行き先</th><td><!-- FILL --></td></tr>
  <tr><th>時期</th><td><!-- FILL --></td></tr>
  <tr><th>日数</th><td><!-- FILL --></td></tr>
  <tr><th>人数・構成</th><td><!-- FILL --></td></tr>
  <tr><th>出発地</th><td><!-- FILL --></td></tr>
  <tr><th>アクセス</th><td><!-- FILL: 主要な交通手段・所要時間・概算費用 --></td></tr>
</table>

<!-- ========== 松プラン ========== -->
<h2>🏆 松竹梅グレード別プラン</h2>

<div class="plan-card matsu">
  <div class="grade">🥇 松プラン<span class="label">贅沢・特別な旅</span></div>
  <div class="budget">💰 予算目安: <!-- FILL: 一人あたり総額 --> /人</div>
  <p><!-- FILL: このグレードのコンセプトを1〜2文で --></p>

  <h3>モデルスケジュール</h3>
  <div class="schedule">
    <!-- FILL: 時間ブロックを日数分繰り返す。例:
    <div class="time-block">
      <div class="time">10:00</div>
      <div class="activity"><strong>〇〇観光</strong> — 説明文</div>
    </div>
    -->
  </div>

  <div class="hotel-section">
    <h3>おすすめ宿泊先</h3>
    <!-- FILL: 1〜2件のホテル。例:
    <div class="hotel">
      <div class="hotel-name">〇〇旅館</div>
      <div class="hotel-meta">📍 エリア ｜ ⭐ 特徴（露天風呂付き客室、ミシュラン掲載等）</div>
      <div class="hotel-price">1泊2食付き 〇〇,〇〇〇円〜 /人</div>
    </div>
    -->
  </div>
</div>

<!-- ========== 竹プラン ========== -->
<div class="plan-card take">
  <div class="grade">🥈 竹プラン<span class="label">バランス重視</span></div>
  <div class="budget">💰 予算目安: <!-- FILL --> /人</div>
  <p><!-- FILL: コンセプト --></p>

  <h3>モデルスケジュール</h3>
  <div class="schedule">
    <!-- FILL -->
  </div>

  <div class="hotel-section">
    <h3>おすすめ宿泊先</h3>
    <!-- FILL: 1〜2件 -->
  </div>
</div>

<!-- ========== 梅プラン ========== -->
<div class="plan-card ume">
  <div class="grade">🥉 梅プラン<span class="label">コスパ最優先</span></div>
  <div class="budget">💰 予算目安: <!-- FILL --> /人</div>
  <p><!-- FILL: コンセプト --></p>

  <h3>モデルスケジュール</h3>
  <div class="schedule">
    <!-- FILL -->
  </div>

  <div class="hotel-section">
    <h3>おすすめ宿泊先</h3>
    <!-- FILL: 1〜2件 -->
  </div>
</div>

<!-- ========== グルメ情報 ========== -->
<h2>🍽️ ご当地グルメ・おすすめ飲食店</h2>
<table>
  <thead><tr><th>店名・料理</th><th>ジャンル</th><th>予算目安</th><th>ポイント</th></tr></thead>
  <tbody>
    <!-- FILL: 5〜8件 -->
  </tbody>
</table>

<!-- ========== 観光スポット ========== -->
<h2>📸 おすすめ観光スポット</h2>
<table>
  <thead><tr><th>スポット</th><th>所要時間</th><th>料金</th><th>おすすめポイント</th></tr></thead>
  <tbody>
    <!-- FILL: 6〜10件（定番＋穴場をバランスよく） -->
  </tbody>
</table>

<!-- ========== お土産 ========== -->
<h2>🎁 おすすめお土産</h2>
<ul>
  <!-- FILL: 4〜6件（名前、価格帯、買える場所を含める） -->
</ul>

<!-- ========== 旅の Tips ========== -->
<h2>💡 旅の Tips</h2>
<div class="tip">
<!-- FILL: 3〜5件の実用的なアドバイス（混雑回避、割引情報、季節の注意点など）を箇条書きで -->
</div>

<!-- ========== 予算比較 ========== -->
<h2>💴 予算比較まとめ</h2>
<table>
  <thead><tr><th>項目</th><th>🥇 松</th><th>🥈 竹</th><th>🥉 梅</th></tr></thead>
  <tbody>
    <!-- FILL: 交通費・宿泊費・食費・観光費・お土産・合計 の行 -->
  </tbody>
</table>

<!-- ========== 参照元 ========== -->
<div class="sources">
  <strong>参照元：</strong>
  <!-- FILL: <a href="URL">タイトル</a> をカンマ区切りで列挙 -->
</div>

<footer>Generated by Claude Code / AutoDailyTask ｜ <!-- FILL:YYYY-MM-DD HH:MM JST --></footer>
</body>
</html>
```

---

## 完了条件

- [ ] ヒアリングで必要情報を確認済み（または $ARGUMENTS で提供済み）
- [ ] `reports/travel-plan-YYYY-MM-DD.html` が生成され、FILL コメントがすべて実データに置換済み
- [ ] 松竹梅3グレードすべてにモデルスケジュール・ホテル提案が含まれている
- [ ] 予算比較表が3グレード分記載されている

## エラー対応

- 同日付ファイルが存在する場合は上書き
- 宿泊料金が取得できない場合は「要確認」と記載し、予約サイトのURLを添える

## 使い方

```
/travel-plan                              # ヒアリングから開始
/travel-plan 箱根 1泊2日 カップル         # 条件を指定して生成
/travel-plan 京都 GW 家族4人 予算5万円    # 詳細条件付き
```
