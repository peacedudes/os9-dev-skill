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

Meta-docs (`CONFIDENCE-TAGS.md`, `VERIFICATION-BACKLOG.md`, `INDEX.md`,
`SOURCES.md`) are excluded from checks 1–3 (used only for their tag set) but
`INDEX.md` is exactly what check 4 scans — they quote calls as examples but
`INDEX.md`'s file-pointers are not "examples," they're the navigation table.

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

Check 6 was proven the same way, and the vacuity trap was checked explicitly
first: the extractor really does bind 182 facts across the corpus, so a silent
green is not an empty scan. Injecting a plausible drift (`M$Mode` `$37` → `$39`
in `device-drivers.md` alone) makes it flag the symbol and name all four
contributing locations across three files, exit 1; reverting is silent again,
exit 0. The disown-suppression is exercised against the real `M$Parity` `$28`
scan-error line, not a synthetic one.
