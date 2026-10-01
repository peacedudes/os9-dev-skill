# (DE) Übersetzung – automatische Platzhalter

Dies ist eine automatische Übersetzungsplatzhalter-Datei. Originalpfad: os9-dev-skill/os9-dev/references/c/os9-clib-reference.md

---

# OS-9 C Standard Library Reference

For Microware C Compiler targeting 68000/6809 OS-9 systems.

**Every `Live` tag here is `Live` (os9exec)** - OS-9/68k. No 6809 C
compiler was available to this project, so nothing on this page is
6809-verified; treat the 6809 column of any comparison as `Manual`.

## Overview

The Microware C library bridges OS-9 system calls and UNIX-style C I/O patterns.
The startup routine converts the OS-9 parameter string into `argc`/`argv`.
All standard I/O is path-based (paths 0=stdin, 1=stdout, 2=stderr) and
uses OS-9 `I$Open`, `I$Read`, `I$Write` calls under the hood.

Most wrapper functions follow UNIX naming for portability, but parameters
and return values may differ from their raw OS-9 equivalents - verify against
the manual's cross-reference table between 