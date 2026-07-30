# OS-9 Device Drivers

Baseline `Manual`, cross-referenced across multiple manuals. The Device
Descriptor field table is verified against the OS-9 Technical I/O Manual (§1,
device-descriptor module figure), which lists every field at exactly these
offsets — `M$Port` $30, `M$Vector` $34, `M$IRQLvl` $35, `M$Prior` $36,
`M$Mode` $37, `M$FMgr` $38, `M$PDev` $3A, `M$DevCon` $3C, `M$Opt` $46
(initialization-table size), `M$DTyp` $48 (device type, first field of the
init table) — and additionally matches os9exec's `mod_dev` struct, which
carries a compile-time `offsetof` assertion per field.

**The entry-point register conventions below are untestable on os9exec**, not
merely untested: its `I$Attach` never allocates driver storage or calls
`Init`, device I/O dispatch uses a fixed internal table keyed by hardcoded
path-prefix matching rather than executing an installed module's code, and
`iniz` has no emulator-side implementation. A correctly-assembled, CRC-valid
`Drivr` module installs and is never invoked at any entry point. The
toolchain and module-format content here (byte layout, `psect` authoring)
*can* be built and verified byte-correct there; the register conventions
cannot, so treat them as `Manual` short of real hardware.

A device driver is an OS-9 module (type `Drivr`, code `$0E`) owned by the
super-user, with the system-state and re-entrant attribute bits set. Its
`M$Exec` field points to a 7-entry jump table instead of a single entry
point; `M$Mem` gives its static storage size.

## Entry Point Table

```
dc.w  INIT      (0)  Initialize device
dc.w  READ      (1)  Read sector/character/block
dc.w  WRITE     (2)  Write sector/character/block
dc.w  GETSTAT   (3)  Get device status
dc.w  SETSTAT   (4)  Set device status
dc.w  TERM      (5)  Terminate/de-initialize device
dc.w  TRAP      (6)  Error handler (currently unused — set to 0)
```

## Universal Rules

- **Static storage is zeroed by the kernel before `INIT` runs**, except
  `V_PORT` (the device's hardware base address, offset `$00`), which is
  pre-loaded from the device descriptor's `M$Port` field. There is no
  initialized-data table for a driver the way there is for an ordinary C
  program.
- **`TERM` is called even if `INIT` failed partway through** — validate
  static storage state before using it in `TERM`; don't assume `INIT` ran
  to completion.
- `TERM` must: wait for pending I/O, disable interrupts, remove itself from
  the IRQ polling table (`F$IRQ`), and return any *dynamically* allocated
  buffers — the kernel releases the static storage itself, don't touch it.
- **IRQ service routines may only destroy d0, d1, a0, a2, a3, a6** — every
  other register must be preserved. Return carry clear if the interrupt was
  serviced, carry set (and exit as fast as possible) if it wasn't yours.
- Two patterns for waking a sleeping driver mainline from an IRQ routine in
  OS-9: **signal-based** (copy `V_BUSY`→`V_WAKE` before sleeping; IRQ routine
  clears `V_WAKE` and sends `S$Wake`) or **event-based** (mainline waits on an
  event; IRQ routine signals it). Signal-based is more common for simple drivers.

## Driver Lifecycle Under the Kernel's I$Attach/I$Detach

Application code never calls `INIT` or `TERM` directly — the kernel's
device-table management does, following specific rules based on which
device opens are happening and whether the driver is already attached.

When a path opens a device name the kernel has never seen before (no
matching device-table entry), the kernel allocates fresh static storage for
the driver, initializes `V_PORT` from the device descriptor's hardware
address field, and invokes `INIT`. If `INIT` succeeds, a device-table entry
is created and the caller gets a path. If `INIT` fails partway through, the
kernel immediately calls `TERM` (even though `INIT` didn't finish), then
deallocates the storage and returns the error — **no device-table entry is
created**. This is why `TERM` must validate static storage state before
using it; it may be partially initialized or zeroed-but-not-configured.

On subsequent opens, the kernel searches for an existing device-table entry
matching port, file manager, and driver:

- **Exact match** (descriptor also matches): the entry's use count increments
  and the path links to it. `INIT` is not called — the driver is already
  active.
- **Match on port/manager/driver, but different descriptor**: this creates a
  **synonymous device** — a second device-table entry sharing the existing
  driver's static storage and hardware, but with different initialization
  parameters. One example: `/T1` configured for terminal mode and `/P1`
  configured for printer mode both use the same serial port, same driver,
  same storage, but different descriptors. Both get entries in the device
  table. `INIT` is not called (the driver is already initialized).
- **No match on port/manager/driver**: the new device is entirely unknown,
  so proceed as with the first open above.

When `I$Detach` is called to close a path, the kernel decrements that
device's use count. Only when the count reaches zero does the kernel search
for other device-table entries using the same driver static storage. If none
exist, `TERM` is called and the storage is freed. If other entries share it,
`TERM` does not run — the driver stays active. This means **`TERM` only
fires on the truly final close of a device**, not on every `I$Detach`. A
driver author must not assume `TERM` called for every close attempt.

## Device Descriptor Fields a Driver Author Needs

The device descriptor is the non-executable module the kernel and file
manager consult when attaching a device; several of its fields are read
directly by driver code or govern what the driver sees in static storage.

| Field | Offset | Purpose |
|---|---|---|
| `M$Port` | `$30` | Hardware interface port address — pre-loaded into the driver's `V_PORT` static-storage slot before `INIT` runs (see Universal Rules above). |
| `M$Mode` | `$37` | Access-mode bits: bit 0 read, bit 1 write, bit 2 execute, bit 6 single-user (non-sharable), bit 7 directory-file access. The kernel checks a caller's requested open mode against this before ever reaching the driver. |
| `M$FMgr` | `$38` | Offset to the file manager's name string — what the descriptor selects for the filesystem-protocol layer. |
| `M$PDev` | `$3A` | Offset to the device driver's name string — what the descriptor selects for the hardware layer. |
| `M$DevCon` | `$3C` | Pointer to an optional driver-specific configuration table (OEM constants, hardware parameters). **Available to the driver only during `INIT`/`TERM`** — unlike the standard init table, it is never copied into path descriptors, so any other driver routine needing it must search the device table for the descriptor itself. |
| `M$Opt` | `$46` | Size of the descriptor's standard initialization table (theoretical max 128 bytes, though individual file managers may cap it lower). This table is what the kernel copies into every newly-opened path's 128-byte option area — see `file-managers.md` for the path-descriptor side of this copy. |

A single physical device can have **multiple descriptors** with different
names/parameters (the synonymous-device case above) — a driver should never
assume one descriptor per physical port.

## Multi-Port and Multi-Class Drivers

- **Multi-port**: one driver instance/static-storage block serves several
  independent ports of the same device class (e.g. a multi-line serial
  card). Ports are distinguished via the device-table entry or the
  `V_PORT` field rather than by separate driver copies — code is shared,
  per-port state lives in a static-storage extension the driver defines.
- **Multi-class**: one driver associates with several device descriptors
  that each point to a *different file manager* (e.g. the same intelligent
  controller used in both block and character mode). The driver code itself
  doesn't need to know which file manager is calling it — only what its
  own READ/WRITE/GETSTAT/SETSTAT entries mean for that mode.

## RBF (Block Device) Driver Specifics

**READ input:** `d0.l`=sector count, `d2.l`=starting LSN, `(a1)`=path
descriptor, `(a2)`=static storage, `(a4)`=process descriptor, `(a5)`=caller's
register stack, `(a6)`=system globals. **WRITE** is symmetric, transferring
from `PD_BUF`, using the same input registers.

**Known gap:** READ/WRITE are the only entry points with a documented
register convention anywhere in this skill. INIT, TERM, GETSTAT, and
SETSTAT have no register inputs specified here or in `file-managers.md` —
a skeleton for those entry points can only be written by unconfirmed
analogy to READ/WRITE's `(a1)/(a4)/(a5)/(a6)` pattern, not from
attested content.

Key behaviors a real RBF driver needs to get right:
- **Sector-0 buffering** (fixed media only — removable media must detect
  media changes): cache LSN 0 via `V_ScZero`/`V_ZeroRd` to skip physical I/O
  on repeat reads; invalidate on any write to LSN 0.
- **Variable sector size**: respond to `GetStat SS_VarSect` with no-error
  if the driver supports sizes other than 256 bytes (via `PD_SSize`); return
  `E$UnkSvc` if fixed at 256 — RBF then assumes 256-byte logical sectors, and
  the driver is responsible for translating/deblocking if physical sector size differs.
- **`SS_DSize`** (autosize devices): return media size in logical sectors.
- **`SS_Reset`**/**`SS_WTrk`** support the format utility (seek-to-track-0,
  write a physical track) — `SS_WTrk` must check the format-protect bit in
  `PD_Cntl` and return `E$Format` if set.
- **`SS_SQD`** (park heads, hard disk only) — validate the target cylinder
  is outside the media area before parking; don't mark the drive
  "initialized" afterward, so the next real access re-inits correctly.

### Drive Table (21 bytes, `DD_SIZ`, copied from sector 0 on init)

The first 21 bytes (`$00`-`$14`) are a driver-local copy of the leading
fields of the disk's Identification Sector — `DD_TOT`, `DD_TKS`, `DD_MAP`,
`DD_BIT`, `DD_DIR`, `DD_ATT`, `DD_FMT` at the same offsets documented in
`file-managers.md`'s Identification Sector table (not restated here); the
21-byte cutoff lands exactly at `DD_BT` (bootstrap fields), which a driver
doesn't need in its own static storage.

Driver/file-manager-maintained extension fields follow at `$16`+ (`V_TRAK`
current track, `V_ScZero`/`V_ZeroRd` sector-0 cache, `V_SoftEr`/`V_HardEr`
error counters, etc.) — see the Technical I/O Manual for the complete table
if hand-authoring one of these. (For the full disk-structure layout these
fields are copied *from* — identification sector, allocation map, file
descriptor sector, directory format — see `file-managers.md`.)

### Driver Static Storage (RBF)

| Offset | Name | Maintained by | Purpose |
|---|---|---|---|
| $00 | `V_PORT` | kernel | Device hardware base address |
| $04 | `V_LPRC` | file manager | Last process ID |
| $06 | `V_BUSY` | file manager | Process ID currently blocked on I/O |
| $08 | `V_WAKE` | driver | Process ID to wake on completion |
| $0A | `V_PATHS` | kernel | Open-paths list |
| $2E | `V_NDRV` | driver | Number of drives |
| $36 | `DRVBEG` | driver/FM | Where per-drive tables begin |

Link order matters: `drvs_X.l` (X = drive count) must be linked before your
own object files — it allocates the I/O globals and X drive tables in the
layout the driver expects.

## SCF (Character Device) Driver Specifics

Same entry points, different concerns — line discipline instead of block
transfer.

**Known gap:** unlike RBF's complete Driver Static Storage offset table
above, SCF's fields below (`V_PAUS`, `V_XON`, `V_BUSY`, `V_WAKE`) are named
in prose only — no offsets, sizes, or total static-storage size are
documented anywhere in this skill. A byte-accurate SCF driver static
storage layout can't be written from this content alone.

**Polled READ**: check hardware for data, strip parity if configured, check
for the three special input characters (pause → sets `V_PAUS` on the paired
echo device; interrupt → sends `S$Intrp` to the last process; abort/quit →
sends `S$Quit`), return the character.

**Interrupt-driven READ**: if the input FIFO is empty, copy `V_BUSY`→`V_WAKE`
and sleep indefinitely; on wake, check whether it was a deadly signal or the
process was condemned (return that instead of a character if so); otherwise
pull from the FIFO. If software flow control is in effect and the FIFO has
drained below its low-water mark, send `V_XON` to the remote end.

A driver must **not** disable the input interrupt — it's expected to stay
enabled for the life of the attachment.

### Signal-on-data-ready (`SS_SSig`) — what a terminal monitor arms

A process that wants to be told when input arrives, without holding a blocking
read, arms **`I$SetStt` `SS_SSig` (`$1A`)** with the signal number to send.
`SS_SEvent` (`$3E`) is the event-based counterpart. This is the mechanism a
login monitor uses: it arms the signal, sleeps, and **never reads the device
itself** — so if the path never delivers, the terminal is simply dead to
keypresses with nothing reporting an error.

Four properties a driver or emulator has to honour (`Source`, os9exec:
`filestuff.c`'s `SS_SSig` case and `utilstuff.c`'s input path):

- **The signal number arrives in `d2`**, and is recorded per *path*, together
  with the arming process's PID.
- **Arming checks readiness immediately.** If data is already waiting, the
  signal fires on the `SetStt` call itself rather than waiting for the next
  byte — "tell me when there is input, including right now".
- **It is one-shot.** The pending signal is cleared as it fires; a monitor
  re-arms after each wake.
- **Deliver to every path bound to that terminal, not just the device's main
  one.** The arming process opens the device itself, so its path is a
  *different* path from the one the terminal normally reads through. Matching
  only the main path leaves the armed process asleep forever.

**NitrOS-9's own `tsmon` does not use this** (`Source`, `level1/cmds/tsmon.asm`):
it installs an `F$Icpt`, closes stdin/stdout/stderr and `I$Dup`s the opened
device onto them, then blocks on an ordinary `I$ReadLn` before forking the
login program. So the armed-signal shape above is one valid implementation of a
terminal monitor, not the only one — don't infer from a monitor's behaviour
which mechanism it used.

## SBF (Streaming Block, e.g. Tape) Driver Specifics

Adds buffered vs. unbuffered transfer modes and tape-specific `SetStat`
codes (`SS_Feed`, `SS_Reset`, `SS_Reten`, `SS_RFM`/`SS_WFM` file-mark
handling, `SS_Skip`). Distinguishes "early EOT" (soft warning, keep
writing) from physical end-of-tape. Async writes return before data
physically lands, useful for streaming throughput but only where
write-completion confirmation can be deferred.

## Interrupt Vector Registration and Dispatch

`F$IRQ` registers a driver's IRQ routine, either in the auto-vectored
polling table (levels 1-7, vectors 25-31, shared/polled among every driver
registered at that level) or a specific vectored-interrupt slot (vectors
64-255, 192 available, may also be shared by multiple devices).

**Register conventions on IRQ entry** (distinct from the normal
READ/WRITE/GETSTAT/SETSTAT dispatch registers above): `(a2)` = driver static
storage, `(a3)` = device port address, `(a6)` = system global storage — a2
and a3 are exactly the values supplied when the handler was installed via
`F$IRQ`, not necessarily the same convention as ordinary entry points. The
routine reports whether it handled the interrupt via the carry flag (clear
= serviced, set = not mine, kernel keeps polling the next handler in the
chain) and may destroy only d0, d1, a0, a2, a3, a6.

- **Level 7 (vector 31) is non-maskable** and can interrupt the kernel at
  dangerous times, including mid-way through a critical kernel section.
  Don't configure ordinary I/O devices at level 7 — it's meant for hardware
  the system genuinely doesn't need to coordinate with (e.g. DRAM refresh),
  and a level-7 handler used that way must never call an OS-9 system call
  or touch system data structures. Levels 1-6 are maskable and safe for
  ordinary device use; OS-9 masks interrupts to protect critical sections
  at the CPU level (via the status register), not merely with a software
  flag.
- **Interrupt latency** increases whenever signals are masked, an
  interrupt-masking system call is active, or the kernel is inside a
  critical section — a driver author budgeting worst-case response time
  needs to account for this, not just the ISR's own instruction count.

---

**Sources:** OS-9 v2.4 Technical I/O Manual (primary — this is by far the
most detailed of the sources for driver internals); cross-checked against
the OS-9 v2.4 Technical Reference Manual, an independent 1985-era
OS-9/68000 technical manual, and the OS-9 Guru.
