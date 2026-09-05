# overlays/

The corpus. One JSON file per `(command, variant)`, named
`<command>@<variant>.json`.

**This is upstream.** Entries are written and verified here; apexe keeps a
byte-identical vendored copy and compiles it in. Contributions and corrections
belong in this repository — see [CONTRIBUTING.md](../CONTRIBUTING.md).

## Why apexe keeps a copy rather than pointing at this one

apexe's built-in set is loaded with `include_str!`, so a missing file is a hard
compile error rather than a degraded feature. A submodule turns
`git clone` without `--recursive` into a build failure, and the same coupling
runs through its tests and `cargo package`. Vendoring keeps that build
self-contained; `tools/check-vendored.py` is what stops the two drifting.

Dropping the built-ins instead is not an option either, and the cost is
measured rather than assumed. Removing `tail`'s overlay from apexe and
rescanning:

| | with the overlay | without |
|---|---|---|
| flags | 10 | 9 |
| `readonly` | `true` | **`false`** |
| `x-apexe-long-running` on `-f` | present | **gone** |
| `x-apexe-conflicts-with` | present | **gone** |

`readonly` flipping means the generated ACL stops auto-allowing `tail`; the
lost `long_running` means nothing warns that `tail -f` never returns. Heuristic
scanning recovers the flag names and little else.

## Reading a file

Each carries the command's flags, mutual exclusions, operand placement, the five
behavioural annotations, and a `provenance` block whose `command` can be re-run
verbatim. The format is defined by
[`tool-overlay.schema.json`](https://github.com/aiperceivable/apexe/blob/main/schemas/tool-overlay.schema.json);
[the consumer guide](https://github.com/aiperceivable/apexe/blob/main/docs/overlay-consumers.md)
is how to read one without apexe.
