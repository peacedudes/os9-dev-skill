# OS-9/6809 System Calls and Module Format

**Mostly `Manual`; a growing set of facts `Live`/`Source`**
(tracking: `6809/STATUS.md`): the module type/attribute byte
encoding (`Prgrm`=$10, `Objct`=1, `ReEnt`=$80) is `Source` (both the
real `DEFS/os9defs.a` on the EOU disk and independently via `ident`'s
decode of real system modules); **`I$WritLn`=$8C and `F$Exit`=$06 are
`Live`, not just `Manual`** — a real assembled
program using `SWI2`+`fcb $8C` actually printed its message to the
console, and `SWI2`+`fcb $06` (with `B` explicitly cleared first — an
uninitialized `B` produces a cosmetic `Error #001 -- Unconditional Abort`
after your own output, unrelated to whether the call itself worked) exited
cleanly with no residual module left in `mdir`. Full repro in
`assembly-and-tools.md`. **`F$Icpt`=$09, `F$Send`=$08, and `F$ID`=$0C are
also now `Live`** — see the Signals section below for the
reserved-signal-range test that exercised all three together.

**2026-07-19: `F$Link`, `F$UnLink`, `F$Fork`, `F$Wait`, `F$Time`,
`I$Open`, `I$Close`, `I$Read`, and `I$Write` are now `Live` too** — full
success- and failure-path register-contract tests in
`test/6809-live-verification/syscall-flink-ffork-fwait.a` and
`syscall-ftime-iread-iwrite.a` (os9exec repo), designed as a re-runnable
regression suite (each assertion prints its own `PASS`/`FAIL` line).
Real, previously-undocumented facts this pass turned up: `F$Time`'s year
byte is `year-1900`; `I$Write` does return `Y` (byte count written);
`F$Link` (resident-module-directory search only) and `F$Fork` (does its
own filesystem load, like `F$Load`) fail with *different* error codes
against an unresolvable name (`E$MNF`/221 vs. `E$PNNF`/216
respectively) — a caller needs to know which call it used to know which
error means what; `F$Wait` with no children fails `E$NoChld`/226. The
specific numeric codes for every other call in the tables below, and the
full module-header byte layout beyond type/attribute, remain `Manual`
(cross-referenced across 8+ independent primary sources: System
Programmers Manual and its Rev F1 errata, Level 2 manuals, a Tandy/CoCo
Technical Reference, two Users Guides, a Quick Reference) and internally
consistent — real signal, but not yet individually `Live` the way 68k's
syscall table has been.

**Same day, second batch: `I$Create`, `I$MakDir`,
`I$ChgDir`, `I$Delete`, `I$Seek`, `I$GetStt` (call confirmed; its SS.SIZ
return-value register convention is not — see that entry), `F$Mem`,
`F$Sleep`, `F$SPrior`, and `F$CRC` are `Live` too** —
`test/6809-live-verification/syscall-imakdir-ichgdir-icreate-idelete.a`,
`syscall-iseek.a`, `syscall-igetstt.a`, and
`syscall-fmem-fsleep-fsprior-fcrc.a` (os9exec repo). `I$Seek` confirms the
`Source`-flagged X:U 32-bit position convention live (not just from
reading NitrOS-9's own code). A further batch
(`test/6809-live-verification/batch3-01.a` through `batch3-03.a`)
exercised `F$PrsNam`/`F$CmpNam`/`F$PErr`/`F$SchBit`/`F$AllBit`/`F$DelBit`/
`F$GPrDsc`/`F$GBlkMp`/`F$GModDr`/`F$GProcP` — most confirmed cleanly,
`F$CmpNam` and `F$SchBit`/`F$GBlkMp` produced results that diverge from a
naive reading of the docs and are flagged inconclusive rather than
asserted either way (see each row), and `F$GProcP` genuinely failed
(`err=00208`, uninvestigated). A fourth file (`batch3-04.a`,
`I$Dup`/`I$WritLn`/`I$DeletX`) hit a genuine permission wall at first
(`synctest.dat` really is owned by someone other than the session's
default identity — public-read only, no public-write) — resolved by
logging in explicitly (**this NitrOS-9 disk's password file has no
`claude` account, only an unnamed UID-0 entry and `USER1`-`USER4`; use
`login USER1` for any 6809 test session going forward**, not the
unauthenticated default) and having the test create its own fresh
fixture instead of depending on an old file's ownership. All three are
now `Live` (see their rows above). Also found along the way: the
`CLAUDE` directory itself refused brand-new file creates (`E$CEF`/218
"already exists", even for names `dir` confirmed absent) while the disk
overall had 170,000+ free sectors and root-level creates worked fine —
plausibly `CLAUDE`'s own directory-extension needs owner-level write
permission it doesn't have under `USER1`, misreported as 218 rather than
214; not root-caused, but real and reproducible — worth working around
(create fixtures at the disk root, or in a directory owned by whichever
user is logged in) rather than fighting. See
`dogfood-report-syscalls-batch3-2026-07-19.md`.

A fourth batch
(`test/6809-live-verification/batch4-01.a` through `batch4-04.a`)
exercised `F$Load`/`F$UnLoad`/`F$SSWI`/`F$SRqMem`/`F$Move`/`F$FModul`/
`I$Attach`/`I$Detach` — found that `F$SRqMem`, `F$Move`, and `F$FModul`
are genuinely **unimplemented** on this kernel build (`err=00208` =
`E$UnkSvc` on all three, same as `F$GProcP` above — a real, meaningful
pattern, not test bugs); `F$Load` and `I$Attach`/`I$Detach` confirmed
cleanly; `F$UnLoad` failed unexpectedly (`E$MNF`) right after loading
the same name, left inconclusive; `F$SSWI`'s install call is accepted
but this pass couldn't confirm the handler actually runs (the only
documented handler-exit convention anywhere in this file, `F$Icpt`'s
plain `RTI`, may not be `F$SSWI`'s own convention).

A fifth, large batch
(`test/6809-live-verification/batch5-01.a` through `batch5-06.a`) swept
the remaining calls whose docs already flagged a Level-2/DAT-image
dependency, confirming most are genuinely **unimplemented** on this
kernel build (`err=00208`=`E$UnkSvc`) — a real, now well-established
pattern rather than a per-call mystery. Real exceptions: `F$MapBlk`
(genuinely implemented, unlike its siblings), `F$AllRAM`/`F$DelRam`,
`F$NMLink`/`F$NMLoad`, `F$VIRQ`, `F$SUser`, `F$CpyMem` all confirmed
cleanly working. F$Chain RESOLVED (2026-07-21, faithful not a bug):
**its failure path produced a raw kernel error because it tears the
caller down before the target resolves** (unlinks old module, frees old
DAT blocks, then F$Exit/condemn on failure) — os9exec 68k matches this,
owner-confirmed intent. `F$DelPrc` was deliberately not attempted
(the only available PID would be the caller's own live one — a real
self-termination risk, not a bounded test). See
`dogfood-report-syscalls-batch5-2026-07-19.md`.

70 of ~93 documented
`F$`/`I$` calls are `Live` as of this pass, up from 5 at the start of
2026-07-19.

Same OS as 68k — see `common/` for the concepts (module directory, position-independent code, process states, file manager architecture, error codes). This file is the 6809-specific *encoding* of those same concepts: different register set, different syscall dispatch mechanism, different byte layout.

## Register Set and Calling Convention

6809 registers: `A`, `B` (or combined `D` = A:B), `X`, `Y`, `U`, `S` (hardware stack), `DP` (direct page), `CC` (condition codes), `PC`.

All system calls use **`SWI2`** followed immediately by a one-byte function code (the 6809 analog of 68k's `TRAP #0` + code word). Assembler convenience macro: `OS9 I$Read` expands to `SWI2` + the code byte.

- **Error convention**: carry bit set + error code in `B` on error; carry clear on success. Registers not specified for a given call are unaltered.
- Strings passed as parameters are terminated by a space+EOL, or by the sign bit (bit 7) set on the last character — same "sign-bit terminator" convention 68k module names use, just applied more broadly here.
- Standard I/O paths: 0=stdin, 1=stdout, 2=stderr (same as 68k).
- At process entry (Fork/Chain/debugger `E`): `Y` = top of data memory, `U`/`X` = bottom (direct page/data area boundaries depending on source), `D` = parameter area size, `PC` = module entry point, `CC` flags F=0, I=0.
- **Command-line parameter area at entry (`Live`, 2026-07-21 — resolved):** on a real shell fork (`progname ARGS`), entry `X` points directly at the argument text with **no leading byte**; the text is the raw command tail (multiple arguments space-separated, verbatim), terminated by a single trailing **CR** (`$0D`). `D` = argument-text-length + 1, the +1 being that CR — bare `progname` with no arguments gives `D`=1, a lone CR. Confirmed with a probe (`DmpPar`, echoing its own param area between `<>` markers) over several invocations: `A`→`D`=2 `<A[CR]>`, `HELLO`→`D`=6, `ONE TWO`→`D`=8 `<ONE TWO[CR]>` (the inter-argument space is preserved as ordinary text), no args→`D`=1 `<[CR]>`. The debugger's `E progname ARGS` is the **outlier**: it prepends a literal leading space (`$20`) before the same text (`D`=1+text+1) — a quirk of how `E` builds the parameter area, not the canonical convention. The shell-fork form above is canonical. (An earlier note claimed the trailing CR was `E`-only; that was wrong — **both** paths terminate with CR, only the leading space differs.) A program reading its own parameters should expect the trailing CR and defensively skip a leading space only if the first byte actually is one. Probe source: `test/6809-live-verification/dmppar.a` (os9exec repo).

## Syscall Reference

Codes `$00-$1D` are ordinary user-mode `F$` calls (Table C.1 of the System Programmer's Manual's own Appendix C); `$28-$52` are privileged system-mode calls (that appendix's Table C.2); `$80-$8F` (plus `$90` added in later revisions) are I/O `I$` calls. The `$1E-$27` range is a mixed group documented in the manual's prose rather than either summary table — `Manual`, occupied by `F$Alarm`($1E), `F$NMLink`($21), `F$NMLoad`($22), and `F$VIRQ`($27) (see below); `$1F`/`$20`/`$23`-`$26` are unconfirmed by any source checked, not verified as unused — treat silence on those four as "unknown," not "free."

### User-mode F$ (process/memory management)

| Call | Code | Params | Notes |
|---|---|---|---|
| F$Link | $00 | A=type/lang, X=name | Returns A=type/lang, B=attr/rev, X=past name, Y=entry point, U=header addr. **`Live`, 2026-07-19**: register contract confirmed exact (self-linking a running process's own module, A=0 accepted as "any type"; returned Y is a plausible in-range code address). **`Live`**: only searches the *resident, in-memory* module directory — fails `E$MNF` (221, "module not found") against a name that has a real file on disk but was never loaded by anything, it does not fall back to a filesystem search the way `F$Load` does. Test: `test/6809-live-verification/syscall-flink-ffork-fwait.a` in the os9exec repo |
| F$Load | $01 | A=lang/type (0=any), X=pathlist | Same returns as Link, applies to first module in file. **Not independently located in NitrOS-9's source** despite a real search (its own dedicated file, `flink.asm`, and the main kernel dispatch files) — plausibly implemented as a shared code path with `F$Link` under a label this search didn't recognize, not evidence the call itself is missing. **`Live`, 2026-07-19**: loading a pre-existing utility module (`hello4`, resolved via the exec-directory search list — a *bare* name that only exists in the current *data* directory, not `CMDS`, fails `E$PNNF`/216, so `F$Load`'s path resolution behaves like `F$Fork`'s, not like `I$Open`'s) returned a plausible code-range entry point with no error. Test: `test/6809-live-verification/batch4-01.a` in the os9exec repo |
| F$UnLink | $02 | U=module header addr | Decrements link count; frees at zero. **`Live`, 2026-07-19**: unlinking a module just linked via `F$Link` above succeeds cleanly (carry clear). Test: same file as `F$Link` |
| F$Fork | $03 | A=lang/type, B=data pages, X=name, Y=param size, U=param start | Returns A=new PID, X=past name. **`Live`, 2026-07-19**: register contract confirmed (A=0 "any type" accepted, B=1 data page sufficient for a trivial helper module, Y=0/U=0 for no parameters, returned A is a plausible small PID). **`Live`**: unlike `F$Link`, `F$Fork` *does* resolve via the filesystem (like `F$Load`) — a name with no file behind it at all fails `E$PNNF` (216, "path name not found"), not `E$MNF`. A caller distinguishing "not loaded yet" from "doesn't exist" needs to know which of these two calls it's using and which error code that implies. Test: same file as `F$Link` |
| F$Wait | $04 | — | Returns A=child PID, B=exit status; error if no children. **`Live`, 2026-07-19**: forking a helper module that exits with a distinctive `F$Exit` status (77), then `F$Wait`ing, returned the correct PID (matching `F$Fork`'s own return) and the correct exit status in B. Calling `F$Wait` with **no children at all** fails `E$NoChld` (226) — the "error if no children" behavior was already documented but not the specific code. Test: same file as `F$Link` |
| F$Chain | $05 | same as Fork | Reconfigures data area in place; doesn't close open paths. **`Live`, 2026-07-19; RESOLVED 2026-07-21 — faithful, not a bug.** A failure-path attempt (bogus target name) produced a raw kernel error with none of the program's own output because `fchain.asm` unlinks the old primary module and frees the old DAT blocks BEFORE linking the new one, then `F$Exit`s on failure (Level-2) / condemns the process (Level-1). The caller is torn down before the target resolves, so a bad name kills it — there is nothing left to return an error to. os9exec's 68k `F$Chain` matches this exactly; owner-confirmed intent. Test: `test/6809-live-verification/batch5-01.a` |
| F$Exit | $06 | B=exit status | Deallocates data area, unlinks primary module, closes all paths. **`Live`**: exited cleanly with no residual module left in `mdir`; `B` must be explicitly cleared first or a stale value produces a cosmetic `Error #001` after your own output. Confirmed in every test file this suite has run |
| F$Mem | $07 | D=new size (0=query) | Returns Y=new upper bound, D=actual size. **`Live`, 2026-07-19**: `D=0` (query) returned a plausible in-range upper-bound address in Y with no error. Test: `test/6809-live-verification/syscall-fmem-fsleep-fsprior-fcrc.a` in the os9exec repo |
| F$Send | $08 | A=dest PID (0=all same group), B=signal code | Signal 0=Kill, 1=Wakeup, 2=Abort, 3=Interrupt, rest user-defined (see below). **`Live`**: confirmed via the reserved-signal-range test below, sending both a disputed-range and undisputed-range code to self |
| F$Icpt | $09 | X=intercept routine, U=routine's storage | Handler gets U=storage, B=signal code; exits via RTI. **`Live`**: confirmed via the same test — handler installed, invoked correctly, received the right code in `B` both times |
| F$Sleep | $0A | X=ticks (0=indefinite) | Returns X=remaining ticks; woken early by signal. **`Live`, 2026-07-19**: `X=50` returned with `remaining=23`, not `0` — the call did pause execution and returned cleanly, but didn't report having consumed the full requested duration. Not chased further (no signal was sent, so "woken early by signal" doesn't explain it as documented); worth remembering if `F$Sleep` timing precision ever matters. Test: same file as `F$Mem` above |
| F$ID | $0C | — | Returns A=PID (1-255), Y=user ID (0-65535). **`Live`, 2026-07-19**: `A` confirmed — returned a plausible small PID (3) with no error. This particular test didn't print a distinguishable second value for `Y`, so the user-ID half wasn't independently re-confirmed here. Test: `test/6809-live-verification/batch3-01.a` in the os9exec repo |
| F$SPrior | $0D | A=PID, B=priority (0=lowest, 255=highest) | Same-user rule; superuser can set any. **`Live`, 2026-07-19**: setting the caller's own priority (via `F$ID` for the PID) to 150 accepted with no error. Test: same file as `F$Mem` above |
| F$SSWI | $0E | A=vector (1=SWI, 2=SWI2, 3=SWI3), X=routine | Per-process vector, not global. **`Live`, 2026-07-19 — the install call itself is accepted with no error** (vector 1/plain SWI, deliberately not vector 2 since SWI2 is this whole test suite's own syscall dispatch mechanism — installing over it would break every subsequent call in the same program). **Whether the handler actually runs on a bare `SWI` afterward is unconfirmed**: a test using a plain `RTI` exit (the only documented handler-exit convention anywhere in this file, borrowed from `F$Icpt`'s row) did not observe the handler's marker being set. `F$Icpt`'s signal-delivery mechanism and `F$SSWI`'s raw hardware-vector mechanism may have different, undocumented entry/exit conventions — not chased further. Test: `test/6809-live-verification/batch4-02.a` |
| F$PErr | $0F | B=error code | Writes "ERROR #nn" to stderr; replaceable. **`Live`, 2026-07-19**: confirmed, and richer than documented — writes a full human-readable line (`Error #216 - Path Name Not Found`), not just a bare `ERROR #nn`. Test: `test/6809-live-verification/batch3-01.a` in the os9exec repo |
| F$PrsNam | $10 | X=pathlist | Parses one legal OS-9 name; returns X/Y bounds, B=length. **`Live`, 2026-07-19**: the call accepts a valid name with no error (carry clear); this test doesn't decode/print the returned X/Y/B values, so only "the call succeeds" is confirmed — the specific bounds/length values remain unverified. Test: `test/6809-live-verification/batch3-01.a` |
| F$CmpNam | $11 | B=length, X/Y=two strings | Carry clear if match; second string sign-bit terminated. **`Live`, 2026-07-19 — dispatches, but the observed result diverges from a naive reading of "carry clear if match."** Comparing two identical 4-byte strings (X and Y both pointing at the same buffer, its 5th byte a separate sign-bit-terminator byte, B=4) returned carry SET (mismatch), not clear. Not chased further; a plausible explanation is that the terminator needs to be the sign bit baked into the *last real character* (as `fcs` produces) rather than a separate trailing byte (as this test built it) — genuinely unconfirmed either way. Test: `test/6809-live-verification/batch3-01.a` |
| F$SchBit | $12 | D=start bit, X=map, Y=count, U=map end | Searches allocation bitmap for a free block. `Source`, with an addition: NitrOS-9's `fallbit.asm` shows this returns D=where the found run starts and Y=how many free bits it spans, back-to-back — neither of which had a documented return here before. **`Live`, 2026-07-19 — call succeeds (carry clear) against a caller-owned zeroed 64-bit local map, but the D/Y values read back afterward don't look like sane "start bit"/"run length" numbers for that input** (values in the 15000s/57000s range). Not root-caused this pass — the same suspicious D value also showed up in a separate test program's `F$GBlkMp` result below, which may point to a shared test-harness artifact rather than two independent syscalls agreeing by coincidence, but that's speculation. Test: `test/6809-live-verification/batch3-02.a` |
| F$AllBit | $13 | D=first bit, X=map, Y=count | Sets bits (marks allocated). **`Live`, 2026-07-19**: accepted with no error against a caller-owned local map; confirmed by reading the map bytes back afterward that the target bits were set. Test: `test/6809-live-verification/batch3-02.a` |
| F$DelBit | $14 | D=first bit, X=map, Y=count | Clears bits (marks free). **`Live`, 2026-07-19**: accepted with no error, symmetric with `F$AllBit` above on the same local map. Test: `test/6809-live-verification/batch3-02.a` |
| F$Time | $15 | X=6-byte buffer | year/month/day/hour/min/sec. **`Live`, 2026-07-19**: the year byte is `year - 1900`, not a raw/2-digit value — read `126` against a known guest date of 2026-07-19 (126+1900=2026), with month/day bytes matching (`07`/`19`) too. Previously unspecified. Test: `test/6809-live-verification/syscall-ftime-iread-iwrite.a` in the os9exec repo |
| F$STime | $16 | X=6-byte packet | Also starts the real-time clock. **`Live`, 2026-07-19 — FAILED**, `err=00000` (an unusual code — 0 isn't a real OS-9 error number, suggesting this call may not populate `B` on failure the way most calls do). Ambiguous which of the paired read (`F$Time`, already firmly `Live`-confirmed in batch 1) or write (`F$STime` itself) actually failed, since this test shared one message for both — left unresolved rather than guessed at. Test: `test/6809-live-verification/batch5-01.a` |
| F$CRC | $17 | X=start, Y=count, U=3-byte accumulator | Accumulator must init to `$FFFFFF` before first call. **`Live`, 2026-07-19**: call accepted with no error and produced a 3-byte result over an 8-byte test buffer; not independently checked against a reference CRC implementation (no known-answer test data available), so this confirms the call works, not the specific checksum algorithm/polynomial. Test: same file as `F$Mem` above |
| F$GPrDsc | $18 | A=PID, X=512-byte buffer | Copy of process descriptor. **`Live`, 2026-07-19**: accepted with no error (own PID via `F$ID`, 512-byte local buffer). Test: `test/6809-live-verification/batch3-03.a` in the os9exec repo |
| F$GBlkMp | $19 | X=1024-byte buffer | Returns D=block size (commonly `$2000`=8K), Y=map size. **`Live`, 2026-07-19 — call succeeds, but the D/Y values read back don't look plausible** (nowhere near the documented common `$2000`); same unexplained-large-value pattern as `F$SchBit` above, not root-caused this pass. Test: `test/6809-live-verification/batch3-03.a` |
| F$GModDr | $1A | X=2048-byte buffer | Copy of module directory; returns Y=copy-end addr, U=system module-dir start addr. **Source-corrected**: NitrOS-9's `fgmoddr.asm` shows Y and U are written by the routine, not read from the caller — the prior documented shape had them backwards as inputs. **`Live`, 2026-07-19**: consistent with the Source-corrected shape — `Y` printed a plausible address-sized value; `U` (system module-dir start) wasn't independently printed by this test. Test: `test/6809-live-verification/batch3-03.a` |
| F$CpyMem | $1B | D=DAT ptr, X=offset, Y=count, U=dest | Reads another process's memory via its DAT image (Level 2). `Source, Flag` — real discrepancy found: NitrOS-9's `fcpymem.asm` never reads caller's X at all — the whole copy is driven by D (DAT image pointer, confirmed via the code's own inline comment), Y (byte count), and U (destination), a 3-register call, not 4. Oddly, that file's *own* header comment still claims the original 4-register shape (`D=block#, X=offset in block, Y=count, U=dest`) that this table was sourced from — so the header comment itself is stale relative to its own code, not just relative to the manual. Can't tell whether NitrOS-9 dropped the offset parameter at some point in its 40+ years of development, or whether the 1980s manual's claim was never quite accurate — the manual's shape is left here as the documented convention, with this note attached rather than silently dropping X. **`Live`, 2026-07-19**: a trivial self-referential copy (own DAT ptr, small count) succeeded with no error. Test: `test/6809-live-verification/batch5-01.a` |
| F$SUser | $1C | Y=user ID | Sets caller's user ID. **`Live`, 2026-07-19**: setting the caller's own already-current ID accepted with no error. Test: `test/6809-live-verification/batch5-01.a` |
| F$UnLoad | $1D | A=type, X=name | Unlink by name instead of address. **`Live`, 2026-07-19 — FAILED**, `err=00221` (`E$MNF`, module not found), immediately after the same name was successfully `F$Load`ed by the same process. Not chased further — possibly `A=type` isn't literally the type/lang byte `F$Load` returns in `A` the way this test assumed. Test: `test/6809-live-verification/batch4-01.a` |

### Mixed range ($1E-$27): outside either summary table

Registers below come from the OS-9 Technical Reference (Tandy)'s own
per-call "Entry Conditions / Exit Conditions / Error Output" listings — a
source not checked in the original register-closing pass (which only
looked at the System Programmer's Manual's Chapters 11.2/12.1 and the
Rev F1 Appendix E, none of which cover this mixed range at all).

| Call | Code | Params | Notes |
|---|---|---|---|
| F$Alarm | $1E | D=mode (`0`=clear, `1`=system-wide, `2`=query the current setting, any PID=arm for that process), X=addr of a 5-byte time packet (only read when arming) | Sets a timed signal for the caller — a 15-second bell ring at the specified time, using the same time-packet layout `F$STime` takes. Only whole-minute alarms are honored (any sub-minute precision in the packet is dropped); at most one alarm can be pending at once. `Live`: D genuinely acts as a mode selector, resolving the earlier manual-vs-source discrepancy — `D=0` (clear) and `D=2` (query) both returned cleanly (no carry/error) with X left unset/garbage in both calls, while `D=99` (an unrecognized mode/PID) failed with carry set, under the identical unset-X condition. Since X was equally invalid in all three calls, the differing outcomes can only be explained by D itself being inspected — confirms NitrOS-9's `clock.asm` reading over the Technical Reference (Tandy)'s silence on the D-register mode byte. Not tested: `D=1` (arm) or the PID-targeting case, both deliberately avoided live (arming a real alarm risks an async signal disrupting the shared test session) |
| F$NMLink | $21 | A=type/lang, X=name ptr | Like `F$Link` but doesn't map the module into the caller's address space — returns A=type/lang, B=revision, X=past name, Y=memory requirement, so a process can size a fork before committing. **Not found in NitrOS-9's source** (checked broadly, not just its usual kernel-module location) — either dropped from the community continuation at some point, or implemented somewhere this search missed. **`Live`, 2026-07-19 — accepted with no error**, against `childprg` (already resident from a preceding `F$Load` in the same test) — turns out to be implemented after all, contrary to the source-search result above. Test: `test/6809-live-verification/batch5-02.a` |
| F$NMLoad | $22 | A=type/lang, X=pathlist ptr | Like `F$Load` but doesn't map the module into the caller's address space — returns A=type/lang, B=revision, X=past pathlist, Y=memory requirement. No full pathlist given → loads from the current execution directory. **Not found in NitrOS-9's source**, same caveat as `F$NMLink` above. **`Live`, 2026-07-19 — accepted with no error**, same target — also implemented despite the source-search result. Test: `test/6809-live-verification/batch5-02.a` |
| F$VIRQ | $27 | Y=addr of a 5-byte packet (install) or a match key (delete), X=0 (delete) or nonzero (install), D=initial tick count (install only) | Installs/removes a virtual (software-polled) interrupt handler; no output beyond the standard carry/error. Packet layout: `Vi.Cnt`(offset $0, 2 bytes)=live counter, `Vi.Rst`($2, 2 bytes)=reset value, `Vi.Stat`($4, 1 byte)=status (bit 0 set when the VIRQ fires, bit 7 set if the counter should reset instead of a one-shot). `Source` (NitrOS-9's `clock.asm`, `FVIRQ` label) — matches the Technical Reference (Tandy) entry exactly, including the delete-by-matching-Y-against-the-table-entry mechanism. **`Live`, 2026-07-19**: both install and delete-by-same-packet-address confirmed with no error. Test: `test/6809-live-verification/batch5-03.a` in the os9exec repo. **Harness note**: the REPL connection stopped responding to any input shortly after this test ran (recovered with a clean `stop`/`start`) — noted as a possible side effect since installing/removing a periodic interrupt is exactly the kind of thing that could interfere with input polling, but the timing is circumstantial, not confirmed causal |

`$1F`/`$20`/`$23`-`$26` remain unconfirmed by any source checked (System
Programmer's Manual Chapters 11.2/12.1, Rev F1 Appendix E, Technical
Reference Tandy's own per-call catalog, and a corpus-wide grep for their
machine-code bytes) — not verified as unused, genuinely undocumented in
what's available.

### Privileged system-mode F$ ($28-$52; kernel-internal, listed for completeness, not for ordinary programs)

**Register-contract spot-check, 2026-07-23:** a batch of these was diffed
directly against the System Programmer's Manual's own per-call INPUT/OUTPUT
listings (§11.2/12.1) — `F$NProc`, `F$SRqMem`, `F$AllImg`, `F$AllPrc`,
`F$AllRAM`, `F$AllTsk`, `F$Move` all match register-for-register. No divergence
found in the sample; the Params column here is faithful to the manual.

Every code here is `Manual`, cross-confirmed by at least two independent sources (the System Programmer's Manual's own Appendix C, Table C.2, and the 1982 OS-9 Quick Reference's own per-call code citations — a different, earlier document from the 1992 FARNA Quick Reference cited elsewhere in this file), except where noted. **Params** below (added in a later pass) come from the same manual's Chapters 11.2 and 12.1, which give full INPUT/OUTPUT register listings per call — codes themselves were NOT re-derived from those chapters (their OCR has code collisions in a couple of spots) and still trust this table's own pre-existing, cross-confirmed Code column. A follow-up gap-closing pass added `F$SSvc`/`F$GCMDir`/`F$LDAXYP`/`F$DATTmp` from two further sources missed the first time: the Gimix OS-9 Programmers Manual's own copy of the Rev F1 Appendix E (which does cover `F$LDAXYP`/`F$DATTmp` — the original pass's search of that appendix used a regex that silently skipped entries with leading whitespace) and the OS-9 Technical Reference (Tandy)'s independent per-call catalog (for `F$SSvc`/`F$GCMDir`).

| Call | Code | Params | Level 2? | Notes |
|---|---|---|---|---|
| F$SRqMem | $28 | D=byte count | | Allocates memory, rounded up to the next page; returns D=granted size, U=block addr; error E$MemFul. **`Live`, 2026-07-19 — FAILS on this system**, `err=00208` = `E$UnkSvc`, genuinely unimplemented, not a test-code issue (see `F$GProcP` above for the same result). `F$SRtMem` untested as a result (never reached). Test: `test/6809-live-verification/batch4-03.a` |
| F$SRtMem | $29 | U=block addr, D=byte count | | Deallocates a contiguous, page-aligned block; U must land on a page boundary or error E$BPAddr. Untested — its paired `F$SRqMem` above fails before this call is ever reached on this kernel build |
| F$IRQ | $2A | D=status-reg addr, X=0 (remove) or control-packet addr, Y=service routine, U=static storage | | Add/remove device from IRQ table; control packet at [X]: flip byte, [X+1]=mask byte, [X+2]=priority (0-255); error E$Poll. **Not independently located in NitrOS-9's source** despite checking its expected location and the main kernel dispatch files — real device drivers throughout the tree clearly call it (`os9 F$IRQ` appears as a caller in several driver modules), so the call is genuinely implemented somewhere, just not found by this search |
| F$IOQu | $2B | A=process number | | Enter I/O queue: links caller into another process's I/O queue and sleeps untimed pending a wakeup signal; used heavily by IOMAN/file managers. **Not found in NitrOS-9's source** as a distinct implementation — plausibly folded into a more general queuing primitive under a different name in this codebase, not confirmed either way |
| F$AProc | $2C | X=process descriptor addr | | Insert process in active process queue; ages already-queued processes and sets the new one's age to its priority |
| F$NProc | $2D | — | | Start next process: pulls the next entry off the active queue and transfers control to it (no return to caller); waits for an interrupt and rechecks if the queue is empty. Caller must already be queued, or it becomes invisible to the scheduler though `Procs` still shows its descriptor |
| F$VModul | $2E | LI: X=new module addr. LII: D=DAT image ptr, X=module block offset | | Checks header parity/CRC, then on a same-name/type collision keeps the higher revision (ties favor the already-resident module); returns U=module directory entry addr; errors E$KwnMod/E$DirFul/E$BMID/E$BMCRC (+E$BMHP on LII only). **`Live`, 2026-07-19 — FAILS**, `err=00208`=`E$UnkSvc`, unimplemented on this system (same pattern as `F$GProcP`/`F$SRqMem`/`F$Move`/`F$FModul`). `F$ELink` below depends on this call's output and was never reached as a result. Test: `test/6809-live-verification/batch5-02.a` |
| F$Find64 | $2F | A=block number, X=base-page addr | | Find a 64-byte memory block by number (numbered 1..N); returns Y=block addr. Untested — depends on `F$All64` below, which fails before this would ever be reached |
| F$All64 | $30 | X=page-table base addr (0=allocate a new base page) | | Splits 256-byte pages into four 64-byte sections (the first section is a page table holding each page's MSB); returns A=block number, X=page-table base, Y=block addr; error E$PthFul; first byte of each block holds its own block number — don't overwrite it. **`Live`, 2026-07-19 — FAILS**, `err=00208`=`E$UnkSvc`, unimplemented on this system. `F$Find64`/`F$Ret64` depend on this and were never reached. Test: `test/6809-live-verification/batch5-03.a` |
| F$Ret64 | $31 | A=block number, X=base-page addr | | Deallocates a 64-byte block (see `F$All64`). Untested — depends on `F$All64` above, which fails before this would ever be reached |
| F$SSvc | $32 | Y=addr of a system-call init table | | Adds or replaces an entry in the kernel's dispatch table so a custom syscall handler takes over a chosen function code. Y's table is a repeating sequence — function-code byte, then a 2-byte offset to the handler (relative to the entry's own 3rd byte) — terminated by a lone `$80` byte. A function code with its high bit set patches the *system*-mode dispatch table only; clear, it patches *both* the system and user tables. `Source` (NitrOS-9's `fssvc.asm`, cross-check only): matches the Technical Reference Tandy entry exactly, plus reveals the terminator byte and the system/user-table split, neither of which any manual checked stated |
| F$IODel | $33 | X=I/O module addr | | Deletes an I/O device if its use count is zero; error E$ModBsy if busy; LI runs the driver's Term routine here, LII defers that to `DETACH`. `Source` (NitrOS-9's `ioman.asm`, `FIODel` label) — input register matches exactly; mechanism is a scan of the live device table for any entry whose descriptor/driver/file-manager pointer still matches the module, not a literal reference count |
| F$SLink | $34 | A=module type, X=name ptr, Y=DAT image ptr for the name | | Link to a module already in the system's own address space by name; returns A=type, B=rev, X=past name, Y=entry point, U=module ptr (see `F$ELink` below for the directory-entry-pointer variant). **`Live`, 2026-07-19 — FAILS**, `err=00208`=`E$UnkSvc`, unimplemented on this system. Test: `test/6809-live-verification/batch5-02.a` |
| F$Boot | $35 | — | | Bootstrap system: links and calls the Boot module (or the one named in `INIT`) |
| F$BtMem | $36 | D=byte count | | Contiguous, block-rounded bootstrap memory request; returns D=granted count, U=block addr. **Deprecated since Level 2 v1.2** — equated to `F$SRqMem`. **`Live`, 2026-07-19 — FAILS**, `err=00208`=`E$UnkSvc`, exactly matching `F$SRqMem`'s own already-confirmed failure — consistent with the two being equated. Test: `test/6809-live-verification/batch5-03.a` |
| F$GProcP | $37 | A=PID | Yes | Translates a PID to its process descriptor's address *in system address space* — only means something on a system with more than one address space; returns Y=descriptor ptr. **Source-resolved** (NitrOS-9's `fgprocp.asm`) — the return register is unambiguously Y, a full 16-bit address (built via a `D`→`Y` transfer); closes the earlier caution flag about the register looking too narrow. **`Live`, 2026-07-19 — FAILS on this system**, `err=00208` = `E$UnkSvc` ("Illegal service request — Unknown service code"), confirmed via `common/error-codes.md`. This kernel build genuinely doesn't implement the call, not a test-code issue — same result batch 4 found for `F$SRqMem`/`F$Move`/`F$FModul` below, all also `E$UnkSvc`. Test: `test/6809-live-verification/batch3-03.a` |
| F$Move | $38 | A=src task#, B=dest task#, X=src ptr, Y=count, U=dest ptr | Yes | Moves data between two *address spaces* (two DAT task mappings) — not needed on a single-address-space Level 1 system. **`Live`, 2026-07-19 — FAILS**, `err=00208` = `E$UnkSvc`, genuinely unimplemented on this system, consistent with this row's own note. Test: `test/6809-live-verification/batch4-04.a` |
| F$AllRAM | $39 | B=block count | | Allocate RAM blocks; returns D=beginning block number — the manual documents `F$DelRAM` as operating on blocks with no DAT-image association at all, confirming this pair isn't Level-2-exclusive. **`Live`, 2026-07-19**: confirmed, 1-block request accepted with no error. Test: `test/6809-live-verification/batch5-04.a` in the os9exec repo |
| F$AllImg | $3A | A=begin block#, B=block count, X=process descriptor ptr | Yes | Allocates RAM blocks for a process's DAT image. **`Live`, 2026-07-19 — FAILS**, `err=00208`=`E$UnkSvc`, unimplemented (same pattern as `F$GProcP`/`F$SRqMem`/`F$Move`/`F$FModul`/`F$VModul`). Test: `test/6809-live-verification/batch5-04.a` |
| F$DelImg | $3B | A=begin block#, B=block count, X=process descriptor ptr | Yes | Frees a process's DAT image. Untested — this test's flow skips it when the preceding `F$AllImg` fails, jumping straight to `F$SetImg` |
| F$SetImg | $3C | A=begin image block#, B=block count, X=process descriptor ptr, U=new image ptr | Yes | Writes a process's DAT image into its descriptor; sets the image-change flag so hardware DAT updates on return. **`Live`, 2026-07-19 — FAILS**, `err=00208`=`E$UnkSvc`, unimplemented. Test: `test/6809-live-verification/batch5-04.a` |
| F$FreeLB | $3D | B=block count, Y=DAT image ptr | Yes | Searches a DAT image for a free low block; returns A=beginning block#. Untested — depends on a working `F$AllPrc` descriptor, and `F$AllPrc` itself fails on this system (see below); this test's flow skips straight past it |
| F$FreeHB | $3E | B=block count, Y=DAT image ptr | Yes | Searches a DAT image for a free high block; returns A=beginning block#. Untested, same reason as `F$FreeLB` above |
| F$AllTsk | $3F | X=process descriptor ptr | Yes | Allocates a DAT task number if not already assigned, then copies the DAT image into DAT hardware. Untested, same reason as `F$FreeLB` above |
| F$DelTsk | $40 | X=process descriptor ptr | Yes | Deallocates a DAT task number. Untested, same reason as `F$FreeLB` above |
| F$SetTsk | $41 | X=process descriptor ptr | Yes | Writes the DAT image into the actual hardware task registers; clears the image-change flag. Untested, same reason as `F$FreeLB` above |
| F$ResTsk | $42 | — | Yes | Reserves a free DAT task number; returns B=task number. **`Live`, 2026-07-19 — FAILS**, `err=00208`=`E$UnkSvc`, unimplemented. `F$RelTsk` below depends on this and was never reached. Test: `test/6809-live-verification/batch5-05.a` |
| F$RelTsk | $43 | B=task number | Yes | Releases a DAT task register. Untested — depends on `F$ResTsk` above, which fails before this would ever be reached |
| F$DATLog | $44 | B=DAT-image block index, X=block offset | Yes | Converts a DAT block/offset pair to a logical address — DAT-specific by definition; returns X=logical addr. **`Live`, 2026-07-19 — FAILS**, `err=00208`=`E$UnkSvc`, unimplemented. Test: `test/6809-live-verification/batch5-06.a` |
| F$DATTmp | $45 | D=block number | Yes | Builds a throwaway DAT image scoped to one memory block, for a one-off access without a full task/image setup; returns Y=DAT image ptr. **`Live`, 2026-07-19 — FAILS**, `err=00208`=`E$UnkSvc`, unimplemented. Test: `test/6809-live-verification/batch5-06.a` |
| F$LDAXY | $46 | X=block offset, Y=DAT image ptr | Yes | Load A from `[X,[Y]]` — cross-task/DAT-image memory access primitive; returns A=data byte; no bounds check (X must stay within the block). **`Live`, 2026-07-19 — FAILS**, `err=00208`=`E$UnkSvc`, unimplemented. Test: `test/6809-live-verification/batch5-06.a` |
| F$LDAXYP | $47 | X=block offset, Y=DAT image ptr | Yes | Load A from `[X+,[Y]]` (post-increment variant of the above); returns A=data byte, X=incremented by one. **`Live`, 2026-07-19 — FAILS**, `err=00208`=`E$UnkSvc`, unimplemented. Test: `test/6809-live-verification/batch5-06.a` |
| F$LDDDXY | $48 | D=offset-to-the-offset, X=offset within DAT image, Y=DAT image ptr | Yes | Load D from `[D+X,[Y]]`; returns D=2 bytes; offsets are relative to the first block the DAT image points to. **`Live`, 2026-07-19 — FAILS**, `err=00208`=`E$UnkSvc`, unimplemented. Test: `test/6809-live-verification/batch5-06.a` |
| F$LDABX | $49 | B=task#, X=data ptr | Yes | Load A from `0,X` in task `B`; returns A=data byte. **`Live`, 2026-07-19 — FAILS**, `err=00208`=`E$UnkSvc`, unimplemented. Test: `test/6809-live-verification/batch5-06.a` |
| F$STABX | $4A | A=data byte, B=task#, X=logical addr | Yes | Store A at `0,X` in task `B`. **`Live`, 2026-07-19 — FAILS**, `err=00208`=`E$UnkSvc`, unimplemented. Test: `test/6809-live-verification/batch5-06.a` |
| F$AllPrc | $4B | — | Yes | Allocates a 512-byte process descriptor (first 256 bytes cleared, system state set, up to 60-64K of DAT image marked unallocated); returns U=descriptor ptr. **`Live`, 2026-07-19 — FAILS**, `err=00208`=`E$UnkSvc`, unimplemented (confirmed twice, independently, in both `batch5-04.a` and `batch5-05.a`). Every descriptor-dependent call below (`F$AllImg`/`F$SetImg`/`F$FreeLB`/`F$FreeHB`/`F$AllTsk`/`F$SetTsk`/`F$DelTsk`) was tested with an uninitialized/never-real descriptor as a result — doesn't undermine their own `E$UnkSvc` findings (that error fires before argument validation), but means none of them were exercised with genuinely valid input |
| F$DelPrc | $4C | A=process ID | | Deallocates a process descriptor — architecture-generic on its face, but internally calls the Level-2-only `F$DelTsk`; left untagged rather than guessed. **Deliberately not tested, 2026-07-19**: the only PID available to pass would be the caller's own live one (`F$AllPrc`-allocated descriptors have no real PID of their own, never having been `F$Fork`'d), and this call deallocating the caller's own running process descriptor mid-execution is a real self-termination risk, not a bounded experiment — skipped rather than guessed at |
| F$ELink | $4D | B=module type, X=ptr to module directory entry | | Links via a module directory entry pointer rather than by name; returns U=header addr, Y=entry point. Untested — needs a directory-entry pointer from `F$VModul` above, which fails before providing one |
| F$FModul | $4E | A=module type, X=name ptr, Y=DAT image ptr for the name | | Finds a module directory entry by name/type (type 0 matches any) — architecture-generic on its face, but internally calls `F$DATLog`/`F$LDAXY`/`F$LDDDXY` (all Level-2-only); left untagged rather than guessed; returns A=type, B=rev, X=past name, U=directory entry ptr. **`Live`, 2026-07-19 — FAILS**, `err=00208` = `E$UnkSvc`, confirming the Level-2-only dependency this row already flagged. Test: `test/6809-live-verification/batch4-04.a` |
| F$MapBlk | $4F | B=block count, X=beginning block# | Yes | Maps blocks into a process's DAT-mapped address space via `F$FreeHB`/`F$SetImg`, from the top down into the highest available addresses; returns U=addr of first block. **`Live`, 2026-07-19 — genuinely implemented, unlike most of its Level-2-flagged siblings on this system**: accepted with no error and returned a real address. Test: `test/6809-live-verification/batch5-06.a` |
| F$ClrBlk | $50 | B=block count, U=addr of first block | Yes | Marks blocks unallocated in a process's DAT image. **`Live`, 2026-07-19 — FAILED**, `err=00219`=`E$IBA` ("illegal block address") — but this is a test-construction gap, not a confirmed finding: the test never captured `F$MapBlk`'s own returned block address and passed it through, so `U` held this program's own base pointer, not a real block address. Left inconclusive rather than asserted as a real divergence; worth re-testing properly with the address actually threaded through. Test: `test/6809-live-verification/batch5-06.a` |
| F$DelRam | $51 | B=block count, X=starting block# | | Deallocate RAM blocks (see `F$AllRAM` note above). **`Live`, 2026-07-19**: confirmed, freeing the exact block `F$AllRAM` just granted, no error. Test: `test/6809-live-verification/batch5-04.a` |
| F$GCMDir | $52 | none (no input, no output registers) | | Squeezes out gaps in the module directory's entry list. `Manual`, no longer single-source: the OS-9 Technical Reference (Tandy) independently confirms code $52 and confirms this call takes no register parameters at all — it's reserved for the kernel's own use, not something application code should invoke directly. Still absent from the System Programmer's Manual's own Table C.2, which ends at `F$DelRam`/$51 |

**Also real, code not confirmed:** `F$AllHRam` ("Allocate High RAM" — like `F$AllRAM` but searches from the top of memory down, used by screen-allocation routines) is `Manual` (three independent sources: Technical Reference Tandy, both Quick References) but none of the passages found gave a clean, legible machine code for it — not included in the table above rather than guessed.

**Level-2-exclusive vs. universal, and why:** the calls marked "Yes" above all explicitly manipulate a DAT image, a DAT task register, or an inter-address-space transfer in their own primary-source description — none of that has meaning on a Level 1 system, which has one unshared 64K address space and no task-register hardware. `F$Boot`/`F$SUser`/`F$UnLoad` are plain bootstrap/user-ID/module-unlink operations with no DAT dependency.

### I/O I$ calls

**Register contracts verified 2026-07-23 against the System Programmer's Manual
§11.3** (per-call INPUT/OUTPUT listings): `I$Open` (A=mode, X=pathlist → A=path,
X=updated), `I$Create` (A=mode, B=attrs, X=pathlist → A=path), `I$Delete`
(X=pathlist), `I$MakDir` (B=attrs, X=pathlist), `I$ChgDir` (A=mode, X=pathlist),
`I$Read`/`I$Write` (A=path, X=buffer, Y=count → Y=actual), `I$ReadLn`, `I$Seek`
(A=path, X=hi16, U=lo16), `I$GetStt`/`I$SetStt` (A=path, B=function code) all
match register-for-register.

| Call | Code | Params | Notes |
|---|---|---|---|
| I$Attach | $80 | A=access mode, X=device name | Returns U=device table entry. **`Live`, 2026-07-19**: confirmed against `/N1` (the REPL's own already-attached channel device) — a real, in-range device table entry address came back with no error. Test: `test/6809-live-verification/batch4-04.a` |
| I$Detach | $81 | U=device table entry | Calls driver Term, deallocates if unused elsewhere. **`Live`, 2026-07-19**: confirmed detaching the entry `I$Attach` just returned, no error — since the device was already in use elsewhere (the REPL's own channel), this correctly adjusted a use count rather than tearing anything down (the REPL kept working afterward). Test: `test/6809-live-verification/batch4-04.a` |
| I$Dup | $82 | A=path | Returns new path number (lowest available), same underlying file. **`Live`, 2026-07-19**: confirmed — duplicating a freshly-created path returned a distinct, plausible new path number with no error. Test: `test/6809-live-verification/batch3-04.a` in the os9exec repo |
| I$Create | $83 | A=mode, B=attributes, X=pathlist | Returns A=path number; error if exists. `Source`, two-layer dispatch: NitrOS-9's `ioman.asm` shares one dispatcher between `I$Open`/`I$Create` that only touches A and X itself, leaving B (and the rest of the caller's register frame) untouched as it hands off to the target file manager — RBF's own `Create` routine (`rbf.asm`) explicitly reads B as "file attributes," confirming the full call contract without IOMan itself needing to reference it directly. **`Live`, 2026-07-19**: register contract confirmed — `A=3` (update mode), `B=$FF` (attributes), `X=`bare-name pathlist (after an `I$ChgDir` into the target directory) returned a valid path number with no error. Test: `test/6809-live-verification/syscall-imakdir-ichgdir-icreate-idelete.a` in the os9exec repo |
| I$Open | $84 | A=access mode, X=pathlist | Returns A=path number. **`Live`, 2026-07-19** (already exercised by `dogfood-asm-line-counter.a`, 2026-07-18, but never credited here until now — see `syscall-ftime-iread-iwrite.a` for a second independent confirmation): register contract confirmed; also confirmed it requires an **existing** file — fails `E$PNNF` (216) against a nonexistent name, does not create-on-open the way some Unix `open()` flag combinations do (`I$Create` is the separate call for that) |
| I$MakDir | $85 | B=attributes, X=pathlist | Auto-creates `.` and `..` entries. `Source`: NitrOS-9's `rbf.asm` implements `MakDir` as a thin wrapper that just calls `Create` (same B=attributes contract) and then sets the directory bit afterward. **`Live`, 2026-07-19**: `B=$FF, X=`pathlist created a directory with no error. Test: same file as `I$Create` above |
| I$ChgDir | $86 | A=mode (1/2/3=data, 4=exec), X=pathlist | **`Live`, 2026-07-19**: `A=1` (data directory) accepted with no error; confirmed effective (not just accepted) since a subsequent bare-name `I$Create` succeeded relative to the new directory. Test: same file as `I$Create` above |
| I$Delete | $87 | X=pathlist | Requires write permission. **`Live`, 2026-07-19**: deleted a file created via `I$Create` moments earlier with no error. Test: same file as `I$Create` above |
| I$Seek | $88 | A=path, X=high 16 bits, U=low 16 bits of the 32-bit position | Random access (RBF) or cursor position (SCF). **Manual + Live agree, 2026-07-23**: the *System Programmer's Manual* (11.3.14) documents exactly this split — "(X) = M.S. 16 bits of desired file position, (U) = L.S. 16 bits" — resolving the old "D or X:D" hedge in this table's favour of neither; the register pair is X:U. NitrOS-9's RBF `Seek` reads it the same way (`Source`). **`Live`, 2026-07-19 — the X:U convention is confirmed, not just Source-suspected**: seeking to offset 5 in a known 10-byte file via `X=0,U=5` and reading 5 bytes back landed exactly on the expected content. **Trap for any test writing this call**: `U` is commonly also a program's own U-relative data-area base pointer — save it (`pshs u`/`puls u` around the `swi2`) or every later `,u`-relative reference breaks silently. Test: `test/6809-live-verification/syscall-iseek.a` in the os9exec repo |
| I$Read | $89 | A=path, X=buffer, Y=count | Returns Y=actual bytes; EOF error at end. **`Live`, 2026-07-19**: register contract confirmed for the plain (non-`Ln`) form specifically — a 10-byte read returned the correct content, and reading again once the file was exhausted correctly failed (no explicit code checked, just carry). Also **`Live`**: a path number that was never opened fails `E$BPNum` (201, "illegal path number"), confirming path numbers are validated, not just trusted. Test: `test/6809-live-verification/syscall-ftime-iread-iwrite.a` in the os9exec repo |
| I$Write | $8A | A=path, X=buffer, Y=count | Past-EOF write expands file. **Source-corrected**: this table had `I$Write` and `I$ReadLn`'s codes swapped — settled by NitrOS-9's `defs/os9.d`, whose sequential `RMB` definitions starting at `ORG $80` are authoritative and unambiguous (each call code is just the previous one plus one, so miscounting is the only way to get this wrong, which is what happened here). **`Live`, 2026-07-19**: register contract confirmed for the plain (non-`Ln`) form; also confirms **`I$Write` does return Y** (the actual byte count written, `Y=10` for a 10-byte write) — previously this row stated no return value at all. Test: same file as `I$Read` above |
| I$ReadLn | $8B | A=path, X=buffer, Y=max | Reads to CR, with line editing. **Source-corrected**, see `I$Write` above — same swap, same fix. **The returned length (in `Y` on exit) includes the CR terminator** — `Live`: summing raw returned lengths across a 3-line file gave a character count 3 too high against an independent `fsize` cross-check. This diverges from BASIC09's own `READ`/`LEN()` (also `Live`), which excludes the terminator — code porting a count from the syscall level to BASIC09 semantics (or vice versa) needs an explicit off-by-one adjustment |
| I$WritLn | $8C | A=path, X=buffer, Y=max | Writes to first CR; SCF adds LF/CR/nulls as configured. **`Live`, 2026-07-19**: confirmed against a freshly-created data file (as opposed to a device path, already `Live` elsewhere) — no error. Test: `test/6809-live-verification/batch3-04.a` |
| I$GetStt | $8D | A=path, B=function code | Device-dependent; see GETSTAT/SETSTAT below. **`Live`, 2026-07-19 — call confirmed, return-value convention NOT confirmed.** `B=6` (SS.EOF) accepted cleanly before EOF. `B=2` (SS.SIZ) also accepted with no error, but the file size did not come back where guessed: tried reading it from X:U afterward (matching `I$Seek`'s confirmed convention) and got `X:U=44:10` against a known 10-byte file — 44 makes no sense as a size's high word, so X is most likely just leftover/untouched by this function rather than a real return value. The actual return convention for SS.SIZ remains open. Test: `test/6809-live-verification/syscall-igetstt.a` in the os9exec repo |
| I$SetStt | $8E | A=path, B=function code | |
| I$Close | $8F | A=path | Implicit Detach. **`Live`, 2026-07-19** (already exercised by `dogfood-asm-line-counter.a`, 2026-07-18, but never credited here until now): register contract confirmed — closing a valid open path succeeds cleanly, both in the read-only line-counter test and in `syscall-ftime-iread-iwrite.a`'s write+read round trip |
| I$DeletX | $90 | A=access mode (1/2/3=data,4=exec), X=pathlist | Added in Rev F1 (1983); delete with explicit directory selection. **`Live`, 2026-07-19**: `A=1` (data) confirmed deleting a file created by the same test, no error. Test: `test/6809-live-verification/batch3-04.a` |

Common GETSTAT/SETSTAT function codes: 0=option section (`SS.OPT`, read/write raw path descriptor options), 1=`SS.RDY` data-ready test (SCF), 2=`SS.SIZ` file size, 5=`SS.POS` file position, 6=`SS.EOF` test. CoCo adds `SS.Mouse` ($89 as a GetStat sub-function) — see `coco-dragon-hardware.md`.

## Signals

Same design as 68k (numbered codes, tiny non-reentrant handlers, `F$Sleep` auto-unmask pattern — see `common/ipc.md`), 6809-specific numbering:

- 0 = Kill (uninterceptable), 1 = Wakeup (does not invoke the intercept routine), 2 = Abort (Ctrl-E), 3 = Interrupt (Ctrl-C). Sources disagree on paper about where the user-definable range starts (some say 4-255, one CoCo-specific source says 128-255), but `Live`: a process installed via `F$Icpt`, then `F$Send`'d code 50 (disputed range) and code 200 (undisputed range) to itself — both delivered identically, handler received the correct code in `B` both times, neither was rejected or treated specially. The "reserved" language is a Microware documentation/naming convention only; the kernel does not enforce any boundary within 4-255 on delivery.
- A signal with no installed handler kills the process unless the code is 0 or 1.
- If a process already has an unprocessed signal pending, `F$Send` to it fails — sender should `F$Sleep` briefly and retry.

## Module Header

Much smaller than 68k's (48-byte universal section): **9 bytes minimum**.
**`Manual`, verified 2026-07-23 against the *OS-9 System Programmer's Manual*
§4.2** (its own module-header definition list): $00-$01 sync `$87,$CD`, $02-$03
size, $04-$05 name offset (sign-bit-terminated), $06 type/language, $07
attributes/revision, $08 header check ("one's complement of the vertical parity
(XOR) of the previous eight bytes") — matching this table field-for-field.

| Offset | Size | Field | Notes |
|---|---|---|---|
| $00-$01 | 2 | Sync | `$87,$CD` — illegal/reserved 6809 opcodes, the 6809 analog of 68k's `$4AFC` (`Source`: this specific byte pair confirmed present against a real Level 2 kernel source listing) |
| $02-$03 | 2 | Module size | Total including CRC |
| $04-$05 | 2 | Name offset | Sign-bit-terminated string, can sit anywhere in the module body |
| $06 | 1 | Type/Language | High nibble = type, low nibble = language (see below) |
| $07 | 1 | Attributes/Revision | Bit 7 = reentrant/sharable, low 4 bits = revision (0-15) |
| $08 | 1 | Header parity | One's-complement XOR of the preceding 8 bytes |

Program/Subroutine modules (type $1/$2) have 4 more bytes: $09-$0A execution offset (relative to sync byte), $0B-$0C permanent storage requirement (minimum data area size).

`Live`: assembling a real Program-type module with
`asm`'s listing (`L S` flags) showed the module's `name` field (an `fcs`
label right after the `mod` directive) landing at offset `$000D` (13
decimal) — exactly 9 generic bytes + 4 Program-type bytes, confirming
this 13-byte total for real. `ident` independently reported the same
module's CRC as `(Good)`, cross-validating the CRC mechanism below
against a real assembled-and-checksummed module, not just the manual's
description of it.

**Type codes** (high nibble of byte $06): $1=Program, $2=Subroutine, $3=Multi-module, $4=Data, $5-$B=user-defined, $C=System, $D=File Manager, $E=Device Driver, $F=Device Descriptor. $0 illegal.

**Language codes** (low nibble): 0=Data (non-executable), **1=6809 object code**, 2=BASIC09 I-code, 3=Pascal P-code, 4=C I-code (reserved/unimplemented), 5=COBOL I-code (reserved/unimplemented), 6=FORTRAN I-code (reserved/unimplemented).

**CRC**: 24-bit, polynomial `$800FE3`, one's-complement-accumulator mechanism. Initialize accumulator to `$FFFFFF`, process every byte from header start through the byte before the CRC, then complement before storing. A valid module's CRC re-verified (including its own CRC bytes) yields `$800FE3`.

Module directory/linking semantics (name lookup, link-count-based sharing, highest-revision-wins on name collision, ROM auto-scan for the sync pattern at cold start) are identical in concept to 68k — see `common/os9-mental-model.md`.

## C Compiler

`int` is **16-bit** on the 6809 compiler (vs 32-bit on 68k). Direct-page addressing via the `DP` register is a 6809-only feature used to distinguish 6809-specific content from 68k.

---

**Sources:** OS-9 System Programmer's Manual (and its Rev F1/1983 errata), OS-9 Level Two Operating System Manual, OS-9 Technical Reference (Tandy/CoCo), two independent OS-9 Users Guides (1983), OS-9 Quick Reference (CoCo, 1992 FARNA Systems). `Manual` — cross-referenced against each other.

The "Privileged system-mode F$" code table is `Manual`, cross-confirmed against two independent, mutually-consistent per-call code listings: the System Programmer's Manual's Appendix C "Service Request Summary" (Tables C.1/C.2 — its authoritative machine-code appendix; the same manual's scattered inline prose cross-references contain wrong values, so never source codes from those) and the 1982 OS-9 Quick Reference's per-call "103F NN" citations. **Note the second of those is not authoritative** — the file named `OS-9_Quick_Reference_1982` is actually F. G. Swygert 1992, a third-party document (see the repo's `SOURCE-AUTHORITY.md`). It is retained only as corroboration; the codes do not rest on it, per the Microware-only re-verification below.

**Whole code column re-verified against Microware, 2026-07-23.** Every `F$`/`I$` code here was diffed mechanically against the System Programmer's Manual's own machine-code listings. Five apparent mismatches all traced to OCR damage in that manual's main scan (it prints duplicate codes — `$18`, `$3B`, `$4B` each appear on two different calls, and `$8E` misreads as `$BE`). In every case this table's value is the correct one, confirmed against a *second Microware source*: F$CpyMem `$1B`, F$FModul `$4E`, F$DelImg `$3B` (SPM Rev F1, 1983); I$SetStt `$8E`, F$VModul `$2E` (OS-9 Technical Reference, Tandy). No divergence — the table agrees with Microware; only the one damaged scan disagrees with itself. Source codes from Appendix C or Rev F1, never the main SPM's inline prose. `F$GCMDir`($52) was originally single-source (1982 Quick Reference only) — the OS-9 Technical Reference (Tandy), found during a later register-closing pass, independently confirms the same code, so this is now two-source. `F$AllHRam`'s code remains unconfirmed and unincluded.
