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


class AckBuckets(unittest.TestCase):
    def test_pending_is_a_ledger_bucket(self):
        item = _item()
        item.ledger = {"v": 1, "acked": {"pending": [1, 2], "spec": [3]}}
        self.assertEqual(bt.acked_ids(item), {1, 2, 3})


if __name__ == "__main__":
    unittest.main()
