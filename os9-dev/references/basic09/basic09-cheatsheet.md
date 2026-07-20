# BASIC09 (6809) — Architecture Delta

BASIC09 is the same language on 6809 and 68k. **See `basic09-language.md`
for the language itself** (syntax, control flow, procedures, I/O,
functions, error handling, debug mode) — nothing there is repeated here.
This file covers only what's actually different about running BASIC09 on
6809: numeric widths/ranges/precision and the platform-specific facts
(hex-constant sign meaning, the Graphics Interface Module) that have no
68k equivalent.

INTEGER overflow and hex-constant sign below are `Live` (real Microware
BASIC09 "6809 VERSION 01.01.00" under XRoar, harness:
`6809/using-nitros9-repl.md`); REAL width/range/precision are `Manual`
(BASIC09 Reference Manual Rev H, OS-9 BASIC User Manual Rev G, 1991) —
not yet independently measured against the running system. See
`6809/STATUS.md` for what's been checked so far.

## Data Types (6809 widths)

| Type | Size | Range | Notes |
|------|------|-------|-------|
| BYTE | 1 byte | 0-255, unsigned | Same on both architectures |
| INTEGER | 2 bytes | -32,768 to 32,767 | Wraps modulo 65,536 on overflow, no error |
| REAL | 5 bytes | ~±1×10³⁸ | 40-bit binary FP (8-bit two's-complement exponent + 4 mantissa bytes, 31 bits + sign); ~9 decimal digits |
| STRING | 1+ bytes, max 32 default | Declared via `STRING[len]` | Can extend up to 2880 chars; otherwise same as 68k |
| BOOLEAN | 1 byte | TRUE / FALSE | Same on both architectures |

**INTEGER overflow wraps silently, no error.** `32,767 + 1` becomes
`-32,768` — a full 16-bit modulo-65,536 wraparound, confirmed by both
source manuals for this architecture and `Live`
(`a=32767: a=a+1: PRINT a` on real NitrOS-9/6809 BASIC09 prints
`-32768`). 68k wraps the same way at 32-bit width (also `Live` —
see `gotchas.md`). A comparison
in the 32,767-65,535 range is silently comparing negative numbers.

**Hexadecimal constants use a `$` prefix** (e.g. `$FFFF`) — on 6809 this
is a 16-bit literal, so `$8000`-`$FFFF` read as *negative* INTEGER
values. `Live`: `PRINT $FFFF` on real 6809 BASIC09 prints
`-1`. The same literal on 68k is a large positive 32-bit value instead
— see `gotchas.md` for why this flips.

REAL range is stated directly by the BASIC09 Reference Manual as
~±1×10³⁸ (~9 decimal digits). (Beware bit-layout-derived figures like
"2.94e-39 to 1.70e38" — plausible, but not what the manual states.)

## Platform-specific facts with no 68k equivalent

- **Graphics Interface Module** (`RUN GFX(...)` / `RUN GFX2(...)`) — exists
  on CoCo/Dragon (6809) systems for this language, specific to those
  platforms' video hardware. Not portable, and not present in the 68k line
  at all. Calling it on 68k fails silently (function not found) — no
  error, just a no-op or crash depending on context. Guard or strip before
  porting to 68k. Full function-by-function syntax reference:
  `6809/gfx-windowing.md`.
- **Comments are stripped by `PACK`'d output** — don't rely on them
  surviving into a distributed compiled program. (Architecture-neutral in
  principle, but only documented in the 6809-era manual on hand.)

---

**Sources:** BASIC09 Reference Manual (Rev H) — 6809-specific numeric
widths, CoCo/Dragon Graphics Interface Module note. Items marked
`Live` were confirmed on real NitrOS-9/6809 BASIC09; the rest is
`Manual`. Language mechanics shared with 68k:
`basic09-language.md`. Full 6809/68k delta table:
`basic09-vs-68k-differences.md`.
