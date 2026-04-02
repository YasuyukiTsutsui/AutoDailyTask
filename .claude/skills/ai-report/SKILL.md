---
name: ai-report
description: |
  生成AIに関する最新情報（技術動向・社会実装・開発者知見）を調査し、
  HTMLレポートを生成してPDFに変換、Claude上で直接提供する。
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

生成AIに関する最新情報を3領域で調査し、HTMLレポートを生成してPDFに変換、
Claude上で直接読める形で提供する。

調査対象期間: 直近7日間の情報を優先する。

---

## Step 1: 最新情報の調査

以下の3領域を WebSearch で調査する。各領域で3〜5件の情報源を参照すること。

### 領域A: 技術動向
- 新モデルリリース（名前・企業・コンテキスト長・主な特徴）
- ベンチマーク最新スコア（SWE-Bench Verified / GPQA Diamond 等）
- エージェント・アーキテクチャの主要アップデート

### 領域B: 社会実装
- 製造業・公共・金融・小売の導入事例と定量データ
- 日本市場固有の動向
- ROI・実装課題

### 領域C: 開発者知見
- プロンプト・RAG・エージェント実装の新テクニック
- フレームワーク更新（LangChain/LlamaIndex/LangGraph 等）
- セキュリティリスクと対策
- コスト最適化の実数値

---

## Step 2: HTMLレポートの生成

**ファイル保存先**: `reports/ai-report-$DATE.html`
（`$DATE` は `$ARGUMENTS` があればその値、なければ今日の日付 `YYYY-MM-DD`）

以下のテンプレートを使い、`<!-- FILL -->` をすべて実データで置き換えること。
CSS・レイアウトはそのまま使用し、データ部分だけを埋める。

```html
<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<title>生成AI動向レポート <!-- FILL:日付 --></title>
<style>
  body { font-family: sans-serif; max-width: 960px; margin: 0 auto; padding: 24px; background:#f8fafc; color:#1e293b; }
  h1 { background: #4f46e5; color: white; padding: 20px 24px; border-radius: 8px; margin-bottom: 8px; font-size: 1.4rem; }
  .meta { color: #64748b; font-size: 0.85rem; margin-bottom: 24px; }
  .summary { background: #eef2ff; border-left: 4px solid #4f46e5; padding: 14px 18px; border-radius: 0 8px 8px 0; margin-bottom: 28px; line-height: 1.7; }
  h2 { font-size: 1.1rem; border-bottom: 2px solid #e2e8f0; padding-bottom: 6px; margin: 28px 0 14px; color: #1e293b; }
  h3 { font-size: 0.95rem; color: #4f46e5; margin: 18px 0 8px; }
  table { width: 100%; border-collapse: collapse; font-size: 0.88rem; margin-bottom: 16px; }
  th { background: #e2e8f0; padding: 8px 10px; text-align: left; font-weight: 600; }
  td { padding: 8px 10px; border-bottom: 1px solid #e2e8f0; vertical-align: top; }
  tr:hover td { background: #f1f5f9; }
  .tag { display: inline-block; background: #e0e7ff; color: #3730a3; font-size: 0.72rem; padding: 1px 6px; border-radius: 3px; margin-right: 4px; }
  .tag.green { background: #dcfce7; color: #166534; }
  .tag.yellow { background: #fef9c3; color: #854d0e; }
  .tag.red { background: #fee2e2; color: #991b1b; }
  ul { padding-left: 18px; font-size: 0.9rem; line-height: 1.7; }
  li { margin-bottom: 6px; }
  .sources { margin-top: 32px; padding-top: 12px; border-top: 1px solid #e2e8f0; font-size: 0.78rem; color: #64748b; }
  .sources a { color: #4f46e5; }
  footer { margin-top: 24px; font-size: 0.75rem; color: #94a3b8; text-align: right; }
</style>
</head>
<body>

<h1>🤖 生成AI 最新動向レポート</h1>
<div class="meta">📅 <!-- FILL:YYYY年MM月DD日 --> 生成 ｜ 直近7日間の情報を集約</div>

<div class="summary">
<!-- FILL: 今週のAI業界を3〜4文でまとめる。最重要トピック・最大の変化・開発者への示唆を含める -->
</div>

<!-- ========== 技術動向 ========== -->
<h2>🔬 技術動向</h2>

<h3>主要モデル比較</h3>
<table>
  <thead><tr><th>モデル</th><th>企業</th><th>主な特徴</th><th>コンテキスト</th><th>状態</th></tr></thead>
  <tbody>
    <!-- FILL: 5〜7行。例:
    <tr>
      <td><strong>Gemini 3.1 Pro</strong></td>
      <td>Google</td>
      <td>ARC-AGI-2 77.1%、マルチモーダル対応</td>
      <td>1M tokens</td>
      <td><span class="tag">最新</span></td>
    </tr>
    -->
  </tbody>
</table>

<h3>SWE-Bench Verified スコア（コーディング能力）</h3>
<table>
  <thead><tr><th>順位</th><th>モデル</th><th>スコア</th></tr></thead>
  <tbody>
    <!-- FILL: 上位5〜6件 -->
  </tbody>
</table>

<h3>エージェント・アーキテクチャ動向</h3>
<ul>
  <!-- FILL: 3〜4件の箇条書き -->
</ul>

<!-- ========== 社会実装 ========== -->
<h2>🏢 社会実装動向</h2>

<h3>業種別ROI・導入状況</h3>
<table>
  <thead><tr><th>業種</th><th>主な用途</th><th>定量効果</th><th>成熟度</th></tr></thead>
  <tbody>
    <!-- FILL: 4〜5行。例:
    <tr>
      <td><strong>製造業</strong></td>
      <td>予測保全・サプライチェーン</td>
      <td>ダウンタイム47%削減、ROI 150〜250%</td>
      <td><span class="tag green">本番稼働</span></td>
    </tr>
    -->
  </tbody>
</table>

<h3>日本市場トピック</h3>
<ul>
  <!-- FILL: 3〜4件の箇条書き（具体的な企業名・数値を含める） -->
</ul>

<h3>主要な実装課題</h3>
<ul>
  <!-- FILL: 3〜4件の箇条書き -->
</ul>

<!-- ========== 開発者知見 ========== -->
<h2>⚡ 開発者向けTips &amp; ベストプラクティス</h2>

<h3>今週の注目テクニック</h3>
<table>
  <thead><tr><th>#</th><th>テクニック</th><th>効果・概要</th><th>カテゴリ</th></tr></thead>
  <tbody>
    <!-- FILL: 5件。例:
    <tr>
      <td>1</td>
      <td><strong>プロンプトキャッシング</strong></td>
      <td>Anthropic APIでシステムプロンプトをキャッシュ → 読取コスト1/10</td>
      <td><span class="tag">コスト</span></td>
    </tr>
    -->
  </tbody>
</table>

<h3>フレームワーク更新</h3>
<table>
  <thead><tr><th>フレームワーク</th><th>バージョン</th><th>主な変更点</th></tr></thead>
  <tbody>
    <!-- FILL: 3〜4件 -->
  </tbody>
</table>

<h3>セキュリティ・リスク</h3>
<ul>
  <!-- FILL: 2〜3件の箇条書き（CVSSスコア・攻撃成功率など数値を含める） -->
</ul>

<h3>コスト最適化（実数値）</h3>
<table>
  <thead><tr><th>手法</th><th>削減率の目安</th><th>実装難易度</th></tr></thead>
  <tbody>
    <!-- FILL: 4〜5件 -->
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

## Step 3: PDF変換とClaude上での提供

```bash
python3 scripts/html-to-pdf.py "reports/ai-report-$DATE.html" "reports/ai-report-$DATE.pdf"
```

変換後、`reports/ai-report-$DATE.pdf` を Read ツールで読み込み、ユーザーに提示する。

---

## 完了条件

- [ ] `reports/ai-report-YYYY-MM-DD.html` が生成され、FILL コメントがすべて実データに置換済み
- [ ] `reports/ai-report-YYYY-MM-DD.pdf` が生成されている
- [ ] Read ツールで PDF を読み込み、Claude 上で表示する

## エラー対応

- weasyprint 未インストール → `pip3 install weasyprint` を実行してから再試行
- 同日付ファイルが存在する場合は上書き
