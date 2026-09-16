#!/usr/bin/env python3
"""Name the other files that discuss a subject whose claim you just changed.

This is an **advisory** check, not a gate. It cannot tell whether two statements
agree; it can only tell you that two files talk about the same thing and that one
of them just moved. Deciding is yours.

Why it exists
-------------
The corpus's recurring failure is not a wrong number, it is a *stale duplicate*:
a fact measured again, corrected carefully in the file being edited, and left
standing in its older form somewhere else. `check_shared_facts` in
`check_doc_consistency.py` catches the value-level case (`SYMBOL $VALUE` given
two values), and that is the easy half. The hard half is a claim whose *shape*
changed -- "the limit is 513 characters" becoming "the limit is not a fixed
number" -- where both files may quote the same digits and still contradict each
other. No value comparison finds that, which is why this looks for adjacency
instead and hands the judgement back.

Worked case, the one it was built from: a commit corrected the `cpp` logical-line
limit in `c/os9-c-cheatsheet.md` while `c/kandr-vs-ansi.md` still said `cpp`
"bus-errors at 513 characters" in two places. Both files agreed 513 fails, so
nothing numeric disagreed; the contradiction was that one presented a fixed
threshold and the other had just established there is none.

What counts as a claim
----------------------
A changed line is claim-bearing only if it carries a quantity or limit wording
(`_CLAIMY`). Prose that mentions a subject without asserting a bound about it is
not interesting -- most mentions are not claims, and treating them as such is
what makes a checker noisy enough to be switched off.

Measured behaviour on this repo's own history: silent on three of four sampled
commits, and on the fourth it named the file holding the stale claim two commits
before a human found it by accident.
"""

import argparse
import collections
import pathlib
import re
import subprocess
import sys

# Confidence tags and the emulator's name are not subjects -- they appear in
# backticks on nearly every claim-bearing line and would key everything to
# everything.
_NOT_SUBJECTS = frozenset(
    {"Live", "Source", "Manual", "Flag", "Absent", "Hearsay", "Note", "os9exec"}
)

_IDENT = re.compile(r"`([A-Za-z_][A-Za-z0-9_$]{1,24})`")

# A line asserts a bound if it carries a multi-digit quantity or limit wording.
_CLAIMY = re.compile(
    r"\b\d{2,6}\b|limit|maximum|\bmax\b|at most|up to|no more than|stops at|"
    r"fails at|bus-error|aborts|exceeds|longer than|not fixed|best case",
    re.IGNORECASE,
)


def subjects_in(line):
    """Return the backticked identifiers a claim-bearing `line` is about."""
    if not _CLAIMY.search(line):
        return set()
    return {name for name in _IDENT.findall(line) if name not in _NOT_SUBJECTS}


def blocks(text):
    """Yield (first lineno, joined text) for each blank-line-separated block.

    The corpus hard-wraps its prose, so a claim's subject and its quantity
    routinely land on **different physical lines** -- "Microware `cpp`" ending one
    line and "bus-errors at 513 characters" beginning the next. Matching line by
    line cannot see those, and the historical case this check exists for is
    exactly that shape. Tables and list items are single lines and so are
    unaffected by the join.
    """
    start = None
    buf = []
    for lineno, line in enumerate(text.splitlines(), 1):
        if line.strip():
            if start is None:
                start = lineno
            buf.append(line)
        elif buf:
            yield start, " ".join(buf)
            start, buf = None, []
    if buf:
        yield start, " ".join(buf)


def subjects_in_text(text):
    """Subjects asserted anywhere within one block of joined prose."""
    return subjects_in(text)


def added_lines(rev, root):
    """Return {path: [added line, ...]} for `rev`, or for the index when rev is None."""
    if rev is None:
        cmd = ["git", "diff", "--cached", "--unified=0", "--", root]
    else:
        cmd = ["git", "show", rev, "--unified=0", "--", root]
    diff = subprocess.run(cmd, capture_output=True, text=True).stdout

    per_file = collections.defaultdict(list)
    current = None
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            current = line[len("+++ b/") :]
        elif current and line.startswith("+") and not line.startswith("+++"):
            per_file[current].append(line[1:])
    return per_file


def coupled_files(subjects, root, exclude):
    """Return [(path, [(lineno, shared subjects, text), ...])] for files making claims
    about any of `subjects`, skipping the files already being edited."""
    found = []
    for path in sorted(pathlib.Path(root).rglob("*.md")):
        if str(path) in exclude:
            continue
        hits = []
        for lineno, block in blocks(path.read_text(errors="replace")):
            shared = subjects_in_text(block) & subjects
            if shared:
                hits.append((lineno, sorted(shared), block.strip()))
        if hits:
            found.append((path, hits))
    return found


def report(rev, root, per_line_cap=3, stream=sys.stdout):
    """Print the advisory. Returns the number of coupled files named."""
    changes = added_lines(rev, root)
    touched = set(changes)

    by_file = {}
    for path, lines in changes.items():
        # A window, not the whole diff: added lines wrap the same way the file
        # does, so a subject and its quantity can be one line apart -- but
        # joining every added line in a commit would couple unrelated edits.
        subjects = set()
        for i in range(len(lines)):
            subjects |= subjects_in_text(" ".join(lines[i : i + 3]))
        if subjects:
            by_file[path] = subjects

    if not by_file:
        print("claim-coupling: no claim-bearing changes under " + root, file=stream)
        return 0

    # One advisory per coupled file, not one per (changed file, coupled file)
    # pair -- editing two files that both touch a subject should not double the
    # reading list.
    all_subjects = set()
    for subjects in by_file.values():
        all_subjects |= subjects

    print("changed: " + ", ".join(sorted(by_file)), file=stream)
    print(f"  claims about: {', '.join(sorted(all_subjects))}", file=stream)

    named = 0
    for other, hits in coupled_files(all_subjects, root, touched):
        named += 1
        print(f"\n  also claims about the same -> {other}", file=stream)
        for lineno, shared, text in hits[:per_line_cap]:
            print(f"      :{lineno} [{', '.join(shared)}] {text[:88]}", file=stream)
        if len(hits) > per_line_cap:
            print(f"      ... {len(hits) - per_line_cap} more", file=stream)

    if named:
        print(
            "\nclaim-coupling: advisory only -- these files may or may not still agree.\n"
            "Read them before assuming the correction is complete.",
            file=stream,
        )
    else:
        print("claim-coupling: nothing else claims about the same subjects.", file=stream)
    return named


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--rev", default=None, help="commit to inspect (default: the staged index)"
    )
    parser.add_argument("--root", default="os9-dev/references", help="tree to scan")
    args = parser.parse_args(argv)
    report(args.rev, args.root)
    return 0  # advisory: never fails a build


if __name__ == "__main__":
    sys.exit(main())
