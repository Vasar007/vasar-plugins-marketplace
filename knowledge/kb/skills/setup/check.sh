#!/usr/bin/env bash
# Print the OS and one line for each missing piece of the KB wiring. Change nothing. Always exit 0.
settings="$HOME/.claude/settings.json"
global_md="$HOME/.claude/CLAUDE.md"

case "$(uname -s 2>/dev/null)" in
  MINGW*|MSYS*|CYGWIN*) os=windows ;;
  Darwin) os=macos ;;
  *) os=linux ;;
esac
echo "OS: $os"

missing() { echo "MISSING: $1"; count=$((count + 1)); }
count=0

kb=""
for d in "$KB_DIR" "$HOME/projects/KB" "$HOME/Documents/GitHub/KB" "${CLAUDE_PROJECT_DIR:-$PWD}" "${CLAUDE_PROJECT_DIR:-$PWD}/KB"; do
  if [ -n "$d" ] && [ -f "$d/_claude/RULES.md" ]; then kb="$d"; break; fi
done
kb_fwd="${kb//\\//}"

if [ -z "$kb" ]; then
  missing "KB clone: no folder with _claude/RULES.md found. Clone the KB repository."
fi
if ! grep -qs '"KB_DIR"' "$settings"; then
  missing "KB_DIR: not set in the env block of $settings."
fi
if ! grep -qsF 'Bash(bash _claude/tools/kb-search.sh *)' "$settings"; then
  missing "allow rule: Bash(bash _claude/tools/kb-search.sh *) is not in permissions.allow in $settings."
fi
if [ "$os" = windows ] && [ -n "$kb" ] && ! grep -qsF "$kb_fwd" "$settings"; then
  missing "additionalDirectories: $kb_fwd is not in permissions.additionalDirectories in $settings."
fi
if ! grep -qsE '^@.*/_claude/CLAUDE\.global\.md' "$global_md"; then
  missing "import line: @.../_claude/CLAUDE.global.md is not in $global_md."
fi
if ! grep -qsE '^@.*/_claude/RULES\.md' "$global_md"; then
  missing "import line: @.../_claude/RULES.md is not in $global_md."
fi
if ! grep -qs '^KB root:' "$global_md"; then
  missing "KB root line: a line starting with 'KB root:' is not in $global_md."
fi

if [ "$os" = windows ]; then
  if ! MSYS_NO_PATHCONV=1 schtasks.exe /Query /TN kb-sync >/dev/null 2>&1; then
    missing "sync timer: the Task Scheduler task kb-sync does not exist."
  fi
else
  if ! crontab -l 2>/dev/null | grep -qF 'kb-sync.sh'; then
    missing "sync timer: no cron line with kb-sync.sh."
  fi
fi

if [ -n "$kb" ] && [ "$(git -C "$kb" config core.hooksPath 2>/dev/null)" != "_claude/git-hooks" ]; then
  missing "core.hooksPath: not _claude/git-hooks in the KB clone."
fi
if [ "$os" = windows ] && [ "$(git config --global core.longpaths 2>/dev/null)" != "true" ]; then
  missing "core.longpaths: not true in the global git configuration."
fi
for key in git-sync.syncEnabled git-sync.syncNewFiles; do
  if [ "$(git config --global "$key" 2>/dev/null)" != "true" ]; then
    missing "$key: not true in the global git configuration."
  fi
done

[ "$count" -eq 0 ] && echo "All pieces are in place."
exit 0
