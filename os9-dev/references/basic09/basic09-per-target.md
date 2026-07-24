# BASIC09 per target — 6809 vs OS-9/68000

BASIC09 is the same language on both targets. **`basic09-language.md` is the
language reference** — syntax, control flow, procedures, I/O, functions,
error handling, debug mode — and none of it is repeated here. This file
covers only what differs: numeric widths and precision, the platform-specific
facts with no counterpart on the other side, and the 68k-only mechanism for
calling machine-language procedures from BASIC09.

**Verification:** 6809 INTEGER overflow and hex-constant sign are `Live`
(Microware BASIC09 "6809 VERSION 01.01.00" under NitrOS-9; harness:
`6809/using-nitros9-repl.md`); 6809 REAL width/range/precision are `Manual`,
not independently measured. 68k items are `Live` on os9exec unless marked
otherwise.

## Data types by target

| Type | 6809 | 68k |
|---|---|---|
| BYTE | 1 byte, 0-255 unsigned | same |
| INTEGER | 2 bytes, -32,768 to 32,767 | 4 bytes, -2,147,483,648 to 2,147,483,647 |
| REAL | 5 bytes, ~±1×10³⁸, ~9 decimal digits | 8 bytes, ~±2.2e-308 to ±1.8e308, ~14 digits |
| STRING | `STRING[len]`, default max 32; extends to 2880 chars | `STRING[len]`, default max 32 |
| BOOLEAN | 1 byte, TRUE / FALSE | same |

The STRING *terminator* differs as well — `$FF` on 6809, NUL on 68k, and none
at all when a string fills its declared maximum. Details and the byte dump:
`basic09-language.md`'s Data Types section.

## INTEGER: 16-bit → 32-bit

**Overflow is ordinary two's-complement wrap at each width, silent, no
error** — `Live` on real 6809 (`32767+1` → `-32768`), real 68k
(`2147483647+1` → `-2147483648`), and `basic09c` alike. This is the **#1
silent-bug source when porting**: the wrap *mechanism* is identical, so code
relying on the *width* still has to change even though nothing looks broken.

One manual defect, not a behavioral divergence: the 68k-era *OS-9 BASIC User
Manual* (ch. 9, p. 9-2) prints `2,147,483,648` — positive, a value a signed
32-bit INTEGER cannot hold — where its own "wraps around" wording implies the
negative result. The 6809-era manual (p. 7-2) uses the same sentence template
and gets it right.

**Hex constants carry the width, and the sign meaning flips with it.**
`$` prefix on both. On 6809 the literal is 16-bit, so **`$8000`-`$FFFF` read
as negative** (`Live`: `PRINT $FFFF` prints `-1`). On 68k the same literal
lives in `$0`-`$FFFFFFFF` with no sign-flip zone. Never compare a hex literal
across a 6809/68k boundary without an explicit cast.

This mirrors the C compiler's `int` widening from 2 bytes (6809) to 4 bytes
(68k) — same direction, independent source.

## REAL: proprietary 5-byte → IEEE-754 double

**6809** REAL is a proprietary 5-byte float: an 8-bit two's-complement
exponent plus 4 mantissa bytes (31 bits + sign). The BASIC09 Reference Manual
states the range directly as ~±1×10³⁸, ~9 decimal digits. A tighter-looking
"2.94e-39 to 1.70e38" figure is calculated from the bit layout rather than
manual-stated — prefer what the manual actually says.

**68k** REAL is a genuine IEEE-754 double (`Manual`, storage format `Live`):
sign in bit 7 of the first byte, an 11-bit exponent (bits 0-6 of byte 1 +
bits 4-7 of byte 2) biased by 1024, and a 52-bit mantissa with an implied
leading one. `PUT`ting `1.0` to a file wrote exactly `3F F0 00 00 00 00 00
00`. `SIZE()` returns 8 for a REAL and 4 for an INTEGER; `1./3.` at
`DIGITS 15` prints `.333333333488554`. The `DIGITS` statement (range 1-15)
controls both display precision and the precision of transcendental
calculations.

**But 68k REAL *arithmetic* runs at single precision** under os9exec's
default `math` module (`Flag`): `0.1+0.2-0.3` leaves a residual of exactly
2⁻²², not the ~1e-16 a 52-bit double would give. Consequences: `0.1+0.2 = 0.3`
compares **EQUAL**, and `1.0/3.0` yields ~9 good digits rather than 15. Not a
display artifact — `DIGITS 15` shows the same residual — and not
BASIC09-specific: os9exec's C `double` behaves identically, so this is the
shared soft-float `math` trap handler, not the CPU core. **BASIC09's fix is a
module swap:** `load /dd/CMDS/math881` before running `basic` upgrades REAL
math to the 68881 and drives that residual to exactly 0. Full analysis, and
the different fix a `cc`-compiled program needs (`-K=2F`, since it links
software FP statically and ignores the `math` module): `c/os9-c-cheatsheet.md`'s
data-types section. Whether real 68k OS-9's stock `math` module is also
single-precision is unknown.

Code relying on accumulated rounding or near-equality behaves differently
across targets — use tolerance comparisons on REAL, never `=`.

## 6809-only

- **Graphics Interface Module** — `RUN GFX(...)` / `RUN GFX2(...)`, specific
  to CoCo/Dragon video hardware and absent from the 68k line entirely.
  Calling it on 68k fails silently (function not found): no error, just a
  no-op or a crash depending on context. Guard or strip before porting.
  Function-by-function reference: `6809/gfx-windowing.md`.
- **`PACK` strips comments** — don't rely on them surviving into a
  distributed compiled program. (Architecture-neutral in principle; only the
  6809-era manual documents it.)

## 68k-only

### Toolchain

`Live`: 68k `basic` identifies itself as "Microware Basic V2.1", and `RunB`,
the standalone runtime-only interpreter, exists and works on a real `PACK`ed
module. A packed module is a *subroutine* module and cannot be run by name
from the shell — invoke it as `runb <name>`. It resolves through the module
directory (`F$Link`) first, then the *execution* directory (`F$Load`), never
the data directory. Module-format background: `common/module-format.md`;
packing mechanics and the resolution rules in full: `pack-and-runb.md`.

### Commands documented only in the 68k-era manual

These four appear in the *OS-9 BASIC User Manual* (Rev G, 1991) and not in
the 6809-era *BASIC09 Reference Manual* (Rev H). That is a 68k-manual-only
**documentation** footprint, not proof the 6809 edition lacks them — treat
6809-side absence as unconfirmed except where noted.

- **SHELL** — runs an OS-9 shell command from inside a *running* procedure,
  returning to BASIC once it completes. Distinct from `$`, which both manuals
  document identically as an interactive System-Mode-only gateway; SHELL
  looks like a genuine 68k addition exposing that gateway to program code.
  **It does exist on 6809 and really forks** (`Live`) — at a cost of roughly
  a quarter-call per second on a 2 MHz 6809; see `6809/using-nitros9-repl.md`.
- **CHAIN** — loads and runs another BASIC program in place of the current
  one. It does not return, unlike `RUN`.
- **Command-line PARAM** — when a BASIC program runs directly from the OS-9
  shell rather than via an internal `RUN`, arguments bind to `PARAM`
  declarations with no call-site parentheses (`filter 11+4 "this"+"that"`).
  The `PARAM` type signature decides whether an argument is read as string or
  numeric, so anything ambiguous (numeric strings, paths) must be quoted to
  force string interpretation. A missing parameter errors only if the code
  actually uses it; extra parameters are ignored.
  **The mechanism exists on 6809 too (`Live`), but numeric `PARAM`s are
  broken there.** A `PACK`ed module invoked bare (`progname 42`) correctly
  detects a *missing* argument (`Error #056 -- Parameter Error`), proving the
  shell-to-`PARAM` plumbing is present — but a *supplied* numeric argument is
  never decimal-parsed. Its raw ASCII bytes land in the `INTEGER` variable's
  2-byte storage: `progname 42` → `13362` (`$3432`, the bytes `'4'`,`'2'`),
  `progname 99` → `14649` (`$3939`). `STRING` `PARAM`s are unaffected (no
  parsing needed). 68k parses correctly. Not root-caused; `runb <name>
  <numeric-arg>` fails differently (`Error #000`), so treat that as a
  separate, undiagnosed failure mode.
- **INTEGER vs REAL performance** — 68000 machines run INTEGER operations as
  native instructions while REAL goes through library calls, roughly an order
  of magnitude slower. A careless decimal point (`value*2.` rather than
  `value*2`) silently promotes the whole expression to REAL. Type discipline
  is not optional in hot loops.

## Calling 68000 machine-language procedures from BASIC09

Genuinely 68k-only; the 6809 side has a different, C-specific `c-link`
mechanism (`c/os9-c-cheatsheet.md`) that does not apply here.

**The mechanism is just `RUN <name>(<params>)`** — the same statement used
for BASIC09-to-BASIC09 calls, no special syntax. If the named procedure isn't
in the workspace, BASIC checks whether it's already a loaded OS-9 module,
then falls back to loading it from the current execution directory. It
inspects the module's type: BASIC I-code gets interpreted, while **a 68000
machine-language module gets a `JSR` straight to its entry point**, returning
via a plain `RTS`. `KILL <name>` releases it afterward so its memory can be
reclaimed.

**Calling convention** (from the manual's stack-frame diagram):

- `D0` = parameter count; `D1` = address of the first parameter.
- On the stack above the return address: for each parameter *after* the
  first, a 4-byte length followed by a 4-byte address, in call order, toward
  higher addresses.
- **Error signaling:** set the carry bit in the CCR and put the error code in
  the low word of `D1`. On success, `RTS` with carry clear.
- By-value vs. by-reference doesn't change the layout — either way the
  routine receives an *address*. The difference is only what it points at:
  the caller's own storage, or a temporary copy BASIC09 made. Writing through
  a by-value parameter's address never propagates back, exactly as within
  pure BASIC09.

**Module header requirement:** type **`Sbrtn`** (subroutine), language
**`Objct`** (machine code), reentrant, with the module's own name as its
entry-point label.

**No worked example is reproduced from the manual** — its Appendix A
"SysCall" example is copyrighted Microware source. The examples below are
original.

`Live` — a minimal by-reference subroutine, assembled with `r68`, linked with
`l68`, called from a real BASIC09 procedure:

```asm
 nam addone
 ttl RUN addone(n) - increments n by reference
Sbrtn set 2
Objct set 1
ReEnt set $80
Type_Lang set (Sbrtn<<8)+Objct
Attr_Rev set (ReEnt<<8)+1
 psect addone,Type_Lang,Attr_Rev,0,0,addone
addone move.l d1,a0
 addq.l #1,(a0)
 rts
 ends
```

(`Sbrtn`/`Objct`/`ReEnt` are hand-defined rather than pulled from
`/h0/defs/oskdefs.d` via `use`; both give identical values, confirmed by
reading that file directly.)

```
r68 -O=addone.r addone.a
l68 -o=addonemod addone.r
```

`file` reports a genuine `OS9/68K module: re-entrant machine language
subroutine`. Called with `n=41`, `RUN addonemod(n)` then `PRINT n` prints
**`42`** — proving the whole documented mechanism, not just absence of a
crash: `D1` genuinely holds the first parameter's address, the write through
it genuinely propagates back to BASIC09's variable, and `RUN`/`JSR`/`RTS`
round-trip.

`Live` — a second example covering what the first can't: stack offsets for
parameters after the first, and a by-value argument.

```asm
 nam addmulmod
 ttl RUN addmulmod(a,b,sum,prod) - sum=a+b, prod=a*b
Sbrtn set 2
Objct set 1
ReEnt set $80
Type_Lang set (Sbrtn<<8)+Objct
Attr_Rev set (ReEnt<<8)+1
 psect addmulmod,Type_Lang,Attr_Rev,0,0,addmulmod
addmulmod move.l d1,a0
 movea.l 8(a7),a1
 movea.l 16(a7),a2
 movea.l 24(a7),a3
 move.l (a0),d0
 move.l (a1),d1
 move.l d0,d2
 add.l d1,d2
 move.l d2,(a2)
 muls.w d1,d0
 move.l d0,(a3)
 moveq #0,d0
 rts
 ends
```

`a` is by-reference (a bare variable), `b` by-value (a literal), `sum`/`prod`
by-reference outputs. `D1` holds `a`'s address per the base convention;
`8(a7)`/`16(a7)`/`24(a7)` are `b`/`sum`/`prod` — **verified offsets** for the
documented "4-byte length + 4-byte address per parameter after the first, in
call order, toward higher addresses" layout, rather than derived-and-never-
checked arithmetic. `RUN addmulmod(a,b,sum,prod)` with `a=6, b=7` prints
`13`, `42`; with `a=-3, b=10` it prints `7`, `-30`, confirming sign handling
through `muls.w` for this range.

### Calling a C function from BASIC09 (68k)

`Live`. BASIC09's convention (`D1` = address of first parameter) is *not*
Ultra C's compiled entry-point convention (`68k/os9-68k-assembly.md`), so a
small assembly shim bridges the two. A minimal K&R C function:

```c
addone_c(n)
int *n;
{
	*n = *n + 1;
}
```

compiled `cc -r -s addonec.c` (relocatable, no stack-check prologue — see
`c/os9-c-cheatsheet.md`). `l68 addonec.r` alone reports `no root psect
found`, which is expected and healthy for a pure-C object with no `psect` of
its own — confirmation it compiled, not a failure.

```asm
 nam cshim
 ttl RUN addonecmod(n) - calls C addone_c(n) by reference
Sbrtn set 2
Objct set 1
ReEnt set $80
Type_Lang set (Sbrtn<<8)+Objct
Attr_Rev set (ReEnt<<8)+1
 psect cshim,Type_Lang,Attr_Rev,0,0,cshim
cshim move.l d1,d0
 jsr addone_c(pc)
 rts
 ends
```

```
r68 -O=cshim.r cshim.a
l68 -o=addonecmod cshim.r addonec.r
```

Called exactly like the assembly-only example (`RUN addonecmod(n)` with
`n=99`) prints **`100`**.

**Gotcha — `jsr addone_c` without `(pc)` assembles but crashes at runtime.**
`r68` accepts a bare `jsr` to an external symbol and only warns `*** warning
- absolute addressing ***`; `l68` links it cleanly. But OS-9/68K modules are
pure position-independent code with no load-time base relocation: an
absolute-long JSR (`4eb9 <file-offset>`) jumps to that literal address in
real memory, landing wherever the module happens *not* to be loaded, and
crashes with an illegal instruction. **Any cross-object call inside a
reentrant module must use explicit PC-relative addressing** — `jsr
addone_c(pc)`, which `r68` encodes as `4eba <16-bit displacement>` with no
warning. Treat "absolute addressing" as a hard error, not a stylistic nit.

**Gotcha — a crashed module stays resident and shadows your rebuild.** After
a `RUN` crashes and aborts the process, the module often stays linked with a
nonzero use count. The *next* `RUN` of that name resolves via `F$Link`
(reusing the resident copy) rather than `F$Load` (reading the rebuilt file),
so a fix that is genuinely on disk and correctly relinked still crashes
identically. `unlink <modname>` doesn't reliably clear it — a dangling link
from the aborted process can survive — but a full `os9exec` restart does. If
a crash looks unchanged after a fix you know is correct, check `Last
syscall:` in the crash dump before doubting the fix: `F$Link` means you're
running stale bytes, `F$Load` means it's fresh.

**Gotcha — the `math` trap handler links lazily and fails misleadingly.**
BASIC09 links `math` (`TRAP #15`) the moment it first needs *any* numeric
handling, which includes compiling an ordinary `DIM x:INTEGER` — not just
REAL arithmetic. If `math` isn't resident and isn't reachable from the
current `CHX`, this fails with `**** Can't install trap handler ****` /
`Error #000:216 (E_PNNF)`, naming nothing about the module you were actually
trying to call, and can strike on the very first `LOAD` of any procedure
containing a numeric declaration. Fix: `load math` before doing anything
numeric, ideally in the startup file alongside `cio`/`csl`. The same banner
has other causes with different fixes — triage table in `pack-and-runb.md`.

---

**Sources:** BASIC09 Reference Manual (Rev H) — "Type INTEGER" p. 7-2, "Type
REAL" p. 7-3, Constants p. 7-6, and the 6809 Graphics Interface Module note.
OS-9 BASIC User Manual (Rev G, 1991) — ch. 2 p. 20/25, ch. 3 "Command Line
Parameters" p. 55-56, ch. 4 "Optimum Use of Numeric Data Types" p. 62, ch. 5
System Mode command summary p. 5-20, ch. 9 "Data Types and Data Structures"
p. 97-98 (INTEGER wraparound, REAL IEEE-754), ch. 11 p. 11-15 to 11-17 (RUN,
Calling External Procedures, the machine-language stack-frame diagram, KILL),
Appendix A p. A-19 (the "SysCall" example, described but not reproduced).
Language mechanics shared by both targets: `basic09-language.md`.
