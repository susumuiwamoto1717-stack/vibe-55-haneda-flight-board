#!/bin/bash
# 羽田ダイヤを一定間隔で自動更新し続ける常駐スクリプト。
# ターミナルでこのフォルダに入り  bash auto_update.sh  で起動。
# Ctrl+C で停止。ターミナルのセッション権限で動くので Documents の
# TCC(プライバシー保護)に引っかからず、launchd より確実。
#
# 更新間隔（秒）。既定=600秒(10分)。欠航/遅延理由は運航時刻に近づくと
# 埋まるので、日中は10分ごと更新でだいたい拾える。
INTERVAL="${1:-600}"

cd "$(dirname "$0")" || exit 1
echo "▶ 羽田ダイヤ自動更新を開始（${INTERVAL}秒ごと / 停止=Ctrl+C）"

while true; do
  echo "----- $(date '+%Y-%m-%d %H:%M:%S') 更新 -----"
  python3 fetch_haneda.py
  # 機材キーがあれば機種も付与（無ければスキップ）
  if [ -n "$AERODATABOX_KEY" ] || [ -f aerodatabox_key.txt ]; then
    python3 fetch_aircraft.py
  fi
  sleep "$INTERVAL"
done
