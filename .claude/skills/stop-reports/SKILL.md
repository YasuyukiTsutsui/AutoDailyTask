---
name: stop-reports
description: |
  serve-reportsで起動したレポートビューアWebサーバーを停止する。
  引数にポート番号を渡せる（デフォルト: 8080）。
disable-model-invocation: false
user-invocable: true
allowed-tools:
  - Bash
---

## 目的

`/serve-reports` で起動したレポートビューア Web サーバーを停止する。

## 手順

1. `$ARGUMENTS` にポート番号が指定されていればそれを使う。なければ `8080` をデフォルトとする。
2. `lsof -i :$PORT -t` で該当ポートのプロセスを確認する。
3. プロセスが見つかった場合は `kill` で停止し、停止完了を案内する。
4. プロセスが見つからない場合は、既に停止済みである旨を案内する。

## 入力

- `$ARGUMENTS`: ポート番号（省略時 `8080`）

## 出力

- サーバープロセスの停止結果を表示する
