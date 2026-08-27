# Change Plan

This document tracks the remaining incremental work required to bring
`lowkey-artifact-builder` into conformance with its permanent specifications
and to implement the next production model.

The permanent normative specifications are:

```text
ARCHITECTURE.md
src/lowkey_artifact_builder/model/models/artwork/DEFINITION.md
src/lowkey_artifact_builder/model/models/shape/DEFINITION.md
```

`CHANGEPLAN.md` is not a normative specification. It records the current
implementation path from repository HEAD toward those specifications.

Completed historical migration phases have been removed from this document.
The current repository already contains the graph, resolver, product-state,
resumability, execution-event, independent-stage-execution, and cross-artifact
dependency foundations established by those earlier phases.

Before selecting each implementation slice, compare the current repository
against the permanent specifications rather than assuming this plan remains
complete.

## Status

```text
Phase 11 — Started
Phase 12 — Not started
Phase 13 — Not started
Phase 14 — Not started
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
implement an entire model, stage sequence, or architectural subsystem.

Tests should preferentially express semantic contracts and invariants rather
than incidental implementation details.

The existing Artwork model remains the primary regression baseline.

# Phase 11 — Registered Geometry and Architectural Alignment

Phase 11 establishes the remaining contracts needed before substantial Shape
implementation and begins exercising registered geometry through the Shape
model.

The objective is not to redesign working engine infrastructure. It is to close
specific gaps between repository HEAD and the permanent specifications and
then introduce Shape in independently testable slices.

## 11.1 Specification and Implementation Alignment

Reconcile known differences between current implementation terminology and the
permanent specifications.

In particular:

- Align `StageSpec` documentation and tests with the architectural meaning of
  numeric stage IDs:
  - stage name is semantic identity;
  - numeric stage ID is a presentation ordinal;
  - stage IDs do not determine dependencies or execution order;
  - stage IDs may change when deterministic model ordering changes.
- Remove documentation or implementation assumptions that treat a model as
  being defined by a distinguished final 3MF.
- Review model and engine terminology for other remnants of superseded
  architecture.
- Resolve `artwork_overlap`:
  - determine whether it remains part of Artwork semantics;
  - if it is obsolete, remove it from configuration and affected code/tests;
  - if it is required, define its semantics in `artwork/DEFINITION.md` before
    relying upon it.
- Keep the Artwork implementation conformant with `artwork/DEFINITION.md`.

Do not perform broad cleanup merely because older terminology exists. Change
code or documentation when it conflicts with a current architectural or model
contract.

## 11.2 Artwork Conformance Evidence

Strengthen executable evidence for the important reusable-geometry invariants
already specified by the Artwork model.

Tests should demonstrate, where not already adequately covered, that:

- raster processing is independent of physical `artwork_size`;
- vector processing is independent of physical `artwork_size` and
  `artwork_raise`;
- vector products share one registered coordinate system;
- the vector manifest records `registered_extent`;
- semantic color identity survives raster and vector processing;
- all registered layers retain their registration;
- standalone extrusion applies one common physical X/Y transformation;
- standalone extrusion introduces physical Z through `artwork_raise`;
- registered vector Artwork can be requested without realizing Artwork
  extrusion or packaging.

Prefer tests of existing observable behavior over implementation rewrites.

## 11.3 Registered Geometry Consumer Contract

Use the first Shape dependencies to exercise the architectural contract for
registered geometry.

Establish tests demonstrating that a consumer can:

- depend logically on registered vector Artwork;
- receive the Artwork vector manifest through normal dependency resolution;
- discover component membership through the manifest rather than directory
  scanning;
- obtain the common registered coordinate extent;
- treat the component payload as opaque;
- preserve registration by applying one common transformation to every
  component.

Do not introduce generated filesystem paths into Shape configuration or Shape
implementation.

## 11.4 Shape Model Declaration

Expand the currently skeletal Shape model only far enough to represent the
next behavior being implemented.

The eventual Shape model must support the semantics defined by
`shape/DEFINITION.md`, including:

- circle geometry;
- square geometry;
- octagon geometry;
- physical `shape_size`;
- physical `shape_base_raise`;
- optional outer ridge;
- optional registered Artwork;
- final multicomponent 3MF packaging.

Do not declare speculative stages merely to make the model look complete.
Introduce stages, parameters, dependencies, and products as the corresponding
behavior becomes testable.

Stage numeric IDs should follow deterministic presentation order rather than
being treated as permanent semantic identifiers.

## 11.5 First Shape Production Slice

The first production capability should be the smallest complete Shape
invariant:

> A Shape can produce structural geometry without Artwork.

Begin with one geometry, preferably the circle, before implementing all three
geometry types.

A suitable incremental sequence is:

1. Declare the minimum Shape stage/product contract.
2. Test circle size semantics.
3. Implement circle 2D geometry.
4. Test physical base thickness.
5. Dimensionalize/extrude the circle into a structural base.
6. Package the resulting component into a valid 3MF.
7. Add an acceptance test proving a Shape without Artwork is a complete valid
   artifact.

Do not introduce Artwork composition into this first production slice.

# Phase 12 — Shape Structural Geometry

Complete the structural portion of the initial Shape model defined by
`shape/DEFINITION.md`.

## 12.1 Common Shape Geometry Semantics

Extend the tested Shape geometry contract from circle to:

- circle;
- square;
- octagon.

For every geometry, verify that `shape_size` means the overall X/Y envelope:

```text
circle   -> diameter
square   -> side length
octagon  -> bounding-box width and height
```

A Shape with:

```text
shape_size = 100
```

must fit within a 100 mm × 100 mm envelope regardless of geometry.

Keep geometry policy in the Shape model and reusable mechanical transformations
outside model-specific code where practical.

## 12.2 Base Geometry

Verify for every supported Shape geometry that:

- a base always exists;
- the base follows the selected Shape boundary;
- its X/Y extent is controlled by `shape_size`;
- it extends from `Z = 0` through `Z = shape_base_raise`.

Add geometry-level tests before adding additional decoration.

## 12.3 Outer Ridge

Implement the optional outer ridge incrementally.

Tests should establish:

- ridge geometry follows the selected Shape boundary;
- ridge width is measured inward;
- the ridge never increases `shape_size`;
- the ridge begins at the top of the base;
- ridge height is `shape_outer_ridge_raise`;
- zero ridge width disables the ridge;
- zero ridge raise disables the ridge;
- the ridge's inner boundary determines the remaining interior region.

Test one geometry first, then generalize the behavior to the other supported
geometries.

## 12.4 Reusable Operations

As Shape implementation begins sharing mechanical transformations with
Artwork or repeating transformations across Shape geometries, extract
model-independent operations where the duplication demonstrates a real common
contract.

Likely reusable operations include:

- scale;
- translate;
- fit;
- inset/offset;
- extrusion;
- packaging or component assembly where genuinely model-independent.

The architectural separation is:

```text
model stage
    -> owns model policy and semantics

reusable operation
    -> owns model-independent transformation mechanics
```

Do not introduce an operation framework merely to rename existing functions.
Extract reusable operations when at least two model contexts establish the
common behavior.

A reusable operation must not depend on model-specific configuration
namespaces or global artifact filesystem layout.

# Phase 13 — Shape and Registered Artwork Composition

Add optional Artwork consumption to Shape.

This phase exercises the central Phase 11 architecture: reusable registered
geometry is interpreted once and dimensionalized by the downstream consumer.

## 13.1 Artwork Dependency Binding

Declare Shape's dependency on the registered vector Artwork product.

Tests must demonstrate that:

- Shape may bind to Artwork belonging to another artifact;
- the dependency is represented by logical product identity;
- dependency resolution supplies the vector manifest to Shape;
- requesting Shape realizes only the required Artwork dependency closure;
- Artwork `prepare`, `raster`, and `vector` execute when necessary;
- Artwork `extrude` and `package` are not required;
- current upstream vector Artwork is reused without unnecessary execution.

This should use the existing cross-model and cross-artifact dependency
mechanisms rather than adding Shape-specific engine behavior.

## 13.2 Interior Region

Make Shape expose or calculate the region available for Artwork.

Tests should establish:

- without a ridge, the interior region is bounded by the Shape boundary;
- with a ridge, the interior region is bounded by the ridge's inner boundary;
- changing ridge width changes available Artwork space without changing
  `shape_size`.

## 13.3 Registered Artwork Fitting

Implement contain-style fitting of registered Artwork into the Shape interior.

Tests must demonstrate that incorporated Artwork is:

- centered;
- uniformly scaled;
- aspect-ratio preserving;
- completely contained within the available interior region;
- transformed using one common transformation for every registered component.

The consumer must use the registered geometry contract rather than independently
calculating and fitting each color layer.

Changing Shape size or ridge dimensions must not require Artwork rasterization
or vectorization to be repeated unless those upstream products are otherwise
stale.

## 13.4 Artwork Z Semantics

Before implementing physical composition of Artwork with the Shape base, define
the Z semantics required by `shape/DEFINITION.md`.

Determine and document:

- where incorporated Artwork begins in Z;
- its extrusion height;
- its relationship to the base top;
- its relationship to the outer ridge;
- whether any overlap required for printable/manifold construction is a
  geometric operation or a model parameter;
- how independently printable color components remain physically associated
  with the structural Shape.

Update `shape/DEFINITION.md` before implementation if these decisions extend its
normative semantics.

Then implement the decisions test-first.

## 13.5 Shape Packaging

Package structural Shape geometry and optional Artwork components into the
declared Shape `artifact.3mf`.

Tests should verify:

- Shape without Artwork packages successfully;
- Shape with Artwork packages successfully;
- structural components are present;
- Artwork color components remain independently printable;
- semantic component/color identity survives composition and packaging;
- packaging does not require the standalone Artwork 3MF.

# Phase 14 — Composition Acceptance and Generalization

Use the completed Shape model to exercise the broader architectural scenarios
that motivated registered geometry and composition.

## 14.1 Same Artwork, Different Physical Shapes

Demonstrate that one registered Artwork product can feed Shapes with different:

- geometry;
- `shape_size`;
- base thickness;
- ridge dimensions.

The upstream registered vector Artwork must remain reusable and
dimension-independent.

## 14.2 Cross-Artifact Shape Composition

Build a Shape artifact that consumes registered Artwork belonging to another
artifact.

Verify end-to-end that:

- logical dependency identity crosses the artifact boundary;
- the resolver supplies the canonical upstream product;
- only required upstream stages are realized;
- current upstream products are reused;
- no generated filesystem path appears in artifact configuration.

## 14.3 Architecture Acceptance Scenarios

Use the relevant scenarios in `ARCHITECTURE.md` as acceptance criteria.

At minimum, preserve or establish executable evidence for:

- standalone Artwork;
- registered Artwork reused by another manufactured object;
- different physical sizes using the same registered Artwork;
- circular structural composition;
- optional structural ridge;
- cross-artifact reuse.

Do not force ornament, keychain, multiple-Artwork composition, arbitrary
placement, labels, or hangers into the initial Shape implementation merely to
complete every future architecture scenario.

Those should become subsequent model definitions or deliberate extensions once
the Shape foundation is stable.

## 14.4 Reevaluate Abstractions

After Shape and Artwork both use the new mechanics, reevaluate the codebase for
demonstrated common operations.

At that point:

- extract duplicated model-independent geometry mechanics;
- keep model policy in model stages;
- avoid inheritance between model pipelines;
- avoid one model invoking another model's stage implementation;
- retain `StageContext` as the independent stage execution boundary;
- keep the generic engine free of Shape- and Artwork-specific behavior.

Do not generalize ahead of demonstrated reuse.

# Continuous Activities

Throughout all phases:

- treat `ARCHITECTURE.md` and model `DEFINITION.md` files as normative;
- compare repository HEAD against those specifications before selecting each
  slice;
- keep `CHANGEPLAN.md` synchronized with discovered remaining work;
- preserve working Artwork behavior unless an intentional specification change
  requires otherwise;
- add tests before production implementation for each behavioral slice;
- prefer invariant and contract tests over implementation-specific tests;
- maintain unit tests for specifications and value objects;
- maintain integration tests for graph, resolver, dependency, and execution
  behavior;
- maintain end-to-end Artwork regression coverage;
- add end-to-end Shape coverage incrementally;
- keep products logically addressed and canonically resolved;
- keep registered geometry independent of manufacturing size until the
  responsible downstream operation introduces that size;
- preserve registration through common transformations;
- consume dynamic collections through manifests rather than filesystem scans;
- keep engine behavior model-independent;
- keep model implementations free of global filesystem policy;
- keep structured execution events semantic and presentation-independent;
- run the complete project quality suite after every completed slice;
- remove obsolete code and tests once replacement behavior is established;
- update a model `DEFINITION.md` before implementing a deliberate change to
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
