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
│   │   ├── fashion-report/          # ファッションレポート
│   │   ├── travel-plan/             # 国内旅行プラン
│   │   ├── serve-reports/           # レポートビューア起動
│   │   └── stop-reports/            # レポートビューア停止
│   └── docs/
│       └── skill-template.md        # 新規スキル作成テンプレート
├── scripts/
│   ├── html-to-pdf.py               # HTML → PDF 変換（weasyprint）
│   ├── serve-reports.py             # レポートビューア Web サーバー
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
| `/fashion-report` | ファッショントレンド・おすすめコーデ | `fashion-report-YYYY-MM-DD.html` |
| `/travel-plan` | 国内旅行プラン（松竹梅グレード別・ホテル提案） | `travel-plan-YYYY-MM-DD.html` |

```bash
/ai-report                          # 当日分を生成
/ai-report 2026-04-01               # 日付指定
/trading-card-release               # 全タイトル対象
/trading-card-release ポケモンカード # タイトル絞り込み
/fashion-report                     # ヒアリング後にレポート生成
/travel-plan                        # ヒアリングから開始
/travel-plan 箱根 1泊2日 カップル   # 条件指定で生成
```

### ユーティリティスキル

| スキル | 概要 |
|---|---|
| `/serve-reports` | `reports/` の Web ビューアを起動（デフォルト: port 8080） |
| `/stop-reports` | ビューアを停止 |

### レポート系スキルを新規追加するときの手順

1. `.claude/skills/<skill-name>/SKILL.md` を作成（テンプレート参照）
2. HTML 出力先を `reports/<skill-name>-YYYY-MM-DD.html` に統一する
3. HTML テンプレート内に `<div class="summary">` を含める（ビューア一覧のプレビューに使われる）
4. `scripts/serve-reports.py` の `CATEGORIES` 辞書にエントリを追加する:
   ```python
   CATEGORIES = {
       "ai-report":             ("AI動向レポート", "🤖"),
       "trading-card-release":  ("トレカ新発売情報", "🃏"),
       "fashion-report":        ("ファッションレポート", "👗"),
       "travel-plan":           ("国内旅行プラン", "✈️"),
       "<skill-name>":          ("<表示名>", "<絵文字>"),  # ← 追加
   }
   ```
5. CLAUDE.md のスキル一覧テーブルにも行を追加する
6. `/serve-reports` で一覧表示・検索・フィルタが正しく動作することを確認する

### レポートビューア (`/serve-reports`) の機能

- **カテゴリ別グループ表示**: `CATEGORIES` に定義された種別で自動分類（折りたたみ可能）
- **日付別サブグループ**: ファイル名の `YYYY-MM-DD` を自動検出
- **検索**: ファイル名でリアルタイム絞り込み
- **フィルタ**: カテゴリボタンで種別切り替え
- **概要プレビュー**: `.summary` 要素の先頭テキストを一覧に表示
- **リスト/グリッド切替**: 表示モード変更

## コンテキスト管理のベストプラクティス

- スキル間で共有するデータは `tasks/templates/` に置く
- セッションをまたぐ状態は `tasks/` 以下のファイルに永続化する
- コンテキストが 70% を超えたら `/clear` で新セッションを始める
- 大きな調査タスクはサブエージェントに委譲してメインコンテキストを節約する
