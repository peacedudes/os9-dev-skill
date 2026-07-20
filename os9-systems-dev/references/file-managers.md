# OS-9 File Managers

**Verification status:** baseline is `Manual` — cross-referenced across
multiple manuals. **Exception: the Record Locking section is now largely
`Live` on 68k** — the mechanism was implemented in `os9exec` and each
behavior verified with a paired before/after transcript (2026-07-19). Read
that section's "Implemented and verified" and "Testing this" subsections
before porting it anywhere; the design intent itself stays `Hearsay` (the
designer's own account) and cannot be upgraded, but the *behavior* is now
demonstrated. One prior `Live` claim there is **retracted** — a lost-update
counter race that passed against code with no locking at all. The path-descriptor byte-offset claims below are
`Source` — spot-checked against `os9exec`'s own C source (the
`PD_FST`/42-byte-header claim matches; see the `PD_COUNT` "Known gap"
note below for a `Source, Flag` offset conflict that check turned up).

**Entry-point conventions below are untestable on `os9exec`, not just
untested — confirmed the same platform gap as `device-drivers.md`, and
the same root cause, not just a similar symptom.** `Live` (2026-07-18):
a correctly-assembled, byte-verified custom file manager module,
installed exactly per this file's own guidance, was never invoked by the
kernel. Source-confirmed: `OS9_I_OpenCreate` (`icalls.c`) classifies
every path via `IO_Type()`'s hardcoded string matching, then dispatches
through `filestuff.c`'s fixed `fmgr_op[]` C table — **the literal same
function and table used for device-driver dispatch**, with no code
anywhere that loads an installed file-manager or driver module. See
`os9-systems-dev/SKILL.md` and `device-drivers.md`'s equivalent note, and
`test/68k-live-verification/dogfood-report-filemgr-2026-07-18.md` (in the
`os9exec` repo) for the full investigation. Treat the entry-point
conventions below as `Manual` indefinitely, same as `device-drivers.md`.

A file manager sits between application I$ calls and a device driver — it's
the layer that understands filesystem/protocol structure (directories,
segments, line editing) while the driver only knows raw sector/character
transfer. RBF, SCF, and SBF are the three standard ones (PIPEMAN is a
fourth, for pipes — see below); a custom file manager (module type `FlMgr`,
code `$0D`) follows the same entry-point shape and must be owned by the
super-user with the system-state attribute bit set, like a driver.
**`Manual, Flag`**: a live-loaded custom file manager module was accepted
by `load` under owner `0.259`, not UID 0 — either the super-user-ownership
requirement isn't enforced at `load` time on `os9exec` (only checked
later, somewhere this session's testing never reached given the dispatch
wall above), or the claim needs a narrower scope. Not chased further.

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
  `Close` the way every other entry point implicitly is — it's a one-shot
  operation, and a file manager without directory support simply returns
  carry set / unknown-service.
- **`ChgDir`** doesn't change anything about the *caller's* current
  directory concept by itself — it searches the target directory and
  stashes its address in the process descriptor; the shell-level `chd`/`chx`
  semantics (see `os9-dev`'s `common/os9-mental-model.md`) are built on top
  of this, one layer up.
- **`Seek`** is purely logical: it repositions the file pointer with no
  physical device access and no error if the new position is past EOF.
  File managers without random access (e.g. SCF) simply no-op it.
- **`Read`** returns the requested byte count or an EOF error if no more
  data is available, generally with no editing of the bytes transferred.
  **`ReadLn`** differs by stopping at the first CR (end-of-record) and
  applying whatever input editing is appropriate for the device class.
- **`Write`** expands the file when past current EOF. On RBF, a partial-sector
  write triggers a read-modify-write cycle unless the entire sector is replaced.
  **`WriteLn`** stops at the first CR and applies output editing (SCF appends a
  linefeed after CR, plus nulls, where configured).
- **`Read`/`Write` are where RBF's record-locking actually happens** — see
  the Record Locking section below, and `os9-dev`'s `common/error-codes.md`
  (`E$DeadLk`) for the deadlock-detection behavior this produces at the
  application level.

## GetStat/SetStat Dispatch Model

`GetStat`/`SetStat` are open-ended rather than fixed enumerations: the file
manager handles codes it recognizes (file size, EOF position, record-lock
control, path options, ...) and **passes unrecognized codes straight through to
the device driver** for hardware-specific handling (formatting a track, tape
motion control, baud rate, etc.). This lets RBF or SCF work with diverse
controllers without hardcoding their status codes.

## Path Descriptor Internals

Path descriptors are dynamically created at open time and freed when the
last reference closes. Each descriptor is a composite structure, divided
into three regions:

The **first 42 bytes** form a file-manager- and driver-agnostic header:
path number, access mode, references to the active file manager and driver,
and other bookkeeping the kernel manages. Every path descriptor starts with
this section regardless of which file manager is driving the I/O.

Beyond that sits a **file-manager-defined working area** (`PD_FST`) whose
layout and meaning vary by file-manager type. RBF uses it for file
pointers, current logical sector number, and record-lock tracking. SCF
uses it for line-buffer state and input editing data. A custom file
manager defines this section for its own needs — the kernel allocates
space, the file manager owns it.

Finally, a fixed **128-byte options region** (`PD_OPT`, at offset `$80`)
holds device-specific and I/O-behavior parameters: baud rate, parity,
flow control, terminal echo, backspace/delete character codes, buffering
strategy. At open time, the kernel populates this region by copying the
device descriptor's initialization table (`M$DTyp` through `M$Opt` — see
`device-drivers.md`). A user program can read the whole region via
`I$GetStt(SS_Opt)` and modify selected fields via `I$SetStt`, subject to
write-protection rules the file manager enforces.

**`Source`:** `os9exec`'s own device-descriptor
header (`module_from_book.h`, Guru-derived, same source as the rest of
this file) confirms `M$Mode`/`$37`, `M$DevCon`/`$3C`, and `M$Opt`/`$46`
exactly, and fills in what was previously missing: `M$Port` (hardware
interface port address) at `$30`, and — answering "which driver/file
manager does this descriptor select" — `M$FMgr` (offset to file manager
name string) at `$38` and `M$PDev` (offset to device driver name string)
at `$3A`. `M$DTyp` still isn't a distinct field: it's byte 0 of the
128-byte options table itself (starting at `$48`), same as `PD_DTP` is
byte 0 of the path-descriptor options section — not a separate top-level
descriptor field, so there's nothing further to resolve there.

Path descriptors support sharing through a reference counter (`PD_COUNT`,
offset `$1A`). When `I$Open` or `I$Create` allocates a new descriptor, the
count starts at 1. `I$Dup` doesn't involve the file manager or driver —
it simply increments the count on the existing descriptor, allowing
parent and child processes (or any multiple processes) to share the same
open-file context without re-opening. Only when `I$Close` drives the count
to zero does the kernel deallocate and unlink the descriptor.

**`Source, Flag`:** `os9exec`'s own path-descriptor header (`sgstat_from_book.h`,
also Guru-derived) defines an "open count" field, `PD_CNT`, at offset `$03`
— not `$1A` — and it's unused dead code (`os9exec` implements no `I$Dup`
at all, so there's no live share-counter to observe either offset against).
This offset conflict is unresolved; treat both as unconfirmed until checked
against a primary source directly.

**Kernel-side bookkeeping** (not the file manager's job, but what the file
manager's Open/Close calls are embedded inside): the kernel maintains a
device table (one entry per attached device — file manager/driver names,
the driver's static-storage pointer, a use count) and a path table (one
entry per open path). A path's device-table entry and descriptor are
resolved on `I$Attach`; see `device-drivers.md` for the INIT/TERM lifecycle
this drives on the driver side.

## RBF Disk Structure

RBF implements a tree-structured filesystem: every disk has the same basic
layout — identification sector at LSN 0, allocation bitmap (usually LSN 1),
root directory immediately following the bitmap, then file data organized
into segments with allocation tracked via the bitmap. LSNs are logical
sector numbers (0 to n-1); mapping an LSN to a physical track/head/sector
is entirely the driver's job, not RBF's.

### Identification Sector (LSN 0)

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

One bit per **cluster** (the true allocation unit — one or more sectors,
always a power-of-2 sector count, per `DD_BIT`), not one bit per sector. A
set bit means the cluster is in use, defective, or non-existent; a clear
bit means free.

### File Descriptor Sector

| Field | Offset | Size | Contents |
|---|---|---|---|
| `FD_ATT` | $00 | 1 | Attribute byte (see bit layout below) |
| `FD_OWN` | $01 | 2 | Owner's user ID |
| `FD_DAT` | $03 | 5 | Last-modified date, Y/M/D/H/M — updated whenever the file is opened write/update |
| `FD_LNK` | $08 | 1 | Hard-link count for this file descriptor |
| `FD_SIZ` | $09 | 4 | File size in bytes |
| `FD_CREAT` | $0D | 3 | Creation date, Y/M/D |
| `FD_SEG` | $10 | 240 | Segment list: 5-byte entries (3-byte LSN + 2-byte sector count) to the end of the sector — 48 entries at 256-byte sectors. Unused entries must be zero. |

**`FD_ATT` bit layout**: 0x01 owner-read, 0x02 owner-write, 0x04
owner-execute, 0x08 public-read, 0x10 public-write, 0x20 public-execute,
0x80 directory. There is no "group" class — only owner and public. Bit
0x40 controls shareability: `Live, Flag` — an os9lib `<stat.h>` mapping
treats it as `S_ISHARE` (set = sharable), while the Disk File Organization
manual's own file-descriptor prose labels it "non-sharable" (set =
single-user). Treat this bit's polarity as unresolved until independently
verified against a real disk image, rather than trusting either source blind.

**Segments**: OS-9 uses multiple-contiguous-segment file structure — each
segment is a run of physically contiguous sectors; a file that outgrows one
segment (on creation-time expansion, or when no single contiguous run is
free) gets additional segments, kept in close physical proximity to
minimize head movement. Small files typically fit one segment. On write
past EOF, the file manager first tries to expand the last segment in
place before allocating a new one, in minimum-allocation-size increments.
On close, unused sectors in the last segment are normally deallocated
(truncated) — **except** when the file is closed in write/update mode
while *not* at EOF, where truncation is deliberately skipped to preserve
reserved space for random-access/database files; a `seek(0)` before close
is the way to force truncation in that case. The segment list is also what
lets random access translate a logical file offset into an actual physical
sector.

### Directory File Format

Directories are files made of 32-byte entries: a 28-byte name field
(`DIR_NM`, bytes 0-27, sign bit set on the name's last character), one
unused byte (byte 28, must be zero), and a 3-byte LSN of the entry's file
descriptor (`DIR_FD`, bytes 29-31). A zero first byte marks a
deleted/unused entry. Every directory automatically gets `.` (itself) and
`..` (parent) entries when created.

## Raw Physical I/O

Appending `@` to a device name (e.g. `/d2@`) opens it for raw physical I/O
— standard open/close/read/write/seek apply, addressing by physical byte
offset and bypassing the filesystem (and its security) entirely. Seek
address = LSN × logical sector size (read `PD_SctSiz` from the path
descriptor; 256 if zero). Only super-users may open the raw device for
write; non-super-users can read only the identification sector and
allocation bitmap through it — any read attempt past that returns EOF.

## Record Locking

**What it is.** RBF hands out short-term exclusive access to *part* of a
file — a byte range, not the whole file — and does it by itself, as a side
effect of ordinary reads and writes. A read on a path open for update locks
the bytes it just returned; the next write on that path releases them.
Anything else touching those bytes meanwhile waits. No locking calls appear
anywhere in the program. The same mechanism, applied past the last byte where
no data exists yet, is what makes a reader wait at end-of-file for a writer
that has not finished — so "record locking" and "EOF lock" are one feature,
not two.

**Why this matters, before the mechanics — this is not a defensive
feature you invoke, it's a design opportunity most programmers using it
never fully exploited, because it was never explained well enough
(firsthand from the person who designed it at Microware): RBF's locking
is automatic and silent. It protects a program whether or not the
programmer ever thought about concurrency — but it also *enables*
designs that would otherwise need real synchronization primitives, and
those designs only get built by someone who knows the guarantee exists.**
Two concrete cases worth designing around deliberately, not just
tolerating as a safety net:

1. **A database-style read-modify-write cycle is safe under concurrent
   access with zero application-level locking calls.** A `Read` (in
   update mode) automatically locks the record just read; the following
   `Write` on that same path automatically releases it. Two processes
   both doing "read a record, change it, write it back" on the same file
   can't silently corrupt each other's update (the classic lost-update
   race) — the kernel serializes them without either program ever
   calling `SS_Lock`. Write a database this way *on purpose* and you get
   real concurrency safety for free.
2. **A plain, ordinary growing file can coordinate a slow producer and a
   slow consumer as if it were a pipe, with a persistent on-disk
   record.** A write landing at the current end of file takes a
   whole-file EOF lock specifically so a reader catching up to a live
   writer stalls right at the edge instead of racing ahead and mistaking
   "caught up to current EOF" for "the writer is done." A spooler
   appending output over a long run and a slow consumer (e.g. feeding a
   printer) can be built around a plain file instead of an actual pipe —
   useful specifically because, unlike a pipe, the data also persists
   after both processes exit. This has no real equivalent on Unix
   systems of that era — a single ordinary file coordinating a
   slow-producer/slow-consumer pair, backed by real storage, isn't
   something a plain `open()`/`read()`/`write()` model gives you.

The mechanics that implement both cases:
- A **read** (or `ReadLn`) on a path opened for update locks the bytes it
  handed back, from the file pointer it started at. `Manual` says the
  *requested* count — a `ReadLn` asking 256 bytes locking 256 regardless of
  where the CR landed. The designer's own recollection is the opposite (a
  `ReadLn` that asks 80 and delivers 43 should lock 43), stated with the
  explicit caveat that he was not certain. **`os9exec` implements
  delivered**, and there is a practical argument for it: BASIC09 offers a
  511-byte buffer for an 8-byte record, so locking the requested count locks
  most of the file and makes unrelated records collide. `Flag` — unresolved
  between manual and designer; if you have a primary source, settle it.
  Reads on read-only or execute-mode paths never lock anything,
  since those modes can't update records anyway — prefer read-only opens
  when writing isn't needed, both for this reason and for speed.
- A **write** always releases any record currently locked by that path; it
  doesn't itself lock anything *unless* it lands at EOF, in which case it
  takes the **EOF lock** — a lock on the position past the last byte.
  **This does NOT serialize appenders**, and an earlier revision of this file
  saying so was wrong. Nothing real is locked: the range covers bytes that do
  not exist. Its only job is to stop a *reader* concluding the file is
  finished. Two programs appending to one log do not shut each other out —
  they never contend, because each append lands at a different offset, and a
  write-only path takes no record lock at all. Getting this backwards means
  building mutual exclusion between writers that the design never had.
- **Which opens lock what**, since "locks only happen in update mode" is only
  two-thirds true:
  - *read auto-lock*: **update mode only** (read+write). A read-only path
    cannot modify what it read, so it locks nothing.
  - *EOF wait*: triggered by any other path holding the file open **for
    write** — update mode is not required. A plain appending writer must
    still make readers wait, or the pipe-like case does not work at all.
  - *explicit `SS_Lock`*: `os9exec` currently applies **no mode check**, so a
    read-only path can take one. Probably wrong — it should plausibly require
    a write-capable open — but unverified against any source, so it is left
    as-is and flagged here rather than guessed at. `Flag`.
- A lock is released by: the next read, the next write, a path close, or
  an explicit `SS_Lock` `SetStat`. A zero-byte read or write drops every
  lock that path holds — record, EOF, or whole-file — outright. `seek()`
  never affects locking.
- `SS_Lock` locks/releases part of a file directly; `SS_Ticks` sets how
  long a caller will wait for a lock held by someone else before giving up.

**RETRACTED 2026-07-19 — that 600/600 proved nothing.** The counter race
below passed against an `os9exec` that had **no record locking whatsoever**:
`SS_Lock` was `pNop`, there was no lock state in any path structure, and
`E_LOCK`/`E_DEADLK` appeared only in a debugger string table. It passed
because `os9exec` never pre-empts (the emulator's own
"Cooperative-Multiprocess" source banner), so a read-modify-write essentially never
interleaves and the race never opens. **A counter race cannot detect a
missing lock.** To tell a working lock from a scheduler that never
interleaves, force a conflict and check it is *refused* — see "Testing this"
below. Kept here because the trap is easy to fall into twice. Original
(now-uninformative) run: `Live`
(2026-07-18), on a real RBF disk image (`/h1/CLAUDETEST/counter.dat`):
two separate processes raced 300 iterations each of unprotected
read-modify-write (`SEEK` to a fixed record offset mid-file, not at EOF /
`GET` / `+1` / `SEEK` / `PUT`, path held open across all iterations, no
`SS_Lock` anywhere in either program) against the same shared counter.
Final count landed exactly on 2×300=600 in two independent full races. See
`test/68k-live-verification/dogfood-report-lostupdate-2026-07-18.md`
(in the `os9exec` repo) for the full pass, including a real but
unrelated blocker hit and worked around (BASIC09 needs the `math` trap
handler resident for any numeric operation; the account's own
`/h0/startup` `load -s cio csl math` line silently fails to make it
resident — `load math` without `-s` works).

## Implemented and verified on `os9exec`/68k (2026-07-19)

`Live`. All of it was missing before this: RBF had no record locking at all,
`SS_Lock` was `pNop` (returning **success** while doing nothing, so a program
that locked defensively was told it had worked), `SS_Ticks` was absent, and a
reader at end-of-file was told the file was finished while a writer was still
appending. Each behavior below has a paired before/after transcript against a
baseline binary in the `os9exec` repo,
`test/68k-live-verification/dogfood-report-eoflock-fix-2026-07-19.md`.

**The prerequisite nobody expects.** Before any locking can matter, two paths
on one file have to be looking at the same file. In `os9exec` they were not:
each path kept its own copy of the FD sector taken at open, and its own data
sector buffer, so a reader never saw the size, the segment list or the sector
contents change underneath it. Fixed by linking paths on the same file into a
ring and treating their buffers as a shared cache. **Anyone porting this
should check the same thing first** — a lock is pointless if the reader cannot
see what the writer wrote.

**What the mechanism turned out to be**, from the designer directly: it is one
lock, not two. A read locks the record it read; the next write releases it;
a conflicting access sleeps and every release wakes all waiters. The EOF case
is that same lock placed where there is no data yet — a **ghost lock** past
the last byte. Nothing real is locked, which is why a second appender is
unaffected and why two programs logging to one file do not shut each other
out. End-of-file is therefore a *lock to acquire*, not a condition to compute
— which is exactly what both reimplementations got wrong.

**Four things that bit, all of which a 6809 port would hit too:**

1. **The directory walk goes through the same read path.** Opening a file for
   update walks directories via the ordinary read routine, so the path takes a
   lock on *directory* bytes and carries those offsets onto the file it ends
   up at. Its own first read then collides with its own stale lock. Locks must
   be dropped whenever a path changes which file it refers to.
2. **Judge a read conflict on bytes delivered, not bytes requested.** A caller
   may offer a buffer far larger than the record. Since reading is not
   destructive, the honest order is: read, then check what was actually
   touched, and unwind if it conflicts. Writes are the opposite — destructive,
   exact length known up front, so check before.
3. **Refuse a same-process conflict rather than sleeping on it** (`E_DEADLK`).
   The only process that could release the lock is the one about to wait for
   it. Without this a single-process test does not fail, it *hangs* — and it
   is what makes the whole thing testable without concurrency.
4. **`SS_Ticks` is only as good as the scheduling under it.** A timeout can
   only fire if the blocked process is re-run while it waits. On `os9exec`,
   which does not pre-empt, a blocked reader got two chances to check its
   deadline and then none until the holder released — so the limit was never
   noticed. It works with the emulator's optional tick on.

## Testing this

The counter race cannot detect a missing lock (see the retraction above).
What does:

- **Force a conflict and check it is refused.** One process, two paths on one
  file, both open for update: path A reads a record, path B reads the same
  bytes. B must be refused with `E_DEADLK`. Deterministic, no timing, cannot
  hang. (`dogfood-recordlock.bas`)
- **Cross-process, for the blocking path.** A holder that reads a record and
  sits on it across yield points, and a waiter that tries the same bytes. The
  waiter must not return until the holder writes. Compare the *values*: before
  the fix the waiter got the stale pre-update record, which is the lost update
  caught in the act. (`dogfood-recordlock-holder/-waiter.bas`)
- **`SS_Lock` needs assembly** — no BASIC09 route to a SetStat.
  (`dogfood-sslock.a`)
- **Single-process, deterministic tests are worth more than they look**: one
  process with two paths covers visibility, cache invalidation, the
  writer-closes-first lifecycle, and the deadlock refusal, with no timing at
  all.

**Does NOT reproduce on NitrOS-9 (6809) — real, reproducible lost
updates.** `Live` (2026-07-19), identical test design (10-byte record,
`count` field pushed away from EOF by 4 `INTEGER` filler fields, no
`SS_Lock` anywhere, N=300 per racer) run against real RBF on the 6809 EOU
test disk, under NitrOS-9 (via XRoar): **two independent races both
landed short of 2×300=600** — 457 (143 lost) and 584 (16 lost). Two
things rule out the obvious alternative explanations: the racers' own
"last local count seen" values (340/457 and 564/584 — neither racer's own
iteration count) directly prove genuine interleaved access, stronger
evidence of real concurrency than the 68k pass had; and neither racer
sets `ON ERROR GOTO`, so if lock contention were erroring, the process
would have dropped into interactive Debug Mode rather than completing
cleanly — both races completed with no crash, ruling out "an unhandled
I/O error let stale data through" as the mechanism. **The lock contention
is not erroring — it is genuinely not being prevented in this build, in
this test.**

**Important scope note, easy to misread this as saying more than it
does: this is a finding about NitrOS-9's own RBF implementation, not
about "6809" as an architecture, and not about genuine Microware OS-9.**
NitrOS-9 is an independent, community-written clone of OS-9 Level 2 — it
does not contain licensed Microware source, and its own reimplementation
of a mechanism can diverge from the original design intent (see the
firsthand design-intent note at the top of this section) in ways that
have nothing to do with what real Microware-authored code on real 1980s
6809 hardware actually did. `os9exec` is likewise an independent
reimplementation, of the 68k side. Both are being measured here against
the same authoritative design intent, and each has now shown its own,
different divergence (this case for NitrOS-9; case 2 below for
`os9exec`) — that is two separate reimplementation gaps, not "68k is
correct and 6809 is broken" or vice versa. Root mechanism for NitrOS-9's
gap not yet determined (candidates: the automatic per-record lock
genuinely isn't acquired/enforced for this access pattern in this
codebase; a BASIC09-on-6809 `GET`/`PUT` buffering layer doesn't route
through the lock-acquiring path). Full investigation:
`test/6809-live-verification/dogfood-report-lostupdate-6809-2026-07-19.md`
(in the `os9exec` repo). **Case 1's design intent is therefore confirmed
`Live` on `os9exec`/68k only — do not assume it extends to NitrOS-9, and
do not read either result as evidence about what genuine Microware OS-9
did.**

**Follow-up `Live` (2026-07-19) — NitrOS-9's record lock is real, not
absent; the lost-update gap is narrower than "no locking exists."** A
decisive contention test settles the question the lost-update pass left
open (does a conflicting accessor ever actually block, the same
discriminating test that established `os9exec` has zero locking at the
source level): one process `GET`s a record and deliberately holds it —
burning real wall-clock time without releasing — while a second process
concurrently tries to `GET` the same record. **In both of two independent
runs, the second process's `GET` did not return until after the first
process's `PUT` released the lock, and it read back the released value,
never the stale pre-lock value.** This is real, observed blocking — the
opposite of "no lock." Reconciling this with the lost-update result
above: NitrOS-9's lock works correctly for a single, well-separated
lock/hold/release cycle, but does not fully prevent lost updates under
*rapid, tight-loop re-acquisition* (300 back-to-back iterations with no
gap between a `PUT` and the next `GET`) — the likely mechanism (not
confirmed further) is a narrow race window in the release-then-reacquire
sequence itself, consistent with the variable, non-total loss magnitude
observed (143 lost in one race, only 16 in another, never all 600).
**So: NitrOS-9 has a real record-lock mechanism whose failure mode is a
timing-dependent reacquisition race, not an absent or no-op lock.** This
is a meaningfully different, more specific characterization than "record
locking doesn't work on NitrOS-9" — don't collapse it back to that
simpler-but-wrong claim. Full investigation:
`test/6809-live-verification/dogfood-report-lockcontention-6809-2026-07-19.md`
(in the `os9exec` repo).

**`os9exec`'s actual behavior vs. the design intent above — confirmed
divergent for case 2, likely a real `os9exec` bug** (the
pipe-like producer/consumer coordination). `Live` (2026-07-18), on a real
RBF disk image (`/h1`, not a host-native mount — host-native mounts have
no real locking machinery underneath):
**a reader path opened while a writer path is concurrently open on the
same file sees zero bytes of that file's data for the reader's entire
remaining lifetime — not "not yet," but never, even long after the
writer closes.** Reproduced cleanly across multiple runs (immediate
open, and opening after 34 records were already flushed — ruling out a
startup race), identically in both `READ`-only and `UPDATE` modes. Each
failed read returns `E$EOF` (211) **immediately, non-blocking** — the
mechanism is poll-based, not a real blocking wait. A **brand-new** `OPEN`
issued after the writer closes reads the file perfectly, proving the
data itself is intact; the bug is specific to a path that was already
open during the writer's activity, and that path never recovers
visibility for the rest of its own life. This is worse than a simple
"locked out until the writer exits" reading — the writer exiting doesn't
fix it either. Plausible mechanism (not confirmed further): a
concurrently-opened path's cached view of the file's current extent
isn't refreshed by anything, including the writer's own close. Full
investigation: `test/68k-live-verification/dogfood-report-eoflock-2026-07-18.md`
(in the `os9exec` repo). **Not fixed as part of documenting this** — flagged
for whoever picks up `os9exec`-side RBF work next.
Separately, missing from this section before now: nothing stated whether
a reader catching up to a live writer blocks or returns immediately —
now known (immediate-return, poll-yourself), added above.

**NitrOS-9 (6809) does NOT reproduce this specific bug — but read that
narrowly, not as "6809 gets it right."** `Live` (2026-07-18), same
experiment (a concurrently-opened reader path racing an active writer
path on a shared, growing file), run against real RBF on the 6809 EOU
test disk under NitrOS-9 (`tools/nitros9repl.sh`), not `os9exec`: **the
reader eventually sees every byte the writer wrote, correctly, in every
clean run** — never the permanent, zero-visibility lockout `os9exec`
produces. **NitrOS-9 is a community-written clone of OS-9 Level 2, not
licensed or verified Microware source** — this result says NitrOS-9's
own RBF doesn't share `os9exec`'s specific permanent-lockout bug, not
that it correctly implements "the mechanism" as Microware originally
built it, and not that "6809" as an architecture is inherently more
correct than 68k. It's a second independent reimplementation with its
own behavior, being compared against the same design-intent statement
`os9exec` is measured against — and its behavior isn't a clean match for
the pipe-like ideal either, a third data point distinct from both
candidates above: the reader's first `READ` call didn't return for
~12 real seconds (well past when the specific record it was reading had
already been flushed and the writer had moved on to later records),
and — the key fact — `E$EOF` was never returned to the caller during
that wait (a retry counter gated on catching that specific error stayed
at 0 the whole time). This is genuine kernel-level **blocking**, the
opposite of `os9exec`'s immediate-return/poll-yourself behavior, and it
released **all** buffered records at once, timestamped to the same real
second the writer's path closed. Best read as "the reader blocks for
the writer's entire remaining lifetime, then everything unblocks at
once when the writer's path closes" — closer to the "locked out until
the writer exits" fallback than to "unblocks promptly on each write,"
but critically it *does* eventually deliver everything correctly, which
`os9exec` does not. **Note the asymmetry with case 1 above: this same
NitrOS-9 codebase gets case 2 right and case 1 wrong**, while `os9exec`
gets case 1 right and case 2 wrong — so neither reimplementation is
"the more correct one" in general; treat each case/platform combination
as independently verified, not as evidence about the other three. Full
investigation:
`test/6809-live-verification/dogfood-report-eoflock-6809-2026-07-18.md`
(in the `os9exec` repo).

**Follow-up `Live` (2026-07-18) sharpens/revises the paragraph above: the
~12-second block was a small-file artifact, not evidence that CLOSE is the
only release trigger.** The original run's file was tiny (13 records, well
under one 256-byte RBF sector); a repeat with a much larger file (50
fixed-80-content-byte records, 4050 bytes on disk once BASIC09's
sequential `WRITE` trailing-CR delimiter is counted, ~15.8 sectors) —
writer bulk-writes all
50 records fast, then deliberately holds the path open-but-idle for a real
~10-second pause before closing — shows a concurrently-opened reader
reading the large majority of already-flushed records (46 of 50, in both of
two clean runs) **live, incrementally, well before the writer's close**,
while the writer was merely holding the path open and producing no further
data. Only the last few records (47-50 both runs) blocked, and that block
released exactly at CLOSE, with `retries=0` throughout (still a genuine
kernel wait, not polling). Read together, the two file sizes show: a reader
**can** see already-flushed data through a live writer's EOF lock — it
isn't held for the writer's whole lifetime — but once it catches up to the
true current end of file (the writer has stopped producing, nothing more
to flush), it correctly stalls right at that live edge until the next
event that moves the edge, which for an idle-but-open writer is only its
own CLOSE. This is much closer to the pipe-like design intent's actual
promise than the small-file run alone suggested; the small file simply
never accumulated enough buffered/flushed data for the reader to ever get
ahead of the write-in-progress tail, so every one of its reads landed on
that same trailing, not-yet-visible edge, making the whole run look like a
single close-gated block. The exact granularity of "already flushed vs.
still trailing" (RBF sector boundary vs. some other buffer threshold, e.g.
in BASIC09's own I/O layer) is not resolved further here — flagged for
whoever looks at RBF's or BASIC09's actual buffering code next. Full
investigation:
`test/6809-live-verification/dogfood-report-eoflock-6809-largefile-2026-07-18.md`
(in the `os9exec` repo).

## File Security

Every file open checks access permission on every directory in the
pathlist plus the target file itself — no read permission on a directory
means nothing under it is reachable, regardless of the target file's own
permissions. One gotcha for a file-manager author porting or debugging
security logic: `FD_OWN` is nominally a 2-byte owner-ID field, but RBF only
ever compares the **low-order byte** of both group and user ID from the
password file — a user with ID 256 (or group 256) collides with ID 0,
which RBF treats as the super-user. Also note that a file manager module
itself, like a driver, must be owned by super-user with the system-state
attribute bit set, or OS-9 refuses to load it.

## Device-Independence in Practice

The whole reason this layer exists: a program's `I$Read` call is identical
whether the underlying device is a disk (RBF), a terminal (SCF), a tape
(SBF), or a pipe (PIPEMAN) — the *file manager* is what's actually
different per device class, not the application-facing system call.
PIPEMAN in particular needs no physical device at all: a pipe's path
descriptor uses a null driver, backed by a plain FIFO memory buffer
(default 90 bytes) rather than any hardware. When writing a new file
manager, the 13-entry table above is the complete contract the kernel
expects; everything below that (how "Seek" or "Read" map onto your
protocol) is entirely up to the implementation.

---

**Sources:** OS-9 v2.4 Technical Reference Manual and Technical I/O Manual
v2.4 (file-manager entry points, GetStat/SetStat dispatch, path descriptor
structure); Disk File Organization manual (RBF disk structure, record
locking, raw I/O, file security) — cross-checked against The OS-9 Guru and
OS-9 v2.4 Technical Reference Manual for pipes. See `device-drivers.md` in
this skill for the driver side of the same layered model. The File
Descriptor Sector table's `FD_LNK` row is confirmed against both the Disk
File Organization manual's own field table (Figure 7-2)
and an independent 1985-era OS-9/68000 technical manual, which
independently list the same 1-byte link-count field at offset $08.
