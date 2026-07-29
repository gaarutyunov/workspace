#!/usr/bin/env python3
"""Unit tests for board-tick.py — run with `python3 -m unittest` from this dir.

The module name has a hyphen, so it cannot be imported normally; load it by path.
No network, no `gh` — everything here is pure parsing / classification.
"""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "board_tick", Path(__file__).with_name("board-tick.py")
)
bt = importlib.util.module_from_spec(_spec)
# @dataclass resolves annotations through sys.modules[cls.__module__], so the
# module has to be registered before it is executed.
sys.modules["board_tick"] = bt
_spec.loader.exec_module(bt)


class SpecBranchKey(unittest.TestCase):
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

    def test_rejects_non_spec_branches(self):
        for branch in ("main", "issue-38", "spec/nonumber"):
            with self.subTest(branch=branch):
                self.assertIsNone(bt.spec_branch_key(branch))

    def test_rejects_a_number_not_separated_from_its_slug(self):
        # Better to miss than to guess: `1abc` is not issue 1.
        self.assertIsNone(bt.spec_branch_key("spec/goga-1abc"))


def _item(**kw):
    base = dict(
        item_id="x", status="In review", loop="hitl", repo="goga", number=1,
        title="t", issue_url="u",
    )
    base.update(kw)
    return bt.Item(**base)


def _review_comment(cid, path, line, body):
    return {
        "databaseId": cid,
        "author": {"login": bt.OWNER},
        "body": body,
        "createdAt": "2026-07-28T05:17:19Z",
        "url": f"https://example.test/#discussion_r{cid}",
        "path": path,
        "line": line,
    }


class PendingReviewComments(unittest.TestCase):
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
                                _review_comment(3662973631, "design.md", 114, "Sqlc will appear in codiq"),
                                _review_comment(3663003636, "tasks.md", 73, "What are these?"),
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
                        "comments": {"nodes": [_review_comment(3662973631, "design.md", 114, "Sqlc will appear in codiq")]},
                    },
                    {
                        "isResolved": False,
                        "path": "tasks.md",
                        "line": 73,
                        "comments": {"nodes": [_review_comment(3663003636, "tasks.md", 73, "What are these?")]},
                    },
                ]
            },
        }

    def test_drafts_land_in_the_human_pool_marked_and_deduped(self):
        item = _item(spec_pr_number=36)
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
        item = _item(spec_pr_number=36)
        bt.apply_spec(item, self._spec_payload())
        bt.compute_signal(item)

        self.assertEqual(item.signal, "HUMAN-INPUT")
        self.assertIn("unsubmitted review", " ".join(item.reasons))
        self.assertTrue(bt.hum_cell(item).endswith("+2✎"))

    def test_details_flags_the_unsubmitted_state(self):
        item = _item(spec_pr_number=36, spec_pr_state="OPEN")
        bt.apply_spec(item, self._spec_payload())
        bt.compute_signal(item)
        text = bt.render_details([item], include_bots=False, body_limit=500)

        self.assertIn("UNSUBMITTED", text)
        self.assertIn("DRAFT REVIEW", text)
        self.assertIn("3662973631", text)

    def test_acked_drafts_stay_gone(self):
        item = _item(spec_pr_number=36)
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
        item = _item(spec_pr_number=36)
        bt.apply_spec(item, payload)

        self.assertEqual(item.pending_draft, [])
        self.assertIn("spec", {c.kind for c in item.pending_human})


class NoPrWarning(unittest.TestCase):
    """`in review with no PR` must only fire when nothing explains the absence.

    A ⚠ that fires on a healthy task is worse than no ⚠ at all — it teaches the
    loop to skim past the hygiene warnings that do matter.
    """

    WARNING = "in review with no PR"

    def _warns(self, **kw):
        item = _item(**kw)
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


class Truncation(unittest.TestCase):
    """A cap that bites must never be silent."""

    def test_warns_naming_the_connection_and_both_numbers(self):
        item = _item()
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
        item = _item()
        bt.note_truncation(item, {"totalCount": 4, "nodes": [1, 2, 3, 4]}, "x")
        bt.note_truncation(item, {"totalCount": 0, "nodes": []}, "x")
        bt.note_truncation(item, None, "x")
        bt.note_truncation(item, {"nodes": [1]}, "x")  # totalCount not selected
        self.assertEqual(item.warnings, [])

    def test_truncation_forces_an_otherwise_quiet_row_into_details(self):
        item = _item(status="In review", labels=["needs:review"])
        bt.note_truncation(item, {"totalCount": 9, "nodes": [1]}, "PR #40 comments")
        bt.compute_signal(item)
        self.assertEqual(item.signal, "WAITING-OWNER")  # a normally-skipped row
        self.assertIn("TRUNCATED", bt.render_details([item], False, 200))


class BlockerParsing(unittest.TestCase):
    """`blocked` is a claim; the blocker it names has to be machine-readable."""

    # The real blocker comment from bikelanes#4. It cites three references: the
    # blocker, its spec PR and its code PR — and the spec PR is MERGED, so a
    # parser that grabs the wrong one reports "cleared" on a live blocker.
    REAL = (
        "**Blocked on gaarutyunov/ui-kit#7**, which is waiting on spec approval "
        "(spec PR: gaarutyunov/workspace#22, code PR: gaarutyunov/ui-kit#9)."
    )

    def test_takes_the_reference_after_the_blocker_phrase(self):
        b = bt.parse_blocker([{"databaseId": 1, "body": self.REAL}])
        self.assertEqual((b.owner, b.repo, b.number), ("gaarutyunov", "ui-kit", 7))
        self.assertEqual(b.ref, "gaarutyunov/ui-kit#7")
        self.assertEqual(b.source_cid, 1)

    def test_accepts_the_url_form_and_other_phrasings(self):
        for body, want in [
            ("Blocked by https://github.com/gaarutyunov/gopgql/issues/9 for now", 9),
            ("This is gating on gaarutyunov/postgres-pglite#6.", 6),
            ("Waiting on gaarutyunov/ui-kit#12 to cut a release", 12),
            ("Depends on gaarutyunov/epos#3", 3),
            ("Blocker: gaarutyunov/sysgo#67", 67),
            ("blocked on gaarutyunov/workspace/pull/22", 22),
        ]:
            with self.subTest(body=body):
                b = bt.parse_blocker([{"databaseId": 1, "body": body}])
                self.assertIsNotNone(b, body)
                self.assertEqual(b.number, want)

    def test_most_recent_blocker_comment_wins(self):
        nodes = [
            {"databaseId": 1, "body": "Blocked on gaarutyunov/ui-kit#7"},
            {"databaseId": 2, "body": "Now blocked on gaarutyunov/gopgql#9 instead"},
        ]
        self.assertEqual(bt.parse_blocker(nodes).ref, "gaarutyunov/gopgql#9")

    def test_no_reference_without_a_blocker_phrase(self):
        # A bare mention is not a blocker — every issue body cites numbers.
        self.assertIsNone(
            bt.parse_blocker([{"databaseId": 1, "body": "See gaarutyunov/ui-kit#7 for context"}])
        )

    def test_bare_hash_number_is_not_a_blocker(self):
        self.assertIsNone(bt.parse_blocker([{"databaseId": 1, "body": "Blocked on #7"}]))

    def test_ignores_the_ledger_comment(self):
        self.assertIsNone(
            bt.parse_blocker([{"databaseId": 1, "body": bt.LEDGER_MARKER + " blocked on a/b#1"}])
        )

    def test_parsed_only_for_blocked_rows(self):
        payload = {
            "labels": {"nodes": []},
            "createdAt": "2026-07-01T00:00:00Z",
            "comments": {"totalCount": 1, "nodes": [{"databaseId": 1, "body": self.REAL,
                                                     "author": {"login": bt.OWNER},
                                                     "createdAt": "2026-07-01T00:00:00Z"}]},
        }
        item = _item()
        bt.apply_issue(item, payload)
        self.assertIsNone(item.blocker)  # no `blocked` label → nothing to re-check

        blocked = _item()
        payload["labels"] = {"nodes": [{"name": "blocked"}]}
        bt.apply_issue(blocked, payload)
        self.assertEqual(blocked.blocker.ref, "gaarutyunov/ui-kit#7")


class BlockerSignal(unittest.TestCase):
    def _blocked(self, blocker):
        item = _item(status="In review", labels=["blocked"])
        item.blocker = blocker
        bt.compute_signal(item)
        return item

    def _resolved(self, state, kind="Issue"):
        return bt.Blocker(
            owner="gaarutyunov", repo="ui-kit", number=7, resolved=True, kind=kind,
            state=state, title="Some blocker", url="https://example.test/7",
            created_at="2026-07-25T18:39:33Z", closed_at="2026-07-26T19:54:22Z",
        )

    def test_cleared_blocker_becomes_actionable(self):
        for state, kind in (("CLOSED", "Issue"), ("MERGED", "PullRequest")):
            with self.subTest(state=state):
                item = self._blocked(self._resolved(state, kind))
                self.assertEqual(item.signal, "UNBLOCKED")
                self.assertTrue(any("CLEARED" in w for w in item.warnings))
                # Ranked above the signals a rotting task would otherwise hide under.
                self.assertLess(
                    bt.SIGNAL_ORDER.index("UNBLOCKED"), bt.SIGNAL_ORDER.index("BLOCKED")
                )
                self.assertLess(
                    bt.SIGNAL_ORDER.index("UNBLOCKED"), bt.SIGNAL_ORDER.index("READY")
                )

    def test_open_blocker_stays_blocked_but_renders(self):
        item = self._blocked(self._resolved("OPEN"))
        self.assertEqual(item.signal, "BLOCKED")
        self.assertFalse(any("CLEARED" in w for w in item.warnings))
        details = bt.render_details([item], False, 200)
        self.assertIn("blocker: gaarutyunov/ui-kit#7 — still open", details)

    def test_unparseable_blocker_is_a_warning(self):
        item = self._blocked(None)
        self.assertEqual(item.signal, "BLOCKED")
        self.assertTrue(any("no comment names a blocker" in w for w in item.warnings))

    def test_unresolvable_blocker_is_a_warning(self):
        item = self._blocked(bt.Blocker(owner="gaarutyunov", repo="gone", number=1))
        self.assertTrue(any("could not be resolved" in w for w in item.warnings))

    def test_a_blocked_row_is_never_a_bare_table_line(self):
        """The regression this exists to prevent: nothing left to re-examine."""
        item = self._blocked(self._resolved("OPEN"))
        self.assertEqual(item.pending, [])
        self.assertEqual(item.warnings, [])  # open blocker warrants no ⚠ …
        self.assertIn("blocker:", bt.render_details([item], False, 200))  # … but still renders

    def test_resolve_blockers_is_skipped_when_nothing_is_blocked(self):
        called = []
        original = bt.gh_graphql
        bt.gh_graphql = lambda *a, **k: called.append(a) or {}
        try:
            bt.resolve_blockers([_item(), _item(labels=["needs:review"])])
        finally:
            bt.gh_graphql = original
        self.assertEqual(called, [])

    def test_resolve_blockers_dedupes_into_one_call(self):
        """N rows blocked on the same thing must cost one alias, not N calls."""
        items = [_item(number=n, labels=["blocked"]) for n in (1, 2, 3)]
        for it in items:
            it.blocker = bt.Blocker(owner="gaarutyunov", repo="ui-kit", number=7)
        queries = []

        def fake(query, tolerant=False):
            queries.append(query)
            return {"b0": {"issueOrPullRequest": {
                "__typename": "Issue", "title": "t", "url": "u",
                "state": "CLOSED", "createdAt": "2026-07-01T00:00:00Z",
                "closedAt": "2026-07-28T00:00:00Z"}}}

        original = bt.gh_graphql
        bt.gh_graphql = fake
        try:
            bt.resolve_blockers(items)
        finally:
            bt.gh_graphql = original

        self.assertEqual(len(queries), 1)
        self.assertEqual(queries[0].count("issueOrPullRequest"), 1)
        self.assertTrue(all(i.blocker.cleared for i in items))

    def test_a_failed_lookup_never_breaks_the_tick(self):
        item = _item(labels=["blocked"])
        item.blocker = bt.Blocker(owner="gaarutyunov", repo="ui-kit", number=7)
        original = bt.gh_graphql

        def boom(*a, **k):
            raise RuntimeError("GraphQL exploded")

        bt.gh_graphql = boom
        try:
            bt.resolve_blockers([item])  # must not raise
        finally:
            bt.gh_graphql = original
        self.assertFalse(item.blocker.resolved)


class AckBuckets(unittest.TestCase):
    def test_pending_is_a_ledger_bucket(self):
        item = _item()
        item.ledger = {"v": 1, "acked": {"pending": [1, 2], "spec": [3]}}
        self.assertEqual(bt.acked_ids(item), {1, 2, 3})


if __name__ == "__main__":
    unittest.main()
