# overlays/

The corpus. One JSON file per `(command, variant)`, named
`<command>@<variant>.json`.

**This is the only copy.** apexe carries no overlays of its own — it reads this
directory like any other consumer, through `overlay_dirs`, `~/.apexe/overlays/`,
or one of the packaged locations it searches. Contributions and corrections
belong here; see [CONTRIBUTING.md](../CONTRIBUTING.md).

## What a consumer loses without this

Measured rather than assumed. Scanning `tail` with apexe, with and without the
corpus present:

| | with the corpus | without |
|---|---|---|
| flags | 10 | 9 |
| `readonly` | `true` | `false` |
| `long_running` on `-f` | present | **gone** |
| `conflicts_with` | present | **gone** |

Heuristic scanning recovers the flag names and little else. `conflicts_with` and
`long_running` have no other source at all — no `--help` or man page format
states either machine-readably, which is the reason overlays exist.

What does *not* degrade is the safety-critical half: name-based inference still
marks `rm` destructive and approval-requiring, and `tail`'s `readonly` fails
toward `false` rather than away from it. So a consumer without the corpus is
less precise, not less careful.

## Reading a file

Each carries the command's flags, mutual exclusions, operand placement, the five
behavioural annotations, and a `provenance` block whose `command` can be re-run
verbatim. The format is defined by
[`tool-overlay.schema.json`](https://github.com/aiperceivable/apexe/blob/main/schemas/tool-overlay.schema.json);
[the consumer guide](https://github.com/aiperceivable/apexe/blob/main/docs/overlay-consumers.md)
is how to read one without apexe.
