#!/usr/bin/env bash
# upload-to-slack.sh
# 指定されたHTMLファイルをSlackチャンネルにアップロードする
#
# 使用方法:
#   bash scripts/upload-to-slack.sh <file_path> [initial_comment]
#
# 必要な環境変数:
#   SLACK_BOT_TOKEN  - Slack Bot User OAuth Token (xoxb-...)
#   SLACK_CHANNEL_ID - アップロード先チャンネルID (C...)
#
# 依存: curl, python3

set -euo pipefail

# ── 引数チェック ────────────────────────────────────────────
FILE_PATH="${1:-}"
INITIAL_COMMENT="${2:-📊 生成AI最新動向レポートが更新されました}"

if [[ -z "$FILE_PATH" ]]; then
  echo "❌ エラー: ファイルパスを指定してください" >&2
  echo "使用方法: bash scripts/upload-to-slack.sh <file_path>" >&2
  exit 1
fi

if [[ ! -f "$FILE_PATH" ]]; then
  echo "❌ エラー: ファイルが見つかりません: $FILE_PATH" >&2
  exit 1
fi

# ── 環境変数チェック ────────────────────────────────────────
if [[ -z "${SLACK_BOT_TOKEN:-}" ]]; then
  echo "❌ エラー: 環境変数 SLACK_BOT_TOKEN が設定されていません" >&2
  echo "  .env ファイルに SLACK_BOT_TOKEN=xoxb-... を設定してください" >&2
  exit 1
fi

if [[ -z "${SLACK_CHANNEL_ID:-}" ]]; then
  echo "❌ エラー: 環境変数 SLACK_CHANNEL_ID が設定されていません" >&2
  echo "  .env ファイルに SLACK_CHANNEL_ID=C... を設定してください" >&2
  exit 1
fi

# ── .env の自動読み込み（存在する場合）─────────────────────
if [[ -f ".env" ]]; then
  set -o allexport
  # shellcheck disable=SC1091
  source ".env"
  set +o allexport
fi

FILENAME=$(basename "$FILE_PATH")
FILE_SIZE=$(wc -c < "$FILE_PATH" | tr -d ' ')
SLACK_API="https://slack.com/api"

echo "📤 Slackへのアップロードを開始します..."
echo "   ファイル: $FILENAME ($FILE_SIZE bytes)"
echo "   チャンネル: $SLACK_CHANNEL_ID"

# ── Step 1: アップロードURLの取得 ───────────────────────────
echo ""
echo "🔗 Step 1/3: アップロードURL取得..."

UPLOAD_URL_RESPONSE=$(curl -s -X POST "${SLACK_API}/files.getUploadURLExternal" \
  -H "Authorization: Bearer ${SLACK_BOT_TOKEN}" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data-urlencode "filename=${FILENAME}" \
  --data-urlencode "length=${FILE_SIZE}")

# レスポンスの検証
OK=$(echo "$UPLOAD_URL_RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('ok', False))" 2>/dev/null || echo "false")

if [[ "$OK" != "True" ]]; then
  ERROR=$(echo "$UPLOAD_URL_RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('error', 'unknown'))" 2>/dev/null || echo "parse error")
  echo "❌ アップロードURL取得に失敗しました: $ERROR" >&2
  echo "レスポンス: $UPLOAD_URL_RESPONSE" >&2
  exit 1
fi

UPLOAD_URL=$(echo "$UPLOAD_URL_RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['upload_url'])")
FILE_ID=$(echo "$UPLOAD_URL_RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['file_id'])")

echo "   ✅ URL取得成功 (file_id: $FILE_ID)"

# ── Step 2: ファイルのアップロード ──────────────────────────
echo ""
echo "📁 Step 2/3: ファイルをアップロード中..."

UPLOAD_RESPONSE=$(curl -s -X POST "$UPLOAD_URL" \
  -H "Content-Type: text/html; charset=utf-8" \
  --data-binary "@${FILE_PATH}")

# アップロードは空レスポンスまたは"OK"を返す場合がある
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$UPLOAD_URL" \
  -H "Content-Type: text/html; charset=utf-8" \
  --data-binary "@${FILE_PATH}" 2>/dev/null || echo "0")

# 200系ステータスコードなら成功とみなす
if [[ "$HTTP_STATUS" -ge 200 && "$HTTP_STATUS" -lt 300 ]] || [[ -z "$UPLOAD_RESPONSE" ]] || [[ "$UPLOAD_RESPONSE" == "OK" ]]; then
  echo "   ✅ アップロード完了"
else
  echo "   ⚠️  アップロードレスポンス: $UPLOAD_RESPONSE"
fi

# ── Step 3: アップロード完了 & チャンネル投稿 ────────────────
echo ""
echo "📨 Step 3/3: チャンネルへ投稿..."

COMPLETE_PAYLOAD=$(python3 -c "
import json, sys
payload = {
    'files': [{'id': '$FILE_ID'}],
    'channel_id': '$SLACK_CHANNEL_ID',
    'initial_comment': '${INITIAL_COMMENT}'
}
print(json.dumps(payload))
")

COMPLETE_RESPONSE=$(curl -s -X POST "${SLACK_API}/files.completeUploadExternal" \
  -H "Authorization: Bearer ${SLACK_BOT_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "$COMPLETE_PAYLOAD")

COMPLETE_OK=$(echo "$COMPLETE_RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('ok', False))" 2>/dev/null || echo "false")

if [[ "$COMPLETE_OK" != "True" ]]; then
  ERROR=$(echo "$COMPLETE_RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('error', 'unknown'))" 2>/dev/null || echo "parse error")
  echo "❌ チャンネル投稿に失敗しました: $ERROR" >&2
  echo "レスポンス: $COMPLETE_RESPONSE" >&2
  exit 1
fi

echo "   ✅ 投稿成功"
echo ""
echo "🎉 完了: ${FILENAME} を #${SLACK_CHANNEL_ID} にアップロードしました"
