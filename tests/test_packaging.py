"""Tests for the published corpus archive."""
import importlib.util
import io
import json
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "package_corpus", ROOT / "tools/package-corpus.py"
)
PACKAGING = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = PACKAGING
SPEC.loader.exec_module(PACKAGING)

MANIFEST = {
    "schema_version": "1.0",
    "name": "fixture",
    "description": "Fixture corpus for packaging tests.",
    "version": "0.1.0",
    "overlay_directory": "overlays",
}


class ArchiveTests(unittest.TestCase):
    def test_archive_is_byte_identical_across_builds(self):
        manifest = PACKAGING.read_manifest(ROOT)
        first = PACKAGING.archive_bytes(ROOT, manifest)
        second = PACKAGING.archive_bytes(ROOT, manifest)
        self.assertEqual(first, second)

    def test_archive_publishes_manifest_and_every_overlay(self):
        manifest = PACKAGING.read_manifest(ROOT)
        payload = PACKAGING.archive_bytes(ROOT, manifest)
        with tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz") as archive:
            names = archive.getnames()
        top = "cli-permissions-{}".format(manifest["version"])
        self.assertIn("{}/manifest.json".format(top), names)
        self.assertIn("{}/schemas/corpus-manifest.schema.json".format(top), names)
        published = [name for name in names
                     if name.startswith("{}/overlays/".format(top)) and name.endswith(".json")]
        expected = sorted((ROOT / "overlays").glob("*.json"))
        self.assertEqual(len(published), len(expected))

    def test_archive_preserves_no_timestamps_or_ownership(self):
        manifest = PACKAGING.read_manifest(ROOT)
        payload = PACKAGING.archive_bytes(ROOT, manifest)
        with tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz") as archive:
            for member in archive.getmembers():
                self.assertEqual(member.mtime, 0, member.name)
                self.assertEqual(member.uid, 0, member.name)
                self.assertEqual(member.gid, 0, member.name)
                self.assertFalse(member.issym(), member.name)


class ManifestTests(unittest.TestCase):
    def write(self, directory, manifest):
        path = Path(directory, "manifest.json")
        path.write_text(json.dumps(manifest), encoding="utf-8")
        return path

    def test_version_must_be_bare_semver(self):
        for version in ["v0.1.0", "0.1", "", "latest"]:
            with tempfile.TemporaryDirectory() as directory:
                self.write(directory, dict(MANIFEST, version=version))
                with self.subTest(version=version):
                    with self.assertRaises(PACKAGING.PackageError):
                        PACKAGING.read_manifest(Path(directory))

    def test_missing_overlay_directory_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            self.write(directory, MANIFEST)
            with self.assertRaises(PACKAGING.PackageError):
                PACKAGING.validate_overlays(Path(directory), MANIFEST)

    def test_unsupported_overlay_format_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            overlays = Path(directory, "overlays")
            overlays.mkdir()
            Path(overlays, "future.json").write_text(
                json.dumps({"schema_version": "2.0", "command": "x", "variant": "gnu"}),
                encoding="utf-8",
            )
            with self.assertRaises(PACKAGING.PackageError):
                PACKAGING.validate_overlays(Path(directory), MANIFEST)

    def test_duplicate_command_variant_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            overlays = Path(directory, "overlays")
            overlays.mkdir()
            document = {"schema_version": "1.0", "command": "x", "variant": "gnu"}
            Path(overlays, "a.json").write_text(json.dumps(document), encoding="utf-8")
            Path(overlays, "b.json").write_text(json.dumps(document), encoding="utf-8")
            with self.assertRaises(PACKAGING.PackageError):
                PACKAGING.validate_overlays(Path(directory), MANIFEST)


if __name__ == "__main__":
    unittest.main()
