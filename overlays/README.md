# overlays/

The corpus lands here.

It has not migrated yet. Today the verified overlays live in
[apexe's `overlays/`](https://github.com/aiperceivable/apexe/tree/main/overlays)
as its built-in set, and the migration is deliberately the **last** step:
the format is being decoupled from apexe first, and a second, non-apexe consumer
has to be shown to work before the data moves. Moving it earlier would mean
publishing a corpus whose only reader is the tool it was extracted from.

Until then, point apexe at its own built-ins — they are already loaded by
default — and watch this directory.

## What a file here looks like

One JSON file per `(command, variant)`, named `<command>@<variant>.json`:

```
overlays/
  sed@bsd.json
  sed@gnu.json
  find@gnu.json
```

Each carries the command's flags, mutual exclusions, operand placement,
behavioural annotations, and a `provenance` block whose `command` field can be
re-run verbatim. See [CONTRIBUTING.md](../CONTRIBUTING.md).
