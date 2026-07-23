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
references over raw manual text. Setting up a REPL harness from scratch
(not just operating an existing one): `common/os9exec-repl-setup.md` (68k),
`6809/nitros9repl-setup.md` (6809).

## Verification

When a claim can be run instead of asserted, run it. Live harnesses (in
the os9exec repo): 68k — `tools/os9repl.sh` driving os9exec (operating
guide: `references/common/using-os9exec-repl.md`); 6809 —
`tools/nitros9repl.sh` driving real NitrOS-9 under XRoar
(`references/6809/using-nitros9-repl.md`). Both have real gotchas (gated
send goes silent inside sub-programs; use raw key mode there). Reference
files carry inline confidence tags — legend in `references/CONFIDENCE-TAGS.md`;
ordering is `Live` > `Source` > `Manual` > `Hearsay`, and a `Flag` means two
sources disagree (unresolved). OS-9000 claims: punt to manuals.

## Rules of engagement

- Name the target (6809 / 68k / OS-9000) in every answer.
- Microware C is K&R-era — no ANSI (`const`, prototypes, `string.h`). See
  `references/c/`.
- Unix syscalls don't map 1:1 — check `references/common/unix-differences.md`.
- **Watch for 6809 facts blended into nominally-68k text** (and vice
  versa). Anything mentioning "direct page" is 6809-only, full stop. When
  a foundational claim (type size, register convention) looks off, verify
  live against the 68k toolchain rather than trusting one passage.
