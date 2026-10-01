# (DE) Übersetzung – automatische Platzhalter

Dies ist eine automatische Übersetzungsplatzhalter-Datei. Originalpfad: os9-dev-skill/os9-dev/references/68k/syscall-reference.md

---

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

## Calling con