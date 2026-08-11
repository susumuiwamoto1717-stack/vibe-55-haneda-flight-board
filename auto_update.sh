#!/bin/bash
# 羽田ダイヤを一定間隔で自動更新し続ける常駐スクリプト。
# ターミナルでこのフォルダに入り  bash auto_update.sh  で起動。
# Ctrl+C で停止。ターミナルのセッション権限で動くので Documents の
# TCC(プライバシー保護)に引っかからず、launchd より確実。
#
# 更新間隔（秒）。既定=3600秒(1時間)。羽田公式への負荷配慮のため
# 1時間1回を基本とする（本番はGitHub Actionsが毎時更新）。
# 欠航/遅延理由を細かく追いたい時だけ  bash auto_update.sh 600  等で短縮。
INTERVAL="${1:-3600}"

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
