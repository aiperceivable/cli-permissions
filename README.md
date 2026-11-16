# cli-permissions

**The data behind agent permission rules.** Verified facts about what each CLI
command does — destructive flags, network reach, BSD vs GNU differences — with a
re-runnable check behind every row, so a policy is written from evidence instead
of intuition.

> **Status: early.** The corpus covers a POSIX core, not your whole `PATH`. See
> [Coverage](#coverage) for exactly what is in it today.

## The problem

Every coding agent asks the same question dozens of times a day — *may I run
this command?* — and every answer is currently written from memory. The tools
that decide are real and improving; what none of them have is a checked answer
to what the command actually does.

So permission rules get written from intuition, and intuition is wrong in ways
that are hard to notice:

| Looks safe | Actually |
|---|---|
| `sed 's/x/y/w out.txt' in.txt` | truncates `out.txt` **before reading any input**, with no `-i` anywhere. GNU has no way to defer it |
| `uniq input output` | the second operand is a write target: `output` is truncated and rewritten |
| `find . -name '*.log' -fprint list.txt` | a *search* predicate that truncates `list.txt` |
| `Bash(tail:*)` in an allowlist | `tail -f` never terminates; the agent hangs |
| `sed -i 's/a/b/' f` | works on Linux, silently fails on macOS — BSD `-i` eats the script as a backup suffix |

None of those are obscure. All of them are one verification away, and nobody had
run it.

## What this is

A corpus of JSON files, one per `(command, variant)`, each carrying the
command's flags, mutual exclusions, operand placement, behavioural annotations
(`readonly` / `destructive` / `idempotent` / `requires_approval` / `open_world`)
— and, for every claim, how it was checked:

```json
"provenance": {
  "platform": "linux", "tool_version": "4.9", "package": "sed",
  "source": "help", "checked_on": "2026-09-05",
  "command": "docker run --rm debian@sha256:0463… sed --help",
  "environment": "debian@sha256:0463…",
  "notes": "GNU sed runs `s///e` as a shell command: `printf 'x\\n' | sed 's/x/echo PWNED/e'`
            prints PWNED. BSD sed rejects the flag. One name, two answers."
}
```

The `command` field is meant to be re-run verbatim. That is the whole point: an
entry you cannot re-check is an opinion.

## What this is not

- **Not a policy engine.** It states what commands do; deciding what to allow is
  the consumer's job. It pairs with the tools that make those decisions rather
  than replacing them.
- **Not a sandbox.** Nothing here enforces anything.
- **Not an awesome-list.** Every row is one verification, which is why there are
  tens of commands rather than hundreds.

## Using it

**With [apexe](https://github.com/aiperceivable/apexe)** — install and register
the corpus directly from GitHub:

```bash
apexe overlays install https://github.com/aiperceivable/cli-permissions
apexe scan ls --no-cache
```

The installer reads `manifest.json`, records the resolved commit, and makes the
overlays available automatically. Pin a branch, tag or commit with `--ref`;
use `apexe overlays update cli-permissions` to refresh the same reference.
For local overlay development, read the current working directory directly:

```bash
# From the apexe checkout, with cli-permissions checked out alongside it.
APEXE_OVERLAY_DIRS=../cli-permissions/overlays apexe scan ls --no-cache
```

This includes uncommitted edits without installing a snapshot. The variable
applies only to this scan; repeat the scan after editing an overlay. Refresh
enabled shims with `apexe env --reload` if the eligible command set changes.
`apexe overlays install ../cli-permissions` instead installs a managed snapshot
of the local Git repository's committed content.

A checkout may also be configured persistently through `overlay_dirs`:


```yaml
# ~/.apexe/config.yaml
overlay_dirs:
  - /path/to/cli-permissions/overlays
```

or `APEXE_OVERLAY_DIRS=/path/to/cli-permissions/overlays`. Configured directories
outrank managed corpora; your own
`~/.apexe/overlays/` still outranks both. apexe ships no built-in overlays.

**Without apexe** — the files describe the command, not any one tool. The format
is defined by [`schemas/tool-overlay.schema.json`](schemas/tool-overlay.schema.json),
which lives here rather than in apexe: apexe is one consumer of it, not its owner.
[`tools/derive-permissions.py`](tools/) is a working reference consumer: it
turns an overlay directory into `.claude/settings.json` or
`.agents/permissions.json` rules, in a different language from apexe and sharing
no code with it. See
[Reading Overlays Without apexe](https://github.com/aiperceivable/apexe/blob/main/docs/overlay-consumers.md)
for how to select the overlay that applies, what `mode` and `confidence` oblige
you to, and the four fields that decide an `argv`.

## Coverage

**22 commands, 44 entries** across their BSD, GNU and Apple variants — the POSIX
core plus `sed`. See [`overlays/`](overlays/). This repository is the only copy:
apexe ships no overlays of its own and reads these like any other consumer.

The corpus is deliberately narrow. An entry that nobody checked against a
running binary does not belong here, and checking is the slow part.

## Corpus metadata and format versions

[`manifest.json`](manifest.json) names the corpus, its release version, description,
overlay directory, homepage and license. Its definition is
[`schemas/corpus-manifest.schema.json`](schemas/corpus-manifest.schema.json).
The corpus release version, manifest format version and overlay format version
are independent; an installation records the release version and an identity
for the exact bytes it loaded — a Git commit for a checkout source, the archive
sha256 for a release source.

### Release artifacts

Releases are cut by tag; the procedure and the version-increment rules are in
[CONTRIBUTING.md](CONTRIBUTING.md#releasing). Each release attaches
`<repo>-v<version>.tar.gz` with a `.sha256` sidecar, plus the stable alias
`<repo>.tar.gz` so the newest release can be fetched without an API call from
`/releases/latest/download/`.

The asset name is the repository name, because that is what a consumer resolves
from a repository URL. A fork that keeps this workflow publishes
`team-corpus.tar.gz` under its own name with no consumer configuration; a fork
that is a different corpus rather than a mirror should also change `name` in
`manifest.json`, which is the name an installation records.

Build the same archive locally with `tools/package.sh` (or
`python3 tools/package-corpus.py`); `--check` builds twice and compares digests.

Verify before unpacking:

```sh
shasum -a 256 -c cli-permissions-v0.2.0.tar.gz.sha256
```

The archive contains `manifest.json`, `overlays/`, `schemas/` and the repository
documents. It is data, not a grant: installing it neither installs CLI binaries
nor widens access by itself.

Overlay formats 1.0 and 1.1 are supported by the reference consumer. Format
1.1 adds explicit native-shim capabilities. Only the reviewed BSD cat/head/ls
entries currently declare order independence and match macOS only, where those
capabilities were checked. FreeBSD needs separate native-capability evidence.
Other entries remain scan-only for native shims. Installing a corpus does not install CLI binaries or grant
permissions. Native shims additionally require matching authoritative overlays
with reviewed capabilities. See apexe's [authoring procedure](https://github.com/aiperceivable/apexe/blob/main/docs/overlays.md).

Run regression tests from the repository root:

```bash
python3 -m pip install jsonschema
python3 -m unittest discover -s tests -v
```

Schema tests require `jsonschema`; without it they are explicitly skipped. The
native behavior tests run only on the reviewed macOS 26.3 (25D125) build and
are skipped on other hosts. They check bounded fixtures, not every invocation.

## Development

### Layout

| Path | What lives there |
| --- | --- |
| `overlays/` | one reviewed JSON file per `(command, variant)` |
| `schemas/` | manifest and overlay JSON Schemas, the contract a consumer reads |
| `tools/` | `derive-permissions.py` (reference consumer), `package-corpus.py` and `package.sh`, `tag-release.sh` |
| `tests/` | regression tests, including schema validation of every document |
| `.github/workflows/` | `ci.yml` on every push, `release.yml` on `v*` tags |

### Local checks

```bash
python3 -m pip install jsonschema
CI_REQUIRE_SCHEMA=1 python3 -m unittest discover -s tests -v
tools/package.sh --check
```

`CI_REQUIRE_SCHEMA=1` turns a missing `jsonschema` into a failure instead of a
skip: a skipped schema test means the corpus was never validated against the
format it claims. `--check` builds the archive twice and compares digests, so a
non-deterministic change (a timestamp, an unsorted entry) fails here rather than
in a release.

### Cutting a release

1. Bump `version` in `manifest.json` using the rules in
   [CONTRIBUTING.md](CONTRIBUTING.md#version-numbers): a patch can only deny
   more, a minor widens the declared surface, a major changes the format.
2. Promote `## [Unreleased]` in [`CHANGELOG.md`](CHANGELOG.md) to
   `## [<version>]` and say what a consumer can rely on after updating. The
   release notes add the machine-readable overlay diff; this section is the part
   a script cannot write.
3. Commit and merge to `main`, and let `ci.yml` pass on that commit.
4. Run `tools/tag-release.sh --push`.

The tag is derived from `manifest.json`, never typed. Before creating it, the
script checks the working tree, `origin/main`, the changelog section, monotonic
version order, a free tag name and a reproducible build. `release.yml` then
re-checks the same facts, runs the tests, builds `<repo>-v<version>.tar.gz`,
attaches it with its `.sha256` plus the stable alias `<repo>.tar.gz`, and
composes notes from the overlay diff and the changelog section.

`workflow_dispatch` accepts an existing tag only, for republishing a release
whose assets failed to upload. It never accepts a version that has no tag.

**Failure policy.** A published tag is never moved and an uploaded asset is
never replaced: both would make every recorded sha256 meaningless. If a release
is wrong, cut the next patch. The full policy, including the one exception for a
tag that was rejected before any asset existed, is in
[CONTRIBUTING.md](CONTRIBUTING.md#failure-policy).

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md) first, then the
[authoring and verification procedure](https://github.com/aiperceivable/apexe/blob/main/docs/overlays.md).
The short version: **a `verified` claim needs a command someone else can re-run**,
and writing an entry from knowledge of a tool — however well you know it — is
the failure mode the procedure exists to prevent.

## License

[Apache-2.0](LICENSE). The provenance requirement and the licence point the same
way: say where a fact came from.
