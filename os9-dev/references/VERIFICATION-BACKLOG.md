# Verification & Expansion Backlog

This is a working backlog, not a status report — read `INDEX.md`'s
confidence notes and each file's own header for current state. This file
answers a different question: **what's worth doing next**, across both
`os9-dev` and `os9-systems-dev`, on both architectures.

## The framing: verify *and* expand, not just re-check

"Verify" undersells the job. The highest-value work this project's history
has actually produced hasn't been re-confirming facts already marked
verified — it's been running real code and finding things nobody had
written down at all: `BASE0` needing a space (a live-syntax bug no
citation pass ever caught), `PACK`/`asm`'s object output landing in the
execution directory instead of the current one, OS9Defs assigning I$/F$
codes by table position rather than literal `EQU` values, the exact
register-level reason `clr b` errors but `clrb` doesn't. None of those
were "verify this claim" — they were "run something real and see what
actually happens." Treat every session against a live REPL as a chance to
do both: confirm what's written, and go looking for what isn't.

Practical discipline for either goal: write the smallest real program that
exercises the thing (not a synthetic snippet if a real one is easy),
confirm the happy path, and **also** try one error path — most existing
docs only describe success. Cross-reference the resulting finding against
the rest of the skill tree before "fixing" anything that looks like a
contradiction (see `feedback_verification_cross_check_own_sources` in
project memory) — a lone dispatch/session correcting an established fact
in isolation is a known regression pattern here.

## Priorities

**For content expansion: 6809 parity is the owner's stated goal**
(2026-07-18) — see the "6809 parity build-out" section below.
**For live verification/bug-hunting: 68k first** — this project owns and
ships `os9exec`, so a 68k finding is often a real emulator bug, and
`os9exec`'s C source is a second independent ground truth (cross-check
only, never extract). 6809/NitrOS-9/XRoar are someone else's software;
findings there are almost always doc fixes only. **6809 now has its own
analog of that same cross-check**, added 2026-07-17: NitrOS-9's kernel
source cloned locally at `os9/nitros9/source/` (see project memory
`nitros9-kernel-source-crosscheck` for provenance/license status) — same
rule applies, secondary cross-check only, never a primary source, never
extracted at length. Trust the actual code over any comment sitting
above it; this project's own first use of it found a NitrOS-9 source
comment describing the wrong function entirely.

## Skill-quality punch list (2026-07-20, from the editorial polish pass)

Ideas for making the skills better that aren't "run more live tests" —
tracked here to work through opportunistically, not all at once:

1. **DONE 2026-07-20 — the 4 real contradictions the Fable editorial
   pass flagged, resolved** (see below); the other 2 items it flagged
   (`E$`/`E_` error-prefix mixing, `os9-dev/SOURCES.md`'s per-file table
   missing 5 self-documenting files) were correctly assessed by that
   pass as deliberate/non-issues, not contradictions needing a fix.
2. **Wrap the ~90 6809 test files (`test/6809-live-verification/`) into
   an actual runnable regression suite** — a driver script that deploys
   all of them, runs each, collects PASS/FAIL, so re-verifying against a
   future NitrOS-9 release is one command instead of a day of manual
   per-file work. Not started.
3. **A cheap automated consistency check**, not another full editorial
   pass — grep every `see X.md`/cross-reference and confirm the target
   exists; flag any paragraph that repeats near-verbatim across two
   files. Turns what the Fable pass did by hand into something that
   catches regressions on every future edit, for free. Not started.
4. **A "don't touch without supervision" 6809 syscall risk table** — the
   risk categorization used to scope batch 5 (`F$Boot`=reboot,
   `F$AProc`/`F$NProc`=scheduler-internal/no-return,
   `F$GCMDir`=explicit-kernel-only, `F$IOQu`=untimed-hang-risk,
   `F$IRQ`=real-hardware-vector, `F$SSvc`=patches-live-dispatch-table,
   `I$SetStt`=channel-disruption-risk, `F$Chain`=looks-unsafe-on-failure)
   only exists scattered across report prose
   (`dogfood-report-syscalls-batch5-2026-07-19.md`) — worth one real
   table in `6809/syscalls-and-module-format.md` or `STATUS.md` so the
   next session doesn't re-derive the same judgment calls. Not started.
5. **A "verified against" version marker convention** — no `Live` tag
   currently says which NitrOS-9 disk image / `os9exec` commit it was
   confirmed against. If the disk image or emulator is ever rebuilt,
   there's no way to tell which facts are timeless (register
   conventions) vs. build-specific (a particular error code from a
   particular kernel). Not started, needs a design decision first (a
   footer date is already common — is that enough, or does it need an
   explicit build/commit reference?).

### Contradiction 1 — INTEGER÷0 behavior (basic09) — RESOLVED 2026-07-20

`gotchas.md` had the stale pre-2026-07-18 claim ("silently falls
through, no error, on both architectures"); `basic09-language.md` had
already been corrected that day with a real `Live` (6809) test
(`Error #045`, Debug Mode) but `gotchas.md` was never updated to match.
Fixed: `gotchas.md` now states the same `Live` (6809) finding, 68k still
flagged unverified, with a note that this file previously said the
opposite.

### Contradiction 2 — PRINT USING `B`-format tag mismatch (basic09) — RESOLVED 2026-07-20

`basic09-language.md`'s version was the more precise, verifiable one
(exact printed string `"True    "`, field width, explicitly scoped
`Live (68k)` only, explicit "6809 not yet checked"). `gotchas.md`'s
"Live on both" had no 6809-specific detail behind it — almost certainly
an unverified extrapolation, not a real second test. Fixed: `gotchas.md`
now matches the 68k-only scoping. **Genuine remaining live-test
opportunity, not urgent**: nobody has actually run `PRINT USING "B8"`
on real 6809 NitrOS-9 yet to confirm the mixed-case rendering there too.

### Contradiction 3 — C true-linefeed escape: `\e` vs `\LF` — RESOLVED 2026-07-20

Checked the already-cited primary source directly
(`os9/txtResources/6809/OS-9_C_Compiler_Microware.txt`, the 1983
Microware C Compiler manual — OCR quality is rough but the relevant
passage is legible): its "Control Character Escape Sequences" section
documents `\e` (lowercase) as the linefeed escape, explicitly "to
distinguish LF from `\n` which on OS9 is the same as `\r`." Fixed:
`c/kandr-vs-ansi.md`'s `\LF` corrected to `\e`, now matching
`common/unix-differences.md` and `common/os9-mental-model.md`, with the
manual citation attached.

### Contradiction 4 — string-literal storage location (C, 68k) — RESOLVED 2026-07-20

Not a 6809-vs-68k difference — `module-format.md`'s version was simply
more precise and mechanistically explained (shared read-only TEXT,
*except* `char array[] = "..."` which gets its own per-process DATA
storage — matching the linker's actual `M$IRefs` TEXT/DATA-pointer
split it documents). `kandr-vs-ansi.md`'s flat "DATA section" was wrong
for the `char *s = "x"` example it was actually describing. Fixed:
corrected to match `module-format.md`, with a cross-reference, and
sharpened the practical consequence (writing to it risks a real fault,
not just "undefined behavior," since it's read-only shared memory).

### 68k — os9-dev

- **DONE 2026-07-18 — program-entry register state** now documented in
  `68k/os9-68k-assembly.md` ("Program entry register state"): what `A0–A7`/
  `D0–D7` hold when `F$Fork`/`F$Chain` transfers control to `M$Exec`. Was a
  genuine gap (the skill had `F$Fork` *inputs* and the module entry *offset*
  but never the child's entry state). Load-bearing fact captured: `A0`, `A2`,
  `A4`, `D4`, `D7` are **undefined** at entry (os9exec sentinel-fills them and
  now bus-errors on a deref — this is `pwrstat`'s latent bug). `Source`
  (os9exec `prepFork`). **Residual:** the exact slot for the *informational*
  registers (D2/D3/D5/D6) is `Source`-only; not yet cross-checked against
  `Manual` (which conflicts internally, same as the `F$Fork` input table).

Items surfaced by the 2026-07-18 redundancy/consistency/density/plagiarism
audit pass (flagged per this file's own "correct a lone finding"
discipline — not silently fixed):

- **`common/module-format.md`'s 6809-C-compiler type/language byte looks
  wrong, not just under-cited.** The file states the compiler sets `$4`
  ("C program — 6809 object"), but `6809/syscalls-and-module-format.md`'s
  own type/language table marks language nibble 4 as "C I-code
  (reserved/unimplemented)," and `c/os9-clib-reference.md`'s `os9fork()`
  entry says a 6809 program's `lang` is object code (1), with 4 reserved
  for that same unimplemented C I-code — both point toward the real byte
  being `$11` (type=Program/`$1`, lang=Object/`$1`), not `$04`. Flagged
  in place in `module-format.md` rather than silently corrected. Needs a
  primary-source recheck (the 1983 6809 C Compiler manual's own module
  example, if it has one) or a live `ident` decode of a real 6809-compiled
  C module.
- **DONE 2026-07-17 — `basic09/basic09-language.md` and
  `basic09/gotchas.md`'s REAL÷0 staleness fixed.** Both described 68k
  `REAL÷0` as an uncatchable crash (`Error #000:107 E_TRAPV`, `ON ERROR
  GOTO` "cannot intercept it"), stale against this session's own
  `ad4c16f` commit ("BASIC09 REAL/0 (and F$STrap arithmetic traps) now
  catchable on 68k", regression test in `test/Sources/OS9Tests/main.swift`).
  Both files now state `REAL÷0` is a catchable trap on 68k matching
  6809's always-catchable behavior, per project memory recording this as
  `Live`. **Not independently re-verified in this pass**: the
  exact BASIC09-level error text/number 68k now shows (6809's is
  `Error #045`) — the regression test covers the `F$STrap`
  assembly-level dispatch, not a BASIC09-level live run. Worth a live
  `nitros9repl`-style confirmation on 68k `os9exec` if the precise wording
  matters for a future card.
- **RESOLVED 2026-07-18 — `basic09/basic09-language.md`'s INTEGER÷0 passage
  corrected and architecture-tagged.** Prior passage claimed `Live` —
  "silently falls through, no error, no trap fired," but 6809 live test
  (on NitrOS-9 BASIC09) confirmed INTEGER÷0 generates `Error #045 -- Divide
  by Zero` and breaks into Debug Mode, identical to REAL÷0 on 6809.
  Passage rewritten to document 6809 behavior as `Live`; 68k behavior
  flagged as unverified.
- `chd` with no argument → home directory; `chx` with no argument → no-op
  (`common/os9-tools-and-shell.md`, `common/unix-differences.md`). `Hearsay`;
  live-verify both, plus whether "home" means `HOME` env var or
  the password-file data dir.
- **RESOLVED 2026-07-18 — `>+`/`>-` redirection forms confirmed `Live`.** Both forms are real OS-9 shell syntax, not documented in Using Professional OS-9 v2.4 (which lists only `<`/`>`/`>>`). Behavior: `>` = create new only (fail if exists); `>+` = append to existing or create new; `>-` = truncate/overwrite existing or create new. Tested on NitrOS-9 6809.
- Shell option letters (`t`/`nt`, `p`/`np`, `x`/`nx`) in
  `os9-tools-and-shell.md`: standard set, but worth a live `set`/invocation
  check.
- tmode/xmode semantics (`utility-usage.md`): `Manual`, confirmed against
  Using Professional OS-9's own entries (tmode = open path, temporary;
  xmode = in-memory descriptor, immediate, survives until reboot, five
  serial params need deiniz→xmode→iniz). Live-testing xmode persistence
  on os9exec is low-value — the emulator's device layer may not implement
  descriptor updates faithfully, so a divergence there would say more
  about os9exec than OS-9.
- PACK/SAVE `>pathlist` spurious-error behavior
  (`basic09/pack-and-runb.md`): observed on os9exec only — unknown whether
  real OS-9 does the same. Test on 6809 NitrOS-9 BASIC09 if possible.
- os9exec open oddities moved out of the reference files (they're emulator
  bugs, not OS-9 facts — tracked in the os9exec repo): `load -s a b c` can
  silently skip one module; intermittent trap-handler-install race
  (timing/baud-pacing-correlated, `-r` suppresses the boot-time
  manifestation).

- **No tracked audit of syscall-by-syscall live confirmation exists.**
  `68k/syscall-reference.md`'s own header admits calls are "attested by
  name in at least one merged card," with register layouts "not
  independently re-derived this pass... carried forward" for many
  entries — that's `Manual` confidence, not the same as an
  assembled test actually exercising the call. Given how much BASIC09/C
  testing this project has done, many calls are probably confirmed
  *indirectly* (e.g. file I/O behavior via C stdio calls that themselves
  wrap I$ calls) without ever being individually assembly-tested with
  known register inputs and checked against documented outputs. Building
  that audit — which calls have real direct confirmation vs. indirect vs.
  none — is the first, highest-leverage step before picking individual
  calls to test.
  **IN PROGRESS, started 2026-07-20, batch 1 — 10 calls now `Live`.**
  Free backfill from existing dogfood work (`I$Open`/`I$Read`/`I$Write`/
  `I$Close`/`F$Exit`/`I$SetStt`/`F$STrap`, 7 calls) plus new testing
  (`F$ID`/`F$Time`/`F$CmpNam`, 3 calls, all fully resolved by checking
  `os9exec`'s own source directly — see
  `dogfood-report-syscalls-batch1-2026-07-20.md`). **Key methodology
  finding: for 68k, unlike 6809/NitrOS-9, this project's own `os9exec` C
  source (`Source/OS9exec_core/fcalls.c`/`funcdispatch.c`) is a direct,
  authoritative ground truth for exact register conventions — check it
  BEFORE guessing a convention in test code, not after a live test fails
  ambiguously.** This resolved `F$CmpNam` definitively (a genuine
  register-discipline bug in the test itself, `moveq` vs `move.w` not
  clearing the full register) after three live-only attempts had failed
  to explain it. Real toolchain gotchas found: `(pc)`-relative
  addressing required everywhere (like 6809's `,pcr`); `ds.b` isn't a
  valid directive on this `r68`; `r68 -O=` doesn't reliably overwrite an
  existing `.r` file, `del` first.
  **Batch 2 — module/process lifecycle, 5 more calls now `Live` (15
  total).** `F$Load`/`F$Link`/`F$UnLink`/`F$Fork`/`F$Wait` all confirmed
  cleanly in one file using a real forked child module
  (`test/68k-live-verification/batch2-01.a`) — `F$Wait`'s returned exit
  status matched the child's own `F$Exit(77)` exactly, full lifecycle
  confirmation. **`F$Fork`'s long-standing `Flag` (conflicting register
  layouts across manuals) is now resolved** — `os9exec`'s real
  implementation matches this skill's existing table exactly. Applying
  the batch-1 register-discipline lesson proactively meant zero
  register bugs this time. See
  `dogfood-report-syscalls-batch2-2026-07-20.md`.
- Two already-flagged, concrete, small open items in
  `c/os9-clib-reference.md`: `os9fork()`'s `modname` resolution rule
  (does a bare name resolve via `PATH`/module directory the way Shell
  does, or does it require a full path — only a full path has been
  tested) and its `datasize` sizing rule (a `4096`-byte guess worked live
  but isn't derived from any documented rule).
- `common/module-format.md`: PSECT's claimed restriction "is unconfirmed
  for 68k" per the file's own note — a small multi-section assembly test
  would settle it.
- `68k/os9-68k-assembly.md` (~line 239): flags an RMA-specific claim as
  unconfirmed for 68k — worth a direct look now that this session's 6809
  work has fresh RMA/RLINK context to compare against.
- `idbg`/OS-9 `debug` command: some commands verified live already
  (`break`, `sc`/`sd`/`sm`, `gs`, `di`, `q` — see project memory
  `os9-dev-skill`), but there's no tracked checklist of the full
  documented command set vs. what's actually been exercised. Build one
  the same way this session did for 6809's debugger (`:` confirmed,
  `B`/`G`/`M`/`S`/`E` not yet).

### 68k — os9-systems-dev (the bigger gap)

DONE 2026-07-17 — verification-status headers added to all three files
(`device-drivers.md`, `kernel-internals.md`, `file-managers.md`).

DONE 2026-07-17 — System Globals / Process Descriptor struct-layout
cross-check against `os9exec`'s own C source. Findings:
- **Process Descriptor**: `os9exec`'s `procid` struct
  (`os9defs/procid_from_book.h`) is wired byte-for-byte into
  `F$GPrDsc`/`F$GPrDBT` as the real guest-visible descriptor image —
  every offset kernel-internals.md describes matches it exactly
  (`P$SigLvl`/$370, 32-entry memory-area arrays, 15 trap-handler slots).
  Found and fixed one real bug: `P$SigLvl` was never populated from the
  emulator's actual signal-mask-nesting counter (`cp->masklevel` in
  `procstuff.c`'s `sig_mask()`) — `BuildPrcDsc()` in `fcalls.c` now copies
  it in. Full test suite green (128/128) after the fix.
- **System Global Memory**: not cross-checkable the same way — `os9exec`
  has no in-memory struct for it at all; `F$SetSys` is a self-described
  "half-dummy" stubbing most `D_*` vars including `D_MinPty`/`D_MaxAge`/
  `D_ActAge` (so the documented scheduler algorithm is real-OS-9 behavior
  `os9exec` doesn't itself replicate). Two individual values *did* confirm
  exact: 16-byte minimum allocation unit, 100Hz default tick rate.
- **Device Descriptor** (`device-drivers.md`): `module_from_book.h`
  confirmed `M$Mode`/`$37`, `M$DevCon`/`$3C`, `M$Opt`/`$46` exactly, and
  filled in three previously-undocumented fields: `M$Port`/$30,
  `M$FMgr`/$38, `M$PDev`/$3A (this resolved the file's "which
  driver/file-manager does a descriptor select" known gap).
- **Path Descriptor** (`file-managers.md`): `PD_FST`/$2A (42-byte header)
  confirmed exact. Turned up a `Source, Flag`: `os9exec`'s own
  `sgstat_from_book.h` defines `PD_CNT` (open count) at offset `$03`, not
  the `$1A` this skill documents for `PD_COUNT` — and it's dead code
  (`os9exec` implements no `I$Dup`, so there's no live counter to check
  either offset against). Tagged `Source, Flag` in both files rather than
  guessed at.
- **Module Directory**: `mdir_entry` struct shape (address/group/size/
  link-count) confirmed structurally, but `os9exec`'s group field mirrors
  the module's own address rather than tracking true same-file groups —
  a known simplification, not a layout bug.

- **DONE 2026-07-18 — attempted, found a platform limitation, not a
  documentation gap.** A dogfood pass built a minimal `Drivr`-type module
  (68k, in-memory loopback SCF driver) end-to-end — assembled, linked,
  CRC-valid, byte-correct jump table, installed via `iniz` — exactly per
  this skill's own guidance. **The kernel never invoked it, at any entry
  point.** Confirmed at the `os9exec` source level (not just live
  symptoms): `I$Attach` (`icalls.c`) is an explicit dummy that never
  allocates driver storage or calls `Init`; device I/O dispatch runs
  through a fixed C table keyed by hardcoded path-prefix matching, never
  by executing an installed module's code; `iniz` has zero emulator-side
  implementation (`grep -rin iniz Source/` = 0 hits). This is a real
  `os9exec` feature gap (implementing real driver dispatch would be a
  substantial addition), not a bug and not something a better-written
  skill could have prevented — `os9-systems-dev/SKILL.md` and
  `device-drivers.md` now both state this plainly so the next attempt
  doesn't re-derive it from scratch. Full report:
  `test/68k-live-verification/dogfood-report-driver-2026-07-18.md` (in
  the `os9exec` repo) — also has 5 new confirmed toolchain facts
  (quote-style for `dc.b` strings, `l68 -o=` naming/output-directory
  behavior, the 6-operand `psect` form's limits, a destructive
  double-`flip -m`), all folded into the skill files. **Toolchain half of
  the original goal (module format, byte-correct `Drivr`/`Devic`
  assembly) is now genuinely `Live`-confirmed** — only the entry-point
  register convention remains untestable, and now for a documented
  reason rather than an open question.
- Scheduler algorithm: the "age-plus-priority, aged by queue-entry events
  not context switches" correction was made once during the original
  rebuild (card-extraction level) but never behaviorally confirmed live —
  moot for direct `os9exec` cross-check now that `D_ActAge` etc. are
  confirmed unimplemented, but still worth a live two-priority test
  against real OS-9 semantics if `os9repl.sh` makes it feasible.

## 6809 parity build-out (owner priority as of 2026-07-18: "CoCo docs scanned, 6809 as complete as possible")

The 6809 corpus (`os9/txtResources/6809/`, ~7.5 MB) is only partially
mined. Gaps below are ordered by value; each is a session-sized
card-extraction job (Haiku per document, per standing process rules —
shingle-scan against the corpus afterward, per the copyright rule above).

1. **DONE 2026-07-17 — `6809/utility-usage.md` built.** Card-extracted
   from `OS-9_Level_2_Operating_System_Manual.txt` lines 5633–10500
   (all ~45 commands, attr…xmode incl. CoCo-only cobbler/config/
   display/montype/tuneport/wcreate) plus the two Level 1 Users Manuals
   and two Farna Quick References as cross-checks; several items now
   `Live` (nitros9repl.sh `help`) (see `6809/STATUS.md` for
   the full list — dcheck options, wcreate screen types, tmode/xmode
   baud table and `psc=` name correction, cobbler's Level-2 existence,
   NitrOS-9's own format syntax). Shingle-scanned clean against all five
   sources. Card trail:
   `docs/superpowers/plans/2026-07-17-6809-utility-usage/cards/` (os9exec
   repo). **Still open, left for a follow-up pass:** `ex`/`list`/`wmode`
   need their actual Level 2 manual entries pulled directly (an
   extraction-task-split gap, not evidence of Level 2 absence); `tape`,
   `tapegen`, `diskcache`, `devs`, `irqs`, `events`, `code`, and other
   68k-documented utilities have no 6809 card yet; FORMAT's vintage
   dash-prefixed density letters (`-sd`/`-dd`) remain unconfirmed since
   NitrOS-9's own `format` doesn't use them at all.
   **Follow-up gap-closing pass, DONE 2026-07-18:** two of the three open
   items closed (FORMAT's density letters, the third, stay open — see the
   end of this paragraph). `ex` and `list` now carry their real Level 2 manual entries
   (lines 7459 and 8119) instead of Level-1-only sourcing; `list` picked
   up the manual's own "don't LIST an executable, use DUMP instead"
   warning, `ex` picked up the zero-process/reboot risk and the `shell
   i=/term&` recovery trick. `wmode` stayed Farna-2nd-edition-only but is
   now confirmed genuinely absent from the Level 2 manual itself (TOC and
   full-text search both empty), not an extraction miss. `tape`,
   `tapegen`, `diskcache`, `devs`, `irqs`, `events`, and `code` were
   searched for across all five 6809 sources this file cites and found in
   none of them — documented as confirmed-absent entries rather than left
   silent, with `events`' absence tied to 6809's process-signal IPC model
   (`F$Send`/`F$Icpt`/`F$Sleep`) differing from 68k's named-event-object
   one (`F$Signal`/`F$Wait`). **Incidental find:** the file catalogued in
   this corpus as the Farna "1st edition" CoCo quick reference is
   mislabeled — its title page identifies it as Professional OS-9/68000
   documentation, not CoCo/6809; its DEVS/IRQS/EVENTS/TAPE/CODE entries
   describe the 68k utilities, not a second 6809 source. Only the
   genuinely-CoCo 2nd edition and the 1982 Tandy CoCo quick reference were
   treated as 6809 cross-checks going forward. This also means the
   `tmode`/`xmode` display-only distinction, previously credited to "both
   Farna quick references," is single-sourced on the 6809 side, not
   doubly cross-checked — corrected in `utility-usage.md`'s tmode/xmode
   section. **Not re-audited:** whether any *other* already-written fact
   in this file leaned on the mislabeled 1st-edition file specifically
   (as opposed to the genuine 2nd edition) — the body text never cited an
   edition by name per-fact, so risk looks low, but a dedicated
   re-audit pass would be the way to fully rule it out. FORMAT's vintage
   dash-prefixed density letters remain open (untouched by this pass, not
   pulled into scope).
2. **DONE 2026-07-17 — `6809/gfx-windowing.md` built.** Card-extracted
   from `OS-9_Level_2_Operating_System_Manual.txt` lines 19300-24175
   (both `RUN GFX(...)`, the Level 1 low-res VDG package, and `RUN
   GFX2([path,]...)`, the Level 2 high-res graphics/windowing package —
   drawing primitives, window/device-window lifecycle, Get/Put buffers,
   palette/color, cursor/text control) plus an independent second OCR of
   the same appendix reprinted in `BASIC09_Reference_Manual_Tandy.txt` as
   a cross-check; no behavioral disagreements surfaced, only heavier OCR
   noise on the cross-check side. One cross-reference resolved with high
   confidence: `DWSET`/`GPLOAD`'s numeric window-format codes match
   `wcreate -s=<type>`'s table in `utility-usage.md` (already
   `Live` on nitros9repl.sh) byte-for-byte. Shingle-scanned clean
   against both sources. Card trail:
   `docs/superpowers/plans/2026-07-17-6809-gfx-windowing/cards/` (os9exec
   repo). **Follow-up gap-closing pass, same day:** `GCOLR`'s full
   syntax found in the BASIC09 Reference Manual Rev G (unchecked by the
   original pass); `OWEND` confirmed no-argument from five converging
   worked examples; `DEFBUFF` spelling and `FONT`'s group number (200)
   both settled by re-reading the primary source directly. `COLGR` turned
   out to be a false positive — a BASIC09 example variable name, not a
   function. **2026-07-18, first attempt**: tried parameter-validation
   testing against the NitrOS-9 nitros9repl.sh image; GFX2 module not
   found in test image (graphics support appears unavailable or not
   installed on this EOU_BETA4 variant).
   **2026-07-18, resolved**: built the community `gfx.asm`/`gfx2.asm`
   package (this project's own copy at
   `os9/nitros9/source/3rdparty/packages/basic09/`) with `asm` (four
   porting fixes needed for `asm`/MIA vs. the modern `lwasm` the source
   was actually written for — see
   `test/6809-live-verification/dogfood-gfx2-install-notes.md` in the
   os9exec repo) and installed it on the live test disk via ToolShed
   (found and worked around a real ToolShed `copy -r` segment-corruption
   bug along the way, same file). Both open items now `Live`:
   `GOSET` is confirmed **absent** from this real GFX2 build (`Error
   #048 -- Unimplemented Routine`, and zero occurrences in the module's
   own ~60-entry function table) — not merely undocumented, genuinely
   not a real function. `PALETTE`'s register/color arguments are
   confirmed to have **no software range validation** at all (register
   up to 99, color up to 200, both accepted with no error, including
   against a real opened window path) — the presumed 0-15/0-63 hardware
   ranges are unenforced, not merely unconfirmed. Full narrative and the
   BASIC09 test variants run:
   `test/6809-live-verification/dogfood-report-gfx2-2026-07-18.md` and
   `dogfood-gfx2-goset-palette-test.bas` (os9exec repo). `gfx-windowing.md`
   updated directly with both findings. **Still open:** everything else
   in the file remains `Manual` (actual pixel/graphics render not
   attempted this pass); the disk now has GFX2 installed and persists
   across restarts, so further non-visual bookkeeping claims in the file
   could be made `Live` in a future pass without needing to redo the
   install.

   **2026-07-18 — the "can't observe a screen" blocker is GONE.** Built
   `tools/cocoscreen.sh` (os9exec repo): window-scoped screenshots of XRoar
   plus HID-level keystroke injection. Full method, and the several traps
   that cost time, are written up in `6809/reading-the-coco-screen.md`.
   Headlines: CoCo CLEAR = host backtick (cycles screens); XRoar must be
   frontmost or injected keys are silently dropped; AppleScript System
   Events cannot inject keys correctly; XRoar's `-gdb` wedges the emulator,
   don't try it; get windint `$1B` opcodes from `source/lib/alib/windefs.as`
   rather than guessing.

   **2026-07-18 (later) — pixel output achieved and a verification pass run.**
   Confirmed `Live`: `BAR` filled / `BOX` outline, `BOX` not moving the draw
   pointer, bare `CIRCLE`/`ELLIPSE` centring on it, `ELLIPSE`'s separate
   radii, `LINE` moving the pointer, the screen-format table's column counts
   (types 6/7/8 via what `wcreate` accepts), type 5 measuring 640 pixels
   wide, and the whole GFX2 **BASIC09 calling sequence** (argument order and
   arity for DWSET/SELECT/COLOR/LINE/BOX/CIRCLE). Corrected: the "X range
   0-639" quoted throughout is only a *640-wide screen's* range — coordinates
   are screen-relative and rescaled into the window by
   `window_width/screen_width`, so a 320-wide screen's range is 0-319, and
   out-of-range values are silently accepted. Also corrected: `SELECT` does
   **not** bring a screen forward (only CLEAR does). New tools:
   `tools/cocoscreen.sh` (screenshot / keystrokes / `measure` for exact ink
   geometry) and `tools/b09run.sh` (compile+run a BASIC09 procedure on the
   guest). Full narrative:
   `test/6809-live-verification/dogfood-gfx-pixels-2026-07-18.md`.

   **Two traps recorded there that will otherwise be re-hit:** a raw
   windint `$1b44` test *looks* like it refutes the `LINE` draw-pointer
   claim — it doesn't, GFX2's `"Line"` maps to the `$46` moving variant; and
   a backgrounded BASIC09 job must have `>/nil >>/nil` or it wrecks the REPL
   channel, which then makes guest-side behaviour look broken.

   **NEXT SESSION STARTS HERE.** The old "a shell won't stay alive on a
   graphics window" blocker is **solved**: don't use a shell at all — run a
   backgrounded BASIC09 procedure ending in `LOOP`/`ENDLOOP` on the window
   (`tools/b09run.sh <name> --bg`). That holds the path open, so the window
   survives and its screen joins the CLEAR cycle. Remaining gaps:

   - **Reaching a specific window's screen is still fiddly.** Only screens
     with a live process appear in the CLEAR cycle, and several background
     runs drew nothing findable — likely a harness problem rather than a
     GFX2 one, since the identical calls succeed in the foreground. A
     deterministic "show window X" would unblock a lot; `SELECT` does not
     do it.
   - **`CWAREA` parameter encoding unknown.** `display 1b 25 00 00 14 18`
     produced a full-width black band and killed later drawing, so its
     documented *rescaling* behaviour is untested. Settling it would also
     confirm the `window_width/screen_width` model from a third angle.
   - **Untested primitives:** `ARC`, `FFILL`/`Fill`, `FCIRCLE`/`FELLIPSE`,
     `PUTGC`/`GCSET`, `DRAW`'s direction-code mini-language, `GET`/`PUT`
     blocks, `PATTERN`, `LOGIC`, `FONT`, and the whole `OWSET`/`OWEND`
     overlay-window family.
   - **The origin question:** is a scale-off coordinate relative to the
     window or the screen? Both test windows sat at 0,0 where the two
     coincide. Needs a window at a non-zero position.
   - **GFX (Level 1)** is entirely untested, including its claim that the
     origin is **lower-left** — the opposite of what GFX2/windint do.

   One caution learned the hard way: if `nitros9repl.sh send` replays stale
   output its `nc` client has died and nothing is reaching the guest —
   verify with `tmux capture-pane` before concluding a *guest-side* failure.

   **2026-07-19 — visual confirmation pass, most of the "untested
   primitives" list above now `Live`.** `DRAW`'s polyline, `GET`/`PUT`,
   `LOGIC`'s raster op (with a nuance: erase-by-redraw doesn't cleanly
   cancel for filled shapes — `FCIRCLE`'s fill isn't pixel-identical
   between calls), `PATTERN`, and `FONT` (confirmed a real, silently-
   unenforced prerequisite: an unmerged font buffer renders garbled
   glyphs, no error) all confirmed with screenshots.
   `CWAREA` resolved: it takes character-grid units like `OWSET`/`CURXY`;
   the earlier "black band" was a wrong-byte-width guess in a hand-driven
   raw escape, and driving it through the validated `RUN GFX2(...)` call
   path instead worked cleanly and matched the documented rescale exactly.
   `OWSET` confirmed as documented (char-grid coordinates, erases its area
   immediately). **New finding, not previously suspected: `OWEND` does not
   visibly restore saved content**, reproduced on two window geometries
   with a `save_switch=0` control ruling out a single-geometry fluke —
   `windint` source isn't in this repo to settle it the way `LINE`/`LINEM`
   was settled, so it's recorded as a live black-box finding, not an
   `os9exec` bug. Level-1 `GFX`'s `MODE` call is accepted but never
   produced a screen reachable via CLEAR-cycling across three different
   output-routing attempts, so its lower-left-origin claim stays `Manual`
   — an environment limitation, not new evidence either way; almost
   certainly the same "screen with no live process isn't reachable" gap
   noted above. `ARC`, `FFILL`/`Fill`, `FCIRCLE`/`FELLIPSE` were already
   confirmed `Live` in the 2026-07-18 pass (see above), so the only items
   left open from this backlog entry are: the normalized-vs-scaled
   coordinate question, `OWEND`'s restore, and everything gated on
   reaching a `wcreate`d window with no live process (Level-1 `GFX`'s
   screen included). Full detail:
   `test/6809-live-verification/dogfood-gfx-pixels-2026-07-18.md`;
   `gfx-windowing.md` updated directly throughout.
3. **DONE 2026-07-17 — privileged-call registers added to
   `6809/syscalls-and-module-format.md`.** This item's own framing was
   stale: the user-mode `F$` and `I$` tables already had full register
   in/out before this pass (an undocumented holdover from an earlier
   density rewrite) — the real gap was narrower, just the
   privileged/kernel-internal `F$` calls ($28-$52). Closed by
   card-extracting the System Programmer's Manual's Chapters 11.2 (11
   universal privileged calls) and 12.1 (34 Level-2/DAT calls), both of
   which give full INPUT/OUTPUT register listings — richer than the Rev
   F1 errata's condensed Appendix E. Codes were **not** re-derived from
   these chapters (real OCR collisions found there, e.g. `F$AllPrc`/
   `F$FModul` both reading `$4B`) — the table's own pre-existing,
   two-source-cross-confirmed Code column was trusted throughout. One
   incidental fix: `F$GModDr`'s user-mode row was missing two input
   registers (`Y`/`U`) that Chapter 12.1 documents. **Follow-up
   gap-closing pass, same day:** `F$LDAXYP`/`F$DATTmp` turned out to
   already be in the Rev F1 Appendix E — the original search's regex
   silently skipped entries with leading whitespace, a real search bug,
   not a real gap. `F$SSvc`/`F$GCMDir` and the whole mixed range
   (`F$Alarm`/`F$NMLink`/`F$NMLoad`/`F$VIRQ`) resolved from the OS-9
   Technical Reference (Tandy), a source neither this item's original
   pass nor its own gap-closing search had checked; `F$GCMDir` also
   picked up a second independent source for its code in the process.
   **Still open:** codes `$1F`/`$20`/`$23`-`$26` — a corpus-wide search
   found zero hits anywhere. Card trail:
   `docs/superpowers/plans/2026-07-17-6809-syscall-registers/cards/`
   (os9exec repo). **Second follow-up, same day — full source cross-check
   against NitrOS-9:** all ~93 calls in the table checked against real
   kernel code (see `6809/STATUS.md` for the full findings list). Biggest
   catch: `I$Write`/`I$ReadLn` had swapped codes, settled against
   `defs/os9.d`'s authoritative sequential definitions. Also caught and
   disproved a false-alarm "dispatch bug" report — worth internalizing as
   a general rule for this kind of work: Haiku's CONFIRMS verdicts proved
   reliable across ~80 calls, but its DISAGREES verdicts needed
   independent verification every time one came up, and one of them
   (`I$SetStt`) was simply wrong.
4. **DONE 2026-07-17 — Level 1 vs Level 2 user-visible differences.**
   Added to `utility-usage.md`: windowing (`wcreate`/`wmode`/`montype`/
   `tuneport`/`GFX2`) is Level-2-only — Level 1 has one physical screen
   and no windowing subsystem at all; per-program memory limits are
   similar in practice (~56-60K both levels) but differ in mechanism
   (cross-referenced to `os9-systems-dev`'s `6809-level2-mmu.md`); the
   manual's own explicit warning that Level 1 and Level 2 commands aren't
   interchangeable. The `#n`/`#nK` memory modifier turned out **not** to
   diverge by level — confirmed against the Level 2 manual's own worked
   example, closing that open question rather than finding a real
   difference. Incidental find while sourcing this: `gfx-windowing.md`'s
   `DWSET` format-code table was missing two special values (`$00`/`$FF`)
   from the same source table already used for the standard codes — added.
   Shingle-scanned clean.
5. **DONE 2026-07-17 — scope decisions recorded for the three unmined
   documents.** **O-FLEX** (`O-FLEX_Operating_System_for_OS-9_Level_II_
   Gimix.txt`, 35K): **out of scope** — a Gimix-specific OS variant, niche
   even within the already-niche Gimix hardware line this project
   otherwise covers lightly. **Hi-Res Screen Dump Utilities**
   (`OS-9_Hi-Res_Screen_Dump_Utilities_Tandy.txt`, 21K): **out of scope**
   — a narrow printer-dump utility, not core OS-9 API surface; small
   enough to reconsider cheaply later if it ever becomes relevant.
   **OS-9 Pascal Reference Manual** (431K): **out of scope, reversed
   2026-07-17.** Briefly queued as a new item 6 after an initial "in
   scope" call, then reconsidered and removed the same session before
   the numbering below was finalized — the item 6 that appears further
   down this list is unrelated (the full-corpus unmined-document sweep),
   not a renumbered survivor of this Pascal item. Reconsidered the same
   session: checking whether the actual compiler was obtainable led to finding
   real disk images on `colorcomputerarchive.com` (the same archive this
   project's manuals already come from) — but pulling down and running
   1984 Microware proprietary binaries is a materially different act
   than mining a manual for facts, and the owner decided against going
   there. Same reasoning extends to other niche/less-common OS-9
   languages noted in passing (CIS COBOL, a Lisp) — not queued, not
   pursued. Documentation-only mining of a manual (no live-testing claim,
   no possession of the software) would still be low-risk if ever
   revisited, same as O-FLEX/Hi-Res above, but isn't being pursued right
   now either — the priority is consolidating what's already built
   (items 1-4) rather than expanding into new languages.
6. **DONE 2026-07-17 — full unmined-document sweep of both `txtResources/`
   trees, cross-referenced against `SOURCES.md`.** Findings:
   - **`6809/OS-9_Assembler_Editor_Debugger_Manual_Dragon.txt` was
     believed already fully mined — turned out to be wrong, corrected
     same day.** This note originally said its Editor section (navigation,
     macro system, file/shell integration) and Debugger command table were
     both present in `6809/assembly-and-tools.md` and left it at that
     (plus a `SOURCES.md` citation-completeness fix). What it missed:
     **Chapter 2, "Assembler" (asm/MIA's own chapter, roughly lines
     1421-2670 of the file — the range between "Chapter 2. Assembler" and
     "Chapter 3. Interactive Debugger"), was never actually mined**,
     despite `assembly-and-tools.md`'s directive table already containing
     `asm`-attributed rows. **DONE, same day**: Chapter 2 mined and merged
     into `assembly-and-tools.md` — see the entry below for what it
     resolved and added.
   - **DONE 2026-07-17 — `6809/OS-9_Relocating_Macro_Assembler_Manual.txt`
     fully mined into `assembly-and-tools.md`.** Added: full RMA
     command-line/OPT option set (ch. 1.4/4.7), input-file and
     listing-format facts (ch. 1.5/1.6), RMA's own expression-evaluation
     rules (ch. 1.7, kept distinct from the debugger's separate calculator
     syntax), the RMA macro facility (ch. 2 — arguments, `\Ln`/`\#`,
     `\@` auto-labels, explicitly distinguished from the Editor's
     unrelated `.MAC` system), full PSECT/VSECT/CSECT operand semantics
     (ch. 3), directive-table corrections/tags for MOD/EMOD/SETDP/ORG as
     `asm`/MIA-only (per Appendix A, RMA has none of these), data-area
     register conventions for both the no-initialized-data and
     `Root.a`-initialized-data cases (ch. 6), full RLINK command-line
     options (ch. 7.2), and the "Differences Between RMA and the
     Microware Interactive Assembler" appendix (Appendix A). The
     label-length discrepancy resolved as a **plain correction, not an
     asm-vs-rma divergence**: the RMA manual states 1-9 characters,
     case-sensitive (no case-folding); the file's old "1-8" sentence
     already used `PSECT`-scoping language in the same breath, confirming
     it was describing RMA all along, so it's now fixed to 1-9 with the
     manual cited directly. Mining also surfaced two more RMA-mis­attribution
     errors in the same pre-existing content, flagged rather than silently
     deleted pending `asm`'s own manual: an OPT-directive table row
     claiming `M`=Motorola-compatible-mode and `O`=object-file, and a
     "two assembler modes" paragraph, neither of which appears anywhere
     in the RMA manual's real option set (`l c f g x e s d w`).
     **RESOLVED 2026-07-17, both confirmed as real `asm`/MIA facts, not
     fabrications**: `asm`'s own manual chapter (ch. 2.8.8 OPT statement,
     ch. 2.4 Operational Modes) was mined the same day. `M`=turn on
     Motorola-compatible mode and `O[=filename]`=generate object code file
     are both genuine, verbatim-confirmed `asm` OPT letters — the original
     table row was correct all along, just unconfirmed pending a primary
     source. The "two assembler modes" paragraph is also confirmed
     accurate for `asm`: normal (OS-9-featured, separate program/data
     counters) vs. Motorola-compatible (single counter, no OS-9 features),
     toggled via the `M` option on the command line or in an `OPT`
     statement, `-M` returns to normal. Both facts are now correctly
     attributed to `asm`/MIA (ch. 2.4/2.8.8) in `assembly-and-tools.md`,
     not RMA. Appendix B (error messages) was not
     dumped as a table per this project's judgment call; a few genuinely
     useful numeric limits from it (macro nesting depth 8, max 9 macro
     args, ~13 nested `USE` levels, max 32 input files) were folded inline
     instead. Appendix C's worked examples were not transcribed, per
     standing policy. Shingle-scanned against the source manual: clean.
   - **Two `Gimix_OS-9_*`-named files are not Gimix content at all** —
     see the note now in `SOURCES.md` (duplicate/misOCR of manuals
     already cited). No scope decision needed; nothing to mine.
   - **`68k/Enhanced_OS-9_68K_MVME_Guide.txt` and
     `68k/Enhanced_OS-9_68K_Release_Notes.txt`: out of scope.** These
     document "Enhanced OS-9 for 68K" v1.1 (2000) / OS-9 v3.2 — a later
     major version than the v2.4-era this project's skills and `os9exec`
     target, plus MVME-VME-bus-board-specific installation detail. Real
     risk of contaminating v2.4 documentation with v3.2 facts if mined
     carelessly. Reconsider only if the project ever targets 3.2-era
     semantics specifically.
   - **`68k/OS9_68000_V2.4_System_Requirements.txt`: out of scope.**
     Peripheral Technology PT68K2/PT68K4 board-specific EPROM
     installation and boot-menu instructions — vendor hardware install
     detail, not general OS-9/68k API/kernel content, same category as
     the already-excluded O-FLEX/Hi-Res docs.
   - **`68k/OS-9_Processors_Hardware_Support.txt`: out of scope.** A 2006
     RadiSys marketing data sheet (supported-CPU-family list); no
     technical/API content at all.
   - **`6809/OS-9_6809_Level1_Y2K_Updates.dsk`**: binary disk image, not
     text — not applicable to manual-mining either way.
   - **`../os9/txtResources/6809/OS-9_6809_Level1_Source.tar.gz`**: real
     Microware source code. Owner decision 2026-07-17: same rule as
     `kernel-source-VERIFICATION-ONLY-do-not-extract/` — cross-check-only,
     never a primary source, never extracted at length. See `SOURCES.md`.

## Dogfood test (2026-07-18) and fixes it produced

First cold dogfood pass on `os9-dev`: a fresh agent wrote, entered, and
live-ran a real BASIC09 program (file create/write/reopen/read with
line/char counting) using only the skill, no session context. Full
report: `test/6809-live-verification/dogfood-report-2026-07-18.md` (in
the `os9exec-git_code` repo), working program alongside it. Language-level
guidance held up completely (zero `Error #NNN` at any point); found real,
narrow REPL-harness/documentation gaps, all fixed:
- `6809/using-nitros9-repl.md`'s sub-prompt gotcha named only `debug`'s
  `DB:` and `help`'s `Topic:` — added BASIC09's own `e`/`E:` editor as a
  third case and reframed as a general pattern, not a fixed list.
- Same file's "Loading a BASIC09 program" section presented `tee`+`LOAD`
  as the only route in — added the interactive-editor alternative
  (already documented on the 68k side, confirmed to work identically on
  6809), which is less work for a short program.
- New fact, not documented anywhere before: a literal `;` inside a
  `PRINT` string constant gets a spurious backslash escape in both
  `LIST` and runtime output — added to `basic09/gotchas.md`, `Live`
  (6809), not tested on 68k.
- The "long CPU-bound computation" delayed-output gotcha's trigger
  condition may be broader than stated — this run hit the same symptom
  after just several rapid `key` calls, no long computation. Flagged in
  place (`Manual, Flag`) rather than rewritten, since it's one data point
  against the original's own `Live` finding.

## 68k debugger dogfood test (2026-07-18)

Eighth dogfood pass: a deliberate, non-obvious 68k logic bug (zero-extend
instead of sign-extend on a negative byte, one stat right/one wrong so
it wasn't obviously broken) found live via `debug` — breakpoints, `g`/`gs`
stepping, register inspection — not by reading source. Full report:
`test/68k-live-verification/dogfood-report-debugger-2026-07-18.md`.
Resolved the one open item this pass touched: `os9-68k-assembly.md`'s
disclosed-unverified "trailing colon = public" symbol-visibility
convention — `Live`-confirmed via `l68 -s` and `sc`, now struck through
and resolved in the skill rather than left as an open gap.

## BASIC09-calls-68k-assembly dogfood test (2026-07-18)

Seventh dogfood pass: a multi-parameter, mixed by-reference/by-value 68k
assembly subroutine (`addmulmod`, `sum=a+b, prod=a*b`) called from
BASIC09, going beyond `basic09-vs-68k-differences.md`'s only prior
worked example (`addone`, a single by-reference param). Clean pass,
first-try, zero errors — confirmed the documented stack layout
(`8(a7)`/`16(a7)`/`24(a7)` for params after the first) with real,
verified offsets. Added as a second worked example in the skill,
directly next to `addone`, closing the gap the test flagged (the
multi-parameter layout was prose-only before, nothing to check
hand-derived offsets against).

## RBF lost-update design-intent dogfood test (2026-07-18) — case 1 confirmed working

Seventh dogfood pass, companion to the EOF-lock one below: testing the
*other* half of `file-managers.md`'s Record Locking design-intent
explanation (firsthand from the project owner — same source as the
EOF-lock case) — case 1, a database-style read-modify-write cycle safe
under concurrent access with zero explicit `SS_Lock` calls, because
`Read` in update mode locks the record just read and the following
`Write` releases it. Full report:
`test/68k-live-verification/dogfood-report-lostupdate-2026-07-18.md`.

**Result: confirmed working as designed on `os9exec`/68k, not divergent.**
Two processes raced 300 unprotected read-modify-write iterations each
against a shared counter on a real RBF disk image; final count landed
exactly on 2×300=600 in two independent full races — no lost updates,
matching case 1 exactly. Unlike the sibling EOF-lock pass (case 2, below),
this one didn't turn up a locking bug — a meaningful result given this
project's RBF implementation has already been shown to have a real
locking bug in the *other* case, so a clean result here wasn't a
foregone conclusion. `file-managers.md`'s Record Locking section updated
with the `Live` confirmation.

**RESOLVED, but the other direction — 2026-07-19, NitrOS-9 (6809) does
NOT reproduce this clean result.** Identical test ported to real RBF on
the 6809 EOU disk under NitrOS-9: two independent races landed at 457 and
584 (expected 600 both times) — real, reproducible lost updates, with
direct evidence of genuine interleaving and with an unhandled-I/O-error
mechanism ruled out (no `ON ERROR GOTO` set, no crash into Debug Mode, so
contention isn't erroring — it's genuinely not being prevented). **This
is a finding about NitrOS-9's own reimplementation, not about "6809" as
an architecture or genuine Microware OS-9** — NitrOS-9 is a community
clone, not licensed Microware source, exactly like `os9exec` is an
independent 68k reimplementation; both are being measured against the
same firsthand design intent and each has now shown its own gap (this
one for NitrOS-9, the EOF-lock case below for `os9exec`). **Case 1 is now
confirmed `Live` on `os9exec`/68k only; do not assume it holds on
6809.** Full report:
`test/6809-live-verification/dogfood-report-lostupdate-6809-2026-07-19.md`.

**DONE, same day — the follow-up decisive lock-contention test, and it
changes the picture.** Root mechanism resolved, at least in outline: a
holder process `GET`s a record and deliberately holds it (real
wall-clock delay) before `PUT`ing; a concurrent waiter's `GET` on the
same record did not return until after the holder's release, and read
back the released value, never the stale one — in both of two
independent runs. **NitrOS-9's record lock is real and does block; the
lost-update gap is a narrower, timing-dependent race in rapid
release-then-reacquire cycles, not an absent lock.** This is a more
specific, more useful characterization than "record locking doesn't
work on NitrOS-9" — don't collapse it back to that. Suggested next step,
not done: a lost-update racer with a tiny deliberate delay between `PUT`
and the next iteration's `GET`, to see whether losses drop with room for
the reacquisition race to close. Full report:
`test/6809-live-verification/dogfood-report-lockcontention-6809-2026-07-19.md`.

**Real blocker hit and worked around, unrelated to the locking question
itself**: on a fresh boot, BASIC09 crashes with `**** Can't install trap
handler ****` (E_PNNF) on its first real numeric operation because the
account's own `/h0/startup` line `load -s cio csl math` silently fails
to make `cio`/`math` resident (`mdir` shows only `csl` after boot) —
while a plain `load math` (no `-s`) from the shell works immediately.
The overall trap-handler-missing mechanism was already documented in
`basic09/pack-and-runb.md`; the new, not-yet-root-caused piece is that
`-s` itself silently fails on this build. Added to that file as a
refinement of triage item 1. **Not chased into `os9exec`'s source** —
open for whoever picks up `os9exec`-side shell/module-loading work next;
worth checking whether `load`'s `-s` handling is an `os9exec`-internal
command or delegates to a real Microware `load` binary before assuming
which side the bug is on.

## RBF EOF-lock design-intent dogfood test (2026-07-18) — real os9exec bug found

Sixth dogfood pass, testing whether `os9exec`'s RBF honors the EOF lock's
original design intent (firsthand from the project owner, who designed
the original Microware mechanism — see project memory
`user-designed-rbf-eof-lock`): a slow writer/slow reader pair should
coordinate through a growing file like a pipe. Full report:
`test/68k-live-verification/dogfood-report-eoflock-2026-07-18.md`.

**Result: neither hypothesis the test was designed to distinguish — a
third, more severe outcome. A reader path opened while a writer path is
concurrently open on the same file sees zero bytes of that file's data
for its entire remaining lifetime, even long after the writer closes.**
Reproduced cleanly, multiple runs, both READ-only and UPDATE mode
identically, immediate/non-blocking `E$EOF` on every retry, data
confirmed intact via a fresh post-close `OPEN`. This is now documented in
`file-managers.md`'s Record Locking section as a `Live`-confirmed,
likely-real `os9exec` RBF bug — **not fixed as part of this pass**,
flagged for `os9exec`-side follow-up (whether by this session or the
sibling one doing emulator-core work).

Also fixed from this pass's harness-friction findings: two concurrent
background processes need a single combined launch command, not two
separate `key` sends (unreliable, risk of accidental duplicate
processes); an unthrottled retry-poll loop can starve a concurrent
process of CPU, not just spam output. Both added to
`common/using-os9exec-repl.md`.

## RBF EOF-lock design-intent dogfood test, NitrOS-9 (6809) (2026-07-18) — os9exec bug NOT reproduced; NitrOS-9's mechanism blocks, doesn't poll

Follow-up to the 68k pass above, this time against **NitrOS-9 on 6809**
(XRoar + DriveWire, `tools/nitros9repl.sh`) rather than `os9exec` — the
question: does NitrOS-9's own RBF honor the pipe-like design intent that
`os9exec`'s reimplementation apparently doesn't? (NitrOS-9 is a
community-written clone of OS-9 Level 2, not licensed Microware source —
this test compares two independent reimplementations against the same
firsthand design intent, it does not have access to the original
Microware-authored code to compare against directly.) Full report:
`test/6809-live-verification/dogfood-report-eoflock-6809-2026-07-18.md`.

**Result: `os9exec`'s specific bug does NOT reproduce in NitrOS-9's RBF —
a concurrently-opened reader path eventually sees every byte the writer
wrote, correctly, every time (two clean runs).** But NitrOS-9's own
mechanism also isn't a clean match for the pipe-like ideal either: the
reader's first `READ` call didn't return for ~12 real seconds (well past
when the record it was reading had already been flushed), with
`retries=0` throughout — no `E$EOF` was ever returned to retry. This is
genuine kernel-level **blocking**, not `os9exec`'s immediate-return
polling, and it released all 13 buffered records at once, timestamped to
the same real second the writer closed. Reads best as **"blocked for the
writer's entire remaining lifetime, then released at once when the
writer's path closes"** — closer to the "locked out until the writer
exits" fallback than to "unblocks promptly on each write," but unlike
`os9exec`, it does eventually deliver everything correctly. **This shows
`os9exec`'s permanent-lockout behavior is specific to `os9exec`'s own
reimplementation, not something forced by the EOF-lock design itself —
but it does NOT show NitrOS-9 implements the mechanism correctly/as
originally designed, only that it doesn't share this particular bug.**
(The lost-update pass on 2026-07-19, added later, found the reverse
asymmetry — NitrOS-9 has its own real gap in the *other* Record Locking
case that `os9exec` doesn't — so neither reimplementation should be
treated as the correct reference for the other.) `file-managers.md`'s
Record Locking section updated with a `Live` NitrOS-9 note to this
effect.

Also fixed from this pass: a real bug in `tools/nitros9repl.sh` itself —
`tmux_escape()` was inserting a literal backslash before every `;` typed
via `key`/`send` (mistaken belief that tmux needed it escaped even
inside an already-quoted bash argv element; live-verified via a
throwaway tmux session that it doesn't). This corrupted any BASIC09
`PRINT` statement using `;` as a separator — i.e., most of them. Fixed
to a no-op; independent of the eoflock finding, benefits every future
session using this REPL. Also newly documented: the OS-9 shell's own
prompt can get visually "buried" under two backgrounded jobs' streamed
output, making the next `send` time out even though the shell is
genuinely idle — a plain `key Enter` recovers it; and `BYE`
(capitalized) is the correct command to leave interactive `basic09`
(lowercase `quit`/`bye` silently fail with `What?`, invisible via `send`
since `B:` doesn't match its prompt-gate regex either way).

## RBF EOF-lock large-file follow-up, NitrOS-9 (6809) (2026-07-18) — small-file "blocks until close" conclusion revised

Direct follow-up to the 6809 pass above, answering the question it
explicitly left open: was the ~12-second full block tied to the writer's
**close** specifically, or was the previous file (13 tiny records, well
under one 256-byte RBF sector) simply too small to ever show a
finer-grained release? Full report:
`test/6809-live-verification/dogfood-report-eoflock-6809-largefile-2026-07-18.md`.

**Result: the small file's "blocked for the writer's whole lifetime, one
shot at close" behavior does NOT hold for a larger file — a reader sees
most already-flushed data live, well before close.** Design: writer
bulk-writes 50 fixed-80-content-byte records (4050 bytes on disk counting
BASIC09 sequential `WRITE`'s trailing-CR delimiter, ~15.8 RBF sectors) as
fast as BASIC09/RBF execute them (no real-time per-record pacing), then
deliberately holds the path open-but-idle for a real ~10-second pause
before closing. Reproduced identically across two clean runs: the reader
read records 1-46 of 50 **live and incrementally**, entirely during the
writer's idle hold window — well before its close — then blocked on the
last 4 records (47-50) until the writer's CLOSE, with `retries=0`
throughout (still a genuine kernel block, not `os9exec`-style polling).
Reframes the previous pass's finding: the reader isn't blocked for the
writer's *entire* lifetime — it's blocked only once it catches up to the
true current end of file, correctly stalling at that live edge (much
closer to the pipe-like design intent than the small-file run alone
suggested). The small file never gave the reader room to get ahead of the
writer's in-progress tail, so every read landed on that same trailing edge,
making the whole run look like a single close-gated block. `os9-systems-dev`'s
`file-managers.md` Record Locking section updated with a `Live` note
sharpening this. Exact release granularity (RBF sector boundary vs. some
other buffer threshold, e.g. in BASIC09's own I/O layer) not resolved
further — flagged for whoever looks at the real buffering code next.

Also fixed from this pass, both real and independent of the eoflock
question: (1) a writer-startup-order race — an early draft built a
one-time 60-iteration pad-string via string concatenation *before*
`CREATE`, giving a concurrently-launched reader's `OPEN` a real chance to
run first and fail with `Error #216` on the not-yet-existent data file;
fixed by moving `CREATE` to the very first executable statement. Even
after that fix the launch-order race isn't fully eliminated (a coin flip
between two freshly-forked processes), so the reader also gained a
defensive OPEN-retry wrapper (~40 short-throttled attempts) — unrelated to
the actual READ-blocking behavior under test. (2) **A genuine BASIC09
compiler gotcha, not previously documented anywhere in either skill**:
`LOAD` auto-sorts numbered lines by their numeric value for final
fall-through/execution order, independent of the physical/typed order in
the source file — classic line-numbered-BASIC behavior that structured
BASIC09 still carries silently, with no compile error when it bites.
Typing retry-loop labels out of numeric order relative to an existing
100/800/900 block silently resequenced execution. Worth folding into
`os9-dev`'s BASIC09 language reference if a second independent case turns
up.

## IPC/pipes dogfood test (2026-07-18)

Fifth dogfood pass, first multi-process one: real producer/consumer pairs
and solo-reader/solo-writer edge cases on OS-9/68k named and unnamed
pipes, via `os9exec`. Full report:
`test/68k-live-verification/dogfood-report-pipes-2026-07-18.md`. The
qualitative model in `common/ipc.md` held up completely (bounded buffer,
blocks-not-errors when full, EOF = empty-and-no-writers, named-vs-unnamed
deadlock-detection split) — but two real gaps and one genuine operational
hazard got fixed:
- **90-byte buffer figure**: qualitative claim `Live`-confirmed, specific
  number not — a lone writer with zero readers ever accepted ~45x that
  before blocking. Most likely BASIC09's `WRITE` batching multiple
  logical writes into fewer real `I$Write` calls (unconfirmed — would
  need syscall tracing to settle). Flagged in place, not overwritten with
  an unverified new number.
- **`OPEN` vs `CREATE` on a not-yet-existing named pipe**: `OPEN` crashes
  the process outright (`E_PNNF`), `CREATE` is what actually works —
  wasn't stated either way before. Added.
- **Real hazard, most actionable finding**: Ctrl-C/Ctrl-E, sent multiple
  times, had zero effect on a process wedged mid-`WRITE` on a full named
  pipe — contradicting `using-os9exec-repl.md`'s "acts immediately
  regardless of what the process is doing" claim for exactly this case.
  Only a full harness `restart` recovered it. Flagged prominently (not
  just noted) since a future session deliberately testing pipe deadlock
  behavior — as this one did, on the user's own request — will hit the
  same wedge expecting Ctrl-E to work.
- Also fixed: `chx` pointed at a personal directory breaks plain
  interactive command lookup, not just compiler sub-tool forking as the
  existing text implied.

**Left genuinely untested, not confirmed or contradicted**: the unnamed-pipe
deadlock-*detection* claim itself (`E_WRITE` to the first blocked writer
when every process with access is simultaneously write-blocked) — needs a
real cyclic multi-process setup this pass didn't have budget to build
safely after the solo-writer recovery cost. Worth a dedicated follow-up.

## 68k assembly dogfood test (2026-07-18)

Fourth cold dogfood pass, companion to the 68k C one above: a fresh agent
hand-wrote real 68k assembly (raw `I$` syscalls via `TRAP #0`, `r68`/`l68`,
no C or BASIC09) for the same file-I/O counting task. Full report:
`test/68k-live-verification/dogfood-report-asm-2026-07-18.md`, working
program alongside it. Rockier than every prior dogfood pass — ~13
assemble/link/run cycles, because `os9-68k-assembly.md` had *disclosed*
(not confidently-wrong) gaps in exactly the two things this task needed:
`psect` directive syntax and I$/F$ numeric call codes. Fixed:
- **Cross-reference gap, the pass's top finding**: a complete, already
  `Live`-tested `psect` example exists in
  `basic09/basic09-vs-68k-differences.md` (the "calling 68k from BASIC09"
  section) but neither `os9-68k-assembly.md`'s "Known gaps" nor its
  "Cross-references" section pointed there — found only by grepping the
  whole skill tree. Added both pointers; also recorded that the 6-operand
  shape works unchanged for a `Prgrm`-type module, not just the `Sbrtn`
  it was originally demonstrated with.
- **New toolchain fact**: no file on this SDK's disk defines I$/F$ call
  names as assemblable symbols (`r68` accepts `dc.w I$Write` silently,
  `l68` then fails `Symbol 'I$Write' unresolved`) — `syscall-reference.md`
  presented call names as if directly usable. Added the fact plus
  confirmed numeric values (sourced from this project's own
  `os9funcs.h`, not proprietary material).
- **Register-table refinement**: `A5` at program entry is a
  NUL-terminated string of the typed command tail (zero-args case starts
  with a bare CR, not a NUL — a first implementation that checked only
  for NUL got this wrong at runtime, no assemble/link-time warning).
  Added, plus an explicit warning against using `D5` ("param-area size")
  to bound a raw read of it — exact `D5` semantics still unpinned.
- **REPL harness gotcha**: a program's own bare-CR output (no LF) can
  desync gated `send` the same way a sub-prompt does — added to
  `common/using-os9exec-repl.md` alongside the existing sub-prompt note,
  same fix (`key Enter`, then resend).

No `os9exec` bugs found this pass. One pure-68k-ISA error hit along the
way (`SUBQ`/`ADDQ` only accept immediate 1-8, not general values) is
correctly out of the skill's disclosed scope, not a gap.

## 68k C dogfood test (2026-07-18)

Third cold dogfood pass, first on 68k: a fresh agent wrote real 68k C
(file I/O counting task, mirroring both 6809 passes above), specifically
to stress-test `c/os9-c-cheatsheet.md`'s toolchain-order table (corrected
yesterday after a redundancy pass caught it showing 6809 tool names in a
68k-labeled file) and `c/os9-clib-reference.md`'s File I/O table. Full
report: `test/68k-live-verification/dogfood-report-c-2026-07-18.md`,
working program alongside it.

**Toolchain-table fix confirmed correct**: `cpp`→`c68`→`o68`→`r68`→`l68`,
exactly as documented, on the first clean compile — no 6809 tool names
needed. Two real gaps found and fixed in `c/os9-clib-reference.md`:
- `_pfltinit()`/`_prfloat()` printf-marker claim was **flatly wrong for
  68k**, not just unverified — calling `_pfltinit()` before a `%ld` fails
  to *link* (`Symbol '_pfltinit' unresolved`), the opposite of the
  documented "silent no-op" behavior. Corrected in place, `Flag`, with
  6809 explicitly left unverified rather than assumed to share the bug.
- `stdlib.h` isn't on Ultra C's default include path (only under gcc2's
  `DEFS/os9lib`/`DEFS/GCC2`) — wasn't stated either way before; added.

**Real `os9exec` bug found, NOT fixed here (out of scope for a skills
pass, flagged for whoever picks up emulator-side work)**: running a
freshly compiled program by bare name (already a documented failure mode
— "run by full path" is the correct workaround) produces
`shell: can't execute "J" - Error #000:216`, always reporting the literal
name `"J"` instead of the real command name, reproduced 3 ways (bare
name, no args, a renamed copy). A genuinely-nonexistent command reports
its own name correctly in the same error format, so this looks like a
narrow rendering bug specific to the bare-name/`PATH`-lookup failure
path, not the "doesn't exist at all" path. The documented full-path
workaround sidesteps it fine; this is about the error *message* being
wrong, not the failure itself.

## 6809 assembly dogfood test (2026-07-18)

Second cold dogfood pass on `os9-dev`, companion to the BASIC09 one above:
a fresh agent hand-wrote real 6809 assembly (raw `I$` syscalls, no
BASIC09) for the same file-I/O counting task, using only the skill. Full
report: `test/6809-live-verification/dogfood-report-asm-2026-07-18.md`,
working program alongside it. Took 3 real assemble/run cycles; found two
bugs only visible via live debugging (one in the skill, one in the
agent's own code — clearly distinguished in the report). Fixed in the
skill:
- `MOD`'s `size` operand needs the end-label `+3` (EMOD's CRC trailer) —
  wasn't stated as a rule anywhere, cost a bad-CRC/`Error #235` cycle.
- Short branches out of ~127-byte range are a hard assemble-time error,
  not just a listing warning — the existing `LBxx`-unneeded warning note
  didn't state the reverse case.
- `I$ReadLn`'s returned length includes the CR terminator, diverging from
  BASIC09's own `READ`/`LEN()` (confirmed in the same-day BASIC09 dogfood
  test) — real off-by-one risk porting a count between the two levels.
- Debugger: `E` shares `L`'s "must already be resident" limitation
  (`Error #221`); a module linked multiple times needs one `unlink` per
  link, not one total (confirmed 4 links → 4 unlinks needed). `B`/`G`/`M`/`E`
  upgraded from `Manual` to `Live` in `assembly-and-tools.md` — only `S`
  remains unexercised.
- **New `Flag`, not resolved**: the command-line parameter area's byte
  layout at entry `X` differs between a real shell fork and the
  debugger's `E <name> <params>` (leading space + trailing CR present
  only via `E`) — flagged in place in `syscalls-and-module-format.md`
  with a concrete next step (probe via real shell invocation only,
  varying argument length, to isolate whether `E` is the outlier) rather
  than guessed at.
- Not a skill gap, noted for completeness: a register-clobbering bug
  (`LDD` inside a loop silently wiping a digit-counter kept in `A`, half
  of `D`) was caught only via debugger register/memory inspection — this
  is 6809-CPU-semantics reasoning, not an OS-9 convention, and no
  documentation could have prevented it. The debugger commands that
  *found* it are exactly what's now upgraded to `Live` above.

## 6809 (secondary priority)

Real gaps found by directly building the assembler/debugger verification
this session (see `6809/STATUS.md` for what *is* now confirmed):

- **The syscall table is the big one.** **DONE 2026-07-19 for the
  originally-recommended batch** — `F$Link`/`F$UnLink`/`F$Fork`/`F$Wait`,
  `I$Open`/`I$Read`/`I$Write`/`I$Close`, `F$Time`, plus `F$Send` (already
  `Live` from the earlier signal test) are now `Live`, tested both
  success and failure paths as a re-runnable regression suite
  (`test/6809-live-verification/syscall-flink-ffork-fwait.a`,
  `syscall-ftime-iread-iwrite.a`; report:
  `dogfood-report-syscalls-2026-07-19.md`). 14 of ~60 documented calls
  are `Live` now, up from 5. Real findings: `F$Time`'s year byte is
  `year-1900`; `I$Write` does return `Y`; `F$Link`/`F$Fork` fail with
  *different* codes (`E$MNF`/221 vs `E$PNNF`/216) against an
  unresolvable name since only one of them consults the filesystem;
  `F$Wait` with no children fails `E$NoChld`/226. **Two real
  register-clobber bugs found in the tests themselves while writing
  them** (a syscall's return register destroyed by a helper call before
  being saved) — see the report for the general lesson, likely to recur
  in any test written this way. **DONE, same day, second batch**:
  `I$Create`, `I$MakDir`, `I$ChgDir`, `I$Delete`, `I$Seek`, `I$GetStt`
  (call confirmed; SS.SIZ's return-value convention is not — see
  `syscalls-and-module-format.md`), `F$Mem`, `F$Sleep`, `F$SPrior`,
  `F$CRC` — all `Live`. `I$Seek` confirms the `Source`-flagged X:U
  position convention live. A *third* register-clobber bug found writing
  these (this time `I$Seek`'s own calling convention destroying the test
  program's `U`-relative data-area base pointer) — see
  `dogfood-report-syscalls-batch2-2026-07-19.md` for the pattern, now
  hit three times across this test suite. `I$SetStt` itself (as opposed
  to `I$GetStt`) remains untested. 24 of ~60 documented calls are `Live`
  now, up from 5 at the start of the day. **DONE, same day, third batch**:
  `F$PrsNam`, `F$CmpNam` (dispatches but result diverges from the
  documented "carry clear if match" — flagged inconclusive, not
  chased), `F$PErr` (confirmed, writes a fuller message than
  documented), `F$SchBit` (dispatches but the returned D/Y don't look
  plausible — inconclusive), `F$AllBit`, `F$DelBit`, `F$GPrDsc`,
  `F$GBlkMp` (same inconclusive-value pattern as `F$SchBit`, including a
  suspiciously identical D value across the two unrelated calls — worth a
  closer look), `F$GModDr`, `F$GProcP` (genuinely **FAILS live**,
  `err=00208`, uninvestigated) — see
  `dogfood-report-syscalls-batch3-2026-07-19.md`. Three more real
  register-clobber/addressing bugs found writing these tests (now five
  total across this suite), plus a harness-level finding: `asm` requires
  an explicit `-O=<name>` to actually write a `CMDS` module — a bare
  `asm file.a` with no `O` flag reports `0 errors` and byte counts but
  persists nothing (already correctly documented in
  `assembly-and-tools.md`'s `O[=filename]` row, just easy to miss).
  `I$Dup`/`I$WritLn`/`I$DeletX` (`batch3-04.a`) hit a real permission
  wall at first (the pre-existing `synctest.dat` fixture is owned by
  someone other than the default boot identity — this disk's password
  file has no `claude` account, only an unnamed UID-0 entry and
  `USER1`-`USER4`, and `nitros9repl.sh start` never logs in as anyone).
  **Fixed properly**: `login USER1` (no password), then had the test
  create its own fresh fixture instead of depending on old-file
  ownership. All three now `Live`. **`login USER1` should be the first
  step of every 6809 test session going forward**, not the
  unauthenticated default. Also found: the `CLAUDE` directory itself
  refuses brand-new file creates (`E$CEF`/218) even with 170,000+ free
  disk sectors and the same create working fine at the disk root —
  plausibly `CLAUDE`'s own directory-extension needs owner permission
  `USER1` lacks; not root-caused, work around it by creating fixtures
  at the disk root instead. 37 of ~60 documented calls are `Live` now.
  **DONE, same day, fourth batch**: `F$Load` (confirmed — path
  resolution is exec-dir-search like `F$Fork`, not data-dir-search like
  `I$Open`), `F$UnLoad` (FAILS unexpectedly, `E$MNF`, right after
  loading the same name — inconclusive), `F$SSWI` (install accepted,
  handler-invocation unconfirmed — the only documented handler-exit
  convention anywhere in this project, `F$Icpt`'s plain `RTI`, may not
  apply here), `F$SRqMem`/`F$Move`/`F$FModul` (all genuinely
  **unimplemented** on this kernel build, `err=00208`=`E$UnkSvc` — same
  code `F$GProcP` hit above, now resolved as a real, repeatable "not
  implemented" signal rather than a mystery), `I$Attach`/`I$Detach`
  (confirmed cleanly against `/N1`, the REPL's own channel device).
  See `dogfood-report-syscalls-batch4-2026-07-19.md`. 45 of ~60
  documented calls are `Live` now.
  **DONE, same day, fifth batch — swept essentially everything
  remaining except explicit kernel-only/hang-risk calls.** Confirmed
  `F$SUser`/`F$CpyMem`/`F$VIRQ`(install+delete)/`F$AllRAM`/`F$DelRam`/
  `F$NMLink`/`F$NMLoad` cleanly working; confirmed `F$VModul`/`F$SLink`/
  `F$BtMem`/`F$AllPrc`/`F$AllImg`/`F$SetImg`/`F$ResTsk`/`F$DATLog`/
  `F$DATTmp`/`F$LDAXY`/`F$LDAXYP`/`F$LDDDXY`/`F$LDABX`/`F$STABX` all
  genuinely **unimplemented** (`err=00208`=`E$UnkSvc`, the same
  now-well-established pattern) — 18 calls confirming the same real
  characteristic of this kernel build rather than 18 separate mysteries.
  **Real exception worth remembering: `F$MapBlk` actually works**,
  unlike its Level-2-flagged siblings. **Real flag, not a doc gap:
  `F$Chain`'s failure path produced a raw, uncontrolled kernel error
  instead of a clean documented failure** — disabled rather than
  chased, left for a supervised follow-up. `F$DelPrc` deliberately
  never attempted (self-PID termination risk). Also still excluded on
  purpose, same reasoning as before: `F$Boot`, `F$AProc`/`F$NProc`,
  `F$GCMDir`, `F$IOQu`, `F$IRQ`, `F$IODel`, `F$SSvc`, `I$SetStt`. See
  `dogfood-report-syscalls-batch5-2026-07-19.md`. 70 of ~93 documented
  calls are `Live` now — essentially done except the calls excluded on
  purpose above and a handful left inconclusive by dependency chains
  (`F$Find64`/`F$Ret64`/`F$ELink`/`F$DelImg`/`F$FreeLB`/`F$FreeHB`/
  `F$AllTsk`/`F$SetTsk`/`F$DelTsk`/`F$RelTsk`).
- **DONE 2026-07-19 — debugger commands beyond `:`.** `B`/`G`/`M`/`E`
  were already `Live` from an earlier session; calculator mode, all four
  Dot-navigation forms, `:reg` get/set, `S` (search), `$` (shell escape),
  and `Q` are now `Live` too, driven interactively against one of the
  syscall regression-test binaries. `K` (clear breakpoints) closed
  2026-07-19 — both forms verified, `K expr` clearing only the named
  breakpoint and bare `K` clearing all, checked by listing with `B`
  between each step. The whole documented command set is now confirmed.
  See `6809/assembly-and-tools.md`'s Debugger section for the
  specific commands and observed output.
- **Attempted 2026-07-19, inconclusive — the Editor section.** The
  on-disk tool's identity doesn't clearly match this section: `ed` on
  this EOU disk is a completely different mouse/GUI graphics-window
  editor, and a second candidate (`edt`, "6EDT Version 2.0") gave an
  ambiguous response to a probe in the documented insert syntax. Left
  `Manual` rather than force a confirmation from an unclear result — see
  `6809/assembly-and-tools.md`'s Editor section for what was tried.
  Next step for whoever picks this up: identify which command is
  actually the vintage line-and-buffer editor this section's source
  describes, if it exists on this disk at all.
- RLINK/PSECT/VSECT multi-file builds remain blocked by the `rma` hang
  (see `6809/STATUS.md` and `using-nitros9-repl.md` for the full
  root-cause trail and next-step suggestions — don't re-run the same
  repro without trying one of the documented next steps first). Separately
  from the live-test block: **DONE 2026-07-17 — the actual
  `OS-9_Relocating_Macro_Assembler_Manual.txt` (the manual for this exact
  tool) is now fully mined into `assembly-and-tools.md`**, reconciled
  against the pre-existing PSECT/VSECT/RLINK content (see the unmined-
  document sweep, item 6 above, for full detail including the
  label-length discrepancy's resolution — a plain correction to 1-9
  chars, not an asm-vs-rma divergence). Mining didn't require a working
  `rma`, as expected — it was a documentation task independent of the
  hang. The live-test block itself is unchanged: RLINK/PSECT/VSECT still
  can't be exercised through this REPL until `rma` itself runs.
- **DONE 2026-07-19 for `L`/`S`, attempted for `G`.** `L S >file` produces
  exactly the documented page-headered listing plus a symbol table using
  the documented type-code letters — confirmed `Live`, no longer "used
  once incidentally." `G` (print every generated byte, not just the
  first) was tested against `L` alone on multi-word `FDB`/multi-byte
  `FCC` directives and showed **no observable difference** — both already
  show every byte via continuation lines regardless of the flag; genuinely
  inconclusive, not confirmed either way. Default page depth (`D66`) is
  visibly real in any multi-page listing even with no `D` flag given.
  **DONE, same day — `D<num>`, `W<num>`, `E`, `N`, `I`, `U`.** `D5`
  produced 42 tiny pages for a 13-line source (page-depth mechanism
  confirmed); `W40` truncates every listing line including `fcc` operand
  strings mid-content; `E` suppresses error messages while still flagging
  the line with an `E` info-field marker and counting it in the summary;
  `N` drops the columnized layout entirely. **`I` is a real bug, not just
  an untested mode**: every line gets an `ASM:` prefix (supports the
  "interactive mode" guess) but the assembled module header comes out
  wrong (`87CD3103` instead of the correct `87CD001D`) while still
  reporting `00000 error(s)` — don't use `I` assembling a file passed as
  a command-line argument. `U` shows no observable effect on the source
  tried, genuinely inconclusive. Only `C`/`F`/`M` (beyond the
  Motorola-mode note above) remain individually untested. Full detail:
  `dogfood-report-syscalls-batch2-2026-07-19.md`.

Lower priority, and likely harder to verify meaningfully through a text
REPL:

- `6809/coco-dragon-hardware.md` (~23KB, essentially untouched) — most of
  it (VDG graphics modes, mouse packets, sound) needs actual visual/audio
  behavior a text channel can't easily observe. Non-visual parts (disk
  descriptor naming conventions, `MONTYPE`/`TUNEPORT` utility behavior)
  might be reachable if anyone wants to try.
- `os9-systems-dev/6809-level2-mmu.md` — DAT/MMU register internals are
  mostly below what an ordinary shell session can observe at all; the
  GMX III boot-ROM material is below what's testable in principle without
  real hardware.

**DONE — cross-architecture-contamination audit pass** (triggered by the
1st-edition-Farna mislabeling discovery): read every file in
`references/` end to end specifically checking whether each concrete
technical claim (register name, syscall code, byte offset, option letter)
is attributed to the correct architecture, as opposed to the
redundancy/consistency pass done earlier the same day. Confirmed both
Farna quick-reference files' actual title pages directly: the 2nd edition
genuinely is CoCo/6809 (title page reads "Tandy Color Computer Level II
... Second Edition"), corroborating the 1st edition's already-known
mislabeling (its own title page reads "Professional OS-9/68000"). Found
and fixed four real contamination cases, all in files that had escaped
the earlier redundancy pass because the wrong-architecture content was
individually true, just unscoped:
- `common/error-codes.md`: the "carry + `d1.w`" return-convention section
  and the entire "000:102–000:158 Processor exception errors" table
  (CHK2/TRAPV/FPCP/PMMU — all 68000-specific hardware) were stated as if
  universal; both now carry explicit 68k-only scoping with the 6809
  equivalent (carry + `B`; no confirmed 6809 equivalent range at all)
  cross-referenced.
- `common/ipc.md` and `common/unix-differences.md`: the signal-code table's
  "256+ = user-defined" tier assumes a 16-bit code (68k's `d1.w`) and is
  physically impossible on 6809's 8-bit `B`-register signal code — both
  files now flag this tier as 68k-only.
- `c/os9-c-cheatsheet.md`: the "Reference: Toolchain Components" table
  (`c.prep`/`c.pass1`/`c.opt`/`c.asm`/`c.link`) is 6809 toolchain naming
  from the file's only C-compiler-manual source (the 1983 6809 edition),
  presented with no architecture tag inside a file titled "(68k)" and
  contradicting that same file's own `Live` 68k chain
  (`cpp`/`c68`/`o68`/`r68`/`l68`) two sections earlier — the file's own
  Pitfalls section had already half-noticed the mismatch ("hasn't been
  reconciled") without resolving it; now labeled and cross-referenced.

Everything else checked (6809/*, 68k/*, basic09/*, remaining c/*,
common/module-format.md's already-known flag) held up — architecture
boundaries were already correctly maintained, largely because of the
density-rewrite and utility-usage work done earlier the same day.

**RESOLVED 2026-07-18 — `setime` interactive prompt year-digit count:**
`6809/coco-dragon-hardware.md` (line ~186) documents `setime`'s
interactive no-clock-module prompt as 4-digit-year `yyyy/mm/dd
hh:mm:ss`, sourced from the Radio Shack/Tandy CoCo OS-9 Level I manual.
`6809/utility-usage.md`'s own `setime` entry (sourced from the Level 2
Operating System Manual) claimed 2 digits with a Y2K-bug note. Live test
on `nitros9repl.sh` confirmed the actual interactive prompt displays
`       yyyy/mm/dd hh:mm:ss` template — **4-digit year is correct**.
coco-dragon-hardware.md tagged `Live`; utility-usage.md corrected to 4 digits
with backward note identifying the prior 2-digit claim as incorrect.

**RESOLVED 2026-07-17 — 6809 signal "reserved" range (4-127 vs 128) is not
kernel-enforced:** `6809/syscalls-and-module-format.md`'s Signals section
and `common/ipc.md`'s signal table both carried a `Manual, Flag` on where
the user-definable signal-code range starts (some sources say 4, one
CoCo-specific source says 128). Live test on `nitros9repl.sh`: a program
installed its own `F$Icpt` handler, then `F$Send`'d itself code 50 (deep
in the disputed 4-127 zone) followed by code 200 (undisputed
user-definable range). Both sends succeeded (carry clear) and both
invoked the handler, which correctly saw the matching code in `B` both
times (`GOT 50` / `GOT 200` printed via `I$WritLn`, CR-terminated for a
clean read — an earlier same-session attempt without an explicit CR byte
in the message buffer produced garbled multi-string spillover, confirming
`I$WritLn` scans for a literal `$0D` and not the FCS sign-bit convention,
an unrelated but real gotcha worth keeping in mind for future `I$WritLn`
tests). No rejection, no kill, no different handling for code 50 vs 200 —
the kernel delivers any code ≥4 identically to an installed handler.
**Conclusion: "reserved" is a Microware naming/documentation convention
only, not a behavioral boundary the kernel enforces** — the 4-vs-128
disagreement between sources is now known to be moot for practical
purposes. Both flagged files updated to `Live` with this finding; the
`Flag` is cleared per `CONFIDENCE-TAGS.md`'s rule that `Live` is the only
tier that resolves one.

## Process rules for any extraction or edit pass

- **Never instruct an agent to preserve a source's worked code example
  "precisely."** Code doesn't survive paraphrasing the way prose does;
  describe what the example demonstrates and have code written fresh from
  a functional spec by an agent that never saw the source. Any smell of
  verbatim reproduction or structural mirroring of a source is a
  stop-and-fix, not a note.
- The "OS-9 Relocating Macro Assembler" manual in 68k archive folders is a
  **6809** manual — never a source for 68k claims.
- Cross-reference a "correction" against the skill's own `Live`
  claims before applying it — a lone session overwriting an established
  fact is this project's known regression pattern.
- User-facing reference files carry **no session dates, commit hashes,
  host paths, or investigation narratives** — the six confidence tags
  (`CONFIDENCE-TAGS.md`) inline, nothing else. Maintainer state lives
  here and in `6809/STATUS.md`.

## Don't re-attempt blindly

- The `rma` hang (6809): root-cause investigation this session was
  genuinely exhaustive for what's reachable without XRoar-level
  instruction tracing or a known trigger address for `-trap`. Re-running
  the same invocation and waiting again will not produce new information.
- The `asm` output-location "mystery" is **solved** (writes to `CMDS`,
  same as `PACK`) — don't re-diagnose it as broken if a fresh session
  checks the wrong directory again.
