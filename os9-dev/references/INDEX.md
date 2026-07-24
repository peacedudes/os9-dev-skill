# Reference Index — read the matching row(s) before answering

Topic → target → file. Keywords are deliberately dense; scan for yours.

**Directory convention.** `common/` holds what applies to both targets — but
where a value differs, **68k is the default** and the 6809 delta is called
out inline or lives under `6809/`. Two files there are 68k-only despite the
directory, each with a 6809 counterpart; cite them by full path, never by
bare filename:

- `common/utility-usage.md` (v2.4 68k utility set) ↔ `6809/utility-usage.md`
- `common/using-os9exec-repl.md` (os9exec is the 68k emulator) ↔
  `6809/using-nitros9-repl.md`

## Quick rosetta (inline — check before loading a file)

- `fork()`/`exec()` → `F$Fork` / `F$Chain`
- file descriptor → path number
- pipe syntax is **`!`**, not `|`; `>>` redirects **stderr**, not append
- `../..` → `...` (one more dot per level, not more `../`)
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
| Per-command **syntax and options** for every v2.4 utility (dir -e, copy -w, del -f, load -d, dsave/fsave/frestore flags, format/os9gen, fixmod -u, grep/pr/qsort/tr, tape…), the `-z`/`-x`/`-b=` conventions, `tee >file` heredoc, full tmode/xmode parameter table (eof=, abort=, quit=, pag=, baud…) | common/utility-usage.md |
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
| Driving live NitrOS-9 as an agent (nitros9repl.sh), DriveWire facts, SCF Escape=EOF, no-echo gotchas | 6809/using-nitros9-repl.md |
| Registers, SWI2 syscall convention, F$/I$ code catalog, 6809 module header bytes | 6809/syscalls-and-module-format.md |
| Per-command syntax/options for the Level 2 utility set (attr…xmode, tmode/xmode parameter table, CoCo/Dragon-only commands called out separately), Level1-vs-Level2 divergences found while cross-checking | 6809/utility-usage.md |
| Assembler directives (asm/RMA), editor, debugger command set, RLINK | 6809/assembly-and-tools.md |
| BASIC09 `RUN GFX(...)`/`RUN GFX2(...)` graphics/windowing subroutine calls: per-function syntax, window/device-window lifecycle (DWSET/DWEND/OWSET/SELECT), Get/Put buffers, palette/color, cursor/text control | 6809/gfx-windowing.md |
| **Seeing** the CoCo screen (screenshots via cocoscreen.sh), injecting keystrokes, CLEAR=backtick screen cycling, windint `$1B` escape-code table, creating graphics windows with wcreate, why XRoar's `-gdb` is a dead end | 6809/reading-the-coco-screen.md |
| CoCo/Dragon hardware (VDG, graphics, mouse, ACIA, drives, monitors), boot/disk patching (MODPATCH/COBBLER/OS9GEN), ToolShed host-side disk editing | 6809/coco-dragon-hardware.md |
| Level 1 vs Level 2, MMU/DAT internals, GMX III | sibling skill: os9-systems-dev `6809-level2-mmu.md` |

## Confidence

Tag legend and what each tag licenses: `CONFIDENCE-TAGS.md`. Every claim
carries its own inline tag; this table is only the shape of the coverage, for
deciding how hard to lean on a file before opening it.

| Area | Mostly |
|---|---|
| 68k `common/`, `c/`, and BASIC09 on both targets | `Live` |
| 6809 assembler/debugger core, ~70 of ~93 documented `F$`/`I$` calls, most `gfx-windowing.md` calling sequences, some `6809/utility-usage.md` items | `Live` |
| Rest of the 6809 syscall catalog and utility set | `Manual` / `Source` |
| `6809/coco-dragon-hardware.md`, `68k/network-sockets.md` | `Manual` only |
