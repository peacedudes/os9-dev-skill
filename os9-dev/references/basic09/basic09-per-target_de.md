# (DE) Übersetzung – automatische Platzhalter

Dies ist eine automatische Übersetzungsplatzhalter-Datei. Originalpfad: os9-dev-skill/os9-dev/references/basic09/basic09-per-target.md

---

# BASIC09 per target - 6809 vs OS-9/68000

BASIC09 is the same language on both targets. **`basic09-language.md` is the
language reference** - syntax, control flow, procedures, I/O, functions,
error handling, debug mode - and none of it is repeated here. This file
covers only what differs: numeric widths and precision, the platform-specific
facts with no counterpart on the other side, and the 68k-only mechanism for
calling machine-language procedures from BASIC09.

**Verification:** 6809 INTEGER overflow and hex-constant sign are `Live` (NitrOS-9)
(Microware BASIC09 "6809 VERSION 01.01.00" under NitrOS-9; harness:
`6809/using-nitros9-repl.md`); 6809 REAL width/range/precision are `Manual`,
not independently measured. 68k items are `Live` (os9exec) unless marked
otherwise.

## Data types by