# OS-9/6809 Assembly, Editor, and Debugger

`Live` end-to-end via `nitros9repl.sh` (see
`6809/STATUS.md`) — assemble, link (implicitly, single-file MOD/EMOD),
run, and confirm output, all the way through. The assembler directives,
MOD/EMOD module-header mechanics, the `SWI2`+syscall-code dispatch
mechanism, and (as of 2026-07-19) the entire debugger command
set are `Live` against a real toolchain. The Editor section is still `Manual`;
attempted live 2026-07-19 but the on-disk tool's identity was
inconclusive (see that section). Originally built by
cross-referencing the Interactive Debugger Users Manual and the
Assembler/Editor/Debugger manual, which independently describe the same
debugger command set.

**Two assemblers exist on the EOU disk; `asm` fully works through this
REPL, `rma` doesn't — this is the answer to "can you even compile under
6809?": yes, completely, via `asm`.**
- **`asm`** (module name `Asm`, ~7KB) — "Standard NitrOS-9 6809/6309
  Assembler" per its own on-disk `help asm` (a completely different,
  older tool from `rma`/RLINK, not part of the modern
  `nitros9project/nitros9` GitHub tree at all — its help text wasn't
  found there). A smaller, non-relocating assembler. `Live`, fully
  end-to-end: assembled a real MOD/EMOD test program (`nam`,
  `mod`, `fcs`, `equ *`, `swi2`+`fcb $8C`/`fcb $06` for I$WritLn/F$Exit,
  PC-relative addressing via `leax ...,pcr`) with `00000 error(s)`, ran
  it, and it printed its message correctly and exited cleanly —
  behaviorally confirming both the syntax/directives *and* the specific
  syscall codes actually do what the syscall table below says, not just
  that they assemble. Real syntax, from `help asm`: `Asm filename
  [<opts>] [>list] [#xxK]`; `O=<name>` (**uppercase** — a completely
  different convention from RMA's lowercase `-o=`) generates the object
  file, a leading `-` on `O` means silent overwrite; other toggles are
  `C`/`D<num>`/`E`/`F`/`G`/`I`/`L`/`M`/`N`/`S`/`U`/`W<num>`.
  **The "output flag doesn't write a file" mystery from the previous pass
  is resolved, not a bug**: `asm`'s `O=<name>` output — like BASIC09's
  `PACK` (see `common/module-format.md`) — writes to the **execution
  directory** (`CMDS`), not the current/data directory. Checking `dir
  name*`/`fsize name` in the data directory after assembling makes every
  run look like a silent failure; check `CMDS/name` (or `fsize
  CMDS/name`) instead. `ident CMDS/<name>` confirms a real, CRC-good
  module.
  **One real gotcha found while getting a clean run**: forgetting to
  explicitly set `B` (the exit-status register) before `SWI2`+`F$Exit`
  ($06) doesn't stop `F$Exit` from working, but a stale/garbage `B` value
  left over from earlier code makes the shell print `Error #001 --
  Unconditional Abort` right after your program's own output — cosmetic
  (the program's own output and behavior are unaffected), but confusing
  the first time you see it. Fix: `clrb` (not `clr b` — `CLR` with an
  explicit register operand is an *undefined name* error on this
  assembler; clearing a register needs the dedicated `clra`/`clrb`
  mnemonic) right before `F$Exit` if you don't have a real status to
  report.
- **`rma`** (module name `rma`, ~20KB; `rma.6809` and `rma.6309` are
  byte-identical copies of the same module under different names, not a
  real 6309-targeted build) — the Relocating Macro Assembler this file's
  PSECT/VSECT/RLINK section describes. **Hangs indefinitely on this
  EOU-disk + XRoar + nitros9repl.sh setup** — reproduced 4+ times across
  independent fresh boots, with both a `USE os9defs.a`-heavy source and a
  tiny raw-bytecode source with no `USE` at all, and with or without an
  `-o=` flag (even bare `rma hello.a`, pure syntax-check mode with no
  output file, hangs). Confirmed NOT a REPL/tmux/DriveWire plumbing issue:
  the DriveWire server and the REPL's `nc`/`perl` bridge process stay
  alive and connected the whole time (verified directly via `ps`/`lsof`,
  not just the REPL wrapper), and XRoar shows real, sustained non-zero CPU
  usage throughout — this is a genuine runaway/stuck condition inside the
  emulated program or CPU emulation, not a dead connection. Waited 8+
  minutes with zero change before giving up (a later, more carefully
  instrumented rerun via the REPL's own gated `send` — not a raw tmux
  bypass — confirmed the same: the `nc` process's TCP socket stayed
  `ESTABLISHED` for 8+ continuous minutes with zero drops while polled
  every 1-2 seconds). Also ruled out: a syntax mistake (the invocation
  matches RMA's own official Microware help text, `level2/sys/rma.hp` in
  the `nitros9project/nitros9` GitHub source, exactly), and insufficient
  memory (the `#<size>k` shell memory modifier that fixes undersized
  BASIC09 programs doesn't even reach `rma` — it gives an immediate
  `WHAT?` from the shell before `rma` starts, a separate minor oddity).
  Root cause not identified (could be an `rma` bug specific to this disk
  image, or an XRoar 6809-core emulation edge case `rma`'s own algorithm
  triggers). Full repro trail and a possible `lwasm`-based host-side
  workaround are in `using-nitros9-repl.md`.
  **Until this is root-caused, use `asm` for single-file MOD/EMOD assembly
  and treat the RLINK/PSECT/VSECT multi-file path as unverified** — it
  cannot currently be tested through this REPL since it requires `rma`.

Register set and calling convention: `syscalls-and-module-format.md`.

**Undocumented per-line length limit, `Live`**: `asm`/MIA appears to have
an internal source-line read limit somewhere between 132 (confirmed OK)
and 135 (confirmed broken) characters — not stated in any manual mined
for this skill. An over-length line doesn't error on itself; instead
`***** Error: bad instr` fires on the *next* physical line, with a stray
fragment of the overflowing text (e.g. `ow)`, `one)`) misread as a bogus
label — a confusing symptom that points at the wrong line. Found porting
real third-party source (`gfx2.asm`) with several long trailing-comment
lines. Fix: keep source lines at 132 characters or fewer; move overflow
comment text to its own `*`-led full-line comment rather than a long
trailing comment.

## Assembler Directives

`Manual`: `asm`/MIA's own manual (ch. 2.8) has been mined and
cross-checked against RMA's. Most basic directives below turn out to be described
near-identically in both manuals (`END`, `EQU`, `SET`, `FCB`, `FDB`, the
`IFxx`/`ELSE`/`ENDC` family, `NAM`/`TTL`, `OS9`, `PAG`/`SPC`, `USE`) — those
rows are unmarked. Only rows that genuinely differ, or exist in only one
assembler, carry an explicit tag; per-assembler command-line option tables
follow further down.

| Directive | Purpose |
|---|---|
| `END` | Optional — end-of-file alone is sufficient to end a program. No label. `Manual` (`asm`/MIA ch. 2.8.1); RMA's own "directives legal inside or outside any section" list (ch. 3.1, see Linkage Editor section below) doesn't separately call out `END`, so its RMA behavior is unconfirmed |
| `FCB n{,n}` | Byte constants (error if value >255 or <-128) |
| `FDB n{,n}` | Word constants; values with an absolute value <256 get a zero-filled high byte |
| `FCC /str/` | ASCII string. **Delimiter set genuinely differs between the two assemblers**: RMA's fixed set is `! " # $ % & ' ( ) * + , = . /`; `asm`/MIA's (ch. 2.8.4) is the same list but with `-` in place of `=` — `! " # $ % & ' ( ) * + , - . /`. For both, open/close delimiters must match and can't appear inside the string |
| `FCS /str/` | Same as FCC but sets the sign bit on the last character — OS-9's string-termination convention (analogous to how 68k module names are sign-bit-terminated) |
| `EQU expr` | One-time constant binding; label must not have been used before, operand can't reference not-yet-defined names |
| `SET expr` | Like EQU but redefinable — for assembler control flags, not true constants |
| `MOD size,nameoff,typelang,attrrev{,execoff,memsize}` | **`asm`/MIA only** (ch. 2.8.6). Emits the module header directly: rewinds both address counters back to their `ORG 0` starting point, emits sync bytes `$87`/`$CD`, evaluates and emits the 4 (or 6) header-field operands in order, computes the header-parity byte automatically. Operand count must be exactly 4 or 6, no other length. **Breaks in Motorola-compatible mode** unless no `RMB`/`ORG` statement appears between `MOD` and `EMOD` (the manual's own explicit warning). RMA has no `MOD`/`EMOD` — it uses `PSECT`/`VSECT` instead and leaves module-header generation to RLINK (RMA manual Appendix A). **`size` must be the end-of-module label `+3`, not the bare label**, to cover `EMOD`'s 3-byte CRC trailer — `Live`: a program written with a bare `eom equ *` label (placed before `EMOD`) as the `size` operand assembles with `00000 error(s)` but produces a module 3 bytes short; `ident` shows a bad CRC (`Module header is incorrect!`) and the shell refuses to run it (`Error #235 - Bad Name`). Every working example in this file uses `modend+3`, not a bare end label — match that pattern, don't copy just the label structure |
| `EMOD` | **`asm`/MIA only.** Closes the module; computes and emits the final 3-byte CRC, continuously accumulated over every byte since `MOD`. Not present in RMA — see `MOD` row |
| `ORG expr` | **`asm`/MIA only**, `Manual` (ch. 2.8.10). No label allowed. Repoints whichever counter is active for the current mode: data counter under normal mode, program counter once Motorola-compatible mode is toggled on. OS-9 modules carry no load-record table (their code is just a contiguous blob starting at the module header), so relocating the program counter mid-file only makes sense for Motorola-compatible-mode output meant to run on bare 6809 hardware — doing so under OS-9 itself breaks loading. RMA still has nothing comparable — RLINK owns all placement; its `PSECT`/`VSECT` counters reset automatically per section with no user-settable `ORG` |
| `RMB n` | Reserves `n` bytes. In `asm`/MIA, the label gets the *data* address counter's value in normal mode, or the *instruction* counter's value in Motorola-compatible mode (ch. 2.6.2.1). In RMA: legal only inside a `VSECT` (uninitialized data) or a `CSECT` (assigns the label the current CSECT counter value, then advances the counter by `n`) — **illegal directly inside a `PSECT`** |
| `SETDP expr` | **`asm`/MIA only** (ch. 2.8.12). No label allowed. Per RMA manual Appendix A, RMA itself has nothing comparable — RLINK, not the assembler, owns every data/DP placement decision in an RMA build. In `asm`, sets the internal direct-page counter used to auto-pick direct vs. extended addressing; default 0. The manual is explicit this should **not** be changed in ordinary OS-9 programs — it's meant for Motorola-compatible-mode use, where there's no OS-9-assigned run-time direct page to track |
| `IFEQ/IFNE/IFLT/IFLE/IFGT/IFGE/IFP1 ... ELSE ... ENDC` | Conditional assembly. `IFLT`/`IFLE`/`IFGT`/`IFGE` test `operand <op> 0`, so comparing two symbols by subtracting them reverses the intuitive reading (`IFLE MAX-MIN` is true when `MIN > MAX`). `IFP1` is true only on assembler pass 1 — used to gate large `USE`d DEFS files so they're processed once, not twice. None of the IF-family may have labels; they nest freely |
| `USE pathlist` | File inclusion, nestable (~13 levels, matching OS-9's simultaneous-open-path limit minus the standard I/O paths); used for DEFS files, interactive input during assembly (`USE /TERM`), and shared subroutine libraries. Cannot have a label |
| `NAM str` / `TTL str` | Listing header program name / title, printed on every listing page's header line. Neither takes a label, and neither leaves room for a trailing comment |
| `OPT option` | **Both assemblers have an `OPT` statement, with genuinely different letter sets** — `Manual`. `asm`/MIA (ch. 2.8.8): `C`/`Dnum`/`E`/`F`/`G`/`L`/`M`/`N`/`O[=filename]`/`S`/`Wnum` — see the `asm` command-line options table below for what each does. `M`=Motorola-compatible mode and `O`=object-file are both genuine `asm` OPT letters (an earlier RMA-only pass had mis-attributed them — they were never RMA facts, but they are genuine `asm` facts, not fabrications). RMA (ch. 4.7, cross-referencing ch. 1.4): `l c f g x e s d w` only — no `M`, no `O`; RMA has neither a Motorola-compatible mode nor a distinct object-file toggle (its ROF output is unconditional, always written). For both assemblers: bare letter turns an option on, a leading `-` turns it off; the numeric options (`D`/`W` for `asm`, `d`/`w` for RMA) need a trailing number. Neither assembler's `OPT` statement can have a label or comment field |
| `OS9 expr` | Convenience macro: emits `SWI2` + the function-code byte, meant to be used with the `OS9Defs` symbolic names (e.g. `OS9 I$Read`) |
| `PSECT {name,typelang,attrrev,edition,stacksize,entry} ... ENDSECT` | **RMA only.** Opens the program's single relocatable code section for multi-file builds; location counter restarts at zero. Full operand list and mainline/library distinction in Linkage Editor below |
| `VSECT {DP} ... ENDSECT` | **RMA only.** Opens a relocatable data section inside a PSECT; RLINK assigns real addresses at link time. Optional `DP` keyword switches to the direct-page counter set instead of the default index-register set; a single PSECT may repeat this block as many times as needed, and each counter set keeps accumulating across every repeat |
| `CSECT {expr}` | **RMA only.** Sets the CSECT base-offset counter (default 0). Each `RMB` inside then assigns its label the current counter value and advances the counter by that RMB's size — a convenience for enumerated field offsets (e.g. a register-save layout) without hand-written `EQU`s |
| `ENDSECT` | **RMA only.** Closes a `PSECT`, `VSECT`, or `CSECT` block |
| `FAIL text` | Aborts assembly with a user-supplied message; typically wrapped in `IFxx ... ENDC` to enforce a build-time constraint. Everything after the `FAIL` keyword becomes the message, which leaves no room on that line for a separate trailing comment |
| `REPT n ... ENDR` | Assembles the enclosed block `n` times; can't be nested, and `n` can't reference an `EXTERNAL` or forward-undefined symbol |
| `PAG` (or `PAGE`) | Forces a page break in the listing. No label |
| `SPC {n}` | Inserts `n` blank lines in the listing (default 1). No label |
| `RZB n` | Reserves `n` zero-filled bytes (vs. `RMB`'s uninitialized reservation) |

**Label/symbol syntax (RMA): 1-9 characters** — corrected from a previously-uncited "1-8" figure; the RMA manual states 1-9 explicitly (ch. 1.5 and 1.7), and the same sentence's own `PSECT`-scoping language confirms the original claim was already describing RMA, not `asm`, so this is a straight correction rather than an asm-vs-rma divergence. Must start with a letter; legal characters are letters, digits, `$`, `.`, `_`, plus `@` per ch. 1.7's expression-operand rules (ch. 1.5's label-field wording omits `@`, an inconsistency in the manual itself, noted not resolved). **RMA does not fold case** — e.g. `bufPtr` and `BUFPTR` would name two separate symbols, not one. A label can only be defined once (barring `SET`). Appending `:` after a label in the label field makes it visible to other modules at link time — without the colon it's local to its own `PSECT`.

**Label/symbol syntax (`asm`/MIA): 1-8 characters, genuinely shorter than RMA's 1-9** — `Manual` (ch. 2.6.2.1, 2.7.3 — this is a real asm-vs-rma divergence, not a manual inconsistency like the earlier 1-8/1-9 mixup was). Legal characters: uppercase or lowercase letters, digits, `$`, `_`, `.`; first character must be a letter. Names must be defined exactly once (barring `SET`); an operand cannot reference a name that isn't yet defined anywhere in its own definition chain (no forward-reference loops). Case-folding behavior isn't stated either way in this chapter, so it's unverified for `asm` — don't assume it matches RMA's case-sensitive behavior above.

**Expression evaluation (`asm`/MIA, ch. 2.7)**: same 16-bit arithmetic model and the *identical* operator-precedence table as RMA above — unary `-` (negate) and `^` (NOT) highest, then `&` (AND)/`!` (OR), then `*`/`/`, then `+`/`-` lowest, evaluated left-to-right within a tier, parentheses override. `Manual` — direct side-by-side comparison of both chapters, not assumed from similar wording. Byte-range checks are identical too (0..255 unsigned / -128..127 signed, error if out of range). Two genuine differences from RMA: symbol names are 1-8 characters (not 1-9, see above), and `asm` has a second location-counter operand, `.` (period), giving the *data* address counter's value at the start of the line (not used in Motorola-compatible mode) — RMA has no equivalent, only `*` for its single instruction counter.

**Two assembler modes** — `Manual`: `asm`/MIA — not RMA — really does have two operating modes (ch. 2.4). **Normal mode** has the OS-9-oriented feature set: separate program and data address counters, `MOD`/`EMOD` module generation, warnings on OS-9-inadvisable addressing modes (see below). **Motorola-compatible mode** collapses to a single program counter, behaving like a plain absolute 6809 assembler with no OS-9-specific behavior — meant for programs targeting bare 6809 hardware with no OS-9. Switch with the `M` option (command line or `OPT M`); `-M`/`OPT -M` returns to normal mode, and modes can be freely toggled mid-file "to achieve special effects" (the manual's own phrase). Concretely, mode affects: `RMB`'s label value (data counter vs. instruction counter, see the `RMB` row above), `ORG`'s target counter (see `ORG` row), and `MOD`/`EMOD` reliability (see `MOD` row) — `SETDP` is explicitly meant for Motorola-compatible-mode use only, not ordinary OS-9 programs. RMA genuinely has no such mode or `M` option (ch. 1.4/3/4.7, as already established) — this was always an `asm`-only fact; it's now sourced directly from `asm`'s own manual instead of inferred from RMA's silence on the subject.

**RMA command-line options** (ch. 1.4; as opposed to the `OPT` directive above, which sets the same flags minus path arguments, from inside the source): up to 10 options total, each a single letter prefixed `-` (turn on) or `--` (turn off) — an unspecified option keeps its documented default, and an in-source `OPT` statement overrides whatever the command line set.
- `-o=path` — write the relocatable object file (ROF) here (must be mass storage); omit it for a syntax-check-only run (errors only, no output)
- `-l` — write a formatted listing to standard output (default off — errors only)
- `-c` — suppress conditional-assembly lines in the listing (**default on**, i.e. conditional lines are hidden unless re-enabled with `--c`)
- `-f` — eject pages with a form-feed character rather than blank lines (default off)
- `-g` — include every byte of generated object code in the listing (default off)
- `-x` — hide macro-expanded lines from the listing (default on)
- `-e` — suppress error-message printing (default on, as written in the manual — a build tool defaulting to hidden errors is surprising; worth confirming live before relying on it)
- `-s` — append the complete symbol table after the listing (default off)
- `-d<n>` — lines per page (default 66)
- `-w<n>` — max line width, truncating longer lines (default 80)

**`asm`/MIA command-line options** (ch. 2.5, 2.8.8 — expanding on the
`Live` toggle list at the top of this file, which is `help asm`'s own
on-disk text with no per-option default states). Command line format:
`asm filename [option(s)] [#memsize] [>listing]`. Options are separated by
spaces or commas, on by presence and off with a leading `-`; an unspecified
option keeps its default; an in-source `OPT` statement overrides whatever
the command line set. `#memsize` (Shell-processed, not assembler code) sets
the assembler's own data-area size for its symbol table — default 4K holds
~200 symbols, each additional 4K adds room for ~273 more (15 bytes/entry);
a `Symbol Table Full` error means bump this. A trailing `>listing`
(also Shell-processed) redirects listing output to any pathlist — file,
device, or pipe.

| Option | Effect | Default |
|---|---|---|
| `C` | Print conditional-assembly (`IFxx`/`ELSE`/`ENDC`) source lines in the listing | on |
| `Dnum` | Page depth: lines per listing page, headers/blanks included | `D66` |
| `E` | Print error messages in the listing; when off, a suppressed error still shows as an `E` flag in that line's info field | on |
| `F` | Eject listing pages with a form-feed instead of blank lines | off |
| `G` | Print every object-code line a directive generates (e.g. every `FCB` byte), not just the first | off |
| `L` | Generate the formatted assembly listing at all; off means error messages only | off |
| `M` | Motorola-compatible mode (see above) | off (normal mode) |
| `N` | Narrow/non-columnized listing format for narrow displays | off |
| `O[=filename]` | Generate an object file — bare `O` names it after the source file, a bare name places it (under that name) in the current execution directory, a full pathlist controls device/directory/name explicitly | off |
| `S` | Append an alphabetical symbol-table dump to the listing, one type-code letter per symbol: `D`=data (`RMB`), `E`=equate, `L`=program label, `S`=set label, `U`=undefined | off |
| `Wnum` | Max listing line width, truncating longer lines; note the comment field itself is fixed at column 50, so setting this too low chops off useful listing content | `W80` |

**`L`/`S` `Live`, 2026-07-19**: `asm <file>.a L S >listing.txt` produced exactly the documented page-headered listing (`Microware OS-9 Assembler RS Version 01.00.00 ... Page 001`, line-numbered source with object bytes) followed by a trailing symbol table using exactly the documented type-code letters (e.g. `001D E eom      000D L nm       0015 E start`). Default page depth (`D66`) is visibly real in the listing too — long sources break across multiple numbered pages at roughly that interval with no `D` flag given at all. **`G` attempted, inconclusive**: compared a listing generated with `L G` against one with plain `L` on the same multi-word `FDB`/multi-byte `FCC` directives (a 5-word `FDB` table, a 10-character string) — the two listings were byte-for-byte identical for those lines, both already showing every generated byte across continuation lines regardless of the flag. Either `G`'s documented effect only shows up on a different category of directive than the ones tested, or it's a genuine no-op on this build; not resolved either way, so `G` stays at its prior confidence rather than being marked confirmed. **`W` `Live`, 2026-07-19**: `asm <file>.a L W40` truncated every listing line at exactly 40 columns against the same source assembled with the default (longest line 59), and the documented warning about the fixed column-50 comment field is real — at `W40` the `fcc` operand strings are cut mid-content (`fcc   /` with the text gone). The `W80` default itself is *not* directly exercised: no line in the source tested exceeded 80, so only the truncation mechanism is confirmed, not that specific number. **`E` `Live`, same day**: assembling a source with two genuine errors under `L -E` suppressed the `***** Error: ...` message lines while still flagging each offending line with `E` in its info field (`00131 E 0117 86FF   lda   #'`) and still reporting `00002 error(s)` in the summary — exactly the documented "suppressed error still shows as an `E` flag" behaviour. **`D<num>` `Live`, 2026-07-19**: `asm childprg.a L D5` produced 42 separate numbered pages for a 13-line source (vs. ~2 pages at the `D66` default) — confirms the page-depth mechanism directly with a small, easy-to-count number. **`N` `Live`, 2026-07-19**: drops the fixed-width address/bytes/label columns entirely — source and object bytes run together on one line per statement instead of aligning into columns, matching "narrow/non-columnized." **`I` — `Live`, and a real bug, not just an untested mode.** Every listing line gets an `ASM:` prefix (support for the "interactive mode" guess below), but the assembled module header comes out **wrong**: `mod eom,nm,...`'s encoded bytes read `87CD3103` under `I`, vs. the correct `87CD001D` every other invocation of the identical source produces (CRC differs too), while assembly still reports `00000 error(s)`. **Practical warning: don't use `I` when assembling a file passed as a normal command-line argument — it can silently produce a corrupted module while reporting success.** Not root-caused (plausibly a stdin-vs-file-argument mismatch under a mode meant for truly interactive input, but that's speculation). **`U` attempted, `Live` but inconclusive**: byte-for-byte identical output to the plain default listing on this source — no observable effect, doesn't rule out an effect on different content. `C`/`F`/`M` (beyond the Motorola-mode note above) remain individually untested.

This chapter doesn't document `I` or `U` — both are already `Live`
toggles from `help asm`'s on-disk text (top of this file) but remain
unexplained by any manual mined so far. The RMA manual's own "RMA has no
interactive mode" comparison line (Appendix A, cited further below) is
still the only clue that `I` may mean an interactive/terminal-input mode;
still unconfirmed.

**Addressing-mode warnings** (ch. 2.7.4.5, 2.7.4.4 — `asm`/MIA): extended
and extended-indirect addressing (absolute addresses baked into the
instruction) get a `W` warning flag in the listing, since OS-9 programs
normally shouldn't use absolute addresses at all — direct-page or
PC-relative addressing is preferred instead. A long-branch instruction
(`LBxx`) whose destination was actually within short-branch range also
gets a `W` flag, as a hint that a shorter/faster instruction was available.
**The opposite direction is a hard error, not a warning**: `Live` — a
short conditional branch (`BEQ`/etc.) whose target is out of 8-bit signed
range (roughly ±127 bytes) fails assembly outright (`***** Error: out of
range`), not just a listing hint. This commonly happens after editing
pushes an error-handler label further from its callers than it started —
switch to the `L`-prefixed long form (`LBEQ`, etc.) to fix it.

**Position-independent code technique**: use `BRA`/`LBRA`/`BSR`/`LBSR`, never `JMP`/`JSR` with an absolute target; use PC-relative (PCR) indexed addressing for constant data instead of immediate-load of an absolute label address. **The distinction that actually matters in practice, `Live`-confirmed the hard way (2026-07-19) — every label in a source file belongs to exactly one of two separate address spaces, and mixing them up produces confusing symptoms rather than a clear error**: (1) anything declared with `FCC`/`FCS`/`RMB`/`FDB`/etc. in the assembled module's own code/data section is a real address *inside the module*, only ever safe to reach via `,PCR`-relative addressing; (2) anything meant to live in the *process's own per-process data area* (the region the `MOD` directive's data-size field reserves, sized to fit at load time) must be a plain numeric `EQU` offset, never an `RMB`, and is only ever reached via `,U`-relative addressing. Two real, independently-hit failure modes from confusing the two: declaring a `,U`-addressed buffer with `RMB` inside the code section (instead of a numeric `EQU`) produced 22 cascading `***** Error: phasing` errors — fixed by converting to `EQU` offsets and enlarging the `MOD` line's data-size field to cover them. Separately, storing to a forward-referenced label with plain absolute/extended addressing (`STX label`) instead of `,PCR` produced the identical class of phasing errors — fixed with `LEAY label,PCR` once, then offset addressing (`STX ,Y` / `STX 2,Y`) from there. **Rule of thumb: if a store/load target was declared with `RMB`/`FCC`/`FCS` anywhere in this file, it needs `,PCR`, full stop — never plain absolute, even for a "just store some bytes" scratch buffer.**

**Phasing errors**: occur when an instruction's length or a symbol's resolved address changes between assembler passes — the classic cause is a branch that could resolve as short or long depending on a forward reference, but (see above, `Live`-confirmed) an addressing-mode mismatch on a forward-referenced label is just as common a real-world cause and easier to miss, since the assembler's own error output points at the wrong-looking line (labels far downstream of the actual mistake, not the mistake itself) — when phasing errors cascade across many unrelated-looking lines, suspect an addressing-mode bug on some early label before assuming it's a branch-range issue.

**Writing a 6809 syscall regression test — hard-won conventions, `Live`, reused across ~90 test files this project (`test/6809-live-verification/`)**:
- **Character literals**: `asm` accepts `LDA #'1'` (alphanumeric) fine, but rejects space/colon/similar (`LDA #' '`, `LDA #':'`) with a syntax error — inconsistent enough that hex (`#$20`, `#$3A`, `#$0D` for CR) is the safe default for any non-alphanumeric character rather than assuming either way.
- **Register-clobber discipline around syscalls**: if a syscall's documented calling convention uses `X`, `Y`, or `U` to return *real data* (not just a status in `A`/`B`), and the test program also uses that same register as its own `,U`-relative data-area base pointer, it WILL get clobbered unless bracketed — `PSHS U` immediately before the `SWI2`, `PULS U` immediately after (`PULS` doesn't touch `CC`, so a carry/error result survives the restore). Hit repeatedly across this project's whole test suite; assume it's needed by default for any call whose convention mentions `X`/`Y`/`U` as an output.
- **Save a return value to memory *immediately*, before any print/helper call.** A shared `copys`/`crwrite` helper pattern (used throughout this test suite) reuses `B` as a byte counter and `Y` as a scratch pointer — calling either before capturing a real return value in those same registers silently destroys it. Store to memory (`STD VALUE,u` etc.) as the very next instruction after the `SWI2`, before any other subroutine call.
- **Keep PASS/FAIL print messages under ~60 characters.** The shared `crwrite` helper this suite uses caps writes at `Y=60` (`I$WritLn`'s max-length input) — a longer message gets silently truncated/garbled into whatever the OUTBUF-adjacent memory holds, not cleanly cut off.
- **A fresh `nitros9repl.sh start` resets ALL in-memory kernel state** — the module directory, process table, and any DAT/task assignments all reset to boot defaults; nothing tested in an earlier boot session (a "resident" module, an installed `F$SSWI`/`F$VIRQ` handler, etc.) persists into a new one. Only *disk-level* changes (files written, deleted, or `attr`-modified) survive a restart. This means: don't assume a module used successfully in an earlier session today is still resident (`F$Link` alone will fail `E$MNF` on it — use `F$Load`, which falls back to a filesystem search, or `F$Fork` it first); and a call that mutates in-memory-only state is generally safer to test than its risk profile might suggest, since a clean reboot is the recovery path either way.
- **A freshly-assembled module's `CMDS`-visible name comes from `asm`'s own `-O=<name>` argument, not the source's `NAM` directive** — the two are independent, and choosing a name that collides with a module already resident on disk from an earlier session (especially one created under a *different logged-in identity*, see `using-nitros9-repl.md`) can fail to overwrite with a permission error rather than cleanly replacing it. Cheaper to just pick a fresh, unused `-O=` name per assembly than to fight over ownership of an old one.

## Linkage Editor (RLINK) and Multi-File Builds

`MOD`/`EMOD` cover a single self-contained source file. For a program built
from several separately-assembled pieces, use `PSECT`/`VSECT`/`CSECT`
instead: each assembles with its own location counter starting at zero (so
every piece is independently position-independent), and **RLINK** — the
linkage editor — combines the resulting relocatable object files (ROFs)
into one module, assigning real addresses and resolving cross-file symbol
references. This split lets a large program be developed incrementally:
change one section, reassemble just that section, relink, without
recompiling everything.

A program with only uninitialized `VSECT` data (`RMB`) gets its data-area
registers set up directly by RLINK's own startup convention: `U` = data
base, `Y` = top of data area, `X`/`S` mirror `Y`, `DP` = the page number of
the lowest address. A program that needs *initialized* data (values baked
into the object file, not just reserved space) additionally needs **`Root.a`**
— an assembly-source startup module shipped with the assembler — linked in
ahead of it; `Root.a` copies the initializer values from the object module
into the live data area at load time and sets up `Y`/`U`/`X` itself. Note
`Root.a` is unrelated to the C compiler's own `cstart.r`/`cstart.a` startup
file (see `c/os9-clib-reference.md`) — same *purpose* (startup shim before
the real entry point runs), different toolchain, not interchangeable.

**`PSECT` operand list** (ch. 3.1.1): `PSECT name,typelang,attrrev,edition,stacksize,entry` — all six are optional as a group (bare `PSECT` defaults `name` to `"program"` and everything else to 0). `name`: up to 20 printable non-space/non-comma bytes, used by RLINK to label the section in its own diagnostic output; doesn't need to be unique across PSECTs. `typelang`: the module type/language byte — **must be 0 for a non-mainline PSECT**; a non-zero value marks this PSECT as the program's mainline segment. `attrrev`: module attribute/revision byte. `edition`: the manual's own text describes this identically to `attrrev` ("module attribute/revision byte") — likely a duplication in the source manual, not resolved further here. `stacksize`: estimated stack bytes this PSECT needs; RLINK sums it across every linked PSECT and adds the total to the data-storage requirement. `entry`: program entry-point offset (0 for non-mainline PSECTs). Exactly one `PSECT` block per assembled file.

**Directives legal inside or outside any section** (ch. 3.1 — placement relative to `PSECT`/`VSECT`/`CSECT`/`ENDSECT` doesn't matter for these): `nam`, `opt`, `ttl`, `pag`, `spc`, `use`, `fail`, `rept`, `endr`, the `ifxx` family, `endc`, `else`, `equ`, `set`, `macro`, `endm`, `endsect`.

**Data-area register conventions** (ch. 6): by convention one index register holds the data area's base address and `DP` holds its lowest page number; RLINK auto-adjusts indexed/direct-page operands to match. **No-initialized-data programs** (VSECT storage declared with `RMB` only, ch. 6.2) get `U`=data-area start, `Y`=data-area end, `SP`=`Y`+1 (parameters, if any, land above `Y`), `DP`=start page number from OS-9 at launch; with no parameters, `Y`=`X`=`SP`. **This convention is universal OS-9 process-invocation behavior, not an RLINK-specific artifact** — `asm`/MIA's own manual (ch. 2.9.4) describes the identical `U`/`Y`/`SP`/`DP` setup for a plain single-file `MOD`/`EMOD` program with no RLINK involved at all, confirming it's a fact about how OS-9 launches any process, independent of which assembler/linker built it. A program can either keep `U` fixed and use constant-offset indexed addressing throughout, or compute real addresses once at startup and cache them as direct-page pointers. **Important**: PC-relative addressing cannot reach the data section from code — program and data sections aren't linked a fixed distance apart, unlike same-section PC-relative references. **Initialized-data programs** (ch. 6.3, needing `Root.a` as above): once `Root.a` runs, `Y`=bottom of the data area (the old `U`-equivalent — matches the C compiler's own data-pointer register choice so mixed-language linking works), `X`=parameter area, `U`=top of linker-allocated data.

**Running RLINK** (ch. 7.1): `rlink [options] mainline [sub1 {subN}] [options]` — `mainline` is the ROF containing the non-zero-typelang PSECT (external refs resolve against it, and the module header generates from it); additional ROFs are always included in the final module whether anything references them or not; no non-mainline ROF may itself contain a mainline PSECT.

**RLINK command-line options** (ch. 7.2):

| Option | Effect |
|---|---|
| `-o=path` | Write the linked memory module here; if `-n` isn't also given, the module gets named after this path's final component |
| `-n=name` | Explicit output module name |
| `-l=path` | Library ROF (a file of merged assembly ROFs) — each PSECT inside is pulled in only if it resolves a currently-unresolved reference; no mainline PSECTs allowed in a library file; libraries are searched in command-line order |
| `-e=n` / `-E=n` | Edition number for the output module (default 1) |
| `-M=size` | Extra data-area memory to allocate, in pages (or `K` for kbytes); if omitted, RLINK sums the stack-size operand from every linked PSECT instead |
| `-m` | Print a linkage map of each PSECT's assigned base address (distinct option from `-M=size` above — reproduced here exactly as the manual writes it, case distinguishing the two; verify live before scripting) |
| `-s` | Print final assigned addresses for all symbols |
| `-b=ept` | Link a C function so BASIC09's `RUN` can call it directly, entering at symbol `ept` |
| `-t` | Allow static data in a BASIC09-callable module, assuming the caller has already sized a static-storage area pointed to by `Y` |

**RMA vs. `asm`/MIA — the manual's own comparison** (Appendix A, "Differences Between RMA and the Microware Interactive Assembler"): RMA has no interactive mode, disk-file input only — implies MIA/`asm` *does* have one, consistent with `asm`'s still-unexplained `I` toggle noted at the top of this file; RMA emits a ROF that RLINK must process into an executable module, where MIA/`asm` emits an executable module (with `MOD`/`EMOD`) directly; RMA's `PSECT`/`VSECT` exist specifically to replace MIA's `MOD`/`EMOD` for this reason; RMA has no `SETDP` equivalent since RLINK, not the assembler, handles all data/DP allocation.

**Direct page selection** (`asm`/MIA only — not covered by the RMA manual, which has no `SETDP`; see above): the assembler tracks direct-page state and auto-selects direct vs. extended addressing based on whether an address's high byte matches the current `SETDP` value; force with a `<` (direct) or `>` (extended) prefix on the operand.

## RMA Source Format, Expressions, and Macros

**Input file format** (ch. 1.5): free-form ASCII lines terminated by return, **max 256 characters** each. Four fields per line: label (must start in column 1; if no label, the line's first character must be a space), operation mnemonic, operand, comment — fields separated by one-or-more spaces. A line whose first character is `*` is a full-line comment: it shows up in the listing output but the assembler otherwise skips over it. Empty lines are likewise skipped for assembly purposes yet still take up a line in the listing.

**Assembly listing format** (`-l`/`OPT L`, ch. 1.6), columns left to right: sequence number, location-counter value, generated object-code bytes (an `=` here flags an external reference in the operand; a `+` in the label-field column flags a line generated by macro expansion), then label, mnemonic, operand, comment.

**Expression evaluation** (ch. 1.7 — RMA's own assembly-time expression syntax; distinct from the interactive debugger's own calculator syntax documented under Debugger below, and not cross-checked against `asm`'s expression syntax, which this manual doesn't cover). All arithmetic is 16-bit (0..65535 unsigned / -32768..32767 signed); byte-sized operand contexts (e.g. 8-bit immediate loads) require -128..127 signed or 0..255 unsigned, else an error. Evaluated strictly left-to-right within a precedence tier; parentheses override. Operand forms: decimal (optional leading `-`, 1-5 digits, no prefix), hex (`$` + 1-4 hex digits), binary (`%` + 1-16 bits), character constant (`'` + one printable ASCII char), symbolic name (RMA's 1-9-char rule above), and `*` for the instruction counter's value at the start of the current line. Operator precedence, highest first: unary `-` (negate) and `^` (logical NOT); then `&` (AND) and `!` (OR); then `*`/`/` (multiply/divide, unsigned only); then `+`/`-` (add/subtract, signed or unsigned). Logical ops are bitwise. Division by zero and multiplication overflowing 65535 are errors with undefined intermediate results. A name used before its own definition is treated as external to the PSECT (recorded for RLINK to resolve later) — but assembler-directive operands (`FCB`, `EQU`, etc.) cannot contain external names at all, and ordinary instruction operands that do can only combine an external name with binary `+`/`-`, nothing else.

**RMA's macro facility** (ch. 2) is a separate mechanism from the Editor's `.MAC` macro system documented under Editor below — different tool, different syntax, not to be conflated. RMA macros are assembly-time text substitution: `name MACRO ... ENDM`, where `name` (the label on the `MACRO` line) becomes a new pseudo-mnemonic usable anywhere after its definition. Body statements can reference other, previously-defined macros (nesting up to 8 deep); defining a macro inside another macro's body is illegal. Redefining a real 6809 mnemonic (`LDA`, `CLR`, etc.) with a same-named macro is legal and is the manual's own documented technique for building a cross-assembler targeting a different instruction set; redefining an assembler directive (`RMB`, etc.) the same way is possible but has "unpredictable consequences" per the manual. Macro source text lives in a temporary work file with a 1K buffer, so heavily-macro'd programs should define short, frequently-used macros first to keep them cached rather than re-read from disk.

**Macro arguments**: up to 9 positional, `\1`-`\9`, substituted only in the operand field (never the label or mnemonic fields) of body statements, replaced by the literal actual-argument text from the macro call. An actual argument containing a comma or backslash must be double-quoted so it isn't parsed as multiple arguments. Omitted trailing arguments become empty strings — no substitution occurs, not a zero value. Two read-only operators support argument validation: `\Ln` = byte length of actual argument `n`; `\#` = count of actual arguments passed in this call — both are typically paired with `IFxx`/`FAIL` inside the macro body to reject bad calls.

**Macro automatic internal labels**: `\@` (with an optional letter/digit suffix, placed either right after the `@` or right before the leading `\`) generates a label unique to that expansion, so a macro needing an internal branch target doesn't collide with itself when used repeatedly. The generated form is `@nnnX`, where `nnn` is a 3-digit sequence number (000-999) incrementing once per expansion of that macro call, and `X` is whatever suffix was given — a macro using both `\@A` and `\@B` produces `@001A`/`@001B` on its first call, `@002A`/`@002B` on its second, and so on.

## DEFS Files (assembly-time symbolic constants)

- `OS9Defs` — service request codes, signal codes, status codes, direct-page variable names, module type/language/attribute masks, process descriptor layout, path descriptor offsets, register-stack offsets, condition code bits, error codes.
- `SCFDefs` — SCF device static storage layout, XON/XOFF character definitions, SCF-specific path descriptor fields.
- `RBFDefs` — RBF path/device/file descriptor layouts, segment list format, directory entry format, drive table layout.
- `SysType` — CPU type, MMU type, CPU speed, disk controller, clock module, PIA type, and other build-time system configuration constants.

Installation convention (ch. 2.2, `asm`/MIA): `asm` itself lives in
`CMDS`, and the `DEFS` directory sits at the root of the system disk —
programs `USE` it with a full pathlist like `/D0/DEFS/OS9Defs`. Actual
on-disk DEFS filenames can vary by system/release (the manual's own
example: a Level Two system's file may be named `os9defs.lii` rather than
plain `os9defs`) — not independently checked against this project's own
disk images.

`Source` (via `grep` on the EOU disk's real
`DEFS/os9defs.a`, an open-source NitrOS-9 file): `Prgrm`=$10, `Objct`=1,
`ReEnt`=%10000000($80) — matches `syscalls-and-module-format.md`'s module
type/attribute table exactly, and cross-validated independently against
`ident`'s own decode of real system modules (`Ty/La At/Rv: $11 $81`/`$82`
= `Prgrm+Objct`, `ReEnt`+revision). **Implementation trivia not previously
documented**: `os9defs.a` doesn't define `I$`/`F$` call codes as literal
`EQU` values — each name is a `RMB 1` entry in a running counted table
(`I$Read: RMB 1`, `I$ReadLn: RMB 1`, etc.), so a call's numeric code is
its *position* in that table, assigned by the assembler's own location
counter rather than hand-written per name.

## Debugger

Full command set (`Manual`, cross-referenced across the two debugger manuals). The `:` register-display command is `Live`: `debug <modulename>` launches the Interactive Debugger and `:` prints exactly the documented header row and column order (`SP  CC  A  B DP  X    Y    U    PC`), and the entry-state `CC` value observed genuinely had bit 7 (E flag) set, confirming the "must be set or `G` won't resume correctly" claim below is the real entry convention, not just a manual assertion. `B`/`G`/`M`/`E` are now also `Live` (a full write-assemble-debug cycle: set breakpoints with `B <addr>`, `G` to run to them, `M <range>` to dump memory, catching a real register-clobbering bug by direct observation this way). `Live` nuance: `L <name>` (link to a module by name) only finds modules already in the live module directory — it does not appear to register a module merely opened as `debug <file>`'s own command-line target, so `L` right after `debug <file>` may fail with `Error #221 - Module Not Found` even using the module's correct (case-sensitive) internal name from its `fcs`-defined name field, not the filename. Not fully root-caused; treat `L` as reliable only for modules independently linked/resident (e.g. via `E`, or already loaded by the shell), not as a way to jump to the header of whatever `debug` just opened. **`E` shares this same limitation** — `Live`: `E <modname> <params>` gives the identical `Error #221 - Module Not Found` unless the module has already been `load`ed into the module directory first; `E`'s own act of loading-for-execution isn't enough to satisfy a *subsequent* `L`/`E` lookup by name within the same debug session. Separately, **a module linked multiple times across a session needs one `unlink` per link, not one total** — `Live`: after linking the same module via a sequence of `L`/`E`/shell-run calls, `mdir` kept showing it resident until four separate `unlink <name>` calls had been issued (matching the number of linking events), not one. **`mdir`'s own listing isn't necessarily exhaustive** — `Live`, 2026-07-19: immediately after a program successfully `F$Load`ed a module (confirmed by a valid returned entry point, no error) and while that same program was itself still the running process, `mdir` showed neither the just-loaded module *nor the running program's own module* in its output. Don't treat `mdir` as a reliable way to confirm whether a specific module is really resident — a `Live` syscall result (a real returned address, no error) is stronger evidence than `mdir`'s absence of an entry.

**2026-07-19: the remaining commands are now `Live` too — calculator mode, all four Dot-navigation forms, `:reg` get/set, `S` (search), `$` (shell escape), and `Q`.** Driven interactively against `debug /dd/CMDS/linkforktest` (one of the syscall regression-test binaries above, already resident on disk):
- **Calculator** (` 5+3`) printed `$0008 #00008` — exact documented hex+decimal format.
- **Dot navigation**: `. $100` set Dot and showed `0100 FF`; a bare Enter incremented to `0101 FF`; `-` decremented back to `0100 FF`; setting `. $200` then `..` correctly recalled the prior value, landing back on `0100 FF`.
- **`:reg` get/set**: `:A` printed `72`; `:A $55` set it with no separate output; a follow-up `:A` confirmed `55`.
- **`S expr1 expr2`**: searching from a valid code address (`. $E8D4`, the module's own entry point, taken from a `:` register dump's `PC` column) for the 2-byte pattern `$50 $41` (`'P'`,`'A'`) found a match and moved Dot to it (`E8F8 41`) — searching from address `$0` first found nothing, likely because low direct-page memory isn't meaningful search territory; **always search from a real code/data address, not an arbitrary one**.
- **`$ dir`** ran the shell command and returned cleanly to `DB:` afterward.
- **`Q`** quit back to the OS-9 shell prompt cleanly.

- **`K expr`** cleared exactly the named breakpoint, leaving the rest set;
  bare **`K`** cleared all of them. Verified by setting two (`B 1000`,
  `B 2000`), listing with `B` (`1000 2000`), clearing one (`B` then showed
  `2000` alone), then clearing all (`B` then listed nothing).

The entire documented debugger command set is now `Live`.

| Command | Effect |
|---|---|
| *(space)* `expr` | Calculator: evaluate and print in hex + decimal |
| `.` | Show Dot (working address) and its contents |
| `. expr` | Set Dot, then show it |
| `..` | Recall the *previous* Dot value |
| `-` | Decrement Dot, show it |
| *(bare return)* | Increment Dot, show it — steps through memory sequentially |
| `= expr` | Write to the address at Dot, verify the write, advance Dot |
| `:` | Show all registers: `SP CC A B DP X Y U PC` |
| `:reg` | Show one register |
| `:reg expr` | Set one register (8-bit registers error if the value doesn't fit in a byte) |
| `B` / `B expr` | List breakpoints / set one (max 12) |
| `K` / `K expr` | Clear all breakpoints / clear one |
| `G` / `G expr` | Resume execution / resume at a specific address |
| `M expr1 expr2` | Hex+ASCII memory dump between two addresses |
| `C expr1 expr2` | Walking-bit RAM test + clear between two addresses — destructive, RAM only |
| `S expr1 expr2` | Search memory from Dot for a 1- or 2-byte pattern |
| `E text` | Load a program for execution (like Chain, but keeps the debugger resident as a coroutine); shows the initial register dump; `G` actually starts it |
| `L text` | Link to a module by name; sets Dot to its first byte |
| `$` / `$ cmd` | Drop into the OS-9 shell / run one shell command, returning to the debugger afterward |
| `Q` | Quit (via `F$Exit`) |

**Breakpoint mechanism**: implemented with the 6809 `SWI` instruction, inserted/removed transparently by the debugger. Restrictions: RAM only (not ROM), must sit on an instruction's first opcode byte, max 12 simultaneous, and **user code cannot use plain `SWI`** (reserved for the debugger) — but `SWI2`/`SWI3` are fine, since `SWI2` is what ordinary syscalls already use and `SWI3` is available for user vectoring. A loop needs *two* breakpoints if you want it to stop on every iteration, not one.

**Register display**: `SP CC A B DP X Y U PC`, one line of names, hex values below. `CC` bit 7 (E flag) must be set or `G` won't resume correctly. `SP` points at the bottom of the saved register block when a breakpoint fires.

**Expression syntax**: hex is the default (`$` prefix optional), `#` for decimal, `%` for binary, `'` for a one-character ASCII constant, `"` for two characters. Indirect addressing: `<expr>` (byte) or `[expr]` (word). 6809 indexed addressing can be written in the calculator as `(:D+:Y)`, equivalent to assembly's `[D,Y]`.

## Editor

Line-and-buffer oriented, not screen-oriented (no cursor addressing — matches the "no termcap" reality noted in `unix-differences.md`). Two buffers (primary/secondary) with `P`/`G` to move lines between them, `B n` to switch primary.

**2026-07-19: attempted live, inconclusive — the on-disk tool's identity doesn't clearly match this section.** `ed` on this EOU test disk is a completely different program: a mouse/joystick-driven full-screen GUI text editor needing a 640×192×2 graphics window (`Ed [filename]` — "80x24 mouse/joystick based Text Editor"), not a line-and-buffer tool at all. A second candidate, `edt`, does launch something calling itself "6EDT Version 2.0 11-30-86" with a terminal-style prompt, but a probe command in the documented insert syntax (`I 1 hello world`) produced an ambiguous, hard-to-parse response that didn't clearly confirm or refute the `L`/`X`/`I n str` command shapes below. Rather than force a confirmation from an unclear result, this is left `Manual` — whoever picks this up next should first identify which command actually is the Microware line editor this section's source (the "Assembler/Editor/Debugger Manual") describes, possibly by checking `6EDT`'s own on-disk help/banner more carefully or looking for a different community disk image where the vintage tool is preserved under its original name.

Core navigation/edit: `L n` (list forward) / `X n` (list backward, i.e. before pointer) / `+n`/`-n` (move by lines) / `>n`/`<n` (move by characters) / `^` (buffer start) / `/` (buffer end) / `K n` (kill n chars) / `D n` (delete n lines) / `I n str` (insert) / `E n str` (extend/append) / `U` (unextend/truncate line) / `C n str1 str2` (change) / `S n str` (search) / `T n` (tab to column) / `A n` (anchor search/change to column n).

**Macro system** (the Editor's own macro facility — a different mechanism from RMA's assembly-time `MACRO`/`ENDM` facility documented under RMA Source Format, Expressions, and Macros above; don't conflate the two): `.MAC "name"` opens a macro for editing; parameters are `#var` (numeric) or `$var` (string); `[commands]n` loops the bracketed commands n times (or `*` = as many as possible, exiting early if any command fails); `:` is a conditional — skip to end of loop/macro unless the fail flag is set, then clear it. Test commands that set/clear the fail flag: `.EOF`/`.NEOF`, `.EOB`/`.NEOB`, `.EOL`/`.NEOL`, `.STR str`/`.NSTR str`, `.ZERO n`, `.STAR n` (true if n = 65535, the wildcard value). `.S`/`.F` force-exit a loop/macro with the fail flag cleared/set respectively.

File/shell integration: `.READ str`/`.WRITE str` redirect the editor's input/output file (empty string restores the original); `.SHELL text` runs an OS-9 shell command without leaving the editor; `.LOAD str`/`.SAVE str1 str2` load/save named macros to a file; `Q` writes remaining buffer content and exits.

---

**Sources:** OS-9 Interactive Debugger Users Manual, OS-9 Assembler/Editor/Debugger Manual (a generic Microware manual despite shipping with Dragon systems — confirmed no Dragon-specific hardware content during extraction; now **fully mined across all three chapters** — Editor, Assembler/`asm`/MIA ch. 2, and Interactive Debugger ch. 3, not just Editor+Debugger as in an earlier pass), OS-9 Relocating Macro Assembler Manual (RMA options, input/listing format, expression evaluation, macro facility, PSECT/VSECT/CSECT semantics, data-area access, RLINK/linker options, and the RMA-vs-Microware-Interactive-Assembler differences appendix — `Manual` only, `rma` hangs on this project's live-test setup; see the `rma` entry above).
