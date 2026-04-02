---
name: weekly-digest
description: |
  過去1週間のレポートを要約し、週次ダイジェストHTMLレポートを生成する。
  毎週のトレンド変化や注目ポイントをまとめる。
  引数なしで過去7日間。引数に日数を渡すと期間を変更できる。
disable-model-invocation: false
user-invocable: true
allowed-tools:
  - Read
  - Write
  - Bash
  - WebSearch
---

## 目的

`reports/` ディレクトリにある過去1週間分の各種レポート（ai-report, trading-card-release,
fashion-report, travel-plan, restock-watch, vtuber-riona, gift-concierge 等）を横断的に読み込み、
週次ダイジェストとしてまとめたHTMLレポートを生成する。

カテゴリごとの要約・ハイライト・トレンド変化・来週の注目ポイントを1つのレポートに集約する。

---

## Step 1: 対象レポートの収集

### 期間の決定

- `$ARGUMENTS` が数値の場合: 過去N日間を対象とする
- `$ARGUMENTS` が空の場合: 過去7日間を対象とする

### ファイルの収集

1. `reports/` ディレクトリ内のHTMLファイルを一覧する（`weekly-digest-*.html` 自身は除外）
2. ファイル名の `YYYY-MM-DD` パターンから日付を抽出し、対象期間内のファイルのみを選別する
3. カテゴリ別にグループ化する（ファイル名のプレフィックスで判別）:
   - `ai-report` → AI動向レポート
   - `trading-card-release` → トレカ新発売情報
   - `restock-watch` → 再販ウォッチ
   - `fashion-report` → ファッションレポート
   - `travel-plan` → 国内旅行プラン
   - `vtuber-riona` → VTuber推し活
   - `gift-concierge` → プレゼント提案

---

## Step 2: 各レポートの内容読み取り

対象の各HTMLファイルを Read で読み込み、以下を抽出する:

- `<div class="summary">` 内のテキスト（概要）
- 主要な見出し（`<h2>`, `<h3>`）とその直下の内容
- テーブルの主要データ
- `.tag` が付いたステータス情報

抽出した内容をカテゴリ別・日付別に整理する。

---

## Step 3: 前週データとの比較（オプション）

対象期間の直前の `weekly-digest-*.html` が存在する場合は Read で読み込み、
トレンド変化の分析に使う。存在しない場合はこのステップをスキップする。

---

## Step 4: HTMLレポートの生成

**ファイル保存先**: `reports/weekly-digest-$DATE.html`
（`$DATE` は今日の日付 `YYYY-MM-DD`）

以下のテンプレートを使い、`<!-- FILL -->` をすべて実データで置き換えること。
CSS・レイアウトはそのまま使用し、データ部分だけを埋める。

```html
<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>週次ダイジェスト <!-- FILL:日付 --></title>
<style>
  body { font-family: sans-serif; max-width: 960px; margin: 0 auto; padding: 24px; background: #f8fafc; color: #1e293b; }
  h1 { background: linear-gradient(135deg, #059669, #10b981); color: white; padding: 20px 24px; border-radius: 8px; margin-bottom: 8px; font-size: 1.4rem; }
  .meta { color: #64748b; font-size: 0.85rem; margin-bottom: 24px; }
  .summary { background: #ecfdf5; border-left: 4px solid #059669; padding: 14px 18px; border-radius: 0 8px 8px 0; margin-bottom: 28px; line-height: 1.7; }
  h2 { font-size: 1.15rem; border-bottom: 2px solid #e2e8f0; padding-bottom: 6px; margin: 32px 0 14px; color: #1e293b; }
  h3 { font-size: 0.95rem; color: #059669; margin: 18px 0 8px; }
  .highlight-card { background: white; border: 1px solid #d1fae5; border-radius: 8px; padding: 14px 18px; margin-bottom: 12px; }
  .highlight-card .hl-rank { font-size: 1.2rem; font-weight: 700; color: #059669; float: left; margin-right: 12px; line-height: 1.4; }
  .highlight-card .hl-title { font-weight: 700; font-size: 0.95rem; margin-bottom: 4px; }
  .highlight-card .hl-desc { font-size: 0.88rem; color: #475569; line-height: 1.6; }
  .highlight-card .hl-source { font-size: 0.78rem; color: #94a3b8; margin-top: 6px; }
  .category-section { background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 18px 22px; margin-bottom: 20px; }
  .category-section h3 { margin-top: 0; font-size: 1.05rem; }
  .category-section .cat-icon { font-size: 1.2rem; margin-right: 6px; }
  .category-summary { font-size: 0.9rem; line-height: 1.7; margin-bottom: 12px; }
  .category-changes { font-size: 0.88rem; color: #475569; line-height: 1.7; }
  .category-links { margin-top: 10px; font-size: 0.82rem; }
  .category-links a { color: #059669; text-decoration: none; margin-right: 12px; }
  .category-links a:hover { text-decoration: underline; }
  table { width: 100%; border-collapse: collapse; font-size: 0.88rem; margin-bottom: 16px; }
  th { background: #e2e8f0; padding: 8px 10px; text-align: left; font-weight: 600; }
  td { padding: 8px 10px; border-bottom: 1px solid #e2e8f0; vertical-align: top; }
  tr:hover td { background: #f1f5f9; }
  .tag { display: inline-block; font-size: 0.72rem; padding: 2px 8px; border-radius: 3px; margin-right: 4px; font-weight: 600; }
  .tag.new { background: #dcfce7; color: #166534; }
  .tag.up { background: #dbeafe; color: #1e40af; }
  .tag.down { background: #fee2e2; color: #991b1b; }
  .tag.stable { background: #f1f5f9; color: #64748b; }
  .tag.hot { background: #fef3c7; color: #92400e; }
  .trend-section { background: #fffbeb; border-left: 4px solid #f59e0b; padding: 14px 18px; border-radius: 0 8px 8px 0; margin-bottom: 20px; }
  .next-week { background: #eff6ff; border-left: 4px solid #3b82f6; padding: 14px 18px; border-radius: 0 8px 8px 0; margin-bottom: 20px; }
  ul { padding-left: 18px; font-size: 0.9rem; line-height: 1.7; }
  li { margin-bottom: 6px; }
  .sources { margin-top: 32px; padding-top: 12px; border-top: 1px solid #e2e8f0; font-size: 0.78rem; color: #64748b; }
  .sources a { color: #059669; }
  footer { margin-top: 24px; font-size: 0.75rem; color: #94a3b8; text-align: right; }
</style>
</head>
<body>

<h1>📊 週次ダイジェスト</h1>
<div class="meta">📅 <!-- FILL:YYYY年MM月DD日 --> 生成 ｜ <!-- FILL:対象期間 例「2026年3月27日〜4月2日（7日間）」 --> ｜ <!-- FILL:対象レポート数 例「12件のレポートを集約」 --></div>

<div class="summary">
<!-- FILL: 今週の全体サマリーを3〜4文で記述。最も重要なトピック、カテゴリ横断的な傾向、注目すべき変化を含める -->
</div>

<!-- ========== 今週のハイライト ========== -->
<h2>🏆 今週のハイライト</h2>

<!-- FILL: 全カテゴリから最も注目度の高い3〜5件を選出。例: -->
<div class="highlight-card">
  <div class="hl-rank">1</div>
  <div class="hl-title"><!-- FILL: ハイライトのタイトル --></div>
  <div class="hl-desc"><!-- FILL: 概要2〜3文 --></div>
  <div class="hl-source"><!-- FILL: 出典レポート名 --> ｜ <span class="tag hot">注目</span></div>
</div>

<div class="highlight-card">
  <div class="hl-rank">2</div>
  <div class="hl-title"><!-- FILL --></div>
  <div class="hl-desc"><!-- FILL --></div>
  <div class="hl-source"><!-- FILL --></div>
</div>

<div class="highlight-card">
  <div class="hl-rank">3</div>
  <div class="hl-title"><!-- FILL --></div>
  <div class="hl-desc"><!-- FILL --></div>
  <div class="hl-source"><!-- FILL --></div>
</div>

<!-- FILL: 必要に応じて4位・5位のhighlight-cardを追加 -->

<!-- ========== カテゴリ別サマリー ========== -->
<h2>📂 カテゴリ別サマリー</h2>

<!-- FILL: 対象期間内にレポートが存在するカテゴリごとに以下のセクションを繰り返す。
     レポートが0件のカテゴリは省略する。 -->

<div class="category-section">
  <h3><span class="cat-icon"><!-- FILL: カテゴリ絵文字 --></span><!-- FILL: カテゴリ名 --><span class="tag"><!-- FILL: レポート数 例「3件」 --></span></h3>
  <div class="category-summary">
    <!-- FILL: このカテゴリの今週のまとめを2〜3文で -->
  </div>
  <div class="category-changes">
    <strong>主なポイント:</strong>
    <ul>
      <!-- FILL: 3〜5件の箇条書き。各レポートから抽出した重要情報 -->
    </ul>
  </div>
  <div class="category-links">
    📄 <!-- FILL: 個別レポートへのリンク。例:
    <a href="ai-report-2026-03-28.html">3/28</a>
    <a href="ai-report-2026-03-30.html">3/30</a>
    <a href="ai-report-2026-04-01.html">4/1</a>
    -->
  </div>
</div>

<!-- ========== トレンド変化 ========== -->
<h2>📈 トレンド変化</h2>

<div class="trend-section">
<!-- FILL: 前週と比較したトレンドの変化を記述する。前週のweekly-digestがない場合は、
     今週のレポート群から読み取れるトレンドを記述する。 -->
<ul>
  <!-- FILL: 3〜5件の変化ポイント。タグで傾向を示す。例:
  <li><span class="tag new">NEW</span> ○○が今週初めて登場</li>
  <li><span class="tag up">↑</span> △△への関心が先週より上昇</li>
  <li><span class="tag down">↓</span> □□の話題が減少傾向</li>
  <li><span class="tag stable">→</span> ◇◇は引き続き安定した注目度</li>
  -->
</ul>
</div>

<!-- ========== 来週の注目 ========== -->
<h2>🔭 来週の注目</h2>

<div class="next-week">
<!-- FILL: 来週注目すべきポイントを記述する。今週のレポート内容から推測される来週の動向。 -->
<ul>
  <!-- FILL: 3〜5件の来週注目ポイント。例:
  <li>4月8日に○○の新モデル発表が予定</li>
  <li>△△の予約受付が来週開始見込み</li>
  <li>□□のセールが来週末まで</li>
  -->
</ul>
</div>

<!-- ========== 参照レポート一覧 ========== -->
<h2>📑 参照レポート一覧</h2>

<table>
  <thead><tr><th>日付</th><th>カテゴリ</th><th>レポート</th></tr></thead>
  <tbody>
    <!-- FILL: 対象期間内の全レポートを日付降順で列挙。例:
    <tr>
      <td>2026-04-02</td>
      <td>🤖 AI動向</td>
      <td><a href="ai-report-2026-04-02.html">ai-report-2026-04-02.html</a></td>
    </tr>
    -->
  </tbody>
</table>

<div class="sources">
  <strong>集約元：</strong>
  <!-- FILL: 全対象レポートへのリンクをカンマ区切りで列挙 -->
</div>

<footer>Generated by Claude Code / AutoDailyTask ｜ <!-- FILL:YYYY-MM-DD HH:MM JST --></footer>
</body>
</html>
```

---

## 完了条件

- [ ] `reports/` 内の対象期間レポートがすべて読み込まれている
- [ ] `reports/weekly-digest-YYYY-MM-DD.html` が生成され、FILL コメントがすべて実データに置換済み
- [ ] レポートが0件のカテゴリは省略されている
- [ ] 各カテゴリの個別レポートへのリンクが正しく設定されている
- [ ] レポート生成後、ファイルパスとダイジェストの概要をユーザーに案内する

## エラー対応

- 対象期間内にレポートが0件の場合 → レポートが見つからない旨をユーザーに伝え、期間の拡大を提案する
- 同日付ファイルが存在する場合は上書き
- 個別レポートの読み込みに失敗した場合 → そのファイルをスキップして残りで生成を続行する

## 使い方

```
/weekly-digest                    # 過去7日間のダイジェスト
/weekly-digest 14                 # 過去14日間のダイジェスト
```
