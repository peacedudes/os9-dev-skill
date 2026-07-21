# BASIC09 (6809) vs OS-9/68000 BASIC — Numeric & Platform Deltas

## Scope

This file covers only what the source manuals actually confirm as a
6809-vs-68k delta: the two numeric type widths, and four commands/behaviors
documented solely in the 68k-era manual. Everything else about BASIC09's
syntax and behavior is architecture-neutral — see `basic09-language.md`
for the language itself; it isn't repeated here.

## INTEGER: 16-bit -> 32-bit

- **6809 BASIC09:** INTEGER is 16-bit signed, 2 bytes, range -32,768 to
  32,767. Overflow (e.g. 32,767+1) silently wraps modulo 65,536 with no
  error — values in 32,768-65,535 read back as negative. Hex constants
  (`$` prefix) range `$0000`-`$FFFF`, so `$8000`-`$FFFF` are read as
  negative values.
- **68k BASIC:** INTEGER is 32-bit signed, range -2,147,483,648 to
  2,147,483,647. Hex constants range `$0`-`$FFFFFFFF`.
- **Overflow is ordinary two's-complement wrap at each width, no error,
  on both architectures** — `Live` on real 6809, real 68k
  (`os9exec`), and `basic09c` alike (`32767+1` → `-32768` at 16-bit,
  `2147483647+1` → `-2147483648` at 32-bit). The 68k-era "OS-9 BASIC User
  Manual" (Chapter 9, p. 9-2) has a typo here — it says `2,147,483,648`
  (positive) instead of the negative result its own "wraps around"
  wording implies (a signed 32-bit INTEGER can't even hold that value).
  The 6809-era manual (p. 7-2) has the same sentence template and gets
  it right. Not a real behavioral divergence — just a sloppy manual,
  everyone's arithmetic agrees.

This mirrors the project's separately-confirmed finding that the C
compiler's `int` widens from 2 bytes (6809) to 4 bytes (68k) — same
direction, independent source.

## REAL: 5-byte -> 64-bit

- **6809 BASIC09:** REAL is a proprietary 5-byte float — an 8-bit
  two's-complement exponent plus 4 mantissa bytes (31 bits + sign). The
  BASIC09 Reference Manual states the range directly as ~±1×10³⁸ (~9
  decimal digits of precision) — a tighter-looking "~2.94e-39 to 1.70e38"
  figure sometimes seen is merely calculated from the bit
  layout rather than manual-stated — prefer what
  the manual actually says.
- **68k BASIC:** REAL is a 64-bit (8-byte) float. Range roughly
  ±2.2e-308 to ±1.8e308; ~14 decimal digits of precision. The `DIGITS`
  statement controls how many significant digits PRINT/Debug-Mode output
  displays, and also controls the precision of transcendental function
  calculations (SIN, COS, LOG, etc.)—range 1 to 15 digits.
- **IEEE-754** (`Manual`): the OS-9 BASIC User Manual documents 68k REAL as
  a standard IEEE-754 double-precision float — sign in bit 7 of the first
  byte, an 11-bit exponent (bits 0-6 of byte 1 + bits 4-7 of byte 2) biased
  by 1024, and a 52-bit mantissa with an implied leading one. Unlike the
  6809's proprietary format, this one is a real, standard IEEE-754 double —
  bit-for-bit rounding behavior should follow normal IEEE-754 semantics.
  **`Live`, 2026-07-21 — storage format confirmed, but arithmetic precision
  diverges (os9exec):** a byte-dump settles the format — `PUT`ting `1.0` to a
  file wrote exactly **8 bytes `3F F0 00 00 00 00 00 00`**, the textbook
  IEEE-754 *double* encoding of 1.0. So the **storage format is genuine IEEE
  double** (Manual confirmed, now `Live`). **But the *arithmetic* runs at
  single precision** (`Flag`): `0.1+0.2-0.3` evaluates to
  `2.384185791015625e-7` — *exactly* 2⁻²², a single-precision-magnitude
  residual, not the ~1e-16 a 52-bit double would leave. This is **not** a
  display artifact — `DIGITS 15` shows the same residual to full width, so the
  computation itself lost the precision. Consequences: `0.1+0.2 = 0.3` compares
  **EQUAL** (the residual is below single-precision resolution) and `1.0/3.0`
  gives ~9 good digits, not 15-16. So on os9exec, **68k BASIC REAL stores as
  double but computes at single precision** — don't rely on bit-for-bit
  IEEE-double arithmetic. **`Live`, 2026-07-21 — NOT BASIC09-specific:** the
  same C test (`c/os9-c-cheatsheet.md`) shows os9exec's **C `double` arithmetic
  is also single-precision** — `0.1+0.2-0.3` (and even the *runtime*-computed
  `1.0/10.0 + 2.0/10.0 - 3.0/10.0`, ruling out constant-parsing) stored a
  residual of exponent −22 (`3E 90 ...`, i.e. 2⁻²²), where a full-double result
  would be ~2⁻⁵⁴. So this is os9exec's **shared default soft-float math** (C and
  BASIC09 alike) computing at single precision, not a BASIC09 quirk. **The
  precision is fixed at compile/link time, not by a runtime module choice:**
  `Live`, `load math881` at runtime did NOT change an already-compiled C
  program's residual (still 2⁻²²). The 68881 FPU is accurate (`Live` elsewhere,
  project memory `fpu-68881-verified-accurate`) but reaching it needs
  FPU-targeted *compilation*, not just loading `math881`. Remaining open
  questions: the exact FPU-compile mechanism, and whether real 68k OS-9
  soft-float is also single-precision or this is an os9exec math-library gap.

## 68k-only documented commands

These four items appear only in the "OS-9 BASIC User Manual" (Revision G,
1991) excerpt on hand; the 6809-era "BASIC09 Reference Manual" (Rev H)
excerpt doesn't mention them. That's evidence of a 68k-manual-only
*documentation* footprint, not proof the 6809 edition lacks all of them —
treat 6809-side absence as unconfirmed rather than established, except
where noted.

- **SHELL statement** — runs an OS-9 shell command from inside a *running*
  BASIC procedure (launches an external program, then returns control to
  BASIC once it completes). This is distinct from the `$` command, which
  both manuals document identically as an interactive System-Mode-only
  gateway to the OS-9 shell — so SHELL specifically looks like a genuine
  68k addition making that gateway available to program code, not just
  interactively.
- **CHAIN** — loads and runs another BASIC program in place of the
  current one; it does not return, unlike RUN (which calls a procedure
  and returns).
- **Command-line PARAM** — when a BASIC program runs directly from the OS-9
  shell (not via internal `RUN`), parameters flow in through `PARAM`
  declarations without call-site parentheses, e.g. `$ filter 11+4 "this"+"that"`.
  The type signature in PARAM decides whether an argument is interpreted as
  string or numeric — arguments that look ambiguous (numeric strings, paths)
  must be quoted to force string interpretation. Inside BASIC, calling the same
  procedure via `RUN name(arg1, arg2)` works normally with parentheses and
  inlined type conversion. Accessing a missing/uninitialized parameter causes
  a runtime error only if used in code; extra parameters are safely ignored.
  **This mechanism does exist on 6809 too (`Live`) — but
  numeric `PARAM`s are broken there.** A `PACK`ed module invoked bare
  (`progname 42`) correctly detects a *missing* argument (`Error #056 --
  Parameter Error`), so the shell-to-`PARAM` plumbing is genuinely present
  — but a supplied numeric argument never gets decimal-parsed. Instead the
  argument's raw ASCII bytes land directly in the `INTEGER` variable's
  2-byte storage: `progname 42` → `13362` (`0x3432`, i.e. the bytes `'4'`,
  `'2'`), `progname 99` → `14649` (`0x3939`). `STRING` `PARAM`s are
  unaffected (no parsing needed — the text just gets copied). 68k performs
  real decimal parsing and gets this right. Not yet root-caused (untested:
  whether `runb`'s own numeric-argument path shares the bug — a quick
  `runb <name> <numeric-arg>` probe returned a distinct `Error #000`
  rather than the same mis-parse, so treat that as a second, separate
  failure mode until someone investigates it directly).
- **INTEGER vs. REAL performance** — 68000-based machines execute INTEGER
  operations through native CPU instructions, but REAL values must go through
  library calls, a substantially slower path. This speed difference is dramatic—
  roughly an order of magnitude. A careless decimal point in an expression
  (`value*2.` rather than `value*2`) will trigger silent REAL conversion of the
  whole expression, destroying hot-loop performance. Type discipline on numeric
  calculations is not optional on this platform.

## Calling 68000 machine-language procedures from BASIC09

This is a genuinely 68k-only capability with no 6809 equivalent
documented in any source surveyed here (the 6809 side has its own,
different, C-specific `c-link` mechanism — see `c/os9-c-cheatsheet.md`
— which does not apply here).

**The mechanism is just `RUN <name>(<params>)`** — the same statement
used for ordinary in-workspace BASIC09-to-BASIC09 calls, no special
syntax. If the named procedure isn't in the workspace, BASIC checks
whether it's already loaded as an OS-9 module, then falls back to
loading it from the current execution directory. It then inspects the
module's type: a BASIC I-code module gets interpreted normally, while
**a 68000 machine-language module gets a `JSR` straight to its entry
point**, running as native code. The routine returns to BASIC via a
plain `RTS`. `KILL <name>` releases it
afterward, same as any other external procedure — do this once it's no
longer needed so its memory can be reclaimed.

**Calling convention (from the manual's own stack-frame diagram):**
- `D0` = parameter count
- `D1` = address of the first parameter
- On the stack, above the return address: for each parameter after the
  first, a 4-byte length followed by a 4-byte address, in call order,
  going toward higher addresses.
- **Error signaling**: on error, set the carry bit in the CCR and put
  the error code in the low word of `D1`. On success, just `RTS` with
  carry clear.
- Whether a parameter was passed by value or by reference (BASIC09's
  usual distinction — a bare variable/array/structure name is by
  reference, a constant or expression is by value) doesn't change this
  layout: either way the routine receives an *address* of the value.
  The difference is only what that address points to — the caller's own
  storage (reference) or a temporary copy BASIC09 made (value) — so
  writing through a by-value parameter's address never propagates back
  to the caller, exactly as within pure BASIC09.

**Module header requirement**: the module must be assembled/declared
as type **`Sbrtn`** (subroutine), language **`Objct`** (machine code),
reentrant, with the module's own name as its entry point label — the
same `psect <name>,(Sbrtn<<8)!Objct,...` shape used for other
BASIC09-linkable modules documented elsewhere in this skill.

**No worked example is reproduced here** — the manual's own Appendix A
example ("SysCall," a generic OS-9 syscall dispatcher reached via
`RUN SysCall(Code,Regs)`) is copyrighted Microware source and isn't
copied into this skill; it demonstrates the same convention above
(parameter-count/length checks against `D0`/the stack offsets, the
`Sbrtn`/`Objct` module header, carry+`D1` error return) plus a more
advanced runtime-code-patching technique this note doesn't need to
repeat to be useful.

`Live` — the mechanism works exactly as documented
above. A minimal originally-written 68k assembly subroutine was
assembled (`r68`), linked (`l68`), and called from a real BASIC09
procedure on `os9exec`:

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

(`Sbrtn`/`Objct`/`ReEnt` are hand-defined here rather than pulled from
`/h0/defs/oskdefs.d` via `use` — both give identical values, confirmed
by reading that file directly: `Sbrtn equ 2`, `Objct equ 1`,
`ReEnt equ $80`.)

Assembled and linked with:
```
r68 -O=addone.r addone.a
l68 -o=addonemod addone.r
```
`file` confirms the result is a genuine `OS9/68K module: re-entrant
machine language subroutine`. Called from a BASIC09 procedure:
```
PROCEDURE asmtest
DIM n:INTEGER
n=41
RUN addonemod(n)
PRINT n
END
```
prints **`42`** — proving the full documented mechanism end-to-end, not
just "it doesn't crash": `D1` genuinely holds the address of the first
parameter, the assembly's write through that address genuinely
propagates back to BASIC09's own variable (by-reference semantics), and
`RUN`/`JSR`/`RTS` round-trip correctly.

**Second worked example, closing a real gap** — `addone` only exercises
a single by-reference parameter, so it never demonstrates the stack
offsets for a second-and-later parameter, or a by-value argument. `Live`:

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

`a` is by-reference (a bare variable), `b` by-value (a literal), `sum`/
`prod` by-reference outputs. `D1` still holds `a`'s address per the base
convention; `8(a7)`/`16(a7)`/`24(a7)` are `b`/`sum`/`prod`'s addresses —
confirming the documented "4-byte length + 4-byte address per parameter
after the first, in call order, toward higher addresses" layout with
real, verified offsets rather than derived-but-never-checked arithmetic.
Called as `RUN addmulmod(a,b,sum,prod)` with `a=6, b=7`: prints `13`,
`42` (sum, product). Cross-checked with a negative operand (`a=-3,
b=10`): `7`, `-30` — confirms sign handling through `muls.w` for this
value range. Both runs succeeded first-try.

**A real, separate gotcha found while live-testing this**: BASIC09
lazily links the `math` trap-handler module (`TRAP #15`) the moment it
first needs any numeric handling — which includes compiling an ordinary
`DIM x:INTEGER` / assignment, not just REAL arithmetic. If `math` isn't
already resident and isn't reachable from the current `CHX`, this fails
with a **misleading-looking** `**** Can't install trap handler ****` /
`Error #000:216 (E_PNNF)` that has nothing to do with the module you're
actually trying to call — it can strike on the very first `LOAD` of any
procedure containing a numeric declaration. Fix: `load math` (or ensure
`CHX` points somewhere `math` is reachable from) before doing anything
numeric in BASIC09 — preloading it in the startup file alongside
`cio`/`csl` is the standing remedy. The same error text has other causes
with different fixes — triage table in `pack-and-runb.md`.

`Live` — calling a real C function from BASIC09
via a hand-written assembly shim. The natural continuation of the
above: BASIC09's own convention (`D1`=address of first parameter) is
*not* the same as Ultra C's compiled entry-point convention (see
"Register conventions (ordinary program modules, C-callable
convention)" in `68k/os9-68k-assembly.md`), so a small shim bridges the
two. A minimal K&R C function:

```c
addone_c(n)
int *n;
{
	*n = *n + 1;
}
```

compiled with `cc -r -s addonec.c` (relocatable, no stack-check
prologue — see `c/os9-c-cheatsheet.md` for these flags). `l68
addonec.r` alone reports `no root psect found`, which is expected and
healthy for a pure-C object with no `psect` of its own — confirmation
it compiled, not a failure.

The shim, assembled and linked against that object:
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
`file` confirms a genuine re-entrant machine-language module. Called
exactly like the assembly-only example above (`RUN addonecmod(n)` with
`n=99`) prints **`100`**.

**Gotcha #1 — `jsr addone_c` (no `(pc)`) assembles but crashes at
runtime.** `r68` accepts a bare `jsr addone_c` to an external symbol
and only warns `*** warning - absolute addressing ***` — it doesn't
error. `l68` links it cleanly too. But OS-9/68K modules are pure
position-independent code with no base-relocation fixup at load time:
an absolute-long JSR (`4eb9 <file-offset>`) jumps to that literal
address in real memory, not module-relative, landing wherever the
module happens *not* to be loaded and crashing with an illegal
instruction. **Any cross-object call inside a reentrant module must use
explicit PC-relative addressing** — `jsr addone_c(pc)` — which `r68`
encodes as `4eba <16-bit displacement>` with no warning at all. Treat
the "absolute addressing" warning as a hard error for anything meant to
run as a loaded module, not a stylistic nit.

**Gotcha #2 — a crashed module can stay resident and shadow your
rebuild.** After a `RUN` crashes and aborts the process, the module
often stays linked in memory with a nonzero use count. The *next* `RUN`
of the same module name resolves via `F$Link` (reusing the resident
copy) rather than `F$Load` (reading the freshly rebuilt file from
disk) — so a fix that's genuinely on disk and correctly relinked can
still crash identically, because the interpreter is still running the
old bytes. `unlink <modname>` from the shell doesn't reliably clear
this (a dangling link from the aborted process can survive it); a full
`os9exec` restart does. If a crash looks unchanged after a fix that you
know is correct, suspect this before doubting the fix — check `Last
syscall:` in the crash dump: `F$Link` means you're looking at a stale
module, `F$Load` means it's genuinely fresh.

---

**Sources:** BASIC09 Reference Manual (Rev H) — "Type INTEGER" p. 7-2,
"Type REAL" p. 7-3, Constants p. 7-6; "OS-9 BASIC User Manual" (Revision
G, 1991) — Chapter 2 p. 20 & p. 25, Chapter 3 "Command Line Parameters"
p. 55-56, Chapter 4 "Optimum Use of Numeric Data Types" p. 62, Chapter 5
"System Mode" command summary p. 5-20, Chapter 9 "Data Types and Data
Structures" p. 97-98 (INTEGER overflow wraparound, REAL IEEE-754 format),
Chapter 11 "Program Statements and Structure" p. 11-15 to 11-17 ("RUN",
"Calling External Procedures", the machine-language stack-frame diagram,
"KILL") and Appendix A p. A-19 (the "SysCall" example, described but not
reproduced above).
