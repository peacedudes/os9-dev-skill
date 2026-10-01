# (DE) Übersetzung – automatische Platzhalter

Dies ist eine automatische Übersetzungsplatzhalter-Datei. Originalpfad: os9-dev-skill/os9-dev/references/common/using-os9exec-repl.md

---

# Driving os9exec as an Agent

When real OS-9/68k equipment is not at hand, the os9exec emulator is one way
to get an OS-9 environment to work in. This page covers the mechanics of that
stand-in: launching, running programs, editing files, accounts, recovery. On
real hardware the OS-9 reference pages apply directly, and where the emulator
and a Microware manual disagree, the manual is the specification. The 6809
equivalent (NitrOS-9 under XRoar) is `6809/using-nitros9-repl.md`.

os9exec reimplements the OS-9 kernel interface over an emulated CPU; it is
not a hardware emulator running real firmware - no ROM, no video/keyboard
console to bridge around. Its stdin/stdout are the OS-9 console, so a plain PTY/pipe harness
works directly. It runs on macOS, Linux and Windows - in practice anything