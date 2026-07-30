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
DIVERGENCE_FILENAME = "DIVERGENCES.md"

# The two installed skills, and the rule between them (README, "Layout"):
# shared content lives in os9-dev, which stands alone; os9-systems-dev may
# depend on it. Only os9-dev is named here because that direction is the one
# the rule fixes -- the check below is symmetric about *qualification*.
SKILL_DIRS = ("os9-dev", "os9-systems-dev")
# Docs that live at the repo root. They are review material: neither skill
# directory contains them, so a payload file citing one points at nothing once
# the skill is installed (symlinked) on its own.
ROOT_ONLY_DOCS = frozenset({"DIVERGENCES.md", "SOURCE-AUTHORITY.md", "README.md"})
# Per-skill manifests: each skill legitimately has its own copy, so a basename
# appearing in both skills is duplication only outside this set.
PER_SKILL_DOCS = frozenset({"INDEX.md", "SOURCES.md", "SKILL.md"})
# A register entry is defined by its `### D-NNN` heading; a claim cites it with
# an inline `DIVERGENCE D-NNN` marker (the warning glyph is not required here,
# so the check does not depend on an emoji surviving an edit).
_DIVERGENCE_HEADING = re.compile(r"^###\s+(D-\d+)", re.MULTILINE)
_DIVERGENCE_MARKER = re.compile(r"DIVERGENCE\s+(D-\d+)")
# `Flag` alone, or the combined form the convention prescribes when stronger
# evidence contradicts a manual -- one backtick span holding the higher tier
# plus Flag, e.g. `Source, Flag` (CONFIDENCE-TAGS.md, "Ordering"). Matching only
# the bare token silently under-reports the inventory.
_FLAG_TOKEN = re.compile(
    r"`(?:(?:Hearsay|Manual|Source|Live|Absent)\s*,\s*)*Flag`"
)

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

# One `SYMBOL $VALUE` binding as stated by one line of one doc.
Fact = namedtuple("Fact", "symbol value file line platform")

# One reported disagreement. `locations` are (file, line) pairs. Always neutral.
Finding = namedtuple("Finding", "check syscall message locations")


# --- parsing ---------------------------------------------------------------

def parse_known_tags(md):
    """Return the confidence-tag names defined in CONFIDENCE-TAGS.md's table.

    Parsed rather than hardcoded, so the known-tag set stays in sync with the doc.
    """
    return {m.group("tag") for m in (TAG_ROW.match(line) for line in md.splitlines()) if m}


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


# A calendar date anywhere in a reference file. `CONFIDENCE-TAGS.md` defines the
# whole notation and gives dates no role in it, so one here is always either a
# session stamp or the residue of a narrated correction -- both of which the
# standing rule keeps out of user-facing files. Caught mechanically because the
# editorial rule alone did not hold: dates drifted into 17 places across 7 files,
# including two standing in for the implementation inside a `Live` tag, which the
# tag spec calls a defect outright.
_SESSION_DATE = re.compile(r"\b(?:19|20)\d{2}-\d{2}-\d{2}\b")


def check_no_session_dates(text, filename, known_tags):
    """Calendar dates in a reference file -- session stamps, not reader content."""
    del known_tags
    findings = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        for match in _SESSION_DATE.finditer(line):
            findings.append(
                Finding(
                    "session-date",
                    None,
                    f"`{match.group(0)}` -- a reference file carries no dates; "
                    "state the fact, and put session state in `maintainer/`",
                    [(filename, lineno)],
                )
            )
    return findings


# --- tag form ---------------------------------------------------------------
# `CONFIDENCE-TAGS.md` fixes one written form: an inline `` `Tag` ``, and for
# `Live` a parenthesised implementation after it. Three malformations turned up
# in one editorial pass and each is mechanical: a tag wrapped in bold (renders
# differently and reads as emphasis, not notation), a qualifier repeated, and a
# comma where the parentheses belong.
_TAG_BOLD = re.compile(r"\*\*`(?P<tag>Live|Manual|Source|Hearsay|Absent|Flag)`\*\*")
_TAG_DOUBLED_QUAL = re.compile(r"\((?P<q>[A-Za-z0-9 ,+/-]+)\)\*{0,2} \((?P=q)\)")
_TAG_COMMA_QUAL = re.compile(r"`Live`,\s*(?:os9exec|NitrOS-9|OS-9)")


def check_tag_form(text, filename, known_tags):
    """Malformed confidence tags: bold-wrapped, doubled qualifier, comma qualifier."""
    del known_tags
    if os.path.basename(filename) == CONFIDENCE_TAGS_FILE:
        return []  # the convention's own file quotes these forms to define them
    findings = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        for m in _TAG_BOLD.finditer(line):
            findings.append(
                Finding(
                    "tag-form", None,
                    f"`{m.group('tag')}` is wrapped in bold -- a tag is notation, write it plain",
                    [(filename, lineno)],
                )
            )
        for m in _TAG_DOUBLED_QUAL.finditer(line):
            findings.append(
                Finding(
                    "tag-form", None,
                    f"qualifier `({m.group('q')})` is repeated -- name the implementation once",
                    [(filename, lineno)],
                )
            )
        if _TAG_COMMA_QUAL.search(line):
            findings.append(
                Finding(
                    "tag-form", None,
                    "`Live`, <impl> -- the implementation goes in parentheses: `Live` (impl)",
                    [(filename, lineno)],
                )
            )
    return findings


_TAG_TOKEN = re.compile(r"`(?:Live|Manual|Source|Hearsay|Absent|Flag)`")


def check_tags_in_code(text, filename, known_tags):
    """A confidence tag inside a fenced code block.

    A tag asserts something about a claim; inside a fence it instead asserts
    that the surrounding *code* was run, which is a claim the fence cannot
    carry -- and the one real instance sat in a trailing comment that the
    language does not even accept, so the lines it vouched for could not have
    compiled. Tags belong in prose beside the block.
    """
    del known_tags
    if os.path.basename(filename) == CONFIDENCE_TAGS_FILE:
        return []
    findings = []
    in_fence = False
    for lineno, line in enumerate(text.splitlines(), start=1):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence and _TAG_TOKEN.search(line):
            findings.append(
                Finding(
                    "tag-in-code", None,
                    "confidence tag inside a code fence -- move it to prose beside the block",
                    [(filename, lineno)],
                )
            )
    return findings


# --- blanket tags -----------------------------------------------------------
# A blanket tag may set a FLOOR, never a CEILING. "`Manual` throughout" cannot
# hide anything: it understates at worst. "Everything below is `Live`" is a
# claim about every row the author never enumerated -- and both instances found
# in one pass were covering a row nobody could have run (a destructive debugger
# command, and an opcode table read out of source). So a blanket naming a
# verified tier must say what it excludes.
_BLANKET = re.compile(
    r"(?:everything|every\s+(?:command|claim|entry|row|fact|item)|all\s+(?:claims|entries|rows))"
    r"[^.\n]{0,80}?`(?P<tag>Live|Source)`"
    r"|`(?P<tag2>Live|Source)`\s+throughout",
    re.I,
)
_BLANKET_EXCEPTION = re.compile(
    r"\b(except|unless|other than|apart from|aside from|save for|but the)\b", re.I
)


def check_blanket_tags(text, filename, known_tags):
    """A span-wide `Live`/`Source` claim with no stated exception."""
    del known_tags
    if os.path.basename(filename) == CONFIDENCE_TAGS_FILE:
        return []
    findings = []
    lines = text.splitlines()
    for lineno, line in enumerate(lines, start=1):
        m = _BLANKET.search(line)
        if not m:
            continue
        # the exception clause routinely wraps onto the next line or two
        window = " ".join(lines[lineno - 1 : lineno + 2])
        if _BLANKET_EXCEPTION.search(window):
            continue
        tag = m.group("tag") or m.group("tag2")
        findings.append(
            Finding(
                "blanket-tag", None,
                f"blanket `{tag}` over a span with no stated exception -- a blanket tag may "
                "set a floor, never a ceiling; name what it excludes or tag rows inline",
                [(filename, lineno)],
            )
        )
    return findings


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


# An OS-9 symbol carrying a documented numeric offset/code: a capitalised name
# with an internal `_`, `$` or `.` (PD_COUNT, M$Opt, F$Link, SS.Size, P$SigLvl).
# The internal separator is what keeps ordinary Capitalised prose words out.
_SYMBOL = r"[A-Z][A-Za-z0-9]*[_$.][A-Za-z0-9_$.]*[A-Za-z0-9]"
# `SYM` followed by its hex value, allowing the notations this corpus actually
# uses: a table cell (`| SYM | $30`), prose (`SYM $00`, `SYM, offset $80`,
# `SYM at $2E`), or a parenthesised aside (`SYM ($1E)`). The connector set is
# deliberately closed -- arbitrary text between name and number would let an
# unrelated nearby value bind to the symbol.
_FACT = re.compile(
    r"`?(?P<sym>" + _SYMBOL + r")`?"
    r"[ \t]*(?:[|,(=:]|--|—)?[ \t]*"
    r"(?:offset[ \t]+|at[ \t]+)?"
    r"`?(?P<val>\$[0-9A-Fa-f]{1,8})`?"
)
# Wording that means "this number is wrong" -- the corpus quotes bad values on
# purpose (an OCR misread, a manual's own typo) to warn the reader off them.
# Such a line states a value it is explicitly disowning, so it is not a claim.
_DISOWNED = re.compile(
    r"\b(scan error|OCR|typo|misread|mis-read|damaged|garbl|obsolete|stale|"
    r"incorrect|not a distinct field)\b",
    re.I,
)


def normalise_hex(value):
    """Return a canonical form of a `$HH` literal, so `$0A`, `$a` and `$A` agree."""
    digits = value.lstrip("$").upper().lstrip("0")
    return digits or "0"


def extract_shared_facts(text, filename):
    """Return a Fact per `SYMBOL $VALUE` binding stated in `text`.

    Skips lines that carry a `Flag` tag or a `DIVERGENCE` marker (a recorded,
    deliberate disagreement is not drift) and lines whose wording disowns the
    number they quote -- see `_DISOWNED`.
    """
    platform = platform_of(filename)
    facts = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        if _FLAG_TOKEN.search(line) or _DIVERGENCE_MARKER.search(line) or _DISOWNED.search(line):
            continue
        for m in _FACT.finditer(line):
            facts.append(
                Fact(m.group("sym"), normalise_hex(m.group("val")), filename, lineno, platform)
            )
    return facts


def _compatible(a, b):
    """True when two platforms can describe the same system ("neutral" fits both)."""
    return a == b or "neutral" in (a, b)


def check_shared_facts(facts):
    """Flag a symbol given two different values by docs that describe one platform.

    A fact repeated across files is a maintenance hazard: `PD_COUNT` appears in
    three files, `M$Parity` in two, and nothing until now checked that they still
    agree. Scoped by platform the same way `check_presence_contradiction` is, so a
    6809 call code legitimately differing from its 68k namesake is not a finding.
    """
    grouped = {}
    for fact in facts:
        grouped.setdefault(fact.symbol, []).append(fact)

    findings = []
    for symbol, group in sorted(grouped.items()):
        by_value = {}
        for fact in group:
            by_value.setdefault(fact.value, []).append(fact)
        if len(by_value) < 2:
            continue
        conflicting = [
            (v1, v2)
            for i, v1 in enumerate(sorted(by_value))
            for v2 in sorted(by_value)[i + 1 :]
            if any(_compatible(a.platform, b.platform) for a in by_value[v1] for b in by_value[v2])
        ]
        if not conflicting:
            continue
        shown = ", ".join(f"${v}" for v in sorted(by_value))
        findings.append(
            Finding(
                "shared-fact",
                symbol,
                f"{symbol} is documented as {shown} in different places -- "
                "reconcile, or mark the disowned value (`Flag`, or wording that "
                "says which reading is wrong)",
                _dedup([(f.file, f.line) for f in group]),
            )
        )
    return findings


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


def collect_doc_texts(roots):
    """Return (display path, text) for every markdown file under `roots`."""
    texts = []
    for path in collect_markdown(roots) + _index_adjacent_files(roots):
        with open(path, encoding="utf-8") as handle:
            texts.append((os.path.relpath(path), handle.read()))
    return texts


def check_qualified_references(files, known_paths):
    """Flag a `dir/file.md` pointer whose directory doesn't match where the file lives.

    Runs over every payload file, not just INDEX.md, and stays quiet on other
    repos' documents because a reference is only judged when its basename is one
    we actually own. What it catches is the stale pointer left behind when a file
    moves between reference directories: the target still exists, so
    `check_cross_references` sees nothing wrong, but the path sends the reader to
    the wrong place. Bare basenames are skipped -- resolving those is
    `check_cross_references`' job.
    """
    by_base = {}
    for path in known_paths:
        normalised = path.replace(os.sep, "/")
        by_base.setdefault(os.path.basename(normalised), set()).add(normalised)
    findings = []
    for filename, text in files:
        for lineno, line in enumerate(text.splitlines(), start=1):
            for ref in extract_doc_references(line):
                ref_path = ref.replace(os.sep, "/")
                if "/" not in ref_path:
                    continue
                candidates = by_base.get(os.path.basename(ref_path))
                if not candidates:
                    continue
                if any(p == ref_path or p.endswith("/" + ref_path) for p in candidates):
                    continue
                actual = ", ".join(sorted(candidates))
                findings.append(
                    Finding(
                        "stale-path",
                        None,
                        f"`{ref}` names a directory it does not live in; it is at {actual}",
                        [(filename, lineno)],
                    )
                )
    return findings


DUPLICATE_MIN_WORDS = 25
# 5-word shingles: long enough that unrelated prose scores ~0, short enough that a
# single substituted word doesn't invalidate a whole sentence's worth of shingles.
DUPLICATE_SHINGLE = 5
DUPLICATE_THRESHOLD = 0.5
_MARKUP = re.compile(r"[`*_>#\[\]()]")


def extract_paragraphs(text):
    """Yield (line number, normalised words) for prose paragraphs worth comparing.

    Fenced code blocks, table rows, and headings are skipped: a worked example
    reproduced beside its output, and table rows sharing a column vocabulary, are
    both *expected* to repeat and would drown any real finding.
    """
    paragraphs, buffer, start, fenced = [], [], 0, False
    def flush():
        if buffer:
            words = _MARKUP.sub(" ", " ".join(buffer)).lower().split()
            if len(words) >= DUPLICATE_MIN_WORDS:
                paragraphs.append((start, words))
        buffer.clear()

    for lineno, line in enumerate(text.splitlines(), start=1):
        if line.lstrip().startswith("```"):
            flush()
            fenced = not fenced
            continue
        if fenced or not line.strip() or line.lstrip().startswith(("|", "#")):
            flush()
            continue
        if not buffer:
            start = lineno
        buffer.append(line.strip())
    flush()
    return paragraphs


def _shingles(words):
    if len(words) <= DUPLICATE_SHINGLE:
        return {tuple(words)}
    return {tuple(words[i : i + DUPLICATE_SHINGLE]) for i in range(len(words) - DUPLICATE_SHINGLE + 1)}


def find_duplicate_paragraphs(files, threshold=DUPLICATE_THRESHOLD):
    """Report prose paragraphs that recur near-verbatim in two *different* files.

    Advisory only -- never a finding, so it cannot fail a commit. Some repetition
    across these skills is deliberate (a trap restated where its reader will meet
    it is this project's stated editorial goal), so every hit is a judgement call
    for a human, not a defect. Similarity is Jaccard overlap of word shingles,
    which tolerates the small edits that make two copies drift apart.
    """
    entries = []
    for filename, text in files:
        for lineno, words in extract_paragraphs(text):
            entries.append((filename, lineno, _shingles(words), " ".join(words)))
    reports = []
    for i, (file_a, line_a, sh_a, text_a) in enumerate(entries):
        for file_b, line_b, sh_b, _ in entries[i + 1 :]:
            if file_a == file_b:
                continue
            union = sh_a | sh_b
            if not union:
                continue
            score = len(sh_a & sh_b) / len(union)
            if score >= threshold:
                excerpt = text_a[:60] + ("..." if len(text_a) > 60 else "")
                reports.append(
                    Finding(
                        "duplicate",
                        None,
                        f"{int(score * 100)}% overlap between `{file_a}` and `{file_b}`: \"{excerpt}\"",
                        [(file_a, line_a), (file_b, line_b)],
                    )
                )
    return reports


def skill_of(path):
    """Return which skill directory `path` sits under, or None if neither."""
    parts = path.replace(os.sep, "/").split("/")
    return next((part for part in parts if part in SKILL_DIRS), None)


def check_skill_boundaries(files):
    """Flag references that break when a skill is installed on its own.

    Each skill is symlinked into `~/.claude/skills/` by itself, so anything it
    cites has to be resolvable from inside that one directory. Two ways that
    breaks, both of which have actually happened here:

    - **A root doc.** `SOURCE-AUTHORITY.md` and friends live beside the skills,
      not inside them. Four payload files pointed at `SOURCE-AUTHORITY.md`
      before this check existed; installed, none of them could resolve it.
    - **A bare sibling filename.** `6809-level2-mmu.md` lives in
      os9-systems-dev; written unqualified in an os9-dev file it names nothing
      a reader of that skill can find. Naming the owning skill fixes it, so the
      check looks for that name on the citing line or the one above (the
      qualifier routinely wraps onto the previous line).

    Also flags a non-manifest basename present in *both* skills: shared content
    is supposed to live in os9-dev alone, with the sibling depending on it.

    Deliberately mechanical -- it checks that a citation *resolves*, not whether
    it is a dependency or a scope marker ("drivers are the sibling's job"),
    which no regex can tell apart. `files` is (filename, text) pairs.
    """
    owners = {}
    for filename, _text in files:
        skill = skill_of(filename)
        if skill:
            owners.setdefault(os.path.basename(filename), set()).add(skill)

    findings = []
    for basename, skills in sorted(owners.items()):
        if len(skills) > 1 and basename not in PER_SKILL_DOCS:
            findings.append(
                Finding(
                    "skill-boundary",
                    None,
                    f"`{basename}` exists in both skills -- shared content belongs in "
                    "os9-dev alone, with os9-systems-dev citing it",
                    sorted((f, 0) for f, _ in files if os.path.basename(f) == basename),
                )
            )

    for filename, text in files:
        skill = skill_of(filename)
        if not skill:
            continue
        lines = text.splitlines()
        for lineno, line in enumerate(lines, start=1):
            context = (lines[lineno - 2] if lineno >= 2 else "") + " " + line
            for ref in extract_doc_references(line):
                base = os.path.basename(ref)
                if base in ROOT_ONLY_DOCS:
                    findings.append(
                        Finding(
                            "skill-boundary",
                            None,
                            f"`{base}` lives at the repo root, outside the installed "
                            "skill -- state the fact inline instead of pointing at it",
                            [(filename, lineno)],
                        )
                    )
                    continue
                elsewhere = owners.get(base, set()) - {skill}
                if not elsewhere or skill in owners.get(base, set()):
                    continue
                other = sorted(elsewhere)[0]
                if other not in context:
                    findings.append(
                        Finding(
                            "skill-boundary",
                            None,
                            f"`{base}` lives in `{other}`; name the skill when citing "
                            "across the split, or this resolves to nothing",
                            [(filename, lineno)],
                        )
                    )
    return findings


def check_divergence_links(files, register_text):
    """Flag any break in the two-way link between `DIVERGENCES.md` and the claims.

    A divergence is only useful if the reader of the *claim* sees it. So every
    **open** `D-NNN` defined in the register must be cited by at least one
    inline `DIVERGENCE D-NNN` marker in a reference file, and every inline
    marker must name an ID the register actually defines. Either break is a
    finding: an uncited open entry is a divergence filed where nobody reading
    the claim will meet it, and an undefined marker is a warning pointing at
    nothing.

    A **closed** entry (Status: withdrawn / resolved) is archival -- the claim
    it once concerned is now correct, so forcing a warning marker onto that row
    would be wrong. Closed entries therefore need no inline marker; a marker may
    still cite one (the ID stays defined), it just isn't required.

    `register_text` is DIVERGENCES.md's contents, or None when the register is
    absent -- in which case any inline marker is dangling by definition.
    """
    findings = []
    defined = set(_DIVERGENCE_HEADING.findall(register_text or ""))
    open_ids = _open_divergences(register_text or "")

    cited = {}
    for filename, text in files:
        if os.path.basename(filename) == DIVERGENCE_FILENAME:
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            for ident in _DIVERGENCE_MARKER.findall(line):
                cited.setdefault(ident, []).append((filename, lineno))

    for ident, locations in sorted(cited.items()):
        if ident not in defined:
            findings.append(
                Finding(
                    "divergence",
                    None,
                    f"inline marker cites `{ident}`, which {DIVERGENCE_FILENAME} does not define",
                    locations,
                )
            )

    for ident in sorted(open_ids - set(cited)):
        findings.append(
            Finding(
                "divergence",
                None,
                f"`{ident}` is open in {DIVERGENCE_FILENAME} but no reference file "
                "carries its inline marker -- a reader of the claim would never see it",
                [(DIVERGENCE_FILENAME, 0)],
            )
        )
    return findings


def _open_divergences(register_text):
    """Return the set of `D-NNN` IDs whose entry is not withdrawn/resolved.

    Splits the register at `### D-NNN` headings and reads each entry's
    `**Status:**` line; an entry counts as open unless that status contains
    `withdrawn` or `resolved` (case-insensitive). A missing status is treated
    as open -- the safe default, since it still demands an inline warning.
    """
    open_ids = set()
    parts = re.split(r"^###\s+(D-\d+)", register_text, flags=re.MULTILINE)
    # parts = [preamble, id1, body1, id2, body2, ...]
    for ident, body in zip(parts[1::2], parts[2::2]):
        status = ""
        m = re.search(r"\*\*Status:\*\*\s*(.+)", body)
        if m:
            status = m.group(1).lower()
        if "withdrawn" not in status and "resolved" not in status:
            open_ids.add(ident)
    return open_ids


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
                            "orphan-memory-link",
                            None,
                            f"orphaned [[{link}]] - no memory file has that frontmatter name:",
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


def run(roots, register_text=None):
    """Scan `roots`, returning (findings, inventory).

    `register_text` is DIVERGENCES.md's contents. It is passed in rather than
    discovered because the register lives at the repo root while `roots` are the
    two `references/` trees -- the inline markers are inside those trees, the
    entries they cite are not. When omitted, a register found among the scanned
    files is used, so a caller can point everything at one directory.

    `findings` are presence-contradiction + tag-hygiene + cross-reference issues
    (any means the run failed); `inventory` is the informational `Flag` worklist.
    Meta-docs are used for their tag set but never scanned as claim sources.
    """
    files = collect_markdown(roots)
    known = load_known_tags(files)
    adjacent = _index_adjacent_files(roots)
    known_basenames = {os.path.basename(p) for p in files + adjacent}
    mentions, facts, findings, inventory, doc_texts = [], [], [], [], []
    # SKILL.md/SOURCES.md are read for boundary and cross-reference purposes but
    # never scanned as claim sources -- they are entry points and manifests, and
    # the boundary check is precisely the one that has to see them (the first
    # dangling root-doc reference this check caught lived in SKILL.md).
    for path in files + adjacent:
        display = os.path.relpath(path)
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        doc_texts.append((display, text))
        if path in adjacent or os.path.basename(path) in META_DOCS:
            continue
        mentions.extend(find_mentions(text, display, known))
        facts.extend(extract_shared_facts(text, display))
        findings.extend(check_tag_hygiene(text, display, known))
        findings.extend(check_no_session_dates(text, display, known))
        findings.extend(check_tag_form(text, display, known))
        findings.extend(check_tags_in_code(text, display, known))
        findings.extend(check_blanket_tags(text, display, known))
        inventory.extend(scan_open_flags(text, display, known))
    findings = check_presence_contradiction(mentions) + check_shared_facts(facts) + findings
    findings += check_cross_references(doc_texts, known_basenames)
    findings += check_qualified_references(
        doc_texts, {os.path.relpath(p) for p in files + adjacent}
    )
    findings += check_skill_boundaries(doc_texts)
    if register_text is None:
        register_text = next(
            (text for name, text in doc_texts if os.path.basename(name) == DIVERGENCE_FILENAME),
            None,
        )
    findings += check_divergence_links(doc_texts, register_text)
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

    `--no-inventory` suppresses the informational `Flag` worklist, leaving only
    findings. For the pre-commit hook: on a failure the inventory's ~16 lines
    would otherwise sit between the finding and the prompt, scrolling the one
    thing the author needs to read off the top.
    """
    argv = list(sys.argv[1:] if argv is None else argv)
    show_inventory = "--no-inventory" not in argv
    show_duplicates = "--duplicates" in argv
    argv = [a for a in argv if a not in ("--no-inventory", "--duplicates")]
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
    register_path = os.path.join(here, os.pardir, DIVERGENCE_FILENAME)
    register_text = None
    if os.path.exists(register_path):
        with open(register_path, encoding="utf-8") as handle:
            register_text = handle.read()
    findings, inventory = run(roots, register_text)
    if memory_dir:
        findings = findings + check_orphaned_memory_links(collect_memory_files(memory_dir))

    if findings:
        print(f"Doc-consistency findings ({len(findings)} -- investigate, neither runtime is an oracle):")
        for finding in findings:
            print(_format(finding))
    else:
        print("Doc-consistency: no presence/hygiene findings.")

    if show_duplicates:
        duplicates = find_duplicate_paragraphs(collect_doc_texts(roots))
        if duplicates:
            print(f"\nNear-verbatim paragraphs ({len(duplicates)} -- advisory, some repetition is deliberate):")
            for item in duplicates:
                print(_format(item))
        else:
            print("\nNear-verbatim paragraphs: none above threshold.")

    if inventory and show_inventory:
        print(f"\n`Flag` divergence inventory ({len(inventory)} unresolved -- for tracking):")
        for item in inventory:
            print(_format(item))

    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
