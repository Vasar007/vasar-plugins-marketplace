#!/usr/bin/env python3
"""Compare one `claude plugin eval` suite at a base commit and at a head commit, or record one baseline.

The verdict follows the rules of skill/scripts/compare.py in https://github.com/anthropics/single-agent-loop-kit.
Run the script with --help for the rules and the subcommands.
"""
import argparse
import io
import json
import math
import os
import posixpath
import re
import shlex
import shutil
import statistics
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

ROUTE_PREFIX = "route-"
SCHEMA_VERSION = 1
NOT_RECORDED = "not recorded"
BASELINE_FILE = "baseline.json"
DEPENDENCY_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
REPO = Path(__file__).resolve().parents[2]
# The eval stand-ins live outside the plugins, because the claude.ai sync skips a plugin with a nested manifest.
STUBS = Path("tests/evals/stubs")
STUB_FOLDER = "eval-stubs"

RULES = """\
rules:
  1. Only the cases with scored runs on both sides are compared.
  2. A grader whose name starts with "route-" checks the route, for example
     which agent ran. The report shows it, but it never counts in a score.
  3. A run keeps the score that claude plugin eval gave it. If the run has a
     route grader, the script scores the run again without that grader. A
     run with no grader results, for example after an API error, does not
     count. The report counts the runs that ended with an error, because an
     error can hide the real result.
  4. If a case has scored runs at the base and none at the head, there is no
     verdict yet. If the mean score of the shared cases is lower at the head,
     the change does not hold. If one case got worse but the mean held, read
     the traces of that case before you keep the change.
  5. A case whose score changed can be noise if at most one run differs
     between the two sides, or if a side has only one run. The report lists
     these changed cases and prints the commands to run each one 4 more
     times on both sides and to compare again with all result files. A case
     with the same score on both sides is not listed.
  6. The report names the agent model and the judge model of each side. If
     the two sides used different models, the report gives a warning.

exit codes: 0 for a report, 1 for --fail-if-worse with no verdict or a lower
mean, 2 for an input error.
"""


class InputError(Exception):
    """An input that the script cannot use: a bad result file, a bad commit, or a failed command."""


def read_result(path):
    try:
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise InputError(f"{path}: cannot read the result file: {exc}") from exc
    if not isinstance(doc, dict) or doc.get("schemaVersion") != SCHEMA_VERSION:
        raise InputError(f"{path}: not a claude plugin eval result with schemaVersion {SCHEMA_VERSION}")
    return doc


def is_route(grader):
    return grader.get("name", "").startswith(ROUTE_PREFIX)


def run_score(run):
    """The score of a run without its route graders. None if the run has no grader that counts."""
    graders = run.get("graders") or []
    if graders and not any(map(is_route, graders)) and run.get("score") is not None:
        return run["score"]
    graders = [g for g in graders if g.get("scored", True) and not is_route(g)]
    total = sum(g.get("weight", 1) for g in graders)
    if not total:
        return None
    return sum(g.get("weight", 1) for g in graders if g.get("passed")) / total


def load_side(paths):
    """Read the result files of one side, and merge the runs of each case over the files."""
    side = {"files": [Path(p).name for p in paths], "cases": {}, "models": set(), "judges": set(),
            "versions": set(), "cost": 0.0, "seconds": 0.0, "partial": []}
    for path in paths:
        doc = read_result(path)
        suite = doc.get("suite") or {}
        if doc.get("partial"):
            side["partial"].append(f"{Path(path).name} ({doc.get('partialReason') or 'no reason given'})")
        side["versions"].add(doc.get("claudeVersion") or NOT_RECORDED)
        side["judges"].add(suite.get("judgeModel") or NOT_RECORDED)
        side["cost"] += doc.get("costUsd") or 0
        side["seconds"] += doc.get("durationSeconds") or 0
        for case in doc.get("cases") or []:
            entry = side["cases"].setdefault(case["name"], {"scores": [], "errors": 0, "unscored": 0, "routes": {}})
            side["models"].add(suite.get("modelOverride") or case.get("model") or NOT_RECORDED)
            for run in (case.get("arms") or {}).get("with") or []:
                if run.get("error") is not None:
                    entry["errors"] += 1
                score = None if run.get("skippedPaidGraders") else run_score(run)
                if score is None:
                    entry["unscored"] += 1
                    continue
                entry["scores"].append(score)
                for grader in filter(is_route, run.get("graders") or []):
                    entry["routes"].setdefault(grader["name"], []).append(bool(grader.get("passed")))
    return side


def lower(a, b):
    return a < b and not math.isclose(a, b, abs_tol=1e-9)


def share(passes):
    return f"{sum(passes)}/{len(passes)}" if passes else "none"


def runs_that_differ(row):
    """Count the runs whose score differs, after the scores of each side are sorted."""
    base, head = sorted(row["base_scores"]), sorted(row["head_scores"])
    if len(base) != len(head):
        return 1
    return sum(not math.isclose(b, h, abs_tol=1e-9) for b, h in zip(base, head))


def compare(base, head):
    """Apply the rules to two loaded sides. Return the facts that the report prints."""
    scored = {name for name, case in base["cases"].items() if case["scores"]}
    scored_head = {name for name, case in head["cases"].items() if case["scores"]}
    common = sorted(scored & scored_head)
    rows = []
    for name in common:
        b, h = base["cases"][name], head["cases"][name]
        rows.append({"case": name, "base": statistics.fmean(b["scores"]), "head": statistics.fmean(h["scores"]),
                     "base_runs": len(b["scores"]), "head_runs": len(h["scores"]),
                     "base_scores": b["scores"], "head_scores": h["scores"]})
    base_mean = statistics.fmean(r["base"] for r in rows) if rows else 0.0
    head_mean = statistics.fmean(r["head"] for r in rows) if rows else 0.0
    worse = [r for r in rows if lower(r["head"], r["base"])]
    better = [r for r in rows if lower(r["base"], r["head"])]
    again = []
    for row in worse + better:
        if min(row["base_runs"], row["head_runs"]) < 2 or runs_that_differ(row) <= 1:
            again.append(row["case"])
    routes = []
    for name in common:
        b, h = base["cases"][name]["routes"], head["cases"][name]["routes"]
        for grader in sorted(set(b) | set(h)):
            rb, rh = b.get(grader, []), h.get(grader, [])
            if not rb or not rh or not math.isclose(sum(rb) / len(rb), sum(rh) / len(rh)):
                routes.append((name, grader, share(rb), share(rh)))
    only_base = sorted(scored - scored_head)
    if only_base:
        verdict = "no-verdict"
    elif not rows:
        raise InputError("the two sides share no case with scored runs, so there is nothing to compare")
    elif lower(head_mean, base_mean):
        verdict = "worse"
    elif worse:
        verdict = "mixed"
    else:
        verdict = "holds"
    return {"rows": rows, "base_mean": base_mean, "head_mean": head_mean, "worse": [r["case"] for r in worse],
            "again": sorted(again), "routes": routes, "only_base": only_base,
            "only_head": sorted(scored_head - scored), "verdict": verdict}


def percent_change(before, after):
    return f"{(after - before) / before:+.0%}" if before else ""


def model_note(kind, flag, base, head):
    for side, models in (("base", base), ("head", head)):
        if not models:
            return f"The {side} has no results, so the {kind} is not compared."
    b, h = ", ".join(sorted(base)), ", ".join(sorted(head))
    if NOT_RECORDED in base | head:
        return (f"The {kind} is not recorded on one side (base: {b}, head: {h}). "
                f"Pass a full model id with {flag}, so that the result names the model that ran.")
    if base != head:
        return f"The sides used different {kind}s (base: {b}, head: {h}). The change is not the only difference."
    return f"{kind[0].upper()}{kind[1:]} on both sides: {b}."


def render(base, head, result, labels=("base", "head"), again_lines=None):
    lb, lh = labels
    rows = result["rows"]
    errors = {side: sum(c["errors"] for c in s["cases"].values()) for side, s in (("base", base), ("head", head))}
    lines = [f"# Eval comparison: {lb} and {lh}", "",
             f"Shared cases: {len(rows)}. Base files: {', '.join(base['files'])}. "
             f"Head files: {', '.join(head['files'])}.", "",
             f"| | {lb} | {lh} | change |", "| --- | ---: | ---: | ---: |",
             f"| mean case score | {result['base_mean']:.2f} | {result['head_mean']:.2f} "
             f"| {result['head_mean'] - result['base_mean']:+.2f} |",
             f"| scored runs | {sum(r['base_runs'] for r in rows)} | {sum(r['head_runs'] for r in rows)} | |",
             f"| run errors | {errors['base']} | {errors['head']} | |",
             f"| cost (USD) | {base['cost']:.2f} | {head['cost']:.2f} | {percent_change(base['cost'], head['cost'])} |",
             f"| duration (s) | {base['seconds']:.0f} | {head['seconds']:.0f} "
             f"| {percent_change(base['seconds'], head['seconds'])} |"]
    changed = [r for r in rows if lower(r["head"], r["base"]) or lower(r["base"], r["head"])]
    if changed:
        lines += ["", "## Cases that changed", "", f"| case | {lb} | {lh} | runs ({lb}/{lh}) |",
                  "| --- | ---: | ---: | ---: |"]
        lines += [f"| {r['case']} | {r['base']:.2f} | {r['head']:.2f} | {r['base_runs']}/{r['head_runs']} |"
                  for r in changed]
    if result["routes"]:
        lines += ["", "## Route checks that changed", "",
                  "These graders show which route a run took. They never count in the score.", "",
                  f"| case | grader | {lb} | {lh} |", "| --- | --- | ---: | ---: |"]
        lines += [f"| {case} | {grader} | {b} | {h} |" for case, grader, b, h in result["routes"]]
    if result["again"]:
        lines += ["", "## Run again", "",
                  "These cases changed by the result of one run, or ran once. That can be noise. "
                  "Run each case 4 more times on both sides, then compare again with all result files.", ""]
        lines += [f"- {case}" for case in result["again"]]
        if again_lines:
            lines += again_lines(result["again"])
    lines += ["", "## Verdict", ""]
    verdict = result["verdict"]
    if verdict == "no-verdict":
        lines.append(f"No verdict yet. These cases have scored runs at {lb} and none at {lh}: "
                     f"{', '.join(result['only_base'])}. Find out why, run them again, and compare again.")
    elif verdict == "worse":
        lines.append(f"{lh} scores lower than {lb}, so the change does not hold. "
                     f"Read the traces of these cases: {', '.join(result['worse'])}.")
    elif verdict == "mixed":
        lines.append(f"{lh} scores the same or higher overall, but these cases got worse: "
                     f"{', '.join(result['worse'])}. Read their traces before you keep the change.")
    else:
        lines.append(f"{lh} holds. Its mean score is at least that of {lb}, and no case got worse.")
    notes = [model_note("agent model", "--model", base["models"], head["models"]),
             model_note("judge model", "--judge-model", base["judges"], head["judges"])]
    if base["versions"] != head["versions"]:
        notes.append(f"The sides ran on different Claude Code versions (base: {', '.join(sorted(base['versions']))}, "
                     f"head: {', '.join(sorted(head['versions']))}).")
    for side_name, side in (("base", base), ("head", head)):
        for case, entry in sorted(side["cases"].items()):
            if entry["errors"] or entry["unscored"]:
                notes.append(f"{side_name}: {case}: runs that ended with an error: {entry['errors']}, "
                             f"runs with no score: {entry['unscored']}. Read the errors before you trust the score.")
        for partial in side["partial"]:
            notes.append(f"{side_name}: the suite did not finish in {partial}.")
    if result["only_head"]:
        notes.append(f"Not compared, because the base has no scored runs for them: {', '.join(result['only_head'])}.")
    lines += ["", "Notes:", ""] + [f"- {note}" for note in notes]
    return "\n".join(lines) + "\n"


def compare_files(base_paths, head_paths, labels=("base", "head"), again_lines=None):
    base, head = load_side(base_paths), load_side(head_paths)
    result = compare(base, head)
    return render(base, head, result, labels, again_lines), result["verdict"]


def git(repo, *args):
    done = subprocess.run(["git", "-C", str(repo), *args], capture_output=True)
    if done.returncode != 0:
        raise InputError(f"git {' '.join(args)} failed: {done.stderr.decode(errors='replace').strip()}")
    return done.stdout


def export_commit(repo, revision, dest):
    """Write the tree of one commit into dest. Return the full commit id."""
    sha = git(repo, "rev-parse", "--verify", f"{revision}^{{commit}}").decode().strip()
    with tarfile.open(fileobj=io.BytesIO(git(repo, "archive", "--format=tar", sha))) as tar:
        tar.extractall(dest, filter="data")
    return sha


def dependency_name(entry, marketplace_name):
    """The plugin name of one entry of `dependencies`: a name, "name@marketplace", or an object with a name."""
    if isinstance(entry, str):
        name, _, market = entry.partition("@")
    elif isinstance(entry, dict) and isinstance(entry.get("name"), str):
        name, market = entry["name"], entry.get("marketplace") or ""
    else:
        raise InputError(f"cannot read the dependency {entry!r}. Use a plugin name, or an object with a name")
    if not DEPENDENCY_NAME.fullmatch(name):
        raise InputError(f"the dependency name {name!r} is not a plugin name. Use letters, digits, dots, hyphens, and underscores")
    if market and market != marketplace_name:
        raise InputError(f"the dependency {entry!r} is not in the marketplace {marketplace_name}")
    return name


def add_dependencies(root, plugin, extra=()):
    """Copy the dependencies of the plugin into <plugin>/.deps/<name>. Root is the exported repository.

    The names in extra are eval-only dependencies. They are copied like the declared ones, but plugin.json does not list them.

    The eval session loads only the plugin under test, so a case lists the copies in its `plugins` field.
    A version range of a dependency is not checked, because the copy comes from the same commit.
    Only the dependencies in plugin.json and the names in extra are copied, one level deep, not those of a dependency.
    """
    manifest = plugin / ".claude-plugin" / "plugin.json"
    try:
        entries = json.loads(manifest.read_text(encoding="utf-8")).get("dependencies") or []
    except (OSError, ValueError, AttributeError) as exc:
        raise InputError(f"cannot read the manifest {manifest.relative_to(root).as_posix()}: {exc}") from exc
    if not isinstance(entries, list):
        raise InputError(f"dependencies in {manifest.relative_to(root).as_posix()} is not a list")
    if not entries and not extra:
        return
    market_file = root / ".claude-plugin" / "marketplace.json"
    try:
        market = json.loads(market_file.read_text(encoding="utf-8"))
        sources = {p["name"]: p["source"] for p in market["plugins"]}
        market_name = market["name"]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise InputError(f"cannot read the plugins of {market_file.relative_to(root).as_posix()}: {exc}") from exc
    names = [dependency_name(entry, market_name) for entry in entries]
    names += [dependency_name(name, market_name) for name in extra]
    for name in dict.fromkeys(names):
        source = sources.get(name)
        if not isinstance(source, str):
            raise InputError(f"the dependency {name} is not in the marketplace {market_name}, or has no path source")
        folder = (root / source).resolve()
        if not folder.is_relative_to(root.resolve()) or not (folder / ".claude-plugin" / "plugin.json").is_file():
            raise InputError(f"the dependency {name} has no plugin folder at {source}")
        deps = (plugin / ".deps").resolve()
        target = (deps / name).resolve()
        if target.parent != deps:
            raise InputError(f"the dependency {name} would be copied outside {deps}")
        # Leave out the eval folder of the dependency, or claude plugin eval also runs its cases.
        skip = manifest_suite(folder) or "evals"
        shutil.copytree(folder, target, symlinks=True,
                        ignore=lambda where, names: [skip] if Path(where) == folder else [])


def add_stubs(root, plugin):
    """Copy each stand-in of <root>/tests/evals/stubs into <plugin>/eval-stubs/<name>. Root is an exported repository.

    A commit with no such folder keeps the eval-stubs folder that its plugin has.
    """
    source = root / STUBS
    if not source.is_dir():
        return
    target = plugin / STUB_FOLDER
    shutil.rmtree(target, ignore_errors=True)
    shutil.copytree(source, target, symlinks=True)


def eval_command(args, plugin_dir, result, claude, suite):
    command = [claude, "plugin", "eval", str(plugin_dir), "--ablation", getattr(args, "ablation", "none"),
               "--runs", str(args.runs),
               "--model", args.model, "--judge-model", args.judge_model, "--threshold", "0",
               "--trust-plugin", "--no-publish", "--output-dir", str(result.with_suffix("")),
               "--json", str(result), "--eval-dir", suite]
    if args.case:
        command += ["--case", args.case]
    if args.scaffold:
        command.append("--scaffold")
    if getattr(args, "keep_temp", False):
        command.append("--keep-temp")
    if args.max_cost_usd is not None:
        command += ["--max-cost-usd", str(args.max_cost_usd)]
    if args.concurrency:
        command += ["--concurrency", str(args.concurrency)]
    # claude plugin eval reads a list option up to the next option, so the lists go last.
    if args.tag:
        command += ["--tag", *args.tag]
    if args.allow_tools:
        command += ["--allow-tools", *args.allow_tools]
    return command


def manifest_suite(plugin):
    """The eval folder that the manifest names in experimental.evals, or None."""
    try:
        manifest = json.loads((plugin / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        suite = (manifest.get("experimental") or {}).get("evals") or None
    except (OSError, ValueError, AttributeError):
        return None
    # The CLI falls back to evals for a bad manifest value, so do the same.
    if not isinstance(suite, str) or Path(suite).is_absolute() or suite.startswith(("/", "\\")) or ".." in Path(suite).parts:
        return None
    return suite


def option_words(args):
    """The options of a run command that a follow-up run repeats. The lists go last."""
    words = []
    repo = Path(args.repo).resolve()
    if repo != REPO:
        words += ["--repo", repo.as_posix()]
    if args.eval_dir:
        words += ["--eval-dir", args.eval_dir]
    if args.claude != "claude":
        words += ["--claude", args.claude]
    for name in args.extra_dep or []:
        words += ["--extra-dep", name]
    if args.scaffold:
        words.append("--scaffold")
    if args.max_cost_usd is not None:
        words += ["--max-cost-usd", str(args.max_cost_usd)]
    if args.concurrency:
        words += ["--concurrency", str(args.concurrency)]
    if args.tag:
        words += ["--tag", *args.tag]
    if args.allow_tools:
        words += ["--allow-tools", *args.allow_tools]
    return words


def again_lines(args, shas, out, cases):
    """The lines that give the commands to run the unclear cases again and to compare all result files."""
    script = ["python3", "tests/evals/compare_versions.py"]
    base, head = [(out / "base.json").as_posix()], [(out / "head.json").as_posix()]
    runs = []
    for number, case in enumerate(cases, 1):
        folder = out.parent / f"{out.name}-more-{number}"
        runs.append(shlex.join([*script, "run", "--plugin", args.plugin, "--base", shas["base"], "--head", shas["head"],
                                "--model", args.model, "--judge-model", args.judge_model, "--case", case,
                                "--runs", "4", "--out", folder.as_posix(), *option_words(args)]))
        base.append((folder / "base.json").as_posix())
        head.append((folder / "head.json").as_posix())
    joined = shlex.join([*script, "compare", "--base", *base, "--head", *head])
    return ["", "Run the cases again:", "", "```sh", *runs, "```", "",
            "Then compare all result files:", "", "```sh", joined, "```"]


DENIED_TEMP_FOLDERS = ("/tmp", "/var/tmp", "/dev/shm", "/run/shm")


def is_linux():
    return sys.platform.startswith("linux")


def temp_folder():
    return os.path.realpath(tempfile.gettempdir())


def check_temp_folder(args):
    """Stop a run that grants Bash on Linux when the temp folder is /tmp, /var/tmp, /dev/shm, /run/shm, or under one.

    The eval sandbox denies writes to these folders. The run folder follows TMPDIR, so every Bash call would fail.
    """
    if not is_linux() or "Bash" not in (args.allow_tools or []):
        return
    folder = posixpath.normpath(temp_folder())
    denied = next((name for name in DENIED_TEMP_FOLDERS if folder == name or folder.startswith(name + "/")), None)
    if denied is not None:
        raise InputError(f"the temporary folder is {folder}, and the eval sandbox denies writes to {denied}, "
                         "so every Bash call in the run would fail. Set TMPDIR to a folder in your home, "
                         "for example export TMPDIR=$HOME/.cache/plugin-evals/tmp, and make that folder. "
                         "Then run the command again")


def find_claude(args):
    claude = shutil.which(args.claude)
    if claude is None:
        raise InputError(f"cannot find the command {args.claude}. Install Claude Code, or pass its path with --claude")
    return claude


def refuse_existing(out, names):
    for name in names:
        existing = out / name
        if existing.exists():
            raise InputError(f"{existing} already exists. Use a new --out folder, so that no result is lost")


def export_plugin(args, tmp, side, revision):
    """Export one commit, and add the dependencies of the plugin. Return the plugin folder and the commit id."""
    root = Path(tmp) / side
    sha = export_commit(args.repo, revision, root)
    plugin = root / args.plugin
    # An absolute path or a path with .. can name the real plugin, and the steps below write into the plugin folder.
    if not plugin.resolve().is_relative_to(root.resolve()):
        raise InputError(f"the plugin folder {args.plugin} is not inside the repository. "
                         "Pass a path relative to the repository root, for example group/plugin")
    if not (plugin / ".claude-plugin" / "plugin.json").is_file():
        raise InputError(f"{args.plugin} is not a plugin folder at the {side} commit {sha[:12]}")
    add_dependencies(root, plugin, args.extra_dep or [])
    return plugin, sha


def run_eval(args, side, plugin, sha, result, claude, suite, runner):
    """Run the suite on one copy. Return the exit code of claude plugin eval."""
    print(f"Running the suite on the {side} commit {sha[:12]}.", file=sys.stderr)
    try:
        code = runner(eval_command(args, plugin, result, claude, suite), cwd=plugin).returncode
    except FileNotFoundError as exc:
        raise InputError(f"cannot start {args.claude}: {exc}") from exc
    if not result.is_file():
        raise InputError(f"claude plugin eval exited with {code} and wrote no result for the {side} commit")
    if code != 0 and side != "baseline":
        print(f"claude plugin eval exited with {code} on the {side} commit. "
              "The report counts the runs that ended with an error.", file=sys.stderr)
    return code


def run_suites(args, runner=subprocess.run):
    """Run the suite of the head commit against the plugin at each commit. Return the result paths and commit ids."""
    check_temp_folder(args)
    claude = find_claude(args)
    out = Path(args.out).resolve()
    refuse_existing(out, ("base.json", "head.json"))
    out.mkdir(parents=True, exist_ok=True)
    results, shas, plugins = {}, {}, {}
    with tempfile.TemporaryDirectory(prefix="compare-versions-", ignore_cleanup_errors=True) as tmp:
        for side, revision in (("head", args.head), ("base", args.base)):
            plugins[side], shas[side] = export_plugin(args, tmp, side, revision)
        suite = args.eval_dir or manifest_suite(plugins["head"]) or "evals"
        if not (plugins["head"] / suite).is_dir():
            raise InputError(f"{args.plugin}/{suite} does not exist at the head commit {shas['head'][:12]}")
        missing = sorted({p.name for p in (plugins["head"] / ".deps").glob("*")}
                         - {p.name for p in (plugins["base"] / ".deps").glob("*")})
        if missing:
            raise InputError(f"the head suite needs the dependency {', '.join(missing)}, but the base commit "
                             f"{shas['base'][:12]} does not declare it. Use a base commit that declares it")
        shutil.rmtree(plugins["base"] / suite, ignore_errors=True)
        shutil.copytree(plugins["head"] / suite, plugins["base"] / suite)
        add_stubs(Path(tmp) / "head", plugins["head"])
        shutil.rmtree(plugins["base"] / STUB_FOLDER, ignore_errors=True)
        if (plugins["head"] / STUB_FOLDER).is_dir():
            shutil.copytree(plugins["head"] / STUB_FOLDER, plugins["base"] / STUB_FOLDER, symlinks=True)
        for side in ("base", "head"):
            results[side] = out / f"{side}.json"
            run_eval(args, side, plugins[side], shas[side], results[side], claude, suite, runner)
    return results, shas


def run_baseline(args, runner=subprocess.run):
    """Run the suite of one commit against the plugin at that commit. Return the result path and the commit id."""
    check_temp_folder(args)
    claude = find_claude(args)
    out = Path(args.out).resolve()
    refuse_existing(out, (BASELINE_FILE,))
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="compare-versions-", ignore_cleanup_errors=True) as tmp:
        plugin, sha = export_plugin(args, tmp, "baseline", args.commit)
        add_stubs(Path(tmp) / "baseline", plugin)
        suite = args.eval_dir or manifest_suite(plugin) or "evals"
        if not (plugin / suite).is_dir():
            raise InputError(f"{args.plugin}/{suite} does not exist at the baseline commit {sha[:12]}")
        result = out / BASELINE_FILE
        code = run_eval(args, "baseline", plugin, sha, result, claude, suite, runner)
    cases = len(read_result(result).get("cases") or [])
    if code != 0 or cases == 0:
        raise InputError(f"claude plugin eval exited with {code} and wrote {cases} case(s) to {result}. "
                         "Read its output, fix the cases, and run the baseline again into a new folder")
    return result, sha


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0], epilog=RULES,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument("--plugin", required=True, help="plugin folder relative to the repository root")
    shared.add_argument("--model", required=True, help="full id of the model under test, stored in the result")
    shared.add_argument("--judge-model", required=True, help="full id of the judge model, stored in the result")
    shared.add_argument("--runs", type=int, default=3, help="runs for each case on each side (default: 3)")
    shared.add_argument("--case", help="case name glob, passed to claude plugin eval")
    shared.add_argument("--tag", nargs="+", help="case tags, passed to claude plugin eval")
    shared.add_argument("--allow-tools", nargs="+", help="tool grants, passed to claude plugin eval")
    shared.add_argument("--scaffold", action="store_true", help="run the scaffold scripts of the cases")
    shared.add_argument("--extra-dep", action="append", metavar="NAME",
                        help="also copy the marketplace plugin NAME into .deps/NAME, for a plugin that the cases load "
                             "but plugin.json does not list (repeatable)")
    shared.add_argument("--max-cost-usd", type=float, help="cost ceiling for each side")
    shared.add_argument("--concurrency", type=int, choices=range(1, 9),
                        help="runs at the same time, passed to claude plugin eval (1 to 8)")
    shared.add_argument("--eval-dir", help="eval folder below the plugin (default: experimental.evals of the manifest, else evals)")
    shared.add_argument("--repo", type=Path, default=REPO, help="repository root (default: this repository)")
    shared.add_argument("--claude", default="claude", help="the claude command (default: claude)")
    run = commands.add_parser("run", parents=[shared], help="run the suite on both commits, then compare",
                              epilog=RULES, formatter_class=argparse.RawDescriptionHelpFormatter)
    run.add_argument("--base", required=True, help="base commit, branch, or tag")
    run.add_argument("--head", default="HEAD", help="head commit, branch, or tag (default: HEAD)")
    run.add_argument("--out", required=True, help="folder for base.json, head.json, their reports, and report.md")
    run.add_argument("--fail-if-worse", action="store_true", help="exit 1 for no verdict or a lower mean")
    baseline = commands.add_parser("baseline", parents=[shared],
                                   help="run the suite on one commit and write one result file, with no comparison")
    baseline.add_argument("--commit", default="HEAD", help="commit, branch, or tag (default: HEAD)")
    baseline.add_argument("--ablation", choices=("none", "with-without"), default="none",
                          help="none, or with-without to also run an arm with no plugin (default: none)")
    baseline.add_argument("--keep-temp", action="store_true",
                          help="keep the temporary folder of each run, passed to claude plugin eval")
    baseline.add_argument("--out", required=True, help=f"folder for {BASELINE_FILE} and the output of claude plugin eval")
    compare_cmd = commands.add_parser("compare", help="compare finished result files",
                                      epilog=RULES, formatter_class=argparse.RawDescriptionHelpFormatter)
    compare_cmd.add_argument("--base", nargs="+", required=True, type=Path, help="result files of the base")
    compare_cmd.add_argument("--head", nargs="+", required=True, type=Path, help="result files of the head")
    compare_cmd.add_argument("--out", type=Path, help="also write the report to this file")
    compare_cmd.add_argument("--fail-if-worse", action="store_true", help="exit 1 for no verdict or a lower mean")
    return parser.parse_args(argv)


def main(argv=None, runner=subprocess.run):
    args = parse_args(argv)
    try:
        if args.command == "baseline":
            result, sha = run_baseline(args, runner)
            print(f"Wrote the baseline of {args.plugin} at {sha[:12]} to {result}.")
            return 0
        if args.command == "run":
            results, shas = run_suites(args, runner)
            labels = (f"base {shas['base'][:12]}", f"head {shas['head'][:12]}")
            out = Path(args.out).resolve()
            report, verdict = compare_files([results["base"]], [results["head"]], labels,
                                            lambda cases: again_lines(args, shas, out, cases))
            out = out / "report.md"
        else:
            report, verdict = compare_files(args.base, args.head)
            out = args.out
        if out:
            Path(out).write_text(report, encoding="utf-8")
    except InputError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(report, end="")
    return 1 if args.fail_if_worse and verdict in ("no-verdict", "worse") else 0


if __name__ == "__main__":
    raise SystemExit(main())
