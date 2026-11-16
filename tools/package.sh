#!/bin/sh
# Build the corpus release archive and its checksum.
#
# A shell entry point so packaging has the same shape as tools/tag-release.sh
# and the installer: no logic lives here, only the call into the packager that
# the release workflow also runs.
#
# Usage:
#   tools/package.sh                      Build into dist/
#   tools/package.sh --out DIR            Choose the output directory
#   tools/package.sh --check              Build twice and compare digests
#   tools/package.sh --asset-name NAME    Override the repository-derived name
set -eu

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
exec python3 "${ROOT}/tools/package-corpus.py" "$@"
