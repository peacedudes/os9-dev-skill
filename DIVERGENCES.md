# Divergences from Microware documentation

**What this is:** a register of every place where this project's documentation
or the runtimes it tests against disagree with, or fail to cover, Microware's
own published documentation. It is maintained for Microware's review.

**Why it exists.** `os9exec` and NitrOS-9 are reverse-engineered
reimplementations built by the user community. Both have had real errors.
Until 2026-07-23 this repo's confidence rules told every contributor that
running one of those reimplementations *resolved* a disagreement with a
manual — with the predictable result that the repo held **540** runtime-derived
`Live` claims against only **5** recorded manual disagreements. That rule is
now reversed (`os9-dev/references/CONFIDENCE-TAGS.md`): a runtime observation
never overrules a manual, and disagreements land here instead of being erased.

**What counts as Microware's word:** see `SOURCE-AUTHORITY.md`. Microware's own
manuals, plus those published under licence by Tandy/Radio Shack, Dragon Data
and Motorola. Third-party books — including the excellent OS-9 Guru — are not
authoritative here, however useful they are as pointers.

**Nothing in this file asserts Microware is wrong.** Where a manual and a
reimplementation disagree, the manual is the specification and the
reimplementation is the candidate defect. Some entries will turn out to be our
error, some a runtime's, some a documentation gap. Adjudicating them is exactly
what we are asking for.

## How entries stay findable

Each entry has an ID (`D-001`). The claim it concerns carries an inline
`⚠ DIVERGENCE D-001` marker **at the point of use** in the reference file, so a
reader relying on that claim sees the warning without ever opening this file.
This register is the aggregate view, not the primary home. The doc-consistency
checker enforces the link in both directions — an entry with no inline marker,
or a marker with no entry, is a build failure.

## Entry format

```
### D-NNN — one-line summary
- **Topic / file:** the skill file and claim affected
- **Microware says:** the passage, with source file and line
- **Observed:** what the runtime(s) actually do, and which runtime
- **Type:** semantic divergence | unimplemented | undocumented | doc conflict
- **Who can settle it:** Microware / real hardware / already settled
- **Status:** open | withdrawn | resolved
```

---

# Part 1 — Confirmed divergences

Manual passage located *and* runtime behaviour observed.

### D-001 — BOOLEAN prints as "True"/"False", manuals specify "TRUE"/"FALSE"
- **Topic / file:** `os9-dev/references/basic09/basic09-language.md` (PRINT
  USING section), `basic09/gotchas.md`
- **Microware says:** two independent authoritative manuals specify uppercase.
  *BASIC09 Programming Language Reference Manual* Rev H (Microware 1980, 1984),
  `68k/BASIC09_Reference_Manual_Rev_H.txt:2493` — "BOOLEAN values print out as
  the character strings: `"TRUE"`…". *BASIC09 Reference Manual* (Tandy 1983),
  `6809/BASIC09_Reference_Manual_Tandy.txt:2128-2129` — "A Boolean operation
  always returns either the character string `"TRUE"` or `"FALSE"`."
- **Observed:** both reimplementations render mixed case. 68k `os9exec`:
  `PRINT #path USING "B8", TRUE` → `"True    "`. 6809 NitrOS-9 with real
  Microware BASIC09 "6809 VERSION 01.01.00" (2026-07-23): `TRUE` → `"True    "`,
  `FALSE` → `"False   "`, `LEN()` 8, output file exactly 18 bytes = 2 × (8+CR).
  Field width matches the manual; only the casing differs.
- **Scope limit, stated honestly:** what was tested is the `B` format of
  `PRINT USING`. The manual passages describe how BOOLEAN values print
  *generally*. Plain `PRINT b` has **not** been separately tested on either
  architecture — if plain `PRINT` yields uppercase, this divergence is narrower
  than stated. That test is queued.
- **Type:** semantic divergence
- **Who can settle it:** Microware, or genuine hardware. Two community
  reimplementations agreeing with each other is not evidence the manual is
  wrong — it is equally consistent with both having inherited the same defect,
  or with the manual describing intent that shipping code never matched.
- **Status:** open

### D-002 — `INTEGER÷0` raises a CPU trap on 68k, not the documented BASIC09 error 45
- **Topic / file:** `os9-dev/references/basic09/gotchas.md` (divide-by-zero)
- **Microware says:** BASIC09 error **45, "Divide by Zero"**, on both
  architectures. `68k/BASIC09_Reference_Manual_Rev_H.txt:6830`;
  `6809/BASIC09_Reference_Manual_Rev_F.txt:5635`;
  `6809/BASIC09_Reference_Manual_Rev_G.txt:6509`;
  `6809/BASIC09_Reference_Manual_Tandy.txt:18148`.
- **Observed:** 6809 NitrOS-9 matches — `Error #045 -- Divide by Zero`, Debug
  Mode if unhandled. 68k `os9exec` does not — `Error #000:105 (E_ZERDIV) zero
  divide TRAP 5`, breaking into the debugger (`Live`, 2026-07-23:
  `a=10 : b=0 : c=a/b`, all INTEGER).
- **Our own error, recorded:** this skill previously stated 68k INTEGER÷0 was
  **silent, no error at all**, tagged `Live` (2026-07-21). Direct retest shows
  that is wrong. A reminder that a `Live` tag records what one run appeared to
  show, not a fact — the earlier test most likely had an `ON ERROR` handler
  swallowing the trap.
- **Type:** semantic divergence (wrong error number / wrong error layer)
- **Open question, deliberately not chased:** whether os9exec's TRAP 5 does what
  BASIC09 expects of it. That is an emulator question, out of scope for the
  skills work.
- **Who can settle it:** Microware, or genuine 68k hardware — does real
  OS-9/68k BASIC09 report 45 here, or 105?
- **Status:** open

### D-003 — `I$MakDir`'s `d1` width was changed from the manual's to match os9exec
- **Topic / file:** `os9-dev/references/68k/syscall-reference.md`, I$MakDir row
- **Microware says:** *OS-9/68000 Operating System Technical Manual* (Microware
  1984), ch. 15 p. 15-13: `d1` = access permissions. The register suffix is
  **illegible in this scan** (renders as `d1.x` in both places it appears), but
  the surrounding prose reads "the **bytes** passed in register `d1`" — plural,
  which points to a word. The 6809 System Programmer's Manual's equivalent uses
  `(B)`, a one-byte register, but that is an architectural difference, not
  evidence about the 68k width.
- **Observed:** an earlier revision of this skill carried `d1.w` and then
  **changed it to `d1.b`, annotated "corrected from `d1.w`"** — on the strength
  of `os9exec`'s implementation.
- **Why it is listed even though unresolved:** this is the exact failure mode
  this register exists for — a Microware-documented value edited to match a
  reverse-engineered reimplementation, with the manual's version erased rather
  than flagged. The width itself is genuinely unsettled; what is certain is that
  agreement with os9exec was not grounds to overwrite it.
- **Type:** method failure (confirmed); no actual divergence
- **Resolution (owner, 2026-07-23):** closed — **both readings were right, and
  there was never a divergence.** The permit bits live in `d1.b`; the caller
  passes the full `d1` register as always, and OS-9/68k uses its low byte. So
  the manual's `d1` and the byte-level `d1.b` are describing the same call
  correctly, from different altitudes. The only real lesson is procedural: our
  table had `d1.w` changed to `d1.b` *because os9exec did that*, and "a runtime
  does it this way" is not a reason to overwrite a manual — the reasoning was
  the defect, not the value.
- **Status:** resolved

**Two plain omissions found in the same pass and simply fixed, not divergences:**
`I$MakDir`'s documented optional input `d2.l` (initial allocation size) was
absent from our table entirely, and `I$MakDir`/`I$Delete`/`I$ChgDir` all showed
no output where the manual documents `(a0)` updated past the pathname.

### D-004 — `F$Sleep` never returns the remaining-ticks count the manual specifies
- **Topic / file:** `os9-dev/references/68k/syscall-reference.md`, F$Sleep row
- **Microware says:** F$Sleep returns how much of the requested sleep was left
  when it woke — so a process woken early by a signal can tell. Two independent
  authoritative manuals: *OS-9/68000 Technical Manual*,
  `68k/M68000_Programmers_Reference_Archive_History.txt:9047` — "OUTPUT: d0.l =
  Remaining number of ticks if awakened prematurely"; *OS-9 System Programmer's
  Manual* (6809), `6809/OS-9_System_Programmers_Manual.txt:4869` — "OUTPUT: (X)
  = Decremented by the number of ticks that the process was asleep."
- **Observed:** `os9exec`'s `OS9_F_Sleep` (`Source/OS9exec_core/fcalls.c`)
  returns without ever writing `d0.l` — the caller's original tick count is left
  in the register. Confirmed by reading the source directly, 2026-07-23; the
  handler's own header comment is stale (it describes `F$Wait`'s output). Its
  dispatch-table entry declares a `d0.l` output that the handler never fills.
- **Consequence:** code that reads `d0.l` after `F$Sleep` to detect an early
  wake, or to resume a partial sleep, gets a wrong value on os9exec — it looks
  like no time passed.
- **Cross-architecture check (2026-07-19, 6809):** real NitrOS-9 6809 *does*
  return it — `F$Sleep` with `X=50` came back `X=23` when signalled early,
  exactly as the 6809 manual specifies. So this is not an OS-9 design question
  at all; it is specifically the **68k os9exec implementation** that drops the
  output. That narrows it to an emulator fix and removes any doubt about what
  the contract should be.
- **Type:** semantic divergence (missing output)
- **Who can settle it:** this one is not really in doubt — two Microware manuals
  agree and the os9exec source plainly omits it. It is an os9exec bug to fix,
  logged for completeness; recording it here so the skill does not present
  os9exec's behaviour as the contract.
- **Status:** open

---

# Part 2 — Divergence candidates: runtime behaviour known, manual passage not yet located

These are **not** yet divergences. Each is a place where a runtime does
something specific and nobody has yet found what Microware's documentation
says. Locating the passage either promotes the entry to Part 1 or closes it.
This is the work queue.

| ID | Topic | What a runtime does | Manual passage |
|---|---|---|---|
| C-02 | REAL ÷ 0 error number (BASIC09) | 68k: catchable, `ERR` = 107. 6809: `Error #045`. Both catchable, different numbers | not yet located |
| C-03 | `F$CpyMem` register contract (6809) | NitrOS-9's `fcpymem.asm` never reads X — a 3-register call (D/Y/U), not the documented 4. That file's *own* header comment still states the 4-register form | manual's shape is recorded; needs exact citation |
| C-04 | `PD_CNT` / `PD_COUNT` path-descriptor offset | `os9exec`'s reconstructed header puts open-count at `$03`; this skill documents `$1A`. **Neither anchor is authoritative** — os9exec's `os9defs/` headers are themselves second-hand reconstructions | not yet located |
| C-05 | `I$Write` / `I$ReadLn` call codes (6809) | Found swapped relative to this skill's table; settled against NitrOS-9's `defs/os9.d` — i.e. against a clone, not against Microware | not yet located |
| C-06 | `SAVE`/`PACK` `>pathlist` | `os9exec` prints `Error #000:043`/`#000:051` spuriously; NitrOS-9 prints nothing and writes correct files. Logged as an os9exec bug | not yet located — is either behaviour documented? |
| C-07 | `SAVE` vs `PACK` redirect target | 6809: `SAVE >rel` → CHD, `PACK >rel` → CHX. Asymmetric and undocumented here until 2026-07-23 | not yet located |
| C-08 | `math` module precision (68k) | `os9exec`'s default `math` is single-precision; whether real OS-9's is too is unknown | not yet located |
| C-09 | GFX2 `GOSET` | Absent from the community-built GFX2 package (`Error #048`, absent from its function table). Note the runtime here is a *third-party* package build, not even NitrOS-9 proper | documented in the Level 2 manual |
| C-10 | GFX2 `PALETTE` argument validation | No range checking at all — register up to 99, colour up to 200 accepted | manual implies 0-15 / 0-63 ranges |
| C-11 | 6809 module type/language byte | Confirmed `(type << 4) \| language`; `dir`/`copy` = `$11`. An earlier revision of this skill claimed `$04` for the C compiler | needs the 6809 C Compiler manual's own module example |

---

# Part 3 — Microware material we do not cover

Authoritative sources sitting unmined or barely mined, measured by citations
across both skills (2026-07-23). For contrast, the third-party Guru and FARNA
references are each cited ~21 times.

| Source | Citations | Consequence |
|---|---|---|
| `OS-9_Primer.txt` (Microware 1994) | **0** | An official Microware introduction to the system, never consulted |
| `OS-9_Internet_Software_Reference_Manual.txt` (Microware 1992) | **0** | `68k/network-sockets.md` carries claims explicitly marked "unverified" and "inferred by analogy to `hostent`, not attested" — while the authoritative manual sits unread. This is the single clearest gap in the set |
| `OS9_Technical_Manual_Disk_File_Organization.txt` (Microware) | **0** | `os9-systems-dev` documents RBF disk structure without citing Microware's own file-organization manual |
| `Microware_Training_OS-9_{Starter,Intermediate,Advanced}.txt` (Microware 1994) | 2 files | Official Microware training material, reached only `memory-and-io.md` and `ipc.md` |
| 68k **process-descriptor field offsets** | not published | No authoritative 68k Microware manual in this corpus gives a `P$` offset table — the descriptor is described in prose only. The offsets in `os9-systems-dev/kernel-internals.md` trace to the third-party Guru book via os9exec's reconstructed struct; Microware sources confirm field *names/semantics* but not offsets. `Source`-tier by necessity, not Microware-verifiable here (2026-07-23) |
| `OS-9_Pascal_Reference_Manual.txt` (Microware 1984) | out of scope | Deliberate prior scope decision, recorded not forgotten |
| `Enhanced_OS-9_68K_*` (Microware 2000, v3.2) | out of scope | Deliberately excluded to avoid importing v3.2 semantics into v2.4 material |

---

# Part 4 — Gaps and inconsistencies within Microware's own documentation

Offered in the spirit the LICENSE describes — these are places where the
published documentation is silent, self-contradictory, or where OCR of the
surviving scans cannot resolve what was originally printed. Microware is the
only party who can say which.

- **`F$Fork`'s register layout conflicts across manuals.** Different Microware
  manuals give different input-register tables for the same call. This skill
  carried it as an unresolved flag for a long time before matching one variant
  against a reimplementation — which settles what the reimplementation does,
  not what was specified.
- **Shell redirection forms `>+` and `>-` appear undocumented.** Both are real,
  working OS-9 shell syntax (append-or-create; truncate-or-create). *Using
  Professional OS-9 v2.4* documents only `<`, `>`, `>>`.
- **Syscall codes `$1F`, `$20`, `$23`-`$26` (6809)** produce zero hits across
  the entire corpus — neither documented nor confirmed reserved.
- **`wmode` is absent from the Level 2 manual entirely** (TOC and full-text
  search both empty), though it is a real utility documented by third parties.
- **Assembler label length: 1-8 vs 1-9 characters.** Resolved as an RMA-vs-`asm`
  difference rather than a contradiction, but the manuals do not state the
  distinction plainly.
- **The v2.4 Technical Reference Manual's error appendix mislabels error 200.**
  It prints `000:200 E$BPNum PATH TABLE FULL` — but `E$BPNum` is also (correctly)
  given for 201, and PATH TABLE FULL is `E$PthFul` everywhere else, including the
  *OS-9/68000 Technical Manual* (`000:200 E$PthFul`), the 6809 *System
  Programmer's Manual* (`$C8 200 E$PthFul`), and this same manual's own
  per-call error lists (`I$Open`/`I$Attach` cite `E$PthFul` for path-table-full).
  So it is a typo in one edition's appendix, not two codes sharing a symbol.
  Low stakes — the numeric code is what matters at runtime — but worth a fix in
  that manual. Whole error-code list otherwise cross-checked clean:
  **87 shared codes, zero name mismatches** against the v2.4 appendix
  (2026-07-23).
- **OCR collisions in the surviving scans — a caution, not a finding.** The
  6809 System Programmer's Manual scans render `F$AllPrc` and `F$FModul` both
  as `$4B`, and `F$CpyMem`/`F$GPrDsc` similarly collide. **No divergence may be
  raised on an OCR-only reading**; reporting a phantom disagreement to the
  people who wrote the original would be worse than reporting nothing. Every
  Part 1 entry requires a legible passage.

---

# Part 5 — Claims resting only on non-authoritative sources

Not divergences — claims whose only backing is a third-party book. Under the
authority rule these are, for review purposes, unsourced. Guru and FARNA are
each cited ~21 times across the two skills; those citations have not yet been
individually traced back to a Microware passage. Auditing them is queued.

---

# Part 6 — What has NOT been audited

Stated plainly so this register is not mistaken for a completed audit.

**Structural surface — DONE (2026-07-23).** The "wrong value silently breaks
code" claims have now been individually diffed against Microware manuals, both
architectures, and either matched (many lifted `Source`→`Manual`) or produced
the Part 1 entries above:
- 68k user-mode syscall register contracts (whole table); 6809 user + I$ +
  a privileged sample — all against the System Programmer's Manual §11/12 and
  the OS-9/68000 Technical Manual chs. 14-15.
- 68k error codes (87/87 names) and 6809 syscall + GetStat codes.
- Struct offsets: 68k + 6809 module headers, device descriptor, path
  descriptor, SCF option area, RBF identification + file-descriptor sectors —
  all against the I/O Technical Manual / Disk File Organization manual.
- BASIC09 core semantics and C-library K&R facts.
- **Recurring caveat:** these scans carry OCR digit-damage (8↔B, 8↔E); every
  apparent mismatch resolved to scan damage via a second Microware source, none
  to a real skill error.

**Behavioural long-tail — NOT yet audited.** The remaining `Live` claims are
mostly *behavioural* (what a call/utility does, timing, edge cases) rather than
structural, and are lower-consequence — a wrong description misleads, but does
not silently corrupt a struct or dispatch. Still worth doing: utility/shell
command option flags, the less-common 6809 privileged calls in full, and the
GFX/windowing behaviour claims.
- **Priority order for continuing**, highest consequence first: utility
  behaviour → less-common privileged calls → GFX/windowing.
- **The instrument that would automate most of this** is the live-verification
  corpus, if it is made rerunnable on genuine OS-9. Then every PASS/FAIL
  mismatch is a divergence report rather than a hand audit. Scoped in the
  os9exec repo's `ROADMAP.md`; currently only 5 of 86 68k files have
  machine-checkable oracles, 0 of 99 on 6809, and the runner is welded to
  `os9exec` as a host process.
