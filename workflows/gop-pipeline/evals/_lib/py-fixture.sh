#!/usr/bin/env bash
# A Python fixture for the gop-work eval cases. A scaffold sources this file after git-fixture.sh.
#
# make_cli_repo: a small command line tool in Python with no solution file, no build step, and no test project.
# main is checked out with one fixture commit and a bare remote. The function does not publish it.
set -euo pipefail

make_cli_repo() {
    fixture_init
    fixture_write .gitignore <<'CLI_EOF'
__pycache__/
*.pyc
CLI_EOF
    fixture_write README.md <<'CLI_EOF'
# greeter

A small command line tool that prints a greeting.

Run it with `python3 cli.py --name Ada`.
CLI_EOF
    fixture_write cli.py <<'CLI_EOF'
"""A command line tool that prints a greeting."""
import argparse


def build_parser():
    parser = argparse.ArgumentParser(description="Print a greeting.")
    parser.add_argument("--name", default="world", help="the name to greet")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    print(f"Hello, {args.name}!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
CLI_EOF
    fixture_commit "add the greeter tool"
    fixture_remote_init
}
