#!/usr/bin/env python3
"""
Migrate stale acceptance-test CREATE invocations to the explicit CREATE CLI.

Converts:

    result = runner.invoke(
        cli,
        [
            "create",
            "nydeli",
        ],
        input="1\\n",
    )

to:

    result = runner.invoke(
        cli,
        [
            "create",
            "--artifact-id=nydeli",
            "--source=nydeli-clean.png",
        ],
    )

Only the explicitly listed acceptance-test files are modified.
"""

from __future__ import annotations

import re
from pathlib import Path

FILES = [
    Path("tests/acceptance/test_color_analysis.py"),
    Path("tests/acceptance/test_incremental_build.py"),
    Path("tests/acceptance/test_incremental_completion_identity.py"),
    Path("tests/acceptance/test_incremental_completion_recovery.py"),
    Path("tests/acceptance/test_incremental_fingerprint_recovery.py"),
    Path("tests/acceptance/test_incremental_invalidation.py"),
    Path("tests/acceptance/test_incremental_parameters.py"),
    Path("tests/acceptance/test_incremental_product_recovery.py"),
    Path("tests/acceptance/test_png_to_3mf.py"),
]


PATTERN = re.compile(
    r"""
    (?P<prefix>
        runner\.invoke\(
        \s*
        cli,
        \s*
        \[
        \s*
        "create",
        \s*
    )
    "nydeli",
    (?P<middle>
        \s*
        \],
        \s*
    )
    input="1\\n",
    (?P<suffix>
        \s*
        \)
    )
    """,
    re.VERBOSE,
)


def replacement(match: re.Match[str]) -> str:
    prefix = match.group("prefix")
    middle = match.group("middle")
    suffix = match.group("suffix")

    return (
        f'{prefix}"--artifact-id=nydeli",\n            "--source=nydeli-clean.png",{middle}{suffix}'
    )


def migrate_file(path: Path) -> int:
    if not path.is_file():
        raise SystemExit(f"ERROR: expected file does not exist: {path}")

    original = path.read_text(encoding="utf-8")
    migrated, count = PATTERN.subn(replacement, original)

    if count == 0:
        print(f"UNCHANGED  {path}")
        return 0

    path.write_text(migrated, encoding="utf-8")
    print(f"UPDATED    {path} ({count} replacement{'s' if count != 1 else ''})")
    return count


def main() -> None:
    total = 0

    for path in FILES:
        total += migrate_file(path)

    print()
    print(f"Completed: {total} CREATE invocation(s) migrated.")


if __name__ == "__main__":
    main()
