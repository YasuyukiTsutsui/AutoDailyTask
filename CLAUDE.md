# AutoDailyTask — Claude Code Skills による日常タスク自動化

## プロジェクト概要

Claude Code Skills（カスタムスラッシュコマンド）を使って日常タスクを自動化するリポジトリ。
各タスクは `.claude/skills/<skill-name>/SKILL.md` として定義し、`/skill-name` で呼び出す。

## ディレクトリ構造

```
AutoDailyTask/
├── CLAUDE.md                        # このファイル
├── README.md                        # 人向けドキュメント
├── .env.example                     # 環境変数テンプレート（.env は gitignore）
├── .gitignore
├── .claude/
│   ├── settings.json                # Hooks 設定
│   ├── skills/
│   │   ├── ai-report/               # 生成AI最新動向レポート
│   │   ├── trading-card-release/    # トレカ新発売情報レポート
│   │   ├── restock-watch/           # 再販ウォッチャー
│   │   ├── fashion-report/          # ファッションレポート
│   │   ├── gift-concierge/          # プレゼント提案
│   │   ├── travel-plan/             # 国内旅行プラン
│   │   ├── vtuber-riona/            # VTuber推し活レポート
│   │   ├── weekly-digest/           # 週次ダイジェスト
│   │   ├── daily-routine/           # 一括レポート実行
│   │   ├── cleanup-reports/         # レポート整理
│   │   ├── serve-reports/           # レポートビューア起動
│   │   └── stop-reports/            # レポートビューア停止
│   └── docs/
│       └── skill-template.md        # 新規スキル作成テンプレート
├── scripts/
│   ├── html-to-pdf.py               # HTML → PDF 変換（weasyprint）
│   ├── serve-reports.py             # レポートビューア Web サーバー
│   ├── scheduler.sh                 # マルチスキル対応デイリースケジューラー
│   ├── com.autodailytask.scheduler.plist  # macOS launchd 自動起動設定
│   └── upload-to-slack.sh           # SlackへHTMLファイルをアップロード
├── reports/                         # 生成されたHTML/PDFレポート（gitignore対象）
└── tasks/
    ├── templates/                   # タスクテンプレート
    └── archive/                     # アーカイブ済みタスク
```

## Skill の作り方

### ファイル配置

```
.claude/skills/<skill-name>/SKILL.md
```

スキル名はケバブケース（`daily-report`, `standup`）で統一する。
スラッシュコマンド名はスキル名と一致する（例: `/daily-report`）。

### SKILL.md フロントマター

```yaml
---
name: skill-name
description: スキルの一行説明（250文字以内。Claude がコマンド選択に使う）
disable-model-invocation: false  # 副作用あり操作は true に設定
user-invocable: true
allowed-tools:
  - Read
  - Write
  - Bash
paths:
  - tasks/
---
```

### `disable-model-invocation` の使い分け

| 操作の性質 | 設定値 | 例 |
|---|---|---|
| ファイル読み取り・レポート生成 | `false` | daily-report, standup |
| ファイル削除・外部API呼び出し・git push | `true` | task-cleanup, deploy |

**原則**: ロールバック不能な副作用がある場合は必ず `true` にする。

### `allowed-tools` の最小権限原則

読み取り専用スキルには `Read, Grep` だけを指定する。
書き込みが必要な場合のみ `Write` や `Bash` を追加する。
ツールを絞ることで誤操作を防ぎ、ユーザーへの確認頻度も下がる。

### 詳細ドキュメントの分離

SKILL.md は 500 行以内を厳守。詳細な仕様は `.claude/docs/` に置き、
`context:` フィールドまたは `@.claude/docs/detail.md` 構文で参照する。

スキル作成テンプレート: @.claude/docs/skill-template.md

## Hooks 設定

`.claude/settings.json` で設定する。フックは CLAUDE.md の指示と違い**常に実行される**。

```json
{
  "hooks": {
    "SessionStart": [
      {
        "type": "command",
        "command": "echo \"Session started: $(date)\" >> .claude/session.log"
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [{ "type": "command", "command": "scripts/post-write.sh" }]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [{ "type": "command", "command": "scripts/safety-check.sh" }]
      }
    ]
  }
}
```

### よく使うフックパターン

| イベント | 用途 | exit code |
|---|---|---|
| `SessionStart` | ログ記録・今日のタスク一覧表示 | 0 (常に許可) |
| `PreToolUse` | 危険操作のブロック（本番ファイル直書きなど） | 0=許可 / 2=ブロック |
| `PostToolUse` | フォーマッター実行・変更通知 | 0 (常に許可) |

フックスクリプトは `scripts/` に置き、実行権限を付与しておく。

## 開発ワークフロー

### 新しいスキルを追加する手順

1. `.claude/docs/skill-template.md` を参照して内容を記述
2. `.claude/skills/<skill-name>/SKILL.md` として配置
3. Claude Code で `/skill-name` を実行して動作確認
4. `allowed-tools` と `paths` を実際の挙動に合わせて絞り込む

### テスト方法

- スキルを実行して期待通りの出力が得られるか確認する
- `disable-model-invocation: true` のスキルは必ずドライランフラグを実装する
- ログは `.claude/session.log` に蓄積して挙動を追跡する

### コミット規約

```
feat(skills): daily-report スキルを追加
fix(hooks): post-write フックのパスを修正
docs: skill-template を更新
chore: 不要なアーカイブファイルを削除
```

プレフィックス: `feat` / `fix` / `docs` / `refactor` / `chore`
スコープ: `skills` / `hooks` / `tasks` / `docs`

## 命名規約

| 対象 | 規約 | 例 |
|---|---|---|
| スキルディレクトリ | ケバブケース | `daily-report` |
| タスクテンプレート | ケバブケース + `.md` | `standup-template.md` |
| アーカイブファイル | `YYYY-MM-DD-<name>.md` | `2026-04-01-standup.md` |
| フックスクリプト | ケバブケース + `.sh` | `safety-check.sh` |

## 実装済みスキル

### レポート系スキル

レポート系スキルは共通の出力パターンに従う:
1. WebSearch で情報を収集
2. `reports/<skill-name>-YYYY-MM-DD.html` に HTML レポートを生成
3. `/serve-reports` でブラウザ閲覧可能

| スキル | 概要 | 出力ファイル |
|---|---|---|
| `/ai-report` | 生成AI最新動向（技術・社会実装・開発者知見） | `ai-report-YYYY-MM-DD.html` |
| `/trading-card-release` | トレカ新発売・予約情報 | `trading-card-release-YYYY-MM-DD.html` |
| `/restock-watch` | 売り切れアイテムの再販・再入荷情報 | `restock-watch-YYYY-MM-DD.html` |
| `/fashion-report` | ファッショントレンド・おすすめコーデ | `fashion-report-YYYY-MM-DD.html` |
| `/gift-concierge` | プレゼント・贈り物提案 | `gift-concierge-YYYY-MM-DD.html` |
| `/travel-plan` | 国内旅行プラン（松竹梅グレード別・ホテル提案） | `travel-plan-YYYY-MM-DD.html` |
| `/vtuber-riona` | VTuber推し活レポート（配信予定・グッズ等） | `vtuber-riona-YYYY-MM-DD.html` |
| `/weekly-digest` | 過去1週間のレポート横断要約・トレンド変化 | `weekly-digest-YYYY-MM-DD.html` |

```bash
/ai-report                          # 当日分を生成
/ai-report 2026-04-01               # 日付指定
/trading-card-release               # 全タイトル対象
/trading-card-release ポケモンカード # タイトル絞り込み
/restock-watch                      # 全カテゴリ横断調査
/restock-watch ポケモンカード       # 特定商品に絞って検索
/fashion-report                     # ヒアリング後にレポート生成
/gift-concierge                     # ヒアリング後にギフト提案
/travel-plan                        # ヒアリングから開始
/travel-plan 箱根 1泊2日 カップル   # 条件指定で生成
/vtuber-riona                       # 最新情報を調査
/weekly-digest                      # 過去7日間のダイジェスト
/weekly-digest 14                   # 過去14日間のダイジェスト
```

### ユーティリティスキル

| スキル | 概要 |
|---|---|
| `/serve-reports` | `reports/` の Web ビューアを起動（デフォルト: port 8080） |
| `/stop-reports` | ビューアを停止 |
| `/daily-routine` | 複数レポートスキルを一括並列実行 |
| `/cleanup-reports` | 古いレポートを月別ダイジェストに整理 |

### レポート系スキルを新規追加するときの手順

1. `.claude/skills/<skill-name>/SKILL.md` を作成（テンプレート参照）
2. HTML 出力先を `reports/<skill-name>-YYYY-MM-DD.html` に統一する
3. HTML テンプレート内に `<div class="summary">` を含める（ビューア一覧のプレビューに使われる）
4. `scripts/serve-reports.py` の `CATEGORIES` 辞書にエントリを追加する:
   ```python
   CATEGORIES = {
       "ai-report":             ("AI動向レポート", "🤖", False),
       "trading-card-release":  ("トレカ新発売情報", "🃏", False),
       "restock-watch":         ("再販ウォッチ", "🔄", False),
       "fashion-report":        ("ファッションレポート", "👗", True),
       "travel-plan":           ("国内旅行プラン", "✈️", True),
       "vtuber-riona":          ("VTuber推し活", "🎀", True),
       "gift-concierge":        ("プレゼント提案", "🎁", False),
       "<skill-name>":          ("<表示名>", "<絵文字>", False),  # ← 追加
   }
   ```
   第3要素はプライベートフラグ（`True` の場合、プライベートトグルOFF時に非表示）
5. CLAUDE.md のスキル一覧テーブルにも行を追加する
6. `/serve-reports` で一覧表示・検索・フィルタが正しく動作することを確認する

### レポートビューア (`/serve-reports`) の機能

**3つのビュー（タブ切替）:**
- **ダッシュボード**: 統計カード、ピン留めレポート、各カテゴリの最新レポート、最近のレポート一覧
- **ブラウズ**: カテゴリ別・日付別のグループ表示（従来のビューを強化）
- **検索**: レポート本文の全文検索（サーバーサイド横断検索）

**ブラウズビューの機能:**
- **カテゴリ別グループ表示**: `CATEGORIES` に定義された種別で自動分類（折りたたみ可能）
- **日付別サブグループ**: ファイル名の `YYYY-MM-DD` を自動検出
- **ファイル名フィルタ**: サイドバーの検索ボックスでリアルタイム絞り込み
- **カテゴリフィルタ**: カテゴリボタンで種別切り替え
- **お気に入りフィルタ**: お気に入り登録したレポートだけを表示
- **概要プレビュー**: `.summary` 要素の先頭テキストを一覧に表示
- **リスト/グリッド切替**: 表示モード変更
- **プライベートトグル**: プライベートカテゴリの表示/非表示（localStorage で記憶）

**カードごとの機能:**
- **お気に入り** (⭐): クリックでトグル。お気に入りフィルタで一括表示
- **ピン留め** (📌): ダッシュボードのピン留めセクションに固定表示
- **タグ** (🏷): 自由にタグを追加・削除。カード上にバッジ表示
- **メモ** (📝): レポートごとにテキストメモを保存
- **比較選択** (☐): 2件選択して差分比較（unified diff）
- **削除** (🗑): 確認ダイアログ付きの削除

**一括操作:**
- **ZIPエクスポート**: 選択したレポートをZIPファイルでダウンロード
- **差分比較**: 2件選択して本文テキストのunified diffを表示

**ウォッチリスト + アラート:**
- サイドバーからキーワードを登録（例: `2002R`, `ポケモンカード`, `GPT-5`）
- ダッシュボードに「ウォッチリストアラート」セクションが表示され、登録キーワードにマッチしたレポートをハイライト
- ウォッチリストは `reports/.metadata.json` の `watchlist` キーに保存

**プロフィール設定:**
- サイドバーの「プロフィール編集」からユーザー情報を登録（性別・年代・体型・スタイル・靴サイズ・予算・興味・出発地）
- `config/profile.json` に保存
- ヒアリング系スキル（fashion-report, travel-plan, gift-concierge）がプロフィールを参照し、設定済みの項目はヒアリングをスキップ

**データ永続化:**
- お気に入り・ピン・タグ・メモ・ウォッチリストは `reports/.metadata.json` にサーバーサイドで保存
- プロフィールは `config/profile.json` に保存
- プライベートトグル状態・アクティブビュー・サイドバー折りたたみ状態は localStorage に保存

### スケジューラー (`scripts/scheduler.sh`)

マルチスキル対応のデイリースケジューラー。

```bash
bash scripts/scheduler.sh           # デーモンモード（常駐）
bash scripts/scheduler.sh --once    # 全スキルを即時実行してテスト
bash scripts/scheduler.sh --list    # スケジュール一覧を表示
```

スケジュールは `SCHEDULE` 配列で定義:
```bash
SCHEDULE=(
  "08:00 ai-report"
  "08:05 trading-card-release"
  "09:00 restock-watch"
)
```

macOS の launchd で自動起動する場合:
```bash
# plist の __REPO_DIR__ を実際のパスに置換してインストール
sed "s|__REPO_DIR__|$(pwd)|g" scripts/com.autodailytask.scheduler.plist \
  > ~/Library/LaunchAgents/com.autodailytask.scheduler.plist
launchctl load ~/Library/LaunchAgents/com.autodailytask.scheduler.plist
```

## コンテキスト管理のベストプラクティス

- スキル間で共有するデータは `tasks/templates/` に置く
- セッションをまたぐ状態は `tasks/` 以下のファイルに永続化する
- コンテキストが 70% を超えたら `/clear` で新セッションを始める
- 大きな調査タスクはサブエージェントに委譲してメインコンテキストを節約する
