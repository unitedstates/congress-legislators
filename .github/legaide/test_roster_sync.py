"""Tests for roster_sync.py. Run: uv run --no-project --with pytest --with pyyaml pytest .github/legaide"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent))
import roster_sync as module  # noqa: E402


def member(bioguide: str, rank: int, title: str | None = None) -> dict:
    entry = {"name": bioguide, "bioguide": bioguide, "party": "majority", "rank": rank}
    if title:
        entry["title"] = title
    return entry


# The SSBU shape observed on 2026-09-02: senate.gov published the chair the
# addendum existed to supply, and upstream ranks the chair 1 while the frozen
# addendum kept the older ordering, so the key had begun overriding correct data.
SSBU_ADDENDUM = [member("G000386", 1), member("C000880", 2), member("J000293", 3, "Chairman")]
SSBU_PRIMARY = [member("J000293", 1, "Chairman"), member("G000386", 2), member("C000880", 3)]


def test_redundant_when_upstream_supplies_the_title_and_reorders() -> None:
    status, why = module.classify(SSBU_ADDENDUM, SSBU_PRIMARY)
    assert status == "redundant"
    assert "overriding correct data" in why


def test_redundant_when_upstream_is_identical() -> None:
    assert module.classify(SSBU_PRIMARY, list(SSBU_PRIMARY))[0] == "redundant"


@pytest.mark.parametrize(
    ("addendum", "primary", "status"),
    [
        ([member("L000491", 1, "Chairman")], None, "missing_upstream"),
        ([member("M001217", 1, "Ranking Member"), member("S000344", 2)],
         [member("S000344", 1, "Ranking Member")], "roster_differs"),
        ([member("W000437", 1, "Chairman")], [member("W000437", 1, "Cochairman")], "titles_differ"),
    ],
)
def test_gap_patching_keys_are_kept(addendum, primary, status) -> None:
    assert module.classify(addendum, primary)[0] == status
    assert status in module.KEEP


MEMBERSHIP = """\
# About JCSE, which stays.
JCSE:
- name: A
  rank: 1
  bioguide: A000001
# About SSBU, which goes.
# A second comment line about SSBU.
SSBU:
- name: B
  rank: 1
  bioguide: B000001

# Section note about the HSFA keys below, after a blank line. It stays.

# About HSFA13, which stays.
HSFA13:
- name: C
  rank: 1
  bioguide: C000001
"""


def test_removing_a_membership_key_takes_only_its_own_block() -> None:
    result = module.remove_membership_keys(MEMBERSHIP, {"SSBU"})
    assert "SSBU" not in result
    assert "# About JCSE, which stays.\nJCSE:" in result
    assert "# About HSFA13, which stays.\nHSFA13:" in result
    assert "# Section note about the HSFA keys below" in result
    assert set(yaml.safe_load(result)) == {"JCSE", "HSFA13"}


COMMITTEES = """\
# File header about HXHR, separated by a blank line. It stays.

# HSBA gap.
- type: house
  thomas_id: HSBA
  subcommittees:
  - name: Task Force
    thomas_id: '98'
# HSFA gaps.
- type: house
  thomas_id: HSFA
  subcommittees:
  - name: Old
    thomas_id: '13'
  # Still missing upstream.
  - name: New
    thomas_id: '17'
- type: house
  name: Commission
  thomas_id: HXHR
"""


def test_removing_the_only_subcommittee_drops_a_bare_parent() -> None:
    result = module.remove_committee_subcommittees(COMMITTEES, {"HSBA98"})
    assert "HSBA" not in result and "# HSBA gap." not in result
    assert result.startswith("# File header about HXHR")
    assert [c["thomas_id"] for c in yaml.safe_load(result)] == ["HSFA", "HXHR"]


def test_removing_one_subcommittee_keeps_its_siblings() -> None:
    result = module.remove_committee_subcommittees(COMMITTEES, {"HSFA13"})
    parsed = yaml.safe_load(result)
    assert parsed[1]["subcommittees"] == [{"name": "New", "thomas_id": "17"}]
    assert "# Still missing upstream." in result and "# HSFA gaps." in result
    assert len(parsed) == 3


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, text=True,
                          capture_output=True).stdout


def test_end_to_end_merges_upstream_and_drops_a_redundant_key(tmp_path, monkeypatch) -> None:
    upstream = tmp_path / "upstream"
    upstream.mkdir()
    git(upstream, "init", "-q", "-b", "main")
    git(upstream, "config", "user.email", "t@example.com")
    git(upstream, "config", "user.name", "t")
    jcse_upstream = [member("W000437", 1, "Cochairman")]
    (upstream / module.MEMBERSHIP_PRIMARY).write_text(
        yaml.safe_dump({"SSBU": SSBU_ADDENDUM, "JCSE": jcse_upstream}))
    (upstream / module.COMMITTEES_PRIMARY).write_text("[]\n")
    git(upstream, "add", ".")
    git(upstream, "commit", "-qm", "base")
    fork = tmp_path / "fork"
    git(tmp_path, "clone", "-q", str(upstream), str(fork))
    git(fork, "config", "user.email", "t@example.com")
    git(fork, "config", "user.name", "t")
    (fork / module.MEMBERSHIP_ADDENDUM).write_text(
        "# About SSBU.\n" + yaml.safe_dump({"SSBU": SSBU_ADDENDUM})
        + "# About JCSE, which stays.\n" + yaml.safe_dump({"JCSE": [member("W000437", 1, "Chairman")]}))
    (fork / module.COMMITTEES_ADDENDUM).write_text("[]\n")
    git(fork, "add", ".")
    git(fork, "commit", "-qm", "addendum")
    (upstream / module.MEMBERSHIP_PRIMARY).write_text(
        yaml.safe_dump({"SSBU": SSBU_PRIMARY, "JCSE": jcse_upstream}))
    git(upstream, "commit", "-qam", "Senate publishes the SSBU chair")
    git(fork, "remote", "add", "upstream", str(upstream))
    git(fork, "fetch", "-q", "upstream")
    monkeypatch.setattr(module, "scrape", lambda repo: None)

    report = module.run(fork)

    assert report["changed"] is True
    assert [c.split(" ", 1)[1] for c in report["upstream_commits"]] == ["Senate publishes the SSBU chair"]
    assert [k["key"] for k in report["redundant_keys"]] == ["SSBU"]
    assert (fork / module.MEMBERSHIP_ADDENDUM).read_text().startswith("# About JCSE, which stays.\nJCSE:")
    body = module.render_body(report)
    assert "`SSBU`: the scraped data supplies every title" in body
    assert "Senate publishes the SSBU chair" in body
    assert report["merge_blockers"] == []
    assert "The workflow merges this pull request" in body


def test_a_change_outside_the_upstream_merge_blocks_the_merge() -> None:
    # An upstream merge that touches workflow code, or any file the merge, scraper and addendum
    # removals did not produce, is not upstream-only and needs a person.
    assert module.merge_blockers(
        [module.MEMBERSHIP_PRIMARY, module.MEMBERSHIP_ADDENDUM], [module.MEMBERSHIP_PRIMARY], []) == []
    blockers = module.merge_blockers(
        [".github/workflows/x.yml", "legislators-current.yaml"], [".github/workflows/x.yml"], [])
    assert blockers == ["`legislators-current.yaml` changed outside the upstream merge, the scraper and the addendum",
                        "`.github/workflows/x.yml` is workflow or LegAide sync code"]
    assert "Not merged automatically" in module.merge_decision(blockers)


def test_quiet_day_proposes_nothing(tmp_path, monkeypatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.email", "t@example.com")
    git(repo, "config", "user.name", "t")
    (repo / module.MEMBERSHIP_PRIMARY).write_text(yaml.safe_dump({"JCSE": [member("W000437", 1, "Cochairman")]}))
    (repo / module.MEMBERSHIP_ADDENDUM).write_text(yaml.safe_dump({"JCSE": [member("W000437", 1, "Chairman")]}))
    (repo / module.COMMITTEES_PRIMARY).write_text("[]\n")
    (repo / module.COMMITTEES_ADDENDUM).write_text("[]\n")
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "base")
    git(repo, "remote", "add", "upstream", str(repo))
    git(repo, "fetch", "-q", "upstream")
    monkeypatch.setattr(module, "scrape", lambda repo: None)

    assert module.run(repo)["changed"] is False


def test_upstream_conflict_aborts_and_fails_closed(tmp_path) -> None:
    upstream = tmp_path / "upstream"
    upstream.mkdir()
    git(upstream, "init", "-q", "-b", "main")
    (upstream / "legislators-current.yaml").write_text("a: 1\n")
    git(upstream, "add", ".")
    git(upstream, "commit", "-qm", "base")
    fork = tmp_path / "fork"
    git(tmp_path, "clone", "-q", str(upstream), str(fork))
    (fork / "legislators-current.yaml").write_text("a: 2\n")
    git(fork, "commit", "-qam", "fork edit")
    (upstream / "legislators-current.yaml").write_text("a: 3\n")
    git(upstream, "commit", "-qam", "upstream edit")
    git(fork, "remote", "add", "upstream", str(upstream))
    git(fork, "fetch", "-q", "upstream")
    head = git(fork, "rev-parse", "HEAD")
    body = tmp_path / "body.md"

    assert module.main(["--repo", str(fork), "--body-file", str(body)]) == 1
    assert not body.exists()
    assert git(fork, "rev-parse", "HEAD") == head
    assert git(fork, "status", "--porcelain") == ""
