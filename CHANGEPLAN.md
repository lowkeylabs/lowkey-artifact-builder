# CHANGEPLAN

## Purpose

This change plan streamlines the user-facing workflow of
`lowkey-artifact-builder` around the common production path:

```text
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
recolor
    ↓
operator-ready 3MFs
    ↓
PrusaSlicer / printer
```

The CLI should optimize this common case while preserving the architectural
distinction between Models, Variants, Artifacts, Realizations, Stages, and
Products.

The central CLI principle is:

> Users normally address Artifacts and Realizations. Variants provide
> Model-owned reusable configuration from which Realizations are derived.

Configuration is therefore exceptional in the ordinary production workflow.
Canonical Realizations permit a newly created Artifact to use every registered
Model Variant without requiring Artifact-specific configuration.

The intended routine batch workflow is:

```text
artifact create
artifact build
artifact build --build-all
# artifact recolor --colors printer
```

Artifact-specific configuration is required only when a canonical Realization
must be customized or an additional named Realization must be defined.

---

# Development Method

This plan is subordinate to:

```text
ARCHITECTURE.md
src/lowkey_artifact_builder/model/models/<model>/DEFINITION.md
prompts/NEW_THREAD.md
prompts/TEST_DRIVEN_DEVELOPMENT.md
```

The permanent specifications define intended behavior. Repository HEAD defines
the current implementation. This file describes a route between them.

At the beginning of each development thread and before selecting each new TDD
slice:

1. review the permanent specifications relevant to the work;
2. review `prompts/TEST_DRIVEN_DEVELOPMENT.md`;
3. review current repository HEAD;
4. review existing tests;
5. determine which work described here HEAD already satisfies;
6. identify meaningful discrepancies rather than silently resolving them;
7. select the next coherent unmet behavioral slice.

Phase and subsection ordering in this document does not override that process.

Work listed here must not be repeated merely because it remains listed. Credit
behavior already satisfied by HEAD and proceed to the next unmet requirement.

Each behavioral change follows:

```text
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

CLI tests should protect user intent, option interpretation, useful errors, and
translation into application operations. They should not duplicate engine,
configuration, color-assignment, or Model semantics already protected at a
lower level.

Each phase below is intended to leave the application in a coherent and usable
state. A phase may contain multiple independently committed TDD slices.

---

# Cross-Phase CLI Semantics

## Realizations are the execution coordinate

Normal CLI execution addresses:

```text
Artifact + Realization
```

not:

```text
Artifact + Variant
```

A Variant is a Model-owned reusable configuration.

A Realization is the application of that Variant to an Artifact, optionally
with Artifact-specific customization.

Multiple Realizations may originate from the same Variant, so Variant identity
is not a sufficient general execution coordinate.

Normal user-facing build, inspection, cleaning, and recoloring operations
should therefore use Realization names.

## Canonical Realizations require no Artifact configuration

Every registered Model Variant supplies a canonical Realization to every
Artifact according to the architecture.

Examples include:

```text
artwork.default  -> artwork_default
shape.default    -> shape_default
shape.ornament   -> shape_ornament
```

A newly created Artifact therefore does not need to declare those Realizations
in `artifact.toml`.

Artifact configuration should contain only source metadata and actual
Artifact-specific customization.

## Scope convention

Where applicable, commands use the same scope convention:

```text
<command>
    all applicable Artifacts

<command> dog
    Artifact dog

<command> --realization shape_ornament
    that Realization across applicable Artifacts

<command> dog --realization shape_ornament
    that Realization of dog
```

Commands must define sensible behavior when a requested Realization is not
available for one or more selected Artifacts rather than silently changing the
meaning of the request.

## Project-owned paths

Artifact-owned managed inputs may be referenced from Artifact configuration
using paths relative to the project root.

Such paths are resolved relative to the project root, not the process working
directory and not the directory containing `artifact.toml`.

For example:

```toml
source = "artifacts/dog/artifact.png"
original = "originals/dog.png"
```

These are persistent references to Artifact-owned source resources.

Generated Model, Stage, and Product filesystem paths must not be persisted in
Artifact configuration.

The distinction is:

```text
Artifact-owned managed input
    persistent source/configuration resource
    may be referenced by project-relative path

generated Model/Stage Product
    materialization of the build graph
    must not be persisted as Artifact configuration
```

The filesystem may materialize generated Products, but Artifact configuration
must continue to address manufacturing behavior through logical configuration
and Product identity rather than generated paths.

---

# Phase 1 — Intake and Build

## Goal

At the end of Phase 1, raw customer PNGs can be ingested and every canonical
Realization can be built without any Artifact-specific product configuration.

The usable workflow is:

```text
artifact create

artifact build
artifact build --build-all
```

A narrower build remains available when desired:

```text
artifact build dog
artifact build --realization shape_ornament
artifact build dog --realization shape_ornament
```

No `config` operation is required for ordinary canonical Realizations.

---

## 1.1 PNG intake

Treat root-level PNG files as an intake queue.

Before:

```text
smith-dog.png
jones-cat.png
lee-house.png
```

After successful batch creation:

```text
originals/
    smith-dog.png
    jones-cat.png
    lee-house.png

artifacts/
    smith-dog/
        artifact.toml
        artifact.png
    jones-cat/
        artifact.toml
        artifact.png
    lee-house/
        artifact.toml
        artifact.png
```

Required semantics:

* `artifact create` with no Artifact ID discovers root-level PNG intake files;
* each successfully ingested PNG creates an Artifact using its filename stem as
  the Artifact ID;
* the original PNG is moved out of the intake directory and preserved beneath
  `originals/`;
* the Artifact receives a managed working copy named `artifact.png`;
* successfully processed PNGs no longer remain in the intake directory;
* no root-level PNGs means that the intake queue is empty;
* ingestion must not lose the only copy of an original PNG if creation fails.

Preserve explicit single-Artifact creation:

```text
artifact create dog
artifact create dog --source customer-final.png
```

When the Artifact ID and source filename differ, preserve the original
filename rather than renaming the preserved customer source merely to match the
Artifact ID.

Define deterministic, safe behavior for:

* an Artifact that already exists;
* an `originals/` destination collision;
* duplicate or conflicting inferred Artifact IDs;
* an explicit source outside the ordinary root intake queue;
* partial failure during batch ingestion.

Do not allow batch convenience to make destructive behavior ambiguous.

---

## 1.2 Artifact source metadata

A newly created Artifact should require only source metadata.

Conceptually:

```toml
source = "artifacts/smith-dog/artifact.png"
original = "originals/smith-dog.png"
```

Required semantics:

* `source` references the managed Artifact input;
* `original` references the preserved customer source;
* both are project-relative;
* `source` must no longer be persisted as an absolute filesystem path;
* the preserved original remains referenceable after ingestion;
* source/original metadata does not redefine Model or Variant semantics;
* neither field represents a generated Model, Stage, or Product path.

Determine the appropriate permanent configuration treatment of `original`
before implementation. Do not accidentally expose it as a Model parameter if
it is Artifact source metadata.

---

## 1.3 Build status

Make bare:

```text
artifact build
```

a read-only build-state operation.

It reports the current state of the effective Realizations across the project
without executing build work.

The report should make useful distinctions such as:

```text
current
stale
missing
```

and provide enough Artifact/Realization identity for the user to understand
what work is required.

For example:

```text
Artifact      Realization       Status
smith-dog     artwork_default   current
smith-dog     shape_default     current
smith-dog     shape_ornament    stale
jones-cat     artwork_default   missing
...
```

The status operation must use the same dependency/Product-state semantics as
the build engine rather than implementing an independent CLI definition of
staleness.

The command should summarize whether build work is required and direct the user
toward `--build-all` when appropriate.

---

## 1.4 Build all

Add:

```text
artifact build --build-all
```

meaning:

> Bring every effective Realization of every defined Artifact up to date.

This is make-like desired-state behavior.

Selecting everything does not imply blindly executing everything. Existing
dependency and Product-state analysis determines what actually needs to run.

A change to Model-owned configuration such as `parameters.toml` should permit:

```text
artifact build
```

to reveal the affected state, followed by:

```text
artifact build --build-all
```

to rebuild only what has become stale or missing.

Preserve useful narrower execution:

```text
artifact build dog
```

builds all effective Realizations for `dog`.

```text
artifact build --realization shape_ornament
```

builds that Realization across applicable Artifacts.

```text
artifact build dog --realization shape_ornament
```

builds exactly that Artifact Realization.

Normal build CLI should not require Variant selection.

Remove or retire normal CLI behavior whose execution coordinate is
`--variant` or `--all-variants` once equivalent Realization-oriented behavior
is established.

Independent Stage execution is a separate developer/diagnostic capability and
must not cause the normal build vocabulary to conflate Variant and
Realization.

---

## 1.5 Named color layers

Packaged 3MF Products produced by an ordinary build must expose the resolved physical printing color in the operator-facing name of each independently printable component.

For Artwork-derived components, the name uses the physical printer color established by the Artwork printer_assignments.

For Model-owned structural components, the name uses the resolved semantic printing color established by the owning Model.

The component name must preserve stable component identity in addition to the color name; color must not replace component identity.

Conceptually:

```text
dog-color-1 - Fire Engine Red
dog-color-2 - Cold White
dog-base - Cold White
dog-outer-ridge - Gold
```

Packaging must not independently select colors. It presents the semantic physical color assignment already established upstream.

---

## Phase 1 completion criterion

Starting with three raw PNG files in the project root, the user can run:

```text
artifact create
artifact build
artifact build --build-all
```

and obtain current build Products for every canonical Realization without
writing or editing Artifact-specific product configuration.

The intake directory is clean afterward, the customer originals are preserved,
and Artifact-owned source references are portable project-relative paths.

Packaged 3MF Products expose both stable component identity and the resolved
physical printing color in their operator-facing component names.

---

# Phase 2 — Customization and Reset

## Goal

At the end of Phase 2, the user can customize Realizations when the canonical
configuration is insufficient and can discard generated work safely.

Phase 1 remains the ordinary workflow.

Phase 2 adds:

```text
artifact config
artifact clean
```

---

## 2.1 Authored configuration

Define:

```text
config = authored/persistent configuration
```

`config` must not become another view of fully resolved Model configuration.

For example:

```text
artifact config dog --realization shape_ornament
```

shows only Artifact-authored customization for that Realization.

If the canonical Realization has no Artifact-specific customization, report
that condition clearly rather than dumping inherited Model/Variant defaults.

---

## 2.2 Realization customization

Support:

```text
artifact config dog \
    --realization shape_ornament \
    --parameters shape_size=110
```

This materializes or updates Artifact-specific customization of an already
existing canonical Realization.

Customizing a canonical Realization does not require `--create`.

Parameter validation and resolution remain owned by the existing
configuration/Model infrastructure. CLI code should not duplicate
Model-specific parameter semantics.

---

## 2.3 Additional named Realizations

Permit an Artifact to define an additional named Realization when required.

For example:

```text
artifact config dog \
    --realization large-ornament \
    --create \
    --parameters variant=shape.ornament shape_size=125
```

CLI configuration treats `variant=shape.ornament` as a configuration
assignment rather than introducing a separate normal `--variant` execution
coordinate.

Required semantics:

* `--create` permits creation of a noncanonical Realization name;
* canonical Realizations already exist and do not require `--create`;
* a misspelled/nonexistent noncanonical Realization must not silently become a
  new Realization without `--create`;
* updating one Realization must preserve unrelated Realization declarations;
* configuration persistence must support safe nested Realization updates rather
  than replacing the entire `[realizations]` table.

Before implementing bulk configuration across Artifacts, explicitly settle
mixed-state and atomicity behavior when some selected Artifacts already contain
the named Realization and others do not.

---

## 2.4 Bulk customization

Once single-Artifact mutation is sound, support the normal scope convention
where useful.

For example:

```text
artifact config \
    --realization large-ornament \
    --create \
    --parameters variant=shape.ornament shape_size=125
```

may define the same additional Realization across the selected Artifact scope.

Bulk mutation must have explicit failure/atomicity semantics before tests are
written.

Do not let batch behavior emerge accidentally from a loop around a
single-Artifact mutator.

---

## 2.5 Clean

Align `clean` with Artifact/Realization execution coordinates.

Support:

```text
artifact clean dog --realization shape_ornament
```

to remove derived Products belonging to that Realization while preserving:

* `artifact.toml`;
* managed source inputs;
* preserved originals;
* unrelated Realizations.

Also support the broader scopes where safe and useful:

```text
artifact clean dog
artifact clean --realization shape_ornament
artifact clean
```

Because broad cleaning is destructive, define confirmation/explicitness policy
before implementing the no-argument form.

Cleaning removes generated Products. It does not remove the Artifact or its
authored configuration.

After cleaning, `artifact build` should report the affected Realizations as
requiring work, and the normal build commands should be capable of restoring
them.

---

## Phase 2 completion criterion

The Phase 1 workflow still works unchanged.

Additionally, the user can customize an existing canonical Realization or
define an additional named Realization, build it through the normal
Realization-oriented build interface, clean its generated Products, and rebuild
it.

No manual TOML editing is required for ordinary customization.

---

# Phase 3 — Recolor for Printer Operation

## Goal

At the end of Phase 3, built 3MFs can optionally be transformed quickly into
operator-friendly 3MFs whose component color metadata and presentation
communicate the intended physical filament assignment.

No geometry work is repeated.

Add:

```text
artifact recolor
```

The production workflow becomes:

```text
artifact create
artifact build
artifact build --build-all
artifact recolor --colors printer
```

---

## 3.1 Recolor operates on packaged component color semantics

`recolor` operates downstream of ordinary geometry generation.

It must not rerun:

* source preparation;
* tracing;
* rasterization;
* vectorization;
* geometry composition;
* extrusion; or
* other geometry-producing operations.

Recolor operates on independently printable components already represented by
a packaged 3MF and on the semantic color information preserved for those
components.

Packaged components may obtain their color semantics in different ways.

For Artwork-derived color components:

```text
measured Artifact color
    ↓
Artwork physical-color assignment
    ↓
packaged component
```

For Model-owned structural components, such as Shape base or outer ridge:

```text
Model-owned semantic printing color
    ↓
packaged component
```

These are distinct semantics and must not be conflated.

Artwork assignment policy applies to Artifact colors. It must not be
indiscriminately reapplied to Model-owned structural colors that already
identify intended semantic physical colors.

Likewise, recoloring a complete Shape 3MF must not ignore structural components
merely because they are not Artwork color regions.

Recolor should therefore preserve both:

* stable independently printable component identity; and
* the semantic source and meaning of that component's printing color.

Prefer reusable, Model-independent 3MF metadata transformation where the
operation is purely mechanical. Do not move Artwork assignment policy or Shape
color policy into generic 3MF infrastructure.

---

## 3.2 Recolor existing 3MF Products

Recolor transforms an existing packaged manufacturing Product into an
operator-facing representation.

Preserve the canonical built 3MF and produce a distinct recolored output unless
a later explicit design decision changes this policy.

Recoloring should be deterministic and idempotent.

Repeated recoloring must not accumulate presentation labels.

The transformation must preserve manufacturing geometry, including:

* mesh coordinates;
* component geometry;
* component partitioning; and
* build composition.

Only operator-facing color/material metadata and presentation information
required by the selected physical color realization should change.

---

## 3.3 Printer recoloring

Support:

```text
artifact recolor --colors printer
```

For Artwork color components, printer recoloring uses the established Artwork
`printer_assignments` semantics: the globally optimal one-to-one assignment
between Artifact colors and configured printer colors.

For Model-owned structural components, the Model's already-resolved semantic
printing color remains authoritative.

Recolor must not reinterpret an explicit Shape color, for example, as a
measured Artwork color merely because another printer color has a closer RGB
value.

The resulting 3MF should make component identity and intended physical color
immediately understandable in PrusaSlicer.

Conceptually:

```text
dog-color-1 - Fire Engine Red
dog-color-2 - Cold White
dog-color-3 - Pine Green
dog-base - Cold White
dog-outer-ridge - Gold
```

Do not replace stable component identity merely with a color name.

The operator must be able to identify both:

* what component this is; and
* what physical color is intended.

Before implementation, settle how a Model-owned semantic color that is not
currently present in `printer_colors` should be represented to the operator.
Do not silently substitute another color through Artwork assignment policy.

---

## 3.4 Library recoloring

Support:

```text
artifact recolor --colors library
```

For Artwork color components, library recoloring uses the established Artwork
`library_assignments` semantics: the globally optimal one-to-one assignment
from filament physically present in the configured library.

For Model-owned structural components, preserve the owning Model's semantic
printing-color intent.

Before implementation, settle the operator-facing behavior when an explicitly
requested structural color is absent from the library. This is an availability
question about an already selected semantic color, not automatically an
Artwork color-matching problem.

This mode allows the operator to determine which loaded filament should remain
and which filament swaps from owned inventory are warranted before printing.

Recolor must reuse established Artwork color-assignment semantics rather than
implementing another nearest-color algorithm.

---

## 3.5 Catalog improvement analysis

Artwork color analysis already distinguishes:

```text
printer_assignments
library_assignments
catalog_assignments
```

and defines individual and aggregate perceptual distance.

Recolor should be capable of presenting those existing comparisons as
production guidance for Artwork-derived color components.

Catalog assignment is diagnostic rather than an assertion that the user owns
those colors.

For Artwork colors, report individual and aggregate perceptual distance
sufficiently to answer:

> How much could this Artwork improve using filament already in the library?

and:

> How much further could it improve if another known catalog color were
> purchased?

Conceptually:

```text
Layer    Selected          Distance    Best catalog       Distance
1        Fire Engine Red      5.8      Cardinal Red          1.0
2        Cold White           1.2      Polar White           0.8
3        Pine Green           3.7      Forest Green          1.5
```

Useful derived comparisons include:

```text
printer improvement = printer aggregate distance - library aggregate distance

purchase improvement = library aggregate distance - catalog aggregate distance
```

These calculations apply to Artwork assignment semantics.

Do not automatically treat a Model-owned structural semantic color as another
measured Artwork color participating in the global Artwork assignment.

Catalog analysis must not silently mutate:

* `printer_colors`;
* `library_colors`;
* Artifact configuration;
* Model-owned structural color configuration; or
* the canonical manufacturing Product.

---

## 3.6 Recolor scope

Apply the normal scope convention:

```text
artifact recolor dog --realization shape_ornament --colors printer
artifact recolor dog --colors printer
artifact recolor --realization shape_ornament --colors printer
artifact recolor --colors printer
```

Only existing applicable packaged Products should be recolored.

Recolor must not implicitly trigger an expensive geometry build merely because
a requested 3MF is absent. Missing build prerequisites should be reported
clearly.

---

## Phase 3 completion criterion

The user can take built Artifacts and rapidly generate operator-ready 3MFs
using the intended physical filament assignments.

For Artwork-derived components, the user can choose assignments based on:

* colors currently available to the printer; or
* colors physically available in the filament library.

The user also receives quantitative Artwork color analysis indicating how much
color fidelity could improve using library or catalog colors.

Model-owned structural components retain the semantic printing colors defined
by their owning Models rather than being incorrectly absorbed into Artwork's
color-matching policy.

No geometry is rebuilt during recoloring.

---

# Phase 4 — Inspection

## Goal

At the end of Phase 4, the user can answer distinct questions without
confusing authored configuration, effective configuration, addressable
objects, and color analysis.

The commands are:

```text
artifact list
artifact config
artifact show
artifact colors
```

Their responsibilities are intentionally distinct:

```text
list
    What exists / what can I address?

config
    What have I explicitly configured?

show
    What configuration will actually be used?

colors
    Why did the Artwork color system make these assignments?
```

---

## 4.1 List

Define:

```text
artifact list
```

to list defined Artifact IDs.

Define:

```text
artifact list dog
```

to list the effective Realizations addressable for `dog`, including canonical
Realizations and explicitly declared additional Realizations.

Listing should use the authoritative Realization catalog rather than
reconstructing it independently in CLI code.

`list` reports identity and availability, not complete configuration.

---

## 4.2 Show

Make `show` Realization-oriented.

For example:

```text
artifact show dog --realization shape_ornament
```

shows the fully resolved configuration that would actually be used for that
Realization.

It should resolve the Realization directly through configuration semantics
rather than detouring through Variant-oriented build planning merely to obtain
a resolver.

Resolved output may include useful provenance where that helps explain whether
a value came from:

* Model defaults;
* Variant overrides;
* Workspace configuration;
* Artifact configuration; or
* Realization customization.

Do not make `show` synonymous with `config`.

---

## 4.3 Colors

Retain `colors` as the detailed Artwork color-analysis command.

It should expose the established Artwork color analysis across:

```text
printer
library
catalog
```

including individual and aggregate perceptual distances.

`recolor` is the production operation that prepares packaged components for
operator use.

`colors` is the Artwork color-assignment inspection/diagnostic operation.

The two should share the applicable underlying Artwork color-analysis semantics
rather than developing parallel assignment implementations.

Where color analysis requires only persistent registered Artwork products,
build only the minimum missing dependency closure required for that analysis.
Do not require standalone Artwork packaging merely to inspect color quality.

Model-owned structural printing colors are not Artifact color regions and
should not be silently included in Artwork's global one-to-one color analysis.

---

## 4.4 Remove misplaced inspection responsibilities

As the new command responsibilities become established, remove or relocate
legacy CLI behavior that no longer belongs to its command.

In particular, Model catalog/workplan inspection currently attached to
Artifact configuration should not force `config` to serve two unrelated
purposes.

Before moving or deleting developer-oriented capabilities, determine whether
they remain useful and choose an explicit home for them rather than silently
discarding them.

---

## Phase 4 completion criterion

Without editing files or invoking developer internals, a user can determine:

* which Artifacts exist;
* which Realizations are available;
* what Artifact-specific configuration was authored;
* what effective configuration a Realization will use;
* whether builds are current;
* and why Artwork physical colors were selected.

The production workflow established in Phases 1–3 remains unchanged.

---

# Phase 5 — CLI Consolidation and Production Polish

## Goal

Complete the transition from the historical CLI to the streamlined
Artifact/Realization-oriented workflow without retaining contradictory command
semantics.

This phase should contain no speculative new manufacturing capability.

It consolidates behavior already proven useful in the preceding phases.

---

## 5.1 Retire obsolete normal-workflow syntax

Review remaining public options and remove or clearly isolate obsolete
Variant-oriented normal execution syntax such as:

```text
--variant
--all-variants
```

where Realization-oriented equivalents now define the intended user workflow.

Do not remove internal Model/Variant coordinates merely because they are no
longer ordinary CLI coordinates.

Variants remain architecturally essential configuration identities.

---

## 5.2 Developer and Stage operations

Review independent Stage execution and other developer-oriented operations.

Preserve the architectural ability to execute a Stage through a complete
`StageContext`.

Do not force specialized Stage execution into the ordinary production command
semantics merely to reduce the number of top-level commands.

If developer operations require a separate command surface, make that
separation explicit.

---

## 5.3 Output consistency

Make routine command output consistent around:

```text
Artifact
Realization
state/action
Product where relevant
```

Avoid exposing implementation-oriented Model/Variant coordinates when they do
not help the user perform the requested operation.

Errors should identify the actionable Artifact/Realization scope that failed.

Batch operations should summarize successful, skipped/current, and failed work
without obscuring the underlying error.

---

## 5.4 End-to-end production acceptance

Protect the final common workflow with a small number of meaningful acceptance
tests.

A representative workflow should establish that the user can:

```text
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
artifact recolor --colors printer
    ↓
obtain operator-ready 3MF Products
```

A customization acceptance path should establish only the additional behavior
that matters:

```text
create
    ↓
config one Realization
    ↓
build that Realization
    ↓
recolor
```

Do not duplicate detailed Model geometry, configuration resolution, build
graph, or color-assignment assertions already protected by focused tests.

---

## Phase 5 completion criterion

The normal user-facing CLI presents one coherent mental model:

```text
create    ingest customer sources

build     inspect build state or make selected work current

config    author Artifact/Realization exceptions

clean     discard generated work

recolor   prepare built 3MFs for physical filament choices

list      discover addressable Artifacts and Realizations

show      inspect effective resolved configuration

colors    inspect Artwork color-assignment quality
```

Variants remain Model-owned reusable configuration.

Realizations remain the Artifact-scoped execution coordinate.

The common production workflow requires no manual configuration when Model
Variants already describe the desired products.

---

# Target Production Workflow

For a routine batch:

```text
# Customer PNGs are placed in the project root.

artifact create

# See what the new intake or configuration changes require.
artifact build

# Bring the project current.
artifact build --build-all

```

When filament swaps from owned inventory are acceptable:

```text
artifact recolor --colors library
```

When one Artifact requires an exception:

```text
artifact config smith-dog \
    --realization shape_ornament \
    --parameters shape_size=110

artifact build smith-dog --realization shape_ornament

artifact recolor smith-dog \
    --realization shape_ornament \
    --colors printer
```

Inspection and maintenance remain available without complicating the ordinary
path:

```text
artifact list
artifact list smith-dog

artifact config smith-dog --realization shape_ornament
artifact show smith-dog --realization shape_ornament

artifact colors smith-dog

artifact clean smith-dog --realization shape_ornament
```

The desired steady-state workflow is therefore:

```text
create → build → recolor → print
```

with:

```text
config
clean
list
show
colors
```

used when the ordinary path requires customization, maintenance, or
explanation.

