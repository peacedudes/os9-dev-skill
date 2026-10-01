Two agent skills that teach an AI coding assistant to work on Microware OS-9 for the 6809 and the 68000: BASIC09, Microware C, 68000 and 6809 assembly, the shell and its utilities, modules, system calls and error codes, and below the application line, device drivers, file managers and the kernel.

AI models know very little about OS-9, and fill the gaps with Unix habits that fail there. These skills give the assistant about 13,000 lines of OS-9 fact, loaded only as a task needs them, with every claim tagged by what stands behind it: a Microware manual, or a program actually run.

**Install in Claude Code**

```
/plugin marketplace add peacedudes/os9-dev-skill
/plugin install os9@os9-dev-skill
```

**Other assistants:** download `os9-dev-skills.zip` below, or clone the repository. Install the two skill folders where your assistant loads skills, or point any agent that reads files at `AGENTS.md`.

Covers the early OS-9 line, from the 6809 through OS-9/68000 v2.4. Sibling projects: [os9exec](https://github.com/peacedudes/os9exec), an OS-9/68000 emulator, and [osk-freeware](https://github.com/peacedudes/osk-freeware), over a thousand programs written for OS-9/68000, runnable in a browser.

These skills come from OS-9's users, not from Microware. Corrections are welcome in the issue tracker.
