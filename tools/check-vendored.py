#!/usr/bin/env python3
"""Check that a downstream vendored copy of the corpus matches this repository.

cli-permissions is upstream: entries are written and verified here. apexe keeps
a byte-identical copy under its own `overlays/` and compiles it in with
`include_str!`, which is why it is vendored rather than submoduled — a missing
file there is a hard compile error, not a degraded feature.

    python3 tools/check-vendored.py ../apexe/overlays

Exit 0 when the two agree. Anything else is drift, and the direction matters:
a file only downstream was added in the wrong place, and a file that differs
means one of the two was edited without the other.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path


def digests(directory: Path) -> dict[str, str]:
    return {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(directory.glob("*.json"))
    }


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    upstream_dir = Path(__file__).resolve().parent.parent / "overlays"
    downstream_dir = Path(sys.argv[1])
    if not downstream_dir.is_dir():
        print(f"not a directory: {downstream_dir}", file=sys.stderr)
        return 2

    upstream, downstream = digests(upstream_dir), digests(downstream_dir)

    missing = sorted(set(upstream) - set(downstream))
    extra = sorted(set(downstream) - set(upstream))
    differing = sorted(
        name for name in set(upstream) & set(downstream)
        if upstream[name] != downstream[name]
    )

    for name in missing:
        print(f"missing downstream: {name} — vendored copy is behind upstream")
    for name in extra:
        print(f"only downstream:    {name} — added in the wrong repository")
    for name in differing:
        print(f"differs:            {name} — one side was edited without the other")

    if missing or extra or differing:
        print(
            f"\n{len(missing) + len(extra) + len(differing)} of {len(upstream)} "
            f"entries out of sync. Upstream is {upstream_dir}.",
            file=sys.stderr,
        )
        return 1

    print(f"{len(upstream)} entries, byte-identical.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
