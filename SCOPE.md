# Scope

> What this corpus collects, and what it deliberately does not.

## One-line definition

> A corpus of verified, re-checkable facts about what CLI commands do, keyed by
> `(command, variant)`, from which agent permission rules can be derived.

## The invariant

Every entry answers **"how do you know?"** with a command someone else can run.
That constraint is the whole product. It is why the corpus is small, why it
grows slowly, and why it is worth anything at all.

An entry that cannot be re-checked is an opinion, and there is no shortage of
opinions about which commands are dangerous.

---

## In scope

**Facts about a command's surface** — flags, their types and value shapes,
mutual exclusions, operand placement, whether `--` is honoured.

**Behavioural annotations** — `readonly`, `destructive`, `idempotent`,
`requires_approval`, `open_world`.

**Per-variant truth.** One name is often several programs. BSD `sed` rejects the
`e` flag; GNU `sed` runs it as a shell command. The variant is a first-class
part of the key, not a footnote.

**The non-obvious.** The editorial rule: *an entry whose facts you already knew
before checking does not earn its place.* "rm is dangerous" is not a fact, it is
common knowledge. That `uniq`'s second operand is a write target is a fact.

## Out of scope

**Policy.** The corpus states what a command does. Which commands your agent may
run is your decision, and it depends on your environment, not on ours.

**Enforcement.** Nothing here refuses anything. Deciding, gating and sandboxing
belong to consumers.

**Tools with rich, parseable `--help`.** Most modern Go / Rust / Python CLIs
describe themselves well enough that a scanner gets the answer right. Curating
them by hand produces a second copy that drifts. The corpus covers what
scanning structurally *cannot* do: bundled BSD usage lines, mutual exclusion
(which no help format expresses machine-readably), and operand placement.

**Interactive programs.** `vim`, `less`, `top` — an agent should not be invoking
them in a non-TTY context, and describing their flags helps nobody.

**Language runtimes.** `python3`, `node`, `ruby`. Their risk is the risk of the
script they are handed; annotating the interpreter says nothing useful.

**Platform-specific openers.** `open`, `xdg-open` — behaviour depends on file
associations, which are not a property of the command.

**Coverage counts as a goal.** Growing the number of entries is not itself
progress. One verified entry is worth more than fifty transcribed ones, because
the transcribed ones cost the corpus the only thing that distinguishes it.

---

## Relationship to apexe

[apexe](https://github.com/aiperceivable/apexe) is the first consumer and the
source of the format, not the owner of these facts. It ships a small built-in
set — deliberately short, as a proof that the mechanism works end to end — and
reads this corpus through `overlay_dirs`.

The dependency runs one way. This repository consumes apexe's schema and
loading protocol; apexe does not depend on this repository to build, test or
release.

## Relationship to permission-policy projects

Several projects define **where** permission rules live and how they translate
between agent hosts. This corpus defines **what the rules should say**. They are
complementary layers, and the split is deliberate: a format with no data is an
empty container, and data with no format reaches nobody.
