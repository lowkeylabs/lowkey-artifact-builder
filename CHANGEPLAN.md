# Change Plan

This change plan captures the remaining Artifact configuration and Model
capability work.

The intended work is evolutionary.

`ARCHITECTURE.md` and the applicable Model `DEFINITION.md` files are the
permanent specifications. This change plan is subordinate to those
specifications. When language or assumptions in this plan conflict with the
permanent specifications, the permanent specifications rule.

Implementation should follow:

```text
prompts/TEST_DRIVEN_DEVELOPMENT.md
```

Tests encountered during this work should be curated according to that policy.
Do not create a separate broad test-cleanup effort.

---

# Phase 0 — Clarify the Permanent Architecture

Before changing Artifact configuration or production behavior, tidy
`ARCHITECTURE.md` so that the permanent specification clearly expresses the
Artifact, Variant, Realization, Stage, and Product relationships required by
the remaining work.

This phase should recover and clarify the intended architecture rather than
introduce a new one.

## 0.1 Preserve Model, Feature, and Parameter Semantics

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

Generic configuration, graph, planning, and execution infrastructure must not
contain Model-specific Feature semantics.

Do not introduce:

* a separate generic Feature-selection mechanism; or
* a parameter-ownership hierarchy beneath Features.

Parameters remain Model-owned configuration.

## 0.2 Clarify Variant Semantics

A Variant is a named, Model-scoped reusable configuration expressed as sparse
parameter overrides over Model defaults.

A Variant:

* belongs to exactly one Model;
* has a local name;
* has a qualified identity such as `shape.ornament`;
* may have a description;
* supplies sparse parameter overrides;
* does not contain or independently select Features; and
* does not define the limits of what the Model can construct.

Variants provide convenient starting configurations and representative catalog
examples of useful things that can be constructed from a Model's capabilities.

The `default` Variant always exists and may contain no parameter overrides
because Model parameter defaults establish ordinary Model behavior.

A new Variant should not be required merely to use capabilities already
provided by the Model.

## 0.3 Clarify Artifact Semantics

An Artifact is the durable source and configuration context from which one or
more builds may be realized.

An Artifact commonly associates an Artifact identifier with source material
such as a base PNG and with the named Realizations that should be reproducibly
buildable from that source.

`artifact.toml` is the user/developer-facing durable build manifest for that
Artifact.

An Artifact is not itself a Stage Product.

## 0.4 Clarify Realization Semantics

A Realization is a named, Artifact-scoped application of a Variant.

A Realization identifies one concrete configured build of an Artifact.

Each Realization:

* has an Artifact-local name;
* selects exactly one qualified Variant;
* therefore selects the Variant's Model;
* may provide sparse Realization-specific parameter overrides;
* may bind dependencies as required by the dependency architecture;
* has independently resolved configuration;
* has independent build state; and
* has its own Stage Products.

An Artifact may define zero, one, or many Realizations.

Multiple Realizations of the same Artifact may select the same Variant while
differing in configuration.

For example:

```toml
source = "customer.png"

[realizations.ornament-120]
variant = "shape.ornament"
shape_size = 120

[realizations.ornament-150]
variant = "shape.ornament"
shape_size = 150
```

defines two Realizations derived from the same Variant:

```text
ornament-120
    Variant: shape.ornament
    shape_size: 120

ornament-150
    Variant: shape.ornament
    shape_size: 150
```

The term Realization reflects the role of realizing or actualizing an Artifact
through a particular configured application of a Model Variant.

Realization must remain distinct from Variant.

## 0.5 Clarify Stage and Product Semantics

A Stage is a unit of build execution.

A Product is a persistent output produced by a Stage.

A Realization's build executes the Stages required by the requested dependency
closure, and those Stages produce Products.

For example, `artifact.3mf` is a Product. It may be the Product ultimately
desired from a particular build, but it is not architecturally privileged over
other Products.

Keep these concepts distinct:

```text
Feature
    = Model capability

Parameter
    = configuration controlling Model behavior and Feature participation

Variant
    = reusable named Model configuration and catalog starting point

Artifact
    = durable source and configuration context

Realization
    = named Artifact-scoped configured application of a Variant

Stage
    = unit of build execution

Product
    = persistent output of a Stage
```

## 0.6 Clarify Configuration Resolution

Preserve the architectural resolution model:

```text
Model parameter defaults
        ↓
Variant parameter overrides
        ↓
Realization parameter overrides
        ↓
effective Realization configuration
```

A Realization starts from a Variant but is not constrained to the exact
configuration represented by that Variant.

For example, a Realization may start from `shape.default` and override whatever
Model parameters are necessary to construct a configuration not represented by
a named Variant.

If such a configuration later becomes sufficiently useful or common, it may be
added as another reusable Variant.

The same resolver framework should determine effective configuration regardless
of whether values originate from Model defaults, Variant overrides, or
Realization overrides.

## 0.7 Clarify Realization and Product Identity

Persistent build state and Product namespaces are scoped by Realization, not by
Variant.

For example:

```text
artifacts/<artifact-id>/shape/ornament-120/...
artifacts/<artifact-id>/shape/ornament-150/...
```

represent independent build namespaces even though both Realizations may select:

```text
shape.ornament
```

Each may independently contain a Product such as:

```text
.../ornament-120/.../artifact.3mf
.../ornament-150/.../artifact.3mf
```

Preserve logical Product identity based on:

```text
Artifact / Model / Realization / Stage / Product
```

Variant identity provides configuration provenance. It does not replace
Realization identity in persistent Product namespaces.

## 0.8 Preserve Product Architecture

Preserve the following architectural invariants:

* persistent Stage outputs remain first-class Products;
* no packaged 3MF becomes an architecturally privileged final Product;
* logical Product identity remains independent of filesystem location;
* dependency-driven execution remains authoritative;
* build only what is required by the requested Product dependency closure; and
* convenience publication of a Product does not establish another Product
  identity.

## 0.9 Completion

Phase 0 is complete when `ARCHITECTURE.md` clearly and consistently establishes:

* Artifact as the durable source/configuration context;
* Variant as reusable Model configuration;
* Realization as the Artifact-scoped configured application of a Variant;
* the ability for multiple Realizations to select the same Variant;
* Realization-scoped build and Product identity;
* Stage and Product semantics;
* configuration precedence through Model, Variant, and Realization values; and
* the role of Variants as useful catalog configurations rather than limits on
  Model capability.

No production implementation is required merely to complete Phase 0.

---

# Phase 1 — Simplify Artifact Realization Configuration

Establish a simple, durable user/developer-facing `artifact.toml` format that
directly represents the Realizations to be built from an Artifact.

The public configuration should expose the architectural distinction between
Variant and Realization while preserving the existing resolver, planning,
Stage, and Product architecture.

## 1.1 Canonical artifact.toml Grammar

Use named Realization tables as the canonical user-facing representation.

The intended form is:

```toml
source = "customer.png"

[realizations.ornament-120]
variant = "shape.ornament"
shape_size = 120
shape_top_text = "Happy Holidays"
shape_bottom_text = "2026"

[realizations.ornament-150]
variant = "shape.ornament"
shape_size = 150
shape_top_text = "Happy Holidays"
shape_bottom_text = "2026"

[realizations.coaster]
variant = "shape.default"
shape_size = 100
shape_outer_ridge_width = 2
```

The table name identifies the Realization:

```text
ornament-120
ornament-150
coaster
```

The `variant` value identifies the reusable starting configuration:

```text
shape.ornament
shape.default
```

A qualified Variant identity identifies both the Model and the Variant's local
name.

Do not redundantly require a separate `model` field.

Realization-specific parameter overrides should be represented directly as
key-value pairs in the Realization table.

Do not require an additional:

```toml
[realizations.<name>.parameters]
```

table merely to distinguish parameter overrides.

The public grammar should remain small.

Reserved Realization metadata keys must be explicit. Other scalar
configuration keys must correspond to parameters recognized by the selected
Model rather than being accepted as arbitrary unvalidated data.

Nested structures should be introduced only where an existing architectural
concept, such as dependency binding, genuinely requires structure that cannot
be represented as an ordinary Model parameter.

## 1.2 Preserve Variant Semantics

A Realization selects a Variant as its starting configuration.

It does not modify that Variant.

For example:

```toml
[realizations.special]
variant = "shape.default"
shape_size = 137
shape_outer_ridge_width = 3
```

does not define a new Shape Variant.

It defines a Realization whose effective configuration is derived from:

```text
Shape Model defaults
        ↓
shape.default overrides
        ↓
special Realization overrides
```

A named specialized Variant is not required to construct a Realization when
the Model already exposes the necessary capabilities through parameters.

If a useful configuration becomes common or representative enough to deserve a
reusable name, it may later be added to the Model's Variant catalog.

## 1.3 Keep Public Serialization at the Artifact I/O Boundary

The public `artifact.toml` representation does not need to mirror internal
Python object structure.

Treat the existing Artifact TOML loading and writing functions as the
translation boundary.

Update:

```text
load_artifact_toml
write_artifact_toml
```

as necessary so they translate between:

```text
flat user-facing artifact.toml
        ↕
existing internal Model / Variant / Realization configuration structures
```

Prefer containing the public grammar change at this boundary.

Do not propagate a new configuration hierarchy through the resolver, planner,
or Model implementation merely because the public serialization has changed.

Preserve the existing resolver precedence:

```text
Model defaults
        ↓
Variant overrides
        ↓
Realization overrides
        ↓
effective configuration
```

Changing `artifact.toml` syntax must not create another parameter-resolution
mechanism.

## 1.4 Realization Identity and Persistent Build State

Ensure that actual Realization identity, rather than Variant local name, flows
through any existing runtime paths where the distinction matters.

For:

```toml
[realizations.ornament-120]
variant = "shape.ornament"
shape_size = 120

[realizations.ornament-150]
variant = "shape.ornament"
shape_size = 150
```

persistent build state should remain independently addressable as:

```text
artifacts/<artifact-id>/shape/ornament-120/...
artifacts/<artifact-id>/shape/ornament-150/...
```

Each Realization may independently contain Products such as:

```text
.../ornament-120/.../artifact.3mf
.../ornament-150/.../artifact.3mf
```

The Variant local name must not be substituted for Realization identity where
doing so would cause distinct Realizations of the same Variant to share
configuration, build state, or Product namespaces.

Preserve the existing logical Product identity model based on Artifact, Model,
Realization, Stage, and Product coordinates.

Do not add Variant as another persistent Product-identity coordinate merely to
record configuration provenance.

## 1.5 Package Publication

Preserve the completed package-publication behavior while ensuring published
filenames distinguish Realizations rather than merely Variants.

Two Realizations based on `shape.ornament` must be publishable independently.

For example:

```text
shape.ornament-120.3mf
shape.ornament-150.3mf
```

may represent convenience copies of the corresponding canonical package
Products.

Published files remain convenience copies.

They are not:

* additional Products;
* dependency targets;
* replacements for canonical Stage Products; or
* evidence that packaged Products are architecturally privileged.

Publication naming should derive from actual Realization identity and must not
collide merely because two Realizations select the same Variant.

## 1.6 Artifact Creation

Update:

```text
artifact create
```

to emit only the canonical Realization-oriented configuration form.

Creation should produce named Realizations selecting qualified Variants and
should write Realization parameter overrides using the flat key-value grammar.

Do not redesign interactive or non-interactive Artifact creation beyond what is
required to emit and consume the canonical configuration.

## 1.7 TDD

Treat the public Artifact configuration grammar as an intentional contract.

Tests should establish at least:

* parsing of a named Realization;
* selection of a qualified Variant;
* Model identity implied by the qualified Variant;
* direct Realization parameter overrides;
* inheritance of Model defaults;
* inheritance of Variant overrides;
* Realization overrides taking precedence over Variant values;
* multiple Realizations in one Artifact;
* multiple Realizations selecting the same Variant;
* independent configuration for Realizations selecting the same Variant;
* independent Product/filesystem namespaces for those Realizations;
* rejection of unknown Model parameters;
* writing the canonical flat form;
* round-trip loading and writing where appropriate;
* `artifact create` emission of the canonical form; and
* collision-free publication of packaged Products from multiple Realizations of
  the same Variant.

Prefer tests at the Artifact configuration I/O boundary for serialization
behavior.

Do not duplicate resolver, planner, Product, or Model tests merely because the
public TOML representation has changed.

Where existing tests encode the accidental conflation of Variant local name and
Realization identity, replace or correct them according to
`TEST_DRIVEN_DEVELOPMENT.md`.

## 1.8 Completion

Phase 1 is complete when:

* `artifact.toml` durably describes the named Realizations associated with an
  Artifact;
* every Realization selects a qualified Variant;
* Realization-specific Model parameter overrides use the canonical flat
  key-value grammar;
* Artifact loading and writing translate that grammar into the existing
  internal configuration architecture;
* multiple Realizations may select the same Variant without configuration,
  filesystem, Product, or publication collisions;
* the existing resolver precedence is preserved; and
* no unnecessary new configuration or identity mechanism has been introduced.

---

# Phase 2 — Extend Model Capabilities

Add the desired manufacturing capabilities as Features of the Models that own
them.

Features belong to Models.

Models declare the parameters used to configure Feature behavior.

Effective parameter values may enable, disable, or otherwise affect Feature
participation according to Model-owned semantics.

Once a Model capability is exposed through Model parameters, it is immediately
available to any Realization of that Model.

A specialized Variant is not required merely to expose an existing Feature.

## 2.1 Specify Features Before Implementation

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

## 2.2 Loop Feature

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

## 2.3 Additional Features

Other required Features should follow the same pattern:

```text
semantic decision
        ↓
Model DEFINITION
        ↓
focused Feature tests
        ↓
implementation
```

Do not add unrelated capabilities merely because affected geometry is already
being modified.

A Feature is complete only when its Model parameters are sufficient for an
ordinary Realization to configure and use it without requiring a specialized
Variant.

For example, after a loop Feature exists, configuration such as:

```toml
[realizations.custom]
variant = "shape.default"
shape_size = 100
loop_inner_diameter = 5
loop_width = 2
loop_raise = 4
```

should be sufficient to use the capability according to the Shape Model's
defined semantics.

## 2.4 Variants as Reusable Catalog Configurations

After the underlying Model capabilities exist, useful named Variants may be
added as reusable and representative configurations.

Examples may include:

```text
artwork.charm
artwork.ear_rings
```

or other Artwork or Shape configurations that represent useful constructions
from already-supported Model capabilities.

Adding such a Variant should ordinarily require only:

* Variant registration;
* a name and description as appropriate; and
* sparse parameter overrides.

A Variant must not introduce new Feature semantics.

If a proposed Variant requires behavior the Model does not yet support, extend
the applicable Model Feature first.

Variants collectively provide a useful catalog of representative constructions,
but that catalog does not define the limits of the Model.

A Realization may always start from the closest available Variant, including
`default`, and supply additional parameter overrides.

## 2.5 TDD

Feature tests should protect the semantics of the Feature itself.

They should not assert:

* the complete Feature inventory of the Model;
* unrelated Variant definitions;
* unrelated repository defaults; or
* implementation details not required by the Feature contract.

Adding a Feature should not require unrelated tests to enumerate or approve the
new Feature merely because the Model has grown.

Tests for a new Variant should be inexpensive and should primarily establish:

* Variant registration/discovery;
* intended sparse parameter overrides;
* inheritance of unspecified Model parameter defaults; and
* qualified Variant identity.

Do not repeat Feature geometry tests for every Variant.

Add acceptance coverage only where a Feature or Variant establishes a
meaningful user-visible integration not already protected at a lower boundary.

## 2.6 Completion

Phase 2 is complete when:

* the required Model-owned Features are specified and tested;
* their behavior is configurable through Model parameters;
* arbitrary Realizations can use those capabilities without requiring new
  Variants;
* useful reusable configurations may be added as lightweight Model Variants;
  and
* no Feature semantics have been moved into Variant or generic engine
  infrastructure.

---

# Completion Criteria

This change plan is complete when:

1. `ARCHITECTURE.md` clearly establishes the Artifact, Variant, Realization,
   Stage, and Product relationships required by the system;
2. `artifact.toml` is a durable declaration of named Artifact Realizations;
3. each Realization selects a qualified Variant and may directly override Model
   parameters;
4. the Artifact TOML reader and writer translate the public flat grammar without
   introducing another internal configuration mechanism;
5. multiple Realizations may use the same Variant while retaining independent
   configuration, build state, Products, filesystem namespaces, and published
   package filenames;
6. configuration continues to resolve through Model defaults, Variant
   overrides, and Realization overrides;
7. the required Model-owned Features are implemented according to their Model
   definitions;
8. new Model capabilities become immediately available to Realizations through
   Model parameters without requiring specialized Variants;
9. useful Variants remain lightweight reusable/catalog configurations of
   already-supported Model behavior;
10. tests encountered during the work are curated according to
    `TEST_DRIVEN_DEVELOPMENT.md`;
11. focused and broader regression suites pass; and
12. no unnecessary large-scale redesign has been introduced.

The guiding principle for this plan is:

> Models provide capabilities. Variants provide reusable starting
> configurations. Artifacts provide source and durable build context.
> Realizations describe the concrete Artifact-scoped builds we want. Stages
> produce the Products required to realize them.
