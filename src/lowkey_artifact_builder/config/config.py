"""
Artifact configuration resolution and persistence.

Configuration is resolved through increasingly specific scopes:

    config/parameters.toml
        System-wide parameter defaults and reference data.

    model/models/<model>/parameters.toml
        Model-specific parameter defaults.

    model-defined variant
        Reusable model-scoped parameter presets.

    workspace.toml
        Optional project-level parameter overrides.

    artifact realization
        One configured invocation of a model, selecting a model,
        variant, and optional parameter overrides.

Effective configured parameter precedence is:

    realization
        >
    artifact
        >
    workspace
        >
    variant
        >
    model
        >
    system

Legacy artifact configuration without explicit realizations is treated
as a single implicit realization named "default". Its artifact-level
configuration occupies the realization scope, preserving existing
configuration behavior.

Models may additionally define derived values in derived.py.

Derived values are evaluated lazily. An explicitly configured value
always takes precedence over a derivation of the same name.

The Resolver presents configured and derived values through a single
interface while retaining provenance information for configuration
inspection and diagnostics. It also exposes artifact, realization,
model, and variant identity.

The system configuration may contain reference data such as the
[colors] catalog. Reference data does not participate in normal
parameter resolution.

Artifact configuration persistence is also owned by this subsystem.
Artifact configuration is stored at:

    artifacts/<artifact_id>/artifact.toml

An artifact may use the legacy single-realization form or declare
explicit named realizations. Realization names are artifact-scoped.
Each realization selects a model, may select one of that model's
variants, and may provide realization-specific parameter overrides.

Artifact TOML files are intentionally sparse. Only artifact-specific
realization choices and parameter overrides need to be persisted.

Artifact TOML files are read and written with tomlkit so that comments,
ordering, whitespace, and other presentation details survive interactive
configuration updates.
"""

from __future__ import annotations

import importlib
import os
import tempfile
import tomllib
from collections.abc import Callable, Mapping, MutableMapping
from pathlib import Path
from typing import Any

import tomlkit
from tomlkit.exceptions import ParseError
from tomlkit.toml_document import TOMLDocument

from lowkey_artifact_builder.model import build_model_registry

# =========================================================
# Types
# =========================================================


type Derivation = Callable[
    ["Resolver"],
    Any,
]

type Derivations = Mapping[
    str,
    Derivation,
]

# =========================================================
# Exceptions
# =========================================================


class ConfigError(RuntimeError):
    """
    Raised when artifact configuration cannot be resolved or persisted.
    """


# =========================================================
# Resolver
# =========================================================


class Resolver:
    """
    Resolve configured and derived artifact values.

    Configured values have already been merged according to
    configuration precedence before the Resolver is constructed.

    Derived values are evaluated lazily and cached for the lifetime of
    the Resolver.

    If a configured value and a derivation share the same name, the
    configured value wins. This permits derived values to be explicitly
    overridden when necessary.
    """

    def __init__(
        self,
        values: Mapping[str, Any],
        provenance: Mapping[str, str],
        *,
        derivations: Derivations | None = None,
        colors: Mapping[str, Any] | None = None,
    ) -> None:
        """
        Construct a resolver.
        """

        self._values = dict(values)
        self._provenance = dict(provenance)

        self._derivations = dict(derivations or {})

        self._colors = dict(colors or {})

        self._derived_cache: dict[
            str,
            Any,
        ] = {}

        self._resolving: list[str] = []

    # =====================================================
    # Resolution
    # =====================================================

    def __call__(
        self,
        name: str,
    ) -> Any:
        """
        Resolve a configuration value by name.
        """

        return self.resolve(
            name,
        )

    def resolve(
        self,
        name: str,
    ) -> Any:
        """
        Resolve a configured or derived value.

        Explicitly configured values always take precedence over
        derivations.
        """

        if name in self._values:
            return self._values[name]

        if name in self._derived_cache:
            return self._derived_cache[name]

        derivation = self._derivations.get(name)

        if derivation is None:
            raise ConfigError(f"Unknown configuration value {name!r}.")

        if name in self._resolving:
            cycle_start = self._resolving.index(name)

            cycle = self._resolving[cycle_start:] + [name]

            raise ConfigError("Derived configuration cycle detected: " + " -> ".join(cycle))

        self._resolving.append(name)

        try:
            value = derivation(self)
        finally:
            self._resolving.pop()

        self._derived_cache[name] = value

        return value

    # =====================================================
    # Parameter introspection
    # =====================================================

    def has(
        self,
        name: str,
    ) -> bool:
        """
        Return whether a configured or derived value exists.
        """

        return name in self._values or name in self._derivations

    def source(
        self,
        name: str,
    ) -> str:
        """
        Return the provenance of a resolved value.

        Configured values report the scope that supplied them.

        A configured value that also has a derivation reports that the
        configured value overrides the derivation.
        """

        if name in self._values:
            source = self._provenance[name]

            if name in self._derivations:
                return f"{source} (overrides derived)"

            return source

        if name in self._derivations:
            return "derived"

        raise ConfigError(f"Unknown configuration value {name!r}.")

    def names(
        self,
    ) -> tuple[str, ...]:
        """
        Return all configured and derived value names.
        """

        return tuple(sorted(set(self._values) | set(self._derivations)))

    def configured_names(
        self,
    ) -> tuple[str, ...]:
        """
        Return explicitly configured value names.
        """

        return tuple(sorted(self._values))

    def derived_names(
        self,
    ) -> tuple[str, ...]:
        """
        Return names having derivations.
        """

        return tuple(sorted(self._derivations))

    def as_dict(
        self,
    ) -> dict[str, Any]:
        """
        Resolve all known values into a dictionary.

        This is primarily intended for configuration inspection and
        command-line --dump output.
        """

        return {name: self.resolve(name) for name in self.names()}

    # =====================================================
    # Color catalog
    # =====================================================

    @property
    def colors(
        self,
    ) -> Mapping[str, Any]:
        """
        Return the system color catalog.

        Color definitions are reference data and are not part of the
        normal parameter-resolution hierarchy.
        """

        return self._colors

    def has_color(
        self,
        name: str,
    ) -> bool:
        """
        Return whether the color catalog contains a color.
        """

        return name in self._colors

    def color(
        self,
        name: str,
    ) -> Any:
        """
        Return a color catalog entry.
        """

        try:
            return self._colors[name]

        except KeyError as exc:
            raise ConfigError(f"Unknown color {name!r}.") from exc


# =========================================================
# Public factory
# =========================================================


def get_resolver(
    artifact_id: str,
    *,
    model: str | None = None,
    realization: str | None = None,
    project_root: Path | str | None = None,
) -> Resolver:
    """
    Construct the resolver for one artifact realization.

    artifact_id is always required.

    An artifact may use either the legacy single-realization
    configuration form or explicit named realizations.

    A legacy artifact implicitly defines exactly one realization named
    "default":

        model = "artwork"
        variant = "default"

        [parameters]
        ...

    An artifact may instead declare explicit realizations:

        source = "source.png"

        [parameters]
        shared_parameter = "value"

        [realizations.small]
        model = "artwork"
        variant = "default"

        [realizations.small.parameters]
        realization_parameter = "value"

    Artifact-scoped configurable values are inherited by every explicit
    realization. Realization-specific configurable values override
    inherited artifact values.

    Model and variant identity are selected by the realization itself
    and are not inherited as ordinary artifact parameters.

    During initial artifact setup, configuration may not yet contain a
    model. In that case setup may supply the selected model explicitly:

        get_resolver(
            "nydeli",
            model="artwork",
        )

    A realization may select one of the variants declared by its model.
    When no variant is configured, the model's default variant is used.

    Configuration precedence is:

        system
            <
        model
            <
        variant
            <
        workspace
            <
        artifact
            <
        realization

    For legacy artifact configuration, the implicit "default"
    realization is the artifact configuration itself. It therefore
    retains the existing artifact-level precedence behavior without
    introducing a separate realization override scope.

    The current working directory is used as the project root unless
    project_root is explicitly supplied.
    """

    _validate_artifact_id(artifact_id)

    root = _project_root(project_root)

    # -----------------------------------------------------
    # System configuration
    # -----------------------------------------------------

    system_document = _load_system_document()

    system_parameters = _parameters_from_document(
        system_document,
        source="system parameters",
    )

    colors = _colors_from_document(system_document)

    # -----------------------------------------------------
    # Artifact and realization configuration
    #
    # Inspect these before model parameters are loaded because
    # the selected realization identifies its model and variant.
    #
    # Legacy artifact configuration is normalized to an
    # implicit realization named "default".
    # -----------------------------------------------------

    artifact_document = load_artifact_config(
        artifact_id,
        project_root=root,
    )

    realization_name = _resolve_realization_name(
        artifact_document,
        realization,
    )

    realization_document = _realization_document(
        artifact_document,
        realization_name,
    )

    explicit_realizations = "realizations" in artifact_document

    configured_model = _artifact_model(
        realization_document,
    )

    model_name = _resolve_model_name(
        artifact_id,
        configured_model=configured_model,
        requested_model=model,
    )

    variant_name = _artifact_variant(
        realization_document,
    )

    # -----------------------------------------------------
    # Model configuration
    # -----------------------------------------------------

    model_parameters = _load_model_parameters(
        model_name,
    )

    derivations = _load_model_derivations(
        model_name,
    )

    model_spec = build_model_registry().get_model(
        model_name,
    )

    variant = _resolve_variant(
        model_spec,
        variant_name,
    )

    # -----------------------------------------------------
    # Workspace configuration
    # -----------------------------------------------------

    workspace_document = _load_optional_toml(root / "workspace.toml")

    workspace_parameters = _parameters_from_document(
        workspace_document,
        source="workspace",
    )

    # -----------------------------------------------------
    # Artifact and realization parameters
    #
    # Explicit named realizations inherit configurable values
    # declared at artifact scope. Their own configurable values
    # then override those inherited values.
    #
    # Legacy configuration already uses the artifact document as
    # its implicit default realization, so it must be merged only
    # once.
    # -----------------------------------------------------

    artifact_parameters = _artifact_parameters(
        artifact_document,
    )

    if explicit_realizations:
        realization_parameters = _artifact_parameters(
            realization_document,
        )
    else:
        realization_parameters = {}

    # -----------------------------------------------------
    # Merge configured values
    # -----------------------------------------------------

    values: dict[str, Any] = {}
    provenance: dict[str, str] = {}

    _merge(
        values,
        provenance,
        system_parameters,
        source="system",
    )

    _merge(
        values,
        provenance,
        model_parameters,
        source="model",
    )

    _merge(
        values,
        provenance,
        variant.parameters,
        source=f"variant {variant.name!r}",
    )

    _merge(
        values,
        provenance,
        workspace_parameters,
        source="workspace",
    )

    _merge(
        values,
        provenance,
        artifact_parameters,
        source="artifact",
    )

    if explicit_realizations:
        _merge(
            values,
            provenance,
            realization_parameters,
            source=f"realization {realization_name!r}",
        )

    # -----------------------------------------------------
    # Artifact and realization identity
    # -----------------------------------------------------

    values["artifact_id"] = artifact_id
    provenance["artifact_id"] = "artifact"

    values["realization"] = realization_name
    provenance["realization"] = "artifact" if explicit_realizations else "implicit default"

    values["model"] = model_name

    if configured_model is not None:
        provenance["model"] = (
            f"realization {realization_name!r}" if explicit_realizations else "artifact"
        )
    else:
        provenance["model"] = "setup"

    values["variant"] = variant.name

    if variant_name is not None:
        provenance["variant"] = (
            f"realization {realization_name!r}" if explicit_realizations else "artifact"
        )
    else:
        provenance["variant"] = "default"

    return Resolver(
        values,
        provenance,
        derivations=derivations,
        colors=colors,
    )


# =========================================================
# Artifact configuration persistence
# =========================================================


def artifact_config_path(
    artifact_id: str,
    *,
    project_root: Path | str | None = None,
) -> Path:
    """
    Return the configuration path for an artifact.

    Artifact configuration is stored at:

        artifacts/<artifact_id>/artifact.toml
    """

    _validate_artifact_id(artifact_id)

    root = _project_root(project_root)

    return root / "artifacts" / artifact_id / "artifact.toml"


def load_artifact_config(
    artifact_id: str,
    *,
    project_root: Path | str | None = None,
) -> dict[str, Any]:
    """
    Load an artifact's sparse configuration.

    A missing artifact.toml is valid and returns an empty dictionary.
    This is necessary during initial artifact setup.

    A plain dictionary is returned so callers do not depend on
    tomlkit's document representation.
    """

    path = artifact_config_path(
        artifact_id,
        project_root=project_root,
    )

    if not path.exists():
        return {}

    document = _load_artifact_document(path)

    return document.unwrap()


def write_artifact_config(
    artifact_id: str,
    values: Mapping[str, Any],
    *,
    project_root: Path | str | None = None,
) -> Path:
    """
    Write an artifact configuration exactly as supplied.

    The artifact directory is created when necessary.

    Existing artifact.toml contents are replaced. Use
    update_artifact_config() when editing an existing artifact and
    preserving its comments and formatting is desired.

    The write is atomic.

    Returns the artifact.toml path.
    """

    path = artifact_config_path(
        artifact_id,
        project_root=project_root,
    )

    document_values = dict(values)

    _validate_artifact_document(document_values)

    document = tomlkit.document()

    for name, value in document_values.items():
        document[name] = value

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    _write_artifact_document_atomic(
        path,
        document,
    )

    return path


def update_artifact_config(
    artifact_id: str,
    values: Mapping[str, Any],
    *,
    project_root: Path | str | None = None,
) -> Path:
    """
    Update selected values in an artifact configuration.

    Existing values not present in values are preserved.

    Existing artifact.toml formatting, comments, and ordering are
    preserved by tomlkit wherever possible.

    Top-level values are updated at the top level.

    If values contains a "parameters" mapping, those entries are merged
    into the existing [parameters] table rather than replacing the
    complete table.

    If artifact.toml does not yet exist, a new document is created.

    Returns the artifact.toml path.
    """

    path = artifact_config_path(
        artifact_id,
        project_root=project_root,
    )

    if path.exists():
        document = _load_artifact_document(path)
    else:
        document = tomlkit.document()

    for name, value in values.items():
        if name == "parameters" and isinstance(value, Mapping):
            _update_parameters_table(
                document,
                value,
            )

            continue

        document[name] = value

    _validate_artifact_document(document.unwrap())

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    _write_artifact_document_atomic(
        path,
        document,
    )

    return path


# =========================================================
# Artifact validation
# =========================================================


def _validate_artifact_id(
    artifact_id: str,
) -> None:
    """
    Validate an artifact identifier.

    Artifact IDs identify a single directory immediately below
    ./artifacts and therefore may not contain path separators or
    represent special filesystem names.
    """

    if not isinstance(
        artifact_id,
        str,
    ):
        raise ConfigError("Artifact ID must be a string.")

    if not artifact_id:
        raise ConfigError("Artifact ID cannot be empty.")

    if artifact_id in {
        ".",
        "..",
    }:
        raise ConfigError(f"Invalid artifact ID {artifact_id!r}.")

    if "/" in artifact_id or "\\" in artifact_id:
        raise ConfigError("Artifact ID cannot contain path separators.")


def _validate_artifact_document(
    document: Mapping[str, Any],
) -> None:
    """
    Validate structural requirements of artifact.toml.

    Initial setup may write a partial document, so a model is not
    required here. When present, however, identity fields must be valid.
    """

    model = document.get("model")

    if model is not None:
        if not isinstance(
            model,
            str,
        ):
            raise ConfigError("Artifact model must be a string.")

        if not model.strip():
            raise ConfigError("Artifact model cannot be empty.")

    variant = document.get("variant")

    if variant is not None:
        if not isinstance(
            variant,
            str,
        ):
            raise ConfigError("Artifact variant must be a string.")

        if not variant.strip():
            raise ConfigError("Artifact variant cannot be empty.")

    parameters = document.get("parameters")

    if parameters is not None and not isinstance(
        parameters,
        Mapping,
    ):
        raise ConfigError("The [parameters] section in artifact.toml must be a TOML table.")

    realizations = document.get("realizations")

    if realizations is not None:
        if not isinstance(
            realizations,
            Mapping,
        ):
            raise ConfigError("The [realizations] section in artifact.toml must be a TOML table.")

        for name, realization in realizations.items():
            if (
                not isinstance(
                    name,
                    str,
                )
                or not name.strip()
            ):
                raise ConfigError("Realization names must be non-empty strings.")

            if not isinstance(
                realization,
                Mapping,
            ):
                raise ConfigError(f"Realization {name!r} must be a TOML table.")

            _validate_realization_document(
                name,
                realization,
            )


def _validate_realization_document(
    name: str,
    document: Mapping[str, Any],
) -> None:
    """
    Validate one realization configuration.
    """

    model = document.get("model")

    if model is not None:
        if not isinstance(
            model,
            str,
        ):
            raise ConfigError(f"Realization {name!r} model must be a string.")

        if not model.strip():
            raise ConfigError(f"Realization {name!r} model cannot be empty.")

    variant = document.get("variant")

    if variant is not None:
        if not isinstance(
            variant,
            str,
        ):
            raise ConfigError(f"Realization {name!r} variant must be a string.")

        if not variant.strip():
            raise ConfigError(f"Realization {name!r} variant cannot be empty.")

    parameters = document.get("parameters")

    if parameters is not None and not isinstance(
        parameters,
        Mapping,
    ):
        raise ConfigError(f"The [parameters] section in realization {name!r} must be a TOML table.")


# =========================================================
# Artifact TOML
# =========================================================


def _load_artifact_document(
    path: Path,
) -> TOMLDocument:
    """
    Load artifact.toml as a tomlkit document.

    The document representation is retained internally so updates can
    preserve comments, whitespace, ordering, and formatting.
    """

    if not path.is_file():
        raise ConfigError(f"Artifact configuration path is not a file: {path}")

    try:
        text = path.read_text(
            encoding="utf-8",
        )

        return tomlkit.parse(text)

    except ParseError as exc:
        raise ConfigError(f"Invalid TOML in {path}: {exc}") from exc

    except OSError as exc:
        raise ConfigError(f"Unable to read artifact configuration {path}: {exc}") from exc


def _update_parameters_table(
    document: TOMLDocument,
    values: Mapping[str, Any],
) -> None:
    """
    Merge values into the artifact [parameters] table.

    Existing formatting and comments within the table are retained.
    """

    existing = document.get("parameters")

    if existing is None:
        parameters = tomlkit.table()

        document["parameters"] = parameters

    else:
        if not isinstance(
            existing,
            MutableMapping,
        ):
            raise ConfigError(
                "The existing [parameters] section in artifact.toml must be a TOML table."
            )

        parameters = existing

    for name, value in values.items():
        parameters[name] = value


def _write_artifact_document_atomic(
    path: Path,
    document: TOMLDocument,
) -> None:
    """
    Atomically write an artifact TOML document.

    tomlkit renders the original document representation, preserving
    comments and formatting retained by the parser.

    The temporary file is created in the destination directory so
    os.replace() remains an atomic filesystem operation.
    """

    temporary_path: Path | None = None

    try:
        text = tomlkit.dumps(document)

        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=path.parent,
            delete=False,
        ) as stream:
            temporary_path = Path(stream.name)

            stream.write(text)

            stream.flush()

            os.fsync(stream.fileno())

        os.replace(
            temporary_path,
            path,
        )

    except (OSError, TypeError, ValueError) as exc:
        if temporary_path is not None and temporary_path.exists():
            try:
                temporary_path.unlink()

            except OSError:
                pass

        raise ConfigError(f"Unable to write artifact configuration {path}: {exc}") from exc


# =========================================================
# Realization resolution
# =========================================================


def _resolve_realization_name(
    artifact_document: Mapping[str, Any],
    requested_realization: str | None,
) -> str:
    """
    Resolve the realization selected for an artifact.

    Artifacts using the legacy single-model configuration implicitly
    contain exactly one realization named "default".

    Artifacts declaring [realizations] expose exactly the realization
    names declared in that table.
    """

    if requested_realization is not None:
        requested_realization = requested_realization.strip()

        if not requested_realization:
            raise ConfigError("Requested realization cannot be empty.")

    realizations = artifact_document.get("realizations")

    if realizations is None:
        realization_name = requested_realization if requested_realization is not None else "default"

        if realization_name != "default":
            raise ConfigError(f"unknown realization {realization_name!r}.")

        return "default"

    if not isinstance(
        realizations,
        Mapping,
    ):
        raise ConfigError("The [realizations] section in artifact.toml must be a TOML table.")

    if requested_realization is None:
        if "default" in realizations:
            return "default"

        raise ConfigError("Artifact defines explicit realizations; a realization must be selected.")

    if requested_realization not in realizations:
        raise ConfigError(f"unknown realization {requested_realization!r}.")

    return requested_realization


def _realization_document(
    artifact_document: Mapping[str, Any],
    realization_name: str,
) -> Mapping[str, Any]:
    """
    Return the configuration document for one realization.

    Legacy artifact configuration is treated as an implicit realization
    named "default".

    Explicit realization configuration is read from the artifact's
    [realizations] table.
    """

    realizations = artifact_document.get("realizations")

    if realizations is None:
        if realization_name != "default":
            raise ConfigError(f"unknown realization {realization_name!r}.")

        return artifact_document

    if not isinstance(
        realizations,
        Mapping,
    ):
        raise ConfigError("The [realizations] section in artifact.toml must be a TOML table.")

    realization = realizations.get(realization_name)

    if realization is None:
        raise ConfigError(f"unknown realization {realization_name!r}.")

    if not isinstance(
        realization,
        Mapping,
    ):
        raise ConfigError(f"Realization {realization_name!r} must be a TOML table.")

    return realization


# =========================================================
# Model resolution
# =========================================================


def _artifact_model(
    document: Mapping[str, Any],
) -> str | None:
    """
    Return the model declared by artifact.toml.

    model is artifact identity rather than an ordinary inherited
    parameter. It therefore lives at the document's top level.
    """

    value = document.get("model")

    if value is None:
        return None

    if not isinstance(
        value,
        str,
    ):
        raise ConfigError("Artifact model must be a string.")

    value = value.strip()

    if not value:
        raise ConfigError("Artifact model cannot be empty.")

    return value


def _artifact_variant(
    document: Mapping[str, Any],
) -> str | None:
    """
    Return the variant declared by artifact.toml.

    Variant selection is artifact identity rather than an ordinary
    inherited parameter. It therefore lives at the document's top
    level.

    A missing variant selects the model's default variant.
    """

    value = document.get("variant")

    if value is None:
        return None

    if not isinstance(
        value,
        str,
    ):
        raise ConfigError("Artifact variant must be a string.")

    value = value.strip()

    if not value:
        raise ConfigError("Artifact variant cannot be empty.")

    return value


def _resolve_variant(
    model,
    configured_variant: str | None,
):
    """
    Resolve the selected variant within one model.

    Variant names are model-scoped. A missing artifact variant selects
    the model's default variant.
    """

    variant_name = configured_variant if configured_variant is not None else "default"

    for variant in model.variants:
        if variant.name == variant_name:
            return variant

    raise ConfigError(f"unknown variant {variant_name!r} for model {model.name!r}.")


def _resolve_model_name(
    artifact_id: str,
    *,
    configured_model: str | None,
    requested_model: str | None,
) -> str:
    """
    Determine the model used to resolve an artifact.
    """

    if requested_model is not None:
        requested_model = requested_model.strip()

        if not requested_model:
            raise ConfigError("Requested model cannot be empty.")

    if (
        configured_model is not None
        and requested_model is not None
        and configured_model != requested_model
    ):
        raise ConfigError(
            f"Artifact {artifact_id!r} declares model "
            f"{configured_model!r}, but model "
            f"{requested_model!r} was requested."
        )

    if configured_model is not None:
        return configured_model

    if requested_model is not None:
        return requested_model

    raise ConfigError(
        f"Artifact {artifact_id!r} does not define a model. "
        "Supply model= during initial artifact setup."
    )


# =========================================================
# Model configuration
# =========================================================


def _model_package_name(
    model: str,
) -> str:
    """
    Return the implementation package for a model.
    """

    return f"lowkey_artifact_builder.model.models.{model}"


def _load_model_parameters(
    model: str,
) -> dict[str, Any]:
    """
    Load model-specific parameter defaults.
    """

    module = _import_model_package(model)

    module_file = getattr(
        module,
        "__file__",
        None,
    )

    if module_file is None:
        raise ConfigError(f"Unable to locate model package {model!r}.")

    path = Path(module_file).resolve().parent / "parameters.toml"

    if not path.exists():
        return {}

    document = _load_toml(path)

    return _parameters_from_document(
        document,
        source=f"model {model!r}",
    )


def _load_model_derivations(
    model: str,
) -> dict[str, Derivation]:
    """
    Load a model's derived-value registry.

    A model may omit derived.py when it has no derived values.
    """

    package_name = _model_package_name(model)

    module_name = f"{package_name}.derived"

    try:
        module = importlib.import_module(module_name)

    except ModuleNotFoundError as exc:
        if exc.name == module_name:
            return {}

        raise ConfigError(f"Unable to load derived values for model {model!r}: {exc}") from exc

    registry = getattr(
        module,
        "DERIVED",
        None,
    )

    if registry is None:
        return {}

    if not isinstance(
        registry,
        Mapping,
    ):
        raise ConfigError(f"{module_name}.DERIVED must be a mapping.")

    derivations: dict[
        str,
        Derivation,
    ] = {}

    for name, function in registry.items():
        if not isinstance(
            name,
            str,
        ):
            raise ConfigError(f"{module_name}.DERIVED contains a non-string name.")

        if not callable(function):
            raise ConfigError(f"Derived value {name!r} for model {model!r} is not callable.")

        derivations[name] = function

    return derivations


def _import_model_package(
    model: str,
):
    """
    Import a model implementation package.
    """

    module_name = _model_package_name(model)

    try:
        return importlib.import_module(module_name)

    except ModuleNotFoundError as exc:
        if exc.name == module_name:
            raise ConfigError(f"Unknown artifact model {model!r}.") from exc

        raise ConfigError(f"Unable to load artifact model {model!r}: {exc}") from exc


# =========================================================
# System configuration
# =========================================================


def _system_parameters_path() -> Path:
    """
    Return the packaged system parameters path.
    """

    return Path(__file__).resolve().parent / "parameters.toml"


def _load_system_document() -> dict[str, Any]:
    """
    Load the system parameters document.
    """

    path = _system_parameters_path()

    if not path.is_file():
        raise ConfigError(f"System configuration file does not exist: {path}")

    return _load_toml(path)


# =========================================================
# Document interpretation
# =========================================================


def _parameters_from_document(
    document: Mapping[str, Any],
    *,
    source: str,
) -> dict[str, Any]:
    """
    Extract the [parameters] table from a configuration document.

    Missing [parameters] is valid and contributes no values.
    """

    parameters = document.get("parameters", {})

    if not isinstance(
        parameters,
        Mapping,
    ):
        raise ConfigError(f"The [parameters] section in {source} must be a TOML table.")

    return dict(parameters)


def _colors_from_document(
    document: Mapping[str, Any],
) -> dict[str, Any]:
    """
    Extract the system [colors] catalog.
    """

    colors = document.get("colors", {})

    if not isinstance(
        colors,
        Mapping,
    ):
        raise ConfigError("The [colors] section in system configuration must be a TOML table.")

    return dict(colors)


def _artifact_parameters(
    document: Mapping[str, Any],
) -> dict[str, Any]:
    """
    Extract configurable values from artifact.toml.

    Artifact identity fields such as model live at the top level.

    Ordinary artifact parameter overrides may either be stored in a
    [parameters] table or, for sparse artifact configuration, directly
    at the top level.

    The top-level form keeps artifact.toml concise:

        model = "artwork"
        source = "new-york-deli-blimp.png"
        printer_colors = ["black", "white", "red"]

    A [parameters] table is also accepted. Values in [parameters]
    override equivalent top-level values.
    """

    parameters: dict[str, Any] = {}

    for name, value in document.items():
        if name in {
            "model",
            "variant",
            "parameters",
            "realizations",
        }:
            continue

        parameters[name] = value

    nested = document.get("parameters", {})

    if not isinstance(
        nested,
        Mapping,
    ):
        raise ConfigError("The [parameters] section in artifact.toml must be a TOML table.")

    parameters.update(nested)

    return parameters


# =========================================================
# Generic TOML loading
# =========================================================


def _load_optional_toml(
    path: Path,
) -> dict[str, Any]:
    """
    Load a TOML document when present.

    Missing workspace configuration is valid.
    """

    if not path.exists():
        return {}

    if not path.is_file():
        raise ConfigError(f"Configuration path is not a file: {path}")

    return _load_toml(path)


def _load_toml(
    path: Path,
) -> dict[str, Any]:
    """
    Load a read-only TOML document.

    System, model, and workspace configuration use the standard-library
    TOML parser because their formatting does not need to be retained
    for artifact editing.
    """

    try:
        with path.open("rb") as stream:
            data = tomllib.load(stream)

    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"Invalid TOML in {path}: {exc}") from exc

    except OSError as exc:
        raise ConfigError(f"Unable to read configuration file {path}: {exc}") from exc

    return data


# =========================================================
# Parameter merging
# =========================================================


def _merge(
    values: dict[str, Any],
    provenance: dict[str, str],
    incoming: Mapping[str, Any],
    *,
    source: str,
) -> None:
    """
    Merge one configuration scope.

    Later scopes replace values supplied by earlier scopes.
    """

    for name, value in incoming.items():
        values[name] = value
        provenance[name] = source


# =========================================================
# Paths
# =========================================================


def _project_root(
    project_root: Path | str | None,
) -> Path:
    """
    Resolve the project root.

    The current working directory is the default project root.
    """

    if project_root is None:
        return Path.cwd().resolve()

    return Path(project_root).resolve()


# =========================================================
# Exports
# =========================================================


__all__ = [
    "ConfigError",
    "Derivation",
    "Derivations",
    "Resolver",
    "artifact_config_path",
    "get_resolver",
    "load_artifact_config",
    "update_artifact_config",
    "write_artifact_config",
]
