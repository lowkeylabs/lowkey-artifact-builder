# Change Plan --- Sparse Variant Application and Selection

## Purpose

Bring the current repository into conformance with `ARCHITECTURE.md`
following the clarified Variant semantics now defined there.

The required change is intentionally small.

The repository already contains the central abstractions needed by the
architecture:

-   Models own Variants.
-   `VariantSpec` already carries an immutable parameter mapping.
-   the configuration resolver already applies Variant parameters
    between Model defaults and later configuration scopes;
-   a missing Variant selects `default`;
-   the existing runtime commonly decomposes Variant identity into Model
    name and a historical `realization` local-name coordinate;
-   Product, dependency, planning, persistence, and filesystem machinery
    already use that decomposed representation.

The work in this plan is therefore not a Variant subsystem redesign. It
is the completion and consistent use of the existing Variant mechanism.

`ARCHITECTURE.md` and the applicable Model `DEFINITION.md` files remain
the permanent normative specifications. This file is temporary and
should be deleted when conformance is demonstrated.

------------------------------------------------------------------------

# Architectural Target

The effective configuration for a Realization is conceptually:

``` text
Model parameter defaults
        ↓
Variant parameter overrides
        ↓
Artifact-specific overrides
        ↓
effective Realization configuration
```

Other existing configuration scopes may continue to participate
according to their established precedence. The important Variant
invariant is that `VariantSpec.parameters` is a sparse override layer
over Model defaults, not a second complete configuration or
Feature-selection system.

A Variant:

-   belongs to exactly one Model;
-   has a Model-scoped local name;
-   contains only parameter overrides that distinguish that reusable
    configuration from Model defaults;
-   may contain no overrides, particularly for `default`;
-   does not independently define or select Features;
-   does not redefine Model-owned parameter or Feature semantics.

Feature participation remains Model-owned behavior. A parameter value
may enable, disable, or otherwise affect a Feature according to that
Model's semantics. No generic boolean Feature-selection mechanism is
required.

A Realization remains:

``` text
Artifact + Variant + optional Artifact-specific customization
```

A fully qualified Variant reference such as:

``` text
shape.ornament
```

is a compact representation of the same identity that existing runtime
structures may represent as:

``` text
model = "shape"
realization = "ornament"
```

The migration must not create a second runtime identity system.

------------------------------------------------------------------------

# Existing HEAD Alignment

The following behavior already aligns with the architecture and should
be preserved rather than rebuilt.

## `VariantSpec`

The existing `VariantSpec` already provides:

``` text
name
parameters
description
```

with an immutable copy of `parameters`.

This is sufficient for the architectural Variant definition. Do not add
a Feature list, Feature-selection field, complete-configuration payload,
or parallel Variant abstraction.

Only documentation or validation changes demonstrated necessary by
focused tests belong in this area.

## Resolver precedence

The existing resolver already applies configuration in a precedence
chain that includes:

``` text
model
    <
variant
    <
later customization scopes
```

and merges `variant.parameters` as the Variant layer.

This is the architectural center of the change. Extend or reuse this
resolver; do not create a second Variant configuration resolver.

## Default Variant

The existing Model machinery provides a `default` Variant when needed,
and the resolver selects `default` when no Variant is configured.

An empty `default` Variant is valid and means ordinary Model behavior is
provided by Model defaults.

Existing ordinary Model tests are therefore presumed to exercise the
default Variant unless Variant identity or selection is specifically
under test.

## Runtime and Product identity

Existing runtime structures using:

``` text
artifact
model
realization
stage
product
```

may remain.

Where `realization` carries the local Variant name, this is a valid
decomposed representation of Variant identity.

Do not rename `ProductRef.realization`, change canonical filesystem
layout, introduce a fully qualified Variant field throughout the engine,
or migrate persistent Product identity merely for terminology.

------------------------------------------------------------------------

# Phase 1 --- Lock In Sparse Variant Resolution

Establish executable evidence for the Variant semantics already
substantially present in HEAD.

Begin with focused configuration/Variant tests.

## Required behavior

Tests must establish that:

-   a Variant belongs to one Model and its local name is Model-scoped;
-   `VariantSpec.parameters` is immutable;
-   a Variant may contain zero parameter overrides;
-   the `default` Variant may contain zero parameter overrides;
-   Model parameter defaults establish ordinary behavior;
-   a specialized Variant overrides only the parameters it names;
-   parameters omitted by a specialized Variant continue to resolve from
    the Model/default configuration layers;
-   Variant overrides do not require a separate Feature-selection
    declaration;
-   Model-owned parameter semantics remain unchanged by the generic
    Variant mechanism;
-   Artifact-specific customization overrides the selected Variant
    without changing Variant identity;
-   adding a Model parameter with a usable Model default does not
    require modifying existing Variants merely to keep them resolvable.

Preserve the existing resolver precedence outside the Variant layer
unless a focused test demonstrates an architectural conflict.

## Production boundary

Prefer no structural production change if existing resolver behavior
satisfies these tests.

Permitted production changes are limited to focused corrections such as:

-   Variant resolution defects;
-   incorrect precedence;
-   inappropriate validation requiring Variants to repeat Model
    defaults;
-   stale comments/docstrings that materially misstate Variant
    semantics.

Do not add generic Feature-selection machinery.

## Phase acceptance

Using one Model with a non-empty set of Model defaults, demonstrate:

``` text
default Variant
    → ordinary Model defaults

specialized Variant
    → Model defaults + sparse Variant overrides

customized application
    → Model defaults + sparse Variant overrides + Artifact customization
```

The resolver must report the expected effective values and provenance.

All non-conflicting existing configuration and Model tests remain green.

------------------------------------------------------------------------

# Phase 2 --- Articulate Useful Model Variants

Use the existing `VariantSpec.parameters` mechanism to define useful
reusable Variants for actual Models where justified by the applicable
Model `DEFINITION.md`.

Review each Model's `DEFINITION.md` before adding or changing its
Variant catalog.

## Required behavior

For each Model changed:

-   preserve the Model's existing ordinary behavior as
    `<model>.default`;
-   keep Model parameter defaults authoritative for ordinary behavior;
-   keep the `default` Variant empty unless an actual override is
    required;
-   define specialized Variants using only the parameter overrides that
    distinguish them from Model defaults;
-   rely on existing Model-owned parameter semantics for Feature
    participation;
-   do not duplicate all Model parameters into each Variant;
-   do not add explicit Feature toggles merely because a Variant uses a
    Feature;
-   do not add a separate Variant Feature list.

For example, if Shape defines:

``` text
shape_outer_ridge_width = 0
```

as ordinary Model behavior and positive width means that the ridge
participates, a specialized Variant may simply override:

``` text
shape_outer_ridge_width = 2
```

Likewise, if a sentinel parameter value such as `"none"` means an
optional component does not participate, a Variant may enable that
behavior by overriding the parameter with an ordinary configured value.

Those semantics belong to Shape, not to generic Variant infrastructure.

## Scope discipline

Names such as:

``` text
shape.ornament
shape.coaster
shape.keychain
```

should be added only when they are justified as useful reusable Model
configurations. `ARCHITECTURE.md` examples are illustrative rather than
a requirement to manufacture every example Variant immediately.

Do not change unrelated geometry, Artwork processing, Product contracts,
Stages, or dependency wiring merely to populate a Variant catalog.

## Phase acceptance

At least one actual Model must expose:

-   `default`, preserving ordinary behavior; and
-   at least one specialized sparse Variant whose effective
    configuration differs from `default`.

Resolver-based tests must demonstrate the difference without requiring
Artifact-specific customization.

------------------------------------------------------------------------

# Phase 3 --- Variant-Oriented Inspection and Build Selection

Expose the architectural Variant identity through the normal user
workflow while normalizing immediately to the existing runtime
representation.

The resolver used for inspection and the resolver used for building must
remain the same source of effective configuration semantics.

## Variant reference

Support a compact Variant reference:

``` text
<model>.<local-variant-name>
```

for example:

``` text
shape.ornament
artwork.default
```

Normalize it at the command/configuration boundary to:

``` text
model = <model>
local Variant name = <local-variant-name>
```

and then reuse existing resolver/planner/runtime machinery.

A bare:

``` text
default
```

may be accepted where the Model is already unambiguous and should mean
that Model's `default` Variant.

Malformed, unknown, or conflicting Variant selections must fail clearly.

## `artifact show`

Extend normal inspection so a user can inspect the effective
configuration for a selected Variant.

Target workflow:

``` text
artifact show dog
artifact show dog --variant=shape.ornament
```

`artifact show dog` continues to inspect ordinary/default behavior.

`artifact show dog --variant=shape.ornament` must display the
configuration obtained from the same resolver semantics used when
building that Variant.

Do not implement a separate display-only merge path.

## `artifact build`

Add Variant-oriented build selection.

Target workflow:

``` text
artifact build dog
artifact build dog --variant=default
artifact build dog --variant=shape.ornament
artifact build dog --variant=artwork.default
artifact build dog --all-variants
```

Required semantics:

### No Variant option

``` text
artifact build dog
```

builds the Artifact's ordinary/default Variant behavior.

It must not silently change to "build every configured realization"
merely because historical realization machinery can represent multiple
local names.

### Explicit Variant

``` text
artifact build dog --variant=shape.ornament
```

selects that Model and Variant and builds the resulting Realization
using the existing graph, planner, Product, persistence, and execution
machinery.

### Explicit default

``` text
artifact build dog --variant=default
```

is equivalent to selecting the applicable Model's `default` Variant.

### All Variants

``` text
artifact build dog --all-variants
```

builds all defined Variants applicable to the Artifact across applicable
Models.

The observable result should be equivalent to requesting those Variants
individually. Existing planning and Product-state machinery may avoid
repeated upstream work.

`--variant` and `--all-variants` are mutually exclusive.

## Historical `--realization`

Inspect existing `--realization` CLI behavior as part of this phase.

Do not mechanically rename engine/runtime `realization` fields.

At the public normal-build boundary, avoid presenting architectural
Realization as a second independent reusable selection mechanism.
Preserve `--realization` only where it still has a distinct,
architecturally valid purpose, such as independent Stage execution or a
compatibility boundary that is explicitly tested and documented.

Do not allow `--variant` and historical `--realization` syntax to create
two independent identities for the same normal-build concept.

## Phase acceptance

Integrated CLI tests must demonstrate:

``` text
artifact show dog --variant=shape.ornament
artifact build dog --variant=shape.ornament --dry-run
```

resolve the same Model, Variant, and effective configuration.

Also demonstrate:

``` text
artifact build dog
```

selecting default behavior,

``` text
artifact build dog --variant=default
```

selecting the same default behavior, and

``` text
artifact build dog --all-variants
```

selecting all applicable Variants without creating parallel runtime
identity.

All non-conflicting existing CLI tests remain green.

------------------------------------------------------------------------

# Phase 4 --- End-to-End Variant Realization

Prove the architecture through real Model behavior and normal
manufacturing output.

This phase should add integrated evidence rather than introduce another
abstraction.

## Required scenarios

Demonstrate at least:

### Default application

``` text
Artifact + <model>.default
```

preserves historical Model-default behavior.

### Specialized Variant application

``` text
Artifact + shape.<specialized-variant>
```

uses Model defaults plus that Variant's sparse overrides and produces
the expected Realization.

### Artifact customization

An Artifact-specific override changes the effective configuration of the
specialized Variant without creating a new Variant identity.

### Dependency reuse

When a specialized Shape Variant consumes an already-current Artwork
Product, the existing Product may satisfy the dependency without
rebuilding unrelated Artwork Stages.

### Persistent identity

The resulting Products continue to use the existing canonical decomposed
namespace:

``` text
artifacts/<artifact>/<model>/<local-variant-name>/<stage>/...
```

No parallel fully-qualified Variant filesystem hierarchy is introduced.

## Manufacturing acceptance

At least one normal CLI path for a specialized Variant must produce the
expected manufacturing output, including the final 3MF when that is the
requested Product.

Existing default Artwork and Shape acceptance paths remain green.

------------------------------------------------------------------------

# Phase 5 --- Final Conformance Audit and Delete CHANGEPLAN

Perform a final repository-wide audit against:

-   `ARCHITECTURE.md`;
-   each applicable Model `DEFINITION.md`;
-   implementation at HEAD;
-   the complete test suite.

## Verify

Confirm that:

-   `VariantSpec` remains the single declarative Variant abstraction;
-   Variants are sparse Model-scoped parameter overrides;
-   `default` may be empty and preserves ordinary Model behavior;
-   Variant configuration does not duplicate Model defaults
    unnecessarily;
-   no generic Feature-selection mechanism has been introduced;
-   Feature participation remains Model-owned parameter semantics;
-   Artifact customization overlays the selected Variant without
    changing its identity;
-   fully qualified Variant references normalize to existing decomposed
    runtime identity;
-   `artifact show` and `artifact build` use consistent resolver
    semantics;
-   default build behavior remains simple;
-   explicit Variant build selection works;
-   all-Variant build selection works;
-   ProductRef, Product resolution, dependency binding, planning,
    persistence, reuse, and canonical filesystem layout remain stable
    unless a focused architectural discrepancy required change;
-   current Products continue to satisfy dependencies;
-   cross-Model and cross-Artifact reuse remain intact;
-   all non-conflicting tests pass;
-   type checking and repository quality checks pass.

Search for stale documentation or comments that still describe a Variant
as:

-   a complete duplicate of Model configuration;
-   an explicit Feature-selection list;
-   an independently reusable Realization definition.

Update only materially misleading language.

## Completion

When the repository conforms to the permanent specifications and the
complete suite is green:

``` text
delete CHANGEPLAN.md
```

The permanent architecture and Model definitions then remain the source
of truth.

------------------------------------------------------------------------

# Explicitly Out of Scope

Unless a focused RED test demonstrates that one of these is necessary
for architectural conformance, do not:

-   redesign `VariantSpec`;
-   add a Variant Feature list;
-   add generic boolean Feature toggles;
-   require complete parameter sets in Variants;
-   create Variant inheritance;
-   create a second configuration resolver;
-   rename `ProductRef.realization`;
-   rename every runtime `realization` field;
-   migrate canonical filesystem layout;
-   redesign Product identity;
-   redesign Stage identity;
-   redesign dependency binding;
-   redesign planning or execution;
-   redesign Product persistence or freshness;
-   change Model geometry unrelated to a Variant override;
-   introduce new generic Operations;
-   perform broad terminology cleanup.

The preferred implementation strategy is:

``` text
prove existing resolver semantics
        ↓
articulate sparse Variants
        ↓
select Variants at public boundaries
        ↓
verify end-to-end
        ↓
delete CHANGEPLAN
```
