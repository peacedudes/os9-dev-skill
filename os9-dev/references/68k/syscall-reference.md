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
| **F$Chain** | Replace current program | as F$Fork `Manual, Flag` | doesn't return | Fork+Exit in one: reuses the caller's process descriptor and PID, preserves open paths. **`Live`, 2026-07-20; RESOLVED 2026-07-21 — faithful, not a bug**: a failure-path attempt (bogus target name) produced a raw `Error #000:221 (E_MNF)` with none of the calling program's own output, because `OS9_F_Chain` (`fcalls.c` ~1836) tears the caller's image down (`unlink_module`/`free_mem`) BEFORE `link_load` resolves the name — so a bad name lands on an already-gutted process and it is killed, with nothing left to return an error to. This is the intended F$Chain contract (owner-confirmed) and matches NitrOS-9 `fchain.asm`, which likewise unlinks the old module and frees the old DAT blocks before linking the new one, then `F$Exit`s on failure (Level-2) / condemns the process (Level-1). The 6809/NitrOS-9 side shows the identical symptom for the same reason. Correct behavior — do not re-flag |
| **F$Exit** | Terminate | d1.w=status | — | Closes paths. Auto-unlinks only the *primary* module and trap handlers — anything else you linked/loaded leaks unless unlinked first. **`Live`**: confirmed clean exit in every 68k assembly dogfood test this project has run (`test/68k-live-verification/dogfood-asm-line-counter.a` and others) |
| **F$Wait** | Wait for child | — | d0.w=child PID, d1.w=status | Also reclaims the dead child's process descriptor; forking without matching waits can fill the process table. **`Live`**: confirmed via the same `F$Fork` test — returned PID matched the forked child's exactly, status matched the child's own `F$Exit(77)` exactly |
| **F$SPrior** | Set priority | d0.w=PID, d1.w=priority (0=min, 65535=max) | — | Same-user rule; superuser (group 0) can set any. Shell: `setpr`. **`Live`**: confirmed setting the caller's own priority, no error |
| **F$ID** | Get process identity | — | d0.w=PID, d1.l=group.user (packed, group in high word), d2.w=priority | **`Live`, 2026-07-20**: register contract confirmed exact against `os9exec`'s own `OS9_F_ID` (`Source/OS9exec_core/fcalls.c`) and live-tested (`test/68k-live-verification/batch1-01.a`) — this row previously had no register detail at all (`Manual`-only). Architecture-general shape (matches 6809's `F$ID`, just wider registers) |
| **F$SUser** | Set process identity | d1.l=(group:16)(user:16), full 16-bit fields each | — | No permission check on `os9exec` — any process may set itself to any identity, no superuser restriction. **Not the same wire format as `F$ID`'s output** — `F$ID` packs group/user into a single word (`group<<8\|user`, one byte each); feeding `F$ID`'s output straight into `F$SUser` sets the wrong identity instead of restoring it. **`Live`, 2026-07-20**: register contract confirmed exact against `os9exec`'s own `OS9_F_SUser` (`Source/OS9exec_core/fcalls.c`) and live-tested — set to an explicit (group=99,user=42), confirmed via `F$ID`'s own packing formula (`test/68k-live-verification/batch11-01.a`) |
| **F$Sleep** | Suspend process | d0.l=ticks (0=indefinite until signaled, 1=no-op/return immediately, negative=fractional 1/256-sec units, positive=raw tick count) | none written (a stale internal comment describes `F$Wait`'s shape, not this call's) | **`Live`, 2026-07-20**: register contract confirmed against `os9exec`'s own `OS9_F_Sleep` — `d0.l=1` (no-op) and a short positive tick count both return promptly with no hang (`test/68k-live-verification/batch11-01.a`). `d0.l=0` (indefinite, wakes only on signal) deliberately never tested live — nothing in a scripted harness can safely signal it |

## Module management

| Call | Purpose | Key inputs | Key outputs | Notes |
|------|---------|-----------|------------|-------|
| **F$Link** | Link resident module | d0.w=type (0=any), (a0)=name | d0.w=type, d1.w=attr/rev, (a1)=entry, (a2)=header | Increments link count, no disk I/O; needs read permission. **`Live`**: confirmed against a module already resident from a preceding `F$Load` (`test/68k-live-verification/batch2-01.a`) |
| **F$Load** | Load from file | d0.b=access mode, d1.l=color (opt), (a0)=pathname | d0.w=type, d1.w=attr, (a1)=entry, (a2)=header | Registers every module in the file (a "module group" — stays resident until the group's combined count is zero), then links. **`Live`**: register contract confirmed exact against `os9exec`'s own `OS9_F_Load`, loaded a real module from disk with no error |
| **F$UnLink** | Unlink by address | (a2)=header | — | Free at zero unless sticky (bit 6) — sticky needs count −1 or memory pressure. **`Live`**: confirmed needing exactly two calls (one per link: the `F$Load` and the `F$Link`) to fully free the module, matching the documented link-count semantics |
| **F$UnLoad** | Unlink by name | (a0)=module name | (a0)=updated | The declared `d0.w` (type/language) input is, like `F$CpyMem`'s PID, accepted but never actually read by `os9exec`'s implementation — it looks the module up by name alone, ignoring type/language entirely. **`Live`, 2026-07-20**: confirmed unloading a real loaded module by name (a deliberately wrong `d0.w` had no effect, confirming the above), then confirmed the module was genuinely gone — not just link-counted down — via a follow-up `F$Link` on the same name correctly failing `E$MNF` (`test/68k-live-verification/batch11-01.a`) |
| **F$SetCRC** | Update module CRC | (a0)=module | — | Recomputes CRC + header parity after in-place modification (data modules); required before saving to disk. **`Live`**: confirmed rejecting a non-header address with `E$BMID` (205) — validates its input rather than trusting it blindly. Success path (a real module image) not yet exercised |
| **F$CRC** | Compute CRC | d0.l=count, d1.l=accumulator (init $FFFFFFFF), (a0)=data | d1.l=updated | 24-bit, one's-complemented for storage. Kernel checks once at load/bootstrap, never re-verifies. **`Live`**: confirmed, real nonzero result over test data, no error |
| **F$DatMod** | Create/link data module | d0.l=size, d1.w=attr/rev, d2.w=access, d3.w=type/lang, d4.l=color, (a0)=name | d0.w=type, d1.w=attr, (a1)=data, (a2)=header | Named shared memory: creator sizes it, later callers link by name. No kernel synchronization — coordinate with events/signals. **`Live`**: confirmed creating a real 64-byte named data module, no error |

## Memory

| Call | Purpose | Key inputs | Key outputs | Notes |
|------|---------|-----------|------------|-------|
| **F$SRqMem** | Request system memory | d0.l=size (rounded up to 16 bytes; `$FFFFFFFF`=request the largest available block) | d0.l=actual size, (a2)=block pointer | **`Live`, 2026-07-20**: register contract confirmed against `os9exec`'s own `OS9_F_SRqMem` and live-tested — requested 256 bytes, wrote/read a real pattern through the returned pointer to confirm it's genuinely usable memory, not just a success code (`test/68k-live-verification/batch10-01.a`) |
| **F$SRtMem** | Return system memory | d0.l=size, (a2)=block pointer | — | Must pass back exactly the size `F$SRqMem` returned, or the block silently isn't freed (`os9exec`'s own documented restriction). **`Live`, 2026-07-20**: confirmed round-tripping a block requested via `F$SRqMem` |
| **F$SRqCMem** | Request colored system memory | d0.l=size, d1.l=color | d0.l=actual size, (a2)=block pointer | Same handler as `F$SRqMem` (confirmed by reading `funcdispatch.c` directly) — the color parameter is accepted but never read by the shared implementation, so it has no effect on `os9exec`. **`Live`, 2026-07-20**: confirmed live with a nonzero color value, behaves identically to plain `F$SRqMem` (`test/68k-live-verification/batch10-01.a`) |
| **F$CpyMem** | Copy memory across a process boundary | d0.w=PID of external memory's owner, d1.l=count, (a0)=source, (a1)=destination | — | The declared `d0.w` "owner PID" is accepted but never read — which is CORRECT: OS-9 lets a user-state caller READ any source address and never validates the source against the owner PID. The DESTINATION is what's checked (F$ChkMem's job): a write is allowed only into the caller's own data/blocks or a loaded RAM module, else `E$BPAddr`. **`Live`, 2026-07-20; hardened 2026-07-21 (commit `a4a62db`)**: register contract confirmed; a write into the caller's own buffer succeeds, a write to a foreign arena address is refused. os9exec has no SPU (System Protection Unit / MMU), so this models *with-SPU* protection and is deliberately stricter than bare-hardware OS-9, where F$ChkMem without an SPU is mostly a no-op. Test: `test/68k-live-verification/batch10-01.a`; suite guard `f$cpymem` |

## I/O

| Call | Purpose | Key inputs | Key outputs | Notes |
|------|---------|-----------|------------|-------|
| **I$Attach** | Attach device | d0.b=mode, (a0)=device name | (a2)=device-table entry | Exact port/manager/driver/descriptor match increments use count; same port+code but different descriptor makes a "synonymous device"; no match allocates static storage and calls the driver's INIT (a failed INIT is rolled back via TERM, no entry left) |
| **I$Detach** | Detach device | (a2)=entry | — | At zero use count, calls TERM and frees storage unless shared. Superuser only |
| **I$Open** | Open path | d0.b=mode, (a0)=pathname | d0.w=path number, (a0)=updated | Allocates a path descriptor (share count 1). Opening a directory requires the directory bit (0x80) in the mode. **`Live`**: register contract confirmed exact — `test/68k-live-verification/dogfood-asm-line-counter.a` opened real files successfully (byte-exact line/char counts matched independent host-side verification), and separately confirmed to fail cleanly against a nonexistent custom device in `dogfood-filemgr-test.a` |
| **I$Create** | Create file | d0.b=mode, d1.b=attrs, d2.l=size hint, (a0)=pathname | d0.w=path | On non-multi-file devices behaves as I$Open. **`Live`**: register contract confirmed against `os9exec`'s own `OS9_I_Create` and live-tested (`test/68k-live-verification/batch3-01.a`) |
| **I$Close** | Close path | d0.w=path | — | Decrements share count; descriptor freed at zero. F$Exit closes leftovers. **`Live`**: confirmed in `dogfood-asm-line-counter.a` |
| **I$Read** / **I$Write** | Raw transfer | d0.w=path, d1.l=count, (a0)=buffer | d1.l=transferred | No editing. Reads return EOF error when exhausted; writes past EOF extend the file (RBF may pre-read a sector for partial-sector writes). **`Live`**: `dogfood-asm-line-counter.a`'s read loop reproduced exact known-good line/char counts on two independently-verified test files; confirmed raw `I$Write` truly does no editing (a bare CR alone doesn't advance the terminal — CR+LF needed) |
| **I$ReadLn** / **I$WritLn** | Line transfer | same | same | Stop at first CR; apply device line editing (SCF: backspace/echo on input, LF append on output; 512-byte line buffer). **`Live`**: `I$ReadLn` confirmed — a real CR-terminated line written then read back returned the exact byte count including the CR |
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
(`test/68k-live-verification/batch5-01.a`). Time-of-day alarms fire at
the *corrected* time after a clock adjustment. A system-state variant runs
a kernel subroutine instead of signaling; pending alarms die with their
process, so a persistent one must be requested as the system process.
**Signal delivery on firing, `Live`, 2026-07-21 (real `os9exec` fix)**: a
process sleeping via `F$Sleep` (any duration, including indefinite
`F$Sleep(0)`) waiting to be woken by its own alarm firing was **never woken by
it** — the alarm-due check ran only on the next `TRAP0` dispatch, and
`DoWait()`'s idle-wait path (reached whenever every process is
asleep/blocked) never polled it, so the signal sat undelivered until the
process woke some other way. Fixed by checking alarms from `DoWait()` too
(`CheckAlarms()`, `alarms.c`/`procstuff.c`) — same idiom as the stdin-poll
fix for `tsmon`. Confirmed live: a 1-second alarm now interrupts both a
10-second `F$Sleep` and an indefinite `F$Sleep(0)`.

## Signals & traps

| Call | Purpose | Notes |
|------|---------|-------|
| **F$Send** | Send signal to a process | Kill (0) restricted to same user/group (superuser excepted); other codes unrestricted. Standard OS-9 documents PID 0 as broadcasting to all same-user/group processes except the sender; signals queue in send order (~10× cost of unqueued delivery). **`Live`, 2026-07-20 — real `os9exec`-specific divergence, not a doc error**: `os9exec`'s own source (`OS9_F_Send`, `Source/OS9exec_core/fcalls.c`) explicitly states "0 is NOT all here!" — PID 0 is a real, specific, valid process ID on `os9exec` (its own comment: "pid=0 is a valid process ID in os9exec/nt"), and sending to it succeeds, but reaches only that one process, **not** a broadcast. Confirmed live: sending to PID 0 succeeds with no error (`test/68k-live-verification/batch3-02.a`), as does sending to the caller's own real PID (a genuine, valid single target) — both dispatch correctly, only the broadcast semantics are missing. Don't rely on PID-0 broadcast when writing `os9exec` test code; target real PIDs explicitly |
| **F$Icpt** | Install signal intercept routine | On entry the kernel puts the count of queued signals in d0.w (1 = nothing else waiting). No handler installed ⇒ any interceptable signal kills the process. **`Live`, 2026-07-20 — real `os9exec` feature gap, not a doc error**: `os9exec`'s own source (`OS9_F_Icpt`) carries an explicit comment, "does not work, as signal handling is not yet implemented (%%%)" — the call stores the handler address/data pointer fields with zero validation and always returns success, but signal delivery to an installed intercept routine is not implemented at all. Confirmed live: `F$Icpt` with a real handler address is accepted (carry clear), matching "always succeeds" — actual signal-to-handler delivery was not (and, per source, cannot currently be) exercised. Anything relying on `F$Icpt`-based signal handling working on `os9exec` should expect it to silently not fire |
| **F$SigMask** | Mask delivery | d1 = +1 increment / −1 decrement / 0 clear-to-zero. Counter is P$SigLvl (unsigned byte); over/underflow silently ignored. F$Sleep unmasks internally, making `mask → sleep(0)` a safe masked wait. **`Live`**: confirmed increment then decrement back, both accepted with no error |
| **F$SigReset** | Reset intercept-nesting counter | Needed when `longjmp()` bypasses F$RTE exits |
| **F$RTE** | Return from intercept | Processes queued signals first |
| **F$STrap** | Install error-exception handler | (a0)=stack, (a1)=service table. Covers bus/address/illegal/zero-divide etc. (vectors 2–8, 10–24, 48–63), otherwise fatal. Handler gets all user registers stacked and chooses resume point. An F$DFork child's resources survive for post-mortem. **`Live`**: register contract confirmed via real REAL÷0/INTEGER÷0 BASIC09 traps now correctly caught (see `basic09/gotchas.md`'s divide-by-zero entry); a deliberately-malformed unterminated service table was separately confirmed to be refused cleanly rather than walking off the arena (`test/68k-live-verification/dogfood-strap-unterminated.a` — this found and fixed a real `os9exec` out-of-bounds read bug) |
| **F$TLink** | Install trap handler | d0.w=trap 1–15, d1.l=memory override, (a0)=module name → (a1)=entry, (a2)=header. Links a TrapLib, allocates private static storage, runs its init. Max 15 per process (one per vector); a `tcall` before install can lazily self-install via the module's M$Excpt entry. **`Live`, 2026-07-20**: install and remove both confirmed against a hand-built `mod_trap` module (`test/68k-live-verification/batch8-01.a`) — `(a0)` must be a module *name*, resolved via the same exec-directory search as `F$Link`/`F$Load`, not a bare filename in the data directory. `_midata`/`_midref` are **not** "no table" at 0 — `os9exec`'s `prepData` unconditionally parses a table at that offset, so a module with no init data needs a real empty table there (dOff=0,cnt=0, then two 0-terminators) or the load fails with `E$BMID`. Found and fixed a genuine `os9exec` leak this call could trigger: `install_traphandler` set `tp->trapmodule`/`tp->mid` before calling `prepData`, and on `prepData` failure returned without rolling them back — corrupting later signal-handler-slot bookkeeping and leaking the loaded module (`Source/OS9exec_core/modstuff.c`) |
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

**F$STime** (d0.l=time, d1.l=date — input-side mirror of `F$Time`'s
output shape, confirmed against `OS9_F_STime`): **`Live`, 2026-07-20**
— confirmed accepting real time/date values with no error
(`test/68k-live-verification/batch7-01.a`). On this build specifically
the call does not touch the real host clock at all — its only host-side
effect is compiled in only under `#ifdef MACOS9` (the classic Mac OS 9
target), not this modern macOS/Linux/Windows build.

**F$Julian** (d0.l=time as `00hhmmss`, d1.l=date packed as
`(year:16)(month:8)(day:8)` — **not** decimal-digit "yyyymmdd" despite
that doc naming, confirmed against `OS9_F_Julian` → d0.l=seconds since
midnight, d1.l=Julian day number) and **F$Gregor** (the inverse: same
d0.l=seconds-since-midnight/d1.l=Julian-day in, `00hhmmss`/packed date
out): **`Live`, 2026-07-20** — round-trip confirmed exact (`F$Julian`'s
output fed straight into `F$Gregor` reproduced the original input
bit-for-bit), which verifies the register contract without needing to
independently verify the internal Julian-day epoch
(`test/68k-live-verification/batch9-01.a`).

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

**F$PrsNam** ((a0)=path string → d0.b=terminator character, d1.w=element
length, (a0)=updated past a leading `/` if present, (a1)=pointer to the
terminator): parses one pathlist element at a time; also the call
whose double-evaluated-`++p` bug once broke single-character redirect
targets (`os9-shell-rejects-single-char-redirect-target`). **`Live`,
2026-07-20**: register contract confirmed exact against `os9exec`'s own
`OS9_F_PrsNam` and live-tested both without and with a leading `/` —
the leading-`/` advance (the historically buggy path) is still correct
(`test/68k-live-verification/batch9-01.a`).

**F$PErr** (d0.w=error message path, 0=none and the only mode
`os9exec` honors; d1.w=error code): prints a formatted `Error
#nnn:nnn (E$NAME) description` line. Writes directly to the emulator's
own console via `upe_printf`, **not** through `I$Write` — bypasses
per-process I/O redirection entirely, the same channel an uncontrolled
kernel-level error (like the `F$Chain` finding above) prints through.
**`Live`, 2026-07-20**: confirmed against `os9exec`'s own `OS9_F_PErr`,
produced the expected formatted line for a known error code
(`test/68k-live-verification/batch9-01.a`).

## Debugger support

| Call | Purpose | Notes |
|------|---------|-------|
| **F$DFork** | Fork suspended debuggee | F$Fork inputs plus (a2)=register buffer → child PID + initial register image. Child has trace bit set, never runs until F$DExec. **`Live`, 2026-07-20**: confirmed forking a real child module (`childprg68k`) suspended, no error, plausible child PID returned (`test/68k-live-verification/batch6-01.a`) |
| **F$DExec** | Drive debuggee | d0.w=PID, d1.l=instruction count (0=free run), d2.w=breakpoint count, (a0)=breakpoint list → instructions executed, remaining count, exception offset/classification/access address/IR. Syscalls (including through trap handlers and F$Chain) run at full speed as one logical instruction. Editing the register buffer changes what the child resumes with. **`Live`**: single-stepping the forked child exactly one instruction (no breakpoints) completed cleanly, parent resumed with no error and no hang |
| **F$DExit** | Kill debuggee | Resources survive for post-mortem examination. **`Live`**: confirmed killing the debug child after single-stepping it, no error |
| **F$SysDbg** | Enter ROM debugger | Used by `break` (superuser, console); halts everything |

## Not implemented on `os9exec`

**F$SSpd, F$Mem, F$SchBit, F$AllBit, F$DelBit, F$Trans, F$UAcct** — all
seven route to a shared `OS9_F_UnImp` handler in `os9exec`'s own
dispatch table (`funcdispatch.c`), confirmed by reading it directly.
Calling any of them is a clean, safe error — `E$UNKSVC` (208), no
crash, no side effect — never a real register contract to document.
**`Live`, 2026-07-20**: all seven confirmed live, each returning exactly
`E$UNKSVC` (`test/68k-live-verification/batch12-01.a`).

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
