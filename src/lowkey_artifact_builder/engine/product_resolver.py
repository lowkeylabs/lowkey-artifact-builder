"""
Logical product filesystem resolution.

This module centralizes the mapping from logical artifact, model, and
realization identities to canonical filesystem locations.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from lowkey_artifact_builder.model.specs import StageSpec


@dataclass(
    frozen=True,
    slots=True,
)
class ProductResolver:
    """
    Resolve logical product identities to canonical filesystem locations.
    """

    project_root: Path

    def artifact_dir(
        self,
        artifact: str,
    ) -> Path:
        """
        Return the canonical directory for an artifact.
        """

        return self.project_root / "artifacts" / artifact

    def model_dir(
        self,
        *,
        artifact: str,
        model: str,
    ) -> Path:
        """
        Return the canonical directory for a model realization namespace.
        """

        return self.artifact_dir(artifact) / model

    def realization_dir(
        self,
        *,
        artifact: str,
        model: str,
        realization: str,
    ) -> Path:
        """
        Return the canonical directory for a model realization.
        """

        return (
            self.model_dir(
                artifact=artifact,
                model=model,
            )
            / realization
        )

    def stage_dir(
        self,
        *,
        artifact: str,
        model: str,
        realization: str,
        stage: StageSpec,
    ) -> Path:
        """
        Return the canonical directory for a stage.
        """

        return (
            self.realization_dir(
                artifact=artifact,
                model=model,
                realization=realization,
            )
            / f"{stage.id}-{stage.name}"
        )


__all__ = [
    "ProductResolver",
]
