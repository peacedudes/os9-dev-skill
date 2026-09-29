# Source authority: what counts as Microware's word

This file exists because the rest of this repo makes claims about OS-9, and a
claim is only as good as what backs it. It answers one question: **for any
source in the corpus, is it Microware speaking, or is it someone else's
reading of Microware?**

**The rule:** for divergence work (`DIVERGENCES.md`), only
Microware-published documentation counts as authoritative - including documentation published under licence by Tandy /
Radio Shack, Dragon Data, and Motorola, which are Microware's own manuals
carrying a licensee's imprint. Third-party books are **not** authoritative,
however good they are. The OS-9 Guru in particular is an excellent book and is
still not Microware's word.

**Equally important, and the reason this project exists at all:** `os9exec` and
NitrOS-9 are **reverse-engineered reimplementations by the user community**.
Neither is a specification. Both have had real errors. Where a runtime and a
Microware manual disagree, the manual is the specification and the runtime is
the candidate defect - see `os9-dev/references/CONFIDENCE-TAGS.md`.

## Filenames in this corpus are unreliable - classify by title page

Four files carry third-party-sounding names but are **genuine Microware
manuals**. Anyone applying the "Microware only" rule by filename would wrongly
throw all four away:

| Filename | What the title page actually says |
|---|---|
| `68k/M68000_Programmers_Reference_Archive_History.txt` | *OS-9/68000 Operating System Technical Manual*, Copyright 1984 Microware Systems Corporation |
| `6809/Gimix_OS-9_Programmers_Manual_Jan83.txt` | *Microware OS-9 Operating System System Programmer's Manual*, Copyright 1980, 1982 Microware |
| `6809/Gimix_OS-9_Users_Manual_1983.txt` | *Microware OS-9 Operating System User's Manual*, Copyright 1980 Microware |
| `6809/OS-9_Interactive_Debugger_Users_Manual_ROUG.txt` | *Microware Interactive Debugger User's Manual*, (C) 1980, 1981, 1982 Microware |

And two are misleading in the other direction:

| Filename | Reality |
|---|---|
| `6809/OS-9_Quick_Reference_1982.txt` | Copyright **1992** by F. G. Swygert - a third-party quick reference, not a 1982 document |
| `6809/OS-9_Quick_Reference_1st_Farna_CoCo.txt` | Professional OS-9/**68000** documentation, not CoCo/6809 material despite the filename |

## Authoritative - Microware, or Microware under licensee imprint

**68000 / OS-9/68k**

| Source | Rights holder / date |
|---|---|
| `BASIC09_Reference_Manual_Rev_H.txt` | Microware 1980, 1984 |
| `M68000_Programmers_Reference_Archive_History.txt` (see rename table) | Microware 1984 |
| `OS-9_BASIC_User_Manual.txt` | Microware 1991 (Rev G, v2.4) |
| `OS-9_Primer.txt` | Microware 1994 (Heilpern; published by Microware, Des Moines) |
| `OS-9_Technical_IO_Manual_V2.4.txt` | Microware 1990 |
| `OS-9_v2.4_Technical_Reference_Manual.txt` | Microware 1994 |
| `OS9_Technical_Manual_Disk_File_Organization.txt` | Microware (Technical Manual extract) |
| `Using_Professional_OS-9_v2.4.txt` | Microware 1991 |
| `os9insights_ed2.txt` | Copyright Microware 1992 |
| `os9insights_ed3.txt` | Copyright Microware 1988, 1992, 1994 |
| `Enhanced_OS-9_68K_MVME_Guide.txt` | Microware 2000 - **v3.2 era, outside this project's v2.4 scope** |
| `Enhanced_OS-9_68K_Release_Notes.txt` | Microware 2000 - same caveat |

**6809 / OS-9 Level One and Two**

| Source | Rights holder / date |
|---|---|
| `BASIC09_Reference_Manual_Rev_F.txt` | Dragon Data Ltd. + Microware 1983 |
| `BASIC09_Reference_Manual_Rev_G.txt` | Microware content, licensee front matter |
| `BASIC09_Reference_Manual_Tandy.txt` | Tandy / Motorola 1983 |
| `Gimix_OS-9_Programmers_Manual_Jan83.txt` (see rename table) | Microware 1980, 1982 |
| `Gimix_OS-9_Users_Manual_1983.txt` (see rename table) | Microware 1980 |
| `OS-9_Assembler_Editor_Debugger_Manual_Dragon.txt` | Microware 1980, 1984 |
| `OS-9_C_Compiler_Microware.txt` | Microware / Radio Shack |
| `OS-9_Interactive_Debugger_Users_Manual_ROUG.txt` (see rename table) | Microware 1980-1982 |
| `OS-9_Level_2_Operating_System_Manual.txt` | Tandy |
| `OS-9_Level_2_System_Designers_Guide.txt` | Microware 1983 |
| `OS-9_Level_Two_Development_System_Tandy.txt` | Tandy |
| `OS-9_Operating_System_Users_Guide.txt` | Microware 1980, 1983 |
| `OS-9_Pascal_Reference_Manual.txt` | Microware 1984 (out of scope by prior decision) |
| `OS-9_Relocating_Macro_Assembler_Manual.txt` | Microware |
| `OS-9_System_Programmers_Manual.txt` | Microware 1980, 1984 (Rev H) |
| `OS-9_System_Programmers_Manual_Rev_F1_1983.txt` | Microware 1980, 1982 |
| `OS-9_Technical_Reference_Tandy.txt` | Microware 1985/1986 |
| `OS-9_Users_Manual_1983.txt` | Microware 1980 |
| `Radio_Shack_CoCo_OS-9_Level_I_1983.txt` | Tandy / Radio Shack |
| `OS-9_Hi-Res_Screen_Dump_Utilities_Tandy.txt` | Tandy (narrow; prior scope decision: out) |

**Corpus root**

| Source | Rights holder / date |
|---|---|
| `Microware_Training_OS-9_Starter.txt` | Microware 1994 - official training material |
| `Microware_Training_OS-9_Intermediate.txt` | Microware - official training material |
| `Microware_Training_OS-9_Advanced.txt` | Microware - official training material |
| `OS-9_Internet_Software_Reference_Manual.txt` | Microware 1992 |

## Not authoritative for divergence purposes

Good sources, several of them excellent, but not Microware speaking. Useful as
corroboration or as a pointer to go find the real passage - never as the
authority a divergence is scored against.

| Source | Who |
|---|---|
| `Galactic Industrial - The OS-9 Guru` (3 files) | Paul S. Dayan, Galactic Industrial, 1992 |
| `Mastering_OS-9_on_the_Tandy_Color_Computer_1995.txt` | FARNA Systems 1995 |
| `Mastering_OS-9_on_the_Tandy_Color_Computer_3.txt` | Paul K. Ward / F. G. Swygert |
| `OS-9_Level_Two_and_the_Tandy_Color_Computer_3_Alexander.txt` | Alexander / Honaker 1992-94 |
| `OS-9_Quick_Reference_1982.txt` | F. G. Swygert 1992 (misnamed - see above) |
| `OS-9_Quick_Reference_1st_Farna_CoCo.txt` | FARNA 1994 (and 68k content, not 6809) |
| `OS-9_Quick_Reference_2nd_Farna_CoCo.txt` | FARNA 1994 |
| `O-FLEX_..._Gimix.txt` | FHL Inc. 1983 |
| `OS-9_GMX_III_Support_ROM_User_Manual_RevC.txt` | GIMIX 1983 |
| `OS9_68000_V2.4_System_Requirements.txt` | Peripheral Technology (board vendor) |
| `OS-9_Processors_Hardware_Support.txt` | RadiSys 2006 marketing data sheet - no technical content |
| `Motorola_M68000_Programmers_Reference_Manual.txt` | Motorola 1992 - **authoritative for the CPU, not for OS-9** |

## Judgment calls, recorded so they can be challenged

- **`os9insights` (ed2/ed3) and `OS-9_Primer` are copyright Microware Systems
  Corporation**, so by the rule above they are authoritative - even though both
  are books in form. They are not third-party books; the rights holder is
  Microware. Treated as authoritative here.
- **Motorola's own M68000 Programmer's Reference Manual** is authoritative for
  processor behaviour (instruction semantics, exception frames) and is used
  that way. It says nothing about OS-9 and is never a source for OS-9 claims.
- The two **Enhanced OS-9 (2000, v3.2)** manuals are genuinely Microware but
  document a later major version. Mining them into v2.4 material risks
  importing v3.2 semantics; kept out of scope, flagged rather than deleted.

## Where the weight still sits

This corpus is what could be found, not Microware's documentation set. Read
nothing here as complete coverage of OS-9: where a fact is absent or thin, the
manual carrying it may simply never have been in reach.

The third-party Guru and FARNA references are cited more
often than any single Microware manual. That reflects how the corpus was
assembled - the third-party books are better indexed and far easier to search
than OCR'd manual scans - rather than a judgment about authority, which the
rule at the top of this file settles the other way.
