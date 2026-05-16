#!/usr/bin/env bash
# Turn a raw branch name into a DNS-/compose-safe slug for preview stacks.
#   feature/foo/bar-baz  -> foo-bar-baz
#   chore/RENAME_THIS    -> rename-this
#   ALLCAPS              -> allcaps
# Empty input or input that sanitises to empty exits non-zero.
set -euo pipefail

raw="${1:-}"
if [ -z "$raw" ]; then
  echo "" >&2
  exit 2
fi

slug=$(printf '%s' "$raw" \
  | tr '[:upper:]' '[:lower:]' \
  | sed -E 's#^(feature|fix|chore|docs|refactor|test|ci|build|perf)/##' \
  | sed -E 's#[^a-z0-9-]+#-#g' \
  | sed -E 's#^-+##; s#-+$##' \
  | cut -c1-40)

if [ -z "$slug" ]; then
  exit 2
fi

printf '%s\n' "$slug"
