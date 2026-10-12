"""Regression tests for corpus metadata and independent consumers."""
import importlib.util
import json
import itertools
import os
import platform
import subprocess
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("derive_permissions", ROOT / "tools/derive-permissions.py")
CONSUMER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = CONSUMER
SPEC.loader.exec_module(CONSUMER)


class CorpusTests(unittest.TestCase):
    def test_loader_accepts_both_supported_overlay_versions(self):
        with tempfile.TemporaryDirectory() as directory:
            for version in ("1.0", "1.1"):
                overlay = {"schema_version": version, "command": "fixture", "variant": "unknown"}
                Path(directory, version + ".json").write_text(json.dumps(overlay), encoding="utf-8")
            overlays, skipped = CONSUMER.load_overlays(Path(directory))
        self.assertEqual({item["schema_version"] for item in overlays}, {"1.0", "1.1"})
        self.assertEqual(skipped, [])

    def test_loader_rejects_future_or_missing_overlay_versions(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "future.json").write_text('{"schema_version":"2.0"}', encoding="utf-8")
            Path(directory, "missing.json").write_text('{}', encoding="utf-8")
            overlays, skipped = CONSUMER.load_overlays(Path(directory))
        self.assertEqual(overlays, [])
        self.assertEqual(len(skipped), 2)

    def test_loader_reports_malformed_json(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "bad.json").write_text('{invalid json}', encoding="utf-8")
            overlays, skipped = CONSUMER.load_overlays(Path(directory))
        self.assertEqual(overlays, [])
        self.assertEqual(len(skipped), 1)

    def test_native_capabilities_do_not_change_permission_derivation(self):
        original = {"schema_version": "1.0", "command": "fixture", "variant": "unknown",
                    "mode": "merge", "confidence": "low", "flags": [],
                    "annotations": {"readonly": True, "destructive": False, "idempotent": True,
                                    "requires_approval": False, "open_world": False}}
        modern = dict(original, schema_version="1.1", short_flag_bundling=False,
                      streaming_stdin_safe=False, cross_flag_ordering=False)
        self.assertEqual(CONSUMER.derive(original), CONSUMER.derive(modern))

    def test_all_corpus_entries_are_visible_to_the_reference_consumer(self):
        overlays, skipped = CONSUMER.load_overlays(ROOT / "overlays")
        self.assertEqual(len(overlays), len(list((ROOT / "overlays").glob("*.json"))))
        self.assertEqual(skipped, [])
        self.assertTrue(any(item["schema_version"] == "1.1" for item in overlays))

    def test_manifest_names_a_real_overlay_directory(self):
        manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["name"], "cli-permissions")
        self.assertEqual(manifest["schema_version"], "1.0")
        self.assertTrue((ROOT / manifest["overlay_directory"]).is_dir())
        self.assertNotEqual(manifest["version"], "")

    @unittest.skipUnless(importlib.util.find_spec("jsonschema"), "Requires jsonschema")
    def test_manifest_and_every_overlay_satisfy_their_schemas(self):
        import jsonschema
        for schema_name, documents in [
            ("corpus-manifest.schema.json", [ROOT / "manifest.json"]),
            ("tool-overlay.schema.json", list((ROOT / "overlays").glob("*.json"))),
        ]:
            schema = json.loads((ROOT / "schemas" / schema_name).read_text(encoding="utf-8"))
            jsonschema.Draft202012Validator.check_schema(schema)
            validator = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
            for document in documents:
                self.assertEqual(list(validator.iter_errors(json.loads(document.read_text(encoding="utf-8")))), [], document.name)


    def test_loader_reports_non_object_json(self):
        with tempfile.TemporaryDirectory() as directory:
            for index, value in enumerate([[], None, True, "invalid"]):
                Path(directory, f"{index}.json").write_text(json.dumps(value), encoding="utf-8")
            overlays, skipped = CONSUMER.load_overlays(Path(directory))
        self.assertEqual(overlays, [])
        self.assertEqual(len(skipped), 4)

    def test_loader_reports_non_string_versions(self):
        with tempfile.TemporaryDirectory() as directory:
            for index, value in enumerate([[], {}, None, True, 1.1]):
                Path(directory, f"{index}.json").write_text(
                    json.dumps({"schema_version": value}), encoding="utf-8")
            overlays, skipped = CONSUMER.load_overlays(Path(directory))
        self.assertEqual(overlays, [])
        self.assertEqual(len(skipped), 5)

    @unittest.skipUnless(importlib.util.find_spec("jsonschema"), "Requires jsonschema")
    def test_manifest_schema_rejects_invalid_metadata(self):
        import jsonschema
        schema = json.loads((ROOT / "schemas/corpus-manifest.schema.json").read_text())
        validator = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
        manifest = json.loads((ROOT / "manifest.json").read_text())
        invalid = {
            "schema_version": ["2.0"], "name": ["", "../escape", "valid\n"],
            "description": ["", "  "],
            "version": ["latest", "1.0", "01.0.0", "1.0.0-01", "1.0.0\n", "1١.0.0"],
            "overlay_directory": ["", "../escape", "/absolute", "a/../b", ".git", "a/.git/b", "C:\\root", "overlays\n"],
            "homepage": ["http://example.com", "https://", "https://user:secret@example.com"],
            "license": ["", "   "],
        }
        for key, values in invalid.items():
            for value in values:
                with self.subTest(field=key, value=value):
                    self.assertTrue(list(validator.iter_errors(dict(manifest, **{key: value}))))
        self.assertTrue(list(validator.iter_errors(dict(manifest, unexpected=True))))

    @unittest.skipUnless(importlib.util.find_spec("jsonschema"), "Requires jsonschema")
    def test_manifest_schema_accepts_semver_and_relative_directories(self):
        import jsonschema
        schema = json.loads((ROOT / "schemas/corpus-manifest.schema.json").read_text())
        validator = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
        manifest = json.loads((ROOT / "manifest.json").read_text())
        for version in ["0.1.0", "1.2.3-rc.1+build.42", "1.2.3-0", "1.2.3-01alpha"]:
            for directory in [".", "overlays", "data/overlays"]:
                with self.subTest(version=version, directory=directory):
                    candidate = dict(manifest, version=version, overlay_directory=directory)
                    self.assertEqual(list(validator.iter_errors(candidate)), [])

    def test_native_pilot_platforms_match_the_recorded_evidence(self):
        for name in ["cat", "head", "ls"]:
            overlay = json.loads((ROOT / "overlays" / f"{name}@bsd.json").read_text())
            self.assertEqual(overlay["match"]["platform"], [overlay["provenance"]["platform"]])
            self.assertEqual(overlay["provenance"]["platform"], "macos")

    def test_native_pilot_conflicts_are_symmetric_and_resolve_to_flags(self):
        for name in ["cat", "head", "ls"]:
            overlay = json.loads((ROOT / "overlays" / f"{name}@bsd.json").read_text())
            aliases = {alias: flag for flag in overlay["flags"]
                       for alias in (flag.get("short"), flag.get("long")) if alias}
            for flag in overlay["flags"]:
                for peer in flag.get("conflicts_with", []):
                    with self.subTest(command=name, flag=flag.get("short"), peer=peer):
                        self.assertIn(peer, aliases)
                        own_aliases = {flag.get("short"), flag.get("long")} - {None}
                        self.assertTrue(own_aliases.intersection(aliases[peer].get("conflicts_with", [])))


@unittest.skipUnless(platform.system() == "Darwin" and
                     subprocess.check_output(["/usr/bin/sw_vers", "-buildVersion"], text=True).strip() == "25D125",
                     "Requires the reviewed macOS 26.3 (25D125) reference build")
class NativePilotTests(unittest.TestCase):
    def test_bundled_flags_and_streaming_stdin_on_reference_binaries(self):
        cases = [(["/bin/cat", "-ns"], b"one\ntwo\n", b"     1\tone\n     2\ttwo\n"),
                 (["/usr/bin/head", "-n1"], b"one\ntwo\n", b"one\n"),
                 (["/usr/bin/head", "-c2"], b"one\ntwo\n", b"on")]
        for arguments, input_data, expected in cases:
            with self.subTest(arguments=arguments):
                result = subprocess.run(arguments, input=input_data, capture_output=True, timeout=5)
                self.assertEqual((result.returncode, result.stdout, result.stderr), (0, expected, b""))

    def test_ls_g_enables_long_output_and_omits_owner(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "fixture").write_text("data")
            results = [subprocess.run(["/bin/ls", flag, directory], capture_output=True,
                                      text=True, timeout=5) for flag in ["-g", "-l"]]
        self.assertTrue(all(result.returncode == 0 for result in results))
        group_line = results[0].stdout.splitlines()[-1].split()
        long_line = results[1].stdout.splitlines()[-1].split()
        self.assertEqual(group_line, long_line[:2] + long_line[3:])

    def test_ls_non_conflicting_flag_pairs_are_order_independent(self):
        overlay = json.loads((ROOT / "overlays/ls@bsd.json").read_text())
        flags = [flag for flag in overlay["flags"] if flag["type"] == "boolean" or flag.get("value_optional")]
        environment = dict(os.environ, LC_ALL="C", COLUMNS="80", CLICOLOR="0", CLICOLOR_FORCE="0")
        with tempfile.TemporaryDirectory() as directory:
            fixture = Path(directory)
            for name in ["ordinary", "with space", "control\tname", ".hidden"]:
                (fixture / name).write_text("fixture\n")
            (fixture / "nested").mkdir()
            (fixture / "link").symlink_to("ordinary")
            count = 0
            for left, right in itertools.combinations(flags, 2):
                left_name, right_name = left.get("short") or left["long"], right.get("short") or right["long"]
                if right_name in left.get("conflicts_with", []) or left_name in right.get("conflicts_with", []):
                    continue
                arguments = [left_name + ("=never" if left.get("value_optional") else ""),
                             right_name + ("=never" if right.get("value_optional") else "")]
                results = [subprocess.run(["/bin/ls", *order, directory], capture_output=True,
                                         env=environment, timeout=5) for order in (arguments, arguments[::-1])]
                with self.subTest(flags=arguments):
                    self.assertEqual((results[0].returncode, results[0].stdout, results[0].stderr),
                                     (results[1].returncode, results[1].stdout, results[1].stderr))
                count += 1
            self.assertGreater(count, 900)


if __name__ == "__main__":
    unittest.main()
