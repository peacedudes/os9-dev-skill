# (DE) Übersetzung – automatische Platzhalter

Dies ist eine automatische Übersetzungsplatzhalter-Datei. Originalpfad: os9-dev-skill/os9-dev/references/common/module-format.md

---

# OS-9 Module Format

The unit of loadable code and data is the **memory module**: standard
header + body + trailing 24-bit CRC, tracked by name in the kernel's
module directory (lifecycle: `os9-mental-model.md`). This file documents
the 68k encoding as the default; 6809 byte values are a separate section
and must never be blended with the 68k tables. BASIC09 packed modules and
RunB: `basic09/pack-and-runb.md`.

Core facts:

- **Position independence (68k):** compilers emit PIC automatically; hand
  assembly must use only PC-relative and register-indirect modes. Load
  address is assigned at fork time.
- **Reentrancy:** one module copy serves all processes; each reaches its
  own data through a6 (linker convention). Data modules are the deliberate
  non-reentrant exception.
- **C string li