# OS-9/68000 System Call Reference

68k-specific: TRAP #0 dispatch and 68000 register conventions. The 6809
equivalent (SWI2 dispatch, different codes and registers) is
`6809/syscalls-and-module-format.md`; C-library wrappers are in
`c/os9-clib-reference.md`.

**Scope: user-mode calls** — the manual's Chapter 15 I/O plus user-state F$.
Chapter 16 system-mode requests (`F$Move`, `F$SLink`, `F$SSvc`, `F$SetSys`,
`F$AllPD`/`F$AllPrc`/`F$AProc`/`F$NProc`/`F$FindPD`/`F$RetPD`, `F$IRQ`,
`F$GPrDsc`/`F$GPrDBT`, …) are kernel-internal and belong to the
`os9-systems-dev` skill — deliberately absent here, not overlooked.

Rows tagged `Flag` carry a known cross-manual register-layout conflict.
Verify against a primary manual before coding against exact register slots on
anything not tagged `Live`.

## Calling convention

Execute **TRAP #0** followed immediately by a constant word holding the
function code. **I$** calls route to file managers/drivers; **F$** calls
run in the kernel (some user-state, some system-state/privileged).

```asm
    move.w  path0(a6),d0
    trap    #0
    dc.w    I$Close
    bcs.s   fail
```

The `OS9` assembler pseudo-instruction emits the trap+word pair:
`OS9 I$Close`. A custom trap library is reached the same way via `tcall
T$Math, T$DMul` (expands to `TRAP #<n>` + `dc.w`), for handlers installed
on TRAP #1–#15 via F$TLink.

- Parameters/results in documented D/A registers per call.
- Error: carry set, error code in `d1.w`; test with `bcs`/`bcc`.
- Strings are NUL-terminated, passed by address.
- TRAP #0 (vector 32) is the OS-9 entry; TRAP #1–#15 (vectors 33–47) are
  user trap handlers.

## Process management

| Call | Purpose | Key inputs | Key outputs | Notes |
|------|---------|-----------|------------|-------|
| **F$Fork** | Create process | d0.w=module type (0=any), d1.l=extra stack/mem, d2.l=param size, d3.w=# I/O paths, d4.w=priority, (a0)=module name, (a1)=params | d0.w=child PID, (a0)=updated past the module name | Child inherits priority, open paths, user/group ID, current dirs, environment — never memory. `Live`; contract is the *OS-9/68000 Operating System Technical Manual* (1984) ch. 14. Conflicting passages in *other* Microware manuals are a documentation inconsistency, logged in `DIVERGENCES.md` Part 4 |
| **F$Chain** | Replace current program | as F$Fork `Manual, Flag` | doesn't return | Fork+Exit in one: reuses the caller's process descriptor and PID, preserves open paths. **A failed chain kills the caller** — the caller's image is torn down (unlink, free) *before* the new name is resolved, so a bad name lands on an already-gutted process with nothing left to return an error to; the bare `E$MNF` you see is printed by the kernel, not the program. Faithful to the contract on both os9exec and NitrOS-9 (`fchain.asm`) — do not flag it as a bug. `Live` |
| **F$Exit** | Terminate | d1.w=status | — | Closes paths. Auto-unlinks only the *primary* module and trap handlers — anything else you linked/loaded leaks unless unlinked first. `Live` |
| **F$Wait** | Wait for child | — | d0.w=child PID, d1.w=status | Also reclaims the dead child's process descriptor; forking without matching waits can fill the process table. `Live` |
| **F$SPrior** | Set priority | d0.w=PID, d1.w=priority (0=min, 65535=max) | — | Same-user rule; superuser (group 0) can set any. Shell: `setpr`. `Live` |
| **F$ID** | Get process identity | — | d0.w=PID, d1.l=group.user (packed, group in high word), d2.w=priority | Architecture-general shape — matches 6809's `F$ID`, just wider registers. `Live` |
| **F$SUser** | Set process identity | d1.l=(group:16)(user:16), full 16-bit fields each | — | **Not the same wire format as `F$ID`'s output** — `F$ID` packs group/user into a single word (`group<<8\|user`, one byte each), so feeding `F$ID`'s output straight into `F$SUser` sets the wrong identity instead of restoring it. os9exec applies no permission check here: any process may set itself to any identity. `Live` |
| **F$Sleep** | Suspend process | d0.l=ticks (0=indefinite until signaled, 1=no-op/return immediately, negative=fractional 1/256-sec units, positive=raw tick count) | **⚠ DIVERGENCE D-004** — manual returns d0.l=remaining ticks if woken early; os9exec writes nothing | `Live`. **D-004:** both Microware manuals document a `d0.l` output (68k: "remaining number of ticks if awakened prematurely"; 6809: `(X)` decremented by ticks slept), so a process can learn it was signalled before its time elapsed. os9exec returns without writing `d0.l`, leaving the caller's original count in place. See `DIVERGENCES.md` |

## Module management

| Call | Purpose | Key inputs | Key outputs | Notes |
|------|---------|-----------|------------|-------|
| **F$Link** | Link resident module | d0.w=type/language byte (0=any), (a0)=name | d0.w=type/language, d1.w=attr/rev, **(a0)=updated past the module name**, (a1)=entry, (a2)=header | Increments link count, no disk I/O; needs read permission. `Live` |
| **F$Load** | Load from file | d0.b=access mode, d1.l=memory "color" type (optional — documented in the v2.4 Technical Manual (1994), absent from the 1984 one, so a later addition rather than a disagreement), (a0)=pathname | d0.w=type/language, d1.w=attr/rev, **(a0)=updated beyond the path name**, (a1)=entry (of the *first* module loaded), (a2)=module pointer | Registers every module in the file (a "module group" — resident until the group's combined count is zero), then links. `Live` |
| **F$UnLink** | Unlink by address | (a2)=header | — | Free at zero unless sticky (bit 6) — sticky needs count −1 or memory pressure. A module that was loaded *and* linked needs one call per link to fully free. `Live` |
| **F$UnLoad** | Unlink by name | (a0)=module name | (a0)=updated | The declared `d0.w` (type/language) input is accepted but never read by os9exec — it looks the module up by name alone. `Live` |
| **F$SetCRC** | Update module CRC | (a0)=module | — | Recomputes CRC + header parity after in-place modification (data modules); required before saving to disk. Rejects a non-header address with `E$BMID` (205) rather than trusting its input. `Live` |
| **F$CRC** | Compute CRC | d0.l=count, d1.l=accumulator (init $FFFFFFFF), (a0)=data | d1.l=updated | 24-bit, one's-complemented for storage. Kernel checks once at load/bootstrap, never re-verifies. `Live` |
| **F$DatMod** | Create/link data module | d0.l=size, d1.w=attr/rev, d2.w=access, d3.w=type/lang, d4.l=color, (a0)=name | d0.w=type, d1.w=attr, (a1)=data, (a2)=header | Named shared memory: creator sizes it, later callers link by name. No kernel synchronization — coordinate with events/signals. `Live` |

## Memory

| Call | Purpose | Key inputs | Key outputs | Notes |
|------|---------|-----------|------------|-------|
| **F$SRqMem** | Request system memory | d0.l=size (rounded up to 16 bytes; `$FFFFFFFF`=request the largest available block) | d0.l=actual size, (a2)=block pointer | `Live` |
| **F$SRtMem** | Return system memory | d0.l=size, (a2)=block pointer | — | Must pass back exactly the size `F$SRqMem` returned, or the block silently isn't freed. `Live` |
| **F$SRqCMem** | Request colored system memory | d0.l=size, d1.l=color | d0.l=actual size, (a2)=block pointer | Shares `F$SRqMem`'s handler on os9exec; the color parameter is accepted but never read, so it has no effect there. `Live` |
| **F$CpyMem** | Copy memory across a process boundary | d0.w=PID of external memory's owner, d1.l=count, (a0)=source, (a1)=destination | — | The declared `d0.w` owner PID is accepted but never read — correct: OS-9 lets a user-state caller READ any source address and never validates it against the owner PID. The DESTINATION is what's checked (F$ChkMem's job): a write is allowed only into the caller's own data/blocks or a loaded RAM module, else `E$BPAddr`. os9exec has no SPU, so it models *with-SPU* protection and is deliberately stricter than bare-hardware OS-9, where F$ChkMem without an SPU is largely a no-op. `Live` |

## I/O

| Call | Purpose | Key inputs | Key outputs | Notes |
|------|---------|-----------|------------|-------|
| **I$Attach** | Attach device | d0.b=mode, (a0)=device name | (a2)=device-table entry | Exact port/manager/driver/descriptor match increments use count; same port+code but different descriptor makes a "synonymous device"; no match allocates static storage and calls the driver's INIT (a failed INIT is rolled back via TERM, no entry left) |
| **I$Detach** | Detach device | (a2)=entry | — | At zero use count, calls TERM and frees storage unless shared. Superuser only |
| **I$Open** | Open path | d0.b=mode, (a0)=pathname | d0.w=path number, (a0)=updated past the pathname, **trailing spaces skipped** | Allocates a path descriptor (share count 1). Opening a directory requires the directory bit (0x80) in the mode. `Live` |
| **I$Create** | Create file | d0.b=mode, d1.b=attrs, d2.l=size hint, (a0)=pathname | d0.w=path | On non-multi-file devices behaves as I$Open. `Live` |
| **I$Close** | Close path | d0.w=path | — | Decrements share count; descriptor freed at zero. F$Exit closes leftovers. `Live` |
| **I$Read** / **I$Write** | Raw transfer | d0.w=path, d1.l=count, (a0)=buffer | d1.l=transferred | No editing — a bare CR alone does not advance the terminal; CR+LF is needed. Reads return EOF error when exhausted; writes past EOF extend the file (RBF may pre-read a sector for partial-sector writes). `Live` |
| **I$ReadLn** / **I$WritLn** | Line transfer | same | same | Stop at first CR; apply device line editing (SCF: backspace/echo on input, LF append on output; 512-byte line buffer). The returned count includes the CR. `Live` |
| **I$Seek** | Position | d0.w=path, d1.l=position | — | Logical only; past-EOF legal; non-random devices no-op; doesn't touch record locks. `Live` |
| **I$Delete** | Delete file | d0.b=mode, (a0)=pathname | (a0)=updated past the pathlist | Multi-file devices only. `Live` |
| **I$MakDir** | Create directory | d0.b=mode, d1=access permissions (permit bits live in the low byte), **d2.l=initial allocation size (optional)**, (a0)=pathname | (a0)=updated past the pathname | Managers without directories return unknown-service. `Live` |
| **I$Dup** | Duplicate path | d0.w=path | d0.w=new path | Only bumps the existing descriptor's share count — file manager/driver never called. `Live` |
| **I$ChgDir** | Change a current directory | d0.b=mode (what `chd`/`chx` invoke with data vs. execute mode), (a0)=pathname | (a0)=updated past the pathname | `Live` |
| **I$GetStt** / **I$SetStt** | Status get/set | d0.w=path, d1.w=code, … | per code | File manager handles known codes, forwards unknown ones to the driver. Known: SS_Opt (128-byte option area), file size (C code 2), SS_Lock (record lock), SS_Ticks (lock timeout). **`I$GetStt`/SS.Size (code 2) returns its result in `d2.l`, not `d1`.** `Live` |

## Events (F$Event subfunctions)

One counter primitive covers mutex + condition variable + counting
semaphore (see `common/ipc.md`). **F$Event** = `$53`; the subfunction is in
`d1.w`. Function codes: Ev$Link=`0`, Ev$UnLnk=`1`, Ev$Creat=`2`,
Ev$Delet=`3`, Ev$Wait=`4`, Ev$WaitR=`5`, Ev$Read=`6`, Ev$Info=`7`,
Ev$Signl=`8`, Ev$Pulse=`9`, Ev$Set=`$0A`, Ev$SetR=`$0B`.

**Register contracts** (`Live`):

- **Ev$Creat**: a0=name, d0.l=initial value, d1.w=2, d2.w=wait-increment,
  d3.w=signal-increment → d0.l=event ID. `E$EvBusy` if the name exists.
- **Ev$Link**: a0=name, d1.w=0 → d0.l=event ID (`E$EvNF` if not created yet).
- **Ev$Wait**: d0.l=event ID, d1.w=4, d2.l=min, d3.l=max → **blocks** until
  `min ≤ value ≤ max`, then adds the wait-increment and returns the new value
  in d1.l. A bad event ID returns `E$EvntID` immediately.
- **Ev$Signl**: d0.l=event ID, d1.w=8 — adds the signal-increment to the
  counter. It only bumps the value; it does **not** explicitly wake a waiter.
- **Ev$Delet**: a0=name, d1.w=3 (by name, not ID).

A blocking wait is woken cross-process (`Live`): process A parks on an
out-of-range Ev$Wait, process B does Ev$Link + Ev$Signl to push the counter
into range, A wakes and returns. Since Ev$Signl performs no wake, on os9exec
the release comes from re-dispatching the parked process to poll-retry the
wait. Exercising this needs two processes, and the signaller must retry
Ev$Link — the waiter has to Ev$Creat first, which is a startup race.

**os9exec implements only Link/UnLnk/Creat/Delet/Wait/Signl.** The other six
— Ev$WaitR, Ev$Read, Ev$Info, Ev$Pulse, Ev$SetR, Ev$Set — fall through to
`E$UnkSvc`. Real OS-9 has them; don't assume they work here.

## Alarms

**F$Alarm** (d0.l=alarm ID, d1.w=function, d2.l=signal, d3.l=interval,
d4.l=date): subfunctions A$Delete=0, A$Set=1 (one-shot), A$Cycle=2
(periodic), A$AtDate=3 / A$AtJul=4 (absolute Gregorian/Julian). `Live`.

Time-of-day alarms fire at the *corrected* time after a clock adjustment. A
system-state variant runs a kernel subroutine instead of signaling; pending
alarms die with their process, so a persistent one must be requested as the
system process. A firing alarm wakes its own process out of `F$Sleep`,
including an indefinite `F$Sleep(0)`.

## Signals & traps

| Call | Purpose | Notes |
|------|---------|-------|
| **F$Send** | Send signal to a process | **d0.w=receiver PID (0=all), d1.w=signal code**. Kill (0) restricted to same user/group (superuser excepted); other codes unrestricted. PID 0 broadcasts to all same-user/group processes except the sender. Signals queue in send order, at roughly 10× the cost of unqueued delivery. `Live` |
| **F$Icpt** | Install signal intercept routine | On entry the kernel puts the count of queued signals in d0.w (1 = nothing else waiting). No handler installed ⇒ any interceptable signal kills the process. `Live` |
| **F$SigMask** | Mask delivery | d1 = +1 increment / −1 decrement / 0 clear-to-zero. Counter is P$SigLvl (unsigned byte); over/underflow silently ignored. F$Sleep unmasks internally, making `mask → sleep(0)` a safe masked wait. `Live` |
| **F$SigReset** | Reset intercept-nesting counter | Needed when `longjmp()` bypasses F$RTE exits |
| **F$RTE** | Return from intercept | Processes queued signals first |
| **F$STrap** | Install error-exception handler | (a0)=stack, (a1)=service table. Covers bus/address/illegal/zero-divide etc. (vectors 2–8, 10–24, 48–63), otherwise fatal. Handler gets all user registers stacked and chooses resume point. An F$DFork child's resources survive for post-mortem. `Live` |
| **F$TLink** | Install trap handler | d0.w=trap 1–15, d1.l=memory override, (a0)=module name → **(a0)=updated past module name**, (a1)=entry, (a2)=header. **Passing (a0)=0, or a name string whose first byte is 0, *unlinks* the handler on that vector** (manual, ch. 14). Links a TrapLib, allocates private static storage, runs its init. Max 15 per process (one per vector); a `tcall` before install can lazily self-install via the module's M$Excpt entry. `(a0)` must be a module *name*, resolved via the same exec-directory search as `F$Link`/`F$Load`, not a bare filename in the data directory. `Live` |
| **F$Sema** | Kernel binary semaphore | OS-9 **v3.0+** only — absent on the v2.4 baseline documented here |

os9exec detail worth knowing when hand-building a trap module: `_midata`/
`_midref` at 0 are **not** read as "no init table" — `prepData` parses a table
at that offset unconditionally, so a module with no init data needs a real
empty table there (dOff=0, cnt=0, then two 0-terminators) or the load fails
`E$BMID`.

## Time

**F$Time** (d0.w=mode: bit0 0=Gregorian/1=Julian, bit1 set=also return
ticks) → d0.l=packed time, d1.l=packed date, d2.w=day of week (0=Sunday),
d3.l=tick rate/current tick if requested. `Live`. **68k returns everything
directly in registers — there is no 6809-style 6-byte buffer pointer.** The
packed field layout inside `d0.l`/`d1.l` is not decoded here; only the
register-slot convention is confirmed.

**F$STime** (d0.l=time, d1.l=date — the input-side mirror of `F$Time`'s
output shape). `Live`. On os9exec's modern macOS/Linux/Windows builds it does
not touch the host clock at all.

**F$Julian** (d0.l=time as `00hhmmss`, d1.l=date packed as
`(year:16)(month:8)(day:8)` — **not** decimal-digit "yyyymmdd" despite that
doc naming) → d0.l=seconds since midnight, d1.l=Julian day number.
**F$Gregor** is the inverse. `Live` — a round trip reproduces the original
input bit-for-bit, which pins the register contract without independently
verifying the internal Julian-day epoch.

## Utility

**F$CmpNam** (d1.w=pattern length, (a0)=pattern, (a1)=target → carry clear
on match): wildcard compare (`?` one char, `*` any string),
case-insensitive — the primitive behind shell wildcard expansion. `Live`.
Two details not stated in the manuals: **the target string must be
plain-NUL-terminated** (a literal `0x00` byte), *not* sign-bit-terminated the
OS-9-module-name way despite that convention applying elsewhere in this call
family; and **the pattern is purely length-bounded by `d1.w`**, needing no
terminator of its own. `d1`'s upper word is irrelevant.

**F$PrsNam** ((a0)=path string → d0.b=terminator character, d1.w=element
length, (a0)=updated past a leading `/` if present, (a1)=pointer to the
terminator): parses one pathlist element at a time. `Live`.

**F$PErr** (d0.w=error message path, 0=none and the only mode os9exec honors;
d1.w=error code): prints a formatted `Error #nnn:nnn (E$NAME) description`
line. On os9exec it writes directly to the emulator console, **not** through
`I$Write`, so it bypasses per-process I/O redirection entirely — the same
channel a kernel-level error prints through. `Live`.

## Debugger support

| Call | Purpose | Notes |
|------|---------|-------|
| **F$DFork** | Fork suspended debuggee | F$Fork inputs plus (a2)=register buffer → child PID + initial register image. Child has trace bit set, never runs until F$DExec. `Live` |
| **F$DExec** | Drive debuggee | d0.w=PID, d1.l=instruction count (0=free run), d2.w=breakpoint count, (a0)=breakpoint list → instructions executed, remaining count, exception offset/classification/access address/IR. Syscalls (including through trap handlers and F$Chain) run at full speed as one logical instruction. Editing the register buffer changes what the child resumes with. `Live` |
| **F$DExit** | Kill debuggee | Resources survive for post-mortem examination. `Live` |
| **F$SysDbg** | Enter ROM debugger | Used by `break` (superuser, console); halts everything |

## Not implemented on os9exec

**F$SSpd, F$Mem, F$SchBit, F$AllBit, F$DelBit, F$Trans, F$UAcct** — all
seven route to a shared unimplemented handler. Calling any is a clean, safe
`E$UNKSVC` (208): no crash, no side effect, and no real register contract to
document. `Live`.

## Notes

- Signal 0 = kill (`kill` command; `kill 0` broadcasts within your
  user/group).
- Intercept-routine saved state: 72 bytes of MPU registers, 168 with FPU.
- Async-safe techniques and single-instruction atomics (`tas`, `cas`,
  `cas2`): `common/ipc.md`.
- Kernel I/O bookkeeping: device table (per I$Attach) + path table (per
  open path). Process and path descriptors are kernel-owned; user code
  never touches them directly.

---
Sources: OS-9 v2.4 Technical Reference Manual; a 1985 independent
OS-9/68000 technical manual (F$DFork register table); The OS-9 Guru; The
OS-9 Primer; OS-9 Insights; Technical I/O Manual v2.4; Disk File
Organization manual; OS-9 C Compiler manual; Using Professional OS-9 v2.4.
