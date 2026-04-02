---
name: daily-routine
description: |
  複数のレポート系スキルを一括で並列実行する。
  引数なしで全レポートスキルを実行。引数にスキル名をカンマ区切りで渡すと指定したものだけ実行。
  「日課」「まとめて実行」「全部レポート出して」などと言われたらこのスキルを使う。
disable-model-invocation: false
user-invocable: true
allowed-tools:
  - Agent
  - Read
  - Bash
  - WebSearch
  - WebFetch
  - Write
  - AskUserQuestion
---

## 目的

毎日のレポート生成タスクをまとめて並列実行し、すべて完了したらレポートビューアを起動する。

## 利用可能なレポートスキル

| スキル名 | 概要 | ヒアリング |
|---|---|---|
| `ai-report` | 生成AI最新動向レポート | 不要 |
| `trading-card-release` | トレカ新発売情報 | 不要 |
| `restock-watch` | 再販・再入荷ウォッチ | 不要 |
| `fashion-report` | ファッショントレンド | 必要（初回のみ） |

## 手順

### Step 1: 実行対象の決定

- `$ARGUMENTS` が空 → ヒアリング不要なスキル（`ai-report`, `trading-card-release`, `restock-watch`）を全て実行対象にする
- `$ARGUMENTS` にスキル名がカンマ区切りで指定されている → 指定されたもののみ実行
- `fashion-report` が対象に含まれる場合、先にヒアリングを完了させてから並列実行に進む

### Step 2: 並列実行

Agent ツールを使い、各レポートスキルと `cleanup-reports` をサブエージェントとして**同時に**起動する。

各サブエージェントには以下を指示する:
- **レポート系**: 対象スキルの SKILL.md を読み込み、その手順に従ってレポートを生成すること。出力先は `reports/<skill-name>-YYYY-MM-DD.html` とすること
- **cleanup-reports**: `.claude/skills/cleanup-reports/SKILL.md` を読み込み、先々月以前のレポートをダイジェスト化すること。削除対象がある場合はファイル一覧をまとめて返すこと（削除自体はメインで確認後に実行する）

**重要**: 複数の Agent 呼び出しを**1つのメッセージ内で同時に**発行すること。順番に実行しない。

### Step 3: 結果報告

全サブエージェントの完了後:
1. 各レポートの生成結果（成功/失敗・ファイルパス）をまとめて報告する
2. `cleanup-reports` で削除対象がある場合、一覧を提示してユーザーに確認する。承認されたら削除を実行する
3. レポートビューアが起動していなければ、起動するか確認する

## 入力

- `$ARGUMENTS`: 実行するスキル名のカンマ区切り（省略時はヒアリング不要な全スキル）

## 使用例

```
/daily-routine                              # ai-report, trading-card-release を並列実行
/daily-routine ai-report                    # ai-report のみ実行
/daily-routine ai-report,trading-card-release,fashion-report  # 全スキル実行（fashion-reportは先にヒアリング）
```
