# (DE) Übersetzung – automatische Platzhalter

Dies ist eine automatische Übersetzungsplatzhalter-Datei. Originalpfad: os9-dev-skill/README.md

---

# OS-9 skills for AI coding assistants

Two agent skills that teach an AI coding assistant to work on **Microware
OS-9** for the 6809 and the 68000. With them loaded, an assistant can write,
port and debug BASIC09, Microware C and 68000 or 6809 assembly. It can drive
the shell and its utilities, build modules, make system calls, read error
codes, and work below the application line on device drivers, file managers
and the kernel.

Install them in Claude Code:

```
/plugin marketplace add peacedudes/os9-dev-skill
/plugin install os9@os9-dev-skill
```

Other assistants: see [Installing](#installing).

## Why it exists

AI models know very little about OS-9, and some of what they know is wrong.
Its documentation is spread across decades of manuals, editions and scans, so
a model has seen litt