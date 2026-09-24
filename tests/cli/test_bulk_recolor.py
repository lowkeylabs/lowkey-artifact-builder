"""
Tests for operator recoloring through the colors command.
"""
# File: tests/cli/test_recolor.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

import pytest

import lowkey_artifact_builder.cli.cmd_color as cmd_color
from lowkey_artifact_builder.colors import (
    PaletteColor,
)
from lowkey_artifact_builder.engine import BuildPlan
from lowkey_artifact_builder.model.models.artwork.color_analysis import (
    ArtworkColorAnalysis,
)


def test_bulk_printer_recolor_prepares_all_artifacts_before_any_mutation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    Bulk printer recoloring validates the complete Artifact scope before
    mutating configuration or final 3MF metadata.
    """

    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr(
        cmd_color,
        "_resolve_color_artifact_ids",
        lambda *, project_root: (
            "cat",
            "dog",
        ),
    )

    mutations: list[str] = []

    def fake_prepare_artifact_recolor(
        artifact_id: str,
        *,
        project_root: Path,
    ) -> tuple[BuildPlan, ...]:
        if artifact_id == "dog":
            raise FileNotFoundError("dog final 3MF is missing")

        return ()

    monkeypatch.setattr(
        cmd_color,
        "_prepare_artifact_recolor",
        fake_prepare_artifact_recolor,
    )

    monkeypatch.setattr(
        cmd_color,
        "_persist_printer_colors",
        lambda *args, **kwargs: mutations.append("config"),
    )

    monkeypatch.setattr(
        cmd_color,
        "update_component_colors",
        lambda *args, **kwargs: mutations.append("3mf"),
    )

    with pytest.raises(
        FileNotFoundError,
        match="dog final 3MF is missing",
    ):
        cmd_color.run_colors(
            None,
            recolor="printer",
        )

    assert mutations == []


def test_bulk_realization_printer_recolor_prepares_all_artifacts_before_any_mutation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    Bulk recoloring of a selected Realization validates that Realization
    independently for every Artifact before any mutation occurs.
    """

    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr(
        cmd_color,
        "_resolve_color_artifact_ids",
        lambda *, project_root: (
            "cat",
            "dog",
        ),
    )

    mutations: list[str] = []
    observed: list[tuple[str, str | None]] = []

    def fake_resolve_recolor_scope(
        artifact_id: str,
        *,
        realization: str | None,
        project_root: Path,
    ) -> BuildPlan:
        observed.append(
            (
                artifact_id,
                realization,
            )
        )

        if artifact_id == "dog":
            raise ValueError("shape_ornament is not applicable to dog")

        return Mock()

    monkeypatch.setattr(
        cmd_color,
        "_resolve_recolor_scope",
        fake_resolve_recolor_scope,
    )

    monkeypatch.setattr(
        cmd_color,
        "_persist_printer_colors",
        lambda *args, **kwargs: mutations.append("config"),
    )

    monkeypatch.setattr(
        cmd_color,
        "update_component_colors",
        lambda *args, **kwargs: mutations.append("3mf"),
    )

    with pytest.raises(
        ValueError,
        match="shape_ornament is not applicable to dog",
    ):
        cmd_color.run_colors(
            None,
            realization="shape_ornament",
            recolor="printer",
        )

    assert observed == [
        (
            "cat",
            "shape_ornament",
        ),
        (
            "dog",
            "shape_ornament",
        ),
    ]

    assert mutations == []


def test_bulk_printer_recolor_computes_all_artifacts_before_any_mutation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    Successful bulk printer recoloring computes every Artifact's prospective
    final-3MF mutations before changing any configuration or final 3MF.
    """

    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr(
        cmd_color,
        "_resolve_color_artifact_ids",
        lambda *, project_root: (
            "cat",
            "dog",
        ),
    )

    cat_final = tmp_path / "cat-artwork-default.3mf"

    cat_product = Mock()
    cat_product.name = "artifact"
    cat_product.path = cat_final

    cat_package_stage = Mock()
    cat_package_stage.name = "package"
    cat_package_stage.products = (cat_product,)

    cat_plan = Mock(spec=BuildPlan)
    cat_plan.realization_name = "artwork_default"
    cat_plan.resolver = Mock()
    cat_plan.resolver.source.return_value = "artifact"
    cat_plan.resolver.system_value.return_value = (
        "black",
        "white",
        "red",
    )
    cat_plan.stages = (cat_package_stage,)

    dog_final = tmp_path / "dog-artwork-default.3mf"

    dog_product = Mock()
    dog_product.name = "artifact"
    dog_product.path = dog_final

    dog_package_stage = Mock()
    dog_package_stage.name = "package"
    dog_package_stage.products = (dog_product,)

    dog_plan = Mock(spec=BuildPlan)
    dog_plan.realization_name = "artwork_default"
    dog_plan.resolver = Mock()
    dog_plan.resolver.source.return_value = "artifact"
    dog_plan.resolver.system_value.return_value = (
        "black",
        "white",
        "blue",
    )
    dog_plan.stages = (dog_package_stage,)

    prepared_plans = {
        "cat": (cat_plan,),
        "dog": (dog_plan,),
    }

    cat_colors: dict[str, PaletteColor] = {
        "artwork-0": Mock(spec=PaletteColor),
    }
    dog_colors: dict[str, PaletteColor] = {
        "artwork-0": Mock(spec=PaletteColor),
    }

    events: list[tuple[object, ...]] = []

    def fake_prepare_artifact_recolor(
        artifact_id: str,
        *,
        project_root: Path,
    ) -> tuple[BuildPlan, ...]:
        events.append(
            (
                "prepare-artifact",
                artifact_id,
            )
        )

        return prepared_plans[artifact_id]

    def fake_prepare_existing_final_recolor(
        plan: BuildPlan,
        *,
        printer_colors: tuple[str, ...],
    ) -> dict[str, PaletteColor]:
        artifact_id = "cat" if plan is cat_plan else "dog"

        events.append(
            (
                "prepare-final",
                artifact_id,
                printer_colors,
            )
        )

        return cat_colors if artifact_id == "cat" else dog_colors

    def fake_persist_printer_colors(
        artifact_id: str,
        *,
        realization: str | None,
        printer_colors: tuple[str, ...],
        project_root: Path,
    ) -> None:
        events.append(
            (
                "persist",
                artifact_id,
                printer_colors,
            )
        )

    monkeypatch.setattr(
        cmd_color,
        "_prepare_artifact_recolor",
        fake_prepare_artifact_recolor,
    )
    monkeypatch.setattr(
        cmd_color,
        "_prepare_existing_final_recolor",
        fake_prepare_existing_final_recolor,
    )
    monkeypatch.setattr(
        cmd_color,
        "_persist_printer_colors",
        fake_persist_printer_colors,
    )

    monkeypatch.setattr(
        cmd_color,
        "_report_retained_printer_color_overrides",
        lambda *args, **kwargs: None,
    )

    monkeypatch.setattr(
        cmd_color,
        "update_component_colors",
        lambda path, **kwargs: events.append(
            (
                "update-final",
                kwargs["artifact_id"],
                path,
                kwargs["colors"],
            )
        ),
    )

    monkeypatch.setattr(
        cmd_color,
        "analyze_artifact_colors",
        lambda artifact_id, *, realization=None: object(),
    )

    result = cmd_color.run_colors(
        None,
        recolor="printer",
    )

    assert isinstance(result, tuple)
    assert len(result) == 2

    first_mutation = next(
        index
        for index, event in enumerate(events)
        if event[0]
        in {
            "persist",
            "update-final",
        }
    )

    assert (
        "prepare-final",
        "cat",
        (
            "black",
            "white",
            "red",
        ),
    ) in events[:first_mutation]

    assert (
        "prepare-final",
        "dog",
        (
            "black",
            "white",
            "blue",
        ),
    ) in events[:first_mutation]

    assert (
        "persist",
        "cat",
        (
            "black",
            "white",
            "red",
        ),
    ) in events

    assert (
        "persist",
        "dog",
        (
            "black",
            "white",
            "blue",
        ),
    ) in events

    assert (
        "update-final",
        "cat",
        cat_final,
        cat_colors,
    ) in events

    assert (
        "update-final",
        "dog",
        dog_final,
        dog_colors,
    ) in events


def test_bulk_realization_printer_recolor_computes_all_artifacts_before_any_mutation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    Successful bulk printer recoloring of one selected Realization computes
    every Artifact's prospective final-3MF mutation before changing any
    Realization configuration or final 3MF.
    """

    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr(
        cmd_color,
        "_resolve_color_artifact_ids",
        lambda *, project_root: (
            "cat",
            "dog",
        ),
    )

    cat_final = tmp_path / "cat-shape-ornament.3mf"

    cat_product = Mock()
    cat_product.name = "artifact"
    cat_product.path = cat_final

    cat_package_stage = Mock()
    cat_package_stage.name = "package"
    cat_package_stage.products = (cat_product,)

    cat_plan = Mock(spec=BuildPlan)
    cat_plan.artifact_id = "cat"
    cat_plan.realization_name = "shape_ornament"
    cat_plan.resolver = Mock()
    cat_plan.resolver.system_value.return_value = (
        "black",
        "white",
        "red",
    )
    cat_plan.stages = (cat_package_stage,)

    dog_final = tmp_path / "dog-shape-ornament.3mf"

    dog_product = Mock()
    dog_product.name = "artifact"
    dog_product.path = dog_final

    dog_package_stage = Mock()
    dog_package_stage.name = "package"
    dog_package_stage.products = (dog_product,)

    dog_plan = Mock(spec=BuildPlan)
    dog_plan.artifact_id = "dog"
    dog_plan.realization_name = "shape_ornament"
    dog_plan.resolver = Mock()
    dog_plan.resolver.system_value.return_value = (
        "black",
        "white",
        "blue",
    )
    dog_plan.stages = (dog_package_stage,)

    cat_colors: dict[str, PaletteColor] = {
        "artwork-0": Mock(spec=PaletteColor),
    }
    dog_colors: dict[str, PaletteColor] = {
        "artwork-0": Mock(spec=PaletteColor),
    }

    events: list[tuple[object, ...]] = []

    def fake_resolve_recolor_scope(
        artifact_id: str,
        *,
        realization: str | None,
        project_root: Path,
    ) -> BuildPlan:
        events.append(
            (
                "resolve",
                artifact_id,
                realization,
            )
        )

        assert realization == "shape_ornament"

        return cat_plan if artifact_id == "cat" else dog_plan

    def fake_prepare_existing_final_recolor(
        plan: BuildPlan,
        *,
        printer_colors: tuple[str, ...],
    ) -> dict[str, PaletteColor]:
        artifact_id = plan.artifact_id

        events.append(
            (
                "prepare-final",
                artifact_id,
                plan.realization_name,
                printer_colors,
            )
        )

        return cat_colors if artifact_id == "cat" else dog_colors

    def fake_persist_printer_colors(
        artifact_id: str,
        *,
        realization: str | None,
        printer_colors: tuple[str, ...],
        project_root: Path,
    ) -> None:
        events.append(
            (
                "persist",
                artifact_id,
                realization,
                printer_colors,
            )
        )

    monkeypatch.setattr(
        cmd_color,
        "_resolve_recolor_scope",
        fake_resolve_recolor_scope,
    )

    monkeypatch.setattr(
        cmd_color,
        "_prepare_existing_final_recolor",
        fake_prepare_existing_final_recolor,
    )

    monkeypatch.setattr(
        cmd_color,
        "_persist_printer_colors",
        fake_persist_printer_colors,
    )

    monkeypatch.setattr(
        cmd_color,
        "update_component_colors",
        lambda path, **kwargs: events.append(
            (
                "update-final",
                kwargs["artifact_id"],
                path,
                kwargs["colors"],
            )
        ),
    )

    cat_analysis = object()
    dog_analysis = object()

    monkeypatch.setattr(
        cmd_color,
        "analyze_artifact_colors",
        lambda artifact_id, *, realization=None: (
            cat_analysis if artifact_id == "cat" else dog_analysis
        ),
    )

    result = cmd_color.run_colors(
        None,
        realization="shape_ornament",
        recolor="printer",
    )

    assert result == (
        cat_analysis,
        dog_analysis,
    )

    first_mutation = next(
        index
        for index, event in enumerate(events)
        if event[0]
        in {
            "persist",
            "update-final",
        }
    )

    assert (
        "prepare-final",
        "cat",
        "shape_ornament",
        (
            "black",
            "white",
            "red",
        ),
    ) in events[:first_mutation]

    assert (
        "prepare-final",
        "dog",
        "shape_ornament",
        (
            "black",
            "white",
            "blue",
        ),
    ) in events[:first_mutation]

    assert (
        "persist",
        "cat",
        "shape_ornament",
        (
            "black",
            "white",
            "red",
        ),
    ) in events

    assert (
        "persist",
        "dog",
        "shape_ornament",
        (
            "black",
            "white",
            "blue",
        ),
    ) in events

    assert (
        "update-final",
        "cat",
        cat_final,
        cat_colors,
    ) in events

    assert (
        "update-final",
        "dog",
        dog_final,
        dog_colors,
    ) in events


def test_bulk_library_recolor_prepares_all_artifacts_before_any_mutation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    Bulk Artifact-scoped Library recoloring validates every selected Artifact
    before changing any configuration or final 3MF.
    """

    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr(
        cmd_color,
        "_resolve_color_artifact_ids",
        lambda *, project_root: (
            "cat",
            "dog",
        ),
    )

    cat_plan = Mock(spec=BuildPlan)
    cat_plan.realization_name = "artwork_default"

    mutations: list[tuple[object, ...]] = []

    def fake_prepare_artifact_recolor(
        artifact_id: str,
        *,
        project_root: Path,
    ) -> tuple[BuildPlan, ...]:
        if artifact_id == "dog":
            raise FileNotFoundError("dog final 3MF is missing")

        return (cat_plan,)

    monkeypatch.setattr(
        cmd_color,
        "_prepare_artifact_recolor",
        fake_prepare_artifact_recolor,
    )

    monkeypatch.setattr(
        cmd_color,
        "_persist_printer_colors",
        lambda *args, **kwargs: mutations.append(
            (
                "persist",
                args,
                kwargs,
            )
        ),
    )

    monkeypatch.setattr(
        cmd_color,
        "update_component_colors",
        lambda *args, **kwargs: mutations.append(
            (
                "update-final",
                args,
                kwargs,
            )
        ),
    )

    with pytest.raises(
        FileNotFoundError,
        match="dog final 3MF is missing",
    ):
        cmd_color.run_colors(
            None,
            recolor="library",
        )

    assert mutations == []


def test_bulk_realization_library_recolor_prepares_all_artifacts_before_any_mutation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    Bulk Library recoloring of one selected Realization validates every
    Artifact + Realization pair before changing configuration or final 3MF.
    """

    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr(
        cmd_color,
        "_resolve_color_artifact_ids",
        lambda *, project_root: (
            "cat",
            "dog",
        ),
    )

    cat_plan = Mock(spec=BuildPlan)
    cat_plan.artifact_id = "cat"
    cat_plan.realization_name = "shape_ornament"

    observed: list[tuple[str, str | None]] = []
    mutations: list[tuple[object, ...]] = []

    def fake_resolve_recolor_scope(
        artifact_id: str,
        *,
        realization: str | None,
        project_root: Path,
    ) -> BuildPlan:
        observed.append(
            (
                artifact_id,
                realization,
            )
        )

        if artifact_id == "dog":
            raise ValueError("shape_ornament is not applicable to dog")

        return cat_plan

    monkeypatch.setattr(
        cmd_color,
        "_resolve_recolor_scope",
        fake_resolve_recolor_scope,
    )

    monkeypatch.setattr(
        cmd_color,
        "_persist_printer_colors",
        lambda *args, **kwargs: mutations.append(
            (
                "persist",
                args,
                kwargs,
            )
        ),
    )

    monkeypatch.setattr(
        cmd_color,
        "update_component_colors",
        lambda *args, **kwargs: mutations.append(
            (
                "update-final",
                args,
                kwargs,
            )
        ),
    )

    with pytest.raises(
        ValueError,
        match="shape_ornament is not applicable to dog",
    ):
        cmd_color.run_colors(
            None,
            realization="shape_ornament",
            recolor="library",
        )

    assert observed == [
        (
            "cat",
            "shape_ornament",
        ),
        (
            "dog",
            "shape_ornament",
        ),
    ]

    assert mutations == []


def test_bulk_library_recolor_computes_all_artifacts_before_any_mutation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    Successful bulk Artifact-scoped Library recoloring independently computes
    each Artifact's Library-selected printer palette and prospective final-3MF
    mutation before changing any configuration or final 3MF.
    """

    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr(
        cmd_color,
        "_resolve_color_artifact_ids",
        lambda *, project_root: (
            "cat",
            "dog",
        ),
    )

    cat_final = tmp_path / "cat-artwork-default.3mf"

    cat_product = Mock()
    cat_product.name = "artifact"
    cat_product.path = cat_final

    cat_package_stage = Mock()
    cat_package_stage.name = "package"
    cat_package_stage.products = (cat_product,)

    cat_plan = Mock(spec=BuildPlan)
    cat_plan.artifact_id = "cat"
    cat_plan.realization_name = "artwork_default"
    cat_plan.stages = (cat_package_stage,)
    cat_plan.resolver = Mock()
    cat_plan.resolver.source.return_value = "artifact"

    dog_final = tmp_path / "dog-artwork-default.3mf"

    dog_product = Mock()
    dog_product.name = "artifact"
    dog_product.path = dog_final

    dog_package_stage = Mock()
    dog_package_stage.name = "package"
    dog_package_stage.products = (dog_product,)

    dog_plan = Mock(spec=BuildPlan)
    dog_plan.artifact_id = "dog"
    dog_plan.realization_name = "artwork_default"
    dog_plan.stages = (dog_package_stage,)
    dog_plan.resolver = Mock()
    dog_plan.resolver.source.return_value = "artifact"

    prepared_plans = {
        "cat": (cat_plan,),
        "dog": (dog_plan,),
    }

    cat_library_colors = (
        "cat-red",
        "cat-white",
    )
    dog_library_colors = (
        "dog-blue",
        "dog-white",
    )

    cat_plan.resolver.return_value = cat_library_colors
    dog_plan.resolver.return_value = dog_library_colors

    cat_colors: dict[str, PaletteColor] = {
        "artwork-0": Mock(spec=PaletteColor),
    }
    dog_colors: dict[str, PaletteColor] = {
        "artwork-0": Mock(spec=PaletteColor),
    }

    events: list[tuple[object, ...]] = []

    def fake_prepare_artifact_recolor(
        artifact_id: str,
        *,
        project_root: Path,
    ) -> tuple[BuildPlan, ...]:
        events.append(
            (
                "prepare-artifact",
                artifact_id,
            )
        )

        return prepared_plans[artifact_id]

    def fake_prepare_existing_final_recolor(
        plan: BuildPlan,
        *,
        printer_colors: tuple[str, ...],
    ) -> dict[str, PaletteColor]:
        artifact_id = plan.artifact_id

        events.append(
            (
                "prepare-final",
                artifact_id,
                printer_colors,
            )
        )

        return cat_colors if artifact_id == "cat" else dog_colors

    def fake_persist_printer_colors(
        artifact_id: str,
        *,
        realization: str | None,
        printer_colors: tuple[str, ...],
        project_root: Path,
    ) -> None:
        events.append(
            (
                "persist",
                artifact_id,
                printer_colors,
            )
        )

    monkeypatch.setattr(
        cmd_color,
        "_prepare_artifact_recolor",
        fake_prepare_artifact_recolor,
    )
    monkeypatch.setattr(
        cmd_color,
        "_prepare_existing_final_recolor",
        fake_prepare_existing_final_recolor,
    )
    monkeypatch.setattr(
        cmd_color,
        "_persist_printer_colors",
        fake_persist_printer_colors,
    )
    monkeypatch.setattr(
        cmd_color,
        "_report_retained_printer_color_overrides",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        cmd_color,
        "update_component_colors",
        lambda path, **kwargs: events.append(
            (
                "update-final",
                kwargs["artifact_id"],
                path,
                kwargs["colors"],
            )
        ),
    )

    cat_analysis = object()
    dog_analysis = object()

    monkeypatch.setattr(
        cmd_color,
        "analyze_artifact_colors",
        lambda artifact_id, *, realization=None: (
            cat_analysis if artifact_id == "cat" else dog_analysis
        ),
    )

    result = cmd_color.run_colors(
        None,
        recolor="library",
    )

    assert result == (
        cat_analysis,
        dog_analysis,
    )

    first_mutation = next(
        index
        for index, event in enumerate(events)
        if event[0]
        in {
            "persist",
            "update-final",
        }
    )

    assert (
        "prepare-final",
        "cat",
        cat_library_colors,
    ) in events[:first_mutation]

    assert (
        "prepare-final",
        "dog",
        dog_library_colors,
    ) in events[:first_mutation]

    assert (
        "persist",
        "cat",
        cat_library_colors,
    ) in events

    assert (
        "persist",
        "dog",
        dog_library_colors,
    ) in events

    assert (
        "update-final",
        "cat",
        cat_final,
        cat_colors,
    ) in events

    assert (
        "update-final",
        "dog",
        dog_final,
        dog_colors,
    ) in events


def test_bulk_realization_library_recolor_computes_all_artifacts_before_any_mutation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    Successful bulk Library recoloring of one selected Realization
    independently computes each Artifact + Realization Library-selected
    printer palette and prospective final-3MF mutation before changing any
    configuration or final 3MF.
    """

    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr(
        cmd_color,
        "_resolve_color_artifact_ids",
        lambda *, project_root: (
            "cat",
            "dog",
        ),
    )

    cat_final = tmp_path / "cat-shape-ornament.3mf"

    cat_product = Mock()
    cat_product.name = "artifact"
    cat_product.path = cat_final

    cat_package_stage = Mock()
    cat_package_stage.name = "package"
    cat_package_stage.products = (cat_product,)

    cat_plan = Mock(spec=BuildPlan)
    cat_plan.artifact_id = "cat"
    cat_plan.realization_name = "shape_ornament"
    cat_plan.stages = (cat_package_stage,)
    cat_plan.resolver = Mock()

    dog_final = tmp_path / "dog-shape-ornament.3mf"

    dog_product = Mock()
    dog_product.name = "artifact"
    dog_product.path = dog_final

    dog_package_stage = Mock()
    dog_package_stage.name = "package"
    dog_package_stage.products = (dog_product,)

    dog_plan = Mock(spec=BuildPlan)
    dog_plan.artifact_id = "dog"
    dog_plan.realization_name = "shape_ornament"
    dog_plan.stages = (dog_package_stage,)
    dog_plan.resolver = Mock()

    cat_library_colors = (
        "cat-red",
        "cat-white",
    )
    dog_library_colors = (
        "dog-blue",
        "dog-white",
    )

    cat_plan.resolver.return_value = cat_library_colors
    dog_plan.resolver.return_value = dog_library_colors

    cat_colors: dict[str, PaletteColor] = {
        "artwork-0": Mock(spec=PaletteColor),
    }
    dog_colors: dict[str, PaletteColor] = {
        "artwork-0": Mock(spec=PaletteColor),
    }

    events: list[tuple[object, ...]] = []

    def fake_resolve_recolor_scope(
        artifact_id: str,
        *,
        realization: str | None,
        project_root: Path,
    ) -> BuildPlan:
        events.append(
            (
                "resolve",
                artifact_id,
                realization,
            )
        )

        assert realization == "shape_ornament"

        return cat_plan if artifact_id == "cat" else dog_plan

    def fake_prepare_existing_final_recolor(
        plan: BuildPlan,
        *,
        printer_colors: tuple[str, ...],
    ) -> dict[str, PaletteColor]:
        artifact_id = plan.artifact_id

        events.append(
            (
                "prepare-final",
                artifact_id,
                plan.realization_name,
                printer_colors,
            )
        )

        return cat_colors if artifact_id == "cat" else dog_colors

    def fake_persist_printer_colors(
        artifact_id: str,
        *,
        realization: str | None,
        printer_colors: tuple[str, ...],
        project_root: Path,
    ) -> None:
        events.append(
            (
                "persist",
                artifact_id,
                realization,
                printer_colors,
            )
        )

    monkeypatch.setattr(
        cmd_color,
        "_resolve_recolor_scope",
        fake_resolve_recolor_scope,
    )
    monkeypatch.setattr(
        cmd_color,
        "_prepare_existing_final_recolor",
        fake_prepare_existing_final_recolor,
    )
    monkeypatch.setattr(
        cmd_color,
        "_persist_printer_colors",
        fake_persist_printer_colors,
    )
    monkeypatch.setattr(
        cmd_color,
        "update_component_colors",
        lambda path, **kwargs: events.append(
            (
                "update-final",
                kwargs["artifact_id"],
                path,
                kwargs["colors"],
            )
        ),
    )

    cat_analysis = object()
    dog_analysis = object()

    monkeypatch.setattr(
        cmd_color,
        "analyze_artifact_colors",
        lambda artifact_id, *, realization=None: (
            cat_analysis if artifact_id == "cat" else dog_analysis
        ),
    )

    result = cmd_color.run_colors(
        None,
        realization="shape_ornament",
        recolor="library",
    )

    assert result == (
        cat_analysis,
        dog_analysis,
    )

    first_mutation = next(
        index
        for index, event in enumerate(events)
        if event[0]
        in {
            "persist",
            "update-final",
        }
    )

    assert (
        "prepare-final",
        "cat",
        "shape_ornament",
        cat_library_colors,
    ) in events[:first_mutation]

    assert (
        "prepare-final",
        "dog",
        "shape_ornament",
        dog_library_colors,
    ) in events[:first_mutation]

    assert (
        "persist",
        "cat",
        "shape_ornament",
        cat_library_colors,
    ) in events

    assert (
        "persist",
        "dog",
        "shape_ornament",
        dog_library_colors,
    ) in events

    assert (
        "update-final",
        "cat",
        cat_final,
        cat_colors,
    ) in events

    assert (
        "update-final",
        "dog",
        dog_final,
        dog_colors,
    ) in events


def test_bulk_reset_prepares_all_artifacts_before_any_mutation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    Bulk Artifact-scoped reset validates every selected Artifact before
    removing any configuration or changing any final 3MF.
    """

    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr(
        cmd_color,
        "_resolve_color_artifact_ids",
        lambda *, project_root: (
            "cat",
            "dog",
        ),
    )

    cat_plan = Mock(spec=BuildPlan)
    cat_plan.realization_name = "artwork_default"

    mutations: list[tuple[object, ...]] = []

    def fake_prepare_artifact_recolor(
        artifact_id: str,
        *,
        project_root: Path,
    ) -> tuple[BuildPlan, ...]:
        if artifact_id == "dog":
            raise FileNotFoundError("dog final 3MF is missing")

        return (cat_plan,)

    monkeypatch.setattr(
        cmd_color,
        "_prepare_artifact_recolor",
        fake_prepare_artifact_recolor,
    )
    monkeypatch.setattr(
        cmd_color,
        "_reset_printer_colors",
        lambda *args, **kwargs: mutations.append(
            (
                "reset",
                args,
                kwargs,
            )
        ),
    )
    monkeypatch.setattr(
        cmd_color,
        "update_component_colors",
        lambda *args, **kwargs: mutations.append(
            (
                "update-final",
                args,
                kwargs,
            )
        ),
    )

    with pytest.raises(
        FileNotFoundError,
        match="dog final 3MF is missing",
    ):
        cmd_color.run_colors(
            None,
            recolor="reset",
        )

    assert mutations == []


def test_bulk_realization_reset_prepares_all_artifacts_before_any_mutation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    Bulk reset of one selected Realization validates every Artifact +
    Realization pair before removing configuration or changing any final 3MF.
    """

    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr(
        cmd_color,
        "_resolve_color_artifact_ids",
        lambda *, project_root: (
            "cat",
            "dog",
        ),
    )

    cat_plan = Mock(spec=BuildPlan)
    cat_plan.artifact_id = "cat"
    cat_plan.realization_name = "shape_ornament"

    observed: list[tuple[str, str | None]] = []
    mutations: list[tuple[object, ...]] = []

    def fake_resolve_recolor_scope(
        artifact_id: str,
        *,
        realization: str | None,
        project_root: Path,
    ) -> BuildPlan:
        observed.append(
            (
                artifact_id,
                realization,
            )
        )

        if artifact_id == "dog":
            raise ValueError("shape_ornament is not applicable to dog")

        return cat_plan

    monkeypatch.setattr(
        cmd_color,
        "_resolve_recolor_scope",
        fake_resolve_recolor_scope,
    )
    monkeypatch.setattr(
        cmd_color,
        "_reset_printer_colors",
        lambda *args, **kwargs: mutations.append(
            (
                "reset",
                args,
                kwargs,
            )
        ),
    )
    monkeypatch.setattr(
        cmd_color,
        "update_component_colors",
        lambda *args, **kwargs: mutations.append(
            (
                "update-final",
                args,
                kwargs,
            )
        ),
    )

    with pytest.raises(
        ValueError,
        match="shape_ornament is not applicable to dog",
    ):
        cmd_color.run_colors(
            None,
            realization="shape_ornament",
            recolor="reset",
        )

    assert observed == [
        (
            "cat",
            "shape_ornament",
        ),
        (
            "dog",
            "shape_ornament",
        ),
    ]

    assert mutations == []


def test_bulk_reset_updates_all_artifacts_only_after_complete_preparation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    Successful bulk Artifact-scoped reset validates every selected Artifact
    before removing any Artifact-level printer_colors override.

    After the complete scope has been validated, each Artifact is reset and
    its previously validated existing finals are recolored using normal
    post-reset configuration resolution.
    """

    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr(
        cmd_color,
        "_resolve_color_artifact_ids",
        lambda *, project_root: (
            "cat",
            "dog",
        ),
    )

    cat_plan = Mock(spec=BuildPlan)
    cat_plan.artifact_id = "cat"
    cat_plan.realization_name = "artwork_default"

    dog_plan = Mock(spec=BuildPlan)
    dog_plan.artifact_id = "dog"
    dog_plan.realization_name = "artwork_default"

    prepared_plans = {
        "cat": (cat_plan,),
        "dog": (dog_plan,),
    }

    events: list[tuple[object, ...]] = []

    def fake_prepare_artifact_recolor(
        artifact_id: str,
        *,
        project_root: Path,
    ) -> tuple[BuildPlan, ...]:
        events.append(
            (
                "prepare-artifact",
                artifact_id,
            )
        )

        return prepared_plans[artifact_id]

    def fake_reset_printer_colors(
        artifact_id: str,
        *,
        realization: str | None,
        project_root: Path,
    ) -> None:
        events.append(
            (
                "reset",
                artifact_id,
                realization,
            )
        )

    def fake_recolor_existing_final(
        artifact_id: str,
        *,
        realization: str,
        project_root: Path,
    ) -> None:
        events.append(
            (
                "recolor-final",
                artifact_id,
                realization,
            )
        )

    monkeypatch.setattr(
        cmd_color,
        "_prepare_artifact_recolor",
        fake_prepare_artifact_recolor,
    )

    monkeypatch.setattr(
        cmd_color,
        "_reset_printer_colors",
        fake_reset_printer_colors,
    )

    monkeypatch.setattr(
        cmd_color,
        "_recolor_existing_final",
        fake_recolor_existing_final,
    )

    monkeypatch.setattr(
        cmd_color,
        "analyze_artifact_colors",
        lambda artifact_id, *, realization=None: Mock(
            spec=ArtworkColorAnalysis,
        ),
    )

    cmd_color.run_colors(
        None,
        recolor="reset",
    )

    assert events == [
        (
            "prepare-artifact",
            "cat",
        ),
        (
            "prepare-artifact",
            "dog",
        ),
        (
            "reset",
            "cat",
            None,
        ),
        (
            "recolor-final",
            "cat",
            "artwork_default",
        ),
        (
            "reset",
            "dog",
            None,
        ),
        (
            "recolor-final",
            "dog",
            "artwork_default",
        ),
    ]


def test_bulk_reset_all_realizations_prepares_all_artifacts_before_any_mutation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    Bulk reset-all-realizations validates every selected Artifact before
    removing any Realization configuration or changing any final 3MF.
    """

    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr(
        cmd_color,
        "_resolve_color_artifact_ids",
        lambda *, project_root: (
            "cat",
            "dog",
        ),
    )

    cat_plan = Mock(spec=BuildPlan)
    cat_plan.realization_name = "shape_ornament"

    mutations: list[tuple[object, ...]] = []

    def fake_prepare_artifact_recolor(
        artifact_id: str,
        *,
        project_root: Path,
    ) -> tuple[BuildPlan, ...]:
        if artifact_id == "dog":
            raise FileNotFoundError("dog final 3MF is missing")

        return (cat_plan,)

    monkeypatch.setattr(
        cmd_color,
        "_prepare_artifact_recolor",
        fake_prepare_artifact_recolor,
    )

    monkeypatch.setattr(
        cmd_color,
        "_reset_all_realization_printer_colors",
        lambda *args, **kwargs: mutations.append(
            (
                "reset-all-realizations",
                args,
                kwargs,
            )
        ),
    )

    monkeypatch.setattr(
        cmd_color,
        "_recolor_existing_final",
        lambda *args, **kwargs: mutations.append(
            (
                "recolor-final",
                args,
                kwargs,
            )
        ),
    )

    with pytest.raises(
        FileNotFoundError,
        match="dog final 3MF is missing",
    ):
        cmd_color.run_colors(
            None,
            recolor="reset-all-realizations",
        )

    assert mutations == []


def test_bulk_reset_all_realizations_updates_only_after_complete_preparation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    Successful bulk reset-all-realizations validates every selected Artifact
    before removing Realization-specific printer_colors overrides.

    After complete preparation, each Artifact has all Realization overrides
    removed and its previously validated existing finals are recolored through
    normal post-reset configuration resolution.
    """

    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr(
        cmd_color,
        "_resolve_color_artifact_ids",
        lambda *, project_root: (
            "cat",
            "dog",
        ),
    )

    cat_plan = Mock(spec=BuildPlan)
    cat_plan.artifact_id = "cat"
    cat_plan.realization_name = "shape_ornament"

    dog_plan = Mock(spec=BuildPlan)
    dog_plan.artifact_id = "dog"
    dog_plan.realization_name = "artwork_default"

    prepared_plans = {
        "cat": (cat_plan,),
        "dog": (dog_plan,),
    }

    events: list[tuple[object, ...]] = []

    def fake_prepare_artifact_recolor(
        artifact_id: str,
        *,
        project_root: Path,
    ) -> tuple[BuildPlan, ...]:
        events.append(
            (
                "prepare-artifact",
                artifact_id,
            )
        )

        return prepared_plans[artifact_id]

    def fake_reset_all_realization_printer_colors(
        artifact_id: str,
        *,
        project_root: Path,
    ) -> None:
        events.append(
            (
                "reset-all-realizations",
                artifact_id,
            )
        )

    def fake_recolor_existing_final(
        artifact_id: str,
        *,
        realization: str,
        project_root: Path,
    ) -> None:
        events.append(
            (
                "recolor-final",
                artifact_id,
                realization,
            )
        )

    monkeypatch.setattr(
        cmd_color,
        "_prepare_artifact_recolor",
        fake_prepare_artifact_recolor,
    )

    monkeypatch.setattr(
        cmd_color,
        "_reset_all_realization_printer_colors",
        fake_reset_all_realization_printer_colors,
    )

    monkeypatch.setattr(
        cmd_color,
        "_recolor_existing_final",
        fake_recolor_existing_final,
    )

    monkeypatch.setattr(
        cmd_color,
        "analyze_artifact_colors",
        lambda artifact_id, *, realization=None: Mock(
            spec=ArtworkColorAnalysis,
        ),
    )

    cmd_color.run_colors(
        None,
        recolor="reset-all-realizations",
    )

    assert events == [
        (
            "prepare-artifact",
            "cat",
        ),
        (
            "prepare-artifact",
            "dog",
        ),
        (
            "reset-all-realizations",
            "cat",
        ),
        (
            "recolor-final",
            "cat",
            "shape_ornament",
        ),
        (
            "reset-all-realizations",
            "dog",
        ),
        (
            "recolor-final",
            "dog",
            "artwork_default",
        ),
    ]
