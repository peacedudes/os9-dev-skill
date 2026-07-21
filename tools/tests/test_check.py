"""Tests for the skill-doc consistency checker.

Run from ~/.claude/skills:
    python3 -m unittest discover -s tools/tests

The presence-contradiction tests are built directly from the false positives
the first dogfood run produced against the real docs -- each "must NOT flag"
case is a real sentence pattern that must never be mistaken for a contradiction,
and the "must flag" case is a reintroduced I$Dup-style bug.
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import check_doc_consistency as chk  # noqa: E402

KNOWN = {"Hearsay", "Manual", "Source", "Live", "Absent", "Flag"}


# --------------------------------------------------------------------------
# parse_known_tags
# --------------------------------------------------------------------------
class TestParseKnownTags(unittest.TestCase):
    def test_extracts_the_six_tags_from_the_confidence_table(self):
        md = (
            "| Tag | Meaning |\n"
            "|---|---|\n"
            "| `Hearsay` | x |\n"
            "| `Manual` | x |\n"
            "| `Source` | x |\n"
            "| `Live` | x |\n"
            "| `Absent` | x |\n"
            "| `Flag` | x |\n"
            "\n`Hearsay` < `Manual` < `Source` < `Live`.\n"
        )
        self.assertEqual(chk.parse_known_tags(md), KNOWN)


# --------------------------------------------------------------------------
# platform_of
# --------------------------------------------------------------------------
class TestPlatformOf(unittest.TestCase):
    def test_6809_path(self):
        self.assertEqual(chk.platform_of("os9-dev/references/6809/foo.md"), "6809")

    def test_68k_path(self):
        self.assertEqual(chk.platform_of("os9-dev/references/68k/foo.md"), "68k")

    def test_common_path_is_neutral(self):
        self.assertEqual(chk.platform_of("os9-dev/references/common/foo.md"), "neutral")


# --------------------------------------------------------------------------
# presence classification (the heart of the rebuild)
# --------------------------------------------------------------------------
class TestPresence(unittest.TestCase):
    def p(self, line, syscall, tags=(), is_subject=True):
        return chk._presence(line, syscall, frozenset(tags), is_subject)

    def test_incidental_mention_on_a_live_failed_row_is_none(self):
        # F$Load is only referenced in F$UnLoad's FAILED row -- not the subject.
        line = "| F$UnLoad | after the same name was `F$Load`ed. **`Live` -- FAILED** |"
        self.assertEqual(self.p(line, "F$Load", ("Live",), is_subject=False), "none")

    def test_explicit_absence_counts_even_when_not_subject(self):
        self.assertEqual(self.p("plausibly, 6809 has no `F$STrap` at all", "F$STrap", is_subject=False), "absent")

    def test_live_without_failure_is_present(self):
        self.assertEqual(self.p("**F$Fork** register contract confirmed.", "F$Fork", ("Live",)), "present")

    def test_does_implement_is_present(self):
        self.assertEqual(self.p("**`os9exec` does implement `I$Dup`**", "I$Dup", ("Live",)), "present")

    def test_live_but_unimplemented_is_absent(self):
        line = "F$LDAXYP ... **`Live` -- FAILS**, `err=00208`=`E$UnkSvc`, unimplemented."
        self.assertEqual(self.p(line, "F$LDAXYP", ("Live",)), "absent")

    def test_live_call_returning_an_error_code_is_still_present(self):
        # The call exists and correctly returns an error on the error path -- present, not absent.
        line = "F$UnLoad ... **`Live` -- FAILED**, err=00221 (`E$MNF`, module not found)."
        self.assertEqual(self.p(line, "F$UnLoad", ("Live",)), "present")

    def test_live_error_path_fail_is_not_absence(self):
        # F$Fork's real row: "a name with no file behind it fails E$PNNF" -- error path, not absence.
        line = "`F$Fork` *does* resolve via the filesystem -- a name with no file fails `E$PNNF` (216). `Live`"
        self.assertEqual(self.p(line, "F$Fork", ("Live",)), "present")

    def test_has_no_call_is_absent(self):
        self.assertEqual(self.p("6809 has no `F$STrap` call at all", "F$STrap"), "absent")

    def test_absent_tag_is_absent(self):
        self.assertEqual(self.p("**F$Zap** never checked. `Absent`", "F$Zap", ("Absent",)), "absent")

    def test_offset_negation_is_not_absence(self):
        # "not `$1A`" is about an offset, not the call -- must read as present.
        line = "at offset `$03`. **`os9exec` does implement `I$Dup`** not `$1A`."
        self.assertEqual(self.p(line, "I$Dup", ("Live",)), "present")

    def test_source_locating_negation_is_not_absence(self):
        line = "**Not independently located in NitrOS-9's source** despite a real search. `Live`"
        self.assertEqual(self.p(line, "F$Load", ("Live",)), "present")

    def test_no_error_phrasing_is_not_absence(self):
        line = "setting the caller's own already-current ID accepted with no error. `Live`"
        self.assertEqual(self.p(line, "F$SUser", ("Live",)), "present")

    def test_manual_only_mention_is_none(self):
        self.assertEqual(self.p("F$GCMDir($52) has no params listed yet.", "F$GCMDir", ("Manual",)), "none")

    def test_unimplemented_in_a_later_clause_does_not_bind(self):
        # "unimplemented" refers to termination, not to F$TLink -- must not read as absence.
        line = "initialization (run at F$TLink), termination (reserved, unimplemented in this build)"
        self.assertEqual(self.p(line, "F$TLink", is_subject=False), "none")


class TestFindMentionsSubject(unittest.TestCase):
    def test_table_row_marks_subject_absent_and_incidental_none(self):
        text = "| F$UnLoad | x | note references `F$Load` | **`Live` -- `E$UnkSvc`, unimplemented** |\n"
        by = {m.syscall: m.presence for m in chk.find_mentions(text, "6809/x.md", KNOWN)}
        self.assertEqual(by["F$UnLoad"], "absent")
        self.assertEqual(by["F$Load"], "none")

    def test_table_row_marks_subject_present(self):
        text = "| **F$Fork** | create process | confirmed. `Live` |\n"
        by = {m.syscall: m.presence for m in chk.find_mentions(text, "68k/s.md", KNOWN)}
        self.assertEqual(by["F$Fork"], "present")



# --------------------------------------------------------------------------
# presence contradiction
# --------------------------------------------------------------------------
def mention(syscall, file="f.md", line=1, platform="neutral", presence="none", tags=()):
    return chk.Mention(syscall, file, line, platform, presence, frozenset(tags))


class TestPresenceContradiction(unittest.TestCase):
    def test_flags_present_vs_absent_on_same_platform(self):
        mentions = [
            mention("I$Dup", "68k/syscall-reference.md", 93, "68k", "present", ("Live",)),
            mention("I$Dup", "common/memory-and-io.md", 210, "68k", "absent"),
        ]
        findings = chk.check_presence_contradiction(mentions)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].syscall, "I$Dup")
        self.assertIn(("68k/syscall-reference.md", 93), findings[0].locations)
        self.assertIn(("common/memory-and-io.md", 210), findings[0].locations)

    def test_neutral_present_conflicts_with_either_platform_absent(self):
        mentions = [
            mention("F$Zap", "common/ipc.md", 5, "neutral", "present", ("Live",)),
            mention("F$Zap", "6809/x.md", 9, "6809", "absent"),
        ]
        self.assertEqual(len(chk.check_presence_contradiction(mentions)), 1)

    def test_absent_on_6809_present_on_68k_is_not_a_contradiction(self):
        # F$STrap: legitimately platform-specific, must stay silent.
        mentions = [
            mention("F$STrap", "common/error-codes.md", 131, "6809", "absent"),
            mention("F$STrap", "68k/syscall-reference.md", 131, "68k", "present", ("Live",)),
        ]
        self.assertEqual(chk.check_presence_contradiction(mentions), [])

    def test_consistently_absent_is_not_a_contradiction(self):
        # F$LDAXYP: Live-FAILS on 6809, only Manual elsewhere -- everyone agrees it's absent.
        mentions = [
            mention("F$LDAXYP", "6809/x.md", 218, "6809", "absent", ("Live",)),
            mention("F$LDAXYP", "6809/x.md", 183, "6809", "none", ("Manual",)),
        ]
        self.assertEqual(chk.check_presence_contradiction(mentions), [])


# --------------------------------------------------------------------------
# tag hygiene
# --------------------------------------------------------------------------
class TestTagHygiene(unittest.TestCase):
    def test_flags_miscased_tag(self):
        findings = chk.check_tag_hygiene("**F$Fork** works. `LIVE`\n", "a.md", KNOWN)
        self.assertEqual(len(findings), 1)
        self.assertIn("LIVE", findings[0].message)
        self.assertIn("Live", findings[0].message)

    def test_flags_transposed_typo(self):
        findings = chk.check_tag_hygiene("Detail is `Manaul` only.\n", "b.md", KNOWN)
        self.assertEqual(len(findings), 1)
        self.assertIn("Manual", findings[0].message)

    def test_exact_tag_is_clean(self):
        self.assertEqual(chk.check_tag_hygiene("All good. `Live`\n", "c.md", KNOWN), [])

    def test_unrelated_backticked_word_is_clean(self):
        self.assertEqual(chk.check_tag_hygiene("returns a `PID` value.\n", "d.md", KNOWN), [])

    def test_near_english_word_is_not_flagged(self):
        self.assertEqual(chk.check_tag_hygiene("the `Line` buffer.\n", "e.md", KNOWN), [])


# --------------------------------------------------------------------------
# flag inventory
# --------------------------------------------------------------------------
class TestOpenFlags(unittest.TestCase):
    def test_lists_an_open_flag_line(self):
        text = "- **`Flag`: the param-area byte layout at entry is unverified.\n"
        inv = chk.scan_open_flags(text, "6809/x.md", KNOWN)
        self.assertEqual(len(inv), 1)
        self.assertEqual(inv[0].locations, [("6809/x.md", 1)])
        self.assertIn("param-area", inv[0].message)

    def test_skips_resolved_flag(self):
        text = "| **F$Fork** | `Live` -- `Flag` resolved: contract confirmed |\n"
        self.assertEqual(chk.scan_open_flags(text, "68k/s.md", KNOWN), [])

    def test_skips_convention_explanation(self):
        text = "Entries additionally tagged `Flag` carry a known cross-manual conflict.\n"
        self.assertEqual(chk.scan_open_flags(text, "68k/s.md", KNOWN), [])

    def test_ignores_lines_without_a_flag(self):
        text = "**F$Fork** works fine. `Live`\n"
        self.assertEqual(chk.scan_open_flags(text, "68k/s.md", KNOWN), [])


# --------------------------------------------------------------------------
# driver
# --------------------------------------------------------------------------
CONFIDENCE_TABLE = (
    "| Tag | Meaning |\n|---|---|\n"
    "| `Hearsay` | x |\n| `Manual` | x |\n| `Source` | x |\n"
    "| `Live` | x |\n| `Absent` | x |\n| `Flag` | x |\n"
)


class TestRun(unittest.TestCase):
    def _tree(self, files):
        root = tempfile.mkdtemp()
        for name, body in files.items():
            path = os.path.join(root, name)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(body)
        return root

    def test_run_flags_reintroduced_i_dup_bug(self):
        root = self._tree({
            "references/CONFIDENCE-TAGS.md": CONFIDENCE_TABLE,
            "references/68k/syscall-reference.md": "| **I$Dup** | duplicate a path | d0.w=path | `Live` |\n",
            "references/common/memory-and-io.md": "Note: os9exec has no `I$Dup`.\n",
        })
        findings, inventory = chk.run([root])
        self.assertEqual([f.syscall for f in findings], ["I$Dup"])

    def test_run_ignores_meta_doc_examples(self):
        # The Absent-tag definition lists calls as examples -- must not be scanned.
        root = self._tree({
            "references/CONFIDENCE-TAGS.md": (
                CONFIDENCE_TABLE
                + "\n`Absent` example: 6809 has no `F$Send`/`F$Icpt` events.\n"
            ),
            "references/68k/syscall-reference.md": "**F$Send** signals. `Live`\n**F$Icpt** traps. `Live`\n",
        })
        findings, _ = chk.run([root])
        self.assertEqual(findings, [])

    def test_run_on_clean_tree_is_silent(self):
        root = self._tree({
            "references/CONFIDENCE-TAGS.md": CONFIDENCE_TABLE,
            "references/68k/syscall-reference.md": "**F$Fork** works. `Live`\n",
        })
        findings, inventory = chk.run([root])
        self.assertEqual(findings, [])
        self.assertEqual(inventory, [])


if __name__ == "__main__":
    unittest.main()
