---
name: serve-reports
description: |
  レポートビューアWebサーバーを起動する。
  reports/ディレクトリ内のPDF・HTMLをブラウザで閲覧できる。
  引数にポート番号を渡せる（デフォルト: 8080）。
disable-model-invocation: false
user-invocable: true
allowed-tools:
  - Bash
  - Read
---

## 目的

`reports/` に生成されたレポート（PDF・HTML）をブラウザで閲覧するための Web サーバーを起動する。

## 手順

1. `$ARGUMENTS` にポート番号が指定されていればそれを使う。なければ `8080` をデフォルトとする。
2. 既に同じポートでサーバーが起動していないか確認する（`lsof -i :PORT`）。起動中なら URL を案内して終了する。
3. 以下のコマンドでバックグラウンド起動する:

```bash
python3 scripts/serve-reports.py --port $PORT &
```

4. ユーザーに URL (`http://localhost:$PORT`) を案内する。

## 入力

- `$ARGUMENTS`: ポート番号（省略時 `8080`）

## 出力

- Web サーバーが起動し、ブラウザでレポートを閲覧可能になる
- 起動した URL を表示する
