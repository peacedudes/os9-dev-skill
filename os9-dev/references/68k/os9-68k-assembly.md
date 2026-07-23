# OS-9/68000 Assembly Language Reference

Scope: OS-9-specific 68k assembly facts (module mechanics, syscall
dispatch, register ABI, exception vectors). No surveyed source provides a
true 68k assembler manual — directive syntax has known gaps (listed at the
end); don't assume 6809 RMA syntax carries over. (The "Relocating Macro
Assembler" manual found in 68k archives is 6809-only — never a 68k
source.)

## Toolchain (`Live` end-to-end on os9exec)

- **`cc`** drives `cpp` → `c68` → `o68` → `r68` (assembler) → **`l68`**
  (linker), forking each by bare name via the execution directory (see
  `common/using-os9exec-repl.md`).
- **`l68`** error taxonomy is diagnostic gold: `file 'x.r' is not a
  relocatable module` = the object didn't parse (corrupt / not a ROF);
  `no root psect found` = parsed fine, no entry point. So `l68` on a
  single `.r` is a cheap integrity check — a healthy object says "no root
  psect found."
- **`LIB/cstart.r`** — prepended by the C driver at the front of every
  link list; supplies the root psect and the startup code that calls
  `main()`.
- **`debug`** — symbolic debugger; usage and its two real defects:
  `common/using-os9exec-repl.md`.
- **`r68 -O=<name>.r` and `l68 -o=<name>` both do not reliably overwrite
  an existing output file of the same name** — `Live`, hit repeatedly
  across sessions. Re-running either against a stale output can silently
  leave the old bytes in place (or produce a corrupt mix) while reporting
  success, so a rebuild after any source edit *looks* clean but tests the
  old binary. Always `del` the output first, or link to a never-before-
  used name, before trusting a rerun's result.

## System call mechanism (TRAP #0)

Full dispatch mechanism (`TRAP #0`/vector 32, the `OS9`/`tcall` macros,
the carry+`d1.w` error convention): `syscall-reference.md` — not
repeated here. Assembly/module-format-specific additions:

- By Microware convention `TRAP #13` is CIO and `TRAP #15` is the math
  trap (see `common/module-format.md`'s Math module section).
- **No file on this SDK's disk defines the I$/F$ call names as assemblable
  symbols** — `Live`: `dc.w I$Write` assembles clean (`r68` treats an
  unresolved name after `dc.w` as an ordinary external symbol and defers
  to the linker with no warning), but `l68` then fails with `Symbol
  'I$Write' unresolved`. A whole-disk search of `/h0/DEFS` (`oskdefs.d`,
  `macros.d`, both the `os9lib` and `GCC2` header trees) for `I$Open`
  found zero hits. `syscall-reference.md`'s call names must be
  hand-defined as numeric `EQU`/`SET` constants in your own source before
  assembling — they aren't pulled in from anywhere automatically. Numeric
  values confirmed to match the standard published table (source: this
  project's own `Source/OS9exec_core/os9funcs.h`, its own
  reimplementation, not proprietary Microware material): `I$Open=$84,
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
| 8 | Privilege violation (`T_PRIV`) | Supervisor-state instruction executed in user state |
| 9 | Trace | Single-step; `F$DFork`/`F$DExec`/`F$DExit` and the OS-9 debugger use this |
| 25-31 | Autovectored interrupts, levels 1-7 | Serviced through `F$IRQ`; level 7 (vector 31) is non-maskable and should not be used for ordinary devices — reserved for hardware the kernel doesn't need to coordinate with (e.g. DRAM refresh); a level-7 ISR must never call a system call or touch kernel data |
| 32 | `TRAP #0` — OS-9 system calls | See above |
| 33-47 | `TRAP #1`-`#15` — user trap handlers | Installed via `F$TLink` |
| 57-63 | 68070 on-chip autovectored interrupts, levels 1-7 | 68070 only |
| 64-255 | Ordinary vectored interrupts | |

Error exception vectors (2-8, 10-24, 48-63) all dispatch through `F$STrap` and are normally fatal — the
offending process is terminated. Exception: if the process was created via
`F$DFork`, its state is preserved rather than torn down, and control passes
back to the parent debugger for a post-mortem look instead. (The table above shows only a subset; the gaps are listed for completeness here.)

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
hardware leaves whatever happened to be there, and os9exec deliberately fills
them with sentinel patterns (`$AAAAAAA0+n` in address registers, `$DDDDDDD0+n`
in data registers) so the mistake surfaces — under os9exec an out-of-arena
access through such a register now raises a real 68k **bus error** rather than
being silently swallowed. (This is exactly the `pwrstat` utility's latent bug:
`MOVEA.L $4C(A0),A0` with `A0` still holding its `$AAAAAAAx` sentinel.)

Slot assignments for the *informational* registers (which datum is in D2 vs
D5, etc.) varied between manual passages, but are now **`Live`-resolved
(2026-07-21)** via a debugger register dump of a forked program (`debug <prog>
hello`): **D2 = priority (`$80` = 128, the default), D3 = # inherited paths
(`3` = stdin/out/err), D5 = param-area size, D6 = total memory** — exactly the
order the table above lists. The same dump confirmed the rest Live: **D0 = the
PID**, **D1 = packed owner** (`0` for a `0.0` super-user), and every
**undefined** register holding its sentinel — **D4=`DDDDDDD4`, D7=`DDDDDDD7`,
A0=`AAAAAAA0`, A2=`AAAAAAA2`, A4=`AAAAAAA4`** (the `$DDDDDDDn`/`$AAAAAAAn`
fill). The defined-vs-undefined split is also `Source` (os9exec's own
`prepFork` register setup).

**`A5`'s actual content, `Live`**: a NUL-terminated string holding
exactly the typed command-line tail (e.g. `"hello"` for one argument —
confirmed via sanitized hex dump: `68 65 6C 6C 6F 00 0D 00 "PORT="...`),
safe to pass directly as a syscall's pathname pointer with no copying.
**With zero arguments, the first byte is a bare CR (`$0D`), not a NUL** —
checking only for a leading NUL to detect "no argument" misses this case
silently (wrong behavior at runtime, no assemble/link-time warning).
**Don't use `D5` to bound a raw read/write of the string** — a
NUL-terminated scan is the safe check; `D5`'s exact meaning was not
pinned down this pass (possibly the whole parameter+environment block
size, not just the argument text) and reading past the NUL using `D5` as
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

## Known gaps (not covered by this rebuild's source set)

No surveyed source is a real 68k assembler manual, so the following are
**unverified for 68k** — confirm against a genuine 68k RMA manual (or
live) before relying on details:

- Exact `psect`/`vsect`/`csect` directive syntax and parameter order (the
  documented PSECT/VSECT syntax is the **6809** RMA's) — **but see
  Cross-references below**: `basic09/basic09-vs-68k-differences.md` has
  a complete, `Live`-tested worked example that fills this gap in
  practice, even though it isn't a manual citation.
- `ds.w`/`ds.l` and other data-definition directive syntax specifics —
  two now resolved, both `Live`: `dc.b 'text'` (single-quoted) fails on
  `r68` with `*** error - value out of range ***` regardless of string
  length, `dc.b "text"` (double-quoted) assembles clean — use double
  quotes for string data. **`ds.b` is not a valid directive on `r68`**
  (`*** error - bad mnemonic ***`) — reserve space with an explicit
  comma-separated `dc.b 0,0,0,...` instead (confirmed repeatedly across
  `test/68k-live-verification/batch*.a`, most recently `batch10-01.a`).
- **Mutable data in a program needs address-register indirect, not a
  PC-relative destination** (`Live`, 2026-07-22): `move.l d0,x(pc)` /
  `subq.l #1,cnt(pc)` do not work — `(d16,PC)` is a **source-only**
  addressing mode on the 68000. Load the address first, write through it:
  `lea cnt(pc),a1` then `subq.l #1,(a1)`. `os9exec` lets a `Prgrm` module
  write into its own `dc`-defined storage this way (each process gets its
  own image), so a scratch counter/flag/saved-ID can sit beside the code
  with no `vsect` — the pattern used throughout the event/alarm tests
  (`test/Sources/OS9Tests/main.swift`).
- ~~The external-symbol "trailing colon = public" visibility convention~~
  — resolved: `Live`, confirmed via `l68 -s` and `debug`'s `sc` symbol
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
  `basic09/basic09-vs-68k-differences.md`'s "Calling 68000 machine-language
  procedures from BASIC09" section has a complete, `Live`-tested
  hand-written 68k assembly example (`psect addone,Type_Lang,Attr_Rev,
  0,0,addone` — the 6-operand shape is `name,typelang,attrrev,edition,
  stacksize,entry`) with real `r68`/`l68` invocations. `Live`: this same
  shape works unchanged for `Prgrm` and `Drivr`-type modules too (they
  share the `M$Exec`/`M$Excpt`/`M$Data`/`M$Stack` header shape), not just
  the `Sbrtn` it was demonstrated with. **`Live`, does NOT generalize to
  `Devic` (device descriptor) modules**: the 6-operand form
  unconditionally reserves the same 12 bytes of header padding before the
  psect body, but a device descriptor's real extended header
  (`M$Port`/`M$Vector`/`M$Mode`/`M$FMgr`/... — see the sibling
  `os9-systems-dev` skill's `device-drivers.md`) is a completely
  different shape at those same offsets, so this recipe silently
  misaligns a hand-authored descriptor. A shorter 4-operand `psect` line
  fails outright (`*** error - comma expected ***`); no working syntax
  for authoring a `Devic`-type module byte-accurately was found this
  session — open gap. This is currently the skill's *only*
  live-verified 68k assembly syntax source for executable module types —
  it just isn't a manual citation, which is why it's easy to miss
  searching this file alone.
- **A linked module's registered name comes from `l68 -o=<name>`'s
  output-file argument, not from the source's `nam`/`psect` name
  operand.** `Live`: linking the same object twice under two different
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
assembly). Toolchain behavior: `Live` on os9exec.
