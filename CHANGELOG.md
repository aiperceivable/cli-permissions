# Changelog

Corpus releases. A section describes what a consumer can rely on after
updating; the GitHub release adds the machine-readable diff of every overlay
and annotation that changed, because whether to adopt a release is the
consumer's decision.

Version numbers are described in [CONTRIBUTING.md](CONTRIBUTING.md#version-numbers):
the corpus release version is independent of the manifest format version and
the overlay format version.

## [Unreleased]

## [0.1.1] - 2026-11-16

### Fixed
- `sort` (Apple and GNU) states `requires_approval: true`. The ceiling was
  already implied by the approval-flag list, but a verified entry that omits an
  annotation forces a consumer to treat it as unknown, and the corpus rule is to
  state all five. `--compress-program` is still refused at the flag level
  (`risk: executes`), so the executing path is unchanged.
- `find@gnu` lists `-d` in `-prune`'s conflicts as well as in `-d`'s own list.
  `-d` is recorded in the same entry as a synonym of `-depth`, and the conflict
  with `-prune` was already verified behaviourally; only one direction carried
  it. A consumer reading either side now sees the same refusal.

### Changed
- Release assets are named after the repository (`<repo>.tar.gz`), derived from
  `GITHUB_REPOSITORY` in the release workflow. A fork publishes under its own
  name with no consumer configuration. `tools/package.sh` is the local entry
  point; `--asset-name` overrides the derived name.

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
