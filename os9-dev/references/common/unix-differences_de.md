# (DE) Übersetzung – automatische Platzhalter

Dies ist eine automatische Übersetzungsplatzhalter-Datei. Originalpfad: os9-dev-skill/os9-dev/references/common/unix-differences.md

---

# OS-9 for people who already know Unix

Delta document, not a tutorial - ordered by how badly a wrong Unix
assumption bites, not by topic. Tier 3 (bottom) is a flat 1:1 lookup table;
skim once. Spend attention on Tier 1.

Applies OS-9-wide, not just 68k: the shell/directory/pipe behaviors below
(chd/chx split, `!` not `|`, CR line endings, ESC-exit, the control-key
inversions) were independently cross-referenced against multiple 6809
primary sources and confirmed identical. Where 6809 genuinely differs
(register conventions, `int` width, module header encoding), that's a
Tier 2/3 item, not a Tier 1 one - the model-level breaks from Unix are the
same regardless of which OS-9 architecture you're on.

---

## Tier 1 - model breaks (wrong, not just slow, if you assume Unix)

### 1. Two curren