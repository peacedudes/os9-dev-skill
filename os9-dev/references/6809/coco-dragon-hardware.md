# CoCo/Dragon Hardware-Specific Reference

`Manual`. Scope: facts genuinely tied to specific 6809 hardware (Tandy Color Computer 1/2/3, Dragon 64/128), not generic OS-9/6809. If you're writing ordinary OS-9/6809 code with a glass-TTY terminal and no graphics hardware, most of this file doesn't apply to you - see `syscalls-and-module-format.md` and `assembly-and-tools.md` for what does.

The split matters: some 6809 OS-9 systems were plain serial terminals with no local graphics; CoCo and Dragon had built-in video/graphics hardware and a correspondingly larger set of OS-9-adjacent conventions for driving it. Treat this file as "if you're targeting this specific hardware," not "true of 6809 in general."

## VDG Text/Graphics Control Codes

Sent as raw bytes through the standard SCF output path (`I$Write`/`I$WritLn`) - there's no termcap/terminfo abstraction (see `unix-differences.md`); a program hardcodes these directly, same situation as any other pre-curses terminal programming.

**Alpha mode** (character ranges): `$00-$0E` cursor/screen control, `$20-$5F` uppercase, `$60-$7F` lowercase (displayed in reverse video - green on black), `$80-$FF` semigraphics block patterns.

| Code | Effect |
|---|---|
| `$01` | HOME (cursor to upper-left) |
| `$02 x y` | CURSOR XY (x,y each offset by 32) |
| `$03` | ERASE LINE |
| `$04` | ERASE TO END OF LINE |
| `$05 c` | ALTER CURSOR (cursor code) |
| `$06`/`$08`/`$09`/`$0A` | CURSOR RIGHT/LEFT/UP/DOWN |
| `$0B` | ERASE TO END OF SCREEN |
| `$0C` | CLEAR SCREEN, home cursor |
| `$0D` | RETURN (cursor to line start) |
| `$0E`/`$0F` | Switch to ALPHA / GRAPHICS mode (GRAPHICS takes mode+color bytes, allocates a 6K display buffer) |
| `$10 c` | PRESET SCREEN to color c |
| `$11 c` | SET COLOR (foreground + color set) |
| `$12` | QUIT GRAPHICS, return the 6K buffer |
| `$13` | ERASE GRAPHICS (erase screen) |

**Graphics mode** (separate cursor from the text cursor; coordinates 0,0 at lower-left, always positive):

| Code | Effect |
|---|---|
| `$14` | Home graphics cursor to (0,0) |
| `$15 x y` | Set graphics cursor position |
| `$16 x y` | Draw line from current position to (x,y), foreground color |
| `$17 x y` | Same as $16 in background color (erase) |
| `$18 x y` / `$19 x y` | Plot / erase a point |
| `$1A r` | Draw circle at current cursor, radius r |

Resolutions: two-color 256×192 (`G6R` mode), four-color 128×192 (`G6C` mode); CoCo 3 extends this considerably (see Window Types below). Color sets 1-2 (black/green, black/buff) work on any display; sets 3-4 are NTSC-only.

Extended text formatting (CoCo 3, via `$1F` prefix): reverse video `$1F20`/`$1F21` on/off, underline `$1F22`/`$1F23`, blinking `$1F24`/`$1F25` (alpha only), insert/delete line `$1F30`/`$1F31`. Graphics extensions (`$1B` prefix): scale, font, bold, proportional-spacing switches, plus absolute/relative point/line/box/bar/circle/ellipse/arc primitives and window/buffer management (`DEFINE GRAPHICS BUFFER`, `GET/PUT BLOCK`, etc.) - CoCo 3 / Multi-Vue specific, substantially expanding on CoCo 1/2's fixed two-mode display.

## Window Types (CoCo 3 / Multi-Vue)

`WCREATE /wN -s=<type> xpos ypos xsize ysize forecolor backcolor` - type 0 (32×16 VDG, needs the `VDGINT` module), 1 (40×24 text, 16 colors, 2K), 2 (80×24 text, 16 colors, 4K), 5 (640×192 2-color graphics, 16K), 6 (320×192 4-color, 16K), 7 (640×192 4-color, 32K), 8 (320×192, 16-color - the widest palette of the standard graphics types, a GIME-enhanced mode). Memory figures and column counts are `Live` (NitrOS-9) in `utility-usage.md`'s `wcreate -s=<type>` entry; treat that as the authoritative copy. Window numbers 8-15 available under Multi-Vue. `WMODE` reports/changes an existing window's attributes without touching its `XMODE`/`TMODE` settings. Vertical resolution is fixed at 192 pixels across every graphics type (5-8); only horizontal resolution and color depth vary. The `-s=` type code selects resolution and color depth together as a single value - there's no separate parameter for each.

Text window coordinates run 0-79 (column) by 0-23 (row), origin at the upper-left. Type 1 (40-column) windows are hard-limited to 40 characters across by the fixed character-cell size. Hardware text windows (types 1/2) render faster than graphics windows since they use dedicated character-cell hardware, but can't draw graphics primitives; graphics windows (5-8) support drawing/painting but render text more slowly since it's done in software. A graphics window's font (e.g. `sys/stdfonts`) must be merged into memory with `wcreate` before the window is created - VDG (32-column) windows don't need this step. Type 2 (80-column text) windows use a fixed 10-entry initial color palette that repeats: 0=white, 1=blue, 2=black, 3=green, 4=red, 5=yellow, 6=magenta, 7=cyan, then wraps (8=white, 9=blue) - a `wcreate` color argument above 9 maps back into this same cycle rather than erroring.

Window-specific error codes (additive to the universal `E$` range in `common/error-codes.md`, not a contradiction of it): 183 Illegal Window Type, 184 Window Already Defined, 185 Font Not Found, 189 Illegal Coordinates, 190 Internal Integrity Check, 191 Buffer Too Small, 195 Illegal Window Definition, 196 Window Undefined, 220 Phone Hangup/Carrier Lost (RS-232, not window-specific but in the same extended range).

## Mouse/Joystick

`I$GetStt` function `$89` (`SS.Mouse`) returns a 32-byte packet: validity flag, active-port flag (0=off, 1=right, 2=left), timeout counters, per-button state/click-count/hold-time (A and B buttons), button-down X/Y snapshot, window-pointer-location code, resolution flag (low: 10×3, high: 1×1 ratio of physical movement to counts), absolute X/Y (always reported in the range 0-639 × 0-191 regardless of the resolution setting), window-relative X/Y (divide by 8 for character-cell position), screen-relative X/Y. Entry: `A`=path, `B`=`$89`, `X`=buffer, `Y`=port select (0=auto, 1=right, 2=left).

Plain joystick (non-window systems): X/Y each 0-63, fire button `$FF`=pressed / `$00`=released.

## Sound

**`Hearsay` throughout this section** - no manual documents CoCo/Dragon sound;
every address and bit layout below comes from retrocomputing web sources (see
the Sources footer). Weakest material in this file.

6-bit DAC on the same PIA chip pair as keyboard/joystick/cassette I/O, at `$FF20-$FF23` (`Manual, Flag` on naming it "PIA0" vs "PIA1"; the address range is unambiguous). `$FF20` bits 7-2 = DAC output value (0-63); `$FF23` bit 3 enables audio through an analog mux shared with cassette-input and cartridge `FSND` - only one of the three can be routed to the output at a time. A separate on/off-only bit (`PB1`) drives square-wave beeps without touching the DAC/mux. Same hardware on CoCo 3 and Dragon, no dedicated sound chip; CoCo 3's GIME adds programmable timers at `$FF92-$FF95` for more precisely-timed DAC updates. An optional "Speech/Sound Pak" cartridge (TMS7040, AY-3-8913, SP0256-AL2) existed as separate add-on hardware - register layout not covered by any source consulted here.

**No OS-9 sound driver/file-manager class exists** - unlike SCF/RBF, there's no audio-specific I/O category. A program hits `$FF20`/`$FF23` directly, same as BASIC, but must not disable interrupts to do it (safe for a single-tasking BASIC program, not for an OS-9 process sharing the CPU). `SOUNDRV2` (archived as `SOUNDRV2.LZH`) is a known freeware utility built around exactly this multitasking-safe direct-I/O approach - confirms the convention exists; its source wasn't read, so no specific register sequence beyond the above is attested from it.

## Screen Dump Utilities (CGSDUMP/BWSDUMP)

Two related utilities capture the active graphics buffer to a printer or file: `CGSDUMP` (color) and `BWSDUMP` (monochrome). Both need an active graphics mode with an allocated display buffer - dumping with no graphics mode active and no picture file given fails with error 246 (device not ready). Both support `-s <path>` to redirect the dump to a disk file instead of a printer. Vertical resolution is fixed at 192 pixels in every mode; `CGSDUMP`'s horizontal resolution is 128 pixels for most color options, with a subset of its ten color/option presets (indexed 0-9) extending to 256 pixels wide. `BWSDUMP` adds an inverse mode (`-i`, swaps black/white) and a reduced-size mode for the Tandy LPVII printer's smaller print area (`-7`, the only mode LPVII accepts). Between the two utilities, supported printers include the CGP-220 ink-jet and the LPVII/LPVIII/DMP series dot-matrix printers (via OS-9's bit-image graphics mode).

## Hard Drive Systems

A CoCo hard drive setup has four parts: power supply, drive(s), drive controller, and a Host Computer Adapter card (a.k.a. Hard Disk Interface Pak) - typically requiring a MultiPak Interface to attach, with rare exceptions. The controller presents as memory-mapped registers (address decoder into a CPU range like `$FF70-77`, a bidirectional data buffer, and Select/Read/Write/Register-Select control lines).

Three incompatible controller/encoding families, not interchangeable: **MFM** (older, lower density), **RLL** (higher density on the same physical media, but needs an RLL-certified controller - an MFM controller on an RLL drive only reaches about two-thirds of its rated capacity, and an RLL controller on an MFM drive risks corruption), and **SCSI** (controller logic built into the drive itself rather than a separate card; designed for peripherals generally, not just disks). **IDE drives are not compatible with the CoCo at all.** Capacity follows directly from geometry: heads × sectors/track × cylinders × bytes/sector (e.g. 4 × 32 × 306 × 256 ≈ 10MB). The Radio Shack CoCo Hard Disk Interface specifically uses a WD1010 controller and supports 10/15/30MB drives; its drivers ship as part of the OS-9 Level 1 Development Pak product.

Hard drives spin at 3600 RPM (12× a CoCo floppy's 300 RPM) with heads flying at 18 millionths of an inch or less above the platter - never move a running drive, since a head strike destroys data; most drives have a safe inner-cylinder landing zone, some auto-park.

## Serial (ACIA) Configuration

Via `TMODE`/`XMODE`'s `baud=` and `type=` parameters - these are two separate fields, not a baud/word-length/parity split across both: `baud=` alone packs baud rate, word length, *and* stop bits (bits 0-3 baud rate, bit 4 reserved, bits 5-6 word length, bit 7 stop bits); `type=` is the device-initialization byte, interpreted device-dependently. **For ACIA (serial) devices:** parity (bits 0-2): 000=none, 001=odd, 011=even, 101=mark, 111=space - per the OS-9 Technical Reference (Tandy), whose encoding table's 3-bit codes only fit in bits 0-2; bit 4 toggles auto-answer modem mode; bits 3, 5-7 reserved. `Manual, Flag`: the Radio Shack CoCo Level I manual instead labels this "bits 5-7 - Parity code" with no accompanying encoding table to check bit-width against - not reconciled here; confirm against real hardware or a live session before depending on either bit position. **For TERM (VDG) devices:** bit 0 toggles true-lowercase, bit 1 selects 32 vs. 80-column screen output. **Baud code** (bits 0-3 of `baud=`): 0=110, 1=300, 2=600, 3=1200, 4=2400, 5=4800, 6=9600, and then two *distinct* codes rather than one - `7`=19200 (ACIAPAK driver only) and `8`=32000 (SIO driver only), `Live` (NitrOS-9) in `6809/utility-usage.md`'s `baud=` row, which supersedes the manuals here. **Word length** (bits 5-6 of `baud=`): 00=8 bits, 01=7 bits. **Stop bits** (bit 7 of `baud=`): 0=1, 1=2.

**Serial hardware:** the stock Tandy Modempak (a ROM cartridge, obsolete by the mid-1990s) has a built-in 300-baud modem and RS-232 port with no hardware handshaking - any modem speed above 9.6K baud needs handshaking support the Modempak's port doesn't provide, so upgrading just the modem chip doesn't help. The separate RS-232 Pak (harder to find than the Modempak) supports up to 14.4K baud for modem use and 19.2K for a direct terminal connection. Default printer baud rate is 600; most printers accept far higher, but raising it isn't strictly linear - too-high a rate can paradoxically slow printing, so the practical rate for a given printer/cable is usually found by testing with `xmode`, not assumed from the printer's rated maximum. None of this applies to a parallel-port printer - parallel transfer has no baud rate, so `tmode`/`xmode` baud settings are simply ignored for it.

**Multi-user terminals:** OS-9 supports up to three external keyboard/monitor pairs (`T1`/`T2`/`T3` device descriptors) attached to one CoCo simultaneously - real multi-user capability, not just multi-tasking a single console. In practice, though, additional terminals visibly slow down the primary user under heavy CPU or disk load, since it's still one 6809 sharing cycles across every session. `T1` is the CoCo's built-in ("Bit Banger") RS-232 port, generally considered unreliable; `T2` maps to the Deluxe RS-232 RomPak cartridge specifically; third-party serial cards need their own `T2`-compatible driver module installed via `OS9GEN`.

**PIPE descriptor:** a virtual (memory-only) device used for inter-process data transfer between utility programs, with no disk I/O involved - the standard way command pipelines move data under OS-9's shell.

## Monitor and serial tuning utilities

Command syntax/options for `montype`/`tuneport`: `6809/utility-usage.md` -
not repeated here. Hardware-specific context: `MONTYPE`'s r/c/m
selection affects sync/color-burst generation on the CoCo's video
hardware, not just a cosmetic display setting; `TUNEPORT` targets the
printer (`/p`) or terminal (`/t1`) port's baud-rate delay loop
specifically.

## Disk (DMODE)

`DMODE drv=n stp=n typ=n dns=n cyl=n sid=n vfy=n sct=n ilv=n sas=n` reconfigures a drive descriptor: step rate (00=35ms ... 03=6ms), drive type (20=5.25" CoCo format), density (1=40 TPI, 3=96 TPI), cylinder count (23=35 track, 28=40 track, 50=80 track), write-verify on/off, sectors/track (12=18 decimal), interleave (normally 3, 2 on newer drives). Standard CoCo Level 1 floppy: double-density, single-sided, 35 tracks × 18 sectors × 256 bytes, 1 sector/cluster (≈157KB total).

Named drive descriptors follow a `Dx_NNs` convention: 35-track single-sided (`D0_35S`...`D3_35S`, the original CoCo drive spec, kept mainly for compatibility with older systems), 40-track double-sided (`D0_40D`...`DDD_40D` - `DDD` being the default-drive variant), and 80-track double-sided (`D1_80D`, `D2_80D`). Only 35-track and 40-track have a ready-made `DDD` default descriptor; there's no stock 80-track default - making an 80-track drive the boot default means cloning and editing an existing descriptor with `dmode` yourself. Most modern (post-1983) floppy mechanisms handle a 6ms step rate fine even though descriptors default to a conservative 30ms for compatibility.

**Boot List Order Bug ("BLOB"):** the order device drivers/descriptors appear in an `OS9Boot` file can itself cause boot failure - a bad ordering can misallocate memory and produce error 207 or 237, or simply fail to boot, with no other symptom pointing at "reorder the boot list" as the fix. Known by that name in the CoCo OS-9 community; not documented as a defect anywhere formal, just a practical gotcha when hand-building a boot file.

## Monitors and Memory

Composite monochrome gives the sharpest text but no color; RGB unlocks full color at real cost premium over composite. The CoCo's sync output is positive; an Atari-ST-style monitor (negative sync) needs the pulses inverted to work, and some Sony multisync monitors need the two sync signals combined and inverted (doable with a single NOR gate). IBM-style TTL monochrome monitors are flatly incompatible, not just lower quality.

A full CoCo 3 + OS-9 Level 2 + windowing setup needs at least 512K of RAM. Error #207 or #237 during operation doesn't necessarily mean memory is full - it commonly means a single request needs more than 64K of *contiguous* memory, which more total free RAM elsewhere can't fix if it's fragmented into smaller pieces.

## Keyboard Quirks

- CoCo 1/2 have no separate Ctrl key - **CLEAR acts as Ctrl**.
- **Ctrl+0** toggles shift-lock state - CoCo-specific, absent from the general control-key table.
- Every other shell control key behaves unmodified (Ctrl-E abort, Ctrl-C interrupt-to-background, ...) - `unix-differences.md` Tier 1.

## OS9Boot Module Differences

- **CoCo 3**: `CC3IO` (keyboard/video driver), `WindInt`, `VDGInt`, `CC3Disk`, `CC3Go` (startup process, sets up initial shell, inherits boot user ID).
- **Dragon 64**: `KBVDIO`, `DDisk`, `SYSGO` - thinner extraction than CoCo; Dragon-specific material in the source library was sparse, mostly "same shape as CoCo, different driver module names." Treat any Dragon-specific claim here as lower-confidence than the CoCo material until a Dragon-focused source is found.

## Boot Configuration & Patching Tools (CoCo-specific)

OS-9 allocates memory to loaded modules in 8K blocks regardless of a module's actual size - a merged file under 8K wastes nothing, but splitting related modules across separate loads costs a full block each. This is why the standard shell (just under 8K on its own) is typically merged with other frequently-used commands up to, but not past, the 8K boundary. Two tools rebuild a merged `OS9Boot` file after editing which modules it contains: **`COBBLER`** copies the in-memory (already-patched) boot image to disk, preserving any live patches; **`OS9GEN`** instead builds fresh from a module list read from disk, so it does *not* pick up in-memory changes. `MODBUSTER` (public-domain, D.P. Johnson) does the reverse of merging - it splits a merged `OS9Boot` back into individual module files.

Direct binary patching of a resident module's bytes is done with `MODPATCH`, either interactively or by feeding it a command script (`MODPATCH scriptfile`): `L` links/loads the target module, `C <offset> <hexbytes>` changes bytes at an offset, `V` re-verifies the module's CRC afterward (required, since a hand-edited module's CRC would otherwise no longer match). Two patches specific to boot-time device descriptors: disk drive descriptors default to a conservative 30ms step rate for compatibility - changing byte 14 (decimal) from `$00` to `$03` drops this to 6ms, which most drives handle fine and noticeably speeds up floppy access; and an OS-9 Level 1 module can be made Level-2-compatible by changing byte 14 from `$FF` to `$07`. `EasyEdit` is a friendlier alternative specifically for device descriptors - it prompts for the same parameters (step rate, track count, sides, verify) and writes the change back directly, without needing `MODPATCH`/`DEBUG`/`COBBLER`/`OS9GEN` at all.

### Host-Side Disk Editing (ToolShed) - `Live` (NitrOS-9)

All the tools above run *inside* a booted OS-9 session. **ToolShed**
(`boisy/toolshed` on GitHub, actively maintained, open source) is a modern
host-native replacement: its `os9` command reads and writes OS-9 RBF disk
images directly as files on a Mac/Linux/Windows machine, no emulator boot
required. It covers the same ground as the classic Radio Shack OS-9
Development System tools (`dir`, `copy`, `del`, `makdir`, `free`, `dcheck`,
`format`, `gen` for bootstrap-track generation, `ident`/`dump` for module
inspection) plus host-filesystem transfer. Builds cleanly on macOS with
the system `cc` if you skip `cocofuse` (the only piece needing FUSE).

**Path syntax**: `os9 <cmd> imagefile,path/inside/image` - the comma
delimits a host path from a path inside the disk image; a bare trailing
comma means the image's root directory. `copy -l` performs CR<->LF
translation for text files (OS-9 text uses bare CR, not CRLF/LF); `copy
-r` overwrites an existing file. `attr` (get/set OS-9 file attributes)
only operates on paths *inside* a disk image (`imagefile,path`) - it
cannot be pointed at a plain host file, since a host file has no OS-9
attribute byte to read or set at all.

**Copying in an executable module leaves it non-executable - a real
gotcha**: `os9 copy` does not set the execute-permission bit on the file
it creates inside the image, even for a compiled module. The kernel's
`load` utility (and `link`) enforce that bit - attempting to `load` a
freshly-copied module fails with error 214 (`EOS_FNA`, "no permission"),
which is easy to misdiagnose as `load` itself being broken (its own
minimal size in some kernel builds, ~36 bytes, doesn't help that
impression - but the utility is fine). The fix: `os9 attr -e -pe
imagefile,path/to/module` immediately after copying any module you intend
to `load` or `link` at runtime, granting execute to both owner and
public. Also note `load`/`link` resolve a bare module **name**, not a
path - `load scdwv.dr` works if `CMDS` is on the exec-directory search
list; `load CMDS/scdwv.dr` fails (error 216, `EOS_PNNF`) since that's not
how these utilities expect their argument.

**`dir -e` can silently under-report; plain `dir` is the complete list** -
`Live` (ToolShed), i.e. `os9 dir` host-side, not the guest's own `dir`. On a disk carrying damaged
file-descriptor sectors (`os9 dcheck` counts them), the extended listing walks
each entry's FD and quietly stops short: one directory listed 56 entries under
`dir -e` and 68 under plain `dir`, and the two sets were *different* - the 12
`-e` never showed were not a tail it truncated, they were files it skipped
past. Nothing in the output says it gave up. So build any name list from plain
`dir` and use `-e` only to decorate names you already have; and if the two
disagree, run `dcheck` before trusting anything else on that disk.

**`deldir` cannot delete an *empty* directory - `Live` (ToolShed).** It fails with
ToolShed's own error 192 (not an OS-9 code) on any directory with no deletable
entries, including one you just emptied. The cause is visible in
`librbfdelete.c`: the directory is opened `FAM_READ`, and only the per-entry
loop body reopens it `FAM_WRITE` - so on an empty directory the final
`_os9_ss_fd` that clears the directory attribute runs against a read-only path,
never clears it, and the delete of a still-`d` file fails. Workaround: copy any
one-byte file in, then `deldir -q`, which deletes the dummy and the directory
together. `-q` is required non-interactively at all times - without it `deldir`
prompts, and a prompt reading EOF fails the delete. `attr` is no help here: it
has no flag for the directory bit.

**A failed `deldir` still writes to the image.** It deletes entries as it goes
and only reports the error it hit at the end, so an image that saw a failed
`deldir` is in an undefined state - discard it and re-extract, never keep
working on it.

**`del` succeeds on entries `copy` and `fstat` refuse with 214.** Damaged or
permission-less directory entries can be unreadable yet still deletable, which
is what you want during a cleanup - don't conclude an entry is stuck just
because you cannot read it.

**Container vs. raw-RBF caveat**: `os9` expects a raw RBF filesystem
starting at byte 0 (a standard `.dsk` floppy image is this). Some
distributed images - e.g. XRoar's own `.ide` hard-disk container format -
wrap the real filesystem behind an emulator-specific header and/or
partition table. Pointing `os9 dir` straight at such a file fails with
error 216 (`EOS_PNNF`): not a broken tool, just the wrong byte offset.
Check the image's own documentation for its header/partition layout, then
carve out the real filesystem with `dd if=container of=raw.img bs=512
skip=<sectors>` before handing it to ToolShed, and write changes back with
`dd if=raw.img of=container bs=512 seek=<sectors> conv=notrunc` -
`conv=notrunc` is essential, since a plain `dd of=` truncates the
container to the partition's size. Sanity-check the extraction: an RBF
LSN0's first 3 bytes are a total-sector count that, times the sector size
(256 bytes for RBF), should equal the extracted file's exact byte size.

**Why this matters for autonomous testing**: because it works without
booting anything, this is the fastest way to inspect or edit a NitrOS-9
disk's `STARTUP` procedure file, kernel module list, or any other file -
including removing an interactive prompt (e.g. a `setime` call whose
input/output is redirected onto the console, `setime<>>>/1`) that would
otherwise block an unattended boot indefinitely, no matter how carefully
timed the injected keystrokes are.

**`setime`'s interactive prompt format** - `Live` (NitrOS-9): when no real-time clock
module is present, `setime` (with no arguments) prints `>> No Clock module found
<<` then repeatedly prompts `Time ?` expecting an answer in
`yyyy/mm/dd hh:mm:ss` format (4-digit year, space between date and time,
no comma). Whether an `a`/`p` AM/PM suffix or 24-hour military time is also
accepted here is unverified. The non-interactive argument form is more
forgiving - it takes space, colon, semicolon or slash delimiters, freely
mixed (`6809/utility-usage.md`).

---

**Sources:** Radio Shack/Tandy Color Computer OS-9 Level I manual (1983), OS-9 Operating System Users Guide (CoCo/Dragon 64), OS-9 Technical Reference (Tandy), OS-9 Quick Reference for the Tandy Color Computer (FARNA Systems, 1992). **The Sound section rests on no manual at all.** No primary-manual sound
documentation was available, so it is drawn from retrocomputing web sources:
CoCopedia's hardware/audio pages, 6809.org.uk's Dragon hardware reference,
Chris Lomont's "Color Computer 1/2/3 Hardware Programming," cococommunity.net's
GIME chip reference, and community references to the `SOUNDRV2` OS-9 utility
archive. These are hardware facts (addresses, bit layouts) cross-referenced
across several independent sources, but by this skill's own legend that is
`Hearsay`, not `Manual` - neither manual-derived nor run. Treat the whole
section as the weakest material in this file and confirm against hardware
before depending on it.
