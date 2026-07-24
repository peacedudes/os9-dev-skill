# OS-9 Error Codes Reference

## Overview

OS-9 error reporting follows a standard convention.

### Error format: "Error #NNN:MMM"

Errors are reported as **Error #NNN:MMM** where:
- **NNN** is the class/module number (000 for kernel/core errors)
- **MMM** is the specific error code within that class

Example: `Error #000:216 (E$PNNF)` is class 000, code 216, symbolic name
`E$PNNF` (Path Name Not Found).

### Return convention: carry flag and an error-code register

Both architectures signal errors via the carry flag; the register holding
the code differs. **68k (this section's example): carry bit (C flag) set
on error, clear on success; `d1.w` holds the error code (MMM) when carry
is set.**

```asm
OS9 I$Open          ; make the system call
BCS.S ErrorHandler   ; branch if carry set (error)
; success path here
```

Device drivers use the same carry/`d1.w` convention on 68k: upon return
from any driver subroutine (via `RTS`), the carry bit signals
success/failure and `d1.w` holds the error code. For IRQ service routines,
this convention is modified — IRQ only uses the carry bit to signal
whether the interrupt was serviced; no caller is waiting for an error code
in `d1.w`. **6809: same carry-flag convention, but the error code lands in
`B` instead of `d1.w`** — see `6809/syscalls-and-module-format.md`'s
Register Set and Calling Convention section.

### Errors in C and BASIC09

C system calls don't use the carry/`d1.w` convention directly — the C
runtime translates it. A failing system call returns `-1`, and the specific
error code is left in the predefined variable `errno` (declared via
`<errno.h>`). `errno` is **not cleared on success** — it only ever holds the
value from the most recently *failed* call. Check the call's own return
value first; only consult `errno` once failure is confirmed.

BASIC09 exposes the same information through the `ERR` function, which
returns the most recent error code and **resets to zero as soon as it's
read**. Codes above 80 are OS-9/system errors (the table below); codes
10–80 are BASIC09-internal (1–9 are unused/reserved — not documented as
meaning anything).

### BASIC09-internal errors (codes 10–80)

| Code | Meaning | Code | Meaning |
|---|---|---|---|
| 10 | Unrecognized symbol | 46 | Operand type mismatch |
| 11 | Excessive verbiage (too many keywords/symbols) | 47 | String stack overflow |
| 12 | Illegal statement construction | 48 | Unimplemented routine |
| 13 | I-code overflow (need more workspace memory) | 49 | Undefined variable |
| 14 | Illegal channel reference (bad path number) | 50 | Floating overflow |
| 15 | Illegal mode (Read/Write/Update/Dir only) | 51 | Line with compiler error |
| 16 | Illegal number | 52 | Value out of range for destination |
| 17 | Illegal prefix | 53 | Subroutine stack overflow |
| 18 | Illegal operand | 54 | Subroutine stack underflow |
| 19 | Illegal operator | 55 | Subscript out of range |
| 20 | Illegal record field name | 56 | Parameter error |
| 21 | Illegal dimension | 57 | System stack overflow |
| 22 | Illegal literal | 58 | I/O type mismatch |
| 23 | Illegal relational | 59 | I/O numeric input format bad |
| 24 | Illegal type suffix | 60 | I/O conversion: number out of range |
| 25 | Too-large dimension | 61 | Illegal input format |
| 26 | Too-large line number | 62 | I/O format repeat error |
| 27 | Missing assignment statement | 63 | I/O format syntax error |
| 28 | Missing path number | 64 | Illegal path number |
| 29 | Missing comma | 65 | Wrong number of subscripts |
| 30 | Missing dimension | 66 | Non-record-type operand |
| 31 | Missing DO statement | 67 | Illegal argument |
| 32 | Memory full (need more workspace memory) | 68 | Illegal control structure |
| 33 | Missing GOTO | 69 | Unmatched control structure |
| 34 | Missing left parenthesis | 70 | Illegal FOR variable |
| 35 | Missing line reference | 71 | Illegal expression type |
| 36 | Missing operand | 72 | Illegal declarative statement |
| 37 | Missing right parenthesis | 73 | Array size overflow |
| 38 | Missing THEN statement | 74 | Undefined line number |
| 39 | Missing TO | 75 | Multiply-defined line number |
| 40 | Missing variable reference | 76 | Multiply-defined variable |
| 41 | No ending quote | 77 | Illegal input variable |
| 42 | Too many subscripts | 78 | Seek out of range |
| 43 | Unknown procedure | 79 | Missing DATA statement |
| 44 | Multiply-defined procedure | 80 | Print buffer overflow |
| 45 | Divide by zero | | |

`Manual` — this table is confirmed word-for-word identical across three
independent BASIC09 Reference Manual editions (Rev F/1983 Dragon Data
edition, Rev G/Tandy edition, Rev H/Microware unbranded edition); see
this file's Sources line. `Live` example codes hit in practice: `000:027` (syntax error — e.g. from `BASE0` typed without
the required space, see `basic09/basic09-language.md`), `000:055`
(subscript out of range — e.g. indexing a `DIM`'d array past its
allocated bound), and `000:011` (e.g. from writing
`LAND`/`LOR`/`LXOR`/`LNOT` as infix operators instead of function calls).

## Error code table

Codes below are grouped by numeric range, matching how the source manuals
present them. Three rows carry a dagger/double-dagger/section mark
(†/‡/§) — see **Known cross-manual discrepancies** further down; those
notes are not optional footnotes, they record a genuine disagreement
between two manual editions that was deliberately not resolved.

### 000:001 – 000:067 — Process, terminal, and math-trap errors

| Code | Symbolic name | Meaning | Cause |
|---|---|---|---|
| 000:001 | — | Process aborted | The process has aborted |
| 000:002 | — | Keyboard quit | Control-E (abort signal) sent to the process |
| 000:003 | — | Keyboard interrupt | Control-C (interrupt signal) sent to the process |
| 000:004 | — | Modem hangup | Device driver detected loss of data carrier |
| 000:064 | E$IllFnc § | Illegal function code | Math trap handler received an invalid function code |
| 000:065 | E$FmtErr | Format error | Math trap handler format error |
| 000:066 | E$NotNum | Number not found | Math trap handler could not find the number |
| 000:067 | E$IllArg | Illegal argument | Math trap handler received an illegal argument |

### 000:102 – 000:158 — Processor exception errors (68k-specific)

**This section is 68000-CPU-specific**, not a shared cross-architecture
table: the codes map 1:1 to 68k's own hardware exception vector table
(`68k/os9-68k-assembly.md`'s Exception vector table — code = vector + 100),
and several entries name 68000-family instructions/coprocessors with no
6809 counterpart (`CHK`/`CHK2`, `TRAPV`/`TRAPcc`/`FTRAPcc`, FPCP, PMMU).
6809 has no `F$STrap` call at all (absent from
`6809/syscalls-and-module-format.md`'s syscall tables) and no confirmed
equivalent numbered error range in the sources surveyed here — its
arithmetic-error handling instead happens earlier, inside the BASIC09
I-code interpreter's own runtime checks (e.g. `Error #045 -- Divide by
Zero`, an ordinary catchable BASIC09 error, not a CPU-trap dispatch — see
`basic09/gotchas.md`'s divide-by-zero entry). A process can install its
own 68k handler via `F$STrap`.

| Code | Symbolic name | Meaning | Cause |
|---|---|---|---|
| 000:102 | E$BusErr | Bus error | CPU bus error exception |
| 000:103 | E$AdrErr | Address error | CPU address error exception |
| 000:104 | E$IllIns | Illegal instruction | CPU executed an illegal opcode |
| 000:105 | E$ZerDiv | Zero divide | Integer zero-divide exception |
| 000:106 | E$Chk | CHK exception | CHK or CHK2 instruction exception |
| 000:107 | E$TrapV | TRAP exception | TRAPV, TRAPcc, or FTRAPcc instruction exception |
| 000:108 | E$Violat | Privilege violation | Privilege violation exception |
| 000:109 | E$Trace | Uninitialized trace | Uninitialized trace exception |
| 000:110 | E$1010 | A-Line emulator trap | 1010-line emulator exception |
| 000:111 | E$1111 | F-Line emulator trap | 1111-line emulator exception |
| 000:113 | — | Coprocessor protocol violation | Coprocessor protocol violation |
| 000:114 | — | Format error (exception) | Format error exception |
| 000:115 | — | Uninitialized interrupt | Uninitialized interrupt occurred |
| 000:124 | — | Spurious interrupt † | Spurious interrupt occurred |
| 000:133–000:147 | E$Trap | Uninitialized user TRAP 1–15 † | User executed a TRAP #1–#15 instruction with no handler installed |
| 000:148 | E$FPUnordC | FPCP unordered condition | FPCP branch/set on unordered condition |
| 000:149 | E$FPInxact | FPCP inexact result | FPCP inexact result |
| 000:150 | E$FPDivZer | FPCP divide by zero | FPCP divide by zero |
| 000:151 | E$FPUndrFl | FPCP underflow | FPCP underflow error |
| 000:152 | E$FPOprErr | FPCP operand error | FPCP invalid operand |
| 000:153 | E$FPOverFl | FPCP overflow | FPCP overflow error |
| 000:154 | E$FPNotNum | FPCP NAN signaled | Not-a-Number signaled |
| 000:155 | — | FPCP unimplemented data type | Unsupported floating-point data type |
| 000:156 | — | PMMU configuration error | PMMU configuration error |
| 000:157 | — | PMMU illegal operation | Illegal PMMU operation |
| 000:158 | — | PMMU access level violation | PMMU access-level violation |

### 000:164 – 000:176 — Miscellaneous errors (continued)

| Code | Symbolic name | Meaning | Cause |
|---|---|---|---|
| 000:164 | E$Permit | No permission | Process/module must be owned by the superuser for this function |
| 000:165 | E$Differ | Different arguments | `F$ChkNam` arguments do not match |
| 000:166 | E$StkOvf | Stack overflow | `F$ChkNam` pattern string is too complex |
| 000:167 | E$EvntID | Illegal event ID | Invalid or illegal event ID number |
| 000:168 | E$EvNF | Event name not found | Link/delete failed — name not in the event table |
| 000:169 | E$EvBusy | Event busy | Delete attempted on an event with nonzero link count, or create attempted on an already-existing named event |
| 000:170 | E$EvParm | Impossible event parameter | Invalid parameters passed to `F$Event` |
| 000:171 | E$Damage | System damage | Corruption detected in a kernel data structure |
| 000:172 | E$BadRev | Incompatible revision | Software revision incompatible with the OS revision |
| 000:173 | E$PthLost | Path lost | Network node down, serial carrier lost, or pipe broken via `SS_Break` |
| 000:174 | E$BadPart | Bad partition | Partition table invalid, or no partition marked active |
| 000:175 | E$Hardware | Hardware damage detected | Driver failed to detect a correct hardware response |
| 000:176 | E$SectSize | Invalid sector size | RBF sector size must be a binary multiple of 256, up to 32768 bytes |

### 000:200 – 000:239 — Operating system errors

Generated by the kernel or file managers.

| Code | Symbolic name | Meaning | Cause |
|---|---|---|---|
| 000:200 | E$PthFul | Path table full | More than 32 I/O paths opened at once, or no contiguous memory to expand the table. **The symbol is `E$PthFul`**, confirmed by the *OS-9/68000 Technical Manual* (`000:200 E$PthFul PATH TABLE FULL`) and the 6809 *System Programmer's Manual* (`$C8 200 E$PthFul`), and matching every call's own error list (`I$Open`/`I$Attach` document `E$PthFul` for this condition). The *v2.4 Technical Reference Manual*'s error appendix instead prints `E$BPNum` here — the same symbol it correctly gives 201 — which is a typo in that one edition, not two codes sharing a name |
| 000:201 | E$BPNum | Illegal path number | Path number out of range, or no open path by that number |
| 000:202 | E$Poll | Interrupt polling table full | Too many IRQ devices for the system INIT module's limit |
| 000:203 | E$BMode | Illegal mode | I/O function attempted that the device/file can't perform (e.g. reading an output-only file). **`Live`** (os9exec): now enforced on disk files (`fRBF`/`fFile`) both ways — writing to a path opened read-only, or reading one opened write-only, returns 203. Was previously **unenforced** (os9exec ignored the open mode); fixed in `filestuff.c` `syspath_read`/`_write`. Console/SCF paths are exempt (os9exec shares one descriptor for stdin/out/err) |
| 000:204 | E$DevOvf | Device table full | Device table exhausted (INIT module sets the max) |
| 000:205 | E$BMID | Illegal module header | Module sync code is incorrect |
| 000:206 | E$DirFul | Module directory full | Not enough memory, or memory too fragmented |
| 000:207 | E$MemFul | Memory full | Not enough contiguous RAM, or process already at its block-allocation limit |
| 000:208 | E$UnkSvc | Illegal service request | Unknown service code, or unknown Getstat/Setstat status code |
| 000:209 | E$ModBsy | Module busy | Non-sharable module already in use by another process |
| 000:210 | E$BPAddr | Boundary error | Invalid block address in a deallocation request, or memory not previously assigned |
| 000:211 | E$EOF | End of file | EOF encountered on a read |
| 000:212 | E$VctBsy | Vector busy | IRQ vector already in use by another device |
| 000:213 | E$NES | Non-existing segment | Disk file segment not found — possibly a damaged file structure |
| 000:214 | E$FNA | File not accessible | Open attempted without correct access permissions — check attributes and owner ID |
| 000:215 | E$BPNam | Bad path name | Syntax error in the pathlist (illegal character, etc.) |
| 000:216 | E$PNNF | Path name not found | Pathlist not found — misspelling or wrong directory |
| 000:217 | E$SLF | Segment list full | File too fragmented to expand further; copying the file/disk can help |
| 000:218 | E$CEF | File already exists | Create attempted with a name already in the current directory |
| 000:219 | E$IBA | Illegal block address | Invalid pointer/block size, or damaged device file structure |
| 000:220 | E$HangUp | Telephone data carrier lost | Modem lost carrier |
| 000:221 | E$MNF | Module not found | Not in the module directory, or its header was modified/corrupted |
| 000:222 | E$NoClk | No clock | Request needs the system clock, but no clock is running — use `SETIME` |
| 000:223 | E$DelSP | Suicide attempt | Process requested deallocation of the memory holding its own stack |
| 000:224 | E$IPrcID | Illegal process number | Process ID is non-existent or not accessible to the caller |
| 000:225 | E$Param | Bad parameter ‡ | Service request passed an illegal or impossible parameter |
| 000:226 | E$NoChld | No children | `F$Wait` called with no child process to wait for |
| 000:227 | E$ITrap | Illegal trap code | Trap code unavailable (in use) or invalid in a `TLINK` call |
| 000:228 | E$PrcAbt | Process aborted | Process aborted by the kill signal code |
| 000:229 | E$PrcFul | Process table full | Too many running processes, or no contiguous memory to expand the table |
| 000:230 | E$IForkP | Illegal fork parameter area | Invalid parameters passed to a fork call |
| 000:231 | E$KwnMod | Known module | Install attempted on a module already resident in memory |
| 000:232 | E$BMCRC | Incorrect module CRC | Bad CRC value — regenerate with `FIXMOD` |
| 000:233 | E$USigP / E$Signal | Unprocessed signal pending / signal error | An unprocessed signal is pending. **Renamed across releases** (`Source`, os9exec `debug.c`): `E$USigP` in OS-9 before 2.2, `E$Signal` from 2.2 on — same code 233. os9exec returns it from `F$Send` as the pre-2.2 `E_USIGP` |
| 000:234 | E$NEMod | Non-executable module | Attempted execution of a module that isn't type program/object |
| 000:235 | E$BNam | Bad name | Syntax error in the specified name |
| 000:236 | E$BMHP | Bad module header parity | Module header parity error |
| 000:237 | E$NoRAM | RAM full | No free system RAM, or not enough contiguous memory for a fork request |
| 000:238 | E$DNE | Directory not empty | Attempted to strip the directory attribute from a non-empty directory |
| 000:239 | E$NoTask | No task number available | A new task was requested but every task number is taken |

### 000:240 – 000:255 — I/O errors

Generated by device drivers or file managers.

| Code | Symbolic name | Meaning | Cause |
|---|---|---|---|
| 000:240 | E$Unit | Illegal drive number | Invalid drive/unit number |
| 000:241 | E$Sect | Bad sector | Invalid disk sector number |
| 000:242 | E$WP | Write protect | Device is write-protected |
| 000:243 | E$CRC | CRC error | CRC mismatch on read or write-verify |
| 000:244 | E$Read | Read error | Data transfer error on disk read, or SCF (terminal) input buffer overrun |
| 000:245 | E$Write | Write error | Hardware error during a disk write |
| 000:246 | E$NotRdy | Not ready | Device reports not ready |
| 000:247 | E$Seek | Seek error | Physical seek to a non-existent sector |
| 000:248 | E$Full | Media full | Insufficient free space on the media |
| 000:249 | E$BTyp | Wrong type | Media incompatible with the drive (e.g. double-side disk in a single-side drive) |
| 000:250 | E$DevBsy | Device busy | Non-sharable device already in use |
| 000:251 | E$DIDC | Disk ID change | Media changed with open files — RBF's disk ID in the path descriptor no longer matches the driver's current disk ID |
| 000:252 | E$Lock | Record locked out | Another process holds the record, or a timed lock wait expired |
| 000:253 | E$Share | Non-sharable file busy | Single-user file/device (attribute bit, or opened single-user) already in use by another process. Also the classic "can't delete a file that's currently open (for write)". **os9exec (`Live`, commit `0ee76c1`):** deleting a file another path holds open **for write** now correctly refuses with 253, matching NitrOS-9 — `pRdelete` walks the open-path ring for another writer before deleting. Deleting a file only other *readers* have open still succeeds (deferred-delete: reclaimed on last close), which is correct RBF behaviour, not a gap. Was previously unenforced (any delete succeeded, orphaning the still-open writer's clusters) — same enforcement-laxity class as the E$BMode fix, now closed |
| 000:254 | E$DeadLk | I/O deadlock | Two processes each hold one of two disk areas the other needs |
| 000:255 | E$Format | Device is format protected | Format attempted on a format-protected disk (commonly set on hard disks) |

## Known cross-manual discrepancies

`Manual, Flag`. The two primary sources — the **OS-9 v2.4 Technical
Reference Manual** and the independent **OS-9/68000 Operating System
Technical Manual (July 1985, Revision S)** — were cross-checked card by
card. Almost everything agrees.

**Whole-table check:** every code+symbol pair here was diffed against the
v2.4 manual's error appendix — **87 shared codes, zero symbol mismatches**.
The one apparent conflict (000:200) resolves in Microware's favour and
against that appendix: it prints `E$BPNum` for both 200 and 201, but 200 is
`E$PthFul` in two other Microware manuals and in every call's own error list,
so the appendix has a typo (corrected in the table above). This confirms the
list is Microware-sourced end to end — any word-level overlap with third-party quick
references is just the shared standard codes, not a dependency on them.

Two edition-level disagreements remain, and rather than silently pick a winner,
both readings are recorded here:

- **† Uninitialized user TRAP range.** The v2.4 manual gives
  **000:133–000:147** (`E$Trap`) for uninitialized user TRAP #1–#15. The 1985
  manual instead gives **000:124–000:138** (`E$Trap`) for uninitialized user
  TRAP #0–#14 — a different base offset *and* a different trap-numbering
  convention (0-based vs. 1-based). Note this also means the 1985 numbering
  overlaps 000:124, which the v2.4 manual assigns to "spurious interrupt" —
  the two editions are not reconcilable by a simple off-by-one; treat both
  ranges as edition-specific and confirm against the actual kernel/INIT
  build you're targeting rather than assuming either table is authoritative.
- **‡ 000:225 (E$Param) specificity.** The v2.4 manual describes 000:225
  generically as "bad parameter — an illegal or impossible parameter was
  passed to a service request." The 1985 manual gives a narrower, concrete
  case for the same code: an impossible vector number passed to the IRQ
  polling system. These aren't contradictory — the 1985 description reads as
  one specific instance of the general v2.4 case — but the 1985 manual
  presents it as *the* meaning rather than *an* example, so both phrasings
  are preserved here rather than merging them into one.
- **§ 000:064 symbol spelling.** The v2.4 manual spells this symbol
  `E$IllFnc`; the 1985 manual spells it `E$IllFno` for the identical code
  and meaning. Both are recorded rather than picking one — treat this as a
  spelling variant across editions, not two different error conditions.

## Other error-handling behavior worth knowing

- **`F$Exit` and parent status.** `F$Exit` terminates the calling process:
  open paths close, data memory is released, and both the primary module and
  any installed user trap handlers are unlinked. A parent blocked in
  `F$Wait` receives the exit status (68k: `d1.w`; 6809: `B`, per
  `6809/syscalls-and-module-format.md`'s `F$Exit`/`F$Wait` rows); by
  convention this should be zero for success or an OS-9 error code
  otherwise. If the parent has already died, the process descriptor is
  freed immediately instead of waiting for a `F$Wait` that will never come.
- **Pipe writes behave differently named vs. unnamed.** On an *unnamed*
  pipe, if every writer hits a full pipe, `I$Write` returns `E$Write` to each
  of them. On a *named* pipe, there is no `E$Write` in that situation — the
  writer instead sleeps until a reader opens the pipe and drains it. This
  difference is what lets a named pipe double as a self-destructing
  temporary RAM-disk file (non-empty, no paths open).
- **6809 runtime arithmetic signals are a separate space.** The 6809 C
  compiler's runtime adds three codes to `<errno.h>` that have no 68k
  equivalent confirmed in these sources: `EFPOVR` (40, floating-point
  overflow/underflow), `EDIVERR` (41, division by zero), and `EINTERR` (42,
  overflow converting float to long). On any of these, the running program
  signals *itself* with that number as the signal value; if uncaught, the
  process exits with an error return to its parent. These live in the
  compiler runtime's own numbering, not the kernel `E$` table above, and
  aren't confirmed identical on a 68k compiler.

---

**Sources:** OS-9 v2.4 Technical Reference Manual, Error Codes section
(000:001–000:255, page B-28 for the low range) and "Write/WritLn" (p. 4-13); OS-9/68000 Operating System
Technical Manual (July 1985, Revision S), Appendix C, "Error Codes" and
§14-12 "F$Exit"; OS-9 C Compiler manual, "Introduction to C System Calls"
(p. 3-1) and "Run-Time Arithmetic Error Handling" (p. 1-8); BASIC09 Reference
Manual (Rev H), Functions section (p. 8-5); BASIC09 Reference Manual, Appendix
C "Error Codes" — cross-confirmed word-for-word identical across the Rev F
(Dragon Data, 1983, p. 113-114), Rev G (Tandy), and Rev H editions; Technical
I/O Manual v2.4, "Driver Module Format" (p. 1-23).
