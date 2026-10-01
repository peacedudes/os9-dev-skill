# (DE) Übersetzung – automatische Platzhalter

Dies ist eine automatische Übersetzungsplatzhalter-Datei. Originalpfad: os9-dev-skill/os9-dev/references/68k/os9-68k-assembly.md

---

# OS-9/68000 Assembly Language Reference

Scope: OS-9-specific 68k assembly facts (module mechanics, syscall
dispatch, register ABI, exception vectors). No surveyed source provides a
true 68k assembler manual - directive syntax has known gaps (listed at the
end); don't assume 6809 RMA syntax carries over. (The "Relocating Macro
Assembler" manual found in 68k archives is 6809-only - never a 68k
source.)

## Before you assemble anything

Five facts that decide whether your first build works. All are detailed
below; they are collected here because each bites *before* you have output
worth debugging.

1. **`I$`/`F$` call names are not symbols** - nothing on the SDK disk defines
   them. `dc.w I$Write` assembles clean and then fails at link. Define them
   as numeric constants in your own sourc