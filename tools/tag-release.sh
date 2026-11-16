#!/usr/bin/env bash
# Create the annotated tag that publishes this corpus.
#
# The tag is the release address; manifest.json is the identity inside the
# bytes. This script derives the tag from the manifest instead of asking a
# person to type a version, so the two cannot disagree, and it fails before
# the tag exists rather than after CI has already rejected the push.
#
# Usage:
#   tools/tag-release.sh                 Check everything, create the tag locally
#   tools/tag-release.sh --push          Also push the tag (starts the release)
#   tools/tag-release.sh --sign          Create a signed tag (git tag -s)
#   tools/tag-release.sh --dry-run       Run every check, create nothing
#   tools/tag-release.sh --skip-main-check
#
# The failure policy this script enforces is in CONTRIBUTING.md: a published
# tag is never moved or deleted, and an uploaded asset is never replaced.
set -euo pipefail

PUSH=0
SIGN=0
DRY_RUN=0
MAIN_CHECK=1

for argument in "$@"; do
    case "${argument}" in
        --push) PUSH=1 ;;
        --sign) SIGN=1 ;;
        --dry-run) DRY_RUN=1 ;;
        --skip-main-check) MAIN_CHECK=0 ;;
        -h|--help) sed -n '2,17p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *)
            echo "error: unknown argument '${argument}'" >&2
            exit 1
            ;;
    esac
done

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

die() {
    echo "error: $*" >&2
    exit 1
}

command -v python3 >/dev/null 2>&1 || die "python3 is required"

VERSION="$(python3 -c 'import json,sys; print(json.load(open("manifest.json"))["version"])')" \
    || die "manifest.json has no readable version"
TAG="v${VERSION}"

echo "Corpus:  $(python3 -c 'import json; print(json.load(open("manifest.json"))["name"])')"
echo "Version: ${VERSION}"
echo "Tag:     ${TAG}"
echo

# 1. The working tree must be exactly what gets tagged.
if [ -n "$(git status --porcelain)" ]; then
    echo "Uncommitted changes:" >&2
    git status --short >&2
    die "commit or stash them; a tag must point at reviewed content"
fi

# 2. HEAD must be on main, or release.yml's ancestry check will reject the tag
#    after it is already public.
if [ "${MAIN_CHECK}" -eq 1 ]; then
    git fetch --quiet origin main || die "cannot fetch origin main"
    head_commit="$(git rev-parse HEAD)"
    main_commit="$(git rev-parse origin/main)"
    if [ "${head_commit}" != "${main_commit}" ]; then
        die "HEAD (${head_commit:0:12}) is not origin/main (${main_commit:0:12}); rebase or merge first"
    fi
fi

# 3. The narrative must exist, because a release tells its users what changed.
if [ ! -f "CHANGELOG.md" ]; then
    die "CHANGELOG.md is missing; add a '## [${VERSION}]' section first"
fi
if ! grep -q "^## \[${VERSION}\]" CHANGELOG.md; then
    die "CHANGELOG.md has no '## [${VERSION}]' section; promote the unreleased entries first"
fi

# 4. Versions are monotonic: re-releasing an existing number would give one
#    version two different byte sequences.
local_tag_exists=0
if git rev-parse --verify --quiet "refs/tags/${TAG}" >/dev/null; then
    local_tag_exists=1
fi
if git ls-remote --tags --exit-code origin "refs/tags/${TAG}" >/dev/null 2>&1; then
    die "tag ${TAG} already exists on origin"
fi
if [ "${local_tag_exists}" -eq 1 ]; then
    die "tag ${TAG} already exists locally; delete it only if it was never pushed"
fi

previous="$(git tag --list 'v*' --sort=-v:refname | head -n 1 || true)"
if [ -n "${previous}" ]; then
    previous_version="${previous#v}"
    highest="$(printf '%s\n%s\n' "${previous_version}" "${VERSION}" | sort -V | tail -n 1)"
    if [ "${highest}" != "${VERSION}" ]; then
        die "version ${VERSION} is lower than the previous tag ${previous}"
    fi
    if [ "${highest}" = "${previous_version}" ]; then
        die "version ${VERSION} already exists as ${previous}; bump manifest.json"
    fi
    echo "Previous release: ${previous}"
fi

# 5. The archive must build from this tree, or the tag will publish nothing.
python3 tools/package-corpus.py --check

if [ "${DRY_RUN}" -eq 1 ]; then
    echo
    echo "Dry run: all checks passed; nothing was created."
    exit 0
fi

# 6. Create the tag. The message names the digest inputs, not a summary: the
#    summary belongs in CHANGELOG.md.
if [ "${SIGN}" -eq 1 ]; then
    git tag -s "${TAG}" -m "cli-permissions ${VERSION}"
else
    git tag -a "${TAG}" -m "cli-permissions ${VERSION}"
fi
echo
echo "Created ${TAG} at $(git rev-parse --short HEAD)."

if [ "${PUSH}" -eq 1 ]; then
    git push origin "${TAG}"
    echo "Pushed ${TAG}. The release workflow verifies and publishes the archive."
else
    echo "Next: git push origin ${TAG}"
    echo "That push is the manual release trigger; nothing publishes until it happens."
fi
