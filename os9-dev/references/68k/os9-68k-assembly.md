# OS-9/68000 Assembly Language Reference

Scope: OS-9-specific 68k assembly facts (module mechanics, syscall
dispatch, register ABI, exception vectors). No surveyed source provides a
true 68k assembler manual — directive syntax has known gaps (listed at the
end); don't assume 6809 RMA syntax carries over. (The "Relocating Macro
Assembler" manual found in 68k archives is 6809-only — never a 68k
source.)

## Before you assemble anything

Five facts that decide whether your first build works. All are detailed
below; they are collected here because each bites *before* you have output
worth debugging.

1. **`I$`/`F$` call names are not symbols** — nothing on the SDK disk defines
   them. `dc.w I$Write` assembles clean and then fails at link. Define them
   as numeric constants in your own source.
2. **`l68 -o=<name>` sets the module's real internal name**, overriding the
   source's own `psect` name — so `mdir` shows the `-o=` name, not the one
   you wrote.
4. **The linker writes to the execution directory**, not your data directory.
   No error, no output where you looked.
5. **A PC-relative *destination* does not exist on the 68000** — `(d16,PC)`
   is source-only. Writing to your own storage needs `lea` then a write
   through the address register.

6. **Branch mnemonics already default to the 16-bit form** — so `.w` buys
   nothing. Bare `bcs`, `bra` and `bsr` all assemble as the opcode with a
   zero low byte plus a 16-bit extension word, byte-identical to the same
   mnemonic written `.w`, and a bare branch over a 210-byte gap assembles
   `Errors: 00000`. `.s` is the suffix that changes anything, emitting the
   2-byte short form. (Measured on r68 V1.9; `Live` (os9exec).)
7. **A diagnostic is printed BEFORE the source line it refers to**, with a
   caret under the offending column and no address/bytes field on that line:

   ```
   00004 0002 4e71            nop
   *** error - bad mnemonic ***
   00005  bogusop d0,d1
                  ^
   ```

   Read it the other way and you go hunting in the previous instruction.
   `Live` (os9exec).

Two directive traps in the same class: `dc.b "text"` needs double quotes
(single quotes fail for two or more characters), and `ds.b` is not valid in
code — reserve variables in a `vsect` instead, where it is (see "Variables
live in a `vsect`, addressed from A6" below). A third, harder to
place: **a label named `a0`-`a7` or `d0`-`d7` collides with the register
names**, and the complaint lands on the instruction that *references* the
label — `*** error - illegal addressing mode ***` — not on the label as a
duplicate symbol, so it sends you to read the wrong line. `Live` (os9exec).

## Toolchain (`Live` (os9exec), end-to-end)

- **`cc`** drives `cpp` → `c68` → `o68` → `r68` (assembler) → **`l68`**
  (linker), forking each by bare name via the execution directory (see
  `common/using-os9exec-repl.md`).
- **`l68`** error taxonomy — `Live` (os9exec): `file 'x.r' is not a
  relocatable module` = the input does not start like a ROF (a zeroed sync
  word, a large text file); `error reading input file` = a truncated ROF;
  `no root psect found` = nothing supplied an entry point. That last one is
  **not** a sign of a healthy object: an empty file and a one-line text file
  both get it, so `l68` on a single `.r` is no integrity check.
- **`LIB/cstart.r`** — prepended by the C driver at the front of every
  link list; supplies the root psect and the startup code that calls
  `main()`.
- **`debug`** — symbolic debugger; usage, and two known faults (`sc`
  addresses, `gs` stepping): `common/using-os9exec-repl.md`.
- **`r68 -O=` and `l68 -o=` overwrite an existing output cleanly** —
  `Live` (os9exec): three rebuilds under one name, longer, shorter and longer
  again, each ran the new text, on a host directory and on an RBF image. If
  a rebuild still seems to run old code, look for a **resident copy**
  (`mdir`) before blaming the file: a module that crashed stays in memory
  and shadows the rebuilt one (`basic09/basic09-per-target.md`).

## A complete worked program (`Live` (os9exec))

Everything else in this file is a contract; this is the idiom. The tables
below give the right register names but not the `psect` preamble, the
`trap #0` sequence, or the error convention — code written from the tables
alone names the right registers and still won't assemble. This is the
smallest program that exercises all three: it creates a file, writes a line,
closes it, then deliberately opens a file that does not exist.

```
Prgrm     set 1
Objct     set 1
ReEnt     set $80
Type_Lang set (Prgrm<<8)+Objct
Attr_Rev  set (ReEnt<<8)+1

ICreate   set $83
IOpen     set $84
IWrite    set $8A
IClose    set $8F
FPErr     set $0F
FExit     set $06

READ      set 1          access mode: read
WRITE     set 2          access mode: write
ATTRS     set $03        new file attributes: owner read + owner write
STDOUT    set 1          path 1 is always standard output

 psect exfileio,Type_Lang,Attr_Rev,0,1024,start

start
* I$Create(d0.b=mode, d1.b=attrs, d2.l=size hint, (a0)=path) -> d0.w=path
 lea    fname(pc),a0
 moveq  #WRITE,d0
 moveq  #ATTRS,d1
 moveq  #0,d2
 trap   #0
 dc.w   ICreate
 bcs    failed
 move.w d0,d7           keep the path number; d0 is scratch from here on

* I$Write(d0.w=path, d1.l=count, (a0)=buffer)
 move.w d7,d0
 lea    line(pc),a0
 move.l #linelen,d1
 trap   #0
 dc.w   IWrite
 bcs    failed

* I$Close(d0.w=path)
 move.w d7,d0
 trap   #0
 dc.w   IClose
 bcs    failed

 lea    okmsg(pc),a0
 move.l #okmsglen,d1
 move.w #STDOUT,d0
 trap   #0
 dc.w   IWrite

* Error path. Carry SET means the call failed and d1.w holds the code.
 lea    missing(pc),a0
 moveq  #READ,d0
 trap   #0
 dc.w   IOpen
 bcc    unexpected       succeeding here is itself the failure
 move.w d1,d6            save the code before anything else clobbers d1

 lea    experr(pc),a0
 move.l #experrlen,d1
 move.w #STDOUT,d0
 trap   #0
 dc.w   IWrite

* F$PErr(d0.w=error-message file path, 0=none; d1.w=error code)
 move.w d6,d1
 moveq  #0,d0
 trap   #0
 dc.w   FPErr

 moveq  #0,d1
 trap   #0
 dc.w   FExit

unexpected
 lea    unexpmsg(pc),a0
 move.l #unexplen,d1
 move.w #STDOUT,d0
 trap   #0
 dc.w   IWrite
 moveq  #1,d1
 trap   #0
 dc.w   FExit

failed
 move.w d1,d6
 lea    failmsg(pc),a0
 move.l #faillen,d1
 move.w #STDOUT,d0
 trap   #0
 dc.w   IWrite
 move.w d6,d1
 moveq  #0,d0
 trap   #0
 dc.w   FPErr
 moveq  #1,d1
 trap   #0
 dc.w   FExit

fname    dc.b "exfile.txt",0
missing  dc.b "no.such.file",0
line     dc.b "written by example-fileio",13
linelen  equ *-line
okmsg    dc.b "PASS create/write/close",13,10
okmsglen equ *-okmsg
experr   dc.b "PASS open of a missing file failed as expected: "
experrlen equ *-experr
unexpmsg dc.b "FAIL open of a missing file succeeded",13,10
unexplen equ *-unexpmsg
failmsg  dc.b "FAIL happy path: "
faillen  equ *-failmsg
 ends
```

Built and run, and what it actually printed:

```
r68 exfileio.a -O=exfileio.r
l68 exfileio.r -o=exfio1
exfio1

PASS create/write/close
PASS open of a missing file failed as expected: Error #000:216 (E_PNNF) Path Name Not Found
```

`dump exfile.txt` confirms the write landed byte-for-byte: 26 bytes,
`written by example-fileio` plus the trailing `$0D` — matching `linelen`.

What the program demonstrates that the tables alone don't:

- **The call code is an inline `dc.w` immediately after `trap #0`**, not a
  register argument. The kernel reads it from the instruction stream and
  resumes past it.
- **Names like `I$Create` are not symbols** — they must be `set` locally, as
  above. See the TRAP #0 section below for why nothing on the disk defines
  them.
- **Carry set = failure, `d1.w` = error code.** Save it immediately: the very
  next call overwrites `d1`. The program stashes it in `d6` before doing
  anything else. `F$PErr` then turns the code into the printed message.
- **`d0` is both an input and a result register.** `I$Create` returns the path
  number there, and every following call wants something else in `d0`, so the
  path is parked in `d7` first.
- **Reach your own data `(pc)`-relative via `lea`** — see the addressing-mode
  note under "Known gaps"; a PC-relative *destination* is not available.
- `r68` emits `*** warning - destination in short branch range ***` for each
  `bcs`/`bcc` here. It is a size hint, not an error (`Errors: 00000`); the
  `.s` form silences it. It fires whenever the target is close enough that
  `.s` *would* assemble, for the bare and `.w` spellings alike — but **not**
  when the target is the very next instruction, where the short form cannot
  encode it at all: shrinking the 4-byte word branch would put the target at
  displacement 0, and 0 is the reserved encoding meaning "use the word form".
  Which is why `bcs.s` to the immediately following label answers
  `*** error - branch out of range ***` — it reads like "too far" and means
  the exact opposite. `Live` (os9exec).
- **After `l68 -o=exfio1` the program was not in the data directory** — it
  landed in the execution directory, as the toolchain section above warns.
  `dir` showed only the `.a` and `.r`; the linked module ran by bare name.

### The rootless-object error (`Live` (os9exec))

`l68`'s "no root psect found" is worth causing once, so it's recognizable.
A `psect` whose type/language and attribute/revision operands are zero
assembles perfectly cleanly:

```
 psect noroot,0,0,0,0,0
```

```
r68 noroot.a -O=noroot.r
Errors: 00000

l68 noroot.r -o=noroot1
l68: error - no root psect found
```

The object is structurally valid — it simply declares no entry point, so
there is nothing for the linker to make a program out of. An assembler that
reports zero errors is not evidence that a module will link.

## System call mechanism (TRAP #0)

Full dispatch mechanism (`TRAP #0`/vector 32, the `OS9`/`tcall` macros,
the carry+`d1.w` error convention): `syscall-reference.md` — not
repeated here. Assembly/module-format-specific additions:

- By Microware convention `TRAP #13` is CIO and `TRAP #15` is the math
  trap (see `common/module-format.md`'s Math module section).
- **No file on this SDK's disk defines the I$/F$ call names as assemblable
  symbols** — `Live` (os9exec): `dc.w I$Write` assembles clean (`r68` treats an
  unresolved name after `dc.w` as an ordinary external symbol and defers
  to the linker with no warning), but `l68` then fails with `Symbol
  'I$Write' unresolved`. A search of the SDK's `DEFS` tree (`oskdefs.d`, `macros.d`,
  both the `os9lib` and `GCC2` header trees) finds `I$Open` only once, in a
  C comment in `funcs.h` beside `#define I_OPEN (0x84)` — a C constant under
  another name, not an assemblable symbol. `syscall-reference.md`'s call names must be
  hand-defined as numeric `EQU`/`SET` constants in your own source before
  assembling — they aren't pulled in from anywhere automatically. Numeric
  values match the standard published table (cross-checked against
  os9exec's call-number header, an independent reimplementation rather than
  Microware material): `I$Open=$84,
  I$Read=$89, I$Write=$8A, I$Close=$8F, F$Exit=$06`.
- If a program executes any `TRAP #1`-`#15` for which no handler has
  been installed, the kernel calls the module's own default trap-entry
  routine instead (the module header's `M$Excpt` field — lazy-binding
  mechanics: `common/module-format.md`'s Trap libraries section).

## Exception vector table (68k)

| Vector(s) | Name | Notes |
|---|---|---|
| 0 | Reset: initial SSP | Kernel uses this to find system-global base on every exception; requires 4K RAM below and above it. Never touch. |
| 1 | Reset: initial PC | Coldstart entry point; after boot, only used to restart after catastrophic failure. Never touch. |
| 2 | Bus error (`T_BUSERR`) | |
| 3 | Address error (`T_ADDERR`) | |
| 4 | Illegal instruction (`T_ILLINS`) | |
| 5 | Zero divide (`T_ZERDIV`) | |
| 8 | Privilege violation (`T_PRIV`) | Supervisor-state instruction executed in user state. 68000-era binaries have a specific trap here — see **Reading SR in user state** below |
| 9 | Trace | Single-step; `F$DFork`/`F$DExec`/`F$DExit` and the OS-9 debugger use this |
| 25-31 | Autovectored interrupts, levels 1-7 | Serviced through `F$IRQ`; level 7 (vector 31) is non-maskable and should not be used for ordinary devices — reserved for hardware the kernel doesn't need to coordinate with (e.g. DRAM refresh); a level-7 ISR must never call a system call or touch kernel data |
| 32 | `TRAP #0` — OS-9 system calls | See above |
| 33-47 | `TRAP #1`-`#15` — user trap handlers | Installed via `F$TLink` |
| 57-63 | 68070 on-chip autovectored interrupts, levels 1-7 | 68070 only |
| 64-255 | Ordinary vectored interrupts | |

Error exception vectors all dispatch through `F$STrap` and are normally fatal
— the offending process is terminated. Exception: if the process was created
via `F$DFork`, its state is preserved rather than torn down, and control passes
back to the parent debugger for a post-mortem look instead. The table above
shows only a subset.

### Reading SR in user state

`MOVE SR,<ea>` is a **user** instruction on the MC68000/MC68008 and privileged
only from the MC68010 on (`Manual`, Motorola M68000 Family PRM: the entry
headed MC68000/MC68008 in the integer chapter, and the 68010+ entry in the
supervisor chapter). Old compilers read SR to get at the condition codes — the
RTF Fortran run-time does — so on a 68010 or later that does not emulate the
instruction in its privilege-violation handler, as Motorola advised, such a
program dies at an ordinary-looking instruction with
`vector=$08 err=#000:108`.

Whether Microware's 68010+ kernels emulate it is unrecorded; CONF68K t50 run
on real hardware would settle it. os9exec emulates a 68020 and lets user state
read SR, delivering S clear (`Live` (os9exec), CONF68K t50).

`MOVE CCR,<ea>` is the 68010+ user-legal way to read the flags, and is not a
68000 instruction at all.

### What an `F$STrap` handler is handed

`Manual` (v2.4 TRM p. 1-60), and `Live` (os9exec) — CONF68K t55–t56, which
pass on big- and little-endian hosts alike. Runtimes depend on this contract,
so it is worth stating exactly:

| Register | On entry to the handler |
|---|---|
| `d7.w` | The exception's vector offset — which error this is |
| `(a0)` | The program counter at the exception. The manual notes this is the same value as `R$PC(a5)` |
| `(a1)` | The stack pointer at the exception (`R$a7(a5)`) |
| `(a5)` | The saved register image — the whole user register set |
| `(a6)` | The program's global data pointer |

To resume, restore the registers from the image at `(a5)` and jump to the PC.
To continue past a faulting instruction rather than retry it, advance the
saved `R$PC` first.

Do not confuse `(a0)` here with `F$STrap`'s own `(a0)` **input**, which is
something else entirely: the stack the handler is to run on, zero meaning
whichever stack is current when the call is made.

**Which vectors, exactly.** Two different facts are easy to conflate. The
*error-exception group* is **vectors 2–8, 10–24, 48–63** — the manual's own
section heading (`Manual`, v2.4 TRM p. 2-31) — and membership of it is what makes
an exception normally fatal. `F$STrap` then catches the members of that group
**considered non-fatal**, which p. 1-60 enumerates: bus error, address error,
illegal instruction, zero divide, CHK, TRAPV, privilege violation, line 1010 and
line 1111 (2–8, 10, 11), plus seven FPCP exceptions (48–54). So the wide range
is not wrong and the narrow list is not a contradiction — one is the group, the
other is the catchable part of it. The manual adds that not all catchable vectors
apply to every CPU: 48–54 are 68020/68030 only. (os9exec departs here: see
"Where os9exec departs from the manuals" in `common/using-os9exec-repl.md`.)

An IRQ service routine invoked by kernel interrupt polling receives
`(a2)` = driver static storage, `(a3)` = device port address, `(a6)` =
system global storage (a2/a3 are whatever was supplied at `F$IRQ`
installation time). It may destroy only `d0, d1, a0, a2, a3, a6`, and
reports whether it handled the interrupt via the carry flag: clear if
serviced, set if not (kernel continues polling the next handler). This is a
*different* register convention from the C-callable convention below —
don't mix the two up when an ISR calls into, or is called from, ordinary C.

## Register conventions (ordinary program modules, C-callable convention)

Documented in the OS-9 Primer's assembly-interface chapter, for 68k:

| Register(s) | Role |
|---|---|
| **D0, D1** | First two parameters in a subroutine call (D0 first, D1 second) |
| **D0** | Return value register; for 64-bit returns, D0 holds low 32 bits and D1 holds high 32 bits |
| **A5** | Frame pointer — used to address local variables and parameters |
| **A6** | Global-variable pointer — initialized to the base of the module's global/static data *plus* `0x8000`, enabling 16-bit signed offsets to reach a full 64K of globals |

The `+0x8000` bias is the key: it allows 16-bit signed offsets from A6 to address the entire 64K global region symmetrically around the bias point.

## Program entry register state (what a forked program sees)

When `F$Fork`/`F$Chain` transfers control to a module's execution entry
point (`M$Exec`), the kernel has already set up a specific register state —
distinct from both `F$Fork`'s *input* registers (what the parent passes, see
`syscall-reference.md`) and the C-callable convention above. The load-bearing
facts a program can rely on:

| Register | At entry |
|---|---|
| **A6** | global/static data base, biased `+0x8000` (as above) |
| **A7** | stack pointer (top of the process stack) |
| **A5** | base of the parameter area (initial SP) |
| **A1** | top of the process memory area (highest allocated address) |
| **A3** | pointer to the program's own primary module header |
| **D0** | the process's own ID |
| **D1** | packed group.user (owner) ID |
| **D2 / D3 / D5 / D6** | priority / # inherited paths / param-area size / total memory |

**Undefined at entry — never read before you write them: `A0`, `A2`, `A4`,
`D4`, `D7`.** A program that dereferences one is relying on luck: real
hardware leaves whatever happened to be there. os9exec fills them with
sentinel patterns (`$AAAAAAA0+n` in address registers, `$DDDDDDD0+n` in data
registers) so the mistake surfaces: an out-of-arena access through such a
register raises a 68k **bus error**. (The `pwrstat` utility has exactly this
latent fault: `MOVEA.L $4C(A0),A0` with `A0` still holding its `$AAAAAAAx`
sentinel.)

Slot assignments for the *informational* registers (which datum is in D2 vs
D5, etc.) vary between manual passages; **measured `Live` (os9exec)** via a debugger
register dump of a forked program: **D2 = priority (`$80` = 128, the default), D3 = # inherited paths
(`3` = stdin/out/err), D5 = param-area size, D6 = total memory** — exactly the
order the table above lists. The same dump confirmed the rest Live: **D0 = the
PID**, **D1 = packed owner** (`0` for a `0.0` super-user), and every
**undefined** register holding its sentinel — **D4=`DDDDDDD4`, D7=`DDDDDDD7`,
A0=`AAAAAAA0`, A2=`AAAAAAA2`, A4=`AAAAAAA4`** (the `$DDDDDDDn`/`$AAAAAAAn`
fill). The defined-vs-undefined split is also `Source` (os9exec's fork
register setup).

**`A5`'s actual content, `Live` (os9exec)**: a NUL-terminated string holding
exactly the typed command-line tail (e.g. `"hello"` for one argument —
confirmed via sanitized hex dump: `68 65 6C 6C 6F 00 0D 00 "PORT="...`),
safe to pass directly as a syscall's pathname pointer with no copying.
**With zero arguments, the first byte is a bare CR (`$0D`), not a NUL** —
checking only for a leading NUL to detect "no argument" misses this case
silently (wrong behavior at runtime, no assemble/link-time warning).
**Don't use `D5` to bound a raw read/write of the string** — a
NUL-terminated scan is the safe check. `D5`'s exact meaning is unresolved
(possibly the whole parameter+environment block size, not just the argument
text), and reading past the NUL using `D5` as
a byte count risks pulling in the environment-variable data that follows
it in memory.

Register conventions for device-driver and file-manager dispatch-table entry
points (Init/Read/Write/GetStat/etc., as opposed to the IRQ convention above
or the C-callable convention) are not attested anywhere in this rebuild's
four source clusters — that material lives in the sibling `os9-systems-dev`
skill, which should be treated as the authority for it rather than this
file.

## Embedded assembly in C

Two distinct mechanisms, from two different compiler generations — don't
conflate them:

- **6809 C compiler (`#asm` / `#endasm`):** a line beginning `#asm` switches
  the compiler into pass-through mode, copying subsequent lines verbatim to
  the assembly output until a line beginning `#endasm`. Compiler-generated
  code normally lives in the PSECT (code) section; if the embedded assembly
  switches to the VSECT (data) section, the programmer must emit an
  `ENDSECT` directive before `#endasm` so the section state is correct again
  for the compiler-generated code that follows. The exact section-directive
  names here are this (6809) compiler's own RMA convention and are not
  confirmed for the 68k toolchain.
- **Ultra C (68k), `_asm()`:** embeds assembly inline inside C code, but the
  compiler does not optimize the assembly, and surrounding C-code
  optimization can inadvertently damage it. Prefer separate assembly files
  or linking instead of embedding inside function bodies. (Ultra C 1.2+
  reportedly supports macro-form assembly inside functions.)

## Module structure an assembler/linker produces (68k)

Full header layout/offsets, type/language/attribute-byte tables, the
data-initialization and pointer-relocation tables, CRC/parity mechanics,
and the word-alignment padding rule: `common/module-format.md` — not
repeated here. What's specific to the assembler/linker's role in
producing this: an assembly-language program's `psect` declaration is
what populates these fields (even though, per "Known gaps" below, the
exact `psect` directive syntax isn't attested in this source set).

**One root psect per linked program:** only one ROF in a link may supply
a non-zero type/language/attribute/revision/edition — the "root psect" —
and it determines the whole output module's type/attributes/edition.
`cstart.r` supplies this for a C program and must be linked first; for a
hand-written assembly program, the programmer's own root psect plays that
role. `l68`'s "no root psect found" error is exactly what happens when no
linked object supplies one.

## Directive syntax: what is settled, and what is still open

No surveyed source is a real 68k assembler manual, so **nothing below rests
on a 68k directive reference.** Several of these were settled live anyway, and
each says so; treat only the ones marked open as unverified.

- Exact `psect`/`vsect`/`csect` directive syntax and parameter order (the
  documented PSECT/VSECT syntax is the **6809** RMA's) — **unverified as a
  manual citation, but resolved in practice**: the worked program above uses
  the 6-operand `psect` form and is `Live` (os9exec), and
  `basic09/basic09-per-target.md` has a second `Live` (os9exec) example of the same
  shape for a `Sbrtn` module.
- `ds.w`/`ds.l` and other data-definition directive syntax specifics —
  resolved, `Live` (os9exec): `dc.b 'ab'` (single-quoted, two or more
  characters) fails on `r68` with `*** error - value out of range ***`,
  while a single character (`dc.b 'x',0`) assembles, as a character
  constant; `dc.b "text"` (double-quoted) assembles clean — use double
  quotes for string data. **`ds.b`, `ds.w` and `ds.l` are rejected in a
  code `psect`** (`*** error - bad mnemonic ***`); **`ds.b` inside a
  `vsect` assembles clean** (`Live` (os9exec)), which is where uninitialised
  storage belongs.
- **Never write into the module itself.** `(d16,PC)` is a **source-only**
  addressing mode on the 68000, so `move.l d0,x(pc)` does not assemble
  (`Live` (os9exec): `*** error - illegal addressing mode ***`) — and
  the workaround of `lea x(pc),a1` then writing through `a1` is wrong on OS-9
  even though it assembles: a module is one shared, re-entrant copy (possibly
  in ROM) used by every process running it, and a write into it changes the
  code for all of them and breaks its CRC. Per-process variables go in the
  data area, below.
- **Variables live in a `vsect`, addressed from A6 — and A6 is not the
  start of your data.** At entry A6 is the data area's base **plus
  `$8000`** (`common/module-format.md`), so a plain `(a6)` or a small
  `N(a6)` points 32 KB *past* the start: with an ordinary 1-8 KB data area
  that is beyond its end, in whatever memory comes next, and a write there
  corrupts another module or process. OS-9 without an SSM does not stop it,
  and the damage shows up somewhere else entirely — a Microware utility
  misbehaving later, not your program failing. The correct forms:

  ```
   vsect
  count: ds.l 1
  buf:   ds.b 16
   ends
  ...
   lea    buf(a6),a0       the linker biases vsect offsets for the $8000
  ```

  `Live` (os9exec): the linked offset of the first `vsect` variable is
  `-$8000`, and `buf(a6)` reaches the right bytes. An explicit negative
  constant (`BUF equ -32700`) also works, but the `vsect` keeps the linker in
  charge of the layout.
- **Indexing from A6 needs a second register.** Because a `vsect` offset is
  near `-$8000`, the indexed form `tab(a6,d0.w)` (8-bit displacement) cannot
  encode it. `Live` (os9exec): **`r68` assembles it with `Errors: 00000`**,
  and only `l68` objects — `operand size error. The value ($ffff8000) is too
  large for a byte operand` — **and writes the module anyway**, so a build
  that checks for an output file passes. Use `lea tab(a6),a1` then
  `0(a1,d0.w)`.
- **A trailing colon makes a label externally visible** — `Live` (os9exec),
  confirmed via `l68 -s` and `debug`'s `sc` symbol
  listing. Colon-suffixed labels (`start:`, `sumloop:`) are
  debugger-/linker-visible symbols; colon-less labels are not — a build
  with only colon-less labels showed just the three universal symbols
  (`btext`/`bname`/`etext`) under `sc`, and adding colons made every
  intended label appear.
- The 68000 instruction set itself is out of scope here (sources assume
  Motorola knowledge and document only OS-9 extensions).
- Driver/file-manager entry-point register conventions live in the
  sibling `os9-systems-dev` skill, not here.

## Cross-references

- **The `psect` directive syntax gap above, resolved in practice —
  but only for `mod_exec`-shaped module types.**
  `basic09/basic09-per-target.md`'s "Calling 68000 machine-language
  procedures from BASIC09" section has a complete, `Live` (os9exec)-tested
  hand-written 68k assembly example (`psect addone,Type_Lang,Attr_Rev,
  0,0,addone` — the 6-operand shape is `name,typelang,attrrev,edition,
  stacksize,entry`) with real `r68`/`l68` invocations. `Live` (os9exec): this same
  shape assembles and links unchanged for `Prgrm` and `Drivr`-type modules
  too, not just the `Sbrtn` it was demonstrated with. The headers differ,
  though: for a `Drivr`, `l68` emits only 12 bytes after `$30` (`M$Exec`
  then 8 zero bytes; `ident` reports `68000 Dev Drv`, `Exec off $3C`), with
  no `M$Stack`/`M$IData`/`M$IRefs` — the `Prgrm` extension does not apply. **`Live` (os9exec), does NOT generalize to
  `Devic` (device descriptor) modules**: the 6-operand form
  unconditionally reserves the same 12 bytes of header padding before the
  psect body, but a device descriptor's real extended header
  (`M$Port`/`M$Vector`/`M$Mode`/`M$FMgr`/... — see the sibling
  `os9-systems-dev` skill's `device-drivers.md`) is a completely
  different shape at those same offsets, so this recipe silently
  misaligns a hand-authored descriptor. A shorter 4-operand `psect` line
  fails outright (`*** error - comma expected ***`); no working syntax
  for authoring a `Devic`-type module byte-accurately is known — open gap.
  For an ordinary `Prgrm` module, prefer the worked program near the top of
  this file; the `basic09-per-target.md` example matters when the target is
  a BASIC09-callable `Sbrtn`.
- **A linked module's registered name comes from `l68 -o=<name>`'s
  output-file argument, not from the source's `nam`/`psect` name
  operand.** `Live` (os9exec): linking the same object twice under two different
  `-o=` names produced two modules with two different `M$Name` strings
  (confirmed via `mdir`/`dump`), regardless of what the source's `nam`
  directive said. Matters for anyone installing a driver/descriptor under
  a specific required name.
- Per-call register-level parameter detail for individual system calls:
  `syscall-reference.md` (this directory)
- Device driver/file manager authoring (entry-point skeletons, static
  storage layout, `F$IRQ` wrapper patterns): sibling `os9-systems-dev` skill
- Compiler/linker toolchain and the `debug` command:
  `c/os9-c-cheatsheet.md` and `common/using-os9exec-repl.md`

Sources: The OS-9 Guru (68000-specific chapters); OS-9 v2.4 Technical
Reference Manual (module format, exception vectors, TRAP conventions);
OS-9 C Compiler manual / The OS-9 Primer (register ABI, embedded
assembly). Toolchain behavior: `Live` (os9exec).
