# (DE) Übersetzung – automatische Platzhalter

Dies ist eine automatische Übersetzungsplatzhalter-Datei. Originalpfad: os9-dev-skill/AGENTS.md

---

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
  Consult it fo