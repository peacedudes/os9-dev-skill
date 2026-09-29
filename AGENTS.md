# OS-9 development skills - agent guide

This folder holds two self-contained reference skills for Microware OS-9
development. They are plain Markdown; any coding agent can use them by reading
the relevant files on demand. No build, no dependencies.

## The two skills

- **`os9-dev/`** - Application work on OS-9 (6809 or 68000): BASIC09, Microware
  C, 68k/6809 assembly, the shell and utilities, modules, syscalls, error
  codes, and driving the os9exec / NitrOS-9 emulators. Consult it when writing,
  porting, or debugging programs that *run on* OS-9.

- **`os9-systems-dev/`** - Below the application line: device drivers, file
  managers, kernel internals (System Globals, Process Descriptor, scheduler),
  exception/IRQ handling, disk/boot mechanics, and 6809 Level 2 MMU/DAT.
  Consult it for kernel/driver work rather than ordinary applications.

They are siblings and cross-reference each other; keep both.

**Scope:** the early OS-9 line - 6809 Level One and Level Two, and OS-9/68000
up to version 2.4. Nothing here covers OS-9000, later OS-9 releases, or other
Microware products such as MAUI, and networking is covered only in outline.
For those, say so and point to Microware's documentation rather than answering
from these files.

## How to use them

1. Start from the `SKILL.md` that matches the task - it is the entry point.
2. Open only the reference files you need. `references/INDEX.md` in each skill
   maps topics to files **and symptoms to causes** - start there when something
   failed and you don't yet know which topic owns it. Detail is loaded on
   demand rather than all at once.
3. Mind the confidence tags. Every claim carries one - `Hearsay`, `Manual`,
   `Source`, `Live`, `Absent`, `Flag` - defined in
   `os9-dev/references/CONFIDENCE-TAGS.md`. That single copy governs both
   skills; `os9-systems-dev` cites it by path rather than keeping its own.
   **A `Live` tag is evidence about an emulator, never proof about OS-9
   itself:** where a runtime and a Microware manual disagree, the manual is the
   specification and the runtime is the candidate defect.

4. Resolve paths the way the files write them. Inside a skill, a reference
   such as `common/ipc.md` is relative to that skill's `references/`
   directory; a reference into the other skill names it (`os9-dev`'s
   `common/module-format.md`).
5. Answer specifics from the files, not from memory. If a file cannot be
   opened, say which claim went unchecked rather than filling the gap -
   widely repeated claims about OS-9 are often wrong, and these files exist to
   correct them.

`SOURCE-AUTHORITY.md` (root) says what counts as Microware's word;
`DIVERGENCES.md` (root) lists where a runtime disagrees with a manual. Both are
review material rather than part of either installed skill.

## Provenance

All source material is public-domain or freely published documentation, or
preservation archives. No proprietary Microware source code was used. Facts are
stated as facts; the prose around them is written here rather than borrowed -
no manual text reproduced at length and no worked example kept verbatim, though
short attributed quotations appear where a manual's exact wording is itself the
evidence. See each skill's `SOURCES.md` for what stands behind which file, and
what was deliberately not used.
