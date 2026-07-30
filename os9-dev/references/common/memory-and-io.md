# OS-9 Memory Model and I/O Architecture

Memory allocation/layout, then the mechanics of the file-manager/driver/
descriptor architecture (concept-level overview: `os9-mental-model.md`).
Disk-block-level RBF detail (identification sector, file-descriptor
fields, directory format, record locking) is in the sibling
`os9-systems-dev` skill's `file-managers.md`.

---

## Memory model

### Allocation units and block sizing

OS-9 allocates in multiples of a **16-byte minimum allocation unit** — the smallest independently-freeable chunk tracked by free-list bookkeeping. This is a logical granularity; actual physical allocation depends on memory protection:

| System type | Minimum allocatable block |
|---|---|
| MMU-equipped (memory protection) | Matches the MMU page size (e.g. 4K) — kernel allocates whole physical pages and subdivides them internally |
| No MMU / no inter-task protection | 256 bytes |

The kernel manages free fragments *within* these larger blocks so a small
request doesn't waste an entire page/block.

### First-fit and the buddy allocator

OS-9 supports two allocation strategies:

- **First-fit** — grabs the first free block large enough for the request. Faster but more fragmentation-prone.
- **Buddy-system allocator** — power-of-two-sized lists with subdivision on exact-size misses. Achieves bounded latency for real-time code, but requires MMU-based protection's `D_MinBlk` to exactly match the MMU page size to maintain security.

### Colored memory

On systems with hardware memory-access limitations, colored memory partitions
address space into distinct regions (non-volatile RAM, DMA-accessible regions, etc.).
Data modules can be allocated from a specific color when needed.

### Fragmentation

Without MMU address translation, separate physical memory areas can't be
combined logically. OS-9's allocation strategy avoids fragmentation rather than
cleaning it up — a necessary choice on systems without virtual memory.

### MMU and DMA

An MMU is **optional** — not required for OS-9 operation. Register-indirect addressing provides process isolation even without one. Where present, MMU adds memory protection (via System Security Module, `ssm`). On MMU systems, DMA transfers from user buffers require address translation, which OS-9 provides.

Without MMU, all user tasks share one address space with no isolation. Recommendation: keep memory in contiguous reserved blocks with expansion room.

### Process memory at fork time

Each process gets three regions, sized as `minimum data space + stack size + parameter string length`:

| Region | Purpose | Notes |
|---|---|---|
| Static storage | Program's initialized/uninitialized variables | Sized from linker metadata; kernel initializes from constant tables |
| Stack | Locals, return addresses, call frames | Grows downward; minimum declared in the module header |
| Parameter string | Arguments from the parent | Copied to the top of allocated memory |

Programs can request additional static storage via `F$Fork`. All data access is register-indirect from a base pointer (A6 for ordinary program modules), enabling ROM placement and concurrent multi-process execution against one code copy. Device drivers and file managers use kernel-supplied register convention (A1/A2/A4/A5/A6 each with specific pointer) — see `68k/os9-68k-assembly.md`.

### Data modules (shared memory, mechanism level)

A data module is a dynamically-created region of system memory obtained via
`F$DatMod`: the kernel returns its address and a link count, and — since the
address isn't known at compile time — a process must reach it by pointer
(C) or register-indirect addressing (assembly), unlinking later with
`F$UnLink`. This is the underlying allocation mechanism for OS-9's shared
memory; for the usage patterns and gotchas of using data modules for actual
inter-process communication, see `ipc.md`.

### `edata` / `end`

Two linker-defined symbols mark the end of a program's own static data:
`edata` is one byte past the end of initialized data, `end` is one byte past
the end of uninitialized data. Neither is a variable — a C program takes
their address (`&edata`, `&end`) to get the value; in assembler they're
plain labels. Useful for a program that wants to know where its own static
region ends before doing its own `sbrk()`/`malloc()`-style allocation on top
of it.

### `malloc()` and the lower-level system-request calls

`malloc()` doesn't turn every request into a fresh call to the kernel — it
keeps its own pool of memory already obtained from the system but not yet
handed to the caller, and only goes back to the kernel when that pool runs
dry. Each trip to the kernel requests in units of a configurable minimum
block size (4K by default); a larger minimum trades some wasted space for
fewer, less-fragmenting system calls.

A hard constraint sits underneath all of this: **a process may hold at most
32 memory areas at once** — and that ceiling counts the process's initial
static storage and stack, not just what it asks for later, so fewer than 32
are actually available. Both `malloc()`'s own system requests and any direct
`_srqmem()` calls come out of the remainder. Programs with large
or fragmented memory needs should request bigger chunks up front rather than
many small ones, precisely because of this ceiling.

For code that wants to bypass `malloc()`'s bookkeeping entirely, `_srqmem()`/
`_srtmem()` request and release memory straight from the kernel (`F$SRqMem`)
with less overhead. Two details worth knowing: passing `0xFFFFFFFF` as the
size to `_srqmem()` is a special case that returns the single largest
contiguous free block in the system (with the actual size delivered via the
global `_srqslz`), and any pointer `_srqmem()` returns is guaranteed to fall
on an even byte boundary — don't lose track of the original pointer value if
you intend to hand it back via `_srtmem()` later. On failure, `_srqmem()`
returns `-1` with the reason in `errno`, the same convention as other C
library calls.

The `_lmalloc()`/`_lcalloc()`/`_lrealloc()` family trades bookkeeping for
size: they skip storing the allocation's size and a validity check value,
saving 8 bytes per allocation compared to `malloc()`/`calloc()`/`realloc()` —
useful when a program makes many small allocations and every byte of
overhead multiplies.

---

## File-manager / device-driver architecture

### The layering (mechanics view)

Kernel → file manager (class logic) → driver (one controller) — configured
by device descriptors; concept-level picture in `os9-mental-model.md`.
Mechanical details worth having here: non-executable modules (descriptors)
are referenced directly as tables, while drivers and file managers are
entered through jump tables; a new physical device usually needs only a new
driver + descriptor when an existing file-manager class fits. **I$** calls
route through file managers/drivers; **F$** calls execute in the kernel,
splitting further into user-state and system-state (privileged-only).

### Device descriptors

A device descriptor is a small data module holding hardware config and
module names. Key fields:

| Field | Offset | Contents |
|---|---|---|
| `M$Port` | $30 | Hardware interface port address, pre-loaded into the driver's `V_PORT` static-storage slot before INIT runs |
| `M$Mode` | $37 | Access-mode bits (below) |
| `M$FMgr` | $38 | Offset to the file manager's name string |
| `M$PDev` | $3A | Offset to the device driver's name string |
| `M$DevCon` | $3C | Pointer to an *optional* driver-specific config table (OEM constants); **never** copied into the path descriptor — available to the driver only during INIT/TERM |
| `M$Opt` | $46 | Byte count spanning the standard device-configuration table (`M$DTyp` onward); extends to 128 bytes maximum by design, though some file managers impose stricter limits |

(`M$Port`/`M$FMgr`/`M$PDev` `Source` (os9exec's own device-descriptor
header); see `os9-systems-dev` skill's `device-drivers.md` for the driver-authoring
angle on these same fields.)

`M$Mode` bit layout:

| Bit | Meaning |
|---|---|
| 0 | Read access |
| 1 | Write access |
| 2 | Executable access |
| 6 | Single-user (non-sharable) |
| 7 | Directory-file access |

The kernel validates a caller's requested open mode against `M$Mode`.

Unlike `M$DevCon`, the table described by `M$Opt` **is** copied — every time
a path opens, it's copied into the path descriptor's 128-byte option area
(`PD_OPT`, offset $80). Path options control per-path I/O behavior
(buffering, echo, parity, flow control, backspace/delete key codes, etc.); a
user can inspect the whole area via `I$GetStt(SS_Opt)`, and modify some of
it via `I$SetStt` — the file manager protects certain values from
inappropriate changes.

A single physical device may have **multiple descriptors** with different
names/parameters — e.g. one descriptor for terminal mode (`/T1`) and another
for printer mode (`/P1`) on the same serial/parallel port. These are
"synonymous devices" in the kernel's matching logic below.

### Kernel I/O tables and `I$Attach`/`I$Detach`

The kernel keeps two tables:

- **Device table** — one entry per attached device (created on first
  `I$Attach`): file manager/driver names, the driver's static storage
  pointer, a use count.
- **Path table** — one entry per open path (created on `I$Open`, destroyed
  on `I$Close`).

`I$Attach` matching logic when a device is opened:

| Match | Result |
|---|---|
| Port, manager, driver, *and* descriptor all match an existing entry | Increment use count |
| Port/manager/driver match but descriptor differs | Create a new "synonymous device" entry |
| Nothing matches | Allocate driver storage, set `V_PORT`, call driver's INIT |

Should INIT fail, the kernel rolls back symmetrically: it calls TERM, frees
whatever it had allocated, and passes the error back — no device table
entry gets created. `I$Detach` decrements the use count; at
zero, the kernel checks whether another device shares the same static
storage, and if not, calls TERM, deallocates storage, and removes the entry.

### Path descriptors

A path descriptor has three sections:

1. A universal 42-byte section (`PD_PD` through `PD_SysGlob`, offsets
   $00-$29 — includes `PD_LProc`, `PD_ErrNo`, and `PD_SysGlob`) common to
   every path descriptor. (The Technical I/O Manual states this section's
   size explicitly as 42 bytes.)
2. A file-manager-specific section (`PD_FST`) for that manager's file
   pointers/state.
3. The 128-byte option area (`PD_OPT`), initialized from the device
   descriptor's `M$Opt` table (above) and alterable via GetStat/SetStat.

`I$Open`/`I$Create` allocate a new path descriptor and path-table entry with
share counter `PD_COUNT` (offset $1A per the manuals) set to 1. `I$Dup`
skips the file manager and driver entirely — it just increments `PD_COUNT`
on the *existing* descriptor, letting multiple processes share one
open-file context cheaply. `I$Close` decrements `PD_COUNT`; only at 0 is the
descriptor actually deallocated and removed from the path table.
os9exec's own path-descriptor header defines a second field, `PD_CNT`, at
offset `$03`. These are **two genuine fields at two offsets, not a
contradiction** — the manual lists both and marks `$03` obsolete. What cannot
be observed is either offset in action: os9exec implements `I$Dup` (`Live`
(os9exec)) but shares paths through host-native bookkeeping and never touches
`PD_CNT`, which is dead and unreferenced in its source, so no guest-visible
share counter exists to watch. Full note: `os9-systems-dev` skill's
`file-managers.md`.

### Multi-port and multi-class drivers

- **Multi-port**: a driver sharing one static storage area across several
  ports on the same physical device, distinguished via the device-table
  entry or `V_PORT`. Reduces memory overhead — one copy of driver code, with
  per-port state kept in a static extension.
- **Multi-class**: a driver associated with multiple device descriptors,
  each pointing to a *different* file manager class (e.g. block mode and
  character mode on the same intelligent controller).

### Device static storage

The kernel allocates one static storage area per device driver, shared by
the file manager and driver:

| Field | Purpose |
|---|---|
| `V_PORT` | Hardware base address (copied from descriptor's `M$Port`) |
| `V_BUSY` | PID currently using the device (0 = idle) |
| `V_WAKE` | PID to wake when I/O completes |
| `V_PATHS` | Linked list of open path descriptors |
| Drive tables | Per-drive state (current track, interleave, error counts, etc.) |

Example use: RBF caches sector 0 in driver static storage to avoid
re-reading it on every access.

### File manager classes: RBF and SCF

- **RBF** (Random Block File Manager) — the file manager for block-oriented
  random-access devices (floppy/hard disk): directory structure, sector/
  segment allocation, block I/O. Supports disk caching. (Disk-block-level
  structure — identification sector, file descriptor layout, record
  locking — is covered in the filesystem reference, not here.)
- **SCF** (Sequential Character File Manager) — the file manager for
  character-at-a-time devices (terminals, character printers):
  line editing, special-character handling, parity stripping, flow control.
  - Line buffer: **512 bytes max** including the trailing CR, one buffer per
    open path.
  - Editing keys are path-descriptor options, remappable via `tmode`/`xmode`
    (full key table: `os9-tools-and-shell.md`); setting a key code to zero
    disables that feature.

### I$ service requests

| Call | Behavior |
|---|---|
| `I$Open` | Allocates buffers, initializes path descriptor vars, parses pathname; multi-file devices search their directory |
| `I$Create` | Same as `I$Open`; on multi-file devices creates a new file, otherwise synonymous with `I$Open` |
| `I$Delete` | Searches for the file, removes it from the directory, returns its space to the free pool (multi-file managers only) |
| `I$Read` | Returns the requested byte count into the caller's buffer; EOF error if no more data; generally no editing |
| `I$ReadLn` | Like `I$Read` but stops at the first CR (end-of-record) and applies input editing |
| `I$Write` | Writes data (generally unedited); writing past EOF expands the file. On fixed-record devices (e.g. RBF) may need to pre-read a sector before a partial-sector write |
| `I$WritLn` | Writes up to and including the first CR, with output editing (e.g. SCF appends LF after CR) |
| `I$Seek` | Random-access devices only; logical repositioning, no physical effect, no error going past EOF; no-op elsewhere |
| `I$GetStt` / `I$SetStt` | Wildcard status get/set; file manager handles known codes, passes unknown codes to the driver |
| `I$MakDir` | Creates a directory (multi-file devices); unsupported managers return carry-set + unknown-service error |

### I/O call flow

**Open:** application calls `I$Open` → kernel's `I$Attach` links descriptor/
manager/driver, allocates device static storage on first open and calls the
driver's INIT → kernel creates the path descriptor from the device
descriptor's options section → the file manager's OPEN routine searches the
directory (RBF) or sets up the line buffer (SCF).

**Read/Write:** file manager validates mode/position/locks → translates
logical position to sector/offset → calls the driver's READ/WRITE routine
with an LSN and buffer address → driver translates LSN to a physical
address and issues the hardware I/O → driver returns bytes transferred or
an error.

### Device naming

| Name pattern | Device |
|---|---|
| `/d0`, `/d1` | Floppies |
| `/h0`, `/h0fmt` | Hard disk (with/without format protect) |
| `/mt0` | Tape |
| `/nil` | Null device |
| `/p`, `/p1`, `/p2` | Parallel/serial printers |
| `/r0` | RAM disk |
| `/term`, `/t1`, `/t2` | Terminals |

All device names begin with `/`; a device name is also its device
descriptor module's name. `/dd` (default device) is a special alias for the
primary storage device (hard disk or RAM disk) — only one `/dd` descriptor
is loaded at a time, and programs use it for config/data files without
caring what the actual physical device is. Changing what `/dd` points to
requires a new boot file/ROM or loading a different-revision descriptor.

---

## 6809-specific: direct page and stack facts

These do not apply to 68k and should not be blended with the general
material above — they're specific to the 6809's hardware direct-page
addressing mode and this compiler's runtime.

- **`direct` storage class** — this C compiler adds `direct`, `extern
  direct`, and `static direct` on top of K&R's storage classes, placing a
  variable in the 6809's 256-byte direct page (addressable with fast 2-byte
  instructions via the CPU's direct-page register). Can't be used for
  function arguments; uninitialized `direct` variables default to zero like
  other globals/statics. The manual itself warns this is unique to this
  compiler and non-portable even across other 6809 toolchains.
- **255-byte usable limit** — total `direct`-class storage is capped at 255
  bytes (the linker itself consumes 1 of the page's 256 bytes). Exceeding
  this is a linker error; the fix is moving some variables out of `direct`.
- **1-byte minimum reservation** — even with zero `direct` variables
  declared, the linker still reserves at least 1 byte of direct-page space.
  This is deliberate: it guarantees a pointer to a direct-page variable can
  never be NULL (0).
- **64-byte stack overhead per call** — on each C function entry, a
  system-interface routine reserves that function's own stack needs plus a
  fixed **64 bytes** for user-written assembly routines, the system
  interface, and arithmetic-support routines. This 64-byte figure is
  specific to this 6809 runtime and not confirmed for a 68k runtime (which
  would likely need a larger reserve, given wider registers).
- **Stack overflow detection** — the runtime tracks the lowest stack address
  granted so far; if a new function's stack request would push that
  watermark down into the data area, the program halts with `**** STACK
  OVERFLOW ****` on stderr instead of continuing. Disable entirely with the
  `-S` compiler flag once stack usage is verified safe, for time-critical
  code.
- **4K default runtime memory pool** — unless `-M=` overrides it, the
  linker's default runtime pool is a program's variables/strings size plus
  a flat 4K (parameter area + stack + stdlib file buffers). Requests for
  less than 256 bytes via `-M=` are
  ignored. Both the 4K default and the 256-byte floor are this specific
  compiler/linker's defaults, not confirmed for a 68k linker.
- **POKE/PEEK (BASIC)** — direct memory read/write from BASIC09, typically
  used only for OS-9 system globals or hardware access; dangerous to system
  stability if misused. (Not 6809-exclusive in principle, but only
  documented for the BASIC09 environment this compiler targets.)

---

Sources: The OS-9 Guru; OS-9 Insights; The OS-9 Primer; OS-9 v2.4 Technical
Reference Manual; Technical I/O Manual v2.4; OS-9 C Compiler manual; Using
Professional OS-9 v2.4; `malloc`/`_srqmem`/`_lmalloc` details from
Microware Training & Education seminar manuals.
