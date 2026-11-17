#!/usr/bin/env bash
# Settings and helpers of the Windows parts of tools/wsl. A script sources this file. It is not meant to run alone.
#
# WSL_DISTRO: the WSL2 distribution (default: Ubuntu).
# TOOLS_DIR: the folder of the tools in the Linux home folder (default: .cache/marketplace-tools).
# WSL_UNC_ROOT: the Windows path of the root folder of the distribution (default: //wsl.localhost/<distribution>).

WSL_DISTRO=${WSL_DISTRO:-Ubuntu}
TOOLS_DIR=${TOOLS_DIR:-.cache/marketplace-tools}
WSL_UNC_ROOT=${WSL_UNC_ROOT-//wsl.localhost/$WSL_DISTRO}
TOOLS_HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

# Run a command in WSL2. It starts in the Linux home folder, so no command starts on a Windows drive.
# Git Bash changes an argument that starts with "/" to a Windows path. The two variables keep each Linux path as it is.
in_wsl() {
    MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL='*' wsl.exe -d "$WSL_DISTRO" --cd '~' -e "$@"
}

# Print the Linux path of the tools folder.
linux_tools() {
    local home
    home=$(in_wsl sh -c 'printf %s "$HOME"' | tr -d '\r')
    [ -n "$home" ] || { echo "STOP: cannot read the home folder of WSL2 distribution $WSL_DISTRO" >&2; return 3; }
    printf '%s/%s\n' "$home" "$TOOLS_DIR"
}

# Print the Windows path of a Linux path.
unc() {
    printf '%s%s\n' "$WSL_UNC_ROOT" "$1"
}

# Copy one file of tools/wsl/linux into <tools folder>/bin of WSL2 through a pipe, and print its Linux path.
# The copy goes to a new file first, and a rename puts it in place. A run that reads the old file then reads it to the end.
put_linux_part() {
    local tools=$1 name=$2
    in_wsl sh -c 'mkdir -p "$1/bin" && cat > "$1/bin/$2.$$" && mv -f "$1/bin/$2.$$" "$1/bin/$2"' sh "$tools" "$name" \
        < "$TOOLS_HERE/linux/$name"
    printf '%s/bin/%s\n' "$tools" "$name"
}

# Run a Linux part in WSL2 with the PATH of a login shell. The part runs in a child bash, so its exit code
# passes through: an "exit" in a login shell runs ~/.bash_logout, and that can change the exit code.
run_linux_part() {
    in_wsl bash -lc 'bash "$0" "$@"' "$@"
}

# Print a name for a file from a ref: each character other than a letter, a digit, ".", "_", or "-" becomes "_".
slug() {
    printf '%s' "$1" | tr -c 'A-Za-z0-9._-' '_'
}
