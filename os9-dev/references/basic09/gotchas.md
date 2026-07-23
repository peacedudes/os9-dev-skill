# BASIC09 Gotchas — all targets unless noted

- **INTEGER overflow wraps silently, no error.** 6809: modulo 65,536
  (32,767 + 1 = −32,768). 68k: modulo 4,294,967,296 — same mechanism,
  just wider (`2,147,483,647 + 1` = `−2,147,483,648`) — `Live` on real
  6809, real 68k, and `basic09c` alike. (The 68k-era manual has a
  typo giving a positive result here — a signed 32-bit INTEGER can't
  even hold that value — not worth more than a footnote; see
  `os9-68k-basic-cheatsheet.md`.) No runtime warning either way — this
  is the #1 silent-bug source when porting between the two, since code
  relying on the *width* still needs to change even though the wrap
  *mechanism* doesn't.
- **Hex constants change sign meaning across targets.** 6809: `$8000`–`$FFFF`
  are negative (16-bit). 68k: the same literal is a large positive 32-bit
  value. Never compare a hex literal across a 6809/68k boundary without
  an explicit cast.
- **REAL precision differs.** 6809: 40-bit binary, ~9 decimal digits. 68k:
  64-bit binary, ~14 decimal digits. Code relying on accumulated rounding
  or near-equality comparisons behaves differently — use tolerance-based
  comparisons, not `=`, on REAL.
- **No automatic variable initialization.** Uninitialized variables contain
  garbage, not zero. Always DIM and initialize explicitly.
- **BYTE parameters are not supported** in PROCEDURE calls — pass a BYTE
  array instead. **This fails silently, not loudly:** `PARAM b: BYTE` is
  accepted with zero error at both edit time and run time, but the passed
  argument is simply discarded — the parameter never gets bound and reads
  as its default/uninitialized value (`Live`, 68k). Don't expect
  a compile or runtime error to catch this mistake.
- **PEEK/POKE and ADDR() are not portable across targets** — 6809 and 68k
  have entirely different address spaces and memory layouts. Treat any
  code using them as hardware/target-specific; stick to OPEN/READ/WRITE
  for portable I/O.
- **PACK output is target-specific I-code.** A packed 6809 `.BIN` will not
  run on 68k and vice versa. Keep the source; recompile per target.
- **Graphics Interface Module is 6809-only** (Dragon/CoCo). Calling it on
  68k fails silently (function not found) — no error, just a no-op or
  crash depending on context. Guard or strip before porting to 68k.
- **Binary PUT/GET files are bytewise identical but not cross-target safe**
  if they contain INTEGER or REAL fields — a 68k-written file read by a
  6809 program (or vice versa) will decode the wrong values because the
  field widths differ. Use text-format WRITE/READ for portable data
  exchange.
- **Comments are stripped by PACK** — don't rely on them surviving into a
  distributed compiled program.
- **PACK/RunB have their own gotcha set** — output goes to CHX, the
  multi-procedure entry-point rule differs between `PACK a,b` and `PACK*`,
  only bare names ever resolve, PARAM binding rules, and
  `Can't install trap handler` triage: see `pack-and-runb.md`.
- **String indexing always starts at 1**, regardless of `BASE 0`/`BASE 1`
  (note the space — `BASE0`/`BASE1` with no space is a syntax error, not
  an alternate spelling; `Live`, 68k). That setting only affects
  array indexing, not strings, and the `DIM` bound is always the element
  count — `BASE 0` shifts where indexing starts, it doesn't add an extra
  slot at index 0 (see `basic09-language.md`'s Data Types section for the
  `Live` error codes this produces if you get it wrong).
- **`PRINT USING`'s format string does NOT use `#`-placeholder syntax
  the way many other BASICs do** — `"###.##"` is fabricated, never real
  BASIC09 syntax, and produces a live error. The real format uses
  directive LETTERS (`R8.2` real, `I4` integer, `S8` string, `H4` hex
  dump, `B8` boolean, `E12.3` exponential) with optional `<`/`>`/`^`
  justify. This is the single most dangerous "looks like something I
  already know" trap in the whole language — see `basic09-language.md`'s
  PRINT USING section for the full grammar.
- **`PRINT USING`'s optional path number goes right after `PRINT`, before
  `USING`** — `PRINT #path USING fmt, list`, not `PRINT USING #path,
  ...` (the latter is a syntax error, `Error #000:018`).
- **⚠ DIVERGENCE D-001**: `PRINT USING`'s `B` (boolean) format is documented by
  Microware as printing `"TRUE"`/`"FALSE"`, but both reimplementations print
  mixed-case `"True    "` / `"False   "` (8-char field, correct width) — `Live`
  on both (68k `os9exec`; 6809 real Microware BASIC09 01.01.00, 2026-07-23).
  **Two community reimplementations agreeing is not the manual being wrong** —
  they may share an inherited defect. Unresolved pending Microware; see
  `DIVERGENCES.md` and `basic09-language.md`'s PRINT USING section.
  Given 68k `os9exec` faithfully reproduces real Microware BASIC09
  behavior elsewhere, this is very likely the Microware runtime itself
  rather than an emulator artifact, but that's an inference, not a
  6809-confirmed fact yet.
- **A literal `;` inside a string constant gets a spurious backslash
  escape** — `PRINT "Enter lines of text; blank line ends input:"`
  stores and echoes as `Enter lines of text\; blank line ends input:`,
  both in `LIST`'s source display and in the actual runtime output.
  `Live` (6809). Since `;` is also BASIC09's statement separator, this
  is presumably the tokenizer disambiguating a literal `;` from a
  separator even inside a string constant — but the effect (an extra
  literal backslash byte in real program output) is easy to miss until
  it shows up in something meant to be exact text (a banner, a
  formatted report). Not tested on 68k.
- **`ON ERROR GOTO` does NOT auto-clear after firing once**, despite some
  references claiming it does. `Live` (68k): triggering the same
  error twice in a row with no re-arming `ON ERROR` call in between fires
  the trap both times. Treat it as staying armed indefinitely until an
  explicit bare `ON ERROR`.
- **⚠ DIVERGENCE D-002 — `INTEGER÷0` reports a different error on each
  platform, and neither matches the manual on 68k.** Microware documents
  BASIC09 **error 45, "Divide by Zero"** (68k Rev H and the 6809 manuals
  alike). **6809** NitrOS-9 matches it: `Error #045 -- Divide by Zero`,
  dropping into Debug Mode if unhandled. **68k** `os9exec` does not — it
  raises `Error #000:105 (E_ZERDIV) zero divide TRAP 5`, the 68000 CPU
  trap, and breaks into the debugger (`Live`, 2026-07-23).
  **This file previously claimed 68k was silent with no error at all. That
  was wrong** — retested directly and it raises 105. Treat the old claim as
  retracted, not merely refined. See `DIVERGENCES.md`. `REAL÷0`
  **used to crash the entire 68k BASIC process** via an uncatchable CPU
  trap
  (`Error #000:107 E_TRAPV`), a genuine divergence from 6809 (where it
  was always an ordinary catchable `Error #045 -- Divide by Zero`
  dropping into interactive Debug Mode). **This was an `os9exec` bug,
  fixed**: four stacked `F$STrap` dispatch bugs (byte-swap, a wrong
  handler-offset, a clobbered stack-pointer register, a dump-gating
  deadlock) turned what should have been a catchable arithmetic trap
  into the crash. `REAL÷0` on 68k now matches 6809: a catchable trap
  that, left unhandled, drops into interactive Debug Mode rather than
  killing the process. Code written to be portable between the two
  should still guard `REAL÷0` explicitly (`ON ERROR GOTO`) since
  Debug Mode isn't a substitute for a real handler — but it's no longer
  a hard crash on either architecture.
- **`EOF(#path)` behaves like C's `feof()`** — a sticky flag set only by
  an actual failed read, not a live position check. It stays `FALSE`
  right after reading the last record, and `SEEK`ing arbitrarily far
  past the end (confirmed up to 1000 bytes into a 6-byte file) does NOT
  set it either — only an actual `READ` attempt that hits the real end
  does (raising the standard OS-9 `E$EOF`, error 211). Well-precedented
  once recognized, not a bug. The natural `WHILE NOT EOF(#path) DO
  READ ... ENDWHILE` loop idiom always over-reads on its final iteration
  and needs `ON ERROR GOTO` to catch it cleanly.
- **`TRIM$` strips TRAILING spaces only** — leading and embedded spaces
  survive. `TRIM$("  hi  ")` = `"  hi"`, not `"hi"`.
- **Division truncates based on the OPERAND types, not the destination
  variable's type.** `r = i / 3` with `i: INTEGER` (both operands
  INTEGER) computes truncating INTEGER division FIRST, then widens the
  already-truncated result into a REAL destination — the fraction is
  gone. A REAL-typed operand (e.g. `i / 3.0`) is what actually forces
  real division, not the destination's declared type.
- **A BOOLEAN operand in a numeric expression is a COMPILE-TIME error**
  (`Error #000:067 E_ILLARG`), not a runtime one — the program never
  even starts running. `Live` (6809, NitrOS-9 BASIC09) as well:
  `i=b+1` with `b:BOOLEAN` fails at
  `Error #067` on the offending line during entry, and a subsequent
  `run` of that procedure fails with `Error #051 -- Line with Compiler
  Error` rather than executing — architecture-neutral, exactly as the
  language reference implies.
- **`RND(n>0)` returns a fractional REAL in `[0,n)`, not necessarily an
  integer** — don't assume `RND(n)` gives a random integer the way it
  does in some other BASICs; use `FIX(RND(n))` for that. `Live`
  (6809 too): `RND(5)` returned `2.11552125`.
- **Real Y2K-class bug in 68k's `DATE$` — not present on 6809.** On 68k,
  any year ≥ 2000 prints a corrupt leading year digit (`Live`:
  `"<6/07/14"` where `"26/07/14"` was correct). `Live` on 6809 NitrOS-9
  confirms it's absent there (`"26/07/16 16:09:41"`, correct) — so it's the 68k
  port's runtime, not shared DATE$ logic. Don't trust 68k `DATE$`'s year
  field.
- **Comments (`!`) must be the first token on a line — a trailing
  comment after real code is a compile error on both real interpreters,
  not a stylistic choice.** `Live` (both): `PRINT x ! note`
  fails to compile on 68k (`Error #000:029 (E_???) <<unknown error
  code>>`) and on 6809 (`Error #034 -- Missing Left Parenthesis` — a
  different message, same underlying rejection), in both cases with the
  error caret pointing right at the `!`. A standalone whole-line `!`
  comment is completely fine on both, anywhere a statement could go, and
  `LIST` always normalizes it to `REM <text>`. `basic09c` (the
  independent modern native compiler)
  is the mirror image of this: it accepts a trailing same-line comment
  (except immediately after a `DIM` type name, where the comment text
  gets glued onto the type and produces an "unknown type" error), but a
  standalone comment *line* anywhere in the file — even one that parses
  fine at the AST/`--syntax-only` level — is fatal at `--compile`/
  `--emit-llvm` time (`statement is not supported by LLVM IR lowering
  yet: Unsupported`). No comment style is safe across all three targets;
  the only style that's clean everywhere is a whole-line comment,
  positioned after any code it explains rather than trailing it.
- **A comment as the literal first line of a file breaks `LOAD` outright
  on 6809, but not on 68k** (`Live`, both): a host-authored
  text file starting with `! ...` and `PROCEDURE name` on the next line
  loads and compiles cleanly via `LOAD` on 68k (`os9exec`) — the leading
  comment is silently discarded, no error, no warning. The identical
  file fails outright on 6809 with `Error #043 -- Unknown Procedure`,
  and the failure isn't scoped to the one broken procedure — **nothing
  in the file loads**, including procedures defined later in the same
  file, past the leading comment. (Confirmed it's genuinely about
  *position*, not comments-in-files generally: a nonexistent filename
  gives a distinct `Error #216 - Path Name Not Found`, so 6809's `LOAD`
  verb itself is recognized and the file is found and opened — something
  about parsing a leading comment specifically derails it.) The same
  comment placed *anywhere else* — as the first line inside a procedure
  body, or standalone between two procedures — loads cleanly on both
  targets and normalizes to `REM`. Fix: never lead a `LOAD`-able source
  file with a comment; put `PROCEDURE` on line 1, and if a whole-file
  comment is wanted, put it after the `PROCEDURE` line instead.
- **6809 command-line `PARAM`: numeric arguments are mis-parsed —
  `STRING` args are not** (`Live`, 6809): a `PACK`ed module
  invoked bare from the shell (`progname 42`) correctly detects a
  *missing* argument (`Error #056 -- Parameter Error`, proving the
  shell-to-`PARAM` plumbing is genuinely present — see
  `basic09-vs-68k-differences.md`'s "Command-line PARAM" section for the
  68k side of this mechanism), but a *supplied* numeric argument never
  gets decimal-parsed: `progname 42` lands `13362` (`0x3432`, i.e. the
  raw ASCII bytes `'4'`,`'2'`) in an `INTEGER PARAM`, not `42`.
  `progname 99` → `14649` (`0x3939`), confirming the pattern. `STRING`
  `PARAM`s are fine (no parsing needed). 68k does real decimal parsing
  and gets this right — a genuine 6809-specific bug, not a
  documentation gap. `runb <name> <numeric-arg>` fails differently
  (`Error #000`, not the same mis-parse) — a distinct, not-yet-diagnosed
  failure mode, don't assume it's the same root cause.
- **There is no multi-line `TYPE`/`ENDTYPE` block form, and no `ENDPROC`**
  — both are fabrications that never existed in any manual. `TYPE` is
  always one semicolon-separated line; a `PROCEDURE` ends with an
  optional, executable `END` (or just runs out of statements), never
  `ENDPROC`. See `basic09-language.md` for the corrected grammar and
  citations.
- **`GOTO`/`GOSUB` targets are real, explicitly-typed line numbers**
  (`10 PRINT x` / `GOTO 10`) — NOT the hex byte-offset addresses `LIST`
  displays for unnumbered structured code. An earlier finding that
  GOTO/GOSUB were "non-functional" was a test-methodology mistake
  (targeting LIST's display annotations, which were never valid jump
  targets), not a real language limitation.
- **There are two distinct `IF` forms — don't mix them.** Type 1:
  `IF cond THEN linenum` — a bare line number, no `GOTO` keyword, no
  `ENDIF`. Type 2: `IF cond THEN` / statements (including `GOTO`/
  `GOSUB`) / `ENDIF` on its own line — `ENDIF` is mandatory, not
  optional the way `ELSE` is. `IF cond THEN GOTO n` (the `GOTO` keyword
  present, but no `ENDIF`) is neither form and correctly fails to
  compile (`Error #000:069`) — not a compiler bug; that syntax was never
  valid in either form.

See `basic09-vs-68k-differences.md` for the full side-by-side portability
table the target-specific gotchas above are drawn from.
