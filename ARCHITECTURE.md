# Architecture

This document defines the architectural model, terminology, relationships,
contracts, and invariants of `lowkey-artifact-builder`.

It is intended to be a durable reference for maintainers, contributors, and
automated development tools, including future LLM-assisted development.

The README describes how to install and use the project. This document
describes what the system means and how its major pieces are intended to
interact.

When implementation details conflict with this document, do not assume the
implementation defines the architecture. Determine whether the implementation
is incomplete or whether an architectural decision has intentionally changed.
If the architecture changes, update this document as part of that change.

---

# 1. Purpose

`lowkey-artifact-builder` is a dependency-driven build system for producing
2.5D manufacturing geometry from source artwork with minimal manual
intervention.

The common use case begins with a single PNG:

```text
                         source PNG
                             │
                             ▼
                           artwork
                             │
                    registered geometry
                             │
          ┌──────────────────┼──────────────────┐
          │                  │                  │
          ▼                  ▼                  ▼
      standalone          coaster           ornament
       artwork               │                  │
                             │                  │
                             └────────┐         │
                                      │         │
                                      ▼         ▼
                                  manufacturing
                                    geometry

                             │
                             └──────────────> keychain
```

The same interpreted artwork should be reusable across many manufactured
objects.

More advanced compositions are also supported:

```text
artwork A ──┐
artwork B ──┼──> registered composition ──> manufactured object
artwork C ──┘
```

The architecture should optimize the user experience for the common case
without restricting the dependency system to the common case.

The long-term objective is for new manufactured products to increasingly be
defined through configuration and composition of reusable operations rather
than new special-purpose Python pipelines.

---

# 2. Fundamental Principle

The fundamental persistent relationship is:

```text
Artifact
    │
    └── Model
          │
          └── Realization
                │
                └── Stage
                      │
                      └── Product
```

Models may also define named variants that provide reusable parameter presets.

A product may be consumed by:

* a later stage of the same realization;
* another realization of the same model;
* another model;
* another artifact;
* another build executed in the future.

The build system is therefore fundamentally a graph of products and the
operations that produce them.

A 3MF is merely one possible product in this graph.

---

# 3. Core Principles

## 3.1 Products are first-class

Every persistent output produced by a stage is a product.

Examples include:

```text
envelope.svg
trace.svg
color-1.png
color-1.svg
color-1.stl
products.json
artifact.3mf
```

The build engine does not architecturally distinguish between "intermediate"
and "final" products.

A product is important because something requests or depends upon it, not
because it appears at the end of a pipeline.

---

## 3.2 There is no privileged final product

A model is not defined by its final 3MF.

For example, an artwork model might contain:

```text
prepare
   ↓
raster
   ↓
vector
   ↓
extrude
   ↓
package
```

A consumer may require only:

```text
prepare:envelope
```

or:

```text
raster:colors
```

or:

```text
vector:colors
```

If nothing requires the extruded or packaged artwork, those stages do not
need to execute.

The fact that `package` produces a 3MF does not make that product
architecturally privileged.

---

## 3.3 Products are reusable manufacturing assets

Successfully generated products are persistent manufacturing assets.

For example, vectorizing source artwork may require substantial interpretation
and computation. Once generated, the registered vector geometry can be reused
to produce:

* standalone printed artwork;
* an ornament;
* a coaster;
* a keychain;
* a magnet;
* a plaque;
* a larger composition containing multiple pieces of artwork;
* future products not yet defined.

Reusable upstream work should not be repeated merely because a downstream
physical product has different dimensions or manufacturing parameters.

---

## 3.4 Dependencies determine execution

Stages and products form a dependency graph.

Numeric stage identifiers, declaration order, filesystem order, and the
concept of a "pipeline" do not determine execution order.

Dependencies determine execution.

The filesystem materializes the graph. It does not define the graph.

---

## 3.5 Logical identity is independent of filesystem location

Consumers refer to products by logical identity.

They do not refer to products using generated filesystem paths.

For example, a logical product reference might identify:

```text
nydeli:artwork:default:vector:colors
```

Its physical files might currently exist beneath:

```text
artifacts/nydeli/artwork/default/30-vector/
```

The logical reference is part of the architecture.

The physical path is an implementation detail determined by the resolver.

Changing filesystem organization must not require changing logical dependency
definitions.

---

## 3.6 Build only what is required

A requested product defines a build target.

The build planner computes the transitive dependency closure necessary to make
the requested products current.

For example, requesting a vector product may require:

```text
prepare
   ↓
raster
   ↓
vector
```

but should not require:

```text
extrude
package
```

unless another requested product depends upon them.

---

## 3.7 Complete definitions should be validated

During the initial implementation, the build system should construct and
validate the complete defined dependency graph for an artifact before
selecting what needs to be realized.

This intentionally favors:

* visibility;
* correctness;
* debugging;
* early detection of invalid references;
* early detection of dependency cycles;
* understanding of available manufacturing capabilities.

The implementation may later construct portions of the graph lazily if eager
construction becomes unwieldy.

The architectural requirement is that the complete set of definitions be
validatable, not that every possible graph node must forever be instantiated
eagerly.

---

# 4. Terminology

## 4.1 Workspace

A workspace is a configured project containing source material, artifacts,
models, and generated products.

Workspace-wide configuration is stored in:

```text
workspace.toml
```

The workspace provides the root context for configuration resolution and
product generation.

---

## 4.2 Artifact

An artifact is a named source and configuration context.

It is identified by an:

```text
artifact_id
```

Examples include:

```text
john
skylar
nydeli
family-2026
```

An artifact may participate in multiple models.

Therefore:

```text
artifact != model
artifact != manufactured object
artifact != final product
```

A single source artifact may feed artwork, coaster, ornament, and keychain
models.

An artifact may also consume products associated with other artifacts.

---

## 4.3 Model

A model defines a reusable manufacturing recipe.

Examples may include:

```text
artwork
coaster
ornament
keychain
```

A model declares:

* inputs;
* parameters;
* variants;
* stages;
* products;
* dependencies.

Models should increasingly be compositions of generic operations rather than
large special-purpose implementations.

The generic build engine must not contain geometry-specific knowledge about
individual models.

---

## 4.4 Operation

An operation is a reusable transformation with defined inputs and outputs.

Conceptual operations may include:

```text
analyze
normalize
trace
rasterize
vectorize
shape
fit
scale
translate
rotate
inset
offset
embed
compose
add-text
add-ridge
add-hanger
extrude
package
```

A stage may currently implement more than one conceptual operation.

For example, an extrusion stage may initially perform both fitting and
extrusion.

The architectural distinction should nevertheless remain clear so that
operations can be separated or reused later without changing product
semantics.

---

## 4.5 Variant

A variant is a named parameter preset defined by a model.

Variants are model-scoped.

For example:

```text
artwork.variants.default

coaster.variants.default
coaster.variants.ridged
coaster.variants.lettered

ornament.variants.default
ornament.variants.small

keychain.variants.default
```

Variants do not need to correspond across models.

A variant named `default` in the coaster model has no necessary relationship
to `default` in the ornament model.

Likewise, the existence of a `90mm` variant in one model does not imply that
another model should have a `90mm` variant.

Variants are defined in model configuration such as `parameters.toml`.

A `default` variant should normally exist or be implicitly available.

---

## 4.6 Variant versus parameter

Variants represent useful named presets or behaviors.

Ordinary dimensions should not automatically become variants.

For example, these may be sensible coaster variants:

```text
default
ridged
lettered
ridged-lettered
```

while:

```text
diameter = 90.0
```

may simply be a parameter.

The distinction is:

```text
Variant
    reusable named behavior/preset

Parameter
    value applied to a particular realization
```

A model may define dimensional variants when they are genuinely useful, but
physical dimensions should not proliferate upstream variants unnecessarily.

---

## 4.7 Realization

A realization is a particular configured invocation of a model.

It identifies:

* a model;
* a variant;
* a parameter set;
* resolved inputs.

For example, two products may both use the `ridged` coaster variant:

```text
coaster-small
    model = coaster
    variant = ridged
    diameter = 90

coaster-large
    model = coaster
    variant = ridged
    diameter = 100
```

These are separate realizations even though they use the same model and
variant.

The distinction between variant and realization prevents model presets from
being confused with individual manufactured configurations.

---

## 4.8 Stage

A stage is an executable node in a model realization.

A stage:

* consumes source inputs, configuration, and/or products;
* performs one or more defined transformations;
* produces one or more products.

Examples from the artwork model include:

```text
prepare
raster
vector
extrude
package
```

Stages participate in a dependency graph.

---

## 4.9 Stage ID

Every stage has a stable numeric identifier used for human presentation and
filesystem organization.

For example:

```text
10-prepare
20-raster
30-vector
40-extrude
50-package
```

The numeric stage ID:

* provides stable human-readable ordering;
* makes filesystem trees easier to inspect;
* permits insertion of future stages between existing stages.

The numeric stage ID does not determine dependency order.

The semantic identity is:

```text
prepare
```

not:

```text
10-prepare
```

Logical product references therefore do not depend on the numeric stage ID.

---

## 4.10 Product

A product is a named persistent output produced by a stage.

Examples include:

```text
envelope
trace
colors
geometry
components
artifact
```

A product may materialize as:

* one file;
* multiple files;
* a manifest describing a collection of files.

All products are first-class and reusable.

---

## 4.11 Product collection

Some logical products consist of a variable number of physical files.

For example:

```text
color-1.svg
color-2.svg
color-3.svg
color-4.svg
color-5.svg
```

may collectively represent:

```text
colors
```

A manifest such as:

```text
products.json
```

describes the members of the collection and their metadata.

Consumers should consume the logical collection rather than infer membership
by globbing directory contents.

---

# 5. Dimensional Semantics

One of the most important architectural distinctions is between relative
geometry and physical manufacturing geometry.

## 5.1 Raster dimensions are not physical dimensions

A raster product may have dimensions such as:

```text
1024 × 1024 pixels
```

Those dimensions define a raster coordinate space.

They do not imply millimeters or any other manufacturing size.

DPI metadata must not accidentally determine manufacturing dimensions unless
an operation explicitly requests that behavior.

---

## 5.2 Vector dimensions are normally relative

Vector products produced by artwork preprocessing should preserve:

* aspect ratio;
* relative dimensions;
* relative positions;
* registration between components;
* relationship to the envelope.

They should normally remain independent of physical manufacturing size.

For example:

```text
nydeli artwork
    ↓
prepare
    ↓
raster
    ↓
vector
```

should normally happen once regardless of whether the resulting artwork is
later used in a 45 mm keychain or a 100 mm coaster.

---

## 5.3 Physical X/Y dimensions are introduced late

Physical dimensions belong to the downstream operation or model that
introduces the corresponding physical constraint.

For example, a coaster may define:

```text
outside diameter = 100 mm
ridge width = 3 mm
lettering region = 12 mm
clearance = 2 mm
```

The coaster then determines the remaining region available for artwork.

The consumed artwork is fitted into that region.

The artwork itself does not need to know the coaster diameter.

---

## 5.4 Extrusion introduces physical Z

Extrusion converts dimensioned 2D geometry into physical 3D geometry.

Conceptually:

```text
Relative2DGeometry
        │
        │ fit / transform
        ▼
Dimensioned2DGeometry
        │
        │ extrude
        ▼
Physical3DGeometry
```

An existing implementation may combine fitting and extrusion in one stage,
but they remain conceptually separate operations.

---

## 5.5 Dimensional responsibility

A useful rule is:

> Physical dimensions belong to the operation or model that introduces the
> corresponding physical constraint.

Therefore:

```text
artwork raster
    does not know coaster diameter

artwork vector
    does not know coaster diameter

composed artwork
    need not know coaster diameter

coaster
    knows coaster outside dimensions

ridge
    knows ridge dimensions

lettering region
    knows lettering constraints

fit
    determines available artwork dimensions

extrude
    establishes physical Z dimensions
```

---

# 6. Registered Geometry

Reusable geometry must preserve registration.

## 6.1 Registered 2D geometry

A registered 2D product consists of one or more geometric components sharing
a coordinate system whose relative geometry must be preserved.

Conceptually:

```text
Registered2DGeometry

coordinate space
    origin
    bounds
    aspect ratio

envelope
    logical outer boundary

components
    one or more registered regions

metadata
    component identifiers
    colors/material roles
```

The physical representation may be a collection of SVG files plus a manifest.

---

## 6.2 Registration is invariant

Once components have been registered, downstream consumers must preserve:

* relative position;
* relative dimensions;
* aspect ratio;
* alignment;
* component registration.

A downstream consumer may apply one common transformation:

```text
T(A)
T(B)
T(C)
```

where the same transformation `T` is applied to every component.

It must not independently transform components:

```text
T1(A)
T2(B)
T3(C)
```

unless modifying their internal relationship is explicitly the responsibility
of that operation.

---

## 6.3 Consumers should treat payloads as opaque

A coaster consuming registered NYDELI artwork should not need to know that the
artwork contains:

* text;
* a blimp;
* a gear;
* particular colors;
* particular paths.

It needs to know the product contract:

```text
registered geometry
known envelope
known coordinate system
preserve registration
```

This allows the same downstream model to consume portraits, houses, logos,
NYDELI artwork, or future artwork types without special cases.

---

# 7. Fitting

Fitting maps reusable relative geometry into a physical or relative target
region.

Conceptually:

```text
fit(
    geometry,
    region,
    mode="contain",
    preserve_aspect_ratio=True,
)
```

A consuming model owns the region into which the upstream geometry must fit.

For example:

```text
100 mm coaster
      │
      ├── ridge
      ├── lettering
      ├── clearance
      │
      ▼
available artwork region
      │
      ▼
fit registered artwork
```

The fit operation computes one transformation for the registered component and
applies it consistently to all of its members.

Changing the coaster diameter should not require re-rasterizing or
re-vectorizing the artwork.

---

# 8. Composition

Composition is recursive.

## 8.1 Single-artwork composition

An irregular piece of artwork may be embedded inside a regular container.

For example:

```text
registered NYDELI artwork
          +
        circle
          │
          ▼
        embed
          │
          ├── artwork regions
          ├── background region
          └── circular envelope
          │
          ▼
Registered2DGeometry
```

The resulting circular composition remains reusable.

It does not inherently need to be physically dimensioned.

---

## 8.2 Multiple-artwork composition

Multiple independent products may be combined:

```text
artwork A ──┐
artwork B ──┼──> compose
artwork C ──┘
                  │
                  ▼
         Registered2DGeometry
```

The composition establishes a new coordinate space while preserving the
internal registration of each child component.

The resulting composition can itself be consumed as an opaque registered
component.

---

## 8.3 Nested composition

Composition may be recursive:

```text
Artwork A ─┐
Artwork B ─┼──> Composition X
Artwork C ─┘          │
                      │
Artwork D ────────────┼──> Composition Y
                      │
Logo E ───────────────┘
                             │
                             ▼
                       manufactured object
```

A downstream consumer of `Composition X` does not need to know that it
contains A, B, and C.

---

# 9. Models as Recipes

Models should increasingly be understood as recipes connecting reusable
operations and products.

For example, a coaster should not require a monolithic
`CircularCoasterBuilder` that understands artwork internals.

Conceptually:

```text
input Registered2DGeometry
          │
          ▼
create outer boundary
          │
          ▼
calculate ridge/lettering regions
          │
          ▼
calculate available artwork region
          │
          ▼
fit input geometry
          │
          ▼
add optional geometry
          │
          ▼
extrude components
          │
          ▼
package
```

The same model can therefore consume many kinds of registered artwork.

---

# 10. Logical Product References

Products must be addressable without filesystem paths.

The resolver should operate on structured logical references.

A complete reference must identify enough context to uniquely resolve a
particular persistent product.

The exact serialized syntax should remain centralized and testable.

At minimum, the logical identity includes:

```text
artifact
model / realization context
stage
product
```

Model variant and realization information must be represented such that two
independent realizations of the same model and variant cannot collide.

During the initial refactor, existing canonical syntax may use:

```text
artifact:model:variant:stage:product
```

where the variant uniquely identifies the realization.

As named realizations are introduced, the resolver may evolve to reference the
realization directly.

The important invariant is not the number of colon-separated fields.

The important invariants are:

1. references are logical;
2. references are globally unambiguous within a workspace;
3. references do not contain generated filesystem paths;
4. reference parsing and formatting are centralized;
5. filesystem organization may change without changing product semantics.

---

# 11. Product Resolver

A central resolver maps logical identity to definitions and physical
locations.

Conceptually:

```text
logical product reference
          │
          ▼
      ProductRef
          │
          ▼
    ProductResolver
          │
    ┌─────┴──────────────┐
    ▼                    ▼
artifact context     ModelRegistry
                          │
                          ▼
                       ModelSpec
                          │
                          ▼
                      Variant /
                     Realization
                          │
                          ▼
                       StageSpec
                          │
                          ▼
                      ProductSpec
                          │
                          ▼
                   ResolvedProduct
                          │
                          ▼
                  filesystem path
```

The resolver answers questions such as:

* which artifact owns this product?
* which model defines it?
* which realization produces it?
* which stage produces it?
* what is its ProductSpec?
* where is it materialized?

The resolver does not determine which stages should execute.

That is the planner's responsibility.

---

# 12. Filesystem Layout

Generated products should mirror their logical ownership.

The intended hierarchy is conceptually:

```text
artifacts/
└── <artifact_id>/
    ├── artifact.png
    ├── artifact.toml
    │
    └── <model>/
        └── <realization-or-variant>/
            └── <stage-id>-<stage-name>/
                └── products...
```

For example:

```text
artifacts/
└── nydeli/
    ├── artifact.png
    ├── artifact.toml
    │
    └── artwork/
        └── default/
            ├── 10-prepare/
            │   ├── envelope.svg
            │   └── trace.svg
            │
            ├── 20-raster/
            │   ├── color-1.png
            │   ├── color-2.png
            │   └── products.json
            │
            ├── 30-vector/
            │   ├── color-1.svg
            │   ├── color-2.svg
            │   └── products.json
            │
            ├── 40-extrude/
            │   ├── color-1.stl
            │   ├── color-2.stl
            │   └── products.json
            │
            └── 50-package/
                └── artifact.3mf
```

There is no special filesystem location for a final product.

---

# 13. Filesystem Invariants

## 13.1 One natural home

Every generated product has exactly one canonical materialized location.

Do not duplicate a 3MF or any other product merely to create a convenient
"final output" location.

Publication or export mechanisms may separately collect products for user
convenience.

---

## 13.2 Stage ownership

Every generated product belongs to the stage that produced it.

Generated products therefore live beneath their producing stage.

---

## 13.3 Model and realization isolation

Products generated by separate models or realizations occupy separate
namespaces.

Two models may both have stages named:

```text
prepare
extrude
package
```

without filesystem ambiguity.

---

## 13.4 Artifact-level inputs remain artifact-level

Inputs and configuration belonging to the artifact as a whole remain at the
artifact level:

```text
artifacts/nydeli/artifact.png
artifacts/nydeli/artifact.toml
```

They should not be unnecessarily copied into every model realization.

---

## 13.5 Path construction is centralized

Model and stage implementation code must not construct global artifact paths
directly.

Avoid assumptions such as:

```python
root / artifact_id / "artwork" / "default" / "30-vector"
```

inside model implementations.

Filesystem policy belongs to the resolver.

---

# 14. ProductSpec Paths

A `ProductSpec` path should be local to its producing stage.

For example:

```python
StageSpec(
    id=10,
    name="prepare",
    products=(
        ProductSpec(
            name="trace",
            path="trace.svg",
        ),
        ProductSpec(
            name="envelope",
            path="envelope.svg",
        ),
    ),
)
```

Avoid repeating stage ownership:

```python
ProductSpec(
    name="envelope",
    path="prepare/envelope.svg",
)
```

The resolver already knows the artifact, model, realization, and stage.

---

# 15. Defined Graph

The Defined Graph represents everything the system knows how to produce for an
artifact.

It is derived from:

```text
registered models
+
model-scoped variants
+
stages
+
products
+
declared dependencies
```

The Defined Graph exists independently of what `artifact.toml` requests.

Initially, the system should construct and validate this complete graph.

This permits early detection of:

* unknown models;
* unknown variants;
* unknown stages;
* unknown products;
* duplicate identities;
* missing producers;
* invalid dependencies;
* dependency cycles;
* invalid cross-artifact references.

---

# 16. Product Catalog

The Product Catalog is the catalog view of the Defined Graph.

It describes everything the system knows how to produce.

For example:

```text
nydeli artwork envelope
nydeli artwork raster colors
nydeli artwork vector colors
nydeli artwork extruded components
nydeli artwork 3MF
nydeli coaster
nydeli ornament
nydeli keychain
```

Catalog membership does not mean that the product currently exists.

A catalog product may be:

```text
DEFINED
ABSENT
INCOMPLETE
INVALID
STALE
CURRENT
```

The Product Catalog is both:

* a manufacturing capability catalog;
* an inventory of reusable manufacturing assets.

---

# 17. Offering Catalog

Commercial or external presentation is separate from technical product
identity.

Any ProductSpec may optionally carry catalog metadata indicating that it is
intended for:

* customer sale;
* download;
* publication;
* another external use.

For example, the following may all be technical products:

```text
envelope
vector colors
extruded components
3MF
```

while only the 3MF is currently offered for customer sale.

Alternatively, vector artwork could later be sold as a digital product without
changing the build architecture.

Therefore:

```text
Product Catalog
      │
      │ offering metadata
      ▼
Offering Catalog
```

The fact that a product is customer-facing does not make it architecturally
privileged.

---

# 18. Requested Graph

`artifact.toml` primarily describes which model realizations or products should
be produced for a particular artifact and any artifact-specific parameter
overrides.

Routine configuration should remain simple.

For example, the common case should eventually be expressible with
configuration conceptually similar to:

```toml
[build]
artwork = true
coaster = true
ornament = true
keychain = true
```

More detailed configurations may define named realizations:

```toml
[products.coaster-small]
model = "coaster"
variant = "ridged"
diameter = 90.0

[products.coaster-large]
model = "coaster"
variant = "ridged"
diameter = 100.0
```

The user should not need to manually wire ordinary model dependencies.

Models know their normal product requirements.

Explicit ProductRefs remain available for advanced overrides and composition.

---

# 19. Realization Graph

The Realization Graph consists of:

```text
requested products
+
their transitive dependencies
```

It represents everything that must be available to satisfy the artifact's
requested outputs.

Products in the Defined Graph that are not requested and are not dependencies
remain unrealized.

For example, the artwork model may define:

```text
prepare
raster
vector
extrude
package
```

but a coaster may require only the artwork's vector geometry.

In that case:

```text
prepare    realized
raster     realized
vector     realized
extrude    not realized
package    not realized
```

unless another requested product requires them.

---

# 20. Execution Plan

The Realization Graph describes what must be available.

The Execution Plan describes what must actually execute now.

Conceptually:

```text
Defined Graph
      │
      │ artifact configuration
      ▼
Requested Graph
      │
      │ dependency closure
      ▼
Realization Graph
      │
      │ state evaluation
      ▼
Execution Plan
```

If required products are already current, their producing stages do not need
to execute again.

---

# 21. Product State and Resumability

Build state exists at the product/stage level rather than only at the artifact
level.

Useful states include:

```text
ABSENT
INCOMPLETE
INVALID
STALE
CURRENT
```

## ABSENT

The product has not been generated.

## INCOMPLETE

A previous execution began but did not successfully complete.

## INVALID

Completion metadata exists, but one or more declared products are missing or
invalid.

## STALE

The product was successfully generated but relevant inputs, dependencies,
configuration, or operation versions have changed.

## CURRENT

The product exists and corresponds to the current dependency and
configuration state.

A subsequent build should reuse current products.

---

# 22. Stage Completion

Directory existence does not imply successful completion.

For example:

```text
40-extrude/
```

may exist because an earlier build was interrupted.

Likewise, the presence of some expected files does not prove the stage
completed.

For stages producing dynamic collections, a manifest such as:

```text
products.json
```

may act as the authoritative completion record.

Where practical, completion metadata should be written only after all stage
products have been successfully generated and validated.

---

# 23. Manifests

Stages producing variable product collections should explicitly describe their
outputs.

For example:

```text
30-vector/
├── color-1.svg
├── color-2.svg
├── color-3.svg
├── color-4.svg
├── color-5.svg
└── products.json
```

Consumers should not infer products by globbing:

```text
*.svg
```

A manifest may eventually contain:

* logical product identifiers;
* paths;
* component roles;
* colors/material roles;
* coordinate-system information;
* bounds;
* dimensions;
* hashes;
* source dependency hashes;
* relevant parameter values;
* operation/tool versions;
* generation metadata.

Manifests should support determining both product membership and freshness.

---

# 24. Source Analysis

Source images may have different preprocessing requirements.

Examples include:

```text
transparent irregular artwork
opaque photograph
portrait requiring background removal
already-regular artwork
logo or line art
```

Source analysis may eventually identify properties such as:

```text
alpha present
background transparent
silhouette irregular
aspect ratio
edge contact
approximate color count
```

Analysis may help choose or parameterize preprocessing operations.

Automatic classification should not silently control the entire pipeline.

Configuration must be able to override analysis when necessary.

---

# 25. Reference Scenario: NYDELI Artwork

The NYDELI source image has a transparent background and an irregular
silhouette.

The artwork model may produce:

```text
nydeli.png
    │
    ▼
prepare
    ├── envelope
    └── trace
         │
         ▼
       raster
         │
         ▼
       vector
         │
         ▼
registered relative geometry
```

The vector geometry is dimension-independent.

It preserves the relationships between the color regions and envelope.

It may subsequently be used to create:

* standalone artwork;
* circular artwork;
* a coaster;
* an ornament;
* a keychain;
* other products.

The artwork model may also define extrusion and package products.

Those products need not be realized when downstream consumers require only
the vector geometry.

---

# 26. Reference Scenario: Circular Embedded Artwork

NYDELI artwork may be embedded within a larger circle:

```text
registered NYDELI geometry
           +
         circle
           │
           ▼
         embed
           │
           ├── artwork
           ├── background
           └── circular envelope
           │
           ▼
  registered circular geometry
```

The resulting disc is still reusable geometry.

It need not yet have a physical manufacturing diameter.

A downstream coaster determines how large that disc becomes.

---

# 27. Reference Scenario: Coaster

A coaster consumes registered geometry.

It does not need to understand the artwork payload.

Conceptually:

```text
Registered2DGeometry
          │
          ▼
  coaster outer boundary
          │
          ├── optional ridge
          ├── optional lettering
          ├── clearances
          │
          ▼
  available artwork region
          │
          ▼
   fit registered input
          │
          ▼
   dimensioned geometry
          │
          ▼
       extrude
          │
          ▼
       package
```

For a 100 mm coaster, the consumed artwork may become:

```text
96 mm
90 mm
72 mm
```

depending on whether the coaster contains ridges, lettering, or other
features.

The input artwork does not change.

Only the downstream fitting and manufacturing geometry change.

---

# 28. Reference Scenario: Ornament and Keychain

The same irregular or registered artwork can feed both ornament and keychain
models.

For example:

```text
                    registered artwork
                           │
               ┌───────────┴───────────┐
               ▼                       ▼
           ornament                 keychain
               │                       │
        determine bounds        determine bounds
        add hanger              add hanger
        fit artwork             fit artwork
        extrude                 extrude
               │                       │
               ▼                       ▼
              3MF                     3MF
```

The upstream raster and vector work is shared.

The models introduce their own physical dimensions.

---

# 29. Reference Scenario: Multiple Artwork Components

A larger object may contain several independent pieces of artwork.

For example:

```text
john artwork ────┐
                 │
nydeli artwork ──┼──> composition
                 │
skylar artwork ──┘
                         │
                         ▼
                registered composite
                         │
                         ▼
                    large coaster
```

This may cross artifact boundaries.

Building the composite may require:

```text
john artwork through vector
nydeli artwork through vector
skylar artwork through vector
```

It should not require any of their standalone artwork extrusion or package
stages unless those products are separately requested.

If the vector products are already current, composition begins from those
existing manufacturing assets.

---

# 30. Cross-Model Dependencies

Models may consume products generated by other models.

A consumer depends upon the required product, not completion of the producer's
entire model.

Conceptually:

```text
artwork
   │
   ▼
registered geometry
   │
   ├──────────> coaster
   ├──────────> ornament
   └──────────> keychain
```

---

# 31. Cross-Artifact Dependencies

Dependencies may cross artifact boundaries.

For example:

```text
john:artwork ──────┐
                   │
nydeli:artwork ────┼──> family-2026 composition
                   │
skylar:artwork ────┘
```

`artifact_id` is therefore one coordinate in a workspace-wide dependency
graph.

---

# 32. Configuration Versus Dependency Wiring

Configuration describes what should be produced and how model behavior should
be parameterized.

Normal users should not need to manually specify routine internal
dependencies.

Prefer:

```toml
[products.coaster]
model = "coaster"
variant = "ridged"
diameter = 100.0
```

where the coaster model already knows that it requires registered artwork.

Explicit logical product references should be available for advanced
composition:

```toml
source = "another-artifact:artwork:default:vector:colors"
```

Avoid generated filesystem paths:

```toml
source = "artifacts/another-artifact/artwork/default/30-vector/color-1.svg"
```

---

# 33. Separation of Responsibilities

## Configuration system

Responsible for:

* loading configuration;
* validating values;
* applying defaults;
* resolving variants;
* resolving overrides;
* tracking provenance.

It does not execute geometry transformations.

---

## Model registry

Responsible for:

* discovering models;
* registering ModelSpec definitions;
* exposing model metadata;
* exposing available variants.

It does not contain model-specific geometry algorithms.

---

## Model specification

Responsible for declaring:

* inputs;
* parameters;
* variants;
* stages;
* stage IDs;
* dependencies;
* products;
* product contracts.

It describes what a model knows how to produce.

---

## Product resolver

Responsible for:

* parsing logical references;
* resolving artifacts;
* resolving models;
* resolving realizations;
* resolving stages;
* resolving products;
* constructing canonical filesystem locations.

It does not decide what must execute.

---

## Build graph builder

Responsible for constructing the Defined Graph.

Initially, it should construct the complete available graph for an artifact so
that definitions can be inspected and validated.

---

## Build planner

Responsible for:

* selecting requested products;
* computing dependency closure;
* constructing the Realization Graph;
* evaluating product state;
* constructing the Execution Plan.

It does not perform model-specific geometry transformations.

---

## Stage runner

Responsible for:

* executing planned stages;
* invoking stage implementations;
* validating execution results;
* recording products;
* recording completion state.

---

## Stage implementation

Responsible for:

* performing model-specific transformations;
* consuming resolved inputs;
* generating declared products.

Stage implementations must not encode global filesystem policy.

---

# 34. Architectural Invariants

The following are core invariants.

## Invariant 1 — First-class products

Every persistent generated output is a product.

A 3MF is not inherently more important than an SVG, raster mask, envelope,
mesh, or manifest.

---

## Invariant 2 — No privileged final product

The build engine does not require models to have a distinguished final
product.

---

## Invariant 3 — One canonical home

Every generated product has exactly one canonical materialized location.

---

## Invariant 4 — Stage ownership

Every generated product belongs to the stage that generated it.

---

## Invariant 5 — Logical references

Products are referenced logically rather than through generated filesystem
paths.

---

## Invariant 6 — Central resolution

The resolver is the authority for mapping logical identity to physical
location.

---

## Invariant 7 — Dependency-driven execution

Dependencies determine execution order.

Stage IDs and filesystem ordering do not.

---

## Invariant 8 — Complete definitions are validatable

The complete set of available model, variant, stage, product, and dependency
definitions must be validatable even when only a subset is requested.

---

## Invariant 9 — Minimal realization

Only the dependency closure necessary for requested products needs to be
realized.

---

## Invariant 10 — Current products are reusable

Current products may satisfy dependencies without rerunning their producers.

---

## Invariant 11 — Cross-model reuse

Products may be consumed by other models.

---

## Invariant 12 — Cross-artifact reuse

Products may be consumed by other artifacts.

---

## Invariant 13 — Dimension independence

Preprocessing, rasterization, and vectorization products should remain
independent of physical manufacturing dimensions wherever practical.

Pixel dimensions and SVG coordinate dimensions do not imply manufacturing
size.

---

## Invariant 14 — Late dimensionalization

Physical X/Y dimensions are introduced by the downstream operation or model
that requires them.

Physical Z dimensions are introduced by extrusion or another explicitly 3D
operation.

---

## Invariant 15 — Registration preservation

Downstream consumers must preserve the relative dimensions, positions, aspect
ratio, and registration of registered geometry unless explicitly responsible
for modifying those relationships.

---

## Invariant 16 — Opaque consumption

A consumer should depend upon a product contract rather than knowledge of the
artwork's internal semantic payload.

---

## Invariant 17 — Recursive composition

Compatible registered geometry may be composed into new registered geometry,
which can itself be reused as an opaque component.

---

## Invariant 18 — Model-scoped variants

Variants belong to models.

Variants are not globally shared merely because they have the same name.

---

## Invariant 19 — Variant is not realization

A variant is a reusable model preset.

A realization is a particular configured invocation of that model and variant.

---

## Invariant 20 — Manifests define collections

Variable product collections are explicitly described by manifests rather
than inferred from directory contents.

---

## Invariant 21 — Directory existence is not completion

A stage directory existing does not imply that the stage completed
successfully.

---

## Invariant 22 — No model-specific engine behavior

The generic engine must not special-case the geometry or semantics of a
particular model.

---

## Invariant 23 — No global path construction in models

Model implementations do not construct global artifact filesystem paths.

---

## Invariant 24 — Common workflows remain simple

Architectural flexibility must not require users to manually configure the
dependency graph for routine workflows.

---

# 35. Architectural Acceptance Tests

A proposed architecture or refactor should be able to represent the following
without special cases.

### Case A — Standalone artwork

One PNG is converted through prepare, raster, vector, extrusion, and packaging
and printed as artwork.

### Case B — Irregular ornament

The same artwork's relative geometry is fitted to ornament constraints, a
hanger is added, and the result is extruded and packaged.

The standalone artwork 3MF is not required.

### Case C — Keychain

The same registered artwork is reused at a smaller physical size with
keychain-specific geometry.

Rasterization and vectorization are not repeated merely because the physical
size changes.

### Case D — Circular coaster

Irregular artwork is embedded in a circular composition with a generated
background.

The coaster determines its outside diameter and fits the registered
composition into the remaining usable region.

### Case E — Decorated coaster

The same circular composition is used in a coaster with optional base, ridge,
lettering region, and other manufacturing geometry.

The artwork remains opaque to the coaster.

### Case F — Multiple-artwork composition

Registered artwork from multiple artifacts is composed into a larger
registered design and subsequently used in a manufactured object.

Only the upstream products actually required by the composition are realized.

If a proposed resolver, filesystem layout, model definition, ProductRef, or
planner cannot cleanly represent all of these cases, the design should be
reconsidered before implementation.

---

# 36. Initial Refactoring Strategy

The existing repository should be evolved incrementally rather than rewritten.

The working artwork model serves as the behavioral regression target.

A recommended sequence is:

1. Introduce stable stage IDs.
2. Introduce explicit logical reference types.
3. Define centralized reference parsing and formatting.
4. Introduce the central resolver.
5. Route existing path construction through the resolver while preserving
   current behavior.
6. Make ProductSpec paths stage-local.
7. Introduce model-scoped variants.
8. Introduce the model/realization filesystem hierarchy.
9. Move all generated products beneath their producing stages.
10. Remove special filesystem handling for `artifact.3mf`.
11. Construct and validate the complete Defined Graph.
12. Derive the Product Catalog from the Defined Graph.
13. Select requested realizations from artifact configuration.
14. Compute the Realization Graph.
15. Evaluate product state and construct the Execution Plan.
16. Add partial product-targeted builds.
17. Add cross-model product dependencies.
18. Add cross-artifact product dependencies.
19. Introduce registered geometry contracts.
20. Implement a second production model to validate composition.

The existing artwork transformations should remain functionally equivalent
throughout the infrastructure refactor.

Once this migration is complete, replace this section with a shorter
implementation-status section.

---

# 37. Guidance for Future Changes

When proposing a feature or refactor, ask:

1. What products does this operation consume?
2. What products does it produce?
3. Which stage owns each product?
4. Are dependencies expressed logically rather than through filesystem paths?
5. Can the resolver uniquely locate every product?
6. Is this geometry relative or physically dimensioned?
7. Which operation actually owns the physical dimension?
8. Does the transformation preserve registered geometry?
9. Does the consumer unnecessarily understand its input's payload?
10. Could this operation consume another compatible registered product?
11. Can its output itself become a reusable component?
12. Can the planner build only the dependency closure actually required?
13. Can current upstream products be reused?
14. Can another model consume this product?
15. Can another artifact consume this product?
16. Does the change introduce a special case for 3MF or another file type?
17. Does it introduce model-specific behavior into the generic engine?
18. Does filesystem organization remain an implementation detail?
19. Can interrupted execution be safely detected and resumed?
20. Does the common user workflow remain simple?

Warning signs include designs that:

* require the complete producer model to execute before consuming an upstream
  product;
* treat a 3MF as the definition of model completion;
* rerasterize or revectorize artwork merely because physical output size
  changed;
* embed generated filesystem paths in configuration;
* independently scale registered color components;
* require a coaster to understand the semantic contents of artwork;
* duplicate products merely to create a convenient final-output directory;
* create new special-purpose models where generic composition operations would
  suffice.

---

# 38. Summary

`lowkey-artifact-builder` should be understood as a dependency-driven 2.5D
manufacturing system.

The common workflow is intentionally simple:

```text
one PNG
   │
   ▼
artwork
   │
   ├──> standalone artwork
   ├──> coaster
   ├──> ornament
   └──> keychain
```

Underneath that simple workflow is a more general product graph.

Source interpretation produces reusable relative and registered geometry.

Downstream consumers introduce the physical constraints they own.

Registered components preserve their internal geometry.

Composition can recursively combine products from the same artifact or from
different artifacts.

Every persistent product is first-class.

A resolver maps logical product identities to physical storage.

The complete Defined Graph describes what the system knows how to produce.

The Product Catalog exposes those capabilities and reusable manufacturing
assets.

Artifact configuration identifies what should be produced.

The Realization Graph determines what products are required.

The Execution Plan determines what work must actually run.

Current products are reused.

A 3MF is simply one possible product.

The long-term manufacturing objective is:

> interpret source material once, preserve reusable manufacturing assets, and
> create increasingly sophisticated physical products by composing generic,
> well-defined operations with minimal manual intervention.
