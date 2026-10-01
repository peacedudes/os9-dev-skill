# (DE) Übersetzung – automatische Platzhalter

Dies ist eine automatische Übersetzungsplatzhalter-Datei. Originalpfad: os9-dev-skill/os9-dev/references/common/ipc.md

---

# OS-9 Inter-Process Communication: Patterns and Gotchas

Mechanism-level call signatures (`F$Send`, `F$Icpt`, `F$Event`/`Ev$*`,
`F$DatMod`, etc.) are in `68k/syscall-reference.md`. This file is the practical
layer on top: how these mechanisms actually get used, and where they bite.

---

## Signals

One process can asynchronously interrupt another via signal - a narrow channel that flags
exceptional conditions or serves as a general-purpose notification when unmasked.

**Codes:**

| Code | Meaning | Interceptable? |
|---|---|---|
| 0 | Kill | No |
| 1 | Wake-up | No |
| 2-4 | Keyboard/modem (Ctrl-E abort, Ctrl-C interrupt, hangup) | Yes |
| 5-255 | Microware-reserved | Yes |
| 256+ | User-defined | Yes |

**68k-specific ceiling:** the `256+` user-defined tier assumes a 16-bit
signal code 