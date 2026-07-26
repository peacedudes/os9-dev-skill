# OS-9/6809 Assembly, Editor, and Debugger

Assembler directives, MOD/EMOD module-header mechanics, the `SWI2`+code
dispatch, and the full debugger command set are `Live` (NitrOS-9) against a real
toolchain. The Editor section is `Manual`.

Register set and calling convention: `syscalls-and-module-format.md`.

## Before you assemble anything

Six facts that decide whether your first build works. All are detailed
below; they are collected here because each one bites *before* you have
any output to debug.

1. **You cannot `use /dd/defs/os9defs.a` with `asm`** — it is RMA source and
   produces a cascade of `bad instr`. Define the constants you need yourself.
2. **There is no `OS9` macro either** — the raw form is `swi2` followed by a
   one-byte `fcb` call code.
3. **Use `-O=<name>`, not `O=<name>`** — the leading dash overwrites; without
   it an existing output file fails the run. Case is not significant.
4. **The object lands in the execution directory (`/dd/cmds`)**, not your data
   directory. `dir` where you are makes every successful run look failed.
5. **Never redirect `asm`'s standard output.** Errors go there, so a broken
   assembly looks silent and successful.
6. **Check the error count, not whether an output file appeared** — `asm`
   writes an object even when the assembly failed, and it will `ident`
   cleanly and then fail at run time on something unrelated.

One more bites *after* a clean build: **`*` is the program counter, `.` is
the data counter.** Using `*` for the `mod` directive's data-size operand
assembles cleanly and yields a module with a zero-sized data area.

## A complete worked program (`Live` (NitrOS-9))

Assembled with `asm` and run on NitrOS-9. It creates a file, writes a line,
closes it, then deliberately opens a file that does not exist. The 68k
counterpart is in the sibling `68k/os9-68k-assembly.md`; comparing the two
is the fastest way to see what does and does not carry across.

**It defines its own constants on purpose.** `/dd/defs/os9defs.a` on this
disk is RMA-format — it opens with `psect` and declares call codes as
`RMB` entries — and `asm` cannot parse any of it. See "Why not `use`
os9defs.a" below.

```
        nam ExFileI
* Constants are defined here rather than pulled from /dd/defs/os9defs.a,
* which is RMA-format and cannot be assembled by asm.
Prgrm   equ $10
Objct   equ $01
ReEnt   equ $80
ICreat  equ $83
IOpen   equ $84
IWrite  equ $8A
IClose  equ $8F
FPErr   equ $0F
FExit   equ $06
READ    equ 1
WRITE   equ 2
ATTRS   equ $03
* Data area: offsets from U. Its size is the mod directive's last operand.
        org 0
path    rmb 1
        rmb 200
size    equ .
        mod eom,name,Prgrm+Objct,ReEnt+1,start,size
name    fcs /ExFileI/
* --- happy path: create, write one line, close ---
start   leax fname,pcr
        lda #WRITE
        ldb #ATTRS
        swi2
        fcb ICreat
        bcs failed
        sta path,u
        leax line,pcr
        ldy #linelen
        lda path,u
        swi2
        fcb IWrite
        bcs failed
        lda path,u
        swi2
        fcb IClose
        bcs failed
        leax okmsg,pcr
        ldy #okmsgln
        lda #1
        swi2
        fcb IWrite
* --- error path: open a file that is not there ---
        leax missing,pcr
        lda #READ
        swi2
        fcb IOpen
        bcc unexpec
        pshs b
        leax experr,pcr
        ldy #experrl
        lda #1
        swi2
        fcb IWrite
        puls b
        swi2
        fcb FPErr
        clrb
        swi2
        fcb FExit
unexpec leax unexmsg,pcr
        ldy #unexln
        lda #1
        swi2
        fcb IWrite
        ldb #1
        swi2
        fcb FExit
failed  pshs b
        leax failmsg,pcr
        ldy #failln
        lda #1
        swi2
        fcb IWrite
        puls b
        swi2
        fcb FPErr
        ldb #1
        swi2
        fcb FExit
fname   fcc /exfile.txt/
        fcb $0D
missing fcc /no.such.file/
        fcb $0D
line    fcc /written by exfilei/
        fcb $0D
linelen equ *-line
okmsg   fcc /PASS create-write-close/
        fcb $0D
okmsgln equ *-okmsg
experr  fcc /PASS open of a missing file: /
experrl equ *-experr
unexmsg fcc /FAIL open of a missing file succeeded/
        fcb $0D
unexln  equ *-unexmsg
failmsg fcc /FAIL happy path: /
failln  equ *-failmsg
        emod
eom     equ *
```

Built and run, and what it actually printed:

```
asm exfilei.a -O=exfilei
00000 error(s)
00000 warning(s)
$012E 00302 program bytes generated
$00C9 00201 data bytes allocated

exfilei
PASS create-write-close
PASS open of a missing file: Error #216 - Path Name Not Found
```

`dump exfile.txt` shows 18 bytes, `written by exfilei` plus the trailing
`$0D`. **Error 216 is the same number the 68k and C examples report for the
same mistake** — OS-9 error codes are shared across architectures and
languages, and the C library passes them through as `errno`.

### The module the assembler produced

```
dump /dd/cmds/exfilei

00000000 87CD 012E 000D 1181 0700 1400 0045 7846  .M...........ExF
00000010 696C 65C9 308D 007C 8602 C603 103F 8325  ileI0..|..F..?.%
```

| Bytes | Field | Reads as |
|---|---|---|
| `87CD` @ `$00` | sync | the 6809 module signature — *not* the 68k `$4AFC` |
| `012E` @ `$02` | module size | 302 bytes |
| `000D` @ `$04` | name offset | `$0D`, where `ExFileI` sits |
| `11` @ `$06` | type/language | `Prgrm`(`$10`) + `Objct`(`$01`) — the `mod` operand |
| `81` @ `$07` | attributes/revision | `ReEnt`(`$80`) + 1 |
| `07` @ `$08` | header parity | one byte here, not the 68k's word |
| `0014` @ `$09` | exec offset | entry 20 bytes in |
| `00C9` @ `$0B` | data size | 201 — the `rmb` block, see below |

Note `fcs /ExFileI/` at `$0D`: the final byte is `C9`, `'I'` with bit 7 set.
That high bit *is* the terminator — `fcs` is not a NUL-terminated string.

### `*` is the program counter, `.` is the data counter

`asm` in its normal mode keeps **two separate location counters**, and the
`mod` directive's last operand wants the data one. Writing `size equ *`
assembles cleanly and produces a module that `ident` calls good — with a
**data size of `$0000`**. Writing `size equ .` gives the intended `$00C9`.
Both were confirmed by `ident` on modules built the two ways, from otherwise
identical source.

This is the quietest failure in this file. A program with a zero-sized data
area may still appear to work — this one did, storing a path number through
`U` — because the process gets a usable page anyway. Nothing warns you.
(The `hello.a` sample on this disk uses `size equ *`, so its declared data
size is its module length by accident rather than by intent.)

### Why not `use` os9defs.a

`asm` cannot assemble `/dd/defs/os9defs.a`. The file is RMA source: it
opens with `psect _os9defs,0,0,0,0,0`, uses `csect`, declares `true:`/
`false:` with trailing-colon labels, and defines every call code as an
`RMB 1` slot in a counted table. Feeding it to `asm` produces a cascade of
`***** Error: bad instr` on those directives, then `undefined name` on every
`OS9`/`I$`/`F$` symbol that never got defined, then `phasing` errors as the
two passes disagree. **The disk's own `hello.a` fails this way too** (47
errors), so a sample that looks canonical is not evidence that `use` works
here. Define the handful of constants your program actually needs, as above.

Consequently there is no `OS9` macro either — the raw mechanism is `swi2`
followed by a one-byte `fcb` call code, which is what the macro expands to
anyway. It reads much like 68k's `trap #0` plus an inline `dc.w`.

### Assembler and toolchain traps (all `Live` (NitrOS-9))

- **`asm` writes an object file even when the assembly reports errors.** A
  source with one bad mnemonic still produced a module that `ident` decoded
  happily (`Prog mod, 6809 obj, re-en, R/O`); running it failed with
  `Error #215 - Bad Path Name`, an error with no relationship to the actual
  mistake. **Check the error count, never the presence of an output file.**
- **Never redirect `asm`'s standard output away** (`>/nil`, `>file`). Errors
  go there, so a failing assembly looks silent and successful, and you are
  left with the broken module described above.
- **`O=<name>` fails if the output already exists** — `***** Error: can't
  open <name>` — while `-O=<name>` overwrites silently. Use the leading dash
  for any rebuild.
- **Case does not matter**: `o=` and `O=` both work and both produce a valid
  module (confirmed by `ident` on each). Despite the emphasis under "Two
  assemblers" below, the distinction that matters is the leading `-`, not
  the letter's case.
- The object lands in the **execution** directory (`/dd/cmds`), not the data
  directory — see the note under "Two assemblers".
- **Only the first 8 characters of a label are significant.** `asm` accepts a
  longer label without complaint and then treats any two that share their
  first 8 characters as the same symbol, so `setupfail` and `setupfail2`
  collide and the second definition fails with `redefined name` — an error
  that points at a line whose label looks obviously distinct. `Source`
  (NitrOS-9 `level1/cmds/asm.asm`, whose own comments read "Arbitrary-length
  labels allowed. (first 8 chars must be unique)" and "First 8 characters of
  label MUST be unique", with `max symbol length` set to 8), and `Live` (NitrOS-9) — hit while building the 6809 conformance suite.
  **`lwasm` does not share this limit**, so cross-assembled source that builds
  clean on the host can fail on the guest. That asymmetry is invisible until
  something rebuilds with the native assembler: keep labels unique within 8
  characters in anything you expect an OS-9 system to reassemble.

## Two assemblers

- **`asm`** (module name `Asm`, ~7KB) — "Standard NitrOS-9 6809/6309
  Assembler" per its own `help asm`. A smaller, non-relocating assembler,
  and an older, separate tool from `rma`/RLINK. `Live` (NitrOS-9) end-to-end: assemble
  a real MOD/EMOD program, run it, get correct output. Syntax: `Asm filename
  [<opts>] [>list] [#xxK]`; `O=<name>` generates the object file, and a
  leading `-` (`-O=<name>`) means silent overwrite — without it, an
  existing output file fails the run. **Case is not significant** — `Live` (NitrOS-9),
  `o=` and `O=` both produce a valid module; an earlier note here implied
  otherwise. RMA's equivalent is `-o=`.
- **`rma`** (~20KB; `rma.6809`/`rma.6309` are byte-identical copies of one
  module, not a real 6309 build) — the Relocating Macro Assembler the
  PSECT/VSECT/RLINK section below describes. **Hangs indefinitely** on the
  EOU-disk + XRoar setup, so the RLINK/PSECT/VSECT multi-file path is
  currently unverifiable. Details and an lwasm-based workaround:
  `using-nitros9-repl.md`.

**`asm`'s `O=<name>` output goes to the execution directory (`CMDS`), not
the current data directory** — the same behavior as BASIC09's `PACK`.
Checking `dir name*` in the data directory after assembling makes every run
look like a silent failure; check `CMDS/name` instead. `ident CMDS/<name>`
confirms a real, CRC-good module.

**Undocumented per-line length limit** (`Live` (NitrOS-9)): `asm` has an internal
source-line read limit between 132 (OK) and 135 (broken) characters. An
over-length line doesn't error on itself — `***** Error: bad instr` fires on
the *next* physical line, with a stray fragment of the overflowing text
misread as a bogus label, pointing at the wrong line entirely. Keep source
lines at 132 characters or fewer.

## Assembler Directives

`Manual`, from `asm`/MIA's own manual (ch. 2.8) cross-checked against RMA's.
Directives described near-identically in both (`END`, `EQU`, `SET`, `FCB`,
`FDB`, the `IFxx` family, `NAM`/`TTL`, `OS9`, `PAG`/`SPC`, `USE`) are
unmarked; only genuine differences or single-assembler directives are tagged.

| Directive | Purpose |
|---|---|
| `END` | Optional — end-of-file alone ends a program. No label |
| `FCB n{,n}` | Byte constants (error if value >255 or <-128) |
| `FDB n{,n}` | Word constants; values with absolute value <256 get a zero-filled high byte |
| `FCC /str/` | ASCII string. **Delimiter set differs between assemblers**: RMA's is `! " # $ % & ' ( ) * + , = . /`; `asm`'s is the same but with `-` in place of `=`. Open/close delimiters must match and can't appear inside the string |
| `FCS /str/` | Same as FCC but sets the sign bit on the last character — OS-9's string-termination convention |
| `EQU expr` | One-time constant binding; label must not have been used before, operand can't reference not-yet-defined names |
| `SET expr` | Like EQU but redefinable — for assembler control flags, not true constants |
| `MOD size,nameoff,typelang,attrrev{,execoff,memsize}` | **`asm` only.** Emits the module header directly: rewinds both address counters to their `ORG 0` start, emits sync bytes `$87`/`$CD`, emits the 4 (or 6) header-field operands in order, computes the header-parity byte. Operand count must be exactly 4 or 6. **Breaks in Motorola-compatible mode** unless no `RMB`/`ORG` appears between `MOD` and `EMOD`. **`size` must be the end-of-module label `+3`, not the bare label**, to cover `EMOD`'s 3-byte CRC trailer — `Live` (NitrOS-9): a bare `eom equ *` assembles with `00000 error(s)` but produces a module 3 bytes short, `ident` shows `Module header is incorrect!`, and the shell refuses to run it (`Error #235`). Use `modend+3`. RMA has no `MOD`/`EMOD` — it uses `PSECT`/`VSECT` and leaves header generation to RLINK |
| `EMOD` | **`asm` only.** Closes the module; computes and emits the final 3-byte CRC accumulated over every byte since `MOD` |
| `ORG expr` | **`asm` only.** No label. Repoints whichever counter is active: data counter in normal mode, program counter in Motorola-compatible mode. OS-9 modules carry no load-record table, so relocating the program counter mid-file only makes sense for Motorola-mode output meant for bare 6809 hardware — under OS-9 it breaks loading. RLINK owns all placement in an RMA build |
| `RMB n` | Reserves `n` bytes. In `asm`, the label gets the *data* counter's value in normal mode, the *instruction* counter's in Motorola mode. In RMA: legal only inside a `VSECT` or `CSECT` — **illegal directly inside a `PSECT`** |
| `SETDP expr` | **`asm` only.** No label. Sets the internal direct-page counter used to auto-pick direct vs. extended addressing; default 0. The manual is explicit that ordinary OS-9 programs should **not** change it — it's for Motorola-compatible mode, where there's no OS-9-assigned run-time direct page. RMA has no equivalent |
| `IFEQ/IFNE/IFLT/IFLE/IFGT/IFGE/IFP1 ... ELSE ... ENDC` | Conditional assembly. `IFLT`/`IFLE`/`IFGT`/`IFGE` test `operand <op> 0`, so comparing two symbols by subtraction reverses the intuitive reading (`IFLE MAX-MIN` is true when `MIN > MAX`). `IFP1` is true only on pass 1 — used to gate large `USE`d DEFS files so they're processed once. No labels; they nest freely |
| `USE pathlist` | File inclusion, nestable (~13 levels, matching OS-9's open-path limit minus standard I/O). For DEFS files, interactive input during assembly (`USE /TERM`), and shared subroutine libraries. No label |
| `NAM str` / `TTL str` | Listing header program name / title. No label, no trailing comment |
| `OPT option` | **Both assemblers have `OPT`, with different letter sets.** `asm` (ch. 2.8.8): `C`/`Dnum`/`E`/`F`/`G`/`L`/`M`/`N`/`O[=filename]`/`S`/`Wnum`. RMA (ch. 4.7): `l c f g x e s d w` only — no `M` (no Motorola mode), no `O` (ROF output is unconditional). For both: bare letter turns an option on, leading `-` turns it off; numeric options need a trailing number. No label or comment field |
| `OS9 expr` | Convenience macro: emits `SWI2` + the function-code byte, for use with `OS9Defs` symbolic names (`OS9 I$Read`) |
| `PSECT {name,typelang,attrrev,edition,stacksize,entry} ... ENDSECT` | **RMA only.** Opens the program's single relocatable code section; location counter restarts at zero |
| `VSECT {DP} ... ENDSECT` | **RMA only.** Opens a relocatable data section inside a PSECT; RLINK assigns real addresses at link time. Optional `DP` switches to the direct-page counter set; a PSECT may repeat the block, each counter set accumulating across repeats |
| `CSECT {expr}` | **RMA only.** Sets the CSECT base-offset counter (default 0). Each `RMB` inside assigns its label the current counter value then advances it — a convenience for enumerated field offsets without hand-written `EQU`s |
| `ENDSECT` | **RMA only.** Closes a `PSECT`, `VSECT`, or `CSECT` |
| `FAIL text` | Aborts assembly with a message; typically wrapped in `IFxx ... ENDC` to enforce a build-time constraint. Everything after the keyword is the message, so no trailing comment |
| `REPT n ... ENDR` | Assembles the block `n` times; can't nest, and `n` can't reference an `EXTERNAL` or forward-undefined symbol |
| `PAG` (or `PAGE`) | Forces a listing page break. No label |
| `SPC {n}` | Inserts `n` blank listing lines (default 1). No label |
| `RZB n` | Reserves `n` zero-filled bytes (vs. `RMB`'s uninitialized reservation) |

**Label/symbol syntax (RMA): 1-9 characters**, starting with a letter; legal
characters are letters, digits, `$`, `.`, `_`, plus `@` per ch. 1.7's
expression rules (ch. 1.5's label-field wording omits `@` — an inconsistency
in the manual itself). **RMA does not fold case**: `bufPtr` and `BUFPTR` are
two symbols. A label can only be defined once (barring `SET`). Appending `:`
in the label field makes it visible to other modules at link time; without
the colon it's local to its own `PSECT`.

**Label/symbol syntax (`asm`): 1-8 characters** — a real divergence from
RMA's 1-9. Legal characters: letters (either case), digits, `$`, `_`, `.`;
first character must be a letter. Defined exactly once (barring `SET`); no
forward-reference loops. Case-folding behavior isn't stated in the manual, so
don't assume it matches RMA's.

**Expression evaluation.** Both assemblers share a 16-bit arithmetic model
and the identical precedence table: unary `-` (negate) and `^` (NOT) highest,
then `&` (AND)/`!` (OR), then `*`/`/`, then `+`/`-`, evaluated left-to-right
within a tier, parentheses override. Byte-range checks are identical (0..255
unsigned / -128..127 signed). `asm` adds a second location-counter operand,
`.` (period), giving the *data* address counter's value at line start; RMA
has only `*` for its single instruction counter.

**Two assembler modes** (`asm` only, ch. 2.4). **Normal mode** has the
OS-9-oriented feature set: separate program and data address counters,
`MOD`/`EMOD` generation, warnings on OS-9-inadvisable addressing modes.
**Motorola-compatible mode** collapses to a single program counter, behaving
like a plain absolute 6809 assembler — for programs targeting bare hardware
with no OS-9. Switch with the `M` option or `OPT M`; `-M` returns to normal,
and modes can be toggled mid-file. Mode affects `RMB`'s label value, `ORG`'s
target counter, and `MOD`/`EMOD` reliability.

**RMA command-line options** (ch. 1.4): up to 10, each a single letter
prefixed `-` (on) or `--` (off). An unspecified option keeps its default; an
in-source `OPT` overrides the command line.

- `-o=path` — write the relocatable object file (ROF) here (mass storage);
  omit for a syntax-check-only run
- `-l` — formatted listing to standard output (default off — errors only)
- `-c` — suppress conditional-assembly lines in the listing (**default on**)
- `-f` — eject pages with a form-feed rather than blank lines (default off)
- `-g` — include every byte of generated object code in the listing (off)
- `-x` — hide macro-expanded lines from the listing (default on)
- `-e` — suppress error-message printing (default on per the manual — a build
  tool defaulting to hidden errors is surprising; confirm before relying on it)
- `-s` — append the complete symbol table after the listing (default off)
- `-d<n>` — lines per page (default 66)
- `-w<n>` — max line width, truncating longer lines (default 80)

**`asm` command-line options** (ch. 2.5, 2.8.8). Format: `asm filename
[option(s)] [#memsize] [>listing]`. Options separated by spaces or commas, on
by presence, off with a leading `-`; an in-source `OPT` overrides the command
line. `#memsize` (Shell-processed) sets the assembler's own data area for its
symbol table — the default 4K holds ~200 symbols, each additional 4K adds
~273 more (15 bytes/entry); a `Symbol Table Full` error means bump it. A
trailing `>listing` (also Shell-processed) redirects listing output anywhere.

| Option | Effect | Default | |
|---|---|---|---|
| `C` | Print conditional-assembly source lines in the listing | on | |
| `Dnum` | Page depth: lines per listing page | `D66` | `Live` (NitrOS-9) |
| `E` | Print error messages; when off, a suppressed error still shows as an `E` flag in that line's info field and the summary still counts it | on | `Live` (NitrOS-9) |
| `F` | Eject listing pages with a form-feed | off | |
| `G` | Print every object-code line a directive generates, not just the first | off | attempted; no observable difference on multi-word `FDB`/`FCC` |
| `L` | Generate the formatted listing at all; off means errors only | off | `Live` (NitrOS-9) |
| `M` | Motorola-compatible mode | off | |
| `N` | Narrow/non-columnized listing for narrow displays | off | `Live` (NitrOS-9) — drops the fixed-width address/bytes/label columns |
| `O[=filename]` | Generate an object file — bare `O` names it after the source, a bare name places it under that name in the execution directory, a full pathlist controls device/directory/name | off | `Live` (NitrOS-9) |
| `S` | Append an alphabetical symbol-table dump, one type-code letter per symbol: `D`=data (`RMB`), `E`=equate, `L`=program label, `S`=set label, `U`=undefined | off | `Live` (NitrOS-9) |
| `Wnum` | Max listing line width, truncating longer lines; the comment field is fixed at column 50, so a low value chops useful content | `W80` | `Live` (NitrOS-9) |

**`I` corrupts the module — do not use it on a file passed as a command-line
argument.** `Live` (NitrOS-9): every listing line gets an `ASM:` prefix, but the
assembled module header comes out wrong (`87CD3103` instead of the correct
`87CD001D`, CRC differing too) while assembly still reports `00000 error(s)`.
Silent corruption reported as success. Neither `I` nor `U` is documented in
any manual mined here; RMA's own comparison appendix ("RMA has no interactive
mode") is the only hint that `I` may mean interactive/terminal input.

**Addressing-mode warnings** (ch. 2.7.4.4-5, `asm`): extended and
extended-indirect addressing (absolute addresses baked into the instruction)
get a `W` flag in the listing, since OS-9 programs normally shouldn't use
absolute addresses — direct-page or PC-relative is preferred. A long branch
(`LBxx`) whose destination was within short-branch range also gets `W`.
**The opposite direction is a hard error**: `Live` (NitrOS-9) — a short conditional
branch whose target is out of 8-bit signed range (±127 bytes) fails assembly
outright (`***** Error: out of range`). This commonly appears after an edit
pushes an error handler further from its callers; switch to the `L`-prefixed
long form.

## Position-independent code

Use `BRA`/`LBRA`/`BSR`/`LBSR`, never `JMP`/`JSR` with an absolute target; use
PC-relative (PCR) indexed addressing for constant data rather than
immediate-loading an absolute label address.

**Every label belongs to exactly one of two address spaces, and mixing them
produces confusing symptoms rather than a clear error** (`Live` (NitrOS-9)):

1. Anything declared with `FCC`/`FCS`/`RMB`/`FDB` in the assembled module's
   own code/data section is a real address *inside the module*, safe to reach
   only via `,PCR`-relative addressing.
2. Anything meant to live in the *process's per-process data area* (the
   region `MOD`'s data-size field reserves) must be a plain numeric `EQU`
   offset, never an `RMB`, and is reached only via `,U`-relative addressing.

Both failure modes are real: declaring a `,U`-addressed buffer with `RMB`
inside the code section produced 22 cascading `***** Error: phasing` errors
(fixed by converting to `EQU` offsets and enlarging `MOD`'s data-size field);
storing to a forward-referenced label with plain extended addressing (`STX
label`) instead of `,PCR` produced the same class of errors (fixed with `LEAY
label,PCR` once, then offset addressing from there).

**Rule of thumb: if a store/load target was declared with `RMB`/`FCC`/`FCS`
anywhere in the file, it needs `,PCR` — never plain absolute, even for a
scratch buffer.**

**Phasing errors** occur when an instruction's length or a symbol's resolved
address changes between passes. The classic cause is a branch that could
resolve short or long depending on a forward reference, but an
addressing-mode mismatch on a forward-referenced label is just as common and
easier to miss, because the error output points at labels far downstream of
the actual mistake. When phasing errors cascade across unrelated-looking
lines, suspect an addressing-mode bug on an early label before assuming a
branch-range issue.

## Writing 6809 assembly test programs — conventions

- **Character literals**: `asm` accepts `LDA #'1'` but rejects `LDA #' '` and
  `LDA #':'` with a syntax error. Hex (`#$20`, `#$3A`, `#$0D` for CR) is the
  safe default for any non-alphanumeric character.
- **Register-clobber discipline around syscalls**: if a call returns real
  data in `X`, `Y` or `U`, and the program uses that same register as its
  `,U`-relative data-area base pointer, it *will* be clobbered unless
  bracketed — `PSHS U` immediately before the `SWI2`, `PULS U` immediately
  after (`PULS` doesn't touch `CC`, so a carry/error result survives).
- **Save a return value to memory immediately**, before any print or helper
  call — shared helpers typically reuse `B` as a counter and `Y` as scratch,
  silently destroying a return value left in them.
- **A module's `CMDS`-visible name comes from `asm`'s `O=<name>` argument,
  not the source's `NAM` directive.** The two are independent, and a name
  colliding with a module already on disk from an earlier session — under a
  different logged-in identity — can fail to overwrite with a permission
  error rather than cleanly replacing it.
- **A fresh boot resets all in-memory kernel state**: module directory,
  process table, DAT/task assignments. Nothing from an earlier session
  persists — a module used successfully before is no longer resident, so
  `F$Link` alone fails `E$MNF` on it; use `F$Load` (which falls back to a
  filesystem search) or `F$Fork` first. Only disk-level changes survive.

## Linkage Editor (RLINK) and Multi-File Builds

`MOD`/`EMOD` cover a single self-contained source file. For a program built
from several separately-assembled pieces, use `PSECT`/`VSECT`/`CSECT`: each
assembles with its own location counter starting at zero (so every piece is
independently position-independent), and **RLINK** combines the resulting
relocatable object files (ROFs) into one module, assigning real addresses and
resolving cross-file symbol references. Change one section, reassemble just
that section, relink.

A program with only uninitialized `VSECT` data (`RMB`) gets its data-area
registers set up by RLINK's startup convention. A program needing
*initialized* data (values baked into the object file) additionally needs
**`Root.a`** — an assembly-source startup module shipped with the assembler —
linked ahead of it; `Root.a` copies initializer values into the live data
area at load time and sets up `Y`/`U`/`X` itself. It is unrelated to the C
compiler's `cstart.r`/`cstart.a` (see `c/os9-clib-reference.md`): same
purpose, different toolchain, not interchangeable.

**`PSECT` operands** (ch. 3.1.1): `PSECT name,typelang,attrrev,edition,
stacksize,entry` — all six optional as a group (bare `PSECT` defaults `name`
to `"program"`, the rest to 0). `name`: up to 20 printable non-space,
non-comma bytes, used only in RLINK's diagnostics; need not be unique.
`typelang`: **must be 0 for a non-mainline PSECT**; non-zero marks this PSECT
as the program's mainline segment. `attrrev`: module attribute/revision byte.
`edition`: the manual describes this identically to `attrrev`, likely a
duplication in the source. `stacksize`: estimated stack bytes; RLINK sums it
across every linked PSECT and adds the total to the data requirement.
`entry`: entry-point offset (0 for non-mainline). Exactly one `PSECT` per
assembled file.

**Directives legal inside or outside any section** (ch. 3.1): `nam`, `opt`,
`ttl`, `pag`, `spc`, `use`, `fail`, `rept`, `endr`, the `ifxx` family,
`endc`, `else`, `equ`, `set`, `macro`, `endm`, `endsect`.

**Data-area register conventions** (ch. 6): one index register holds the data
area's base address and `DP` holds its lowest page number; RLINK auto-adjusts
indexed and direct-page operands to match. **No-initialized-data programs**
get `U`=data-area start, `Y`=data-area end, `SP`=`Y`+1 (parameters land above
`Y`), `DP`=start page number; with no parameters, `Y`=`X`=`SP`. **This is
universal OS-9 process-invocation behavior, not an RLINK artifact** — `asm`'s
own manual (ch. 2.9.4) describes the identical setup for a plain single-file
`MOD`/`EMOD` program with no RLINK involved. **Important**: PC-relative
addressing cannot reach the data section from code — program and data
sections aren't a fixed distance apart. **Initialized-data programs** (ch.
6.3, needing `Root.a`): once `Root.a` runs, `Y`=bottom of the data area
(matching the C compiler's own data-pointer register choice, so mixed-language
linking works), `X`=parameter area, `U`=top of linker-allocated data.

**Running RLINK** (ch. 7.1): `rlink [options] mainline [sub1 {subN}]
[options]` — `mainline` is the ROF containing the non-zero-typelang PSECT
(external refs resolve against it, and the module header generates from it);
additional ROFs are always included whether referenced or not; no
non-mainline ROF may itself contain a mainline PSECT.

| RLINK option | Effect |
|---|---|
| `-o=path` | Write the linked memory module here; without `-n`, the module is named after this path's final component |
| `-n=name` | Explicit output module name |
| `-l=path` | Library ROF (merged assembly ROFs) — each PSECT inside is pulled in only if it resolves a currently-unresolved reference; no mainline PSECTs allowed; libraries searched in command-line order |
| `-e=n` / `-E=n` | Edition number for the output module (default 1) |
| `-M=size` | Extra data-area memory, in pages (or `K` for kbytes); if omitted, RLINK sums the stack-size operand from every linked PSECT |
| `-m` | Print a linkage map of each PSECT's assigned base address (a distinct option from `-M=size`; case is the only difference — verify before scripting) |
| `-s` | Print final assigned addresses for all symbols |
| `-b=ept` | Link a C function so BASIC09's `RUN` can call it directly, entering at symbol `ept` |
| `-t` | Allow static data in a BASIC09-callable module, assuming the caller has already sized a static area pointed to by `Y` |

**RMA vs. `asm` — the manual's own comparison** (Appendix A): RMA has no
interactive mode, disk-file input only; RMA emits a ROF that RLINK must
process into an executable module, where `asm` emits an executable module
directly via `MOD`/`EMOD`; RMA's `PSECT`/`VSECT` exist specifically to
replace those; RMA has no `SETDP` equivalent since RLINK, not the assembler,
handles all data/DP allocation.

**Direct page selection** (`asm` only): the assembler tracks direct-page
state and auto-selects direct vs. extended addressing based on whether an
address's high byte matches the current `SETDP` value; force with a `<`
(direct) or `>` (extended) prefix on the operand.

## RMA Source Format, Expressions, and Macros

**Input file format** (ch. 1.5): free-form ASCII lines terminated by return,
**max 256 characters**. Four fields: label (must start in column 1; if
absent, the line's first character must be a space), operation mnemonic,
operand, comment — separated by one or more spaces. A line whose first
character is `*` is a full-line comment. Empty lines are skipped for assembly
but occupy a listing line.

**Assembly listing format** (`-l`/`OPT L`, ch. 1.6), left to right: sequence
number, location-counter value, generated object bytes (`=` here flags an
external reference in the operand; `+` in the label-field column flags a
macro-generated line), then label, mnemonic, operand, comment.

**Expression evaluation** (ch. 1.7 — assembly-time syntax, distinct from the
debugger's calculator below). All arithmetic is 16-bit (0..65535 unsigned /
-32768..32767 signed); byte-sized contexts require -128..127 or 0..255.
Evaluated left-to-right within a precedence tier; parentheses override.
Operand forms: decimal (optional leading `-`, 1-5 digits, no prefix), hex
(`$` + 1-4 digits), binary (`%` + 1-16 bits), character constant (`'` + one
printable ASCII char), symbolic name, and `*` for the instruction counter at
line start. Precedence, highest first: unary `-` and `^` (NOT); then `&`
(AND) and `!` (OR); then `*`/`/` (unsigned only); then `+`/`-`. Logical ops
are bitwise. Division by zero and multiplication overflowing 65535 are errors
with undefined intermediate results. A name used before its own definition is
treated as external to the PSECT (recorded for RLINK) — but assembler-
directive operands cannot contain external names at all, and instruction
operands that do can only combine an external name with binary `+`/`-`.

**RMA's macro facility** (ch. 2) is assembly-time text substitution and a
separate mechanism from the Editor's `.MAC` system below. `name MACRO ...
ENDM`, where the label on the `MACRO` line becomes a new pseudo-mnemonic
usable after its definition. Body statements can reference previously-defined
macros (nesting up to 8 deep); defining a macro inside another's body is
illegal. Redefining a real 6809 mnemonic with a same-named macro is legal and
is the manual's own documented technique for building a cross-assembler for a
different instruction set; redefining an assembler directive the same way has
"unpredictable consequences" per the manual. Macro text lives in a temporary
work file with a 1K buffer, so define short, frequently-used macros first to
keep them cached.

**Macro arguments**: up to 9 positional, `\1`-`\9`, substituted only in the
operand field (never label or mnemonic) of body statements, replaced by the
literal actual-argument text. An actual argument containing a comma or
backslash must be double-quoted. Omitted trailing arguments become empty
strings — no substitution, not a zero value. Two read-only operators support
validation: `\Ln` = byte length of actual argument `n`; `\#` = count of
arguments passed — typically paired with `IFxx`/`FAIL` to reject bad calls.

**Macro automatic internal labels**: `\@` (with an optional letter/digit
suffix placed either right after the `@` or right before the leading `\`)
generates a label unique to that expansion. The form is `@nnnX`, where `nnn`
is a 3-digit sequence number incrementing once per expansion and `X` is the
suffix — a macro using `\@A` and `\@B` produces `@001A`/`@001B` on its first
call, `@002A`/`@002B` on its second.

## DEFS Files (assembly-time symbolic constants)

- `OS9Defs` — service request codes, signal codes, status codes, direct-page
  variable names, module type/language/attribute masks, process descriptor
  layout, path descriptor offsets, register-stack offsets, condition code
  bits, error codes.
- `SCFDefs` — SCF device static storage layout, XON/XOFF characters,
  SCF-specific path descriptor fields.
- `RBFDefs` — RBF path/device/file descriptor layouts, segment list format,
  directory entry format, drive table layout.
- `SysType` — CPU type, MMU type, CPU speed, disk controller, clock module,
  PIA type, and other build-time configuration constants.

Installation convention (ch. 2.2): `asm` lives in `CMDS` and the `DEFS`
directory sits at the root of the system disk — programs `USE` it with a full
pathlist like `/D0/DEFS/OS9Defs`. On-disk DEFS filenames vary by
system/release (a Level Two system's may be `os9defs.lii` rather than plain
`os9defs`).

`Source` (the EOU disk's real `DEFS/os9defs.a`): `Prgrm`=$10, `Objct`=1,
`ReEnt`=$80 — matching `syscalls-and-module-format.md`'s type/attribute
table, and cross-validated against `ident`'s decode of real system modules.
**Implementation trivia**: `os9defs.a` doesn't define `I$`/`F$` call codes as
literal `EQU` values — each name is an `RMB 1` entry in a running counted
table (`I$Read: RMB 1`, `I$ReadLn: RMB 1`, …), so a call's numeric code is
its *position* in that table, assigned by the location counter rather than
written per name. **That file is RMA source and `asm` cannot `use` it at
all** — see "Why not `use` os9defs.a" near the top of this file for what
happens and what to do instead.

## Debugger

The full command set below is `Live` (NitrOS-9).

| Command | Effect |
|---|---|
| *(space)* `expr` | Calculator: evaluate and print in hex + decimal (` 5+3` → `$0008 #00008`) |
| `.` | Show Dot (working address) and its contents |
| `. expr` | Set Dot, then show it |
| `..` | Recall the *previous* Dot value |
| `-` | Decrement Dot, show it |
| *(bare return)* | Increment Dot, show it — steps through memory sequentially |
| `= expr` | Write to the address at Dot, verify the write, advance Dot |
| `:` | Show all registers: `SP CC A B DP X Y U PC` |
| `:reg` | Show one register |
| `:reg expr` | Set one register (8-bit registers error if the value doesn't fit) |
| `B` / `B expr` | List breakpoints / set one (max 12) |
| `K` / `K expr` | Clear all breakpoints / clear one |
| `G` / `G expr` | Resume execution / resume at a specific address |
| `M expr1 expr2` | Hex+ASCII memory dump between two addresses |
| `C expr1 expr2` | Walking-bit RAM test + clear between two addresses — destructive, RAM only |
| `S expr1 expr2` | Search memory from Dot for a 1- or 2-byte pattern |
| `E text` | Load a program for execution (like Chain, but keeps the debugger resident as a coroutine); shows the initial register dump; `G` starts it |
| `L text` | Link to a module by name; sets Dot to its first byte |
| `$` / `$ cmd` | Drop into the OS-9 shell / run one shell command, returning afterward |
| `Q` | Quit (via `F$Exit`) |

**`S` must start from a real code or data address** — searching from `$0`
finds nothing, since low direct-page memory isn't meaningful search territory.
Take a starting address from a `:` register dump's `PC` column.

**`L` and `E` only find modules already in the live module directory.**
`Live` (NitrOS-9): neither registers a module merely opened as `debug <file>`'s own
command-line target, so both fail `Error #221 - Module Not Found` right after
`debug <file>` even with the module's correct case-sensitive internal name
from its `fcs` name field. `E`'s own act of loading-for-execution doesn't
satisfy a *subsequent* `L`/`E` lookup either. Treat both as reliable only for
independently resident modules.

**A module linked multiple times needs one `unlink` per link, not one total**
— `Live` (NitrOS-9): after a sequence of `L`/`E`/shell-run calls, `mdir` kept showing
the module resident until four separate `unlink` calls, matching the number
of linking events.

**`mdir`'s listing isn't exhaustive** — `Live` (NitrOS-9): immediately after a program
successfully `F$Load`ed a module (valid returned entry point, no error), and
while that program was itself still running, `mdir` showed neither the loaded
module nor the running program's own. A successful syscall result is stronger
evidence of residency than `mdir`'s silence.

**Breakpoint mechanism**: the 6809 `SWI` instruction, inserted and removed
transparently. Restrictions: RAM only (not ROM), must sit on an instruction's
first opcode byte, max 12 simultaneous, and **user code cannot use plain
`SWI`** (reserved for the debugger) — `SWI2` is what ordinary syscalls
already use and `SWI3` is available for user vectoring. A loop needs *two*
breakpoints to stop on every iteration.

**Register display**: `SP CC A B DP X Y U PC`, one line of names, hex values
below. `CC` bit 7 (E flag) must be set or `G` won't resume correctly — the
entry-state `CC` genuinely has it set (`Live` (NitrOS-9)). `SP` points at the bottom of
the saved register block when a breakpoint fires.

**Expression syntax**: hex is the default (`$` prefix optional), `#` for
decimal, `%` for binary, `'` for a one-character ASCII constant, `"` for two.
Indirect addressing: `<expr>` (byte) or `[expr]` (word). 6809 indexed
addressing can be written in the calculator as `(:D+:Y)`, equivalent to
assembly's `[D,Y]`.

## Editor

`Manual`. Line-and-buffer oriented, not screen-oriented (no cursor
addressing — matching the "no termcap" reality in `unix-differences.md`). Two
buffers (primary/secondary) with `P`/`G` to move lines between them, `B n` to
switch primary.

The vintage Microware line editor this section describes was not found on the
EOU test disk: its `ed` is an unrelated mouse/joystick-driven full-screen GUI
editor needing a 640×192×2 graphics window, and a second candidate, `edt`,
identifies itself as "6EDT Version 2.0 11-30-86" but did not clearly answer
to the command shapes below.

Core navigation/edit: `L n` (list forward) / `X n` (list backward) / `+n`/`-n`
(move by lines) / `>n`/`<n` (move by characters) / `^` (buffer start) / `/`
(buffer end) / `K n` (kill n chars) / `D n` (delete n lines) / `I n str`
(insert) / `E n str` (extend/append) / `U` (unextend/truncate line) /
`C n str1 str2` (change) / `S n str` (search) / `T n` (tab to column) /
`A n` (anchor search/change to column n).

**Macro system** — the Editor's own facility, a different mechanism from
RMA's assembly-time `MACRO`/`ENDM`: `.MAC "name"` opens a macro for editing;
parameters are `#var` (numeric) or `$var` (string); `[commands]n` loops the
bracketed commands n times (or `*` = as many as possible, exiting early if
any command fails); `:` is a conditional — skip to end of loop/macro unless
the fail flag is set, then clear it. Test commands that set or clear the fail
flag: `.EOF`/`.NEOF`, `.EOB`/`.NEOB`, `.EOL`/`.NEOL`, `.STR str`/`.NSTR str`,
`.ZERO n`, `.STAR n` (true if n = 65535, the wildcard value). `.S`/`.F`
force-exit a loop or macro with the fail flag cleared/set.

File/shell integration: `.READ str`/`.WRITE str` redirect the editor's
input/output file (empty string restores the original); `.SHELL text` runs an
OS-9 shell command without leaving the editor; `.LOAD str`/`.SAVE str1 str2`
load/save named macros to a file; `Q` writes remaining buffer content and
exits.

---

**Sources:** OS-9 Interactive Debugger Users Manual; OS-9 Assembler/Editor/
Debugger Manual (a generic Microware manual despite shipping with Dragon
systems — no Dragon-specific hardware content); OS-9 Relocating Macro
Assembler Manual (RMA options, input/listing format, expression evaluation,
macro facility, PSECT/VSECT/CSECT semantics, data-area access, RLINK options,
and the RMA-vs-Microware-Interactive-Assembler differences appendix — all
`Manual` only, since `rma` hangs on the live-test setup).
