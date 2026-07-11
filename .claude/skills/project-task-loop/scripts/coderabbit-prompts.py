#!/usr/bin/env python3
"""Extract CodeRabbit's "Prompt for AI Agents" fix instructions from a PR.

Usage: coderabbit-prompts.py <owner/repo> <pr-number>
  e.g. coderabbit-prompts.py gaarutyunov/workspace 2

Prints, per CodeRabbit finding: file:line, the REST comment id, severity/title,
and the exact agent prompt CodeRabbit generated — so each can be verified
against the current code and applied or declined.

Requires: `gh` on PATH (authenticated), python3.
"""
import json
import re
import subprocess
import sys

FENCE = "`" * 3
PROMPT_RE = re.compile(r"Prompt for AI Agents</summary>\s*" + FENCE + r"(.*?)" + FENCE, re.S)
TITLE_RE = re.compile(r"\*\*(.+?)\*\*")
SEV_RE = re.compile(r"(\U0001F7E1 Minor|\U0001F7E0 Major|\U0001F534[^_|]*)")


def main() -> int:
    if len(sys.argv) != 3:
        sys.exit("usage: coderabbit-prompts.py <owner/repo> <pr-number>")
    repo, pr = sys.argv[1], sys.argv[2]

    out = subprocess.run(
        ["gh", "api", f"repos/{repo}/pulls/{pr}/comments", "--paginate"],
        capture_output=True, text=True,
    )
    if out.returncode != 0:
        sys.exit(out.stderr.strip() or "gh api failed")

    comments = json.loads(out.stdout)
    found = 0
    for c in comments:
        body = c.get("body", "")
        if "cr-comment" not in body:            # CodeRabbit marker
            continue
        found += 1
        sev = SEV_RE.search(body)
        title = TITLE_RE.search(re.sub(r"<details>.*?</details>", "", body, flags=re.S))
        prompt = PROMPT_RE.search(body)
        print("=" * 70)
        print(f"[{c['path']}:{c.get('line')}]  comment_id={c['id']}")
        print(f"  {sev.group(1) if sev else '?'} — {title.group(1) if title else '(see body)'}")
        print()
        print(prompt.group(1).strip() if prompt else "(no agent prompt in this comment)")

    if not found:
        print("No CodeRabbit comments found on this PR.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
