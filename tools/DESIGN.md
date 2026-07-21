# Skill-doc consistency checker — design

Repo: `~/.claude/skills` (os9-dev + os9-systems-dev). Entry: `check_doc_consistency.py`.
Run from `~/.claude/skills`:

```
python3 tools/check_doc_consistency.py            # scan both skills' references/
python3 tools/check_doc_consistency.py <dir>...   # scan given roots
python3 -m unittest discover -s tools/tests       # the test suite
```

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

Meta-docs (`CONFIDENCE-TAGS.md`, `VERIFICATION-BACKLOG.md`, `INDEX.md`,
`SOURCES.md`) are used for their tag set but never scanned as claim sources —
they quote calls as examples.

The run also prints a **`Live` verified-against** footer: the per-platform build
baselines from the "What `Live` is verified against" table in `CONFIDENCE-TAGS.md`
(os9exec `git describe`; 6809 disk + XRoar + lwasm). Surfacing it every run keeps
the baseline visible so stale `Live` claims get re-checked after an emulator fix.
Informational only.

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

## Failability (project rule: make it fail once)

Every check went red before implementation (TDD). Each real false-positive
pattern from the first dogfood run is a permanent "must-not-flag" regression
test, and a reintroduced-I$Dup case is a "must-flag" test. Proven on real data:
injecting an I$Dup absence into a copy of the actual docs makes the checker flag
it; the untouched corpus is silent.
