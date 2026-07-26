"""Tests for the skill-doc consistency checker.

Run from ~/.claude/skills:
    python3 -m unittest discover -s tools/tests

The presence-contradiction tests are built directly from the false positives
the first dogfood run produced against the real docs -- each "must NOT flag"
case is a real sentence pattern that must never be mistaken for a contradiction,
and the "must flag" case is a reintroduced I$Dup-style bug.
"""

import contextlib
import io
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

    def test_lists_a_combined_tier_plus_flag(self):
        """CONFIDENCE-TAGS.md's own legend writes the combined form inside ONE
        backtick span (`Source, Flag`), which is what the convention tells
        authors to use when stronger evidence contradicts a manual. A regex
        matching only a bare `Flag` silently under-reports the inventory."""
        for combined in ("`Source, Flag`", "`Live, Flag`", "`Manual, Flag`"):
            text = "os9exec accepts `{` as a name char. %s\n" % combined
            inv = chk.scan_open_flags(text, "68k/syscall-reference.md", KNOWN)
            self.assertEqual(len(inv), 1, "missed %s" % combined)
            self.assertEqual(inv[0].locations, [("68k/syscall-reference.md", 1)])

    def test_combined_flag_still_skips_resolved(self):
        text = "| **F$Fork** | `Source, Flag` resolved: offset confirmed |\n"
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
# --------------------------------------------------------------------------
# shared-fact agreement
#
# The "must NOT flag" cases are the real notations this corpus uses to quote a
# number it is disowning (an OCR misread, a manual's own typo) and the real
# 6809-vs-68k code collision -- both would otherwise read as drift.
# --------------------------------------------------------------------------
class TestNormaliseHex(unittest.TestCase):
    def test_case_and_leading_zeros_do_not_make_two_values(self):
        self.assertEqual(chk.normalise_hex("$0A"), chk.normalise_hex("$a"))
        self.assertEqual(chk.normalise_hex("$00"), "0")

    def test_distinct_values_stay_distinct(self):
        self.assertNotEqual(chk.normalise_hex("$37"), chk.normalise_hex("$39"))


class TestExtractSharedFacts(unittest.TestCase):
    def test_reads_the_notations_the_corpus_actually_uses(self):
        text = (
            "| `M$Port` | $30 | port address |\n"
            "`PD_PD` $00 (path number), `PD_MOD` $02\n"
            "`PD_OPT`, offset $80\n"
            "`M$Parity` at `$2E`\n"
            "`F$Alarm`($1E)\n"
        )
        got = {(f.symbol, f.value) for f in chk.extract_shared_facts(text, "common/x.md")}
        self.assertEqual(
            got,
            {("M$Port", "30"), ("PD_PD", "0"), ("PD_MOD", "2"),
             ("PD_OPT", "80"), ("M$Parity", "2E"), ("F$Alarm", "1E")},
        )

    def test_ignores_prose_words_without_an_os9_symbol_shape(self):
        text = "The header is 48 bytes and Sync is $87 on the 6809.\n"
        self.assertEqual(chk.extract_shared_facts(text, "common/x.md"), [])

    def test_skips_a_value_the_line_disowns(self):
        text = "it prints `M$Parity` at `$28`. That is a scan error (8-for-E)\n"
        self.assertEqual(chk.extract_shared_facts(text, "common/x.md"), [])

    def test_skips_flagged_and_divergent_lines(self):
        flagged = "| `PD_CNT` | $03 | disputed `Flag` |\n"
        diverged = "`PD_CNT` $03 -- see DIVERGENCE D-002\n"
        self.assertEqual(chk.extract_shared_facts(flagged, "common/x.md"), [])
        self.assertEqual(chk.extract_shared_facts(diverged, "common/x.md"), [])


class TestSharedFactAgreement(unittest.TestCase):
    def _facts(self, *rows):
        return [chk.Fact(sym, chk.normalise_hex(val), f, 1, chk.platform_of(f))
                for sym, val, f in rows]

    def test_flags_the_same_symbol_given_two_values(self):
        findings = chk.check_shared_facts(self._facts(
            ("M$Mode", "$37", "common/memory-and-io.md"),
            ("M$Mode", "$39", "systems/device-drivers.md"),
        ))
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].check, "shared-fact")
        self.assertEqual(findings[0].syscall, "M$Mode")
        self.assertIn("$37", findings[0].message)
        self.assertIn("$39", findings[0].message)

    def test_reports_every_contributing_location(self):
        findings = chk.check_shared_facts(self._facts(
            ("M$Mode", "$37", "common/a.md"),
            ("M$Mode", "$37", "common/b.md"),
            ("M$Mode", "$39", "common/c.md"),
        ))
        self.assertEqual(len(findings[0].locations), 3)

    def test_agreement_is_not_a_finding(self):
        self.assertEqual(chk.check_shared_facts(self._facts(
            ("M$Mode", "$37", "common/a.md"),
            ("M$Mode", "$37", "systems/b.md"),
        )), [])

    def test_same_name_different_architecture_is_legitimate(self):
        """6809 and 68k number their calls differently -- not drift."""
        self.assertEqual(chk.check_shared_facts(self._facts(
            ("F$Link", "$00", "references/6809/syscalls.md"),
            ("F$Link", "$1C", "references/68k/syscall-reference.md"),
        )), [])

    def test_but_a_neutral_file_still_conflicts_with_both(self):
        findings = chk.check_shared_facts(self._facts(
            ("F$Link", "$00", "references/6809/syscalls.md"),
            ("F$Link", "$1C", "references/common/shared.md"),
        ))
        self.assertEqual(len(findings), 1)


class TestExtractDocReferences(unittest.TestCase):
    def test_finds_backticked_and_bare_md_tokens(self):
        line = "| Read | `common/foo.md` | and also bar.md plain |"
        self.assertEqual(chk.extract_doc_references(line), ["common/foo.md", "bar.md"])

    def test_finds_sibling_qualified_token(self):
        line = "sibling os9-dev skill: `references/6809/using-nitros9-repl.md`"
        self.assertEqual(chk.extract_doc_references(line), ["references/6809/using-nitros9-repl.md"])


class TestSkillOf(unittest.TestCase):
    def test_reads_the_skill_from_the_path(self):
        self.assertEqual(chk.skill_of("os9-dev/references/common/ipc.md"), "os9-dev")
        self.assertEqual(chk.skill_of("os9-systems-dev/SKILL.md"), "os9-systems-dev")

    def test_the_two_names_do_not_shadow_each_other(self):
        """`os9-dev` must not match inside `os9-systems-dev`, or every
        systems-dev file would be misattributed to the sibling."""
        self.assertEqual(chk.skill_of("os9-systems-dev/references/x.md"), "os9-systems-dev")

    def test_none_outside_the_skills(self):
        self.assertIsNone(chk.skill_of("DIVERGENCES.md"))
        self.assertIsNone(chk.skill_of("tools/DESIGN.md"))


class TestSkillBoundaries(unittest.TestCase):
    """Each skill is symlinked into ~/.claude/skills/ alone, so every citation
    has to resolve from inside that one directory."""

    SIBLING = ("os9-systems-dev/references/6809-level2-mmu.md", "# MMU\n")

    def test_flags_a_root_doc_cited_from_the_payload(self):
        # The real defect this check was written for: SKILL.md pointed at a
        # file that is not inside the installed skill.
        files = [("os9-dev/SKILL.md", "See `SOURCE-AUTHORITY.md` for authority.\n")]
        findings = chk.check_skill_boundaries(files)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].check, "skill-boundary")
        self.assertIn("repo root", findings[0].message)
        self.assertEqual(findings[0].locations, [("os9-dev/SKILL.md", 1)])

    def test_flags_every_root_doc(self):
        for doc in ("DIVERGENCES.md", "SOURCE-AUTHORITY.md", "README.md"):
            files = [("os9-dev/references/common/ipc.md", "see `%s`\n" % doc)]
            self.assertEqual(len(chk.check_skill_boundaries(files)), 1, doc)

    def test_root_doc_named_outside_a_skill_is_fine(self):
        """tools/ and the root docs themselves may cite each other freely."""
        files = [("tools/DESIGN.md", "See `SOURCE-AUTHORITY.md`.\n")]
        self.assertEqual(chk.check_skill_boundaries(files), [])

    def test_flags_a_bare_sibling_filename(self):
        files = [
            ("os9-dev/references/6809/utility-usage.md", "see `6809-level2-mmu.md` for DAT\n"),
            self.SIBLING,
        ]
        findings = chk.check_skill_boundaries(files)
        self.assertEqual(len(findings), 1)
        self.assertIn("os9-systems-dev", findings[0].message)

    def test_sibling_named_on_the_same_line_resolves(self):
        files = [
            ("os9-dev/references/6809/utility-usage.md",
             "see `os9-systems-dev`'s `6809-level2-mmu.md` for DAT\n"),
            self.SIBLING,
        ]
        self.assertEqual(chk.check_skill_boundaries(files), [])

    def test_sibling_named_on_the_previous_line_resolves(self):
        """The qualifier routinely wraps -- "Full mechanism: `os9-systems-dev`"
        ends one line and the filename starts the next."""
        files = [
            ("os9-dev/references/common/os9-mental-model.md",
             "Full mechanism: `os9-systems-dev`\nskill's `kernel-internals.md`.\n"),
            ("os9-systems-dev/references/kernel-internals.md", "# Kernel\n"),
        ]
        self.assertEqual(chk.check_skill_boundaries(files), [])

    def test_citing_a_file_in_your_own_skill_needs_no_qualifier(self):
        files = [
            ("os9-dev/references/common/ipc.md", "see `error-codes.md`\n"),
            ("os9-dev/references/common/error-codes.md", "# Errors\n"),
        ]
        self.assertEqual(chk.check_skill_boundaries(files), [])

    def test_flags_shared_content_duplicated_into_both_skills(self):
        files = [
            ("os9-dev/references/CONFIDENCE-TAGS.md", "# Tags\n"),
            ("os9-systems-dev/references/CONFIDENCE-TAGS.md", "# Tags\n"),
        ]
        findings = chk.check_skill_boundaries(files)
        self.assertEqual(len(findings), 1)
        self.assertIn("os9-dev alone", findings[0].message)

    def test_per_skill_manifests_may_exist_in_both(self):
        """INDEX/SOURCES/SKILL are each skill's own; only shared *content*
        is supposed to live in os9-dev alone."""
        files = [
            ("os9-dev/references/INDEX.md", "# Index\n"),
            ("os9-systems-dev/references/INDEX.md", "# Index\n"),
            ("os9-dev/SOURCES.md", "# Sources\n"),
            ("os9-systems-dev/SOURCES.md", "# Sources\n"),
        ]
        self.assertEqual(chk.check_skill_boundaries(files), [])

    def test_systems_dev_may_depend_on_os9_dev(self):
        """The allowed direction: shared content lives in os9-dev and the
        sibling cites it by path."""
        files = [
            ("os9-systems-dev/SKILL.md", "Legend: `os9-dev/references/CONFIDENCE-TAGS.md`.\n"),
            ("os9-dev/references/CONFIDENCE-TAGS.md", "# Tags\n"),
        ]
        self.assertEqual(chk.check_skill_boundaries(files), [])


class TestNoInventoryFlag(unittest.TestCase):
    """The pre-commit hook passes --no-inventory so a failure shows the finding,
    not ~16 lines of unrelated `Flag` worklist above the prompt."""

    def _corpus(self, extra=""):
        root = tempfile.mkdtemp()
        os.makedirs(os.path.join(root, "68k"))
        with open(os.path.join(root, chk.CONFIDENCE_TAGS_FILE), "w") as handle:
            handle.write("| Tag | Meaning |\n|---|---|\n| `Live` | ran it |\n| `Flag` | disagree |\n")
        with open(os.path.join(root, "68k", "s.md"), "w") as handle:
            handle.write("**F$Fork** forks. `Live`, `Flag` disputed.\n" + extra)
        return root

    def test_inventory_is_printed_by_default(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = chk.main([self._corpus()])
        self.assertEqual(code, 0)
        self.assertIn("divergence inventory", out.getvalue())

    def test_no_inventory_suppresses_it_but_keeps_findings(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = chk.main([self._corpus("`LIVE` is a miswritten tag.\n"), "--no-inventory"])
        printed = out.getvalue()
        self.assertEqual(code, 1)
        self.assertNotIn("divergence inventory", printed)
        self.assertIn("miswritten", printed)

    def test_flag_order_does_not_matter(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            chk.main(["--no-inventory", self._corpus()])
        self.assertNotIn("divergence inventory", out.getvalue())


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


class TestQualifiedReferences(unittest.TestCase):
    """A directory-qualified `dir/file.md` pointer must name the real directory.

    Complements check_cross_references: that one asks "does this file exist at
    all", scoped to INDEX.md. This one asks "is the path right", and can run over
    every payload file without false-positiving on other repos' documents,
    because a reference whose basename is unknown is skipped entirely.
    """

    KNOWN = {
        "os9-dev/references/basic09/gotchas.md",
        "os9-dev/references/common/module-format.md",
        "os9-dev/references/CONFIDENCE-TAGS.md",
    }

    def test_flags_wrong_directory(self):
        files = [("os9-dev/references/c/os9-c-cheatsheet.md", "See `common/gotchas.md`.\n")]
        findings = chk.check_qualified_references(files, self.KNOWN)
        self.assertEqual(len(findings), 1)
        self.assertIn("common/gotchas.md", findings[0].message)
        self.assertIn("basic09/gotchas.md", findings[0].message)

    def test_silent_when_directory_correct(self):
        files = [("os9-dev/references/c/os9-c-cheatsheet.md", "See `basic09/gotchas.md`.\n")]
        self.assertEqual(chk.check_qualified_references(files, self.KNOWN), [])

    def test_silent_for_bare_basename(self):
        # Bare names are the INDEX.md convention and are check_cross_references' job.
        files = [("os9-dev/references/c/os9-c-cheatsheet.md", "See `gotchas.md`.\n")]
        self.assertEqual(chk.check_qualified_references(files, self.KNOWN), [])

    def test_silent_for_unknown_basename(self):
        # Another repo's document -- no opinion can be formed, so none is offered.
        files = [("os9-dev/references/6809/STATUS.md", "See `reports/dogfood-2026-07-18.md`.\n")]
        self.assertEqual(chk.check_qualified_references(files, self.KNOWN), [])

    def test_sibling_qualified_path_resolves(self):
        files = [("os9-systems-dev/references/INDEX.md", "See `os9-dev/references/CONFIDENCE-TAGS.md`.\n")]
        self.assertEqual(chk.check_qualified_references(files, self.KNOWN), [])


LONG_A = (
    "The OS-9 shell treats a leading space in the line editor as an instruction to "
    "insert the line, and without it the text is parsed as an editor command that "
    "usually fails with a What? message, which is easy to misread as a syntax error "
    "in the program itself rather than in the editor."
)
LONG_B = LONG_A.replace("usually fails", "normally fails").replace("easy to", "simple to")
LONG_OTHER = (
    "Module CRC accumulation covers the whole module including the header, while the "
    "header parity word protects only the universal header, so a corrupted stack size "
    "passes the parity check and is caught solely by the CRC when the loader runs it."
)


class TestDuplicateParagraphs(unittest.TestCase):
    def test_flags_near_verbatim_paragraph_across_two_files(self):
        files = [("a/one.md", LONG_A + "\n"), ("b/two.md", LONG_B + "\n")]
        dupes = chk.find_duplicate_paragraphs(files)
        self.assertEqual(len(dupes), 1)
        self.assertIn("one.md", dupes[0].message)
        self.assertIn("two.md", dupes[0].message)

    def test_silent_for_dissimilar_paragraphs(self):
        files = [("a/one.md", LONG_A + "\n"), ("b/two.md", LONG_OTHER + "\n")]
        self.assertEqual(chk.find_duplicate_paragraphs(files), [])

    def test_silent_within_a_single_file(self):
        # Repeating yourself inside one file is a different (editorial) problem.
        files = [("a/one.md", LONG_A + "\n\n" + LONG_B + "\n")]
        self.assertEqual(chk.find_duplicate_paragraphs(files), [])

    def test_silent_for_short_paragraphs(self):
        # Short repeated lines ("See also: X") are idiomatic, not duplication.
        files = [("a/one.md", "See the sibling skill.\n"), ("b/two.md", "See the sibling skill.\n")]
        self.assertEqual(chk.find_duplicate_paragraphs(files), [])

    def test_ignores_fenced_code_and_table_rows(self):
        # A worked example intentionally reproduced alongside its output, and table
        # rows sharing a column vocabulary, are both expected to repeat.
        block = "```\n" + LONG_A + "\n```\n"
        rows = "\n".join("| " + LONG_A + " |" for _ in range(2)) + "\n"
        files = [("a/one.md", block), ("b/two.md", block), ("c/three.md", rows)]
        self.assertEqual(chk.find_duplicate_paragraphs(files), [])


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
