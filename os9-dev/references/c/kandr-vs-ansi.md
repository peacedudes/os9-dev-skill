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

## Porting checklist

- [ ] K&R function definitions (params after name, types declared separately)
- [ ] `+=`/`-=`/`*=`, not `=+`/`=-`/`=*`
- [ ] Check every `\n` — CR here, not LF
- [ ] No direct struct assignment — use `strass()` instead
- [ ] `<strings.h>`, not `<string.h>`
- [ ] Source files need CR-only line endings before compiling (`flip -m`)
- [ ] Assume string literals are read-only

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
