#!/usr/bin/env python3
"""Tests for board-tick.py — the pure logic only: no network, no `gh` calls.

The script is deliberately stdlib-only so it stays runnable with zero install
steps; these tests keep that property (plain `unittest`, no pytest).

Run:
    python3 -m unittest discover -s .agents/skills/loop-common/scripts -p 'test_*.py' -v
"""

from __future__ import annotations

import argparse
import contextlib
import importlib.util
import inspect
import io
import json
import re
import sys
import unittest
from pathlib import Path

# board-tick.py is not an importable module name (hyphen), so load it by path.
_SPEC = importlib.util.spec_from_file_location(
    "board_tick", Path(__file__).resolve().parent / "board-tick.py"
)
bt = importlib.util.module_from_spec(_SPEC)
# @dataclass resolves annotations through sys.modules[cls.__module__], so the
# module has to be registered *before* its body runs.
sys.modules["board_tick"] = bt
_SPEC.loader.exec_module(bt)


# ── helpers ─────────────────────────────────────────────────────────────────


def make_item(**kw) -> "bt.Item":
    """An Item with the required fields filled in; override anything by keyword."""
    base = dict(
        item_id="PVTI_test",
        status="In progress",
        loop="auto",
        repo="demo",
        number=1,
        title="A task",
        issue_url="https://github.com/gaarutyunov/demo/issues/1",
    )
    base.update(kw)
    return bt.Item(**base)


def blocker(number: int, state: str = "OPEN", repo: str = "gaarutyunov/dep") -> "bt.Blocker":
    return bt.Blocker(
        repo=repo,
        number=number,
        state=state,
        title=f"blocker {number}",
        url=f"https://github.com/{repo}/issues/{number}",
        created="2020-01-01T00:00:00Z",
    )


def human_comment(cid: int = 1) -> "bt.Comment":
    return bt.Comment(
        kind="issue",
        cid=cid,
        author="gaarutyunov",
        body="please rework this",
        created="2020-01-01T00:00:00Z",
        url="https://example.invalid/c",
        who="human",
    )


def signal_of(item: "bt.Item") -> str:
    bt.compute_signal(item)
    return item.signal


def chain_signals() -> list[str]:
    """Signals in the order compute_signal's if/elif chain can assign them.

    Derived from the source so a signal added to the chain but not to
    SIGNAL_ORDER (or vice versa) fails the test instead of silently sorting to
    the bottom of the digest.
    """
    src = inspect.getsource(bt.compute_signal)
    return re.findall(r'item\.signal\s*=\s*"([A-Z][A-Z-]*)"', src)


# ── the two highest-risk invariants ─────────────────────────────────────────


class TestActiveStatuses(unittest.TestCase):
    def test_blocked_is_an_active_status(self):
        """Regression: dropping Blocked here makes blocked items vanish entirely.

        A blocked item outside ACTIVE_STATUSES is fetched by no tick, so it is
        strictly less visible than the old label-only scheme.
        """
        self.assertIn("Blocked", bt.ACTIVE_STATUSES)

    def test_blocked_status_constant_matches(self):
        self.assertEqual(bt.BLOCKED_STATUS, "Blocked")
        self.assertIn(bt.BLOCKED_STATUS, bt.ACTIVE_STATUSES)
        self.assertIn(bt.BLOCKED_STATUS, bt.STATUS_OPTION_IDS)

    def test_backlog_and_done_stay_inactive(self):
        self.assertNotIn("Backlog", bt.ACTIVE_STATUSES)
        self.assertNotIn("Done", bt.ACTIVE_STATUSES)


class TestSignalOrderAgreesWithChain(unittest.TestCase):
    def test_every_assignable_signal_is_orderable(self):
        """Both lists must name the same signals — derived, never hardcoded."""
        chain = set(chain_signals())
        order = set(bt.SIGNAL_ORDER)
        self.assertEqual(
            chain - order, set(), "signal(s) assigned by compute_signal but missing from SIGNAL_ORDER"
        )
        self.assertEqual(
            order - chain, set(), "signal(s) in SIGNAL_ORDER that compute_signal never assigns"
        )

    def test_signal_order_has_no_duplicates(self):
        self.assertEqual(len(bt.SIGNAL_ORDER), len(set(bt.SIGNAL_ORDER)))

    def test_unblocked_ranks_immediately_after_human_input_in_both(self):
        chain = chain_signals()
        self.assertEqual(chain[:2], ["HUMAN-INPUT", "UNBLOCKED"])
        self.assertEqual(bt.SIGNAL_ORDER[:2], ["HUMAN-INPUT", "UNBLOCKED"])

    def test_blocked_precedes_waiting_owner_in_both(self):
        chain = chain_signals()
        self.assertLess(chain.index("BLOCKED"), chain.index("WAITING-OWNER"))
        self.assertLess(
            bt.SIGNAL_ORDER.index("BLOCKED"), bt.SIGNAL_ORDER.index("WAITING-OWNER")
        )

    def test_unblocked_outranks_blocked_in_the_sort(self):
        self.assertLess(
            bt.SIGNAL_ORDER.index("UNBLOCKED"), bt.SIGNAL_ORDER.index("BLOCKED")
        )


# ── compute_signal, branch by branch ────────────────────────────────────────


class TestComputeSignalBlocked(unittest.TestCase):
    def test_blocked_status_with_open_blocker(self):
        item = make_item(status="Blocked", blockers=[blocker(9)], blockers_total=1)
        self.assertEqual(signal_of(item), "BLOCKED")
        self.assertTrue(any("dep#9" in r for r in item.reasons))

    def test_blocked_label_with_open_blocker(self):
        item = make_item(status="In review", labels=["blocked"], blockers=[blocker(9)], blockers_total=1)
        self.assertEqual(signal_of(item), "BLOCKED")

    def test_mixed_blockers_stay_blocked(self):
        item = make_item(
            status="Blocked",
            blockers=[blocker(9, "CLOSED"), blocker(10, "OPEN")],
            blockers_total=2,
        )
        self.assertEqual(signal_of(item), "BLOCKED")

    def test_reason_names_open_blockers_and_their_age(self):
        item = make_item(status="Blocked", blockers=[blocker(9)], blockers_total=1)
        signal_of(item)
        reason = " ".join(item.reasons)
        self.assertIn("dep#9", reason)
        self.assertIn("open", reason)


class TestComputeSignalUnblocked(unittest.TestCase):
    def test_all_blockers_closed_is_unblocked(self):
        item = make_item(
            status="Blocked", blockers=[blocker(9, "CLOSED")], blockers_total=1
        )
        self.assertEqual(signal_of(item), "UNBLOCKED")

    def test_reason_names_the_blocker_that_closed(self):
        item = make_item(
            status="Blocked",
            blockers=[blocker(9, "CLOSED"), blocker(10, "CLOSED")],
            blockers_total=2,
        )
        signal_of(item)
        reason = " ".join(item.reasons)
        self.assertIn("dep#9 closed", reason)
        self.assertIn("dep#10 closed", reason)
        self.assertIn("Ready", reason)

    def test_unblocked_outranks_waiting_owner(self):
        item = make_item(
            status="Blocked",
            labels=["blocked", "needs:review"],
            blockers=[blocker(9, "CLOSED")],
            blockers_total=1,
        )
        self.assertEqual(signal_of(item), "UNBLOCKED")

    def test_unblocked_yields_to_a_waiting_owner_comment(self):
        item = make_item(
            status="Blocked", blockers=[blocker(9, "CLOSED")], blockers_total=1
        )
        item.comments.append(human_comment())
        self.assertEqual(signal_of(item), "HUMAN-INPUT")

    def test_unblocked_outranks_pr_approved(self):
        item = make_item(
            status="Blocked",
            labels=["blocked", "approved:pr"],
            blockers=[blocker(9, "CLOSED")],
            blockers_total=1,
        )
        self.assertEqual(signal_of(item), "UNBLOCKED")

    def test_not_flagged_blocked_never_gets_a_blocked_signal(self):
        """A native edge alone does not park a task — it warns instead."""
        item = make_item(status="Ready", blockers=[blocker(9)], blockers_total=1)
        self.assertEqual(signal_of(item), "READY")
        self.assertTrue(any("open blocker" in w for w in item.warnings))


class TestUnblockedNeedsARecordedBlocker(unittest.TestCase):
    """UNBLOCKED must never fire over an *empty* blocker set.

    `all(b.closed for b in [])` is vacuously true, so a task flagged blocked with
    nothing recorded used to rank UNBLOCKED — an actionable pickup the loops are
    told to "never leave sitting". Both blocked items on the live board hit this,
    each with a ⚠ on the same row saying no blocker was recorded: the digest
    contradicted its own signal and sent the loop to start genuinely blocked work.
    """

    def test_blocked_status_with_no_recorded_blocker_is_not_unblocked(self):
        item = make_item(status="Blocked")
        self.assertNotEqual(signal_of(item), "UNBLOCKED")
        self.assertEqual(item.signal, "BLOCKED-UNRECORDED")

    def test_blocked_label_with_no_recorded_blocker_is_not_unblocked(self):
        """The legacy label-only items — surfaced as hygiene, not as a pickup."""
        item = make_item(status="In review", labels=["blocked", "needs:review"])
        self.assertEqual(signal_of(item), "BLOCKED-UNRECORDED")

    def test_the_signal_and_the_row_warning_now_agree(self):
        """The contradiction itself: signal said "go", the ⚠ said "nothing recorded"."""
        item = make_item(status="Blocked")
        signal_of(item)
        self.assertTrue(
            any("no recorded blocker" in w for w in item.warnings), item.warnings
        )
        self.assertNotEqual(item.signal, "UNBLOCKED")
        self.assertTrue(any("no blocker is recorded" in r for r in item.reasons), item.reasons)

    def test_the_reason_names_the_fix_rather_than_offering_a_pickup(self):
        item = make_item(status="Blocked")
        signal_of(item)
        reason = " ".join(item.reasons)
        self.assertIn("board-tick.py block", reason)
        self.assertNotIn("move it back to Ready", reason)

    def test_one_recorded_blocker_that_closed_still_unblocks(self):
        """The guard must not cost the real case its actionable signal."""
        item = make_item(status="Blocked", blockers=[blocker(9, "CLOSED")], blockers_total=1)
        self.assertEqual(signal_of(item), "UNBLOCKED")

    def test_unrecorded_is_a_skip_not_a_pickup_in_the_sort(self):
        """It ranks with the skips: there is no edge to watch, so no work to start."""
        self.assertGreater(
            bt.SIGNAL_ORDER.index("BLOCKED-UNRECORDED"), bt.SIGNAL_ORDER.index("READY")
        )
        self.assertGreater(
            bt.SIGNAL_ORDER.index("BLOCKED-UNRECORDED"), bt.SIGNAL_ORDER.index("UNBLOCKED")
        )

    def test_the_row_is_never_suppressed_from_details(self):
        item = make_item(status="Blocked")
        signal_of(item)
        out = bt.render_details([item], include_bots=False, body_limit=500)
        self.assertIn("BLOCKED-UNRECORDED", out)


class TestComputeSignalOtherBranches(unittest.TestCase):
    def test_human_input(self):
        item = make_item()
        item.comments.append(human_comment())
        self.assertEqual(signal_of(item), "HUMAN-INPUT")

    def test_pr_approved(self):
        self.assertEqual(signal_of(make_item(labels=["approved:pr"])), "PR-APPROVED")

    def test_spec_approved(self):
        item = make_item(labels=["approved:spec", "needs:spec-approval"])
        self.assertEqual(signal_of(item), "SPEC-APPROVED")

    def test_unpushed(self):
        self.assertEqual(
            signal_of(make_item(worktree="/tmp/wt", wt_unpushed=2)), "UNPUSHED"
        )

    def test_spec_merged(self):
        item = make_item(spec_pr_number=7, spec_pr_state="MERGED")
        self.assertEqual(signal_of(item), "SPEC-MERGED")

    def test_ci_red_on_failing_check(self):
        item = make_item(pr_number=3, pr_changed_files=4, ci_failing=["build"])
        self.assertEqual(signal_of(item), "CI-RED")

    def test_ci_red_on_conflict(self):
        item = make_item(pr_number=3, pr_changed_files=4, pr_mergeable="CONFLICTING")
        self.assertEqual(signal_of(item), "CI-RED")

    def test_threads(self):
        item = make_item(pr_number=3, pr_changed_files=4, unresolved_threads=2)
        self.assertEqual(signal_of(item), "THREADS")

    def test_waiting_owner(self):
        item = make_item(status="In review", labels=["needs:review"])
        self.assertEqual(signal_of(item), "WAITING-OWNER")

    def test_tracker(self):
        item = make_item(status="In progress", labels=["tracker"])
        self.assertEqual(signal_of(item), "TRACKER")

    def test_ready(self):
        self.assertEqual(signal_of(make_item(status="Ready")), "READY")

    def test_not_started(self):
        self.assertEqual(signal_of(make_item(status="In progress")), "NOT-STARTED")

    def test_wip(self):
        item = make_item(status="In progress", pr_number=3, pr_changed_files=5)
        self.assertEqual(signal_of(item), "WIP")

    def test_idle(self):
        self.assertEqual(signal_of(make_item(status="In review")), "IDLE")

    def test_every_chain_signal_is_reachable_by_some_test(self):
        """Sanity: the branch tests above cover the whole chain."""
        covered = {
            "HUMAN-INPUT", "UNBLOCKED", "PR-APPROVED", "SPEC-APPROVED", "UNPUSHED",
            "SPEC-MERGED", "CI-RED", "THREADS", "BLOCKED", "BLOCKED-UNRECORDED",
            "WAITING-OWNER", "TRACKER", "READY", "NOT-STARTED", "WIP", "IDLE",
        }
        self.assertEqual(set(chain_signals()), covered)


# ── hygiene warnings ────────────────────────────────────────────────────────


class TestBlockedHygiene(unittest.TestCase):
    def test_blocked_status_without_a_recorded_blocker_warns(self):
        item = make_item(status="Blocked")
        signal_of(item)
        self.assertTrue(
            any("blocked with no recorded blocker" in w for w in item.warnings), item.warnings
        )

    def test_legacy_label_without_blocked_status_warns_about_migration(self):
        item = make_item(status="In review", labels=["blocked"])
        signal_of(item)
        self.assertTrue(
            any("legacy `blocked` label" in w for w in item.warnings), item.warnings
        )

    def test_legacy_label_item_also_warns_about_the_missing_blocker(self):
        """The three legacy items carry the label and no dependency edge — both
        warnings apply, and they name two different fixes."""
        item = make_item(status="In review", labels=["blocked"])
        signal_of(item)
        self.assertTrue(
            any("blocked with no recorded blocker" in w for w in item.warnings), item.warnings
        )
        self.assertTrue(any("board-tick.py block" in w for w in item.warnings), item.warnings)

    def test_recorded_blocker_suppresses_the_missing_blocker_warning(self):
        item = make_item(status="Blocked", blockers=[blocker(9)], blockers_total=1)
        signal_of(item)
        self.assertFalse(
            any("no recorded blocker" in w for w in item.warnings), item.warnings
        )

    def test_all_blockers_closed_warns_to_move_to_ready(self):
        item = make_item(
            status="Blocked", blockers=[blocker(9, "CLOSED")], blockers_total=1
        )
        signal_of(item)
        self.assertTrue(any("move it to Ready" in w for w in item.warnings), item.warnings)

    def test_open_blocker_without_the_flag_warns(self):
        item = make_item(status="In progress", pr_number=1, pr_changed_files=2,
                         blockers=[blocker(9)], blockers_total=1)
        signal_of(item)
        self.assertTrue(
            any("not marked" in w and "dep#9" in w for w in item.warnings), item.warnings
        )

    def test_unfetched_blockers_warn(self):
        item = make_item(status="Blocked", blockers=[blocker(9)], blockers_total=25)
        signal_of(item)
        self.assertTrue(any("only 1 fetched" in w for w in item.warnings), item.warnings)

    def test_blocked_label_is_not_routed_to_in_review(self):
        """`blocked` belongs in Blocked, so it must not also say "In review"."""
        item = make_item(status="In progress", labels=["blocked"], blockers=[blocker(9)])
        signal_of(item)
        self.assertFalse(
            any("move to In review" in w for w in item.warnings), item.warnings
        )

    def test_blocked_label_no_longer_justifies_sitting_in_in_review(self):
        """In review = waiting on a human. `blocked` means waiting on an issue, so
        it must not be offered as a valid reason to be In review."""
        src = inspect.getsource(bt.compute_signal)
        self.assertNotIn("needs:*/blocked label", src)
        self.assertNotIn("is the blocker written on the issue", src)

    def test_in_review_warning_names_the_human_decision(self):
        item = make_item(status="In review", pr_number=3, pr_changed_files=2)
        signal_of(item)
        self.assertTrue(
            any("waiting on a human" in w for w in item.warnings), item.warnings
        )

    def test_in_review_with_no_pr_points_at_the_blocked_status(self):
        item = make_item(status="In review", labels=["needs:review"])
        signal_of(item)
        self.assertTrue(
            any("board-tick.py block" in w and "no PR" in w for w in item.warnings),
            item.warnings,
        )

    def test_blocked_flagged_item_is_not_told_off_twice_for_in_review(self):
        """check_blocked_hygiene already names the fix — no redundant pile-on."""
        item = make_item(status="In review", labels=["blocked"])
        signal_of(item)
        self.assertFalse(any("waiting on a human" in w for w in item.warnings), item.warnings)
        self.assertFalse(any("no PR" in w for w in item.warnings), item.warnings)

    def test_other_waiting_labels_still_route_to_in_review(self):
        item = make_item(status="In progress", labels=["needs:review"],
                         pr_number=1, pr_changed_files=2)
        signal_of(item)
        self.assertTrue(
            any("move to In review" in w for w in item.warnings), item.warnings
        )


# ── the suppression bug ─────────────────────────────────────────────────────


class TestDetailsSuppression(unittest.TestCase):
    def _render(self, item):
        bt.compute_signal(item)
        return bt.render_details([item], include_bots=False, body_limit=500)

    def test_blocked_item_is_never_suppressed(self):
        """A well-recorded blocked item has no pending comments and no warnings —
        the old `quiet` tuple printed nothing at all for it."""
        item = make_item(status="Blocked", blockers=[blocker(9)], blockers_total=1)
        out = self._render(item)
        self.assertIn(item.slug, out)
        self.assertIn("BLOCKED", out)
        self.assertIn("dep#9", out)

    def test_unblocked_item_is_never_suppressed(self):
        item = make_item(status="Blocked", blockers=[blocker(9, "CLOSED")], blockers_total=1)
        out = self._render(item)
        self.assertIn(item.slug, out)
        self.assertIn("UNBLOCKED", out)

    def test_blocker_url_is_printed(self):
        item = make_item(status="Blocked", blockers=[blocker(9)], blockers_total=1)
        self.assertIn("https://github.com/gaarutyunov/dep/issues/9", self._render(item))

    def test_idle_item_with_nothing_new_is_still_suppressed(self):
        """The lean-digest property the `quiet` tuple exists for must survive."""
        item = make_item(status="In review", labels=["approved:pr"])
        item.signal = "IDLE"  # set directly: no compute_signal, no warnings
        out = bt.render_details([item], include_bots=False, body_limit=500)
        self.assertEqual(out.strip(), "")


# ── table cells ─────────────────────────────────────────────────────────────


class TestBlkCell(unittest.TestCase):
    def test_no_blockers(self):
        self.assertEqual(bt.blk_cell(make_item()), "-")

    def test_partially_closed(self):
        item = make_item(
            blockers=[blocker(9, "CLOSED"), blocker(10, "OPEN")], blockers_total=2
        )
        self.assertEqual(bt.blk_cell(item), "1/2")

    def test_none_closed(self):
        item = make_item(blockers=[blocker(9), blocker(10)], blockers_total=2)
        self.assertEqual(bt.blk_cell(item), "0/2")

    def test_fully_unblocked_is_visually_distinct(self):
        item = make_item(
            blockers=[blocker(9, "CLOSED"), blocker(10, "CLOSED")], blockers_total=2
        )
        self.assertEqual(bt.blk_cell(item), "2/2✓")

    def test_total_count_beyond_the_fetched_page(self):
        item = make_item(blockers=[blocker(9, "CLOSED")], blockers_total=25)
        self.assertEqual(bt.blk_cell(item), "1/25")


class TestTableColumnAlignment(unittest.TestCase):
    def test_header_and_row_widths_match(self):
        items = [
            make_item(status="Blocked", blockers=[blocker(9)], blockers_total=1),
            make_item(number=2, status="Ready", pr_number=4, pr_changed_files=3),
        ]
        for it in items:
            bt.compute_signal(it)
        lines = bt.render_table(items).splitlines()
        header_cols = len(lines[0].split())
        self.assertEqual(header_cols, 16, "BLK must be added to headers exactly once")
        self.assertIn("BLK", lines[0].split())
        # Positional lists: a mismatch shifts every later column, so compare the
        # padded widths rather than the (variable) token counts.
        widths = [len(c) for c in re.findall(r"-+", lines[1])]
        self.assertEqual(len(widths), header_cols)

    def test_blk_column_sits_between_thr_and_pr(self):
        cols = bt.render_table([make_item()]).splitlines()[0].split()
        self.assertEqual(cols[cols.index("BLK") - 1], "THR")
        self.assertEqual(cols[cols.index("BLK") + 1], "PR")


# ── ledger round-trip ───────────────────────────────────────────────────────


class TestLedgerRoundTrip(unittest.TestCase):
    def test_documented_shape_round_trips(self):
        data = {"v": 1, "acked": {"issue": [1, 2], "pr": [3], "review": [], "spec": []}}
        out = bt.parse_ledger(bt.render_ledger(data))
        out.pop("updated", None)
        self.assertEqual(out, data)

    def test_unknown_top_level_keys_survive(self):
        """render_ledger re-emits every non-underscore key, so extra state
        round-trips without a new mechanism."""
        data = {"v": 1, "acked": {}, "blocked_note": "waiting on dep#9", "tries": 3}
        out = bt.parse_ledger(bt.render_ledger(data))
        self.assertEqual(out["blocked_note"], "waiting on dep#9")
        self.assertEqual(out["tries"], 3)

    def test_underscore_keys_are_dropped(self):
        data = {"v": 1, "acked": {}, "_comment_id": 999}
        out = bt.parse_ledger(bt.render_ledger(data))
        self.assertNotIn("_comment_id", out)

    def test_render_ledger_stamps_updated(self):
        self.assertIn("updated", bt.parse_ledger(bt.render_ledger({"v": 1, "acked": {}})))

    def test_unparseable_body_degrades_to_an_empty_ledger(self):
        self.assertEqual(bt.parse_ledger("no json here"), {"v": 1, "acked": {}})

    def test_ledger_comment_is_excluded_from_last_activity(self):
        """apply_issue must not count our own ledger write as activity — it would
        make a rotting task look fresh."""
        item = make_item()
        issue = {
            "createdAt": "2020-01-01T00:00:00Z",
            "labels": {"nodes": []},
            "blockedBy": {"totalCount": 0, "nodes": []},
            "comments": {
                "nodes": [
                    {
                        "databaseId": 5,
                        "author": {"login": "gaarutyunov"},
                        "body": bt.render_ledger({"v": 1, "acked": {}}),
                        "createdAt": "2030-01-01T00:00:00Z",
                        "url": "https://example.invalid/l",
                    }
                ]
            },
        }
        bt.apply_issue(item, issue)
        self.assertTrue(item.has_ledger)
        self.assertEqual(item.comments, [])
        self.assertEqual(item.last_activity, "2020-01-01T00:00:00Z")


# ── blocker refs and the GraphQL surface ────────────────────────────────────


class TestParseBlockerRef(unittest.TestCase):
    def test_bare_number_means_the_same_repo(self):
        self.assertEqual(bt.parse_blocker_ref("123", "demo"), ("gaarutyunov", "demo", 123))

    def test_hash_number_means_the_same_repo(self):
        self.assertEqual(bt.parse_blocker_ref("#123", "demo"), ("gaarutyunov", "demo", 123))

    def test_owner_repo_hash_number(self):
        self.assertEqual(
            bt.parse_blocker_ref("gaarutyunov/blog#31", "demo"), ("gaarutyunov", "blog", 31)
        )

    def test_other_owner_is_preserved(self):
        self.assertEqual(
            bt.parse_blocker_ref("someone/other#7", "demo"), ("someone", "other", 7)
        )

    def test_repo_hash_number_defaults_the_owner(self):
        self.assertEqual(
            bt.parse_blocker_ref("postgres-pglite#6", "demo"),
            ("gaarutyunov", "postgres-pglite", 6),
        )

    def test_surrounding_whitespace_is_tolerated(self):
        self.assertEqual(bt.parse_blocker_ref("  #9 ", "demo"), ("gaarutyunov", "demo", 9))

    def test_garbage_is_rejected(self):
        for bad in ("", "abc", "demo#", "#", "1/2/3"):
            with self.subTest(ref=bad):
                with self.assertRaises(RuntimeError):
                    bt.parse_blocker_ref(bad, "demo")


class TestMutationText(unittest.TestCase):
    def test_add_mutation_shape(self):
        out = bt.blocked_by_mutation("add", "I_target", "I_blocking")
        self.assertIn("addBlockedBy", out)
        self.assertIn('issueId: "I_target"', out)
        self.assertIn('blockingIssueId: "I_blocking"', out)

    def test_remove_mutation_shape(self):
        out = bt.blocked_by_mutation("remove", "I_target", "I_blocking")
        self.assertIn("removeBlockedBy", out)
        self.assertNotIn("addBlockedBy", out)

    def test_status_move_command_uses_the_blocked_option_id(self):
        cmd = bt.status_move_command("PVTI_x", "Blocked")
        self.assertIn("--single-select-option-id 8351b71b", cmd)
        self.assertIn(f"--field-id {bt.STATUS_FIELD_ID}", cmd)
        self.assertIn(f"--project-id {bt.PROJECT_NODE_ID}", cmd)

    def test_status_move_command_for_ready(self):
        self.assertIn("61e4505c", bt.status_move_command("PVTI_x", "Ready"))


class TestIssueFragment(unittest.TestCase):
    def test_blocked_by_rides_along_with_the_issue_query(self):
        """Free: no extra API call, so the digest cost is unchanged."""
        self.assertIn("blockedBy", bt.ISSUE_FRAGMENT)
        self.assertIn("totalCount", bt.ISSUE_FRAGMENT)
        self.assertIn("nameWithOwner", bt.ISSUE_FRAGMENT)

    def test_apply_blockers_reads_the_payload(self):
        item = make_item()
        bt.apply_blockers(
            item,
            {
                "blockedBy": {
                    "totalCount": 2,
                    "nodes": [
                        {
                            "number": 28,
                            "state": "OPEN",
                            "title": "moisture sensor",
                            "url": "https://github.com/gaarutyunov/blog/issues/28",
                            "createdAt": "2020-01-01T00:00:00Z",
                            "repository": {"nameWithOwner": "gaarutyunov/blog"},
                        },
                        {
                            "number": 9,
                            "state": "CLOSED",
                            "title": "done thing",
                            "url": "https://github.com/gaarutyunov/gopgql/issues/9",
                            "createdAt": "2020-01-01T00:00:00Z",
                            "repository": {"nameWithOwner": "gaarutyunov/gopgql"},
                        },
                    ],
                }
            },
        )
        self.assertEqual(item.blockers_total, 2)
        self.assertEqual([b.slug for b in item.open_blockers], ["blog#28"])
        self.assertEqual([b.slug for b in item.closed_blockers], ["gopgql#9"])

    def test_missing_blocked_by_is_handled(self):
        item = make_item()
        bt.apply_blockers(item, {})
        self.assertEqual(item.blockers, [])
        self.assertEqual(item.blockers_total, 0)


class TestBlockedFlagged(unittest.TestCase):
    def test_status_alone_flags(self):
        self.assertTrue(make_item(status="Blocked").blocked_flagged)

    def test_label_alone_flags(self):
        self.assertTrue(make_item(status="In review", labels=["blocked"]).blocked_flagged)

    def test_neither_does_not_flag(self):
        self.assertFalse(make_item(status="Ready").blocked_flagged)


# ── JSON output ─────────────────────────────────────────────────────────────


class TestRenderJson(unittest.TestCase):
    def test_blockers_and_signal_are_exposed(self):
        import json as _json

        item = make_item(
            status="Blocked",
            blockers=[blocker(9, "CLOSED"), blocker(10, "OPEN")],
            blockers_total=2,
        )
        bt.compute_signal(item)
        payload = _json.loads(bt.render_json([item]))[0]
        self.assertEqual(payload["signal"], "BLOCKED")
        self.assertEqual(payload["blocked"]["total"], 2)
        self.assertEqual(payload["blocked"]["open"], 1)
        self.assertEqual(payload["blocked"]["closed"], 1)
        self.assertTrue(payload["blocked"]["flagged"])
        self.assertEqual(
            [b["number"] for b in payload["blocked"]["blockers"]], [9, 10]
        )
        self.assertIn("url", payload["blocked"]["blockers"][0])

    def test_unblocked_signal_is_exposed(self):
        import json as _json

        item = make_item(status="Blocked", blockers=[blocker(9, "CLOSED")], blockers_total=1)
        bt.compute_signal(item)
        payload = _json.loads(bt.render_json([item]))[0]
        self.assertEqual(payload["signal"], "UNBLOCKED")
        self.assertEqual(payload["blocked"]["open"], 0)


# ── spec-PR discovery ───────────────────────────────────────────────────────


class TestSpecBranchKey(unittest.TestCase):
    """Every branch style a tick has ever produced must resolve to (repo, issue).

    A branch that fails to parse means the spec PR is never found, which means the
    owner's spec feedback is never read — the failure this test exists to prevent.
    """

    def test_trailing_slug(self):
        # The style the spec flow actually produces, and the one `fullmatch`
        # without a slug group silently dropped.
        self.assertEqual(bt.spec_branch_key("spec/goga-1-framework-foundations"), ("goga", 1))
        self.assertEqual(
            bt.spec_branch_key("spec/gopgql-issue-38-migration-modes"), ("gopgql", 38)
        )
        self.assertEqual(
            bt.spec_branch_key("spec/gopgql-issue-9-m7-full-sdl-conformance"), ("gopgql", 9)
        )
        self.assertEqual(
            bt.spec_branch_key("spec/ui-kit-6-workout-components"), ("ui-kit", 6)
        )

    def test_no_slug(self):
        self.assertEqual(bt.spec_branch_key("spec/gopgql-issue-38"), ("gopgql", 38))
        self.assertEqual(bt.spec_branch_key("spec-ui-kit-6"), ("ui-kit", 6))
        self.assertEqual(bt.spec_branch_key("spec/ui-kit-issue-10"), ("ui-kit", 10))

    def test_repo_group_does_not_swallow_the_issue_number(self):
        # `repo` is non-greedy: a slug starting with digits must not be mistaken
        # for the issue number, and the repo must not absorb it either.
        self.assertEqual(bt.spec_branch_key("spec/ui-kit-6-workout-components"), ("ui-kit", 6))
        self.assertEqual(bt.spec_branch_key("spec/ui-kit-6-2fa-support"), ("ui-kit", 6))
        self.assertEqual(bt.spec_branch_key("spec/goga-12-multi-digit"), ("goga", 12))

    # Every branch below is a real head ref in gaarutyunov/workspace (or, for
    # mcp-anything, the naming a repo with two hyphens would produce). Hyphens in
    # the repo name are the hard case: the parse has to know which hyphen run
    # starts the issue number, and the only signal is "the first `-<digits>`
    # that leaves a valid remainder".
    REAL_BRANCHES = [
        ("spec/goga-1-framework-foundations", ("goga", 1)),
        ("spec/gopgql-issue-38-v2", ("gopgql", 38)),
        ("spec/gopgql-issue-38-d4a", ("gopgql", 38)),
        ("spec/gopgql-14-http", ("gopgql", 14)),
        ("spec/mcp-anything-issue-142", ("mcp-anything", 142)),
        ("spec/site-review-issue-2", ("site-review", 2)),
        ("spec/ui-kit-issue-10", ("ui-kit", 10)),
        ("spec-ui-kit-6", ("ui-kit", 6)),
        ("spec-gopgql-14", ("gopgql", 14)),
        ("spec/garutyunov-com-issue-5", ("garutyunov-com", 5)),
        ("spec/epos-issue-44", ("epos", 44)),
    ]

    def test_every_real_branch_style(self):
        for branch, expected in self.REAL_BRANCHES:
            with self.subTest(branch=branch):
                self.assertEqual(bt.spec_branch_key(branch), expected)

    def test_rejects_non_spec_branches(self):
        # `fix/digest-spec-pr-blindspots` is a real branch and contains "spec":
        # a substring match rather than an anchored one would claim it.
        for branch in (
            "main",
            "issue-38",
            "spec/nonumber",
            "fix/digest-spec-pr-blindspots",
            "archive-issue-12",
        ):
            with self.subTest(branch=branch):
                self.assertIsNone(bt.spec_branch_key(branch))

    def test_rejects_a_number_not_separated_from_its_slug(self):
        # Better to miss than to guess: `1abc` is not issue 1.
        self.assertIsNone(bt.spec_branch_key("spec/goga-1abc"))


class TestAttachSpecPrs(unittest.TestCase):
    """When several spec branches collide on one key, the right PR must win.

    Accepting a trailing slug means a respun spec no longer gets a key of its
    own: `spec/gopgql-issue-38`, `…-v2` and `…-d4a` are all (gopgql, 38). Picking
    the wrong one of those points the digest at a stale PR's comments — the same
    class of failure as not finding the PR at all.
    """

    def setUp(self):
        self._gh = bt.gh
        self.addCleanup(lambda: setattr(bt, "gh", self._gh))

    def _attach(self, prs, repo="gopgql", number=38):
        # `gh pr list` returns newest first; mirror that so the test would catch
        # a re-introduction of "last write wins".
        listing = sorted(prs, key=lambda p: p["number"], reverse=True)
        bt.gh = lambda *a, **k: json.dumps(listing)
        item = make_item(repo=repo, number=number)
        bt.attach_spec_prs([item])
        return item

    @staticmethod
    def _pr(number, branch, state):
        return {
            "number": number,
            "headRefName": branch,
            "state": state,
            "url": f"https://example.test/pull/{number}",
        }

    def test_newest_of_several_merged_respins_wins(self):
        item = self._attach(
            [
                self._pr(33, "spec/gopgql-issue-38", "MERGED"),
                self._pr(37, "spec/gopgql-issue-38-v2", "MERGED"),
                self._pr(43, "spec/gopgql-issue-38-d4a", "MERGED"),
            ]
        )
        self.assertEqual(item.spec_pr_number, 43)
        self.assertEqual(item.spec_pr_state, "MERGED")

    def test_open_respin_beats_an_older_merged_spec(self):
        # The one that changes an answer: a merged spec would read as approved
        # and hide the respin the owner is still reviewing.
        item = self._attach(
            [
                self._pr(33, "spec/gopgql-issue-38", "MERGED"),
                self._pr(50, "spec/gopgql-issue-38-v3", "OPEN"),
            ]
        )
        self.assertEqual(item.spec_pr_number, 50)
        self.assertTrue(item.spec_pr_state == "OPEN")

    def test_open_beats_merged_even_when_it_is_the_lower_number(self):
        item = self._attach(
            [
                self._pr(50, "spec/gopgql-issue-38-v3", "MERGED"),
                self._pr(33, "spec/gopgql-issue-38", "OPEN"),
            ]
        )
        self.assertEqual(item.spec_pr_number, 33)

    def test_an_abandoned_closed_respin_never_wins(self):
        item = self._attach(
            [
                self._pr(33, "spec/gopgql-issue-38", "MERGED"),
                self._pr(60, "spec/gopgql-issue-38-abandoned", "CLOSED"),
            ]
        )
        self.assertEqual(item.spec_pr_number, 33)

    def test_a_lone_closed_spec_pr_is_still_reported(self):
        # Ranked last, but a closed spec PR is better than pretending none exists.
        item = self._attach([self._pr(60, "spec/gopgql-issue-38", "CLOSED")])
        self.assertEqual(item.spec_pr_number, 60)

    def test_goga_1_finds_pr_36(self):
        # The live regression: PR #36 on a trailing-slug branch, previously
        # unmatched, leaving goga#1 reading as "in review with no PR".
        item = self._attach(
            [self._pr(36, "spec/goga-1-framework-foundations", "OPEN")],
            repo="goga",
            number=1,
        )
        self.assertEqual(item.spec_pr_number, 36)
        self.assertEqual(item.spec_pr_url, "https://example.test/pull/36")

    def test_a_non_spec_branch_is_not_attached(self):
        item = self._attach([self._pr(99, "fix/digest-spec-pr-blindspots", "OPEN")])
        self.assertIsNone(item.spec_pr_number)


# ── unsubmitted (PENDING) review comments ───────────────────────────────────


def draft_review_comment(cid: int, path: str, line: int, body: str) -> dict:
    """One inline comment node as it arrives under a review's `comments`."""
    return {
        "databaseId": cid,
        "author": {"login": bt.OWNER},
        "body": body,
        "createdAt": "2026-07-28T05:17:19Z",
        "url": f"https://example.test/#discussion_r{cid}",
        "path": path,
        "line": line,
    }


class TestPendingReviewComments(unittest.TestCase):
    """Comments in an unsubmitted review are owner direction and must surface."""

    def _spec_payload(self):
        return {
            "state": "OPEN",
            "url": "https://example.test/pull/36",
            "comments": {"nodes": []},
            "reviews": {
                "nodes": [
                    {
                        "databaseId": 4793987058,
                        "author": {"login": bt.OWNER},
                        "body": "",
                        "state": "PENDING",
                        "submittedAt": None,
                        "url": "https://example.test/pull/36",
                        "comments": {
                            "nodes": [
                                draft_review_comment(
                                    3662973631, "design.md", 114, "Sqlc will appear in codiq"
                                ),
                                draft_review_comment(
                                    3663003636, "tasks.md", 73, "What are these?"
                                ),
                            ]
                        },
                    }
                ]
            },
            # GitHub also exposes each draft comment as an unresolved thread; the
            # digest must count the thread once and the comment once.
            "reviewThreads": {
                "nodes": [
                    {
                        "isResolved": False,
                        "path": "design.md",
                        "line": 114,
                        "comments": {
                            "nodes": [
                                draft_review_comment(
                                    3662973631, "design.md", 114, "Sqlc will appear in codiq"
                                )
                            ]
                        },
                    },
                    {
                        "isResolved": False,
                        "path": "tasks.md",
                        "line": 73,
                        "comments": {
                            "nodes": [
                                draft_review_comment(
                                    3663003636, "tasks.md", 73, "What are these?"
                                )
                            ]
                        },
                    },
                ]
            },
        }

    def test_drafts_land_in_the_human_pool_marked_and_deduped(self):
        item = make_item(status="In review", spec_pr_number=36)
        bt.apply_spec(item, self._spec_payload())

        self.assertEqual(len(item.pending_human), 2)
        self.assertEqual(len(item.pending_draft), 2)
        self.assertEqual({c.kind for c in item.pending_draft}, {"pending"})
        self.assertEqual({c.draft_on for c in item.pending_draft}, {"spec PR #36"})
        self.assertEqual(
            sorted(c.cid for c in item.pending_draft), [3662973631, 3663003636]
        )
        # The thread pass must not re-add them under kind "spec".
        self.assertEqual([c.cid for c in item.comments].count(3662973631), 1)
        self.assertEqual(item.spec_unresolved_threads, 2)

    def test_drafts_drive_the_signal_and_the_hum_cell(self):
        item = make_item(status="In review", spec_pr_number=36)
        bt.apply_spec(item, self._spec_payload())
        bt.compute_signal(item)

        self.assertEqual(item.signal, "HUMAN-INPUT")
        self.assertIn("unsubmitted review", " ".join(item.reasons))
        self.assertTrue(bt.hum_cell(item).endswith("+2✎"))

    def test_details_flags_the_unsubmitted_state(self):
        item = make_item(status="In review", spec_pr_number=36, spec_pr_state="OPEN")
        bt.apply_spec(item, self._spec_payload())
        bt.compute_signal(item)
        text = bt.render_details([item], include_bots=False, body_limit=500)

        self.assertIn("UNSUBMITTED", text)
        self.assertIn("DRAFT REVIEW", text)
        self.assertIn("3662973631", text)

    def test_acked_drafts_stay_gone(self):
        item = make_item(status="In review", spec_pr_number=36)
        bt.apply_spec(item, self._spec_payload())
        item.ledger = {"v": 1, "acked": {"pending": [3662973631]}}
        bt.drop_acked(item)

        self.assertEqual([c.cid for c in item.pending_human], [3663003636])

    def test_submitted_reviews_are_unaffected(self):
        """A submitted review's comments still arrive via its thread, kind `spec`."""
        payload = self._spec_payload()
        payload["reviews"]["nodes"][0].update(
            state="CHANGES_REQUESTED", submittedAt="2026-07-28T06:00:00Z", body="please fix"
        )
        item = make_item(status="In review", spec_pr_number=36)
        bt.apply_spec(item, payload)

        self.assertEqual(item.pending_draft, [])
        self.assertIn("spec", {c.kind for c in item.pending_human})

    def test_pending_is_a_ledger_bucket(self):
        item = make_item()
        item.ledger = {"v": 1, "acked": {"pending": [1, 2], "spec": [3]}}
        self.assertEqual(bt.acked_ids(item), {1, 2, 3})


# ── the "in review with no PR" warning ──────────────────────────────────────


class TestNoPrWarning(unittest.TestCase):
    """`in review with no PR` must only fire when nothing explains the absence.

    A ⚠ that fires on a healthy task is worse than no ⚠ at all — it teaches the
    loop to skim past the hygiene warnings that do matter.
    """

    WARNING = "in review with no PR"

    def _warns(self, **kw):
        item = make_item(status="In review", **kw)
        bt.compute_signal(item)
        return any(self.WARNING in w for w in item.warnings)

    def test_fires_when_there_is_genuinely_nothing_to_show(self):
        self.assertTrue(self._warns(labels=["needs:review"]))

    def test_silent_for_a_spec_only_task_awaiting_the_spec_gate(self):
        # goga#1: spec PR open, spec gate not passed, so no code PR *by design*.
        self.assertFalse(
            self._warns(labels=["needs:spec-approval"], spec_pr_number=36, spec_pr_state="OPEN")
        )

    def test_still_fires_when_the_spec_pr_is_missing(self):
        # `needs:spec-approval` with no spec PR to approve is exactly the state
        # blind spot 1 produced — the label claims a gate that isn't there.
        self.assertTrue(self._warns(labels=["needs:spec-approval"]))

    def test_still_fires_when_the_label_is_missing(self):
        # A spec PR with no needs:spec-approval is unexplained — the loop either
        # forgot the label or the spec already cleared and coding never started.
        self.assertTrue(self._warns(labels=[], spec_pr_number=36, spec_pr_state="OPEN"))

    def test_silent_when_blocked_or_a_question_is_out(self):
        self.assertFalse(self._warns(labels=["blocked"]))
        self.assertFalse(self._warns(labels=["needs:input"]))

    def test_silent_when_a_code_pr_exists(self):
        self.assertFalse(self._warns(labels=["needs:review"], pr_number=40))


# ── truncated connections ───────────────────────────────────────────────────


class TestTruncation(unittest.TestCase):
    """A cap that bites must never be silent."""

    def test_warns_naming_the_connection_and_both_numbers(self):
        item = make_item()
        nodes = bt.note_truncation(
            item, {"totalCount": 47, "nodes": [{"databaseId": i} for i in range(30)]},
            "spec PR #36 review threads",
        )
        self.assertEqual(len(nodes), 30)  # still returns what it got
        self.assertEqual(len(item.warnings), 1)
        warning = item.warnings[0]
        self.assertIn("TRUNCATED", warning)
        self.assertIn("spec PR #36 review threads", warning)
        self.assertIn("30 of 47", warning)
        self.assertIn("17 not seen", warning)

    def test_silent_when_nothing_was_dropped(self):
        item = make_item()
        bt.note_truncation(item, {"totalCount": 4, "nodes": [1, 2, 3, 4]}, "x")
        bt.note_truncation(item, {"totalCount": 0, "nodes": []}, "x")
        bt.note_truncation(item, None, "x")
        bt.note_truncation(item, {"nodes": [1]}, "x")  # totalCount not selected
        self.assertEqual(item.warnings, [])

    def test_truncation_forces_an_otherwise_quiet_row_into_details(self):
        item = make_item(status="In review", labels=["needs:review"])
        bt.note_truncation(item, {"totalCount": 9, "nodes": [1]}, "PR #40 comments")
        bt.compute_signal(item)
        self.assertEqual(item.signal, "WAITING-OWNER")  # a normally-skipped row
        self.assertIn("TRUNCATED", bt.render_details([item], False, 200))

    def test_every_capped_connection_selects_total_count(self):
        """A `first:`/`last:` with no sibling totalCount can truncate silently."""
        for name, fragment in (
            ("ISSUE_FRAGMENT", bt.ISSUE_FRAGMENT),
            ("SPEC_FRAGMENT", bt.SPEC_FRAGMENT),
            ("PR_FRAGMENT", bt.PR_FRAGMENT),
        ):
            with self.subTest(fragment=name):
                caps = len(re.findall(r"\((?:first|last):\s*\d+\)", fragment))
                totals = fragment.count("totalCount")
                # `labels` is the one deliberate exception: 50 labels on one issue
                # is not a real state, and a ⚠ there would be pure noise.
                expected = caps - fragment.count("labels(first:")
                self.assertGreaterEqual(totals, expected, f"{name}: {totals} < {expected}")


# ── the GraphQL rate-limit guard ────────────────────────────────────────────


class TestRateLimitGuard(unittest.TestCase):
    """A tick that cannot see the board must not look like one that saw it empty.

    Every test here stubs the budget — none of them touch the network, which is
    the point: measuring this against the live API is what exhausted it.
    """

    def setUp(self):
        self._budget = bt.graphql_budget
        self._gh = bt.gh
        self.addCleanup(lambda: setattr(bt, "graphql_budget", self._budget))
        self.addCleanup(lambda: setattr(bt, "gh", self._gh))

    def _budget_is(self, remaining, limit=5000, reset_in_s=840):
        import time

        bt.graphql_budget = lambda: (remaining, limit, int(time.time()) + reset_in_s)

    def test_preflight_passes_with_headroom(self):
        self._budget_is(5000)
        self.assertIsNone(bt.preflight(bt.MIN_GRAPHQL_BUDGET))

    def test_preflight_refuses_when_exhausted(self):
        self._budget_is(0)
        banner = bt.preflight(bt.MIN_GRAPHQL_BUDGET)
        self.assertIsNotNone(banner)
        self.assertIn("EXHAUSTED", banner)
        self.assertIn("NOTHING WAS READ", banner)
        self.assertIn("0/5000", banner)
        self.assertIn("resets", banner)
        self.assertRegex(banner, r"resets \d{4}-\d\d-\d\d \d\d:\d\d UTC \(in \d+m\)")

    def test_preflight_refuses_when_merely_too_low(self):
        self._budget_is(50)
        banner = bt.preflight(bt.MIN_GRAPHQL_BUDGET)
        self.assertIn("TOO LOW", banner)
        self.assertIn("50 point(s) left", banner)

    def test_banner_names_the_misleading_gh_error(self):
        # Anyone debugging this otherwise chases token scopes.
        self._budget_is(0)
        banner = bt.preflight(bt.MIN_GRAPHQL_BUDGET)
        self.assertIn("unknown owner type", banner)
        self.assertIn("gh api rate_limit", banner)

    def test_preflight_proceeds_when_the_budget_is_unreadable(self):
        bt.graphql_budget = lambda: None
        self.assertIsNone(bt.preflight(bt.MIN_GRAPHQL_BUDGET))

    def test_min_budget_zero_disables_the_gate(self):
        self._budget_is(1)
        self.assertIsNone(bt.preflight(0))

    def test_cmd_tick_refuses_loudly_and_nonzero(self):
        self._budget_is(0)
        calls = []
        bt.gh = lambda *a, **k: calls.append(a) or ""
        ns = argparse.Namespace(
            loop=None, repo=None, status=None, include_bots=False, body_limit=50,
            projects_dir="/nonexistent", no_local=True, json=True,
            min_budget=bt.MIN_GRAPHQL_BUDGET,
        )
        err = io.StringIO()
        out = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(out):
            code = bt.cmd_tick(ns)
        self.assertEqual(code, 75)  # EX_TEMPFAIL
        self.assertEqual(calls, [])  # refused before touching the API
        self.assertIn("EXHAUSTED", err.getvalue())
        # Critically: no output on stdout, so --json cannot yield a valid-looking
        # empty board that a caller would treat as "nothing to do".
        self.assertEqual(out.getvalue(), "")

    def test_a_rate_limited_gh_failure_raises_RateLimited(self):
        self._budget_is(0)
        original_run = bt.subprocess.run

        class Proc:
            returncode = 1
            stdout = ""
            stderr = "gh: API rate limit already exceeded for user ID 1."

        bt.subprocess.run = lambda *a, **k: Proc()
        try:
            with self.assertRaises(bt.RateLimited):
                bt.gh("api", "graphql", "-f", "query=x")
        finally:
            bt.subprocess.run = original_run

    def test_the_misleading_error_is_classified_by_the_real_budget(self):
        """`unknown owner type` is a rate limit when the budget says so."""
        self._budget_is(0)
        original_run = bt.subprocess.run

        class Proc:
            returncode = 1
            stdout = ""
            stderr = "unknown owner type"

        bt.subprocess.run = lambda *a, **k: Proc()
        try:
            with self.assertRaises(bt.RateLimited):
                bt.gh("project", "item-list", "6")
        finally:
            bt.subprocess.run = original_run

    def test_a_genuine_error_stays_a_plain_RuntimeError(self):
        """A real bug must not be excused as a rate limit."""
        self._budget_is(5000)
        original_run = bt.subprocess.run

        class Proc:
            returncode = 1
            stdout = ""
            stderr = "unknown owner type"

        bt.subprocess.run = lambda *a, **k: Proc()
        try:
            with self.assertRaises(RuntimeError) as ctx:
                bt.gh("project", "item-list", "6")
            self.assertNotIsInstance(ctx.exception, bt.RateLimited)
        finally:
            bt.subprocess.run = original_run

    def test_a_rate_limited_graphql_payload_is_not_a_plain_query_error(self):
        """The budget can run out *inside* a 200 response, in the errors array."""
        bt.gh = lambda *a, **k: json.dumps(
            {"errors": [{"type": "RATE_LIMITED", "message": "API rate limit exceeded"}]}
        )
        with self.assertRaises(bt.RateLimited):
            bt.gh_graphql("query {x}")

    def test_an_ordinary_graphql_error_stays_a_plain_RuntimeError(self):
        bt.gh = lambda *a, **k: json.dumps(
            {"errors": [{"type": "NOT_FOUND", "message": "Could not resolve to an Issue"}]}
        )
        with self.assertRaises(RuntimeError) as ctx:
            bt.gh_graphql("query {x}")
        self.assertNotIsInstance(ctx.exception, bt.RateLimited)


# ── the local (LOCAL / UNPUSHED) check ──────────────────────────────────────


class TestLocalCheck(unittest.TestCase):
    """`LOCAL -` must mean "I looked", never "I could not look".

    LOCAL is what produces `UNPUSHED`, the only signal guarding against work lost
    outright — so a silently-skipped local check is the most expensive false
    reassurance the digest can give.
    """

    def _projects(self, *repos):
        """A projects dir like a worktree's: real, but holding only .gitignore."""
        import tempfile

        root = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(root, ignore_errors=True))
        (root / ".gitignore").write_text("*\n")
        for repo in repos:
            (root / repo).mkdir()
        return root

    def test_missing_clone_is_unknown_not_clean(self):
        item = make_item(repo="goga")
        bt.inspect_worktree(item, self._projects())  # dir exists, no clones
        self.assertFalse(item.local_checked)
        self.assertEqual(bt.local_cell(item), "?")

    def test_present_clone_with_no_worktree_is_clean(self):
        item = make_item(repo="goga")
        bt.inspect_worktree(item, self._projects("goga"))
        self.assertTrue(item.local_checked)
        self.assertEqual(bt.local_cell(item), "-")

    def test_run_level_warning_when_nothing_could_be_checked(self):
        projects = self._projects()
        items = [make_item(repo="goga"), make_item(repo="epos")]
        for it in items:
            bt.inspect_worktree(it, projects)
        notice = bt.local_check_notice(items, projects, no_local=False)
        self.assertIsNotNone(notice)
        self.assertIn("ANY task", notice)
        self.assertIn("UNPUSHED cannot fire", notice)
        self.assertIn("git worktree", notice)
        self.assertIn(str(projects), notice)

    def test_no_run_level_warning_when_some_clone_was_found(self):
        projects = self._projects("goga")
        items = [make_item(repo="goga"), make_item(repo="epos")]
        for it in items:
            bt.inspect_worktree(it, projects)
        self.assertIsNone(bt.local_check_notice(items, projects, no_local=False))
        # …but the unchecked row still says so for itself.
        self.assertEqual(bt.local_cell(items[1]), "?")

    def test_no_local_flag_is_also_unknown(self):
        items = [make_item(repo="goga")]
        notice = bt.local_check_notice(items, "/anywhere", no_local=True)
        self.assertIn("--no-local", notice)
        self.assertIn("will NOT be reported", notice)
        self.assertEqual(bt.local_cell(items[0]), "?")

    def test_diagnose_empty_does_not_claim_a_missing_worktree(self):
        unchecked = make_item(status="In progress")
        self.assertIn("local state is unknown", bt.diagnose_empty(unchecked))

        checked = make_item(status="In progress")
        checked.local_checked = True
        self.assertIn("no local worktree", bt.diagnose_empty(checked))

    def test_spec_worktree_is_not_derivable_from_the_branch_name(self):
        """Why the lookup goes through `git worktree list` and not a convention."""
        for branch, directory in [
            ("spec/garutyunov-com-issue-5", "spec-issue-5"),
            ("spec/goga-1-framework-foundations", "spec-goga-1"),
            ("spec/gopgql-14-http", "spec-gopgql-14-http"),
            ("spec-ui-kit-6", "spec-ui-kit-6"),
        ]:
            self.assertIsNotNone(bt.spec_branch_key(branch), branch)
            # The point: no rule turns the branch into the directory. All four
            # are real, and three of them disagree with any naming convention.
        self.assertNotIn("garutyunov-com", "spec-issue-5")


class TestSpecWorktreeLocalCheck(unittest.TestCase):
    """The spec half of a task lives in a *different repo*, and nothing looked.

    goga#1 held an entire uncommitted revision round in
    `workspace/.worktrees/spec-goga-1` for three days while every digest
    reported `LOCAL -`. The case that actually happened was a **committed but
    unpushed** commit, so that is the one asserted hardest here.
    """

    def _workspace(self, *branches):
        """A real workspace repo with a worktree per branch. Returns its root.

        Real git, not a mock: the existing local-state tests build real repos
        (see `test_workspace_root_resolves_the_main_worktree`), and the whole
        bug was about what git actually reports.

        **A bare remote with `main` pushed is not optional.** Unpushed commits
        are counted as `rev-list HEAD --not --remotes`, so in a repo with no
        remote *every* commit is unpushed and every fixture worktree would look
        stranded — the fixture has to match the real workspace, which has an
        origin, or the tests assert a state that cannot occur.
        """
        import subprocess
        import tempfile

        root = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(root, ignore_errors=True))
        origin = root / "origin.git"
        main = root / "workspace"
        main.mkdir()
        run = lambda *a, **k: subprocess.run(
            a, cwd=k.get("cwd", main), capture_output=True, check=True
        )
        subprocess.run(["git", "init", "-q", "--bare", str(origin)],
                       capture_output=True, check=True)
        run("git", "init", "-q", "-b", "main")
        run("git", "config", "user.email", "t@t.t")
        run("git", "config", "user.name", "t")
        (main / "README.md").write_text("x\n")
        run("git", "add", "README.md")
        run("git", "commit", "-qm", "init")
        run("git", "remote", "add", "origin", str(origin))
        run("git", "push", "-q", "origin", "main")
        for branch, directory in branches:
            run("git", "worktree", "add", "-q", "-b", branch,
                str(main / ".worktrees" / directory))
        return main

    def _commit(self, path, name="extra.md"):
        import subprocess

        (path / name).write_text("spec revision\n")
        subprocess.run(["git", "add", name], cwd=path, capture_output=True, check=True)
        subprocess.run(["git", "commit", "-qm", "revision round"],
                       cwd=path, capture_output=True, check=True)

    def _dirty(self, path, name="draft.md"):
        (path / name).write_text("uncommitted\n")

    # ── the case that actually happened ─────────────────────────────────────

    def test_spec_worktree_with_unpushed_commit_is_seen(self):
        ws = self._workspace(("spec/goga-1-framework-foundations", "spec-goga-1"))
        self._commit(ws / ".worktrees" / "spec-goga-1")
        item = make_item(repo="goga", number=1)
        item.local_checked = True  # code side looked, found nothing
        bt.inspect_spec_worktree(item, bt.spec_worktrees(ws))
        self.assertEqual(item.spec_wt_unpushed, 1)
        self.assertEqual(item.spec_wt_dirty, 0)
        self.assertTrue(item.local_work, "a committed-but-unpushed spec is stranded work")
        self.assertEqual(bt.local_cell(item), "spec:1c")
        self.assertEqual(signal_of(item), "UNPUSHED")

    def test_warning_names_the_spec_path(self):
        ws = self._workspace(("spec/goga-1-framework-foundations", "spec-goga-1"))
        self._commit(ws / ".worktrees" / "spec-goga-1")
        item = make_item(repo="goga", number=1)
        item.local_checked = True
        bt.inspect_spec_worktree(item, bt.spec_worktrees(ws))
        bt.compute_signal(item)
        warning = "\n".join(item.warnings)
        self.assertIn("spec-goga-1", warning)
        self.assertIn("1 unpushed commit(s)", warning)

    # ── the rest of the matrix ──────────────────────────────────────────────

    def test_spec_worktree_dirty(self):
        ws = self._workspace(("spec/epos-issue-44", "spec-epos-44"))
        self._dirty(ws / ".worktrees" / "spec-epos-44")
        item = make_item(repo="epos", number=44)
        item.local_checked = True
        bt.inspect_spec_worktree(item, bt.spec_worktrees(ws))
        self.assertEqual((item.spec_wt_unpushed, item.spec_wt_dirty), (0, 1))
        self.assertEqual(bt.local_cell(item), "spec:1f")

    def test_both_worktrees_dirty_renders_both(self):
        ws = self._workspace(("spec/goga-1-framework-foundations", "spec-goga-1"))
        self._commit(ws / ".worktrees" / "spec-goga-1")
        item = make_item(repo="goga", number=1, worktree="/tmp/code",
                         wt_unpushed=2, wt_dirty=3)
        item.local_checked = True
        bt.inspect_spec_worktree(item, bt.spec_worktrees(ws))
        self.assertEqual(bt.local_cell(item), "code:2c+3f spec:1c")
        bt.compute_signal(item)
        warning = "\n".join(item.warnings)
        self.assertIn("/tmp/code", warning)
        self.assertIn("spec-goga-1", warning)

    def test_spec_worktree_clean_does_not_fire(self):
        ws = self._workspace(("spec/goga-1-framework-foundations", "spec-goga-1"))
        item = make_item(repo="goga", number=1)
        item.local_checked = True
        bt.inspect_spec_worktree(item, bt.spec_worktrees(ws))
        self.assertTrue(item.spec_local_checked)
        self.assertFalse(item.local_work)
        self.assertEqual(bt.local_cell(item), "clean")

    def test_spec_branch_exists_but_worktree_is_not_on_this_machine(self):
        """Branch parses, no worktree here: unknown for that half, never clean."""
        ws = self._workspace()  # no worktrees at all
        item = make_item(repo="goga", number=1)
        item.local_checked = True
        bt.inspect_spec_worktree(item, bt.spec_worktrees(ws))
        self.assertFalse(item.spec_local_checked)
        self.assertIsNone(item.spec_worktree)
        self.assertEqual(bt.local_cell(item), "-")

    def test_no_spec_branch_at_all(self):
        ws = self._workspace(("spec/epos-issue-44", "spec-epos-44"))
        item = make_item(repo="goga", number=1)  # a different task
        item.local_checked = True
        bt.inspect_spec_worktree(item, bt.spec_worktrees(ws))
        self.assertFalse(item.spec_local_checked)
        self.assertEqual(bt.local_cell(item), "-")

    def test_respun_spec_aggregates_every_worktree(self):
        """gopgql#38 really has three. Work in a superseded one is still lost."""
        ws = self._workspace(
            ("spec/gopgql-issue-38", "spec-gopgql-38"),
            ("spec/gopgql-issue-38-v2", "spec-gopgql-38-v2"),
            ("spec/gopgql-issue-38-d4a", "spec-gopgql-38-d4a"),
        )
        self._commit(ws / ".worktrees" / "spec-gopgql-38")
        self._dirty(ws / ".worktrees" / "spec-gopgql-38-v2")
        item = make_item(repo="gopgql", number=38)
        item.local_checked = True
        specs = bt.spec_worktrees(ws)
        self.assertEqual(len(specs[("gopgql", 38)]), 3)
        bt.inspect_spec_worktree(item, specs)
        self.assertEqual((item.spec_wt_unpushed, item.spec_wt_dirty), (1, 1))
        # The named path is one that actually holds work, not a clean sibling.
        self.assertIn("spec-gopgql-38", item.spec_worktree)

    def test_unchecked_code_side_stays_unknown_even_when_spec_is_clean(self):
        """`?` must not become `-` just because the other half was checked."""
        ws = self._workspace(("spec/goga-1-framework-foundations", "spec-goga-1"))
        item = make_item(repo="goga", number=1)  # local_checked stays False
        bt.inspect_spec_worktree(item, bt.spec_worktrees(ws))
        self.assertEqual(bt.local_cell(item), "?")

    def test_spec_work_shows_even_when_code_side_was_never_checked(self):
        """Known work always beats `?` — never hide a finding behind unknown."""
        ws = self._workspace(("spec/goga-1-framework-foundations", "spec-goga-1"))
        self._commit(ws / ".worktrees" / "spec-goga-1")
        item = make_item(repo="goga", number=1)  # no clone for the code side
        bt.inspect_spec_worktree(item, bt.spec_worktrees(ws))
        self.assertEqual(bt.local_cell(item), "spec:1c")

    def test_run_level_notice_suppressed_when_only_spec_was_checkable(self):
        ws = self._workspace(("spec/goga-1-framework-foundations", "spec-goga-1"))
        items = [make_item(repo="goga", number=1)]
        bt.inspect_spec_worktree(items[0], bt.spec_worktrees(ws))
        self.assertIsNone(bt.local_check_notice(items, "/anywhere", no_local=False))


class TestLocalCheckRemainder(unittest.TestCase):
    def test_workspace_root_resolves_the_main_worktree(self):
        """The actual bug: from a linked worktree, projects/ lives in the main one."""
        import subprocess
        import tempfile

        root = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(root, ignore_errors=True))
        main = root / "main"
        run = lambda *a, **k: subprocess.run(a, cwd=k.get("cwd", main),
                                             capture_output=True, check=True)
        main.mkdir()
        run("git", "init", "-q", "-b", "main")
        run("git", "config", "user.email", "t@t.t")
        run("git", "config", "user.name", "t")
        (main / "projects").mkdir()
        # Exactly as the repo has it: everything ignored except the file itself,
        # which is why git recreates the (empty) directory in every worktree.
        (main / "projects" / ".gitignore").write_text("*\n!.gitignore\n")
        (main / "projects" / "somerepo").mkdir()
        run("git", "add", "-A")
        run("git", "commit", "-qm", "init")
        wt = root / "wt"
        run("git", "worktree", "add", "-q", "-b", "task", str(wt))

        # git materialises projects/ in the worktree from the tracked .gitignore,
        # but with no clones — the trap an is_dir() check would walk straight into.
        self.assertTrue((wt / "projects").is_dir())
        self.assertEqual([p.name for p in (wt / "projects").iterdir() if p.is_dir()], [])

        # The real resolution: --git-common-dir from the worktree → main root.
        common = bt.git(wt, "rev-parse", "--path-format=absolute", "--git-common-dir")
        self.assertEqual(Path(common).parent.resolve(), main.resolve())


if __name__ == "__main__":
    unittest.main()
