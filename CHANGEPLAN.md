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

Phase 0 establishes the permanent Artifact, Variant, Realization, Stage, and
Product relationships required by the remaining work.

`ARCHITECTURE.md` is authoritative for these semantics.

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

## 0.2 Preserve Variant Semantics

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

## 0.3 Preserve Artifact Semantics

An Artifact is the durable source and configuration context from which builds
may be realized.

An Artifact commonly associates an Artifact identifier with source material
such as a base PNG and with Artifact-specific configuration.

`artifact.toml` is the user/developer-facing durable build manifest for that
Artifact.

An Artifact is not itself a Stage Product.

The set of Realizations available for an Artifact is not limited to
Realizations explicitly serialized in `artifact.toml`.

## 0.4 Preserve Realization Semantics

A Realization is a named, Artifact-scoped application of a Variant.

A Realization identifies one concrete configured build of an Artifact.

Each Realization:

* has an Artifact-local name;
* originates from exactly one qualified Variant;
* therefore has exactly one Model;
* may provide sparse Realization-specific parameter overrides;
* may bind dependencies as required by the dependency architecture;
* has independently resolved configuration;
* has independent build state; and
* has its own Stage Products.

For every Model Variant available to an Artifact, the system provides a
corresponding default Realization without requiring an explicit Realization
declaration in `artifact.toml`.

The canonical default Realization name is:

```text
<model>_<variant-local-name>
```

For example:

```text
artwork.default   -> artwork_default
shape.default     -> shape_default
shape.ornament    -> shape_ornament
```

A default Realization applies its Variant without Artifact-specific
Realization overrides unless the Artifact explicitly customizes that
Realization.

Artifact configuration may also define additional named Realizations.

Multiple Realizations of the same Artifact may originate from the same Variant
while differing in configuration.

For example, an Artifact may have:

```text
shape_ornament
    Variant: shape.ornament
    shape_size: Variant value

ornament-120
    Variant: shape.ornament
    shape_size: 120

ornament-150
    Variant: shape.ornament
    shape_size: 150
```

The first may be the automatically derived default Realization. The other two
may be additional Artifact-defined Realizations.

The term Realization reflects the role of realizing or actualizing an Artifact
through a particular configured application of a Model Variant.

Realization must remain distinct from Variant.

## 0.5 Preserve Effective Realization Discovery

The effective Realization set for an Artifact consists of:

```text
default Realizations derived from available Variants
        +
Artifact customization of those default Realizations
        +
additional Artifact-defined Realizations
```

Omission of a default Realization from `artifact.toml` does not remove it.

A minimal Artifact such as:

```toml
source = "customer.png"
```

may therefore have an effective Realization set such as:

```text
artwork_default
shape_default
shape_ornament
```

when the corresponding Variants are available.

Artifact configuration should not be required merely to restate the Model-owned
Variant catalog.

## 0.6 Preserve Stage and Product Semantics

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

## 0.7 Preserve Configuration Resolution

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

For example, an additional Realization may start from `shape.default` and
override whatever Model parameters are necessary to construct a configuration
not represented by a named Variant.

If such a configuration later becomes sufficiently useful or common, it may be
added as another reusable Variant.

The same resolver framework should determine effective configuration regardless
of whether values originate from Model defaults, Variant overrides, or
Realization overrides.

## 0.8 Preserve Realization and Product Identity

Persistent build state and Product namespaces are scoped by Realization, not by
Variant.

For example:

```text
artifacts/<artifact-id>/shape/shape_ornament/...
artifacts/<artifact-id>/shape/ornament-120/...
artifacts/<artifact-id>/shape/ornament-150/...
```

may represent independent build namespaces even though all three Realizations
select:

```text
shape.ornament
```

Preserve logical Product identity based on:

```text
Artifact / Model / Realization / Stage / Product
```

Variant identity provides configuration provenance. It does not replace
Realization identity in persistent Product namespaces.

## 0.9 Preserve Product Architecture

Preserve the following architectural invariants:

* persistent Stage outputs remain first-class Products;
* no packaged 3MF becomes an architecturally privileged final Product;
* logical Product identity remains independent of filesystem location;
* dependency-driven execution remains authoritative;
* build only what is required by the requested Product dependency closure; and
* convenience publication of a Product does not establish another Product
  identity.

## 0.10 Completion

Phase 0 is complete when `ARCHITECTURE.md` clearly and consistently establishes:

* Artifact as the durable source/configuration context;
* Variant as reusable Model configuration;
* Realization as the Artifact-scoped configured application of a Variant;
* a default Realization for every available Variant;
* canonical default Realization naming;
* effective Realization discovery independent of explicit Artifact declarations;
* the ability to customize a default Realization;
* the ability to define additional Realizations;
* the ability for multiple Realizations to select the same Variant;
* Realization-scoped build and Product identity;
* Stage and Product semantics;
* configuration precedence through Model, Variant, and Realization values; and
* the role of Variants as useful catalog configurations rather than limits on
  Model capability.

No production implementation is required merely to complete Phase 0.

With the corresponding permanent semantics present in `ARCHITECTURE.md`, this
phase is complete.

---

# Phase 1 — Simplify Artifact Realization Configuration

Establish the effective Realization catalog and a simple, durable
user/developer-facing `artifact.toml` format.

The common case should require as little Artifact configuration as possible.

A valid Artifact may consist only of:

```toml
source = "customer.png"
```

The system must still discover and be capable of building the default
Realization corresponding to every available Model Variant.

Explicit Artifact configuration exists to customize those default Realizations
or to define additional Artifact-specific Realizations. It must not be required
merely to reproduce the Model-owned Variant catalog.

Preserve the existing resolver, planning, Stage, Product, and dependency
architecture wherever possible.

## 1.1 Derive Default Realizations

Establish the effective default Realization catalog from the registered Model
Variant catalog.

For every available qualified Variant:

```text
<model>.<variant-local-name>
```

derive a default Realization named:

```text
<model>_<variant-local-name>
```

For example:

```text
artwork.default   -> artwork_default
shape.default     -> shape_default
shape.ornament    -> shape_ornament
```

The default Realization:

* exists without an explicit `[realizations.*]` table;
* selects the Variant from which it was derived;
* therefore selects that Variant's Model;
* begins with no Artifact-specific Realization parameter overrides;
* resolves configuration through ordinary Model and Variant precedence;
* has its own Realization identity;
* has independently addressable build state; and
* participates in ordinary planning and Product resolution.

Do not serialize redundant Realization declarations merely to make the Variant
catalog discoverable.

Do not treat the absence of a `[realizations]` table as the absence of
Realizations.

The effective Realization catalog should be derived from authoritative Model
and Variant registration rather than duplicated in Artifact configuration.

## 1.2 Customize Default Realizations

Allow Artifact configuration to customize a derived default Realization.

For example:

```toml
source = "customer.png"

[realizations.shape_ornament]
shape_size = 120
```

customizes the automatically derived:

```text
shape_ornament -> shape.ornament
```

Realization.

The table does not create a second `shape_ornament` Realization.

It applies Artifact-specific Realization configuration to the existing default
Realization.

The selected Variant is already implied by the canonical default Realization
identity and therefore need not be redundantly stated.

Effective configuration remains:

```text
Shape Model defaults
        ↓
shape.ornament overrides
        ↓
shape_ornament Realization overrides
        ↓
effective configuration
```

A default Realization with no Artifact customization must behave the same
whether or not an empty customization table is present.

Reserved Realization metadata keys must remain explicit.

Other scalar configuration keys must correspond to parameters recognized by
the Realization's Model rather than being accepted as arbitrary unvalidated
data.

## 1.3 Define Additional Named Realizations

Artifact configuration may define additional named Realizations that do not
correspond to canonical default Realization names.

For example:

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
```

defines two additional Realizations derived from the same Variant.

For an additional Realization, the `variant` value identifies the reusable
starting configuration:

```text
shape.ornament
```

The qualified Variant identity identifies both the Model and the Variant's
local name.

Do not redundantly require a separate `model` field.

Realization-specific parameter overrides should be represented directly as
key-value pairs in the Realization table.

Do not require an additional:

```toml
[realizations.<name>.parameters]
```

table merely to distinguish parameter overrides.

An additional Realization selects a Variant as its starting configuration. It
does not modify that Variant.

For example:

```toml
[realizations.special]
variant = "shape.default"
shape_size = 137
shape_outer_ridge_width = 3
```

defines:

```text
Shape Model defaults
        ↓
shape.default overrides
        ↓
special Realization overrides
```

It does not define another Shape Variant.

A named specialized Variant is not required to construct a Realization when
the Model already exposes the necessary capabilities through parameters.

If a useful configuration becomes common or representative enough to deserve a
reusable name, it may later be added to the Model's Variant catalog.

## 1.4 Establish Canonical artifact.toml I/O

Treat Artifact TOML loading and writing as the public serialization boundary.

The public representation does not need to mirror internal Python object
structure.

The canonical Artifact grammar should support all of these cases.

Minimal Artifact:

```toml
source = "customer.png"
```

Customization of a default Realization:

```toml
source = "customer.png"

[realizations.shape_ornament]
shape_size = 120
```

Additional Realization:

```toml
source = "customer.png"

[realizations.large-ornament]
variant = "shape.ornament"
shape_size = 150
```

Combined configuration:

```toml
source = "customer.png"

[realizations.shape_ornament]
shape_size = 120

[realizations.large-ornament]
variant = "shape.ornament"
shape_size = 150
```

The resulting effective Realization set may include:

```text
artwork_default
shape_default
shape_ornament
large-ornament
```

depending on the registered Variant catalog.

Update the existing Artifact TOML loading and writing boundary as necessary so
it translates between:

```text
minimal flat user-facing artifact.toml
        ↕
effective Model / Variant / Realization configuration
```

Prefer containing serialization concerns at this boundary.

Do not propagate a new parameter-resolution hierarchy through the resolver,
planner, or Model implementation merely because the public serialization has
changed.

Preserve:

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

When writing canonical Artifact configuration, do not emit derived default
Realizations that contain no Artifact-specific configuration.

## 1.5 Preserve Realization Identity and Persistent Build State

Ensure that actual Realization identity, rather than Variant local name, flows
through runtime paths where the distinction matters.

For an Artifact with:

```text
shape_ornament
ornament-120
ornament-150
```

where all three select:

```text
shape.ornament
```

persistent build state must remain independently addressable, for example:

```text
artifacts/<artifact-id>/shape/shape_ornament/...
artifacts/<artifact-id>/shape/ornament-120/...
artifacts/<artifact-id>/shape/ornament-150/...
```

Each Realization may independently contain Products such as:

```text
.../shape_ornament/.../artifact.3mf
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

## 1.6 Integrate Effective Realizations with Planning and Build Selection

Default Realizations must be operational Realizations, not merely configuration
metadata.

Planning and build selection must operate over the effective Realization set.

A source-only Artifact such as:

```toml
source = "customer.png"
```

must be capable of building its derived default Realizations without requiring
the user to add redundant Realization declarations.

Given available Variants such as:

```text
artwork.default
shape.default
shape.ornament
```

the corresponding effective Realizations:

```text
artwork_default
shape_default
shape_ornament
```

must be individually addressable by the build/planning architecture.

Operations that intentionally request all applicable Realizations or all
available Variant-derived constructions must include the derived default
Realizations.

Preserve dependency-driven planning.

Do not eagerly execute every Realization merely because it is discoverable.

A request for one Realization should still build only the Product dependency
closure required by that request.

Where one Realization depends on Products from another Model or Realization,
preserve the existing dependency architecture rather than adding special-case
execution ordering for default Realizations.

Do not introduce a second build-planning mechanism for implicit Realizations.

## 1.7 Package Publication

Preserve the completed package-publication behavior while ensuring published
filenames distinguish Realizations rather than merely Variants.

Default and additional Realizations based on the same Variant must be
publishable independently.

For example:

```text
shape.shape_ornament.3mf
shape.ornament-120.3mf
shape.ornament-150.3mf
```

may represent convenience copies of corresponding canonical package Products,
subject to the existing publication naming convention.

Published files remain convenience copies.

They are not:

* additional Products;
* dependency targets;
* replacements for canonical Stage Products; or
* evidence that packaged Products are architecturally privileged.

Publication naming must derive from actual Realization identity and must not
collide merely because multiple Realizations originate from the same Variant.

Do not change publication naming beyond what is required to preserve
Realization identity and collision freedom.

## 1.8 Artifact Creation

Update:

```text
artifact create
```

to emit canonical Artifact configuration without redundantly serializing the
derived default Realization catalog.

When no Artifact-specific customization is required, creation should be able to
produce the minimal form:

```toml
source = "customer.png"
```

When a default Realization is customized, creation should serialize only the
necessary Artifact-specific customization.

When an additional Realization is requested, creation should serialize its
qualified Variant selection and flat Realization parameter overrides.

Do not redesign interactive or non-interactive Artifact creation beyond what is
required to emit and consume the canonical configuration.

## 1.9 TDD and Integration

Treat effective Realization discovery and the public Artifact configuration
grammar as intentional contracts.

Proceed in coherent behavioral slices.

### Slice A — Default Realization Discovery

Tests should first establish that:

* every available Variant contributes one default Realization;
* the `default` Variant participates exactly like any other Variant;
* canonical default Realization names follow
  `<model>_<variant-local-name>`;
* a source-only Artifact discovers its default Realizations;
* a default Realization resolves the correct Model;
* a default Realization resolves the correct Variant;
* Model parameter defaults are inherited;
* Variant parameter overrides are inherited; and
* derived default Realizations do not require explicit Artifact declarations.

Use synthetic Models and Variants where the behavior under test belongs to
generic infrastructure.

### Slice B — Default Realization Customization

Tests should establish that:

* a canonical default Realization may be explicitly customized;
* customization does not create a duplicate Realization;
* the Variant need not be redundantly specified for that customization;
* direct flat parameter overrides are accepted;
* Realization overrides take precedence over Variant values;
* unspecified Variant and Model values continue to be inherited;
* an unknown parameter is rejected according to existing configuration
  validation semantics; and
* configuration does not leak between Realizations.

### Slice C — Additional Realizations

Tests should establish that:

* an additional named Realization may select a qualified Variant;
* Model identity is implied by that qualified Variant;
* multiple additional Realizations may select the same Variant;
* default and additional Realizations may select the same Variant;
* each retains independent effective configuration; and
* invalid or unknown Variant selections are rejected.

### Slice D — Serialization

Tests should establish that:

* a source-only Artifact loads correctly;
* default Realizations need not be serialized;
* default Realization customizations use the canonical flat form;
* additional Realizations use qualified Variant identity;
* a separate redundant `model` field is not required;
* nested parameter tables are not required;
* writing omits uncustomized derived default Realizations;
* canonical writing preserves necessary Artifact-specific configuration; and
* round-trip loading and writing preserve the durable Artifact configuration
  semantics where appropriate.

Prefer tests at the Artifact configuration I/O boundary for serialization
behavior.

### Slice E — Planning, Identity, and Products

Tests should establish that:

* derived default Realizations are individually planable/buildable;
* planning uses actual Realization identity;
* multiple Realizations selecting the same Variant have independent
  Product/filesystem namespaces;
* default and additional Realizations do not collide;
* requesting one Realization does not eagerly build unrelated Realizations;
* dependency-driven execution remains authoritative; and
* operations requesting the complete applicable Realization set include the
  derived defaults.

### Slice F — Creation and Publication

Tests should establish that:

* `artifact create` can emit the minimal source-only form;
* `artifact create` does not enumerate uncustomized default Realizations;
* customized default Realizations are emitted canonically;
* additional Realizations are emitted canonically; and
* packaged Products from multiple Realizations of the same Variant publish
  without collisions.

Do not duplicate resolver, planner, Product, or Model tests merely because the
public TOML representation has changed.

Where existing tests encode the accidental conflation of Variant local name and
Realization identity, replace or correct them according to
`TEST_DRIVEN_DEVELOPMENT.md`.

Where existing tests assume that Realizations exist only when declared in
`artifact.toml`, replace or correct those assumptions according to the
permanent architecture.

## 1.10 Completion

Phase 1 is complete when:

* every available Model Variant contributes a canonical default Realization;
* a source-only Artifact discovers those default Realizations;
* the `default` Variant participates in automatic Realization discovery;
* default Realizations need not be redundantly serialized;
* Artifact configuration may customize a default Realization;
* Artifact configuration may define additional named Realizations;
* additional Realizations select qualified Variants;
* Realization-specific Model parameter overrides use the canonical flat
  key-value grammar;
* Artifact loading and writing translate the public grammar into the existing
  configuration architecture;
* effective configuration continues to resolve through Model defaults, Variant
  overrides, and Realization overrides;
* default and additional Realizations participate in ordinary planning and
  dependency-driven builds;
* multiple Realizations may originate from the same Variant without
  configuration, filesystem, Product, or publication collisions;
* `artifact create` does not redundantly reproduce the Model-owned Variant
  catalog; and
* no unnecessary new configuration, identity, or planning mechanism has been
  introduced.

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

Every new Variant also becomes eligible for the corresponding automatically
derived default Realization according to the permanent architecture.

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
* inheritance of unspecified Model parameter defaults;
* qualified Variant identity; and
* availability through the generic default-Realization discovery behavior
  without requiring Variant-specific realization plumbing.

Do not repeat Feature geometry tests for every Variant.

Do not add one-off Realization registration code merely because a Variant was
added. Generic Variant discovery should make its default Realization available.

Add acceptance coverage only where a Feature or Variant establishes a
meaningful user-visible integration not already protected at a lower boundary.

## 2.6 Completion

Phase 2 is complete when:

* the required Model-owned Features are specified and tested;
* their behavior is configurable through Model parameters;
* arbitrary Realizations can use those capabilities without requiring new
  Variants;
* useful reusable configurations may be added as lightweight Model Variants;
* newly registered Variants automatically participate in default Realization
  discovery; and
* no Feature semantics have been moved into Variant or generic engine
  infrastructure.

---

# Completion Criteria

This change plan is complete when:

1. `ARCHITECTURE.md` clearly establishes the Artifact, Variant, Realization,
   Stage, and Product relationships required by the system;

2. every available Model Variant contributes a canonical default Realization
   for an Artifact without requiring an explicit `artifact.toml` declaration;

3. the simplest useful Artifact may contain only its source configuration while
   still exposing its derived default Realizations;

4. default Realizations follow the canonical
   `<model>_<variant-local-name>` identity;

5. `artifact.toml` may customize a derived default Realization without
   redundantly selecting its Variant;

6. `artifact.toml` may define additional named Realizations that select
   qualified Variants and directly override Model parameters;

7. the Artifact TOML reader and writer translate the public flat grammar without
   introducing another internal parameter-resolution mechanism;

8. uncustomized default Realizations need not be serialized merely to make them
   discoverable or buildable;

9. multiple Realizations may originate from the same Variant while retaining
   independent configuration, build state, Products, filesystem namespaces,
   and published package filenames;

10. configuration continues to resolve through Model defaults, Variant
    overrides, and Realization overrides;

11. derived default Realizations participate in ordinary dependency-driven
    planning and build execution rather than requiring a separate build
    mechanism;

12. adding a Model Variant automatically makes its corresponding default
    Realization available without requiring Artifact configuration or
    Variant-specific engine changes;

13. the required Model-owned Features are implemented according to their Model
    definitions;

14. new Model capabilities become immediately available to Realizations through
    Model parameters without requiring specialized Variants;

15. useful Variants remain lightweight reusable/catalog configurations of
    already-supported Model behavior;

16. tests encountered during the work are curated according to
    `TEST_DRIVEN_DEVELOPMENT.md`;

17. focused and broader regression suites pass; and

18. no unnecessary large-scale redesign has been introduced.

The guiding principle for this plan is:

> Models provide capabilities. Variants provide reusable starting
> configurations. Artifacts provide source and durable build context.
> Every available Variant provides a default Artifact-scoped Realization.
> Artifact configuration customizes those defaults or adds additional
> Realizations. Stages produce the Products required to realize them.

