#!/usr/bin/env bash
# Print the OS, one line for each missing piece, and one line for each stale rule of the KB wiring. Change nothing. Always exit 0.
settings="$HOME/.claude/settings.json"
global_md="$HOME/.claude/CLAUDE.md"

case "$(uname -s 2>/dev/null)" in
  MINGW*|MSYS*|CYGWIN*) os=windows ;;
  Darwin) os=macos ;;
  *) os=linux ;;
esac
echo "OS: $os"

missing() { echo "MISSING: $1"; count=$((count + 1)); }
stale() { echo "STALE: $1"; count=$((count + 1)); }
count=0

settings_kb_dir="$(grep -o '"KB_DIR" *: *"[^"]*"' "$settings" 2>/dev/null | sed 's/^[^:]*: *"//; s/"$//; s#\\\\#/#g')"
kb=""
for d in "$settings_kb_dir" "$KB_DIR" "$HOME/projects/KB" "$HOME/Documents/GitHub/KB" "${CLAUDE_PROJECT_DIR:-$PWD}" "${CLAUDE_PROJECT_DIR:-$PWD}/KB"; do
  if [ -n "$d" ] && [ -f "$d/_claude/RULES.md" ]; then kb="$d"; break; fi
done
# A path rule names only the clone that a full KB_DIR names. The project folder, the default places, and a relative KB_DIR never give a path rule.
kb_named=""
for d in "$settings_kb_dir" "$KB_DIR"; do
  case "$d" in
    /*|[A-Za-z]:[\\/]*) if [ -f "$d/_claude/RULES.md" ]; then kb_named="$d"; break; fi ;;
  esac
done
[ -n "$kb_named" ] && kb="$kb_named"
kb_fwd=""
[ -n "$kb" ] && kb_fwd="$(cd "$kb" && (pwd -W 2>/dev/null || pwd))"
kb_fwd="${kb_fwd//\\//}"

if [ -z "$kb" ]; then
  missing "KB clone: no folder with _claude/RULES.md found. Clone the KB repository."
fi
if [ -z "$settings_kb_dir" ]; then
  missing "KB_DIR: not set in the env block of $settings."
elif [ ! -f "$settings_kb_dir/_claude/RULES.md" ]; then
  missing "KB_DIR: $settings_kb_dir has no _claude/RULES.md. Set it to the KB clone."
fi
rule_lists="$(tr -d '\r\n' 2>/dev/null < "$settings")"
entries='\[[[:space:]]*("([^"\\]|\\.)*"[[:space:]]*,?[[:space:]]*)*\]'
allow="$(printf '%s' "$rule_lists" | grep -oE "\"allow\" *: *$entries")"
ask="$(printf '%s' "$rule_lists" | grep -oE "\"ask\" *: *$entries")"
has_rule() { printf '%s' "$1" | grep -qF -- "\"$2\""; }
# On Windows the drive letter can differ in case, so a path rule also passes with a lower-case drive letter.
kb_alt="$(printf '%s' "${kb_fwd:0:1}" | tr 'A-Z' 'a-z')${kb_fwd:1}"
has_path_rule() {
  has_rule "$1" "$2" && return 0
  [ "$os" = windows ] && has_rule "$1" "${2//"$kb_fwd"/"$kb_alt"}"
}
# Older versions printed these rules with a relative path, which matches the script of that path in every project.
# Only these files of the clone tell a session which command to run.
first_relative_call() {
  [ -n "$kb_named" ] || return 0
  for file in _claude/RULES.md _claude/capture.md _claude/close-task.md _claude/hooks/session-start.sh _claude/hooks/subagent-start.sh; do
    if [ -f "$kb_named/$file" ] && grep -qF -- "$1" "$kb_named/$file" 2>/dev/null; then
      echo "$file"
      return 0
    fi
  done
}
for rule in 'Bash(bash _claude/tools/kb-search.sh *)' 'Bash(python3 -B _claude/tools/ste-check.py *)' 'Bash(python3 -B _claude/tools/md-check.py *)'; do
  if has_rule "$allow" "$rule"; then
    call="${rule#Bash(}"
    call="${call% \*)}"
    caller="$(first_relative_call "$call")"
    advice="Remove it."
    [ -n "$caller" ] && advice="Keep it for now: $caller still calls the script with a relative path."
    stale "allow rule: $rule is in permissions.allow in $settings. Its relative path matches a script in any project. $advice"
  fi
done
if [ -n "$kb_named" ]; then
  # A space or a * in the path changes what a Bash rule matches, so such a path gets no script rule.
  case "$kb_fwd" in
    *[!A-Za-z0-9._/:~-]*)
      missing "allow rules: the clone path $kb_fwd has a character that is not an ASCII letter (A to Z, a to z), a digit, or one of . _ / : ~ -. No script rule is printed for it. Move the clone to a path with only these characters."
      ;;
    *)
      for rule in "Bash(bash $kb_fwd/_claude/tools/kb-search.sh *)" "Bash(python3 -B $kb_fwd/_claude/tools/ste-check.py *)" "Bash(python3 -B $kb_fwd/_claude/tools/md-check.py *)"; do
        if ! has_path_rule "$allow" "$rule"; then
          missing "allow rule: $rule is not in permissions.allow in $settings."
        fi
      done
      ;;
  esac
  for sub in status log show; do
    rule="Bash(git -C $kb_fwd $sub *)"
    if ! has_path_rule "$allow" "$rule"; then
      missing "allow rule: $rule is not in permissions.allow in $settings."
    fi
  done
  rule="Bash(git -C $kb_fwd * --output*)"
  if ! has_path_rule "$ask" "$rule"; then
    missing "ask rule: $rule is not in permissions.ask in $settings."
  fi
elif [ -n "$kb" ]; then
  missing "allow rules: the clone $kb_fwd is not the clone that KB_DIR names, so no path rule is printed for it. Set KB_DIR to the full path of the KB clone, then run the setup again."
fi
dirs="$(tr -d '\r\n' 2>/dev/null < "$settings" | grep -o '"additionalDirectories" *: *\[[^]]*\]' | sed 's#\\\\#/#g')"
if [ "$os" = windows ] && [ -n "$kb" ] && ! printf '%s' "$dirs" | grep -qiF "\"$kb_fwd\""; then
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
