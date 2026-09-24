# CHANGEPLAN

## Purpose

This change plan streamlines the user-facing workflow of

`lowkey-artifact-builder` around the common production path:

``` text

raw PNGs

    ↓

create

    ↓

Artifacts

    ↓

build

    ↓

3MF Products

    ↓

colors

    ↓

operator-ready 3MFs

    ↓

PrusaSlicer / printer
```

The CLI should optimize this common case while preserving the

architectural distinction between Models, Variants, Artifacts,

Realizations, Stages, and Products.

The central CLI principle is:

> Users normally address Artifacts and Realizations. Variants provide

> Model-owned reusable configuration from which Realizations are

> derived.

Configuration is therefore exceptional in the ordinary production

workflow. Canonical Realizations permit a newly created Artifact to use

every registered Model Variant without requiring Artifact-specific

configuration.

The intended routine batch workflow is:

``` text

artifact create

artifact build

artifact build --build-all

artifact colors
```

`artifact colors` is the single user-facing color operation. Without

`--recolor`, it is read-only analysis. With `--recolor`, it explicitly

applies an operator-selected physical-color assignment to existing final

3MFs.

Artifact-specific configuration is required only when a canonical

Realization must be customized, an additional named Realization must be

defined, or an operator intentionally persists a color selection.

------------------------------------------------------------------------

# Development Method

This plan is subordinate to:

``` text

ARCHITECTURE.md

src/lowkey_artifact_builder/model/models/<model>/DEFINITION.md

prompts/NEW_THREAD.md

prompts/TEST_DRIVEN_DEVELOPMENT.md
```

The permanent specifications define intended behavior. Repository HEAD

defines the current implementation. This file describes a route between

them.

At the beginning of each development thread and before selecting each

new TDD slice:

1.  review the permanent specifications relevant to the work;

2.  review `prompts/TEST_DRIVEN_DEVELOPMENT.md`;

3.  review current repository HEAD;

4.  review existing tests;

5.  determine which work described here HEAD already satisfies;

6.  identify meaningful discrepancies rather than silently resolving

    them;

7.  select the next coherent unmet behavioral slice.

Phase and subsection ordering in this document does not override that

process. Work listed here must not be repeated merely because it remains

listed. Credit behavior already satisfied by HEAD and proceed to the

next unmet requirement.

Each behavioral change follows:

``` text

resolve semantics

    ↓

write coherent tests

    ↓

observe RED

    ↓

evaluate failures

    ↓

implement

    ↓

focused tests

    ↓

complete quality suite

    ↓

commit

    ↓

reevaluate HEAD
```

CLI tests should protect user intent, option interpretation, useful

errors, and translation into application operations. They should not

duplicate engine, configuration, color-assignment, or Model semantics

already protected at a lower level.

Each phase below is intended to leave the application in a coherent and

usable state. A phase may contain multiple independently committed TDD

slices.

------------------------------------------------------------------------

# Cross-Phase CLI Semantics

## Realizations are the execution coordinate

Normal CLI execution addresses:

``` text

Artifact + Realization
```

not:

``` text

Artifact + Variant
```

A Variant is a Model-owned reusable configuration.

A Realization is the application of that Variant to an Artifact,

optionally with Artifact-specific customization.

Multiple Realizations may originate from the same Variant, so Variant

identity is not a sufficient general execution coordinate.

Normal user-facing build, inspection, cleaning, and color operations

should therefore use Realization names where Realization-specific scope

is requested.

## Canonical Realizations require no Artifact configuration

Every registered Model Variant supplies a canonical Realization to every

Artifact according to the architecture.

Examples include:

``` text

artwork.default  -> artwork_default

shape.default    -> shape_default

shape.ornament   -> shape_ornament
```

A newly created Artifact therefore does not need to declare those

Realizations in `artifact.toml`.

Artifact configuration should contain only source metadata and actual

Artifact-specific customization.

## Scope convention

Where applicable, commands use the same scope convention:

``` text

<command>

    all applicable Artifacts

<command> dog

    Artifact dog

<command> --realization shape_ornament

    that Realization across applicable Artifacts

<command> dog --realization shape_ornament

    that Realization of dog
```

Commands must define sensible behavior when a requested Realization is

not available for one or more selected Artifacts rather than silently

changing the meaning of the request.

For color mutation, scope determines exactly where `printer_colors` is

mutated.

Without `--realization`, recoloring mutates only Artifact-level

`printer_colors`:

``` text

artifact colors dog --recolor=library

    persist Artifact-level printer_colors

    do not modify Realization-specific printer_colors

    update applicable final Realization 3MFs according to each

    Realization's effective resolved printer_colors
```

With --realization, recoloring mutates only that Realization's

printer_colors:

``` text

artifact colors dog --realization shape_ornament --recolor=library

    persist Realization-specific printer_colors

    update only dog/shape_ornament
```

Normal configuration precedence remains authoritative.

An Artifact-level recolor must not erase or replace Realization-specific

printer_colors. A Realization-specific override therefore continues to
win

over the newly selected Artifact-level palette.

When an Artifact-level recolor encounters a Realization-specific

printer_colors override, report that the Realization retains its
explicit

override so the operator understands why that Realization was not
changed to

the newly selected Artifact palette.

## Project-owned paths

Artifact-owned managed inputs may be referenced from Artifact

configuration using paths relative to the project root.

Such paths are resolved relative to the project root, not the process

working directory and not the directory containing `artifact.toml`.

For example:

``` toml

source = "artifacts/dog/artifact.png"

original = "originals/dog.png"
```

These are persistent references to Artifact-owned source resources.

Generated Model, Stage, and Product filesystem paths must not be

persisted in Artifact configuration.

The distinction is:

``` text

Artifact-owned managed input

    persistent source/configuration resource

    may be referenced by project-relative path

generated Model/Stage Product

    materialization of the build graph

    must not be persisted as Artifact configuration
```

The filesystem may materialize generated Products, but Artifact

configuration must continue to address manufacturing behavior through

logical configuration and Product identity rather than generated paths.

------------------------------------------------------------------------

# Phase 1 - complete

------------------------------------------------------------------------

# Phase 2 --- Inspection

## Goal

At the end of Phase 2, the user can answer distinct questions without

confusing authored configuration, effective configuration, addressable

objects, and color analysis.

The commands are:

``` text

artifact list

artifact config

artifact show

artifact colors
```

Their responsibilities are intentionally distinct:

``` text

list

    What exists / what can I address?

config

    What have I explicitly configured?

show

    What configuration will actually be used?

colors

    What physical color assignments are available, why were they selected,

    and which assignment is currently configured for printing?
```

`colors` is already established in Phase 1 as both a read-only analysis

command and, only when `--recolor` is supplied, the explicit

color-selection mutation surface.

------------------------------------------------------------------------

## 2.1 List

Define:

``` text

artifact list
```

to list defined Artifact IDs.

Define:

``` text

artifact list dog
```

to list the effective Realizations addressable for `dog`, including

canonical Realizations and explicitly declared additional Realizations.

Listing should use the authoritative Realization catalog rather than

reconstructing it independently in CLI code.

`list` reports identity and availability, not complete configuration.

------------------------------------------------------------------------

## 2.2 Show

Make `show` Realization-oriented.

For example:

``` text

artifact show dog --realization shape_ornament
```

shows the fully resolved configuration that would actually be used for

that Realization.

It should resolve the Realization directly through configuration

semantics rather than detouring through Variant-oriented build planning

merely to obtain a resolver.

Resolved output may include useful provenance where that helps explain

whether a value came from:

-   Model defaults;

-   Variant overrides;

-   Workspace configuration;

-   Artifact configuration; or

-   Realization customization.

Do not make `show` synonymous with `config`.

------------------------------------------------------------------------

## 2.3 Colors integration

`artifact colors` owns color-assignment inspection and operator color

selection.

Do not reintroduce a separate `artifact recolor` command.

Inspection must continue to expose the established Artwork assignment

semantics and quantitative comparison established in Phase 1.

Mutation remains explicit through:

``` text

--recolor=printer

--recolor=library

--recolor=reset

--recolor=reset-all-realizations
```

Catalog remains advisory and cannot be selected for recoloring.

Model-owned structural printing colors are not Artifact color regions

and must not be silently included in Artwork's global one-to-one color

analysis, even though they should be represented appropriately in the

operator-facing component display.

------------------------------------------------------------------------

## 2.4 Remove misplaced inspection responsibilities

As the command responsibilities become established, remove or relocate

legacy CLI behavior that no longer belongs to its command.

In particular, Model catalog/workplan inspection currently attached to

Artifact configuration should not force `config` to serve two unrelated

purposes.

Before moving or deleting developer-oriented capabilities, determine

whether they remain useful and choose an explicit home for them rather

than silently discarding them.

------------------------------------------------------------------------

## Phase 2 completion criterion

Without editing files or invoking developer internals, a user can

determine:

-   which Artifacts exist;

-   which Realizations are available;

-   what Artifact-specific configuration was authored;

-   what effective configuration a Realization will use;

-   whether builds are current;

-   what System, Printer, Library, and Catalog color assignments are

    available;

-   why Artwork physical colors were selected; and

-   which printer palette is currently configured.

The production workflow established in Phase 1 remains unchanged.

------------------------------------------------------------------------

# Phase 3 --- CLI Consolidation and Production Polish

## Goal

Complete the transition from the historical CLI to the streamlined

Artifact/Realization-oriented workflow without retaining contradictory

command semantics.

This phase should contain no speculative new manufacturing capability.

It consolidates behavior already proven useful in the preceding phases.

------------------------------------------------------------------------

## 3.1 Retire obsolete normal-workflow syntax

Review remaining public options and remove or clearly isolate obsolete

Variant-oriented normal execution syntax such as:

``` text

--variant

--all-variants
```

where Realization-oriented equivalents now define the intended user

workflow.

Do not remove internal Model/Variant coordinates merely because they are

no longer ordinary CLI coordinates.

Variants remain architecturally essential configuration identities.

Remove or reject the obsolete standalone:

``` text

artifact recolor
```

command once `artifact colors --recolor=...` is established as the sole

public color-mutation surface.

------------------------------------------------------------------------

## 3.2 Developer and Stage operations

Review independent Stage execution and other developer-oriented

operations.

Preserve the architectural ability to execute a Stage through a complete

`StageContext`.

Do not force specialized Stage execution into the ordinary production

command semantics merely to reduce the number of top-level commands.

If developer operations require a separate command surface, make that

separation explicit.

------------------------------------------------------------------------

## 3.3 Output consistency

Make routine command output consistent around:

``` text

Artifact

Realization

state/action

Product where relevant
```

Avoid exposing implementation-oriented Model/Variant coordinates when

they do not help the user perform the requested operation.

Errors should identify the actionable Artifact/Realization scope that

failed.

Batch operations should summarize successful, skipped/current, and

failed work without obscuring the underlying error.

Color output should use consistent terminology for:

``` text

System

Printer

Library

Catalog
```

and clearly distinguish read-only analysis from a requested recolor

mutation.

------------------------------------------------------------------------

## 3.4 End-to-end production acceptance

Protect the final common workflow with a small number of meaningful

acceptance tests.

A representative workflow should establish that the user can:

``` text

place PNGs in intake

    ↓

artifact create

    ↓

artifact build

    ↓

inspect pending build state

    ↓

artifact build --build-all

    ↓

artifact colors

    ↓

optionally artifact colors --recolor=library

    ↓

obtain operator-ready final 3MF Products
```

A customization acceptance path should establish only the additional

behavior that matters:

``` text

create

    ↓

config one Realization

    ↓

build that Realization

    ↓

inspect colors

    ↓

optionally recolor that Realization through artifact colors
```

A reset acceptance path should establish that:

``` text

select library colors

    ↓

persist printer_colors at the selected scope

    ↓

recolor final 3MF

    ↓

--recolor=reset

    ↓

remove that scope's printer_colors override

    ↓

restore inherited effective printer assignment

    ↓

update final 3MF presentation
```

Do not duplicate detailed Model geometry, configuration resolution,

build graph, or color-assignment assertions already protected by focused

tests.

------------------------------------------------------------------------

## Phase 3 completion criterion

The normal user-facing CLI presents one coherent mental model:

``` text

create    ingest customer sources

build     inspect build state or make selected work current

config    author Artifact/Realization exceptions

clean     discard generated work

colors    inspect color assignments and explicitly select/reset

          operator-facing physical colors

list      discover addressable Artifacts and Realizations

show      inspect effective resolved configuration
```

Variants remain Model-owned reusable configuration.

Realizations remain the Artifact-scoped execution coordinate.

The common production workflow requires no manual configuration when

Model Variants and inherited color configuration already describe the

desired products.

------------------------------------------------------------------------

# Target Production Workflow

For a routine batch:

``` text

# Customer PNGs are placed in the project root.

artifact create

# See what the new intake or configuration changes require.

artifact build

# Bring the project current.

artifact build --build-all

# Inspect current and alternative physical color assignments.

artifact colors
```

When filament swaps from owned inventory are acceptable:

``` text

artifact colors --recolor=library
```

Each Artifact's Library assignment is computed independently before

mutation.

When one Artifact should pin the system/default printer palette:

``` text

artifact colors smith-dog --recolor=printer
```

When one Artifact should select its best owned-library colors for all

applicable Realizations:

``` text

artifact colors smith-dog --recolor=library
```

When only one Realization requires a color exception:

``` text

artifact colors smith-dog \\

    --realization shape_ornament \\

    --recolor=library
```

When that color exception should be removed:

``` text

artifact colors smith-dog \\

    --realization shape_ornament \\

    --recolor=reset
```

When all Realization-specific color exceptions for one Artifact should
be removed while retaining its Artifact-level printer palette:

``` text
artifact colors smith-dog --recolor=reset-all-realizations
```

Inspection and maintenance remain available without complicating the

ordinary path:

``` text

artifact list

artifact list smith-dog

artifact config smith-dog --realization shape_ornament

artifact show smith-dog --realization shape_ornament

artifact colors smith-dog

artifact colors smith-dog --realization shape_ornament

artifact clean smith-dog --realization shape_ornament
```

The desired steady-state workflow is therefore:

``` text

create → build → colors → print
```

with:

``` text

config

clean

list

show
```

used when the ordinary path requires customization, maintenance, or

broader configuration explanation.

`colors` remains part of the ordinary production path because it

provides both the operator's color comparison and the explicit, optional

recolor selection.
