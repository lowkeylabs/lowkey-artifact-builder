# Command-Line Interface

This document describes the `artifact` command-line interface from the

operator's perspective.

System terminology, relationships, and invariants are defined by

`ARCHITECTURE.md`. This document does not redefine them.

## Operator goal

The primary CLI workflow is simple:

> Get the desired 3MF to the printer as quickly and efficiently as

> possible.

The normal value chain is:

```text

customer image

      │

      ▼

artifact create

      │

      ▼

managed Artifact

      │

      ▼

artifact build

      │

      ▼

correct printable 3MF

      │

      ▼

slicer / share / upload / print
```

`create` and `build` define the ordinary manufacturing path. `show`,

`config`, `colors`, and `clean` support that path when inspection,

customization, color selection, or maintenance is needed. They should

not become mandatory ceremony before routine manufacturing.

## Working directory

The CLI operates on the current working directory as the project root.

A project may contain:

-   root-level PNG files awaiting intake;

-   `originals/`, containing preserved Artifact registrations and source

    artwork; and

-   `artifacts/`, containing materialized Artifact state and generated

    Products.

The operator should not need to create internal directories before using

the CLI. Missing collection directories normally represent empty

collections rather than errors.

Artifact registration and Artifact materialization are distinct. An

Artifact may be registered under `originals/` before

`artifacts/<artifact_id>/artifact.toml` exists.

## Presentation

The CLI presents information needed for operator decisions rather than

exposing implementation mechanics.

Where output is naturally structured as rows and columns, Rich tables

are appropriate for information such as:

-   Artifact inventories;

-   Realization manufacturing state;

-   color analysis and assignments;

-   configuration summaries; and

-   build or batch summaries.

Routine output should remain terse. A short success message, Product

path, warning, prompt, or actionable error should remain simple when a

table would add visual weight without helping the operator.

Operator-facing Product paths should be relative to the project root

when practical.

Reusable application operations remain independent of terminal

presentation. Rich tables, markup, and other presentation-specific

objects belong to the CLI layer.

## Semantic verbosity and diagnostic logging

Semantic manufacturing messages and Python diagnostic logging are

separate concerns.

Top-level semantic messaging options are:

```text

-v, --verbose

-vv, --very-verbose

--quiet
```

Default BUILD output reports the operator-relevant manufacturing result.

`--verbose` shows manufacturing progress, including Stage completion and

reuse. `--very-verbose` shows richer semantic execution diagnostics,

including Product-state information that explains execution and reuse

decisions. `--quiet` suppresses semantic messaging.

`--quiet`, `--verbose`, and `--very-verbose` are mutually exclusive.

Diagnostic logging is controlled independently with:

```text

--log-level=LEVEL
```

Supported logging levels are:

```text

TRACE

DEBUG

INFO

PROGRESS

SUCCESS

WARNING

ERROR

CRITICAL
```

`--log-level` controls Python diagnostic logging only. It may be

combined with any semantic messaging mode, including `--quiet`.

Semantic output should use operator terminology. For example, an engine

decision to skip execution because a current Product can be reused

should normally be presented to the operator as reuse rather than as an

implementation-level skip.

## Commands

### `artifact create`

Registers Artifact identity and ingests source artwork. CREATE does not

materialize Artifact workspaces or manufacture Products.

With no options:

```text

artifact create
```

CREATE inspects the intake state, including registered Artifacts and

root-level PNG sources available for ingestion.

To ingest one PNG using its filename stem as the Artifact ID:

```text

artifact create --source lilo.png
```

To assign the Artifact ID explicitly:

```text

artifact create --artifact-id baird-lilo --source lilo.png
```

To ingest all eligible root-level PNG sources:

```text

artifact create --all-sources
```

A source-less Artifact may be registered explicitly:

```text

artifact create --artifact-id blank-coaster
```

Successfully ingested source artwork is preserved under `originals/`

using the canonical Artifact identity. CREATE owns registration and

source ingestion; BUILD owns Artifact workspace materialization and

manufacturing.

### `artifact show`

SHOW answers progressively:

> What Artifacts exist in this project, and what is their manufacturing

> state?

> What can I manufacture from this Artifact, and what already exists?

> What is the manufacturing state of this specific Realization?

SHOW is read-only. It does not materialize missing work or modify

persistent Artifact state.

#### Workspace inventory

With no Artifact ID:

```text

artifact show
```

SHOW discovers registered Artifacts and presents a manufacturing

summary.

For each Artifact, the summary accounts for its effective Realizations

and their established manufacturing states, including current, stale,

and not built. Registered but unmaterialized Artifacts remain visible.

#### Artifact inspection

Given an Artifact:

```text

artifact show baird-lilo
```

SHOW presents the Artifact's effective built-in and custom Realizations,

their manufacturing state, and accessible manufacturing outputs.

The operator should be able to determine whether a desired 3MF can be

used immediately or whether additional work is required.

#### Realization inspection

A specific Realization may be selected:

```text

artifact show baird-lilo --realization shape_ornament
```

This narrows the same manufacturing inspection to one Realization.

SHOW describes manufacturing state and available Products. Effective

construction configuration and provenance belong to CONFIG.

### `artifact config`

CONFIG inspects and changes construction configuration for existing

Artifacts and Realizations.

For one Artifact:

```text

artifact config baird-lilo
```

CONFIG presents the authored Artifact configuration and effective

Realization catalog.

For one selected Realization:

```text

artifact config baird-lilo --realization shape_ornament
```

CONFIG presents the controlling Model construction parameters, their

effective values, and the source responsible for each value.

Provenance may include system, Model, Variant, workspace, derived,

Artifact, or Realization configuration. Provenance answers why an

effective value has its current value; it does not identify the normal

operator mutation target.

Normal operator parameter changes are persisted as sparse Realization

overrides in the Artifact's `artifact.toml`:

```text

artifact config baird-lilo --realization shape_ornament \\

    --parameters shape_size=200
```

The change does not modify an upstream system, workspace, Model, or

Variant source merely because that source supplied the previous

effective value.

CONFIG can also create an additional named Realization. The source

Variant is supplied explicitly through the parameter bindings:

```text

artifact config baird-lilo --realization large-ornament --create \\

    --parameters variant=shape.ornament \\

    --parameters shape_size=125
```

Realization configuration and creation may also be applied across all

existing Artifacts by omitting the Artifact ID:

```text

artifact config --realization shape_ornament \\

    --parameters shape_size=110
```

Bulk operations validate their applicable scope before mutation.

CONFIG is not a substitute for SHOW. CONFIG explains construction

configuration; SHOW describes manufacturing state and accessible

manufacturing Products.

### `artifact colors`

COLORS analyzes physical color requirements and manages operator

printer-color assignments.

Analyze an Artifact:

```text

artifact colors baird-lilo
```

Analyze a selected Realization:

```text

artifact colors baird-lilo --realization shape_ornament
```

Color analysis consumes existing manufacturing Products. It does not

execute BUILD stages to manufacture or refresh missing prerequisites.

When required manufacturing state is unavailable, BUILD remains

responsible for creating it.

COLORS also supports explicit recoloring operations:

```text

artifact colors baird-lilo --recolor printer

artifact colors baird-lilo --recolor library

artifact colors baird-lilo --recolor reset

artifact colors baird-lilo --recolor reset-all-realizations
```

A selected Realization may be combined with recoloring modes where that

scope is meaningful:

```text

artifact colors baird-lilo --realization shape_ornament --recolor printer
```

Recoloring persists printer-color configuration at the selected Artifact

or Realization scope and updates applicable existing final 3MF color

assignments without manufacturing missing geometry. Recoloring therefore

requires the existing manufacturing Products needed by the operation.

`reset` removes the selected `printer_colors` override so normal

configuration inheritance resumes. `reset-all-realizations` removes

Realization-specific `printer_colors` overrides in the selected Artifact

scope and cannot be combined with `--realization`.

Catalog colors are advisory and are not a recoloring target.

Color analysis and recoloring are support operations. They are not

mandatory steps before every build or print.

### `artifact build`

BUILD makes requested manufacturing Products current using

dependency-driven incremental execution.

Bare BUILD is a read-only project-status operation:

```text

artifact build
```

To build one selected Realization:

```text

artifact build baird-lilo --realization shape_ornament
```

Without `--realization`, explicitly selected Artifacts are built across

their effective Realizations:

```text

artifact build baird-lilo
```

To incrementally build every effective Realization of every project

Artifact:

```text

artifact build --build-all
```

Already-current Products are reused. BUILD executes only work required

to make the requested manufacturing Products current.

To clean and rebuild one selected Artifact Realization:

```text

artifact build baird-lilo --realization shape_ornament --rebuild
```

To clean and rebuild every effective Realization of every project

Artifact:

```text

artifact build --rebuild-all
```

`--dry-run` displays normal build planning without performing

manufacturing work.

From the operator's perspective, the important BUILD result is a current

manufacturing Product, normally a 3MF, ready for downstream use.

#### Independent Stage execution

BUILD also exposes an advanced developer capability for executing

exactly one declared Stage independently:

```text

artifact build baird-lilo --stage vector
```

A Realization may be selected when needed:

```text

artifact build baird-lilo --stage vector --realization artwork_default
```

Independent Stage execution may bind declared inputs, parameters, and

outputs explicitly:

```text

artifact build baird-lilo --stage vector \\

    --input raster.manifest=external/raster.json \\

    --parameter artwork_size=90 \\

    --output manifest=external/vector.json
```

`--input`, `--parameter`, and `--output` belong only to independent

Stage execution. Independent Stage execution accepts exactly one

Artifact and is separate from normal dependency-driven Artifact

manufacturing.

This capability is intended for development, diagnostics, and

exceptional low-level execution. It is not part of the ordinary

source-to-3MF workflow.

### `artifact clean`

CLEAN removes generated Products while preserving persistent Artifact

configuration and Artifact-owned inputs.

Clean generated Products for one Artifact:

```text

artifact clean baird-lilo
```

Clean one Realization of one Artifact:

```text

artifact clean baird-lilo --realization shape_ornament
```

Clean one Realization across all existing Artifacts:

```text

artifact clean --realization shape_ornament
```

With no Artifact ID or Realization, CLEAN targets all existing Artifacts

and asks for confirmation:

```text

artifact clean
```

For unattended project-wide cleaning:

```text

artifact clean --force
```

Cleaning is a maintenance operation rather than part of the normal path

from source image to printable 3MF.

## Scope

Commands operating on existing Artifacts use the narrowest scope

appropriate to their purpose.

Common scope patterns include:

```text

COMMAND

    project-wide or discovery scope, where supported

COMMAND baird-lilo

    Artifact baird-lilo

COMMAND --realization shape_ornament

    that Realization across applicable Artifacts, where supported

COMMAND baird-lilo --realization shape_ornament

    that Realization of baird-lilo
```

Individual commands support only the scopes meaningful to their

operation. Omitting an Artifact ID does not universally mean "all

Artifacts"; for example, bare BUILD reports project status rather than

requesting project-wide manufacturing. Explicit project-wide BUILD

execution uses `--build-all` or `--rebuild-all`.

## Empty projects and errors

Broad discovery over an empty project is normally successful. For

example:

```text

artifact show
```

may report that no Artifacts exist without producing an error or

traceback.

Missing collection directories alone should not produce tracebacks.

An explicitly requested Artifact or Realization that does not exist is

an operator error and should produce a concise CLI error. Malformed or

inconsistent persistent Artifact state is also an error and should be

reported clearly rather than silently treated as an empty project.

Expected operator, configuration, planning, and manufacturing errors

should cross the CLI boundary as concise actionable messages without

Python tracebacks. Unexpected invariant or programming failures should

not be indiscriminately converted into ordinary operator errors.

## Common workflows

### New customer image

For a specific incoming image:

```text

artifact create --artifact-id baird-lilo --source lilo.png

artifact show baird-lilo

artifact build baird-lilo --realization shape_ornament
```

If the desired Realization is already known, SHOW is optional; CREATE

followed directly by BUILD is the normal short manufacturing path.

For a batch of root-level PNGs:

```text

artifact create --all-sources

artifact show

artifact build --build-all
```

### Two-sided Coin

A Coin combines two complete packaged Shape Products as opposite Faces
of one printable object. The Face dependencies are persistent Artifact
configuration rather than ordinary Coin parameters.

For example, a Coin Artifact may bind its Faces in `artifact.toml`:

```toml
model = "coin"

[product_dependencies.faceA]
artifact = "front"
model = "shape"
realization = "shape_default"
stage = "package"
product = "artifact"

[product_dependencies.faceB]
artifact = "back"
model = "shape"
realization = "shape_default"
stage = "package"
product = "artifact"
```

`faceA` and `faceB` are independent Product dependencies. They may refer
to the same packaged Shape Product, different Shape Realizations of one
Artifact, or packaged Shape Products from different Artifacts.

Face B must be a Shape whose resolved raise style is `inlaid`. Coin
validates that requirement from the packaged Shape Product.

Coin orientation is controlled by the `coin_orientation` parameter:

-   `aligned` is the default. When each outward Face is viewed directly,
    the semantic tops of Face A and Face B appear at the same physical
    end.
-   `inverted` places Face B's semantic top opposite Face A.

When the default `aligned` orientation is appropriate, no Coin parameter
override is required. To select `inverted`:

```text
artifact config coin-example --realization coin_default \
    --parameters coin_orientation=inverted
```

Build the Coin through the ordinary dependency-driven workflow:

```text
artifact build coin-example --realization coin_default
```

The operator does not need to build Face A and Face B manually first.
BUILD realizes missing or stale packaged Shape dependencies as required,
reuses current dependency Products, composes the two Faces, and produces
the Coin 3MF.

The current CONFIG command edits Realization parameters such as
`coin_orientation`; it does not author `product_dependencies`. Face
bindings are therefore configured in the Coin Artifact's
`artifact.toml`.

### Existing current Realization

```text

artifact show baird-lilo

        │

        ▼

shape_ornament is current

        │

        ▼

use the existing shape_ornament.3mf
```

No build or additional inspection is necessary.

### Missing or stale Realization

```text

artifact show baird-lilo

        │

        ▼

shape_ornament is stale or not built

        │

        ▼

artifact build baird-lilo --realization shape_ornament

        │

        ▼

use the resulting shape_ornament.3mf
```

### Configuration exception

Inspect the effective construction configuration:

```text

artifact config baird-lilo --realization shape_ornament
```

Apply only the required sparse override:

```text

artifact config baird-lilo --realization shape_ornament \\

    --parameters shape_size=110
```

Then build the affected Realization:

```text

artifact build baird-lilo --realization shape_ornament
```

Dependency-driven execution determines which manufacturing work must

actually be repeated.

### Color exception

Inspect the relevant physical color state:

```text

artifact colors baird-lilo --realization shape_ornament
```

If an operator color assignment is required:

```text

artifact colors baird-lilo --realization shape_ornament --recolor printer
```

COLORS does not manufacture missing geometry. If required manufacturing

Products do not yet exist or are not usable for the requested color

operation, BUILD must bring them current.

### Regenerate selected generated work

Clean only the affected Realization:

```text

artifact clean baird-lilo --realization shape_ornament
```

Then rebuild it:

```text

artifact build baird-lilo --realization shape_ornament
```

BUILD regenerates the required dependency-driven work and produces the

current final 3MF.

## Guiding principle

Commands are not independent utilities. Together they support the

shortest practical path from incoming artwork to a usable manufacturing

Product.

When designing or changing the CLI, prefer workflows that let the

operator:

1.  register incoming artwork with minimal ceremony;

2.  discover effective Realizations and their manufacturing state when

    needed;

3.  reuse an existing current 3MF whenever possible;

4.  make only necessary configuration or color decisions;

5.  build only missing or stale work; and

6.  retrieve the resulting 3MF for slicing, sharing, uploading, or

    printing.

The ordinary path should remain:

```text

artifact create

      ↓

artifact build

      ↓

printable 3MF
```

Inspection, customization, developer Stage execution, and maintenance

remain available when they answer a specific operator or developer need.

