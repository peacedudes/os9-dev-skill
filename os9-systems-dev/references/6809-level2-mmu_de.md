# (DE) Übersetzung – automatische Platzhalter

Dies ist eine automatische Übersetzungsplatzhalter-Datei. Originalpfad: os9-dev-skill/os9-systems-dev/references/6809-level2-mmu.md

---

# OS-9/6809 Level 2 Memory Management (DAT/MMU)

`Manual` - MMU/DAT register internals sit below what a shell session
can observe, and the boot-ROM material below what any emulator exercises,
so `Live` verification isn't reachable here. Cross-referenced across the
Level 2 Operating System Manual and the Level 2 System Designer's Guide,
which agree closely.

## The Split: Level 1 vs Level 2

6809 OS-9 exists in two distinct configurations, differing fundamentally in
memory organization:

**Level 1** is a single-process (or minimal multi-process) system confined
to a flat, shared 64K address space combining RAM and ROM. No MMU, no
memory isolation. Practical systems needed at least 12K RAM, with most
real deployments using 56-60K usable space after accounting for ROM and
video RAM. Level 1 i