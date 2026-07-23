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
class TestVerifiedAgainst(unittest.TestCase):
    def test_extracts_baseline_rows_from_the_section(self):
        md = (
            "## What `Live` is verified against\n\n"
            "| Platform | Build identity | How |\n"
            "|---|---|---|\n"
            "| 68k (os9exec) | v0.0.0-482-g534315a | the hash |\n"
            "| 6809 (NitrOS-9) | XRoar 1.11 + eou_ide-v0.3 | disk+emu |\n"
            "\n## Next section\n| unrelated | table |\n"
        )
        self.assertEqual(
            chk.verified_against(md),
            [("68k (os9exec)", "v0.0.0-482-g534315a"), ("6809 (NitrOS-9)", "XRoar 1.11 + eou_ide-v0.3")],
        )

    def test_empty_when_no_section(self):
        self.assertEqual(chk.verified_against("# nothing here\n| a | b |\n"), [])


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


# --------------------------------------------------------------------------
# cross-reference integrity (INDEX.md pointers)
# --------------------------------------------------------------------------
class TestExtractDocReferences(unittest.TestCase):
    def test_finds_backticked_and_bare_md_tokens(self):
        line = "| Read | `common/foo.md` | and also bar.md plain |"
        self.assertEqual(chk.extract_doc_references(line), ["common/foo.md", "bar.md"])

    def test_finds_sibling_qualified_token(self):
        line = "sibling os9-dev skill: `references/6809/using-nitros9-repl.md`"
        self.assertEqual(chk.extract_doc_references(line), ["references/6809/using-nitros9-repl.md"])


class TestCrossReferences(unittest.TestCase):
    def test_flags_index_entry_with_no_matching_file(self):
        files = [("os9-dev/references/INDEX.md", "| Topic | ghost-file.md |\n")]
        findings = chk.check_cross_references(files, known_basenames={"INDEX.md"})
        self.assertEqual(len(findings), 1)
        self.assertIn("ghost-file.md", findings[0].message)
        self.assertEqual(findings[0].locations, [("os9-dev/references/INDEX.md", 1)])

    def test_silent_when_basename_matches(self):
        files = [("os9-dev/references/INDEX.md", "| Topic | `common/foo.md` |\n")]
        findings = chk.check_cross_references(files, known_basenames={"foo.md"})
        self.assertEqual(findings, [])

    def test_sibling_qualified_path_resolves_by_basename(self):
        # os9-systems-dev/INDEX.md style: "os9-dev/references/CONFIDENCE-TAGS.md"
        files = [("os9-systems-dev/references/INDEX.md", "See `os9-dev/references/CONFIDENCE-TAGS.md`.\n")]
        findings = chk.check_cross_references(files, known_basenames={"CONFIDENCE-TAGS.md"})
        self.assertEqual(findings, [])

    def test_non_index_files_are_not_scanned(self):
        # A prose doc mentioning a file that lives in a different repo entirely
        # (e.g. a dogfood report) must never be flagged -- only INDEX.md is scoped.
        files = [("os9-dev/references/6809/STATUS.md", "See `dogfood-report-2026-07-18.md`.\n")]
        findings = chk.check_cross_references(files, known_basenames={"STATUS.md"})
        self.assertEqual(findings, [])


# --------------------------------------------------------------------------
# DIVERGENCES.md two-way link integrity
#
# The point of these: a divergence from Microware documentation is only useful
# if the reader of the affected *claim* meets the warning. The failure this
# guards against is real and has a history -- the repo's old confidence rule
# told contributors to clear a manual disagreement whenever a reimplementation
# was observed, which is how 540 runtime claims came to sit against 5 recorded
# disagreements. An entry whose inline marker gets rewritten away is that same
# failure in slow motion, so it must break the build.
# --------------------------------------------------------------------------
class TestDivergenceLinks(unittest.TestCase):
    REGISTER = "### D-001 — boolean casing\n- **Status:** open\n"

    def test_silent_when_entry_and_marker_agree(self):
        files = [("os9-dev/references/basic09/gotchas.md", "⚠ DIVERGENCE D-001 applies here.\n")]
        self.assertEqual(chk.check_divergence_links(files, self.REGISTER), [])

    def test_flags_entry_with_no_inline_marker(self):
        # The burial case: the register documents it, no claim warns about it.
        files = [("os9-dev/references/basic09/gotchas.md", "Nothing cites the register.\n")]
        findings = chk.check_divergence_links(files, self.REGISTER)
        self.assertEqual(len(findings), 1)
        self.assertIn("D-001", findings[0].message)
        self.assertIn("would never see it", findings[0].message)

    def test_flags_marker_citing_an_undefined_entry(self):
        files = [("os9-dev/references/basic09/gotchas.md", "See DIVERGENCE D-404.\n")]
        findings = chk.check_divergence_links(files, self.REGISTER)
        # D-404 dangles, and D-001 is uncited -- both are real breaks.
        messages = " ".join(f.message for f in findings)
        self.assertIn("D-404", messages)
        self.assertIn("does not define", messages)

    def test_marker_need_not_carry_the_warning_glyph(self):
        # The check keys on the ID, so it survives an editor stripping the emoji.
        files = [("os9-dev/references/basic09/gotchas.md", "DIVERGENCE D-001 without a glyph.\n")]
        self.assertEqual(chk.check_divergence_links(files, self.REGISTER), [])

    def test_register_itself_is_not_scanned_for_markers(self):
        # DIVERGENCES.md quotes its own IDs in the format section; that must not
        # count as a reference file citing them.
        files = [("DIVERGENCES.md", "### D-001 — x\ncited as DIVERGENCE D-001 in the format guide\n")]
        findings = chk.check_divergence_links(files, self.REGISTER)
        self.assertEqual(len(findings), 1)
        self.assertIn("no reference file", findings[0].message)

    def test_absent_register_makes_every_marker_dangle(self):
        files = [("os9-dev/references/basic09/gotchas.md", "DIVERGENCE D-001 here.\n")]
        findings = chk.check_divergence_links(files, None)
        self.assertEqual(len(findings), 1)
        self.assertIn("does not define", findings[0].message)

    def test_resolved_entry_needs_no_inline_marker(self):
        # A closed entry is archival; the row it once flagged is now correct, so
        # forcing a warning onto it would be wrong.
        register = "### D-003 — settled\n- **Status:** resolved\n"
        files = [("os9-dev/references/68k/syscall-reference.md", "no marker here\n")]
        self.assertEqual(chk.check_divergence_links(files, register), [])

    def test_withdrawn_entry_needs_no_inline_marker(self):
        register = "### D-009 — dropped\n- **Status:** withdrawn\n"
        files = [("os9-dev/references/68k/syscall-reference.md", "no marker here\n")]
        self.assertEqual(chk.check_divergence_links(files, register), [])

    def test_open_entry_still_requires_its_marker(self):
        # The closed-entry exemption must not weaken the open-entry rule.
        register = "### D-004 — live\n- **Status:** open\n"
        files = [("os9-dev/references/68k/syscall-reference.md", "no marker here\n")]
        findings = chk.check_divergence_links(files, register)
        self.assertEqual(len(findings), 1)
        self.assertIn("D-004", findings[0].message)

    def test_missing_status_defaults_to_open(self):
        register = "### D-005 — no status line at all\n- some body\n"
        files = [("os9-dev/references/68k/syscall-reference.md", "no marker\n")]
        findings = chk.check_divergence_links(files, register)
        self.assertEqual(len(findings), 1)
        self.assertIn("D-005", findings[0].message)


# --------------------------------------------------------------------------
# orphaned [[memory]] link detection
# --------------------------------------------------------------------------
class TestParseMemoryName(unittest.TestCase):
    def test_reads_name_from_frontmatter(self):
        text = "---\nname: my-memory\ndescription: x\n---\n\nbody\n"
        self.assertEqual(chk.parse_memory_name(text), "my-memory")

    def test_none_when_no_frontmatter(self):
        self.assertIsNone(chk.parse_memory_name("just a body, no frontmatter\n"))


class TestOrphanedMemoryLinks(unittest.TestCase):
    def test_flags_link_to_nonexistent_memory(self):
        files = [("real.md", "---\nname: real\n---\nSee [[ghost-memory]] for detail.\n")]
        findings = chk.check_orphaned_memory_links(files)
        self.assertEqual(len(findings), 1)
        self.assertIn("ghost-memory", findings[0].message)
        self.assertEqual(findings[0].locations, [("real.md", 4)])

    def test_silent_when_link_resolves(self):
        files = [
            ("a.md", "---\nname: a\n---\nSee [[b]].\n"),
            ("b.md", "---\nname: b\n---\nSee [[a]].\n"),
        ]
        self.assertEqual(chk.check_orphaned_memory_links(files), [])

    def test_self_reference_is_not_orphaned(self):
        files = [("a.md", "---\nname: a\n---\nRelated: [[a]].\n")]
        self.assertEqual(chk.check_orphaned_memory_links(files), [])

    def test_backtick_quoted_link_is_a_convention_example_not_a_link(self):
        # "`[[memory]]` detection" describes the linking convention itself.
        files = [("a.md", "---\nname: a\n---\nSee orphaned `[[memory]]` detection.\n")]
        self.assertEqual(chk.check_orphaned_memory_links(files), [])


if __name__ == "__main__":
    unittest.main()
