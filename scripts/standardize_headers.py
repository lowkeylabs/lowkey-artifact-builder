#!/usr/bin/env python3

"""
Standardize Python source-file headers.

Inspects Python files for a module docstring followed by project-relative
file metadata, copyright information, and an SPDX license identifier.

The default behavior is a dry run that reports required changes without
modifying files.

Use --add-missing to add missing header elements without changing existing
ones. Use --replace to replace existing header metadata with canonical
values without adding missing elements. Use --clean to normalize header
formatting and spacing without adding or replacing header sections.

The --summarize option is reserved for future LLM-assisted replacement of
module docstrings with summaries of module contents.
"""
# File: scripts/standardize_headers.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import argparse
import ast
import sys
from dataclasses import dataclass
from pathlib import Path

COPYRIGHT = "Copyright 2026 LowKeyLabs LLC"
LICENSE = "SPDX-License-Identifier: Apache-2.0"

DEFAULT_DIRECTORIES = (
    "src",
    "tests",
    "scripts",
)

EXCLUDED_DIRECTORIES = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "__pycache__",
    "build",
    "dist",
}

HEADER_PREFIXES = (
    "# File:",
    "# Copyright",
    "# SPDX-License-Identifier:",
)


@dataclass(frozen=True)
class HeaderStatus:
    """
    Describe the standard-header state of one Python source file.
    """

    has_docstring: bool
    file_line: str | None
    copyright_line: str | None
    license_line: str | None

    @property
    def missing(self) -> tuple[str, ...]:
        """
        Return names of missing header elements.
        """

        missing: list[str] = []

        if not self.has_docstring:
            missing.append("docstring")

        if self.file_line is None:
            missing.append("file")

        if self.copyright_line is None:
            missing.append("copyright")

        if self.license_line is None:
            missing.append("license")

        return tuple(missing)


def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments.
    """

    parser = argparse.ArgumentParser(
        description="Inspect or standardize Python source-file headers.",
    )

    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help=("Files or directories to process. Defaults to src, tests, and scripts."),
    )

    actions = parser.add_mutually_exclusive_group()

    actions.add_argument(
        "--add-missing",
        action="store_true",
        help=("Add missing docstring and header elements. Existing content is preserved."),
    )

    actions.add_argument(
        "--replace",
        action="store_true",
        help=(
            "Replace existing standard header metadata with canonical "
            "values. Missing elements are not added and the module "
            "docstring is preserved."
        ),
    )

    actions.add_argument(
        "--clean",
        action="store_true",
        help=(
            "Normalize header formatting and spacing without adding or replacing header sections."
        ),
    )

    actions.add_argument(
        "--summarize",
        action="store_true",
        help=("Replace module docstrings with LLM-generated summaries (not yet implemented)."),
    )

    return parser.parse_args()


def project_root() -> Path:
    """
    Locate the project root containing pyproject.toml.
    """

    path = Path(__file__).resolve().parent

    for candidate in (
        path,
        *path.parents,
    ):
        if (candidate / "pyproject.toml").is_file():
            return candidate

    raise RuntimeError("Could not locate project root containing pyproject.toml.")


def python_files(
    root: Path,
    paths: list[Path],
) -> tuple[Path, ...]:
    """
    Return Python files contained in the requested paths.
    """

    requested = paths or [Path(directory) for directory in DEFAULT_DIRECTORIES]

    files: set[Path] = set()

    for requested_path in requested:
        path = requested_path

        if not path.is_absolute():
            path = root / path

        if path.is_file():
            if path.suffix == ".py":
                files.add(path.resolve())

            continue

        if not path.is_dir():
            raise RuntimeError(f"Path does not exist: {requested_path}")

        for candidate in path.rglob("*.py"):
            if _is_excluded(candidate, root):
                continue

            files.add(candidate.resolve())

    return tuple(
        sorted(
            files,
            key=lambda path: path.relative_to(root).as_posix(),
        )
    )


def _is_excluded(
    path: Path,
    root: Path,
) -> bool:
    """
    Return whether a path belongs to an excluded directory.
    """

    relative = path.resolve().relative_to(root.resolve())

    return any(part in EXCLUDED_DIRECTORIES for part in relative.parts)


def module_docstring_range(
    source: str,
) -> tuple[int, int] | None:
    """
    Return the zero-based line range occupied by the module docstring.

    The returned end position is exclusive.
    """

    try:
        module = ast.parse(source)

    except SyntaxError as exc:
        raise RuntimeError(f"Cannot parse Python source: {exc}") from exc

    if not module.body:
        return None

    first = module.body[0]

    if not (
        isinstance(first, ast.Expr)
        and isinstance(first.value, ast.Constant)
        and isinstance(first.value.value, str)
    ):
        return None

    if first.lineno is None or first.end_lineno is None:
        raise RuntimeError("Python AST did not provide docstring locations.")

    return (
        first.lineno - 1,
        first.end_lineno,
    )


def inspect_source(
    source: str,
) -> HeaderStatus:
    """
    Inspect the standard header elements in Python source.
    """

    lines = source.splitlines()

    return HeaderStatus(
        has_docstring=module_docstring_range(source) is not None,
        file_line=_find_header_line(
            lines,
            prefix="# File:",
        ),
        copyright_line=_find_header_line(
            lines,
            prefix="# Copyright",
        ),
        license_line=_find_header_line(
            lines,
            prefix="# SPDX-License-Identifier:",
        ),
    )


def expected_header(
    relative_path: str,
) -> tuple[str, str, str]:
    """
    Return the canonical metadata header for one source file.
    """

    return (
        f"# File: {relative_path}",
        f"# {COPYRIGHT}",
        f"# {LICENSE}",
    )


def module_name(
    relative_path: str,
) -> str:
    """
    Return a descriptive Python module name for a project-relative path.

    Source files beneath src are represented by their importable module
    names. Other Python files use their project-relative dotted names.
    """

    path = Path(relative_path)

    if path.parts and path.parts[0] == "src":
        path = Path(*path.parts[1:])

    parts = list(path.with_suffix("").parts)

    if parts and parts[-1] == "__init__":
        parts.pop()

    if not parts:
        return relative_path

    return ".".join(parts)


def generated_docstring(
    relative_path: str,
) -> list[str]:
    """
    Return a minimal module docstring for a Python source file.

    The generated description identifies the module without attempting
    to infer its purpose. Semantic documentation may later be generated
    explicitly with --summarize.
    """

    name = module_name(relative_path)

    return [
        '"""',
        f"Module for {name}.",
        '"""',
    ]


def add_missing_source(
    source: str,
    *,
    relative_path: str,
) -> tuple[str, tuple[str, ...]]:
    """
    Add missing standard header elements.

    Existing module docstrings and existing metadata lines are preserved.
    A missing module docstring receives a minimal generated description.

    Newly added metadata is placed immediately after the module docstring
    without an intervening blank line.
    """

    newline = _newline_for(source)
    had_final_newline = source.endswith(("\n", "\r\n"))

    lines = source.splitlines()
    status = inspect_source(source)

    changes: list[str] = []

    if not status.has_docstring:
        lines = _insert_missing_docstring(
            lines,
            relative_path=relative_path,
        )

        changes.append("docstring")

    working_source = _join_lines(
        lines,
        newline=newline,
        final_newline=had_final_newline,
    )

    docstring_range = module_docstring_range(
        working_source,
    )

    if docstring_range is None:
        raise RuntimeError("Failed to locate module docstring.")

    _, docstring_end = docstring_range

    expected_file, expected_copyright, expected_license = expected_header(relative_path)

    additions: list[str] = []

    if status.file_line is None:
        additions.append(expected_file)
        changes.append("file")

    if status.copyright_line is None:
        additions.append(expected_copyright)
        changes.append("copyright")

    if status.license_line is None:
        additions.append(expected_license)
        changes.append("license")

    if additions:
        insertion = docstring_end

        # If the docstring itself was just generated, we own the
        # surrounding whitespace and can use the canonical layout.
        if "docstring" in changes:
            while insertion < len(lines) and not lines[insertion].strip():
                del lines[insertion]

        lines[insertion:insertion] = additions

        after_header = insertion + len(additions)

        if after_header < len(lines) and lines[after_header].strip():
            lines.insert(
                after_header,
                "",
            )

    return (
        _join_lines(
            lines,
            newline=newline,
            final_newline=had_final_newline,
        ),
        tuple(changes),
    )


def replace_source(
    source: str,
    *,
    relative_path: str,
) -> tuple[str, tuple[str, ...]]:
    """
    Replace existing standard metadata with canonical values.

    Missing metadata is not added. The module docstring and spacing are
    preserved.
    """

    newline = _newline_for(source)
    had_final_newline = source.endswith(("\n", "\r\n"))

    lines = source.splitlines()

    expected_file, expected_copyright, expected_license = expected_header(relative_path)

    replacements = (
        (
            "# File:",
            expected_file,
            "file",
        ),
        (
            "# Copyright",
            expected_copyright,
            "copyright",
        ),
        (
            "# SPDX-License-Identifier:",
            expected_license,
            "license",
        ),
    )

    changes: list[str] = []

    for prefix, expected, name in replacements:
        index = _find_header_index(
            lines,
            prefix=prefix,
        )

        if index is None:
            continue

        if lines[index] == expected:
            continue

        lines[index] = expected
        changes.append(name)

    return (
        _join_lines(
            lines,
            newline=newline,
            final_newline=had_final_newline,
        ),
        tuple(changes),
    )


def clean_source(
    source: str,
) -> tuple[str, tuple[str, ...]]:
    """
    Normalize spacing around existing standard header sections.

    Cleaning never adds a missing docstring or metadata field and never
    changes the contents of existing docstrings or metadata lines.

    When a module docstring and metadata header are both present, metadata
    is placed immediately after the docstring with no blank lines between
    them. Existing consecutive metadata lines are compacted together, and
    exactly one blank line follows the metadata block.
    """

    newline = _newline_for(source)
    had_final_newline = source.endswith(("\n", "\r\n"))

    lines = source.splitlines()

    docstring_range = module_docstring_range(source)

    if docstring_range is None:
        return source, ()

    _, docstring_end = docstring_range

    metadata_indices = [index for index, line in enumerate(lines) if _is_header_line(line)]

    if not metadata_indices:
        return source, ()

    # Only clean metadata that belongs to the module header. Header
    # metadata is expected to occur before the first substantive Python
    # statement following the docstring.
    first_code = _first_code_line_after(
        lines,
        docstring_end,
    )

    header_indices = [
        index for index in metadata_indices if first_code is None or index < first_code
    ]

    if not header_indices:
        return source, ()

    metadata_lines = [lines[index] for index in header_indices]

    # Remove the existing header metadata lines. Remove blank lines in
    # the same header region as well; they will be reconstructed below.
    header_index_set = set(header_indices)

    region_end = max(header_indices) + 1

    retained_region = [
        line
        for index, line in enumerate(
            lines[docstring_end:region_end],
            start=docstring_end,
        )
        if (index not in header_index_set and line.strip())
    ]

    # Be conservative. If nonblank, non-header material occurs between
    # the docstring and metadata, do not move metadata across it.
    if retained_region:
        return source, ()

    before = lines[:docstring_end]
    after = lines[region_end:]

    while after and not after[0].strip():
        after.pop(0)

    cleaned_lines = [
        *before,
        *metadata_lines,
    ]

    if after:
        cleaned_lines.append("")
        cleaned_lines.extend(after)

    updated = _join_lines(
        cleaned_lines,
        newline=newline,
        final_newline=had_final_newline,
    )

    if updated == source:
        return source, ()

    return updated, ("spacing",)


def _insert_missing_docstring(
    lines: list[str],
    *,
    relative_path: str,
) -> list[str]:
    """
    Insert a minimal module docstring without disturbing a shebang.
    """

    result = list(lines)

    insertion = 0

    if result and result[0].startswith("#!"):
        insertion = 1

        while insertion < len(result) and not result[insertion].strip():
            insertion += 1

    result[insertion:insertion] = generated_docstring(
        relative_path,
    )

    return result


def _find_header_line(
    lines: list[str],
    *,
    prefix: str,
) -> str | None:
    """
    Return an existing standard header line.
    """

    index = _find_header_index(
        lines,
        prefix=prefix,
    )

    if index is None:
        return None

    return lines[index]


def _find_header_index(
    lines: list[str],
    *,
    prefix: str,
) -> int | None:
    """
    Return the index of an existing standard header line.
    """

    for index, line in enumerate(lines):
        if line.strip().startswith(prefix):
            return index

    return None


def _is_header_line(
    line: str,
) -> bool:
    """
    Return whether a line is recognized standard header metadata.
    """

    stripped = line.strip()

    return any(stripped.startswith(prefix) for prefix in HEADER_PREFIXES)


def _first_code_line_after(
    lines: list[str],
    start: int,
) -> int | None:
    """
    Return the first substantive non-header line after an index.

    Blank lines and standard header metadata are ignored.
    """

    for index in range(
        start,
        len(lines),
    ):
        line = lines[index]

        if not line.strip():
            continue

        if _is_header_line(line):
            continue

        return index

    return None


def _newline_for(
    source: str,
) -> str:
    """
    Return the newline convention used by source.
    """

    if "\r\n" in source:
        return "\r\n"

    return "\n"


def _join_lines(
    lines: list[str],
    *,
    newline: str,
    final_newline: bool,
) -> str:
    """
    Join source lines while preserving final-newline behavior.
    """

    result = newline.join(lines)

    if final_newline:
        result += newline

    return result


def describe_dry_run(
    path: Path,
    *,
    root: Path,
) -> bool:
    """
    Report standard-header changes that could be made to one file.

    Return True when the file has all required elements with canonical
    metadata values and canonical header spacing.
    """

    relative_path = path.relative_to(root).as_posix()

    source = path.read_text(
        encoding="utf-8",
    )

    try:
        status = inspect_source(source)

        _, clean_changes = clean_source(
            source,
        )

    except RuntimeError as exc:
        print(
            f"ERROR {relative_path}: {exc}",
            file=sys.stderr,
        )

        return False

    expected_file, expected_copyright, expected_license = expected_header(relative_path)

    changes: list[str] = []

    for name in status.missing:
        changes.append(f"add {name}")

    existing = (
        (
            "file",
            status.file_line,
            expected_file,
        ),
        (
            "copyright",
            status.copyright_line,
            expected_copyright,
        ),
        (
            "license",
            status.license_line,
            expected_license,
        ),
    )

    for name, actual, expected in existing:
        if actual is not None and actual != expected:
            changes.append(f"replace {name}")

    if clean_changes:
        changes.append("clean spacing")

    if not changes:
        print(f"OK    {relative_path}")
        return True

    print(f"DRY   {relative_path}: " + ", ".join(changes))

    return False


def process_add_missing(
    path: Path,
    *,
    root: Path,
) -> bool:
    """
    Add missing standard header elements to one file.
    """

    relative_path = path.relative_to(root).as_posix()

    source = path.read_text(
        encoding="utf-8",
    )

    try:
        updated, changes = add_missing_source(
            source,
            relative_path=relative_path,
        )

    except RuntimeError as exc:
        print(
            f"ERROR {relative_path}: {exc}",
            file=sys.stderr,
        )

        return False

    if not changes:
        print(f"OK    {relative_path}")
        return True

    path.write_text(
        updated,
        encoding="utf-8",
    )

    print(f"ADDED {relative_path}: " + ", ".join(changes))

    return True


def process_replace(
    path: Path,
    *,
    root: Path,
) -> bool:
    """
    Replace existing standard header metadata in one file.
    """

    relative_path = path.relative_to(root).as_posix()

    source = path.read_text(
        encoding="utf-8",
    )

    try:
        updated, changes = replace_source(
            source,
            relative_path=relative_path,
        )

    except RuntimeError as exc:
        print(
            f"ERROR {relative_path}: {exc}",
            file=sys.stderr,
        )

        return False

    if not changes:
        print(f"OK    {relative_path}")
        return True

    path.write_text(
        updated,
        encoding="utf-8",
    )

    print(f"REPLACED {relative_path}: " + ", ".join(changes))

    return True


def process_clean(
    path: Path,
    *,
    root: Path,
) -> bool:
    """
    Clean formatting and spacing of an existing standard header.
    """

    relative_path = path.relative_to(root).as_posix()

    source = path.read_text(
        encoding="utf-8",
    )

    try:
        updated, changes = clean_source(
            source,
        )

    except RuntimeError as exc:
        print(
            f"ERROR {relative_path}: {exc}",
            file=sys.stderr,
        )

        return False

    if not changes:
        print(f"OK    {relative_path}")
        return True

    path.write_text(
        updated,
        encoding="utf-8",
    )

    print(f"CLEANED {relative_path}: " + ", ".join(changes))

    return True


def summarize_files(
    files: tuple[Path, ...],
    *,
    root: Path,
) -> int:
    """
    Replace module docstrings with LLM-generated module summaries.

    This is a placeholder for future LLM integration.
    """

    del files
    del root

    print(
        "--summarize is reserved for future LLM-assisted module summarization.",
        file=sys.stderr,
    )

    return 2


def main() -> int:
    """
    Run the standard-header utility.
    """

    args = parse_args()

    try:
        root = project_root()

        files = python_files(
            root,
            args.paths,
        )

    except RuntimeError as exc:
        print(
            f"ERROR: {exc}",
            file=sys.stderr,
        )

        return 2

    if args.summarize:
        return summarize_files(
            files,
            root=root,
        )

    if args.add_missing:
        results = [
            process_add_missing(
                path,
                root=root,
            )
            for path in files
        ]

        return 0 if all(results) else 1

    if args.replace:
        results = [
            process_replace(
                path,
                root=root,
            )
            for path in files
        ]

        return 0 if all(results) else 1

    if args.clean:
        results = [
            process_clean(
                path,
                root=root,
            )
            for path in files
        ]

        return 0 if all(results) else 1

    # Default behavior is intentionally read-only.
    results = [
        describe_dry_run(
            path,
            root=root,
        )
        for path in files
    ]

    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
