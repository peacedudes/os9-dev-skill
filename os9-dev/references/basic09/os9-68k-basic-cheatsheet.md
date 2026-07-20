# OS-9/68000 BASIC09 — Architecture Delta

BASIC09 is the same language on 6809 and 68k. **See `basic09-language.md`
for the language itself** (syntax, control flow, procedures, I/O,
functions, error handling, debug mode) — nothing there is repeated here.
This file covers only what's actually different about running BASIC09 on
68k: numeric widths/ranges/precision and facts `Live` on the 68k
emulator (os9exec). The sibling `basic09-cheatsheet.md` carries the 6809
deltas.

## Data Types (68k widths)

| Type | Size | Range | Notes |
|------|------|-------|-------|
| BYTE | 1 byte | 0-255, unsigned | Same on both architectures |
| INTEGER | 4 bytes | -2,147,483,648 to 2,147,483,647 | See overflow behavior below |
| REAL | 8 bytes | ~±2.2e-308 to ±1.8e308 | ~14 decimal digits; `DIGITS` controls display & transcendental precision, range 1-15 |
| STRING | 1+ bytes, max 32 default | Declared via `STRING[len]` | Same on both architectures |
| BOOLEAN | — | TRUE / FALSE | Same on both architectures |

**INTEGER overflow wraps silently, no error.** `2,147,483,647 + 1` gives
`-2,147,483,648` (ordinary two's-complement wrap), `Live`
(`tools/benchmarks/basic09-langtest.bas`) and matched independently by
`basic09c` and by real 6809 hardware at its own width. The "OS-9 BASIC
User Manual" has a typo giving `2,147,483,648` (positive) instead — not
worth more than this note; see `basic09-vs-68k-differences.md`.

**REAL is IEEE-754** (`Manual`). The OS-9 BASIC User Manual documents 68k
REAL as a standard IEEE-754 double-precision float — sign in bit 7 of the
first byte, an 11-bit exponent (bits 0-6 of byte 1 + bits 4-7 of byte 2)
biased by 1024, a 52-bit mantissa with an implied leading one. Bit-for-bit
rounding behavior should follow normal IEEE-754 semantics. `Live`: `SIZE(REAL var)` = 8,
`SIZE(INTEGER var)` = 4; `1./3.` at `DIGITS 15` prints as
`.333333333488554`.

Hex constants (`$` prefix) range `$0`-`$FFFFFFFF` — no sign-flip zone the
way 6809's 16-bit range has one (see the 6809 file).

## 68k-only documented commands

Four commands/behaviors — `SHELL`, `CHAIN`, command-line `PARAM`, and the
INTEGER-vs-REAL performance gap — are documented only in the 68k-era "OS-9
BASIC User Manual", not the 6809-era manual. Full description of each: see
`basic09-vs-68k-differences.md`'s "68k-only documented commands" section
(not repeated here).

## Toolchain facts

`Live`: 68k `basic` identifies itself as "Microware Basic
V2.1". `RunB`, the standalone runtime-only interpreter, exists and works
on 68k — `Live`, running a real `PACK`ed module.
A packed module is a *subroutine* module and can't be run by name from the
shell; run it as `runb <name>`. Load path: module directory (`F$Link`) first,
then the *execution* directory (`F$Load`) — never the data directory. See
`common/module-format.md` for the full writeup.

---

**Sources:** OS-9 BASIC User Manual (Revision G, 1991) — 68k-specific
numeric widths, IEEE-754 REAL confirmation, 68k-only commands. Language
mechanics shared with 6809: `basic09-language.md`. Full 6809/68k delta
table: `basic09-vs-68k-differences.md`. `Live` source: this
project's `os9exec` emulator.
