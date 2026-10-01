# (DE) Übersetzung – automatische Platzhalter

Dies ist eine automatische Übersetzungsplatzhalter-Datei. Originalpfad: os9-dev-skill/os9-dev/references/c/os9-c-cheatsheet.md

---

# OS-9 C Compiler Cheatsheet (68k)

**Every `Live` tag here is `Live` (os9exec).** No 6809 C compiler was
available to this project - the 1983-manual column below is `Manual`.

## Setup

**Before any of this works you need a running OS-9 system and Microware's
compiler.** Neither ships with this material: `cc`, `cpp`, `c68`, `o68`, `r68`
and `l68` are proprietary Microware programs that come from a licensed SDK or
disk image. The commands below are typed at the OS-9 shell prompt. Without
hardware, getting from an emulator plus such an image to that prompt is covered
in `common/using-os9exec-repl.md`.


```
chx /h0/CMDS
setenv CLIB /h0/LIB
setenv CDEF /h0/DEFS
```

`CLIB` (must contain `cstart.r`, `clib.l`) and `CDEF` (header files) are
required. OS-9 requires `chx` - the execution director