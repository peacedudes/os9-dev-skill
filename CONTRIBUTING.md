# Corrections and additions

**Corrections are genuinely wanted.** This is a reference work about a system
whose documentation is scattered, partly OCR'd, and occasionally
self-contradictory. Errors are expected, and a reader who hits one is better
placed to catch it than the author was.

**Set your expectations honestly, though.** This is not an actively maintained
project. It was built for a purpose, it reached a usable state, and it may sit
untouched for long stretches. Corrections may be merged promptly, slowly, or
not at all. Nothing here is a commitment to respond, and a quiet repository is
the expected steady state rather than a sign something went wrong. If that makes
a fork the better route for you, fork it — the license permits it without asking.

## The most useful thing you can send

You do not need to open a pull request, or know anything about this repo's
conventions, to help. **An issue saying "this line is wrong, here is what I
saw" is valuable on its own**, and is the highest-value contribution there is.

A good correction report answers three things:

1. **What this repo says** — the file and the line.
2. **What you observed instead** — the actual output, error, or register state,
   quoted rather than paraphrased. Exact text matters; a message's precise
   wording is often the only way to tell two causes apart.
3. **Where you observed it** — real hardware, which machine and OS-9 version;
   or an emulator, which one and which build. This one decides everything about
   how the correction can be recorded.

That third point is not bureaucracy. Every claim here carries a confidence tag
naming its evidence, so a report that says *where* can be acted on, while one
that says only *what* usually cannot.

### Where to send it

If you are reading this in a checkout of the published repository, use its issue
tracker — that is the place, and no account beyond the host's is needed.

<!-- PUBLISH: replace the line above with the real issue-tracker URL. -->

If you have a copy that came to you some other way — a zip, a folder someone
sent you — it may have travelled without its repository link. In that case send
the report to whoever gave you the copy, or raise it on any OS-9 community forum
where the author is likely to see it; a correction recorded publicly is better
than one that waits for the right inbox.

**Reports from real hardware are the rarest and most valuable thing** this
project can receive. Nothing in it has been checked against a real OS-9 machine.
Several claims are flagged precisely because only hardware can settle them, and
one measurement from a real system may resolve a question that has been open
here for months.

## If you want to send a patch

The same three things apply, plus the conventions that keep the corpus
trustworthy. Both gates must pass, and a tracked pre-commit hook enforces them:

```sh
git config core.hooksPath tools/hooks     # re-run after a fresh clone
python3 tools/check_doc_consistency.py
python3 tools/tests/test_check.py
```

Then:

- **Tag every claim.** `Hearsay`, `Manual`, `Source`, `Live`, `Absent`, `Flag` —
  defined in `os9-dev/references/CONFIDENCE-TAGS.md`. An untagged assertion
  cannot be weighed by the next reader and will not be merged as-is.
- **A `Live` tag names what it ran on** — `Live` (os9exec), `Live` (NitrOS-9),
  `Live` (OS-9/68000). Never a bare `Live`. A `Live` claim is evidence about
  that implementation, not about OS-9 in the abstract.
- **Run it, or say you didn't.** An unrun example is `Manual` at best. Where
  something could not be tested, say which claim went unchecked rather than
  filling the gap from memory.
- **Where sources disagree, add a `Flag` naming both readings** rather than
  picking a winner. An honest unresolved flag is worth more than a confident
  guess, and this project would rather carry twenty of them than one wrong
  resolution.
- **Don't overwrite an established measurement on one reading.** If something
  looks like a contradiction, check it against the existing `Live` claims and
  against a manual first. A lone correction silently replacing a verified fact
  is this project's known failure mode, and it has been caught happening.
- **Reference files carry no dates, commit hashes, host paths, or narrative**
  about their own history. State the rule positively; provenance belongs in the
  tag and the `Sources` footer, not in a story about what the file used to say.
- **Where the manual and an emulator disagree**, the manual is the
  specification and the emulator is the candidate defect. Record both; see
  `SOURCE-AUTHORITY.md`.

## What is likely to be declined

- An assertion with no stated evidence, however plausible.
- A claim about OS-9 drawn from emulator behaviour alone and presented as
  OS-9's behaviour. Tag it as the emulator's and it is welcome.
- Material copied from a manual at length. Short attributed quotations are
  used here where the exact wording *is* the evidence; reproduced passages,
  verbatim code examples, and anything mirroring a source's structure are
  deliberately kept out. See `SOURCE-AUTHORITY.md` for why that line is drawn
  where it is.
- Large new sections on topics nobody has tested. The corpus is sized to what
  could be verified.

## Scope

Both collections cover the older end of the line: the v2.4-era OS-9/68000
system and OS-9/6809 Level Two. Later versions, OS-9000 beyond passing
mention, and OS-9 for other processors are out of scope — not because they
don't matter, but because nothing here was verified against them.
