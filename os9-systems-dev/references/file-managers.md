# OS-9 File Managers

Baseline `Manual`, cross-referenced across multiple manuals; path-descriptor
byte offsets are additionally `Source` against os9exec's C.

**The entry-point conventions below are `Manual`**, and stay so short of
real hardware: os9exec, the 68k runtime available here, never runs an
installed file manager's code (`os9-dev`'s `common/using-os9exec-repl.md`,
"What os9exec does not implement"), so they could not be exercised.
The same holds for `device-drivers.md`.

A file manager sits between application I$ calls and a device driver — the
layer that understands filesystem or protocol structure (directories,
segments, line editing) while the driver knows only raw sector or character
transfer. RBF, SCF and SBF are the three standard ones; PIPEMAN is a fourth,
for pipes. A custom file manager (module type `FlMgr`, code `$0D`) follows
the same entry-point shape and must be owned by the super-user with the
system-state attribute bit set, like a driver. `Manual, Flag`: os9exec's
`load` accepted a custom file manager owned by `0.259` rather than UID 0 —
either os9exec does not enforce the requirement at load time, or OS-9 checks
it somewhere other than `load`.

## Entry Point Table (13 subroutines)

Called by the kernel with `(a1)`=path descriptor, `(a4)`=process descriptor,
`(a5)`=caller's register stack, `(a6)`=system globals:

```
+0   Create   Allocate buffers, init path descriptor, parse pathname, create file
+2   Open     Same as Create but for an existing file
+4   MakDir   Create a directory file (multi-file devices only)
+6   ChgDir   Search the directory, save its address in the process descriptor (P$DIO)
+8   Delete   Search directory, remove entry, deallocate sectors
+10  Seek     Reposition (meaningful for RBF; no-op/error on sequential devices)
+12  Read     Copy bytes to caller's buffer, handle EOF, apply record locks in update mode
+14  Write    Copy bytes to media, release record locks, acquire an EOF lock if writing at end
+16  ReadLn   Read to end-of-line, with input line editing (backspace, etc.)
+18  WriteLn  Write to end-of-line, with output formatting (linefeeds, nulls)
+20  GetStat  Get status
+22  SetStat  Set status
+24  Close    Close the path
```

## Notes on Individual Entries

- **`Open`/`Create`** allocate whatever buffers the file manager needs,
  initialize path descriptor variables, and parse the pathname; on
  multi-file devices this includes searching the directory to locate the
  file. Where a file manager has no multi-file support, `Create` is treated
  as synonymous with `Open`.
- **`MakDir`** is unusual: it's never preceded by `Create` or followed by
  `Close` the way every other entry point implicitly is — a one-shot
  operation. A file manager without directory support returns carry set /
  unknown-service.
- **`ChgDir`** doesn't change the *caller's* current directory by itself — it
  searches the target directory and stashes its address in the process
  descriptor; shell-level `chd`/`chx` semantics are built on top of this, one
  layer up.
- **`Seek`** is purely logical: it repositions the file pointer with no
  physical device access and no error past EOF. File managers without random
  access (e.g. SCF) no-op it.
- **`Read`** returns the requested byte count or an EOF error, generally with
  no editing of the bytes transferred. **`ReadLn`** stops at the first CR and
  applies whatever input editing suits the device class.
- **`Write`** expands the file when past current EOF. On RBF, a
  partial-sector write triggers a read-modify-write cycle unless the entire
  sector is replaced. **`WriteLn`** stops at the first CR and applies output
  editing (SCF appends a linefeed after CR, plus nulls, where configured).
- **`Read`/`Write` are where RBF's record locking happens** — see Record
  Locking below, and `os9-dev`'s `common/error-codes.md` (`E$DeadLk`) for the
  deadlock-detection this produces at the application level.

## GetStat/SetStat Dispatch Model

`GetStat`/`SetStat` are open-ended rather than fixed enumerations: the file
manager handles codes it recognizes (file size, EOF position, record-lock
control, path options, …) and **passes unrecognized codes straight through to
the device driver** for hardware-specific handling (formatting a track, tape
motion control, baud rate). This lets RBF or SCF work with diverse
controllers without hardcoding their status codes.

## Path Descriptor Internals

Path descriptors are created at open time and freed when the last reference
closes. Each is a composite structure in three regions.

The **first 42 bytes** ($00–$29) are a file-manager- and driver-agnostic
header the kernel manages. `Manual` (OS-9 Technical I/O Manual §1, universal
table), independently matching os9exec's `PD_` offsets:

`PD_PD` $00 (path number), `PD_MOD` $02 (access mode), `PD_CNT` $03 (open
count — **the manual marks this obsolete**), `PD_DEV` $04 (device-table
pointer), `PD_CPR` $08 (requester PID), `PD_RGS` $0A (caller register stack),
`PD_BUF` $0E (buffer), `PD_USER` $12 (owner group/user), `PD_PATHS` $16
(open-path list), `PD_COUNT` $1A (open count — the current one), `PD_LProc`
$1C (last active PID), `PD_ErrNo` $20 and `PD_SysGlob` $24 (C-language file
manager `errno` / system-global pointer), then `PD_FST` $2A and `PD_OPT` $80.

`PD_CNT` and `PD_COUNT` are two genuine fields at two offsets, not a
conflict — the manual lists both, marking `$03` obsolete.

Beyond the header sits a **file-manager-defined working area** (`PD_FST`)
whose layout varies by file-manager type. RBF uses it for file pointers,
current logical sector number, and record-lock tracking; SCF for line-buffer
state and input editing. A custom file manager defines this section for its
own needs — the kernel allocates the space, the file manager owns it.

Finally a fixed **128-byte options region** (`PD_OPT`, offset `$80`) holds
device-specific and I/O-behavior parameters: baud rate, parity, flow control,
terminal echo, backspace/delete codes, buffering strategy. At open time the
kernel populates it by copying the device descriptor's initialization table
(`M$DTyp` through `M$Opt` — see `device-drivers.md`). A user program can read
the whole region via `I$GetStt(SS_Opt)` and modify selected fields via
`I$SetStt`, subject to write-protection rules the file manager enforces.

SCF field offsets, `Manual` (Technical I/O Manual §3), matching os9exec's
SCF option structure. **Offsets here are relative to the option region**, while the
manual lists the same fields as absolute path-descriptor offsets — each
manual value is `$80` plus the value here: `PD_DTP` byte 0, `PD_EOR` `$0B`,
`PD_INT` `$10` (keyboard interrupt char), `PD_QUT` `$11` (keyboard abort),
`PD_PAR` `$14` (parity/stop-bits/bits-per-char), `PD_BAU` `$15` (baud
**code**, not a literal rate — one byte cannot hold one). The encoding is not
shared across targets: on 68k the byte is a flat index into a rate table, on
6809 it packs rate, word length and stop bits together, so neither target's
numbering can be read for the other. Both tables are in the `os9-dev` skill's
`common/utility-usage.md`, under the `baud=` note.

`PD_PAR`'s bits, `Manual` (Technical I/O Manual v2.4 p. 3-9; v2.4 Technical
Reference Manual p. B-17): bits 0–1 parity (0 none, 1 odd, 3 even); bits 2–3
bits per character (0 = 8, 1 = 7, 2 = 6, 3 = 5); bits 4–5 stop bits (0 = 1,
1 = 1½, 2 = 2); bits 6–7 reserved. SCF copies the byte to `V_TYPE` in the
driver's static storage for its interrupt routine. `xmode`'s `type=` is this
value in hex, and its `par=` (odd/even/none), `cs=` (8/7/6/5) and `stop=`
(1/1.5/2) edit the fields; none takes effect until the device is `iniz`ed
(*Using Professional OS-9* v2.4, `xmode`).

Device-descriptor offsets, `Source`: `M$Port` (hardware interface port
address) `$30`, `M$Mode` `$37`, `M$FMgr` (offset to file manager name string)
`$38`, `M$PDev` (offset to device driver name string) `$3A`, `M$DevCon`
`$3C`, `M$Opt` `$46`. `M$DTyp` is not a distinct field — it's byte 0 of the
128-byte options table starting at `$48`, exactly as `PD_DTP` is byte 0 of
the path descriptor's options section.

Path descriptors support sharing through `PD_COUNT`. `I$Open`/`I$Create`
start it at 1. `I$Dup` doesn't involve the file manager or driver — it simply
increments the count, letting parent and child (or any set of processes)
share one open-file context without re-opening. Only when `I$Close` drives
the count to zero does the kernel deallocate and unlink the descriptor.

**Kernel-side bookkeeping** — not the file manager's job, but what its
Open/Close calls are embedded inside: the kernel maintains a device table
(one entry per attached device: file manager and driver names, the driver's
static-storage pointer, a use count) and a path table (one entry per open
path). A path's device-table entry and descriptor are resolved on `I$Attach`;
see `device-drivers.md` for the INIT/TERM lifecycle this drives.

## RBF Disk Structure

RBF implements a tree-structured filesystem. Every disk has the same layout:
identification sector at LSN 0, allocation bitmap (usually LSN 1), root
directory immediately following the bitmap, then file data in segments with
allocation tracked via the bitmap. LSNs are logical sector numbers (0 to
n-1); mapping an LSN to a physical track/head/sector is entirely the driver's
job, not RBF's.

### Identification Sector (LSN 0)

`Manual`, verified against the OS-9 Technical Manual "Disk File
Organization". That manual carries one field this table omits: a 2-byte
`DD_RES` reserved slot at `$13`, between `DD_SPT` and `DD_BT`.

Every other field below abuts its neighbour exactly, with one exception worth
knowing if you are hand-authoring an LSN 0: **`$5F` is unaccounted for** —
`DD_OPT` ends at `$5E` and `DD_SYNC` starts at `$60`. Whether that byte is a
second reserved slot or a transcription gap is not settled here; treat it as
reserved and write zero.

| Field | Offset | Size | Contents |
|---|---|---|---|
| `DD_TOT` | $00 | 3 | Total sectors on media |
| `DD_TKS` | $03 | 1 | Track size, in sectors |
| `DD_MAP` | $04 | 2 | Allocation map size actually in use, in bytes |
| `DD_BIT` | $06 | 2 | Sectors per cluster (always a power of 2) |
| `DD_DIR` | $08 | 3 | LSN of the root directory's file descriptor |
| `DD_OWN` | $0B | 2 | Owner ID of the disk itself (distinct from a file's `FD_OWN`) |
| `DD_ATT` | $0D | 1 | Disk-level file attributes |
| `DD_DSK` | $0E | 2 | Disk ID |
| `DD_FMT` | $10 | 1 | Format flags: bit0 single/double side, bit1 FM/MFM density, bit2 double track (96/135 TPI), bit3 quad density (192 TPI), bit4 octal density (384 TPI) |
| `DD_SPT` | $11 | 2 | Sectors per track |
| `DD_BT` | $15 | 3 | Bootstrap's starting LSN |
| `DD_BSZ` | $18 | 2 | Bootstrap size |
| `DD_DAT` | $1A | 5 | Creation date: Y/M/D/H/M |
| `DD_NAM` | $1F | 32 | Volume name |
| `DD_OPT` | $3F | 32 | Default path-descriptor options for the device |
| `DD_SYNC` | $60 | 4 | Media integrity code |
| `DD_MapLSN` | $64 | 4 | Allocation map's starting LSN (0 defaults to LSN 1) |
| `DD_LSNSize` | $68 | 2 | Logical sector size (0 defaults to 256 bytes) |
| `DD_VersID` | $6A | 2 | Sector-0 version ID |

### Allocation Map

One bit per **cluster** — the true allocation unit, one or more sectors,
always a power-of-2 sector count per `DD_BIT` — not one bit per sector. A set
bit means the cluster is in use, defective, or non-existent; a clear bit
means free.

### File Descriptor Sector

`Manual`, verified against the OS-9 "Disk File Organization" manual.

| Field | Offset | Size | Contents |
|---|---|---|---|
| `FD_ATT` | $00 | 1 | Attribute byte (see bit layout below) |
| `FD_OWN` | $01 | 2 | Owner's user ID |
| `FD_DAT` | $03 | 5 | Last-modified date, Y/M/D/H/M — updated whenever the file is opened write/update |
| `FD_LNK` | $08 | 1 | Hard-link count for this file descriptor |
| `FD_SIZ` | $09 | 4 | File size in bytes |
| `FD_CREAT` | $0D | 3 | Creation date, Y/M/D |
| `FD_SEG` | $10 | 240 | Segment list: 5-byte entries (3-byte LSN + 2-byte sector count) to the end of the sector — 48 entries at 256-byte sectors. Unused entries must be zero |

**`FD_ATT` bit layout**: 0x01 owner-read, 0x02 owner-write, 0x04
owner-execute, 0x08 public-read, 0x10 public-write, 0x20 public-execute, 0x80
directory. There is no "group" class — only owner and public. Bit 0x40
controls shareability: `Live, Flag` — an os9lib `<stat.h>` mapping treats it
as `S_ISHARE` (set = sharable), while the Disk File Organization manual's own
prose labels it "non-sharable" (set = single-user). Treat this bit's polarity
as unresolved.

**Segments**: OS-9 uses multiple-contiguous-segment file structure — each
segment is a run of physically contiguous sectors. A file that outgrows one
segment gets additional segments, kept in close physical proximity to
minimize head movement; small files typically fit one. On write past EOF, the
file manager first tries to expand the last segment in place before
allocating a new one, in minimum-allocation-size increments. On close, unused
sectors in the last segment are normally deallocated — **except** when the
file is closed in write/update mode while *not* at EOF, where truncation is
deliberately skipped to preserve reserved space for random-access and
database files; a `seek(0)` before close forces truncation in that case. The
segment list is also what lets random access translate a logical file offset
into a physical sector.

### Directory File Format

Directories are files of 32-byte entries: a 28-byte name field (`DIR_NM`,
bytes 0-27, sign bit set on the name's last character), one unused byte (byte
28, must be zero), and a 3-byte LSN of the entry's file descriptor (`DIR_FD`,
bytes 29-31). A zero first byte marks a deleted or unused entry. Every
directory automatically gets `.` and `..` entries when created.

## Raw Physical I/O

Appending `@` to a device name (`/d2@`) opens it for raw physical I/O —
standard open/close/read/write/seek apply, addressing by physical byte offset
and bypassing the filesystem and its security entirely. Seek address = LSN ×
logical sector size (read `PD_SctSiz` from the path descriptor; 256 if zero).
Only super-users may open the raw device for write; non-super-users can read
only the identification sector and allocation bitmap, and any read past that
returns EOF.

## Record Locking

**What it is.** RBF hands out short-term exclusive access to *part* of a file
— a byte range, not the whole file — and does it by itself, as a side effect
of ordinary reads and writes. A read on a path open for update locks the
bytes it just returned; the next write on that path releases them. Anything
else touching those bytes meanwhile waits. No locking calls appear anywhere
in the program. The same mechanism, applied past the last byte where no data
exists yet, is what makes a reader wait at end-of-file for a writer that has
not finished — so "record locking" and "EOF lock" are one feature, not two.

**This is not a defensive feature you invoke; it's a design opportunity.**
RBF's locking is automatic and silent. It protects a program whether or not
its author ever thought about concurrency — but it also *enables* designs
that would otherwise need real synchronization primitives, and those designs
only get built by someone who knows the guarantee exists. Two cases worth
designing around deliberately rather than merely tolerating as a safety net
(`Hearsay` — firsthand from the mechanism's designer at Microware):

1. **A database-style read-modify-write cycle is safe under concurrent
   access with zero application-level locking calls.** A `Read` in update
   mode automatically locks the record just read; the following `Write` on
   that path releases it. Two processes both doing "read a record, change it,
   write it back" on one file cannot silently corrupt each other's update —
   the classic lost-update race — because the kernel serializes them without
   either program calling `SS_Lock`. Write a database this way *on purpose*
   and concurrency safety is free.
2. **A plain growing file can coordinate a slow producer and a slow consumer
   as if it were a pipe, with a persistent on-disk record.** A write landing
   at the current end of file takes an EOF lock — a "ghost lock" past the
   last byte, not a lock on any real data — specifically so a reader catching
   up to a live writer stalls at the edge instead of mistaking "caught up to
   current EOF" for "the writer is done." A spooler appending output over a
   long run and a slow consumer feeding a printer can be built around a plain
   file rather than an actual pipe, and unlike a pipe the data persists after
   both processes exit. Unix of that era had no equivalent.

### Mechanics

- A **read** (or `ReadLn`) on a path opened for update locks the bytes it
  requested, from the file pointer it started at — a `ReadLn` asking 256
  bytes locks 256 regardless of where the CR landed. **Clamped to the end of
  the file**, which is not optional: a read that locks past EOF holds ground
  belonging to whoever is appending, and the result is a genuine deadlock
  that no `E$DEADLK` catches, because the two paths are different processes.
  The invariant is **no path ever locks a byte that does not exist yet**.
  Consequence: BASIC09 asks 511 bytes on every `READ` whatever the target
  string's size, so two records closer together than that can never be held
  independently — fine for record-oriented code that asks for its record
  size, coarse for BASIC09. Reads on read-only or execute-mode paths never
  lock anything, since those modes can't update records anyway; prefer
  read-only opens when writing isn't needed, both for that reason and speed.
- A **write** always releases any record currently locked by that path, and
  locks nothing itself *unless* it lands at EOF, in which case it takes the
  EOF lock — **in any write mode, not only update**. Nothing real is locked:
  the range covers bytes that do not exist. It has two jobs, and the second
  is easy to miss. One, stop a *reader* concluding the file is finished.
  Two, **stop two writers extending the file at the same time** — which the
  documentation gives as the reason the EOF lock exists at all. So appenders
  *are* serialized at the edge. A write-only sequential-output creator gains
  the EOF lock as soon as it creates the file; that is what keeps a spooler
  one step behind an assembler writing its listing through plain `>`.
- **Which opens lock what**, since "locks only happen in update mode" is only
  two-thirds true:
  - *read auto-lock*: **update mode only** (read+write). A read-only path
    cannot modify what it read, so it locks nothing.
  - *EOF wait*: a reader blocks at end-of-file while **another path holds the
    EOF lock**, and that lock is taken by whoever last wrote at the end — in
    any write mode. Both the waiting reader's mode and the producer's are
    irrelevant: a follower opens plain `READ`, and a producer using plain `>`
    holds the ghost just as an update-mode one does. This is the correction
    below: there is no way for a sequential writer to opt *out* of being
    followed by choosing its open mode.
  - *explicit `SS_Lock`*: **update mode too**, same rule — a path that cannot
    modify what it read has nothing to protect, and allowing it a lock would
    hand it a way to hold up writers, the very lockout this design avoids. A
    *release* is always allowed; it can only let something go.
- A lock is released by the next read, the next write, a path close, or an
  explicit `SS_Lock` SetStat. A zero-byte read or write drops every lock that
  path holds — record, EOF, or whole-file. `seek()` never affects locking.
- `SS_Lock` locks or releases part of a file directly; `SS_Ticks` sets how
  long a caller waits for someone else's lock before giving up.

**The EOF lock is not gated on mode, and getting that wrong breaks the
spooler.** A write landing at end of file gains it in *any* write mode — it is
the only case where a write locks part of a file, and a sequential-output
creator gains it on creation. Case 2 above depends on this: the *write-only*
assembler must hold the ghost lock, or the consumer has nothing to sleep
against.

How the two reimplementations do it, if you are modelling one:

- **os9exec** — the EOF lock is its own flag on the path, gained by a write
  landing at the end of the file through any write-capable path (write-only
  or update) and by a create for output, and dropped at close before the
  wake. `Live` (os9exec), RBF image, reader and writer in separate processes:
  a reader of a file its creator has not yet written to waits until the first
  write; a writer that has moved away from the end holds no lock, and a
  reader then sees every byte already written, including those appended at
  EOF before it opened. The implementation traps worth knowing if you model
  this: the creator's lock must survive the path walk's directory locks, and
  a path joining a file others hold open must take the file's end from the
  most advanced path, not from disk, because a growing file's end lives in
  the writer's state until it is flushed.
- **NitrOS-9** — stock 6809 RBF takes it for a write-only producer and a
  write-only creator alike, and wakes waiters on every write. `Live`
  (NitrOS-9). The mode gate the stock module *does* have is on the read
  auto-lock, which is correct. Its real remaining RBF defect is a lost update after a
  parked writer wakes — a matter of retrying the conflict walk, not of mode.

Either way a read-only path takes nothing and only ever waits: the manuals'
"reads or writes" names the position, not a licence for a follower to lock the
end, which would have the spooler block the assembler.

Under os9exec, locking exists only on RBF images, not on host directories —
see `os9-dev`'s `common/using-os9exec-repl.md`.

### Implementing it — four things that bite

For anyone implementing the mechanism, in a file manager or an emulation of
one; all four apply on 6809 as on 68k.

1. **Two paths on one file must actually see the same file.** Before locking
   can matter at all, check this: if each path keeps its own copy of the FD
   sector taken at open and its own data sector buffer, a reader never sees
   size, segment list or sector contents change underneath it, and a lock is
   pointless. Link paths on the same file into a ring and treat their buffers
   as a shared cache.
2. **The directory walk goes through the same read path.** Opening a file for
   update walks directories via the ordinary read routine, so the path takes
   a lock on *directory* bytes and carries those offsets onto the file it
   ends up at — its own first read then collides with its own stale lock.
   Drop locks whenever a path changes which file it refers to.
3. **Judge a read conflict on bytes delivered, not bytes requested.** A
   caller may offer a buffer far larger than the record. Since reading is not
   destructive, the honest order is: read, check what was actually touched,
   unwind if it conflicts. Writes are the opposite — destructive, exact
   length known up front, so check before.
4. **Refuse a same-process conflict rather than sleeping on it**
   (`E_DEADLK`). The only process that could release the lock is the one
   about to wait for it. Without this, a single-process test doesn't fail, it
   *hangs* — and this refusal is what makes the whole mechanism testable
   without concurrency.

Also: **`SS_Ticks` is only as good as the scheduling under it.** A timeout
can fire only if the blocked process is re-run while it waits, so on a
runtime that never preempts, a blocked reader may never notice its deadline.

### Testing it

**A lost-update counter race cannot detect a missing lock.** On a runtime
that never pre-empts, a read-modify-write essentially never interleaves, so
the race never opens and the counter lands on the expected total against an
implementation with no locking whatsoever. What works instead:

- **Force a conflict and check it is refused.** One process, two paths on one
  file, both open for update: path A reads a record, path B reads the same
  bytes. B must be refused with `E_DEADLK`. Deterministic, no timing, cannot
  hang.
- **Cross-process, for the blocking path.** A holder that reads a record and
  sits on it across yield points, and a waiter that tries the same bytes. The
  waiter must not return until the holder writes — and compare the *values*:
  a waiter that returns the stale pre-update record is the lost update caught
  in the act.
- **`SS_Lock` needs assembly** — there's no BASIC09 route to a SetStat.
- **Single-process deterministic tests are worth more than they look**: one
  process with two paths covers visibility, cache invalidation, the
  writer-closes-first lifecycle, and the deadlock refusal, with no timing at
  all.

Neither os9exec nor NitrOS-9 matches the design intent above in full, and
they fail differently — do not treat either as a reference for this
mechanism, and do not read either one's behavior as evidence about what
genuine Microware OS-9 did.

## File Security

Every file open checks access permission on every directory in the pathlist
plus the target file itself — no read permission on a directory means nothing
under it is reachable, whatever the target file's own permissions say.

One gotcha for a file-manager author porting or debugging security logic:
`FD_OWN` is nominally a 2-byte owner-ID field, but RBF compares only the
**low-order byte** of both group and user ID from the password file — a user
with ID 256 (or group 256) collides with ID 0, which RBF treats as
super-user. A file manager module itself, like a driver, must be owned by
super-user with the system-state attribute bit set or OS-9 refuses to load it.

## Device-Independence in Practice

The reason this layer exists: a program's `I$Read` is identical whether the
device is a disk (RBF), a terminal (SCF), a tape (SBF), or a pipe (PIPEMAN) —
the *file manager* is what differs per device class, not the
application-facing system call. PIPEMAN needs no physical device at all: a
pipe's path descriptor uses a null driver backed by a plain FIFO memory
buffer — 90 bytes by default per the manuals, though os9exec ships 4096 (see
the `os9-dev` skill's `common/ipc.md`). When writing a new file manager, the 13-entry
table above is the complete contract the kernel expects; how "Seek" or "Read"
map onto your protocol is entirely up to the implementation.

---

**Sources:** OS-9 v2.4 Technical Reference Manual and Technical I/O Manual
v2.4 (file-manager entry points, GetStat/SetStat dispatch, path descriptor
structure); Disk File Organization manual (RBF disk structure, record
locking, raw I/O, file security) — cross-checked against The OS-9 Guru and
the v2.4 Technical Reference Manual for pipes. The File Descriptor Sector
table's `FD_LNK` row is confirmed against both the Disk File Organization
manual's own field table (Figure 7-2) and an independent 1985-era OS-9/68000
technical manual. The mode rules for the EOF lock are cross-referenced across
four: the 6809 *System Programmers Manual* §6.6.1/§6.6.3/§6.6.5, Tandy's
*Technical Reference* and *Level Two Development System*, and the 68k *v2.4
Technical Reference*. See `device-drivers.md` for the driver side of the same
layered model.
