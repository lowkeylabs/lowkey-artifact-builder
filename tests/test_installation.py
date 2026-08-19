"""Tests for package installation and metadata."""

from importlib.metadata import version

import lowkey_artifact_builder


def test_package_is_importable() -> None:
    """The lowkey_artifact_builder package can be imported."""

    assert lowkey_artifact_builder is not None


def test_distribution_has_version() -> None:
    """The installed distribution exposes version metadata."""

    installed_version = version("lowkey-artifact-builder")

    assert installed_version
