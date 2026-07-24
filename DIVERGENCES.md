# Divergences from Microware documentation

Places where our documentation, or the behaviour we observed, disagrees with
or is not covered by Microware's own published manuals. Maintained for
Microware's review — the manual is the specification; anything here is a
candidate defect on our side or a question only Microware can settle.

**Scope:** this file lists things *Microware* can adjudicate. Bugs in a
community reimplementation (os9exec, NitrOS-9) are not divergences from OS-9
and are not listed here — they are tracked in those projects. Two such bugs
worth naming only so the skill doesn't present them as the contract: 68k
os9exec raises a CPU trap (error 105) for `INTEGER÷0` where BASIC09 documents
error 45, and its `F$Sleep` never writes the remaining-ticks output. On 6809,
real NitrOS-9 matches the manual on both.

## Behavioural divergence

### D-001 — BOOLEAN prints as `True`/`False`, not the documented `TRUE`/`FALSE`

Both the Rev H (Microware) and Tandy BASIC09 manuals specify uppercase; both
reimplementations, and real Microware BASIC09 6809 v01.01.00, print mixed
case. Only Microware or genuine hardware can say whether the manual overstates
or shipping code always diverged. Tested via `PRINT USING "B"`; plain `PRINT`
of a BOOLEAN is not yet separately checked.

## Questions in Microware's own documentation

Places the published manuals are silent, self-contradictory, or (in surviving
scans) illegible — offered for Microware to resolve.

- **Shell redirections `>+` and `>-` are undocumented.** Both are real,
  working OS-9 syntax (append-or-create; truncate-or-create). *Using
  Professional OS-9 v2.4* lists only `<`, `>`, `>>`.
- **Error 200 is mislabelled in the v2.4 Technical Reference appendix** as
  `E$BPNum` ("path table full"); it is `E$PthFul` in every other Microware
  source and in that manual's own per-call error lists. A single-edition typo.
- **`wmode` is absent from the Level 2 manual** (TOC and full-text both empty)
  though it is a real utility.
- **`F$Fork`'s input-register table differs between Microware manuals** for the
  same call.
- **6809 syscall codes `$1F`, `$20`, `$23`–`$26` appear nowhere** — neither
  documented nor confirmed reserved.

## Not yet located

Runtime behaviour observed, Microware passage not yet found — work queue, not
divergences: REAL÷0 error number (BASIC09), GFX2 `PALETTE` accepting
out-of-range values, GFX2 `GOSET` absent from the shipped package, and the
6809 module type/language byte encoding.
