#!/usr/bin/env bash
# Run one KB hook from the local KB clone. If no clone is found, exit 0 so that no session breaks.
name="$1"
find_kb() {
  if [ -n "$KB_DIR" ] && [ -f "$KB_DIR/_claude/RULES.md" ]; then printf '%s' "$KB_DIR"; return; fi
  base="${CLAUDE_PROJECT_DIR:-$PWD}"
  for d in "$base" "$base"/*; do
    if [ -f "$d/_claude/RULES.md" ]; then printf '%s' "$d"; return; fi
  done
}
kb="$(find_kb)"
if [ -z "$kb" ]; then
  [ "$name" = session-start ] && echo "KB plugin: no KB clone found. Set KB_DIR with /kb:setup."
  exit 0
fi
case "$name" in
  stop) exec bash "$kb/_claude/kb-sync.sh" --if-changed ;;
  *) exec bash "$kb/_claude/hooks/$name.sh" ;;
esac
