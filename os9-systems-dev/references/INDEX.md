# Reference Index — read the matching row before answering

| If the task involves… | Read |
|---|---|
| Writing a device driver: entry points, static storage, IRQ handling, RBF/SCF/SBF-specific driver conventions | device-drivers.md |
| Writing a file manager: entry points, Create/Open/Read/Write contract, GetStat/SetStat dispatch, path descriptor internals, RBF disk structure (identification sector, file descriptors, directories, allocation bitmap), record locking, file security | file-managers.md |
| Kernel structures (System Globals, Process Descriptor, Path Descriptor), the scheduler algorithm (priority + aging, D_MaxAge), module directory internals, trap-handler mechanics, memory-allocation internals, exception/interrupt vector layout | kernel-internals.md |
| 6809 Level 1 vs Level 2 (flat 64K vs DAT/MMU), Level 2 MMU/DAT register internals, Gimix GMX III support ROM | 6809-level2-mmu.md |
| DriveWire server implementation, NitrOS-9 scdwv/dwio driver pair | sibling os9-dev skill: `references/6809/using-nitros9-repl.md` |

Module format, syscall catalog, and error codes are shared with
application-level work and live in the sibling `os9-dev` skill
(`common/module-format.md`, `68k/syscall-reference.md`,
`common/error-codes.md`) — not duplicated here. `os9-dev`'s
`common/memory-and-io.md` also covers a mental-model-level pass over
device descriptors, `I$Attach`/device-table matching, and path-descriptor
structure — the same territory `device-drivers.md`/`file-managers.md`
cover in full systems depth here; the two are meant to agree, cross-check
`memory-and-io.md` when changing a shared fact (offset, field name,
matching rule) in either of those two files.

**Confidence:** tag legend in the sibling skill,
`os9-dev/references/CONFIDENCE-TAGS.md`. **Struct layouts are largely
`Source`**, cross-checked against os9exec's C: the Process Descriptor, the
module header / executable / device-descriptor structs (with compile-time
offset assertions), and the path descriptor (common `PD_` header plus the
128-byte SCF options struct). What stays `Manual` is the **behavioral** layer
os9exec doesn't emulate — driver and file-manager dispatch, the scheduler
algorithm, System Global memory, the Module Directory — plus
`6809-level2-mmu.md`, which is `Manual` only. `file-managers.md`'s Record
Locking section is largely `Live` (68k). Entry-point calling conventions are
untestable on os9exec, not merely untested (see SKILL.md → Verification).
