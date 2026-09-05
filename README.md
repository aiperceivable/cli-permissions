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

**With [apexe](https://github.com/aiperceivable/apexe)** — clone anywhere and
point `overlay_dirs` at it:

```yaml
# ~/.apexe/config.yaml
overlay_dirs:
  - /path/to/cli-permissions/overlays
```

or `APEXE_OVERLAY_DIRS=/path/to/cli-permissions/overlays`. Files here outrank
apexe's built-ins; your own `~/.apexe/overlays/` still outranks these.

**Without apexe** — the files describe the command, not any one tool. See
[Reading Overlays Without apexe](https://github.com/aiperceivable/apexe/blob/main/docs/overlay-consumers.md)
for how to select the overlay that applies, what `mode` and `confidence` oblige
you to, and the four fields that decide an `argv`.

## Coverage

**The corpus has not migrated here yet** — see [`overlays/`](overlays/) for where
it stands and why the move is deliberately last. Today the verified entries ship
as apexe's built-in set: 22 commands across their BSD, GNU and Apple variants,
covering the POSIX core plus `sed`.

The corpus is deliberately narrow. An entry that nobody checked against a
running binary does not belong here, and checking is the slow part.

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md) first, then the
[authoring and verification procedure](https://github.com/aiperceivable/apexe/blob/main/docs/overlays.md).
The short version: **a `verified` claim needs a command someone else can re-run**,
and writing an entry from knowledge of a tool — however well you know it — is
the failure mode the procedure exists to prevent.

## License

[Apache-2.0](LICENSE). The provenance requirement and the licence point the same
way: say where a fact came from.
