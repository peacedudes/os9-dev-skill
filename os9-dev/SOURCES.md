# Provenance

This skill contains only curated, condensed reference material written in
its own words. No manual text is reproduced at length; no worked code example
from any source is preserved verbatim (code examples were either dropped
or rewritten clean-room from functional specs); no file mirrors any
source's chapter structure. Short attributed quotations — a clause or a
sentence, cited to chapter and page — appear only where the manual's exact
wording is itself the evidence on a disputed point. All source material is public-domain,
freely-published Microware/Tandy documentation, or historical-preservation
archives. **No proprietary Microware source code was used anywhere in this
chain.**

Facts marked `Live` (see `references/CONFIDENCE-TAGS.md`) were confirmed
by running real programs on OS-9/68k (the os9exec emulator) or OS-9/6809
(NitrOS-9 under XRoar) — those confirmations are original findings,
independent of any manual.

## Primary sources by file

| File | Primary sources |
|---|---|
| common/os9-mental-model.md, common/unix-differences.md, common/module-format.md, common/memory-and-io.md, common/os9-tools-and-shell.md | OS-9 v2.4 Technical Reference Manual; Technical I/O Manual v2.4; Disk File Organization manual; Using Professional OS-9 v2.4; The OS-9 Primer; OS-9 Insights; The OS-9 Guru; a 1985 independent OS-9/68000 technical manual; OS-9 C Compiler manual; Microware Training & Education seminar manuals (malloc/_srqmem family, event variants) |
| common/ipc.md | OS-9 Insights (ed. 3); OS-9 v2.4 Technical Reference Manual (IPC chapter); Microware seminar manuals |
| common/utility-usage.md | Using Professional OS-9 v2.4, "The OS-9 Utilities" chapter (per-utility SYNTAX/OPTIONS sections and the tmode parameter table) |
| common/error-codes.md | OS-9 v2.4 Technical Reference Manual (error codes); OS-9/68000 Operating System Technical Manual (1985, Rev S) Appendix C; OS-9 C Compiler manual; BASIC09 Reference Manual App. C (identical across Rev F/G/H editions); Technical I/O Manual v2.4 |
| common/using-os9exec-repl.md | `Live` (os9exec) |
| basic09/* | BASIC09 Reference Manual (Rev H, and Rev F/G for cross-checks); OS-9 BASIC User Manual (Rev G, 1991); extensive `Live` coverage on both 68k (os9exec) and 6809 (NitrOS-9) |
| c/* | Microware C Compiler manual (1983, 6809 edition); The OS-9 Primer (Ultra C era); K&R; OS-9 v2.4 Technical Reference Manual; The OS-9 Guru (cstart/linker startup); 68k type sizes `Live` |
| 68k/syscall-reference.md | OS-9 v2.4 Technical Reference Manual; 1985 independent OS-9/68000 technical manual; The OS-9 Guru; OS-9 Insights; Technical I/O Manual v2.4 |
| 68k/os9-68k-assembly.md | The OS-9 Guru (68000-specific chapters); OS-9 v2.4 Technical Reference Manual; OS-9 C Compiler manual |
| 68k/network-sockets.md | OS-9 Internet Software Reference Manual (68000-only; no live verification — no network device in the emulator) |
| 6809/syscalls-and-module-format.md, 6809/assembly-and-tools.md | 9+ cross-referenced 6809 sources: OS-9 System Programmer's Manual (+ Rev F1 errata; Appendix C machine-code tables are the authoritative syscall-code source); Level 2 Operating System Manual; OS-9 Level Two Development System manual (Tandy); Tandy/CoCo Technical Reference; two independent User's Guides; Interactive Debugger manual; OS-9 Assembler/Editor/Debugger Manual (fully mined — Editor, Assembler/`asm`/MIA ch. 2, and Debugger command-table chapters; a generic Microware manual despite shipping with Dragon systems); OS-9 Relocating Macro Assembler Manual (RMA options, input/listing format, expression evaluation, macro facility, PSECT/VSECT/CSECT semantics, data-area access, RLINK/linker options, RMA-vs-MIA differences appendix); 1982/1992 Quick References. Assembler/debugger core and I$WritLn/F$Exit `Live` on real NitrOS-9; open-source NitrOS-9 project files (os9defs.a, help texts) used as `Source` cross-checks |
| 6809/coco-dragon-hardware.md | Tandy/CoCo Technical Reference; Radio Shack CoCo Level I manual; two Farna "Mastering OS-9" guides (1995/CoCo-3); OS-9 Hi-Res Screen Dump Utilities manual; "OS-9 Level Two and the Tandy Color Computer 3" (Alexander, 1994); OS-9 Quick Reference 2nd Ed. (Farna). Not `Live` (needs real/emulated hardware with video) |
| 6809/using-nitros9-repl.md | `Live` (NitrOS-9 EOU under XRoar via DriveWire) |
| 6809/gfx-windowing.md | OS-9 Level 2 Operating System Manual (GFX/GFX2 chapter, Ch. 9) primary; BASIC09 Reference Manual (Tandy), which reprints the same appendix, as an independent second OCR pass for function names and syntax; GFX2 calling sequences largely `Live` (NitrOS-9 under XRoar) |
| 6809/utility-usage.md | OS-9 Level 2 Operating System Manual (System Command Descriptions) primary; OS-9 Users Manual 1983 and Gimix OS-9 Users Manual 1983 (both Level 1) plus the Farna Quick References as cross-checks for OCR ambiguity and Level 1/Level 2 differences; a handful of entries `Live` on NitrOS-9 |
| 6809/reading-the-coco-screen.md | `Live` throughout (NitrOS-9 EOU under XRoar, driven over DriveWire with host-side screen capture); NitrOS-9's `windefs.as` as a `Source` cross-check for windint opcodes only |

Known-bad source note: the "OS-9 Relocating Macro Assembler" manual
circulating in 68k archives is actually a **6809** manual (it documents 6809
registers and addressing) — never use it for a 68k-specific claim. Its 6809
content is drawn on in `6809/assembly-and-tools.md`.

Provenance note on the Microware 6809 Level 1 source archive held alongside
this corpus: it is actual Microware source code, not a manual, and is held to
the same rule as the NitrOS-9 kernel-source cross-check — cross-check only,
never a primary source, never extracted at length. It has not been opened for
any purpose.

Two files in the 6809 text-resource set are named `Gimix_OS-9_*` but carry no
Gimix-specific content: `Gimix_OS-9_Programmers_Manual_Jan83.txt` is a
byte-identical duplicate of the System Programmer's Manual Rev F1 cited above,
and `Gimix_OS-9_Users_Manual_1983.txt` is an independent OCR pass of the same
Rev G User's Manual. Misleading filenames only. Genuinely Gimix-specific
material — the O-FLEX operating system and the GMX III Support ROM manual — is
handled separately; the GMX III manual is cited in `os9-systems-dev/SOURCES.md`.

Where two manuals disagree, both readings are recorded in the file with
a `Flag` tag, rather than silently picking one (see common/error-codes.md
and common/module-format.md for examples).
