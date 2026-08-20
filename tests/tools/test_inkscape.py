"""
Tests for the Inkscape tool interface.
"""

from pathlib import Path
from subprocess import CompletedProcess

import pytest

from lowkey_artifact_builder.tools import inkscape

# =========================================================
# Unit conversion
# =========================================================


def test_px_to_mm() -> None:
    """
    SVG pixels are converted using 96 pixels per inch.
    """

    assert inkscape.px_to_mm(96.0) == pytest.approx(25.4)

    assert inkscape.px_to_mm(0.0) == 0.0


# =========================================================
# Executable discovery
# =========================================================


def test_find_inkscape_uses_configured_executable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    The configured executable takes precedence over PATH.
    """

    executable = tmp_path / "inkscape"
    executable.touch()

    monkeypatch.setenv(
        inkscape.INKSCAPE_ENVIRONMENT_VARIABLE,
        str(executable),
    )

    monkeypatch.setattr(
        inkscape.shutil,
        "which",
        lambda name: "/usr/bin/inkscape",
    )

    assert inkscape.find_inkscape() == str(executable)


def test_find_inkscape_rejects_missing_configured_executable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    An explicitly configured missing executable is an error.
    """

    executable = tmp_path / "missing-inkscape"

    monkeypatch.setenv(
        inkscape.INKSCAPE_ENVIRONMENT_VARIABLE,
        str(executable),
    )

    with pytest.raises(
        inkscape.InkscapeError,
        match="does not exist",
    ):
        inkscape.find_inkscape()


def test_find_inkscape_uses_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Inkscape is discovered from PATH when not configured.
    """

    monkeypatch.delenv(
        inkscape.INKSCAPE_ENVIRONMENT_VARIABLE,
        raising=False,
    )

    monkeypatch.setattr(
        inkscape.shutil,
        "which",
        lambda name: "/usr/bin/inkscape",
    )

    assert inkscape.find_inkscape() == ("/usr/bin/inkscape")


def test_find_inkscape_uses_windows_installation_under_wsl(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Standard Windows installations are considered under WSL.
    """

    monkeypatch.delenv(
        inkscape.INKSCAPE_ENVIRONMENT_VARIABLE,
        raising=False,
    )

    monkeypatch.setattr(
        inkscape.shutil,
        "which",
        lambda name: None,
    )

    original_is_file = Path.is_file

    def is_file(
        path: Path,
    ) -> bool:
        if str(path) == ("/mnt/c/Program Files/Inkscape/bin/inkscape.exe"):
            return True

        return original_is_file(path)

    monkeypatch.setattr(
        Path,
        "is_file",
        is_file,
    )

    assert inkscape.find_inkscape() == ("/mnt/c/Program Files/Inkscape/bin/inkscape.exe")


def test_find_inkscape_rejects_missing_executable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Discovery fails when no Inkscape executable is available.
    """

    monkeypatch.delenv(
        inkscape.INKSCAPE_ENVIRONMENT_VARIABLE,
        raising=False,
    )

    monkeypatch.setattr(
        inkscape.shutil,
        "which",
        lambda name: None,
    )

    monkeypatch.setattr(
        Path,
        "is_file",
        lambda path: False,
    )

    with pytest.raises(
        inkscape.InkscapeError,
        match="Could not find Inkscape",
    ):
        inkscape.find_inkscape()


# =========================================================
# Invocation
# =========================================================


def test_run_constructs_command(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Inkscape invocation includes the document, arguments, and actions.
    """

    svg = tmp_path / "source.svg"
    svg.write_text(
        "<svg/>",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        inkscape,
        "find_inkscape",
        lambda: "/usr/bin/inkscape",
    )

    observed: list[str] = []

    def run(
        command,
        **kwargs,
    ):
        observed.extend(command)

        return CompletedProcess(
            command,
            0,
            stdout="success\n",
            stderr="",
        )

    monkeypatch.setattr(
        inkscape.subprocess,
        "run",
        run,
    )

    result = inkscape.run(
        svg,
        args=("--query-all",),
        actions=(
            "select-clear",
            "select-by-id:path1",
        ),
    )

    assert observed == [
        "/usr/bin/inkscape",
        str(svg),
        "--query-all",
        ("--actions=select-clear;select-by-id:path1"),
    ]

    assert result == "success\n"


def test_run_omits_actions_when_empty(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    No --actions argument is emitted when no actions are supplied.
    """

    svg = tmp_path / "source.svg"
    svg.touch()

    monkeypatch.setattr(
        inkscape,
        "find_inkscape",
        lambda: "/usr/bin/inkscape",
    )

    observed: list[str] = []

    def run(
        command,
        **kwargs,
    ):
        observed.extend(command)

        return CompletedProcess(
            command,
            0,
            stdout="",
            stderr="",
        )

    monkeypatch.setattr(
        inkscape.subprocess,
        "run",
        run,
    )

    inkscape.run(svg)

    assert observed == [
        "/usr/bin/inkscape",
        str(svg),
    ]


def test_run_rejects_missing_svg(
    tmp_path: Path,
) -> None:
    """
    Inkscape is not invoked for a missing source document.
    """

    svg = tmp_path / "missing.svg"

    with pytest.raises(
        inkscape.InkscapeError,
        match="SVG file does not exist",
    ):
        inkscape.run(svg)


def test_run_wraps_execution_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Operating-system failures while starting Inkscape are wrapped.
    """

    svg = tmp_path / "source.svg"
    svg.touch()

    monkeypatch.setattr(
        inkscape,
        "find_inkscape",
        lambda: "/usr/bin/inkscape",
    )

    def run(
        command,
        **kwargs,
    ):
        raise OSError("cannot execute")

    monkeypatch.setattr(
        inkscape.subprocess,
        "run",
        run,
    )

    with pytest.raises(
        inkscape.InkscapeError,
        match="Could not execute Inkscape",
    ):
        inkscape.run(svg)


def test_run_rejects_unsuccessful_process(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    A nonzero Inkscape exit status becomes an InkscapeError.
    """

    svg = tmp_path / "source.svg"
    svg.touch()

    monkeypatch.setattr(
        inkscape,
        "find_inkscape",
        lambda: "/usr/bin/inkscape",
    )

    def run(
        command,
        **kwargs,
    ):
        return CompletedProcess(
            command,
            1,
            stdout="stdout text",
            stderr="stderr text",
        )

    monkeypatch.setattr(
        inkscape.subprocess,
        "run",
        run,
    )

    with pytest.raises(
        inkscape.InkscapeError,
        match="Inkscape failed",
    ) as exc_info:
        inkscape.run(svg)

    message = str(exc_info.value)

    assert "stdout text" in message
    assert "stderr text" in message


# =========================================================
# Queries
# =========================================================


def test_query_all_parses_object_bounds(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Inkscape query results are parsed and converted to millimeters.
    """

    svg = tmp_path / "source.svg"
    svg.touch()

    monkeypatch.setattr(
        inkscape,
        "run",
        lambda svg, **kwargs: ("path1,96,192,48,24\npath2,0,0,192,96\n"),
    )

    bounds = inkscape.query_all(svg)

    assert bounds["path1"] == pytest.approx(
        {
            "x": 25.4,
            "y": 50.8,
            "width": 12.7,
            "height": 6.35,
        }
    )

    assert bounds["path2"] == pytest.approx(
        {
            "x": 0.0,
            "y": 0.0,
            "width": 50.8,
            "height": 25.4,
        }
    )


def test_query_all_ignores_unrecognized_lines(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Query output that is not an object bounding box is ignored.
    """

    svg = tmp_path / "source.svg"
    svg.touch()

    monkeypatch.setattr(
        inkscape,
        "run",
        lambda svg, **kwargs: ("diagnostic text\npath1,0,0,96,96\n"),
    )

    bounds = inkscape.query_all(svg)

    assert tuple(bounds) == ("path1",)


def test_query_all_rejects_invalid_numeric_bounds(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Invalid numeric query values are reported as Inkscape errors.
    """

    svg = tmp_path / "source.svg"
    svg.touch()

    monkeypatch.setattr(
        inkscape,
        "run",
        lambda svg, **kwargs: ("path1,not-a-number,0,96,96\n"),
    )

    with pytest.raises(
        inkscape.InkscapeError,
        match="invalid object bounding box",
    ):
        inkscape.query_all(svg)


# =========================================================
# Selection actions
# =========================================================


def test_select_by_id() -> None:
    """
    Object IDs are combined into one selection action.
    """

    assert inkscape.select_by_id(
        (
            "path1",
            "path2",
            "path3",
        )
    ) == ("select-by-id:path1,path2,path3")


def test_select_by_id_requires_object() -> None:
    """
    At least one object is required for selection.
    """

    with pytest.raises(
        inkscape.InkscapeError,
        match="At least one object ID",
    ):
        inkscape.select_by_id(())


# =========================================================
# Path actions
# =========================================================


def test_union_actions() -> None:
    """
    Union actions select all operands before performing the union.
    """

    assert inkscape.union_actions(
        (
            "path1",
            "path2",
        )
    ) == [
        "select-clear",
        "select-by-id:path1,path2",
        "path-union",
    ]


def test_union_actions_requires_two_objects() -> None:
    """
    Union requires at least two objects.
    """

    with pytest.raises(
        inkscape.InkscapeError,
        match="at least two objects",
    ):
        inkscape.union_actions(("path1",))


def test_difference_actions() -> None:
    """
    Difference actions select the target and cutter in order.
    """

    assert inkscape.difference_actions(
        "target",
        "cutter",
    ) == [
        "select-clear",
        "select-by-id:target,cutter",
        "path-difference",
    ]


# =========================================================
# Export actions
# =========================================================


def test_export_object_actions(
    tmp_path: Path,
) -> None:
    """
    Object export retains the document page as the registration area.
    """

    output = tmp_path / "layer.svg"

    actions = inkscape.export_object_actions(
        "path1",
        output,
    )

    assert actions == [
        "select-clear",
        "select-by-id:path1",
        "export-type:svg",
        f"export-filename:{output.resolve()}",
        "export-id:path1",
        "export-id-only",
        "export-area-page",
        "export-do",
    ]
