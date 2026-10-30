import subprocess
import tempfile
import unittest
from pathlib import Path

import sync_upstream as sync


class PolicyTests(unittest.TestCase):
    def test_status_record_keeps_spaces_and_skips_renames(self) -> None:
        blob = b"UU my file.txt\0R  b file.txt\0a.txt\0M  clean.go\0"
        self.assertEqual(sync.parse_status_z(blob), [("UU", "my file.txt")])

    def test_structured_files_are_not_line_merged(self) -> None:
        self.assertEqual(sync.merge_kind("web/src/i18n/locales/en.json"), "locale")
        self.assertEqual(sync.merge_kind("web/package.json"), "human")
        self.assertEqual(sync.merge_kind(".github/workflows/ci.yml"), "human")
        self.assertEqual(sync.merge_kind("go.sum"), "regen")
        self.assertEqual(sync.merge_kind("main.go"), "text")

    def test_unmerged_record_keeps_spaces_in_the_path(self) -> None:
        blob = b"100644 abcdef 1\tfoo/my file.go\0"
        self.assertEqual(sync.parse_unmerged_z(blob), [("1", "foo/my file.go")])

    def test_adjacent_edit_survives_an_overlapping_line(self) -> None:
        base = "keep\nshared\ntail\n"
        ours = "keep ours\nshared OURS\ntail\n"
        theirs = "keep\nshared THEIRS\ntail\n"
        resolved, dropped = sync.merge_texts(base, ours, theirs, keep_ours=False)
        self.assertEqual(resolved, "keep ours\nshared THEIRS\ntail\n")
        self.assertEqual(dropped, ["shared OURS\n"])

    def test_ledger_keeps_only_the_overlapping_line(self) -> None:
        base = "flag=on\nonly-upstream\n"
        ours = "flag=off\nonly-upstream\n"
        theirs = "flag=patched\nonly-upstream changed\n"
        resolved, dropped = sync.merge_texts(base, ours, theirs, keep_ours=True)
        self.assertEqual(resolved, "flag=off\nonly-upstream changed\n")
        self.assertEqual(dropped, ["flag=patched\n"])

    def test_block_replacement_keeps_a_later_upstream_insert(self) -> None:
        base = "alpha\nbeta\ngamma\n"
        ours = "ours-block\ngamma\n"
        theirs = "alpha\nbeta\ninserted\ngamma\n"
        resolved, dropped = sync.merge_texts(base, ours, theirs, keep_ours=False)
        self.assertEqual(resolved, "ours-block\ninserted\ngamma\n")
        self.assertEqual(dropped, [])

    def test_locale_keeps_one_sided_upstream_edits(self) -> None:
        base = '{"translation": {"A": "old", "B": "same", "D": "same", "G": "gone"}}\n'
        ours = '{"translation": {"A": "ours", "B": "same", "D": "same", "E": "added"}}\n'
        theirs = '{"translation": {"A": "theirs", "B": "same", "C": "new", "D": "fixed"}}\n'
        merged, dropped = sync.merge_locale(base, ours, theirs)
        doc = __import__("json").loads(merged)["translation"]
        self.assertEqual(doc["A"], "ours")
        self.assertEqual(doc["B"], "same")
        self.assertEqual(doc["C"], "new")
        self.assertEqual(doc["D"], "fixed")
        self.assertEqual(doc["E"], "added")
        self.assertNotIn("G", doc)
        self.assertTrue(any(item.startswith("A=") for item in dropped))

    def test_inserts_at_the_same_point_are_both_kept(self) -> None:
        base = "head\n"
        ours = "head\nours\n"
        theirs = "head\ntheirs\n"
        resolved, dropped = sync.merge_texts(base, ours, theirs, keep_ours=False)
        self.assertEqual(resolved, "head\ntheirs\nours\n")
        self.assertEqual(dropped, [])

    def test_disjoint_replacements_are_both_kept(self) -> None:
        base = "a\nb\nc\nd\n"
        ours = "X\nc\nd\n"
        theirs = "a\nb\nY\n"
        resolved, dropped = sync.merge_texts(base, ours, theirs, keep_ours=False)
        self.assertEqual(resolved, "X\nY\n")
        self.assertEqual(dropped, [])

    def test_overlapping_unequal_spans_are_emitted_once(self) -> None:
        base = "a\nb\nc\nd\ne\n"
        ours = "X\nd\ne\n"
        theirs = "a\nY\ne\n"
        resolved, dropped = sync.merge_texts(base, ours, theirs, keep_ours=False)
        self.assertEqual(resolved, "a\nY\ne\n")
        self.assertEqual(dropped, ["X\nd\n"])
        resolved, dropped = sync.merge_texts(base, ours, theirs, keep_ours=True)
        self.assertEqual(resolved, "X\nd\ne\n")
        self.assertEqual(dropped, ["a\nY\n"])

    def test_straddling_replacements_are_emitted_once(self) -> None:
        base = "a\nb\nc\nd\ne\n"
        ours = "a\nb\nZ\n"
        theirs = "X\nY\nd\ne\n"
        resolved, dropped = sync.merge_texts(base, ours, theirs, keep_ours=False)
        self.assertEqual(resolved, "X\nY\nd\ne\n")
        self.assertEqual(dropped, ["a\nb\nZ\n"])
        resolved, dropped = sync.merge_texts(base, ours, theirs, keep_ours=True)
        self.assertEqual(resolved, "a\nb\nZ\n")
        self.assertEqual(dropped, ["X\nY\nd\ne\n"])

    def test_one_sided_neighbor_stays_beside_an_overlapping_line(self) -> None:
        base = "func Foo() int {\n\treturn 1\n}\n"
        ours = "func Foo() int {\n\treturn 2\n}\n"
        theirs = "func Foo() string {\n\treturn \"x\"\n}\n"
        resolved, _dropped = sync.merge_texts(base, ours, theirs, keep_ours=True)
        self.assertEqual(resolved, "func Foo() string {\n\treturn 2\n}\n")
        resolved, dropped = sync.merge_texts(base, ours, theirs, keep_ours=False)
        self.assertEqual(resolved, theirs)
        self.assertEqual(dropped, ["\treturn 2\n"])

    def test_go_mod_unions_requires_and_keeps_upstream_version(self) -> None:
        ours = "module example.com/app\n\ngo 1.26\n\nrequire (\n\texample.com/ours v1.0.0\n\texample.com/both v1.2.0\n)\n"
        theirs = "module example.com/app\n\ngo 1.26\n\nrequire (\n\texample.com/both v9.0.0\n\texample.com/up v1.0.0\n)\n"
        merged = sync.merge_go_mod(ours, theirs, {"example.com/both": "v1.2.3"})
        self.assertIn("example.com/ours v1.0.0", merged)
        self.assertIn("example.com/up v1.0.0", merged)
        self.assertIn("example.com/both v1.2.3", merged)
        self.assertIn("module example.com/app", merged)

    def test_single_line_require_joins_the_union(self) -> None:
        ours = "module example.com/app\n\ngo 1.26\n\nrequire example.com/pinned v1.0.0\n"
        theirs = "module example.com/app\n\ngo 1.26\n\nrequire example.com/pinned v9.0.0\n"
        merged = sync.merge_go_mod(ours, theirs, {"example.com/pinned": "v1.2.3"})
        self.assertEqual(merged.count("example.com/pinned"), 1)
        self.assertIn("example.com/pinned v1.2.3", merged)

    def test_pin_drift_is_the_modules_tidy_failed_to_keep(self) -> None:
        self.assertEqual(sync.pin_drift({"example.com/pinned": "v1.2.3"}, {}, {"example.com/pinned": "v1.2.3"}), ["example.com/pinned"])
        self.assertEqual(
            sync.pin_drift({"example.com/pinned": "v1.2.3"}, {"example.com/pinned": "v9.0.0"}, {"example.com/pinned": "v1.2.3"}),
            ["example.com/pinned"],
        )
        self.assertEqual(sync.pin_drift({"example.com/pinned": "v1.2.3"}, {"example.com/pinned": "v1.2.3"}, {"example.com/pinned": "v1.2.3"}), [])

    def test_pass_count_must_match_the_named_tests(self) -> None:
        sync.require_named_passes("--- PASS: TestA\n--- PASS: TestA/sub\n--- PASS: TestB\n", ["TestA", "TestB"])
        with self.assertRaises(sync.Stop) as caught:
            sync.require_named_passes("--- PASS: TestA\n--- PASS: TestA/sub\n--- PASS: TestB\n", ["TestA", "TestB", "TestC"])
        self.assertEqual(caught.exception.code, 1)

    def test_one_sided_insert_inside_a_replacement_is_kept(self) -> None:
        base = "a\nb\nc\nd\n"
        ours = "a\nX\nd\n"
        theirs = "a\nb\nY\nc\nd\n"
        for keep in (False, True):
            resolved, dropped = sync.merge_texts(base, ours, theirs, keep_ours=keep)
            self.assertEqual(resolved, "a\nX\nY\nd\n")
            self.assertEqual(dropped, [])

    def test_shared_insert_lines_are_not_repeated(self) -> None:
        base = "a\nc\n"
        short = "a\nL1\nc\n"
        long = "a\nL1\nL2\nc\n"
        for ours, theirs in ((short, long), (long, short)):
            for keep_ours in (False, True):
                resolved, dropped = sync.merge_texts(base, ours, theirs, keep_ours=keep_ours)
                self.assertEqual(resolved, long)
                self.assertEqual(dropped, [])

    def test_shared_insert_line_does_not_interleave_blocks(self) -> None:
        base = "a\n"
        ours = "a\nA\ncommon\nB\n"
        theirs = "a\nC\ncommon\nD\n"
        resolved, dropped = sync.merge_texts(base, ours, theirs, keep_ours=False)
        self.assertEqual(resolved, "a\nC\ncommon\nD\nA\ncommon\nB\n")
        self.assertEqual(dropped, [])

    def test_shared_closing_brace_keeps_both_insert_blocks(self) -> None:
        base = "head\n"
        ours = "head\nO1\n}\n"
        theirs = "head\nT1\n}\n"
        resolved, dropped = sync.merge_texts(base, ours, theirs, keep_ours=False)
        self.assertEqual(resolved, "head\nT1\n}\nO1\n}\n")
        self.assertEqual(dropped, [])

    def test_ambiguous_eof_move_requires_human_resolution(self) -> None:
        base = "r1\nr2\nr3\n"
        ours = "r2\nr3\nr1\n"
        theirs = "r1 edited\nr2\nr3\n"
        for keep_ours in (False, True):
            with self.assertRaises(sync.Stop) as caught:
                sync.merge_texts(base, ours, theirs, keep_ours=keep_ours)
            self.assertEqual(caught.exception.code, 3)
            self.assertIn("insertion", str(caught.exception))

    def test_new_brace_insert_requires_human_resolution(self) -> None:
        base = "a\n}\nb\n"
        ours = "a\nb\nfunc() {\nbody\n}\n"
        theirs = "a\n} patched\nb\n"
        with self.assertRaises(sync.Stop) as caught:
            sync.merge_texts(base, ours, theirs, keep_ours=False)
        self.assertEqual(caught.exception.code, 3)
        self.assertIn("insertion", str(caught.exception))

    def test_insert_at_deleted_block_boundary_is_kept(self) -> None:
        base = "a\nb\nc\n"
        deleted = "a\n"
        inserted_before = "a\nY\nb\nc\n"
        for ours, theirs in ((deleted, inserted_before), (inserted_before, deleted)):
            resolved, dropped = sync.merge_texts(base, ours, theirs, keep_ours=False)
            self.assertEqual(resolved, "a\nY\n")
            self.assertEqual(dropped, [])

    def test_insert_strictly_inside_deleted_block_requires_human_resolution(self) -> None:
        base = "a\nb\nc\nd\n"
        deleted = "a\nd\n"
        inserted_inside = "a\nb\nY\nc\nd\n"
        for ours, theirs in ((deleted, inserted_inside), (inserted_inside, deleted)):
            for keep_ours in (False, True):
                with self.assertRaises(sync.Stop) as caught:
                    sync.merge_texts(base, ours, theirs, keep_ours=keep_ours)
                self.assertEqual(caught.exception.code, 3)
                self.assertIn("deletion span", str(caught.exception))

    def test_eof_insert_blocks_without_newlines_do_not_concatenate(self) -> None:
        base = "head\n"
        with self.assertRaises(sync.Stop) as caught:
            sync.merge_texts(base, "head\nours", "head\ntheirs", keep_ours=False)
        self.assertEqual(caught.exception.code, 3)
        self.assertIn("newline", str(caught.exception))

    def test_span_body_keeps_insert_at_later_span_start(self) -> None:
        base = ["a\n", "b\n", "c\n", "d\n"]
        ops = {0: ("span", 0), 1: ("span", 0), 2: ("span", 1), 3: ("span", 1)}
        spans = [(0, 2, ["X\n"]), (2, 4, ["Y\n"])]
        inserts = [[], [], ["between\n"], [], []]
        body = sync._span_body(base, ops, spans, inserts, 0, 4)
        self.assertEqual(body, ["X\n", "between\n", "Y\n"])

    def test_overlapping_delete_and_replace_are_one_region(self) -> None:
        base = "a\nb\nc\nd\n"
        deleted = "c\nd\n"
        replaced = "a\nY\nd\n"
        resolved, _dropped = sync.merge_texts(base, deleted, replaced, keep_ours=False)
        self.assertEqual(resolved, replaced)
        resolved, _dropped = sync.merge_texts(base, deleted, replaced, keep_ours=True)
        self.assertEqual(resolved, deleted)
        resolved, _dropped = sync.merge_texts(base, replaced, deleted, keep_ours=True)
        self.assertEqual(resolved, replaced)
        resolved, _dropped = sync.merge_texts(base, replaced, deleted, keep_ours=False)
        self.assertEqual(resolved, deleted)

    def test_inserted_line_inside_a_signature_change_keeps_our_return(self) -> None:
        base = "func Foo() int {\n\treturn 1\n}\n"
        ours = "func Foo() int {\n\treturn 2\n}\n"
        theirs = "func Foo() string {\n\tlog()\n\treturn \"x\"\n}\n"
        resolved, dropped = sync.merge_texts(base, ours, theirs, keep_ours=True)
        self.assertEqual(resolved, "func Foo() string {\n\tlog()\n\treturn 2\n}\n")
        self.assertEqual(dropped, ["\treturn \"x\"\n"])
        resolved, dropped = sync.merge_texts(base, ours, theirs, keep_ours=False)
        self.assertEqual(resolved, theirs)
        self.assertIn("\treturn 2\n", dropped)

    def test_fresh_report_discards_a_previous_file(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            subprocess.run(["git", "-C", str(root), "init", "-b", "main"], check=True, capture_output=True)
            path = sync._report_file(root)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("old conflict\n", encoding="utf-8")
            self.assertEqual(sync.load_report(root, resume=False), [])
            self.assertFalse(path.exists())
            path.write_text("kept\n", encoding="utf-8")
            self.assertEqual(sync.load_report(root, resume=True), ["kept"])

    def test_go_mod_stops_when_the_go_line_differs(self) -> None:
        ours = "module example.com/app\n\ngo 1.26\n\nrequire (\n\texample.com/a v1.0.0\n)\n"
        theirs = "module example.com/app\n\ngo 1.25\n\nrequire (\n\texample.com/a v1.0.0\n)\n"
        with self.assertRaises(sync.Stop) as caught:
            sync.merge_go_mod(ours, theirs, {})
        self.assertEqual(caught.exception.code, 3)

    def test_single_line_and_block_require_still_merge(self) -> None:
        ours = "module example.com/app\n\ngo 1.26\n\nrequire example.com/lib v1.0.0\n"
        theirs = "module example.com/app\n\ngo 1.26\n\nrequire (\n\texample.com/lib v2.0.0\n)\n"
        merged = sync.merge_go_mod(ours, theirs, {})
        self.assertIn("example.com/lib v2.0.0", merged)
        self.assertEqual(merged.count("example.com/lib"), 1)
        self.assertNotIn("require example.com/lib", merged)

    def test_require_comments_are_not_modules(self) -> None:
        text = "module example.com/app\n\ngo 1.26\n\nrequire (\n\t// indirect\n\texample.com/a v1.0.0\n)\n"
        self.assertEqual(sync._require_map(text), {"example.com/a": "v1.0.0"})

    def test_dotted_ledger_paths_stay_on_our_side(self) -> None:
        self.assertTrue(sync.is_ledger(".env.example"))
        self.assertTrue(sync.is_ledger(".gitignore"))
        self.assertTrue(sync.is_ledger("docs/site/guide.md"))
        self.assertFalse(sync.is_ledger("controller/other.go"))

    def test_delete_decisions(self) -> None:
        self.assertEqual(sync.decide_delete("UD", "Dockerfile"), "keep-ours")
        self.assertEqual(sync.decide_delete("UD", "controller/other.go"), "accept-delete")
        self.assertEqual(sync.decide_delete("DU", "docs/site/a.md"), "keep-deleted")
        self.assertEqual(sync.decide_delete("DU", "controller/other.go"), "take-theirs")
        self.assertEqual(sync.decide_delete("AA", "Dockerfile"), "human")


class MergeTests(unittest.TestCase):
    def test_real_merge_keeps_ledger_hunk_and_upstream_overlap(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            run = lambda *args: subprocess.run(["git", "-c", "user.name=sync-test", "-c", "user.email=sync-test@example.com", "-C", str(root), *args], check=True, text=True, capture_output=True)
            run("init", "-b", "main")
            (root / "Dockerfile").write_text("flag=on\n", encoding="utf-8")
            (root / "other.txt").write_text("keep\nshared\ntail\n", encoding="utf-8")
            run("add", "Dockerfile", "other.txt")
            run("commit", "-m", "base")
            run("checkout", "-b", "upstream")
            (root / "Dockerfile").write_text("flag=patched\n", encoding="utf-8")
            (root / "other.txt").write_text("keep\nshared THEIRS\ntail\n", encoding="utf-8")
            run("add", "Dockerfile", "other.txt")
            run("commit", "-m", "upstream")
            run("checkout", "main")
            (root / "Dockerfile").write_text("flag=off\n", encoding="utf-8")
            (root / "other.txt").write_text("keep ours\nshared OURS\ntail\n", encoding="utf-8")
            run("add", "Dockerfile", "other.txt")
            run("commit", "-m", "ours")
            merged = subprocess.run(["git", "-C", str(root), "-c", "merge.conflictStyle=merge", "merge", "--no-commit", "--no-ff", "upstream"], text=True, capture_output=True)
            self.assertEqual(merged.returncode, 1, merged.stderr)
            sync.resolve_worktree(root, {}, report := [])
            sync.ensure_clean_resolution(root)
            self.assertEqual((root / "Dockerfile").read_text(encoding="utf-8"), "flag=off\n")
            self.assertEqual((root / "other.txt").read_text(encoding="utf-8"), "keep ours\nshared THEIRS\ntail\n")
            self.assertTrue(any("flag=patched" in line for line in report))
            self.assertTrue(any("shared OURS" in line for line in report))
            subprocess.run(["git", "-C", str(root), "update-ref", "refs/remotes/upstream/main", "upstream"], check=True)
            sync.commit_merge(root)
            parents = subprocess.run(["git", "-C", str(root), "rev-list", "--parents", "-n", "1", "HEAD"], check=True, text=True, capture_output=True).stdout.split()
            self.assertEqual(len(parents), 3)

    def test_reapply_go_mod_uses_upstream_version_after_a_clean_merge(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            run = lambda *args: subprocess.run(["git", "-c", "user.name=sync-test", "-c", "user.email=sync-test@example.com", "-C", str(root), *args], check=True, text=True, capture_output=True)
            run("init", "-b", "main")
            (root / "go.mod").write_text("module example.com/app\n\ngo 1.26\n\nrequire example.com/a v1.0.0\n", encoding="utf-8")
            (root / "keep.txt").write_text("same\n", encoding="utf-8")
            run("add", "go.mod", "keep.txt")
            run("commit", "-m", "base")
            run("checkout", "-b", "upstream")
            (root / "go.mod").write_text("module example.com/app\n\ngo 1.26\n\nrequire example.com/a v9.0.0\n", encoding="utf-8")
            (root / "keep.txt").write_text("upstream\n", encoding="utf-8")
            run("add", "go.mod", "keep.txt")
            run("commit", "-m", "upstream")
            run("checkout", "main")
            (root / "go.mod").write_text("module example.com/app\n\ngo 1.26\n\nrequire example.com/a v2.0.0\n", encoding="utf-8")
            (root / "keep.txt").write_text("ours\n", encoding="utf-8")
            run("add", "go.mod", "keep.txt")
            run("commit", "-m", "ours")
            merged = subprocess.run(["git", "-C", str(root), "-c", "merge.conflictStyle=merge", "merge", "--no-commit", "--no-ff", "upstream"], text=True, capture_output=True)
            self.assertIn(merged.returncode, {0, 1}, merged.stderr)
            report: list[str] = []
            sync.reapply_go_mods(root, {}, report)
            text = (root / "go.mod").read_text(encoding="utf-8")
            self.assertIn("example.com/a v9.0.0", text)
            self.assertNotIn("example.com/a v2.0.0", text)

    def test_clean_ledger_delete_is_restored(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            run = lambda *args: subprocess.run(["git", "-c", "user.name=sync-test", "-c", "user.email=sync-test@example.com", "-C", str(root), *args], check=True, text=True, capture_output=True)
            run("init", "-b", "main")
            (root / "Dockerfile").write_text("flag=off\n", encoding="utf-8")
            (root / "other.txt").write_text("keep\n", encoding="utf-8")
            run("add", "Dockerfile", "other.txt")
            run("commit", "-m", "base")
            run("checkout", "-b", "upstream")
            run("rm", "Dockerfile")
            (root / "other.txt").write_text("upstream\n", encoding="utf-8")
            run("add", "other.txt")
            run("commit", "-m", "upstream")
            run("checkout", "main")
            (root / "other.txt").write_text("ours\n", encoding="utf-8")
            run("add", "other.txt")
            run("commit", "-m", "ours")
            merged = subprocess.run(["git", "-C", str(root), "-c", "merge.conflictStyle=merge", "merge", "--no-commit", "--no-ff", "upstream"], text=True, capture_output=True)
            self.assertIn(merged.returncode, {0, 1}, merged.stderr)
            self.assertFalse((root / "Dockerfile").exists())
            sync.restore_ledger_deletes(root, report := [])
            self.assertEqual((root / "Dockerfile").read_text(encoding="utf-8"), "flag=off\n")
            self.assertTrue(any("Dockerfile" in line for line in report))

    def test_resume_keeps_a_human_resolved_go_mod(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            run = lambda *args: subprocess.run(["git", "-c", "user.name=sync-test", "-c", "user.email=sync-test@example.com", "-C", str(root), *args], check=True, text=True, capture_output=True)
            run("init", "-b", "main")
            (root / "go.mod").write_text("module example.com/app\n\ngo 1.26\n\nrequire example.com/a v1.0.0\n", encoding="utf-8")
            (root / "keep.txt").write_text("same\n", encoding="utf-8")
            run("add", "go.mod", "keep.txt")
            run("commit", "-m", "base")
            run("checkout", "-b", "upstream")
            (root / "go.mod").write_text("module example.com/app\n\ngo 1.26\n\ntoolchain go1.26.1\n\nrequire example.com/a v9.0.0\n", encoding="utf-8")
            run("add", "go.mod")
            run("commit", "-m", "upstream")
            run("checkout", "main")
            (root / "go.mod").write_text("module example.com/app\n\ngo 1.26\n\nrequire example.com/a v2.0.0\n", encoding="utf-8")
            run("add", "go.mod")
            run("commit", "-m", "ours")
            merged = subprocess.run(["git", "-C", str(root), "-c", "merge.conflictStyle=merge", "merge", "--no-commit", "--no-ff", "upstream"], text=True, capture_output=True)
            self.assertIn(merged.returncode, {0, 1}, merged.stderr)
            human = "module example.com/app\n\ngo 1.26\n\ntoolchain go1.26.1\n\nrequire example.com/a v2.0.0\n"
            (root / "go.mod").write_text(human, encoding="utf-8")
            run("add", "go.mod")
            sync.reapply_go_mods(root, {}, [], resume=True)
            self.assertEqual((root / "go.mod").read_text(encoding="utf-8"), human)

    def test_ledger_rename_stops_for_a_human(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            run = lambda *args: subprocess.run(["git", "-c", "user.name=sync-test", "-c", "user.email=sync-test@example.com", "-C", str(root), *args], check=True, text=True, capture_output=True)
            run("init", "-b", "main")
            (root / "Dockerfile").write_text("flag=off\n", encoding="utf-8")
            (root / "other.txt").write_text("keep\n", encoding="utf-8")
            run("add", "Dockerfile", "other.txt")
            run("commit", "-m", "base")
            run("checkout", "-b", "upstream")
            run("mv", "Dockerfile", "Dockerfile.legacy")
            (root / "other.txt").write_text("upstream\n", encoding="utf-8")
            run("add", "-A")
            run("commit", "-m", "upstream")
            run("checkout", "main")
            (root / "other.txt").write_text("ours\n", encoding="utf-8")
            run("add", "other.txt")
            run("commit", "-m", "ours")
            merged = subprocess.run(["git", "-C", str(root), "-c", "merge.conflictStyle=merge", "merge", "--no-commit", "--no-ff", "upstream"], text=True, capture_output=True)
            self.assertIn(merged.returncode, {0, 1}, merged.stderr)
            with self.assertRaises(sync.Stop) as caught:
                sync.restore_ledger_deletes(root, [])
            self.assertEqual(caught.exception.code, 3)
            self.assertIn("Dockerfile", str(caught.exception))


    def test_ledger_rename_resume_uses_report_marker(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            run = lambda *args: subprocess.run(["git", "-c", "user.name=sync-test", "-c", "user.email=sync-test@example.com", "-C", str(root), *args], check=True, text=True, capture_output=True)
            run("init", "-b", "main")
            (root / "Dockerfile").write_text("flag=off\n", encoding="utf-8")
            run("add", "Dockerfile")
            run("commit", "-m", "base")
            run("mv", "Dockerfile", "Dockerfile.legacy")
            report: list[str] = []
            with self.assertRaises(sync.Stop):
                sync.restore_ledger_deletes(root, report, resume=False)
            sync.restore_ledger_deletes(root, report, resume=True)
            self.assertFalse((root / "Dockerfile").exists())
            self.assertTrue((root / "Dockerfile.legacy").exists())

    def test_low_similarity_ledger_replacement_stops_once(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            run = lambda *args: subprocess.run(["git", "-c", "user.name=sync-test", "-c", "user.email=sync-test@example.com", "-C", str(root), *args], check=True, text=True, capture_output=True)
            run("init", "-b", "main")
            (root / "Dockerfile").write_text("old\n", encoding="utf-8")
            run("add", "Dockerfile")
            run("commit", "-m", "base")
            run("rm", "Dockerfile")
            (root / "replacement.txt").write_text("completely different\n", encoding="utf-8")
            run("add", "replacement.txt")
            report: list[str] = []
            with self.assertRaises(sync.Stop):
                sync.restore_ledger_deletes(root, report, resume=False)
            sync.restore_ledger_deletes(root, report, resume=True)
            self.assertFalse((root / "Dockerfile").exists())

    def test_finish_rebuilds_go_mod_before_an_unrelated_human_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            run = lambda *args: subprocess.run(["git", "-c", "user.name=sync-test", "-c", "user.email=sync-test@example.com", "-C", str(root), *args], check=True, text=True, capture_output=True)
            run("init", "-b", "main")
            (root / "go.mod").write_text("module example.com/app\n\ngo 1.26\n\nrequire example.com/a v1.0.0\n", encoding="utf-8")
            (root / "config.json").write_text('{"value":"base"}\n', encoding="utf-8")
            run("add", "go.mod", "config.json")
            run("commit", "-m", "base")
            run("checkout", "-b", "upstream")
            (root / "go.mod").write_text("module example.com/app\n\ngo 1.26\n\nrequire (\n\texample.com/a v9.0.0\n\texample.com/up v1.0.0\n)\n", encoding="utf-8")
            (root / "config.json").write_text('{"value":"upstream"}\n', encoding="utf-8")
            run("add", "go.mod", "config.json")
            run("commit", "-m", "upstream")
            run("checkout", "main")
            (root / "go.mod").write_text("module example.com/app\n\ngo 1.26\n\nrequire example.com/a v2.0.0\n", encoding="utf-8")
            (root / "config.json").write_text('{"value":"ours"}\n', encoding="utf-8")
            run("add", "go.mod", "config.json")
            run("commit", "-m", "ours")
            merged = subprocess.run(["git", "-C", str(root), "-c", "merge.conflictStyle=merge", "merge", "--no-commit", "--no-ff", "upstream"], text=True, capture_output=True)
            self.assertEqual(merged.returncode, 1, merged.stderr)
            with self.assertRaises(sync.Stop) as caught:
                sync.finish(root, skip_build=True, resume=False)
            self.assertEqual(caught.exception.code, 3)
            merged_go_mod = (root / "go.mod").read_text(encoding="utf-8")
            self.assertIn("example.com/a v9.0.0", merged_go_mod)
            self.assertIn("example.com/up v1.0.0", merged_go_mod)
            report = sync.load_report(root, resume=True)
            self.assertTrue(any(line.startswith("go.mod\tgo.mod") for line in report))



if __name__ == "__main__":
    unittest.main()
