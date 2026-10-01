# (DE) Übersetzung – automatische Platzhalter

Dies ist eine automatische Übersetzungsplatzhalter-Datei. Originalpfad: os9-dev-skill/os9-systems-dev/references/file-managers.md

---

# OS-9 File Managers

Baseline `Manual`, cross-referenced across multiple manuals; path-descriptor
byte offsets are additionally `Source` against os9exec's C.

**The entry-point conventions below are `Manual`**, and stay so short of
real hardware: os9exec, the 68k runtime available here, never runs an
installed file manager's code (`os9-dev`'s `common/using-os9exec-repl.md`,
"What os9exec does not implement"), so they could not be exercised.
The same holds for `device-drivers.md`.

A file manager sits between application I$ calls and a device driver - the
layer that understands filesystem or protocol structure (directories,
segments, line editing) while the driver knows only raw sector or character
transfer. RBF, SCF and SBF are the three standard ones; PIPEMAN is a fourth,
for pipes. A cu