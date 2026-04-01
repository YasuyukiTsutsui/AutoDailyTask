# Skill 作成テンプレート

新しいスキルを作成するときはこのテンプレートをコピーして使う。

## ファイル配置

```
.claude/skills/<skill-name>/SKILL.md
```

## SKILL.md テンプレート

```markdown
---
name: skill-name
description: |
  このスキルが何をするかを 1〜2 文で説明する。
  Claude がスラッシュコマンドを選ぶときに使われる（250 文字以内が理想）。
disable-model-invocation: false
user-invocable: true
allowed-tools:
  - Read
  - Grep
# 書き込みが必要な場合のみ追加:
# - Write
# - Edit
# - Bash
paths:
  - tasks/
# コンテキストファイルが必要な場合:
# context:
#   - tasks/templates/my-template.md
---

## 目的

このスキルが解決する問題や達成するゴールを記述する。

## 手順

1. （最初のステップ）
2. （次のステップ）
3. （出力または完了条件）

## 入力

- `$ARGUMENTS`: ユーザーがコマンドに渡す引数（例: タスク名、日付）

## 出力形式

（スキルが生成するファイルや出力の形式を記述する）

## 注意事項

- （副作用や制約があれば記述する）
- ロールバック不能な操作がある場合は `disable-model-invocation: true` にすること
```

---

## フロントマターフィールド一覧

| フィールド | 必須 | 説明 |
|---|---|---|
| `name` | 必須 | スラッシュコマンド名（ケバブケース、64文字以内） |
| `description` | 推奨 | Claude がコマンド選択に使う説明（250文字以内） |
| `disable-model-invocation` | 任意 | `true` にすると Claude が自動起動しない（副作用ある操作に使う） |
| `user-invocable` | 任意 | `false` にするとスラッシュメニューに表示されない（背景知識スキル向け） |
| `allowed-tools` | 推奨 | スキル実行時に許可するツールの一覧（最小権限の原則） |
| `paths` | 任意 | Claude がアクセスしてよいパスの制限 |
| `context` | 任意 | スキル起動時に自動ロードするファイルのリスト |
| `context` (`fork`) | 任意 | `context: fork` でサブエージェントとして実行 |

## disable-model-invocation 判断フロー

```
副作用はあるか?
  ├─ はい → ロールバック可能か?
  │         ├─ いいえ（削除・push・API送信）→ true
  │         └─ はい（上書き可能なファイル生成）→ 状況に応じて true 推奨
  └─ いいえ（読み取り・レポート生成）→ false
```

## スキルのサイズガイドライン

- `SKILL.md`: 500 行以内
- 詳細仕様: `.claude/docs/<skill-name>-detail.md` に分離
- 例・サンプル: `.claude/docs/<skill-name>-examples.md` に分離

## 既存スキルの例

スキルを作成したら `.claude/skills/` に追加し、`CLAUDE.md` の構造セクションも更新する。
