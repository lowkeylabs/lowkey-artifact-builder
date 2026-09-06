# Change Plan

This change plan captures a small set of semantic corrections, workflow
improvements, Model Feature additions, and Variants.

The intended work is evolutionary.

`ARCHITECTURE.md` and the applicable Model `DEFINITION.md` files are the
permanent specifications. This change plan is subordinate to those
specifications. When language or assumptions in this plan conflict with the
permanent specifications, the permanent specifications rule.

The existing architecture, dependency-driven build system, Model boundaries,
Stage execution, Product identity, Variant and Realization semantics, and
persistent Product layout should be preserved unless a specific requirement
below demonstrates that a change is necessary.

Implementation should follow:

```text
prompts/TEST_DRIVEN_DEVELOPMENT.md
```

Tests encountered during this work should be curated according to that policy.
Do not create a separate broad test-cleanup effort.

---

# Phase 0 — Align the Change Plan with Permanent Specifications

Before changing production behavior, confirm that the work described by this
plan is expressed in terms consistent with `ARCHITECTURE.md` and the applicable
Model `DEFINITION.md` files.

This phase does not introduce a new architecture and should not rewrite
permanent specifications merely to accommodate terminology or assumptions from
this change plan.

## 0.1 Preserve Model, Feature, and Parameter Semantics

Use the relationships established by `ARCHITECTURE.md`.

A Model declares:

* inputs;
* parameters;
* Features;
* Variants;
* Stages;
* Products; and
* dependencies.

A Feature is a Model-owned optional capability or behavior.

Feature participation may be determined by effective parameter values according
to Model-owned Feature semantics.

For example, a Shape Feature may participate when one of the Shape Model's
parameters has a nonzero value. The meaning of that value and its effect on
Feature participation belong to the Shape Model.

Do not introduce a separate generic Feature-selection mechanism.

Do not introduce a separate parameter-ownership hierarchy beneath Features.

Generic configuration, graph, planning, and execution infrastructure must not
contain Model-specific Feature semantics.

## 0.2 Preserve Variant and Realization Semantics

Preserve the permanent architectural distinction:

```text
Variant
    = Model + named reusable configuration
    = sparse parameter overrides over Model defaults

Realization
    = Artifact + Variant
      + optional Artifact-specific customizations
```

A Variant does not contain or independently select Features.

Instead, a Variant supplies sparse overrides to Model parameters. The resulting
effective parameter values may affect Feature participation according to
Model-owned semantics.

The `default` Variant may contain no overrides because the Model's parameter
defaults establish its ordinary behavior.

Historical runtime fields named `realization` may continue to represent the
local Variant-name coordinate where their meaning is unambiguous.

This work does not require a broad internal terminology migration.

## 0.3 Preserve Configuration Resolution

Unless a specific phase intentionally changes the public configuration syntax,
preserve the architectural resolution model:

```text
Model parameter defaults
        ↓
Variant parameter overrides
        ↓
Artifact-specific overrides
        ↓
effective Realization configuration
```

A public syntax change must not create another configuration hierarchy or
another Variant identity mechanism.

## 0.4 Preserve Product Architecture

Preserve the following architectural invariants:

* persistent Stage outputs remain first-class Products;
* no packaged 3MF becomes an architecturally privileged final Product;
* logical Product identity remains independent of filesystem location;
* dependency-driven execution remains authoritative;
* build only what is required by the requested Product dependency closure; and
* convenience publication of a Product does not establish another Product
  identity.

## 0.5 Completion

Phase 0 is complete when this change plan contains no requirement that conflicts
with `ARCHITECTURE.md` or the applicable Model definitions.

No production implementation is required merely to complete Phase 0.

---

# Phase 1 — Correct Standalone Artwork Physical Sizing

Correct the semantics of:

```text
artwork_size
```

for standalone Artwork dimensionalization.

This is a Model specification correction followed by a bug fix.

The current Artwork definition describes physical sizing in terms of scaling
the complete registered coordinate extent. That behavior does not express the
desired physical size of the actual occupied Artwork.

## 1.1 Define Artwork Size

Update the Artwork `DEFINITION.md` before changing tests or production
implementation.

For standalone Artwork:

```text
artwork_size
```

defines the maximum physical X/Y extent of the occupied Artwork envelope.

If the registered Artwork envelope has width `w` and height `h`, the common
uniform scale should make:

```text
max(physical_width, physical_height) = artwork_size
```

while preserving the Artwork's aspect ratio.

For example, Artwork whose occupied envelope is twice as wide as it is high
and whose:

```text
artwork_size = 120
```

should dimensionalize to approximately:

```text
120 mm × 60 mm
```

rather than scaling the complete registered coordinate canvas to 120 mm.

## 1.2 Preserve Registration

Physical dimensionalization must use one common affine transformation for the
registered Artwork.

The same transformation applies consistently to:

* the Artwork envelope; and
* every registered color layer.

Do not independently fit, scale, or center individual color layers.

The dimensionalized occupied Artwork should be centered according to the
standalone Artwork placement semantics.

## 1.3 Preserve Registered Geometry Semantics

Registered Artwork remains dimensionless before the responsible downstream
consumer introduces physical dimensionalization.

The distinction remains:

```text
registered_extent
    = common registered coordinate system

Artwork envelope
    = occupied region within that coordinate system
```

Correcting `artwork_size` must not change the meaning of upstream registered
Artwork or force upstream Stages to depend on physical Artwork dimensions.

## 1.4 TDD

Treat this work according to the bug-fix guidance in
`TEST_DRIVEN_DEVELOPMENT.md`.

Replace or correct existing tests that explicitly protect the old,
now-intentionally-revised sizing contract.

The regression behavior should establish at least:

* the maximum occupied physical X/Y extent equals `artwork_size`;
* aspect ratio is preserved;
* offset Artwork within the registered coordinate system is handled correctly;
* all color layers receive one common transformation; and
* individual color layers are not independently fitted.

Prefer a small synthetic non-square, offset registered Artwork fixture over a
large real-world Artifact.

Curate existing extrusion tests encountered during this work without expanding
the phase into unrelated test cleanup.

## 1.5 Completion

Phase 1 is complete when standalone Artwork dimensionalization gives
`artwork_size` its documented physical meaning while preserving registration
and upstream reusable Artwork semantics.

---

# Phase 2 — Publish Packaged 3MF Files

Provide a convenient user-facing copy of a successfully packaged 3MF in the
Artifact home directory.

Canonical Stage Products remain unchanged.

For example, a canonical Product such as:

```text
artifacts/nydeli/artwork/default/50-package/artifact.3mf
```

may be published as:

```text
artifacts/nydeli/artwork.default.3mf
```

Likewise:

```text
artifacts/nydeli/shape/default/40-package/artifact.3mf
artifacts/nydeli/shape/ornament/40-package/artifact.3mf
```

may be published as:

```text
artifacts/nydeli/shape.default.3mf
artifacts/nydeli/shape.ornament.3mf
```

## 2.1 Publication Semantics

A published 3MF is a convenience copy of an existing persistent Product.

It is not:

* a second Product;
* a new logical Product identity;
* a dependency target;
* a replacement for the canonical Product; or
* evidence that packaged 3MF Products are architecturally privileged.

Canonical Product resolution and dependency tracking continue to use the
existing Product architecture.

## 2.2 Publication Timing

Publication should occur when execution successfully produces or completes the
applicable package Product as part of the requested build operation.

A build that stops before packaging should not publish a 3MF merely because a
canonical package Product happens to exist from earlier work.

Targeted dependency builds that require only upstream Products must remain
minimal and must not cause packaging or publication.

Explicit execution that successfully performs the package step should publish
the resulting package Product.

## 2.3 Naming

Published package filenames should identify the Variant unambiguously using its
fully qualified Variant identity:

```text
<model>.<variant>.3mf
```

within the Artifact home directory.

For example:

```text
artwork.default.3mf
shape.default.3mf
shape.ornament.3mf
```

Do not encode generated Stage paths into Artifact configuration.

## 2.4 Implementation Boundary

Determine the smallest existing orchestration boundary that can publish a
successfully produced package Product without introducing Model-specific
knowledge into the generic engine.

Do not redesign Product identity, Stage execution, or package Stages merely to
support publication.

If a small declarative mechanism is needed to identify publishable Products,
prefer that over hard-coding Artwork or Shape package behavior into generic
infrastructure.

Do not introduce a generalized publication framework beyond what the current
requirement demonstrates.

## 2.5 TDD

Tests should distinguish:

* canonical Product creation;
* successful publication;
* published filename;
* absence of publication when packaging is not executed; and
* independence of the convenience copy from canonical Product identity.

Use acceptance coverage only for the meaningful user-visible publication
workflow. Keep detailed Product and execution semantics at their appropriate
lower test boundary.

## 2.6 Completion

Phase 2 is complete when a successful package operation makes the expected
Variant-qualified 3MF conveniently available beside `artifact.toml` without
changing canonical Product semantics.

---

# Phase 3 — Simplify Artifact Variant Configuration

Replace historical user-facing Realization-oriented Artifact configuration
with configuration expressed directly in terms of qualified Variants.

This is a deliberate public configuration-schema change.

It does not require a corresponding broad change to internal runtime structures
whose historical `realization` terminology remains semantically unambiguous.

## 3.1 Canonical Configuration Form

Artifact configuration should identify Variant-specific customization using the
qualified Variant identity.

The intended form is:

```toml
source = "artifact.png"

[artwork.default.parameters]
artifact_color_count = 3
artwork_size = 120.0
```

An Artifact using several Variants may contain:

```toml
source = "artifact.png"

[artwork.default.parameters]
artifact_color_count = 3
artwork_size = 120.0

[shape.default.parameters]
shape_size = 100.0

[shape.ornament.parameters]
shape_size = 100.0
```

The table identity:

```text
artwork.default
shape.default
shape.ornament
```

already identifies both the Model and local Variant name.

Do not redundantly require `model` or `variant` fields inside such a table.

These tables contain Artifact-specific parameter overrides for the selected
Variant. They do not define or modify the Variant itself.

## 3.2 Remove Historical User-Facing Realization Schema

Remove support for historical Artifact configuration expressed through:

```toml
[realizations.<name>]
```

This is intentionally a clean schema break.

Do not add compatibility behavior solely to preserve obsolete configuration or
obsolete tests.

Tests protecting the retired public configuration contract should be replaced
or removed as they are encountered.

This does not imply removal or renaming of every internal field, object,
filesystem coordinate, or API argument historically named `realization`.

## 3.3 Artifact Creation

Update:

```text
artifact create
```

to emit only the canonical qualified-Variant configuration form.

Creation should no longer generate `[realizations.*]` sections.

Preserve the existing purpose of interactive and non-interactive Artifact
creation. Do not redesign the command beyond what is necessary for the new
schema.

## 3.4 Configuration Resolution

Qualified Variant configuration must preserve the architectural resolution
order:

```text
Model parameter defaults
        ↓
Variant parameter overrides
        ↓
Artifact-specific overrides
        ↓
effective Realization configuration
```

The schema change must not introduce a second Variant identity mechanism or a
second parameter-resolution mechanism.

## 3.5 TDD

Treat this as an intentional public-contract change rather than a compatibility
bug.

Tests should establish:

* parsing of qualified Variant tables;
* Model and local Variant identity implied by the table name;
* Artifact-specific parameter overrides;
* multiple qualified Variants within one Artifact;
* rejection of the retired `[realizations.*]` schema;
* `artifact create` emission of the canonical form; and
* continued correct resolution into the existing runtime representation.

Curate configuration tests encountered during this change according to
`TEST_DRIVEN_DEVELOPMENT.md`.

## 3.6 Completion

Phase 3 is complete when Artifact configuration uses Variant terminology
directly and the historical user-facing Realization schema has been removed,
without requiring an unnecessary internal terminology migration.

---

# Phase 4 — Extend Models with New Features

Add the desired manufacturing capabilities as Features of the Models that own
them.

Features belong to Models.

The Models declare the parameters used to configure their behavior.

Variants added later configure Model behavior by supplying sparse parameter
overrides. Effective parameter values may enable, disable, or otherwise affect
Feature participation according to Model-owned Feature semantics.

Do not define Feature semantics inside Variants.

## 4.1 Specify Features Before Implementation

For each new Feature, update the applicable Model `DEFINITION.md` before RED
tests when the requested behavior introduces new semantic decisions.

The Feature specification should establish only the semantics needed to make
the capability unambiguous.

Depending on the Feature, this may include:

* applicable Model parameters;
* parameter defaults;
* the condition under which the Feature participates;
* physical dimensions;
* placement;
* registration;
* Z behavior;
* color or material behavior;
* interaction with existing Features;
* Product participation; and
* whether Feature geometry contributes to the Model's defined physical extent.

Avoid prescribing implementation mechanics unless they are themselves
architecturally significant.

## 4.2 Loop Feature

Add a loop capability to each Model for which a loop is required.

The conceptual loop is a cylindrical/ring attachment controlled by Model
parameters including:

```text
loop_inner_diameter
loop_width
loop_raise
```

The outer diameter is derived from:

```text
loop_inner_diameter + 2 * loop_width
```

`loop_raise` should default according to the total physical raise semantics of
the owning Model.

Before implementation, settle in each applicable Model definition:

* how loop participation is determined from effective parameter values;
* attachment position and orientation;
* the mechanical overlap required to attach it to the primary geometry;
* whether the loop extends beyond the size-controlled primary geometry;
* how `loop_raise` is derived when not overridden;
* color/material behavior; and
* interaction with other relevant Features.

The same conceptual Feature in Artwork and Shape remains Model-owned in each
case.

Similar Model semantics do not require one Model to invoke another Model's
Feature or Stage implementation.

If implementation reveals a genuinely identical Model-independent mechanical
operation, it may be shared through existing architectural mechanisms. Do not
create speculative abstraction merely because both Models have a Feature named
`loop`.

## 4.3 Additional Features

Other Features identified while completing this plan should follow the same
pattern:

```text
semantic decision
        ↓
Model DEFINITION
        ↓
focused Feature tests
        ↓
implementation
```

Do not add unrelated capabilities merely because the affected geometry is being
modified.

## 4.4 TDD

Feature tests should protect the semantics of the Feature itself.

They should not assert:

* the complete Feature inventory of the Model;
* unrelated Variant definitions;
* unrelated repository defaults; or
* implementation details not required by the Feature contract.

When existing Model tests are encountered, curate them according to
`TEST_DRIVEN_DEVELOPMENT.md`.

Adding a Feature should not require unrelated tests to enumerate or approve the
new Feature merely because the Model has grown.

## 4.5 Completion

Phase 4 is complete when the required Model-owned Features are specified,
tested, and configurable through the Model's parameters independently of any
particular specialized Variant.

---

# Phase 5 — Add Variants Using the New Features

After the underlying Features are complete, add named Variants that configure
those capabilities into useful Artifact Realizations.

A Variant does not own or contain Features.

A Variant supplies sparse overrides to Model parameters. Those effective
parameter values may affect Feature participation according to the semantics of
the Model.

## 5.1 Artwork Variants

Add the planned Artwork Variants, including:

```text
artwork.charm
artwork.ear_rings
```

Preserve these names unless a later explicit design decision changes them.

Each Variant should specify only the parameter values that distinguish it from
ordinary Artwork behavior.

For example, a loop-using Artwork Variant may override appropriate:

```text
loop_inner_diameter
loop_width
loop_raise
```

values without redefining the loop Feature or repeating unrelated Model
defaults.

Exact Variant parameter values should be selected as product/design decisions
before their tests are written.

## 5.2 Additional Variants

Additional Artwork or Shape Variants may be added when they represent a useful
named reusable configuration of already-supported Model capabilities.

Do not add new Feature semantics to a Variant merely to avoid defining the
capability in its owning Model.

If a proposed Variant requires behavior the Model does not yet support, add or
extend the applicable Model Feature first.

## 5.3 TDD

Variant tests should be inexpensive.

They should primarily establish:

* Variant registration/discovery;
* intended sparse parameter overrides;
* inheritance of unspecified Model parameter defaults;
* qualified Variant identity; and
* selection where the Variant introduces a meaningful selection case.

Do not repeat Feature geometry tests for each Variant.

Add acceptance coverage only where a Variant establishes a meaningful
user-visible integration not already protected by Feature, configuration, and
selection tests.

## 5.4 Completion

Phase 5 is complete when the desired named Variants configure the established
Model capabilities through sparse parameter overrides and can be selected and
built through the existing Variant workflow.

---

# Completion Criteria

This change plan is complete when:

1. the work remains aligned with `ARCHITECTURE.md` and the applicable Model
   `DEFINITION.md` files;
2. standalone `artwork_size` measures the occupied Artwork envelope as
   documented;
3. successfully packaged Variant 3MF files are published conveniently in the
   Artifact home directory without becoming additional Products;
4. Artifact configuration uses qualified Variant tables rather than the
   historical user-facing Realization schema;
5. the required Model-owned Features are implemented according to their Model
   definitions and configured through Model parameters;
6. the desired Variants configure Model behavior through sparse parameter
   overrides;
7. tests encountered during the work have been curated according to
   `TEST_DRIVEN_DEVELOPMENT.md`;
8. focused and broader regression suites pass; and
9. no unnecessary large-scale redesign has been introduced.

The guiding principle for this plan is:

> Preserve the architecture, clarify Model semantics where necessary, correct
> demonstrated behavior, and extend the system only as much as the requested
> capabilities require.

