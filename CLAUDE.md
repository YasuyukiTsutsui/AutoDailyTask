# AutoDailyTask — Claude Code Skills による日常タスク自動化

## プロジェクト概要

Claude Code Skills（カスタムスラッシュコマンド）を使って日常タスクを自動化するリポジトリ。
各タスクは `.claude/skills/<skill-name>/SKILL.md` として定義し、`/skill-name` で呼び出す。

## ディレクトリ構造

```
AutoDailyTask/
├── CLAUDE.md                        # このファイル
├── README.md                        # 人向けドキュメント
├── .claude/
│   ├── settings.json                # Hooks 設定
│   ├── skills/
│   │   ├── daily-report/            # 例: 日次レポート生成
│   │   │   └── SKILL.md
│   │   └── standup/                 # 例: スタンドアップメモ作成
│   │       └── SKILL.md
│   └── docs/
│       └── skill-template.md        # 新規スキル作成テンプレート
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

## コンテキスト管理のベストプラクティス

- スキル間で共有するデータは `tasks/templates/` に置く
- セッションをまたぐ状態は `tasks/` 以下のファイルに永続化する
- コンテキストが 70% を超えたら `/clear` で新セッションを始める
- 大きな調査タスクはサブエージェントに委譲してメインコンテキストを節約する
