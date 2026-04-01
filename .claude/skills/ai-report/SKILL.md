---
name: ai-report
description: |
  生成AIに関する最新情報（技術動向・社会実装・開発者知見）を調査し、
  視覚化したHTMLレポートを生成してSlackチャンネルにアップロードする。
  引数なしで当日分を生成。引数に日付(YYYY-MM-DD)を渡すと指定日分を生成。
disable-model-invocation: false
user-invocable: true
allowed-tools:
  - WebSearch
  - WebFetch
  - Write
  - Read
  - Bash
---

## 目的

生成AIに関する最新情報を3つの観点で調査し、視覚化したHTMLレポートを生成して
Slackチャンネルにアップロードする。

調査対象期間: 直近7日間の情報を優先する。

---

## Step 1: 最新情報の調査

以下の3領域を**並行して**WebSearchで調査する。各領域で最低5件の情報源を参照すること。

### 領域A: 技術動向
検索キーワード例:
- `generative AI model release 2026 latest`
- `LLM breakthrough site:openai.com OR site:anthropic.com OR site:deepmind.google`
- `AI agent multimodal reasoning 2026`

収集する情報:
- 新モデルリリース（名前・性能・コンテキスト長）
- アーキテクチャの新技術（推論・マルチモーダル・エージェント）
- ベンチマーク更新（SWE-Bench, MMLU, HumanEval等の最新スコア）
- 注目論文・技術ブログの要点

### 領域B: 社会実装
検索キーワード例:
- `generative AI manufacturing industry implementation 2026`
- `AI enterprise ROI case study 2026`
- `生成AI 製造業 導入事例 2026`
- `AI public sector government deployment`

収集する情報:
- 製造業・公共・金融・小売の導入事例
- ROI・生産性向上の定量データ
- 日本市場固有の動向
- 主要な実装課題と対処法

### 領域C: 開発者知見
検索キーワード例:
- `LLM development best practices 2026`
- `prompt engineering tips RAG agentic`
- `AI production deployment cost optimization`

収集する情報:
- プロンプトエンジニアリングの新テクニック
- RAG/エージェント実装のベストプラクティス更新
- 評価・テストフレームワークの新情報
- コスト・セキュリティの実践知見

---

## Step 2: HTMLレポートの生成

収集した情報をもとに以下の仕様でHTMLファイルを生成する。

**ファイル保存先**: `reports/ai-report-$DATE.html`
（`$DATE` は `$ARGUMENTS` があればその値、なければ今日の日付 `YYYY-MM-DD`）

### HTML仕様

以下のテンプレートをベースに、調査した実データで各セクションを埋めること。
`<!-- FILL: ... -->` のコメントを実データに置き換える。

```html
<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>生成AI最新動向レポート <!-- FILL: YYYY-MM-DD --></title>
<style>
  :root {
    --primary: #6366f1;
    --primary-dark: #4f46e5;
    --success: #10b981;
    --warning: #f59e0b;
    --danger: #ef4444;
    --bg: #0f172a;
    --surface: #1e293b;
    --surface2: #334155;
    --text: #f1f5f9;
    --text-muted: #94a3b8;
    --border: #475569;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.6;
    padding: 24px;
    max-width: 1200px;
    margin: 0 auto;
  }
  /* Header */
  .header {
    background: linear-gradient(135deg, var(--primary) 0%, #8b5cf6 100%);
    border-radius: 16px;
    padding: 32px;
    margin-bottom: 24px;
    position: relative;
    overflow: hidden;
  }
  .header::before {
    content: '';
    position: absolute;
    top: -50%;
    right: -10%;
    width: 300px;
    height: 300px;
    background: rgba(255,255,255,0.05);
    border-radius: 50%;
  }
  .header h1 { font-size: 2rem; font-weight: 700; margin-bottom: 8px; }
  .header .date { opacity: 0.85; font-size: 0.95rem; }
  .header .summary {
    margin-top: 16px;
    background: rgba(0,0,0,0.2);
    border-radius: 8px;
    padding: 16px;
    font-size: 0.95rem;
    line-height: 1.7;
  }
  /* Grid */
  .grid-3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 24px; }
  .grid-2 { display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; margin-bottom: 24px; }
  @media (max-width: 900px) {
    .grid-3 { grid-template-columns: 1fr; }
    .grid-2 { grid-template-columns: 1fr; }
  }
  /* Cards */
  .card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 20px;
  }
  .card-header {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 16px;
    padding-bottom: 12px;
    border-bottom: 1px solid var(--border);
  }
  .card-header .icon {
    width: 36px;
    height: 36px;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.2rem;
  }
  .card-header h2 { font-size: 1.05rem; font-weight: 600; }
  .card-header .badge {
    margin-left: auto;
    font-size: 0.7rem;
    padding: 2px 8px;
    border-radius: 20px;
    font-weight: 600;
    background: var(--primary);
    color: white;
  }
  /* News items */
  .news-item {
    border-left: 3px solid var(--primary);
    padding: 10px 14px;
    margin-bottom: 12px;
    background: var(--surface2);
    border-radius: 0 8px 8px 0;
  }
  .news-item:last-child { margin-bottom: 0; }
  .news-item .title { font-weight: 600; font-size: 0.9rem; margin-bottom: 4px; }
  .news-item .desc { font-size: 0.82rem; color: var(--text-muted); line-height: 1.5; }
  .news-item .meta {
    margin-top: 6px;
    font-size: 0.75rem;
    color: var(--text-muted);
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
  }
  .tag {
    background: var(--surface2);
    border: 1px solid var(--border);
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 0.72rem;
    color: var(--text-muted);
  }
  /* Model table */
  .model-table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
  .model-table th {
    text-align: left;
    padding: 8px 12px;
    background: var(--surface2);
    color: var(--text-muted);
    font-weight: 500;
    font-size: 0.78rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
  .model-table td { padding: 10px 12px; border-bottom: 1px solid var(--border); }
  .model-table tr:last-child td { border-bottom: none; }
  .model-name { font-weight: 600; color: var(--text); }
  .model-org { font-size: 0.78rem; color: var(--text-muted); }
  /* Bar chart (CSS only) */
  .bar-chart { margin-top: 8px; }
  .bar-row {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 10px;
    font-size: 0.82rem;
  }
  .bar-label { width: 140px; flex-shrink: 0; color: var(--text-muted); }
  .bar-track {
    flex: 1;
    background: var(--surface2);
    border-radius: 4px;
    height: 20px;
    overflow: hidden;
  }
  .bar-fill {
    height: 100%;
    border-radius: 4px;
    background: linear-gradient(90deg, var(--primary), #8b5cf6);
    display: flex;
    align-items: center;
    padding-left: 8px;
    font-size: 0.75rem;
    font-weight: 600;
    color: white;
    white-space: nowrap;
  }
  /* Tips */
  .tip-item {
    display: flex;
    gap: 12px;
    padding: 12px 0;
    border-bottom: 1px solid var(--border);
  }
  .tip-item:last-child { border-bottom: none; }
  .tip-num {
    width: 28px;
    height: 28px;
    border-radius: 50%;
    background: var(--primary);
    color: white;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.8rem;
    font-weight: 700;
    flex-shrink: 0;
  }
  .tip-content .title { font-weight: 600; font-size: 0.9rem; margin-bottom: 4px; }
  .tip-content .desc { font-size: 0.82rem; color: var(--text-muted); }
  /* Industry cards */
  .industry-card {
    background: var(--surface2);
    border-radius: 8px;
    padding: 14px;
    margin-bottom: 10px;
  }
  .industry-card:last-child { margin-bottom: 0; }
  .industry-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
  }
  .industry-name { font-weight: 600; font-size: 0.9rem; }
  .roi-badge {
    font-size: 0.78rem;
    padding: 2px 8px;
    border-radius: 4px;
    font-weight: 600;
  }
  .roi-high { background: rgba(16,185,129,0.2); color: #10b981; }
  .roi-mid  { background: rgba(245,158,11,0.2); color: #f59e0b; }
  .industry-card .desc { font-size: 0.82rem; color: var(--text-muted); }
  /* Sources */
  .sources { margin-top: 24px; }
  .sources h3 { font-size: 0.85rem; color: var(--text-muted); margin-bottom: 10px; text-transform: uppercase; letter-spacing: 0.05em; }
  .source-list { display: flex; flex-wrap: wrap; gap: 8px; }
  .source-link {
    font-size: 0.78rem;
    color: var(--primary);
    text-decoration: none;
    background: rgba(99,102,241,0.1);
    padding: 3px 10px;
    border-radius: 4px;
    border: 1px solid rgba(99,102,241,0.3);
  }
  .source-link:hover { background: rgba(99,102,241,0.2); }
  /* Footer */
  .footer {
    margin-top: 32px;
    padding-top: 16px;
    border-top: 1px solid var(--border);
    font-size: 0.78rem;
    color: var(--text-muted);
    display: flex;
    justify-content: space-between;
  }
  .section-title {
    font-size: 1.25rem;
    font-weight: 700;
    margin-bottom: 16px;
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .section-title::after {
    content: '';
    flex: 1;
    height: 1px;
    background: var(--border);
    margin-left: 8px;
  }
</style>
</head>
<body>

<!-- HEADER -->
<div class="header">
  <div class="date">📅 <!-- FILL: YYYY年MM月DD日 --> 生成 | 直近7日間の情報を集約</div>
  <h1>🤖 生成AI 最新動向レポート</h1>
  <div class="summary">
    <!-- FILL: 今週のAI業界を3〜4文でサマリー。最重要トピック・最大の変化・開発者への示唆を含める -->
  </div>
</div>

<!-- KPI ROW -->
<div class="grid-3">
  <div class="card">
    <div class="card-header">
      <div class="icon" style="background:rgba(99,102,241,0.15)">🚀</div>
      <h2>新モデル・リリース</h2>
      <span class="badge"><!-- FILL: 件数 -->件</span>
    </div>
    <!-- FILL: 今週の主要リリース一覧（3件程度） news-item形式 -->
  </div>
  <div class="card">
    <div class="card-header">
      <div class="icon" style="background:rgba(16,185,129,0.15)">🏭</div>
      <h2>産業導入トピック</h2>
      <span class="badge"><!-- FILL: 件数 -->件</span>
    </div>
    <!-- FILL: 今週の産業導入ニュース（3件程度） news-item形式 -->
  </div>
  <div class="card">
    <div class="card-header">
      <div class="icon" style="background:rgba(245,158,11,0.15)">⚡</div>
      <h2>開発者向けTips</h2>
      <span class="badge"><!-- FILL: 件数 -->件</span>
    </div>
    <!-- FILL: 今週の開発者向け新情報（3件程度） news-item形式 -->
  </div>
</div>

<!-- SECTION 1: TECHNICAL -->
<div class="section-title">🔬 技術動向</div>
<div class="grid-2">
  <div class="card">
    <div class="card-header">
      <div class="icon" style="background:rgba(99,102,241,0.15)">📊</div>
      <h2>モデル性能比較</h2>
    </div>
    <!-- モデル一覧テーブル -->
    <table class="model-table">
      <thead>
        <tr>
          <th>モデル</th>
          <th>特徴</th>
          <th>コンテキスト</th>
        </tr>
      </thead>
      <tbody>
        <!-- FILL: 最新の主要モデルを5〜8行で。例:
        <tr>
          <td><div class="model-name">Claude Opus 4.6</div><div class="model-org">Anthropic</div></td>
          <td>適応的思考、コード・金融分析強化</td>
          <td>1M tokens</td>
        </tr>
        -->
      </tbody>
    </table>
  </div>
  <div class="card">
    <div class="card-header">
      <div class="icon" style="background:rgba(139,92,246,0.15)">📈</div>
      <h2>ベンチマーク推移</h2>
    </div>
    <div class="bar-chart">
      <!-- FILL: 主要ベンチマーク（SWE-Bench等）のスコアを bar-row形式で5件程度。例:
      <div class="bar-row">
        <span class="bar-label">Gemini 3 Pro</span>
        <div class="bar-track"><div class="bar-fill" style="width:76%">76.2%</div></div>
      </div>
      widthはスコアの%値をそのまま使う。ベンチマーク名を card-header に記載すること。
      -->
    </div>
  </div>
</div>

<div class="card" style="margin-bottom:24px">
  <div class="card-header">
    <div class="icon" style="background:rgba(99,102,241,0.15)">🤖</div>
    <h2>エージェント・アーキテクチャ動向</h2>
  </div>
  <!-- FILL: エージェントAI・マルチエージェント・新アーキテクチャの最新動向を news-item形式で4〜6件 -->
</div>

<!-- SECTION 2: SOCIAL IMPLEMENTATION -->
<div class="section-title">🏢 社会実装動向</div>
<div class="grid-2">
  <div class="card">
    <div class="card-header">
      <div class="icon" style="background:rgba(16,185,129,0.15)">🏭</div>
      <h2>業種別導入状況</h2>
    </div>
    <!-- FILL: 業種別の導入事例を industry-card形式で4〜5件。roi-high/roi-midでROI水準を示す。例:
    <div class="industry-card">
      <div class="industry-header">
        <span class="industry-name">💰 金融・保険</span>
        <span class="roi-badge roi-high">ROI 4.2x</span>
      </div>
      <div class="desc">決算業務30〜50%短縮、不正検知精度向上。主要行で本番稼働開始。</div>
    </div>
    -->
  </div>
  <div class="card">
    <div class="card-header">
      <div class="icon" style="background:rgba(99,102,241,0.15)">🇯🇵</div>
      <h2>日本市場トピック</h2>
    </div>
    <!-- FILL: 日本市場固有のAI動向・政策・企業事例を news-item形式で4〜5件 -->
  </div>
</div>

<!-- SECTION 3: DEVELOPER TIPS -->
<div class="section-title">⚡ 開発者向けTips &amp; ベストプラクティス</div>
<div class="grid-2">
  <div class="card">
    <div class="card-header">
      <div class="icon" style="background:rgba(245,158,11,0.15)">💡</div>
      <h2>今週の注目テクニック</h2>
    </div>
    <!-- FILL: 開発者向けの実践的なTipsをtip-item形式で5件。例:
    <div class="tip-item">
      <div class="tip-num">1</div>
      <div class="tip-content">
        <div class="title">プロンプトキャッシングで10倍コスト削減</div>
        <div class="desc">Anthropic APIでsystem promptをキャッシュするとread時コストが1/10に。繰り返し処理で必須。</div>
      </div>
    </div>
    -->
  </div>
  <div class="card">
    <div class="card-header">
      <div class="icon" style="background:rgba(239,68,68,0.15)">🛡️</div>
      <h2>セキュリティ・リスク</h2>
    </div>
    <!-- FILL: 最新のセキュリティリスク・対策をnews-item形式で3〜4件 -->
  </div>
</div>

<div class="card" style="margin-bottom:24px">
  <div class="card-header">
    <div class="icon" style="background:rgba(16,185,129,0.15)">🔧</div>
    <h2>フレームワーク・ツール更新</h2>
  </div>
  <div class="grid-2" style="margin:0">
    <div>
      <!-- FILL: LangChain/LlamaIndex/LangGraph等の最新アップデートをnews-item形式で3件 -->
    </div>
    <div>
      <!-- FILL: 評価ツール・監視ツール等の最新情報をnews-item形式で3件 -->
    </div>
  </div>
</div>

<!-- SOURCES -->
<div class="sources">
  <h3>参照元</h3>
  <div class="source-list">
    <!-- FILL: 調査で参照したURLを source-link形式でリスト。例:
    <a href="https://..." class="source-link" target="_blank">Anthropic Blog</a>
    -->
  </div>
</div>

<!-- FOOTER -->
<div class="footer">
  <span>🤖 Generated by Claude Code / AutoDailyTask</span>
  <span><!-- FILL: YYYY-MM-DD HH:MM JST --></span>
</div>

</body>
</html>
```

---

## Step 3: Slackへのアップロード

HTMLファイルの生成が完了したら、以下のコマンドでSlackにアップロードする。

```bash
bash scripts/upload-to-slack.sh "reports/ai-report-$DATE.html"
```

スクリプトが成功すると、指定Slackチャンネルにファイルが投稿される。

---

## 完了条件

- [ ] `reports/ai-report-YYYY-MM-DD.html` が生成されている
- [ ] HTMLが有効で、すべての `<!-- FILL: ... -->` コメントが実データに置き換わっている
- [ ] Slackアップロードスクリプトが成功（exit 0）している
- [ ] アップロード完了メッセージをユーザーに報告する

---

## エラー対応

- **環境変数未設定**: `SLACK_BOT_TOKEN` または `SLACK_CHANNEL_ID` が未設定の場合、
  HTMLは生成するがSlack通知はスキップし、ユーザーに `.env` 設定を促す。
- **WebSearch失敗**: 少なくとも1件のURLにアクセスできれば続行する。
  完全に検索不能な場合はユーザーに報告してスキップする。
- **既存ファイル**: 同日付のHTMLが既に存在する場合は上書きする。
