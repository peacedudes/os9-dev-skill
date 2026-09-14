# Reference Index — read the matching row(s) before answering

Topic → target → file. Keywords are deliberately dense; scan for yours.

**Directory convention.** `common/` holds what applies to both targets — but
where a value differs, **68k is the default** and the 6809 delta is called
out inline or lives under `6809/`.

**So an unqualified value in `common/` is a promise that it holds on both
targets.** When writing here, either verify that or mark the scope inline —
an unmarked 68k-only fact is indistinguishable from a verified shared one,
and the reader has no way to tell which they are looking at. This is not
hypothetical: `common/` carried "super-user = group 0" bare in four places,
which is true on 68k and false on 6809 (flat user ID 0) — a privilege guard
written from the bare claim classifies every ordinary 6809 account as
privileged. The canonical statement of that particular delta lives once, in
`6809/syscalls-and-module-format.md`.

**State a cross-target delta once and link to it.** Restating it in each file
that touches the topic creates copies that drift apart, and a reader who
finds one copy cannot tell whether the others still agree.

**`common/` is where a delta gets stated, but not everything in it is
shared.** Two files there are 68k-only despite the directory, each with a
6809 counterpart; cite them by full path, never by bare filename:

- `common/utility-usage.md` (v2.4 68k utility set) ↔ `6809/utility-usage.md`
- `common/using-os9exec-repl.md` (os9exec is the 68k emulator) ↔
  `6809/using-nitros9-repl.md`

## Symptom → cause (when you have a failure, not a topic)

The rest of this index is organised by topic. This table is the other door:
you have a symptom and no idea which topic it belongs to. Every cause here
has bitten a real session.

| Symptom | Likely cause | Where |
|---|---|---|
| Assembles clean, won't run / `ident` shows nothing sane | assembler wrote an object *despite* errors — check the error count | `6809/assembly-and-tools.md` |
| Rebuild behaves exactly like the old binary | `r68 -O=`/`l68 -o=` didn't overwrite; you ran the stale file | `68k/os9-68k-assembly.md` |
| Build reports success, no output file where you looked | output goes to the **execution** directory, not the data directory | both assembly files |
| Assembly "silently succeeded" but nothing works | you redirected the assembler's stdout — errors went with it | `6809/assembly-and-tools.md` |
| Module runs but its data area is wrong / corrupt scratch | `mod` data size written with `*` (program counter) instead of `.` | `6809/assembly-and-tools.md` |
| `mdir` shows a different name than the file you linked | the module name comes from `l68 -o=`, not the source | `68k/os9-68k-assembly.md` |
| Link fails on `I$`/`F$` symbol names | call names aren't defined anywhere — declare them yourself | `68k/os9-68k-assembly.md` |
| Program opens a file, reads nothing, and reports on it anyway | the SDK `cio` library's trap-13 selectors hit the `cio` module's memory routine — rebuild trap-free (`-qm`) | `c/os9-c-cheatsheet.md` |
| Unsure whether a fault is yours or the system's | run a period-built program that does the same thing on the same disk — it differs from yours only in who compiled it | `common/using-os9exec-repl.md` |
| Program needs Enter after every key though it called `cbreak()` | `cbreak()` sets a curses flag only; stdio `getchar()` ignores it — read with `getch()` | `c/os9-clib-reference.md` |
| `popen of "..." failed!` | reported to need `shell` reachable and the named program in the **data** directory, not on `chx` — `Hearsay`, unmeasured | `c/os9-clib-reference.md` |
| `E_FNA` (214) opening a file that is present and readable | a leading space in the pathname — `F$PrsNam` does not skip one, and the failure surfaces at the open as a permission error | `68k/syscall-reference.md` |
| Full-screen program refuses to start (`Unknown terminal type`) or draws only part of its screen | a modern `TERM` it does not know — try `TERM=vt100` before suspecting the program | `common/using-os9exec-repl.md` |
| A program's last line of output is missing, or the prompt sits on top of it | the message ended in a bare CR and the prompt overwrote it — append `; echo ""` | `common/using-os9exec-repl.md` |
| EVERY line overwrites the last, or programs seem to print almost nothing | `PD_ALF` cleared on the device — no LF follows CR. Check the raw CR:LF ratio; no bytes are lost | `common/memory-and-io.md` |
| Shell says `User abort` / `Error #000:002` / `E_???` and nobody pressed a key | a child's non-zero exit status is printed through the error table as though it were an error code — a GNU port that prints usage and `exit(2)` does this every time | `common/os9-tools-and-shell.md` |
| `r68`: `branch out of range` on a branch to the very next line | it is too **close**, not too far — the short form would need displacement 0, which is the reserved "use the word form" encoding; drop the `.s` | `68k/os9-68k-assembly.md` |
| `r68` error points at an instruction that is plainly correct | the diagnostic is printed **above** the line it refers to — read the line *after* the `*** error ***` | `68k/os9-68k-assembly.md` |
| A conversion tool or port hangs at 100% CPU with no error | an unbounded scan: os9exec's arena is zeroed, so an out-of-bounds read finds no terminator and never stops | `common/using-os9exec-repl.md`, `c/kandr-vs-ansi.md` |
| Output stops at a suspiciously round byte count | a stdio buffer boundary, not a write ceiling — the program stopped writing | `common/using-os9exec-repl.md` |
| `E_PNNF` (216) on a file you just created and can see on the host | the device is an RBF **image**, a snapshot — the file is not inside it until the image is rebuilt; a host directory would have shown it at once | `common/using-os9exec-repl.md` |
| An RBF image turns out damaged, with no telling when | two emulator processes had it open at once, each caching its own allocation bitmap — one writer per image; `lsof` before starting a harness | `common/using-os9exec-repl.md` |
| `E_PNNF` (216) on a relative pathlist containing `../..` or a mixed dot-run, on an RBF image | an os9exec defect before `985e0d8`, not OS-9 — dot-runs compose and may be mixed; host-directory devices were always correct | `common/unix-differences.md` |
| `^syntax error` and nothing runs, from a batch invocation | a shell option written on the command line — `-nx` belongs on the procedure file's first line | `common/using-os9exec-repl.md` |
| `c68` says `; expected` / `expression with little effect` on correct-looking C | adjacent string literals — nothing in this toolchain joins them, and `cccp2` runs `-traditional` | `c/kandr-vs-ansi.md` |
| `**** multiple definition ****` on parameter declarations that look right | `ansi2knr` was run on an already-K&R tree and rewrote its own output | `c/kandr-vs-ansi.md` |
| "Can't find" a command that is plainly present | fork lookups use `chx`, not `PATH` | `common/using-os9exec-repl.md` |
| Redirect produced error text, or clobbered the file | `>>` is **stderr**; append is `>+`; plain `>` fails if the file exists | `common/os9-tools-and-shell.md` |
| `Wildcard match failed` — the command never ran | a `*`/`?` pattern matched no file, which aborts the command instead of passing through; `?` in a borrowed `$?` idiom does this too | `common/os9-tools-and-shell.md` |
| A batch run stalled, or later procedure lines never executed | either an earlier command failed (`-x` abort-on-error is the default, and the skipping is announced by nothing) or a utility hit an interactive prompt — classically `copy` without `-r` — and read your remaining lines as its answers | `common/using-os9exec-repl.md` |
| `can't execute "<the name you typed>"` with `E_FNA`/214 | the procedure file is in the execution directory; bare-name procedure lookup resolves against the *data* directory | `common/os9-tools-and-shell.md` |
| `can't execute "<a word you never typed>"` | you named a data file, and the shell is running its contents as commands — the quoted word came from inside the file | `common/os9-tools-and-shell.md` |
| A file you just created won't open, or `dir` shows a shorter name than you gave | names address only their first 27 characters, so a longer one is reachable by its prefix alone — and two long names sharing that prefix are one file | `common/unix-differences.md` |
| Compiler reads the whole source as one line | source has LF endings; OS-9 needs CR-only | `common/using-os9exec-repl.md` |
| Same symptom after editing a file you did not create | it was already CR-only and `flip -m` ran again, collapsing it; `flip -t` first | `common/using-os9exec-repl.md` |
| `cpp` dies on a `.dat`/data file you never thought of as source | it is `#include`d as C initialisers — the CR rule applies by USE, not by extension | `common/using-os9exec-repl.md` |
| Program builds and runs but misreads its own data file | LF endings in runtime data: the silent form of the CR rule, nothing reports it | `common/using-os9exec-repl.md` |
| OS-9's `unshar` says `No shell commands in <file>` | the archive was transported without converting to OS-9 text | `common/using-os9exec-repl.md` |
| Program dies immediately with a trap-handler banner | linked against the proprietary `cio`, absent from this disk | `common/using-os9exec-repl.md` |
| Harness times out with the command visibly working | prompt gate doesn't recognise a sub-program's prompt — use raw keys | both REPL files |
| Session hangs or dies on a syscall that looked ordinary | `F$SSvc`/`F$IOQu`/`F$NProc` (6809), `F$SysDbg`/`F$RTE` (68k) | both REPL files |
| Fix has no effect although the rebuild succeeded | besides a stale output file (above): the crashed module is **still resident** and shadows the new one | `basic09/basic09-per-target.md` |
| `Exception: ... vector=$08 err=#000:108` (E$Violat) at an ordinary-looking instruction, classically `MVSR2.W` / `MOVE SR,<ea>` | the binary was built for a 68000, where reading SR is user-legal; it is privileged from the 68010 on, and the system is not emulating it. os9exec v4.0.0 did this to every RTF Fortran program; later builds do not | `68k/os9-68k-assembly.md`, exception vector table |
| `Error #001 — Unconditional Abort` printed after output that was correct | `F$Exit` called with `B` never cleared — cosmetic, not a real failure | `6809/syscalls-and-module-format.md` |
| Breakpoint or examine lands at the wrong address | `sc`'s listing double-applies an offset — never take an address from it | `common/using-os9exec-repl.md` |
| `-d 2` trace shows a `<<<` return under the wrong call name | a nested call overwrote the per-process current-call field — pair returns to entries by position | `common/using-os9exec-repl.md` |
| `Error #000:043` from BASIC09 — and you can't tell if anything failed | four unrelated causes share this code; two of them mean the operation succeeded | `basic09/pack-and-runb.md` |
| A listing is short, or something you know exists reads as absent | page pause ate the tail (`tmode pag=0`), or a filter dropped the marked entries | `common/using-os9exec-repl.md` |
| Output stopped dead, no error, session otherwise alive | a stray `$13` (XOFF) reached the terminal; SCF swallowed it and is holding output until `$11` | `common/os9-tools-and-shell.md` |
| Ctrl-C/Ctrl-E killed the wrong process | both go to the device's last writer, not a process you name — use `kill <pid>` | `common/using-os9exec-repl.md` |
| Separate writes run together / output garbled | `I$WritLn` writes **to the first CR** — a buffer without one runs past its end | `common/memory-and-io.md` |
| A console line stops ending on Enter, or a read returns fewer bytes than asked | on SCF the terminator is **PD_EOR**, not literally CR — `tmode eor=` or a program's SS_Opt moved it. Set to zero, I$Read runs to its full count (the raw-input idiom); the manual warns I$ReadLn then ends only on EOF or error | `common/memory-and-io.md` |
| BASIC09 `E`, bare `E` or `LOAD` fails `#248 - Media Full`, `0 free` workspace at any `#nk` | a stray second CR in the boot autotype reached the guest — restart it | `6809/using-nitros9-repl.md` |
| TCP connects but no banner ever arrives | an earlier session closed without logging out; or channels exhausted after a few connect/detach cycles even with clean logouts | `6809/using-nitros9-repl.md` |
| Nothing listening at all, guest looks dead | the DriveWire *server* crashed — check host crash reports before diagnosing the guest | `6809/using-nitros9-repl.md` |
| Session died while listing a directory | channel-filling output kills it — narrow the listing or read the image host-side | `6809/using-nitros9-repl.md` |
| Session ended while sending ordinary content | Escape (`$1B`) is SCF's EOF — the shell exited normally on it | `6809/using-nitros9-repl.md` |
| File written through the harness fails to parse at a line that looks fine | `tee` dropped a trailing CR under load, joining two lines silently | `6809/using-nitros9-repl.md` |
| Transfer traffic appears on your own terminal; the device argument did nothing | `kermit` needs `l` to aim at a device, and ignores it silently without | `common/utility-usage.md` |

Error *codes* (number → meaning) are a different lookup: `common/error-codes.md`.

## Quick rosetta (inline — check before loading a file)

- `fork()`/`exec()` → `F$Fork` / `F$Chain`
- file descriptor → path number
- pipe syntax is **`!`**, not `|`; `>>` redirects **stderr**, not append —
  append is **`>+`** (`>-` truncates, plain `>` fails if the file exists)
- climbing: write `...` (one dot per level plus one) — runs compose and add; `../..` also works but the dotted form is the OS-9 one
- Ctrl-C backgrounds; **Ctrl-E** is the kill key; ESC on a blank line
  exits the shell
- shared memory → data modules; `/dev` + VFS → descriptors + file managers
- more memory for a program (BASIC09 especially): `cmd #32k` modifier
- Full mappings and traps: common/unix-differences.md (Tier 1 first)

## Common (both architectures)

| Question about… | Read |
|---|---|
| General concepts: modules, link counts, process model, scheduler (priority+aging), two current directories (chd/chx), I/O layering (file manager / driver / descriptor), CR line endings, big-endian | common/os9-mental-model.md |
| "How do I do `<Linux thing>` in OS-9?", Unix-habit traps, K&R-not-ANSI, mknod/directory-open surprises, signal contract vs Unix | common/unix-differences.md |
| Shell syntax (`;` `&` `!` separators, `<` `>` `>>` redirection, `#nk` memory modifier), wildcards, built-ins (chd/chx/ex/profile/setenv/set), PROMPT, procedure files, control keys and line editing (Ctrl-A recall, Ctrl-W pause, ESC=EOF), page pause, the standard utility catalog (attr…xmode) | common/os9-tools-and-shell.md |
| Per-command **syntax and options** for every v2.4 utility (dir -e, copy -w, del -f, load -d, dsave/fsave/frestore flags, format/os9gen, fixmod -u, grep/pr/qsort/tr, tape…), the `-z`/`-x`/`-b=` conventions, `tee >file` heredoc, full tmode/xmode parameter table (eof=, abort=, quit=, pag=, baud…), the 68k baud code table and what `tmode baud=` really writes, `kermit` flag traps (`l`, `i`-not-`8`) | common/utility-usage.md |
| Module header fields/offsets, type/language/attribute codes, permissions, header parity, CRC, module directory mechanics, module groups, a6 bias, trap libraries vs subroutine modules, Math module, data modules, boot-time module discovery, INIT module, l68/ROF/linker facts, ident/fixmod/mdir | common/module-format.md |
| Memory allocation (first-fit/buddy, colored memory, 32-segment limit, malloc/_srqmem/_lmalloc, edata/end), device descriptors (M$Mode/M$DevCon/M$Opt), path descriptors (PD_OPT, PD_COUNT), I$Attach matching, device static storage, I$ call behavior table, device naming (/dd /h0 /term /nil), fork-time memory regions | common/memory-and-io.md |
| Signals (codes, masking, queuing, intercept), alarms (guard/ticker patterns), events (the one sync primitive), pipes (named vs unnamed, 90-byte default, EOF/deadlock rules), **record locking** (RBF's automatic read/write byte-range locks, EOF lock, lost-update-race-for-free design pattern), data-module IPC patterns, reentrancy in system state | common/ipc.md |
| `Error #NNN:MMM` format, full E$ table 000–255, BASIC09-internal errors 10–80, errno/ERR conventions, cross-manual discrepancies | common/error-codes.md |
| Driving the os9exec emulator/REPL as an agent: launch/OS9DISK gotchas, gated-vs-raw send, grep -a, editing files (vi/tee/flip), compiling C end-to-end, BASIC09 session mechanics, cio trap-handler triage, accounts/login/.login, chx-vs-PATH fork rule, RBF image vs host directory, symlink quirks, stopping runaways, idbg, the OS-9 `debug` command (sc/gs defects) | common/using-os9exec-repl.md |

## BASIC09 (same language on both targets — read basic09-language.md first)

| Question about… | Target | Read |
|---|---|---|
| Syntax, types, PROCEDUREs, I/O, operators, functions, error handling, debug mode | all | basic09/basic09-language.md |
| Numeric widths/ranges/precision per target, INTEGER overflow, hex-constant sign flip, REAL formats and the single-precision-`math` trap, 68k-only commands (SHELL/CHAIN/command-line PARAM), Graphics Interface Module, **calling 68k assembly or C from BASIC09** (worked `psect`/`r68`/`l68` examples) | both | basic09/basic09-per-target.md |
| Digest of every trap, one line each with a pointer: porting hazards, fabricated syntax, surprising behavior | all | basic09/gotchas.md |
| **"BASIC09 ran out of workspace"** — the fix is the shell's `#<size>k` modifier (`basic09 #32k`), not anything inside the language | all | common/os9-tools-and-shell.md |
| PACK, RunB, packed-module resolution (F$Link/CHX), PARAM argument binding, "Can't install trap handler" triage | all | basic09/pack-and-runb.md |

## C

| Question about… | Read |
|---|---|
| K&R vs ANSI constructs, prototypes, missing headers | c/kandr-vs-ansi.md |
| `cc` invocation, CLIB/CDEF, compiler quirks, calling C from BASIC09 (6809 c-link) | c/os9-c-cheatsheet.md |
| Standard library behavior (stdio/strings/malloc/os9fork) | c/os9-clib-reference.md |

## 68k

| Question about… | Read |
|---|---|
| F$/I$ syscall catalog, TRAP #0 convention, register contracts, F$Event/F$Alarm subfunctions, debugger-support calls (F$DFork/F$DExec) | 68k/syscall-reference.md |
| Assembly: register conventions, program-entry register state, embedded asm, exception vectors, TRAP mnemonics, `r68`/`l68` gotchas | 68k/os9-68k-assembly.md |
| **Working `psect` syntax for a hand-written 68k module** (the assembly file flags this as a manual gap; the only live-verified example lives here) | basic09/basic09-per-target.md |
| TCP/IP sockets, SOCKMAN/IFMAN/mbuf, hosts/inetdb config, ifgen/ipconfig/routed, ftp | 68k/network-sockets.md |

## 6809

| Question about… | Read |
|---|---|
| Driving live NitrOS-9 as an agent (nitros9repl.sh), stock-inetd `tcp listen`/`join` bridge, per-connection login and session ownership, no `.login` on 6809, DriveWire facts, SCF Escape=EOF, echo/auto-LF gotchas | 6809/using-nitros9-repl.md |
| Registers, SWI2 syscall convention, F$/I$ code catalog, which calls need supervision before you automate them, 6809 module header bytes | 6809/syscalls-and-module-format.md |
| Per-command syntax/options for the Level 2 utility set (attr…xmode, tmode/xmode parameter table, CoCo/Dragon-only commands called out separately), **making a bootable disk — `os9gen`/`cobbler`/`config` — plus `modpatch`**, Level1-vs-Level2 divergences found while cross-checking | 6809/utility-usage.md |
| Assembler directives (asm/RMA), editor, debugger command set, RLINK | 6809/assembly-and-tools.md |
| BASIC09 `RUN GFX(...)`/`RUN GFX2(...)` graphics/windowing subroutine calls: per-function syntax, window/device-window lifecycle (DWSET/DWEND/OWSET/SELECT), Get/Put buffers, palette/color, cursor/text control | 6809/gfx-windowing.md |
| **Seeing** the CoCo screen (screenshots via cocoscreen.sh), injecting keystrokes, CLEAR=backtick screen cycling, windint `$1B` escape-code table, creating graphics windows with wcreate, why XRoar's `-gdb` is a dead end | 6809/reading-the-coco-screen.md |
| CoCo/Dragon hardware (VDG, graphics, mouse, ACIA, drives, monitors), the Boot List Order Bug, ToolShed host-side disk editing and its own traps | 6809/coco-dragon-hardware.md |
| Level 1 vs Level 2, MMU/DAT internals, GMX III | sibling skill: os9-systems-dev `6809-level2-mmu.md` |

## Confidence

Tag legend and what each tag licenses: `CONFIDENCE-TAGS.md`. Every claim
carries its own inline tag; this table is only the shape of the coverage, for
deciding how hard to lean on a file before opening it.

| Area | Mostly |
|---|---|
| 68k `common/`, `c/`, and BASIC09 on both targets | `Live` (os9exec) |
| 6809 assembler/debugger core, ~70 of ~93 documented `F$`/`I$` calls, most `gfx-windowing.md` calling sequences, some `6809/utility-usage.md` items | `Live` (NitrOS-9) |
| Rest of the 6809 syscall catalog and utility set | `Manual` / `Source` |
| `6809/coco-dragon-hardware.md`, `68k/network-sockets.md` | `Manual` only |
