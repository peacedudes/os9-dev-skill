# OS-9/6809 System Calls and Module Format

Same OS as 68k — see `common/` for the concepts (module directory,
position-independent code, process states, file manager architecture, error
codes). This file is the 6809-specific *encoding* of those concepts: different
register set, different syscall dispatch, different byte layout.

Most call codes are `Manual`, cross-referenced across 8+ independent primary
sources and internally consistent; ~70 of the ~93 documented `F$`/`I$` calls
are additionally `Live` (NitrOS-9). Rows carry their own tags. Where a
call is marked unimplemented, that is a fact about **this NitrOS-9 build**,
not about OS-9.

## Register Set and Calling Convention

6809 registers: `A`, `B` (or combined `D` = A:B), `X`, `Y`, `U`, `S` (hardware
stack), `DP` (direct page), `CC` (condition codes), `PC`.

All system calls use **`SWI2`** followed immediately by a one-byte function
code (the 6809 analog of 68k's `TRAP #0` + code word). Assembler convenience
macro: `OS9 I$Read` expands to `SWI2` + the code byte.

- **Error convention**: carry set + error code in `B` on error; carry clear on
  success. Registers not specified for a call are unaltered.
- String parameters are terminated by space+EOL, or by the sign bit (bit 7)
  set on the last character — the same sign-bit terminator 68k module names
  use, applied more broadly here.
- Standard I/O paths: 0=stdin, 1=stdout, 2=stderr (same as 68k).
- At process entry (Fork/Chain/debugger `E`): `Y` = top of data memory,
  `U`/`X` = bottom (direct page/data area boundaries depending on source),
  `D` = parameter area size, `PC` = module entry point, `CC` flags F=0, I=0.
- **Command-line parameter area at entry** (`Live` (NitrOS-9)): on a shell fork
  (`progname ARGS`), entry `X` points directly at the argument text with **no
  leading byte** — the raw command tail, multiple arguments space-separated
  verbatim, terminated by a single **CR** (`$0D`). `D` = argument-text-length
  + 1, the +1 being that CR; bare `progname` gives `D`=1, a lone CR. The
  debugger's `E progname ARGS` is the outlier: it prepends a literal space
  (`$20`) before the same text. A program reading its own parameters should
  expect the trailing CR and skip a leading space only if the first byte
  actually is one.

## Syscall Reference

Codes `$00-$1D` are ordinary user-mode `F$` calls (System Programmer's Manual
Appendix C, Table C.1); `$28-$52` are privileged system-mode calls (Table
C.2); `$80-$8F` (plus `$90`, added in a later revision) are I/O `I$` calls.
The `$1E-$27` range is documented in the manual's prose rather than either
summary table — occupied by `F$Alarm`($1E), `F$NMLink`($21), `F$NMLoad`($22),
`F$VIRQ`($27). `$1F`/`$20`/`$23`-`$26` are unconfirmed by any source checked:
treat silence on those four as "unknown", not "free".

### User-mode F$ (process/memory management)

Register contracts below match the System Programmer's Manual §11.1
register-for-register for `F$Fork`, `F$Wait`, `F$ID`, `F$Link`, `F$Load`,
`F$UnLink`, `F$Mem`, `F$CmpNam`, `F$CRC`, `F$Icpt`, `F$Sleep`, `F$PrsNam`.

| Call | Code | Params | Notes |
|---|---|---|---|
| F$Link | $00 | A=type/lang, X=name | Returns A=type/lang, B=attr/rev, X=past name, Y=entry point, U=header addr. **Searches only the resident, in-memory module directory** — fails `E$MNF` (221) against a name that has a real file on disk but was never loaded; it does not fall back to a filesystem search the way `F$Load` does. A=0 is accepted as "any type". `Live` (NitrOS-9) |
| F$Load | $01 | A=lang/type (0=any), X=pathlist | Same returns as Link, applied to the first module in the file. Path resolution follows the **execution**-directory search list, like `F$Fork`, not `I$Open` — a bare name present only in the current *data* directory fails `E$PNNF` (216). `Live` (NitrOS-9) |
| F$UnLink | $02 | U=module header addr | Decrements link count; frees at zero. `Live` (NitrOS-9) |
| F$Fork | $03 | A=lang/type, B=data pages, X=name, Y=param size, U=param start | Returns A=new PID, X=past name. Unlike `F$Link`, resolves via the filesystem — a name with no file behind it fails `E$PNNF` (216), not `E$MNF`. **A caller distinguishing "not loaded yet" from "doesn't exist" must know which of the two calls it used.** `Live` (NitrOS-9) |
| F$Wait | $04 | — | Returns A=child PID, B=exit status. With **no children at all** fails `E$NoChld` (226). `Live` (NitrOS-9) |
| F$Chain | $05 | same as Fork | Reconfigures data area in place; doesn't close open paths. **A failed chain kills the caller**: `fchain.asm` unlinks the old primary module and frees the old DAT blocks *before* linking the new one, then `F$Exit`s (Level 2) / condemns the process (Level 1). So a bad name lands on an already-torn-down process with nothing left to return an error to, and the bare kernel error you see is not the program's. os9exec's 68k `F$Chain` matches exactly. Faithful — do not flag as a bug. `Live` (NitrOS-9) |
| F$Exit | $06 | B=exit status | Deallocates data area, unlinks primary module, closes all paths. **`B` must be explicitly cleared first** or a stale value produces a cosmetic `Error #001 -- Unconditional Abort` after your own output. `Live` (NitrOS-9) |
| F$Mem | $07 | D=new size (0=query) | Returns Y=new upper bound, D=actual size. `Live` (NitrOS-9) |
| F$Send | $08 | A=dest PID (0=all same group), B=signal code | Signal 0=Kill, 1=Wakeup, 2=Abort, 3=Interrupt, rest user-defined (see Signals below). `Live` (NitrOS-9) |
| F$Icpt | $09 | X=intercept routine, U=routine's storage | Handler gets U=storage, B=signal code; exits via RTI. `Live` (NitrOS-9) |
| F$Sleep | $0A | X=ticks (0=indefinite) | Returns X=remaining ticks; woken early by signal. `Live` (NitrOS-9), `Flag`: `X=50` returned `remaining=23` with no signal sent, so the returned remainder does not simply mean "woken early" — treat `F$Sleep` timing precision as unverified |
| F$ID | $0C | — | Returns A=PID (1-255), Y=user ID (0-65535). `Live` (NitrOS-9) — A confirmed; Y not independently re-confirmed. **The 6809 user ID is one flat integer, NOT 68k's packed `group.user`** — see the cross-target warning below |
| F$SPrior | $0D | A=PID, B=priority (0=lowest, 255=highest) | Same-user rule; superuser can set any. `Live` (NitrOS-9) |
| F$SSWI | $0E | A=vector (1=SWI, 2=SWI2, 3=SWI3), X=routine | Per-process vector, not global. `Live` (NitrOS-9) for the install call; **whether the handler then runs on a bare `SWI` is unconfirmed** — a test using `F$Icpt`'s plain-`RTI` exit convention never saw its marker set, and `F$SSWI`'s raw hardware-vector mechanism may have a different, undocumented entry/exit convention |
| F$PErr | $0F | B=error code | Writes to the standard error path. A stock system prints a bare `ERROR #<decimal>`, but **the reporting routine is vectored and replaceable by design** — freely on Level 1; on Level 2 only system-wide, and Microware shipped no Level 2 replacement. So NitrOS-9's fuller `Error #216 - Path Name Not Found` line is that documented extensibility in use, **not** undocumented richness. `Manual` + `Live` (NitrOS-9) |
| F$PrsNam | $10 | X=pathlist | One name per call. Returns X past a leading `/`, Y=address of last name char +1, A=delimiter byte, B=count. Terminates on any non-component character **or a set high-order bit**, and **skips one trailing comma or any number of trailing spaces**. `E$BNam` is the only error and is the **documented end-of-pathlist signal** — "if X was at the end of a pathlist, a bad name error will be returned"; **on that error `Y` is still returned**, advanced past spaces/commas so the next pathlist in a command can be parsed. `Manual` (6809 System Programmer's Manual, §11.1.14 — notably fuller than the 68k TRM's entry); `Live` (NitrOS-9) for call success only, returned values unverified. **6809-only: do not carry the trailing skip or the error-path `Y` over to 68k** — the 68k line evolved from this design and its TRM specifies neither, so this row is not evidence about os9exec. See `68k/syscall-reference.md` |
| F$CmpNam | $11 | B=length, X/Y=two strings | Carry clear if match; second string sign-bit terminated. `Live` (NitrOS-9), `Flag`: two identical 4-byte strings with a *separate* trailing sign-bit byte returned carry SET. Plausibly the terminator must be the sign bit baked into the last real character (as `fcs` produces) rather than an extra byte — unconfirmed either way |
| F$SchBit | $12 | D=start bit, X=map, Y=count, U=map end | Searches allocation bitmap for a free block. `Source` (NitrOS-9 `fallbit.asm`): returns D=where the found run starts, Y=how many free bits it spans — neither previously documented. `Live` (NitrOS-9), `Flag`: the call succeeds against a zeroed 64-bit local map but the D/Y values read back are not sane start/length numbers for that input |
| F$AllBit | $13 | D=first bit, X=map, Y=count | Sets bits (marks allocated). `Live` (NitrOS-9) — confirmed by reading the map bytes back |
| F$DelBit | $14 | D=first bit, X=map, Y=count | Clears bits (marks free). `Live` (NitrOS-9) |
| F$Time | $15 | X=6-byte buffer | year/month/day/hour/min/sec. **The year byte is `year - 1900`**, not a raw or 2-digit value. `Live` (NitrOS-9) |
| F$STime | $16 | X=6-byte packet | Also starts the real-time clock. `Live` (NitrOS-9) — FAILED with `err=00000`, which is not a real OS-9 error number, suggesting the call may not populate `B` on failure. Unresolved |
| F$CRC | $17 | X=start, Y=count, U=3-byte accumulator | Accumulator must init to `$FFFFFF`. `Live` (NitrOS-9) for the call; the checksum algorithm itself was not checked against a known-answer reference |
| F$GPrDsc | $18 | A=PID, X=512-byte buffer | Copy of process descriptor. `Live` (NitrOS-9) |
| F$GBlkMp | $19 | X=1024-byte buffer | Returns D=block size (commonly `$2000`=8K), Y=map size. `Live` (NitrOS-9), `Flag`: call succeeds but D/Y come back nowhere near the documented values |
| F$GModDr | $1A | X=2048-byte buffer | Copy of module directory; returns Y=copy-end addr, U=system module-dir start addr. **Source-corrected**: NitrOS-9's `fgmoddr.asm` writes Y and U rather than reading them — the previously documented shape had them backwards as inputs. `Live` (NitrOS-9) |
| F$CpyMem | $1B | D=DAT ptr, X=offset, Y=count, U=dest | Reads another process's memory via its DAT image (Level 2). `Source, Flag`: NitrOS-9's `fcpymem.asm` never reads X — the copy is driven by D, Y and U alone, a 3-register call. That file's *own* header comment still states the 4-register shape, so it is stale relative to its own code. Whether NitrOS-9 dropped the offset parameter or the manual was never accurate is undetermined; the manual's shape is kept here with this note. `Live` (NitrOS-9) for a trivial self-referential copy |
| F$SUser | $1C | Y=user ID | Sets caller's user ID. `Live` (NitrOS-9) |
| F$UnLoad | $1D | A=type, X=name | Unlink by name instead of address. `Live` (NitrOS-9) — FAILED `E$MNF` (221) immediately after the same name was successfully `F$Load`ed by the same process. Possibly `A=type` is not literally the type/lang byte `F$Load` returns in `A`. Unresolved |

### Cross-target trap: the 6809 user ID has no group field

**On 6809 the user ID is a single flat integer, 0-65535, and the superuser is
ID 0 outright.** The System Programmers Manual says both: F$ID (11.1.9,
p.81) describes "the user ID which is a integer in the range 0 to 65535",
and F$Send's notes name "the superuser (ID number 0)". Ownership fields
(`FD.OWN`, `DD.OWN`) are 2-byte user numbers, not packed pairs.

**68k is the divergence, not 6809.** There a user ID is `group<<8 | user`
and the superuser is *any* user in group zero — so the 68k test "is the high
byte zero?" applied on 6809 declares every ID below 256 to be the superuser,
i.e. essentially every ordinary account. `Live` (NitrOS-9): a guard written
that way SKIPped every account on a NitrOS-9 disk whose password file uses
flat IDs 0-4. Compare the **whole 16-bit value** against 0 on 6809.

This is the same shape as the `attr` set/clear inversion: both entries are
right for their own target, and the trap is carrying one target's model
across. For os9exec (68k) read the 68k manuals — 6809 is an earlier
evolutionary stage, not a fuller description of the same design.

**Consequence when a 68k tool builds a disk a 6809 will read** (`Live`,
2026-07-25): the on-disk owner field is two bytes on both targets, so the
bytes travel fine — but the two targets *interpret* them differently.
os9exec stamping account `1.7` writes `$0107`; the same file on 6809 is
owned by flat user **263**. Neither reading is zero, so a non-privileged
owner stays non-privileged and public permission bits still govern, which
is usually all that matters. Two things do bite:

- **A host-side check written against the 68k model misjudges the 6809
  one.** ToolShed's `dir -e` splits the flat value into two dot-separated
  bytes for display, so an ordinary 6809 ID below 256 shows as `0.N` and
  looks like a group-zero superuser. Assert the owner field is **non-zero**
  rather than testing a "group" byte that only one target has.
- **Ownership is not portable as a name, only as a number.** Do not expect
  an account on the receiving system to match; design for the public bits.

### Mixed range ($1E-$27)

Registers here come from the OS-9 Technical Reference (Tandy)'s per-call
Entry/Exit listings; the System Programmer's Manual doesn't cover this range.

| Call | Code | Params | Notes |
|---|---|---|---|
| F$Alarm | $1E | D=mode (`0`=clear, `1`=system-wide, `2`=query, any PID=arm for that process), X=addr of a 5-byte time packet (read only when arming) | Sets a timed signal for the caller — a 15-second bell ring at the specified time, using `F$STime`'s time-packet layout. Only whole-minute alarms are honored; at most one alarm pending at a time. `Live` (NitrOS-9): D genuinely acts as a mode selector — `D=0` and `D=2` both returned cleanly with X unset, while `D=99` failed, under identical unset-X conditions. Confirms NitrOS-9's `clock.asm` over the Technical Reference's silence on the D-register mode byte. `D=1` (arm) and PID-targeting untested — arming a real alarm risks an async signal into a shared session |
| F$NMLink | $21 | A=type/lang, X=name ptr | Like `F$Link` but doesn't map the module into the caller's address space — returns A=type/lang, B=revision, X=past name, Y=memory requirement, so a process can size a fork before committing. `Live` (NitrOS-9) |
| F$NMLoad | $22 | A=type/lang, X=pathlist ptr | Like `F$Load` without mapping; same returns as `F$NMLink`. Without a full pathlist, loads from the current execution directory. `Live` (NitrOS-9) |
| F$VIRQ | $27 | Y=addr of a 5-byte packet (install) or match key (delete), X=0 (delete) or nonzero (install), D=initial tick count (install only) | Installs/removes a virtual (software-polled) interrupt handler; no output beyond carry/error. Packet layout: `Vi.Cnt`($0, 2 bytes)=live counter, `Vi.Rst`($2, 2 bytes)=reset value, `Vi.Stat`($4, 1 byte)=status (bit 0 set when the VIRQ fires, bit 7 set if the counter should reset instead of one-shot). `Source` (NitrOS-9 `clock.asm`) matches the Technical Reference exactly, including delete-by-matching-Y. `Live` (NitrOS-9) for both install and delete |

### Privileged system-mode F$ ($28-$52)

Kernel-internal; listed for completeness, not for ordinary programs. Codes are
`Manual`, cross-confirmed across two independent listings. Params come from
the System Programmer's Manual §11.2/12.1; `F$NProc`, `F$SRqMem`, `F$AllImg`,
`F$AllPrc`, `F$AllRAM`, `F$AllTsk` and `F$Move` were diffed against those
listings and match register-for-register.

Many of these are **unimplemented on this NitrOS-9 build**, returning
`E$UnkSvc` (208) — a consistent pattern, not per-call mystery, and a fact
about the build rather than about OS-9.

| Call | Code | Params | Level 2? | Notes |
|---|---|---|---|---|
| F$SRqMem | $28 | D=byte count | | Allocates memory, rounded up to the next page; returns D=granted size, U=block addr; error E$MemFul. `Live` (NitrOS-9) — unimplemented (`E$UnkSvc`) |
| F$SRtMem | $29 | U=block addr, D=byte count | | Deallocates a contiguous, page-aligned block; U must land on a page boundary or error E$BPAddr. Untested — `F$SRqMem` fails first |
| F$IRQ | $2A | D=status-reg addr, X=0 (remove) or control-packet addr, Y=service routine, U=static storage | | Add/remove device from IRQ table; control packet at [X]: flip byte, [X+1]=mask byte, [X+2]=priority (0-255); error E$Poll. Real drivers throughout the NitrOS-9 tree call it, so it is implemented |
| F$IOQu | $2B | A=process number | | Enter I/O queue: links caller into another process's I/O queue and sleeps untimed pending a wakeup signal; used heavily by IOMAN/file managers |
| F$AProc | $2C | X=process descriptor addr | | Insert process in active process queue; ages already-queued processes and sets the new one's age to its priority |
| F$NProc | $2D | — | | Start next process: pulls the next entry off the active queue and transfers control to it (no return to caller); waits for an interrupt and rechecks if the queue is empty. Caller must already be queued, or it becomes invisible to the scheduler though `Procs` still shows its descriptor |
| F$VModul | $2E | LI: X=new module addr. LII: D=DAT image ptr, X=module block offset | | Checks header parity/CRC, then on a same-name/type collision keeps the higher revision (ties favor the already-resident module); returns U=module directory entry addr; errors E$KwnMod/E$DirFul/E$BMID/E$BMCRC (+E$BMHP on LII only). `Live` (NitrOS-9) — unimplemented (`E$UnkSvc`) |
| F$Find64 | $2F | A=block number, X=base-page addr | | Find a 64-byte memory block by number (numbered 1..N); returns Y=block addr. Untested — depends on `F$All64` |
| F$All64 | $30 | X=page-table base addr (0=allocate a new base page) | | Splits 256-byte pages into four 64-byte sections (the first section is a page table holding each page's MSB); returns A=block number, X=page-table base, Y=block addr; error E$PthFul. The first byte of each block holds its own block number — don't overwrite it. `Live` (NitrOS-9) — unimplemented (`E$UnkSvc`) |
| F$Ret64 | $31 | A=block number, X=base-page addr | | Deallocates a 64-byte block. Untested — depends on `F$All64` |
| F$SSvc | $32 | Y=addr of a system-call init table | | Adds or replaces an entry in the kernel's dispatch table so a custom handler takes over a chosen function code. Y's table is a repeating sequence — function-code byte, then a 2-byte offset to the handler relative to the entry's own 3rd byte — terminated by a lone `$80`. A function code with its high bit set patches the *system*-mode dispatch table only; clear, it patches *both* system and user tables. `Source` (NitrOS-9 `fssvc.asm`) — the terminator byte and the table split appear in no manual checked |
| F$IODel | $33 | X=I/O module addr | | Deletes an I/O device if its use count is zero; error E$ModBsy if busy. LI runs the driver's Term routine here, LII defers it to `DETACH`. `Source` (NitrOS-9 `ioman.asm`): the mechanism is a scan of the live device table for any entry still pointing at the module, not a literal reference count |
| F$SLink | $34 | A=module type, X=name ptr, Y=DAT image ptr for the name | | Link by name to a module already in the system's address space; returns A=type, B=rev, X=past name, Y=entry point, U=module ptr. `Live` (NitrOS-9) — unimplemented (`E$UnkSvc`) |
| F$Boot | $35 | — | | Bootstrap system: links and calls the Boot module (or the one named in `INIT`) |
| F$BtMem | $36 | D=byte count | | Contiguous, block-rounded bootstrap memory request; returns D=granted count, U=block addr. **Deprecated since Level 2 v1.2** — equated to `F$SRqMem`. `Live` (NitrOS-9) — unimplemented (`E$UnkSvc`), matching `F$SRqMem`, consistent with the two being equated |
| F$GProcP | $37 | A=PID | Yes | Translates a PID to its process descriptor's address *in system address space* — only meaningful with more than one address space; returns Y=descriptor ptr. `Source` (NitrOS-9 `fgprocp.asm`): the return register is unambiguously Y, a full 16-bit address. `Live` (NitrOS-9) — unimplemented (`E$UnkSvc`) |
| F$Move | $38 | A=src task#, B=dest task#, X=src ptr, Y=count, U=dest ptr | Yes | Moves data between two address spaces (two DAT task mappings) — meaningless on single-address-space Level 1. `Live` (NitrOS-9) — unimplemented (`E$UnkSvc`) |
| F$AllRAM | $39 | B=block count | | Allocate RAM blocks; returns D=beginning block number. The manual documents `F$DelRAM` as operating on blocks with no DAT-image association, confirming this pair isn't Level-2-exclusive. `Live` (NitrOS-9) |
| F$AllImg | $3A | A=begin block#, B=block count, X=process descriptor ptr | Yes | Allocates RAM blocks for a process's DAT image. `Live` (NitrOS-9) — unimplemented (`E$UnkSvc`) |
| F$DelImg | $3B | A=begin block#, B=block count, X=process descriptor ptr | Yes | Frees a process's DAT image. Untested |
| F$SetImg | $3C | A=begin image block#, B=block count, X=process descriptor ptr, U=new image ptr | Yes | Writes a process's DAT image into its descriptor; sets the image-change flag so hardware DAT updates on return. `Live` (NitrOS-9) — unimplemented (`E$UnkSvc`) |
| F$FreeLB | $3D | B=block count, Y=DAT image ptr | Yes | Searches a DAT image for a free low block; returns A=beginning block#. Untested — needs a working `F$AllPrc` descriptor |
| F$FreeHB | $3E | B=block count, Y=DAT image ptr | Yes | Searches a DAT image for a free high block; returns A=beginning block#. Untested, same reason |
| F$AllTsk | $3F | X=process descriptor ptr | Yes | Allocates a DAT task number if not already assigned, then copies the DAT image into DAT hardware. Untested, same reason |
| F$DelTsk | $40 | X=process descriptor ptr | Yes | Deallocates a DAT task number. Untested, same reason |
| F$SetTsk | $41 | X=process descriptor ptr | Yes | Writes the DAT image into the hardware task registers; clears the image-change flag. Untested, same reason |
| F$ResTsk | $42 | — | Yes | Reserves a free DAT task number; returns B=task number. `Live` (NitrOS-9) — unimplemented (`E$UnkSvc`) |
| F$RelTsk | $43 | B=task number | Yes | Releases a DAT task register. Untested — depends on `F$ResTsk` |
| F$DATLog | $44 | B=DAT-image block index, X=block offset | Yes | Converts a DAT block/offset pair to a logical address; returns X=logical addr. `Live` (NitrOS-9) — unimplemented (`E$UnkSvc`) |
| F$DATTmp | $45 | D=block number | Yes | Builds a throwaway DAT image scoped to one memory block, for a one-off access without a full task/image setup; returns Y=DAT image ptr. `Live` (NitrOS-9) — unimplemented (`E$UnkSvc`) |
| F$LDAXY | $46 | X=block offset, Y=DAT image ptr | Yes | Load A from `[X,[Y]]` — cross-task memory access primitive; returns A=data byte; no bounds check. `Live` (NitrOS-9) — unimplemented (`E$UnkSvc`) |
| F$LDAXYP | $47 | X=block offset, Y=DAT image ptr | Yes | Load A from `[X+,[Y]]` (post-increment variant); returns A=data byte, X=incremented. `Live` (NitrOS-9) — unimplemented (`E$UnkSvc`) |
| F$LDDDXY | $48 | D=offset-to-the-offset, X=offset within DAT image, Y=DAT image ptr | Yes | Load D from `[D+X,[Y]]`; returns D=2 bytes; offsets relative to the first block the DAT image points to. `Live` (NitrOS-9) — unimplemented (`E$UnkSvc`) |
| F$LDABX | $49 | B=task#, X=data ptr | Yes | Load A from `0,X` in task `B`; returns A=data byte. `Live` (NitrOS-9) — unimplemented (`E$UnkSvc`) |
| F$STABX | $4A | A=data byte, B=task#, X=logical addr | Yes | Store A at `0,X` in task `B`. `Live` (NitrOS-9) — unimplemented (`E$UnkSvc`) |
| F$AllPrc | $4B | — | Yes | Allocates a 512-byte process descriptor (first 256 bytes cleared, system state set, up to 60-64K of DAT image marked unallocated); returns U=descriptor ptr. `Live` (NitrOS-9) — unimplemented (`E$UnkSvc`). Every descriptor-dependent call above was therefore only reachable with an unreal descriptor |
| F$DelPrc | $4C | A=process ID | | Deallocates a process descriptor — architecture-generic on its face, but internally calls the Level-2-only `F$DelTsk`. Deliberately untested: the only PID available to pass is the caller's own live one, making this a self-termination risk rather than a bounded experiment |
| F$ELink | $4D | B=module type, X=ptr to module directory entry | | Links via a module directory entry pointer rather than by name; returns U=header addr, Y=entry point. Untested — needs a pointer from `F$VModul`, which fails first |
| F$FModul | $4E | A=module type, X=name ptr, Y=DAT image ptr for the name | | Finds a module directory entry by name/type (type 0 matches any); returns A=type, B=rev, X=past name, U=directory entry ptr. Internally calls the Level-2-only `F$DATLog`/`F$LDAXY`/`F$LDDDXY`. `Live` (NitrOS-9) — unimplemented (`E$UnkSvc`) |
| F$MapBlk | $4F | B=block count, X=beginning block# | Yes | Maps blocks into a process's DAT-mapped address space via `F$FreeHB`/`F$SetImg`, from the top down into the highest available addresses; returns U=addr of first block. `Live` (NitrOS-9) — **genuinely implemented**, unlike most of its Level-2-flagged siblings here |
| F$ClrBlk | $50 | B=block count, U=addr of first block | Yes | Marks blocks unallocated in a process's DAT image. Untested — the one attempt passed a bogus `U` and its `E$IBA` result says nothing |
| F$DelRam | $51 | B=block count, X=starting block# | | Deallocate RAM blocks. `Live` (NitrOS-9) — freeing exactly the block `F$AllRAM` granted |
| F$GCMDir | $52 | none | | Squeezes out gaps in the module directory's entry list. Takes no register parameters at all — reserved for the kernel's own use, not for application code. Absent from the System Programmer's Manual's Table C.2, which ends at `F$DelRam`/$51 |

**Also real, code not confirmed:** `F$AllHRam` ("Allocate High RAM" — like
`F$AllRAM` but searching from the top of memory down, used by
screen-allocation routines) is `Manual` across three independent sources, but
none gave a legible machine code, so it is omitted from the table rather than
guessed.

**Level-2-exclusive vs. universal:** the calls marked "Yes" all explicitly
manipulate a DAT image, a DAT task register, or an inter-address-space
transfer in their own primary-source description — none of which means
anything on a Level 1 system, with one unshared 64K address space and no task
registers. `F$Boot`/`F$SUser`/`F$UnLoad` are plain bootstrap/user-ID/unlink
operations with no DAT dependency.

### I/O I$ calls

Register contracts match the System Programmer's Manual §11.3
register-for-register for `I$Open`, `I$Create`, `I$Delete`, `I$MakDir`,
`I$ChgDir`, `I$Read`/`I$Write`, `I$ReadLn`, `I$Seek`, `I$GetStt`/`I$SetStt`.

| Call | Code | Params | Notes |
|---|---|---|---|
| I$Attach | $80 | A=access mode, X=device name | Returns U=device table entry. `Live` (NitrOS-9) |
| I$Detach | $81 | U=device table entry | Calls driver Term, deallocates if unused elsewhere. `Live` (NitrOS-9) — against a device still in use elsewhere it correctly adjusted a use count rather than tearing anything down |
| I$Dup | $82 | A=path | Returns new path number (lowest available), same underlying file. `Live` (NitrOS-9) |
| I$Create | $83 | A=mode, B=attributes, X=pathlist | Returns A=path number; error if the file exists. `Source`, two-layer dispatch: NitrOS-9's `ioman.asm` shares one dispatcher between `I$Open`/`I$Create` that touches only A and X, leaving B untouched as it hands off to the file manager — RBF's own `Create` reads B as file attributes. `Live` (NitrOS-9) |
| I$Open | $84 | A=access mode, X=pathlist | Returns A=path number. Requires an **existing** file — fails `E$PNNF` (216) against a nonexistent name; it does not create-on-open the way some Unix `open()` flag combinations do. `Live` (NitrOS-9) |
| I$MakDir | $85 | B=attributes, X=pathlist | Auto-creates `.` and `..` entries. `Source`: NitrOS-9's `rbf.asm` implements MakDir as a thin wrapper over Create (same B contract) that sets the directory bit afterward. `Live` (NitrOS-9) |
| I$ChgDir | $86 | A=mode (1/2/3=data, 4=exec), X=pathlist | `Live` (NitrOS-9) — confirmed effective, not merely accepted: a subsequent bare-name `I$Create` resolved relative to the new directory |
| I$Delete | $87 | X=pathlist | Requires write permission. `Live` (NitrOS-9) |
| I$Seek | $88 | A=path, X=high 16 bits, U=low 16 bits of the 32-bit position | Random access (RBF) or cursor position (SCF). The register pair is **X:U** — the System Programmer's Manual (11.3.14) documents exactly this split, NitrOS-9's RBF `Seek` reads it the same way (`Source`), and `Live` (NitrOS-9) confirms it. **Trap when writing this call**: `U` is commonly also a program's own U-relative data-area base pointer — save it (`pshs u`/`puls u` around the `swi2`) or every later `,u`-relative reference breaks silently |
| I$Read | $89 | A=path, X=buffer, Y=count | Returns Y=actual bytes; EOF error at end. A path number that was never opened fails `E$BPNum` (201), so path numbers are validated rather than trusted. `Live` (NitrOS-9) |
| I$Write | $8A | A=path, X=buffer, Y=count | Past-EOF write expands the file. **Returns Y** — the actual byte count written. `Live` (NitrOS-9) |
| I$ReadLn | $8B | A=path, X=buffer, Y=max | Reads to CR, with line editing. **The returned length in `Y` includes the CR terminator** (`Live` (NitrOS-9)) — which diverges from BASIC09's own `READ`/`LEN()` (also `Live` (NitrOS-9)), where it does not. Code carrying a count between syscall and BASIC09 semantics needs an explicit off-by-one adjustment |
| I$WritLn | $8C | A=path, X=buffer, Y=max | Writes to first CR; SCF adds LF/CR/nulls as configured. `Live` (NitrOS-9) |
| I$GetStt | $8D | A=path, B=function code | Device-dependent; see GETSTAT/SETSTAT below. `Live` (NitrOS-9) for the call — `B=6` (SS.EOF) and `B=2` (SS.SIZ) both accepted cleanly. **The SS.SIZ return-value convention is NOT confirmed**: the size did not come back in X:U (`I$Seek`'s convention), and X most likely just went untouched |
| I$SetStt | $8E | A=path, B=function code | |
| I$Close | $8F | A=path | Implicit Detach. `Live` (NitrOS-9) |
| I$DeletX | $90 | A=access mode (1/2/3=data, 4=exec), X=pathlist | Added in Rev F1 (1983); delete with explicit directory selection. `Live` (NitrOS-9) |

Common GETSTAT/SETSTAT function codes (`Manual`, against the System
Programmer's Manual §11.3 GetStat table, whose canonical spellings are
`SS.Opt`/`SS.Ready`/`SS.Size`/`SS.Pos`/`SS.EOF`): 0=option section (`SS.OPT`,
read/write raw path descriptor options), 1=`SS.RDY` data-ready test (SCF),
2=`SS.SIZ` file size, 5=`SS.POS` file position, 6=`SS.EOF` test. Two more the
CoCo work rarely needs: `SS.DevNm` ($E, return device name — IOMAN) and
`SS.FD` ($F, read file-descriptor sector — RBF, Level II). Record locking
added `SS.Lock`/`SS.Ticks` (setstat) in Rev F1. CoCo adds `SS.Mouse` ($89 as a
GetStat sub-function) — see `coco-dragon-hardware.md`.

## Calls that can end the session that makes them

These are safe to *document* and hazardous to *call*, so they resist scripted
testing. The risk is the reason — a call whose risk you can design around is
fair game, and two of them are shown below.

| Call | Risk |
|---|---|
| `F$Boot` | Reboots. Ends the session outright |
| `F$AProc`, `F$NProc` | Scheduler-internal — queue a process or switch to the next one; may never return to the caller |
| `F$DelPrc` | Terminates a process by ID; trivially self-terminating |
| `F$GCMDir` | Explicitly kernel-only in its own description |
| `F$IOQu` | Untimed wait on an I/O queue — hangs with nothing to time it out |
| `F$IRQ`, `F$IODel` | Manipulate real hardware interrupt vectors/device tables |
| `F$SSvc` | Patches the live syscall dispatch table |
| `I$SetStt` | Can disrupt the very channel the test is driven over |
| `F$Chain` | Looked unsafe on failure — see below |

The last two are reachable if the call is fenced rather than avoided:

- **`I$SetStt`** — `I$GetStt` first to save the setting, set, confirm,
  restore, re-confirm. A wedged terminal then costs only a REPL restart.
- **`F$Chain`** — confine the blast radius to a child. The parent forks a
  child; the child prints a marker, chains to a module that fails, then prints
  a second marker; the parent `F$Wait`s. The second marker says whether
  control returned to the caller at all, and the wait status says what the
  parent sees. Do not assume it returns: on a failed chain, both 6809 and
  os9exec have produced a raw uncontrolled error instead of handing control
  back, so a caller that plans to recover from a bad chain needs to verify
  that it can.

## Signals

Same design as 68k (numbered codes, tiny non-reentrant handlers, `F$Sleep`
auto-unmask pattern — see `common/ipc.md`), with 6809-specific numbering:

- 0 = Kill (uninterceptable), 1 = Wakeup (does not invoke the intercept
  routine), 2 = Abort (Ctrl-E), 3 = Interrupt (Ctrl-C). Sources disagree on
  where the user-definable range starts (some say 4-255, one CoCo-specific
  source says 128-255), but `Live` (NitrOS-9): codes 50 and 200 sent to a process with an
  installed `F$Icpt` handler were delivered identically, with the correct code
  in `B` both times. **The "reserved" language is a documentation convention;
  the kernel enforces no boundary within 4-255 on delivery.**
- A signal with no installed handler kills the process unless the code is 0 or 1.
- If a process already has an unprocessed signal pending, `F$Send` to it
  fails — the sender should `F$Sleep` briefly and retry.

## Module Header

Much smaller than 68k's 48-byte universal section: **9 bytes minimum**.
`Manual`, matching the *OS-9 System Programmer's Manual* §4.2 field-for-field.

| Offset | Size | Field | Notes |
|---|---|---|---|
| $00-$01 | 2 | Sync | `$87,$CD` — illegal/reserved 6809 opcodes, the 6809 analog of 68k's `$4AFC` (`Source`) |
| $02-$03 | 2 | Module size | Total including CRC |
| $04-$05 | 2 | Name offset | Sign-bit-terminated string, can sit anywhere in the module body |
| $06 | 1 | Type/Language | High nibble = type, low nibble = language (see below) |
| $07 | 1 | Attributes/Revision | Bit 7 = reentrant/sharable, low 4 bits = revision (0-15) |
| $08 | 1 | Header parity | One's-complement XOR of the preceding 8 bytes |

Program/Subroutine modules (type $1/$2) have 4 more bytes: $09-$0A execution
offset (relative to the sync byte), $0B-$0C permanent storage requirement
(minimum data area size). `Live` (NitrOS-9): in a real assembled Program module the name
field lands at offset `$000D` — exactly 9 generic + 4 Program-type bytes.

**Type codes** (high nibble of byte $06): $1=Program, $2=Subroutine,
$3=Multi-module, $4=Data, $5-$B=user-defined, $C=System, $D=File Manager,
$E=Device Driver, $F=Device Descriptor. $0 is illegal.

**Language codes** (low nibble): 0=Data (non-executable), **1=6809 object
code**, 2=BASIC09 I-code, 3=Pascal P-code, 4=C I-code, 5=COBOL I-code,
6=FORTRAN I-code (the last three reserved/unimplemented).

The type/attribute byte encoding (`Prgrm`=$10, `Objct`=1, `ReEnt`=$80) is
`Source` — from the real `DEFS/os9defs.a` and independently via `ident`'s
decode of real system modules.

**CRC**: 24-bit, polynomial `$800FE3`, one's-complement-accumulator mechanism.
Initialize the accumulator to `$FFFFFF`, process every byte from header start
through the byte before the CRC, then complement before storing. A valid
module's CRC re-verified — including its own CRC bytes — yields `$800FE3`.

Module directory and linking semantics (name lookup, link-count sharing,
highest-revision-wins on name collision, ROM auto-scan for the sync pattern at
cold start) are identical in concept to 68k — see
`common/os9-mental-model.md`.

## C Compiler

`int` is **16-bit** on the 6809 compiler (32-bit on 68k). Direct-page
addressing via the `DP` register is 6809-only — a reliable marker for telling
6809-specific content from 68k.

---

**Sources:** OS-9 System Programmer's Manual (and its Rev F1/1983 errata),
OS-9 Level Two Operating System Manual, OS-9 Technical Reference (Tandy/CoCo),
two independent OS-9 Users Guides (1983), OS-9 Quick Reference (CoCo, 1992
FARNA Systems).

Source call codes from the System Programmer's Manual's Appendix C
(Tables C.1/C.2) or the Rev F1 errata — **never** from that manual's inline
prose cross-references, which contain wrong values. Its main scan also carries
OCR damage that prints duplicate codes (`$18`, `$3B`, `$4B` each appear twice,
and `$8E` misreads as `$BE`); in each case a second Microware source settles
it — F$CpyMem `$1B`, F$FModul `$4E`, F$DelImg `$3B` (SPM Rev F1); I$SetStt
`$8E`, F$VModul `$2E` (OS-9 Technical Reference, Tandy). The table agrees with
Microware throughout; only the one damaged scan disagrees with itself.
