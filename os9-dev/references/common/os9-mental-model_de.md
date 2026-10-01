# (DE) Übersetzung – automatische Platzhalter

Dies ist eine automatische Übersetzungsplatzhalter-Datei. Originalpfad: os9-dev-skill/os9-dev/references/common/os9-mental-model.md

---

# OS-9 Mental Model

Modules, processes, I/O, and memory as one system. These concepts are
identical across 6809/68k/OS-9000; where a byte value or register is
architecture-specific it's marked inline. 68k values are the default here;
6809 byte layouts live in `6809/syscalls-and-module-format.md`.

## Modules: the unit of software is memory, not files

- Everything executable or data-bearing is a **module**: header (type,
  language, attributes, CRC) + body + trailing 24-bit CRC. Programs, device
  drivers, file managers, trap libraries, shared data - all modules.
- The kernel tracks resident modules by name in the **module directory**.
  "Loading" registers a module there; "running" forks a process from the
  registered copy. One resident copy serves every process running it.
- Header sta