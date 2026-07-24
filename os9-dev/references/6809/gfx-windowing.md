# 6809 BASIC09 Graphics: GFX and GFX2

Reference for BASIC09's two CoCo/Dragon graphics subroutine packages, invoked
via `RUN GFX(...)` / `RUN GFX2(...)`: `GFX` is the Level 1 low-resolution VDG
package, `GFX2` is the Level 2 high-resolution graphics/windowing package.
Built from the Level 2 Operating System Manual's GFX/GFX2 chapter and
cross-checked against an independent second OCR of the same appendix
reprinted in the Tandy BASIC09 Reference Manual. Both sources are
OCR-scanned and locally dirty — curly quotes, `l`/`1`/`I`, and `O`/`0`
routinely garble, and the module name itself is misOCR'd in most of the
Tandy source's worked examples (`GEX2`, `GEN2`, `GEXA`, etc.). Where the two
sources agreed it's `Manual`; disagreements are tagged `Manual, Flag`
inline rather than silently picked. Most of this content has not been run
against a real system — a text REPL cannot observe a screen, so this file
has stayed `Manual` for most claims. **That constraint is now lifted:**
`6809/reading-the-coco-screen.md` describes a working screenshot + keystroke
path (`tools/cocoscreen.sh`), so visual claims here are verifiable and should
be promoted to `Live` as they are checked. Note one already-corrected error
below: SELECT is windint `$1b21`, and an earlier "confirmation" of its
deferral behavior was invalid because it used `$1b22` (`WOWSet`) by mistake —
the deferral claim remains **unverified**.

**2026-07-18, the BASIC09 calling sequence is `Live`.** Driving real
`RUN GFX2(...)` calls (not just the windint escape codes underneath them)
confirmed the documented **argument order and arity** for `DWSET` (nine
parameters after the path), `SELECT`, `COLOR`, `LINE`, `BOX` and `CIRCLE`,
and that the path-as-first-argument form works. Harness: `tools/b09run.sh`
in the os9exec repo. **Assume no argument validation anywhere in this file** —
`LINE` at x=639 on a 320-pixel-wide screen is accepted silently, matching the
earlier `PALETTE` result (register 99, color 200 also accepted). Bad
coordinates fail silently, never diagnosably.

**2026-07-18, first pixels actually observed.** A box and a circle were drawn
on a `wcreate`d 320x192 4-color window and photographed. First result:
**the X coordinate range claims below are suspect.** Y behaves as documented,
X does not — a box spanning the nominal `(0,0)`-`(639,191)` space filled the
full height but only about half the width, and a radius-64 circle came out
markedly wider-than-tall in the wrong direction. Either drawing clips at the
device window's pixel width or X is scaled; mechanism not yet established, so
nothing here is re-tagged `Live` yet. Method and the exact next experiment:
`test/6809-live-verification/dogfood-gfx-pixels-2026-07-18.md` (os9exec repo). **2026-07-18**: the community-maintained
`gfx.asm`/`gfx2.asm` package (this project's own copy, at
`os9/nitros9/source/3rdparty/packages/basic09/`) was built with `asm`
and installed on the live NitrOS-9 test disk for the first time,
unblocking `Live` testing of the non-visual bookkeeping/error-behavior
claims below (still not pixel output itself — see the "Open ends"
section for what that testing found). Notation: `[..]` optional, `{..}`
repeatable.

**2026-07-19, visual confirmation pass completed for the remaining known-
accepted calls.** `DRAW`'s polyline, `GET`/`PUT` block copying, `LOGIC`'s
raster op, `PATTERN`, and `FONT` are all now `Live` below, along with the
`OWSET`/`OWEND` overlay family (`OWSET` confirmed as documented; `OWEND`'s
restore did **not** reproduce, twice, on two window geometries — a real
black-box finding about NitrOS-9's own windowing driver, not an `os9exec`
bug) and `CWAREA` (resolved: character-grid units, matching `OWSET`;
2026-07-18's "black band" was almost certainly a wrong-byte-width guess in
a hand-driven raw escape, not a real defect). Level-1 `GFX`'s lower-left-
origin claim stays `Manual` — its `MODE` call is accepted but never produced
a screen reachable through this NitrOS-9 build's CLEAR-cycle mechanism
across three different output-routing attempts, an environment limitation
rather than a falsified claim. Full detail on all of the above:
`test/6809-live-verification/dogfood-gfx-pixels-2026-07-18.md` in the
os9exec repo.

## GFX (Level 1 low-resolution VDG graphics)

Loading: `GFX` must be in the execution directory or already resident;
BASIC09 auto-loads it on the first `RUN GFX(...)` call, or it can be
preloaded with `LOAD`. Once loaded it stays resident until removed with
`UNLINK` (OS-9 shell) or `KILL` (BASIC09).

- `RUN GFX("MODE",format,color)` — switches from text to graphics screen;
  must be called before any other GFX function. `format` `0` = 256×192,
  2 colors; `1` = 128×192, 4 colors. Allocates a 6KB memory block; errors
  if unavailable. Coordinate origin (0,0) is the **lower-left** corner, all
  coordinates positive. A separate invisible "draw pointer" starts at 0,0;
  some functions (`LINE`) move it as a side effect, tracked independently
  of anything visible on screen. **Attempted `Live`, origin
  claim still `Manual` — for a documented reason, not an oversight.**
  `RUN GFX("MODE",0,1)` plus two `LINE` calls forming an "L" anchored at
  `(0,0)` was accepted with no error (confirmed by stray control-byte
  fragments leaking into whatever text channel served as output), but never
  produced a screen reachable by CLEAR-cycling, tried three different ways
  of routing the call's output (`GFX`, unlike `GFX2`, takes no `path`
  argument, so it always draws to the calling process's own default
  output): backgrounded with stdout to `/nil`, held open in the foreground
  on the process's default DriveWire stdout, and with `basic09`'s own
  stdout explicitly redirected to a real `/wN` window at invocation. All
  three left only the pre-existing text/window screens reachable — no new
  graphics screen ever appeared, on the same disk where GFX2 windows work
  reliably. Reads as a genuine incompatibility between Level-1 GFX and this
  NitrOS-9 build's Level-2/windowed environment (see "Reaching a specific
  window's screen" in the test report below), not evidence for or against
  the lower-left-origin claim. Full detail:
  `test/6809-live-verification/dogfood-gfx-pixels-2026-07-18.md` in the
  os9exec repo.
- `RUN GFX("ALPHA")` — switches to the text screen; the graphics screen
  stays intact in memory (can switch back).
- `RUN GFX("QUIT")` — switches to the text screen **and** deallocates the
  graphics memory (unlike `ALPHA`, this is a one-way trip).
- `RUN GFX("CLEAR"[,color])` — clears to `color`, or to the current
  background color if omitted; also resets the graphics cursor to 0,0.
- `RUN GFX("COLOR",color)` — changes the foreground color, and may switch
  the current color set (BASIC09 divides GFX's palette into color sets; a
  code outside the current set auto-initializes the new one). Does not
  touch graphics format or cursor position.
- `RUN GFX("POINT",xcor,ycor[,color])` — plots a dot; uses the current
  foreground color if `color` omitted.
- `RUN GFX("LINE"[,xcor1,ycor1],xcor2,ycor2[,color])` — draws from the
  draw pointer if the start point is omitted, else from the given start to
  the given end; always leaves the draw pointer at the endpoint.
- `RUN GFX("CIRCLE"[,xcor,ycor],radius[,color])` — centers on the draw
  pointer if coordinates omitted. X range 0-255, Y range 0-191 — out of
  range errors.
- `RUN GFX("MOVE",xcor,ycor)` — repositions the draw pointer only; no
  visible effect.
- `RUN GFX("JOYSTK",stick,fire,xcor,ycor)` — `stick` `0`=right, `1`=left;
  `fire` is an output variable (byte/integer/boolean; nonzero/`TRUE` =
  pressed); `xcor`/`ycor` are output variables, range 0-63. Standard
  joystick or mouse only — does not work with the high-resolution mouse
  adapter.
- `RUN GFX("GLOC",storage)` — writes the graphics screen's memory address
  into `storage` (integer/byte variable), enabling direct `PEEK`/`POKE`
  access for effects GFX itself doesn't expose (area fill, saving a screen
  to disk). Needs ≥8KB free in the user's address space to map the screen
  in; total program+data memory must stay ≤56KB while doing this.
- `RUN GFX("GCOLR",[xcor,ycor,]color)` — reads a pixel's color into
  `color` (an integer or byte variable): at the draw pointer if
  coordinates are omitted, or at the given `xcor,ycor` if given. Resolved
  from the BASIC09 Reference Manual Rev G, whose own detailed entry gives
  both call forms directly (`GCOLR`, not `GCOLOR` — the Level 2 manual's
  quick-reference table abbreviates it that way too; the primary GFX
  chapter itself never printed a full syntax line for this one).

## GFX2 (Level 2 high-resolution graphics/windowing)

### Concepts shared across GFX2 functions

- General call form: `RUN GFX2([path,]"FUNCTION",params...)`. `path` is
  optional on nearly every function — omit it to operate on the current
  window. **Exceptions with no `path` parameter at all:** `DEFBUFF`,
  `GPLOAD`, and `GCSET` — these operate on buffer/cursor storage that
  isn't window-scoped.
- Drawing coordinates use a 640×192 grid (X 0-639, Y 0-191). Text-cursor
  coordinates (`CURXY`, `DWSET`'s `xcor`/`ycor`) are column/row units
  relative to the window's own character grid, not pixels.
- Two independent cursors exist: the **draw pointer** (invisible, used by
  graphics functions, starts at 0,0) and the **text cursor** (used by
  cursor-movement functions). `LINE` updates the draw pointer to its
  endpoint as a side effect; `BOX` and `BAR` explicitly do **not** move it.
  `SETDPTR(path,xcor,ycor)` sets the draw pointer explicitly — anything
  that omits its own coordinates (bare `CIRCLE`, `LINE` with only an end
  point) starts from wherever the draw pointer currently is. Coordinates
  are screen-relative unless `SCALESW` is off, in which case they become
  relative to the window's own working-area origin.
  **`Live` — substantially correct, but incomplete in a way
  that misleads.** "Screen-relative" is right: with scaling **on** (the
  default) a coordinate is in the **screen's** pixel space and is then
  **rescaled into the device window**, not clipped to it. The scale factor is
  therefore `window_width / screen_width`:

  | Window | Screen | Coordinate → window pixel |
  |---|---|---|
  | 320px, 40 col | 640px (type 5) | ÷2 |
  | 320px, 40 col | 320px (type 6) | 1:1 |

  Measured both ways: on the type-5 window, lines at x=0/160/320/480/639
  landed at window columns 40/120/200/280/359 (exactly x/2) and a
  40-character text row spanned the identical width; on the type-6 window a
  `BOX` at x=20..200 landed at offsets 20..200 (1:1). With `SCALESW`
  **off**, coordinates become **literal window pixels** and drawing **clips
  at the window edge** — x=320/480/639 simply vanish on a 320-wide window.

  **The practical trap is the "0-639" range** quoted throughout the entries
  below: that is the coordinate range of a *640-wide* screen type (5 and 7).
  On a 320-wide screen type (6 and 8) the meaningful range is 0-319. Nothing
  rejects a larger value — `LINE` at x=639 on a 320-wide screen returned no
  error (consistent with GFX2's general lack of bounds checking) — so
  out-of-range coordinates fail silently rather than diagnosably.

  Still untested: the origin half of the claim. Both test windows sat at
  0,0, where window- and screen-relative origins coincide.
- **Window/screen format codes** (used by `DWSET`'s `format` and
  `GPLOAD`'s `format` parameters) are small integers. `Manual`, but
  cross-referenced against a `Live` table: this manual's own Table 9.6
  (memory-requirement listing) matches `wcreate`'s `-s=<type>` table in
  `utility-usage.md` (`Live` there) exactly on byte counts and
  resolution/color combinations: `1` = 40-column text (2K), `2` =
  80-column text (4K), `5` = 640×192 2-color graphics / 80-column (16K),
  **`Live` — column counts confirmed** by what `wcreate`
  accepts: `-s=6` and `-s=8` take 40 columns but reject 80 with
  `Error #189 Illegal Coordinates`, while `-s=7` takes 80. Type 5's screen
  also measured **640 pixels wide** directly (a 40-column window covered
  exactly its left half). Practical consequence: a `-s=8 0 0 80 24` request
  is 80 columns on a 40-column screen — error 189 there is correct and means
  bad geometry, not memory exhaustion.
  `6` = 320×192 4-color graphics / 40-column (16K), `7` = 640×192
  4-color graphics / 80-column (32K), `8` = 320×192 16-color graphics /
  40-column (32K). GFX2's own use of the codes hasn't itself been
  independently confirmed `Live` (only `wcreate`'s has). Two additional special
  values exist only for `DWSET`'s `format` (not `wcreate`'s `-s=<type>`,
  which always creates a new window and has no "current screen" concept):
  `$00` = the calling process's current screen (inherit its format rather
  than specifying a new one), `$FF` = whatever screen is currently
  displayed — the primary source restricts `$FF` to procedure files that
  intentionally stack more than one window onto a single shared display
  (Level 2's merged-windows/devices model, see `utility-usage.md`'s "Level
  1 vs Level 2" note); ordinary programs should target their own current
  screen instead.
- **Palette:** 64 total colors exist; the CoCo3 palette hardware holds 16
  at a time across registers 0-15, each loaded with a color value 0-63.
  Register 0 = window/screen border, register 2 = background, register 3 =
  foreground (per the primary source's Table 9.7). Default color-register
  assignments beyond black/red/green/yellow/blue/magenta/cyan/white
  (registers 0-7) weren't cleanly recovered by either OCR pass.
- **Typical window lifecycle from BASIC09:** `DIM` a path-number variable,
  `OPEN` a path to the window device, `SELECT` the new window, read/write
  through the path, then `CLOSE` (and `SELECT` back to the original window
  if still needed — skippable if staying in the new window). A window
  created this way via `OPEN` disappears automatically when its path
  closes; for a window that should outlive the path, run `SHELL "INIZ
  /window"` first to initialize the device independently before `OPEN`.

### Window management

- `DWSET(path,format,xcor,ycor,width,length,fg,bg,border)` — defines a
  device window: `format` is the screen-type code (see above), `xcor`/
  `ycor` are the upper-left corner in character columns/rows, `width`/
  `length` are the window's size in characters/lines, `fg`/`bg`/`border`
  are palette register numbers. Typically run right after opening a path
  to the window.
- `DWEND(path)` — tears down a window `DWSET` created; once no device
  window remains on a screen, its memory goes back to the system pool.
  Display jumps to whatever device window comes next, the same effect a
  CLEAR keypress has. A common pattern is calling `DWSET` again right
  after, to reuse the same path for a window of a different type.
- `DWPROTSW(path,switch)` — OS-9's CoCo3 windowing is protected by default
  (windows can't overlap); `switch` `OFF` removes that protection for one
  window so others can be placed over it, `ON` restores it (the default).
  **GOTCHA:** removing protection can destroy the unprotected window's
  contents when something else draws over it — use with care.
- `OWSET([path,]save_switch,xpos,ypos,xsize,ysize,fg,bg)` — establishes an
  overlay window on top of an existing device window (same size or
  smaller). `save_switch` `0` = don't preserve the covered area, `1` =
  save it and restore it when the overlay ends. `xpos`/`ypos` = character
  column/row of the overlay's upper-left corner; `xsize`/`ysize` = its
  width/depth in characters; `fg`/`bg` = its initial colors.
  **`Live`** — `xpos`/`ypos`/`xsize`/`ysize` confirmed as
  character-grid units (matches `CURXY`/`CWAREA`): `OWSET(1,5,3,20,8,2,1)`
  over an existing full-color `BAR` punched a rectangular hole at character
  column 5, row 3, sized 20×8, filled with the overlay's own `bg` register
  immediately on the call — no further drawing needed to see it.
- `OWEND` *(no `path` — see Open ends)* — deallocates an overlay window
  created with `OWSET`, restoring the previous screen contents if they
  were saved. No source checked ever prints a formal `Syntax:` line for
  this call, but five independent worked-example occurrences across two
  manuals all invoke it bare, `RUN GFX2("OWEND")`, never with a `path` or
  any other argument — consistent enough across independent sources to
  treat as the real call shape, not just an inference.
  **`Live` — call shape confirmed, but the documented restore
  did not reproduce.** `RUN GFX2("OWEND")` right after the `OWSET` above
  left the punched-out area still background-colored — the original bar
  content underneath was not restored, contradicting "restoring the
  previous screen contents if they were saved." Varied twice before
  reporting this: a `save_switch=0` control on the same geometry never
  erased the area in the first place (so, consistently, nothing needed
  restoring), and the same `OWSET(1,...)`+`OWEND` sequence reproduced
  identically on a type-7 (640×192, 80-column) window with proportionally
  scaled parameters. Both calls' arity is independently confirmed correct
  (foreground `PRINT`-marker pass, no errors) — it's specifically the
  restore behavior that's suspect. No `windint` source is available in
  this repo to check the real implementation the way `LINE`/`LINEM` was
  settled from `gfx2.asm` itself, so this is a black-box finding about
  NitrOS-9's own CoCo3 windowing driver — not an `os9exec` bug, since
  `os9exec` only runs the 6809 code and has no windowing logic of its own.
  Full detail:
  `test/6809-live-verification/dogfood-gfx-pixels-2026-07-18.md`.
- `SELECT([path])` — makes a window the active display target; if
  omitted, defaults to the standard input/output/error paths (0/1/2).
  Whether the switch is visible right away depends on which window the
  calling code is currently running from — from inside the window being
  switched to, it shows immediately; from elsewhere, the switch is
  deferred and only takes visible effect on the next CLEAR keypress.
  **`Live` — necessary, but not sufficient.** Two results, and
  the second corrects a first impression:
  - It does **not** display the window by itself. Writing `WSelect` ($1b21)
    to a window changed nothing, including when the writing process had
    *all* its std paths on that window (`display 1b 21 <>/w4`). A CLEAR
    keypress is still needed to bring the screen forward.
  - But it **is required**. A backgrounded BASIC09 procedure that did
    `DWSET` and drew *without* calling `SELECT` produced a screen that
    could not be found by cycling at all — the drawing simply never became
    visible. Adding `RUN GFX2(p,"SELECT")` after `DWSET` made it appear
    (and then one CLEAR reached it).

  So: call `SELECT` after `DWSET`, and still expect to need CLEAR to
  actually see the screen. Omitting it loses the output silently.
  Commonly chained with `DWSET`/`DWEND`: open a path to a window, `DWSET`
  to configure it, `SELECT` to display it, draw, then `DWEND` + `CLOSE` to
  tear it down.
- `CWAREA(path,xcor,ycor,sizex,sizey)` — shrinks (never grows) the portion
  of a window that output is confined to; everything drawn afterward gets
  rescaled into that smaller region — graphics geometry and any placed
  images scale down with it, but text glyphs keep their original pixel
  size rather than shrinking too. **`Live`** — the parameters
  are character-grid units, the same convention as `OWSET`/`CURXY`, not
  pixels: `CWAREA(0,0,20,12)` on a 40×24-character window, followed by a
  `BOX` at the full nominal `(0,0)`-`(639,191)` range, rendered compressed
  into roughly the top-left half of the window, matching the 20/40 × 12/24
  = 50%/50% shrink exactly. An earlier session's raw-escape test of this
  call produced a corrupted "black band" and was read as a parameter-unit
  mystery; re-testing through the validated `RUN GFX2(...)` call path
  (letting `gfx2.asm`'s own encoder build the escape sequence instead of
  guessing byte widths by hand) resolved cleanly, so that result was almost
  certainly a wrong-byte-width guess in the raw escape, not a real defect.

### Drawing primitives

- `POINT([path,][xcor,ycor])` — sets one pixel to the current foreground
  color, at the draw pointer or at given coordinates.
- **`Live` — `LINE` does move the draw pointer, confirmed, but
  mind the layer.** windint has *two* line opcodes and they differ: `WLine`
  `$1b44` draws without moving the pointer, `WLineM` `$1b46` draws and moves
  it (verified live — a following bare `CIRCLE` centered on the line's start
  vs its end respectively). GFX2 exposes **only** the moving variant: its
  `FuncTbl` has no `LineM` name, and the registered `"Line"` points at the
  handler loading `#$46` (`gfx2.asm` L060D). So a raw-escape test of `$1b44`
  will look like it contradicts this entry — it doesn't; it's a different
  primitive.
- `LINE([path,][xcor1,ycor1,]xcor2,ycor2)` — from the draw pointer, or
  from a given start to a given end; always leaves the draw pointer at the
  endpoint (see "Concepts" above).
- `ARC([path,][mx,my],xrad,yrad,xcor1,ycor1,xcor2,ycor2)` — draws an arc
  centered at the draw pointer or at `mx,my`; `xrad`=`yrad` draws a
  circular arc, otherwise elliptical. The two coordinate pairs define an
  imaginary line **relative to the center as the origin** — the arc is
  drawn starting at the point closest to the first pair and ending at the
  point closest to the second; reversing the pair order flips which side
  of that line the arc is drawn on.
- `CIRCLE([path,][xcor,ycor,]radius)` — centers on the draw pointer if
  coordinates are omitted. X range 0-639, Y range 0-191.
- `ELLIPSE([path,][xcor,ycor,]xrad,yrad)` — same centering rule as
  `CIRCLE`; `xrad`/`yrad` are the horizontal/vertical radii.
- `BAR([path,][xcor1,ycor1,]xcor2,ycor2)` — filled rectangle between two
  diagonal corners; does not move the draw pointer.
- `BOX([path,][xcor1,ycor1,]xcor2,ycor2)` — rectangle outline, same corner
  convention as `BAR`; also does not move the draw pointer.
  **`Live`** — confirmed on all counts: `BOX` renders as an
  outline and `BAR` as a solid fill; after a box drawn (100,50)→(400,150) a
  following bare `CIRCLE` centered on (100,50), proving the draw pointer never
  moved. Bare `CIRCLE`/`ELLIPSE` centering on the draw pointer, and
  `ELLIPSE`'s separate x/y radii, are confirmed too.
- `DRAW(path,option_string)` — draws a polyline from a mini-language of
  direction codes and magnitudes in one string: `N`/`S`/`E`/`W`/`NE`/`NW`/
  `SE`/`SW` each followed by a distance (e.g. `N40`); `A<val>` rotates the
  drawing axis (`0`/`1`/`2`/`3` = 0°/90°/180°/270°); `U<xcor>,<ycor>` moves
  by a relative vector without changing the draw pointer; `B<xcor>,<ycor>`
  moves the same way but blanks (invisibly) — an offscreen `B` move hides
  whatever's drawn next. Options are separated by spaces or commas; a
  comma is specifically required between `B`/`U` and their coordinate
  pair. **`Live`** — `SETDPTR(50,50)` then
  `DRAW("N40E60S40W60")` rendered a clean closed rectangle outline,
  confirming the direction codes compose and the path closes correctly
  when the N/S and E/W magnitudes cancel.
- **`Live`** — `FCIRCLE`, `FELLIPSE`, `ARC` (8-argument form) and
  `FILL` all render as documented: the F-variants come out solid, `ARC` draws
  an arc, and `FILL` from a point inside a `BOX` outline fills it completely.
  Documented argument counts accepted in every case.
- `FILL([path,][xcor,ycor])` — flood-fills the connected region of
  same-colored pixels touching the draw pointer (or the given coordinates,
  which reposition the draw pointer first) with the current foreground
  color.

### Cursor and text functions

- `CURHOME(path)` — text cursor to 0,0 (window's absolute top-left).
- `CURXY(path,column,row)` — text cursor to a given column/row.
- `CURUP` / `CURDWN` / `CURRGT` / `CURLFT` `(path)` — move the text cursor
  one line/character in the named direction.
- `CUROFF` / `CURON` `(path)` — hide/show the text cursor.
- `SETDPTR(path,xcor,ycor)` — sets the draw pointer (X 0-639, Y 0-191 —
  the primary source's own copy showed "0-194" for Y, corrected here from
  the coordinate space every other function agrees on).
- `CRRTN(path)` — carriage return: cursor down one line, to the window's
  left edge.
- `INSLIN(path)` — inserts a blank line at the cursor, pushing the lines
  below it down one.
- `DELLIN(path)` — deletes the cursor's line and closes the gap (lines
  below move up). Works on both text and graphics screens.
- `ERLINE(path)` — deletes the cursor's line **without** closing the gap —
  this is the one difference from `DELLIN`.
- `EREOLINE(path)` — erases from the cursor to the line's right edge.
- `EREOWNDW(path)` — erases from the cursor down to the window's bottom.
- `REVON` / `REVOFF` `(path)` — reverse video on/off; a persistent state,
  not a per-call effect — stays in effect until the counterpart is called.
- `UNDLNON` / `UNDLNOFF` `(path)` — underline on/off, same persistent-state
  behavior as `REVON`/`REVOFF`. Default is off.
- `BOLDSW(path,"switch")` — `"ON"`/`"OFF"` bold typeface; **graphics
  screens only**, has no effect on hardware text screens. Default regular.
- `PROPSW(path,"switch")` — `"ON"`/`"OFF"` proportional character spacing.
  Default off.
- `BLNKON` / `BLNKOFF` `(path)` — character blink on/off. **Hardware text
  windows only** (`/W1`-`/W7`); no effect on graphics windows. `BLNKOFF`
  only stops *new* characters from blinking — characters already blinking
  keep blinking.

### Color and palette

- `COLOR(path,fg[,bg[,border]])` — changes any combination of foreground/
  background/border via palette register numbers; doesn't move the draw
  pointer. **GOTCHA:** changing a window's border color changes it for
  *every* window sharing that physical screen — border is a screen-global
  palette register, not a per-window setting.
- `DEFCOL(path)` — resets a window's palette registers to their default
  values (actual hues depend on `montype`).
- `PALETTE([path,]register,color)` — installs one of the 64 available
  colors into a given palette register. Re-checked directly against the
  primary source's own `PALETTE` section (parameters, function
  description, and example) — genuinely never states the register's
  valid numeric range anywhere in that section (presumably 0-15, matching
  the 16-register hardware limit noted under "Concepts" above, but not
  explicitly confirmed by any source checked). **`Live`**:
  this GFX2 build's client-side implementation performs **no range
  validation** on either `register` or `color` — calls with `register`
  up to 99 and `color` up to 200 (both far outside the presumed
  0-15/0-63 hardware ranges), including against a real, opened window
  path (`/W1`, not just the no-path default target), all executed
  without any OS-9 error, silently. Source-confirmed too: the handler
  only checks BASIC09's parameter *count* before writing the raw values
  out. The manual's presumed 0-15/0-63 ranges are therefore unenforced
  by software in this implementation, not merely undocumented — see
  Open ends for what this does and doesn't establish about the real
  hardware behavior.
- `BORDER(path,color)` — shorthand that sets palette register 0 (border)
  directly, equivalent to `COLOR`'s third argument.
- `LOGIC(path,"function")` — sets a persistent raster-op mode applied to
  every subsequent drawing call until changed: `"OFF"` (none), `"AND"`,
  `"OR"`, `"XOR"`. `XOR` is the one commonly used for toggle-effects (e.g.
  drawing and re-drawing the same shape to erase it without touching what
  else is on screen). **`Live` — real, but the erase-by-redraw
  idiom is unreliable for filled shapes.** Drawing `FCIRCLE(100,100,30)`,
  then `LOGIC "XOR"` and the identical `FCIRCLE` call again, did **not**
  cleanly erase back to background — it left a mottled residue with a
  visible seam, clearly different from a solid `LOGIC "OFF"` control circle
  drawn alongside it. The mottling is itself proof `XOR` is toggling real
  pixels (a no-op would just look like a second identical solid circle);
  the residue means `FCIRCLE`'s fill isn't pixel-identical between two
  calls (likely dithered for this color), so two XORed draws of the "same"
  filled shape don't fully cancel.

### Buffers, fonts, and the graphics cursor

- **`Live` — calling sequences accepted as documented** for
  `DRAW("N40E60S40W60")`, `BORDER(color)`, `CURXY(col,row)`,
  `LOGIC("XOR")`, `DEFBUFF(group,buffer,size)`,
  `GET(group,buffer,x,y,xsize,ysize)` and `PUT(group,buffer,x,y)`. Note
  `DEFBUFF` accepted an explicit `path` argument without complaint despite
  being documented as taking none — read "no path argument" as "does not
  require one". Visual behavior of these is not yet confirmed, only that
  the calls are well-formed.
- `DEFBUFF(group,buffer,size)` *(no `path` argument)* — allocates a
  Get/Put buffer for `GET`/`PUT`. `group` 1-199 (0 and 200-255 are
  reserved for OS-9 itself), `buffer` 1-255, `size` 1-8192 bytes. Each
  distinct `group` number costs a whole 8KB allocation (~30 bytes
  overhead, ~8162 bytes usable) regardless of how many buffers live in
  it — the manual recommends using your own process ID (obtainable via a
  `SYSCALL` "get ID" call) as the group number specifically to avoid
  colliding with another process's buffers. Persists until `KILLBUFF`.
  **`DEFBUFF`, double F, is correct** — `Manual`, re-checked directly
  against the primary source's own section header, its `Syntax:` line,
  and its index entry, all three of which independently agree; the Tandy
  cross-check's single-F reading was that source's own OCR error, not a
  real disagreement in the underlying text.
- `KILLBUFF(group,buffer)` — deallocates a Get/Put buffer.
- `GET(path,group,buffer,xcor,ycor,xsize,ysize)` — copies a window region
  into a Get/Put buffer (creating it automatically if not already defined
  via `DEFBUFF`; if the captured data would exceed an existing buffer's
  size, it's silently truncated to fit). `xcor`/`ycor` = upper-left corner
  of the region to save (X 0-639, Y 0-191); `xsize`/`ysize` = its
  dimensions.
- `PUT(path,group,buffer,xcor,ycor)` — draws a previously `GET`-saved
  image back into the window at `xcor,ycor` (its upper-left corner);
  dimensions come from what `GET` recorded, not from a parameter here.
  Repeated `PUT` calls at incrementing coordinates is the documented
  technique for simple animation — each call overwrites what the last one
  drew. **`Live`** — `FCIRCLE(50,50,20)`, `DEFBUFF(1,1,2000)`,
  `GET(1,1,30,30,40,40)`, `PUT(1,1,150,100)` produced two identical
  filled circles: the original plus a second copy at the `PUT` target,
  confirming both the capture and the block-copy.
- `GPLOAD(group,buffer,format,xdim,ydim,size)` *(no `path` argument)* —
  loads externally-prepared image data straight into a Get/Put buffer,
  the way `GET` does from a live window but from data supplied directly
  instead. `format` is a screen-format code (same family as `DWSET`'s).
  Creates the buffer if it doesn't exist yet; if it already exists, new
  data can't exceed the existing buffer's size.
- `PATTERN([path,]group,buffer)` — points subsequent drawing calls at a
  previously loaded Get/Put buffer to use as a repeating fill texture
  instead of a flat color, until turned off again with `group=0,buffer=0`.
  A pattern tile is 32×8 pixels; how many bytes that needs depends on the
  active screen's color depth (1/2/4 bits per pixel needs a 32/64/128-byte
  buffer) since the color mode dictates how many pixels each byte packs.
  **`Live`** — captured a hand-drawn 4-stripe 32×8 tile with
  `GET`, then `PATTERN(1,3)` before a `BAR`: the bar rendered as a
  repeating tiled texture, clearly distinct from a flat `PATTERN(0,0)`
  control bar drawn beside it. **Trap hit building this test:** an earlier
  attempt used `COLOR 1` for the fill and got nothing visible at all —
  register 1 was the window's own `bg` register from `DWSET`'s
  `fg,bg,border` triple, so foreground matched background. This
  same-register invisibility trap isn't unique to `PALETTE`'s unenforced
  ranges (see Open ends below); it bites any call whose foreground happens
  to match whatever `DWSET` assigned as background.
- `FONT(path,group,buffer)` — points BASIC09 at a buffer holding a custom
  character font; **graphics screens only**, no effect on hardware text
  screens. Three fonts ship built-in via `SYS/Stdfonts` (merge that file
  into the window first): **Group 200**, Buffers 1-3 — `Manual`, settled
  by re-reading the primary source's own descriptive paragraph directly
  (previously only its garbled numeric example had been checked), which
  states the group number in plain prose rather than digits, resolving it
  in favor of 200 over the earlier-flagged 206 misreading.
  **`Live`** — `FONT(200,3)` was accepted with no error
  *without* first merging `SYS/Stdfonts`, but the text it rendered was
  garbled repeating glyphs, visibly different from a normal
  `PRINT #p,"HELLO WORLD"` line drawn with the default font just above it
  on the same screen. Clean confirmation that "merge the file into the
  window first" above is a real, silently-unenforced prerequisite — GFX2
  happily points `FONT` at an unmerged/garbage buffer and draws whatever is
  there rather than erroring.
- `GCSET(group,buffer)` *(no `path` argument)* — defines a buffer as the
  graphics cursor's shape source; `group=0` disables the graphics cursor
  entirely. Requires merging `SYS/Stdcur` into the window before use.
- `PUTGC(path,xcor,ycor)` — plots the graphics cursor at `xcor,ycor`.
  Unlike most GFX2 functions, these coordinates are **screen-relative**,
  not window-relative. Built-in cursor shapes live in Group 202
  (`SYS/Stdptrs`); selecting which shape to use is done through a function
  called `GOSET` in the one example that mentions it, but `GOSET` itself
  has no documented entry anywhere in the corpus checked, and `Live`
  testing (2026-07-18, see Open ends) confirms it isn't a real function
  in this GFX2 build at all — whatever selects a cursor shape in
  practice, it isn't `GOSET`.

### Miscellaneous

- `BELL` — rings the terminal bell/speaker. No parameters appear in any
  example from either source; whether it accepts an optional `path` the
  way most other GFX2 functions do is unclear — not stated either way.

## Open ends from this extraction pass

**Resolved in a follow-up gap-closing pass (2026-07-17), sources checked
beyond the original two:** `GCOLR`'s full syntax (found in the BASIC09
Reference Manual Rev G, a source not used in the original pass), `OWEND`'s
no-argument call shape (five converging worked examples across two
manuals), `DEFBUFF`'s spelling (re-checked against the primary source's
own header/syntax/index, all three agree — the single-F reading was the
Tandy cross-check's own OCR error), and `FONT`'s built-in font group
number (Group 200, confirmed from the primary source's own prose, not
just its garbled numeric example). **`COLGR` turned out not to be a
function at all** — it's a plain BASIC09 variable name the manual's own
example programs happen to declare (`DIM X,Y,R,T,COLGR: INTEGER`),
apparently short for "color group," reused across several unrelated
`PALETTE`/`COLOR` example listings. There was never a documentation gap
here, just a false positive from seeing the string appear near color-
related code.

**Resolved `Live`** (see
`test/6809-live-verification/dogfood-report-gfx2-2026-07-18.md` and
`dogfood-gfx2-goset-palette-test.bas` in the os9exec repo): the
community `gfx.asm`/`gfx2.asm` package (this project's own copy) was
built with `asm` (four porting fixes needed — a comment-leader mismatch,
three 8-char label-truncation collisions, an undefined `H6309`
conditional symbol, and three over-length source lines; none changed
program behavior) and installed on the live NitrOS-9 test disk, finally
unblocking the two items below.

- **`GOSET`** (selecting a graphics-cursor shape for `PUTGC`) — `Live,
  Absent`: `RUN GFX2("GOSET",1)` gives `Error #048 -- Unimplemented
  Routine` (GFX2's own function-dispatch table reporting "not found"),
  and a direct grep of `gfx2.asm`'s ~60-entry function table confirms
  `GOSET` is not a registered function name anywhere in this
  implementation. Not just undocumented — genuinely absent from this
  real, community-maintained build. The one worked example mentioning it
  appears to be aspirational/mistaken, not a trustworthy syntax source.
  Whatever mechanism (if any, beyond `GCSET`, which *is* real) actually
  selects a `PUTGC` cursor shape in practice remains unknown.
- **`PALETTE`'s register-number range** — `Live`: not bracketable the way
  planned, because nothing tested was rejected. `register` values up to
  99 and `color` values up to 200 (both far past the presumed 0-15/0-63
  hardware ranges) all executed with no OS-9 error, including against a
  real, explicitly-opened window path (`/W1`), ruling out "the default
  target isn't a real window anyway" as the explanation. Source-confirmed:
  the handler only validates BASIC09's parameter *count*, not the values
  themselves, before writing them straight out via `I$Write`. So the
  confirmed fact is that this implementation performs **no software range
  validation** on either argument — not that 0-15/0-63 is confirmed as
  the real range, which remains genuinely unknown (real CoCo3 GIME
  hardware might wrap/alias an out-of-range value, or something else
  might silently misbehave; establishing that needs actual pixel/palette
  observation, not attempted here — a text-only REPL channel can't do it
  regardless). The full 16-entry default color table beyond registers 0-7
  (black/red/green/yellow/blue/magenta/cyan/white) also wasn't cleanly
  recovered by either OCR pass and remains open.
- **Window/screen format codes** (`DWSET`'s and `GPLOAD`'s `format`
  parameter) are `Manual`, cross-referenced against `wcreate -s=<type>`'s
  `Live` table, but GFX2's own use of those codes has not itself been
  confirmed `Live`.
- **`OWEND`'s restore, 2026-07-19** — reproduced twice (two window
  geometries) that it does not visibly restore content saved by
  `OWSET(1,...)`, contradicting the documented behavior. See the `OWEND`
  entry above for the full test and the varied-configuration controls that
  ruled out a single-geometry fluke. Unresolved because no `windint` source
  is available in this repo to check the real implementation the way
  `LINE`/`LINEM` was settled from `gfx2.asm` itself — a future pass with
  such a source, or further black-box variation (delay before `OWEND`,
  content drawn into the overlay first, a smaller overlay), could take
  this further.
- **Level-1 `GFX`'s screen, 2026-07-19** — `MODE` is accepted with no
  error but never produced a screen reachable through CLEAR-cycling across
  three different output-routing attempts (see the `MODE` entry above).
  Most likely the same underlying reachability gap noted below for
  `wcreate`d windows with no live process, not evidence against the
  lower-left-origin claim, which stays `Manual`.
- Most of the calling-sequence and error-behavior claims in this file are
  now `Live` as of the 2026-07-18/19 passes; what remains genuinely
  `Manual` is concentrated in: the window/screen format codes above, the
  full 16-entry default palette table, `PUTGC`'s screen-relative coordinate
  claim, `BELL`'s optional-`path` question, and the mechanics noted in the
  main "Open questions" section of
  `test/6809-live-verification/dogfood-gfx-pixels-2026-07-18.md` (the
  normalized-vs-scaled coordinate question, and reaching a `wcreate`d
  window that has no live process on it — the same gap that blocks
  Level-1 `GFX`'s screen above).

---
Sources: OS-9 Level 2 Operating System Manual (GFX/GFX2 chapter, Chapter 9)
is primary; the BASIC09 Reference Manual (Tandy) reprints the same
appendix and was used as an independent second OCR pass to cross-check
function names and syntax the primary source's own scan had garbled — it
reported no actual behavioral disagreements with the primary, only heavier
OCR noise (notably on the module name `GFX2` itself). All text here is
paraphrased, not quoted, from those sources — see
`docs/superpowers/plans/2026-07-17-6809-gfx-windowing/cards/` in the
os9exec repo for the underlying atomic-fact extraction if a claim needs
re-tracing to its origin.
