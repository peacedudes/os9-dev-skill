# OS-9 Module Format

The unit of loadable code and data is the **memory module**: standard
header + body + trailing 24-bit CRC, tracked by name in the kernel's
module directory (lifecycle: `os9-mental-model.md`). This file documents
the 68k encoding as the default; 6809 byte values are a separate section
and must never be blended with the 68k tables. BASIC09 packed modules and
RunB: `basic09/pack-and-runb.md`.

Core facts:

- **Position independence (68k):** compilers emit PIC automatically; hand
  assembly must use only PC-relative and register-indirect modes. Load
  address is assigned at fork time.
- **Reentrancy:** one module copy serves all processes; each reaches its
  own data through a6 (linker convention). Data modules are the deliberate
  non-reentrant exception.
- **C string literals** live in the shared read-only TEXT section — except
  `char array[] = "..."` which gets per-process DATA storage and is safely
  mutable.
- The assembler `info` directive places strings in the module's
  information area (version, copyright); C reaches it via `#asm`.

## Universal header (68k) — 48 bytes, offsets 0x00–0x2F (`modhcom` in `module.h`)

| Field | Offset | Size | Value/Purpose | Symbol |
|-------|--------|------|---------------|--------|
| Sync word | 0x00 | 2 | `$4AFC` — an illegal 68000 instruction, so coldstart can scan ROM for it word-by-word at near-zero cost, running parity/CRC checks only on hits | `M$ID` |
| System revision | 0x02 | 2 | Header format revision | `M$SysRev` |
| Module size | 0x04 | 4 | Total bytes, header through CRC | `M$Size` |
| Owner | 0x08 | 4 | Creator group.user ID | `M$Owner` |
| Name offset | 0x0C | 4 | Offset from module start to NUL-terminated name string | `M$Name` |
| Access permissions | 0x10 | 2 | rwx for owner/group/public (low 12 bits, below) | `M$Accs` |
| Module type | 0x12 | 1 | Table below | `M$Type` |
| Language | 0x13 | 1 | Table below | `M$Lang` |
| Attributes | 0x14 | 1 | bit 7 sharable, bit 6 sticky, bit 5 supervisor state | `M$Attr` |
| Revision level | 0x15 | 1 | Drives directory substitution (below) | `M$Revs` |
| Edition | 0x16 | 2 | Human-facing version counter (don't confuse with M$Revs) | `M$Edit` |
| Usage offset | 0x18 | 4 | Offset to usage/comment string | `M$Usage` |
| Symbol table offset | 0x1C | 4 | Offset to symbol table if present | `M$Symbol` |
| Reserved | 0x20 | 14 | — | — |
| Header parity | 0x2E | 2 | Integrity check over the header words | `M$Parity` |

Type-specific fields begin at 0x30. Offsets are from the v2.4 Technical
Reference Manual's header figure; per-field sizes are derived from the
gaps between documented offsets. **`Source`:** every offset in
this universal-header table matches os9exec's own `modhcom` struct
(`Source/OS9exec_core/os9defs/module_from_book.h`), which carries
**compile-time** offset assertions (`offsetof` checks that fail the build
if any field moves) for all 14 fields plus a `sizeof == 0x030` check — so
the layout is *continuously enforced*, not verified once. (os9exec breaks
the `0x20` "reserved" span into `_mident` at `$20` + a 12-byte `_mspare` at
`$22`.) M$Attr at 0x14 is additionally `Live`: real 68k C-runtime startup
code tests bit 5 of offset 0x14 against the module base.

**Independently confirmed against a second Microware manual:** the
*OS-9/68000 Technical Manual*'s own header figure (ch. 1) lists the same
offsets. One OCR trap in that scan, called out so it isn't mistaken for a
conflict: it prints `M$Parity` at `$28`. That is a scan error (8-for-E, the
same misread that turns I$SetStt's `$8E` into `$BE` in the 6809 manuals) —
`M$Parity` is the header's last word at **`$2E`**, confirmed by both the v2.4
Technical Reference (`$2E M$Parity`) and the fixed 48-byte header size. Trust
`0x2E`.

### Type codes (M$Type)

| Code | Symbol | Meaning |
|---|---|---|
| 0 | — | wildcard |
| 1 | Prgm | program |
| 2 | Sbrtn | subroutine module |
| 3 | Multi | multi-module |
| 4 | Data | data module |
| 5 | CSDData | — |
| 6–10 | — | reserved |
| 11 | TrapLib | user trap library |
| 12 | Systm | system component |
| 13 | Flmgr | file manager |
| 14 | Drivr | device driver |
| 15 | Devic | device descriptor |
| 16–255 | — | user-definable |

The kernel validates type against use: forking a non-Prgm module returns
`E_NEMOD`.

### Language codes (M$Lang)

| Code | Symbol | Meaning |
|---|---|---|
| 0 | — | wildcard |
| 1 | Objct | 68000 machine language |
| 2 | ICode | compiled BASIC09 I-code |
| 3 | PCode | Pascal |
| 4 | CCode | C |
| 5 | CblCode | COBOL |
| 6 | FrtnCode | Fortran |
| 7–15 / 16–255 | — | reserved / user-definable |

The language code tells the kernel/shell which runtime, if any, must
interpret the module (this is how typing a packed BASIC09 module's name
launches RunB).

### Attribute byte (M$Attr)

| Bit | Meaning |
|---|---|
| 7 | Sharable/reentrant — clear limits the module to one simultaneous link (one open path, for a descriptor) |
| 6 | Sticky — survives link count 0; removed at count −1 or under memory pressure |
| 5 | Supervisor state — module runs in 68000 supervisor mode (set on all OS components) |

Bits 0–4 undocumented in the surveyed manuals.

### Permissions (M$Accs) and security

Low 12 bits: owner rwx (bits 0–2), group rwx (4–6), public rwx (8–10);
bits 3/7/11 reserved. Read/execute gate load/link/fork; write matters only
with memory-protection hardware. Group 0 (superuser) bypasses permission
checks entirely; everyone else is evaluated against exactly one field —
owner, group, or public, by best identity match. A superuser-owned program
can hand a narrow capability to ordinary callers, covering setuid-style
needs without a separate mechanism. I/O-system modules (file managers,
drivers, descriptors) must be superuser-owned with the supervisor bit set;
a module file owned by superuser must stay superuser-owned or OS-9 refuses
to load it.

### Header parity

XOR of all prior header words, one's-complemented — so folding *every*
header word including M$Parity yields `$FFFF` on an intact header. Checked
on every link; mismatch = `E_BMHP`. Protects the header only (the body may
legitimately change post-load, e.g. breakpoints). Cross-manual notes: some
v2.4-era sources describe a refined scheme that also rotates the
accumulator right by (word mod 16) per word (v2.2 reportedly summed low 16
bits instead); OS-9 Insights states the verification result as `0`, which
is inconsistent with "complement of XOR" — `$FFFF` is treated as
authoritative here. This parity is unrelated to the module CRC.

## 6809 header divergence (do not blend with 68k values)

The 6809 header is a different, shorter layout (9 bytes, sync `$87,$CD`,
16-bit fields) — full byte layout in `6809/syscalls-and-module-format.md`.
Compiler-specific values worth isolating:

- The 6809 C compiler's module type/language byte and attribute/revision
  `$81` (reentrant, rev 1) are compiler-specific values, not general
  constants; the byte is `$11`, not `$04`. **`Manual` + `Live` (6809):**
  the packing is documented, not merely inferred — the *OS-9 System Programmer's Manual* §4.2.1 states "the module
  type is coded into the four most significant bits of byte 6" and lists
  `$10` Prgrm, `$20` Sbrtn, `$40` Data; the language occupies the low nibble.
  `ident` on real modules confirms it directly: the byte is `(type << 4) |
  language`, one byte, so the type nibble is the *high* one — `dir` and `copy` (native 6809 object
  programs) both read `$11`, `basic09`'s own `BFX` reads `$21` (Sbrtn +
  object), and a freshly `PACK`ed BASIC09 procedure reads `$22` (Sbrtn +
  BASIC09 I-code, `At/Rv $81` exactly as above). `$04` would decode as
  type nibble 0 — not a valid module type at all — with language 4, the
  nibble `6809/syscalls-and-module-format.md` marks as the *reserved,
  unimplemented* C I-code. A 6809 C program compiling to native object
  code is therefore `$11`, agreeing with `c/os9-clib-reference.md`'s
  `os9fork()` entry (`lang == 1`). **Scope this honestly:** what was run
  live is the encoding and the native-object-program value; no actual
  6809 C-compiled module was available to `ident`, so `$11` for that
  specific compiler's output is a sound inference from a confirmed
  encoding, not a direct observation.
- `os9fork()`/`chain()` on 6809 want `lang == 1` (6809 machine code).
  Numerically equal to 68k's Objct=1 but a mutually incompatible format —
  never merge the two facts.
- Pointer initializers are fixed up at load time via two tables (data-text
  and data-data reference tables) that startup walks after copying
  initializer data — the 6809 counterpart of 68k M$IData/M$IRefs, solved
  differently.
- The 6809 RMA assembler organizes source as PSECT (code) / VSECT (data,
  optionally direct-page) / CSECT (offset counter); PSECT carries the
  type/lang/attr/stack/entry info the older MOD directive held, consumed
  by the linker rather than OS-9. **Confirmed a Microware-family
  convention beyond RMA, `Live`**: the 68k assembler (`r68`) uses the
  same lowercase `psect` directive with the identical argument shape
  (`psect name,type_lang,attr_rev,edition,stacksize,entrylabel`),
  consumed by `l68` at link time to build the module header.

## Program-module extended header (68k, offset 0x30+)

| Field | Offset | Size | Purpose | Symbol |
|-------|--------|------|---------|--------|
| Execution offset | 0x30 | 4 | Entry point relative to module start | `M$Exec` |
| Trap entry offset | 0x34 | 4 | Default handler for an unhandled TRAP (lazy binding, below) | `M$Excpt` |
| Min data space | 0x38 | 4 | Required data-area size | `M$Mem` |
| Min stack | 0x3C | 4 | Linker's assumed max stack depth; default 3K, linker option overrides. Fork memory = M$Stack + M$Mem + parameter size + caller extra | `M$Stack` |
| Data init offset | 0x40 | 4 | → data-initialization table | `M$IData` |
| Pointer init offset | 0x44 | 4 | → pointer-relocation tables | `M$IRefs` |

All 32-bit fields. **`Source`:** all six offsets match os9exec's
`mod_exec` struct (`Source/OS9exec_core/os9defs/module_from_book.h`) with
compile-time `offsetof` assertions (`_mexec` $030 through `_midref` $044) plus
a `sizeof == 0x048` check — the build fails if any move. Entry point = load
address + M$Exec; the linker takes it from whichever psect was designated root.

- **M$IData table:** entries of (4-byte data-area offset, 4-byte size,
  literal bytes); the kernel copies them into the fresh data area at fork —
  this is how C static initializers work. Linker vsect values land here.
- **M$IRefs tables:** two sub-tables, each (MSW-of-offset word, count
  word, count× LSW offsets, zero terminator). First table marks data slots
  holding pointers into TEXT (fixed up with the module base), second marks
  pointers into DATA (fixed up with the data base). Walked by F$Fork.

## Module CRC

24-bit trailer over everything from header start up to (not including) the
CRC field; accumulator initialized all-ones, result one's-complemented for
storage. Sources describe the init as `$FFFFFF` (3-byte view) or
`$FFFFFFFF` (`F$CRC`'s d1.l) — not a conflict, only the low 24 bits
participate. The linker pads the body with one zero byte before the CRC
when the length would be odd (68000 even-alignment). A valid module's full
accumulation *including* the CRC bytes lands on `$800FE3`.

- Kernel validates via F$CRC before directory entry — mismatch means not
  loaded (`E_BMCRC`; `fixmod` repairs a hand-patched module). Checked once
  at load/bootstrap, never re-verified afterward.
- Time-critical code should pre-load modules rather than eat a CRC-checked
  load mid-operation.
- The C library `crc()` accumulates into a caller-supplied 3-byte array
  (start at `$FFFFFF`; complement before storing as a module's CRC field).

## Module directory mechanics

Beyond the lifecycle basics (`os9-mental-model.md`). C wrappers:
`modlink()` = F$Link, `modload()` = F$Load, `munlink()` = F$UnLink.

- **Type check on fork/chain:** a resident name whose type/language doesn't
  match the request returns `E_NEMOD` — no silent substitution; only if no
  resident match is the name tried as a file path.
- **Revision substitution:** loading a module whose name/type/language
  match a resident one compares M$Revs — higher revision replaces the
  directory entry immediately; running processes keep the old bytes.
- **Module groups:** all modules loaded from one file share one contiguous
  allocation and free only when the group's combined link count hits zero.
- **Module files:** a file may hold any number of concatenated modules;
  to RBF it's an ordinary file.
- Link counts can be adjusted artificially (`link`/`unlink` utilities) —
  don't treat them as exact.
- **a6 bias:** the data-area base register is biased by `$8000` so indexed
  addressing spans a full 64K; the linker compensates automatically. This
  is why disassembled code shows data references offset by `$8000`.

## Trap libraries & subroutine modules

A **TrapLib** (type 11) exposes subroutines reached via `TRAP #1`–`#15` +
function word instead of linked addresses. Three entry points: execution,
initialization (run at F$TLink), termination (reserved, unimplemented in
this era). Installation (`F$TLink`) links the module, allocates *private
per-client static storage*, runs init; max 15 trap links per process.
**Lazy binding:** a `tcall` before F$TLink jumps through the module's
M$Excpt entry, which installs the handler and re-executes the call (zero
M$Excpt aborts instead).

**Subroutine modules** (type 2) by contrast have no static storage —
routines are reached through an index table of offsets, state passed by
parameter; they run in the *caller's* CPU state, while a trap module runs
in the state its own attributes declare. No limit on subroutine links.

**The Math module** is the canonical TrapLib (trap 15): floating point,
extended integer ops, conversions, transcendentals, shared by every
language. `Math881.l` (68881/882 hardware FP) substitutes for `Math.l`
under the same registered name without recompiling clients. Internally
promotes 32-bit floats to 64-bit doubles (no speed gain from `float`); no
denormals or negative zero. Compilers link and call it automatically;
assembly reaches it via F$TLink + trap. Pre-`load`ing it speeds first
use; baking it into `OS9Boot` is generally not recommended.

## Data modules

Named shared memory (`F$DatMod`; C: `_os_datmod()`/`_os_mkmodule()`):
creator sets size and
attributes, data area arrives zeroed with a valid CRC; later processes
link by name. Allowed to be non-reentrant/mutable — that's the point. No
kernel synchronization; pair with events/signals (`common/ipc.md`).
**Gotcha:** an in-place-modified data module has a stale CRC — call
`F$SetCRC` (C: `_setcrc()`) before saving it to disk (or `fixmod` the
file) or it won't reload. `dump` can inspect one directly.

## Boot-time module discovery

Coldstart scans ROM (and the boot file) word-by-word for `$4AFC`; each hit
gets a parity check, size read, and CRC check, and survivors enter the
module directory — this is how ROMed modules (including user ones)
auto-register at boot. Then the kernel links the **INIT module** (a
configuration table: initial table sizes, system device names, kernel
customization modules whose init functions are called at startup — new
system calls can be added without rebuilding the kernel), initializes its
tables, and forks the first program. The **Clock module** is the
platform-specific real-time-clock handler.

## Linker & object-format facts (68k `l68`, 6809 `c.link`)

- **`l68` error taxonomy (`Live`):** `file 'x.r' is not a
  relocatable module` = the object didn't parse (corrupt / not a ROF);
  `no root psect found` = parsed fine, just no entry point. So running
  `l68` on a single object is a cheap integrity check — healthy objects
  say "no root psect found." When exactly one input out of many is
  rejected, rebuild that object before theorizing about linker limits.
- **ROF header (`Live`):** 0x00 sync longword `$DEADFACE`;
  0x0C–0x11 creation date (year−1900, month, day, hour, minute, second);
  0x1C code size; 0x38 NUL-terminated module name. Decoding two objects'
  timestamps settles "were these built by different compiler
  generations?" instantly.
- **RMA library merge order (6809):** `c.link` resolves externals
  first-found in merge order, so if library proc A calls library proc B,
  B's ROF must be merged *after* A's — intra-library references must all
  point forward. A property of this single-pass linker, not necessarily
  of any 68k linker.

## Inspection tools

`mdir` (resident modules; `-e` adds address/size/owner/type/links),
`ident` (header decode + CRC check; also reads S-record files),
`binex`/`exbin` (module ↔ S-record, validates as a side effect), `dump`
(raw bytes), `fixmod` (recompute CRC/parity). Reach for these before
deeper debugging when a module won't load.

---
Sources: The OS-9 Guru; a 1985 independent OS-9/68000 technical manual;
OS-9 v2.4 Technical Reference Manual; The OS-9 Primer; OS-9 Insights; OS-9
C Compiler manual; Using Professional OS-9 v2.4; Technical I/O Manual
v2.4; Disk File Organization manual. The `l68` error taxonomy and ROF
header layout are `Live` findings on os9exec's toolchain; M$Attr offset 0x14
is `Live` against a real compiled 68k program.
