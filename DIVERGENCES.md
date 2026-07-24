# Divergences from Microware documentation

Places where our documentation, or the behaviour we observed, disagrees with
or is not covered by Microware's own published manuals. Maintained for
Microware's review — the manual is the specification, so anything here is a
candidate defect on our side, or a question only Microware can settle.

Bugs in a community reimplementation (os9exec, NitrOS-9) are **not** listed
here — they are defects in a clone, not questions about OS-9. Two worth naming
only so the skill doesn't mistake them for the contract: 68k os9exec raises a
CPU trap (error 105) for `INTEGER÷0` where BASIC09 documents error 45, and its
`F$Sleep` never writes the remaining-ticks output. Real 6809 NitrOS-9 matches
the manual on both.

## Behaviour that disagrees with the manual

Both BASIC09 manuals (Rev H Microware, and Tandy 1983) specify that BOOLEAN
values print as `TRUE`/`FALSE`. Every runtime tested — 68k os9exec and real
Microware 6809 BASIC09 v01.01.00 alike — prints `True`/`False` instead
(mixed case, correct field width). Checked via `PRINT USING "B"`. Only
Microware can say whether the manual overstates or shipping code always
diverged.

## Gaps in Microware's own documentation

Places the published manuals are silent, self-contradictory, or (in surviving
scans) illegible — offered for Microware to resolve.

- **Shell redirections `>+` and `>-` are undocumented.** Both are real,
  working OS-9 syntax (append-or-create; truncate-or-create). *Using
  Professional OS-9 v2.4* lists only `<`, `>`, `>>`.
- **Error 200 is mislabelled in the v2.4 Technical Reference appendix** as
  `E$BPNum` ("path table full"); it is `E$PthFul` in every other Microware
  source and in that manual's own per-call error lists. A single-edition typo.
- **6809 syscall codes `$1F`, `$20`, `$23`–`$26` appear nowhere** — neither
  documented nor confirmed reserved.

## Not yet located

Runtime behaviour observed, Microware passage not yet found — a work queue,
not divergences: REAL÷0 error number (BASIC09), and GFX2 `PALETTE` accepting
out-of-range values.
