#!/usr/bin/env bash
# scheduler.sh
# バックグラウンドで動作するマルチスキル対応デイリースケジューラー
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
#
#   # 全スキルを即時実行してテスト
#   bash scripts/scheduler.sh --once
#
#   # スケジュール一覧を表示
#   bash scripts/scheduler.sh --list

set -euo pipefail

# ---------------------------------------------------------------------------
# スケジュール設定
# Format: "HH:MM skill-name [args]"
# ---------------------------------------------------------------------------
SCHEDULE=(
  "07:00 daily-routine"
)

# ---------------------------------------------------------------------------
# 基本設定
# ---------------------------------------------------------------------------
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
CLAUDE_BIN="${CLAUDE_BIN:-$(command -v claude 2>/dev/null || echo /opt/node22/bin/claude)}"
LOG_DIR="$REPO_DIR/.claude/logs"
TIMEZONE="Asia/Tokyo"
NOTIFY_SCRIPT="$REPO_DIR/scripts/notify.py"

mkdir -p "$LOG_DIR"

# ---------------------------------------------------------------------------
# ユーティリティ関数
# ---------------------------------------------------------------------------
log() {
  echo "[$(TZ="$TIMEZONE" date '+%Y-%m-%d %H:%M:%S JST')] $*"
}

# 現在時刻を HH:MM 形式で取得
current_hhmm() {
  TZ="$TIMEZONE" date '+%H:%M'
}

# 現在の日付を取得
current_date() {
  TZ="$TIMEZONE" date '+%Y-%m-%d'
}

# epoch秒を取得（クロスプラットフォーム）
date_to_epoch() {
  local datestr="$1"
  TZ="$TIMEZONE" date -d "$datestr" +%s 2>/dev/null \
    || TZ="$TIMEZONE" date -j -f "%Y-%m-%d %H:%M:%S" "$datestr" +%s 2>/dev/null
}

# N秒後の日時を取得（クロスプラットフォーム）
date_after_seconds() {
  local secs="$1"
  TZ="$TIMEZONE" date -d "+${secs} seconds" '+%Y-%m-%d %H:%M:%S' 2>/dev/null \
    || TZ="$TIMEZONE" date -v "+${secs}S" '+%Y-%m-%d %H:%M:%S' 2>/dev/null \
    || echo "(calculation pending)"
}

# スケジュールエントリをパースして時刻・スキル名・引数を返す
parse_entry() {
  local entry="$1"
  local time_part="${entry%% *}"
  local rest="${entry#* }"
  local skill_name="${rest%% *}"
  local skill_args=""
  if [ "$rest" != "$skill_name" ]; then
    skill_args="${rest#* }"
  fi
  echo "$time_part" "$skill_name" "$skill_args"
}

# ---------------------------------------------------------------------------
# 次回実行時刻までの待機秒数を計算
# ---------------------------------------------------------------------------
seconds_until_next() {
  local now_epoch
  now_epoch=$(TZ="$TIMEZONE" date +%s)
  local today
  today=$(current_date)
  local min_diff=86400  # 最大1日

  for entry in "${SCHEDULE[@]}"; do
    local time_part
    time_part="${entry%% *}"
    local hh="${time_part%%:*}"
    local mm="${time_part##*:}"

    local target_epoch
    target_epoch=$(date_to_epoch "$today $(printf '%02d:%02d:00' "$((10#$hh))" "$((10#$mm))")")

    local diff=$(( target_epoch - now_epoch ))

    # 今日の時刻を過ぎていれば翌日分を計算
    if [ "$diff" -le 0 ]; then
      diff=$(( diff + 86400 ))
    fi

    if [ "$diff" -lt "$min_diff" ]; then
      min_diff="$diff"
    fi
  done

  echo "$min_diff"
}

# ---------------------------------------------------------------------------
# スキル実行
# ---------------------------------------------------------------------------
run_skill() {
  local skill_name="$1"
  local skill_args="${2:-}"
  local run_date
  run_date=$(current_date)
  local log_file="$LOG_DIR/${skill_name}-${run_date}.log"

  local cmd_str="/$skill_name"
  if [ -n "$skill_args" ]; then
    cmd_str="/$skill_name $skill_args"
  fi

  log "▶ $cmd_str 実行開始 (ログ: $log_file)"

  local exit_code=0
  cd "$REPO_DIR"
  if "$CLAUDE_BIN" --print "$cmd_str" >> "$log_file" 2>&1; then
    log "✅ $cmd_str 完了"
  else
    exit_code=$?
    log "❌ $cmd_str 失敗 (exit: $exit_code). ログを確認してください: $log_file"
  fi

  # 通知スクリプトが存在する場合に通知を送信
  if [ -x "$NOTIFY_SCRIPT" ] || [ -f "$NOTIFY_SCRIPT" ]; then
    local report_file
    report_file="reports/${skill_name}-${run_date}.html"
    local message
    if [ "$exit_code" -eq 0 ]; then
      message="$cmd_str completed successfully"
    else
      message="$cmd_str failed (exit: $exit_code)"
    fi

    local notify_args=("--type" "all" "--message" "$message")
    if [ -f "$REPO_DIR/$report_file" ]; then
      notify_args+=("--file" "$report_file")
    fi

    log "📨 通知送信: $message"
    python3 "$NOTIFY_SCRIPT" "${notify_args[@]}" >> "$log_file" 2>&1 || \
      log "⚠️  通知送信失敗 (スキル実行自体には影響なし)"
  fi

  return "$exit_code"
}

# ---------------------------------------------------------------------------
# --list: スケジュール一覧を表示して終了
# ---------------------------------------------------------------------------
show_list() {
  echo "=== AutoDailyTask スケジュール ==="
  echo ""
  printf "%-8s %-25s %s\n" "時刻" "スキル" "引数"
  printf "%-8s %-25s %s\n" "--------" "-------------------------" "----"
  for entry in "${SCHEDULE[@]}"; do
    read -r time_part skill_name skill_args <<< "$(parse_entry "$entry")"
    printf "%-8s %-25s %s\n" "$time_part" "$skill_name" "$skill_args"
  done
  echo ""
  echo "合計: ${#SCHEDULE[@]} 件"
  exit 0
}

# ---------------------------------------------------------------------------
# --once: 全スキルを即時実行して終了
# ---------------------------------------------------------------------------
run_once() {
  log "=== --once モード: 全スキルを即時実行 ==="
  local total=${#SCHEDULE[@]}
  local success=0
  local fail=0

  for entry in "${SCHEDULE[@]}"; do
    read -r _ skill_name skill_args <<< "$(parse_entry "$entry")"
    if run_skill "$skill_name" "$skill_args"; then
      success=$(( success + 1 ))
    else
      fail=$(( fail + 1 ))
    fi
  done

  log "=== 完了: 成功=$success 失敗=$fail / 合計=$total ==="
  exit "$fail"
}

# ---------------------------------------------------------------------------
# 引数処理
# ---------------------------------------------------------------------------
case "${1:-}" in
  --list)
    show_list
    ;;
  --once)
    run_once
    ;;
  "")
    # 通常のデーモンモード — 下のメインループへ
    ;;
  *)
    echo "Usage: $0 [--once | --list]" >&2
    exit 1
    ;;
esac

# ---------------------------------------------------------------------------
# メインループ（デーモンモード）
# ---------------------------------------------------------------------------
log "スケジューラー起動: ${#SCHEDULE[@]} 件のスキルを管理"
for entry in "${SCHEDULE[@]}"; do
  read -r time_part skill_name skill_args <<< "$(parse_entry "$entry")"
  log "  $time_part  /$skill_name $skill_args"
done
log "リポジトリ: $REPO_DIR"
log "Claude CLI: $CLAUDE_BIN"
log "停止するには Ctrl+C またはプロセスをkillしてください"

# 今日すでに実行済みのスキルを追跡
declare -A LAST_RUN_DATE

while true; do
  local_now=$(current_hhmm)
  local_date=$(current_date)

  for entry in "${SCHEDULE[@]}"; do
    read -r time_part skill_name skill_args <<< "$(parse_entry "$entry")"

    # 今日すでに実行済みならスキップ
    if [ "${LAST_RUN_DATE[$skill_name]:-}" = "$local_date" ]; then
      continue
    fi

    # 現在時刻がスケジュール時刻と一致（分単位）
    if [ "$local_now" = "$time_part" ]; then
      LAST_RUN_DATE[$skill_name]="$local_date"
      # 各スキルを独立して実行（1つの失敗が他に影響しない）
      run_skill "$skill_name" "$skill_args" || true
    fi
  done

  # 次回実行までの待機時間を計算して表示
  wait_sec=$(seconds_until_next)
  next_time=$(date_after_seconds "$wait_sec")
  log "次回実行まで ${wait_sec}秒 待機... (予定: $next_time JST)"

  # 1分未満なら30秒スリープ、それ以外は次回の1分前まで寝る
  if [ "$wait_sec" -le 60 ]; then
    sleep 30
  else
    sleep $(( wait_sec - 30 ))
  fi
done
