# Command-Line Interface

This document describes the `artifact` command-line interface from the
operator's perspective.

System terminology, relationships, and invariants are defined by
`ARCHITECTURE.md`. This document does not redefine them.

## Operator goal

The primary CLI workflow is simple:

> Get the desired 3MF to the printer as quickly and efficiently as possible.

The normal value chain is:

```text
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

- incoming source images;
- `originals/`, containing preserved Artifact sources; and
- `artifacts/`, containing managed Artifact state and generated Products.

The operator should not need to create internal directories before using
the CLI. Missing storage directories are normally equivalent to empty
collections, not exceptional conditions.

## Presentation

The CLI should present information for operator decisions rather than expose
internal implementation activity.

Where output is naturally structured as rows and columns, prefer the Python
`rich` package for terminal presentation.

Use Rich tables for content such as:

- Artifact lists;
- Realization lists and manufacturing state;
- color analysis and assignments;
- configuration summaries where values are naturally tabular;
- build or batch summaries; and
- other repeated structured records.

Tables should normally include concise column headers that identify the
operator-relevant meaning of each value.

For example:

```text
Realization          Type       State       3MF
artwork_default      built-in   current     artwork_default.3mf
shape_default        built-in   not built   —
shape_ornament       built-in   current     shape_ornament.3mf
large-ornament       custom     stale       large-ornament.3mf
```

Prefer Rich's semantic formatting capabilities over manually aligning columns,
drawing separators, or embedding terminal escape sequences in application
logic.

Rich presentation remains a UI concern. Reusable application operations should
return structured information or semantic events rather than Rich tables,
renderables, terminal markup, or presentation-specific strings.

Do not force naturally simple output into a table. A short success message,
single path, warning, prompt, or actionable error should remain simple when a
table would add visual weight without helping the operator.

Routine output should remain terse. Rich is used to improve readability and
operator comprehension, not to increase the amount of information displayed.


## CLI semantic verbosity and logging

Before continuing the Artwork planning/reuse investigation, clean up BUILD
observation so subsequent manufacturing work is easier to inspect.

Keep semantic execution messaging independent from Python logging.

### Semantic messaging

- Default BUILD output reports only Artifact/Realization completion and the
  resulting manufacturing Product.
- Display operator-facing paths relative to the project root when possible.
- `-v`, `--verbose` shows manufacturing progress, including Stage completion
  and reuse.
- `-vv`, `--very-verbose` shows richer semantic diagnostics, including the
  Product-state information explaining execution/reuse decisions.
- `--quiet` suppresses semantic messaging, including normal completion output.
- Quiet, verbose, and very-verbose are mutually exclusive.
- Keep the internal verbosity representation extensible; do not unnecessarily
  constrain future verbosity levels.

Semantic messaging should be derived from structured execution events rather
than Python log messages. Prefer operator terminology such as `reused` where
the underlying engine event is `stage.skipped` because an existing Product is
current.

### Diagnostic logging

- Add top-level `--log-level=LEVEL`.
- Support the levels already recognized by `logging_config.py`.
- `--log-level` controls Python diagnostic logging only.
- `-v`, `-vv`, and `--quiet` do not alter the configured Python log level.
- `--log-level` may therefore be combined with any semantic messaging mode,
  including `--quiet`.

Implement this as a small TDD slice using the existing semantic execution-event
channel. Do not change engine execution behavior as part of this work.


## Commands

### `artifact create`

Registers incoming source material as a managed Artifact.

The operator assigns the `artifact_id` during creation.

```text
artifact create baird-lilo --source lilo.png
```

Without an explicit source, `create` may discover source images in the
working directory for ingestion.

`create` owns source ingestion and Artifact identity. It does not need to
build manufacturing Products.

### `artifact list`

Answers:

> What managed Artifacts do I have?

This is useful before `create` when choosing an Artifact ID or determining
whether incoming artwork has already been registered.

```text
artifact list
```

Listing is discovery, not detailed inspection.

### `artifact show`

Answers:

> What can I manufacture from this Artifact, and what already exists?

Given an Artifact, `show` should present its available canonical and custom
Realizations, their useful build state, and available manufacturing
outputs.

```text
artifact show baird-lilo
```

Conceptually, and preferably rendered as a `rich` table:

```text
Realization          Type       State       3MF
artwork_default      built-in   current     artwork_default.3mf
shape_default        built-in   not built   —
shape_ornament       built-in   current     shape_ornament.3mf
large-ornament       custom     stale       large-ornament.3mf
```

A specific Realization may be inspected more closely:

```text
artifact show baird-lilo --realization shape_ornament
```

The operator should be able to tell whether the desired manufacturing
output can be used immediately or requires additional work.

### `artifact config`

Answers:

> What have I explicitly configured?

`config` displays or manages authored Artifact and Realization
configuration.

It is not a substitute for `show`: `config` describes operator-authored
configuration, while `show` describes the effective object the operator
can manufacture.

Configuration inspection is normally needed only when the operator wants
to understand or change customization.

### `artifact colors`

Answers:

> What colors are available or configured for printing?

`colors` owns color-assignment analysis and operator color selection.

```text
artifact colors baird-lilo --realization shape_ornament
```

Color changes are explicit:

```text
--recolor=printer
--recolor=library
--recolor=reset
--recolor=reset-all-realizations
```

Catalog colors are advisory and are not a recoloring target.

Color analysis should be used when color selection requires operator
attention; it should not be a mandatory step before every build or print.

### `artifact build`

Answers:

> What work is necessary to make the requested manufacturing Product current?

Build should execute only the work required by the requested scope.

```text
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

```text
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

```text
artifact list
No artifacts found.
```

Missing directories alone should not produce tracebacks.

An explicitly requested object that does not exist is an operator error:

```text
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

```text
artifact list

artifact create baird-lilo --source lilo.png

artifact show baird-lilo
```

The operator can then select the appropriate Realization and build it if
necessary.

### Existing current Realization

```text
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

```text
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

```text
artifact show baird-lilo
        │
        ├── configuration question
        │       └── artifact config ...
        │
        └── color question
                └── artifact colors ...
```

After any required adjustment, build only what is necessary and use the
resulting 3MF.

## Guiding principle

Commands are not independent utilities. Together they support the shortest
practical path from incoming artwork to a usable manufacturing Product.

When designing or changing the CLI, prefer workflows that let the operator:

1. find the Artifact quickly;
2. see available Realizations and their state;
3. identify an existing usable 3MF;
4. make only necessary configuration or color decisions;
5. build only missing or stale work; and
6. retrieve the resulting 3MF for slicing, sharing, uploading, or printing.
