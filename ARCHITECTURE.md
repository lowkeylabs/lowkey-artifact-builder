# Architecture

This document defines the architectural model, terminology,

relationships, contracts, and invariants of `lowkey-artifact-builder`.

It is intended to be a durable reference for maintainers, contributors,

and automated development tools, including future LLM-assisted

development.

The README describes how to install and use the project. This document

describes what the system means and how its major pieces are intended to

interact.

When implementation details conflict with this document, do not assume

the implementation defines the architecture. Determine whether the

implementation is incomplete or whether an architectural decision has

intentionally changed. If the architecture changes, update this document

as part of that change.

## Normative specifications

`ARCHITECTURE.md` defines the system-wide architectural terminology,

relationships, contracts, and invariants of `lowkey-artifact-builder`.

Each:

``` text

model/models/\\<model>/DEFINITION.md
```

defines the normative semantics, requirements, and invariants specific

to that model.

The repository implementation and tests must conform to both the system

architecture and the applicable model definitions.

A `CHANGEPLAN.md`, when present, is a temporary implementation plan

derived by comparing the current repository against these permanent

specifications. It describes testable changes needed to bring the

implementation into alignment. It is not itself a normative

specification and may be removed once alignment is complete.

Tests provide executable evidence of conformance. They do not replace

the permanent specifications. Tests exercising a Model's ordinary
behavior

without selecting a specialized Variant may be understood as exercising

that Model's `default` Variant. Such tests need not explicitly name the

`default` Variant unless Variant selection or identity is itself under
test.

When evaluating architectural completeness, compare the current

repository against `ARCHITECTURE.md` and the applicable model

`DEFINITION.md` files. When differences exist, a change plan may be

created to resolve those differences in independently testable slices.

------------------------------------------------------------------------

# 1. Purpose

`lowkey-artifact-builder` is a dependency-driven build system for

producing 2.5D manufacturing geometry from source material with minimal

manual intervention.

A common use case begins with a customer image:

``` text

                         source PNG

                             │

                             ▼

                      artwork model

                             │

                    registered geometry

                             │

                             ▼

                        shape model

                             │

             ┌───────────────┼───────────────┐

             │               │               │

             ▼               ▼               ▼

         ornament         coaster         keychain

          variant          variant          variant

             │               │               │

             └───────────────┼───────────────┘

                             │

                             ▼

                       realizations

                             │

                             ▼

                    manufacturing geometry
```

The same interpreted artwork should be reusable across many manufactured

objects and many variants of those objects.

More advanced compositions are also supported:

``` text

artwork A ──┐

artwork B ──┼──> registered composition ──> manufactured object

artwork C ──┘
```

The architecture should optimize the user experience for the common case

without restricting the dependency system to the common case.

The long-term objective is for new manufactured products to increasingly

be defined through model features, variants, configuration, and

composition of reusable operations rather than new special-purpose

Python pipelines.

------------------------------------------------------------------------

# 2. Fundamental Principle

The fundamental relationship between reusable definitions and concrete

manufacturing work is:

``` text

Model

    │

    ├── Feature

    │

    └── Variant

          │

          │ applied to

          ▼

Artifact ───────> Realization

                     │

                     └── Stage

                           │

                           └── Product
```

A Model defines reusable manufacturing capabilities.

A Feature is a Model-owned optional capability or behavior.

A Variant is a named, Model-scoped set of parameter overrides
representing

a reusable configuration of that Model. Variant overrides are applied
over

the Model's ordinary parameter defaults. They do not independently
redefine

Features or their semantics.

A Model's parameter defaults establish its ordinary behavior, including

Feature participation where participation is determined by parameter
values.

A Variant specifies only the values that differ for that reusable

configuration. The `default` Variant may therefore contain no parameter

overrides.

A Variant's complete identity includes its Model. Selecting a Variant

therefore selects its Model; Model and Variant are not independent

dimensions of a Realization.

A Realization is the application of a Variant to an Artifact, with or

without Artifact-specific customizations.

Conceptually:

``` text

Variant

    = Model + named reusable configuration

    = sparse parameter overrides over Model defaults

Realization

    = Artifact + Variant + optional Artifact-specific customizations
```

A Realization is not a second mechanism for defining reusable product

configurations. Reusable catalog configurations belong to Variants.

A Product may be consumed by:

\-   a later Stage of the same Realization;

\-   another Realization;

\-   another Model;

\-   another Artifact;

\-   another build executed in the future.

The build system is therefore fundamentally a graph of Products and the

operations that produce them.

A 3MF is merely one possible Product in this graph.

The use of the word "product" when discussing a Variant as a catalog

offering does not change the architectural meaning of `Product`. A

Product is a persistent output produced by a Stage.

------------------------------------------------------------------------

# 3. Core Principles

## 3.1 Products are first-class

Every persistent output produced by a Stage is a Product.

Examples include:

``` text

envelope.svg

trace.svg

color-1.png

color-1.svg

color-1.stl

products.json

artifact.3mf
```

The build engine does not architecturally distinguish between

"intermediate" and "final" Products.

A Product is important because something requests or depends upon it,

not because it appears at the end of a pipeline.

## 3.2 There is no privileged final product

A Model is not defined by its final 3MF.

For example, an artwork Model might contain:

``` text

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

A consumer may require only `prepare:envelope`, `raster:colors`, or

`vector:colors`.

If nothing requires extruded or packaged artwork, those Stages do not

need to execute.

## 3.3 Products are reusable manufacturing assets

Successfully generated Products are persistent manufacturing assets.

Once registered artwork geometry has been generated, it may be reused

for standalone artwork, ornaments, coasters, keychains, magnets,

plaques, compositions, or future products.

Reusable upstream work should not be repeated merely because a

downstream Variant has different Features, dimensions, or manufacturing

parameters.

## 3.4 Dependencies determine execution

Stages and Products form a dependency graph.

Numeric Stage identifiers, declaration order, filesystem order, and the

concept of a pipeline do not determine execution order.

Dependencies determine execution.

The filesystem materializes the graph. It does not define the graph.

## 3.5 Logical identity is independent of filesystem location

Consumers refer to Products by logical identity, not generated

filesystem paths.

For example:

``` text

nydeli:artwork:default:vector:colors
```

may identify a Product belonging to the Realization produced by applying

the `artwork.default` Variant to Artifact `nydeli`.

Its files might currently exist beneath:

``` text

artifacts/nydeli/artwork/default/30-vector/
```

The logical reference is architectural. The physical path is resolver

policy.

## 3.6 Build only what is required

A requested Product defines a build target.

The planner computes the transitive dependency closure necessary to make

the requested Products current. Requesting a vector Product should not

require extrusion or packaging unless another requested Product depends

upon them.

## 3.7 Complete definitions should be validated

The complete set of registered Model, Feature, Variant, Stage, Product,

and dependency definitions must be validatable independently of which

subset is realized for a particular Artifact.

This favors visibility, correctness, debugging, early detection of

invalid references, and early detection of dependency cycles.

## 3.8 Execution is independent of orchestration

Stage implementations are reusable execution units.

A Stage implementation must be executable from a complete resolved Stage

context without requiring the caller to traverse the surrounding Model.

Orchestration determines what should execute. The Stage implementation

determines how one Stage executes.

## 3.9 Execution is observable but presentation-independent

Execution may emit structured semantic events describing build, Stage,

Product, state, skip, completion, and failure transitions.

Engine behavior must not depend on CLI verbosity, logging policy,

terminal availability, progress rendering, or observer presence.

Observers must not alter dependency, Product-state, resumability, or

execution decisions.

The execution engine remains synchronous unless concurrency is

introduced by a separate architectural decision.

------------------------------------------------------------------------

# 4. Terminology

## 4.1 Workspace

A Workspace is a configured project containing source material,

Artifacts, Models, and generated Products.

Workspace-wide configuration is stored in `workspace.toml`.

## 4.2 Artifact

An Artifact is a named source and configuration context identified by an

`artifact_id`.

Examples:

``` text

john

skylar

nydeli

family-2026

mydog
```

An Artifact is not a Model, manufactured object, Variant, Realization,

or final Product.

An Artifact may provide source material used by multiple Models and

Variants, and may consume Products associated with other Artifacts.

Artifact configuration may customize the application of a Variant. Such

customizations affect the resulting Realization. They do not define a

new Variant and do not change the Realization's originating Variant.

## 4.3 Model

A Model defines a reusable manufacturing recipe and owns a namespace of

Features and Variants.

Examples include:

``` text

artwork

shape
```

A Model declares:

\-   inputs;

\-   parameters;

\-   Features;

\-   Variants;

\-   Stages;

\-   Products;

\-   dependencies.

Models should increasingly be compositions of generic operations rather

than large special-purpose implementations.

The generic build engine must not contain geometry-specific knowledge

about individual Models.

## 4.4 Operation

An Operation is a reusable transformation with defined inputs and

outputs.

Conceptual Operations may include:

``` text

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

A Stage is an execution and persistence boundary. An Operation is

reusable transformation logic that may be invoked by one or more Stages.

Model-specific Stages own Model policy. Reusable Operations own

Model-independent mechanics.

## 4.5 Feature

A Feature is an optional composable capability or behavior supported by

a Model.

Features are Model-scoped.

Examples for a Shape Model may include:

``` text

artwork

outer-ridge

inner-ridge

lettering

hanger
```

A Feature may:

\-   alter geometry;

\-   affect behavior of an always-present Stage;

\-   enable or disable Stage participation;

\-   affect Product generation;

\-   introduce or remove configuration requirements;

\-   affect dependencies.

Features describe Model capabilities. They are not independently

constructible catalog offerings and do not identify Realizations.

Variants configure Model behavior by overriding parameters. Those
parameter

values may affect Feature participation according to Model-owned Feature

semantics. A separate generic Feature-selection mechanism is not
required.

Generic configuration, graph, planning, and execution infrastructure

must not contain Model-specific Feature semantics.

## 4.6 Variant

A Variant is a named, Model-scoped set of parameter overrides
representing a reusable configuration of that Model.

A Variant does not need to repeat the Model's complete configuration.
Instead, effective configuration begins with the Model's ordinary
parameter defaults and applies the Variant's parameter overrides.
Feature participation and behavior remain Model-owned semantics and may
be determined by the resulting parameter values.

Variants are reusable across Artifacts and constitute the Model's
catalog of named configurations.

Examples:

``` text
artwork.default
shape.default
shape.ornament
shape.ornament-large
shape.coaster
shape.keychain
```

The local Variant name is Model-scoped. Therefore:

``` text
shape.default
artwork.default
```

are distinct Variants.

A Variant's complete identity consists of its Model and local Variant
name:

``` text
Variant identity = Model + local Variant name
```

A fully qualified Variant reference may represent that identity
compactly as `<model>.<local-name>`. For example:

``` text
Model name:          shape
local Variant name: ornament
Variant reference:  shape.ornament
```

A fully qualified Variant reference and a decomposed representation of
the Model name and local Variant name identify the same Variant. The
architecture does not require every internal data structure or interface
to use the same representation.

Existing implementation structures may decompose Variant identity into a
Model name and a local name. Historical implementation fields named
`realization` may serve as that local-name component. Such a
representation does not by itself imply a separate architectural
Realization identity and does not require renaming when its meaning is
otherwise unambiguous. For example:

``` text
model = shape
realization = ornament
```

may be a decomposed representation of:

``` text
variant = shape.ornament
```

Architectural meaning is determined by the relationship represented, not
by the historical field name.

Interfaces may accept a fully qualified Variant reference as a compact
alternative to supplying its Model name and local Variant name
separately. Such syntax does not introduce another identity mechanism;
it is another representation of the same Variant identity.

Selecting a Variant therefore necessarily selects its Model.

A `default` Variant should normally exist or be implicitly available so
that a Model remains directly usable without specialized Variant
selection. The `default` Variant represents the Model's ordinary
behavior. Because that behavior is established by Model defaults, the
`default` Variant may contain no parameter overrides.

A specialized Variant specifies only the parameter values that
distinguish its reusable configuration from the Model defaults. Adding a
new Feature or parameter to a Model therefore does not require modifying
every existing Variant when the new Model default already gives those
Variants the intended behavior.

A Variant is a reusable named configuration, not a second mechanism for
defining Feature semantics or duplicating the Model's complete
configuration.

## 4.7 Variant configuration and customization

Parameters may contribute to Model defaults, Variant overrides, or
Artifact-specific customization.

Effective parameter resolution is conceptually:

``` text
Model parameter defaults
        ↓
Variant parameter overrides
        ↓
Artifact-specific overrides
        ↓
effective Realization configuration
```

Variant definitions are intentionally sparse. A Variant need specify
only parameters whose values differ from the Model defaults. The Model
owns the semantics of those parameters, including any values that
enable, disable, or otherwise affect Feature participation.

For example, a Model may define an optional Feature whose width of zero
means that the Feature does not participate. A Variant may enable that
Feature simply by overriding the width with a positive value. The
generic Variant mechanism need not separately encode a boolean Feature
selection.

A Model author may intentionally define two Variants whose principal
difference is one or more parameter values when those Variants represent
distinct reusable catalog configurations.

For example:

``` text
shape.ornament
    size = 100

shape.ornament-large
    size = 125
```

are valid distinct Variants even if size is their only material
difference.

By contrast:

``` text
Artifact = mydog
Variant = shape.ornament
customization:
    size = 110
```

does not create another Variant. It produces a customized Realization
whose originating Variant remains `shape.ornament`.

Whether a configuration difference deserves a distinct Variant is
therefore a Model/catalog decision, not a mechanical consequence of
changing a parameter.

## 4.8 Realization

A Realization is the application of a Variant to an Artifact, with or

without Artifact-specific customizations.

A Realization has:

\-   one Artifact;

\-   one originating Variant;

\-   the Model identified by that Variant;

\-   effective Feature selections;

\-   effective parameter values;

\-   resolved inputs.

A Realization is concrete and Artifact-specific. A Variant is reusable

and Model-owned.

A Realization does not independently select a Model and a Variant. Its

Model is determined by its originating Variant.

A Realization is not an independently named reusable product

configuration. Reusable product configurations belong to Variants.

Conceptually:

``` text

mydog + shape.ornament

            │

            ▼

        Realization
```

and:

``` text

mydog + shape.ornament

        + size = 110

            │

            ▼

   customized Realization
```

both originate from `shape.ornament`.

### Variant and Realization invariants

\-   Every Variant belongs to exactly one Model.

\-   A Variant's complete identity includes its Model.

\- A Variant defines a reusable constructible catalog configuration through sparse parameter overrides over Model defaults. Feature participation is determined by the resulting effective parameter values according to Model-owned semantics.

\-   Every Realization originates from exactly one Variant.

\-   A Realization is produced by applying that Variant to an Artifact.

\-   Artifact-specific customizations may modify effective configuration

    without changing the originating Variant.

\-   Model and Variant are not independent selections within a

    Realization.

\-   Realization is not a second reusable configuration or

    catalog-definition mechanism.

\-   Distinct reusable catalog offerings are represented by distinct

    Variants.

\-   Two Variants may legitimately differ only by parameter values such

    as size.

## 4.9 Stage

A Stage is an executable node in a Realization.

A Stage consumes source inputs, configuration, and/or Products; performs

one or more transformations; and produces one or more Products.

Stages participate in a dependency graph.

## 4.10 Independent stage execution

A Stage is independently executable when supplied with a complete

resolved execution context.

Normal execution remains responsible for dependency traversal, selecting

required Stages, configuration resolution, Product-state evaluation,

resumability, dependency validation, and canonical Product locations.

Explicit Stage execution executes only the requested Stage and does not

implicitly execute dependencies.

## 4.11 Stage ID

A numeric Stage ID is a presentation ordinal used for deterministic

human-readable ordering and filesystem organization.

Stage IDs do not define Stage semantics, operation type, compatibility,

dependencies, execution order, or relationships between Stages in

different Models.

The semantic identity is the Stage name, not its numeric presentation.

## 4.12 Product

A Product is a named persistent output produced by a Stage.

Examples:

``` text

envelope

trace

colors

geometry

components

artifact
```

A Product may materialize as one file, multiple files, or a manifest

describing a collection of files.

All Products are first-class and reusable.

A Product is not the same concept as a Variant catalog offering.

## 4.13 Product collection

Variable physical files representing one logical Product should be

described by an explicit manifest such as `products.json`.

Consumers should consume the logical collection rather than infer

membership by globbing directory contents.

------------------------------------------------------------------------

# 5. Dimensional Semantics

## 5.1 Raster dimensions are not physical dimensions

Raster dimensions define raster coordinate space. They do not imply

millimeters or manufacturing size.

DPI metadata must not accidentally determine manufacturing dimensions

unless an Operation explicitly requests that behavior.

## 5.2 Vector dimensions are normally relative

Artwork preprocessing should preserve aspect ratio, relative dimensions,

relative positions, registration, and relationship to the envelope while

remaining independent of physical manufacturing size.

## 5.3 Physical X/Y dimensions are introduced late

Physical dimensions belong to the downstream Operation or Model that

introduces the physical constraint.

A Shape Variant may override default dimensions for its catalog
offering,

while the Shape Model owns the semantics of how those dimensions

constrain geometry.

## 5.4 Extrusion introduces physical Z

Conceptually:

``` text

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

## 5.5 Dimensional responsibility

Physical dimensions belong to the Operation or Model that introduces the

corresponding physical constraint.

Variant parameter overrides configure those semantics; they do not

transfer dimensional responsibility to the Variant abstraction itself.

------------------------------------------------------------------------

# 6. Registered Geometry

## 6.1 Registered 2D geometry

A registered 2D Product consists of one or more geometric components

sharing a coordinate system whose relative geometry must be preserved.

It may describe coordinate space, envelope, components, component

identifiers, colors/material roles, bounds, and other metadata.

## 6.2 Registration is invariant

Downstream consumers must preserve relative position, dimensions, aspect

ratio, alignment, and component registration unless modifying those

relationships is explicitly the responsibility of the Operation.

## 6.3 Consumers should treat payloads as opaque

Consumers depend upon Product contracts rather than knowledge of artwork

semantics.

A Shape Model consuming registered artwork should not need special cases

for portraits, houses, logos, text, or other source-specific content.

------------------------------------------------------------------------

# 7. Fitting

Fitting maps reusable relative geometry into a physical or relative

target region.

A consuming Model owns the region into which upstream geometry must fit.

The fit Operation computes one transformation for a registered component

and applies it consistently to all members.

Changing a Variant's physical dimensions should not require

re-rasterizing or re-vectorizing upstream artwork.

------------------------------------------------------------------------

# 8. Composition

Composition is recursive.

Registered geometry may be embedded into generated geometry, multiple

independent Products may be combined into a new coordinate space, and

the resulting registered composition may itself be consumed as an opaque

reusable component.

Composition must preserve each child component's internal registration

unless the composition Operation explicitly owns changing it.

------------------------------------------------------------------------

# 9. Models as Recipes

Models should increasingly be understood as recipes connecting reusable

Operations and Products.

A Model should not require a monolithic builder that understands

upstream artwork internals.

Variants configure the recipe by supplying sparse parameter overrides
over Model defaults. Those resolved parameter values may affect Feature
participation according to Model-owned semantics. Variants do not
replace Stages, Operations, Products, Features, or dependency
definitions.

------------------------------------------------------------------------

# 10. Logical Product References

Products must be addressable without filesystem paths.

A complete logical reference must identify enough context to resolve a

unique persistent Product.

Conceptually, the context includes:

``` text

Artifact

Variant

    └── Model is inherent in Variant identity

Realization context

Stage

Product
```

A serialized reference may continue to include explicit Artifact, Model,

Realization/Variant, Stage, and Product fields when that is useful to

the implementation.

For example:

``` text

nydeli:artwork:default:vector:colors
```

may represent the `vector:colors` Product of the Realization obtained by

applying `artwork.default` to `nydeli`.

The architecture does not require a particular number of colon-separated

fields. It requires that:

1\\.  references are logical;

2\\.  references are globally unambiguous within a Workspace;

3\\.  references do not contain generated filesystem paths;

4\\.  parsing and formatting are centralized;

5\\.  filesystem organization may change without changing Product

    semantics.

The existence of an engine-level Realization coordinate does not create

an independently named reusable configuration dimension.

------------------------------------------------------------------------

# 11. Product Resolver

A central resolver maps logical identity to definitions and physical

locations.

Conceptually:

``` text

logical Product reference

          │

          ▼

      ProductRef

          │

          ▼

    ProductResolver

          │

    ┌─────┴──────────────┐

    ▼                    ▼

Artifact context     ModelRegistry

                          │

                          ▼

                       ModelSpec

                          │

                          ▼

                       Variant

                          │

                          ▼

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

The resolver may answer which Artifact owns a Product, which Variant and

Model define the Realization, which Stage produces it, what its

ProductSpec is, and where it is materialized.

The resolver does not determine which Stages should execute.

------------------------------------------------------------------------

# 12. Filesystem Layout

Generated Products should mirror logical ownership.

Conceptually:

``` text

artifacts/

└── \\<artifact_id>/

    ├── artifact.png

    ├── artifact.toml

    │

    └── \\<model>/

        └── \\<realization>/

            └── \\<stage-id>-\\<stage-name>/

                └── products...
```

Because a Realization originates from a Variant, an implementation may

use the Variant's local name as the canonical Realization namespace when

one Realization of that Variant exists for the Artifact.

For example:

``` text

artifacts/

└── nydeli/

    └── artwork/

        └── default/

            ├── 10-prepare/

            ├── 20-raster/

            ├── 30-vector/

            ├── 40-extrude/

            └── 50-package/
```

The filesystem materializes logical ownership; it does not define the

domain model.

------------------------------------------------------------------------

# 13. Filesystem Invariants

## 13.1 One natural home

Every generated Product has exactly one canonical materialized location.

Publication or export mechanisms may separately expose convenient copies

or links without changing canonical ownership.

## 13.2 Stage ownership

Every generated Product belongs to the Stage that produced it.

## 13.3 Realization isolation

Products generated by separate Realizations occupy separate namespaces.

## 13.4 Artifact-level inputs remain artifact-level

Inputs and configuration belonging to the Artifact as a whole remain at

the Artifact level and should not be unnecessarily copied into every

Realization.

## 13.5 Path construction is centralized

Model and Stage implementation code must not construct global Artifact

paths directly.

Filesystem policy belongs to the resolver.

------------------------------------------------------------------------

# 14. ProductSpec Paths

A `ProductSpec` path is local to its producing Stage.

For example:

``` python

ProductSpec(

    name="envelope",

    path="envelope.svg",

)
```

rather than repeating global Artifact, Model, Realization, or Stage

ownership in the path.

------------------------------------------------------------------------

# 15. Defined Graph

The Defined Graph represents everything the system knows how to produce.

It is derived from:

``` text

registered Models

\+

Model-scoped Features

\+

Model-scoped Variants

\+

Stages

\+

Products

\+

declared dependencies
```

The Defined Graph exists independently of Artifact-specific

customization.

It must support validation of unknown Models, Features, Variants,

Stages, Products, missing producers, duplicate identities, invalid

dependencies, and cycles.

------------------------------------------------------------------------

# 16. Product Catalog

The Product Catalog is the technical catalog view of the Defined Graph.

It describes persistent Products the system knows how to produce and may

track their states:

``` text

DEFINED

ABSENT

INCOMPLETE

INVALID

STALE

CURRENT
```

This technical Product Catalog is distinct from the catalog of Variant

offerings exposed by a Model.

A Variant catalog answers:

> Which named reusable configurations may be applied to an Artifact?

The Product Catalog answers:

> Which persistent Stage Products can the build graph produce or reuse?

These concepts must not be conflated.

------------------------------------------------------------------------

# 17. Offering Catalog

Commercial or external presentation is separate from technical Product

identity.

A Model's Variants provide natural constructible catalog configurations

such as:

``` text

shape.ornament

shape.ornament-large

shape.coaster

shape.keychain
```

External presentation may attach additional metadata such as title,

description, price, availability, publication status, or customer-facing

imagery without changing Variant, Realization, Stage, or Product

identity.

Likewise, individual technical Products may be published or sold without

becoming architecturally privileged.

------------------------------------------------------------------------

# 18. Requested Graph

Artifact configuration describes source material, optional Variant

customizations, explicit advanced dependency bindings, and any requested

build scope.

Routine Artifact configuration must not need to redundantly redefine the

Model's Variant catalog.

Given required Artifact inputs, the system must be able to discover the

Model-owned Variants that are available for application to that

Artifact.

Conceptually:

``` text

Artifact: mydog

source: mydog.png

Shape Variants:

    ornament

    ornament-large

    coaster

    keychain
```

may produce four Realizations without requiring four independently named

Realization definitions in `artifact.toml`.

Artifact configuration may customize a Variant application. The exact

configuration syntax is an implementation concern, but its semantics

must remain:

``` text

Artifact + Variant + optional customization -> Realization
```

Explicit ProductRefs remain available for advanced composition and

producer selection.

------------------------------------------------------------------------

# 19. Realization Graph

A Realization Graph describes the Product dependency closure required

for one concrete Realization.

A Realization has already been established by applying one Variant to

one Artifact, including any Artifact-specific customization.

The Realization Graph therefore does not define the Variant or create a

second configuration identity. It determines which Products and Stages

are required to satisfy the requested outputs of that concrete

Realization.

Products in the Defined Graph that are not requested and are not

dependencies remain unrealized.

------------------------------------------------------------------------

# 20. Execution Plan

Conceptually:

``` text

Defined Graph

      │

      │ apply Variant to Artifact

      ▼

Realization

      │

      │ requested Products + dependency closure

      ▼

Realization Graph

      │

      │ state evaluation

      ▼

Execution Plan
```

The Execution Plan describes what must actually execute now.

If required Products are already current, their producing Stages do not

need to execute again.

Configuration validation follows required execution. Configuration

required by Stages that execute must be valid for those Stages.

Historical configuration used only to produce an already-current

reusable Product need not remain valid merely because that Product is

consumed.

The planner determines validation scope. Model-specific validation rules

remain Model-owned.

------------------------------------------------------------------------

# 21. Product State and Resumability

Build state exists at the Product/Stage level.

Useful states include:

``` text

ABSENT

INCOMPLETE

INVALID

STALE

CURRENT
```

A subsequent build should reuse current Products.

Variant or Artifact customization changes that affect a Product's

effective inputs must participate in freshness evaluation for the

Products they affect.

------------------------------------------------------------------------

# 22. Stage Completion

Directory existence does not imply successful completion.

Completion metadata or manifests should be written only after declared

Products have been successfully generated and validated.

------------------------------------------------------------------------

# 23. Manifests

Stages producing variable Product collections should explicitly describe

their outputs.

Consumers should not infer Product membership by globbing.

Manifests may include logical identifiers, paths, component roles,

colors, coordinate information, bounds, dimensions, hashes, relevant

configuration, Operation versions, and generation metadata.

------------------------------------------------------------------------

# 24. Source Analysis

Source analysis may identify properties useful for preprocessing, such

as alpha, background transparency, silhouette, aspect ratio, edge

contact, or approximate color count.

Automatic analysis must not silently control the entire build graph.

Configuration and Model policy must be able to override analysis.

------------------------------------------------------------------------

# 25. Reference Scenario: Artwork

A source image may be interpreted once:

``` text

mydog.png

    │

    ▼

artwork.default

    │

    ▼

prepare

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

The resulting geometry is dimension-independent and reusable by

downstream Realizations.

The artwork Model may also define extrusion and package Products, but

those Products need not be realized when a downstream consumer requires

only vector geometry.

------------------------------------------------------------------------

# 26. Reference Scenario: Circular Embedded Artwork

Registered artwork may be embedded within generated geometry such as a

circle.

The resulting registered composition remains reusable and need not yet

have a physical manufacturing diameter.

A downstream Shape Variant determines the physical constraints it

requires.

------------------------------------------------------------------------

# 27. Reference Scenario: Shape Variants

A Shape Model may define reusable Features:

``` text
artwork
outer-ridge
inner-ridge
lettering
hanger
```

The Shape Model defines the parameters, defaults, and semantics
governing those Features. It may then define sparse Variants such as:

``` text
shape.ornament
    size = 100
    outer_ridge_width = 2

shape.ornament-large
    size = 125
    outer_ridge_width = 2

shape.coaster
    size = 100

shape.keychain
    size = 45
    hanger_size = 4
```

Only values that differ from Shape's Model defaults need appear in a
Variant. Whether values such as `outer_ridge_width` or `hanger_size`
cause a Feature to participate is a Shape Model semantic, not a generic
Variant semantic.

These examples are conceptual; exact Feature names and parameter
semantics belong to the Shape Model's `DEFINITION.md`.

Applying these Variants to Artifact `mydog` yields distinct
Realizations:

``` text
mydog + shape.ornament
mydog + shape.ornament-large
mydog + shape.coaster
mydog + shape.keychain
```

No Artifact-specific parameter selection is required merely to make
these Variants usable when Model defaults and Variant overrides already
provide the intended reusable configuration.

# 28. Reference Scenario: Customized Variant

Suppose `shape.ornament` defaults to 100 mm.

Artifact `mydog` may customize its application:

``` text

shape.ornament

    size = 110

    lettering = disabled
```

The resulting Realization remains an application of `shape.ornament`.

Customization does not create a new Variant.

If the Model author intentionally wants a reusable 110 mm catalog

offering, that offering may instead be defined as another Variant.

------------------------------------------------------------------------

# 29. Reference Scenario: Multiple Artwork Components

A larger object may contain several independent pieces of artwork from

the same or different Artifacts.

Only the upstream Products actually required by the composition are

realized. Already-current Products are reused.

------------------------------------------------------------------------

# 30. Cross-Model Dependencies

Models may consume Products generated by other Models.

A consumer depends upon the required Product, not completion of the

producer's entire Model or Realization.

------------------------------------------------------------------------

# 31. Cross-Artifact Dependencies

Dependencies may cross Artifact boundaries.

`artifact_id` is therefore one coordinate in a Workspace-wide dependency

graph.

------------------------------------------------------------------------

# 32. Configuration Versus Dependency Wiring

Model specifications declare Product dependencies that Stages know how

to consume.

A declared Product dependency identifies a producer contract

independently of a particular producer Artifact or Realization.

A Product dependency binding associates that dependency with a concrete

producer Artifact and Realization.

Conceptually:

``` text

ProductDependencySpec

        │

        │ bound for a consuming Realization

        ▼

ProductDependencyBinding

        │

        ▼

ProductRef
```

A declared dependency does not require every Variant or Realization of

the consumer Model to use it.

Feature and Variant semantics may determine whether a dependency

participates, but generic dependency infrastructure must not contain

Model-specific rules.

Normal users should not need to manually wire routine internal

dependencies.

Explicit logical Product references remain available for advanced

composition and producer selection.

Generated filesystem paths must not be used as dependency identity.

------------------------------------------------------------------------

# 33. Separation of Responsibilities

## Configuration system

Responsible for:

\-   loading configuration;

\-   applying defaults;

\-   resolving Variant defaults;

\-   applying Artifact-specific customizations;

\-   validating resolved values;

\-   tracking provenance.

It does not define Model-specific Feature semantics or execute geometry.

## Model registry

Responsible for:

\-   discovering Models;

\-   registering ModelSpec definitions;

\-   exposing Model metadata;

\-   exposing Features;

\-   exposing Variants.

## Model specification

Responsible for declaring:

\-   inputs;

\-   parameters;

\-   Features;

\-   Variants;

\-   Stages;

\-   dependencies;

\-   Products;

\-   Product contracts.

A Variant definition is part of the Model specification.

## Product resolver

Responsible for:

\-   parsing logical references;

\-   resolving Artifacts;

\-   resolving Realizations and their originating Variants/Models;

\-   resolving Stages;

\-   resolving Products;

\-   constructing canonical filesystem locations.

It does not decide what must execute.

## Build graph builder

Responsible for constructing and validating the Defined Graph.

## Build planner

Responsible for:

\-   selecting requested Products;

\-   computing dependency closure;

\-   constructing Realization Graphs;

\-   evaluating Product state;

\-   constructing Execution Plans.

## Stage runner

Responsible for executing planned Stages, validating execution results,

recording Products and completion state, and reporting structured

execution events.

## Stage implementation

Responsible for performing Model-specific transformations, consuming

resolved inputs, and generating declared Products.

Stage implementations must not encode global filesystem policy.

## Printer colors and color catalog

Printer and library color configuration, color reference data, and

Model-specific color semantics remain separate from the

Variant/Realization distinction.

Models may reference shared color catalog data. Model-specific color

selection, assignment, inheritance, matching, and use belong to the

applicable Model definition.

------------------------------------------------------------------------

# 34. Architectural Invariants

## Invariant 1 --- First-class Products

Every persistent generated output is a Product.

## Invariant 2 --- No privileged final Product

A 3MF is not architecturally privileged.

## Invariant 3 --- One canonical home

Every generated Product has exactly one canonical materialized location.

## Invariant 4 --- Stage ownership

Every generated Product belongs to the Stage that generated it.

## Invariant 5 --- Logical references

Products are referenced logically rather than through generated

filesystem paths.

## Invariant 6 --- Central resolution

The resolver is authoritative for mapping logical identity to physical

location.

## Invariant 7 --- Dependency-driven execution

Dependencies determine execution order. Stage IDs and filesystem

ordering do not.

## Invariant 8 --- Complete definitions are validatable

The complete set of Model, Feature, Variant, Stage, Product, and

dependency definitions must be validatable even when only a subset is

realized.

## Invariant 9 --- Minimal realization

Only the dependency closure necessary for requested Products needs to be

realized.

## Invariant 10 --- Current Products are reusable

Current Products may satisfy dependencies without rerunning their

producers.

## Invariant 11 --- Cross-Model reuse

Products may be consumed by other Models.

## Invariant 12 --- Cross-Artifact reuse

Products may be consumed by other Artifacts.

## Invariant 13 --- Dimension independence

Reusable preprocessing geometry should remain independent of physical

manufacturing dimensions wherever practical.

## Invariant 14 --- Late dimensionalization

Physical dimensions are introduced by the downstream Model or Operation

that owns the corresponding constraint.

## Invariant 15 --- Registration preservation

Registered geometry remains registered unless an Operation explicitly

owns changing those relationships.

## Invariant 16 --- Opaque consumption

Consumers depend on Product contracts rather than source-specific

payload semantics.

## Invariant 17 --- Recursive composition

Compatible registered geometry may be recursively composed and reused.

## Invariant 18 --- Model-scoped Features

Features belong to Models and express optional composable capabilities.

## Invariant 19 --- Model-scoped Variant identity

Every Variant belongs to exactly one Model. Its complete identity

includes that Model.

Selecting a Variant therefore selects its Model.

## Invariant 20 --- Sparse Variant configuration

A Variant is a named, Model-scoped set of parameter overrides over Model
defaults. A Variant need not repeat parameters whose Model defaults
already provide the intended behavior.

The `default` Variant may contain no parameter overrides. Adding a Model
Feature or parameter does not require modifying existing Variants when
the new Model default already provides their intended behavior.

## Invariant 21 --- Realization is application

A Realization is the application of one Variant to one Artifact, with or

without Artifact-specific customizations.

## Invariant 22 --- Variant is not Realization

A Variant is reusable and Model-owned.

A Realization is concrete and Artifact-specific.

Realization must not become a second reusable configuration or catalog

definition mechanism.

## Invariant 23 --- Customization preserves originating Variant

Artifact-specific customization may alter effective parameter values and
therefore may alter Feature participation according to Model-owned
semantics, without changing the originating Variant.

## Invariant 24 --- Catalog differences may be dimensional

Distinct Variants may legitimately differ only by parameter values such

as physical size when they represent intentionally distinct catalog

offerings.

## Invariant 25 --- Manifests define collections

Variable Product collections are explicitly described rather than

inferred from directory contents.

## Invariant 26 --- Directory existence is not completion

A Stage directory existing does not imply successful completion.

## Invariant 27 --- No Model-specific engine behavior

The generic engine must not special-case the geometry or semantics of a

particular Model.

## Invariant 28 --- No global path construction in Models

Model implementations do not construct global Artifact filesystem paths.

## Invariant 29 --- Common workflows remain simple

Architectural flexibility must not require users to manually configure

routine dependency wiring or redundantly enumerate the Model's Variant

catalog.

## Invariant 30 --- Observable, presentation-independent execution

Execution semantics must not depend upon presentation or observer

policy.

## Invariant 31 --- Validation follows required execution

Configuration validation applies to Stages required by the Execution

Plan.

Historical configuration and source inputs used only to produce an

already-current persistent Product do not need to remain valid for that

Product to be reused.

------------------------------------------------------------------------

# 35. Architectural Acceptance Tests

A proposed architecture or refactor should be able to represent the

following without special cases.

### Case A --- Standalone artwork

One PNG is converted through artwork preparation, rasterization,

vectorization, and, when requested, extrusion and packaging.

### Case B --- Shape ornament Variant

The same registered artwork is applied to `shape.ornament`, whose sparse
parameter overrides over Shape defaults define the reusable ornament
configuration.

The standalone artwork 3MF is not required.

### Case C --- Shape keychain Variant

The same registered artwork is reused through `shape.keychain` at a
smaller physical size with parameter values whose Shape-owned semantics
produce the keychain behavior.

Rasterization and vectorization are not repeated merely because the

physical size changes.

### Case D --- Shape coaster Variant

The same registered artwork is used through `shape.coaster`, which
overrides the Shape defaults needed for the reusable coaster
configuration.

### Case E --- Multiple catalog Variants

Given Artifact `mydog` and the required source input, the system can

discover and realize:

``` text

shape.ornament

shape.ornament-large

shape.coaster

shape.keychain
```

without requiring `artifact.toml` to redefine each Variant's parameter
overrides.

### Case F --- Customized Variant application

Artifact `mydog` may customize `shape.ornament` without creating or

renaming the originating Variant.

### Case G --- Multiple-artwork composition

Registered artwork from multiple Artifacts is composed into a larger

design and used by another Realization.

Only required upstream Products are realized.

If a proposed resolver, filesystem layout, Model definition, Variant

definition, ProductRef, or planner cannot cleanly represent all of these

cases, the design should be reconsidered before implementation.

------------------------------------------------------------------------

# 36. Implementation Alignment

The repository should evolve incrementally toward the architecture

defined by this document and the normative definitions of its Models.

Implementation work should begin by comparing the current repository

against:

``` text

ARCHITECTURE.md

model/models/\\<model>/DEFINITION.md
```

Differences between permanent specifications and implementation should

be captured in a temporary `CHANGEPLAN.md` as small, independently

testable changes.

Existing implementation terminology does not override this architecture.

In particular, an implementation that permits independently named

Realizations to act as reusable product configurations must be

reconciled with the normative Variant/Realization semantics defined

here.

When the repository conforms to the permanent specifications, the

temporary change plan is no longer required.

------------------------------------------------------------------------

# 37. Guidance for Future Changes

When proposing a feature or refactor, ask:

1\\.  What Products does this Operation consume?

2\\.  What Products does it produce?

3\\.  Which Stage owns each Product?

4\\.  Are dependencies expressed logically?

5\\.  Can the resolver uniquely locate every Product?

6\\.  Is this geometry relative or physically dimensioned?

7\\.  Which Model or Operation owns the physical dimension?

8\\.  Does the transformation preserve registered geometry?

9\\.  Does the consumer unnecessarily understand its input payload?

10\\. Can current upstream Products be reused?

11\\. Can another Model or Artifact consume this Product?

12\\. Does the change introduce Model-specific behavior into the generic

    engine?

13\\. Does filesystem organization remain an implementation detail?

14\\. Is the behavior a Model Feature?

15\\. If it is a reusable catalog configuration, is it represented as a

    Variant?

16\\. Does the Variant define its reusable offering through sparse parameter overrides over Model defaults, with Feature participation remaining governed by Model-owned parameter semantics?

17\\. Is a proposed Realization truly an application of a Variant to an

    Artifact, rather than another reusable configuration definition?

18\\. Does Artifact customization preserve the originating Variant?

19\\. Can the Model's Variant catalog be discovered without redundant

    Artifact configuration?

20\\. Does the common user workflow remain simple?

Warning signs include designs that:

\-   treat Variant as merely a parameter preset;

\-   allow Model and Variant to become independent Realization

    selections;

\-   create independently named Realizations as reusable catalog

    definitions;

\-   require Artifact configuration to repeat Variant Features or

    defaults merely to make a Variant buildable;

\-   automatically create a new Variant identity for every parameter

    override;

\-   prohibit useful dimensional Variants merely because their primary

    difference is size;

\-   confuse Variant catalog offerings with persistent Stage Products;

\-   require a complete producer Model to execute before consuming an

    upstream Product;

\-   treat a 3MF as the definition of Model completion;

\-   rerasterize or revectorize artwork merely because physical output

    size changed;

\-   embed generated filesystem paths in configuration;

\-   independently scale registered components;

\-   duplicate Products merely to create a convenient output directory.

------------------------------------------------------------------------

# 38. Summary

`lowkey-artifact-builder` is a dependency-driven 2.5D manufacturing

system.

Its core product-definition relationship is:

``` text

Model

  ├── Features

  └── Variants

Variant

  = Model-scoped reusable configuration

  = sparse parameter overrides over Model defaults

Realization

  = application of Variant to Artifact

    + optional Artifact-specific customizations

```

A Model's Variants form a reusable catalog of named configurations.

For example:

``` text

shape.ornament

shape.ornament-large

shape.coaster

shape.keychain
```

may all be applied to the same Artifact and source image without

requiring the Artifact to redefine their Variant parameter overrides.

A customized application remains a Realization of its originating

Variant.

Underneath this catalog model is a general Product dependency graph.

Source interpretation produces reusable relative and registered

geometry. Downstream Models introduce the physical constraints they own.

Registered components preserve their internal geometry. Composition may

combine Products from the same Artifact or different Artifacts.

Every persistent Stage output is a first-class Product.

The Defined Graph describes what the system knows how to produce. A

Realization Graph describes the dependency closure required for one

application of a Variant to an Artifact. The Execution Plan determines

what work must actually run.

Current Products are reused.

A 3MF is simply one possible Product.

The long-term manufacturing objective is:

> interpret source material once, preserve reusable manufacturing

> assets, and create increasingly sophisticated physical products by

> applying Model-owned Variants to Artifacts and composing

> generic, well-defined operations with minimal manual intervention.
