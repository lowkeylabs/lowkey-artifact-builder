# Change Plan

This document tracks the remaining incremental work required to bring
`lowkey-artifact-builder` into conformance with its permanent specifications.

The previous change plan established the current Artwork and Shape integration,
including semantic structural colors, reusable registered Artwork, cross-model
and cross-artifact dependencies, Shape-owned physical dimensionalization, and
multicomponent 3MF packaging.

A fresh comparison of repository HEAD against the permanent specifications
identified one remaining substantive implementation gap in the initial Shape
model: optional Shape-owned Artwork fill geometry is specified and configurable
but is not yet physically produced.

This plan contains only the work remaining after that comparison.

## Status

```text
Phase 1 — Completed
Phase 2 — Started
```

## Permanent Specifications

The permanent normative specifications are:

```text
ARCHITECTURE.md

src/lowkey_artifact_builder/model/models/artwork/DEFINITION.md

src/lowkey_artifact_builder/model/models/shape/DEFINITION.md
```

`CHANGEPLAN.md` is not a normative specification.

It records only the temporary implementation path from repository HEAD toward
the permanent specifications.

Before selecting each implementation slice, compare repository HEAD against the
permanent specifications rather than assuming this plan remains complete.

When repository HEAD conforms to the permanent specifications, this file should
be deleted rather than retained as historical documentation.

# Development Method

Development is test-driven and incremental.

For each slice:

1. Identify one unmet architectural or model invariant.
2. Determine the observable behavior that demonstrates the invariant.
3. Write or revise the smallest useful test that expresses that behavior.
4. Confirm that the new test fails for the intended reason.
5. Make the smallest production-code change necessary to satisfy the test.
6. Refactor only after the required behavior is green.
7. Run the affected tests.
8. Run the complete test, lint, formatting, and type-check suite.
9. Commit the independently working slice.
10. Reevaluate repository HEAD before selecting the next slice.

Tests should preferentially express semantic contracts and invariants rather
than incidental implementation details.

Do not introduce abstractions merely because two implementations contain
similar code.

Extract shared operations only when multiple model implementations demonstrate
the same model-independent contract.

# Phase 1 — Complete Shape Artwork Fill Semantics

Implement the optional Shape-owned Artwork fill behavior already defined by:

```text
src/lowkey_artifact_builder/model/models/shape/DEFINITION.md
```

The current repository already defines and resolves:

```text
shape_artwork_fill_color
```

with a default of:

```text
none
```

but Shape extrusion does not currently use that parameter to produce physical
fill geometry.

The permanent Shape definition requires fill geometry, when enabled, to occupy:

```text
registered Shape interior region
    minus
transformed registered Artwork envelope
```

and to receive the same Shape-owned physical Z interval as incorporated
Artwork:

```text
Z = shape_base_raise
through
Z = shape_base_raise + shape_artwork_raise
```

Artwork fill is a semantic component distinct from both:

```text
Shape structural base
```

and:

```text
incorporated Artwork color components
```

even when two of those components happen to use the same semantic color.

## 1.1 Establish Artwork Fill Registered Geometry

Add executable evidence for the registered-space geometry required by the
Shape definition before introducing physical extrusion.

Tests should establish that when:

```text
shape_artwork_fill_color = none
```

no Artwork fill component is required.

When a fill color is configured, the registered fill region is:

```text
Shape interior
    minus
transformed Artwork envelope
```

Tests should demonstrate that:

* the Shape interior region remains the boundary controlling Artwork placement;
* the transformed Artwork envelope is subtracted from that interior;
* the fill does not cover the transformed Artwork envelope;
* the fill does not extend into the structural outer-ridge region;
* fill geometry remains registered geometry until Shape extrusion;
* fill geometry introduces no physical X/Y size;
* fill geometry introduces no physical Z dimension;
* changing the fill color does not change registered geometry;
* ridge style does not change the semantic definition of the fill region.

Use the transformed common Artwork envelope rather than independently deriving
fill boundaries from individual Artwork color components.

Do not rediscover Artwork structure by scanning producer or compose-stage
directories.

The persistent Shape composition already contains the information required by
downstream dimensionalization. Extend that contract only if the current
persistent representation cannot express the required fill geometry without
rediscovery.

## 1.2 Dimensionalize Artwork Fill

Extend Shape extrusion to produce the physical Artwork fill component when
fill is enabled.

Shape owns the physical dimensionalization.

Tests should establish that:

* no physical fill component is produced when
  `shape_artwork_fill_color = none`;

* a configured fill color causes a physical fill component to be produced when
  incorporated Artwork is present;

* the fill receives the same Shape-owned physical X/Y mapping as the registered
  Shape composition;

* the fill begins at:

  ```text
  Z = shape_base_raise
  ```

* the fill ends at:

  ```text
  Z = shape_base_raise + shape_artwork_raise
  ```

* incorporated Artwork and Artwork fill therefore share the same physical
  Z interval;

* the fill does not replace or alter the structural Shape base;

* the fill does not overlap incorporated Artwork geometry in X/Y;

* the fill does not manufacture ridge geometry;

* integrated and separate ridge styles do not change the fill's physical
  Z origin or raise;

* changing the fill color does not alter physical geometry.

Invalid physical configurations should fail through normal Shape validation
rather than silently producing ambiguous geometry.

## 1.3 Preserve Artwork Fill Semantic Identity

Associate the physical fill component with its configured semantic color.

Use the shared color infrastructure already used by Artwork and Shape:

```text
PaletteColor
resolve_palette_color()
```

Tests should establish that:

* `shape_artwork_fill_color` resolves through the shared color catalog;
* invalid semantic color names fail through the normal shared color-resolution
  mechanism;
* the physical-component manifest identifies the fill by semantic role;
* the manifest preserves its semantic color name;
* the manifest preserves the corresponding RGB representation;
* the fill remains semantically distinct from the structural base even when
  both use the same color;
* the fill remains semantically distinct from incorporated Artwork components
  that happen to use the same color;
* semantic color identity does not determine component existence except for the
  explicit `none` enable/disable policy already defined by the Shape model;
* Shape does not assign the fill to a physical printer head.

Do not move Shape fill-selection policy into the shared color subsystem.

## 1.4 Package Artwork Fill

Extend the existing Shape physical-component and packaging path so the fill
survives into:

```text
artifact.3mf
```

Packaging should continue to consume the physical-component manifest rather
than reconstructing Shape policy.

Tests should establish that:

* enabled fill appears as an independently identifiable packaged component;
* disabled fill does not cause a packaged fill object to be invented;
* the packaged fill preserves its semantic role;
* the packaged fill preserves its semantic color identity;
* the structural base remains independently identifiable;
* incorporated Artwork color components remain independently identifiable;
* ridge components remain governed by existing ridge semantics;
* multiple physical components may legitimately share the same semantic color;
* shared semantic colors do not cause semantically distinct components to be
  merged;
* assembled physical registration is preserved;
* packaging does not re-resolve fill policy;
* packaging does not assign printer heads.

Use the existing shared 3MF component and packaging capability.

Do not introduce a second Shape-specific 3MF mechanism.

## 1.5 Shape Artwork Fill Acceptance

Add end-to-end evidence through normal public configuration, planning,
dependency resolution, execution, and packaging.

At minimum demonstrate:

### Fill disabled

A Shape incorporating registered Artwork with:

```text
shape_artwork_fill_color = none
```

produces the expected structural and Artwork components without an Artwork
fill component.

### Fill enabled

A Shape incorporating registered Artwork with an explicit fill color produces:

```text
structural Shape component(s)
+
Artwork fill
+
incorporated Artwork color components
```

in one valid multicomponent:

```text
artifact.3mf
```

### Shared semantic color

Demonstrate that the structural base and Artwork fill may use the same semantic
color while remaining distinct semantic and physical components.

### Ridge interaction

Demonstrate fill behavior with at least one physically present outer ridge and
verify that ridge style does not alter the fill's specified physical Z
semantics.

Acceptance evidence should verify that:

* Artwork interpretation still stops at reusable registered geometry for the
  Shape dependency path;
* standalone Artwork extrusion is not required;
* standalone Artwork packaging is not required;
* Shape owns fill physical dimensionalization;
* registered Artwork remains reusable;
* semantic colors survive into the final 3MF;
* no generated filesystem path is required in artifact configuration.

Completion of Phase 1 means every initial-scope Shape Artwork-fill invariant in
`shape/DEFINITION.md` has executable implementation evidence.

# Phase 2 — Final Permanent-Specification Conformance Audit

After Phase 1 is complete, perform a fresh comparison of repository HEAD
against:

```text
ARCHITECTURE.md

src/lowkey_artifact_builder/model/models/artwork/DEFINITION.md

src/lowkey_artifact_builder/model/models/shape/DEFINITION.md
```

Do not audit HEAD against this CHANGEPLAN alone.

The purpose of this phase is to determine whether any meaningful difference
remains between the permanent specifications and the implementation.

## 2.1 Audit ARCHITECTURE.md

Review every architectural invariant against repository HEAD.

Confirm in particular that the implementation still provides executable
evidence for:

* first-class persistent products;
* no engine-level privileged final product;
* one canonical materialized home per product;
* stage ownership of products;
* logical product references;
* centralized filesystem resolution;
* dependency-driven execution;
* validation of complete model definitions;
* minimal dependency realization;
* reuse of current products;
* cross-model reuse;
* cross-artifact reuse;
* dimension-independent reusable registered geometry;
* late physical dimensionalization;
* registration preservation;
* product-contract consumption rather than producer-stage coupling;
* recursive registered composition where currently implemented;
* model-scoped variants;
* separation of variants from realizations;
* manifest-defined variable collections;
* completion state independent of directory existence;
* absence of model-specific behavior in the generic engine;
* absence of global artifact-path construction in model stages;
* simple ordinary configuration;
* structured execution behavior independent of presentation policy.

Do not require future models such as ornament or keychain merely because they
appear as architecture reference scenarios.

The architecture must be capable of representing those scenarios without
requiring them all to be implemented by the current model set.

## 2.2 Audit Artwork DEFINITION.md

Review the complete Artwork definition against HEAD.

Confirm executable evidence for:

* source materialization;
* palette-based preparation;
* Artwork envelope production;
* raster component production;
* registered vector geometry;
* common registered extent;
* stable component membership;
* semantic color identity;
* RGB color representation;
* manifest-defined dynamic components;
* dimension independence before extrusion;
* common registration across Artwork components;
* standalone Artwork physical dimensionalization;
* standalone Artwork multicomponent 3MF packaging;
* preservation of semantic colors through packaging;
* reuse of registered Artwork without standalone extrusion or packaging.

As part of this audit, explicitly resolve whether Artwork's current requirement
that the configured palette contain:

```text
white
```

is part of the intended permanent Artwork contract.

If the implementation intentionally requires white as the envelope-fill color
during preparation, ensure that requirement is unambiguously represented by
the permanent Artwork definition.

If the permanent definition intentionally permits palettes without white,
identify the implementation discrepancy and create a new narrowly scoped
CHANGEPLAN rather than silently changing either side.

Do not change this behavior merely because the implementation and specification
use different wording. First determine whether a semantic discrepancy actually
exists.

## 2.3 Audit Shape DEFINITION.md

Review every initial-scope Shape invariant against HEAD.

Confirm executable evidence for:

* supported structural geometries;
* registered Shape normalization;
* Shape interior-region semantics;
* outer-ridge registered geometry;
* integrated ridge semantics;
* separate ridge semantics;
* equivalent assembled geometry where required;
* structural base color;
* independent ridge color;
* registered Artwork dependency;
* common Artwork transformation;
* preserved Artwork registration;
* centered uniform fitting;
* persistent registered composition;
* Shape-owned physical X/Y dimensionalization;
* Shape-owned Artwork raise;
* optional Shape-owned Artwork fill;
* Artwork fill geometry;
* Artwork fill semantic color;
* structural, fill, ridge, and Artwork component identity;
* final multicomponent 3MF packaging.

Distinguish initial-scope requirements from explicitly deferred future
capabilities.

## 2.4 Reevaluate Shared Operations

Perform one final review for demonstrated model-independent duplication.

In particular review:

```text
color resolution
registered geometry transformation
OpenSCAD rendering
component manifests
STL loading
3MF component representation
3MF packaging
```

Existing shared abstractions should be retained when they already express the
common contract.

Do not introduce a generic packaging framework, generic model pipeline, or
generic geometry framework merely to make implementations appear structurally
similar.

Model stages should retain policy for:

```text
what components exist
what those components mean
which semantic colors belong to them
how model-specific geometry is constructed
```

Shared infrastructure should remain responsible only for demonstrated
model-independent mechanics.

## 2.5 Full Repository Validation

After all permanent-specification comparisons are clean, run the complete
repository validation suite, including slow tests.

At minimum run the repository's normal equivalents of:

```text
pytest
ruff
format checks
pyright
```

using the standard project commands.

Do not declare conformance based only on the short test suite.

Any failure that reveals a permanent-specification discrepancy should result in
a new narrowly scoped implementation slice before proceeding.

## 2.6 Delete CHANGEPLAN.md

If the final audit finds no meaningful difference between repository HEAD and:

```text
ARCHITECTURE.md
artwork/DEFINITION.md
shape/DEFINITION.md
```

and the complete repository validation suite is green, delete:

```text
CHANGEPLAN.md
```

The repository should then be governed by:

```text
ARCHITECTURE.md
model/models/<model>/DEFINITION.md
tests
implementation
```

Do not preserve a completed CHANGEPLAN merely as historical documentation.

Version control already records that history.

If the final audit identifies another meaningful discrepancy, do not delete
CHANGEPLAN.md.

Instead:

1. remove completed work from this document;
2. replace it with only the newly discovered remaining work;
3. restart phase numbering from Phase 1;
4. continue until HEAD conforms to the permanent specifications.
