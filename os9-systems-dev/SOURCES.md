# Provenance

Sibling skill to `os9-dev`, holding the device-driver/file-manager/
kernel-internals content that application programmers don't need. Same
provenance rules as `os9-dev/SOURCES.md`: curated, condensed reference
material in its own words; no raw manual text reproduced; no verbatim
worked code examples; no proprietary Microware source code anywhere in
the chain.

| Reference file | Primary source(s) |
|---|---|
| device-drivers.md | OS-9 v2.4 Technical I/O Manual (primary); cross-checked against the OS-9 v2.4 Technical Reference Manual, a 1985 independent OS-9/68000 technical manual, and The OS-9 Guru |
| file-managers.md | OS-9 v2.4 Technical Reference Manual + Technical I/O Manual v2.4 (entry points, GetStat/SetStat, path descriptors); Disk File Organization manual (RBF disk structure, record locking, raw I/O, security); The OS-9 Guru cross-checks |
| kernel-internals.md | 1985 independent OS-9/68000 technical manual (scheduler, vector layout); The OS-9 Guru (module directory, allocation, process descriptor); OS-9 Insights; OS-9 v2.4 Technical Reference Manual; Microware Training & Education "OS-9 Advanced" seminar manual (trap entry-point names, D_MaxAge details, timeslice inheritance — the D_MaxAge two-tier mechanism additionally cross-checked against Using Professional OS-9 v2.4) |
| 6809-level2-mmu.md | 6809 Level 2 System Designer's Guide (primary), cross-referenced against other 6809 System Programmer's/Level 2 manuals; Gimix "OS-9 GMX III Support ROM User's Manual" Rev C (1983). `Manual` only |

None of these files carries a `Live` tag yet (see the INDEX confidence
note); verification backlog lives in os9-dev
`references/VERIFICATION-BACKLOG.md`.
