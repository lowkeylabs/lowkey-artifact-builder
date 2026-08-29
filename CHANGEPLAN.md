# Change Plan

This document tracks the remaining incremental work required to bring
`lowkey-artifact-builder` into conformance with its permanent specifications
and to complete the initial integration between the Shape and Artwork models.

## Status

```text
Phase 1 — Completed
Phase 2 — Started
Phase 3 — Not started
```

## Key Documents

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
> subsequently fitted, composed, dimensionalized, and manufactured by a
> downstream Shape without repeating upstream interpretation merely because
> the physical Shape changes.

The current repository already contains partial groundwork for this phase:

- Artwork vectorization produces a persistent registered vector manifest.
- The Artwork vector manifest records the common `registered_extent`.
- The manifest identifies each vector component by relative path, semantic
  color name, RGB representation, and stable component index.
- Shape composition contains registered-Artwork value types and initial
  common-transform fitting logic.
- The build engine supports declarative product dependencies, concrete
  artifact/realization bindings, cross-model dependencies, and cross-artifact
  dependencies.

These existing capabilities are implementation groundwork, not evidence that
Shape currently consumes Artwork.

Shape's compose stage currently declares no Artwork product dependency and does
not yet incorporate a bound Artwork product into its persistent composition.

Phase 2 completes that integration without:

- introducing generated filesystem paths into configuration;
- requiring standalone Artwork extrusion or packaging;
- moving Shape-specific policy into the generic build engine;
- coupling Shape to Artwork stage implementations;
- or weakening the independence of registered geometry from physical
  manufacturing dimensions.


## 2.1 Validate the Registered Artwork Consumer Contract

Before declaring Shape's dependency, verify that the current Artwork vector
product satisfies the permanent registered-Artwork contract.

Tests should establish that the declared Artwork vector manifest provides:

- one common `registered_extent`;
- stable component membership;
- one vector payload path for each component;
- component paths relative to the manifest product location;
- semantic color identity for every component;
- RGB representation for every component;
- sufficient information to load all components without directory scanning;
- no physical manufacturing size;
- no physical Z semantics.

Verify that all component payloads participate in the common coordinate system
represented by `registered_extent`.

The consumer contract belongs to registered Artwork rather than to Shape.
Shape should consume the published registered representation rather than infer
Artwork structure from implementation details.

If the current Artwork implementation satisfies this contract, do not change
the producer merely to support Shape.

If a discrepancy exists between the current vector product and
`artwork/DEFINITION.md`, repair the producer contract before introducing
Shape-specific assumptions.

Completion of this slice establishes the tested reusable product contract that
Shape will consume.


## 2.2 Declare and Bind the Optional Artwork Dependency

Declare Shape composition's optional dependency on:

    artwork / vector / manifest

using the existing declarative product-dependency mechanism.

The declarative dependency identifies the producer model, stage, and product.
Artifact and realization identity are supplied by normal artifact dependency
binding.

Tests must demonstrate that:

- Shape remains valid and buildable without an Artwork binding;
- a Shape may bind registered Artwork from the same artifact;
- a Shape may bind registered Artwork from another artifact;
- configuration contains logical dependency identity rather than generated
  product paths;
- `StageContext` supplies the resolved Artwork vector manifest to Shape;
- requesting Shape computes the required upstream Artwork dependency closure;
- Artwork `prepare`, `raster`, and `vector` execute when required;
- Artwork `extrude` and `package` are not prerequisites merely because Shape
  consumes registered Artwork;
- a current registered Artwork vector product is reused rather than rebuilt
  unnecessarily.

Optionality is part of the contract. Adding registered Artwork support must not
turn Artwork into a mandatory prerequisite for every Shape.

Do not add Shape-specific dependency behavior to the generic build engine.


## 2.3 Define the Shape Interior Region

Define the registered region available for incorporated Artwork.

The interior region is the portion of Shape available after structural
boundaries such as the outer ridge have been accounted for.

Tests should establish the interior region for:

- a Shape without an outer ridge;
- a Shape with an integrated outer ridge;
- a Shape with a separate outer ridge;
- supported Shape geometries.

The interior-region contract must distinguish:

- the complete registered Shape boundary;
- structural ridge boundaries;
- the region available for incorporated Artwork.

The interior region remains registered geometry.

It must not introduce Artwork physical size or Z semantics.

Physical Shape parameters may influence registered structural boundaries where
the Shape definition explicitly requires conversion into registered space, but
the result of this slice remains a registered composition boundary rather than
a manufactured object.

Completion of this slice gives Artwork placement a defined target region rather
than requiring it to infer available Shape geometry.


## 2.4 Fit Registered Artwork Into Shape

Validate and complete the existing registered-Artwork fitting groundwork.

Registered Artwork must be fitted using the common `registered_extent` from the
Artwork vector manifest.

One common transform must be applied to every Artwork component.

Tests should demonstrate that:

- fitting is uniform;
- aspect ratio is preserved;
- all Artwork components receive the same transform;
- component registration is preserved;
- the transformed registered extent fits entirely within the Shape interior
  region;
- Artwork is centered within the available region unless later Shape
  configuration explicitly defines another placement policy;
- fitting does not inspect individual component bounds to independently size
  or center components;
- fitting introduces no physical Z dimension.

Existing registered-Artwork value objects and fitting operations should be
tested against the permanent model definitions before new abstractions are
introduced.

If the existing groundwork satisfies the required contract, retain it and
integrate it rather than replacing it.


## 2.5 Produce Persistent Registered Composition

Make Shape composition consume the bound Artwork vector manifest when Artwork
is configured.

The compose stage must produce a persistent registered composition sufficient
for downstream dimensionalization without rediscovering component structure.

The persistent composition must retain:

- Shape structural geometry;
- Shape structural partition identity;
- incorporated Artwork component membership;
- Artwork semantic color identity;
- Artwork component registration;
- the common transformation applied to incorporated Artwork;
- enough information for downstream stages to locate every dynamic component
  without scanning stage directories.

Determine whether the current single `composition.svg` product remains a
sufficient persistent contract once dynamic Artwork components participate.

If multiple or variable registered components must survive composition, use a
declared manifest or equivalent persistent product contract rather than
encoding dynamic-product discovery in filesystem conventions.

Tests should demonstrate that:

- Shape without Artwork continues to produce valid registered composition;
- Shape with Artwork preserves the structural Shape boundary;
- every incorporated Artwork component survives composition;
- semantic color identity survives composition;
- all incorporated Artwork components remain registered after transformation;
- downstream consumers need not inspect the Artwork producer's stage
  directory;
- downstream consumers need not scan the Shape compose directory.

Composition remains nonphysical.

This slice must not extrude geometry or assign physical Z dimensions.


## 2.6 Define Incorporated Artwork Physical Z Semantics

Before dimensionalizing incorporated Artwork, make its physical Z relationship
to Shape explicit in `shape/DEFINITION.md`.

Standalone Artwork extrusion semantics do not automatically define incorporated
Artwork semantics.

The Shape model owns the physical dimensionalization of Artwork it consumes.

The specification must define:

- where incorporated Artwork begins relative to the Shape base;
- the physical height of incorporated Artwork;
- whether Artwork is raised from, embedded in, or otherwise related to the
  structural top surface;
- the relationship between incorporated Artwork and integrated ridge geometry;
- the relationship between incorporated Artwork and separate ridge geometry;
- the behavior required when physical dimensions would create invalid or
  ambiguous geometry.

Do not infer these semantics accidentally from the current standalone Artwork
extrusion implementation.

Add specification-level tests where appropriate before implementing the
physical behavior.

Completion of this slice leaves no undefined physical Z policy for incorporated
Artwork.


## 2.7 Dimensionalize the Complete Shape Composition

Extend Shape extrusion so that it dimensionalizes the complete registered
composition.

Shape owns the physical transformation.

Tests should demonstrate that:

- registered Shape geometry maps consistently to `shape_size`;
- incorporated Artwork receives the same Shape-owned physical X/Y mapping
  implied by registered composition;
- Artwork components remain registered with one another;
- Artwork placement within Shape is preserved;
- Shape base geometry retains its existing physical semantics;
- integrated ridge geometry retains its existing physical semantics;
- separate ridge geometry retains its existing physical semantics;
- incorporated Artwork receives the physical Z semantics defined in 2.6;
- Artwork semantic colors survive dimensionalization;
- structural Shape semantic colors survive dimensionalization;
- physical component membership follows model semantics rather than color
  values;
- changing semantic colors does not alter geometry.

This slice must also resolve demonstrated model-to-model implementation
coupling in physical rendering.

Shape currently obtains a reusable rendering mechanic from an Artwork stage
implementation. That violates the architectural boundary that models compose
shared operations rather than invoke or depend on another model's stage
implementation.

Where Artwork and Shape demonstrably require the same model-independent
rendering or dimensionalization mechanic:

- extract the common mechanic into an appropriate reusable operation or format
  capability;
- have each model stage compose that operation independently;
- keep model-specific policy in the model stage;
- do not create a generic operation merely because two pieces of code happen
  to look similar.

Completion of this slice leaves no Shape dependency on an Artwork stage
implementation.


## 2.8 Package Shape With Incorporated Artwork

Extend Shape packaging to include all physical components produced by complete
Shape dimensionalization.

Packaging must consume the upstream physical-component contract rather than
reconstructing model policy.

Tests should demonstrate final `artifact.3mf` behavior for:

- Shape base components;
- integrated ridge components when physically present;
- separate ridge components when physically present;
- incorporated Artwork color components;
- shared semantic colors across multiple physical components;
- distinct semantic colors across physical components.

The final 3MF must preserve:

- semantic component role;
- semantic color identity;
- independently printable component identity where the model requires it;
- assembled physical registration.

Packaging must not:

- re-resolve Shape or Artwork color policy;
- rediscover dynamic components by scanning directories;
- assign physical printer heads;
- decide whether structural or Artwork components should exist.

Those decisions belong upstream.


## 2.9 Shape + Artwork Acceptance

Add end-to-end acceptance evidence for the complete reuse path:

    source PNG
        ↓
    Artwork prepare
        ↓
    Artwork raster
        ↓
    Artwork vector
        ↓
    Shape compose
        ↓
    Shape extrude
        ↓
    Shape package
        ↓
    artifact.3mf

Acceptance tests should demonstrate at minimum:

- a Shape consuming registered Artwork from a source PNG;
- Artwork interpretation stops at the reusable vector product for the
  dependency path;
- standalone Artwork extrusion is not required;
- standalone Artwork packaging is not required;
- the Shape determines the physical size of incorporated Artwork;
- the Shape determines the physical placement of incorporated Artwork;
- registered Artwork color components remain aligned;
- Artwork semantic colors survive into the final 3MF;
- Shape structural semantic colors survive into the final 3MF;
- structural and Artwork components coexist in one valid multicomponent 3MF;
- changing Shape physical size does not require repeating upstream Artwork
  interpretation when the registered Artwork product remains current;
- the final assembled geometry conforms to the Shape and Artwork model
  definitions.

Include at least one cross-artifact case in which a Shape consumes registered
Artwork produced by another configured artifact.

The acceptance path must use normal public configuration, planning, dependency
resolution, execution, and packaging boundaries rather than manually supplying
generated product paths.

Phase 2 is complete when a Shape can optionally consume reusable registered
Artwork through the normal product-dependency architecture, fit and compose it
in registered space, dimensionalize the resulting object according to Shape
semantics, and produce a valid multicomponent `artifact.3mf` without requiring
standalone Artwork extrusion or packaging.

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
