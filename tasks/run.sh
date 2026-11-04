#!/bin/bash
# run.sh <name> <brief> <sandbox>  — Sol high worker with the standard prepended
cd "/c/Users/Mohith S/Desktop/take-two"
N="$1"; B="$2"; S="${3:-danger-full-access}"
echo "$(date) start $N" >> work/queue.log
codex exec --skip-git-repo-check -s "$S" -c sandbox_workspace_write.network_access=true -m gpt-6.1-sol -c service_tier=fast -c model_reasoning_effort=high -c 'web_search="live"' --add-dir "E:/DevDrive/switch" -o "work/$N.md" "$(cat tasks/WORKER-STANDARD.md; echo; echo '---'; echo; cat "$B")" < /dev/null > "work/$N.log" 2>&1
echo "$(date) done $N exit=$?" >> work/queue.log
