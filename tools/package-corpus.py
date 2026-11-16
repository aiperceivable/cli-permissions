#!/usr/bin/env python3
"""Build the corpus release archive and its checksum.

The archive is the unit consumers pin: an installation records its sha256 as
the identity of the rules it loaded, so the bytes must be reproducible from the
tag. Reproducibility here means entry order, timestamps, ownership and
permissions are normalised, and gzip is written with mtime 0 and no filename.
Deflate output still depends on the zlib build, so CI is the authority for the
published digest; `--check` proves the recipe is repeatable on this machine,
not that two machines agree byte for byte.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import re
import sys
import tarfile
import tempfile
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[1]

# Only these paths are published. tests/ and tools/ stay in the repository:
# consumers do not read them, and every published byte is covered by the digest.
ARCHIVE_FILES = ("manifest.json", "README.md", "LICENSE", "SCOPE.md")
ARCHIVE_DIRECTORIES = ("overlays", "schemas")

SEMVER = re.compile(
    r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
    r"(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$"
)
SUPPORTED_OVERLAY_SCHEMA_VERSIONS = frozenset({"1.0", "1.1"})
MAX_ENTRY_BYTES = 8 * 1024 * 1024
MAX_TOTAL_BYTES = 32 * 1024 * 1024


class PackageError(Exception):
    """A release-input problem that must stop packaging."""


def read_manifest(root: Path) -> Dict[str, object]:
    path = root / "manifest.json"
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise PackageError("manifest.json is missing") from None
    except json.JSONDecodeError as error:
        raise PackageError("manifest.json is not valid JSON: {}".format(error)) from None
    if not isinstance(manifest, dict):
        raise PackageError("manifest.json must be a JSON object")
    version = manifest.get("version")
    if not isinstance(version, str) or not SEMVER.match(version):
        raise PackageError(
            "manifest.json version must be a bare SemVer string such as 0.2.0"
        )
    overlay_directory = manifest.get("overlay_directory")
    if not isinstance(overlay_directory, str) or not overlay_directory:
        raise PackageError("manifest.json overlay_directory must be a relative path")
    return manifest


def validate_overlays(root: Path, manifest: Dict[str, object]) -> int:
    """Parse every published overlay and reject entries a consumer cannot load."""
    directory = root / str(manifest["overlay_directory"])
    if not directory.is_dir():
        raise PackageError(
            "overlay_directory '{}' is not a directory".format(manifest["overlay_directory"])
        )
    seen: Dict[Tuple[str, str], str] = {}
    count = 0
    for path in sorted(directory.glob("*.json")):
        try:
            overlay = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise PackageError("{}: invalid JSON: {}".format(path.name, error)) from None
        schema_version = overlay.get("schema_version")
        if schema_version not in SUPPORTED_OVERLAY_SCHEMA_VERSIONS:
            raise PackageError(
                "{}: unsupported overlay format '{}'".format(path.name, schema_version)
            )
        command = overlay.get("command")
        variant = overlay.get("variant")
        if not isinstance(command, str) or not command:
            raise PackageError("{}: command must be a non-empty string".format(path.name))
        if not isinstance(variant, str) or not variant:
            raise PackageError("{}: variant must be a non-empty string".format(path.name))
        key = (command, variant)
        if key in seen:
            raise PackageError(
                "{} and {} both declare {}@{}".format(
                    seen[key], path.name, command, variant
                )
            )
        seen[key] = path.name
        count += 1
    if count == 0:
        raise PackageError("no overlays found in '{}'".format(directory.name))
    return count


def collect_entries(
    root: Path, manifest: Dict[str, object], asset: str
) -> List[Tuple[str, Path, bool]]:
    """Return (archive name, source path, is_directory) in deterministic order."""
    top = "{}-{}".format(asset, manifest["version"])
    entries: List[Tuple[str, Path, bool]] = [(top, root, True)]
    for name in ARCHIVE_DIRECTORIES:
        directory = root / name
        if not directory.is_dir():
            raise PackageError("{} is missing".format(name))
        entries.append(("{}/{}".format(top, name), directory, True))
        for path in sorted(directory.rglob("*")):
            if path.is_symlink():
                raise PackageError("{} is a symlink; the archive must be self-contained".format(path))
            if path.is_dir():
                entries.append(("{}/{}".format(top, path.relative_to(root)), path, True))
            elif path.is_file():
                entries.append(("{}/{}".format(top, path.relative_to(root)), path, False))
            else:
                raise PackageError("{} is not a regular file or directory".format(path))
    for name in ARCHIVE_FILES:
        path = root / name
        if not path.is_file():
            raise PackageError("{} is missing".format(name))
        entries.append(("{}/{}".format(top, name), path, False))
    entries.sort(key=lambda entry: entry[0])
    return entries


def archive_bytes(root: Path, manifest: Dict[str, object], asset: str) -> bytes:
    """Serialise the corpus to tar.gz with every varying field normalised."""
    entries = collect_entries(root, manifest, asset)
    total = 0
    raw = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0, compresslevel=9) as compressed:
        with tarfile.open(fileobj=compressed, mode="w", format=tarfile.USTAR_FORMAT) as archive:
            for name, path, is_directory in entries:
                info = tarfile.TarInfo(name)
                info.mtime = 0
                info.uid = 0
                info.gid = 0
                info.uname = ""
                info.gname = ""
                if is_directory:
                    info.type = tarfile.DIRTYPE
                    info.mode = 0o755
                    info.size = 0
                    archive.addfile(info)
                    continue
                size = path.stat().st_size
                if size > MAX_ENTRY_BYTES:
                    raise PackageError("{} exceeds {} bytes".format(name, MAX_ENTRY_BYTES))
                total += size
                if total > MAX_TOTAL_BYTES:
                    raise PackageError("archive exceeds {} bytes".format(MAX_TOTAL_BYTES))
                info.type = tarfile.REGTYPE
                info.mode = 0o644
                info.size = size
                with path.open("rb") as source:
                    archive.addfile(info, source)
    return raw.getvalue()


def asset_name(manifest: Dict[str, object], asset: str) -> str:
    """A release asset is named after its repository, which is what a consumer
    resolves from the repository URL. A fork therefore needs no configuration."""
    return "{}-v{}.tar.gz".format(asset, manifest["version"])


def write_artifact(root: Path, out_dir: Path, asset: str) -> Path:
    manifest = read_manifest(root)
    validate_overlays(root, manifest)
    out_dir.mkdir(parents=True, exist_ok=True)
    destination = out_dir / asset_name(manifest, asset)
    payload = archive_bytes(root, manifest, asset)
    destination.write_bytes(payload)
    digest = hashlib.sha256(payload).hexdigest()
    destination.with_name(destination.name + ".sha256").write_text(
        "{}  {}\n".format(digest, destination.name), encoding="utf-8"
    )
    print("Built {}".format(destination))
    print("sha256 {}".format(digest))
    return destination


def check_reproducible(root: Path, asset: str) -> None:
    manifest = read_manifest(root)
    validate_overlays(root, manifest)
    with tempfile.TemporaryDirectory() as directory:
        first = archive_bytes(root, manifest, asset)
        second = archive_bytes(root, manifest, asset)
    if first != second:
        raise PackageError("packaging is not reproducible: two builds differ")
    digest = hashlib.sha256(first).hexdigest()
    print("Reproducible: {}".format(digest))
    print("Note: the published digest is the one CI builds for the tag.")


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=str(ROOT / "dist"), help="output directory")
    parser.add_argument(
        "--asset-name",
        default=ROOT.name,
        help="repository name used in the asset filename (default: %(default)s)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="build twice in memory and compare digests instead of writing files",
    )
    arguments = parser.parse_args(argv)
    asset = arguments.asset_name
    if not asset or "/" in asset or asset.startswith("."):
        print("error: --asset-name must be a non-empty path segment", file=sys.stderr)
        return 1
    try:
        if arguments.check:
            check_reproducible(ROOT, asset)
        else:
            write_artifact(ROOT, Path(arguments.out), asset)
    except PackageError as error:
        print("error: {}".format(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
