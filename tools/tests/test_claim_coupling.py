"""Tests for the claim-coupling advisory.

Run from the repo root:
    python3 tools/tests/test_claim_coupling.py

Every "must NOT name" case here is the reason this is advisory rather than a
gate: the check reasons about adjacency, so its failure mode is noise, and a
noisy check gets switched off. The "must name" cases are built from the real
miss that prompted it -- a `cpp` line-limit correction landing in one file while
another still stated the old fixed threshold.
"""

import io
import os
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import check_claim_coupling as cc  # noqa: E402


# --------------------------------------------------------------------------
# subjects_in -- what counts as asserting a bound about something
# --------------------------------------------------------------------------
class TestSubjectsIn(unittest.TestCase):
    def test_names_the_subject_of_a_quantity_claim(self):
        self.assertEqual(
            cc.subjects_in("Microware `cpp` bus-errors at 513 characters."), {"cpp"}
        )

    def test_names_the_subject_of_a_limit_claim_carrying_no_digits(self):
        self.assertEqual(
            cc.subjects_in("`cpp` has no fixed limit; earlier content lowers it."),
            {"cpp"},
        )

    def test_a_bare_mention_with_no_claim_is_not_a_subject(self):
        # The corpus mentions tools constantly. Only assertions of a bound matter.
        self.assertEqual(cc.subjects_in("Run `cpp` first, then `c68`."), set())

    def test_confidence_tags_are_never_subjects(self):
        # `Live` appears on nearly every measured line; keying on it would
        # couple every claim to every other claim.
        self.assertEqual(
            cc.subjects_in("`Live` (os9exec): the buffer is 512 bytes."), set()
        )

    def test_emulator_name_is_never_a_subject(self):
        self.assertEqual(cc.subjects_in("`os9exec` stops at 1023 characters."), set())

    def test_unbackticked_words_are_not_subjects(self):
        self.assertEqual(cc.subjects_in("The preprocessor stops at 513 chars."), set())


# --------------------------------------------------------------------------
# coupled_files -- both directions
# --------------------------------------------------------------------------
class TestCoupledFiles(unittest.TestCase):
    def _tree(self, files):
        tmp = tempfile.mkdtemp()
        for name, text in files.items():
            path = pathlib.Path(tmp) / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
        return tmp

    def test_names_a_file_still_stating_the_old_threshold(self):
        # The real miss: one file corrected, another left saying 513.
        root = self._tree(
            {
                "stale.md": "Microware `cpp` bus-errors at 513 characters.\n",
                "unrelated.md": "The shell parses `<path` with no space.\n",
            }
        )
        found = cc.coupled_files({"cpp"}, root, exclude=set())
        self.assertEqual([p.name for p, _ in found], ["stale.md"])

    def test_does_not_name_a_file_that_only_mentions_the_subject(self):
        root = self._tree({"mentions.md": "Invoke `cpp` before `c68`.\n"})
        self.assertEqual(cc.coupled_files({"cpp"}, root, exclude=set()), [])

    def test_does_not_name_the_file_being_edited(self):
        root = self._tree({"edited.md": "`cpp` stops at 512 characters.\n"})
        exclude = {str(pathlib.Path(root) / "edited.md")}
        self.assertEqual(cc.coupled_files({"cpp"}, root, exclude=exclude), [])

    def test_does_not_couple_on_an_unrelated_subject(self):
        root = self._tree({"other.md": "`c68` stops at 1023 characters.\n"})
        self.assertEqual(cc.coupled_files({"cpp"}, root, exclude=set()), [])

    def test_reports_the_first_line_of_the_block_and_the_shared_subject(self):
        root = self._tree({"s.md": "intro para\n\n`cpp` fails at 513 characters.\n"})
        (_, hits), = cc.coupled_files({"cpp"}, root, exclude=set())
        self.assertEqual(hits[0][0], 3)
        self.assertEqual(hits[0][1], ["cpp"])

    def test_finds_a_claim_whose_subject_and_quantity_are_on_different_lines(self):
        # The regression this check exists for. The corpus hard-wraps, so the
        # real stale claim read "Microware `cpp`" / "bus-errors at 513
        # characters" across a line break. Line-at-a-time matching missed it and
        # the check silently passed the commit that should have flagged it.
        root = self._tree(
            {
                "wrapped.md": (
                    "**Line limits apply to the LOGICAL line.** Microware `cpp`\n"
                    "bus-errors at 513 characters and `c68` stops at 1023.\n"
                )
            }
        )
        found = cc.coupled_files({"cpp"}, root, exclude=set())
        self.assertEqual([p.name for p, _ in found], ["wrapped.md"])

    def test_a_blank_line_still_separates_unrelated_claims(self):
        # Joining must not run across paragraphs, or every subject in a file
        # couples to every quantity in it.
        root = self._tree({"two.md": "Mentions `cpp` only.\n\n`c68` stops at 1023.\n"})
        self.assertEqual(cc.coupled_files({"cpp"}, root, exclude=set()), [])


# --------------------------------------------------------------------------
# report -- stays quiet, and says so, when there is nothing to say
# --------------------------------------------------------------------------
class TestReportIsAdvisory(unittest.TestCase):
    def test_no_claim_bearing_changes_says_so_and_names_nothing(self):
        buf = io.StringIO()
        named = cc.report("HEAD", "no/such/tree", stream=buf)
        self.assertEqual(named, 0)
        self.assertIn("no claim-bearing changes", buf.getvalue())

    def test_main_never_fails_a_build(self):
        # A gate that can only guess must not be able to block a commit.
        self.assertEqual(cc.main(["--rev", "HEAD", "--root", "no/such/tree"]), 0)


if __name__ == "__main__":
    unittest.main()
