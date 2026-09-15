# OS-9 C Compiler Cheatsheet (68k)

**Every `Live` tag here is `Live` (os9exec).** No 6809 C compiler was
available to this project — the 1983-manual column below is `Manual`.

## Setup

**Before any of this works you need a running OS-9 system and Microware's
compiler.** Neither ships with this material: `cc`, `cpp`, `c68`, `o68`, `r68`
and `l68` are proprietary Microware programs that come from a licensed SDK or
disk image. Getting from an emulator plus such an image to the shell prompt these
commands are typed at is covered in `common/using-os9exec-repl.md` — read that
first if you do not already have a prompt. The commands below assume one.


```bash
chx /h0/CMDS
setenv CLIB /h0/LIB
setenv CDEF /h0/DEFS
```

`CLIB` (must contain `cstart.r`, `clib.l`) and `CDEF` (header files) are
required. OS-9 requires `chx` — the execution directory — to include the
compiler's directory (so it can fork its sub-tools: preprocessor, assembler,
linker, etc.).

## One Complete Example

`[clean-room]` — a full compile-and-run session, not copied from any manual.

```c
/* hello.c */
#include <stdio.h>

main()
{
    printf("Hello from OS-9\n");
}
```

Source files need CR-only line endings before compiling. If the file was
authored on the host (LF endings), convert first:
```bash
flip -m hello.c
```
Then compile and run:
```bash
cc hello.c
hello
```
`cc hello.c` produces an executable module named `hello` (no separate link
step for a single file). The compiler automatically links `LIB/cstart.r`
first—a startup routine built from `C/SOURCE/cstart.a` that initializes
the program and calls `main()`. This is the actual OS-9 entry point.

## Pitfalls

These are the ones that actually cost time — read this before anything else
in this file:

- **`int` is 32-bit on 68k** (`Live` (os9exec), via `sizeof()` on a real 68k
  toolchain), same as `long` and any pointer. Some documentation
  describes a 16-bit `int` — that's the *6809* compiler's data model, not
  68k's. The same applies to floating point: the 6809 compiler's `float`/
  `double` are a proprietary sign-magnitude format, not IEEE 754 — don't
  assume that carries over to 68k either. Don't trust a data-representation
  claim without confirming which architecture's manual it came from (see
  the data-types reference table below).
- **`\n` is CR (0x0D), not LF** — matches OS-9's own line convention, but
  will silently produce the wrong bytes if you're thinking in Unix terms.
  **`Live` (os9exec)**: `putc('\n', f)` to a file wrote the
  single byte `0x0D` (the file read back `58 0D 59` for `X`,`\n`,`Y`) — the
  compiler maps the escape to CR at compile time; a raw `putc(0x0A, f)` stays
  `0x0A`, so there is no I/O-layer translation, it is purely what `\n` compiles
  to.
- **`<strings.h>`, not `<string.h>`** — different API (`index`/`rindex`,
  not `strchr`/`strrchr`); see `os9-clib-reference.md`.
- **Link installed programs `-qm` (trap-free), never `-qixm`.** This is the
  costliest trap in the C toolchain, it does not announce itself, and on at least
  one SDK a `-qixm` build is broken **by construction rather than by choice**.

  The mechanism, `Source` (both sides disassembled): a cio-linked program reaches
  the C library through `TRAP #13` with a selector word. Two library vintages
  exist and the maximum selector in a program's stub table identifies which it
  linked — **`$45` is the 70-entry library and matches the modules; `$44` is the
  69-entry library and does not.** Every `cio` module agrees with the stub table up
  to `$40` and then carries **five memory routines at `$41`..`$45`**, where the
  69-entry library expects `_flshbuf` and `_filbuf`.

  So a program calling `$41` to flush a buffer lands on the module's raw
  allocator, which reads `d0` as a byte count while `d0` actually holds the
  `FILE *`. The allocation *succeeds*, so the call appears to return a pointer,
  the `FILE`'s `ptr`/`end` are never updated, the next `putc` takes the slow path
  again — and **every character leaks a fresh chunk until the arena is gone**,
  which is what produces a flood of `No more memory !!!`.

  Measured, `Live` (os9exec), from `putchar('x')` four thousand times:

  | Build | x's written | `No more memory !!!` |
  |---|---|---|
  | `-qixm` | **2** | **3920** |
  | `-qm` | 4002 | 0 |

  And the syscall trace makes the per-character leak direct rather than inferred:
  the `-qixm` build issues **4001 `F$SRqMem` calls, one per `putchar`**, each
  asking for **413,256 bytes**, never returning one, until the 32 MB arena is
  gone — against just **2 `I$WritLn`**, which is why exactly two characters reach
  the terminal. That 413,256 *is* the `FILE` pointer read as a byte count, and it
  was proven to be an address by moving the heap under it and watching the
  "size" follow.

  **Do not try to fix it with a bigger buffer.** `-qixm=4k`, `=16k` and `=64k`
  behave identically, to the same counts. It is not a size problem.

  Why the library and not the module is the variable: in the **matched** vintage
  `putc`/`getc` compile to ordinary function calls (`$12`/`$09`) and the buffering
  happens inside the module, consistently. In the **mismatched** vintage the
  header *inlines* them and the slow path reaches `$41`/`$42`. Across 353
  cio-linked programs on one collection, **no** program from the 70-entry library
  calls `$41`/`$42` and **all 41** that do came from the 69-entry one.

  Two consequences worth knowing before you debug this:

  - **Comparing module CRCs will tell you nothing.** The modules are identical
    between SDK and collection; the mismatch is between a module and the
    *library* a program was linked against. `ident` cannot see it.
  - **`cio020` fails differently** — its table stops at `$40`, so it cannot serve
    `$41` at all and wild-jumps rather than flooding.

  And one false lead: a program making many large identical allocations is not
  necessarily this. `ksh` issues 188 requests of ~262 KB from `malloc` (`$3B`)
  reaching the module's own allocator — one chunk, reused, working correctly. From
  outside it looks exactly like the fault.

- **A usage message is not proof a program works**, and for the class above it
  is specifically misleading: a usage line proves only that **argument parsing
  ran**. The failure is later, at first file I/O, and the exit status is still 0 —
  so neither the banner nor `$?` can see it. **The sound test is whether a
  redirect target was actually created and written**: give the program real input,
  send its output to a file, and check the file. Better still, assert the
  *content* of the answer — that `2^200` comes back as its 61 digits — rather
  than that output merely exists.
- **CLIB/CDEF must be set correctly** or the linker/preprocessor can't find
  their inputs — errors here look like missing-file errors, not
  environment errors.
- **Register variables: 6809 vs. 68k behavior differs sharply.** On 6809,
  one register variable per function is allowed; only `int`, `unsigned`, and
  pointer types are valid. Invalid declarations (a second `register` variable,
  or an unsupported type) aren't rejected — they're silently downgraded to
  ordinary `auto` storage with no error. On 68k (Ultra C), the compiler
  completely ignores programmer `register` declarations and determines
  register placement itself — any `register` keyword is a no-op.
- Language-syntax gotchas (K&R-only function definitions, no
  `const`/`volatile`, etc.): `kandr-vs-ansi.md`.
- **Linking against anything beyond the default `CLIB`** (e.g. termcap
  functions `tgetent`/`tgetstr`/`tputs`, which need `termlib.l`) needs an
  explicit extra-library flag — `Live` (os9exec): `cc`'s own documented
  `-L=<name>` is broken/not forwarded correctly (`l68: error - unknown
  option -L`). Use lowercase `-l=<full-path-to-file.l>` instead (matches
  `l68`'s own flag, which `cc -?` doesn't fully list — run `l68 -?`
  separately if a flag doesn't seem to exist): `cc -l=/h0/LIB/termlib.l
  file.c`. A bare name like `-l=termlib` fails to open — needs the full
  path.
- **Mixing compiler/linker and runtime-library "generations" breaks with
  a specific, identifiable error**, not a vague one: `l68: error - psect
  'cstart_a' in file '<path>/cstart.r' created by assembler too new for
  this linker`. This means the `l68` you're using and the `cstart.r` it's
  linking against came from different SDK releases — get a matching pair
  (same release's `l68` + `cstart.r`/`clib.l`), don't mix an older
  compiler pipeline with a newer runtime lib or vice versa. On this
  project the actual sub-tool names present are `cpp`/`c68`/`c68020`/
  `o68`/`r68`/`r68020`/`l68`. **Resolved, not an unreconciled SDK variant**:
  the toolchain-components table below listing different names
  (`c.prep`/`c.pass1`/`c.link` etc.) is the separate 6809 toolchain's own
  component naming, cross-architecture noise from this file's sole
  C-compiler-manual source being the 1983 6809 edition — see that table's
  own header note.
- **Embedded assembly is compiler-generation-specific and easy to get
  burned by.** The old 6809-era `#asm` / `#endasm` pragma just switches the
  compiler into pass-through mode (copy lines verbatim to the assembly
  output); Ultra C's 68k `_asm()` function is a different, later mechanism
  entirely — and critically, the compiler does *not* optimize the assembly
  inside it, so surrounding-code optimization can inadvertently damage it.
  Prefer separate assembly files/linking over embedding assembly in a C
  function body; only from Ultra C 1.2 onward is macro-form assembly
  inside functions supported. See the reference section below for both
  mechanisms' details.

## Microware `cpp` is pre-ANSI: three measured divergences

Each of these is legal C that this preprocessor rejects or quietly mishandles,
and each was measured `Live` (os9exec) with `cc -qm=16k` against the SDK. They
surface immediately on Unix code and nowhere on your development host, so when a
port fails in the preprocessor, check all three before suspecting the code.

### `#include<file.h>` needs the space

`Live` (os9exec), `cc -qm=16k` against the SDK. `#include<stdio.h>` is rejected
outright:

```
nospace.c : line 1 **** incorrect include file syntax ****
#include<stdio.h>
         ^
```

The caret sits on the `<`. The identical file with `#include <stdio.h>` compiles
and runs. This `cpp` requires whitespace between `include` and the delimiter,
where a C89-conforming preprocessor does not.

It costs nothing to comply and it is the **first** error you hit on code written
the other way, so it masks everything after it — fix all of them before reading
any other diagnostic from the file.

### `#undef` before redefining a macro: it keeps the first definition

`Live` (os9exec), measured with two probes, `cc -qm=16k` against the SDK:

- `#define answer() 42` with **no earlier definition**, then `printf("%d",
  answer())` prints `42`. Zero-argument function-like macros expand normally.
- `#include <stdio.h>`, then `#define getchar() 7` with **no `#undef`**, then
  `printf("%d", getchar())` with stdin on `/nil`. `cpp` warns `**** redefined
  macro ****` and the program prints `-1` — stdio's `getchar` reading EOF. **The
  new definition was ignored and the first one stayed in force.**

So the diagnostic is real and the redefinition is not. **`#undef` before
redefining any macro, library or not.** It is one line and it is the difference
between your definition being used and silently discarded.

This is a legitimate reading of the standard rather than a defect — redefining a
macro with a different body requires a diagnostic, and what happens next is not
guaranteed — so do not expect a host compiler to reproduce it. A host `cpp` that
takes the *second* definition will hide the bug on your development machine and
surface it only on OS-9.

**What it looks like when it bites: nothing.** A rogue 5.3 port put `#define
getchar() md_getchar()` in a header included after `<stdio.h>`. The one warning
scrolled past, the build linked, and in play no key did what it should — every
keystroke behaved as though stdio's `getchar` was still in force, because it was.
Adding `#undef getchar` on the line above fixed input entirely.

### An object-like macro is not rescanned with the `(` that follows it

`#define P putchar` and then `P(65)` fails:

```
pobj.c : line 5 **** macro arguments required ****
putchar
         ^
```

The echoed line shows why: `P` expanded to `putchar`, and the `(65)` sitting
right after it in the source was never joined to it, so the function-like
`putchar` macro from `<stdio.h>` was left without arguments. A conforming
preprocessor rescans the replacement together with the rest of the source and
finds that `(`.

**The fix is to make the macro function-like**: `#define P(x) putchar(x)`
compiles and prints as expected. The general rule — **an object-like macro whose
expansion names a function-like macro will not pick up arguments from the call
site** — so give the wrapper the parameters instead of relying on the rescan.

This one is worth knowing by name because the error names `putchar`, which is
correct and unhelpful: the macro at fault is `P`, and `P` appears nowhere in the
diagnostic.

## Big data: the 64K wall, and `remote`

Two walls stop a port with large buffers, and they are the same wall twice:

- **Static data over 64K** — `l68` refuses with
  `non-remote data allocation exceeds 64k`.
- **A stack local past a 16-bit displacement** — the assembler refuses with
  `*** error - value out of range ***`.

The cause is the addressing mode, and it is already documented in
`68k/os9-68k-assembly.md`: globals are reached A6-relative, with A6 biased by
`+0x8000` so that a **16-bit signed** offset spans a full 64K and no more. Stack
locals are reached the same way from the frame pointer. Anything that will not fit
in that window cannot be addressed by the ordinary mode.

**`remote` is the escape, and Microware's `c68` supports it** — `Live` (os9exec),
measured with `cc … -qm=16k`:

- **File scope.** `remote char big[300000];` compiles, links and runs: writing
  `big[0]` and `big[299999]` and printing both works.
- **Function-local static.** `static remote char buf[200000];` inside a
  non-recursive function, called twice, returns the right values across both
  calls.

This is what a Unix port with real buffers needs — agrep 2.01 carries over a
megabyte of file-scope arrays and 98K of locals, and hits both walls without it.

**Two things not established**, so do not assume either way:

- whether an `extern` declaration of a remote array must itself say `remote`;
- whether **initialized** remote data is accepted in a program module. There is a
  lead rather than an answer: Microware's Enhanced OS-9 release notes record that
  `l68` "will now correctly report when remote initialized data exists as well as
  non-remote initialized data, **when it is not allowed for certain module
  types**", fixed in `l68` edition 151. That says such a restriction exists and
  that older linkers mis-reported it — it does not say which module types, and
  those notes document a **v3.2-era** system that this reference otherwise keeps
  out of scope, so treat it as a pointer for testing rather than as the rule
  here. `Flag`.

## Reference: Calling Conventions (68k)

Register usage when C calls (or is called from) assembly:

| Register | Role |
|---|---|
| D0, D1 | First two parameters passed to a subroutine call (D0 first, D1 second) |
| D0 | Also doubles as the function return value (low 32 bits, for a 64-bit return value; D1 holds the high 32 bits in that case) |
| A5 | Frame pointer — locals and parameters are addressed relative to A5, set up by the `link` instruction |
| A6 | Global variable pointer — initialized to the base of globals plus `0x8000`, so 16-bit signed A6-relative offsets can reach a full 64KB of globals |

Source: *The OS-9 Primer*, Chapter 12 ("Register conventions").

## Reference: Embedded Assembly

Two unrelated mechanisms, from two different compiler generations:

| Mechanism | Compiler | Behavior |
|---|---|---|
| `#asm` ... `#endasm` | 6809-era Microware C | Pass-through mode to assembler. Compiler generates PSECT; if your assembly uses VSECT, insert `ENDSECT` before `#endasm` to reset section context. |
| `_asm()` | Ultra C (68k) | Function-style assembly embedding. The compiler does **not** optimize it; surrounding optimizations can damage it. Prefer separate assembly files. Supported in function bodies from Ultra C 1.2 onward. |

Sources: OS-9 C Compiler manual, "Imbedded Assembly Language", p. 1-4; *The
OS-9 Primer*, Chapter 12 ("Placing assembly directly within a C code
module").

## Reference: Data Types — 6809 vs. 68k

The only C compiler manual behind this reference is the **1983 6809**
manual. Its data-representation claims are 6809-specific and do **not**
carry over to 68k — `Live` (os9exec) (verified via `sizeof()` on a real 68k
toolchain): `int`, `long`, and pointers are all 32-bit there, not the
16-bit `int` the 6809 manual describes.

| Type | 6809 compiler (1983 manual) | 68k (`Live` (os9exec) where noted) |
|---|---|---|
| `char` | 1 byte | 1 byte |
| `int` | 2 bytes | **4 bytes** (`Live` (os9exec)) |
| `unsigned` | 2 bytes | presumably 4 bytes (follows `int`; not independently spot-checked) |
| `long` | 4 bytes | 4 bytes (`Live` (os9exec)) |
| `float` | 4 bytes — proprietary sign-magnitude binary format (exponent biased by 128, 3-byte mantissa with implied leading 1), **not IEEE 754** | **4 bytes, IEEE-754 single (`Live` (os9exec))** — a C `float`=1.0 stored `3F 80 00 00` (big-endian), textbook IEEE single. NOT the 6809 proprietary format |
| `double` | 8 bytes — same proprietary format, 7-byte mantissa | **8 bytes, IEEE-754 double (`Live` (os9exec))** — a C `double`=1.0 stored `3F F0 00 00 00 00 00 00` (big-endian), textbook IEEE double |

**`float`/`double` *storage* is IEEE-754, but *arithmetic* is single-precision
on os9exec (`Live` (os9exec)).** A `double` computation loses precision to
about single-precision magnitude: `0.1+0.2-0.3` (and the runtime-computed
`1.0/10.0+2.0/10.0-3.0/10.0`, so it isn't constant-parsing) yielded a 2⁻²²
residual — `0.1+0.2 != 0.3` is still true (C does a real IEEE compare, unlike
BASIC09's tolerant `=`), but you get ~7 good digits, not ~16. This is the
default soft-float math (the `math` trap handler), shared with BASIC09 REAL, and
it's fixed at compile time — `load math881` at runtime does NOT change an
already-compiled program (`Live` (os9exec)). **To get full precision, compile for the
68881 FPU: `cc -K=2F` (`-K=2` = target 68020, `F` = 68881; uses the `c68020`/
`r68020` passes).** `Live` (os9exec): with `-K=2F`, the runtime-computed
`1.0/10.0+2.0/10.0-3.0/10.0` gave a residual of **exactly 0** (the 68881's 80-bit
extended precision — even tighter than 64-bit double), vs 2⁻²² without it. So the
68881 emulation is accurate; the single-precision default is a `math`-trap
limitation, not the CPU core. See `basic09/basic09-per-target.md`.

On the 6809 compiler only, `SHORT`/`SHORT INT` are synonyms for plain
`int`, `LONG INT` is a synonym for `long`, and `LONG FLOAT` means `double`
(PDP-11-derived naming). That compiler's manual also documents BASIC09's
`INTEGER` as identical to its 2-byte `int`, and BASIC09's `BYTE`/`BOOLEAN`
as identical to `char` — an equivalence that assumes the 6809 sizes and so
does not hold on 68k.

**String termination differs between the two languages, and this bites
in practice.** A C string is NUL-terminated (`0x00`); a BASIC09 STRING is
terminated by a sentinel byte **whose value differs by target** — and
**`$FF` is the 6809 value, NOT 68k's.** `Live` (byte-dump of a
`PUT` on 68k os9exec): a `STRING[8]` set to `"XY"` after being filled with
`"ABCDEFGH"` stored `58 59 00 44 45 46 47 48` — i.e. `"XY"` then a **`00`
(NUL)** terminator (overwriting the old `C`), so **68k BASIC09 terminates a
STRING with NUL, not `$FF`.** **A BASIC09 string at its declared maximum
length still has no terminator byte at all** (`Live` (os9exec): a `STRING[3]` set to
`"XYZ"` stored exactly `58 59 5A`) — so a C function reading a BASIC09 STRING
must check the declared length as well as scanning for the terminator, and
the terminator to scan for is `$FF` on 6809 but `0x00` on 68k.

**Multi-dimensional arrays are stored in opposite element order.**
BASIC09 stores a multi-dimensional array column-wise; C stores the same
shape row-wise. Concretely: BASIC09's `DIM array(5,3):INTEGER` and C's
`int array[5][3];` do NOT lay out memory the same way, and accessing the
same logical element requires transposed subscripts — BASIC09's
`array(4,2)` is C's `array[2][4]`, not `array[4][2]`. Passing a
multi-dimensional array between the two languages without accounting for
this silently reads/writes the wrong elements. **`Live` (os9exec)**:
a `DIM m(2,3):BYTE` filled `m(i,j)=i*16+j` and `PUT` to a file stored
`11 21 12 22 13 23` — i.e. `m(1,1),m(2,1),m(1,2),m(2,2),m(1,3),m(2,3)`, the
first subscript varying fastest, confirming BASIC09's column-major layout.

Sources: OS-9 C Compiler manual, "Data Representation and Storage
Requirements", p. 1-5, and "Interfacing to BASIC09", p. C-1
(cross-checked against the same appendix restated cleanly at
https://hathaway3.github.io/nitros9A/ccguide/basic09/ — surviving OCR
scans of this appendix mangle the string "BASIC09" badly).

## Reference: Toolchain Components (6809 — do not blend with the live 68k chain above)

**This table is 6809-specific**, not this file's 68k subject: it's sourced
from the 1983 6809 C Compiler manual (this file's only C-compiler-manual
source — see `Sources:` below), and its component names don't match the
`Live` (os9exec)-verified 68k sub-tool chain used throughout the rest of this
file (`cpp`→`c68`/`c68020`→`o68`→`r68`/`r68020`→`l68`, driven by `cc`; see
`Setup` above and `68k/os9-68k-assembly.md`). Kept here for reference since
`c-link`/`c.link` naming shows up in mixed-architecture archives, but treat
it as describing the 6809 toolchain's own internal component names, not an
alternate name for any 68k tool.

| Component | Purpose |
|-----------|---------|
| `cc` / `cc2` | Driver program; `cc` is two-pass, `cc2` is single-pass. Identical from the command line. |
| `c.prep` / `c.preq` | Macro preprocessor |
| `c.pass1` / `c.comp` | Initial compilation phase |
| `c.pass2` | Second pass (`cc` only) |
| `c.opt` | Assembly code optimizer |
| `c.asm` | Relocating assembler (generates `.r` files) |
| `c.link` | Linker (generates executable modules) |

## Reference: File Suffixes

| Suffix | Meaning |
|--------|---------|
| `.c` | C source file |
| `.a` | Assembly language source |
| `.r` | Relocatable module (intermediate) |
| none | Executable binary (OS-9 memory module) |

Multiple sources compile and link together: `cc prog1.c prog2.c prog3.c`

## Reference: Compiler Flags

**Letters are from the 1983 6809 manual; the punctuation observed on 68k is
`=`.** The `Live` (os9exec) invocations elsewhere in this skill use
`-f=<path>` and `-l=<path>` — lowercase, with an equals sign — so treat the
bare `-F<name>`/`-M<n>` forms below as the manual's notation, not a
verified 68k spelling. Confirm the exact form with `cc -?` (and `l68 -?`)
before scripting one.

| Flag | Effect |
|---|---|
| `-A` | Skip assembler step; output remains as assembly code (.a files) |
| `-R` | Suppress linking; outputs `.r` relocatables instead of an executable |
| `-Es<n>` | Set the module header edition number |
| `-F<name>` | Override output filename |
| `-O` | Run the optimizer. On 6809 this typically shrinks code ~11%; 68k behavior not documented. |
| `-P` | Enable profiler (function call-frequency stats) |
| `-M<n>` / `-M<n>K` | Compile-time memory allocation, in pages or KB (linker ignores requests under 256 bytes) |
| `-l=<full-path>` | Link extra library. The documented `-L=<file>` flag is broken in `cc` (not forwarded to linker); use lowercase `-l=<full-path-to-file.l>` instead (bare names fail — needs absolute path). |
| `-C` | Emit source as comments alongside assembler output |
| `-S` | Suppress stack-checking code — only with time-critical code whose stack usage is fully understood |
| `-D<id>` | Equivalent to `#define <id>`, for `#ifdef`-controlled compilation |

## Reference: Calling C from BASIC09 (6809 only — see below for 68K)

**This entire section is 6809-only.** Its source, the C Compiler
manual's "Interfacing to BASIC09" appendix, is a Radio-Shack/CoCo 6809
document (explicit 6809 references, zero 68000 mentions) despite
sometimes circulating in 68k archive folders. `c-link`, named throughout
below, is a 6809 tool — it does not exist on 68k SDKs (exhaustively
searched on a real 68k disk image). **For 68K, use the `Live` (os9exec) method
in `basic09/basic09-per-target.md`'s "Calling 68000
machine-language procedures from BASIC09" section instead**: compile
the C function with ordinary `cc -r -s`, then hand-write a small
assembly shim (assembled with `r68`, linked with the ordinary `l68` —
no special tool needed) that translates BASIC09's own calling
convention into a call to the compiled C function. That section has a
complete, `Live` (os9exec) worked example.

The rest of this section is kept for 6809 work and for historical
context on how the *concept* carries over (the mechanism below and the
68K one solve the same problem — bridging BASIC09's calling convention
to C — with different concrete tools).

The C Compiler manual's "Interfacing to BASIC09" appendix documents a
distinct build path for a C function BASIC09 can call directly via `RUN`.
This is a genuinely different workflow from an ordinary standalone C
program — a normal `cc`/`l68` build won't produce something BASIC09 can
link to.

**Build steps:**
1. Compile with `-r` (leave a relocatable `.r` file, don't link) and `-s`
   (suppress stack-checking code — required, since the module won't have
   the normal stack-check runtime support).
2. Link with **`c-link`**, not the ordinary linker — `c-link <file.r>
   -b=<entry-function> -o=<output-module-name>`. `-b=` names which C
   function is the entry point BASIC09's `RUN` calls; `-o=` names the
   resulting OS-9 module. `RUN <output-module-name>(...)` from BASIC09
   then invokes it.

**Why the different build path:** skipping `cstart.r` means nothing runs
the usual startup work — statics are never zeroed/initialized, and the
stack-check helper the compiler normally calls into doesn't exist. A
BASIC09-callable C module has to supply its own stand-ins (a dummy
`_Stkcheck` routine, an `errno` storage cell) for anything the C library
code it calls expects to find.

**Parameter-passing convention:** BASIC09 passes parameters to the C
function on the stack as: a 2-byte count of how many parameter pairs
follow, then one (address, size) pair per argument. Because of this, **a
BASIC09-callable C function should declare every parameter as a pointer**
(`int *arg`, not `int arg`) — the compiler then generates the correct
dereferencing code, and the count/size values are typically unused unless
you want to validate what was actually passed.

**Static data needs an explicit BASIC09-side memory block, not `static`
declarations.** Since there's no `cstart.r`-provided static-data area, a
function needing persistent storage takes an extra pointer parameter (a
memory block BASIC09 allocates and passes in), and the *first* statement
in the function must be inline assembly loading that pointer from a fixed
stack offset (`6,8` in the appendix's example) before anything else runs.
Link with `-rot` to have `c-link` report the exact byte size BASIC09 must
allocate for this block; the BASIC09 side then `DIM`s an array of that
size, zero-initializes it, and passes it as the function's first
argument.

**Converting between BASIC09 REAL and C `double`:** these are different
binary formats (see the data-type table above) and need explicit
conversion functions on the C side (traditionally named `getbreal`/
`putbreal` in the manual's example) that manipulate the byte layout
directly — there's no automatic coercion crossing the language boundary.

*(Some of this appendix's example C source is badly OCR-corrupted in this
project's extracted source and wasn't independently re-verified beyond
what's stated here — treat exact variable names/offsets in a from-scratch
attempt as needing a fresh check against the real manual, not this
summary, if precision matters.)*

---

**Sources:** Official Microware C Compiler manual (1983, 6809,
Radio-Shack/CoCo-branded) and "The OS-9 Primer" (documents the later
"Ultra C" 68k compiler and its register conventions). 68k data-type
sizes: `Live` (os9exec), confirmed on a real toolchain, not just documentation. The
68K way to call C from BASIC09 (`basic09/basic09-per-target.md`)
is `Live` (os9exec), not `Manual`.
