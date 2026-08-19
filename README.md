# lowkey-artifact-builder

`lowkey-artifact-builder` is a model-driven build system for creating
reproducible, 3D-printable artifacts.

The project manages configurable artifacts through declarative build
pipelines. Each artifact selects a model, enables optional features, and
provides configuration that is resolved into a build plan consisting of
stages, dependencies, and filesystem products.

The final product of a successful build is a ready-to-slice 3MF file:

```text
artifacts/<artifact_id>.3mf
```

`lowkey-artifact-builder` is developed by
[LowKeyLabs LLC](https://lowkeylabs.com).


## Status

**Early development / architectural implementation.**

The project is currently establishing the model registry, configuration
system, build planner, dependency graph, filesystem conventions, and
pipeline runner.

The initial implementation is derived from experience building the
[`low-ornament-workflow`](https://github.com/lowkeylabs/low-ornament-workflow)
PNG-to-3MF pipeline.

The new architecture generalizes that workflow so that multiple artifact
models can share the same configuration and build infrastructure.


## Goals

`lowkey-artifact-builder` is designed around several principles:

- **Model independent** — the build engine should not contain assumptions
  about a particular artifact geometry.
- **Artifact oriented** — every build operates on a uniquely identified
  artifact.
- **Declarative** — models declare their features, stages, dependencies,
  and expected filesystem products before execution begins.
- **Inspectable** — the complete build plan can be examined before a build.
- **Resumable** — completed filesystem products can be reused rather than
  regenerated unnecessarily.
- **Debuggable** — intermediate products remain available for inspection.
- **Reproducible** — configuration and build dependencies determine what
  must be rebuilt.
- **Extensible** — new models can use the generic pipeline without adding
  model-specific behavior to the build engine.


## Concepts

### Workspace

A workspace is a directory containing the source material and configuration
for one or more artifacts.

A workspace will contain a `workspace.toml` file that provides
workspace-wide and artifact-specific configuration.

For example:

```text
customer-project/
├── workspace.toml
├── 2121_stuart.png
├── goldberry.png
└── artifacts/
```

Artifacts in the same workspace can share configuration such as physical
dimensions, printer characteristics, and filament colors while overriding
settings specific to an individual artifact.


### Artifact

An artifact is an individual object managed by the build system.

Every artifact has an `artifact_id`, such as:

```text
2121_stuart
goldberry
fan_district
```

The artifact ID is used throughout configuration, planning, building, and
filesystem organization.


### Model

Each artifact selects a registered model.

A model defines the model-specific behavior required to transform source
material and resolved parameters into a final 3MF.

Possible models include:

```text
circular
logo
```

Models are independently extensible packages implementing the interfaces
defined by `lowkey-artifact-builder`.

The generic build system should not need to know whether a model represents
a coaster, ornament, logo, medallion, or another type of object.


### Features

Models may provide optional features.

For example, a circular model may eventually support:

```text
labels
hanger
magnet
```

Features may affect:

- configuration requirements;
- model geometry;
- enabled build stages;
- stage dependencies; and
- generated products.

Features belong to the model rather than the generic build engine.


### Stages

A model declares the stages that make up its build pipeline.

For example, a circular model might contain:

```text
holder
labels
artwork
package
```

Stages are dependency-graph nodes rather than merely a fixed sequence of
commands.

For example:

```text
              holder ────┐
                         │
              labels ────┼──> package
                         │
              artwork ───┘
```

If labels are not enabled, the model may produce a different build plan:

```text
              holder ────┐
                         ├──> package
              artwork ───┘
```

This allows independent stages to be inspected, rebuilt, and tested
separately.


### Products

Every stage declares its expected filesystem products before execution.

Products may include files such as:

```text
source.png
mask.png
source.svg
paths.svg
model.scad
model.stl
model.3mf
```

The filesystem path identifies the artifact and stage, allowing product
filenames themselves to remain consistent.


## Artifact Filesystem

All generated products are stored beneath:

```text
artifacts/
```

Intermediate products for an artifact are stored beneath:

```text
artifacts/<artifact_id>/
```

The final ready-to-slice product is stored directly in the `artifacts`
directory:

```text
artifacts/<artifact_id>.3mf
```

For example:

```text
artifacts/
├── 2121_stuart.3mf
├── goldberry.3mf
│
├── 2121_stuart/
│   ├── holder/
│   │   ├── model.scad
│   │   └── model.stl
│   │
│   ├── labels/
│   │   ├── source.svg
│   │   ├── paths.svg
│   │   └── model.stl
│   │
│   └── artwork/
│       └── ...
│
└── goldberry/
    ├── holder/
    └── artwork/
```

This provides two useful invariants:

```text
artifacts/<artifact_id>/     intermediate and reviewable products
artifacts/<artifact_id>.3mf  final ready-to-slice product
```

Generated products are not intended to be committed to Git.


## Configuration

The planned configuration system uses three levels of parameter resolution:

```text
master defaults
      ↓
workspace overrides
      ↓
artifact overrides
```

The model defines which parameters and features are valid.

The configuration system determines their effective values and tracks
parameter provenance so that users can determine where a value originated
and whether it has been overridden.

The user-facing workspace configuration is stored in:

```text
workspace.toml
```

TOML is intentionally retained as a human-readable, version-controllable
configuration format.


## Command Line Interface

The command-line entry point is:

```bash
artifact
```

The planned interface includes commands such as:

```bash
artifact models
artifact config
artifact plan <artifact_id>
artifact build <artifact_id>
artifact status <artifact_id>
artifact clean <artifact_id>
```

During early development, not all commands shown above are implemented.

The CLI uses Click for command organization and Rich where enhanced terminal
presentation is useful.


## Build Planning

A model will be queried before execution to construct a complete build plan.

The plan describes:

- selected model;
- enabled features;
- stages;
- stage dependencies;
- configuration dependencies;
- input files;
- expected filesystem products; and
- final 3MF product.

This makes it possible to inspect the complete workflow before starting a
build and provides the information needed for progress reporting,
incremental rebuilding, status reporting, and debugging.


## Incremental Builds

The build system is intended to operate similarly to `make`.

A stage should only be rebuilt when necessary, such as when:

- an expected product is missing;
- an input has changed;
- relevant configuration has changed;
- an enabled feature has changed; or
- a dependency has been rebuilt.

Intermediate products are intentionally retained so that a build can be
stopped, inspected, and resumed.

The build engine is responsible for deciding whether a stage is current;
individual models should not need to implement their own incremental-build
systems.


## Architecture

The high-level architecture is:

```text
                 workspace.toml
                       │
                       ▼
                 configuration
                       │
                       ▼
                    artifact
                       │
                       ▼
                 ModelRegistry
                       │
             ┌─────────┴─────────┐
             ▼                   ▼
          circular              logo
             │                   │
             └─────────┬─────────┘
                       ▼
                   BuildPlan
                       │
                       ▼
                dependency graph
                       │
                       ▼
                  stage runner
                       │
                       ▼
              filesystem products
                       │
                       ▼
          artifacts/<artifact_id>.3mf
```

Model-specific behavior belongs in model packages.

The generic configuration, planning, dependency, and build systems should
not import or special-case individual model implementations.


## Development

See [`SETUP.md`](SETUP.md) for complete development-environment setup
instructions.

The short version is:

```bash
git clone https://github.com/lowkeylabs/lowkey-artifact-builder.git
cd lowkey-artifact-builder

uv sync
source .venv/bin/activate
pre-commit install

make check
```

Run the CLI with:

```bash
artifact --help
```

Common development commands include:

```bash
make test
make coverage
make lint
make format
make typecheck
make check
make pre-commit
```


## Testing

The project uses pytest.

Tests are organized to mirror the source package:

```text
tests/
├── test_installation.py
├── cli/
├── models/
└── build/
```

Run the complete test suite with:

```bash
make test
```

The generic model registry, build planner, dependency graph, and pipeline
runner are designed to be testable without requiring external tools such
as OpenSCAD or Inkscape.

External modeling and graphics tools should be introduced through focused
integration tests rather than being required by the core test suite.


## Documentation

Repository-level development and contributor documentation is maintained
at the repository root:

```text
README.md
SETUP.md
CONTRIBUTING.md
```

Source material for the project website and GitHub Pages documentation will
be maintained under:

```text
site-src/
```

Generated GitHub Pages content will be written to:

```text
docs/
```


## Contributing

Contributions are welcome.

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for contribution guidelines.


## License

`lowkey-artifact-builder` is open-source software distributed under the
Apache License, Version 2.0.

Commercial use, modification, and redistribution are permitted subject to
the terms of the license.

See:

- [`LICENSE`](LICENSE)
- [`NOTICE`](NOTICE)
- [`COPYRIGHT`](COPYRIGHT)
- [`COMMERCIAL.md`](COMMERCIAL.md)


## Citation

Citation metadata is provided in [`CITATION.cff`](CITATION.cff).


## About LowKeyLabs

`lowkey-artifact-builder` is developed by
[LowKeyLabs LLC](https://lowkeylabs.com).

Project repository:

https://github.com/lowkeylabs/lowkey-artifact-builder
