#!/usr/bin/env python3
"""Tests for board-tick.py — the pure logic only: no network, no `gh` calls.

The script is deliberately stdlib-only so it stays runnable with zero install
steps; these tests keep that property (plain `unittest`, no pytest).

Run:
    python3 -m unittest discover -s .agents/skills/loop-common/scripts -p 'test_*.py' -v
"""

from __future__ import annotations

import importlib.util
import inspect
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

    def test_blocked_label_with_no_recorded_blocker_is_unblocked(self):
        """The three legacy label-only items — surfaced, not skipped."""
        item = make_item(status="In review", labels=["blocked", "needs:review"])
        self.assertEqual(signal_of(item), "UNBLOCKED")

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
            "SPEC-MERGED", "CI-RED", "THREADS", "BLOCKED", "WAITING-OWNER",
            "TRACKER", "READY", "NOT-STARTED", "WIP", "IDLE",
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


if __name__ == "__main__":
    unittest.main()
