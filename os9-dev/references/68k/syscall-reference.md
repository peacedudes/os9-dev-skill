# OS-9/68000 System Call Reference

68k-specific: TRAP #0 dispatch and 68000 register conventions. The 6809
equivalent (SWI2 dispatch, different codes and registers) is
`6809/syscalls-and-module-format.md`; C-library wrappers are in
`c/os9-clib-reference.md`.

Confidence: `Manual` throughout — every call listed is attested in this
skill's primary-source set. Entries additionally tagged `Flag` carry a
known cross-manual register-layout conflict; entries noted as
single-sourced have register detail from only one manual. Verify against
a primary manual (or run it) before coding against exact register slots.

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
| **F$Fork** | Create process | d0.w=module type (0=any), d1.l=extra stack/mem, d2.l=param size, d3.w=# I/O paths, d4.w=priority, (a0)=module name, (a1)=params | d0.w=child PID, (a0)=updated | Child inherits priority, open paths, user/group ID, current dirs, environment — never memory. `Manual, Flag`: register layout mirrors the fully-documented F$DFork table; other manual passages place priority in d2.w, group.user in d1.l, or param size in d5.l — verify before relying on exact slots |
| **F$Chain** | Replace current program | as F$Fork `Manual, Flag` | doesn't return | Fork+Exit in one: reuses the caller's process descriptor and PID, preserves open paths |
| **F$Exit** | Terminate | d1.w=status | — | Closes paths. Auto-unlinks only the *primary* module and trap handlers — anything else you linked/loaded leaks unless unlinked first |
| **F$Wait** | Wait for child | — | d0.w=child PID, d1.w=status | Also reclaims the dead child's process descriptor; forking without matching waits can fill the process table |
| **F$SPrior** | Set priority | d0.w=PID, d1.w=priority (0=min, 65535=max) | — | Same-user rule; superuser (group 0) can set any. Shell: `setpr` |

## Module management

| Call | Purpose | Key inputs | Key outputs | Notes |
|------|---------|-----------|------------|-------|
| **F$Link** | Link resident module | d0.w=type (0=any), (a0)=name | d0.w=type, d1.w=attr/rev, (a1)=entry, (a2)=header | Increments link count, no disk I/O; needs read permission |
| **F$Load** | Load from file | d0.b=access mode, d1.l=color (opt), (a0)=pathname | d0.w=type, d1.w=attr, (a1)=entry, (a2)=header | Registers every module in the file (a "module group" — stays resident until the group's combined count is zero), then links |
| **F$UnLink** | Unlink by address | (a2)=header | — | Free at zero unless sticky (bit 6) — sticky needs count −1 or memory pressure |
| **F$SetCRC** | Update module CRC | (a0)=module | — | Recomputes CRC + header parity after in-place modification (data modules); required before saving to disk |
| **F$CRC** | Compute CRC | d0.l=count, d1.l=accumulator (init $FFFFFFFF), (a0)=data | d1.l=updated | 24-bit, one's-complemented for storage. Kernel checks once at load/bootstrap, never re-verifies |
| **F$DatMod** | Create/link data module | d0.l=size, d1.w=attr/rev, d2.w=access, d3.w=type/lang, d4.l=color, (a0)=name | d0.w=type, d1.w=attr, (a1)=data, (a2)=header | Named shared memory: creator sizes it, later callers link by name. No kernel synchronization — coordinate with events/signals |

## I/O

| Call | Purpose | Key inputs | Key outputs | Notes |
|------|---------|-----------|------------|-------|
| **I$Attach** | Attach device | d0.b=mode, (a0)=device name | (a2)=device-table entry | Exact port/manager/driver/descriptor match increments use count; same port+code but different descriptor makes a "synonymous device"; no match allocates static storage and calls the driver's INIT (a failed INIT is rolled back via TERM, no entry left) |
| **I$Detach** | Detach device | (a2)=entry | — | At zero use count, calls TERM and frees storage unless shared. Superuser only |
| **I$Open** | Open path | d0.b=mode, (a0)=pathname | d0.w=path number, (a0)=updated | Allocates a path descriptor (share count 1). Opening a directory requires the directory bit (0x80) in the mode |
| **I$Create** | Create file | d0.b=mode, d1.w=attrs, d2.l=size hint, (a0)=pathname | d0.w=path | On non-multi-file devices behaves as I$Open |
| **I$Close** | Close path | d0.w=path | — | Decrements share count; descriptor freed at zero. F$Exit closes leftovers |
| **I$Read** / **I$Write** | Raw transfer | d0.w=path, d1.l=count, (a0)=buffer | d1.l=transferred | No editing. Reads return EOF error when exhausted; writes past EOF extend the file (RBF may pre-read a sector for partial-sector writes) |
| **I$ReadLn** / **I$WritLn** | Line transfer | same | same | Stop at first CR; apply device line editing (SCF: backspace/echo on input, LF append on output; 512-byte line buffer) |
| **I$Seek** | Position | d0.w=path, d1.l=position | — | Logical only; past-EOF legal; non-random devices no-op; doesn't touch record locks |
| **I$Delete** | Delete file | d0.b=mode, (a0)=pathname | — | Multi-file devices only |
| **I$MakDir** | Create directory | d0.b=mode, d1.w=attrs, (a0)=pathname | — | Managers without directories return unknown-service |
| **I$Dup** | Duplicate path | d0.w=path | d0.w=new path | Only bumps the existing descriptor's share count — file manager/driver never called |
| **I$GetStt** / **I$SetStt** | Status get/set | d0.w=path, d1.w=code, … | per code | File manager handles known codes, forwards unknown ones to the driver. Known: SS_Opt (128-byte option area), file size (C code 2), SS_Lock (record lock), SS_Ticks (lock timeout) |

## Events (F$Event subfunctions)

One counter primitive covers mutex + condition variable + counting
semaphore (see `common/ipc.md`). Subfunction names (`Manual`, name-level
only — register layouts not reproduced here): Ev$Link, Ev$UnLnk, Ev$Creat, Ev$Delet, Ev$Wait (block
until value in range), Ev$WaitR (relative range), Ev$Read, Ev$Info,
Ev$Pulse (momentary signal), Ev$Signl (permanent increment), Ev$Set
(absolute set), Ev$SetR (relative adjust).

## Alarms

**F$Alarm** `Manual` (single-sourced register layout, not cross-verified)
(d0.l=alarm ID, d1.w=function, d2.l=signal, d3.l=interval,
d4.l=date): subfunctions A$Delete, A$Set (one-shot), A$Cycle (periodic),
A$AtDate / A$AtJul (absolute Gregorian/Julian). Time-of-day alarms fire at
the *corrected* time after a clock adjustment. A system-state variant runs
a kernel subroutine instead of signaling; pending alarms die with their
process, so a persistent one must be requested as the system process.

## Signals & traps

| Call | Purpose | Notes |
|------|---------|-------|
| **F$Send** | Send signal to a process | Kill (0) restricted to same user/group (superuser excepted); other codes unrestricted. PID 0 broadcasts to all same-user/group processes except the sender. Signals queue in send order (~10× cost of unqueued delivery) |
| **F$Icpt** | Install signal intercept routine | On entry the kernel puts the count of queued signals in d0.w (1 = nothing else waiting). No handler installed ⇒ any interceptable signal kills the process |
| **F$SigMask** | Mask delivery | d1 = +1 increment / −1 decrement / 0 clear-to-zero. Counter is P$SigLvl (unsigned byte); over/underflow silently ignored. F$Sleep unmasks internally, making `mask → sleep(0)` a safe masked wait |
| **F$SigReset** | Reset intercept-nesting counter | Needed when `longjmp()` bypasses F$RTE exits |
| **F$RTE** | Return from intercept | Processes queued signals first |
| **F$STrap** | Install error-exception handler | (a0)=stack, (a1)=service table. Covers bus/address/illegal/zero-divide etc. (vectors 2–8, 10–24, 48–63), otherwise fatal. Handler gets all user registers stacked and chooses resume point. An F$DFork child's resources survive for post-mortem |
| **F$TLink** | Install trap handler | d0.w=trap 1–15, d1.l=memory override, (a0)=module name → (a1)=entry, (a2)=header. Links a TrapLib, allocates private static storage, runs its init. Max 15 per process (one per vector); a `tcall` before install can lazily self-install via the module's M$Excpt entry |
| **F$Sema** | Kernel binary semaphore | OS-9 **v3.0+** only — absent on the v2.4 baseline documented here |

## Utility

**F$CmpNam** (d1.w=pattern length, (a0)=pattern, (a1)=target → carry clear
on match): wildcard compare (`?` one char, `*` any string), case-
insensitive — the primitive behind shell wildcard expansion.

## Debugger support

| Call | Purpose | Notes |
|------|---------|-------|
| **F$DFork** | Fork suspended debuggee | F$Fork inputs plus (a2)=register buffer → child PID + initial register image. Child has trace bit set, never runs until F$DExec |
| **F$DExec** | Drive debuggee | d0.w=PID, d1.l=instruction count (0=free run), d2.w=breakpoint count, (a0)=breakpoint list → instructions executed, remaining count, exception offset/classification/access address/IR. Syscalls (including through trap handlers and F$Chain) run at full speed as one logical instruction. Editing the register buffer changes what the child resumes with |
| **F$DExit** | Kill debuggee | Resources survive for post-mortem examination |
| **F$SysDbg** | Enter ROM debugger | Used by `break` (superuser, console); halts everything |

## `Manual`-only calls (register detail not reproduced here)

These exist (attested by name in primary sources; some also `Source` —
implemented by os9exec) but their exact register contracts are not
reproduced in this file — consult the OS-9 Technical Manual before use: F$ID (PID +
group.user + priority), F$SSpd (suspend), F$Time / F$STime (read/set
system time), F$Gregor / F$Julian (date conversion), F$Sleep (d0.l ticks;
0 = until signal), F$UnLoad (unlink by name), F$SRqMem / F$SRtMem
(request/return system memory), F$Mem (resize data area), F$SRqCMem
(colored request), F$CpyMem (copy external memory), F$Trans (address
translation), F$PrsNam (parse pathlist element), F$PErr (print error
message), F$AllBit / F$DelBit / F$SchBit (bitmap ops), F$SUser (set user
ID), F$UAcct (accounting hook), I$ChgDir (change a current directory —
what `chd`/`chx` invoke with data vs. execute mode).

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
