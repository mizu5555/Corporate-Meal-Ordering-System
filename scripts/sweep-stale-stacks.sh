#!/usr/bin/env bash
# Sweep: drop deploy stacks whose corresponding PR is CLOSED or MERGED.
# OPEN or unknown -> leave alone. Never touches stable stacks (main/staging/prod).
set -euo pipefail

PROJECT_PREFIX="${PROJECT_PREFIX:-mealorder}"

# Resolve owner/repo once so we can query the PR API by branch name.
# `gh api ... ?head=owner:branch` finds PRs even after the branch has been
# deleted (which happens automatically on `gh pr merge --delete-branch`).
# `gh pr list --head <deleted-branch>` returns empty and breaks cleanup.
REPO=$(gh repo view --json nameWithOwner --jq '.nameWithOwner' 2>/dev/null || echo "")
OWNER="${REPO%%/*}"

PROJECTS=$(docker compose ls --filter name=${PROJECT_PREFIX}- --format json \
  | jq -r --arg p "$PROJECT_PREFIX" '
      .[]
      | select(.Name != ($p + "-main"))
      | select(.Name != ($p + "-staging"))
      | select(.Name != ($p + "-prod"))
      | .Name')

for proj in $PROJECTS; do
  BRANCH=$(docker ps -a --filter "label=mealorder.branch" \
    --filter "label=com.docker.compose.project=$proj" \
    --format '{{.Label "mealorder.branch"}}' | head -n1)

  if [ -z "$BRANCH" ]; then
    echo "[skip] $proj has no mealorder.branch label, leaving alone"
    continue
  fi

  STATE="UNKNOWN"
  if [ -n "$REPO" ] && [ -n "$OWNER" ]; then
    STATE=$(gh api "repos/${REPO}/pulls?state=all&head=${OWNER}:${BRANCH}&per_page=100" \
      --jq 'if length == 0 then "UNKNOWN"
            elif any(.state == "open") then "OPEN"
            else (.[0] | if .merged_at then "MERGED" else "CLOSED" end)
            end' 2>/dev/null || echo "UNKNOWN")
  fi

  case "$STATE" in
    CLOSED|MERGED)
      echo "[drop] $proj (branch=$BRANCH state=$STATE)"
      docker compose -p "$proj" down -v --remove-orphans
      ;;
    OPEN)
      echo "[keep] $proj (branch=$BRANCH state=OPEN)"
      ;;
    *)
      echo "[skip] $proj (branch=$BRANCH state=$STATE) — not touching"
      ;;
  esac
done
