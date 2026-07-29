#!/usr/bin/env python3
"""board-tick — one-call situational awareness for the delivery loops.

Fetches every *active* item on the gaarutyunov project board (everything except
Backlog and Done), and for each one pulls the issue, its labels, its comments,
the linked PR's comments, review threads and CI status — including the inline
comments of reviews the owner *started but never submitted*, which no ordinary
comment endpoint returns.

Comments are classified (human / agent / bot) and filtered against a per-issue
**ack ledger** stored as a machine-managed comment on the issue itself, so
comments that were already seen and addressed never come back.

The output is a decision table for the orchestrator plus a details block holding
the full text of everything still unaddressed.

Subcommands
-----------
  tick          (default) print the decision table + details
  ack           mark comments as seen/addressed in an issue's ledger
  post          add a comment carrying the agent marker (issue or PR)
  label         add/remove loop labels on an issue (creates them if missing)
  init-labels   create the loop label set in a repo

Requires: `gh` authenticated with the `project` scope.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import textwrap
from dataclasses import dataclass, field
from datetime import datetime, timezone

OWNER = "gaarutyunov"
PROJECT = 6

# Statuses the loops care about. Backlog = not picked up, Done = finished.
ACTIVE_STATUSES = ("Ready", "In progress", "In review")

# Every comment the loops write carries this marker so a later tick can tell
# agent output from owner input — both are posted by the same GitHub account.
AGENT_MARKER = "<!-- loop-agent -->"
LEDGER_MARKER = "<!-- loop-state:v1 -->"

BOT_LOGINS = {
    "coderabbitai",
    "github-actions",
    "dependabot",
    "codecov",
    "sonarcloud",
    "vercel",
    "netlify",
    "renovate",
}

# ── Label protocol ──────────────────────────────────────────────────────────
# The owner only ever moves an item to Ready and applies `approved:*` labels.
# Every other status move, and every `needs:*`/`blocked` label, is the agent's.
OWNER_LABELS = {
    "approved:spec": ("0e8a16", "Owner approved the spec — agent may implement"),
    "approved:pr": ("0e8a16", "Owner approved the PR — agent may merge"),
}
# Agent labels that mean "the owner has to do something" — these force In review.
WAITING_LABELS = {
    "needs:spec-approval": ("fbca04", "Spec PR open, waiting for owner approval"),
    "needs:review": ("fbca04", "Code PR ready, waiting for owner review"),
    "needs:input": ("fbca04", "Question posted on the issue, waiting for owner"),
    "blocked": ("b60205", "Blocked — blocker described in the issue"),
}
# Agent labels that describe a state without waiting on anyone.
INFO_LABELS = {
    "tracker": ("c5def5", "Epic decomposed into sub-issues; tracks their progress"),
}
AGENT_LABELS = {**WAITING_LABELS, **INFO_LABELS}
LOOP_LABELS = {**OWNER_LABELS, **AGENT_LABELS}

# Short display forms for the table's label column.
LABEL_ABBREV = {
    "approved:spec": "A:spec",
    "approved:pr": "A:pr",
    "needs:spec-approval": "N:spec",
    "needs:review": "N:rev",
    "needs:input": "N:inp",
    "blocked": "BLOCKED",
    "tracker": "trk",
}


# ── gh plumbing ─────────────────────────────────────────────────────────────


class RateLimited(RuntimeError):
    """The GitHub GraphQL budget ran out mid-tick.

    Its own type because it demands its own handling: a rate-limited tick has
    seen *nothing*, and must not be mistaken for a tick that saw a quiet board.
    """


# `gh` does not say "rate limit" in every case. Notably a rate-limited
# `gh project item-list` prints `unknown owner type`, which reads like a scope or
# argument bug — so any gh failure is checked against the real budget.
RATE_LIMIT_TEXT = re.compile(r"rate limit|RATE_LIMITED|secondary rate", re.I)


def gh(*args: str, check: bool = True, stdin: str | None = None) -> str:
    proc = subprocess.run(
        ["gh", *args],
        capture_output=True,
        text=True,
        input=stdin,
    )
    if check and proc.returncode != 0:
        err = proc.stderr.strip()
        if RATE_LIMIT_TEXT.search(err) or exhausted_budget():
            raise RateLimited(err)
        raise RuntimeError(f"gh {' '.join(args)} failed:\n{err}")
    return proc.stdout


def graphql_budget() -> tuple[int, int, int] | None:
    """(remaining, limit, reset epoch) for the GraphQL budget, or None if unknown.

    `GET /rate_limit` is REST and is itself exempt from rate limiting, so this is
    free to call — including on the failure path.
    """
    proc = subprocess.run(
        ["gh", "api", "rate_limit"], capture_output=True, text=True
    )
    if proc.returncode != 0:
        return None
    try:
        res = (json.loads(proc.stdout or "{}").get("resources") or {}).get("graphql") or {}
    except json.JSONDecodeError:
        return None
    if "remaining" not in res:
        return None
    return int(res["remaining"]), int(res.get("limit", 0)), int(res.get("reset", 0))


def exhausted_budget() -> bool:
    budget = graphql_budget()
    return budget is not None and budget[0] <= 0


def reset_phrase(reset_epoch: int) -> str:
    when = datetime.fromtimestamp(reset_epoch, tz=timezone.utc)
    mins = max(0, int((when - datetime.now(timezone.utc)).total_seconds() // 60))
    return f"{when.strftime('%Y-%m-%d %H:%M UTC')} (in {mins}m)"


def rate_limit_banner(headline: str, budget: tuple[int, int, int] | None) -> str:
    """The one thing a tick must never do quietly is fail to see the board."""
    rule = "═" * 74
    if budget:
        remaining, limit, reset = budget
        line = f" graphql budget: {remaining}/{limit} · resets {reset_phrase(reset)}"
    else:
        line = " graphql budget: unknown (could not read gh api rate_limit)"
    return "\n".join(
        [
            rule,
            f" {headline}",
            rule,
            line,
            "",
            " This is NOT an empty board and NOT a healthy tick. No board data was",
            " read, so nothing here can be trusted: do not pick up, skip, label or",
            " close any task on the basis of this run.",
            "",
            " `gh` disguises this failure. The same condition makes",
            f"   gh project item-list {PROJECT} --owner {OWNER}",
            " print `unknown owner type`, which reads like a permissions or argument",
            " bug and is nothing of the kind. Confirm with:  gh api rate_limit",
            "",
            " Every `gh pr list` / `gh pr view` and every hydration query draws on",
            " this same GraphQL budget, and it is shared by every agent and tool on",
            " the machine — concurrent runs drain it together.",
            "",
            " Wait for the reset and re-run. Do NOT weaken or trim queries to make",
            " the error go away.",
            rule,
        ]
    )


def gh_graphql(query: str, tolerant: bool = False) -> dict:
    """Run a GraphQL query. `tolerant` keeps partial data when some alias errors.

    A batched query over many aliases (blocker lookups) can have one alias fail —
    a deleted or private issue — while the rest are fine. GitHub returns the good
    data *and* an errors array; tolerant callers want the data.
    """
    out = gh("api", "graphql", "-f", f"query={query}", check=not tolerant)
    try:
        payload = json.loads(out or "{}")
    except json.JSONDecodeError:
        if tolerant:
            return {}
        raise
    errors = payload.get("errors")
    if errors:
        blob = json.dumps(errors)
        if RATE_LIMIT_TEXT.search(blob):
            # Even a `tolerant` caller must not swallow this: a rate-limited
            # response is missing data, not reporting absent data.
            raise RateLimited(blob)
        if not tolerant:
            raise RuntimeError("GraphQL errors: " + json.dumps(errors, indent=2))
    return payload.get("data") or {}


# ── Data model ──────────────────────────────────────────────────────────────


@dataclass
class Comment:
    kind: str  # issue | pr | review | spec | pending
    cid: int  # databaseId — the id used by the ledger
    author: str
    body: str
    created: str
    url: str
    who: str = "human"  # human | agent | bot
    thread_id: str | None = None
    thread_resolved: bool = False
    path: str | None = None
    # Set for comments belonging to a review the owner started but never
    # submitted. Nobody but us can see these, so the digest has to say so.
    draft_on: str | None = None  # e.g. "PR #40" / "spec PR #36"


@dataclass
class Blocker:
    """The issue/PR a `blocked` task names as the thing it is waiting on."""

    owner: str
    repo: str
    number: int
    source_cid: int | None = None  # the comment it was parsed from
    resolved: bool = False  # did the state lookup succeed?
    kind: str = ""  # Issue | PullRequest
    state: str = ""  # OPEN | CLOSED | MERGED
    title: str = ""
    url: str = ""
    created_at: str = ""
    closed_at: str = ""

    @property
    def ref(self) -> str:
        return f"{self.owner}/{self.repo}#{self.number}"

    @property
    def cleared(self) -> bool:
        """Has the thing this task waits on finished?"""
        return self.state in ("CLOSED", "MERGED")


@dataclass
class Item:
    item_id: str
    status: str
    loop: str | None
    repo: str  # short name, no owner
    number: int
    title: str
    issue_url: str
    labels: list[str] = field(default_factory=list)
    pr_number: int | None = None
    pr_url: str | None = None
    pr_draft: bool = False
    pr_state: str = ""
    pr_mergeable: str = "UNKNOWN"
    pr_review_decision: str | None = None
    ci_state: str | None = None
    ci_failing: list[str] = field(default_factory=list)
    ci_pending: list[str] = field(default_factory=list)
    pr_changed_files: int = 0
    pr_additions: int = 0
    pr_deletions: int = 0
    pr_commits: int = 0
    # Local state — work that exists on this machine but not on GitHub.
    worktree: str | None = None
    wt_dirty: int = 0  # uncommitted files
    wt_unpushed: int = 0  # commits ahead of the remote branch
    wt_stat: str = ""
    comments: list[Comment] = field(default_factory=list)
    seen_cids: set[int] = field(default_factory=set)
    unresolved_threads: int = 0
    # The spec PR lives in the *workspace* repo on a `spec…` branch naming this
    # repo and issue (see spec_branch_key), i.e. usually a different repo from the
    # issue — nothing links it, so it has to be found separately.
    spec_pr_number: int | None = None
    spec_pr_url: str | None = None
    spec_pr_state: str = ""
    spec_unresolved_threads: int = 0
    # What a `blocked` row is waiting on, parsed from its blocker comment and
    # resolved so a cleared blocker cannot sit unnoticed.
    blocker: "Blocker | None" = None
    issue_created: str = ""
    last_activity: str = ""
    has_ledger: bool = False
    ledger: dict = field(default_factory=dict)
    signal: str = ""
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def slug(self) -> str:
        return f"{self.repo}#{self.number}"

    @property
    def spec_merged(self) -> bool:
        return self.spec_pr_state == "MERGED"

    @property
    def pushed_work(self) -> bool:
        """Is there anything on GitHub to show for this task?"""
        return bool(self.pr_number) and self.pr_changed_files > 0

    @property
    def local_work(self) -> bool:
        """Is there work on this machine that never reached GitHub?"""
        return self.wt_dirty > 0 or self.wt_unpushed > 0

    @property
    def work_started(self) -> bool:
        return self.pushed_work or self.local_work

    @property
    def oldest_pending_human(self) -> str:
        stamps = [c.created for c in self.pending_human if c.created]
        return min(stamps) if stamps else ""

    @property
    def pending(self) -> list[Comment]:
        """Comments that still need the agent's attention."""
        return [c for c in self.comments if c.who != "agent"]

    @property
    def pending_human(self) -> list[Comment]:
        return [c for c in self.comments if c.who == "human"]

    @property
    def pending_bot(self) -> list[Comment]:
        return [c for c in self.comments if c.who == "bot"]

    @property
    def pending_draft(self) -> list[Comment]:
        """Unaddressed comments the owner left in a review they never submitted."""
        return [c for c in self.comments if c.draft_on and c.who != "agent"]


# ── Time ────────────────────────────────────────────────────────────────────


def parse_ts(stamp: str) -> datetime | None:
    if not stamp:
        return None
    try:
        return datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    except ValueError:
        return None


def age_of(stamp: str) -> str:
    """Compact age: 45m / 5h / 4d / 3w."""
    when = parse_ts(stamp)
    if not when:
        return "-"
    secs = (datetime.now(timezone.utc) - when).total_seconds()
    if secs < 3600:
        return f"{int(secs // 60)}m"
    if secs < 86400:
        return f"{int(secs // 3600)}h"
    days = int(secs // 86400)
    return f"{days}d" if days < 14 else f"{days // 7}w"


def newest(*stamps: str) -> str:
    real = [s for s in stamps if s]
    return max(real) if real else ""


# ── Board ───────────────────────────────────────────────────────────────────


def fetch_board(statuses: tuple[str, ...]) -> list[Item]:
    raw = json.loads(
        gh(
            "project",
            "item-list",
            str(PROJECT),
            "--owner",
            OWNER,
            "--format",
            "json",
            "--limit",
            "300",
        )
    )
    items: list[Item] = []
    for entry in raw.get("items", []):
        content = entry.get("content") or {}
        if content.get("type") != "Issue":
            continue
        if entry.get("status") not in statuses:
            continue
        repo_full = content.get("repository", "")
        repo = repo_full.split("/")[-1]
        item = Item(
            item_id=entry["id"],
            status=entry.get("status", ""),
            loop=entry.get("loop"),
            repo=repo,
            number=content["number"],
            title=content.get("title", ""),
            issue_url=content.get("url", ""),
        )
        for url in entry.get("linked pull requests", []) or []:
            m = re.search(rf"/{OWNER}/{re.escape(repo)}/pull/(\d+)$", url)
            if m:
                item.pr_number = int(m.group(1))
                item.pr_url = url
                break  # newest link wins; a task has one code PR
        if item.pr_number is None:
            item.pr_number = find_pr_by_branch(repo, item.number)
        items.append(item)
    return items


# ── Local worktrees ─────────────────────────────────────────────────────────
# A PR with no changed files is ambiguous on its own: the run may have been
# stopped, run out of context, or crashed — possibly *after* editing files that
# were never committed or never pushed. Only the local checkout can tell which,
# and stranded work is the one failure mode that loses effort outright.


def workspace_root() -> "Path":
    from pathlib import Path

    # <root>/.agents/skills/loop-common/scripts/board-tick.py — resolve() so the
    # .claude/skills symlink lands on the real path.
    return Path(__file__).resolve().parents[4]


def git(cwd, *args: str) -> str | None:
    proc = subprocess.run(
        ["git", "-C", str(cwd), *args], capture_output=True, text=True
    )
    return proc.stdout.strip() if proc.returncode == 0 else None


def inspect_worktree(item: Item, projects_dir) -> None:
    """Look for uncommitted / unpushed work in the task's local checkout."""
    from pathlib import Path

    branch = f"issue-{item.number}"
    candidates = [Path(projects_dir) / item.repo / ".worktrees" / branch]
    # The work may also sit in the base clone if it was checked out there.
    base = Path(projects_dir) / item.repo
    if git(base, "rev-parse", "--abbrev-ref", "HEAD") == branch:
        candidates.append(base)

    for path in candidates:
        if not (path / ".git").exists():
            continue
        if git(path, "rev-parse", "--is-inside-work-tree") != "true":
            continue
        item.worktree = str(path)

        status = git(path, "status", "--porcelain")
        item.wt_dirty = len([l for l in (status or "").splitlines() if l.strip()])

        # Commits reachable from HEAD but from no remote-tracking branch. This
        # covers the case that matters most — a branch that was never pushed at
        # all, where `@{upstream}` does not resolve.
        ahead = git(path, "rev-list", "--count", "HEAD", "--not", "--remotes")
        if ahead is None:
            ahead = git(path, "rev-list", "--count", "@{upstream}..HEAD")
        item.wt_unpushed = int(ahead) if ahead and ahead.isdigit() else 0

        stat = git(path, "diff", "--shortstat", "HEAD")
        if stat:
            item.wt_stat = stat
        return


SPEC_REPO = "workspace"  # specs are always authored in the workspace repo


def spec_branch_key(branch: str) -> tuple[str, int] | None:
    """Parse a spec branch name into (repo, issue number), or None.

    Matched loosely on purpose. Ticks have named these branches every which way —
    `spec/<repo>-issue-<N>`, `spec-<repo>-<N>`, and (most often, because the spec
    flow names the branch after the change) `spec/<repo>-<N>-<slug>` — and an
    exact-match lookup silently dropped the spec PR for every style but the first,
    which meant its comments (where the owner's spec feedback lives) were never
    read. A missed owner comment is far worse than a mis-parsed branch name, so
    accept any `spec`-prefixed branch carrying the issue number, with or without
    a trailing descriptive slug.

    The `repo` group is non-greedy so that the *first* `-<digits>-` run is taken
    as the issue number: `spec/ui-kit-6-workout-components` is (ui-kit, 6), not
    (ui-kit-6, …) — a slug that itself starts with digits cannot steal the match.
    The trailing slug must be separated by `/` or `-`, so `spec/goga-1abc` stays
    unmatched rather than silently reading as issue 1.
    """
    m = re.fullmatch(
        r"spec[/-](?P<repo>.+?)[/-](?:issue[/-])?(?P<num>\d+)(?:[/-].*)?",
        branch,
    )
    if not m:
        return None
    return m.group("repo"), int(m.group("num"))


def attach_spec_prs(items: list[Item]) -> None:
    """Find each task's spec PR.

    Specs live in the workspace repo on a `spec…` branch naming the task's repo
    and issue number — a *different* repo from the issue for every project task,
    so nothing on the issue links to them. One list call covers the whole board.
    """
    if not items:
        return
    out = gh(
        "pr",
        "list",
        "--repo",
        f"{OWNER}/{SPEC_REPO}",
        "--state",
        "all",
        "--limit",
        "200",
        "--json",
        "number,headRefName,state,url",
        check=False,
    )
    try:
        prs = json.loads(out or "[]")
    except json.JSONDecodeError:
        return
    by_task: dict[tuple[str, int], dict] = {}
    for pr in prs:
        key = spec_branch_key(pr.get("headRefName", ""))
        if key:
            # Later PRs win — a respun spec supersedes an earlier attempt.
            by_task[key] = pr
    for item in items:
        pr = by_task.get((item.repo, item.number))
        if not pr:
            continue
        item.spec_pr_number = pr["number"]
        item.spec_pr_state = pr.get("state", "")
        item.spec_pr_url = pr.get("url")


# ── Blockers ────────────────────────────────────────────────────────────────
# `blocked` is a *claim*, and claims go stale: the blocker merges and nobody
# notices, so the row keeps ranking BLOCKED and every tick keeps skipping it.
# Two rows were sitting on already-closed blockers when this was written.

# Phrases the loops actually use to name a blocker. The reference is taken from
# *after* one of these, never from anywhere in the comment: a real blocker
# comment also cites the blocker's own spec and code PRs, and those are usually
# merged — picking the wrong reference would report "cleared" on a live blocker.
BLOCKER_MARKER = re.compile(
    r"block(?:ed|er|ing)\s*(?:on|by|:)|wait(?:ing|s)\s+on|depends?\s+on|gat(?:ed|ing)\s+on",
    re.I,
)
# `owner/repo#N`, or the equivalent issue/PR URL. Deliberately no bare `#N`:
# every issue body mentions numbers, and a wrong blocker is worse than none.
BLOCKER_REF = re.compile(
    r"(?:https?://github\.com/)?"
    r"(?P<owner>[A-Za-z0-9][\w.-]*)/(?P<repo>[A-Za-z0-9][\w.-]*)"
    r"(?:/(?:issues|pull)/|#)"
    r"(?P<num>\d+)"
)


def parse_blocker(comment_nodes: list[dict]) -> Blocker | None:
    """Find what a `blocked` task is waiting on, from its blocker comment.

    Scans comments newest-first and returns the first reference that follows a
    blocker phrase, so the most recent statement of the blocker wins.
    """
    for node in reversed(comment_nodes or []):
        body = node.get("body") or ""
        if LEDGER_MARKER in body:
            continue
        marker = BLOCKER_MARKER.search(body)
        if not marker:
            continue
        ref = BLOCKER_REF.search(body, marker.end())
        if not ref:
            continue
        return Blocker(
            owner=ref.group("owner"),
            repo=ref.group("repo"),
            number=int(ref.group("num")),
            source_cid=node.get("databaseId"),
        )
    return None


def resolve_blockers(items: list[Item]) -> None:
    """Look up every named blocker's state — one batched call for the whole board.

    Deduplicated by (owner, repo, number), so N rows blocked on the same thing
    cost one alias, and skipped entirely when no row is blocked. Failures are
    swallowed on purpose: an unresolvable blocker is reported as a warning on its
    row (see compute_signal) and must never take the whole tick down.
    """
    blockers = [i.blocker for i in items if i.blocker]
    if not blockers:
        return
    groups: dict[tuple[str, str, int], list[Blocker]] = {}
    for b in blockers:
        groups.setdefault((b.owner, b.repo, b.number), []).append(b)
    keys = list(groups)
    parts = [
        f'b{idx}: repository(owner: "{owner}", name: "{repo}") '
        f"{{ issueOrPullRequest(number: {num}) {{ __typename "
        "... on Issue { title url state createdAt closedAt } "
        "... on PullRequest { title url state createdAt closedAt mergedAt } } }"
        for idx, (owner, repo, num) in enumerate(keys)
    ]
    try:
        data = gh_graphql("query {\n" + "\n".join(parts) + "\n}", tolerant=True)
    except RuntimeError:
        return
    for idx, key in enumerate(keys):
        node = (data.get(f"b{idx}") or {}).get("issueOrPullRequest") or {}
        if not node:
            continue  # deleted, private, or wrong number — flagged on the row
        for b in groups[key]:
            b.resolved = True
            b.kind = node.get("__typename", "")
            b.state = node.get("state", "")
            b.title = node.get("title", "")
            b.url = node.get("url", "")
            b.created_at = node.get("createdAt", "")
            b.closed_at = node.get("mergedAt") or node.get("closedAt") or ""


def find_pr_by_branch(repo: str, issue: int) -> int | None:
    """Fallback for a PR the board didn't link: the loops' `issue-<N>` branch."""
    out = gh(
        "pr",
        "list",
        "--repo",
        f"{OWNER}/{repo}",
        "--head",
        f"issue-{issue}",
        "--state",
        "all",
        "--json",
        "number,state",
        check=False,
    )
    try:
        prs = json.loads(out or "[]")
    except json.JSONDecodeError:
        return None
    if not prs:
        return None
    openish = [p for p in prs if p.get("state") == "OPEN"]
    return (openish or prs)[-1]["number"]


# ── GraphQL hydration ───────────────────────────────────────────────────────

# Every capped connection selects `totalCount` next to its `nodes`. A cap that
# silently returns fewer rows than exist is indistinguishable from "there was
# nothing more" — the exact failure that hid this PR's owner comments for a day —
# so `note_truncation` turns every such gap into a row-level ⚠.
ISSUE_FRAGMENT = """
fragment IssueBits on Issue {
  number url title state createdAt
  labels(first: 50) { nodes { name } }
  comments(last: 100) {
    totalCount
    nodes { databaseId author { login } body createdAt url }
  }
}
"""

SPEC_FRAGMENT = """
fragment SpecBits on PullRequest {
  number url state mergedAt isDraft
  comments(last: 50) {
    totalCount
    nodes { databaseId author { login } body createdAt url }
  }
  reviews(last: 20) {
    totalCount
    nodes {
      databaseId author { login } body state submittedAt url
      comments(first: 50) {
        totalCount
        nodes { databaseId author { login } body createdAt url path line }
      }
    }
  }
  reviewThreads(first: 30) {
    totalCount
    nodes {
      isResolved path line
      comments(first: 5) {
        totalCount
        nodes { databaseId author { login } body createdAt url }
      }
    }
  }
}
"""

PR_FRAGMENT = """
fragment PrBits on PullRequest {
  number url isDraft state mergeable reviewDecision headRefName
  changedFiles additions deletions
  comments(last: 100) {
    totalCount
    nodes { databaseId author { login } body createdAt url }
  }
  reviews(last: 30) {
    totalCount
    nodes {
      databaseId author { login } body state submittedAt url
      comments(first: 50) {
        totalCount
        nodes { databaseId author { login } body createdAt url path line }
      }
    }
  }
  reviewThreads(first: 60) {
    totalCount
    nodes {
      id isResolved isOutdated path line
      comments(first: 10) {
        totalCount
        nodes { databaseId author { login } body createdAt url }
      }
    }
  }
  commits(last: 1) {
    totalCount
    nodes { commit { committedDate statusCheckRollup { state contexts(first: 100) {
      totalCount
      nodes {
      __typename
      ... on CheckRun { name conclusion status detailsUrl }
      ... on StatusContext { context state targetUrl }
    } } } } }
  }
}
"""


def build_query(chunk: list[Item]) -> str:
    parts = []
    for idx, item in enumerate(chunk):
        parts.append(
            f'i{idx}: repository(owner: "{OWNER}", name: "{item.repo}") '
            f"{{ issue(number: {item.number}) {{ ...IssueBits }} }}"
        )
        if item.pr_number:
            parts.append(
                f'p{idx}: repository(owner: "{OWNER}", name: "{item.repo}") '
                f"{{ pullRequest(number: {item.pr_number}) {{ ...PrBits }} }}"
            )
        if item.spec_pr_number:
            parts.append(
                f's{idx}: repository(owner: "{OWNER}", name: "{SPEC_REPO}") '
                f"{{ pullRequest(number: {item.spec_pr_number}) {{ ...SpecBits }} }}"
            )
    # GraphQL rejects a fragment that is defined but never referenced, so a
    # chunk of issues with no PRs must not declare the PR fragments.
    query = "query {\n" + "\n".join(parts) + "\n}\n" + ISSUE_FRAGMENT
    if any(i.pr_number for i in chunk):
        query += PR_FRAGMENT
    if any(i.spec_pr_number for i in chunk):
        query += SPEC_FRAGMENT
    return query


def hydrate(items: list[Item], chunk_size: int = 6) -> None:
    for start in range(0, len(items), chunk_size):
        chunk = items[start : start + chunk_size]
        data = gh_graphql(build_query(chunk))
        for idx, item in enumerate(chunk):
            issue = (data.get(f"i{idx}") or {}).get("issue") or {}
            apply_issue(item, issue)
            pr = (data.get(f"p{idx}") or {}).get("pullRequest") if item.pr_number else None
            if pr:
                apply_pr(item, pr)
            spec = (data.get(f"s{idx}") or {}).get("pullRequest") if item.spec_pr_number else None
            if spec:
                apply_spec(item, spec)


def classify(login: str, body: str) -> str:
    if login.endswith("[bot]") or login.lower() in BOT_LOGINS:
        return "bot"
    if AGENT_MARKER in body:
        return "agent"
    if login.lower() == OWNER.lower():
        return "human"
    return "human"  # an outside human is still a human to answer


def ingest(item: Item, node: dict, kind: str, **extra) -> Comment | None:
    """Turn one API comment node into a tracked Comment (ledger comment aside)."""
    body = node.get("body") or ""
    if LEDGER_MARKER in body:
        return None
    # A draft-review comment is reachable two ways — through its review and
    # through its (unresolved) review thread. Whichever arrives first wins, so
    # the draft pass runs before the thread pass and keeps its `draft_on` mark.
    cid = node["databaseId"]
    if cid in item.seen_cids:
        return None
    item.seen_cids.add(cid)
    login = (node.get("author") or {}).get("login", "ghost")
    created = node.get("createdAt") or node.get("submittedAt") or ""
    comment = Comment(
        kind=kind,
        cid=cid,
        author=login,
        body=body,
        created=created,
        url=node.get("url", ""),
        who=classify(login, body),
        **extra,
    )
    item.comments.append(comment)
    item.last_activity = newest(item.last_activity, created)
    return comment


def note_truncation(item: Item, conn: dict | None, what: str) -> list:
    """Warn when a capped connection returned fewer rows than actually exist.

    Every `first:`/`last:` in the fragments above is a cap, and GraphQL reports no
    error when it bites — it just returns fewer nodes. That makes an
    under-reporting tick indistinguishable from a quiet one, which is how this
    tool lost five owner comments for a day. So the caller pairs every capped
    connection with `totalCount` and routes it through here: any shortfall
    becomes a row-level ⚠ naming the connection and both numbers, so a tick can
    never silently under-report.

    Returns the connection's nodes, so call sites can use it inline.
    """
    conn = conn or {}
    nodes = conn.get("nodes") or []
    total = conn.get("totalCount")
    if isinstance(total, int) and total > len(nodes):
        item.warnings.append(
            f"TRUNCATED: {what} returned {len(nodes)} of {total} — "
            f"{total - len(nodes)} not seen by this tick; raise the cap in the "
            "GraphQL fragment before trusting this row"
        )
    return nodes


def ingest_pending_review(item: Item, review: dict, label: str) -> int:
    """Fold an *unsubmitted* review's inline comments into the pending pool.

    A review the owner starts and never submits stays `PENDING` with a null
    `submittedAt`, and its inline comments are invisible to the ordinary comment
    endpoints — `GET /pulls/{n}/comments` omits them, and so does
    `gh pr view --json comments,reviews`. They are nonetheless real owner
    direction, and because the loop and the owner share one GitHub account the
    API hands us the drafts. Ignoring them is exactly how five owner comments on
    a spec PR stayed hidden for over an hour.

    They ride in on the `reviews` connection the digest already queries, so this
    adds no API call. Comments are tagged `pending` (their own ack bucket) and
    carry `draft_on` so the renderer can flag the state — the owner may well not
    realise an unsubmitted review is invisible to everyone else.
    """
    count = 0
    for node in note_truncation(item, review.get("comments"), f"{label} draft-review comments"):
        line = node.get("line")
        got = ingest(
            item,
            node,
            "pending",
            draft_on=label,
            path=f"{node.get('path')}:{line}" if node.get("path") else None,
        )
        if got:
            count += 1
    return count


def apply_issue(item: Item, issue: dict) -> None:
    item.labels = [n["name"] for n in (issue.get("labels") or {}).get("nodes", [])]
    item.issue_created = issue.get("createdAt", "")
    item.last_activity = newest(item.last_activity, item.issue_created)
    nodes = note_truncation(item, issue.get("comments"), "issue comments")
    for node in nodes:
        if LEDGER_MARKER in (node.get("body") or ""):
            # The ledger is our own bookkeeping: it is neither a comment to act
            # on nor activity — counting it would make every task look fresh.
            item.has_ledger = True
            item.ledger = parse_ledger(node["body"])
            item.ledger["_comment_id"] = node["databaseId"]
            continue
        ingest(item, node, "issue")
    if "blocked" in item.labels:
        item.blocker = parse_blocker(nodes)


def apply_spec(item: Item, spec: dict) -> None:
    item.spec_pr_state = spec.get("state", item.spec_pr_state)
    item.spec_pr_url = spec.get("url") or item.spec_pr_url
    label = f"spec PR #{item.spec_pr_number}"
    for node in note_truncation(item, spec.get("comments"), f"{label} comments"):
        ingest(item, node, "spec")
    for node in note_truncation(item, spec.get("reviews"), f"{label} reviews"):
        state = node.get("state", "")
        if state == "PENDING":
            # Runs before the thread pass below so the draft mark survives dedupe.
            ingest_pending_review(item, node, label)
            continue
        body = (node.get("body") or "").strip()
        if not body and state not in ("CHANGES_REQUESTED", "APPROVED"):
            continue
        node = {**node, "body": f"[spec review {state}] {body}".strip()}
        ingest(item, node, "spec")
    for thread in note_truncation(item, spec.get("reviewThreads"), f"{label} review threads"):
        if thread.get("isResolved"):
            continue
        item.spec_unresolved_threads += 1
        where = f"{thread.get('path')}:{thread.get('line')}"
        for node in note_truncation(item, thread.get("comments"), f"{label} thread {where}"):
            ingest(item, node, "spec", path=where)


def apply_pr(item: Item, pr: dict) -> None:
    item.pr_draft = pr.get("isDraft", False)
    item.pr_state = pr.get("state", "")
    item.pr_mergeable = pr.get("mergeable", "UNKNOWN")
    item.pr_review_decision = pr.get("reviewDecision")
    item.pr_url = pr.get("url") or item.pr_url
    item.pr_changed_files = pr.get("changedFiles") or 0
    item.pr_additions = pr.get("additions") or 0
    item.pr_deletions = pr.get("deletions") or 0
    item.pr_commits = ((pr.get("commits") or {}).get("totalCount")) or 0

    label = f"PR #{item.pr_number}"
    for node in note_truncation(item, pr.get("comments"), f"{label} comments"):
        ingest(item, node, "pr")

    for node in note_truncation(item, pr.get("reviews"), f"{label} reviews"):
        state = node.get("state", "")
        if state == "PENDING":
            # Runs before the thread pass below so the draft mark survives dedupe.
            ingest_pending_review(item, node, label)
            continue
        body = (node.get("body") or "").strip()
        if not body and state not in ("CHANGES_REQUESTED", "APPROVED"):
            continue
        ingest(item, {**node, "body": f"[review {state}] {body}".strip()}, "pr")

    for thread in note_truncation(item, pr.get("reviewThreads"), f"{label} review threads"):
        if thread.get("isResolved"):
            continue  # resolving a thread *is* the ack for review comments
        item.unresolved_threads += 1
        where = f"{thread.get('path')}:{thread.get('line')}"
        for node in note_truncation(item, thread.get("comments"), f"{label} thread {where}"):
            login = (node.get("author") or {}).get("login", "ghost")
            if classify(login, node.get("body") or "") == "agent":
                continue
            ingest(item, node, "review", thread_id=thread["id"], path=where)

    commits = (pr.get("commits") or {}).get("nodes", [])
    if commits:
        item.last_activity = newest(item.last_activity, commits[0]["commit"].get("committedDate", ""))
    rollup = (commits[0]["commit"].get("statusCheckRollup") if commits else None) or {}
    item.ci_state = rollup.get("state")
    for ctx in note_truncation(item, rollup.get("contexts"), f"{label} CI checks"):
        if ctx.get("__typename") == "CheckRun":
            name = ctx.get("name", "?")
            if ctx.get("status") != "COMPLETED":
                item.ci_pending.append(name)
            elif ctx.get("conclusion") in ("FAILURE", "TIMED_OUT", "CANCELLED", "ACTION_REQUIRED"):
                item.ci_failing.append(name)
        else:
            name = ctx.get("context", "?")
            state = ctx.get("state")
            if state == "PENDING":
                item.ci_pending.append(name)
            elif state in ("FAILURE", "ERROR"):
                item.ci_failing.append(name)


# ── Ledger ──────────────────────────────────────────────────────────────────


def parse_ledger(body: str) -> dict:
    m = re.search(r"```json\s*(\{.*?\})\s*```", body, re.S)
    if not m:
        return {"v": 1, "acked": {}}
    try:
        data = json.loads(m.group(1))
    except json.JSONDecodeError:
        return {"v": 1, "acked": {}}
    data.setdefault("acked", {})
    return data


def render_ledger(data: dict) -> str:
    payload = {k: v for k, v in data.items() if not k.startswith("_")}
    payload["updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    body = json.dumps(payload, indent=2, sort_keys=True)
    return (
        f"{LEDGER_MARKER}\n"
        "<details><summary>🤖 loop state — machine-managed, ignore</summary>\n\n"
        f"```json\n{body}\n```\n\n"
        "</details>\n"
    )


def acked_ids(item: Item) -> set[int]:
    out: set[int] = set()
    for bucket in (item.ledger.get("acked") or {}).values():
        out.update(int(x) for x in bucket)
    return out


def drop_acked(item: Item) -> None:
    seen = acked_ids(item)
    item.comments = [c for c in item.comments if c.cid not in seen]


# ── Signals ─────────────────────────────────────────────────────────────────


def diagnose_empty(item: Item) -> str:
    """Explain an empty PR: a stopped run, an exhausted one, or a lost worktree."""
    if not item.pr_number:
        if item.worktree:
            return f"no PR exists, but a worktree does ({item.worktree}) — resume there"
        return "no PR and no local worktree — the task was claimed but never begun"
    if item.pr_commits <= 1:
        base = (
            f"PR #{item.pr_number} holds only the starter commit; "
            "a previous tick was interrupted (stopped, out of context, or crashed) "
        )
    else:
        base = f"PR #{item.pr_number} has {item.pr_commits} commits but no file changes; "
    if item.worktree:
        return base + f"and its worktree ({item.worktree}) is clean — restart the work"
    return base + "and no local worktree survives — restart the work from scratch"


def compute_signal(item: Item) -> None:
    labels = set(item.labels)
    n_human = len(item.pending_human)
    reasons = item.reasons

    # Board hygiene — the loops must never park a blocked/owner-waiting task in
    # "In progress"; anything that needs the owner belongs in "In review".
    owner_waiting = labels & set(WAITING_LABELS)
    if item.status == "In progress" and owner_waiting:
        item.warnings.append(
            f"in progress but carries {', '.join(sorted(owner_waiting))} → move to In review"
        )
    if item.status == "In review" and not (owner_waiting | (labels & set(OWNER_LABELS))):
        item.warnings.append("in review with no needs:*/blocked label — say what it waits for")
    if item.status == "Ready" and not item.loop:
        item.warnings.append("Ready but no Loop value — neither loop will pick this up")
    if item.status == "In review" and item.pr_number is None:
        # The warning exists for a task parked In review with *nothing to show*.
        # Three things fully explain an absent code PR, and firing anyway trains
        # the loop to ignore the ⚠ line: a question is out (`needs:input`), the
        # task is blocked (the blocker is on the issue by the label protocol), or
        # the spec gate has not passed yet — a spec-only task has no code PR *by
        # design*, so an open spec PR plus `needs:spec-approval` is the complete
        # answer to "where is the work?".
        spec_gate_pending = (
            item.spec_pr_number is not None and "needs:spec-approval" in labels
        )
        if not (spec_gate_pending or labels & {"needs:input", "blocked"}):
            item.warnings.append("in review with no PR — is the blocker written on the issue?")
    if "blocked" in labels:
        # A `blocked` row used to be the quietest thing on the board: bottom of
        # the sort, "skip — do not touch", and (before this) not even rendered in
        # DETAILS. So the claim has to be re-checked mechanically every tick.
        blocker = item.blocker
        if blocker is None:
            item.warnings.append(
                "carries `blocked` but no comment names a blocker as "
                "`owner/repo#N` — nothing to re-check, so this can never "
                "un-block itself; state the blocker or drop the label"
            )
        elif not blocker.resolved:
            item.warnings.append(
                f"blocker {blocker.ref} could not be resolved (deleted, private, "
                "or a bad reference) — check it by hand"
            )
        elif blocker.cleared:
            item.warnings.append(
                f"blocker {blocker.ref} has CLEARED "
                f"({blocker.state.lower()} {blocker.closed_at[:10]}, "
                f"{age_of(blocker.closed_at)} ago) — the `blocked` label is stale; "
                "remove it and pick this up"
            )
    if item.local_work:
        bits = []
        if item.wt_unpushed:
            bits.append(f"{item.wt_unpushed} unpushed commit(s)")
        if item.wt_dirty:
            bits.append(f"{item.wt_dirty} uncommitted file(s)")
        item.warnings.append(
            f"local work not on GitHub: {', '.join(bits)} in {item.worktree} — "
            "push it (or discard it deliberately) before doing anything else"
        )
    if item.status == "In progress" and not item.work_started and "tracker" not in labels:
        item.warnings.append(
            "in progress but nothing has been pushed — " + diagnose_empty(item)
        )

    if n_human:
        note = f"{n_human} unaddressed owner comment(s)"
        n_draft = len(item.pending_draft)
        if n_draft:
            note += f" ({n_draft} in an unsubmitted review)"
        reasons.append(note)
        item.signal = "HUMAN-INPUT"
    elif "approved:pr" in labels:
        reasons.append("owner approved the PR")
        item.signal = "PR-APPROVED"
    elif "approved:spec" in labels and "needs:spec-approval" in labels:
        reasons.append("owner approved the spec")
        item.signal = "SPEC-APPROVED"
    elif item.local_work:
        # Work exists only on this machine — the one state that can lose effort.
        detail = []
        if item.wt_unpushed:
            detail.append(f"{item.wt_unpushed} unpushed commit(s)")
        if item.wt_dirty:
            detail.append(f"{item.wt_dirty} uncommitted file(s)")
        reasons.append("stranded local work: " + ", ".join(detail))
        item.signal = "UNPUSHED"
    elif item.spec_merged and not item.work_started:
        # The spec cleared days ago and nobody started coding — the exact way a
        # task rots silently once its comments have been acked.
        reasons.append(f"spec PR #{item.spec_pr_number} is merged but no work is pushed")
        item.signal = "SPEC-MERGED"
    elif item.blocker and item.blocker.cleared:
        # Same rot as SPEC-MERGED — a gate cleared and nobody noticed. Ranked as
        # actionable rather than BLOCKED because the task is pickable *now*, and
        # BLOCKED means "skip, do not touch": leaving it there is what let two
        # rows sit on already-closed blockers.
        reasons.append(
            f"blocker {item.blocker.ref} cleared {age_of(item.blocker.closed_at)} ago "
            "— pickable now; drop the `blocked` label"
        )
        item.signal = "UNBLOCKED"
    elif item.ci_failing:
        reasons.append("CI failing: " + ", ".join(item.ci_failing[:4]))
        item.signal = "CI-RED"
    elif item.pr_mergeable == "CONFLICTING":
        reasons.append("PR has conflicts")
        item.signal = "CI-RED"
    elif item.unresolved_threads:
        reasons.append(f"{item.unresolved_threads} unresolved review thread(s)")
        item.signal = "THREADS"
    elif "blocked" in labels:
        reasons.append("blocked — waiting on the owner to unblock")
        item.signal = "BLOCKED"
    elif labels & set(WAITING_LABELS):
        reasons.append("waiting on owner: " + ", ".join(sorted(labels & set(WAITING_LABELS))))
        item.signal = "WAITING-OWNER"
    elif "tracker" in labels:
        reasons.append("tracker — progress lives in its sub-issues")
        item.signal = "TRACKER"
    elif item.status == "Ready":
        reasons.append("ready to pick up")
        item.signal = "READY"
    elif item.status == "In progress" and not item.work_started:
        reasons.append(diagnose_empty(item))
        item.signal = "NOT-STARTED"
    elif item.status == "In progress":
        reasons.append("work in flight")
        item.signal = "WIP"
    else:
        item.signal = "IDLE"

    if item.spec_pr_number and item.spec_pr_state == "OPEN" and item.signal != "HUMAN-INPUT":
        reasons.append(f"spec PR #{item.spec_pr_number} still open")

    if item.ci_pending and item.signal in ("PR-APPROVED", "WAITING-OWNER", "WIP"):
        reasons.append(f"CI pending: {len(item.ci_pending)} check(s)")


# Ordering used to sort the table — what the orchestrator should look at first.
SIGNAL_ORDER = [
    "HUMAN-INPUT",
    "PR-APPROVED",
    "SPEC-APPROVED",
    "UNPUSHED",
    "SPEC-MERGED",
    "UNBLOCKED",
    "CI-RED",
    "THREADS",
    "READY",
    "NOT-STARTED",
    "WIP",
    "TRACKER",
    "WAITING-OWNER",
    "BLOCKED",
    "IDLE",
]


# ── Rendering ───────────────────────────────────────────────────────────────


def ci_cell(item: Item) -> str:
    if not item.pr_number:
        return "-"
    if item.ci_failing:
        return f"FAIL({len(item.ci_failing)})"
    if item.ci_pending:
        return f"pend({len(item.ci_pending)})"
    if item.ci_state == "SUCCESS":
        return "ok"
    return (item.ci_state or "-").lower()


def label_cell(item: Item) -> str:
    marks = [LABEL_ABBREV[l] for l in item.labels if l in LABEL_ABBREV]
    return ",".join(marks) if marks else "-"


def spec_cell(item: Item) -> str:
    if not item.spec_pr_number:
        return "-"
    tag = {"MERGED": "merged", "OPEN": "open", "CLOSED": "closed"}.get(item.spec_pr_state, "?")
    return f"#{item.spec_pr_number}:{tag}"


def hum_cell(item: Item) -> str:
    """Count of unaddressed owner comments, and how long the oldest has waited.

    A trailing `+N✎` says N of them come from a review the owner never submitted.
    """
    pending = item.pending_human
    if not pending:
        return "-"
    cell = f"{len(pending)}·{age_of(item.oldest_pending_human)}"
    drafts = len(item.pending_draft)
    return f"{cell}+{drafts}✎" if drafts else cell


def work_cell(item: Item) -> str:
    """What the PR actually contains — an empty PR is the tell-tale."""
    if not item.pr_number:
        return "-"
    if item.pr_changed_files:
        return f"{item.pr_changed_files}f"
    return "EMPTY"


def local_cell(item: Item) -> str:
    """Work sitting in the local worktree that GitHub has never seen."""
    if not item.worktree:
        return "-"
    bits = []
    if item.wt_unpushed:
        bits.append(f"{item.wt_unpushed}c")
    if item.wt_dirty:
        bits.append(f"{item.wt_dirty}f")
    return "+".join(bits) if bits else "clean"


def render_table(items: list[Item]) -> str:
    headers = ["SIGNAL", "TASK", "STATUS", "LOOP", "LABELS", "AGE",
               "HUM", "BOT", "THR", "PR", "WORK", "LOCAL", "CI", "MRG", "SPEC"]
    rows = []
    for it in items:
        rows.append(
            [
                it.signal,
                it.slug,
                it.status,
                it.loop or "-",
                label_cell(it),
                age_of(it.last_activity),
                hum_cell(it),
                str(len(it.pending_bot)) if it.pending_bot else "-",
                str(it.unresolved_threads) if it.unresolved_threads else "-",
                (f"#{it.pr_number}" + ("d" if it.pr_draft else "")) if it.pr_number else "-",
                work_cell(it),
                local_cell(it),
                ci_cell(it),
                {"MERGEABLE": "ok", "CONFLICTING": "CONFLICT"}.get(it.pr_mergeable, "?")
                if it.pr_number
                else "-",
                spec_cell(it),
            ]
        )
    widths = [max(len(h), *(len(r[i]) for r in rows)) if rows else len(h) for i, h in enumerate(headers)]
    out = ["  ".join(h.ljust(w) for h, w in zip(headers, widths)).rstrip()]
    out.append("  ".join("-" * w for w in widths))
    for row in rows:
        out.append("  ".join(c.ljust(w) for c, w in zip(row, widths)).rstrip())
    return "\n".join(out)


def wrap_body(body: str, limit: int, indent: str = "      ") -> str:
    body = body.strip()
    if len(body) > limit:
        body = body[:limit].rstrip() + f"\n… [truncated, {len(body)} chars total]"
    lines = []
    for raw in body.splitlines():
        lines.extend(textwrap.wrap(raw, width=100) or [""])
    return "\n".join(indent + l for l in lines)


def render_details(items: list[Item], include_bots: bool, body_limit: int) -> str:
    out = []
    for it in items:
        quiet = ("IDLE", "TRACKER", "WAITING-OWNER", "BLOCKED")
        # A blocked row always renders: its blocker is a claim that has to be
        # re-checkable, and a single table line gives nothing to re-check.
        if it.signal in quiet and not it.pending and not it.warnings and not it.blocker:
            continue  # nothing to do and nothing new — keep the digest lean
        out.append("")
        out.append(f"── {it.slug} · {it.status} · loop={it.loop or '-'} · {it.signal}")
        out.append(f"   {it.title}")
        out.append(f"   item={it.item_id}")
        out.append(f"   issue={it.issue_url}")
        out.append(f"   labels: {', '.join(it.labels) if it.labels else '(none)'}")
        out.append(f"   last activity: {age_of(it.last_activity)} ago")
        if it.worktree:
            state = []
            if it.wt_unpushed:
                state.append(f"{it.wt_unpushed} unpushed commit(s)")
            if it.wt_dirty:
                state.append(f"{it.wt_dirty} uncommitted file(s)")
            if it.wt_stat:
                state.append(it.wt_stat)
            out.append(
                f"   worktree: {it.worktree} — {', '.join(state) if state else 'clean, in sync'}"
            )
        if it.blocker:
            b = it.blocker
            if not b.resolved:
                out.append(f"   blocker: {b.ref} — unresolvable")
            elif b.cleared:
                out.append(
                    f"   blocker: {b.ref} — {b.state.lower()} "
                    f"{b.closed_at[:10]} ({age_of(b.closed_at)} ago) · {b.title}\n"
                    f"   {b.url}"
                )
            else:
                # Quiet line: still blocked, but now visible and re-checkable.
                out.append(
                    f"   blocker: {b.ref} — still {b.state.lower()}, opened "
                    f"{age_of(b.created_at)} ago · {b.title}\n   {b.url}"
                )
        if it.spec_pr_number:
            bits = [f"spec PR #{it.spec_pr_number} ({it.spec_pr_state.lower()})"]
            if it.spec_unresolved_threads:
                bits.append(f"{it.spec_unresolved_threads} unresolved thread(s)")
            out.append("   " + " · ".join(bits) + f"\n   {it.spec_pr_url}")
        if it.pr_number:
            bits = [
                f"PR #{it.pr_number}{' (draft)' if it.pr_draft else ''}",
                (
                    f"{it.pr_changed_files} file(s) +{it.pr_additions}/-{it.pr_deletions}"
                    f" over {it.pr_commits} commit(s)"
                    if it.pr_changed_files
                    else f"EMPTY — {it.pr_commits} commit(s), no file changes"
                ),
                f"CI={ci_cell(it)}",
                f"mergeable={it.pr_mergeable}",
                f"review={it.pr_review_decision or '-'}",
                f"threads={it.unresolved_threads} unresolved",
            ]
            out.append("   " + " · ".join(bits))
            if it.ci_failing:
                out.append("   failing: " + ", ".join(it.ci_failing))
            out.append(f"   {it.pr_url}")
        for reason in it.reasons:
            out.append(f"   → {reason}")
        for warn in it.warnings:
            out.append(f"   ⚠ {warn}")
        if not it.has_ledger and it.comments:
            out.append(
                "   ⚠ no ack ledger yet — comments below may include pre-marker agent output; "
                "read them, then ack what is already handled"
            )
        drafts = it.pending_draft
        if drafts:
            where = ", ".join(sorted({c.draft_on for c in drafts if c.draft_on}))
            out.append(
                f"   ⚠ {len(drafts)} of the owner comments below sit in an UNSUBMITTED "
                f"(pending) review on {where} — visible only because the loop shares the "
                "owner's account, invisible to everyone else. Treat them as direction; "
                "when you reply, say the review was never submitted."
            )
        for c in it.pending_human:
            tag = "OWNER · DRAFT REVIEW" if c.draft_on else "OWNER"
            head = f"   [{tag} · {c.kind} {c.cid}] @{c.author} {c.created} ({age_of(c.created)} ago)"
            if c.path:
                head += f" · {c.path}"
            out.append(head)
            out.append(wrap_body(c.body, body_limit))
        bots = it.pending_bot
        if bots:
            if include_bots:
                for c in bots:
                    head = f"   [BOT · {c.kind} {c.cid}] @{c.author} {c.created}"
                    if c.path:
                        head += f" · {c.path}"
                    out.append(head)
                    out.append(wrap_body(c.body, body_limit))
            else:
                out.append(
                    f"   [BOT] {len(bots)} machine comment(s) suppressed — "
                    f"use --include-bots, or coderabbit-prompts.py {OWNER}/{it.repo} {it.pr_number}"
                )
        if it.pending:
            out.append(
                f"   ack: board-tick.py ack --repo {it.repo} --issue {it.number} --all "
                f'--note "<what you did>"'
            )
    return "\n".join(out)


def render_json(items: list[Item]) -> str:
    payload = []
    for it in items:
        payload.append(
            {
                "item_id": it.item_id,
                "repo": it.repo,
                "issue": it.number,
                "title": it.title,
                "issue_url": it.issue_url,
                "status": it.status,
                "loop": it.loop,
                "labels": it.labels,
                "signal": it.signal,
                "reasons": it.reasons,
                "warnings": it.warnings,
                "has_ledger": it.has_ledger,
                "last_activity": it.last_activity,
                "last_activity_age": age_of(it.last_activity),
                "oldest_pending_human": it.oldest_pending_human or None,
                "work_started": it.work_started,
                "pushed_work": it.pushed_work,
                "local": (
                    {
                        "worktree": it.worktree,
                        "uncommitted_files": it.wt_dirty,
                        "unpushed_commits": it.wt_unpushed,
                        "diff_stat": it.wt_stat or None,
                    }
                    if it.worktree
                    else None
                ),
                "pr": (
                    {
                        "number": it.pr_number,
                        "url": it.pr_url,
                        "draft": it.pr_draft,
                        "state": it.pr_state,
                        "mergeable": it.pr_mergeable,
                        "review_decision": it.pr_review_decision,
                        "changed_files": it.pr_changed_files,
                        "additions": it.pr_additions,
                        "deletions": it.pr_deletions,
                        "commits": it.pr_commits,
                        "ci_state": it.ci_state,
                        "ci_failing": it.ci_failing,
                        "ci_pending": it.ci_pending,
                        "unresolved_threads": it.unresolved_threads,
                    }
                    if it.pr_number
                    else None
                ),
                "blocker": (
                    {
                        "ref": it.blocker.ref,
                        "kind": it.blocker.kind,
                        "state": it.blocker.state,
                        "cleared": it.blocker.cleared,
                        "resolved": it.blocker.resolved,
                        "title": it.blocker.title,
                        "url": it.blocker.url,
                        "closed_at": it.blocker.closed_at or None,
                        "from_comment": it.blocker.source_cid,
                    }
                    if it.blocker
                    else None
                ),
                "spec_pr": (
                    {
                        "number": it.spec_pr_number,
                        "repo": SPEC_REPO,
                        "url": it.spec_pr_url,
                        "state": it.spec_pr_state,
                        "unresolved_threads": it.spec_unresolved_threads,
                    }
                    if it.spec_pr_number
                    else None
                ),
                "pending_comments": [
                    {
                        "kind": c.kind,
                        "id": c.cid,
                        "who": c.who,
                        "author": c.author,
                        "created": c.created,
                        "url": c.url,
                        "path": c.path,
                        "thread_id": c.thread_id,
                        "draft_review_on": c.draft_on,
                        "body": c.body,
                    }
                    for c in it.pending
                ],
            }
        )
    return json.dumps(payload, indent=2)


# ── Commands ────────────────────────────────────────────────────────────────


# A tick is a few dozen GraphQL requests (the board list, a spec-PR list, a PR
# list per unlinked item, the hydration chunks, the blocker lookup), and requests
# cost points rather than one each. Refuse to start without headroom: a tick that
# dies halfway has already spent the budget and still tells you nothing.
#
# Measured, not guessed: a 17-item hitl tick cost 228 of the 5000 hourly points
# (4121 → 3893). The default leaves headroom for a larger board; raise it if the
# board grows, and note that ~20 ticks per hour is the ceiling either way.
MIN_GRAPHQL_BUDGET = 400


def preflight(min_budget: int) -> str | None:
    """Refuse to start a tick the GraphQL budget cannot finish. None = go ahead."""
    budget = graphql_budget()
    if budget is None:
        return None  # can't tell — proceed and let the mid-tick guard catch it
    remaining, _, _ = budget
    if remaining >= min_budget:
        return None
    headline = (
        "GITHUB GRAPHQL BUDGET TOO LOW TO RUN A TICK — NOTHING WAS READ"
        if remaining > 0
        else "GITHUB GRAPHQL RATE LIMIT EXHAUSTED — NOTHING WAS READ"
    )
    extra = (
        f"\n Refusing to start: {remaining} point(s) left, {min_budget} needed "
        f"(--min-budget to override)."
    )
    return rate_limit_banner(headline, budget) + extra


def cmd_tick(args: argparse.Namespace) -> int:
    # Before anything else: a tick that cannot see the board must say so rather
    # than half-read it. Checked up front because `gh` reports exhaustion with
    # misleading errors that read like configuration bugs.
    refusal = preflight(args.min_budget)
    if refusal:
        print(refusal, file=sys.stderr)
        return 75  # EX_TEMPFAIL — transient; re-run after the reset
    statuses = tuple(args.status) if args.status else ACTIVE_STATUSES
    items = fetch_board(statuses)
    if args.loop:
        items = [i for i in items if i.loop == args.loop]
    if args.repo:
        items = [i for i in items if i.repo == args.repo]
    if not items:
        print("No active board items match.")
        return 0
    attach_spec_prs(items)
    hydrate(items)
    # Must follow hydrate: the blocker reference is parsed out of the comments
    # hydrate fetches. One batched call, skipped when nothing is blocked.
    resolve_blockers(items)
    projects = args.projects_dir or (workspace_root() / "projects")
    for it in items:
        if not args.no_local:
            inspect_worktree(it, projects)
        drop_acked(it)
        compute_signal(it)
    # Most urgent signal first; within a signal, the longest-neglected first.
    items.sort(
        key=lambda i: (
            SIGNAL_ORDER.index(i.signal) if i.signal in SIGNAL_ORDER else 99,
            i.oldest_pending_human or i.last_activity or "9999",
            i.slug,
        )
    )

    if args.json:
        print(render_json(items))
        return 0

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    print(f"Board tick · {stamp} · {len(items)} active item(s)\n")
    print(render_table(items))
    details = render_details(items, args.include_bots, args.body_limit)
    if details.strip():
        print("\nDETAILS")
        print(details)
    return 0


def find_ledger_comment(repo: str, issue: int) -> tuple[int | None, dict]:
    out = gh(
        "api",
        f"repos/{OWNER}/{repo}/issues/{issue}/comments",
        "--paginate",
        "-q",
        ".[] | {id: .id, body: .body}",
    )
    for line in out.splitlines():
        if not line.strip():
            continue
        node = json.loads(line)
        if LEDGER_MARKER in (node.get("body") or ""):
            return node["id"], parse_ledger(node["body"])
    return None, {"v": 1, "acked": {}}


def collect_pending_ids(repo: str, issue: int) -> dict[str, list[int]]:
    """Re-fetch one item so `ack --all` covers exactly what a tick would show."""
    items = [i for i in fetch_board(ACTIVE_STATUSES) if i.repo == repo and i.number == issue]
    if not items:
        # Not on the board (or not active) — still ack what is on the issue/PR.
        item = Item(item_id="", status="", loop=None, repo=repo, number=issue, title="", issue_url="")
        item.pr_number = find_pr_by_branch(repo, issue)
        items = [item]
    item = items[0]
    attach_spec_prs([item])
    hydrate([item])
    drop_acked(item)
    buckets: dict[str, list[int]] = {
        "issue": [],
        "pr": [],
        "review": [],
        "spec": [],
        "pending": [],
    }
    for c in item.pending:
        buckets.setdefault(c.kind, []).append(c.cid)
    return buckets


def cmd_ack(args: argparse.Namespace) -> int:
    comment_id, ledger = find_ledger_comment(args.repo, args.issue)
    acked = ledger.setdefault("acked", {})

    if args.all:
        buckets = collect_pending_ids(args.repo, args.issue)
    else:
        buckets = {
            "spec": list(args.spec_comment),
            "issue": list(args.issue_comment),
            "pr": list(args.pr_comment),
            "review": list(args.review_comment),
            "pending": list(args.pending_comment),
        }
    total = sum(len(v) for v in buckets.values())
    if not total:
        print("Nothing to ack.")
        return 0

    for kind, ids in buckets.items():
        if not ids:
            continue
        bucket = acked.setdefault(kind, [])
        bucket.extend(i for i in ids if i not in bucket)
        bucket.sort()

    if args.note:
        notes = ledger.setdefault("notes", [])
        notes.append(
            {
                "at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "acked": total,
                "note": args.note,
            }
        )
        del notes[:-20]  # keep the ledger small

    body = render_ledger(ledger)
    if args.dry_run:
        print(f"[dry-run] would ack {total} comment(s) on {args.repo}#{args.issue}")
        print(f"[dry-run] {'PATCH comment ' + str(comment_id) if comment_id else 'POST new ledger comment'}")
        print(body)
        return 0
    if comment_id:
        gh(
            "api",
            "-X",
            "PATCH",
            f"repos/{OWNER}/{args.repo}/issues/comments/{comment_id}",
            "-f",
            f"body={body}",
        )
    else:
        gh(
            "api",
            "-X",
            "POST",
            f"repos/{OWNER}/{args.repo}/issues/{args.issue}/comments",
            "-f",
            f"body={body}",
        )
    print(f"Acked {total} comment(s) on {args.repo}#{args.issue}.")
    return 0


def cmd_post(args: argparse.Namespace) -> int:
    body = sys.stdin.read() if args.body == "-" else args.body
    body = body.rstrip() + f"\n\n{AGENT_MARKER}\n"
    target = args.pr or args.issue
    gh(
        "api",
        "-X",
        "POST",
        f"repos/{OWNER}/{args.repo}/issues/{target}/comments",
        "-f",
        f"body={body}",
    )
    print(f"Posted agent comment on {args.repo}#{target}.")
    return 0


def ensure_labels(repo: str, names: list[str]) -> None:
    for name in names:
        if name not in LOOP_LABELS:
            continue
        color, desc = LOOP_LABELS[name]
        gh(
            "label",
            "create",
            name,
            "--repo",
            f"{OWNER}/{repo}",
            "--color",
            color,
            "--description",
            desc,
            check=False,
        )


def cmd_label(args: argparse.Namespace) -> int:
    if not args.add and not args.remove:
        print("Nothing to do — pass --add and/or --remove.", file=sys.stderr)
        return 2
    unknown = [n for n in args.add if n not in LOOP_LABELS]
    if unknown:
        print(f"warning: not a loop label: {', '.join(unknown)}", file=sys.stderr)
    if args.add and set(args.add) & set(OWNER_LABELS):
        print(
            f"refusing to set owner-only label(s): "
            f"{', '.join(sorted(set(args.add) & set(OWNER_LABELS)))} — only the owner approves",
            file=sys.stderr,
        )
        return 2
    ensure_labels(args.repo, args.add)
    cmd = ["issue", "edit", str(args.issue), "--repo", f"{OWNER}/{args.repo}"]
    for name in args.add:
        cmd += ["--add-label", name]
    for name in args.remove:
        cmd += ["--remove-label", name]
    if args.dry_run:
        print("[dry-run] gh " + " ".join(cmd))
        return 0
    gh(*cmd)
    print(f"{args.repo}#{args.issue}: +{args.add or []} -{args.remove or []}")
    return 0


def cmd_init_labels(args: argparse.Namespace) -> int:
    ensure_labels(args.repo, list(LOOP_LABELS))
    print(f"Loop labels ensured on {OWNER}/{args.repo}: {', '.join(LOOP_LABELS)}")
    return 0


# ── CLI ─────────────────────────────────────────────────────────────────────


def main(argv: list[str]) -> int:
    if not shutil.which("gh"):
        print("gh CLI not found on PATH", file=sys.stderr)
        return 2

    parser = argparse.ArgumentParser(prog="board-tick.py", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd")

    p_tick = sub.add_parser("tick", help="print the decision table (default)")
    p_tick.add_argument("--loop", choices=["hitl", "auto"], help="only items routed to this loop")
    p_tick.add_argument("--repo", help="only items in this repo")
    p_tick.add_argument("--status", action="append", help="override the active statuses")
    p_tick.add_argument("--include-bots", action="store_true", help="print bot comment bodies too")
    p_tick.add_argument("--body-limit", type=int, default=1800, help="chars per comment body")
    p_tick.add_argument("--projects-dir", help="where task worktrees live (default <workspace>/projects)")
    p_tick.add_argument("--no-local", action="store_true", help="skip the local worktree check")
    p_tick.add_argument("--json", action="store_true", help="machine-readable output")
    p_tick.add_argument(
        "--min-budget",
        type=int,
        default=MIN_GRAPHQL_BUDGET,
        help=f"refuse to start below this many GraphQL points (default {MIN_GRAPHQL_BUDGET}; 0 disables)",
    )
    p_tick.set_defaults(func=cmd_tick)

    p_ack = sub.add_parser("ack", help="mark comments seen/addressed in the issue's ledger")
    p_ack.add_argument("--repo", required=True)
    p_ack.add_argument("--issue", required=True, type=int)
    p_ack.add_argument("--all", action="store_true", help="ack every currently pending comment")
    p_ack.add_argument("--issue-comment", action="append", type=int, default=[])
    p_ack.add_argument("--pr-comment", action="append", type=int, default=[])
    p_ack.add_argument("--review-comment", action="append", type=int, default=[])
    p_ack.add_argument("--spec-comment", action="append", type=int, default=[])
    p_ack.add_argument(
        "--pending-comment",
        action="append",
        type=int,
        default=[],
        help="ack a comment from an unsubmitted (pending) review",
    )
    p_ack.add_argument("--note", help="short record of what was done about them")
    p_ack.add_argument("--dry-run", action="store_true")
    p_ack.set_defaults(func=cmd_ack)

    p_post = sub.add_parser("post", help="comment as the agent (adds the agent marker)")
    p_post.add_argument("--repo", required=True)
    p_post.add_argument("--issue", type=int)
    p_post.add_argument("--pr", type=int)
    p_post.add_argument("--body", required=True, help="text, or - to read stdin")
    p_post.set_defaults(func=cmd_post)

    p_label = sub.add_parser("label", help="add/remove loop labels on an issue")
    p_label.add_argument("--repo", required=True)
    p_label.add_argument("--issue", required=True, type=int)
    p_label.add_argument("--add", action="append", default=[])
    p_label.add_argument("--remove", action="append", default=[])
    p_label.add_argument("--dry-run", action="store_true")
    p_label.set_defaults(func=cmd_label)

    p_init = sub.add_parser("init-labels", help="create the loop label set in a repo")
    p_init.add_argument("--repo", required=True)
    p_init.set_defaults(func=cmd_init_labels)

    # `tick` is the default subcommand, but keep top-level -h/--help working.
    if not argv or (argv[0].startswith("-") and argv[0] not in ("-h", "--help")):
        argv = ["tick", *argv]
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help()
        return 1
    if args.cmd == "post" and not (args.issue or args.pr):
        print("post: pass --issue or --pr", file=sys.stderr)
        return 2
    return args.func(args)


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except RateLimited:
        # Deliberately not a partial digest: a half-read board invites exactly the
        # silent under-reporting the TRUNCATED warning exists to prevent. Whatever
        # was collected before this point is discarded.
        print(
            rate_limit_banner(
                "GITHUB GRAPHQL RATE LIMIT HIT MID-TICK — THIS TICK IS VOID",
                graphql_budget(),
            ),
            file=sys.stderr,
        )
        sys.exit(75)  # EX_TEMPFAIL — transient; re-run after the reset
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
