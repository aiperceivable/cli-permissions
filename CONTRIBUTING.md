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

## State all five annotations, including the boring ones

`readonly`, `destructive`, `idempotent`, `requires_approval`, `open_world` — an
entry at `confidence: verified` should state every one, even where the answer is
obviously `false`.

**Leaving one out is not neutral.** The schema requires none of them, so an
absent field means *unknown*, and a consumer reading the corpus alone has to
treat an unknown consequential property as the conservative answer. In practice
that costs the command any blanket allow: with `open_world` unstated across the
corpus, the reference consumer could not justify a single `allow` rule, for
`cat` or anything else.

`sort` is why this is a check and not a formality. It reads as a pure text
utility, and `--compress-program=PROG` runs PROG — sort spills to temporary
files past its buffer and pipes each one through the named program. It had gone
unannotated, and a consumer equating absent with false would have reported that
`sort`'s domain of interaction is closed.

For an `authoritative` overlay the check is tractable: the flag list is the
complete option set, so review every flag and operand for a value that names a
program to execute or a host to reach, then say so in `provenance.notes` —
including that the conclusion is only as good as the completeness claim above
it.

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

## Version numbers

Three numbers exist and they move independently. Confusing them is the most
common way to publish something a consumer cannot verify.

| Number | Where | What it answers | When it changes |
| --- | --- | --- | --- |
| corpus release `version` | `manifest.json` | which reviewed snapshot this is | every release |
| manifest format `schema_version` | `manifest.json` | how the manifest may be parsed | only when a consumer must change |
| overlay format `schema_version` | each overlay file | how that overlay may be parsed | only when overlay parsing changes |

The release `version` is bare SemVer (`0.2.0`); the Git tag is the same number
with a `v` prefix (`v0.2.0`). Both must describe the same bytes, so the tag is
derived from the manifest rather than typed: `tools/tag-release.sh` does that
and refuses the release when they disagree.

Choose the increment by what a consumer would have to do:

- **patch** — descriptions, provenance, metadata; no admission behaviour changes.
- **minor** — a command, flag or route is added, so the declared surface
  *widens*. A previously refused call may now be allowed; that is a security
  relevant change, not a patch.
- **major** — routes are removed or tightened, an annotation changes meaning
  (for example `readonly` becomes `destructive`), or `schema_version` changes.

Format versions are not release versions. Adding overlays or correcting flags
never changes `schema_version`; it changes `version`.

## Releasing

Releases are tags, and tags are deliberate. Pushing to `main` validates the
corpus but publishes nothing.

1. Bump `version` in `manifest.json` using the rule above.
2. Add a `## [<version>]` section to [`CHANGELOG.md`](CHANGELOG.md) — what
   changed, and why a consumer should care. The GitHub release adds the
   machine-readable overlay diff; this section is the part a script cannot
   write.
3. Commit both, merge to `main`, and let CI pass on that commit.
4. Run `tools/tag-release.sh --push`. It checks the working tree, `origin/main`,
   the changelog section, monotonic version order, a unique tag name and that
   the archive builds, then creates and pushes the tag.
5. The release workflow re-verifies the same facts, builds the archive, and
   attaches `<repo>-v<version>.tar.gz`, its `.sha256`, the stable alias
   `<repo>.tar.gz` and its `.sha256`.

The asset name is derived from the repository name by the workflow, because a
consumer resolves `<repo>.tar.gz` from the repository URL. A fork therefore
publishes under its own name without touching either repository. A fork that is
a distinct corpus rather than a mirror should also change `name` in
`manifest.json`: that is the name an installation records and the stable alias
does not.

`workflow_dispatch` accepts an **existing** tag only, for republishing a
release whose assets failed to upload. It never accepts a version number that
has no tag.

### Failure policy

These are not preferences; each one protects the identity a consumer pins.

- **A published tag is never moved and never deleted.** If the tag is wrong,
  release the next patch instead. The one exception is a tag that was rejected
  before any asset existed and that no consumer could have pinned; deleting it
  must be recorded in the issue that explains why.
- **An uploaded asset is never replaced.** Re-uploading different bytes under
  the same version makes every recorded sha256 meaningless.
- **A version number maps to exactly one byte sequence.** That is why the
  version must be greater than the previous tag, and why the archive must be
  reproducible from it.

## Corrections

A wrong entry is worse than a missing one, because `mode: authoritative` lets it
replace a consumer's own description. If you find one, an issue with the command
that disproves it is enough — you do not need to write the fix.

## License

Contributions are accepted under [Apache-2.0](LICENSE).
