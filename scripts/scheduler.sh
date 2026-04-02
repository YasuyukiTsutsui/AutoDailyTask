#!/usr/bin/env bash
# scheduler.sh
# バックグラウンドで動作するシンプルなデイリースケジューラー
#
# 使用方法:
#   # フォアグラウンド実行
#   bash scripts/scheduler.sh
#
#   # バックグラウンド実行（ログをファイルに記録）
#   nohup bash scripts/scheduler.sh > .claude/logs/scheduler.log 2>&1 &
#   echo $! > .claude/logs/scheduler.pid
#
#   # 停止
#   kill $(cat .claude/logs/scheduler.pid)

set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
CLAUDE_BIN="${CLAUDE_BIN:-/opt/node22/bin/claude}"
LOG_DIR="$REPO_DIR/.claude/logs"
TARGET_HOUR=8      # 実行時刻（時）
TARGET_MIN=0       # 実行時刻（分）
TIMEZONE="Asia/Tokyo"

mkdir -p "$LOG_DIR"

log() {
  echo "[$(TZ="$TIMEZONE" date '+%Y-%m-%d %H:%M:%S JST')] $*"
}

log "スケジューラー起動: 毎日 $(printf '%02d:%02d' $TARGET_HOUR $TARGET_MIN) JST に /ai-report を実行"
log "リポジトリ: $REPO_DIR"
log "Claude CLI: $CLAUDE_BIN"
log "停止するには Ctrl+C またはプロセスをkillしてください"

# 次回実行時刻までの待機秒数を計算
seconds_until_target() {
  local now_epoch
  local target_epoch
  now_epoch=$(TZ="$TIMEZONE" date +%s)

  # 今日のターゲット時刻のepoch
  local today
  today=$(TZ="$TIMEZONE" date '+%Y-%m-%d')
  target_epoch=$(TZ="$TIMEZONE" date -d "$today $(printf '%02d:%02d:00' $TARGET_HOUR $TARGET_MIN)" +%s 2>/dev/null \
    || TZ="$TIMEZONE" date -j -f "%Y-%m-%d %H:%M:%S" "$today $(printf '%02d:%02d:00' $TARGET_HOUR $TARGET_MIN)" +%s 2>/dev/null)

  local diff=$(( target_epoch - now_epoch ))

  # すでに今日の時刻を過ぎていれば翌日分を計算
  if [ "$diff" -le 0 ]; then
    diff=$(( diff + 86400 ))
  fi

  echo "$diff"
}

run_report() {
  local run_date
  run_date=$(TZ="$TIMEZONE" date '+%Y-%m-%d')
  local log_file="$LOG_DIR/ai-report-$run_date.log"

  log "▶ /ai-report 実行開始 (ログ: $log_file)"

  cd "$REPO_DIR"
  if "$CLAUDE_BIN" --print "/ai-report" >> "$log_file" 2>&1; then
    log "✅ /ai-report 完了"
  else
    log "❌ /ai-report 失敗 (exit: $?). ログを確認してください: $log_file"
  fi
}

# メインループ
while true; do
  wait_sec=$(seconds_until_target)
  next_time=$(TZ="$TIMEZONE" date -d "+${wait_sec} seconds" '+%Y-%m-%d %H:%M:%S' 2>/dev/null \
    || TZ="$TIMEZONE" date -v "+${wait_sec}S" '+%Y-%m-%d %H:%M:%S' 2>/dev/null \
    || echo "（計算中）")

  log "次回実行まで ${wait_sec}秒 待機... (予定: $next_time JST)"
  sleep "$wait_sec"

  run_report
done
