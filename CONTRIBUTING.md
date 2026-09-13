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
forking the better route for you, check [LICENSE](LICENSE) for whether that is
permitted yet — while the pre-publication notice stands, it is not.

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

**The repository's issue tracker, and nowhere else.** That is the only channel;
there is deliberately no email address here, and the author is not reachable
through OS-9 forums or mailing lists.

<!-- PUBLISH: put the repository URL on the line below. -->

If you are holding a copy that arrived as a zip or a folder rather than a
checkout, it travelled without its link. The repository is public; search for its
name, or ask whoever gave you the copy. A correction posted anywhere public is
still better than one that waits for the right inbox — but the tracker is where
it will actually be seen.

**Reports from real hardware are the rarest and most valuable thing** this
project can receive. Nothing in it has been checked against a real OS-9 machine.
Several claims are flagged precisely because only hardware can settle them, and
one measurement from a real system may resolve a question that has been open
here for months.

### If you have real hardware, there is a worklist waiting for you

Two ready-made lists of open questions, both already written down:

```sh
python3 tools/check_doc_consistency.py    # prints every open `Flag`, with file and line
```

That inventory is the set of places where sources contradict each other or a
measurement is missing, each one named and located. Several say outright that
only Microware or real hardware can settle them.

`DIVERGENCES.md` is the shorter, sharper list: places where observed behaviour
disagrees with a Microware manual. Every item on it is a question a real machine
could answer, and the first one is flagged as having been seen only under
emulation.

Pick any line from either and test it. You do not need to fix the file — saying
"I ran this on real hardware and got X" is the whole contribution.

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
  cannot be weighed by the next reader, so it will need a tag before it lands —
  and if you are unsure which applies, say what you did and leave the tag to
  whoever merges it. That is not a reason to hold the patch back.
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
  against a manual first — the two may be describing different things. This is
  the mistake the project's own authors have made most often, which is why it is
  listed: a plausible correction that quietly replaced a verified fact has had to
  be reverted here more than once.

  The reason the tags and the git history earn their keep is that **a recorded
  measurement is the control case for the next observation.** When what you see
  disagrees with what the file says, one of you is wrong and the file is the one
  with its evidence written down — so the first move is to find out whether you
  are looking at the same thing, not to replace it. A sister project doing
  captured-output work had two results that looked exactly like damage it had just
  caused, and the only reason neither was "fixed" is that the previous capture was
  committed and could be compared byte for byte. Both turned out to be
  long-standing behaviour. Preserve the old reading in a `Flag` if you cannot
  reconcile it.
- **Reference files carry no dates, commit hashes, host paths, or narrative**
  about their own history. State the rule positively; provenance belongs in the
  tag and the `Sources` footer, not in a story about what the file used to say.
- **Where the manual and an emulator disagree**, the manual is the
  specification and the emulator is the candidate defect. Record both; see
  `SOURCE-AUTHORITY.md`.
- **If you script an edit across many files, check what each match *does*, not
  only what it *is*.** A pattern can identify the right lines and still miss what
  those lines are responsible for. Two real instances, both caught only by reading
  the result back: a script that removed "the staging line" from a set of
  documents was correct that each line staged a file, and wrong that staging was
  all it did — one of them also set an environment variable the program needed.
  And `git commit -- <path>` is genuinely a commit scoped to a path, while also
  committing the *working tree* rather than the index, quietly including changes
  that were deliberately left unstaged. In both cases the pattern matched exactly
  what it was meant to. **Read back what a bulk edit produced before trusting the
  pattern that produced it** — a diff line count is usually enough to see it.

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

## Taking this over

**This project is built to be adopted, and a fork becoming the active copy is a
good outcome rather than a failure.** The author's preference is for it to end up
maintained by people who use it, and to step back. Nothing here depends on him
continuing.

What a successor inherits is unusually self-sufficient for a documentation
project, and it is worth knowing before you decide:

- **The claims carry their own evidence.** Every statement has a confidence tag
  naming what backs it, so a new maintainer can tell measured fact from read-it-
  in-a-manual without re-deriving the whole corpus. That is the thing that
  normally rots first and here it is explicit.
- **The quality rules are mechanical, not cultural.** `tools/check_doc_consistency.py`
  enforces tag hygiene, cross-file numeric drift, dump-decode claims, error
  symbols against the error table, and the no-dates/no-hashes/no-host-paths rule.
  Its own behaviour is covered by 136 tests. You do not have to absorb a house
  style by osmosis; run the checker.
- **The provenance chain is written down.** `SOURCE-AUTHORITY.md` says which
  sources are Microware speaking and which are someone's reading of Microware,
  and `NOTICE` records who is owed credit. Keep those current and the project
  stays defensible.
- **The open questions are listed, not implied.** The checker prints every
  unresolved `Flag`, and `DIVERGENCES.md` holds the manual-versus-observed
  conflicts. That is a roadmap you did not have to write.

If you fork it and take it somewhere better, the license permits that outright
once it is in force, and credit under `NOTICE` is the only thing asked. Say so in
your README so readers can find the active copy.

## Scope

Both collections cover the older end of the line: the v2.4-era OS-9/68000
system and OS-9/6809 Level Two. Later versions, OS-9000 beyond passing
mention, and OS-9 for other processors are out of scope — not because they
don't matter, but because nothing here was verified against them.
