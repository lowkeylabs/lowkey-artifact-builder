"""
Tests for the OpenSCAD tool interface.
"""

from pathlib import Path
from subprocess import CompletedProcess

import pytest

from lowkey_artifact_builder.tools import openscad

# =========================================================
# Executable discovery
# =========================================================


def test_find_openscad_uses_configured_executable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    The configured executable takes precedence over PATH.
    """

    executable = tmp_path / "openscad"
    executable.touch()

    monkeypatch.setenv(
        openscad.OPENSCAD_ENVIRONMENT_VARIABLE,
        str(executable),
    )

    monkeypatch.setattr(
        openscad.shutil,
        "which",
        lambda name: "/usr/bin/openscad",
    )

    assert openscad.find_openscad() == str(executable)


def test_find_openscad_rejects_missing_configured_executable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    An explicitly configured missing executable is an error.
    """

    executable = tmp_path / "missing-openscad"

    monkeypatch.setenv(
        openscad.OPENSCAD_ENVIRONMENT_VARIABLE,
        str(executable),
    )

    with pytest.raises(
        openscad.OpenSCADError,
        match="does not exist",
    ):
        openscad.find_openscad()


def test_find_openscad_uses_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    OpenSCAD is discovered from PATH when not configured.
    """

    monkeypatch.delenv(
        openscad.OPENSCAD_ENVIRONMENT_VARIABLE,
        raising=False,
    )

    monkeypatch.setattr(
        openscad.shutil,
        "which",
        lambda name: "/usr/bin/openscad",
    )

    assert openscad.find_openscad() == ("/usr/bin/openscad")


def test_find_openscad_uses_windows_installation_under_wsl(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Standard Windows installations are considered under WSL.
    """

    monkeypatch.delenv(
        openscad.OPENSCAD_ENVIRONMENT_VARIABLE,
        raising=False,
    )

    monkeypatch.setattr(
        openscad.shutil,
        "which",
        lambda name: None,
    )

    original_is_file = Path.is_file

    def is_file(
        path: Path,
    ) -> bool:
        if str(path) == ("/mnt/c/Program Files/OpenSCAD/openscad.exe"):
            return True

        return original_is_file(path)

    monkeypatch.setattr(
        Path,
        "is_file",
        is_file,
    )

    assert openscad.find_openscad() == ("/mnt/c/Program Files/OpenSCAD/openscad.exe")


def test_find_openscad_rejects_missing_executable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Discovery fails when no OpenSCAD executable is available.
    """

    monkeypatch.delenv(
        openscad.OPENSCAD_ENVIRONMENT_VARIABLE,
        raising=False,
    )

    monkeypatch.setattr(
        openscad.shutil,
        "which",
        lambda name: None,
    )

    monkeypatch.setattr(
        Path,
        "is_file",
        lambda path: False,
    )

    with pytest.raises(
        openscad.OpenSCADError,
        match="Could not find OpenSCAD",
    ):
        openscad.find_openscad()


# =========================================================
# Definitions
# =========================================================


def test_format_define_integer() -> None:
    """
    Integer values are emitted directly.
    """

    assert (
        openscad.format_define(
            "count",
            5,
        )
        == "count=5"
    )


def test_format_define_float() -> None:
    """
    Floating-point values are emitted directly.
    """

    assert (
        openscad.format_define(
            "height",
            1.5,
        )
        == "height=1.5"
    )


def test_format_define_true() -> None:
    """
    True is encoded using OpenSCAD boolean syntax.
    """

    assert (
        openscad.format_define(
            "enabled",
            True,
        )
        == "enabled=true"
    )


def test_format_define_false() -> None:
    """
    False is encoded using OpenSCAD boolean syntax.
    """

    assert (
        openscad.format_define(
            "enabled",
            False,
        )
        == "enabled=false"
    )


def test_format_define_string() -> None:
    """
    String values are quoted.
    """

    assert (
        openscad.format_define(
            "label",
            "hello",
        )
        == 'label="hello"'
    )


def test_format_define_escapes_string() -> None:
    """
    Backslashes and quotes are escaped in string values.
    """

    assert openscad.format_define(
        "path",
        'C:\\Models\\"example".svg',
    ) == ('path="C:\\\\Models\\\\\\"example\\".svg"')


def test_format_define_rejects_unsupported_type() -> None:
    """
    Unsupported Python values cannot become OpenSCAD definitions.
    """

    with pytest.raises(
        openscad.OpenSCADError,
        match="Unsupported OpenSCAD parameter type",
    ):
        openscad.format_define(
            "values",
            [1, 2, 3],  # type: ignore[arg-type]
        )


# =========================================================
# Invocation
# =========================================================


def test_run_constructs_command(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    OpenSCAD invocation contains output, definitions, arguments,
    and source document.
    """

    scad = tmp_path / "model.scad"
    scad.write_text(
        "cube(1);",
        encoding="utf-8",
    )

    output = tmp_path / "model.stl"

    monkeypatch.setattr(
        openscad,
        "find_openscad",
        lambda: "/usr/bin/openscad",
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
            stdout="stdout text\n",
            stderr="stderr text\n",
        )

    monkeypatch.setattr(
        openscad.subprocess,
        "run",
        run,
    )

    result = openscad.run(
        scad,
        output=output,
        defines={
            "height": 1.5,
            "enabled": True,
        },
        args=("--render",),
    )

    assert observed == [
        "/usr/bin/openscad",
        "-o",
        str(output),
        "-D",
        "height=1.5",
        "-D",
        "enabled=true",
        "--render",
        str(scad),
    ]

    assert result == ("stdout text\nstderr text")


def test_run_creates_output_parent_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    The output parent directory is created before OpenSCAD runs.
    """

    scad = tmp_path / "model.scad"
    scad.touch()

    output = tmp_path / "nested" / "directory" / "model.stl"

    monkeypatch.setattr(
        openscad,
        "find_openscad",
        lambda: "/usr/bin/openscad",
    )

    def run(
        command,
        **kwargs,
    ):
        assert output.parent.is_dir()

        return CompletedProcess(
            command,
            0,
            stdout="",
            stderr="",
        )

    monkeypatch.setattr(
        openscad.subprocess,
        "run",
        run,
    )

    openscad.run(
        scad,
        output=output,
    )

    assert output.parent.is_dir()


def test_run_rejects_missing_scad(
    tmp_path: Path,
) -> None:
    """
    OpenSCAD is not invoked for a missing source document.
    """

    scad = tmp_path / "missing.scad"

    with pytest.raises(
        openscad.OpenSCADError,
        match="OpenSCAD file does not exist",
    ):
        openscad.run(scad)


def test_run_wraps_execution_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Operating-system failures while starting OpenSCAD are wrapped.
    """

    scad = tmp_path / "model.scad"
    scad.touch()

    monkeypatch.setattr(
        openscad,
        "find_openscad",
        lambda: "/usr/bin/openscad",
    )

    def run(
        command,
        **kwargs,
    ):
        raise OSError("cannot execute")

    monkeypatch.setattr(
        openscad.subprocess,
        "run",
        run,
    )

    with pytest.raises(
        openscad.OpenSCADError,
        match="Could not execute OpenSCAD",
    ):
        openscad.run(scad)


def test_run_rejects_unsuccessful_process(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    A nonzero OpenSCAD exit status becomes an OpenSCADError.
    """

    scad = tmp_path / "model.scad"
    scad.touch()

    monkeypatch.setattr(
        openscad,
        "find_openscad",
        lambda: "/usr/bin/openscad",
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
        openscad.subprocess,
        "run",
        run,
    )

    with pytest.raises(
        openscad.OpenSCADError,
        match="OpenSCAD failed",
    ) as exc_info:
        openscad.run(scad)

    message = str(exc_info.value)

    assert "stdout text" in message
    assert "stderr text" in message


# =========================================================
# STL rendering
# =========================================================


def test_render_stl(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    STL rendering invokes OpenSCAD and returns the generated path.
    """

    scad = tmp_path / "model.scad"
    scad.touch()

    output = tmp_path / "model.stl"

    observed_defines = None

    def run(
        source,
        *,
        output=None,
        defines=None,
        args=(),
    ):
        nonlocal observed_defines

        assert source == scad
        assert output == tmp_path / "model.stl"

        observed_defines = defines

        assert output is not None

        output.touch()

        return ""

    monkeypatch.setattr(
        openscad,
        "run",
        run,
    )

    result = openscad.render_stl(
        scad,
        output,
        defines={
            "height": 2.0,
        },
    )

    assert result == output

    assert observed_defines == {
        "height": 2.0,
    }


def test_render_stl_requires_stl_extension(
    tmp_path: Path,
) -> None:
    """
    STL rendering rejects a non-STL output filename.
    """

    with pytest.raises(
        openscad.OpenSCADError,
        match="must end in .stl",
    ):
        openscad.render_stl(
            tmp_path / "model.scad",
            tmp_path / "model.obj",
        )


def test_render_stl_rejects_missing_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Successful invocation must actually create the requested STL.
    """

    scad = tmp_path / "model.scad"
    scad.touch()

    output = tmp_path / "model.stl"

    monkeypatch.setattr(
        openscad,
        "run",
        lambda *args, **kwargs: "",
    )

    with pytest.raises(
        openscad.OpenSCADError,
        match="without creating the expected STL",
    ):
        openscad.render_stl(
            scad,
            output,
        )


# =========================================================
# Source rendering
# =========================================================


def test_render_stl_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Source text is written to a temporary SCAD file and rendered.
    """

    output = tmp_path / "model.stl"

    observed_source: str | None = None
    observed_scad: Path | None = None

    def render_stl(
        scad: Path,
        destination: Path,
        *,
        defines=None,
    ) -> Path:
        nonlocal observed_source
        nonlocal observed_scad

        observed_scad = scad

        assert scad.parent == tmp_path.resolve()
        assert scad.suffix == ".scad"
        assert scad.name.startswith(".lowkey-artifact-")

        observed_source = scad.read_text(
            encoding="utf-8",
        )

        destination.touch()

        return destination

    monkeypatch.setattr(
        openscad,
        "render_stl",
        render_stl,
    )

    result = openscad.render_stl_source(
        "cube(10);",
        output,
    )

    assert result == output
    assert observed_source == "cube(10);"

    assert observed_scad is not None
    assert not observed_scad.exists()


def test_render_stl_source_cleans_temporary_file_after_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Temporary source files are removed when rendering fails.
    """

    output = tmp_path / "model.stl"

    observed_scad: Path | None = None

    def render_stl(
        scad: Path,
        destination: Path,
        *,
        defines=None,
    ) -> Path:
        nonlocal observed_scad

        observed_scad = scad

        raise openscad.OpenSCADError("render failed")

    monkeypatch.setattr(
        openscad,
        "render_stl",
        render_stl,
    )

    with pytest.raises(
        openscad.OpenSCADError,
        match="render failed",
    ):
        openscad.render_stl_source(
            "cube(10);",
            output,
        )

    assert observed_scad is not None
    assert not observed_scad.exists()


def test_render_stl_source_requires_stl_extension(
    tmp_path: Path,
) -> None:
    """
    Source rendering rejects a non-STL output filename.
    """

    with pytest.raises(
        openscad.OpenSCADError,
        match="must end in .stl",
    ):
        openscad.render_stl_source(
            "cube(10);",
            tmp_path / "model.obj",
        )


def test_render_stl_source_rejects_non_string(
    tmp_path: Path,
) -> None:
    """
    OpenSCAD source must be text.
    """

    with pytest.raises(
        openscad.OpenSCADError,
        match="source must be a string",
    ):
        openscad.render_stl_source(
            123,  # type: ignore[arg-type]
            tmp_path / "model.stl",
        )


def test_render_stl_source_rejects_empty_source(
    tmp_path: Path,
) -> None:
    """
    Empty OpenSCAD source cannot be rendered.
    """

    with pytest.raises(
        openscad.OpenSCADError,
        match="source cannot be empty",
    ):
        openscad.render_stl_source(
            "   \n\t",
            tmp_path / "model.stl",
        )
