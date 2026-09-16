# lowkey-artifact-builder

`lowkey-artifact-builder` is a dependency-driven build system for turning
source artwork into reproducible, multicolor 2.5D manufacturing geometry.

A customer image can be interpreted once as registered Artwork and reused in
multiple printable objects such as ornaments, coasters, plaques, and other
Shape variants.

Conceptually:

```text
                         source PNG
                             │
                             ▼
                         Artwork
                             │
                    registered geometry
                             │
                             ▼
                          Shape
                             │
                 ┌───────────┼───────────┐
                 │           │           │
                 ▼           ▼           ▼
             ornament     coaster     other
              variant      variant    variants
                 │           │           │
                 └───────────┼───────────┘
                             │
                             ▼
                        Realizations
                             │
                             ▼
                  manufacturing Products
```

The system is designed so that reusable upstream work does not need to be
repeated merely because the same Artwork is used in another manufactured
object or configuration.

The project is developed by **lowkeylabs** and distributed under the
Apache License, Version 2.0.

---

## Status

`lowkey-artifact-builder` is under active development.

The current implementation supports two primary Models:

* **Artwork** — interprets raster artwork and produces registered,
  color-separated geometry;
* **Shape** — constructs physical objects and can incorporate registered
  Artwork.

The command-line interface and production workflow continue to evolve as the
project develops.

See [`CHANGEPLAN.md`](CHANGEPLAN.md) for the current implementation plan.

---

## Typical Workflow

The intended workflow minimizes per-Artifact configuration.

For routine production, customer PNG files are placed in the project root:

```text
smith-dog.png
jones-cat.png
lee-house.png
```

Create Artifacts from the intake files:

```bash
artifact create
```

Check the current build state:

```bash
artifact build
```

Bring stale or missing Realizations up to date:

```bash
artifact build --build-all
```

Ordinary packaged 3MF Products expose independently printable component
identity together with the resolved physical printing color, making normal
build output ready for slicing and printing.

When a particular Artifact requires customization, configure only the
Realization that differs from its Model-owned Variant:

```bash
artifact config smith-dog \
    --realization shape_ornament \
    --parameters shape_size=110
```

Then build that Realization:

```bash
artifact build smith-dog --realization shape_ornament
```

The CLI also provides inspection, maintenance, color-analysis, and recoloring
operations as the workflow requires them.

Run:

```bash
artifact --help
```

for the command surface available in the installed version.

---

## Core Concepts

Only a small amount of architectural vocabulary is necessary for ordinary use.

### Artifact

An **Artifact** is a named source and configuration context.

For example:

```text
smith-dog
jones-cat
family-2026
```

An Artifact commonly begins with source artwork and may participate in multiple
manufacturing Realizations.

### Model

A **Model** defines a reusable manufacturing recipe.

The current primary Models are:

```text
artwork
shape
```

Models own their parameters, Features, Variants, Stages, Products, and
manufacturing semantics.

### Variant

A **Variant** is a Model-owned reusable configuration.

Examples include:

```text
artwork.default
shape.default
shape.ornament
```

Variants provide shared configuration that can be applied consistently across
many Artifacts.

### Realization

A **Realization** is the application of a Variant to an Artifact, optionally
with Artifact-specific customization.

For example:

```text
Artifact:       smith-dog
Variant:        shape.ornament
Realization:    shape_ornament
```

Realizations are the normal Artifact-scoped execution coordinate used by the
CLI.

Every registered Model Variant provides a corresponding canonical Realization
without requiring the Realization to be declared explicitly in
`artifact.toml`.

### Product

A **Product** is a persistent output produced by a build Stage.

Products may include:

```text
PNG
SVG
STL
JSON manifests
3MF
```

Products can be consumed by later Stages, other Realizations, other Models, or
future builds.

A 3MF is therefore one possible manufacturing Product rather than a
privileged architectural "final product."

For the complete terminology, relationships, contracts, and invariants, see
[`ARCHITECTURE.md`](ARCHITECTURE.md).

---

## Models

### Artwork

The `artwork` Model converts raster source artwork into reusable registered,
color-separated geometry.

Artwork separates:

* interpretation of the source image;
* discovery of the colors represented by that image;
* assignment of physical filament colors to those discovered colors;
* registered raster and vector geometry; and
* optional physical dimensionalization.

The colors discovered in source Artwork are **Artifact colors**. They are
measured from the interpreted source rather than quantized to the colors
currently available to the printer.

Artwork can compare those Artifact colors with three physical color scopes:

```text
printer colors
library colors
color catalog
```

The current printer assignment defines the physical semantic colors used to
manufacture the Artwork.

Registered Artwork remains reusable and nonphysical until a Model introduces
physical dimensions. It can therefore be packaged as standalone Artwork or
consumed by another Model without repeating source interpretation.

The normative Artwork specification is:

[`src/lowkey_artifact_builder/model/models/artwork/DEFINITION.md`](src/lowkey_artifact_builder/model/models/artwork/DEFINITION.md)

### Shape

The `shape` Model constructs a physical object from parameterized
two-dimensional structural geometry.

Shape supports objects such as:

```text
coasters
ornaments
plaques
```

and other primarily 2.5D manufactured forms.

Shape owns physical properties such as:

* structural geometry;
* overall physical size;
* base geometry and thickness;
* optional structural Features such as an outer ridge;
* structural component partitioning;
* structural printing colors; and
* placement and dimensionalization of incorporated registered Artwork.

Shape can consume registered Artwork while preserving the Artwork's registered
geometry and color semantics.

Structural Shape geometry and incorporated Artwork remain registered through
composition. Physical dimensionalization occurs afterward.

The normative Shape specification is:

[`src/lowkey_artifact_builder/model/models/shape/DEFINITION.md`](src/lowkey_artifact_builder/model/models/shape/DEFINITION.md)

---

## Dependency-Driven Builds

`lowkey-artifact-builder` is a dependency-driven build system rather than a
fixed sequential pipeline.

Conceptually:

```text
requested Product
       │
       ▼
dependency planning
       │
       ▼
required Products
       │
       ▼
required Stages
       │
       ▼
current manufacturing state
```

Dependencies determine what must execute.

Successfully generated Products are persistent manufacturing assets and can be
reused when still current.

The planner therefore builds the dependency closure necessary for the
requested work rather than assuming that every Stage of every Model must run.

This permits registered Artwork, for example, to be reused by a Shape without
requiring standalone Artwork extrusion or packaging.

The complete build-system architecture is documented in
[`ARCHITECTURE.md`](ARCHITECTURE.md).

---

## Configuration

Configuration is layered so that common behavior can be defined once and
Artifact-specific configuration can remain sparse.

Conceptually:

```text
system configuration
        ↓
Model defaults
        ↓
Variant overrides
        ↓
workspace configuration
        ↓
Artifact customization
        ↓
Realization customization
        ↓
effective configuration
```

Model defaults define ordinary Model behavior.

Variants contain reusable overrides rather than complete duplicated
configurations.

Artifact and Realization configuration should therefore normally contain only
values that actually differ for that Artifact.

A newly created Artifact can use canonical Realizations without explicitly
declaring them in `artifact.toml`.

For complete configuration semantics and precedence rules, see
[`ARCHITECTURE.md`](ARCHITECTURE.md) and the applicable Model
`DEFINITION.md`.

---

## Color Workflow

Artwork distinguishes between the colors discovered in source artwork and the
physical filament colors available to manufacture it.

The three physical availability scopes are:

```text
printer
    colors currently available to the printer

library
    colors physically available in the filament library

catalog
    known physical filament colors
```

Artwork determines globally optimized one-to-one assignments between its
Artifact colors and the applicable physical palette.

Printer assignments define the physical semantic colors used by the current
Artwork manufacturing Realization.

Library and catalog assignments permit comparison with alternative palettes
without changing the current manufacturing configuration.

Shape structural components have their own Model-owned semantic printing
colors. Incorporated Artwork retains the color semantics supplied by Artwork.

Packaged 3MF Products preserve these semantic printing-color identities so
independently printable components can be identified by both component
identity and intended physical color.

Detailed color-assignment semantics are defined by the Artwork and Shape Model
definitions.

---

## Project Structure

The principal repository areas are:

```text
lowkey-artifact-builder/
├── ARCHITECTURE.md
├── CHANGEPLAN.md
├── CONTRIBUTING.md
├── README.md
├── SETUP.md
├── prompts/
├── src/
│   └── lowkey_artifact_builder/
│       ├── cli/
│       ├── config/
│       ├── engine/
│       └── model/
│           └── models/
│               ├── artwork/
│               │   └── DEFINITION.md
│               └── shape/
│                   └── DEFINITION.md
├── tests/
├── site-src/
└── docs/
```

The generic engine is intended to remain Model-independent.

Model-specific manufacturing policy belongs to the applicable Model package,
while reusable Model-independent mechanics may be implemented as shared
operations or infrastructure.

---

## Development

Development setup is documented in:

[`SETUP.md`](SETUP.md)

For a new checkout, the basic development setup is:

```bash
git clone https://github.com/lowkeylabs/lowkey-artifact-builder.git
cd lowkey-artifact-builder

uv sync
source .venv/bin/activate
pre-commit install

make check
```

The normal development cycle is:

```bash
make format
make check
```

Contribution guidelines, testing expectations, and pull-request practices are
documented in:

[`CONTRIBUTING.md`](CONTRIBUTING.md)

---

## Documentation

Project documentation is divided by responsibility.

| Document                                                                                  | Purpose                                                                                   |
| ----------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| [`README.md`](README.md)                                                                  | Project introduction, normal usage, and documentation entry point                         |
| [`ARCHITECTURE.md`](ARCHITECTURE.md)                                                      | Normative system-wide terminology, relationships, contracts, and architectural invariants |
| [Artwork `DEFINITION.md`](src/lowkey_artifact_builder/model/models/artwork/DEFINITION.md) | Normative semantics and invariants of the Artwork Model                                   |
| [Shape `DEFINITION.md`](src/lowkey_artifact_builder/model/models/shape/DEFINITION.md)     | Normative semantics and invariants of the Shape Model                                     |
| [`SETUP.md`](SETUP.md)                                                                    | Development environment and tool setup                                                    |
| [`CONTRIBUTING.md`](CONTRIBUTING.md)                                                      | Contribution, testing, and development practices                                          |
| [`prompts/`](prompts/)                                                                    | Reusable instructions and workflows for structured and LLM-assisted development           |
| [`CHANGEPLAN.md`](CHANGEPLAN.md)                                                          | Temporary, non-normative implementation plan for the current change                       |
| [`site-src/`](site-src/)                                                                  | Authoritative source material for the project website                                     |
| [`docs/`](docs/)                                                                          | Generated GitHub Pages output                                                             |

### Development Prompts

The [`prompts/`](prompts/) directory contains reusable instructions for
structured development work, including procedures for starting a new
development thread and following the project's test-driven development
process.

These prompts guide the development process. They do not define system or
Model semantics.

When evaluating intended behavior, the authority is:

```text
ARCHITECTURE.md
        │
        ├── artwork/DEFINITION.md
        └── shape/DEFINITION.md
```

`CHANGEPLAN.md` is derived from comparison of those permanent specifications
with the current repository. It is an implementation plan rather than a
normative specification.

Tests provide executable evidence of conformance but do not replace the
permanent specifications.

---

## Website

Project website source is maintained under:

```text
site-src/
```

Generated GitHub Pages content is written beneath:

```text
docs/
```

The generated site should not be treated as the authoritative source for
system architecture or Model semantics.

---

## Contributing

Contributions are welcome.

See [`CONTRIBUTING.md`](CONTRIBUTING.md) before submitting changes.

Architectural changes should be evaluated against `ARCHITECTURE.md`.
Model-specific semantic changes should be evaluated against and, when
appropriate, accompanied by changes to the applicable Model `DEFINITION.md`.

---

## License

`lowkey-artifact-builder` is licensed under the Apache License, Version 2.0.

See:

* [`LICENSE`](LICENSE)
* [`NOTICE`](NOTICE)
* [`COPYRIGHT`](COPYRIGHT)

for details.

Commercial licensing and related information, when applicable, is documented
in [`COMMERCIAL.md`](COMMERCIAL.md).

---

## Citation

Citation metadata for the project is provided in:

[`CITATION.cff`](CITATION.cff)

---

## About

`lowkey-artifact-builder` is developed by **lowkeylabs**.

The project explores reproducible, dependency-driven workflows for converting
source artwork into reusable registered geometry and multicolor additive
manufacturing Products.
