"""Paths and helpers that the repository tests share."""
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

# Keep __pycache__ folders out of the plugin folders, which ship to users.
sys.dont_write_bytecode = True

REPO = Path(__file__).resolve().parent.parent
IN_CI = os.environ.get("CI") == "true"


def tracked_markdown_files():
    """The tracked .md files that are in the work tree, as paths relative to the repository root."""
    out = subprocess.run(["git", "-C", str(REPO), "ls-files", "-z", "--", "*.md"],
                         capture_output=True, text=True, check=True).stdout
    return sorted(p for p in out.split("\0") if p and (REPO / p).is_file())


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def tool_missing(test, message):
    """Skip on a developer machine. Fail in CI, where every tool must exist."""
    if IN_CI:
        test.fail(message)
    test.skipTest(message)
