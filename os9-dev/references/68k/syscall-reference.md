# OS-9/68000 System Call Reference

68k-specific: TRAP #0 dispatch and 68000 register conventions. The 6809
equivalent (SWI2 dispatch, different codes and registers) is
`6809/syscalls-and-module-format.md`; C-library wrappers are in
`c/os9-clib-reference.md`.

**Scope: user-mode calls** - the manual's Chapter 15 I/O plus user-state F$.
Chapter 16 system-mode requests (`F$Move`, `F$SLink`, `F$SSvc`, `F$SetSys`,
`F$AllPD`/`F$AllPrc`/`F$AProc`/`F$NProc`/`F$FindPD`/`F$RetPD`, `F$IRQ`,
`F$GPrDsc`/`F$GPrDBT`, ...) are kernel-internal and belong to the
`os9-systems-dev` skill - deliberately absent here, not overlooked.

Verify exact register slots against a primary manual before coding against
them; entries tagged `Live` (os9exec) have at least been exercised on an
implementation.

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

`path0` here is a `vsect` label; a plain `(a6)` is not the start of the data
area (`68k/os9-68k-assembly.md`).

The `OS9` assembler pseudo-instruction emits the trap+word pair:
`OS9 I$Close`. A custom trap library is reached the same way via `tcall
T$Math, T$DMul` (expands to `TRAP #<n>` + `dc.w`), for handlers installed
on TRAP #1-#15 via F$TLink.

- Parameters/results in documented D/A registers per call.
- Error: carry set, error code in `d1.w`; test with `bcs`/`bcc`.
- Strings are NUL-terminated, passed by address.
- TRAP #0 (vector 32) is the OS-9 entry; TRAP #1-#15 (vectors 33-47) are
  user trap handlers.

## Process management

| Call | Purpose | Key inputs | Key outputs | Notes |
|------|---------|-----------|------------|-------|
| **F$Fork** | Create process | d0.w=module type (0=any), d1.l=extra stack/mem, d2.l=param size, d3.w=# I/O paths, d4.w=priority, (a0)=module name, (a1)=params | d0.w=child PID, (a0)=updated past the module name | Child inherits priority, open paths, user/group ID, current dirs, environment - never memory. `Live` (os9exec); contract confirmed against the *OS-9/68000 Operating System Technical Manual* (1984) ch. 14 |
| **F$Chain** | Replace current program | as F$Fork | doesn't return | Fork+Exit in one: reuses the caller's process descriptor and PID, preserves open paths. **A failed chain kills the caller** - the caller's image is torn down (unlink, free) *before* the new name is resolved, so a bad name lands on an already-gutted process with nothing left to return an error to. The caller simply exits with status `E$MNF` (221); the line you see is the *parent shell* reporting that status, and under a parent that is not a shell nothing prints at all (`Live` (os9exec)). This is the contract, not a fault; NitrOS-9 (`fchain.asm`) does the same. `Live` (os9exec); NitrOS-9 side is `Source` (`fchain.asm`), not run |
| **F$Exit** | Terminate | d1.w=status | - | Closes paths. Auto-unlinks only the *primary* module and trap handlers - anything else you linked/loaded leaks unless unlinked first. `Live` (os9exec) |
| **F$Wait** | Wait for child | - | d0.w=child PID, d1.w=status | Also reclaims the dead child's process descriptor; forking without matching waits can fill the process table. `Live` (os9exec) |
| **F$SPrior** | Set priority | d0.w=PID, d1.w=priority (0=min, 65535=max) | - | Same-user rule; superuser (group 0) can set any. Shell: `setpr`. `Live` (os9exec) |
| **F$ID** | Get process identity | - | d0.w=PID, d1.l=group.user (packed, group in high word), d2.w=priority | The call exists on both targets, but **the identity format does not carry across**: 6809's `F$ID` returns a *flat* user ID with no group field at all, so a group/user split applied there is wrong - see the cross-target trap in `6809/syscalls-and-module-format.md`. `Live` (os9exec) |
| **F$SUser** | Set process identity | d1.l=(group:16)(user:16), full 16-bit fields each | - | Same wire format as `F$ID`'s `d1.l` output, so save/restore round-trips. Permitted in exactly **three** cases, `E$Permit` otherwise: (1) caller is 0.0; (2) caller's primary module is *owned by* 0.0; (3) the new ID equals the caller's own primary module's owner. Owner = `M$Owner`, header offset $008, group word then user word - same packing as d1.l, so it compares directly. Case 3 is OS-9's setuid: a module owned by X lets whoever runs it become X. Case 2 is why `login` works at all - `ident` shows `login` owned by 0.0 while `shell`/`list`/`attr` are 1.0. **Case 1 is literally 0.0, both halves - NOT `is_super()` (group 0 alone).** The TRM draws that line deliberately: `is_super` is what an identity may *do*, F$SUser case 1 is who may *change* identity, so a group-0/user-nonzero account (0.153) is a super user that still cannot freely reassign its ID. `Live` (os9exec, enforced + tested) + `Manual` (v2.4 TRM p.1-62, checked against the manual's own wording) |
| **F$Sleep** | Suspend process | d0.l=ticks (0=indefinite until signaled, 1=no-op/return immediately, positive=raw tick count, **high bit set = the low 31 bits are 256ths of a second** - the same convention as `F$Alarm`'s `d3`, `Manual`) | d0.l=remaining ticks if woken early | `Live` (os9exec). Both Microware manuals document the `d0.l` output (68k: "remaining number of ticks if awakened prematurely"; 6809: `(X)` decremented by ticks slept), so a process woken by a signal can tell how much sleep was left |

## Module management

| Call | Purpose | Key inputs | Key outputs | Notes |
|------|---------|-----------|------------|-------|
| **F$Link** | Link resident module | d0.w=type/language byte (0=any), (a0)=name | d0.w=type/language, d1.w=attr/rev, **(a0)=updated past the module name**, (a1)=entry, (a2)=header | Increments link count, no disk I/O. Fails if the module's access word does not give the process read permission (`Manual`) - `E$Permit`, judged by owner, group or public field as the caller relates to the module's owner (the Guru 3.2.4). A module that is not re-entrant may be linked by only one process at a time, else `E$ModBsy` (`Manual`). `Live` (os9exec) |
| **F$Load** | Load from file | d0.b=access mode, d1.l=memory "color" type (optional - documented in the v2.4 Technical Manual (1994), absent from the 1984 one, so a later addition rather than a disagreement), (a0)=pathname | d0.w=type/language, d1.w=attr/rev, **(a0)=updated beyond the path name**, (a1)=entry (of the *first* module loaded), (a2)=module pointer | Registers every module in the file (a "module group" - resident until the group's combined count is zero), then links. `Live` (os9exec) |
| **F$UnLink** | Unlink by address | (a2)=header | - | Free at zero unless sticky (bit 6) - sticky needs count -1 or memory pressure (`Manual`). A module that was loaded *and* linked needs one call per link to fully free. `Live` (os9exec) |
| **F$UnLoad** | Unlink by name | (a0)=module name | (a0)=updated | `d0.w`=type/language takes part in the lookup, as the manual's input list says: `Live` (os9exec), `d0=$DEAD` gives `E$MNF` and leaves the module loaded, while the module's own type/language or `0` unloads it |
| **F$SetCRC** | Update module CRC | (a0)=module | - | Recomputes CRC + header parity after in-place modification (data modules); required before saving to disk. Rejects a non-header address with `E$BMID` (205) rather than trusting its input. `Live` (os9exec) |
| **F$CRC** | Compute CRC | d0.l=count, d1.l=accumulator (init $FFFFFFFF), (a0)=data | d1.l=updated | 24-bit, one's-complemented for storage. Kernel checks once at load/bootstrap, never re-verifies. `Live` (os9exec) |
| **F$DatMod** | Create/link data module | d0.l=size, d1.w=attr/rev, d2.w=access, d3.w=type/lang, d4.l=color, (a0)=name - **d3 and d4 are read only if bit 15 of d2 is set**; otherwise the module is type Data, language 0, general memory (the Guru 11.5.4, `Hearsay`-grade third party; the TRM marks both "optional" without saying how) | d0.w=type, d1.w=attr, (a1)=data, (a2)=header | Named shared memory: creator sizes it, later callers link by name. No kernel synchronization - coordinate with events/signals. `Live` (os9exec) |

## Memory

| Call | Purpose | Key inputs | Key outputs | Notes |
|------|---------|-----------|------------|-------|
| **F$Mem** | Resize the data memory area | d0.l=desired size in bytes, rounded up to an allocation block ("16 bytes in version 2.0"); 0=information request | d0.l=actual size, (a1)=new end of the data area (+1) | Grows "contiguously upward", shrinks "downward from the old highest address": the base never moves (A6 points into it). Contracting to at or below the stack pointer is `E$DelSP` (223). An expansion may be refused with adequate memory free, because the space directly ABOVE the data area must itself be free (`Manual`, F$Mem page 1 - 43) - a C program built with `cc -I` loads `cio` right after entry and that module then sits above its data area, so `load` the trap handler first if a program's F$Mem expansion keeps failing. `Live` (os9exec): information request, E$DelSP, and expansion when the arena above is free (CONF68K t51-t53). |
| **F$SysID** | Get system identification | Pre-3.0 form: (a0)/(a1)/(a2)=80-byte buffers for the version, copyright and author-names strings, 0=not wanted | d0.l=licensee, d1.l=serial (both 1 by default), d2.l=MPU in use, d3.l=MPU the kernel was built for (Motorola part numbers), d4-d7=0 | **Not in the v2.4 manual**: "implemented but not documented" before v3.0 (OS-9 Insights ed. 3, App. A), the register form above being the OS-9 Guru's 11.5.16 (`Hearsay`-grade third party, but confirmed by period code: hc_utils `sysid.c` passes exactly these registers). v3.0 redefined it around a parameter block after OS-9000's `_os_SysID()`; that layout is not documented in anything available here. `Live` (os9exec): the pre-3.0 form, answering 68020/68020, 1/1, and its own strings (CONF68K t54). |
| **F$SRqMem** | Request system memory | d0.l=size (rounded up to 16 bytes; `$FFFFFFFF`=request the largest available block) | d0.l=actual size, (a2)=block pointer | `Live` (os9exec) |
| **F$SRtMem** | Return system memory | d0.l=size, (a2)=block pointer | - | Must pass back exactly the size `F$SRqMem` returned, or the block silently isn't freed. `Live` (os9exec) |
| **F$SRqCMem** | Request colored system memory | d0.l=size, d1.l=color | d0.l=actual size, (a2)=block pointer | os9exec accepts the color but does not act on it. `Live` (os9exec) |
| **F$CpyMem** | Copy memory across a process boundary | d0.w=PID of external memory's owner, d1.l=count, (a0)=source, (a1)=destination | - | "You can view any memory in the system with F$CpyMem" (`Manual`) - it is the way to examine modules and system memory from user state. The DESTINATION is what is checked: a write only into the caller's own memory, else `E$BPAddr`. `Live` (os9exec) (os9exec departs - see "Where os9exec departs from the manuals" in `common/using-os9exec-repl.md`) |

## I/O

| Call | Purpose | Key inputs | Key outputs | Notes |
|------|---------|-----------|------------|-------|
| **I$Attach** | Attach device | d0.b=mode, (a0)=device name | (a2)=device-table entry | Exact port/manager/driver/descriptor match increments use count; same port+code but different descriptor makes a "synonymous device"; no match allocates static storage and calls the driver's INIT (a failed INIT is rolled back via TERM, no entry left) |
| **I$Detach** | Detach device | (a2)=entry | - | At zero use count, calls TERM and frees storage unless shared. Superuser only |
| **I$Open** | Open path | d0.b=mode - a **bit field** `D S E W R`, so **0 requests no access** and reads then fail on a successfully opened path (see `common/unix-differences.md`; POSIX `O_RDONLY` is 0), (a0)=pathname | d0.w=path number, (a0)=updated past the pathname - to the first blank after it (`Live` (os9exec): `'fx   '` opens `fx` and returns a0 at name+2); trailing spaces are not stepped over | Allocates a path descriptor (share count 1). Opening a directory requires the directory bit (0x80) in the mode. `Live` (os9exec). **`E` alone chooses where the name resolves - the execution directory - and grants no read:** `I$Read` needs a path opened in read or update mode `Manual`, so a file found through `chx` and opened `S_IEXEC` alone cannot be read. Open it `S_IEXEC | S_IREAD`, and expect read permission to be checked too. `F$Load`'s "Exec_ or Read_" makes the same choice of *directory*, which is what makes this look readable. Silent in the usual shape of the code: a failed header read looks like "not a module". `Live` (os9exec) |
| **I$Create** | Create file | d0.b=mode, d1.b=attrs, d2.l=size hint, (a0)=pathname | d0.w=path | **Not `creat()`**: an existing name is an error (`E$CEF`, 218), never truncate-and-reopen, and it cannot make a directory - that is `I$MakDir` (`Manual`). On non-multi-file devices behaves as I$Open. `Live` (os9exec) |
| **I$Close** | Close path | d0.w=path | - | Decrements share count; descriptor freed at zero. F$Exit closes leftovers. `Live` (os9exec) |
| **I$Read** / **I$Write** | Raw transfer | d0.w=path, d1.l=count, (a0)=buffer | d1.l=transferred | No editing - a bare CR alone does not advance the terminal; CR+LF is needed. Reads return EOF error when exhausted; writes past EOF extend the file (RBF may pre-read a sector for partial-sector writes). `Live` (os9exec) |
| **I$ReadLn** / **I$WritLn** | Line transfer | same | same | Stop at first CR; apply device line editing (SCF: backspace/echo on input, LF append on output; 512-byte line buffer). The returned count includes the CR. On SCF the terminator is **PD_EOR**, which merely defaults to CR (`tmode eor=`; SCF devices only). The byte count TRUNCATES the line rather than ending the read: input past it is discarded, PD_OVF echoed per byte, until PD_EOR arrives - so the tail is lost, not returned by a second read. `Live` (os9exec) |
| **I$Seek** | Position | d0.w=path, d1.l=position | - | Logical only; past-EOF legal; non-random devices no-op; doesn't touch record locks. `Live` (os9exec) |
| **I$Delete** | Delete file | d0.b=mode, (a0)=pathname | (a0)=updated past the pathlist | Multi-file devices only. `Live` (os9exec) |
| **I$MakDir** | Create directory | d0.b=mode, d1=access permissions (permit bits live in the low byte), **d2.l=initial allocation size (optional)**, (a0)=pathname | (a0)=updated past the pathname | Managers without directories refuse it: `Live` (os9exec), `/pipe/x` gives `E$UnkSvc` (208), `/term/x` and `/nil/x` give `E$BPNam` (215) |
| **I$Dup** | Duplicate path | d0.w=path | d0.w=new path | Only bumps the existing descriptor's share count - file manager/driver never called. `Live` (os9exec) |
| **I$ChgDir** | Change a current directory | d0.b=mode (what `chd`/`chx` invoke with data vs. execute mode), (a0)=pathname | (a0)=updated past the pathname | `Live` (os9exec) |
| **I$GetStt** / **I$SetStt** | Status get/set | d0.w=path, d1.w=code, ... | per code | File manager handles known codes, forwards unknown ones to the driver. Known: SS_Opt (128-byte option area), file size (C code 2), SS_Lock (record lock), SS_Ticks (lock timeout). **`I$GetStt`/SS.Size (code 2) returns its result in `d2.l`, not `d1`.** `Live` (os9exec). SS_Size, "Return Current File Size (RBF, PIPE)" / "Set File Size (RBF, PIPE)": GetStat returns d2.l=current size; SetStat takes d2.l=desired size, and for a pipe `d2.l=0` resets the pipe path "provided the pipe has no active readers or writers" - any other value is ignored (`Manual`). Neither page names an access mode the path needs. On a pipe, GetStat is ambiguous: the SS_Size page says file size, while Pipeman's own list says it "returns the size of the pipe buffer" (`Manual`, `Flag`) |

## Events (F$Event subfunctions)

One counter primitive covers mutex + condition variable + counting
semaphore (see `common/ipc.md`). **F$Event** = `$53`; the subfunction is in
`d1.w`. Function codes: Ev$Link=`0`, Ev$UnLnk=`1`, Ev$Creat=`2`,
Ev$Delet=`3`, Ev$Wait=`4`, Ev$WaitR=`5`, Ev$Read=`6`, Ev$Info=`7`,
Ev$Signl=`8`, Ev$Pulse=`9`, Ev$Set=`$0A`, Ev$SetR=`$0B`.

**Register contracts** (`Live` (os9exec)):

- **Ev$Creat**: a0=name, d0.l=initial value, d1.w=2, d2.w=wait-increment,
  d3.w=signal-increment -> d0.l=event ID. `E$EvBusy` if the name exists.
- **Ev$Link**: a0=name, d1.w=0 -> d0.l=event ID (`E$EvNF` if not created yet).
- **Ev$Wait**: d0.l=event ID, d1.w=4, d2.l=min, d3.l=max -> **blocks** until
  `min <= value <= max`, then adds the wait-increment; returns "actual event
  value" in d1.l (`Manual`) - **the value that satisfied the wait, before
  the increment.** The manual's signal case confirms the reading: a waiter
  woken by a signal instead gets a value "not within the specified range",
  with the increment not applied. Period code depends on it: TOP's `os9lib`
  (1988) takes a mutex with `while (_ev_wait(id, 0, 0) != 0);` on an event
  created at 0 with wait-increment +1. A bad event ID returns `E$EvntID`
  immediately. `Live` (os9exec): an event at 0 with increment +1, waited on
  0..0, returns 0; a second wait on 1..1 returns 1.
- **Ev$Signl**: d0.l=event ID, d1.w=8 - adds the signal-increment to the
  counter, then wakes the first waiting process whose range the value is
  in; with the MS bit of d1 set it wakes every process in range (`Manual`).
- **Ev$Delet**: a0=name, d1.w=3 (by name, not ID).

A blocking wait is woken cross-process (`Live` (os9exec)): process A parks on an
out-of-range Ev$Wait, process B does Ev$Link + Ev$Signl to push the counter
into range, A wakes and returns. Exercising this needs two processes, and the
signaller must retry Ev$Link - the waiter has to Ev$Creat first, which is a
startup race.

The other six functions - Ev$WaitR, Ev$Read, Ev$Info, Ev$Pulse, Ev$SetR,
Ev$Set - are listed in the manual's table above. `Ev$Pulse` wakes a process
already waiting and puts the value back before it returns, so only a waiter
parked at the moment of the call ever sees the pulsed value. `Live` (os9exec),
all twelve.

## Alarms

**F$Alarm** (d0.l=alarm ID, d1.w=function, d2.l=signal, d3.l=interval,
d4.l=date): subfunctions A$Delete=0, A$Set=1 (one-shot), A$Cycle=2
(periodic), A$AtDate=3 / A$AtJul=4 (absolute Gregorian/Julian). `Live` (os9exec).

**How `d3` is encoded, which decides whether your alarm fires at all**
(`Manual`, v2.4 TRM, F$Alarm and both A$Set/A$Cycle): the interval is a count of
**system clock ticks** - *unless* **bit 31 is set**, in which case the low 31
bits are **256ths of a second**. All times round up to the nearest tick. The
absolute subfunctions read `d3` differently again: **A$AtDate** takes `00hhmmss`
and **A$AtJul** takes seconds after midnight.

That high bit is easy to lose and expensive to lose. A C `alarm()` built on
`secs<<8 | $80000000` is asking for 256ths - which is what the `unix.l` `alarm()`
shipping with the freeware collection does, so `alarm(2)` passes `$80000200`.
Code that drops bit 31 turns the same word into an enormous tick count, and
the alarm **silently never fires** rather than firing early or late; the call
still returns carry clear. `Live` (os9exec): `A$Set` and `A$Cycle` decode bit 31
and round up to the tick, as the manual's NOTE requires (CONF68K t72-t76).

**Two different faults make a ported program's alarm look dead, and fixing one
leaves the other.** A lost bit 31 means the alarm never comes due at all. But a
Unix-compatibility `signal()` may also deliver handlers only on a poll, so even a
correctly armed alarm runs nothing until the program calls `check_signal()` -
that one is a library property, not a kernel property, and is described in
`c/os9-clib-reference.md`. Establish which you have before changing anything:
arm a deadline from **assembly**, or from Microware's own `intercept()`, and you
have removed the library from the question.

**`F$Sleep` shares the high-bit convention but not the rounding rule.** Its page
states none, where `F$Alarm`'s NOTE requires rounding up. Do not rely on a
sub-tick `F$Sleep` returning early: nothing in the manual promises it, and one
implementation rounds up (`Live` (os9exec): `$80000001`...`$80000007` slept 1,
1, 2, 2, 2 and 3 ticks).

**The same high-bit convention appears elsewhere**, so recognise it rather than
learning it per-call: a record-lock timeout uses it too - zero sleeps forever,
one returns an error if the record is not free immediately, and with bit 31 set
the low bits convert from 256ths into ticks, "so that programmed delays are
independent of the system clock rate" (`Manual`, same TRM).

Time-of-day alarms fire at the *corrected* time after a clock adjustment. A
system-state variant runs a kernel subroutine instead of signaling; pending
alarms die with their process, so a persistent one must be requested as the
system process. A firing alarm wakes its own process out of `F$Sleep`,
including an indefinite `F$Sleep(0)`.

## Signals & traps

| Call | Purpose | Notes |
|------|---------|-------|
| **F$Send** | Send signal to a process | **d0.w=receiver PID (0=all), d1.w=signal code**. Kill (0) restricted to same user/group (superuser excepted); other codes unrestricted. PID 0 broadcasts to all same-user/group processes except the sender. A signal sent while an earlier one is still pending joins a FIFO queue for that process `Manual`; Dibble's *OS-9 Insights* §8.9 (third-party) puts a queued send at up to 10× the cost of an unqueued one. `Live` (os9exec) for the order (CONF68K t69) |
| **F$Icpt** | Install signal intercept routine | The manual names only d1.w (signal code) and a6 as set on entry `Manual`. Dibble's *OS-9 Insights* §8.1 (third-party, "An Undocumented Feature") adds that d0.w holds the count of queued signals, counting the one being delivered, so 1 = nothing else waiting; the C `intercept()` wrapper hides it. `Live` (os9exec) (CONF68K t70). No handler installed => any interceptable signal kills the process. `Live` (os9exec) |
| **F$SigMask** | Mask delivery | d1 = +1 increment / -1 decrement / 0 clear-to-zero. Counter is P$SigLvl, an eight-bit level that saturates rather than wraps in either direction (`Manual`: Microware's intermediate training course); keep increments and decrements paired. F$Sleep unmasks internally, making `mask -> sleep(0)` a safe masked wait. `Live` (os9exec) |
| **F$SigReset** | Reset intercept-nesting counter | Needed when `longjmp()` bypasses F$RTE exits |
| **F$RTE** | Return from intercept | Processes queued signals first |
| **F$STrap** | Install error-exception handler | **(a0)=the stack the handler is to run on** (0 = the stack current at the call), (a1)=service table. Error exceptions occupy **vectors 2-8, 10-24, 48-63** and are normally fatal (`Manual`, v2.4 TRM p. 2-31); F$STrap catches those of the group *considered non-fatal*, which p. 1-60 names as bus error, address error, illegal instruction, zero divide, CHK, TRAPV, privilege violation, line 1010 and line 1111 (2-8, 10, 11) plus seven FPCP exceptions (48-54). The manual warns that not all catchable vectors apply to every CPU - 48-54 are 68020/68030 only. Handler entry registers and the resume sequence: `68k/os9-68k-assembly.md`. An F$DFork child's resources survive for post-mortem. `Live` (os9exec) |
| **F$TLink** | Install trap handler | d0.w=trap 1-15, d1.l=memory override, (a0)=module name -> **(a0)=updated past module name**, (a1)=entry, (a2)=header. **Passing (a0)=0, or a name string whose first byte is 0, *unlinks* the handler on that vector** (manual, ch. 14). Links a TrapLib, allocates private static storage, runs its init. Max 15 per process (one per vector); a `tcall` before install can lazily self-install via the module's M$Excpt entry. `(a0)` must be a module *name*, resolved via the same exec-directory search as `F$Link`/`F$Load`, not a bare filename in the data directory. `Live` (os9exec) |
| **F$Sema** | Kernel binary semaphore | OS-9 **v3.0+** only - absent on the v2.4 baseline documented here |

A trap module with no init data, hand-built for os9exec, needs an empty
init table: see "What os9exec does not implement" in
`common/using-os9exec-repl.md`.

## Time

**F$Time** (d0.w=mode: bit0 0=Gregorian/1=Julian, bit1 set=also return
ticks) -> d0.l=packed time, d1.l=packed date, d2.w=day of week (0=Sunday),
d3.l=tick rate/current tick if requested. `Live` (os9exec). **68k returns everything
directly in registers - there is no 6809-style 6-byte buffer pointer.** The
packed field layout inside `d0.l`/`d1.l` is not decoded here; only the
register-slot convention is confirmed.

**F$STime** (d0.l=time, d1.l=date - the input-side mirror of `F$Time`'s
output shape). `Live` (os9exec).

**F$Julian** (d0.l=time as `00hhmmss`, d1.l=date packed as
`(year:16)(month:8)(day:8)` - **not** decimal-digit "yyyymmdd" despite that
doc naming) -> d0.l=seconds since midnight, d1.l=Julian day number.
**F$Gregor** is the inverse. `Live` (os9exec) - a round trip reproduces the original
input bit-for-bit, which pins the register contract without independently
verifying the internal Julian-day epoch.

## Utility

**F$CmpNam** (d1.w=pattern length, (a0)=pattern, (a1)=target -> carry clear
on match): wildcard compare (`?` one char, `*` any string),
case-insensitive - the primitive behind shell wildcard expansion. `Live` (os9exec).
Two details not stated in the manuals: **the target string must be
plain-NUL-terminated** (a literal `0x00` byte), *not* sign-bit-terminated the
OS-9-module-name way despite that convention applying elsewhere in this call
family; and **the pattern is purely length-bounded by `d1.w`**, needing no
terminator of its own. `d1`'s upper word is irrelevant.

**F$PrsNam** ((a0)=path string -> d0.b=terminator character, d1.w=element
length, (a0)=updated past a leading `/` if present, (a1)=address of the last
character of the name +1, i.e. the terminator): parses **one** element per
call, so a multi-element pathlist takes several. `Live` (os9exec).

Valid element characters are `A-Z a-z 0-9 . _ $`. **No character is
"invalid"** - anything else simply terminates the element and is returned as
the delimiter. That is why **`E$BNam` (235) is this call's only possible
error, and a zero-length element is the only way to raise it**; reaching
`E$BNam` at the end of a pathlist is the **documented way a caller's parse
loop ends**, not a fault. 68k BASIC09 depends on exactly that and consumes it
silently (`Live` (os9exec)) - see `basic09/pack-and-runb.md`.

**A leading space is not skipped**, which follows from "no character is
invalid": a blank ahead of the name terminates a zero-length element rather than
being stepped over. `Live` (os9exec). The reason it is worth stating separately
is where the consequence appears - a pathname built with an off-by-one slice,
`" bench.f"`, produced **`E$FNA` (214) from the open** on an RBF device
(under os9exec, `E$BPNam` (215) on a host directory), not a name-parse diagnostic. So a leading blank reads as a *permission* failure on a file that is
present and readable, some distance from the code that built the string. Compare
the 6809 entry, which *does* skip trailing spaces; neither line skips leading
ones, and `I$Open` separately skips **trailing** spaces (see its row above).

On the error path the 68k ERROR OUTPUT specifies carry + `d1.w` and nothing
else, so read nothing else back after `E$BNam`. (os9exec leaves `d0.b`/`a1`
holding the caller's pre-call values, which conforms. `Source`.)

**Do not import the 6809 entry's fuller contract here.** The 6809 System
Programmer's Manual describes this primitive with a trailing comma/space skip
and a meaningful error-path pointer; the 68k line is an *evolution* of that
design, not the same implementation, and the 68k TRM specifies neither. 68k
callers - the shell included - rely on `a1` pointing *at* the terminator,
exactly as the 68k manual says, so adding the 6809 skip would break them.

**F$PErr** (d0.w=path to an **error-message file**, 0=none; d1.w=error code):
writes an error message to the **standard error path**. `d0.w` is *not* a mode
switch - given a path, the kernel searches that ASCII file for a line whose
first seven characters match the error number (`000:215`) and prints the rest
of that line after the number (continuation lines begin with a space); with
`d0.w=0` there is no such file and a stock system prints just
`ERROR #mmm.nnn`. Numbers `000:000`-`063:255` are reserved for the OS.
`Manual`.

`Live` (os9exec): the line honours `>>` redirection, and a `d0.w` path open
on `/dd/SYS/errmsg` prints that file's text. With `d0.w=0` os9exec prints a
named message rather than a bare number: see "Where os9exec departs from the
manuals" in `common/using-os9exec-repl.md`.

## Debugger support

| Call | Purpose | Notes |
|------|---------|-------|
| **F$DFork** | Fork suspended debuggee | F$Fork inputs plus (a2)=register buffer -> child PID + initial register image. Child never runs until F$DExec; the image shows SR with the trace bit set. `Live` (os9exec) |
| **F$DExec** | Drive debuggee | d0.w=PID, d1.l=instruction count (0=free run), d2.w=breakpoint count, (a0)=breakpoint list -> instructions executed, remaining count, exception offset/classification/access address/IR. Syscalls (including through trap handlers and F$Chain) run at full speed as one logical instruction (PC advances by 4). The child resumes from the register buffer, so edits to it take effect (only SR's condition codes are taken from it, not its system byte). A free run that ends in the child's exit returns carry set with `E$PrcAbt` (228). `Live` (os9exec) |
| **F$DExit** | Kill debuggee | Resources survive for post-mortem examination. `Live` (os9exec) |
| **F$SysDbg** | Enter ROM debugger | Used by `break` (superuser, console); halts everything |

## Notes

- **F$SSpd** is marked "currently not implemented" in the v2.4 manual
  (`Manual`). os9exec also leaves `F$Trans` and `F$UAcct` unimplemented: see
  "What os9exec does not implement" in `common/using-os9exec-repl.md`.

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
