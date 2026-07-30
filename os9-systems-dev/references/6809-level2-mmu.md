# OS-9/6809 Level 2 Memory Management (DAT/MMU)

`Manual` — MMU/DAT register internals sit below what a shell session
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
video RAM. Level 1 is simpler, cheaper, and adequate for embedded control
or single-user applications within tight RAM budgets.

**Level 2** adds Dynamic Address Translation (DAT) hardware — an MMU that
virtualizes each process's address space independently. While each process
still generates only 16-bit logical addresses (64K per task, not more),
those addresses are mapped by the MMU into disjoint portions of a larger
*physical* memory pool. This enables true multitasking with memory
isolation — different tasks can occupy different physical regions while
each seeing the same logical address layout.

**Common misreading**: "Level 2 gives an 8MB address space" is wrong. Each
process is confined to 64K *logical* addressing — the CPU generates only
16-bit addresses, an absolute per-task ceiling, no negotiation. The "up to
several MB" in hardware specs is the *combined physical* address space the
MMU can map across all tasks simultaneously — e.g. 8 task registers + 9-bit
mapping RAM addresses up to 512K physical, shared by all tasks, not 512K
per task. The manuals occasionally blur this distinction (cross-checked
across two independent documents to separate logical-per-task from
physical-system-wide cleanly).

Level 1's constrained 64K address space (often much less after ROM/video RAM) drove OS-9's minimal-footprint design ethos discussed in `os9-dev`'s `common/os9-mental-model.md`.

## How DAT Translation Works

- **DAT image**: each process descriptor holds a full software copy of the MMU's register state. On every context switch, the kernel copies the incoming process's DAT image into the actual MMU registers. MMU registers are write-only — the kernel reads from the process descriptor instead of the hardware.
- **Translation pipeline**: the 6809's high-order logical address bits (typically 4 or 5 lines, e.g. A12-A15 or A11-A15) index into a fast lookup table ("mapping RAM"). The looked-up value supplies the high-order *physical* address bits (A16-A20+); the low-order logical bits pass straight through unchanged. Block size follows directly from how many high bits go through the MMU: 4 lines → 4K blocks, 5 lines → 2K blocks.
- **Task Select Register**: a latch/PIA-driven register selecting which section of the mapping RAM is "live" — switching a process in is just changing this register's value plus reloading the DAT image, not physically moving anything.
- Minimum viable system: 5 virtual maps (system + 4 user tasks); 8 is the practical floor since hardware RAM sizes are powers of two.
- Common mapping-RAM parts: Fairchild/Motorola 93L412 (open-collector out) / 93L422 (three-state out), 256×4 bits, ~25ns access, two ganged for a 256×8 arrangement. The Motorola **MC6829** is a single-chip alternative (replaces 10-30 discrete parts) but adds ~110ns of address delay, capping practical clock speed around 1.0-1.5MHz — discrete bipolar RAM was preferred for 2MHz systems despite the extra parts count.

## Bootstrap and Addressing Subtleties

- After reset, mapping RAM contents are undefined, so the boot ROM at `$F000-$FFFF` must always be selected regardless of what's in the (garbage) mapping RAM — this requires *logical*-side address decoding for the ROM-select logic, not physical-side, to avoid a chicken-and-egg dependency.
- Logical-side ROM decoding is simpler but caps per-task space at 60K (interrupt vectors and task-clear code have to live in the reserved high block of every map). The alternative — disabling/redirecting the MMU immediately post-reset, then re-enabling under software control — allows the full 64K per task but needs more complex, fully-decoded (20-21 bit) address hardware.
- Writing to the MMU's own control range (e.g. `$F000-$F00F`) multiplexes the mapping RAM's address input away from the normal `A12-A15` (or `A11-A15`) source over to `A0-A3`, so the 16 (or so) entries can be loaded sequentially by software. The decoder that triggers this multiplexer switch **must** decode logical addresses, not physical ones — decoding physical addresses here creates a circular dependency (you need the MMU to know if you're addressing the MMU).

## The 6809 IRQ-Masking Peculiarity (real hazard for automatic task switching)

- `SWI2`/`SWI3` — the instructions OS-9 syscalls and user vectoring are
  built on — **do not set the 6809's IRQ mask bit**. A hardware IRQ firing
  between task-switch start and the kernel reloading its own stack pointer
  (which may still point into whatever map was active pre-switch) corrupts
  the stack and crashes the system.
- **Fix used in practice**: hardware externally masks the IRQ line from
  the moment interrupt-acknowledge is detected (decode `BA=1,BS=1` on the
  6809's `BA`/`BS` lines) until the kernel's first instruction
  (`ORCC #IRQMASK`) actually executes in its own map.
- Automatic task-switching hardware (the MC6829 approach) additionally
  needs a cycle-counting "fuse register" to know when it's safe to switch
  the task register *back* from 0 (kernel map) to the interrupted user
  task, since restoration happens via a plain `RTI` with no other signal
  marking "done."

Automatic switching's payoff: without it, every user map must waste part of its address space mirroring interrupt vectors and task-clear code (capping user space at 60-62K depending on block size); with it, user tasks get the full 64K.

## Physical Memory Layout Conventions

- RAM assumed contiguous from physical `$00000` upward, in 2K/4K-aligned blocks; OS-9 auto-scans for it at startup.
- Bootstrap ROM: at least 4K at `$FF000-$FFFFF` (reset vector, MMU init, ~3K of kernel) — worth noting the Designers Guide is internally inconsistent here: its MMU-chip-selection discussion frames this same 4K figure as a not-to-exceed ceiling ("should not exceed 4K bytes in total"), while its system-memory-map section frames it as a floor ("should be at least 4K bytes"). The memory-map section's "at least," 2K/4K-block-aligned framing is treated as authoritative here since it's the address-map-specific passage. Optional secondary ROM at `$F0000-$FBFFF`.
- I/O devices live in fully-decoded physical address space (20-21 bits, not logical), conventionally packed into as few physical blocks as possible near the top of the map (e.g. `$FE00-$FEFF`).
- DMA can bypass the MMU entirely (physical addressing); OS-9 arbitrates multiple DMA-capable devices in software, so no hardware bus-arbitration logic is required.
- Only the kernel (`OS9P1`/`OS9P2`) ever touches MMU hardware directly — file managers, drivers, and user code all go through ordinary syscalls, so a port to different MMU hardware only requires kernel-level changes.

## Gimix GMX III: A Concrete Support-ROM Implementation

Gimix's CPU III board is a real-world implementation of this MMU
architecture; its boot-time Support ROM is a worked example of the
memory-diagnostic tooling a DAT-based system needs. It manages physical
address space in fixed 2K blocks (matching a 2K mapping-RAM granularity),
numbered sequentially:

- **Address-decoding test**: writes a block's own number into it at every
  extended address alias, checks nothing else got clobbered.
- **Convergence test**: writes/verifies a pattern then its complement
  across 256 passes per block, shifting the pattern each pass, to exercise
  every bit combination at every address.
- **Unattended overnight/weekend mode**: runs all diagnostics in sequence,
  stops only on error.
- **Blocks 0-3 can't be marked bad/excluded** — a physically defective
  chip there prevents boot; the chip must be replaced.
- **Auto-detects standard-ACIA vs. intelligent I/O board configurations**
  via a jumper-selectable Task Select Register bit — a Level 2 boot ROM
  commonly needs to probe hardware variants before it can bring up a
  console at all.

---

**Sources:** OS-9 Level Two Operating System Manual; OS-9 Level Two System Designers Guide (Revision C, 1983) — the latter written explicitly for hardware designers building 6809 MMU boards, reflecting Microware's own consultation with Motorola on the MC6829's design. GMX III section: "OS-9 GMX III Support ROM User's Manual" Revision C (1983, Gimix Inc.).
