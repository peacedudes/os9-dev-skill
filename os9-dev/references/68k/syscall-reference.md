# OS-9/68000 System Call Reference

68k-specific: TRAP #0 dispatch and 68000 register conventions. The 6809
equivalent (SWI2 dispatch, different codes and registers) is
`6809/syscalls-and-module-format.md`; C-library wrappers are in
`c/os9-clib-reference.md`.

Confidence: mostly `Manual` — every call listed is attested in this
skill's primary-source set, but until 2026-07-20 none had been
individually live-tested with known register inputs and checked against
documented outputs (existing `Live` findings elsewhere in this project
exercised specific calls incidentally, e.g. via BASIC09/C programs, but
that coverage was never backfilled here). A live audit is now
in progress, `Live` tags landing per-row as calls are confirmed — see
`VERIFICATION-BACKLOG.md`'s 68k syscall audit entry for progress.
Entries additionally tagged `Flag` carry a known cross-manual
register-layout conflict; entries noted as single-sourced have register
detail from only one manual. Verify against a primary manual (or run it)
before coding against exact register slots on anything not yet `Live`.

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
| **F$Fork** | Create process | d0.w=module type (0=any), d1.l=extra stack/mem, d2.l=param size, d3.w=# I/O paths, d4.w=priority, (a0)=module name, (a1)=params | d0.w=child PID, (a0)=updated | Child inherits priority, open paths, user/group ID, current dirs, environment — never memory. **`Live`, 2026-07-20 — `Flag` resolved**: register contract confirmed exact against `os9exec`'s own `OS9_F_Fork` (`Source/OS9exec_core/fcalls.c`) and live-tested end-to-end (`test/68k-live-verification/batch2-01.a` — forked a real child module, `F$Wait`'d it, got back the exact PID and exit status the child actually used). The conflicting other-manual passages this row used to flag are wrong for `os9exec`'s implementation, whatever their origin |
| **F$Chain** | Replace current program | as F$Fork `Manual, Flag` | doesn't return | Fork+Exit in one: reuses the caller's process descriptor and PID, preserves open paths |
| **F$Exit** | Terminate | d1.w=status | — | Closes paths. Auto-unlinks only the *primary* module and trap handlers — anything else you linked/loaded leaks unless unlinked first. **`Live`**: confirmed clean exit in every 68k assembly dogfood test this project has run (`test/68k-live-verification/dogfood-asm-line-counter.a` and others) |
| **F$Wait** | Wait for child | — | d0.w=child PID, d1.w=status | Also reclaims the dead child's process descriptor; forking without matching waits can fill the process table. **`Live`**: confirmed via the same `F$Fork` test — returned PID matched the forked child's exactly, status matched the child's own `F$Exit(77)` exactly |
| **F$SPrior** | Set priority | d0.w=PID, d1.w=priority (0=min, 65535=max) | — | Same-user rule; superuser (group 0) can set any. Shell: `setpr`. **`Live`**: confirmed setting the caller's own priority, no error |
| **F$ID** | Get process identity | — | d0.w=PID, d1.l=group.user (packed, group in high word), d2.w=priority | **`Live`, 2026-07-20**: register contract confirmed exact against `os9exec`'s own `OS9_F_ID` (`Source/OS9exec_core/fcalls.c`) and live-tested (`test/68k-live-verification/batch1-01.a`) — this row previously had no register detail at all (`Manual`-only). Architecture-general shape (matches 6809's `F$ID`, just wider registers) |

## Module management

| Call | Purpose | Key inputs | Key outputs | Notes |
|------|---------|-----------|------------|-------|
| **F$Link** | Link resident module | d0.w=type (0=any), (a0)=name | d0.w=type, d1.w=attr/rev, (a1)=entry, (a2)=header | Increments link count, no disk I/O; needs read permission. **`Live`**: confirmed against a module already resident from a preceding `F$Load` (`test/68k-live-verification/batch2-01.a`) |
| **F$Load** | Load from file | d0.b=access mode, d1.l=color (opt), (a0)=pathname | d0.w=type, d1.w=attr, (a1)=entry, (a2)=header | Registers every module in the file (a "module group" — stays resident until the group's combined count is zero), then links. **`Live`**: register contract confirmed exact against `os9exec`'s own `OS9_F_Load`, loaded a real module from disk with no error |
| **F$UnLink** | Unlink by address | (a2)=header | — | Free at zero unless sticky (bit 6) — sticky needs count −1 or memory pressure. **`Live`**: confirmed needing exactly two calls (one per link: the `F$Load` and the `F$Link`) to fully free the module, matching the documented link-count semantics |
| **F$SetCRC** | Update module CRC | (a0)=module | — | Recomputes CRC + header parity after in-place modification (data modules); required before saving to disk. **`Live`**: confirmed rejecting a non-header address with `E$BMID` (205) — validates its input rather than trusting it blindly. Success path (a real module image) not yet exercised |
| **F$CRC** | Compute CRC | d0.l=count, d1.l=accumulator (init $FFFFFFFF), (a0)=data | d1.l=updated | 24-bit, one's-complemented for storage. Kernel checks once at load/bootstrap, never re-verifies. **`Live`**: confirmed, real nonzero result over test data, no error |
| **F$DatMod** | Create/link data module | d0.l=size, d1.w=attr/rev, d2.w=access, d3.w=type/lang, d4.l=color, (a0)=name | d0.w=type, d1.w=attr, (a1)=data, (a2)=header | Named shared memory: creator sizes it, later callers link by name. No kernel synchronization — coordinate with events/signals. **`Live`**: confirmed creating a real 64-byte named data module, no error |

## I/O

| Call | Purpose | Key inputs | Key outputs | Notes |
|------|---------|-----------|------------|-------|
| **I$Attach** | Attach device | d0.b=mode, (a0)=device name | (a2)=device-table entry | Exact port/manager/driver/descriptor match increments use count; same port+code but different descriptor makes a "synonymous device"; no match allocates static storage and calls the driver's INIT (a failed INIT is rolled back via TERM, no entry left) |
| **I$Detach** | Detach device | (a2)=entry | — | At zero use count, calls TERM and frees storage unless shared. Superuser only |
| **I$Open** | Open path | d0.b=mode, (a0)=pathname | d0.w=path number, (a0)=updated | Allocates a path descriptor (share count 1). Opening a directory requires the directory bit (0x80) in the mode. **`Live`**: register contract confirmed exact — `test/68k-live-verification/dogfood-asm-line-counter.a` opened real files successfully (byte-exact line/char counts matched independent host-side verification), and separately confirmed to fail cleanly against a nonexistent custom device in `dogfood-filemgr-test.a` |
| **I$Create** | Create file | d0.b=mode, d1.b=attrs, d2.l=size hint, (a0)=pathname | d0.w=path | On non-multi-file devices behaves as I$Open. **`Live`**: register contract confirmed against `os9exec`'s own `OS9_I_Create` and live-tested (`test/68k-live-verification/batch3-01.a`) |
| **I$Close** | Close path | d0.w=path | — | Decrements share count; descriptor freed at zero. F$Exit closes leftovers. **`Live`**: confirmed in `dogfood-asm-line-counter.a` |
| **I$Read** / **I$Write** | Raw transfer | d0.w=path, d1.l=count, (a0)=buffer | d1.l=transferred | No editing. Reads return EOF error when exhausted; writes past EOF extend the file (RBF may pre-read a sector for partial-sector writes). **`Live`**: `dogfood-asm-line-counter.a`'s read loop reproduced exact known-good line/char counts on two independently-verified test files; confirmed raw `I$Write` truly does no editing (a bare CR alone doesn't advance the terminal — CR+LF needed) |
| **I$ReadLn** / **I$WritLn** | Line transfer | same | same | Stop at first CR; apply device line editing (SCF: backspace/echo on input, LF append on output; 512-byte line buffer) |
| **I$Seek** | Position | d0.w=path, d1.l=position | — | Logical only; past-EOF legal; non-random devices no-op; doesn't touch record locks. **`Live`**: register contract confirmed exact, seeking a freshly-created file to position 5 with no error |
| **I$Delete** | Delete file | d0.b=mode, (a0)=pathname | — | Multi-file devices only. **`Live`**: confirmed deleting a file this same test created |
| **I$MakDir** | Create directory | d0.b=mode, d1.b=attrs (corrected from `d1.w`, same as I$Create), (a0)=pathname | — | Managers without directories return unknown-service. **`Live`**: confirmed creating a real directory with no error |
| **I$Dup** | Duplicate path | d0.w=path | d0.w=new path | Only bumps the existing descriptor's share count — file manager/driver never called. **`Live`**: confirmed, returned a distinct path number for the same underlying file |
| **I$ChgDir** | Change a current directory | d0.b=mode (what `chd`/`chx` invoke with data vs. execute mode), (a0)=pathname | — | **`Live`, 2026-07-20**: register contract confirmed exact against `os9exec`'s own `OS9_I_ChgDir` and live-tested — changed into a directory this same test created, no error. Previously `Manual`-only with zero register detail |
| **I$GetStt** / **I$SetStt** | Status get/set | d0.w=path, d1.w=code, … | per code | File manager handles known codes, forwards unknown ones to the driver. Known: SS_Opt (128-byte option area), file size (C code 2), SS_Lock (record lock), SS_Ticks (lock timeout). **`Live`**: `I$SetStt`/SS_Lock and SS_Ticks both confirmed dispatching (`test/68k-live-verification/dogfood-sslock.a`, `dogfood-ssticks.a`) — this pass found and fixed a real `os9exec` bug, `SS_Lock` claiming success while doing nothing; now a real, working record lock (see `os9-systems-dev/file-managers.md`'s Record Locking section and project memory `nitros9-rbf-lock-fix-implemented` for the fix). **`I$GetStt`/SS.Size (code 2) confirmed — result comes back in `d2.l`, not `d1`** (`test/68k-live-verification/batch4-01.a`, verified against the real host-reported file size) |

## Events (F$Event subfunctions)

One counter primitive covers mutex + condition variable + counting
semaphore (see `common/ipc.md`). Subfunction names (`Manual`, name-level
only — register layouts not reproduced here): Ev$Link, Ev$UnLnk, Ev$Creat, Ev$Delet, Ev$Wait (block
until value in range), Ev$WaitR (relative range), Ev$Read, Ev$Info,
Ev$Pulse (momentary signal), Ev$Signl (permanent increment), Ev$Set
(absolute set), Ev$SetR (relative adjust).

## Alarms

**F$Alarm** (d0.l=alarm ID, d1.w=function, d2.l=signal, d3.l=interval,
d4.l=date): subfunctions A$Delete=0, A$Set=1 (one-shot), A$Cycle=2
(periodic), A$AtDate=3 / A$AtJul=4 (absolute Gregorian/Julian). **`Live`,
2026-07-20**: register contract and function codes confirmed exact
against `os9exec`'s own `OS9_F_Alarm`/`Alarm()` (`Source/OS9exec_core/
fcalls.c`/`alarms.c`) and live-tested — `A$Set` (far-future interval,
never allowed to fire) returned a real alarm ID with no error,
`A$Delete` on that same ID succeeded immediately after
(`test/68k-live-verification/batch5-01.a`). Actual signal delivery on
firing not exercised. Time-of-day alarms fire at
the *corrected* time after a clock adjustment. A system-state variant runs
a kernel subroutine instead of signaling; pending alarms die with their
process, so a persistent one must be requested as the system process.

## Signals & traps

| Call | Purpose | Notes |
|------|---------|-------|
| **F$Send** | Send signal to a process | Kill (0) restricted to same user/group (superuser excepted); other codes unrestricted. Standard OS-9 documents PID 0 as broadcasting to all same-user/group processes except the sender; signals queue in send order (~10× cost of unqueued delivery). **`Live`, 2026-07-20 — real `os9exec`-specific divergence, not a doc error**: `os9exec`'s own source (`OS9_F_Send`, `Source/OS9exec_core/fcalls.c`) explicitly states "0 is NOT all here!" — PID 0 is a real, specific, valid process ID on `os9exec` (its own comment: "pid=0 is a valid process ID in os9exec/nt"), and sending to it succeeds, but reaches only that one process, **not** a broadcast. Confirmed live: sending to PID 0 succeeds with no error (`test/68k-live-verification/batch3-02.a`), as does sending to the caller's own real PID (a genuine, valid single target) — both dispatch correctly, only the broadcast semantics are missing. Don't rely on PID-0 broadcast when writing `os9exec` test code; target real PIDs explicitly |
| **F$Icpt** | Install signal intercept routine | On entry the kernel puts the count of queued signals in d0.w (1 = nothing else waiting). No handler installed ⇒ any interceptable signal kills the process. **`Live`, 2026-07-20 — real `os9exec` feature gap, not a doc error**: `os9exec`'s own source (`OS9_F_Icpt`) carries an explicit comment, "does not work, as signal handling is not yet implemented (%%%)" — the call stores the handler address/data pointer fields with zero validation and always returns success, but signal delivery to an installed intercept routine is not implemented at all. Confirmed live: `F$Icpt` with a real handler address is accepted (carry clear), matching "always succeeds" — actual signal-to-handler delivery was not (and, per source, cannot currently be) exercised. Anything relying on `F$Icpt`-based signal handling working on `os9exec` should expect it to silently not fire |
| **F$SigMask** | Mask delivery | d1 = +1 increment / −1 decrement / 0 clear-to-zero. Counter is P$SigLvl (unsigned byte); over/underflow silently ignored. F$Sleep unmasks internally, making `mask → sleep(0)` a safe masked wait. **`Live`**: confirmed increment then decrement back, both accepted with no error |
| **F$SigReset** | Reset intercept-nesting counter | Needed when `longjmp()` bypasses F$RTE exits |
| **F$RTE** | Return from intercept | Processes queued signals first |
| **F$STrap** | Install error-exception handler | (a0)=stack, (a1)=service table. Covers bus/address/illegal/zero-divide etc. (vectors 2–8, 10–24, 48–63), otherwise fatal. Handler gets all user registers stacked and chooses resume point. An F$DFork child's resources survive for post-mortem. **`Live`**: register contract confirmed via real REAL÷0/INTEGER÷0 BASIC09 traps now correctly caught (see `basic09/gotchas.md`'s divide-by-zero entry); a deliberately-malformed unterminated service table was separately confirmed to be refused cleanly rather than walking off the arena (`test/68k-live-verification/dogfood-strap-unterminated.a` — this found and fixed a real `os9exec` out-of-bounds read bug) |
| **F$TLink** | Install trap handler | d0.w=trap 1–15, d1.l=memory override, (a0)=module name → (a1)=entry, (a2)=header. Links a TrapLib, allocates private static storage, runs its init. Max 15 per process (one per vector); a `tcall` before install can lazily self-install via the module's M$Excpt entry |
| **F$Sema** | Kernel binary semaphore | OS-9 **v3.0+** only — absent on the v2.4 baseline documented here |

## Time

**F$Time** (d0.w=mode: bit0 0=Gregorian/1=Julian, bit1 set=also return
ticks → d0.l=packed time, d1.l=packed date, d2.w=day of week
(0=Sunday), d3.l=tick rate/current tick if requested): **`Live`,
2026-07-20** — register contract confirmed exact against `os9exec`'s own
`OS9_F_Time` (`Source/OS9exec_core/fcalls.c`) and live-tested
(`test/68k-live-verification/batch1-01.a`, `d0.w=0` → real nonzero
packed time/date values, carry clear). This row previously had no
register detail at all (`Manual`-only) — a first guess assuming a
6809-style 6-byte-buffer-pointer convention was live-tested and found
**wrong**: 68k's `F$Time` returns everything directly in registers, no
buffer at all. Packed time/date field layout not decoded in this pass —
only the register-slot convention is confirmed, not what the bits inside
`d0.l`/`d1.l` mean.

**F$STime** (set current time) remains `Manual`-only, register detail
not reproduced here — presumably the input-side mirror of `F$Time`'s
output shape, but not live-tested this pass.

## Utility

**F$CmpNam** (d1.w=pattern length, (a0)=pattern, (a1)=target → carry clear
on match): wildcard compare (`?` one char, `*` any string), case-
insensitive — the primitive behind shell wildcard expansion. **`Live`,
2026-07-20**: register contract confirmed exact via `os9exec`'s own
`OS9_F_CmpNam` (`Source/OS9exec_core/fcalls.c`) plus a live match/mismatch
test (`test/68k-live-verification/batch1-01.a`). Two precise, previously
undocumented details, both source-confirmed and live-verified: **the
target string must be plain-NUL-terminated** (a literal `0x00` byte) —
*not* sign-bit-terminated the OS-9-module-name way, despite that
convention applying elsewhere in this same call family; and **the
pattern is purely length-bounded by `d1.w`**, needing no terminator of
its own at all.

No register-clearing gotcha applies to this call — `d1`'s upper word is
irrelevant (`loword()` reads it directly), confirmed live.

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
reproduced in this file — consult the OS-9 Technical Manual before use:
F$SSpd (suspend), F$STime (set system time — see the Time section
above), F$Gregor / F$Julian (date conversion), F$Sleep (d0.l ticks;
0 = until signal), F$UnLoad (unlink by name), F$SRqMem / F$SRtMem
(request/return system memory), F$Mem (resize data area), F$SRqCMem
(colored request), F$CpyMem (copy external memory), F$Trans (address
translation), F$PrsNam (parse pathlist element), F$PErr (print error
message), F$AllBit / F$DelBit / F$SchBit (bitmap ops), F$SUser (set user
ID), F$UAcct (accounting hook).

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
