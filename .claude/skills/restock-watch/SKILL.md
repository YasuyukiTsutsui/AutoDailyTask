---
name: restock-watch
description: |
  売り切れアイテムの再販・再入荷情報をウォッチし、HTMLレポートを生成する。
  引数に商品名・ブランド・カテゴリを渡すと絞り込み検索。引数なしで人気カテゴリを横断調査。
  「再販」「再入荷」「リストック」「sold out」「買えない」などの話題が出たらこのスキルを使う。
disable-model-invocation: false
user-invocable: true
allowed-tools:
  - WebSearch
  - WebFetch
  - Write
  - Read
  - Bash
---

<!-- NOTE: serve-reports.py の CATEGORIES に以下を追加すること:
  "restock-watch": ("再販ウォッチ", "🔄", False),
-->

## 目的

売り切れ・品薄になっている人気アイテムの再販・再入荷情報を調査し、
HTMLレポートを生成する。

---

## Step 1: 再販・再入荷情報の調査

WebSearch を使って直近の再販・再入荷情報を検索する。

### 検索対象

$ARGUMENTS が指定されている場合はその商品名・ブランド・カテゴリに絞る。
空の場合は以下の**全カテゴリ**を対象にする：

**トレカ**
- ポケモンカード（人気パックの再販）
- 遊戯王OCG（品薄パック・限定BOX）
- ワンピースカードゲーム

**ゲーム機・周辺機器**
- 人気ゲーム機本体
- 限定モデル・コラボモデル
- 人気周辺機器（コントローラー等）

**スニーカー・限定ファッションアイテム**
- Nike / adidas / New Balance 等の限定モデル
- コラボスニーカー
- Supreme / BAPE 等のストリートブランド限定品

**フィギュア・ホビー**
- 人気アニメ・ゲームフィギュア再販
- プラモデル（ガンプラ等）の再販
- 限定コラボグッズ

**コスメ・美容（限定品）**
- デパコス限定コレクション
- 完売コスメの再販情報
- 人気スキンケアの再入荷

**家電（人気商品）**
- 品薄家電の入荷情報
- 人気調理家電・美容家電
- オーディオ機器

検索キーワード例:
- "再販 再入荷 [商品名] [年月]"
- "[カテゴリ] リストック 入荷 [年]"
- "[商品名] restock [年]"
- "[商品名] 在庫あり 購入可能"
- "[カテゴリ] 品薄 再販決定"

### 各アイテムの収集情報

- **商品名**: 正式な商品名
- **カテゴリ**: トレカ / ゲーム / スニーカー / フィギュア / コスメ / 家電 等
- **再販日・入荷日**: 再販日または入荷予定日
- **価格**: 定価・販売価格
- **購入先URL**: 購入可能なショップのURL
- **ステータス**: 再販中 / 予約受付中 / 入荷待ち / 数量限定
- **補足情報**: 販売条件（抽選・先着等）、購入のコツ、転売注意喚起

---

## Step 2: HTMLレポートの生成

**ファイル保存先**: `reports/restock-watch-$DATE.html`
（`$DATE` は今日の日付 `YYYY-MM-DD`）

以下のテンプレートを使い、`<!-- FILL -->` をすべて実データで置き換えること。
CSS・レイアウトはそのまま使用し、データ部分だけを埋める。

```html
<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>再販ウォッチレポート <!-- FILL:日付 --></title>
<style>
  body { font-family: sans-serif; max-width: 960px; margin: 0 auto; padding: 24px; background:#f8fafc; color:#1e293b; }
  h1 { background: linear-gradient(135deg, #f59e0b, #d97706); color: white; padding: 20px 24px; border-radius: 8px; margin-bottom: 8px; font-size: 1.4rem; }
  .meta { color: #64748b; font-size: 0.85rem; margin-bottom: 24px; }
  .summary { background: #fffbeb; border-left: 4px solid #f59e0b; padding: 14px 18px; border-radius: 0 8px 8px 0; margin-bottom: 28px; line-height: 1.7; }
  h2 { font-size: 1.15rem; border-bottom: 2px solid #e2e8f0; padding-bottom: 6px; margin: 32px 0 14px; color: #1e293b; }
  h3 { font-size: 0.95rem; color: #d97706; margin: 18px 0 8px; }
  .item-section { background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px 20px; margin-bottom: 20px; }
  .item-section h3 { margin-top: 0; font-size: 1.05rem; color: #b45309; }
  table { width: 100%; border-collapse: collapse; font-size: 0.88rem; margin-bottom: 12px; }
  th { background: #e2e8f0; padding: 8px 10px; text-align: left; font-weight: 600; }
  td { padding: 8px 10px; border-bottom: 1px solid #e2e8f0; vertical-align: top; }
  tr:hover td { background: #f1f5f9; }
  .overview-table th { background: #d97706; color: white; }
  .tag { display: inline-block; font-size: 0.72rem; padding: 2px 8px; border-radius: 3px; margin-right: 4px; font-weight: 600; }
  .tag.restocked { background: #dcfce7; color: #166534; }
  .tag.preorder { background: #fef9c3; color: #854d0e; }
  .tag.waiting { background: #dbeafe; color: #1e40af; }
  .tag.limited { background: #fee2e2; color: #991b1b; }
  .note { font-size: 0.85rem; color: #64748b; margin-top: 8px; line-height: 1.6; }
  ul { padding-left: 18px; font-size: 0.9rem; line-height: 1.7; }
  li { margin-bottom: 6px; }
  .tips { background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; padding: 16px 20px; margin-bottom: 24px; }
  .tips h3 { color: #166534; margin-top: 0; }
  .tips li { margin-bottom: 8px; }
  .sources { margin-top: 32px; padding-top: 12px; border-top: 1px solid #e2e8f0; font-size: 0.78rem; color: #64748b; }
  .sources a { color: #d97706; }
  footer { margin-top: 24px; font-size: 0.75rem; color: #94a3b8; text-align: right; }
</style>
</head>
<body>

<h1>🔄 再販・再入荷ウォッチレポート</h1>
<div class="meta">📅 <!-- FILL:YYYY年MM月DD日 --> 生成 ｜ <!-- FILL:対象カテゴリ or 検索対象 --></div>

<div class="summary">
<!-- FILL: 今回の再販・再入荷情報のハイライトを3〜4文でまとめる。特に注目の再販品、すぐに動くべきアイテム、今後の再販予定を含める -->
</div>

<!-- ========== 再販・再入荷アイテム一覧 ========== -->
<h2>📋 再販・再入荷アイテム一覧</h2>

<table class="overview-table">
  <thead><tr><th>商品名</th><th>カテゴリ</th><th>再販日/入荷日</th><th>価格</th><th>購入先</th><th>ステータス</th></tr></thead>
  <tbody>
    <!-- FILL: 収集した全アイテムを一覧で記載。例:
    <tr>
      <td><strong>ポケモンカード 拡張パック「〇〇」</strong></td>
      <td>トレカ</td>
      <td>2026年4月10日</td>
      <td>1パック 180円 / 1BOX 5,400円</td>
      <td><a href="https://example.com" target="_blank">ポケモンセンター</a></td>
      <td><span class="tag restocked">再販中</span></td>
    </tr>
    <tr>
      <td><strong>Nike Dunk Low "Panda" 2026</strong></td>
      <td>スニーカー</td>
      <td>2026年4月15日（予定）</td>
      <td>¥14,300</td>
      <td><a href="https://example.com" target="_blank">SNKRS</a></td>
      <td><span class="tag preorder">予約受付中</span></td>
    </tr>
    <tr>
      <td><strong>RG νガンダム</strong></td>
      <td>フィギュア・ホビー</td>
      <td>2026年4月下旬</td>
      <td>¥4,950</td>
      <td><a href="https://example.com" target="_blank">プレミアムバンダイ</a></td>
      <td><span class="tag waiting">入荷待ち</span></td>
    </tr>
    <tr>
      <td><strong>SUQQU ザ クリーム 限定セット</strong></td>
      <td>コスメ</td>
      <td>2026年4月5日 10:00〜</td>
      <td>¥38,500</td>
      <td><a href="https://example.com" target="_blank">公式オンライン</a></td>
      <td><span class="tag limited">数量限定</span></td>
    </tr>
    -->
  </tbody>
</table>

<!-- ========== 各アイテム詳細 ========== -->
<!-- FILL: 収集したアイテムごとに以下のセクションを繰り返す -->

<div class="item-section">
  <h3><!-- FILL: 商品名 --></h3>
  <table>
    <tr><th style="width:140px">カテゴリ</th><td><!-- FILL --></td></tr>
    <tr><th>再販日・入荷日</th><td><!-- FILL --></td></tr>
    <tr><th>価格</th><td><!-- FILL --></td></tr>
    <tr><th>購入先</th><td><!-- FILL: 購入先URL付きリンク --></td></tr>
    <tr><th>ステータス</th><td><!-- FILL: タグ付きステータス --></td></tr>
    <tr><th>販売条件</th><td><!-- FILL: 抽選・先着・個数制限等 --></td></tr>
  </table>
  <div class="note">💡 <!-- FILL: 補足情報（入手のコツ、過去の再販実績、転売注意等） --></div>
</div>

<!-- ========== 再入荷ゲットのコツ ========== -->
<div class="tips">
  <h3>💡 再入荷アイテムをゲットするコツ</h3>
  <ul>
    <!-- FILL: 5〜7件の実用的なアドバイス。例:
    <li><strong>通知設定を活用:</strong> 各ショップの再入荷通知・お気に入り登録で即座にアラートを受け取る</li>
    <li><strong>複数サイトで狙う:</strong> Amazon・楽天・公式サイト等、複数の購入先を事前にブックマーク</li>
    <li><strong>発売時間を確認:</strong> オンライン販売は午前10時開始が多い。5分前にはページを開いておく</li>
    <li><strong>転売価格に注意:</strong> 定価を必ず確認し、転売業者からの高額購入を避ける</li>
    <li><strong>抽選応募は複数店舗:</strong> 抽選販売の場合は応募可能な店舗すべてに申し込む</li>
    -->
  </ul>
</div>

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

- [ ] `reports/restock-watch-YYYY-MM-DD.html` が生成され、FILL コメントがすべて実データに置換済み
- [ ] アイテムごとに購入先URLが含まれている
- [ ] ステータスタグが適切に設定されている（restocked / preorder / waiting / limited）
- [ ] レポート生成後、ファイルパスをユーザーに案内する

## エラー対応

- 同日付ファイルが存在する場合は上書き
- 特定カテゴリで情報が見つからない場合はそのカテゴリをスキップし、見つかったものだけでレポートを生成する

## 使い方

```
/restock-watch                              # 全カテゴリを横断調査
/restock-watch ポケモンカード               # 特定商品に絞って検索
/restock-watch Nike Dunk                    # スニーカーの再販情報
/restock-watch ガンプラ                     # プラモデルの再販情報
/restock-watch コスメ 限定                  # コスメの限定品再販情報
```
