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

``` text

customer image

      │

      ▼

identify / create Artifact

      │

      ▼

select Realization

      │

      ▼

verify readiness

      │

      ▼

build if necessary

      │

      ▼

3MF

      │

      ▼

slicer / share / upload / print
```

Inspection and configuration commands support this workflow. They should

not create unnecessary steps when a suitable current 3MF already exists.

## Working directory

The CLI operates on the current working directory.

A working directory may contain:

-   incoming source images;

-   `originals/`, containing preserved Artifact sources; and

-   `artifacts/`, containing managed Artifact state and generated
    Products.

The operator should not need to create internal directories before using

the CLI. Missing storage directories are normally equivalent to empty

collections, not exceptional conditions.

## Presentation

The CLI should present information for operator decisions rather than
expose

internal implementation activity.

Where output is naturally structured as rows and columns, prefer the
Python

`rich` package for terminal presentation.

Use Rich tables for content such as:

-   Artifact lists;

-   Realization lists and manufacturing state;

-   color analysis and assignments;

-   configuration summaries where values are naturally tabular;

-   build or batch summaries; and

-   other repeated structured records.

Tables should normally include concise column headers that identify the

operator-relevant meaning of each value.

For example:

``` text

Realization          Type       State       3MF

artwork_default      built-in   current     artwork_default.3mf

shape_default        built-in   not built   —

shape_ornament       built-in   current     shape_ornament.3mf

large-ornament       custom     stale       large-ornament.3mf
```

Prefer Rich's semantic formatting capabilities over manually aligning
columns,

drawing separators, or embedding terminal escape sequences in
application

logic.

Rich presentation remains a UI concern. Reusable application operations
should

return structured information or semantic events rather than Rich
tables,

renderables, terminal markup, or presentation-specific strings.

Do not force naturally simple output into a table. A short success
message,

single path, warning, prompt, or actionable error should remain simple
when a

table would add visual weight without helping the operator.

Routine output should remain terse. Rich is used to improve readability
and

operator comprehension, not to increase the amount of information
displayed.

## CLI semantic verbosity and logging

Before continuing the Artwork planning/reuse investigation, clean up
BUILD

observation so subsequent manufacturing work is easier to inspect.

Keep semantic execution messaging independent from Python logging.

### Semantic messaging

-   Default BUILD output reports only Artifact/Realization completion
    and the

  resulting manufacturing Product.

-   Display operator-facing paths relative to the project root when
    possible.

-   `-v`, `--verbose` shows manufacturing progress, including Stage
    completion

  and reuse.

-   `-vv`, `--very-verbose` shows richer semantic diagnostics, including
    the

  Product-state information explaining execution/reuse decisions.

-   `--quiet` suppresses semantic messaging, including normal completion
    output.

-   Quiet, verbose, and very-verbose are mutually exclusive.

-   Keep the internal verbosity representation extensible; do not
    unnecessarily

  constrain future verbosity levels.

Semantic messaging should be derived from structured execution events
rather

than Python log messages. Prefer operator terminology such as `reused`
where

the underlying engine event is `stage.skipped` because an existing
Product is

current.

### Diagnostic logging

-   Add top-level `--log-level=LEVEL`.

-   Support the levels already recognized by `logging_config.py`.

-   `--log-level` controls Python diagnostic logging only.

-   `-v`, `-vv`, and `--quiet` do not alter the configured Python log
    level.

-   `--log-level` may therefore be combined with any semantic messaging
    mode,

  including `--quiet`.

Implement this as a small TDD slice using the existing semantic
execution-event

channel. Do not change engine execution behavior as part of this work.

## Commands

### `artifact create`

Registers incoming source material as a managed Artifact.

The operator assigns the `artifact_id` during creation.

``` text

artifact create baird-lilo --source lilo.png
```

Without an explicit source, `create` may discover source images in the

working directory for ingestion.

`create` owns source ingestion and Artifact identity. It does not need
to

build manufacturing Products.

### `artifact show`

Answers progressively:

> What Artifacts exist in this workspace, and what is their
> manufacturing state?

> What can I manufacture from this Artifact, and what already exists?

> What is the manufacturing state of this specific Realization?

#### Workspace inventory

With no Artifact ID:

``` text
artifact show
```

`show` discovers Artifact identities from the workspace and presents a
manufacturing summary.

Artifact identity may be established by preserved registration under
`./originals/` or by a stable `./artifacts/<artifact_id>/` workspace
directory.

For each discovered Artifact, the summary should make it possible to
determine:

-   whether the Artifact is materialized;
-   how many effective Realizations are defined for the Artifact; and
-   how those Realizations are distributed across the established
    manufacturing   states, such as current, stale, and not built.

An Artifact is materialized when
`./artifacts/<artifact_id>/artifact.toml` exists. The existence of the
Artifact directory alone does not imply materialization, and
materialization does not imply that any Realization or Product is
current.

An unmaterialized Artifact remains visible. Its effective Realizations
are still part of the inventory and have manufacturing status
independently of Artifact materialization.

Workspace `show` uses the same manufacturing-state semantics as focused
Artifact inspection. Every effective Realization should be accounted for
by the reported state summary; `show` does not introduce a separate
workspace-level manufacturing-state model.

The exact terminal columns and layout are presentation decisions and may
evolve as the implementation is refined.

#### Artifact inspection

Given an Artifact:

``` text
artifact show baird-lilo
```

`show` presents its available canonical and custom Realizations, their
useful manufacturing state, and available manufacturing outputs.

The operator should be able to determine whether a desired manufacturing
Product can be used immediately or whether additional work is required.

Operator-facing Product paths should be useful relative paths rather
than unnecessarily long absolute filesystem paths.

#### Realization inspection

A specific Realization may be selected:

``` text
artifact show baird-lilo --realization shape_ornament
```

This presents the same manufacturing information narrowed to that
Realization.

`show` does not display effective construction configuration merely
because a Realization is selected. Effective configuration, provenance,
and operator customization belong to `config`.

Across all three scopes, `show` is an inspection operation. It does not
materialize missing work or modify persistent Artifact state.

### `artifact config`

Answers:

> What parameters control construction of this Realization, what values
> are effective, and where did those values come from?

`config` is the operator-facing surface for inspecting and changing
construction configuration.

For a selected Realization, `config` should expose the controlling Model
parameters that affect construction, their effective values, and the
configuration source responsible for each value. This supports both
routine configuration and power-user debugging of the effective
resolution chain.

Configuration source and operator mutation target are distinct concepts.
Reported provenance may include system, Model, Variant, workspace,
derived, Artifact, or Realization configuration. Reporting an upstream
source does not imply that the operator should modify that source.

Normal operator parameter changes are persisted as sparse Realization
overrides in the Artifact's `artifact.toml`. System, workspace, Model,
and Variant configuration are not the normal operator mutation surface.

For example, inspection of a selected Realization should make
information of this form available:

``` text
Parameter                    Value        Source
shape_size                   100          model
shape_outer_ridge_width      2            variant 'ornament'
shape_loop_raise             2            derived
shape_base_color             white        artifact
```

The exact terminal layout is a presentation decision and may evolve. The
important contract is that the operator can discover the construction
parameters, inspect their effective values, and understand their
provenance.

Parameter changes may be made through `config` without requiring the
operator to edit `artifact.toml` directly. The Artifact and Realization
are selected explicitly. For example:

``` text
artifact config baird-lilo --realization shape_ornament \
    --parameters shape_size=200
```

A parameter change creates or updates a sparse override for the selected
Realization in the Artifact's `artifact.toml`. It does not modify whichever
upstream source supplied the previous effective value merely because that
source appears in provenance.

`config` is not a substitute for `show`. `config` explains the
construction configuration that determines a Realization; `show`
describes manufacturing state and available manufacturing Products.

Configuration inspection is normally needed only when the operator wants
to understand, debug, or change construction configuration.

### `artifact colors`

Answers:

> What colors are available or configured for printing?

`colors` owns color-assignment analysis and operator color selection.

``` text

artifact colors baird-lilo --realization shape_ornament
```

Color changes are explicit:

``` text

--recolor=printer

--recolor=library

--recolor=reset

--recolor=reset-all-realizations
```

Catalog colors are advisory and are not a recoloring target.

Color analysis should be used when color selection requires operator

attention; it should not be a mandatory step before every build or
print.

### `artifact build`

Answers:

> What work is necessary to make the requested manufacturing Product
> current?

Build should execute only the work required by the requested scope.

``` text

artifact build baird-lilo --realization shape_ornament
```

Already-current Products should be reused.

From the operator's perspective, the important result is a current

manufacturing Product, normally a 3MF, ready for downstream use.

### `artifact clean`

Removes generated state according to the selected scope.

Cleaning is a maintenance operation rather than part of the normal path

from source image to printer.

## Scope

Commands operating on existing Artifacts should use a consistent scope

vocabulary where applicable:

``` text

COMMAND

    all applicable Artifacts

COMMAND baird-lilo

    Artifact baird-lilo

COMMAND --realization shape_ornament

    that Realization across applicable Artifacts

COMMAND baird-lilo --realization shape_ornament

    that Realization of baird-lilo
```

Individual commands may support only the scopes meaningful to their

operation.

## Empty workspaces and errors

Broad discovery over an empty workspace is normally successful:

``` text

artifact show
No artifacts found.
```

Missing directories alone should not produce tracebacks.

An explicitly requested object that does not exist is an operator error:

``` text

artifact show baird-lilo

Error: Artifact 'baird-lilo' does not exist.
```

Likewise, requesting an unavailable Realization should produce a concise

CLI error.

Malformed or inconsistent persistent Artifact state is also an error and

should be reported clearly rather than silently treated as an empty

workspace.

Expected operator and configuration errors should not expose Python

tracebacks.

## Common workflows

### New customer image

``` text

artifact show
artifact create baird-lilo --source lilo.png

artifact show baird-lilo
```

The operator can then select the appropriate Realization and build it if

necessary.

### Existing current Realization

``` text

artifact show baird-lilo

        │

        ▼

shape_ornament is current

        │

        ▼

use shape_ornament.3mf
```

No build or additional inspection is necessary.

### Missing or stale Realization

``` text

artifact show baird-lilo

        │

        ▼

shape_ornament is missing/stale

        │

        ▼

artifact build baird-lilo --realization shape_ornament

        │

        ▼

use shape_ornament.3mf
```

### Realization needs operator attention

``` text

artifact show baird-lilo

        │

        ├── configuration question

        │       └── artifact config ...

        │

        └── color question

                └── artifact colors ...
```

After any required adjustment, build only what is necessary and use the

resulting 3MF.

## Guiding principle

Commands are not independent utilities. Together they support the
shortest

practical path from incoming artwork to a usable manufacturing Product.

When designing or changing the CLI, prefer workflows that let the
operator:

1.  find the Artifact quickly;

2.  see available Realizations and their state;

3.  identify an existing usable 3MF;

4.  make only necessary configuration or color decisions;

5.  build only missing or stale work; and

6.  retrieve the resulting 3MF for slicing, sharing, uploading, or
    printing.
