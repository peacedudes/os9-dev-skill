# Divergences from Microware documentation

Places where observed OS-9 behaviour, or our own documentation, disagrees with
or isn't covered by Microware's published manuals. The manual is the
specification; each item is a question for Microware to settle.

## Behaviour vs. the manual

- **BOOLEAN prints `True`/`False`, not the documented `TRUE`/`FALSE`.** Both
  BASIC09 manuals (Rev H, and Tandy 1983) specify uppercase; a genuine Microware
  6809 BASIC09 v01.01.00 module prints mixed case. (Checked via
  `PRINT USING "B"`.) **The module was Microware's; the machine was not** — this
  was observed under emulation, and which runtime is not recorded here. Of every
  item on this page it is the cheapest to re-test on a real 6809, and doing so is
  exactly the contribution `CONTRIBUTING.md` asks for.

## Internal contradictions within a manual

- **`F$Load`'s "POSSIBLE ERRORS" list is incomplete.** The v2.4 Technical
  Reference gives only `E$MemFul` and `E$BMID`, yet the same entry's prose
  says an error "can indicate an actual I/O error, a module with a bad parity
  or CRC, or that the system memory is full" — and `F$VModul`, which performs
  exactly that check and is named in `F$Load`'s SEE ALSO, lists `E$BMCRC` and
  `E$BMHP`. The list also omits `E$MNF`/`E$PNNF`, which `F$Load` must be able
  to return for a missing file. So the manual does not state which code a
  caller sees for a corrupt module.
- **The 68k *OS-9 BASIC User Manual* prints `2,147,483,648`** (ch. 9, p. 9-2)
  — positive, and a value a signed 32-bit INTEGER cannot hold — where its own
  "wraps around" wording implies the negative result. The 6809-era manual
  (p. 7-2) uses the same sentence template without the defect.

## Gaps in the manuals themselves

- **Shell redirections `>+` and `>-` are undocumented.** Both are real,
  working syntax (append-or-create; truncate-or-create); *Using Professional
  OS-9 v2.4* lists only `<`, `>`, `>>`.
- **Error 200 is mislabelled** `E$BPNum` in the v2.4 Technical Reference
  appendix; it is `E$PthFul` everywhere else, including that manual's own
  per-call error lists. A single-edition typo.
- **6809 syscall codes `$1F`, `$20`, `$23`–`$26`** are neither documented nor
  confirmed reserved anywhere in the manuals.
- **`M$Attr` bits 0–4 are undocumented** in any surveyed manual; only bits 5
  (supervisor state), 6 (sticky) and 7 (sharable) are described.
- **Signal-queue depth on intercept entry is undocumented.** On entry to an
  intercept routine `d0` holds the number of currently-queued signals,
  including the one just delivered, so 1 means nothing else is waiting. The
  source is Dibble's *OS-9 Insights* (third-party); the Technical Manual names
  only `d1` and `a6`, and no manual we hold states it.
- **`asm`'s source-line length limit is undocumented** — a real limit between
  132 and 135 characters, whose only symptom is a misleading `bad instr` error
  reported against the *following* line.
