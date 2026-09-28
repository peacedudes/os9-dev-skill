# OS-9 Kernel Internals

Baseline `Manual`, cross-referenced across multiple manuals.

**Authority ceiling on the Process Descriptor offsets.** The field *offsets*
here are not published in any authoritative Microware manual in this corpus:
the 68k manuals describe the process descriptor only in prose (state,
priority, paths, memory list), and the one `P$` offset table that exists — in
the 6809 *System Programmer's Manual* — is the 6809 descriptor, a different
and smaller layout. These offsets trace to the Guru book (Dayan;
third-party, so not Microware's word) as reflected in os9exec's
reconstructed `procid` struct, against which they are `Source`-confirmed
byte-for-byte. Microware manuals and the Guru corroborate the field *names
and semantics* (`P$SigLvl`, `P$Signal`, `P$State`), but the numeric offsets
rest on a third-party foundation — the strongest tier available here, and not
Microware-authoritative. Real hardware or a Microware internal header would
lift it.

**System Global Memory** is `Manual` only, because there is no source here
to check it against: os9exec keeps no in-memory System Globals. Its
`F$SetSys` answers each `D_*` offset it models from its own state, which
covers most that programs read, but an answer is not a mechanism:
`D_MinPty` and `D_MaxAge` are merely stored and echoed back, and nothing
schedules by them. The scheduler algorithm below is OS-9's; os9exec schedules
its own way (see the last section of this file). `Source` (os9exec). Two
System Global values are also `Source`: os9exec's 16-byte minimum allocation
unit and 100Hz default tick rate agree with OS-9's documented values. The
**Module Directory** entry shape (address / group / size / link-count) is
`Source`, matching os9exec's structure; os9exec simplifies module groups (its
group field holds the module's own address rather than the first module
loaded from the same file), so its group behaviour is no evidence about
OS-9's.

Structures and algorithms below the level any ordinary I$/F$ call exposes —
relevant if you're inspecting/modifying kernel state directly, writing a
`Procs`-style utility, or working on `os9exec`'s own emulation of the
kernel. OS-9 ships two kernel variants per processor: a standard kernel
with full development facilities, and a smaller/faster "atomic" kernel
aimed at embedded systems that trade away development conveniences for
execution speed — the internals below apply to both unless noted.

## System Global Memory (~8KB, resident at RAM base)

Contains, roughly in order: the exception dump table (64 bytes, one entry
per hardware exception, populated when one fires), the `D_*`-prefixed
system global variables (`D_MinPty`, `D_MaxAge`, etc. — see below), the
process descriptor table, the path descriptor table, the module directory,
and the active/waiting/sleeping process queues. `F$SetSys` reads or writes
individual system globals by offset (superuser only for writes; the MSB of
`d1.w` selects read-vs-write).

A few offsets a process actually reads at run time: `D_SPUMem` ($3D8), the
System Security Module's static storage, is read by every Microware-C start-up
to detect an SSM, and a machine without one shows 0 -- which is what os9exec
returns (`Live` (os9exec)). `D_Julian` ($30) is today's Julian day.

**`D_Second` ($34) counts the seconds LEFT UNTIL midnight — the opposite of
`F$Time`'s Julian form, which gives seconds since.** The Guru states it twice,
once with the reason: the tick handler only has to decrement it and test for
zero to know the day has turned. Two freeware programs written for real
OS-9 agree: `getsys` labels the field "system time seconds
left until midnight", and `aprocs` computes process ages on that assumption.
Microware's v2.4 manuals document `F$Time`/`F$STime`, which are the syscalls,
not this global, so they do not bear on it. Convert with `86400 - D_Second`
before comparing it to anything stated as seconds since midnight — a process
descriptor's `P$TimBeg`, or `F$Time`'s `d0`.

Getting the direction backwards is expensive and easy to recognise: with
`D_Second` answered as seconds *since* midnight, `aprocs` reported every process as roughly 2³²
seconds old (`1193028:33:46`, a small negative difference wrapped) while
Microware's `procs -e` said `Age 0:00`. `Live` (os9exec). **If `aprocs` ages every process
by about 2³² seconds, suspect whatever sets `D_Second` — a clock driver, say —
before anything else.**

Exception vector 0 holds the reset-time initial supervisor stack pointer
(SSP) value — every subsequent exception dispatch uses this vector to
relocate the base address of system global storage, which is why at least
4K of RAM must exist both below and above it. Vector 1 holds the reset
initial PC (the coldstart entry point); after startup its only remaining
use is restarting the system after a catastrophic failure. Neither vector
should be touched by ordinary code.

## Process Descriptor (one per process, allocated dynamically)

Tracks: process ID, group/user ID, priority, current state (Active /
Waiting-for-child / Sleeping), memory allocation pointers (code and data
areas), the open-path list, the signal-intercept routine pointer and its
nesting level (`P$SigLvl`, an unsigned byte incremented/decremented/cleared
by `F$SigMask`; while nonzero the intercept routine is not invoked, and
overflow past 255 / underflow past 0 is silently ignored), the
exception-trap table, pointers to the primary module and any linked
modules, and saved register/stack state. `F$GPrDsc` retrieves a copy of a
specific process's descriptor by PID; `F$GPrDBT` retrieves the whole
process descriptor block table (what the `procs`/`iprocs` utilities use to
list running processes).

`P$PModul` (the pointer to a process's primary module) must be a valid
address, because a monitor reads the descriptor and follows it to the module
header to print the module name -- `devprc -a`, `top`, `sysmon` and `aprocs`
all do. (os9exec's kernel process reports 0 here; see `os9-dev`'s
`common/using-os9exec-repl.md`, "What os9exec does not implement".)

**When a process was forked: `P$DatBeg` ($2BC) and `P$TimBeg` ($2C0).** The
first holds the Julian day number, the second the seconds **since** midnight —
the same form as `F$Time` with `d0.w=1`, and not the countdown `D_Second` uses.
`F$AllPrc` stamps them from the system clock when it allocates the descriptor.
A process that wants its own start time, or the machine's uptime, reads its
descriptor with `F$GPrDsc` and combines the two with a Julian-mode `F$Time`;
Microware's `rstatd` works out boot time for `rup` this way (`Live`
(os9exec), seen in a syscall trace). Offsets and formats come from the Guru
only (see the authority ceiling above): unconfirmed against Microware, and a
monitor that turns out wrong should suspect them first.

- **Process descriptor table**: an array of process-descriptor addresses; a
  process's ID is literally its index into this table (a zero entry means
  that ID is unused/free). The table starts small and the kernel doubles
  its size whenever it fills — so a PID's numeric value can vary run to
  run and should never be hardcoded.
- **Memory-area ceiling**: a process may dynamically hold at most 32
  separate memory areas total, counting its initial static storage and
  stack; the kernel tracks every one for automatic cleanup at exit.
  Contiguous areas are merged where possible specifically to make the most
  of this 32-entry ceiling.
- **Signal-intercept state save**: entering an intercept routine
  auto-masks signals (`P$SigLvl` set to 1). The non-recursive fast path
  saves one full register image (72 bytes covering all MPU registers, 168
  bytes if the FPU is active) in system state; a recursive intercept call
  instead pushes its saved state onto the user stack.

## Path Descriptor (one per open file/device)

Tracks the path number, access mode, current file manager and driver in
use, and file-manager/device-specific option fields. See
`file-managers.md` in this skill for the detailed three-section layout
(universal section / file-manager-specific section / 128-byte option
area) and the `PD_COUNT` share-counter mechanics — this is the same
structure, described there from the file-manager author's side of the
same fence.

## The Scheduler Algorithm

**This section is OS-9/68000.** OS-9/6809 schedules differently — it really
does age each queued process individually, via a per-descriptor `P$Age` field
(`Source`, NitrOS-9 `faproc.asm`; see the `F$AProc` row in the `os9-dev`
skill's `6809/syscalls-and-module-format.md`). The two are not versions of one
description, so neither account should be used to "correct" the other.

On 68k, OS-9 implements priority-plus-age scheduling through a single
**system-wide** counter — **not** a value ticked up on each waiting
process individually (a misreading that is easy to arrive at, not least
because it *is* how 6809 works). The
System Globals field `D_ActAge` ("system age") is a 32-bit value,
initialized to `$7FFF0000`, and the kernel **decrements it by one** at the
start of every `F$AProc` call — i.e., every time *any* process is inserted
into the active queue (a fresh fork, a signal delivery, a satisfied wait
condition, or the current process being re-queued when its time slice
expires). When a process is inserted, the kernel computes a **scheduling
constant** — ordinarily `priority + (the just-decremented) D_ActAge` — and
stores it in the process descriptor's `P$Sched` field; the active queue
stays sorted by this value, with the highest constant at the head. Once
set, a process's own `P$Sched` is **not** recalculated while it waits —
only new insertions consume the next (lower) system-age value, which is
what makes a process that has been waiting through many other insertions
look progressively more favorable relative to newer arrivals at the same
priority. (The literal per-process increment does happen in one specific
case: if `D_ActAge` itself decrements below zero, it resets to
`$7FFF0000` and every process currently in the active queue has its
scheduling constant recalculated at that point — not on every ordinary
insertion.) A separate, purely informational "age" value — `P$Sched` minus
the current `D_ActAge` — is computed on demand by `F$GPrDsc` for tools like
`procs`; it plays no role in scheduling itself and is clamped to `-1`
(`$FFFF`) if the computed value looks unreasonable (over 10000).

Two system globals tune this behavior:

- **`D_MaxAge`** (writable by superuser via `F$SetSys`, normally zero)
  defines a **priority threshold, not an age cap**: a process whose
  priority is at or above it gets its scheduling constant computed as
  `priority + $80000000` instead of `priority + D_ActAge` — a value the
  aging counter never touches, so members of this upper tier are ordered
  strictly by raw priority among themselves, with no aging effect at all.
  As a whole, this upper tier preempts and completely starves every
  process below the threshold for as long as any upper-tier process stays
  active — a genuinely active high-priority workload monopolizes the CPU
  rather than "waiting its turn" against lower tiers. Setting `D_MaxAge` to
  1 pushes essentially every process into the upper tier, producing strict
  priority-only scheduling with aging effectively switched off system-wide.
- **`D_MinPty`** (normally zero) sets a hard priority floor. A process
  below it gets a scheduling constant of exactly zero instead of the
  normal calculation, which places it at the tail of the queue; once the
  head of the queue has a zero scheduling constant the kernel treats the
  active queue as empty and halts, so such a process effectively never
  runs. Raising it temporarily creates a frozen tier, useful for critical
  real-time sections (often used by `F$SSpd` to implement process
  suspension by making a process unreachable to the scheduler). **Setting
  `D_MinPty` above every task's priority halts the system** — the kernel
  becomes locked in an idle-wait state waiting for an interrupt that will
  never free it; only hardware reset recovers. Restore `D_MinPty`
  immediately after your critical section finishes.

Processes with equal priority rotate time slices among themselves (round-robin at
that level). The real-time clock (typically 100Hz on 68k systems, but
configurable) drives timeslicing; one time slice spans **two clock ticks (~20ms)**
rather than one. A process that preempts a lower-priority one doesn't start
its own fresh slice — it gets only whatever was left of the preempted
process's slice, with the clock continuing from where it stood.

**User state is preempted; system state is not.** User code is interrupted by
the clock when its slice expires — that is what makes the timeslicing above
mean anything, and it is why a read-modify-write cycle can genuinely be cut in
half by another process on real hardware. System-state code (kernel calls and
I/O operations mid-call) is never preempted mid-operation: it must complete or
voluntarily sleep/yield, to protect kernel data-structure consistency.

## Module Directory Internals

The module directory is a kernel-maintained table, one entry per loaded
module, tracking: the module's memory address, a **link count**, a
**group identifier** (the memory address of the first module loaded from
the same file — see "module groups" below), and a parity check value.
Lookup compares a requested name against each candidate module header's own
name field (see `os9-dev`'s `common/module-format.md` for the header layout
itself).

Link-count lifecycle (`F$Link`/`F$Load`/`F$UnLink`, the sticky-bit
exception, `F$Exit` only auto-unlinking a process's *primary* module),
module-group membership, revision-driven (`M$Revs`) substitution, and the
`E_NEMOD` type/language-mismatch behavior on fork/chain are the same facts
documented from the application side in `os9-dev`'s `common/module-format.md`
("Module directory mechanics") and `common/os9-mental-model.md`
("Module directory lifecycle") — not restated here. One reasoning
detail worth adding at the kernel level: **module groups exist because
merged modules in one file aren't necessarily page-aligned individually**
— keeping the group intact keeps the underlying contiguous memory block
valid for the memory manager, which is why the group only frees once
every member's combined link count is zero.

- **Type/language matching is per-*field*, with 0 = wildcard — not a
  whole-word compare** (`Live` (os9exec)). The requested type/language
  is a word: high byte = type, low byte = language. The kernel matches the
  two bytes **independently**, and a zero in either field means "any"
  (`MT_ANY` / `ML_ANY`, both 0, as os9exec names them). So
  `$0200` requests "a *subroutine* module, *any* language" and legitimately
  matches a `$0202` subroutine / BASIC09-I-code module. This is exactly how `RunB` links a packed BASIC09
  procedure without hard-coding its language sub-code — and the reason a
  naïve `requested == actual` full-word comparison is wrong: it rejects the
  match and the resident module looks "not found." (The symptom of such a
  comparison: a *loaded* packed module is invisible to `F$Link`, RunB falls
  back to `F$Load`, and execution comes to depend on the current directory.
  See os9-dev `basic09/pack-and-runb.md` for
  the application-side view.)
- **`F$Load`'s access mode is a *byte*, `d0.b`, and it chooses the
  directory.** The v2.4 Technical Manual: the mode "may be specified as
  either Exec_ or Read_, causing the file to load from the current execution
  or data directory, respectively" (`Manual`); bit 7 of `d0.b` only says
  whether `d1.l` carries a memory colour. `Live` (os9exec): `$01` (`Read_`)
  resolves a relative name in the data directory; `0`, `$80` and modes with
  `Exec_` use the execution directory; `$0401` and `$FF01` behave as `$01`.
  RunB's module lookup searches `chx` (application side in os9-dev's
  `basic09/pack-and-runb.md`; the F$Load row of `68k/syscall-reference.md`).
  The point worth adding for kernel/emulator work specifically: reading the
  mode as a full word flips the decision, because RunB leaves its
  type/language in the high byte (`Source`: os9exec's F$Load, which masks to
  `d0.b` for that reason).

### Header Integrity: Parity and CRC

Two independent checks protect a module, checked at different times:

- **Header parity** (`M$Parity`, offset `$2E`): one's complement of the
  word-by-word XOR of every preceding header word. XORing all header words
  including parity yields `$FFFF` on an intact header. Checked at module link
  time; mismatch returns `E$BMHP`.
- **Module CRC**: 24-bit CRC over the entire module body (header through the
  byte before the CRC field), computed once when first entered into the directory
  (ROM coldstart scan or RAM load) and **not re-verified on subsequent use** —
  an in-memory module can theoretically drift from its on-disk state without
  detection. Where the body's length would leave the total odd, the linker pads
  it with a single zero byte before the CRC field (68000 instructions require
  even addresses).

### Boot-Time Module Discovery

On reset/coldstart, the kernel scans ROM (and the boot file) word-by-word
for the sync bytes `$4AFC` — deliberately an illegal 68000 instruction, so
scanning is cheap and unambiguous. On a hit, it verifies header parity,
reads the module's size from the header, computes its CRC, and — if both
checks pass — enters it into the module directory. This is how every ROMed
module (system and user-supplied alike) ends up automatically linked and
already present in the directory before user code ever runs. Only after
this population phase does coldstart link the INIT configuration module,
initialize kernel tables/paths/directories, and fork the initial process
(`SYSGO`).

## Trap Handler Mechanics

A trap handler module (type `TrapLib`) is installed via `F$TLink`, which links
to the module, allocates **private static storage** for that handler, and runs
its one-time initialization entry point. (Subroutine modules have no private
static storage.) A process may link at most 15 trap modules simultaneously,
matching the 15 available user trap vectors (33-47, `TRAP #1`-`#15`). Trap
module code executes in the CPU state its module attributes declare, regardless
of the calling process's state.

A trap module exposes three named entry points: **`TrapInit`** (run once per
process that links to the module, for setup), **`TrapEnt`** (the actual
handler invoked on each `tcall`), and **`TrapTerm`** (reserved for per-link
teardown; not implemented in this era's OS-9 releases). Assembly code
normally reaches a trap handler through the `tcall` macro: it accepts a
pair of word-sized arguments — trap vector number (1-15) and a
function-selector word — expanding to the appropriate `TRAP` instruction.

**Lazy binding**: a `tcall` made before `F$TLink` has installed the target
handler checks the module's `M$Excpt` (default trap entry) offset — zero
aborts the call, non-zero jumps to that exception routine, which installs
the handler and re-executes the original `tcall`. This lets a program defer
a trap handler's linkage until it's actually needed at runtime.

## Memory Allocation Internals

- **Minimum allocation unit**: 16 bytes — the smallest chunk OS-9's
  free-list bookkeeping can track; every free region is linked via a
  16-byte controlling structure at its start.
- **Minimum *allocatable block* size** is larger and depends on whether
  memory protection is in play: on an MMU-equipped system it typically
  matches the MMU page size (e.g. 4K), since the kernel grabs whole
  physical pages and subdivides them internally; without inter-task memory
  protection it defaults to 256 bytes instead. Either way this is larger
  than the 16-byte logical unit above — the kernel manages free fragments
  *within* these larger blocks to avoid wasting a whole block/page on a
  small request.
- **First-fit strategy**: the allocator takes the first free block large enough
  rather than searching for best-fit. Fragmentation without an MMU stays rare
  unless the system is severely memory-constrained or allocates very large blocks.
- **Buddy-system allocator**: a second allocation scheme that splits/merges
  power-of-2-sized blocks instead of maintaining fragment lists. Under MMU
  protection, `D_MinBlk` must equal the MMU page size for buddy blocks to map
  cleanly onto whole pages.
- **Colored memory**: address space partitioned into distinct regions (e.g.
  battery-backed non-volatile RAM, cache-friendly regions, DMA-accessible areas).
  A data module or allocation request can be steered into a specific region via
  color tags rather than using the default allocator placement.
- **DMA and MMU address translation**: on MMU-equipped systems, DMA transfers
  from a user buffer require explicit address translation (DMA hardware does not
  respect virtual-to-physical mappings). OS-9 provides translation services; a
  driver on such a system must not pass raw user virtual addresses to the controller.
- OS-9 does not require an MMU for basic operation — register-indirect
  addressing provides process isolation without it. A System Security Module
  optionally adds an MMU for memory *protection* on top of that baseline.

## Exception and Interrupt Vector Layout

- Vector 0/1: reset SSP/PC (see System Global Memory above).
- Vectors 2-5: CPU hardware error exceptions — bus error (`T_BUSERR`,
  access to non-existent/privileged memory), address error (`T_ADDERR`,
  misaligned access), illegal instruction (`T_ILLINS`), zero divide
  (`T_ZERDIV`). All dispatch through `F$STrap` and are fatal to the
  offending process by default (unconditional termination) unless it
  installed a handler; a process created via `F$DFork` instead keeps its
  resources intact for post-mortem debugger examination rather than being
  torn down.
- Vector 9: trace exception (set by `F$DFork` to put a debug child under
  single-step control; also what the OS-9 debugger uses generally).
- Vectors 25-31: the seven auto-vectored interrupt levels (1-7), serviced
  through `F$IRQ` identically to vectored interrupts; level 7 is
  non-maskable.
- Vector 32: the `TRAP #0` OS-9 system-call entry point (F$/I$ dispatch).
- Vectors 33-47: user trap vectors 1-15 (`F$TLink` installs handlers here;
  see Trap Handler Mechanics above).
- Vectors 64-255: 192 ordinary vectored (non-auto) interrupts, registered
  via `F$IRQ`; multiple devices may share one.

Hardware error exceptions are normally fatal to the offending process
unless it installed a handler via `F$STrap` — the handler runs in user
state with registers already stacked, and must either fix up and continue
or terminate. `F$STrap` takes a handler stack and a service table pairing
exception vectors with handler routines; the installable set is the CPU
error/trap group (bus and address error, illegal instruction, zero-divide,
CHK, TRAPV, privilege, plus the line-emulator and co-processor traps). It is
one of the least-travelled parts of the ABI — ordinary code tests an operand
before dividing rather than catching the hardware trap — so its handler-entry
conventions were thinly documented from the start. One 68k subtlety a resuming
handler must respect: **bus and address errors push a longer CPU exception
frame** than the other vectors (they add fault-address and status-word fields —
roughly 8 extra bytes on the 68010 and later), so the saved state a handler is
handed is not the same size for every exception. An interrupt service routine, by contrast, runs in **system
state with no current-process context** — it's servicing the CPU, not
"running as" any particular process, which is why an ISR has such a
restrictive register-preservation contract (see `device-drivers.md`).

## os9exec's scheduler and idle loop — for work on the emulator

Everything above describes OS-9. This section describes os9exec's
implementation instead (`Source` (os9exec)), for anyone extending its kernel
layer; none of it is evidence about OS-9. os9exec does **not** implement the
`D_ActAge`/`P$Sched` priority-age machinery; it runs a simpler round-robin in
`do_arbitrate()` (`procstuff.c`).

- **The OS-9 clock is real host wall-clock time** — `GetSystemTick()`
  (`funcdispatch.c`) reads `gettimeofday()` on UNIX (`GetTickCount()` on
  Windows), not a counter incremented by the emulation loop. So blocking the
  host (`nanosleep`, `select`, a syscall) does **not** stall OS-9 time: on
  return, ticks/alarms/sleeps reflect the real elapsed interval. This is what
  makes an idle host-side block safe.
- **Blocked/waiting processes are poll-retried, not event-woken.** A process
  in `pWaitRead`/`pWaitWrite` (a blocked console/pipe read, a parked
  `Ev$Wait`) is re-dispatched by `do_arbitrate` only every Nth round (throttled
  by `pW_age`); it re-runs the syscall and re-checks. The exception is RBF
  record/EOF locks, which do an **explicit** wake of a known in-emulator
  waiter. Host-tty readiness is `select()`-driven in `DoWait` (below).
- **`DoWait()` (`procstuff.c`) is the ONLY code that runs while every process
  is blocked/sleeping** (the fully-idle path `do_arbitrate` drops into when
  nothing is runnable). It is therefore the sole place stdin
  (`CheckInputBuffers()`) and due alarms (`CheckAlarms()`) get serviced while
  idle. Any new "wake a blocked process from a host event" mechanism must be
  serviced here too, not only in the syscall dispatcher.

---

**Sources:** An independent 1985-era OS-9/68000 technical manual (primary
for the scheduler algorithm and vector layout);
The OS-9 Guru (module directory, memory allocation, process
descriptor internals — including the detailed
`F$AProc`/`D_ActAge`/`P$Sched` scheduler walkthrough behind the
system-wide-counter description above); cross-checked against OS-9
Insights (editions 2-3) and the OS-9 v2.4 Technical Reference Manual. (The
rejected per-process
"age by one on each arrival" description conflicts with that walkthrough —
the real mechanism is a single decrementing system-wide counter plus
a per-process scheduling constant fixed at insertion time).
