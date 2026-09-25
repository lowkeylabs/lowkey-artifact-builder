#!/usr/bin/env python3
"""
Mechanically update CLI BUILD test doubles for execute_artifact_build().

The production execute_artifact_build() boundary returns:

    tuple[ExecutionPlan, ...]

Older CLI tests monkeypatch that boundary with local fake functions that
implicitly return None. The CLI now consumes the established return value,
so those fakes must return an empty tuple when they have no ExecutionPlan
result relevant to the test.

This script intentionally modifies only local functions that are explicitly
installed with:

    monkeypatch.setattr(
        cmd_build,
        "execute_artifact_build",
        <function_name>,
    )

It does NOT modify failure-display expectations or event-presentation
expectations. Those require semantic review rather than mechanical migration.
"""

from __future__ import annotations

import ast
from pathlib import Path

FILES = (
    Path("tests/cli/test_build.py"),
    Path("tests/cli/test_build_events.py"),
)


def target_function_names(source: str) -> set[str]:
    """
    Return names of functions installed as cmd_build.execute_artifact_build.
    """

    tree = ast.parse(source)

    targets: set[str] = set()

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        if not (
            isinstance(node.func, ast.Attribute)
            and node.func.attr == "setattr"
            and len(node.args) >= 3
        ):
            continue

        module_arg = node.args[0]
        attribute_arg = node.args[1]
        replacement_arg = node.args[2]

        if not (isinstance(module_arg, ast.Name) and module_arg.id == "cmd_build"):
            continue

        if not (
            isinstance(attribute_arg, ast.Constant)
            and attribute_arg.value == "execute_artifact_build"
        ):
            continue

        if not isinstance(replacement_arg, ast.Name):
            continue

        targets.add(replacement_arg.id)

    return targets


def function_nodes(
    source: str,
    targets: set[str],
) -> list[ast.FunctionDef]:
    """
    Return FunctionDef nodes corresponding to the target fake functions.
    """

    tree = ast.parse(source)

    nodes = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name in targets
    ]

    found = {node.name for node in nodes}

    missing = targets - found

    if missing:
        raise RuntimeError(f"Could not find function definitions for: {sorted(missing)}")

    return nodes


def annotation_is_none(node: ast.FunctionDef) -> bool:
    """
    Return whether a function explicitly declares -> None.
    """

    return isinstance(node.returns, ast.Constant) and node.returns.value is None


def has_terminal_empty_tuple_return(node: ast.FunctionDef) -> bool:
    """
    Return whether the function already ends with `return ()`.
    """

    if not node.body:
        return False

    statement = node.body[-1]

    return (
        isinstance(statement, ast.Return)
        and isinstance(statement.value, ast.Tuple)
        and len(statement.value.elts) == 0
    )


def indentation_for_function_body(
    lines: list[str],
    node: ast.FunctionDef,
) -> str:
    """
    Determine indentation used by statements in a function body.
    """

    if not node.body:
        raise RuntimeError(f"Function {node.name!r} unexpectedly has no body.")

    first_statement = node.body[0]
    line = lines[first_statement.lineno - 1]

    return line[: len(line) - len(line.lstrip())]


def return_annotation_span(
    source: str,
    node: ast.FunctionDef,
) -> tuple[int, int]:
    """
    Return character offsets covering the function's return annotation.

    This is used only for an explicit `-> None` annotation.
    """

    if node.returns is None:
        raise RuntimeError(f"Function {node.name!r} has no return annotation.")

    lines = source.splitlines(keepends=True)

    line_offsets: list[int] = []
    offset = 0

    for line in lines:
        line_offsets.append(offset)
        offset += len(line)

    start = line_offsets[node.returns.lineno - 1] + node.returns.col_offset
    end = line_offsets[node.returns.end_lineno - 1] + node.returns.end_col_offset

    return start, end


def line_end_offset(
    source: str,
    lineno: int,
) -> int:
    """
    Return character offset immediately after a source line.
    """

    lines = source.splitlines(keepends=True)

    return sum(len(line) for line in lines[:lineno])


def migrate_file(path: Path) -> None:
    """
    Migrate mechanical execute_artifact_build test doubles in one file.
    """

    source = path.read_text()

    targets = target_function_names(source)

    if not targets:
        print(f"{path}: no execute_artifact_build fakes found")
        return

    nodes = function_nodes(
        source,
        targets,
    )

    lines = source.splitlines(keepends=True)

    edits: list[tuple[int, int, str]] = []

    for node in nodes:
        print(f"{path}: inspecting {node.name}")

        if annotation_is_none(node):
            start, end = return_annotation_span(
                source,
                node,
            )

            edits.append(
                (
                    start,
                    end,
                    "tuple[ExecutionPlan, ...]",
                )
            )

            print("  return annotation: None -> tuple[ExecutionPlan, ...]")

        elif node.returns is None:
            raise RuntimeError(
                f"{path}: {node.name} has no return annotation; stopping rather than guessing."
            )

        else:
            annotation = ast.unparse(node.returns)

            if annotation != "tuple[ExecutionPlan, ...]":
                raise RuntimeError(
                    f"{path}: {node.name} has unexpected return annotation "
                    f"{annotation!r}; stopping rather than guessing."
                )

            print("  return annotation already current")

        if has_terminal_empty_tuple_return(node):
            print("  terminal return () already present")
            continue

        body_indent = indentation_for_function_body(
            lines,
            node,
        )

        insertion_point = line_end_offset(
            source,
            node.end_lineno,
        )

        edits.append(
            (
                insertion_point,
                insertion_point,
                f"\n{body_indent}return ()\n",
            )
        )

        print("  adding terminal return ()")

    # Apply edits backwards so earlier character offsets remain valid.
    for start, end, replacement in sorted(
        edits,
        key=lambda edit: edit[0],
        reverse=True,
    ):
        source = source[:start] + replacement + source[end:]

    # Verify that the resulting source is syntactically valid before writing.
    ast.parse(source)

    path.write_text(source)

    print(f"{path}: migrated {len(nodes)} execute_artifact_build fake(s)")


def main() -> None:
    for path in FILES:
        if not path.is_file():
            raise FileNotFoundError(path)

        migrate_file(path)


if __name__ == "__main__":
    main()
