# Contributing

The bar is not "is this correct?" — it is **"can someone else re-run your
check?"** Everything below follows from that.

## Before you write anything

Read the [authoring and verification procedure](https://github.com/aiperceivable/apexe/blob/main/docs/overlays.md).
It is the normative document and it is long for a reason: it is written from the
mistakes this corpus has actually made, including three occasions where a
checker produced a **false accusation** and the overlay under suspicion turned
out to be right.

Two rules from it are worth repeating here, because they are the ones people
skip:

**Do not write an entry from knowledge of a tool.** It produces plausible,
mostly-correct output that systematically misses recent additions — and being
mostly correct is exactly what makes the failure hard to notice. An earlier
`ls@gnu` written this way scored 100% precision and silently missed `--zero`,
added in coreutils 8.25.

**Do not claim `confidence: verified` without `provenance`.** The schema
enforces the block's presence; what it cannot enforce is that you actually ran
the thing. `provenance.command` must be re-runnable **verbatim** by a stranger,
and `provenance.environment` must pin the exact build — an image digest, not a
tag, since tags move.

## What a good entry looks like

Not "this flag is destructive", but the probe that shows it:

```
Probed on macOS 26.5.2: `sed -i 's/a/X/' t1.txt` consumes `s/a/X/` as the backup
extension and reads `t1.txt` as the script — observed `undefined label '1.txt'`,
exit 1, file unmodified. `sed -i.bak 's/a/X/' t3.txt` succeeds and writes
t3.txt.bak. The attached spelling is the only one that also works on GNU.
```

Someone reading that a year from now can decide whether it still holds, and can
find out in one command. That is the standard.

## The editorial rule

**An entry whose facts you already knew before checking does not earn its
place.** The corpus is not trying to describe every flag of every tool; it is
trying to hold the ones that are wrong in people's heads. If your check
confirmed what you expected and nothing surprised you, the entry is probably not
worth adding — and if it is, say plainly in `notes` that the obvious answer was
confirmed, which is itself useful.

## Which tools to cover

See [SCOPE.md](SCOPE.md). Briefly: tools whose `--help` a scanner already parses
correctly do **not** belong here. What belongs is what scanning structurally
cannot produce — bundled BSD usage lines, mutual exclusion, operand placement.

## Checklist

1. Confirm heuristic scanning genuinely cannot do the job.
2. Obtain the reference installation — the host for BSD, a pinned container for
   GNU/BusyBox.
3. Read the real flag list from `man` / `--help`. Not from memory.
4. Add `conflicts_with` by reading the prose. Nothing else can produce it.
5. Diff your list against the reference in **both** directions — and
   sanity-check your extractor before believing a difference.
6. Record `provenance` with a re-runnable `command` and a digest-pinned
   `environment`.
7. Choose `authoritative` only if you closed the option set against the running
   tool; otherwise `merge`.
8. Validate against the schema.
9. Open a PR describing what you ran, not what you concluded.

## Corrections

A wrong entry is worse than a missing one, because `mode: authoritative` lets it
replace a consumer's own description. If you find one, an issue with the command
that disproves it is enough — you do not need to write the fix.

## License

Contributions are accepted under [Apache-2.0](LICENSE).
