#!/usr/bin/env bash
# Run one KB hook from the KB clone that KB_DIR names. If there is no such clone, exit 0 so that no session breaks.
# Never look in the project folder: a clone of another repository must not run its own scripts in a session.
name="$1"
kb="${KB_DIR-}"
# A relative path resolves from the project folder, so it names no clone.
case "$kb" in
  /*|[A-Za-z]:[\\/]*) [ -f "$kb/_claude/RULES.md" ] || kb="" ;;
  *) kb="" ;;
esac
if [ -z "$kb" ]; then
  [ "$name" = session-start ] && echo "KB plugin: no KB clone found. Set KB_DIR with /kb:setup."
  exit 0
fi
case "$name" in
  stop) script="$kb/_claude/kb-sync.sh" ;;
  *) script="$kb/_claude/hooks/$name.sh" ;;
esac
if [ ! -f "$script" ]; then
  [ "$name" = session-start ] && echo "KB plugin: the KB clone has no script for $name. Sync the clone."
  exit 0
fi
case "$name" in
  stop) exec bash "$script" --if-changed ;;
  *) exec bash "$script" ;;
esac
