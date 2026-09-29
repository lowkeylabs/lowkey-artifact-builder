#!/usr/bin/env python3
"""
Migrate incremental engine tests to PlannedInput.source_path semantics.

PlannedInput semantics:
    source_path
        External configured source resource.
        Used for fingerprint provenance and for tests that mutate the
        external source.

    path
        Artifact-owned materialized copy.
        Used for stage execution.

This script intentionally modifies only the known stale test patterns.
It does not perform a global `.path` -> `.source_path` replacement.
"""

from __future__ import annotations

from pathlib import Path

TEST_FILES = (
    "tests/engine/test_incremental_event_sink_failures.py",
    "tests/engine/test_incremental_partial_failure.py",
    "tests/engine/test_incremental_recovery.py",
    "tests/engine/test_incremental_build_completion_failure_events.py",
    "tests/engine/test_incremental_failure_sink_isolation.py",
    "tests/engine/test_incremental_reuse_persistence.py",
    "tests/engine/test_incremental_validation.py",
    "tests/engine/test_incremental_convergence.py",
    "tests/engine/test_incremental_reused_build_events.py",
    "tests/engine/test_incremental_planning.py",
    "tests/engine/test_incremental_missing_product.py",
    "tests/engine/test_incremental_state_events.py",
    "tests/engine/test_incremental_build_events.py",
    "tests/engine/test_incremental_build_failure_events.py",
    "tests/engine/test_incremental_invalid_product.py",
    "tests/engine/test_incremental_artifact_events.py",
    "tests/engine/test_incremental_restart.py",
    "tests/engine/test_incremental_missing_completion.py",
    "tests/engine/test_incremental_build_planning_failure_events.py",
    "tests/engine/test_incremental_events.py",
)


def migrate_file(path: Path) -> int:
    """
    Replace stale PlannedInput.path uses identified by the audit.

    The listed files use these occurrences either to materialize the configured
    external source or to mutate that source for invalidation tests. Both
    operations now belong to PlannedInput.source_path.
    """

    original = path.read_text(encoding="utf-8")

    updated = original.replace(
        "planned_input.path.parent.mkdir(",
        "planned_input.source_path.parent.mkdir(",
    )

    updated = updated.replace(
        "planned_input.path.write_bytes(",
        "planned_input.source_path.write_bytes(",
    )

    if updated == original:
        return 0

    replacements = original.count("planned_input.path.parent.mkdir(") + original.count(
        "planned_input.path.write_bytes("
    )

    path.write_text(
        updated,
        encoding="utf-8",
    )

    return replacements


def main() -> None:
    repository_root = Path.cwd()

    missing: list[Path] = []
    changed_files = 0
    replacements = 0

    for relative_path in TEST_FILES:
        path = repository_root / relative_path

        if not path.is_file():
            missing.append(path)
            continue

        count = migrate_file(path)

        if count:
            changed_files += 1
            replacements += count
            print(f"updated {relative_path}: {count} replacement(s)")
        else:
            print(f"unchanged {relative_path}")

    if missing:
        print()
        print("ERROR: expected test files were not found:")

        for path in missing:
            print(f"  {path}")

        raise SystemExit(1)

    print()
    print(f"Done: {replacements} replacement(s) across {changed_files} file(s).")


if __name__ == "__main__":
    main()
