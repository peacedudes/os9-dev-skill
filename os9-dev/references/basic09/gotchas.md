# BASIC09 Gotchas — all targets unless noted

A digest of the traps, one to three lines each, with a pointer to the full
treatment. Nothing here is the only statement of a fact except where a bullet
carries its own detail.

## Porting between targets

Full per-target detail: `basic09-per-target.md`.

- **INTEGER overflow wraps silently** at each target's width, no error, no
  warning. The wrap *mechanism* is identical across targets, so porting code
  that relies on the *width* breaks without any visible symptom — the #1
  silent-bug source here.
- **Hex constants change sign meaning across targets.** 6809 `$8000`-`$FFFF`
  are negative (16-bit); the same literal on 68k is a large positive 32-bit
  value. Never compare one across the boundary without an explicit cast.
- **REAL precision differs** — ~9 decimal digits on 6809, ~14 on 68k. Code
  relying on accumulated rounding or near-equality needs tolerance
  comparisons, not `=`.
- **Binary `PUT`/`GET` files are not cross-target safe** if they contain
  INTEGER or REAL fields — the field widths differ, so a 68k-written file
  decodes to wrong values on 6809 and vice versa. Use text-format
  `WRITE`/`READ` for portable data exchange.
- **`PACK` output is target-specific I-code.** A packed 6809 module will not
  run on 68k or vice versa. Keep the source; recompile per target.
- **Graphics Interface Module is 6809-only** (CoCo/Dragon). Calling `GFX`/
  `GFX2` on 68k fails silently — no error, just a no-op or a crash depending
  on context. Guard or strip before porting.
- **`PEEK`/`POKE` and `ADDR` are not portable** — the two targets have
  entirely different address spaces and memory layouts. Treat any code using
  them as target-specific; use `OPEN`/`READ`/`WRITE` for portable I/O.
- **6809 mis-parses numeric command-line `PARAM`s.** A supplied numeric
  argument lands in the INTEGER as its raw ASCII bytes (`progname 42` →
  `13362`). `STRING` params are fine; 68k parses correctly.

## Syntax that looks right and isn't

Full grammar and the live error codes: `basic09-language.md`.

- **`PRINT USING` does NOT take `#`-placeholder format strings.** `"###.##"`
  was never real BASIC09 syntax and fails at run time. The real format uses
  directive **letters** — `R8.2` real, `I4` integer, `S8` string, `H4` hex,
  `B8` boolean, `E12.3` exponential — with optional `<`/`>`/`^` justify.
  This is the single most dangerous "looks like something I already know"
  trap in the language.
- **`PRINT USING`'s path number goes after `PRINT`, before `USING`** —
  `PRINT #path USING fmt, list`. The reverse is a syntax error.
- **There is no multi-line `TYPE`/`ENDTYPE` block, and no `ENDPROC`.** Both
  are fabrications that appear in no manual. `TYPE` is always one
  semicolon-separated line; a `PROCEDURE` ends with an optional, executable
  `END`, or simply runs out of statements.
- **Two distinct `IF` forms — don't mix them.** Type 1: `IF cond THEN
  linenum`, a bare line number, no `GOTO` keyword, no `ENDIF`. Type 2:
  `IF cond THEN` / statements / `ENDIF` on its own line, where `ENDIF` is
  mandatory. `IF cond THEN GOTO n` is neither form and correctly fails to
  compile — not a compiler bug.
- **`GOTO`/`GOSUB` targets are explicitly-typed line numbers**, not the hex
  byte offsets `LIST` displays beside unnumbered structured code. Aiming a
  `GOTO` at one of those reads as "GOTO is broken" and isn't.
- **`LAND`/`LOR`/`LXOR`/`LNOT` are function calls, not infix operators.**
  `6 LAND 3` is a syntax error; write `LAND(6,3)`. `AND`/`OR`/`XOR`/`NOT`
  *are* infix, and are BOOLEAN-only.
- **`BASE 0`/`BASE 1` needs the space** — `BASE0` is a syntax error, not an
  alternate spelling. It affects array subscripts only: **string indexing
  always starts at 1** regardless. And the `DIM` bound is always the element
  count — `BASE 0` shifts where indexing starts, it does not add a slot.
- **A trailing comment after code is a compile error on both interpreters.**
  `!` must be the first non-blank token on its line. A standalone whole-line
  `!` comment is fine anywhere a statement could go, and `LIST` normalizes it
  to `REM`. (`basic09c`, the independent native compiler, is the mirror
  image: it accepts trailing comments and rejects standalone comment lines —
  no comment style is clean across all three.)

## Behavior that surprises

- **A comment as the literal first line of a file breaks `LOAD` outright on
  6809, but not on 68k** (`Live`, both). A host-authored file starting with
  `! ...` above `PROCEDURE` loads and compiles cleanly on 68k, the comment
  silently discarded. The identical file fails on 6809 with `Error #043 --
  Unknown Procedure`, and the failure is not scoped to one procedure —
  **nothing in the file loads**, including procedures defined after the
  comment. It is genuinely about *position*: the same comment inside a
  procedure body, or standalone between two procedures, loads cleanly on both
  and normalizes to `REM`. **Fix: put `PROCEDURE` on line 1**, and if a
  whole-file comment is wanted, place it after that line.
- **No automatic variable initialization** — uninitialized variables hold
  garbage, not zero. `DIM` and initialize explicitly.
- **BYTE variables cannot be passed as parameters, and this fails silently.**
  `PARAM b: BYTE` is accepted with no error at edit time or run time, but the
  argument is simply discarded and the parameter reads as uninitialized. Pass
  a BYTE array instead. Microware documents the restriction; the silence is
  faithful, not a quirk.
- **Division truncates based on the OPERAND types, not the destination's.**
  `r = i / 3` with `i: INTEGER` does truncating INTEGER division first, then
  widens the already-truncated result into the REAL destination. A REAL
  operand (`i / 3.0`) is what forces real division.
- **A BOOLEAN operand in a numeric expression is a COMPILE-TIME error**
  (`Error #000:067`), not a runtime one — the program never starts.
- **`EOF(#path)` behaves like C's `feof()`** — a sticky flag set only by an
  actual failed read, not a live position check. It stays FALSE right after
  reading the last record, and `SEEK`ing arbitrarily far past the end never
  sets it. So `WHILE NOT EOF(#path) DO READ ... ENDWHILE` always over-reads on
  its final iteration and needs `ON ERROR GOTO` to catch it cleanly.
- **`ON ERROR GOTO` does NOT auto-clear after firing**, despite claims
  otherwise. It stays armed indefinitely until an explicit bare `ON ERROR`.
- **`TRIM$` strips TRAILING spaces only** — `TRIM$("  hi  ")` is `"  hi"`.
- **`FIX()` rounds to nearest, it does not truncate** — `FIX(-3.9)` is `-4`.
- **`RND(n>0)` returns a fractional REAL in `[0,n)`**, not an integer the way
  some other BASICs do. Use `FIX(RND(n))` for a random integer.
- **Divide-by-zero reports a different code on each target.** 6809 raises
  Microware's documented `Error #045 -- Divide by Zero` for both INTEGER and
  REAL. 68k raises the underlying 68000 CPU exception instead — `#000:105`
  (`E_ZERDIV`) for INTEGER, `#000:107` (`E_TRAPV`) for REAL. All four are
  catchable and all four drop into Debug Mode if unhandled, so branch on
  "an error occurred", never on the number.
- **A literal `;` inside a string constant gains a spurious backslash.**
  `PRINT "text; more"` stores and echoes as `text\; more`, in both `LIST`'s
  display and real runtime output — presumably the tokenizer disambiguating
  from the statement separator. `Live` (6809); not tested on 68k. Easy to
  miss until it shows up in something meant to be exact text.
- **Real Y2K-class bug in 68k's `DATE$`.** Any year ≥ 2000 prints a corrupt
  leading year digit (`"<6/07/14"` where `"26/07/14"` was correct). `Live` on
  6809 confirms it is **absent** there, so it's the 68k runtime's own
  formatting, not shared logic. Don't trust the 68k year field.
- **BOOLEAN prints mixed case, contrary to the manual.** `PRINT USING`'s `B`
  format is documented by Microware as printing `"TRUE"`/`"FALSE"`, but every
  runtime tested prints `"True    "`/`"False   "` (correct 8-char field
  width) — `Live` on 68k os9exec *and* on real Microware BASIC09 6809
  01.01.00, so it is not an emulator artifact. Whether the manual overstates
  or shipping code always diverged is unresolved.

## Packing and running

- **`PACK`/`RunB` have their own gotcha set** — output goes to CHX (not
  CHD, unlike `SAVE`), the entry-point rule differs between `PACK a,b` and
  `PACK*`, only bare names ever resolve, residency from an earlier run can
  shadow a later one, and the `Can't install trap handler` banner has three
  distinct causes. All of it: `pack-and-runb.md`.
