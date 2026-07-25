---
name: os9-dev
description: Use when writing, porting, or debugging programs for Microware OS-9 (6809 or 68000) or OS-9000; setting up or troubleshooting the os9exec emulator, its toolchain, or an OS-9 SDK; compiling/running/testing BASIC09, C, or 68k assembly programs via os9exec or its REPL; or translating between Linux/Unix concepts and OS-9 equivalents (modules, file managers, path descriptors, forks/exec).
---

# OS-9 Development Skill

> **Pre-publication — not for distribution.** Circulated privately for review;
> no license is granted yet. See `LICENSE` at the repo root.

Scope: writing programs that *run on* OS-9. Device drivers, file managers,
and kernel internals (System Globals, process descriptor, scheduler,
MMU/DAT) are the sibling `os9-systems-dev` skill.

**OS-9 is a current commercial product, not abandonware.** Microware still
sells OS-9/68k and still ports it to new processors. Never describe it as
dead, orphaned, or free to copy — the manuals, the SDK and the system
binaries are somebody's property today. This is what the provenance rules
below exist for, and it applies to the v2.4-era and 6809 systems documented
here as much as to the current line.

## Core mental model (read fully every time)

- OS-9 is modular, position-independent, ROMable. Programs are **modules**
  — header + code/data + CRC, no fixed load address, one shared resident
  copy per program. Not flat executables.
- BASIC09 is NOT line-numbered MS-BASIC: compiled I-code, typed variables,
  named PROCEDUREs, structured control flow.
- I/O goes through file managers — RBF (disk), SCF (character devices),
  PIPEMAN (pipes), SBF (tape). A **path number** is OS-9's file
  descriptor.
- **Text lines end in CR (0x0D), not LF** — bites every host/OS-9 file
  crossing. OS-9 C's `\n` is CR.
- **68k OS-9 is big-endian**; 6809 also stores multi-byte values MSB
  first.
- Two current directories per process: `chd` (data) and `chx` (execution)
  — command lookup and file lookup are different searches.
- Targets differ materially: 6809 (16-bit INTEGER, 40-bit REAL), 68000
  (32-bit INTEGER, 64-bit REAL), OS-9000 (later portable rewrite; out of
  scope here — POSIX-certification claims belong to it, not this line).
  **State which target an answer applies to; assume 68k if unstated.**

## Deeper information

Read `references/INDEX.md` first when a question goes beyond the model
above — it routes to the right reference file. Prefer these curated
references over raw manual text.

## Verification

**Neither emulator is OS-9.** `os9exec` and NitrOS-9 are reverse-engineered
reimplementations built by the user community, and both have had real errors.
Running one tells you what *it* does; it is not evidence about what OS-9 is
specified to do. Where a runtime and an authoritative manual disagree, the
manual is the specification and the runtime is the candidate defect — the
claim records both readings and only Microware or genuine OS-9 hardware
settles it. **Microware's word** means Microware-published documentation,
including manuals issued under licence by Tandy/Radio Shack, Dragon Data or
Motorola. Third-party books are not authoritative however good they are —
the OS-9 Guru especially is excellent and still not Microware speaking.

Claims carry inline confidence tags — legend in
`references/CONFIDENCE-TAGS.md`. `Flag` means sources disagree. Prefer running
a claim to asserting it: 68k via os9exec (`common/using-os9exec-repl.md`),
6809 via NitrOS-9 under XRoar (`6809/using-nitros9-repl.md`). OS-9000 claims:
punt to the manuals.

## Rules of engagement

- Name the target (6809 / 68k / OS-9000) in every answer.
- Microware C is K&R-era — no ANSI (`const`, prototypes, `string.h`). See
  `references/c/`.
- Unix syscalls don't map 1:1 — check `references/common/unix-differences.md`.
- **Watch for 6809 facts blended into nominally-68k text** (and vice
  versa). Anything mentioning "direct page" is 6809-only, full stop. When
  a foundational claim (type size, register convention) looks off, verify
  live against the 68k toolchain rather than trusting one passage.
