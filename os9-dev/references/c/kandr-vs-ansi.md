# K&R vs ANSI C: OS-9 Microware Compiler

The Microware OS-9 C compiler is a **K&R-era implementation**. Modern ANSI C
will often fail to compile. Most of these are just "this is K&R C" facts —
the two that actually bite in practice (and are genuinely OS-9-specific, not
just old-C-history) are the function-definition syntax you need to write
anything at all, and the `\n` escape sequence, which is called out
separately below.

**Provenance note:** rows marked *(6809 manual)* below are `Manual`,
sourced from the 1983 6809 C Compiler manual's own "Differences From The
K & R Specification" section and not independently re-confirmed against a
68k Ultra C toolchain — treat them as "this is what the 6809-vintage
compiler did," not as a guaranteed 68k fact, unless another row or
`os9-c-cheatsheet.md` says otherwise. Unmarked rows reflect either
baseline K&R-era behavior or `Live` (os9exec)-verified facts on a real 68k
toolchain.

| Modern C pattern | Status on this compiler | Fix |
|---|---|---|
| `int add(int a, int b) { ... }` (ANSI prototype) | Not supported — see K&R form below | Use K&R-style definitions (only form accepted) |
| `x =+ 5;` (old compound-assignment form) | **Not** supported *(6809 manual)* — parses as `x = +5` | Use `x += 5;` |
| `struct1 = struct2;` (direct struct assignment) | Not supported *(6809 manual)* | Use the library's `strass()` function — a byte-by-byte block copy provided as the documented workaround |
| `<string.h>` | Doesn't exist | `<strings.h>` — different API (`index`/`rindex`, not `strchr`/`strrchr`) |
| Modifying a string literal (`char *s = "x"; s[0] = 'y';`) | Undefined behavior — a `char *` literal like this lives in the module's shared, read-only TEXT section (see `common/module-format.md`), not DATA; writing to it risks a real fault, not just silent corruption. (Contrast `char array[] = "x"` — that form gets its own per-process, mutable DATA storage and is safe to write) | Copy to a `char[]` buffer first with `strcpy` |

## Function definitions (the one syntax you actually need to get right)

```c
int add(a, b)
int a;
int b;
{
    return a + b;
}
```

Old-style definition — parameter names in the parens, types declared
separately before the opening brace. This is the *only* form the compiler
accepts; there is no prototype syntax.

## The `\n` escape sequence: the OS-9-specific gotcha

**`\n` means carriage return (CR, 0x0D) here, not linefeed (0x0A)** — it
matches OS-9's own text-line convention, but it's the opposite of Unix and
will surprise anyone porting code either direction.

```c
printf("Line 1\nLine 2\n");    /* outputs CR, not LF */
printf("Line 1\eLine 2\e");    /* \e (lowercase) is this compiler's true-linefeed escape */
printf("Value: %d\x0D");       /* or just be explicit with \x0D / \x0A */
```

`Source` (OS-9 C Compiler manual, Microware, 1983, 6809 edition — the
compiler's own "Control Character Escape Sequences" section, extending
K&R p.181): `\e` is documented explicitly "to distinguish LF from `\n`
which on OS9 is the same as `\r`."

## Converting an ANSI tree with `ansi2knr`

`ansi2knr` (Aladdin/Ghostscript, shipped inside the JPEG library sources) is the
standard de-ANSIfier and it builds under Microware `cc`, so it is the obvious
tool to reach for. It earns its place, but four limits decide how much hand work
is left, and a fifth can hang your build.

**It rewrites definitions only — declarations reach `c68` untouched.** This is
the one that changes how you estimate a job. `Live` (os9exec), two game ports:
46 and 90 function *definitions* converted automatically, while 33 and 66
*prototypes* survived in the headers and all had to be done by hand. **So when
sizing an ANSI tree for this compiler, count the declarations.**

**But the definitions are only free in one brace style.** The tool requires the
function *name* to be the first thing on its line (`Source`, `ansi2knr.c`: "the
function name must be the first thing on the line", and its test returns early
with `no name at left margin`). So it converts

```c
int                     /* name on its own line -> converted */
foo(int a, char *b)
```

and skips the ordinary same-line form

```c
int foo(int a, char *b) /* `int` is at the margin, not `foo` -> skipped */
```

`Live` (os9exec), two trees that are ANSI throughout and converted **nothing**:
one with all sixteen definitions written on one line, one with twenty-four. A
tree in that style gets no benefit at all, and the estimate built on "the
definitions are free" is wrong by the whole job.

**So the pre-port measurement is two counts, not one:** the declarations (never
converted), and the definitions *not* already in the split style (also never
converted). "Is this ANSI?" does not predict the work; the brace style does.

Three more blind spots, each confirmed in the tool's own source (`Source`):

- **It only recognises a function whose name is at the left margin.** Its header
  says so: *"a non-keyword identifier at the left margin, followed by a left
  parenthesis."* So `static void f(void)` — keyword first — is skipped entirely.
- **It has no variadic support at all.** `va_alist`, `va_dcl` and `va_list`
  appear nowhere in `ansi2knr.c`. Variadic definitions convert by hand to
  `format(va_alist) va_dcl` plus `va_start`/`va_arg`/`va_end` — and the converted
  file must then be **excluded** from the pass, or the next run rewrites it again.
- **It never looks inside a struct**, so ANSI function pointers declared as struct
  members are invisible to it. Eleven `void (*init)(board_t *, ...)` members
  produced 60 errors, none of them pointing at the real line.

**A macro invocation at the left margin makes it hang — silently and forever.**
A file of `ROOM(...)`/`OBJECT(...)` macro calls at the margin, with arguments
spanning lines, has the same shape as a function header, and the tool tries to
rewrite them. `Live` (os9exec): with an unbalanced `(` inside one of the string
literals it spun at full CPU and never exited, corrupting string literals on the
way (commas inside them became `;`). The same shape with balanced parentheses
converted and exited. There is no error and no exit status to test.

The cause is visible in the source (`Source`): `convert1()` scans with
`for ( ; end == NULL; p++ )`, switching only on `,` `(` `)`, with **no NUL check
and no bound** against a 5000-byte buffer (`#define bufsize 5000 /* arbitrary
size */`), so it walks off the end of the text. Note the tool documents the
*confusion* and not the consequence: it warns that it will be confused by *"any
other construct that starts at the left margin and follows the above syntax (such
as a macro or function call)"*, and separately that *"there are no error
messages"* — it just never says that being confused means hanging. The cure is to
drop that one file from the conversion list.

**Running it on an already-K&R tree is harmful, not merely useless.** `Live`
(os9exec): it rewrites a definition it has already rewritten, and `c68` then
reports `**** multiple definition ****` against parameter declarations that are
plainly correct K&R. A distinctive symptom, easy to misread as a defect in the
source.

## Two ANSI features the preprocessor will not give you

**Adjacent string literals are not joined.** `"abc" "def"` is ANSI translation
phase 6 and nothing in this toolchain performs it: `c68` reads two expressions and
says `; expected` plus `expression with little effect`. Join them in the source.
`Live` (os9exec). (The SDK's `gcc2` driver is the exception: it runs `cccp2`
without `-traditional`, and a `gcc2` build of `"abc" "def"` prints `abcdef`.)

When hunting for them, do not grep for lines beginning with a quote: that counts
string-array initialisers and comma-separated arguments, both legal K&R, and
scored 116 hits on a tree that compiled fine. A genuine adjacent pair is **a line
ending in a closing quote with no comma, followed by a line opening with a
quote.**

**Line limits apply to the LOGICAL line, and continuations are spliced before
counting** — so `\` buys you nothing, and neither does hiding the line in a
`#if 0`. `Live` (os9exec): `cpp` gives way first, and **its limit is not a fixed
number** — 511 characters is the best case measured in a file with nothing else
in it, and content earlier in the file lowers it, with the same length diagnosed
cleanly in one file and killing `cpp` outright in another (`os9-c-cheatsheet.md`
has the measurements). `c68` stops at 1023. Joining string literals by hand
routinely lands a line between the two, so **keep joined lines well under 500**
rather than aiming at a threshold.

The hidden case is `__FILE__` inside a macro's format string: it expands at every
call site, so the line that breaks is the *caller*, and the errors point there
rather than at the header that caused it. Pass it as a `%s` argument instead of
embedding it.

## Porting checklist

- [ ] K&R function definitions (params after name, types declared separately)
- [ ] `+=`/`-=`/`*=`, not `=+`/`=-`/`=*`
- [ ] Check every `\n` — CR here, not LF
- [ ] No direct struct assignment — use `strass()` instead
- [ ] `<strings.h>`, not `<string.h>`
- [ ] Source files need CR-only line endings before compiling (`flip -m`)
- [ ] Assume string literals are read-only
- [ ] Count **two** shapes: the declarations (`ansi2knr` never converts them)
      and the definitions whose return type shares a line with the name (it
      skips those too). Both are hand work; "is it ANSI" predicts neither
- [ ] Join adjacent string literals (`"a" "b"`); nothing here concatenates them
- [ ] Keep joined logical lines well under 500 characters — the limit is not
      fixed, earlier content in the file lowers it, and `\` continuations do not help

---

**Sources:** Official Microware C Compiler manual (1983, 6809 edition),
"Differences From The K & R Specification" section (bit fields, initializer
operands, `=+`-style operators, `\n` as CR); `strass()` is documented
separately in the same manual's C System Calls reference, not the
Differences chapter — usage `strass(s1, s2, count)`, described there as a
byte-by-byte copy for structures the compiler can't assign directly.
Cross-checked against "The OS-9 Primer." Note: rows marked *(6809 manual)*
are `Manual`, sourced from 6809-era material only, and may not apply
unchanged to 68k; check `os9-c-cheatsheet.md` for 68k-specific
differences.

## `char` is SIGNED — `Live` (os9exec)

Measured by compiling on a Microware SDK and running: `char c = -1;` tests
negative, and **`EOF` assigned to a `char` still compares equal to `EOF`**.

This matters because the commonest 1980s C read loop is

    char ch;
    while ((ch = getc(fp)) != EOF) ...

which is a latent bug on any compiler where `char` is unsigned, and is NOT one
here. Do not reach for it as an explanation when a K&R program reads past end
of file on OS-9 — it will not be the cause, and it is an easy theory to spend
an hour on. (It was, on `cdiff`.)
