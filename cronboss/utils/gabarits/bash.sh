#!/bin/bash
set -euo pipefail
# -e : stoppe au premier échec
# -u : erreur si variable non définie
# -o pipefail : propage les erreurs dans les pipes

LOG_FILE="/var/log/cronhub/$(basename $0).log"
mkdir -p "$(dirname "$LOG_FILE")"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 🚀 Début du job $0" | tee -a "$LOG_FILE"

if ! your_command_here >>"$LOG_FILE" 2>&1; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ❌ Échec du job $0" | tee -a "$LOG_FILE"
    exit 1
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✅ Succès du job $0" | tee -a "$LOG_FILE"
exit 0
