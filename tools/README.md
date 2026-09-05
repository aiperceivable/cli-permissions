# tools/

## `derive-permissions.py`

A **reference consumer**: it turns an overlay corpus into agent permission
rules. Its job is not to be the tool you use — it is to demonstrate, rather than
assert, that the corpus is usable without apexe.

So it is deliberately handicapped. It is written in a different language from
apexe, shares no code with it, has no third-party dependencies, and was written
against [`tool-overlay.schema.json`](https://github.com/aiperceivable/apexe/blob/main/schemas/tool-overlay.schema.json)
and [the consumer guide](https://github.com/aiperceivable/apexe/blob/main/docs/overlay-consumers.md)
alone. If it needs something those two do not explain, the spec has a gap, and
the script says so on stderr instead of guessing quietly.

```bash
python3 tools/derive-permissions.py <overlay-dir> --format report
python3 tools/derive-permissions.py <overlay-dir> --format claude   # .claude/settings.json
python3 tools/derive-permissions.py <overlay-dir> --format agents   # .agents/permissions.json
```

### What it demonstrates

Selection is the part worth checking, because it is where a naive consumer goes
wrong. On the same macOS host, with the same command name:

```
$ derive-permissions.py ../apexe/overlays --format report | grep sed
sed  bsd  deny  macos macOS 26.5.2, checked 2026-09-05

$ PATH="/opt/homebrew/opt/gnu-sed/libexec/gnubin:$PATH" derive-permissions.py … | grep -A3 sed
sed  gnu  deny  sed 4.9, checked 2026-09-05
                - destructive
                - open_world: leaves this machine or runs another program
                - writes to disk via operand <input-file>
```

Every path and platform signal still says BSD; only running the declared probe
tells them apart, and only the GNU variant is `open_world` — its `s///e` runs
the replacement as a shell command, which BSD sed rejects outright. A consumer
that matched on platform alone would have got that backwards.

### What it found

Writing it is what turned "the format should be independently consumable" into
a checked claim, and it produced two results worth keeping.

It works: 22 commands derived on this host with no reference to apexe's source.

And the spec has gaps — chiefly that **no derivation rule exists from
annotations to a permission tier**, so two consumers reading this corpus can
reach different policies. They are now written down in
[§8 of the consumer guide](https://github.com/aiperceivable/apexe/blob/main/docs/overlay-consumers.md).

### One confirmed limitation of `.agents/permissions.json`

The vendor-neutral permission format keys a rule on `(tool, pattern, tier)` and
has **no place for the variant**. BSD `sed` and GNU `sed` differ on `open_world`
and on whether `-i` takes a mandatory argument, and both collapse into one rule.
The exporter emits the stricter of the two and says so on stderr rather than
silently picking one.
