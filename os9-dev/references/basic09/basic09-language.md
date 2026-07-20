# BASIC09 Language Reference — shared, architecture-independent

**This is the primary BASIC09 language reference.** BASIC09 is the same
language on 6809 and 68k OS-9 — same statements, same keywords, same
built-in functions, same control-flow constructs. Everything on this page
applies to both architectures identically. The only things that differ
between 6809 and 68k are numeric type widths/ranges/precision and a
handful of platform-specific facts — those live in
`os9-68k-basic-cheatsheet.md` and `basic09-cheatsheet.md` (6809), each a
short delta file, not a second copy of this one.

**Verification status:** baseline is `Manual` — claims are cross-referenced
across the BASIC09 Reference Manual (Rev H) and the OS-9 BASIC User Manual
(Rev G, 1991), which document the language identically apart from the
numeric deltas. Items marked `Live` were confirmed on OS-9/68k (os9exec);
several were additionally confirmed on real 6809 NitrOS-9 where noted
(see `gotchas.md` for the 6809-confirmed list).

## Getting Started

BASIC09 operates through three interactive prompts, each a distinct mode:
`B:` for System Mode (workspace management, file operations, launching
code), `E:` for Edit Mode (source entry/modification), and `D:` for Debug
Mode (breakpoint inspection, single-stepping). A fourth "mode," Execution,
is triggered by `RUN` at the `B:` prompt and runs your code before
returning to `B:`. From System Mode, `e <name>` enters Edit Mode and `run
<name>` compiles then executes. Within System Mode, `$` runs an OS-9 shell
command without exiting BASIC; with no argument, `$` alone suspends BASIC
for a full interactive OS-9 session (EOF or ESCAPE resumes).

`Live` (os9exec, "Microware Basic V2.1"): `e <name>` switches
the prompt from `B:` to `E:`
and auto-headers the new procedure (`PROCEDURE <name>`); `BYE` at the `B:`
prompt exits BASIC09 back to the OS-9 shell prompt cleanly.

A procedure name starts with a letter, continues with alphanumeric
characters only (no underscores, dollar signs, or periods); names are
case-insensitive. Maximum length unspecified in source manuals. Each
procedure has its own private namespace: line numbers and variables
declared in one procedure never collide with another's, even if reused
verbatim (`Live`: a helper procedure with its own `PARAM b:
BYTE` and its own print statement can't affect a caller's counters — see
`tools/benchmarks/basic09-langtest.bas` in the os9exec repo for a working
demonstration). Procedures talk to each other only through parameters,
invoked with `RUN`.

## One Complete Example

`[clean-room]` — original, not copied from any manual.

```basic
PROCEDURE grades
PARAM count: INTEGER
DIM score(20): INTEGER
DIM i, total: INTEGER
DIM avg: REAL

total = 0
FOR i = 1 TO count
  INPUT "Score: ", score(i)
  total = total + score(i)
NEXT i

avg = FLOAT(total) / FLOAT(count)
PRINT USING "'Average: ',R6.2", avg

IF avg >= 70.0 THEN
  PRINT "Class passes"
ELSE
  PRINT "Class needs review"
ENDIF
END
```

Enter via `e grades` at the `B:` prompt, type the lines, then run with
`RUN grades(5)` (5 = how many scores to prompt for). `count` arrives by
reference (the default) — a plain variable name in the PARAM/RUN slot;
note that `total` and `avg` are never reassigned outside this procedure,
so by-value-forcing tricks (`x+0`) aren't needed here. This source is
architecture-neutral and doesn't stress either platform's numeric ranges.
The `PRINT USING` line uses the real directive-letter format (see below)
and its literal-string-plus-`R`-format combination is independently
`Live` (68k) (`"'Average: ',R6.2"` with `avg=82.567` produces
`Average:  82.57`) — the individual constructs used elsewhere in this
procedure are each independently `Live` too, but the procedure
as a complete, unmodified whole hasn't been run start-to-finish.

## Data Types

| Type | Notes |
|------|-------|
| BYTE | 0-255, unsigned. Truncates silently on overflow. **Cannot be passed as a procedure parameter** — see Pitfalls. |
| INTEGER | Signed. Faster than REAL (see Control Structures below). Width/range/overflow behavior is architecture-specific — see the per-architecture file. |
| REAL | Width/range/precision is architecture-specific — see the per-architecture file. |
| STRING | Declared via `STRING[len]` (max length, default 32 if omitted). Null-terminated in a fixed buffer; silently truncates past max. |
| BOOLEAN | TRUE / FALSE. Not usable in numeric expressions — storing anything else into a BOOLEAN fails at runtime instead of being silently coerced. |

Undeclared numeric variables default to REAL; a name ending in `$` and
left undeclared defaults to STRING[32]. Mixing numeric types in an
expression (BYTE/INTEGER/REAL) auto-converts to the largest type present;
mixing STRING with a numeric type is a compile-time error, not a runtime
coercion. A constant containing a decimal point or `E` exponent (e.g.
`1.95E+12`) is always REAL, even if its value would fit in INTEGER.

**A BOOLEAN operand in a numeric expression is a COMPILE-TIME error, not
a runtime one.** `Live`: `n = flag + 1` with `flag: BOOLEAN` fails
at `LOAD` with `Error #000:067 (E_ILLARG)` — the program never even
starts running. This is a stricter check than the destination-assignment
case in the table row above (which the manual frames as a runtime
coercion failure) — using a BOOLEAN as an *operand* is caught earlier,
at compile time.

**Division truncates based on the OPERAND types, not the destination
variable's type — assigning to a REAL destination does NOT retroactively
force real division.** `Live` (68k): `r = i / 3` with `i: INTEGER`
(both operands INTEGER) computes INTEGER division first (truncating,
e.g. `100000/3` → `33333`) and only *then* widens that already-truncated
result into the REAL destination `r` — the fraction is gone, `r` prints
as `33333.` not `33333.333...`. A REAL-typed operand (e.g. `i / 3.0`, or
any variable declared REAL) forces real division and preserves the
fraction. This is a common trap for anyone assuming "the destination
type decides the arithmetic" the way it does in some other BASICs — here
the operand types decide, before the result ever reaches the
destination.

```basic
DIM name: TYPE
DIM name(size): TYPE                    ! Arrays, 1-3 dimensions
DIM name: STRING[max_len]
DIM a, b, c: INTEGER; x, y: REAL        ! Comma = shared type, semicolon = new group
```

Array indexing base is controlled per-procedure by the statement `BASE 0`
(0-based) or `BASE 1` (1-based, default) — **note the space; `BASE0`/
`BASE1` with no space is a syntax error** (`Live`: `Error #000:027`),
not an alternate spelling. This affects array subscripts only. STRING
character positions are NOT affected: a string's first character is
always position 1, regardless of the current BASE setting.

**The `DIM` bound is the element count, not the highest valid index — BASE
only shifts where indexing starts, it does not add an extra slot.**
`DIM arr(2): BYTE` allocates exactly 2 elements: under `BASE 1` (default)
those are `arr(1)` and `arr(2)`; under `BASE 0` they are `arr(0)` and
`arr(1)` — `arr(2)` is out of bounds under `BASE 0` (`Live`:
`Error #000:055`). Don't assume `BASE 0` gives you the same top index plus
one extra slot at 0; it doesn't.

Assignment accepts `LET x := 1`, `x := 1`, or plain `x = 1` — all three
compile to identical I-code.

### TYPE records

**There is no multi-line `TYPE`/`ENDTYPE` block form — that construct
never existed in BASIC09** (a plausible-looking fabrication; don't emit
it). The BASIC09
Reference Manual's own formal grammar for the TYPE statement (Rev H,
p.54-55) is unambiguous: `TYPE type_decl {; type_decl}` — a single
statement, semicolon-separated fields, with `{; type_decl}` as the only
repetition mechanism. `ENDTYPE` does not appear anywhere in that grammar,
anywhere else in either primary manual, or in any of the manual's own
worked examples — which cover both a flat record and a record containing
another record's type as a field, and every one is a single `TYPE`
statement with semicolon-separated fields, no closing keyword. The block
form was a fabrication introduced somewhere in this skill's own extraction
history, not a real feature that happens to be broken in this build —
`Live` (loaded directly via `LOAD`, bypassing any editor
involvement) as a syntax error regardless: every line inside a
`TYPE point` / `x: INTEGER` / `y: INTEGER` / `ENDTYPE` block is rejected
individually (`Error #000:027` on each). The one-liner form is the only
form that has ever existed, works correctly, and supports both nesting and
array fields:

```basic
TYPE point = x:INTEGER; y:INTEGER
DIM p: point
p.x = 10
p.y = 20
```

```basic
TYPE inner = a:INTEGER; b:INTEGER
TYPE outer = n:inner; arr(3):INTEGER
DIM o: outer
o.n.a = 5              ! nested TYPE field, `Live`
o.arr(1) = 100         ! array field, `Live`
```

Fields may nest (a field's type can itself be a previously-defined TYPE,
`Live`) and are accessed by dot notation, including through
nesting: `variable.field`, `variable.field1.field2`. Array fields
(`Live`) use the same `(size)` syntax as a plain array
declaration. The manual frames records as *more* efficient than an array
of similar values, not less — field offsets resolve at compile time
instead of being computed at runtime.

```basic
TYPE typename = field1:TYPE; field2(size):TYPE; ...
DIM var: typename
DIM array(10): typename
var.field1 := value
```

## Control Structures

```basic
IF expr THEN
  stmts
[ ELSE
  stmts ]
ENDIF

FOR var = start TO end [ STEP incr ]
  stmts
NEXT [var]

WHILE expr DO
  stmts
ENDWHILE

REPEAT
  stmts
UNTIL expr

LOOP
  stmts
  [ EXITIF expr THEN stmts ENDEXIT ]
  stmts
ENDLOOP
```

**EXITIF always closes with ENDEXIT** — both the BASIC09 Reference Manual
(Rev H) and the OS-9 BASIC User Manual (Rev G) show `EXITIF expr THEN
stmts ENDEXIT` consistently. `Live`: `EXITIF`/`ENDEXIT` inside
a `LOOP`/`ENDLOOP` correctly exits the loop (see
`tools/benchmarks/basic09-langtest.bas`).

**`WHILE` requires `DO`** — a bare `WHILE expr` (no `DO`) is a live syntax
error (`Error #000:031`). Both this and `WHILE expr DO` were tried; only
the `DO` form compiles and runs (`Live`, 3-iteration loop
confirmed — see `tools/benchmarks/basic09-langtest.bas`). Earlier drafts
of this file omitted `DO`; corrected here.

An INTEGER-typed FOR loop counter compiles to direct machine instructions
and runs quickly; a REAL-typed counter invokes library routines at
runtime, incurring significant overhead — roughly an order of magnitude
slower, since REAL arithmetic on both architectures goes through library
calls rather than native instructions (INTEGER does not). Hot loops
benefit most from INTEGER counters. A careless decimal point in an
expression (`value*2.` rather than `value*2`) silently forces the whole
expression to REAL, so watch for this in anything performance-sensitive.

Legacy line-number `GOTO`/`GOSUB` (targets 1-32767) and `ON expr GOTO/GOSUB
line1,line2,...` are both supported and `Live`, working correctly
— `GOTO`/`GOSUB` require **explicit line numbers typed in the source**
(classic numbered-BASIC style, e.g. `10 PRINT x`, `20 GOTO 10`), targeting
one of those explicit numbers. GOSUB pushes a return frame distinct from a
procedure call frame, popped by `RETURN`. Confirmed live: a `GOTO` past two
intervening lines correctly skipped them; a `GOSUB`/`RETURN` correctly
returned to the caller with a value modified inside the subroutine.

**Corrected finding, superseding an earlier false report:** an earlier
verification pass concluded GOTO/GOSUB were "confirmed non-functional,"
based on targeting the hex byte-offset addresses `LIST` displays for
unnumbered structured code (e.g. `GOTO 6` aimed at a statement `LIST`
showed at offset `0006`). **Those byte offsets are not valid GOTO/GOSUB
targets at all** — they're `LIST`'s own internal display annotation for
structured (non-numbered) code, unrelated to the classic line-number
addressing GOTO/GOSUB actually use. The "confirmed non-functional" result
was a test-methodology mistake, not a real language or emulator bug; both
statements work fine once given real, explicitly-typed line numbers.

**The manual actually defines two distinct `IF` forms, and conflating
them produces invalid syntax that looks reasonable but isn't:**

```basic
IF <bool expr> THEN <line#>                          ! Type 1
IF <bool expr> THEN <statements> [ELSE <statements>]
ENDIF                                                 ! Type 2
```

**Type 1** is a bare line number after `THEN` — no `GOTO` keyword at
all — and has no `ENDIF`: `IF i<5 THEN 10` (`Live`: compiles and
runs correctly, jumps to line 10 when true, falls through otherwise).
**Type 2** takes any statement(s) as its body, including `GOTO`/`GOSUB`,
but `ENDIF` is written as a mandatory part of the syntax (unlike the
bracketed-optional `[ELSE ...]`), on its own line:
```basic
IF i<5 THEN
  GOTO 10
ENDIF
```
(`Live`).

**`IF i<5 THEN GOTO 10` — a single line, `GOTO` keyword present, no
`ENDIF` — is neither form.** It's an invalid hybrid: Type 1 syntax
forbids the `GOTO` keyword; Type 2 syntax requires `ENDIF`. `Live`:
this correctly fails to compile (`Error #000:069`), and it fails even
as the *only* statement in an otherwise-empty procedure — this is
**not** a compiler bug, direction-dependent, GOTO-vs-GOSUB-specific, or
about combining with other constructs; it's the compiler correctly
rejecting syntax that was never valid (easy to misdiagnose as a bug if
you don't check the manual's two-form grammar).
**Use Type 1 (`IF cond THEN linenum`) for a bare conditional jump, or
Type 2 with `ENDIF` on its own line for anything else** — never mix a
`GOTO`/`GOSUB` keyword into a same-line `THEN` clause without `ENDIF`.

## Procedures & Parameters

```basic
PROCEDURE name
PARAM param1, param2: TYPE
DIM local_vars: TYPE
stmts
END                                      ! optional, see below

RUN name                                ! call
RUN name(arg1, arg2)                    ! with args
RUN name(var)                           ! by reference (default) — callee can mutate caller's var
RUN name(var+0)                         ! by value — wrap in a no-op expr to force a copy
```

**`ENDPROC` does not exist — this was another fabrication, same pattern
as the `TYPE`/`ENDTYPE` one above.** Zero occurrences anywhere in either
primary manual. The only procedure terminator is `END`, and per the
manual it isn't really a closing keyword at all (BASIC09 Reference
Manual, Rev H, p.50): a procedure simply ends when its statements run
out, and `END` may appear zero, one, or several times anywhere in a
procedure's body as an ordinary executable statement, not a required
trailer. `END` mid-procedure works like an early return, and can carry
an output list that behaves the same as `PRINT`'s.

By default, variables, arrays, and records arrive at a called procedure by
reference — the actual memory location is passed, not a copy. Any
assignment to a parameter overwrites the caller's original value.
Constants and expressions cannot be passed by reference; they always
arrive by value (read-only). To force by-value semantics for a variable,
wrap it in a trivial expression: `x+0` for numerics or `s$+""` for
strings. `Live` (68k), both directions: a plain `INTEGER` or
`STRING` variable passed to `RUN` is mutated by the callee's assignment
to its `PARAM` (caller sees the change); the same call with `x+0`/`s$+""`
leaves the caller's variable untouched.

**Recursion works, including multiple simultaneous live activations of
the same procedure.** `Live` (68k) with two cases: a
single-recursive factorial (`RUN fact(n-1, sub)`, unwind-as-you-go) and
a doubly-recursive Fibonacci (`RUN fib(n-1,a)` then `RUN fib(n-2,b)` in
the same frame — a meaningfully harder case since it needs multiple
concurrent activation records of the same procedure, not just a simple
chain). `fact(5)=120`, `fib(10)=55`, both correct.

**BYTE variables cannot be passed as parameters.** Pass a BYTE array
instead. **This fails silently, not loudly:** `PARAM b: BYTE` is accepted
with zero error at both edit time and run time, but the passed argument
is simply discarded — the parameter never gets bound and reads as its
default/uninitialized value (`Live` (68k) — see
`tools/benchmarks/basic09-langtest.bas`). Don't expect a compile or
runtime error to catch this mistake; it won't.

## I/O

**Standard paths:** `#0` keyboard (input), `#1` screen (output), `#2`
error (output).

```basic
INPUT [ #path, ] [ "prompt", ] var_list        ! Line-based; retype on error
PRINT [ #path, ] output_list                   ! To terminal or file
PRINT USING fmt_string, output_list            ! Formatted output — see below
GET #path, var_or_array                        ! Binary/random read
PUT #path, var_or_array                        ! Binary/random write
OPEN #var, "pathlist" [ :mode ]                ! Open existing file
CREATE #var, "pathlist" [ :mode ]              ! Create new file
CLOSE #path1, #path2, ...
DELETE "pathlist"
SEEK #path, byte_offset
```

Access modes: READ, WRITE, UPDATE (read+write), EXEC, DIR.

```basic
DATA expr1, expr2, expr3, ...         ! Define data
READ var_list                          ! Read next DATA items
RESTORE [ line_number ]               ! Rewind or jump to DATA
```

DATA wraps around when exhausted rather than erroring.

`EOF(#path)` returns TRUE at end-of-file; `ERR` holds the most recent error
code and auto-resets to 0 once read; `POS` reports the current print
column.

**`EOF()` behaves like C's `feof()` — a sticky flag set only by an
actual failed read, not a live position check.** `Live`: reading
a 2-line sequential file, `EOF(#path)` is still `FALSE` immediately
after the second (last) successful `READ`. Only a further `READ`
attempt — which raises `Error #000:211 (E$EOF)` — makes `EOF(#path)`
become `TRUE`. **Confirmed this is NOT a position-tracking bug**: `SEEK`
to computed positions ranging from just-past-end up to `1000` bytes
into a 6-byte file leaves `EOF()` unchanged (`FALSE`) every time — `SEEK`
by itself never sets the flag, no matter how far past the end. Only an
actual I/O attempt that hits the real end sets it, exactly like C's
`feof()` after `fseek()`. This is a well-precedented, ordinary I/O
pattern once recognized, not an emulator defect or a language design
flaw — it just surprises anyone expecting a look-ahead EOF check. This
means the naive loop idiom `WHILE NOT EOF(#path) DO READ #path,x ...
ENDWHILE` will always attempt one over-read on its final iteration and
needs an `ON ERROR GOTO` to catch it cleanly, or a different loop
structure (check `EOF` after the read, not before). `E$EOF` (211) is a
standard OS-9 system-level I/O error code (documented in
`common/error-codes.md`), not one of BASIC09's own low-numbered
compiler/runtime error codes — `READ`/`WRITE` surface it via `ERR` like
any other OS-9 file-manager error. (os9exec's own `pReof()` — `Source/
OS9exec_core/file_rbf.c` — does a straightforward `currPos>=lastPos`
position comparison and looks correct on inspection; BASIC09's `EOF()`
evidently isn't driven by a live call to that check the way a
look-ahead EOF would require, which is what produces this behavior.)

**`READ` is context-sensitive.** `READ var_list` (no `#path`) reads the next
`DATA` items. `READ #path, var` (with `#path`) reads from an open file
instead — same keyword, two unrelated behaviors depending on whether a path
number is given. (BASIC09 Reference Manual, Tandy ed., ch. 8 "Disk Files".)

### Sequential vs. random access files

BASIC09 has two file-access patterns that use different statement pairs and
store data differently — they are not interchangeable:

| | Sequential | Random access |
|---|---|---|
| Statements | `WRITE`/`READ` | `PUT`/`GET` |
| Storage format | ASCII text, CR (ASCII 13) delimits each record | Binary, exactly as BASIC09 stores it internally — no ASCII conversion |
| Record length | Variable | Fixed |
| Positioning | Sequential only — reaching EOF means reading through everything before it | Direct, via `SEEK` to any byte offset |

**Sequential:** `WRITE #path, data` appends data plus a trailing CR;
`READ #path, var` reads up to and including the next CR, stripping it. To
append to an existing sequential file, open with `UPDATE` mode and `READ`
through all existing records first — that's the only way to position at
EOF. **Gotcha:** using `INPUT` (not `READ`) against a file opened `UPDATE`
writes `INPUT`'s prompt text into the file itself, corrupting the data —
use `READ`/`WRITE`, not `INPUT`, for file I/O.

Overwriting sequential data in place only works if the replacement is
exactly the same byte length as the original (pad with spaces); a longer
replacement clobbers whatever data follows it in the file.

```basic
PROCEDURE addentry
  DIM lp: BYTE
  OPEN #lp, "notes": UPDATE      (* open existing file for read+write
  READ #lp, entry                (* advance past record 1
  READ #lp, entry                (* advance past record 2 — now positioned at EOF
  WRITE #lp, "checked equipment"
  WRITE #lp, "logged off shift"
  CLOSE #lp
END
```

**Random access:** record N of a fixed `record_length` lives at byte offset
`(N-1) * record_length` — `SEEK #path, (record_number-1) * SIZE(record)`
combines this with `SIZE()` to avoid hardcoding the length. `SEEK` can
target any byte, not just record boundaries, so a partial record can be
read/written mid-record. `PUT`/`GET` also work on whole arrays in one call
— storing or loading N records in a single bulk operation instead of
looping. Structured `TYPE` records combine naturally with this: dimension
an array of a `TYPE`, and `PUT`/`GET` moves whole records (or the whole
array) at once. `Live` (68k)
(`tools/benchmarks/basic09-randfile-test.bas`): pre-allocate several
empty `TYPE` records, `SEEK` to
a computed `SIZE()`-based offset, `PUT` a record there, `SEEK` back and
`GET` it — round-trips correctly, and a neighboring untouched record is
confirmed still empty (proves `SEEK`+`PUT` only touches its target, not
adjacent records).

```basic
PROCEDURE stockfile
  TYPE stock_rec = tag: STRING[16]; onhand, reorder: INTEGER; price: REAL
  DIM blank: stock_rec
  DIM sp: BYTE; n, slot: INTEGER

  CREATE #sp, "stock"
  blank.tag = "": blank.onhand = 0
  blank.reorder = 0: blank.price = 0
  FOR n = 1 TO 50
    PUT #sp, blank          (* pre-allocate 50 empty slots
    NEXT n
  ...
  SEEK #sp, (slot - 1) * SIZE(blank)     (* jump straight to record `slot`
  PUT #sp, blank                         (* one call writes the whole record
END
```

Pre-allocating every record (as above) before random-order updates avoids
EOF errors from `SEEK`ing past the current end of a sparse file.

(Mechanism per BASIC09 Reference Manual, Tandy ed., ch. 8 "Disk Files";
the example above is original, not the manual's own.)

## PRINT USING

**The format-string syntax uses directive LETTERS, not `#` placeholders.**
A generic-BASIC-style `"###.##"` format string was **never real BASIC09
syntax** — it fails at run time (`Error #000:063`) and is a
plausible-looking fabrication to guard against. The real syntax, confirmed
against the manual's grammar (`Manual`); `Live` (68k) end to end:

| Directive | Meaning | Syntax |
|---|---|---|
| `Rw.f[j]` | REAL (also works for INTEGER/BYTE) | width `w`, `f` fraction digits, optional justify `<`/`>` |
| `Ew.f[j]` | Exponential/scientific notation | same shape as `R` |
| `Iw[j]` | INTEGER (also BYTE, in-range REAL) | width `w` |
| `Hw[j]` | Hexadecimal dump of any type's internal bytes | width `w` |
| `Sw[j]` | STRING, padded/truncated to width `w` | `<` left (default), `>` right |
| `Bw[j]` | BOOLEAN — same shape as `S`, converts to a word | width `w` |

Justify `j`: `<` left, `>` right, `^` center. **The `^` resolves an OCR
ambiguity**: the manual's own text rendered this symbol as a garbled
"°" (degree sign), illegible as transcribed. `Live` (68k) to
settle it: `'%'` is a runtime syntax error (`Error #000:063`); `'^'`
compiles and genuinely centers — confirmed by exact byte capture, not
eyeballing: `"HI"` in an 8-wide `S8^` field produces `"   HI   "` (3
spaces each side). Control specs — `Tn` jumps to column `n`, `Xn` skips
`n` columns, `'literal string'` inserts fixed text — are allowed between
item specs and don't consume an entry from the output list. Repeat groups:
`N(spec,spec)`, nestable. **Path number placement**: `PRINT #path USING
fmt, list` — the `#path` comes right after `PRINT`, before `USING`, not
after it (`PRINT USING #path, ...` is a syntax error, `Error #000:018`).

`Live`, field-width-exact (captured via a file round-trip and
`LEN()`, not by eyeballing terminal spacing): `PRINT #path USING "R8.2",
12.349` produces an exactly-8-character field, correctly rounded to
`12.35`. `PRINT #path USING "I4", 10`, `"S8", "HELLO"`, `"H4", 100`
(→ `0064`, correct hex of 100) all compiled and ran with no error.

**Real divergence from the manual, not a test mistake:** the manual
states BOOLEAN format converts to the strings `"TRUE"` and `"FALSE"`
(uppercase). `Live` (68k): `PRINT #path USING "B8", TRUE`
produces `"True    "` — mixed case (capital T, lowercase `rue`), not
`"TRUE"`. Field width is still exactly correct (8 chars). Worth flagging
to the compiler's author directly — this is exactly the kind of
manual-vs-implementation gap a real 6809 build should be checked against.

```basic
PRINT [ print-list ]
PRINT [ #path ] USING format-string, print-list   ! e.g. PRINT USING "R8.2", price
```

**The separator between the format string and the value list is a
comma, not a colon** — the colon form (`PRINT USING "R8.2": price`) is a
compile-time syntax error (`Error #000:029`). The comma form is confirmed both by
the manuals' own formal grammar (`Manual`) and `Live` end to end
(see the directive-letter table and worked examples above — this is now
fully resolved, not just the separator).

`print-list` items are expressions or `TAB(expr)`. Plain `PRINT` behaves
like ordinary comma/semicolon-separated BASIC output; `PRINT USING` adds
a format string (field width, decimal places, etc.) controlling exact
layout — available identically in program code and in Debug Mode's
interactive `PRINT` command.

## Operators & Functions

Precedence, highest to lowest: `NOT` / unary negate; `^`/`**`
(right-to-left); `*`, `/`, `MOD`; `+`, `-`; comparisons; `AND`; `OR`;
`XOR`. Equal-precedence operators evaluate left-to-right except
exponentiation. **A negative base is not accepted for exponentiation
in BASIC09** (BASIC09 Reference Manual, Rev H) — the specific runtime
error code is unverified.

**AND/OR/XOR/NOT vs. LAND/LOR/LXOR/LNOT — easy to mix up.** AND/OR/XOR/NOT
are Boolean-only **infix operators** (`a AND b`, operands and result
TRUE/FALSE). LAND/LOR/LXOR/LNOT are **function calls, not operators** —
`LAND(a,b)`/`LOR(a,b)`/`LXOR(a,b)`/`LNOT(a)` — operating on integer values
bit-by-bit. **Writing `6 LAND 3` as if it were infix is a syntax error**
(`Live`: `Error #000:011`) — use `LAND(6,3)`. The `*NOT` member
of each family takes one operand, the rest take two. The names invite
confusion precisely because they look like variants of each other rather
than a different call shape entirely.

| Function | Effect |
|---|---|
| `FIX(realnum)` | Rounds a REAL to the nearest INTEGER — despite the name, NOT truncation. `Live`: `FIX(3.9)=4`, `FIX(3.1)=3`, `FIX(-3.9)=-4` (the negative case is the deciding one: truncation-toward-zero would give `-3`; only round-to-nearest gives `-4`). |
| `FLOAT(intnum)` | Converts INTEGER to REAL (adds `.0`) |
| `SUBSTR(search$, source$)` | Position of first occurrence of `search$` in `source$`, or 0; position numbering always starts at 1, unaffected by BASE mode (`Live`) |
| `SIZE(variable)` | Byte size of a variable/structure — common in pointer/record arithmetic, e.g. `SEEK #file, SIZE(record)*(index-1)`. Value is architecture-specific — see the per-architecture file. |
| `ADDR(var)` | Absolute memory address of a variable — not portable across targets, see `gotchas.md` |
| `SIN`/`COS`/`TAN`/`ASN`/`ACS`/`ATN`/`LOG`/`LOG10`/`EXP`/`SQR`/`SQRT`/`PI` | Transcendental, REAL result; angles in degrees or radians via `DEG`/`RAD`. Precision is architecture-specific — see the per-architecture file. Per the BASIC09 Reference Manual, all of these are derived internally via a CORDIC algorithm written specifically for BASIC09, rather than a lookup table or a standard math-library routine. `SQR` and `SQRT` are the same function — `Live` (6809): source typed as `SQR(x+1.)` is stored and `LIST`ed back as `SQRT(x+1.)`, confirming `SQR` is just an accepted abbreviation, not a distinct function. |
| `ABS`/`SGN`/`SQ`/`MOD` | Basic numeric functions |
| `RND(0)` / `RND(n>0)` / `RND(n<0)` | Random 0-1 / random 0-n / reseed with `ABS(n)` as the new seed. **`RND(n>0)` returns a REAL in `[0,n)`, NOT necessarily an integer** — `Live`: `RND(5)` returned `1.75959429`, a fractional value. Don't assume `RND(n)` gives a random integer 0..n-1 the way it does in some other BASICs; use `FIX(RND(n))` for that. **Reseeding is fully deterministic** (`Live`): calling `RND(-42)` then three `RND(0)` calls, twice in a row, produces the exact same 3-value sequence both times — useful for reproducible test data. |
| `LEN`/`MID$`/`LEFT$`/`RIGHT$`/`STR$`/`VAL`/`CHR$`/`ASC` | String functions |
| `DATE$` | Current date/time as `"YY/MM/DD HH:MM:SS"`. **Y2K-class bug on 68k** (`Live`): for years ≥ 2000 the year's tens digit is corrupt (`"<6/07/14"` where `"26/07/14"` was correct — first byte reads ASCII 60 `'<'`, a +10 offset from the un-reduced year value). `Absent` on real 6809 NitrOS-9 — the bug is specific to the 68k BASIC09 runtime's own formatting. Don't trust the 68k year field past 1999. Details: `gotchas.md` |
| `TRIM$(str$)` | Removes **trailing** spaces only — leading/embedded spaces are untouched, matching both manuals' description of the function. `Live`: `TRIM$("  hi  ")` = `"  hi"` (2 leading spaces survive). |
| `PEEK(address)` / `POKE address, value` | Direct memory access — not portable across targets, see `gotchas.md` |
| `LAND(a,b)`/`LOR(a,b)`/`LXOR(a,b)`/`LNOT(a)` | **Function calls, not infix operators** — see above |

## Error Handling

```basic
ON ERROR GOTO line_number             ! Set trap
ON ERROR                               ! Disable trap
ERROR expr                             ! Generate error with code
```

`ON ERROR GOTO` needs an explicit, typed-in line number as its target —
same requirement as `GOTO`/`GOSUB` (see above). `Live`: a
subscript-out-of-range error correctly transferred control to the trap
target and `ERR` correctly held the triggering error code.

Non-fatal errors trigger the trap (if set) or drop into Debug Mode
otherwise. **The claim that "a trap clears itself after firing once" does
NOT match live behavior.** Cleanly confirmed with a two-error test (two
separate `arr(99)=1` subscript-out-of-range triggers in the same
procedure, no `ON ERROR` call between them): the trap fired both times
(`hits=1`, then `hits=2`), with no re-arming in between. Treat
`ON ERROR GOTO` as remaining armed indefinitely until explicitly disabled
with a bare `ON ERROR` — it does not need to be (and is not) re-armed
after each trip.

**Divide-by-zero has two very different outcomes depending on type —
neither goes through the documented "Divide by Zero" error path in the
way you'd expect:**
- **INTEGER ÷ 0** (e.g. `i = i / 0` with `i: INTEGER`): `Live` (6809) —
  generates `Error #045 -- Divide by Zero` and drops into interactive
  Debug Mode if left unhandled, same as REAL÷0 on 6809. (68k behavior
  unverified; may differ.)
- **REAL ÷ 0** (e.g. `z = x / y` with `y: REAL` = 0): **used to crash the
  entire BASIC process** (`Error #000:107 (E_TRAPV) TrapV instruction
  TRAP 7 occurred`, `E_PRCABT(228)`) — a raw, uncatchable 68k CPU trap
  that `ON ERROR GOTO` never got a chance to run against. Root cause was
  an `os9exec` bug (four stacked `F$STrap` dispatch bugs), now fixed —
  see `basic09/gotchas.md`'s divide-by-zero entry. `REAL÷0` is now a
  catchable trap on 68k, matching 6809's always-catchable behavior
  (drops into interactive Debug Mode if left unhandled, same as
  6809's `Error #045`). **Still avoid REAL division where the divisor
  could be zero** — catchable now, but there is still no automatic
  recovery without an explicit `ON ERROR GOTO`.

## Debug Mode

| Command | Prompt/context | Effect |
|---|---|---|
| (interactive session) | `B:` System, `E:` Edit, `D:` Debug | The three modes — a reliable way to tell which mode a session is in |
| `PAUSE` (in source) | enters `D:` | Intentional breakpoint-like suspend, for inspection/single-stepping |
| `TRON` / `TROFF` | Debug | Trace: shows each statement before execution + its expression results on the next line; local to a procedure, stops at a call unless the callee also has trace on |
| `BREAK <procname>` | Debug | One breakpoint per active procedure, triggered when returned to via nesting; removes itself after firing once |
| `STATE` | Debug | Lists the call-nesting order — innermost (suspended) procedure at top, outermost at bottom |
| `STEP` / `STEP n` / bare CR | Debug | Executes 1 (or n) source statements; a FOR/NEXT structure line executes once per STEP, so loop "top"/"bottom" lines may not appear to repeat as expected |
| `LET var := expr` | Debug | Sets an existing variable (must exist in source already; no new vars, no record types) |
| `r [start[,incr]]` / `r*` | Edit | RENUMBER — default start 100, increment 10 |
| CONTROL-Q | any | Terminates execution, returns to System Mode — unlike CONTROL-C, does *not* enter Debug Mode; trappable via `ON ERROR GOTO` in RunB |

BASIC09's I-code interpreter does its own runtime checking (array bounds,
call-nesting depth, arithmetic errors, etc.) that a native machine-code
compiler typically wouldn't catch — a small performance cost in exchange
for not crashing on those classes of bug.

## Comments

`!` starts a comment — **but only as the first non-blank token on the
line.** Unlike most BASIC dialects (and unlike `basic09c`, the
independent native compiler — see `gotchas.md`), a real BASIC09
interpreter does not support a trailing comment after code on the same
line; `PRINT x ! note` is a compile error, not a stylistic choice.
`Live` on both real interpreters: rejected on
68k (`Error #000:029`) and on 6809 (`Error #034 -- Missing Left
Parenthesis` — different message, same rejection), in both cases with
the error caret landing right at the `!`. A standalone whole-line `!`
comment, by contrast, is completely fine anywhere a statement could go
— `LIST` always normalizes it to `REM <text>`, regardless of which
spelling appears in the source. See `gotchas.md` for a further,
`LOAD`-specific 6809-vs-68k divergence when the very first line of a
*file* is a comment.

## System Mode Commands

`$` (drop to shell), `BYE`, `CHD`, `CHX`, `DIR`, `EDIT`, `KILL`, `LIST`,
`LOAD`, `MEM`, `PACK`, `RENAME`, `RUN`, `SAVE`.

`PACK` converts a procedure already in the workspace into a non-listable,
non-editable form in place, trading away editability/debuggability for
IP-protected distribution — it does not speed up in-workspace execution.
`RunB` is the runtime-only executable for running a `PACK`ed/`SAVE`d module
standalone outside interactive `basic`. Full mechanism, invocation rules,
argument passing, the multi-procedure entry-point distinction
(`PACK proc1,proc2` vs. `PACK*`), and
known gotchas are all in `pack-and-runb.md`
— that's the single authoritative reference, not repeated
here.

A **Graphics Interface Module** exists on CoCo/Dragon (6809) systems for
this language, specific to those platforms' video hardware — see the
per-architecture file.

---

**Sources:** BASIC09 Reference Manual (Rev H) and "OS-9 BASIC User Manual"
(Revision G, 1991) — architecture-independent language mechanics, shared
across the 6809 and 68k editions, plus 5 authored BNF-grammar cards.
Numeric widths, the 6809/68k delta, and remaining platform-specific facts:
see `os9-68k-basic-cheatsheet.md`, `basic09-cheatsheet.md`,
`basic09-vs-68k-differences.md`, and `gotchas.md`.
