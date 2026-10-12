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
apexe overlays install aiperceivable/cli-permissions
apexe scan ls --no-cache
```

The installer reads `manifest.json`, records the resolved commit, and makes the
overlays available automatically. Pin a branch, tag or commit with `--ref`;
use `apexe overlays update cli-permissions` to refresh the same reference.
A manually cloned checkout can also be configured through `overlay_dirs`:

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
are independent; installations also record the actual Git commit.

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

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md) first, then the
[authoring and verification procedure](https://github.com/aiperceivable/apexe/blob/main/docs/overlays.md).
The short version: **a `verified` claim needs a command someone else can re-run**,
and writing an entry from knowledge of a tool — however well you know it — is
the failure mode the procedure exists to prevent.

## License

[Apache-2.0](LICENSE). The provenance requirement and the licence point the same
way: say where a fact came from.
