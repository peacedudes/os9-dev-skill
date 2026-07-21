#!/usr/bin/env python3
"""Skill-doc consistency checker for the os9-dev / os9-systems-dev skills.

Anchors on OS-9 system-call tokens (F$.../I$...) and cross-checks, per platform,
whether the docs agree on each call's *presence*. See DESIGN.md.

Neither the 6809 (NitrOS-9) nor the 68k (os9exec) runtime is an oracle -- both
are reverse-engineered clones, wrong in minor cases. Findings are framed
neutrally ("these disagree, investigate"), never "X is authoritative, fix Y".

Key subtlety learned from the first dogfood run: confidence tags encode
*evidence strength*, not presence. `Live` means "we ran it and observed" -- and
you can observe an *absence* ("`Live` -- FAILS, unimplemented"). So presence is
read from specific wording, not from the tag alone.
"""

import os
import re
import sys
from collections import namedtuple

# --- lexical anchors -------------------------------------------------------

TAG_ROW = re.compile(r"^\|\s*`(?P<tag>[A-Za-z]+)`\s*\|")
SYSCALL = re.compile(r"\b[FI]\$[A-Za-z][A-Za-z0-9]+\b")
BACKTICK_WORD = re.compile(r"`([A-Za-z][A-Za-z0-9]*)`")

# A run that *observed the call missing* -- absence, not presence. Narrow on
# purpose: a mere "fails E$PNNF" is an error-path return of a call that exists;
# only "unimplemented" / E$UnkSvc (OS-9's unimplemented-service error) means gone.
_FAILURE = re.compile(r"\b(unimplemented|not implemented|never implemented)\b|E\$UnkSvc", re.I)
# Explicit "this call does not exist here" wording, bound tightly to the token.
# The proximity forms forbid clause punctuation between token and verdict, so a
# later clause's "unimplemented" (a comma/paren away) cannot bind to the call.
_ABSENCE = [
    r"\b(?:has|have|had)\s+no\s+`?{sc}\b",
    r"\b(?:no|lacks?|without)\s+`?{sc}\b",
    r"`?{sc}`?\b[^.,;:()]{{0,40}}?\b(?:is\s+)?(?:unimplemented|absent|not\s+implemented|does\s?n['’]?t\s+exist)",
]
# Explicit "this call is here and works" wording.
_PRESENCE = [
    r"\bdoes\s+implement\s+`?{sc}\b",
    r"`?{sc}`?\b[^.,;:()]{{0,40}}?\bis\s+implemented\b",
]

# A `Flag` written as already-cleared -- "`Flag` resolved" narrates the fix, so
# it is not an open divergence.
_FLAG_RESOLVED = re.compile(r"`?Flag`?\s+(?:is\s+|now\s+)?(?:resolved|cleared)", re.I)

# A `.md`-shaped path token, backticked or bare -- used by the INDEX.md
# cross-reference check. Word/dot/slash/dash chars only, so prose punctuation
# around it (backticks, trailing periods) never gets swept in.
_DOC_TOKEN = re.compile(r"[\w./-]+\.md")

INDEX_FILENAME = "INDEX.md"

# A wiki-style memory cross-link, e.g. "see [[user-designed-rbf-eof-lock]]".
# Optional surrounding backticks are captured so a backtick-quoted occurrence
# (`` `[[memory]]` `` describing the linking convention itself, not using it)
# can be told apart from a real link.
_MEMORY_LINK = re.compile(r"(`?)\[\[([A-Za-z0-9_-]+)\]\](`?)")

# The `name:` field of a memory file's YAML frontmatter.
_FRONTMATTER_NAME = re.compile(r"\A---\n.*?^name:\s*(\S+)\s*$.*?^---", re.M | re.S)

# Platform hints found in the prose itself (override the path when present in an
# absence clause -- e.g. "6809 has no F$STrap" written in a platform-neutral file).
_PLAT_6809 = re.compile(r"\b(6809|nitros-?9|coco)\b", re.I)
_PLAT_68K = re.compile(r"\b(68k|68000|os9exec|os-?9000)\b", re.I)

# Meta-docs are indexes / conventions / worklists that *quote* calls as examples
# rather than making claims about them -- never scan them for mentions.
META_DOCS = {"CONFIDENCE-TAGS.md", "VERIFICATION-BACKLOG.md", "INDEX.md", "SOURCES.md"}
CONFIDENCE_TAGS_FILE = "CONFIDENCE-TAGS.md"

# A mention of one syscall on one line: which platform it speaks to, whether it
# asserts the call present/absent/neither, and the confidence tags on the line.
Mention = namedtuple("Mention", "syscall file line platform presence tags")

# One reported disagreement. `locations` are (file, line) pairs. Always neutral.
Finding = namedtuple("Finding", "check syscall message locations")


# --- parsing ---------------------------------------------------------------

def parse_known_tags(md):
    """Return the confidence-tag names defined in CONFIDENCE-TAGS.md's table.

    Parsed rather than hardcoded, so the known-tag set stays in sync with the doc.
    """
    return {m.group("tag") for m in (TAG_ROW.match(line) for line in md.splitlines()) if m}


def verified_against(md):
    """Return the (platform, build-identity) baseline rows from CONFIDENCE-TAGS.md.

    Reads the data rows of the table under the "What `Live` is verified against"
    heading, so the checker can surface which build the `Live` tier reflects.
    """
    rows, in_section = [], False
    for line in md.splitlines():
        if line.startswith("## "):
            in_section = "verified against" in line.lower()
            continue
        if in_section and line.lstrip().startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) >= 2 and "---" not in cells[0] and cells[0].lower() != "platform":
                rows.append((cells[0], cells[1]))
    return rows


def platform_of(path):
    """Classify a doc path as "6809", "68k", or "neutral" (applies to both)."""
    parts = path.replace(os.sep, "/").split("/")
    if "6809" in parts:
        return "6809"
    if "68k" in parts:
        return "68k"
    return "neutral"


def _presence(line, syscall, tags, is_subject):
    """Read whether `line` asserts `syscall` is present, absent, or neither.

    Presence comes from specific wording, not the tag: `Live` next to a failure
    marker means the call was observed *missing*. Tag-based presence applies only
    to the row's subject syscall -- a call merely *referenced* in another row's
    notes (e.g. "the name was `F$Load`ed") is not a claim about that call.
    """
    sc = re.escape(syscall)
    if any(re.search(p.format(sc=sc), line, re.I) for p in _ABSENCE):
        return "absent"
    if any(re.search(p.format(sc=sc), line, re.I) for p in _PRESENCE):
        return "present"
    if not is_subject:
        return "none"
    if "Absent" in tags:
        return "absent"
    if "Live" in tags and _FAILURE.search(line):
        return "absent"
    if "Live" in tags:
        return "present"
    return "none"


def _absence_platform(line, default):
    """Scope an absence claim to the platform its sentence names, if any."""
    if _PLAT_6809.search(line):
        return "6809"
    if _PLAT_68K.search(line):
        return "68k"
    return default


def find_mentions(text, filename, known_tags):
    """Return a Mention per syscall occurrence in `text`."""
    path_platform = platform_of(filename)
    mentions = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        syscalls = SYSCALL.findall(line)
        if not syscalls:
            continue
        tags = frozenset(w for w in BACKTICK_WORD.findall(line) if w in known_tags)
        # In a markdown table row the subject is the call in the first column;
        # tag-based presence attaches to it, not to calls named in the notes.
        subject = syscalls[0] if line.lstrip().startswith("|") else None
        for syscall in syscalls:
            presence = _presence(line, syscall, tags, syscall == subject)
            platform = _absence_platform(line, path_platform) if presence == "absent" else path_platform
            mentions.append(Mention(syscall, filename, lineno, platform, presence, tags))
    return mentions


# --- checks ----------------------------------------------------------------

def _by_syscall(mentions):
    grouped = {}
    for m in mentions:
        grouped.setdefault(m.syscall, []).append(m)
    return grouped


def _dedup(pairs):
    seen, out = set(), []
    for pair in pairs:
        if pair not in seen:
            seen.add(pair)
            out.append(pair)
    return out


def check_presence_contradiction(mentions):
    """A syscall asserted present in one place and absent in another, same platform.

    A mention scoped to a concrete platform (or "neutral", which speaks to both)
    only conflicts with the opposing assertion on that same platform -- so a call
    absent on the 6809 but present on the 68k is not flagged.
    """
    findings = []
    for syscall, group in _by_syscall(mentions).items():
        conflicting_platforms = []
        contributors = []
        for platform in ("6809", "68k"):
            present = [m for m in group if m.presence == "present" and m.platform in (platform, "neutral")]
            absent = [m for m in group if m.presence == "absent" and m.platform in (platform, "neutral")]
            if present and absent:
                conflicting_platforms.append(platform)
                contributors.extend(present + absent)
        if conflicting_platforms:
            where = " and ".join(conflicting_platforms)
            findings.append(
                Finding(
                    "presence",
                    syscall,
                    f"{syscall} is described as both present and absent for {where} -- "
                    "reconcile: a true contradiction only if the *same* implementation and "
                    "level both has and lacks it (a 6809/68k or Level I/II difference is legitimate)",
                    _dedup([(m.file, m.line) for m in contributors]),
                )
            )
    return findings


def _is_adjacent_transposition(a, b):
    """True when `a` becomes `b` by swapping one adjacent pair (manaul/manual)."""
    if len(a) != len(b):
        return False
    diffs = [i for i in range(len(a)) if a[i] != b[i]]
    return (
        len(diffs) == 2
        and diffs[1] == diffs[0] + 1
        and a[diffs[0]] == b[diffs[1]]
        and a[diffs[1]] == b[diffs[0]]
    )


def _suspected_tag(word, known_tags):
    """Return the tag `word` looks like a typo of, or None.

    Conservative: only a case variant or an adjacent transposition counts, so
    ordinary words one substitution from a tag (e.g. `Line` vs `Live`) are safe.
    """
    if word in known_tags:
        return None
    low = word.lower()
    for tag in known_tags:
        lt = tag.lower()
        if low == lt or _is_adjacent_transposition(low, lt):
            return tag
    return None


def check_tag_hygiene(text, filename, known_tags):
    """Backticked words that look like a confidence tag but are miswritten."""
    findings = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        for word in BACKTICK_WORD.findall(line):
            tag = _suspected_tag(word, known_tags)
            if tag:
                findings.append(
                    Finding("hygiene", None, f"`{word}` looks like a miswritten `{tag}` tag", [(filename, lineno)])
                )
    return findings


_FLAG_TOKEN = re.compile(r"`Flag`")
_FLAG_ABOUT = re.compile(r"tagged\s+`?Flag`?", re.I)


def scan_open_flags(text, filename, known_tags):
    """Every open `Flag` line, as a standing "investigate" worklist.

    Informational -- `Flag` is the convention's marker for a known, unresolved
    manual/runtime divergence. Line-level (not syscall-anchored) because flags
    also cover behaviours and layouts, not just individual calls. Skips flags
    narrated as resolved and the convention's own explanation of the tag.
    """
    if "Flag" not in known_tags:
        return []
    inventory = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        if not _FLAG_TOKEN.search(line) or _FLAG_RESOLVED.search(line) or _FLAG_ABOUT.search(line):
            continue
        snippet = " ".join(line.split())
        if len(snippet) > 110:
            snippet = snippet[:107] + "..."
        inventory.append(Finding("flag", None, snippet, [(filename, lineno)]))
    return inventory


def extract_doc_references(line):
    """Return every `something.md`-shaped token mentioned in `line`, backticked or bare."""
    return _DOC_TOKEN.findall(line)


def check_cross_references(files, known_basenames):
    """Flag an INDEX.md entry that names a file matching nothing in `known_basenames`.

    Scoped to `INDEX.md` files only -- the two skills' manifests are the one place
    a broken pointer breaks navigation; prose elsewhere routinely names files that
    live in a different repo (dogfood reports, `ROADMAP.md`) and is not in scope.
    Resolution is by basename: INDEX.md rows are written as bare names, tree-
    relative paths, or sibling-skill-qualified paths (`os9-dev/references/...`),
    and basename matching is the one rule that resolves all three without having
    to hand-parse "sibling X skill" prose to pick a path root.
    """
    findings = []
    for filename, text in files:
        if os.path.basename(filename) != INDEX_FILENAME:
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            for ref in extract_doc_references(line):
                base = os.path.basename(ref)
                if base not in known_basenames:
                    findings.append(
                        Finding(
                            "cross-ref",
                            None,
                            f"INDEX.md points to `{ref}`, no file named `{base}` was found",
                            [(filename, lineno)],
                        )
                    )
    return findings


def parse_memory_name(text):
    """Return a memory file's frontmatter `name:` value, or None if absent."""
    m = _FRONTMATTER_NAME.match(text)
    return m.group(1) if m else None


def check_orphaned_memory_links(files):
    """Flag a `[[name]]` link with no memory file whose frontmatter `name:` matches.

    `files` is a list of (filename, text) pairs covering every memory file, so the
    known-name set and the scan are both built from the same corpus in one pass.
    """
    known = {name for name in (parse_memory_name(text) for _, text in files) if name}
    findings = []
    for filename, text in files:
        for lineno, line in enumerate(text.splitlines(), start=1):
            for open_tick, link, close_tick in _MEMORY_LINK.findall(line):
                if open_tick == "`" and close_tick == "`":
                    continue
                if link not in known:
                    findings.append(
                        Finding(
                            "memory-link",
                            None,
                            f"[[{link}]] has no matching memory file (frontmatter name: {link})",
                            [(filename, lineno)],
                        )
                    )
    return findings


# --- driver ----------------------------------------------------------------

def collect_markdown(roots):
    """Return every `.md` file under the given roots, sorted for stable output."""
    files = []
    for root in roots:
        for dirpath, _dirs, names in os.walk(root):
            files.extend(os.path.join(dirpath, n) for n in names if n.endswith(".md"))
    return sorted(files)


def load_known_tags(files):
    """Parse the confidence-tag set from CONFIDENCE-TAGS.md among `files`."""
    for path in files:
        if os.path.basename(path) == CONFIDENCE_TAGS_FILE:
            with open(path, encoding="utf-8") as handle:
                return parse_known_tags(handle.read())
    raise SystemExit(f"{CONFIDENCE_TAGS_FILE} not found under scanned roots")


def _index_adjacent_files(roots):
    """SKILL.md/SOURCES.md one directory above each root -- INDEX.md's only
    non-references/ targets, named explicitly rather than re-walked for."""
    extra = []
    for root in roots:
        parent = os.path.dirname(os.path.normpath(root))
        for name in ("SKILL.md", "SOURCES.md"):
            path = os.path.join(parent, name)
            if os.path.isfile(path):
                extra.append(path)
    return extra


def run(roots):
    """Scan `roots`, returning (findings, inventory).

    `findings` are presence-contradiction + tag-hygiene + cross-reference issues
    (any means the run failed); `inventory` is the informational `Flag` worklist.
    Meta-docs are used for their tag set but never scanned as claim sources.
    """
    files = collect_markdown(roots)
    known = load_known_tags(files)
    known_basenames = {os.path.basename(p) for p in files + _index_adjacent_files(roots)}
    mentions, findings, inventory, doc_texts = [], [], [], []
    for path in files:
        display = os.path.relpath(path)
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        doc_texts.append((display, text))
        if os.path.basename(path) in META_DOCS:
            continue
        mentions.extend(find_mentions(text, display, known))
        findings.extend(check_tag_hygiene(text, display, known))
        inventory.extend(scan_open_flags(text, display, known))
    findings = check_presence_contradiction(mentions) + findings
    findings += check_cross_references(doc_texts, known_basenames)
    return findings, inventory


def _format(finding):
    where = ", ".join(f"{f}:{ln}" for f, ln in finding.locations)
    return f"  [{finding.check}] {finding.message}\n         {where}"


def collect_memory_files(memory_dir):
    """Return (filename, text) for every memory `.md` file under `memory_dir`."""
    files = []
    for dirpath, _dirs, names in os.walk(memory_dir):
        for name in sorted(names):
            if not name.endswith(".md"):
                continue
            path = os.path.join(dirpath, name)
            with open(path, encoding="utf-8") as handle:
                files.append((os.path.relpath(path), handle.read()))
    return files


def main(argv=None):
    """CLI entry: scan skill reference trees, print findings, return exit code.

    `--memory-dir DIR` additionally scans DIR's memory files for orphaned
    `[[name]]` links; the path is project-specific so it is never hardcoded.
    """
    argv = list(sys.argv[1:] if argv is None else argv)
    memory_dir = None
    if "--memory-dir" in argv:
        i = argv.index("--memory-dir")
        memory_dir = argv[i + 1]
        del argv[i : i + 2]
    here = os.path.dirname(os.path.abspath(__file__))
    roots = argv or [
        os.path.join(here, os.pardir, "os9-dev", "references"),
        os.path.join(here, os.pardir, "os9-systems-dev", "references"),
    ]
    findings, inventory = run(roots)
    if memory_dir:
        findings = findings + check_orphaned_memory_links(collect_memory_files(memory_dir))

    if findings:
        print(f"Doc-consistency findings ({len(findings)} -- investigate, neither runtime is an oracle):")
        for finding in findings:
            print(_format(finding))
    else:
        print("Doc-consistency: no presence/hygiene findings.")

    if inventory:
        print(f"\n`Flag` divergence inventory ({len(inventory)} unresolved -- for tracking):")
        for item in inventory:
            print(_format(item))

    for path in collect_markdown(roots):
        if os.path.basename(path) == CONFIDENCE_TAGS_FILE:
            with open(path, encoding="utf-8") as handle:
                baselines = verified_against(handle.read())
            if baselines:
                print("\n`Live` verified against:")
                for platform, identity in baselines:
                    print(f"  {platform}: {identity}")
            break

    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
