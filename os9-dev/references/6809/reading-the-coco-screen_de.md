# (DE) Übersetzung – automatische Platzhalter

Dies ist eine automatische Übersetzungsplatzhalter-Datei. Originalpfad: os9-dev-skill/os9-dev/references/6809/reading-the-coco-screen.md

---

# Seeing the CoCo Screen (6809, XRoar)

A DriveWire text channel drives a NitrOS-9 shell but can never observe a
screen. Verifying graphics work therefore needs a second channel:
host-side screenshots and
keystroke injection against XRoar's own window. Split the roles - drive text
commands over the serial REPL, press keys and capture the screen host-side.
Everything below is `Live` (NitrOS-9) against a running CoCo3, **except the
windint opcode table**, which is `Source` - read out of NitrOS-9's own
`windefs.as`, not exercised opcode by opcode.

## CLEAR is the host backtick

The CoCo `CLEAR` key cycles between the screens of active windows, and is how
you bring a background window's screen to the front. Under XRoar it is the
**host backtick** (macOS virtual keycode 50).

On a stock EOU di