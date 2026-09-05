#!/usr/bin/env python3
"""Derive agent permission rules from a cli-permissions overlay corpus.

A reference consumer, written against `tool-overlay.schema.json` and the
consumer guide alone — deliberately not sharing a line with apexe, and in a
different language, so that "the format is independently consumable" is
demonstrated rather than asserted.

    python3 derive-permissions.py <overlay-dir> [--format claude|agents|report]

No third-party dependencies. Reads JSON overlays; YAML ones are skipped with a
note, since the format permits them and the standard library cannot parse them.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

# --- Match strength, strongest first. Section 2 of the consumer guide. -------
STRENGTH_PROBE = 3
STRENGTH_PLATFORM_GLOBS = 2
STRENGTH_PLATFORM = 1
STRENGTH_UNCONDITIONAL = 0


@dataclass
class Gap:
    """Something the spec did not settle, recorded rather than guessed."""

    where: str
    question: str


GAPS: list[Gap] = []


def note_gap(where: str, question: str) -> None:
    if not any(g.where == where and g.question == question for g in GAPS):
        GAPS.append(Gap(where, question))


def host_platform() -> str:
    """`std::env::consts::OS` spelling, lower-cased — schema `$defs/platform`."""
    system = platform.system().lower()
    return {"darwin": "macos", "windows": "windows"}.get(system, system)


def load_overlays(directory: Path) -> tuple[list[dict], list[str]]:
    overlays, skipped = [], []
    for path in sorted(directory.iterdir()):
        if path.suffix in {".yaml", ".yml"}:
            skipped.append(f"{path.name} (YAML needs a parser this script avoids)")
            continue
        if path.suffix != ".json" or path.name == "README.md":
            continue
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            skipped.append(f"{path.name} ({exc})")
            continue
        if doc.get("schema_version") != "1.0":
            skipped.append(f"{path.name} (schema_version {doc.get('schema_version')!r})")
            continue
        doc["_file"] = path.name
        overlays.append(doc)
    return overlays, skipped


def run_probe(binary: str, probe: dict) -> bool:
    """Run the declared probe. A probe that cannot run is a failed condition."""
    try:
        proc = subprocess.run(
            [binary, *probe["args"]],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    succeeded = proc.returncode == 0
    if probe["expect"] == "success" and not succeeded:
        return False
    if probe["expect"] == "failure" and succeeded:
        return False
    wanted = probe.get("output_contains")
    if wanted is not None:
        # The schema says "combined stdout and stderr" — a BSD tool that
        # rejects --version prints its usage line to stderr.
        if wanted not in (proc.stdout + proc.stderr):
            return False
    return True


def evaluate_match(overlay: dict, binary: str | None) -> int | None:
    """Strength if every declared condition holds, else None.

    "Every declared condition must hold. A condition that is stated and not
    satisfied rejects the overlay outright." — consumer guide §2.
    """
    match = overlay.get("match") or {}
    if not match:
        return STRENGTH_UNCONDITIONAL

    platforms = match.get("platform") or []
    if platforms and host_platform() not in [p.lower() for p in platforms]:
        return None

    globs = match.get("binary_globs") or []
    if globs:
        if binary is None or not any(fnmatch.fnmatch(binary, g) for g in globs):
            return None

    if "version_range" in match:
        note_gap(
            "match.version_range",
            "The schema gives the syntax ('>=9.0', comma-ANDed) but neither it "
            "nor the guide says how a consumer obtains the version to compare "
            "against, or what to do when it cannot. Treated as satisfied here.",
        )

    if "probe" in match:
        if binary is None or not run_probe(binary, match["probe"]):
            return None
        return STRENGTH_PROBE

    if platforms and globs:
        return STRENGTH_PLATFORM_GLOBS
    if platforms:
        return STRENGTH_PLATFORM
    return STRENGTH_UNCONDITIONAL


def select(overlays: list[dict], command: str, binary: str | None) -> dict | None:
    candidates = []
    for overlay in overlays:
        if overlay["command"] != command:
            continue
        strength = evaluate_match(overlay, binary)
        if strength is not None:
            candidates.append((strength, overlay))
    if not candidates:
        return None
    best = max(s for s, _ in candidates)
    tied = [o for s, o in candidates if s == best]
    if len(tied) > 1:
        note_gap(
            "tie-break",
            f"{command}: {len(tied)} overlays tie at equal strength "
            f"({', '.join(o['_file'] for o in tied)}). The guide says the more "
            "local source wins, which assumes a consumer with layered sources; "
            "a single-directory consumer has no such signal. Taking the last.",
        )
    return tied[-1]


# --- Deriving a rule --------------------------------------------------------

@dataclass
class Verdict:
    command: str
    variant: str
    tier: str  # allow | ask | deny
    reasons: list[str] = field(default_factory=list)
    evidence: str = ""


WRITES_TO_DISK = ("truncat", "rewritten", "created if it does not exist")


def derive(overlay: dict) -> Verdict:
    ann = overlay.get("annotations") or {}
    reasons: list[str] = []

    if not ann:
        note_gap(
            "annotations",
            f"{overlay['_file']}: no annotations at all. Every field is optional, "
            "so the overlay declines to say — but the guide does not tell a "
            "consumer what to default to. Treated as unknown -> ask.",
        )
        return Verdict(overlay["command"], overlay["variant"], "ask",
                       ["no behavioural annotations"], provenance_line(overlay))

    # An absent field means "unknown" and must NOT be read as false — guide §6.
    # Writing `ann.get("open_world")` and testing it for truth is how this
    # script originally got it wrong, and `sort` is why that matters: it reads
    # as a pure text utility and `--compress-program=PROG` runs PROG.
    def stated(field: str) -> bool | None:
        return ann[field] if field in ann else None

    destructive = stated("destructive")
    readonly = stated("readonly")
    open_world = stated("open_world")
    approval = stated("requires_approval")

    unknown = [f for f in ("destructive", "readonly", "open_world")
               if stated(f) is None]
    if unknown:
        reasons.append(f"unstated: {', '.join(unknown)} (read as unknown, not false)")

    if destructive is True:
        reasons.append("destructive")
    if open_world is True:
        reasons.append("open_world: leaves this machine or runs another program")
    if approval is True and destructive is not True:
        reasons.append("requires_approval")

    # Guide §6: readonly is a claim about local state and says nothing about
    # what the command sends. readonly + open_world is the exfiltration shape.
    if readonly is True and open_world is True:
        reasons.append("readonly but open_world — the exfiltration shape")

    # Guide §5: a flag that may not terminate hangs an agent even on a
    # command whose annotations are otherwise harmless.
    long_running = [flag_name(f) for f in overlay.get("flags", [])
                    if f.get("long_running")]
    if long_running:
        reasons.append(f"never terminates with {', '.join(long_running)}")

    # Guide §6: a command can destroy without a destructive-looking flag.
    hidden = hidden_writes(overlay)
    if hidden:
        reasons.append(f"writes to disk via {', '.join(hidden)}")

    if destructive is True or open_world is True:
        tier = "deny"
    elif long_running or hidden or approval is True:
        tier = "ask"
    elif readonly is True and open_world is False:
        # Only a *stated* closed world earns a blanket allow. `readonly` alone
        # is a claim about local state; without open_world it is not enough.
        tier = "allow"
    elif readonly is True:
        tier = "ask"
        reasons.append("readonly, but nothing states whether it stays local")
    elif destructive is False and readonly is False:
        # Neither: mkdir, touch. They create but destroy nothing, and the
        # format has no word for that — guide §8.
        tier = "ask"
        reasons.append("neither readonly nor destructive")
    else:
        tier = "ask"
        reasons.append("too little stated to judge")

    return Verdict(overlay["command"], overlay["variant"], tier, reasons,
                   provenance_line(overlay))


def flag_name(flag: dict) -> str:
    return flag.get("long") or flag.get("short") or "?"


def hidden_writes(overlay: dict) -> list[str]:
    found = []
    for operand in overlay.get("positional_args", []):
        text = (operand.get("description") or "").lower()
        if operand.get("type") == "path" and any(k in text for k in WRITES_TO_DISK):
            found.append(f"operand <{operand['name']}>")
    for flag in overlay.get("flags", []):
        text = (flag.get("description") or "").lower()
        carries_file = flag.get("type") == "path" or "FILE" in (flag.get("value_name") or "")
        if carries_file and any(k in text for k in WRITES_TO_DISK):
            found.append(flag_name(flag))
    return found


def provenance_line(overlay: dict) -> str:
    prov = overlay.get("provenance") or {}
    if not prov:
        return f"confidence={overlay.get('confidence', 'low')}, no provenance"
    return (f"{prov.get('package') or prov.get('platform')} "
            f"{prov.get('tool_version')}, checked {prov.get('checked_on')}")


# --- Output -----------------------------------------------------------------

def emit_claude(verdicts: list[Verdict]) -> str:
    buckets: dict[str, list[str]] = {"allow": [], "ask": [], "deny": []}
    for v in sorted(verdicts, key=lambda x: x.command):
        rule = f"Bash({v.command}:*)"
        if rule not in buckets[v.tier]:
            buckets[v.tier].append(rule)
    return json.dumps({"permissions": buckets}, indent=2)


def emit_agents(verdicts: list[Verdict]) -> str:
    note_gap(
        ".agents/permissions.json",
        "The vendor-neutral format keys a rule on (tool, pattern, tier). It has "
        "no place for the variant, so BSD sed and GNU sed — which differ on "
        "open_world and on -i — collapse to one rule. Emitting the stricter of "
        "the two, and recording the loss here.",
    )
    seen: dict[str, Verdict] = {}
    order = {"deny": 0, "ask": 1, "allow": 2}
    for v in verdicts:
        prior = seen.get(v.command)
        if prior is None or order[v.tier] < order[prior.tier]:
            seen[v.command] = v
    rules = [{"tool": "Bash", "pattern": f"{v.command}:*", "tier": v.tier}
             for v in sorted(seen.values(), key=lambda x: x.command)]
    return json.dumps({"defaultMode": "standard", "rules": rules}, indent=2)


def emit_report(verdicts: list[Verdict]) -> str:
    lines = [f"{'command':<10} {'variant':<7} {'tier':<6} evidence / why", "-" * 96]
    for v in sorted(verdicts, key=lambda x: (x.command, x.variant)):
        lines.append(f"{v.command:<10} {v.variant:<7} {v.tier:<6} {v.evidence}")
        for reason in v.reasons:
            lines.append(f"{'':<25} - {reason}")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("overlay_dir", type=Path)
    ap.add_argument("--format", choices=["claude", "agents", "report"], default="report")
    ap.add_argument("--all-variants", action="store_true",
                    help="derive for every overlay, not only those matching this host")
    args = ap.parse_args()

    overlays, skipped = load_overlays(args.overlay_dir)
    if not overlays:
        print(f"no overlays in {args.overlay_dir}", file=sys.stderr)
        return 1

    verdicts = []
    if args.all_variants:
        verdicts = [derive(o) for o in overlays]
    else:
        for command in sorted({o["command"] for o in overlays}):
            binary = shutil.which(command)
            chosen = select(overlays, command, binary)
            if chosen is None:
                note_gap("selection",
                         f"{command}: no overlay matched this host "
                         f"(binary={'found' if binary else 'not on PATH'}).")
                continue
            verdicts.append(derive(chosen))

    emit = {"claude": emit_claude, "agents": emit_agents, "report": emit_report}[args.format]
    print(emit(verdicts))

    if skipped:
        print("\n# skipped:", file=sys.stderr)
        for s in skipped:
            print(f"#   {s}", file=sys.stderr)
    if GAPS:
        print(f"\n# {len(GAPS)} spec gaps hit while deriving:", file=sys.stderr)
        for g in GAPS:
            print(f"#   [{g.where}] {g.question}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
