# Change Plan

This document tracks the remaining incremental work required to bring
`lowkey-artifact-builder` into conformance with its permanent specifications
and to complete the initial integration between the Shape and Artwork models.

The permanent normative specifications are:

```text
ARCHITECTURE.md

src/lowkey_artifact_builder/model/models/artwork/DEFINITION.md

src/lowkey_artifact_builder/model/models/shape/DEFINITION.md
```

`CHANGEPLAN.md` is not a normative specification. It records the current
implementation path from repository HEAD toward those specifications.

Completed historical phases have been removed from this document.

The current repository already contains the graph, resolver, product-state,
resumability, execution-event, independent-stage-execution, cross-model,
cross-artifact, registered-geometry, Shape structural-geometry, outer-ridge,
extrusion, and packaging foundations established by earlier work.

The current Shape implementation can produce a complete printable
`artifact.3mf` containing structural Shape geometry without incorporated
Artwork.

Before selecting each implementation slice, compare repository HEAD against
the permanent specifications rather than assuming this plan remains complete.

## Status

```text
Phase 1 — Started
Phase 2 — Not started
Phase 3 — Not started
```

# Development Method

Development is test-driven and incremental.

For each slice:

1. Identify one small unmet architectural or model invariant.
2. Determine the observable behavior that demonstrates the invariant.
3. Write or revise the smallest useful test that expresses that behavior.
4. Confirm that the new test fails for the intended reason.
5. Make the smallest production-code change necessary to satisfy the test.
6. Refactor only after the required behavior is green.
7. Run the affected tests.
8. Run the complete test, lint, formatting, and type-check suite.
9. Commit the independently working slice.
10. Reevaluate repository HEAD before selecting the next slice.

A slice should normally establish one new capability or invariant rather than
implement an entire phase or architectural subsystem.

Tests should preferentially express semantic contracts and invariants rather
than incidental implementation details.

The existing Artwork model remains the primary regression baseline.

The completed structural Shape-to-3MF path remains the Shape regression
baseline.

# Phase 1 — Shape Component Colors

Complete the color semantics required by the Shape model.

Shape already produces structural base and outer-ridge geometry. This phase
associates semantic printing colors with those components and preserves those
color identities through extrusion and packaging.

Color is a property of a model component.

A model does not assign a component to a physical printer head.

Conceptually:

```text
Shape component
      │
      ├── role
      │     base
      │     ridge
      │
      └── semantic color
            white
            red
            black
            ...
                  │
                  ▼
            dimensionalization
                  │
                  ▼
          printable component
                  │
                  ▼
             packaging
                  │
                  ▼
            artifact.3mf
```

The packaged component must retain sufficient semantic color identity for the
slicer or user to associate that component with the appropriate physical
printer head later.

The model and generic build engine do not perform that printer-head
assignment.

## 1.1 Complete Shape Color Specification

Before implementing Shape color behavior, reconcile the Shape definition with
the color mechanism required by its existing semantics.

The Shape definition already requires:

* an independently assignable base color;
* an independently assignable outer-ridge color;
* the outer-ridge color to default to the base color;
* integrated and separate ridges to support independent color assignment;
* color distinctions to remain representable through dimensionalization and
  packaging.

The definition names:

```text
shape_outer_ridge_color
```

but the current specification must also identify the parameter controlling the
base color.

Define:

```text
shape_base_color
```

in `shape/DEFINITION.md`.

The specification must establish:

* `shape_base_color` identifies the semantic printing color of the Shape base;
* `shape_outer_ridge_color` identifies the semantic printing color of the
  outer ridge;
* Shape colors are semantic color names;
* semantic color names are resolved through the shared color catalog;
* the default `shape_outer_ridge_color` is the resolved
  `shape_base_color`;
* explicitly configuring `shape_outer_ridge_color` overrides that default;
* color does not alter registered or physical geometry;
* color does not determine ridge existence;
* color does not determine ridge style;
* Shape does not assign colors to physical printer heads.

Select and document the default base color before implementing it.

Do not invent a Shape-specific RGB or filament representation.

Shape should use the shared color semantics already provided by:

```text
src/lowkey_artifact_builder/colors.py
```

## 1.2 Shape Color Configuration and Resolution

Add the minimum Shape configuration required by the permanent definition.

Tests should establish that:

* `shape_base_color` has the defined model default;
* `shape_base_color` may be overridden normally;
* `shape_outer_ridge_color` defaults to the resolved
  `shape_base_color`;
* changing the base color changes the default ridge color;
* explicitly configuring the ridge color makes it independent of later base
  color resolution;
* configured Shape color names resolve through the shared color catalog;
* invalid color names fail through the normal shared color-resolution
  mechanism;
* Shape color configuration does not require knowledge of printer-head
  positions.

Use the existing configuration derivation mechanism when appropriate rather
than duplicating default-resolution behavior inside Shape stages.

In particular, the semantic relationship:

```text
shape_outer_ridge_color defaults to shape_base_color
```

should be represented as a resolved configuration relationship rather than by
copying one literal default value into two independent parameters.

## 1.3 Color-Aware Shape Components

Associate semantic color identity with the physical components produced by
Shape extrusion.

Use the existing shared color abstraction where appropriate:

```text
PaletteColor

resolve_palette_color()
```

Shape does not need perceptual color matching because Shape already knows the
semantic color requested for each structural component.

Shape therefore should not use Artwork-specific matching behavior such as:

```text
MeasuredColor
assign_colors()
color_distance()
```

Tests should establish that the extrusion product or its manifest identifies
each physical component by both:

* structural role;
* semantic color.

For example, conceptually:

```text
base
    color = white

ridge
    color = red
```

The physical filename may preserve both identities when appropriate, for
example:

```text
base-white.stl
ridge-red.stl
```

Exact persistent naming must remain centralized and tested rather than inferred
by downstream directory scanning.

Color metadata should include the shared semantic color identity and the RGB
representation needed by downstream packaging where that representation is
part of the established component contract.

## 1.4 Ridge Color Semantics

Apply Shape's existing ridge-color semantics to the physical component
partition already established by the Shape model.

Tests must cover the meaningful structural cases.

### No ridge

When:

```text
shape_outer_ridge_width = 0
```

there is no physical ridge component or ridge-color volume.

The base retains its configured color.

Ridge color configuration does not create geometry.

### Separate ridge

When the ridge is separately printable and has physical volume:

```text
base
    -> shape_base_color

ridge
    -> shape_outer_ridge_color
```

Base and ridge may use the same or different colors.

Their colors do not alter their established geometry.

### Integrated ridge with positive raise

When:

```text
shape_outer_ridge_style = integrated
shape_outer_ridge_raise > 0
```

the base material retains the base color.

Only the physical ridge volume above the base top receives the independently
assigned ridge color.

Conceptually:

```text
base
    Z = 0 through shape_base_raise
    color = shape_base_color

upper ridge
    Z = shape_base_raise
        through
        shape_base_raise + shape_outer_ridge_raise
    color = shape_outer_ridge_color
```

### Integrated ridge with zero or negative raise

When:

```text
shape_outer_ridge_raise <= 0
```

no independently colored ridge volume exists above the base.

The established structural geometry remains unchanged.

The semantic ridge region may continue to exist in registered geometry, but
color configuration must not manufacture an otherwise nonexistent physical
ridge-color component.

### Zero-height separate ridge

At:

```text
shape_outer_ridge_raise = -shape_base_raise
```

the separate ridge remains semantically defined but has zero physical volume.

Packaging must not invent physical ridge geometry merely to represent its
color.

## 1.5 Preserve Color Identity Through Packaging

Extend Shape packaging so that semantic component/color identity survives into
the Shape `artifact.3mf`.

Tests should verify that:

* the base remains identifiable by role and semantic color;
* a physically present independent ridge remains identifiable by role and
  semantic color;
* an integrated positive ridge with a distinct physical upper-ridge component
  retains its ridge color identity;
* absent or zero-volume ridge-color geometry is not invented during packaging;
* base and ridge may share a semantic color;
* base and ridge may use different semantic colors;
* packaging consumes component metadata rather than independently re-resolving
  Shape color policy;
* packaging does not assign physical printer heads.

The resulting 3MF should expose independently printable objects with useful
component/color identities so that the slicer can subsequently associate those
objects with the appropriate loaded printer colors.

Where Artwork and Shape demonstrate the same model-independent packaging
requirement, prefer a shared operation or format capability rather than
duplicating packaging mechanics.

Do not generalize merely because two implementations contain superficially
similar code. Extract only a demonstrated common contract.

## 1.6 Shape Color Acceptance

Add end-to-end evidence that a colored structural Shape produces a valid
multicomponent `artifact.3mf`.

At minimum demonstrate:

* a base-only Shape with a configured color;
* a Shape whose separate ridge uses a color different from the base;
* a Shape whose positive integrated ridge uses a color different from the
  base;
* the packaged objects preserve their semantic role/color identities;
* changing colors does not change the intended assembled geometry.

Completion of Phase 1 means the structural Shape model conforms to its
base/ridge color semantics and produces a packaged artifact in which every
physical structural component has the appropriate semantic color identity.

# Phase 2 — Shape and Registered Artwork Composition

Add optional registered Artwork consumption to Shape.

This phase exercises the central architecture:

> Source Artwork is interpreted once as reusable registered geometry and is
> subsequently fitted, dimensionalized, and manufactured by a downstream
> Shape without repeating upstream interpretation merely because the physical
> Shape changes.

Shape consumes the registered Artwork product.

Shape does not consume the standalone Artwork 3MF.

## 2.1 Artwork Dependency Contract

Review the Artwork definition and current vector-product manifest before
declaring Shape's dependency.

Establish the exact product contract Shape consumes.

The contract must provide sufficient information for Shape to:

* discover Artwork component membership;
* identify the common registered coordinate system;
* determine the registered Artwork envelope;
* preserve registration;
* retain semantic component/color identity;
* locate the component payloads through resolved product information rather
  than generated global paths.

If the existing Artwork vector product already satisfies this contract, use it
without changing Artwork.

If the contract is incomplete relative to the permanent Artwork definition,
strengthen the producer contract before adding Shape-specific assumptions.

## 2.2 Artwork Dependency Binding

Declare Shape's optional dependency on registered vector Artwork.

Tests must demonstrate that:

* Shape can exist and build without Artwork;
* Shape may bind to registered Artwork belonging to the same artifact;
* Shape may bind to registered Artwork belonging to another artifact;
* the dependency is represented by logical product identity;
* dependency resolution supplies the registered Artwork product to Shape;
* requesting Shape realizes only the required Artwork dependency closure;
* Artwork `prepare`, `raster`, and `vector` execute when necessary;
* Artwork `extrude` and `package` are not required;
* current upstream vector Artwork is reused without unnecessary execution.

Use the existing cross-model and cross-artifact dependency mechanisms.

Do not introduce Shape-specific behavior into the generic engine.

Do not place generated filesystem paths in Shape configuration.

## 2.3 Shape Interior Region

Use Shape's registered structural geometry to define the region available for
incorporated Artwork.

Tests should establish that:

* without a ridge, the available region is bounded by the Shape boundary;
* with a ridge, the available region is bounded by the ridge inner boundary;
* integrated and separate ridge styles expose the same Artwork region for
  otherwise identical ridge geometry;
* changing ridge width changes the available Artwork region;
* changing ridge style alone does not;
* changing ridge raise alone does not;
* changing Shape color does not;
* changing `shape_size` changes later physical dimensionalization rather than
  the registered interior geometry.

The interior-region contract should remain registered and nonphysical until the
downstream dimensionalization operation introduces physical size.

## 2.4 Registered Artwork Fitting

Fit registered Artwork into the available Shape interior.

Use contain-style fitting unless the Shape definition is intentionally changed
before implementation.

Tests must demonstrate that incorporated Artwork is:

* centered;
* uniformly scaled;
* aspect-ratio preserving;
* completely contained within the available interior region;
* transformed using one common transformation for every registered component;
* still represented in the same registered Shape coordinate system after
  composition.

The consumer must treat Artwork as registered geometry rather than fitting
individual color components independently.

Changing Shape geometry, size, ridge dimensions, ridge style, or structural
colors must not require Artwork rasterization or vectorization to be repeated
unless the upstream Artwork product is otherwise stale.

## 2.5 Registered Composition Product

The Shape composition stage should produce a registered composition containing:

```text
structural Shape geometry
        +
registered Artwork geometry
```

The resulting product must preserve:

* the Shape coordinate system;
* Shape structural boundaries;
* Artwork component registration;
* Artwork semantic color identity;
* component membership;
* the relationship between the Shape interior and fitted Artwork.

The registered composition remains conceptually distinct from physical
manufacturing geometry.

Consumers should use its declared product/manifest contract rather than infer
members by scanning files.

## 2.6 Artwork Physical Z Semantics

Before implementing physical extrusion of incorporated Artwork, verify that
`shape/DEFINITION.md` completely specifies the required Artwork Z semantics.

The permanent specification must determine:

* where incorporated Artwork begins in Z;
* Artwork extrusion height;
* its relationship to the base top;
* its relationship to the outer ridge;
* how independently printable Artwork color components remain physically
  associated with the Shape;
* whether any required physical overlap is a geometric operation or explicit
  model parameter;
* whether ridge partitioning changes Artwork Z semantics.

If any of these semantics remain undefined, update `shape/DEFINITION.md`
before implementing them.

Do not allow current Artwork standalone extrusion behavior to silently define
Shape's incorporated-Artwork semantics.

## 2.7 Dimensionalize Incorporated Artwork

Dimensionalize the complete registered Shape composition.

Tests must establish that:

* one physical X/Y transformation is applied consistently to all registered
  Artwork components;
* the transformation corresponds to `shape_size`;
* Artwork retains its registration after dimensionalization;
* Artwork physical Z follows the Shape definition;
* Artwork components remain independently printable by semantic color;
* Shape structural colors remain independent from Artwork colors;
* components sharing the same semantic color are allowed to remain distinct
  semantic/structural components;
* geometry does not depend on printer-head assignment.

Physical dimensionalization belongs to Shape because Shape owns the physical
manufacturing dimensions of the composed object.

## 2.8 Shape Packaging with Artwork

Package structural Shape components and incorporated Artwork components into
the declared Shape:

```text
artifact.3mf
```

Tests should verify:

* Shape without Artwork still packages successfully;
* Shape with Artwork packages successfully;
* structural components remain present;
* base color identity survives packaging;
* physical ridge color identity survives packaging;
* Artwork color components remain independently printable;
* Artwork semantic color identity survives packaging;
* component names provide useful semantic role/color identity;
* packaging does not require the standalone Artwork 3MF;
* packaging does not assign components to printer heads.

The resulting 3MF should provide the slicer with independently identifiable
colored objects from which physical printer-head assignments can be made.

## 2.9 Shape + Artwork Acceptance

Add end-to-end acceptance coverage for at least:

```text
source PNG
    ↓
Artwork prepare
    ↓
Artwork raster
    ↓
Artwork vector
    ↓
registered Artwork
    ↓
Shape composition
    ↓
Shape dimensionalization/extrusion
    ↓
Shape artifact.3mf
```

Acceptance evidence should demonstrate:

* the standalone Artwork extrusion and package stages are not required;
* Shape introduces the physical manufacturing dimensions;
* Artwork registration is preserved;
* structural and Artwork color identities survive into the packaged Shape;
* the resulting 3MF is valid and printable as a multicomponent artifact.

Completion of Phase 2 means registered Artwork can be reused as a genuine
upstream manufacturing asset by Shape.

# Phase 3 — Architectural Acceptance and Generalization

Use the completed colored Shape + Artwork model to validate the broader
architecture and extract only common mechanics demonstrated by actual use.

## 3.1 Same Artwork, Different Shapes

Demonstrate that one registered Artwork product can feed Shape realizations
with different:

* geometry;
* polygon side count;
* polygon rotation;
* `shape_size`;
* base thickness;
* ridge dimensions;
* ridge styles;
* base colors;
* ridge colors.

The upstream registered vector Artwork must remain reusable and
dimension-independent.

Physical Shape changes must not cause unnecessary Artwork rasterization or
vectorization.

## 3.2 Cross-Artifact Shape Composition

Build a Shape artifact that consumes registered Artwork belonging to another
artifact.

Verify end-to-end that:

* logical dependency identity crosses the artifact boundary;
* the resolver supplies the canonical upstream product;
* only required upstream stages are realized;
* current upstream products are reused;
* no generated filesystem path appears in artifact configuration;
* semantic color identities survive the cross-artifact composition.

## 3.3 Architecture Acceptance Scenarios

Review the acceptance scenarios in `ARCHITECTURE.md` against repository HEAD.

Maintain or establish executable evidence for the scenarios already supported
by the current models, including:

* standalone Artwork;
* registered Artwork reused by another manufactured object;
* different physical sizes using the same registered Artwork;
* circular structural composition;
* polygon structural composition;
* optional integrated structural ridge;
* optional separately printable structural ridge;
* equivalent assembled geometry across ridge styles;
* independently assigned structural colors;
* preserved Artwork color identity;
* cross-model reuse;
* cross-artifact reuse.

Do not force ornament, keychain, labels, hangers, multiple-Artwork composition,
or arbitrary placement into Shape merely to make every future architecture
scenario executable.

Those capabilities should be introduced through subsequent model definitions
or deliberate Shape extensions when their semantics are ready to be specified.

## 3.4 Reevaluate Shared Color and Component Contracts

After Artwork and Shape both produce and package semantically colored
components, review their implementations for demonstrated common contracts.

Potential shared concepts include:

* semantic component identity;
* semantic color identity;
* RGB metadata representation;
* component-manifest serialization;
* component-manifest validation;
* 3MF component naming;
* 3MF packaging.

Preserve the distinction between:

```text
model policy
    decides what a component means
    decides which semantic color belongs to it

shared color infrastructure
    resolves semantic color names
    provides common color representations

shared packaging mechanics
    preserve component/color identity

slicer
    assigns packaged objects to physical printer heads
```

Do not move model color-selection policy into generic color or packaging code.

Do not add printer-head assignment to Artwork, Shape, the generic engine, or
the generic color subsystem.

## 3.5 Reevaluate Shared Geometry Operations

After Shape and Artwork both exercise the required geometry mechanics,
reevaluate the codebase for demonstrated common operations.

Likely candidates include:

* scale;
* translate;
* fit;
* inset/offset;
* extrusion;
* registered-component transformation;
* packaging/component assembly.

At that point:

* extract duplicated model-independent mechanics;
* keep model policy in model stages;
* avoid inheritance between model pipelines;
* avoid one model invoking another model's stage implementation;
* retain `StageContext` as the independent stage execution boundary;
* keep the generic engine free of Shape- and Artwork-specific behavior.

In particular, remove model-to-model stage reuse when the two model contexts
have demonstrated the reusable mechanical contract that should replace it.

Do not introduce an operation framework merely to rename functions.

## 3.6 Completion Review

When the preceding work is complete, perform a fresh repository-wide
conformance review against:

```text
ARCHITECTURE.md

src/lowkey_artifact_builder/model/models/artwork/DEFINITION.md

src/lowkey_artifact_builder/model/models/shape/DEFINITION.md
```

Do not evaluate completion against historical phases in this file.

Identify any remaining meaningful differences between permanent
specifications and repository HEAD.

If no differences remain within the implemented model scope, remove
`CHANGEPLAN.md`.

If differences remain, replace this plan with a new plan containing only the
remaining work and restart phase numbering as appropriate.

# Continuous Activities

Throughout all phases:

* treat `ARCHITECTURE.md` and model `DEFINITION.md` files as normative;
* compare repository HEAD against those specifications before selecting each
  slice;
* keep `CHANGEPLAN.md` synchronized with discovered remaining work;
* preserve working Artwork behavior unless an intentional specification change
  requires otherwise;
* preserve the completed structural Shape-to-3MF pipeline;
* add tests before production implementation for each behavioral slice;
* prefer invariant and contract tests over implementation-specific tests;
* maintain unit tests for specifications and value objects;
* maintain integration tests for graph, resolver, dependency, and execution
  behavior;
* maintain end-to-end Artwork regression coverage;
* extend end-to-end Shape coverage incrementally;
* keep products logically addressed and canonically resolved;
* keep registered geometry independent of manufacturing size until the
  responsible downstream operation introduces that size;
* preserve registration through common transformations;
* preserve semantic component/color identity through manifests and packaging;
* keep model color policy independent of physical printer-head assignment;
* consume dynamic collections through manifests rather than filesystem scans;
* keep engine behavior model-independent;
* keep model implementations free of global filesystem policy;
* keep structured execution events semantic and presentation-independent;
* extract reusable operations only after multiple model contexts demonstrate
  the common mechanical contract;
* run the complete project quality suite after every completed slice;
* remove obsolete code and tests once replacement behavior is established;
* update a model `DEFINITION.md` before implementing a deliberate change to
  that model's normative semantics.

# Slice Selection Rule

Do not implement an entire phase at once.

Before beginning a slice:

1. Review `ARCHITECTURE.md`.
2. Review the applicable model `DEFINITION.md`.
3. Review this `CHANGEPLAN.md`.
4. Inspect current repository HEAD.
5. Identify the smallest meaningful unmet invariant.
6. Identify the layer at which that invariant should be tested.
7. Write the test first.
8. Confirm the test fails for the expected missing behavior.
9. Make the smallest implementation change that makes it pass.
10. Run the complete quality suite.
11. Commit the working slice.
12. Reevaluate HEAD before choosing the next slice.

A later item in a phase is not authorization to implement it early.

The permanent specifications define the destination.

The failing test defines the immediate destination.

The production change should be only large enough to reach it.
