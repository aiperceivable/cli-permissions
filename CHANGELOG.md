# Changelog

Corpus releases. A section describes what a consumer can rely on after
updating; the GitHub release adds the machine-readable diff of every overlay
and annotation that changed, because whether to adopt a release is the
consumer's decision.

Version numbers are described in [CONTRIBUTING.md](CONTRIBUTING.md#version-numbers):
the corpus release version is independent of the manifest format version and
the overlay format version.

## [Unreleased]

## [0.1.0] - 2026-11-16

First tagged release. 44 reviewed entries across 22 commands, covering the
POSIX core and `sed` in their BSD, GNU and Apple variants.

- Manifest format `1.0`, overlay formats `1.0` and `1.1`. Format `1.1` adds
  explicit native-shim capabilities; only the reviewed BSD `cat`/`head`/`ls`
  entries currently declare order independence, and they match macOS only.
- Every `confidence: verified` entry carries a `provenance` block with a
  re-runnable command and a digest-pinned environment.
- Published as `cli-permissions-v0.1.0.tar.gz` with a `.sha256` sidecar, plus
  the stable alias `cli-permissions.tar.gz` for
  `releases/latest/download/`. The archive is not a permission grant: it
  describes commands, and installing it neither installs binaries nor widens
  access by itself.
