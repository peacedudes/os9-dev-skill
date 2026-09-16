# Skill-doc consistency checker — design

Repo: `~/Developer/os9/os9-dev-skill` (os9-dev + os9-systems-dev; symlinked
into `~/.claude/skills/`). Entry: `check_doc_consistency.py`. Run from the
repo root:

```
python3 tools/check_doc_consistency.py            # scan both skills' references/
python3 tools/check_doc_consistency.py <dir>...   # scan given roots
python3 tools/check_doc_consistency.py --memory-dir <dir>  # + orphaned [[memory]] links
python3 -m unittest discover -s tools/tests       # the test suite (stdlib, no pytest)
```

**Scan both skills together, or cross-references false-positive.** The two
skills point at each other's files on purpose (os9-dev's INDEX.md cites
`6809-level2-mmu.md`, which lives in os9-systems-dev — a scope marker, not a
dependency; shared content lives in os9-dev, see README). Narrowing a run to one
root — `... check_doc_consistency.py os9-dev` — reports those legitimate
pointers as broken cross-refs. The no-arg form scans both and is what a
clean-run claim must be based on.

Exit status is nonzero if there are any presence/hygiene **findings**; the
`Flag` **inventory** is informational and never fails the run.
`--no-inventory` suppresses the inventory, leaving findings only.

## Pre-commit hook

`hooks/pre-commit` runs the checker and the test suite before every commit and
rejects the commit if either fails. Both together take well under a second, so
it always runs rather than trying to guess which edits matter.

Enable it once per clone — the hook is tracked, but which hooks directory git
consults is local config:

```
git config core.hooksPath tools/hooks
```

Silent when green; on a failure it prints the findings and stops, having
committed nothing. `git commit --no-verify` bypasses it for the one commit.
The checker is invoked with `--no-inventory` there: on a failure the ~16-line
`Flag` worklist would otherwise sit between the finding and the prompt and
scroll the one line the author needs off the top.

## Problem

Skill-doc claims about OS-9 system calls can drift out of sync across files.
Motivating case: two docs asserted "os9exec has no `I$Dup`" while the 68k
syscall table had `I$Dup` `Live`-confirmed working — found by luck, not design.

## Guiding truth: neither runtime is an oracle

The 6809 (NitrOS-9) and 68k (os9exec) are **independent implementations of a
shared design on different hardware — not one emulator ported to two machines.**
The 68k derives from the 6809 but has calls the 6809 lacks; within the 6809,
Level I and Level II differ (MMU hardware). Both are reverse-engineered clones,
wrong in minor cases. Consequences the checker honours:

- A call present on one platform/level and absent on another is a **legitimate
  difference, not a contradiction.** Only the *same* implementation at the *same*
  level both having and lacking a call is a real contradiction.
- Output is **neutral**: "reconcile / investigate which is right", never "X is
  authoritative, fix Y".

## Anchor and platform

Every `F$…` / `I$…` token is an anchor (`\b[FI]\$[A-Za-z][A-Za-z0-9]+\b`). Each
doc's platform comes from its path: `references/6809/…` → 6809,
`references/68k/…` → 68k, everything else → **neutral** (speaks to both). An
absence clause that names a platform in prose ("6809 has no `F$STrap`",
"os9exec…") overrides the path for that claim.

## Key subtlety: tags are evidence strength, not presence

Confidence tags (`Hearsay < Manual < Source < Live`, plus `Absent`/`Flag`) say
how strong the evidence is, **not** whether the call exists. You can `Live`-
observe an *absence* ("`Live` — FAILS, `E$UnkSvc`, unimplemented"). So presence
is read from specific wording:

- **absent** if: an `Absent` tag on the subject; or the subject is `Live` **and**
  the line says `unimplemented` / `E$UnkSvc` (a mere "fails E$PNNF" is an
  error-path return of a call that *exists* — present, not absent); or an
  explicit bound phrase ("has no `X`", "no `X`", "`X` … unimplemented/absent").
- **present** if: "does implement `X`" / "`X` is implemented"; or the subject
  carries `Live` without an unimplemented marker.
- **none** otherwise.

The known-tag set is **parsed from `CONFIDENCE-TAGS.md`** (single source of truth).

## Subject rule

In a markdown table row (`| … |`) the **subject** is the call in the first
column; tag-based presence attaches only to it. A call merely referenced in
another row's notes ("the name was `F$Load`ed", "same as `F$Fork`") is *not* a
claim about that call — otherwise a `Live`/failure marker leaks onto every call
named nearby. Explicit bound phrases still count for any call, subject or not,
but never bind across clause punctuation (`,;:()`), so a later clause's
"unimplemented" cannot attach to an earlier call.

## Checks

1. **Presence contradiction** — per platform (6809, 68k; neutral applies to
   both), a call asserted *present* by one location and *absent* by another.
   Cross-platform differences never conflict. Fails the run.
2. **Tag hygiene** — a backticked word that looks like a miswritten confidence
   tag (case variant like `LIVE`, or an adjacent transposition like `Manaul`).
   Conservative: general edit-distance-1 is avoided so real words one
   substitution from a tag (`Line` vs `Live`) don't false-flag. Fails the run.
3. **Open-`Flag` inventory** — every line carrying an open `Flag`, as a standing
   "investigate" worklist. Line-level (flags cover behaviours/layouts, not just
   calls). Skips flags narrated as resolved ("`Flag` resolved") and the
   convention's own explanation ("tagged `Flag`"). Informational only.
4. **Cross-reference integrity** — an `INDEX.md` row naming a `.md` file that
   doesn't exist. Scoped to `INDEX.md` only: prose elsewhere in the corpus
   routinely names files that live in a different repo entirely (dogfood
   reports under `os9exec-git_code/test/`, that repo's gitignored
   `ROADMAP.md`) and scanning them would false-positive on legitimate
   cross-repo mentions — exactly the "fragile general-prose claim-matching"
   this checker deliberately avoids. Resolution is **by basename**: `INDEX.md`
   rows are written as bare names, tree-relative paths, or sibling-skill-
   qualified paths (`os9-dev/references/CONFIDENCE-TAGS.md`), and basename
   matching is the one rule that resolves all three without hand-parsing
   "sibling X skill" prose to pick a path root. The known-basename set adds
   each root's sibling `SKILL.md`/`SOURCES.md` explicitly (`INDEX.md`'s only
   non-`references/` targets) rather than re-walking the whole skill tree.
   Fails the run.
5. **Orphaned `[[memory]]` link** — a wiki-style `[[name]]` cross-link (the
   auto-memory system's own linking convention, `~/.claude/projects/*/memory/`)
   with no memory file whose frontmatter `name:` matches. Opt-in via
   `--memory-dir <dir>` since that path is project- and machine-specific and
   is never hardcoded into the tool. A `` `[[name]]` `` wrapped in backticks
   is read as quoting the convention itself (as this very sentence in the
   plan does), not as a real link, and is skipped — same idea as check 3's
   "tagged `Flag`" self-reference guard. Fails the run when active.

6. **Shared-fact agreement** — one OS-9 symbol documented with two different
   hex values by files that describe the same platform. A fact repeated across
   files is a maintenance hazard the corpus had no guard for: `M$Mode`,
   `M$Opt`, `M$FMgr` and `M$DevCon` are each stated in three files
   (`memory-and-io.md`, `device-drivers.md`, `file-managers.md`), and
   `INDEX.md` previously handled this by *asking the human to remember* to
   cross-check. Platform-scoped exactly like check 1, so a 6809 call code
   legitimately differing from its 68k namesake is not a finding. Fails the run.

   A symbol is recognised only with an internal `_`, `$` or `.` (`PD_COUNT`,
   `M$Opt`, `SS.Size`) — that separator is what keeps ordinary capitalised
   prose out. The connector between name and value is a **closed** set (table
   pipe, comma, paren, `=`, `:`, `offset`, `at`), because arbitrary text
   between the two would let an unrelated nearby number bind to the symbol.
   Values are normalised (`$0A` = `$a` = `$A`) so notation is never mistaken
   for disagreement.

   Three kinds of line are skipped, because each states a number it is not
   claiming: one tagged `Flag`, one carrying a `DIVERGENCE D-NNN` marker (a
   retired convention — the skip rule is kept as harmless dead code rather
   than re-tested away), and
   one whose wording disowns the value it quotes (`scan error`, `OCR`, `typo`,
   `misread`, `garbl`, `obsolete`, `stale`, `incorrect`). The corpus really
   does quote bad values on purpose — `module-format.md` prints `M$Parity` at
   `$28` specifically to warn the reader that that scan is wrong.

7. **Skill boundary** — a citation that stops resolving once a skill is
   installed on its own. Each skill is symlinked into `~/.claude/skills/`
   individually, so anything it names must be findable from inside that one
   directory. Three ways that breaks, all of which really happened:
   a **root doc** (`SOURCE-AUTHORITY.md`, `DIVERGENCES.md`, `README.md` sit
   beside the skills, not in them — four payload files pointed at
   `SOURCE-AUTHORITY.md` and none could resolve it once installed); a **bare
   sibling filename** (`6809-level2-mmu.md` written unqualified in an os9-dev
   file names nothing an os9-dev reader can find); and **shared content
   duplicated into both skills**, which the layout rule puts in os9-dev alone.
   Fails the run.

   The sibling test looks for the owning skill's name on the citing line **or
   the one above**, because the qualifier routinely wraps ("Full mechanism:
   `os9-systems-dev`" / "skill's `kernel-internals.md`"). `INDEX.md`,
   `SOURCES.md` and `SKILL.md` are exempt from the duplication rule — each
   skill legitimately has its own.

   Deliberately mechanical: it checks that a citation **resolves**, not whether
   it is a dependency or a scope marker ("drivers are the sibling's job"). No
   regex separates those, and os9-dev names the sibling legitimately and often.
   This is the one check that must see `SKILL.md`/`SOURCES.md`, so `run()`
   reads them into the doc set — they are still never scanned as claim sources.

6. **Stale directory-qualified pointers** (`check_qualified_references`). Where
   check 4 asks "does this file exist at all" and is scoped to `INDEX.md`, this
   asks "is the path right" and runs over **every** payload file. A reference
   is judged only when its basename is one we own, so prose naming another
   repo's document (`dogfood-report-*.md`, `ROADMAP.md`) is skipped rather than
   false-positived — which is what confined check 4 to `INDEX.md` in the first
   place. Bare basenames are check 4's job and are ignored here. Catches the
   pointer left behind when a file moves between reference directories: the
   target still exists, so check 4 stays silent, but the reader is sent to the
   wrong place.

**Near-verbatim paragraphs** (`find_duplicate_paragraphs`) is *not* a check —
it is an opt-in report behind `--duplicates`, and never affects exit status.
Repetition across these skills is often deliberate (restating a trap where its
reader will meet it is this project's stated editorial goal), so every hit is a
judgement call for a human. Jaccard overlap of 5-word shingles over prose
paragraphs of ≥25 words, threshold 0.5, cross-file only; fenced code, table
rows and headings are skipped because a worked example beside its output, and
table rows sharing a column vocabulary, are expected to repeat. At the time of
writing the corpus scores **zero hits even at 0.25** across 710 comparable
paragraphs — verified as a real result, not a blind detector, by planting an
edited copy of a real 867-word paragraph and confirming it scores 97%.

Meta-docs (`CONFIDENCE-TAGS.md`, `VERIFICATION-BACKLOG.md`, `INDEX.md`,
`SOURCES.md`) are excluded from checks 1–3 (used only for their tag set) but
`INDEX.md` is exactly what check 4 scans — they quote calls as examples but
`INDEX.md`'s file-pointers are not "examples," they're the navigation table.

## A second tool: `check_claim_coupling.py` (advisory, not a gate)

**The failure it exists for is not a wrong value, it is a stale duplicate.** A
fact gets measured again, the file being edited is corrected carefully, and an
older statement of the same fact is left standing somewhere else. `check_shared_facts`
above catches the value-level form (`SYMBOL $VALUE` given two values). It cannot
catch the form that actually bit this corpus: `cpp` "bus-errors at 513
characters" in one file while another had just established the limit is **not a
fixed number**. Both files quoted the same digits. Nothing numeric disagreed —
the claims disagreed about the *shape* of the fact.

So this tool does not attempt to decide agreement. Given a commit (or the staged
index) it reports **which other files make claims about the same subjects**, and
hands the judgement back. A changed line is claim-bearing only if it carries a
quantity or limit wording; a bare mention is not a claim, and treating every
mention as one is what makes a check noisy enough to be switched off.

**Why advisory and not a gate.** It reasons about adjacency, so it can only ever
be a prompt. Per the false-positive rule above, a gate that blocks on a guess is
one people learn to bypass — and a bypassed gate protects nothing. It prints and
exits 0. Its *tests* are a gate; its findings are not.

**Two limits worth knowing before trusting it:**

- **It works per-commit, not corpus-wide.** A whole-tree sweep grouping every
  claim by subject was tried and is useless: common identifiers (`dir`, `copy`,
  `load`, `ident`) carry claims in seven to nine files each, so everything
  couples to everything. Starting from what changed is what makes the subject set
  small enough to be meaningful.
- **It matches on blocks, not lines, and that was a bug first.** The corpus
  hard-wraps prose, so a subject and its quantity routinely sit on different
  physical lines — the real stale claim read "Microware `cpp`" / "bus-errors at
  513 characters" across a break. The first implementation matched line by line,
  passed its own unit tests, and **silently failed the historical case it was
  built for**. Only running it against the tree as it stood at that commit
  exposed it. `test_finds_a_claim_whose_subject_and_quantity_are_on_different_lines`
  is the regression test.

Measured on this repo's own history: silent on two of six sampled commits, three
files named on the one that mattered — including, two commits before a human
found it by accident, the file holding the stale claim.

**What it still cannot find:** two prose statements that contradict each other in
files that share no backticked subject, and any disagreement of reasoning rather
than of fact. Those need a reader.

## Honest limits

- **Level I vs Level II is not modelled.** Both fall in the "6809" bucket, so a
  future Level-II-present / Level-I-absent split *could* surface as a presence
  finding; the message flags this so a human reconciles it rather than the tool
  asserting an error. There is currently no such case in the corpus.
- Present claims are read from **table rows**, not prose. A `Live` mention in a
  paragraph asserts nothing (safe under-reporting) — the authoritative presence
  claims live in the reference tables. Explicit absence prose still counts.
- This is token-level, not semantic: it cannot detect a register-layout
  divergence ("manual says d0.w, runtime uses d1.w"). Those are tracked by the
  `Flag` convention (check 3).
- **Check 6 sees only the `SYMBOL $VALUE` form.** A table that leads with the
  offset (`| $00-$01 | 2 | Sync |`) or writes it as `0x2E` states the same fact
  in a shape the extractor does not bind, so it is watched less densely than a
  reader might assume: 182 bindings over 155 symbols, 12 of them stated in more
  than one file. `0x` was left out deliberately — in this corpus it appears as
  bit masks (`0x80 directory`), never as a symbol-to-offset binding, so
  including it would add false positives rather than coverage.

## Failability (project rule: make it fail once)

Every check went red before implementation (TDD). Each real false-positive
pattern from the first dogfood run is a permanent "must-not-flag" regression
test, and a reintroduced-I$Dup case is a "must-flag" test. Proven on real data:
injecting an I$Dup absence into a copy of the actual docs makes the checker flag
it; the untouched corpus is silent.

Checks 4–5 (added 2026-07-21) were proven the same way: injecting a bogus
`INDEX.md` row flags it and reverting is silent again (the real `INDEX.md`
corpus has zero cross-reference findings). Check 5, run for real against the
live memory directory (`--memory-dir`), immediately found genuine rot: 36
`[[name]]` links across ~15 memory files pointing at slugs that don't exist
(mostly a dropped/added `feedback_` prefix drift, e.g. `[[commit_approval]]`
vs. the real `feedback_commit_approval`) — real data the check was never
tuned against, which is why it's convincing rather than circular. That
inventory is a maintenance worklist, not fixed by this change; see the
`doc-consistency-checker` memory.

Check 7 was proven against the two breaks that motivated it, both real and both
already fixed by the time the check existed: reintroducing the
`SOURCE-AUTHORITY.md` pointer into `os9-dev/SKILL.md` and the bare
`6809-level2-mmu.md` into `6809/utility-usage.md` makes the checker flag
exactly those two lines, exit 1; restoring both is silent again, exit 0. Run
for real it also found one break nobody had noticed — `os9-systems-dev`'s
`INDEX.md` citing `memory-and-io.md` with the `os9-dev` qualifier four lines
upstream, out of any reasonable reader's reach — which is the useful kind of
result, since the check was written before that line was looked at.

Check 6 was proven the same way, and the vacuity trap was checked explicitly
first: the extractor really does bind 182 facts across the corpus, so a silent
green is not an empty scan. Injecting a plausible drift (`M$Mode` `$37` → `$39`
in `device-drivers.md` alone) makes it flag the symbol and name all four
contributing locations across three files, exit 1; reverting is silent again,
exit 0. The disown-suppression is exercised against the real `M$Parity` `$28`
scan-error line, not a synthetic one.

`check_absent_scope` was proven in both directions, and the second direction is
the one this section exists to insist on — because it is the one that was nearly
skipped even with this page already written.

Must-flag: the three bare `Absent` tags that shipped in `6809/utility-usage.md`
before the scope rule existed, recovered from git and fed to the check, produce
exactly three findings. Must-not-flag: the forms it has to accept —
`Absent` (6809), `Absent` on real NitrOS-9, `Absent` from this SDK,
`Absent`: untestable here.

**The first version of the pattern passed the must-flag test and failed the
must-not-flag one.** It required the scope marker immediately after the tag, so
`` `Absent` — from the v2.4 manuals `` and `` `Absent` -- on NitrOS-9 `` were
flagged for obeying the rule. Both are now regression tests.

Worth stating the asymmetry, because it decides which direction to test when time
is short: **a false positive is the more expensive failure.** A check that misses
a violation costs one defect. A check that flags correct work teaches contributors
that the rule is arbitrary, and a gate nobody believes gets routed around,
commented out, or `--no-verify`d — taking every other check with it. A gate is
only as strong as its credibility.

And the flavour of false positive to watch for is a check firing on text that
*documents* the thing it forbids. Every `../..` in this corpus appears in prose
teaching that OS-9 spells it `...`; a naive pathlist gate would flag the
explanation of the rule it enforces. Screen the context, not just the string.

**Wiring is a separate claim from correctness, and needs its own proof.** A check
can be right, tested, and never invoked. The function passing its unit tests and
the tree being green are two true statements that together still permit a check
that the CLI never calls — registering it in the driver is a third thing, and
reading the line is not evidence it executes.

`check_absent_scope` was therefore proven along the whole chain, not just at the
function. Removing the scope from one real `Absent` entry in
`6809/utility-usage.md`:

1. the **function**, called directly, reports the finding;
2. the **CLI** exits 1 and names `os9-dev/references/6809/utility-usage.md:400`
   under `[absent-scope]`;
3. the **pre-commit hook** refuses the commit — *"nothing committed"* — with the
   violation staged.

Reverting is silent again at all three. Step 2 is the one worth insisting on: it
is what distinguishes a registered check from a defined one, and a unit test
cannot see the difference. A sister project hit exactly this — a breaker function
written but not added to its registry, with the verification tool then reporting
"24 of 24 breaks were caught", which was true and answered a different question.
Nothing lied; the missing label in the output was the only evidence.

**Where a breaker cannot reach, say so instead of writing one.** A proof that
exercises nothing is worse than a documented absence of proof, because it reports
success. If the harness cannot put a check's inputs under test, record that and
prove the check another way rather than staging a break the check could not have
seen.
