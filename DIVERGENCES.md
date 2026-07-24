# Divergences from Microware documentation

Places where observed OS-9 behaviour, or our own documentation, disagrees with
or isn't covered by Microware's published manuals. The manual is the
specification; each item is a question for Microware to settle.

## Behaviour vs. the manual

- **BOOLEAN prints `True`/`False`, not the documented `TRUE`/`FALSE`.** Both
  BASIC09 manuals (Rev H, and Tandy 1983) specify uppercase; real Microware
  6809 BASIC09 v01.01.00 prints mixed case. (Checked via `PRINT USING "B"`.)

## Gaps in the manuals themselves

- **Shell redirections `>+` and `>-` are undocumented.** Both are real,
  working syntax (append-or-create; truncate-or-create); *Using Professional
  OS-9 v2.4* lists only `<`, `>`, `>>`.
- **Error 200 is mislabelled** `E$BPNum` in the v2.4 Technical Reference
  appendix; it is `E$PthFul` everywhere else, including that manual's own
  per-call error lists. A single-edition typo.
- **6809 syscall codes `$1F`, `$20`, `$23`–`$26`** are neither documented nor
  confirmed reserved anywhere in the manuals.
