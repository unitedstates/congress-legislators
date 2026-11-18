#!/usr/bin/env python3
"""Prepare LegAide's daily congress-legislators sync, with no model involved.

This replaces Bot Chief's ``bot-chief-congress-legislators-sync`` routine.  It
runs inside a GitHub Actions checkout of the fork's ``main`` with an
``upstream`` remote already fetched, and it leaves every change uncommitted for
the workflow to commit on a branch and propose as a pull request.  LegAide
production reads ``main`` live and unpinned, so nothing here pushes to it.

The steps match the routine:

1. Merge ``upstream/main`` into the local ``main``.
2. Run upstream's committee scraper with its pinned dependencies.
3. Delete every manual addendum key the scraped data has caught up on.
   Downstream applies the membership addendum as a full per-key override, so a
   key upstream has caught up on is no longer patching a gap; it is overriding
   correct data.

It never looks for out-of-date rosters and never adds or corrects addendum
keys; that is separate work a person directs.

Outputs: ``--body-file`` receives the pull request description and the last
stdout line is a JSON report whose ``changed`` field says whether a pull
request is needed.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

MEMBERSHIP_PRIMARY = "committee-membership-current.yaml"
MEMBERSHIP_ADDENDUM = "committee-membership-manual-addendum.yaml"
COMMITTEES_PRIMARY = "committees-current.yaml"
COMMITTEES_ADDENDUM = "committees-current-manual-addendum.yaml"

# committee_membership.py declares no dependencies, so it runs through uv.
SCRAPER_DEPS = [
    "pyyaml",
    "rtyaml",
    "scrapelib==2.4.1",
    "lxml>=2.2",
    "cssselect",
    "pytz",
]

GIT_TIMEOUT_SECONDS = 300
SCRAPER_TIMEOUT_SECONDS = 900

# Classifications that mean the addendum key is still earning its place.
KEEP = {"missing_upstream", "roster_differs", "titles_differ"}


class SyncError(RuntimeError):
    """A technical failure; the run must stop without proposing anything."""


def git(repo: Path, *args: str, check: bool = True) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), *args],
            text=True,
            capture_output=True,
            timeout=GIT_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise SyncError(f"git {args[0]} could not run") from exc
    if check and result.returncode:
        raise SyncError(f"git {args[0]} failed: {result.stderr.strip()[:300]}")
    return result.stdout


def merge_upstream(repo: Path) -> list[str]:
    """Merge upstream/main into the checked-out main. Return merged commit subjects."""
    pending = [
        line
        for line in git(repo, "log", "--oneline", "--no-merges", "HEAD..upstream/main").splitlines()
        if line.strip()
    ]
    merge = subprocess.run(
        ["git", "-C", str(repo), "merge", "--no-edit", "upstream/main"],
        text=True,
        capture_output=True,
        timeout=GIT_TIMEOUT_SECONDS,
        check=False,
    )
    if merge.returncode:
        git(repo, "merge", "--abort", check=False)
        raise SyncError("upstream merge conflicted and was aborted; a person must merge by hand")
    return pending


def scrape(repo: Path) -> None:
    """Run committee_membership.py against clerk.house.gov and senate.gov."""
    uv = shutil.which("uv")
    if not uv:
        raise SyncError("uv is not on PATH, so the committee scraper cannot run")
    argv = [uv, "run", "--no-project"]
    for dep in SCRAPER_DEPS:
        argv += ["--with", dep]
    argv += ["python", "committee_membership.py"]
    try:
        result = subprocess.run(
            argv,
            cwd=repo / "scripts",
            text=True,
            capture_output=True,
            timeout=SCRAPER_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise SyncError("the committee scraper could not run") from exc
    if result.returncode:
        raise SyncError(f"the committee scraper failed: {result.stderr.strip()[-300:]}")


def load_yaml(path: Path) -> Any:
    try:
        return yaml.safe_load(path.read_text()) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise SyncError(f"could not parse {path.name}") from exc


def classify(addendum_entry: list[dict], primary_entry: list[dict] | None) -> tuple[str, str]:
    """Say whether one membership addendum key still earns its place.

    `redundant` is the finding that matters: the scraped data already carries
    every title this key overrides, so the override now only freezes a stale
    ordering on top of correct data.
    """
    if primary_entry is None:
        return "missing_upstream", "the committee is absent from the scraped data"
    addendum = {member["bioguide"]: member for member in addendum_entry}
    primary = {member["bioguide"]: member for member in primary_entry}
    if set(addendum) != set(primary):
        return "roster_differs", "the addendum seats a different set of members"
    if any(addendum[b].get("title") != primary[b].get("title") for b in addendum):
        return "titles_differ", "the addendum overrides titles the scraped data still has wrong"
    if any(addendum[b].get("rank") != primary[b].get("rank") for b in addendum):
        return (
            "redundant",
            "the scraped data supplies every title this key overrides and now ranks "
            "members differently, so the key is overriding correct data",
        )
    return "redundant", "the scraped data is identical to this key"


def committee_addendum_status(repo: Path) -> list[dict[str, str]]:
    """Report committees-addendum subcommittees the scraped catalog now carries."""
    primary = load_yaml(repo / COMMITTEES_PRIMARY)
    addendum = load_yaml(repo / COMMITTEES_ADDENDUM)
    known: dict[str, set[str]] = {}
    for committee in primary if isinstance(primary, list) else []:
        thomas_id = committee.get("thomas_id")
        if thomas_id:
            known[thomas_id] = {
                sub.get("thomas_id") for sub in committee.get("subcommittees", []) or []
            }
    findings = []
    for committee in addendum if isinstance(addendum, list) else []:
        parent = committee.get("thomas_id")
        for sub in committee.get("subcommittees", []) or []:
            key = f"{parent}{sub.get('thomas_id')}"
            if sub.get("thomas_id") in known.get(parent, set()):
                findings.append(
                    {"key": key, "status": "redundant", "why": "the scraped catalog now lists it"}
                )
            else:
                findings.append(
                    {"key": key, "status": "missing_upstream", "why": "still absent upstream"}
                )
    return findings


def survey(repo: Path) -> dict[str, list[dict[str, str]]]:
    primary = load_yaml(repo / MEMBERSHIP_PRIMARY)
    addendum = load_yaml(repo / MEMBERSHIP_ADDENDUM)
    membership = []
    for key, entry in addendum.items():
        status, why = classify(entry, primary.get(key))
        membership.append({"key": key, "status": status, "why": why})
    return {
        "membership_addendum": membership,
        "committees_addendum": committee_addendum_status(repo),
    }


def _owned_ranges(lines: list[str], starts: list[int], limit: int) -> list[tuple[int, int]]:
    """Give each item its directly attached comments, its key, and its body.

    A comment block separated from the next item by a blank line is a section
    note, not part of the previous item, so a range ends at its last content line.
    """
    def is_content(line: str) -> bool:
        return bool(line.strip()) and not line.lstrip().startswith("#")

    ranges = []
    for n, start in enumerate(starts):
        first = start
        while first > 0 and lines[first - 1].lstrip().startswith("#"):
            first -= 1
        stop = starts[n + 1] if n + 1 < len(starts) else limit
        end = max(i for i in range(start, stop) if is_content(lines[i])) + 1
        ranges.append((first, end))
    return ranges


def remove_membership_keys(text: str, keys: set[str]) -> str:
    """Delete top-level keys and their own comment blocks, keeping all other bytes."""
    lines = text.splitlines(keepends=True)
    pattern = re.compile(r"^([A-Za-z0-9]+):\s*$")
    starts = [i for i, line in enumerate(lines) if pattern.match(line)]
    drop: set[int] = set()
    for start, (first, end) in zip(starts, _owned_ranges(lines, starts, len(lines))):
        if pattern.match(lines[start]).group(1) in keys:
            drop.update(range(first, end))
    return "".join(line for i, line in enumerate(lines) if i not in drop)


def remove_committee_subcommittees(text: str, keys: set[str]) -> str:
    """Delete addendum subcommittees by parent+child key.

    A parent entry left with no subcommittees and nothing else to add (only
    ``type`` and ``thomas_id``) is removed with its comments too.
    """
    lines = text.splitlines(keepends=True)
    starts = [i for i, line in enumerate(lines) if line.startswith("- ")]
    drop: set[int] = set()
    for first, end in _owned_ranges(lines, starts, len(lines)):
        parent = yaml.safe_load("".join(lines[first:end]))[0]
        subs = parent.get("subcommittees") or []
        doomed = {
            s.get("thomas_id") for s in subs if f"{parent['thomas_id']}{s.get('thomas_id')}" in keys
        }
        if not doomed:
            continue
        if len(doomed) == len(subs) and set(parent) <= {"type", "thomas_id", "subcommittees"}:
            drop.update(range(first, end))
            continue
        header = next(i for i in range(first, end) if lines[i].startswith("  subcommittees:"))
        stop = next(
            (i for i in range(header + 1, end)
             if lines[i].strip() and not lines[i].startswith(("  - ", "    ")) and not lines[i].lstrip().startswith("#")),
            end,
        )
        sub_starts = [i for i in range(header + 1, stop) if lines[i].startswith("  - ")]
        for sub_start, (sub_first, sub_end) in zip(sub_starts, _owned_ranges(lines, sub_starts, stop)):
            item = yaml.safe_load("".join(line[2:] for line in lines[sub_start:sub_end]))
            if item[0].get("thomas_id") in doomed:
                drop.update(range(sub_first, sub_end))
    return "".join(line for i, line in enumerate(lines) if i not in drop)


def apply_removals(repo: Path, redundant: list[dict[str, str]], findings: dict[str, list[dict[str, str]]]) -> None:
    membership_keys = {item["key"] for item in redundant if item in findings["membership_addendum"]}
    committee_keys = {item["key"] for item in redundant if item in findings["committees_addendum"]}
    if membership_keys:
        path = repo / MEMBERSHIP_ADDENDUM
        before = load_yaml(path)
        path.write_text(remove_membership_keys(path.read_text(), membership_keys))
        after = load_yaml(path)
        expected = {k: v for k, v in before.items() if k not in membership_keys}
        if after != expected:
            raise SyncError("removing membership addendum keys changed other data")
    if committee_keys:
        path = repo / COMMITTEES_ADDENDUM
        before = load_yaml(path)
        path.write_text(remove_committee_subcommittees(path.read_text(), committee_keys))
        expected = []
        for committee in before:
            subs = committee.get("subcommittees") or []
            kept = [s for s in subs if f"{committee['thomas_id']}{s.get('thomas_id')}" not in committee_keys]
            if subs and not kept and set(committee) <= {"type", "thomas_id", "subcommittees"}:
                continue
            if len(kept) != len(subs):
                committee = {**committee, "subcommittees": kept or None}
            expected.append(committee)
        if load_yaml(path) != expected:
            raise SyncError("removing committee addendum subcommittees changed other data")


def membership_changes(repo: Path, base: str) -> list[str]:
    """Committee codes whose scraped roster differs between ``base`` and the worktree."""
    try:
        before = yaml.safe_load(git(repo, "show", f"{base}:{MEMBERSHIP_PRIMARY}")) or {}
    except yaml.YAMLError as exc:
        raise SyncError(f"could not parse {MEMBERSHIP_PRIMARY} at {base}") from exc
    after = load_yaml(repo / MEMBERSHIP_PRIMARY)
    return sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))


def bullet(items: list[str], empty: str) -> str:
    return "\n".join(f"- {item}" for item in items) if items else empty


def render_body(report: dict[str, Any]) -> str:
    upstream = report["upstream_commits"]
    kept = [
        f"`{item['key']}` ({item['status']}: {item['why']})"
        for item in report["addendum_status"]["membership_addendum"]
        + report["addendum_status"]["committees_addendum"]
        if item["status"] in KEEP
    ]
    removed = [f"`{item['key']}`: {item['why']}" for item in report["redundant_keys"]]
    roster = report["scraper_committees"]
    return f"""## Summary
Daily sync of the LegAide fork with `unitedstates/congress-legislators` `main` (upstream head `{report['upstream_head'][:7]}`). Opened by the `legaide-roster-sync` GitHub Actions workflow. It is not merged automatically, because LegAide production reads this repository's `main` live and unpinned.

## Upstream changes
{bullet(upstream, "- None. Upstream had no new commits.")}

Files the upstream merge changed: {", ".join(f"`{f}`" for f in report["merge_files"]) or "none"}.

## Committee scraper
Ran `committee_membership.py` from `scripts` with {", ".join(SCRAPER_DEPS)}. It exited successfully.

Files the scraper changed: {", ".join(f"`{f}`" for f in report["scraper_files"]) or "none"}.
{f"Committees whose scraped roster changed ({len(roster)}): " + ", ".join(f"`{k}`" for k in roster) + "." if roster else "No committee roster changed."}

## Addendum keys removed
Downstream applies the membership addendum as a full per-key override, so a key upstream has caught up on overrides correct data.
{bullet(removed, "- None. Every addendum key still patches a gap.")}

Addendum keys kept: {", ".join(kept) or "none"}.

## Merge decision
A reviewer should read the upstream and scraper diffs above, confirm each removed addendum key is now correct upstream, and decide whether this data should go live in production. Merging is a person's or the LegAide Catalog review's decision; this workflow never merges.
"""


def run(repo: Path) -> dict[str, Any]:
    base = git(repo, "rev-parse", "HEAD").strip()
    merged = merge_upstream(repo)
    merge_head = git(repo, "rev-parse", "HEAD").strip()
    merge_files = [f for f in git(repo, "diff", "--name-only", base, merge_head).splitlines() if f]
    scrape(repo)
    scraper_files = [f for f in git(repo, "diff", "--name-only").splitlines() if f]
    scraper_committees = membership_changes(repo, merge_head)
    findings = survey(repo)
    redundant = [
        item
        for item in findings["membership_addendum"] + findings["committees_addendum"]
        if item["status"] not in KEEP
    ]
    apply_removals(repo, redundant, findings)
    if git(repo, "diff", "--check", check=False).strip():
        raise SyncError("git diff --check found whitespace errors in the sync")
    if git(repo, "ls-files", "--others", "--exclude-standard").strip():
        raise SyncError("the sync left untracked files")
    final_files = [f for f in git(repo, "diff", "--name-only", base).splitlines() if f]
    return {
        # A quiet day is the common case: upstream added nothing, the scrape
        # moved nothing, and every addendum key still earns its place.
        "changed": bool(merged or final_files or redundant),
        "base": base,
        "upstream_head": git(repo, "rev-parse", "upstream/main").strip(),
        "upstream_commits": merged,
        "merge_files": merge_files,
        "scraper_files": scraper_files,
        "scraper_committees": scraper_committees,
        "redundant_keys": redundant,
        "changed_files": final_files,
        "addendum_status": findings,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--body-file", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = run(args.repo.resolve())
    except SyncError as exc:
        print(f"congress-legislators sync failed: {exc}", file=sys.stderr)
        return 1
    if report["changed"]:
        args.body_file.write_text(render_body(report))
    print(json.dumps(report, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
