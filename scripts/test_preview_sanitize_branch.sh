#!/usr/bin/env bash
# Minimal unit-style test for preview-sanitize-branch.sh.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
SCRIPT="$HERE/preview-sanitize-branch.sh"

pass=0; fail=0
expect() {
  local input="$1" want="$2"
  local got
  got=$(bash "$SCRIPT" "$input" 2>/dev/null || true)
  if [ "$got" = "$want" ]; then
    pass=$((pass+1))
  else
    fail=$((fail+1))
    printf 'FAIL: input=%q want=%q got=%q\n' "$input" "$want" "$got" >&2
  fi
}

expect "feature/foo/bar-baz"            "foo-bar-baz"
expect "chore/RENAME_THIS"               "rename-this"
expect "ALLCAPS"                         "allcaps"
expect "feature/jenkins-cicd/preview"    "jenkins-cicd-preview"
expect "fix/abc_def"                     "abc-def"

# Empty / pathological inputs
got=$(bash "$SCRIPT" "" 2>/dev/null || echo "<error>")
if [ "$got" = "<error>" ]; then pass=$((pass+1)); else fail=$((fail+1)); echo "FAIL: empty input should error" >&2; fi
got=$(bash "$SCRIPT" "////" 2>/dev/null || echo "<error>")
if [ "$got" = "<error>" ]; then pass=$((pass+1)); else fail=$((fail+1)); echo "FAIL: slashes-only should error" >&2; fi

echo "$pass passed, $fail failed"
exit $fail
