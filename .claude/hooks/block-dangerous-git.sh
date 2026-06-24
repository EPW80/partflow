#!/bin/bash
# Blocks irreversible/destructive git operations before Claude runs them.
# Customized for PartFlow: plain `git push` is allowed (the phased build pushes
# at each gate); only force-push and history/working-tree-destroying ops are blocked.

INPUT=$(cat)
COMMAND=$(printf '%s' "$INPUT" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("tool_input",{}).get("command",""))' 2>/dev/null)

DANGEROUS_PATTERNS=(
  "git reset --hard"
  "reset --hard"
  "git clean -fd"
  "git clean -f"
  "git branch -D"
  "git checkout \."
  "git restore \."
  "push --force"
  "push -f"
  "force-with-lease"
)

for pattern in "${DANGEROUS_PATTERNS[@]}"; do
  if printf '%s' "$COMMAND" | grep -qE -- "$pattern"; then
    echo "BLOCKED: '$COMMAND' matches dangerous pattern '$pattern'. The user has prevented you from doing this." >&2
    exit 2
  fi
done

exit 0
