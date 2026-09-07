# Change Plan

This change plan captures the remaining work required to align the repository
with `ARCHITECTURE.md` and the applicable Model `DEFINITION.md` files.

The permanent specifications are authoritative.

Implementation follows:

```text
prompts/TEST_DRIVEN_DEVELOPMENT.md
```

The Artifact / Variant / Realization configuration refactor is complete and is
intentionally omitted from this plan.

The current work extends the Artwork Model with two Model-owned optional
Features:

```text
Loop
Base
```

These Features are implemented independently before their composition is
tested.

The guiding architectural rules are:

* a Feature is an optional capability of a Model;
* intrinsic Model properties are not Features merely because parameters control
  their behavior;
* Feature participation is determined by effective Model parameter values;
* Model-specific Feature semantics remain owned by the Model;
* derived parameter values may depend on other resolved parameters or
  Model-owned derived information;
* a Feature need not participate in every representation produced by its Model;
* registered Artwork remains reusable and dimensionless;
* standalone Artwork Features do not become part of registered Artwork merely
  because another Model consumes that Artwork;
* arbitrary Realizations may configure Model Features directly without requiring
  specialized Variants; and
* generic configuration, planning, and execution infrastructure must not acquire
  Artwork-specific Feature semantics.

Do not introduce a separate generic Feature-selection mechanism.

---

# Phase 1 — Artwork Loop Feature

Implement the Artwork Loop Feature according to
`src/lowkey_artifact_builder/model/models/artwork/DEFINITION.md`.

Loop is implemented first because it establishes the Artwork-owned
attachment-color semantics subsequently reused by the Base Feature.

Implementation should proceed through focused TDD slices. Do not implement the
entire Feature before establishing its individual behavioral boundaries.

## 1.1 Loop Configuration and Participation

Expose the Artwork parameters required by the Loop Feature:

```text
loop_inner_diameter
loop_width
loop_position
loop_raise
loop_color
```

`loop_outer_diameter` is derived geometry and is not an independent
configuration parameter.

Tests should establish that:

* all Loop parameters are recognized Artwork parameters;
* `loop_inner_diameter = 0` disables Loop participation;
* negative `loop_inner_diameter` is invalid;
* values greater than zero but less than `0.5 mm` are invalid;
* a participating Loop requires positive `loop_width`;
* `loop_position` accepts only the positions defined by the Artwork Model;
* `loop_raise` may be explicitly configured;
* `loop_color` may be explicitly configured;
* explicit parameter values participate in ordinary Model / Variant /
  Realization resolution; and
* Loop configuration is available to an ordinary Artwork Realization without
  requiring a specialized Variant.

Parameter tests should protect configuration, resolution, participation, and
validation semantics rather than geometry implementation details.

Do not introduce a boolean such as:

```text
loop_enabled
```

Participation is determined by the effective value of
`loop_inner_diameter`.

## 1.2 Attachment-Color Selection

Implement the Artwork-owned attachment-color operation required by Loop.

Given a supported cardinal attachment position, Artwork determines the Artwork
color at the envelope attachment point.

If the exact boundary point is color-ambiguous, Artwork selects the nearest
occupied Artwork color immediately inward from the attachment point along the
same cardinal axis.

Tests should establish that:

* top attachment selects the expected Artwork color;
* right attachment selects the expected Artwork color;
* bottom attachment selects the expected Artwork color;
* left attachment selects the expected Artwork color;
* boundary ambiguity resolves to the nearest occupied Artwork color inward
  along the selected axis;
* the selected color preserves the corresponding physical semantic printer
  color identity; and
* selection is deterministic.

Test the semantic operation independently of Loop geometry where practical.

Attachment-color selection is Artwork-owned Model policy.

If existing geometry or color infrastructure provides suitable
Model-independent mechanics, reuse those mechanics. Do not move Artwork
attachment-color semantics into the generic engine.

## 1.3 Loop Geometry

Implement annular Loop geometry according to the Artwork definition.

For a participating Loop:

```text
r_inner = loop_inner_diameter / 2

r_outer = r_inner + loop_width

loop_outer_diameter =
    loop_inner_diameter + 2 * loop_width
```

Tests should establish that the Loop:

* is annular;
* has the configured inner diameter;
* has the configured radial width;
* therefore has the defined derived outer diameter;
* is centered on the cardinal axis selected by `loop_position`;
* uses the dimensionalized Artwork envelope to locate the attachment boundary;
* places the inward-facing point of its inner circle at the Artwork-envelope
  boundary along the selected cardinal axis;
* overlaps the Artwork inward by exactly `loop_width`; and
* remains registered with the dimensionalized Artwork.

Exercise all four supported positions sufficiently to establish the defined
rotational semantics without duplicating equivalent implementation tests.

## 1.4 Loop Physical Extent

Protect the distinction between Artwork size and total manufactured-object
extent.

Tests should establish that:

* `artwork_size` continues to control the maximum physical X/Y extent of the
  Artwork envelope itself;
* Loop geometry extends outside that size-controlled envelope;
* enabling Loop does not cause the Artwork proper to be rescaled smaller merely
  to keep the total object within `artwork_size`; and
* total standalone manufactured extent therefore increases when Loop extends
  beyond the Artwork envelope.

Do not redefine `artwork_size` as total packaged-object size.

## 1.5 Loop Raise

Implement Loop physical Z semantics.

Tests should establish that:

* explicit `loop_raise` determines Loop physical height;
* when `loop_raise` is not explicitly configured, its effective value derives
  from `artwork_raise`;
* changing `artwork_raise` changes the derived Loop raise when no explicit
  `loop_raise` exists;
* explicit `loop_raise` overrides the derived value; and
* without Base participation, Loop and Artwork proper begin at the same
  supporting Z plane.

The derivation rule belongs to Artwork Model semantics. Generic configuration
infrastructure may support derived values but must not contain knowledge of
`loop_raise` or `artwork_raise`.

## 1.6 Loop Color

Implement Loop color semantics.

Tests should establish that:

* explicit `loop_color` is authoritative;
* when `loop_color` is not explicitly configured, its effective value is
  derived using attachment-color selection at the effective `loop_position`;
* changing `loop_position` may therefore change the derived Loop color;
* an explicit `loop_color` overrides attachment-derived color; and
* the complete Loop uses the resolved semantic physical color identity.

Do not reduce the resolved semantic color to RGB merely for convenience if the
existing manufacturing pipeline preserves semantic color identity.

## 1.7 Loop Product Boundary

Integrate Loop with standalone Artwork dimensionalization and packaging.

Tests should establish that:

* disabled Loop configuration produces no Loop component;
* enabled Loop geometry participates in standalone Artwork extrusion;
* enabled Loop geometry participates in standalone Artwork packaging;
* the packaged Loop remains independently printable with its resolved semantic
  color identity;
* Loop geometry is not added to prepared Artwork;
* Loop geometry is not added to registered raster Artwork;
* Loop geometry is not added to registered vector Artwork;
* consuming registered Artwork does not require standalone Loop
  dimensionalization; and
* enabling Loop does not disturb dependency-driven reuse of registered Artwork.

Loop is a standalone physical Artwork Feature. It is not part of the reusable
registered Artwork representation.

## 1.8 Loop Acceptance

Add only the user-visible acceptance coverage necessary to prove the Feature
works through the ordinary Artifact / Variant / Realization architecture.

At minimum establish that:

* an ordinary Artwork Realization can enable Loop through parameter overrides;
* no specialized Variant is required;
* standalone Artwork builds successfully with Loop enabled;
* the resulting package contains the expected Loop component and semantic
  physical color identity; and
* ordinary Artwork with Loop disabled retains existing behavior.

Do not add `artwork.charm`, `artwork.ear_rings`, or another specialized Variant
merely to exercise Loop.

## 1.9 Loop Completion

The Loop Feature is complete when:

* its parameters and validation conform to the Artwork definition;
* participation is determined by `loop_inner_diameter`;
* attachment-color selection is implemented;
* geometry and cardinal placement conform to the definition;
* Artwork-size semantics remain unchanged;
* derived and explicit raise behavior conforms to the definition;
* derived and explicit color behavior conforms to the definition;
* Loop participates in standalone extrusion and packaging;
* registered Artwork remains free of Loop geometry;
* an arbitrary Artwork Realization may use Loop without a specialized Variant;
  and
* focused and broader regression suites pass.

Commit the completed Loop Feature before beginning Base.

---

# Phase 2 — Artwork Base Feature

Implement the Artwork Base Feature according to
`src/lowkey_artifact_builder/model/models/artwork/DEFINITION.md`.

Base is implemented after Loop so that it can reuse the already-established
Artwork attachment-color operation and resolved Loop color semantics.

Do not redesign Loop while implementing Base unless a demonstrated defect in
the permanent definitions requires a specification change first.

## 2.1 Base Configuration and Participation

Expose the Artwork parameters required by the Base Feature:

```text
artwork_base_raise
artwork_base_color
```

Tests should establish that:

* both Base parameters are recognized Artwork parameters;
* `artwork_base_raise = 0` disables Base participation;
* positive `artwork_base_raise` enables Base participation;
* negative `artwork_base_raise` is invalid;
* `artwork_base_color` may be explicitly configured;
* explicit parameter values participate in ordinary Model / Variant /
  Realization resolution; and
* Base configuration is available to an ordinary Artwork Realization without
  requiring a specialized Variant.

Do not introduce a boolean such as:

```text
artwork_base_enabled
```

Participation is determined by the effective value of
`artwork_base_raise`.

## 2.2 Base Geometry

Implement Base planar geometry according to the Artwork definition.

Tests should establish that a participating Base:

* conforms in X/Y to the dimensionalized Artwork envelope;
* uses the same dimensional transformation as the standalone Artwork envelope;
* does not independently fit or scale individual Artwork color layers;
* does not enlarge the size-controlled Artwork envelope;
* does not shrink the Artwork proper; and
* remains registered with the dimensionalized Artwork.

The Base is derived from the Artwork envelope, not from independent bounding
boxes of individual color layers.

## 2.3 Base Z Placement

Implement Base physical Z semantics.

When Base participates:

```text
Base:
    Z = 0 .. artwork_base_raise

Artwork proper:
    Z = artwork_base_raise
        ..
        artwork_base_raise + artwork_raise
```

When Base does not participate:

```text
Artwork proper:
    Z = 0 .. artwork_raise
```

Tests should establish that:

* Base begins at `Z = 0`;
* Base has physical height `artwork_base_raise`;
* Artwork proper rests on top of Base;
* every Artwork color component receives the same Z translation;
* Artwork color-layer registration is preserved;
* total physical raise becomes the Base raise plus Artwork raise when Base
  participates; and
* disabling Base restores ordinary standalone Artwork Z placement.

## 2.4 Base Color

Implement Base color semantics by reusing the Artwork-owned attachment-color
operation established for Loop.

Tests should establish that:

* explicit `artwork_base_color` is authoritative;
* when no explicit Base color exists and Loop participates, Base uses the
  resolved `loop_color`;
* this includes a `loop_color` that was explicitly configured;
* when Loop participates with a derived color, Base uses that resolved derived
  Loop color;
* when Loop does not participate, Base derives its color using the same
  attachment-color semantics as a hypothetical Loop at:

```text
loop_position = 0
```

* Base color derivation is deterministic; and
* the complete Base uses the resolved semantic physical color identity.

Do not duplicate the attachment-color algorithm inside Base.

Base consumes the Artwork-owned semantic operation established in Phase 1.

## 2.5 Base Product Boundary

Integrate Base with standalone Artwork dimensionalization and packaging.

Tests should establish that:

* disabled Base configuration produces no Base component;
* enabled Base geometry participates in standalone Artwork extrusion;
* enabled Base geometry participates in standalone Artwork packaging;
* the packaged Base remains independently printable with its resolved semantic
  color identity;
* Base geometry is not added to prepared Artwork;
* Base geometry is not added to registered raster Artwork;
* Base geometry is not added to registered vector Artwork;
* consuming registered Artwork does not require standalone Base
  dimensionalization; and
* enabling Base does not disturb dependency-driven reuse of registered Artwork.

When registered Artwork is consumed by Shape or another Model, the consuming
Model remains responsible for its own supporting physical geometry.

Do not make Shape disable or override the Artwork Base parameter merely because
Shape consumes registered Artwork. The Base is absent because standalone
Artwork Feature geometry does not belong to the registered representation.

## 2.6 Base Acceptance

Add only the user-visible acceptance coverage necessary to prove the Feature
works through the ordinary Artifact / Variant / Realization architecture.

At minimum establish that:

* an ordinary Artwork Realization can enable Base through parameter overrides;
* no specialized Variant is required;
* standalone Artwork builds successfully with Base enabled;
* Artwork proper is physically positioned above the Base;
* the resulting package contains the expected Base component and semantic
  physical color identity; and
* ordinary Artwork with Base disabled retains existing behavior.

Do not introduce a specialized Variant merely to exercise Base.

## 2.7 Base Completion

The Base Feature is complete when:

* its parameters and validation conform to the Artwork definition;
* participation is determined by `artwork_base_raise`;
* Base geometry conforms to the dimensionalized Artwork envelope;
* Base and Artwork Z placement conform to the definition;
* explicit and derived Base color behavior conforms to the definition;
* Base reuses the Artwork attachment-color semantics established for Loop;
* Base participates in standalone extrusion and packaging;
* registered Artwork remains free of Base geometry;
* an arbitrary Artwork Realization may use Base without a specialized Variant;
  and
* focused and broader regression suites pass.

Commit the completed Base Feature before beginning Feature-composition work.

---

# Phase 3 — Artwork Feature Composition and Integration

After Loop and Base are independently complete, protect their defined
composition.

This phase should contain only behavior that requires the Features to coexist.

Do not repeat tests already sufficient to establish individual Base or Loop
semantics.

## 3.1 Base and Loop Z Composition

Tests should establish that when both Features participate:

* Base begins at `Z = 0`;
* Artwork proper begins at `Z = artwork_base_raise`;
* Loop begins at the same supporting Z plane as the Artwork proper;
* Loop therefore rests on top of Base;
* Loop physical height remains the effective `loop_raise`;
* Artwork physical height remains `artwork_raise`; and
* differing `loop_raise` and `artwork_raise` values do not disturb the common
  supporting plane.

## 3.2 Base and Loop Color Composition

Tests should establish that when both Features participate:

* explicit `artwork_base_color` remains authoritative;
* otherwise Base uses the resolved `loop_color`;
* a derived Loop color therefore becomes the derived Base color;
* an explicitly configured Loop color therefore becomes the derived Base color;
* explicit Base color may differ from Loop color; and
* the independently printable Base and Loop components preserve their resolved
  semantic physical color identities.

## 3.3 Feature Independence

Tests should establish all four participation combinations:

```text
Base disabled    Loop disabled
Base enabled     Loop disabled
Base disabled    Loop enabled
Base enabled     Loop enabled
```

Each combination should produce only the physical components implied by its
effective Feature parameters.

In particular:

* Loop does not require Base;
* Base does not require Loop;
* enabling one Feature does not implicitly enable the other; and
* disabling one Feature does not prevent the other from participating.

Avoid testing every geometry detail again for every combination.

## 3.4 Registered Artwork Isolation

Protect the representation boundary with both Features enabled.

Tests should establish that:

* registered Artwork is identical in Feature participation semantics whether
  Base and Loop are enabled or disabled;
* neither Feature becomes part of registered vector Artwork;
* another Model may consume registered Artwork without realizing either
  standalone Feature;
* standalone Feature parameters do not introduce unnecessary producer stages
  into a dependency plan that requires only registered Artwork; and
* the consumer remains responsible for its own physical dimensionalization and
  supporting geometry.

This behavior should follow ordinary dependency-driven planning rather than
special-case suppression of Base or Loop.

## 3.5 End-to-End Feature Composition

Add a small acceptance test exercising standalone Artwork with both Features
enabled.

The test should establish the meaningful user-visible integration:

* ordinary Realization parameter overrides enable both Features;
* no specialized Variant is required;
* the build succeeds through the ordinary planning and execution path;
* the package contains Artwork, Base, and Loop physical components as required;
* Z relationships conform to the Artwork definition;
* semantic physical colors are preserved; and
* the final 3MF remains a valid independently printable multicomponent package.

Do not use acceptance tests to repeat low-level geometry assertions already
protected by focused Model tests.

---

# Phase 4 — Optional Reusable Variants

This phase is optional and should begin only if useful reusable Artwork
configurations are desired after the underlying Features are complete.

Possible examples include:

```text
artwork.charm
artwork.ear_rings
```

A new Variant is a reusable sparse configuration of already-supported Model
behavior.

A Variant must not introduce new Feature semantics.

Adding a Variant should ordinarily require only:

* Variant registration;
* a name and description as appropriate; and
* sparse parameter overrides.

Tests for a Variant should establish only:

* Variant registration and discovery;
* intended sparse parameter overrides;
* inheritance of unspecified Model parameter defaults;
* qualified Variant identity; and
* availability of the automatically derived default Realization through the
  generic Variant / Realization architecture.

Do not repeat Loop or Base geometry tests for a Variant.

Do not add one-off Realization registration or engine behavior for a Variant.

If a proposed Variant requires behavior not already supported by Artwork,
update the permanent Artwork `DEFINITION.md` and implement the required
Model-owned capability before defining the Variant.

Completion of this optional phase is not required for completion of the Base
and Loop Feature work.

---

# Test Curation

Tests encountered during this work should be curated according to
`prompts/TEST_DRIVEN_DEVELOPMENT.md`.

In particular:

* resolve semantic questions in the permanent Model definition before writing
  RED tests;
* write focused tests at the smallest boundary that owns the behavior;
* use Model tests for Artwork-specific Feature semantics;
* use generic engine tests only for genuinely Model-independent behavior;
* avoid tests that enumerate the complete Feature inventory of Artwork;
* avoid tests that require unrelated code to be updated merely because a new
  Feature exists;
* avoid duplicating geometry tests across Variants;
* preserve acceptance tests for meaningful user-visible integration; and
* remove or revise obsolete tests whose expectations contradict the permanent
  specifications.

A Feature test should protect the contract, not the incidental implementation.

---

# Completion Criteria

The required change plan is complete when:

1. Artwork Loop parameters are recognized, resolved, and validated according to
   the Artwork definition;

2. Loop participation is determined by the effective
   `loop_inner_diameter`;

3. Artwork attachment-color selection is implemented according to the Artwork
   definition;

4. Loop geometry, placement, overlap, extent, raise, and color conform to the
   Artwork definition;

5. Loop participates in standalone Artwork dimensionalization and packaging
   without becoming part of registered Artwork;

6. Artwork Base parameters are recognized, resolved, and validated according to
   the Artwork definition;

7. Base participation is determined by the effective
   `artwork_base_raise`;

8. Base geometry conforms to the dimensionalized Artwork envelope;

9. Base and Artwork Z placement conform to the Artwork definition;

10. explicit and derived Base color behavior conforms to the Artwork
    definition and reuses the Artwork attachment-color semantics;

11. Base participates in standalone Artwork dimensionalization and packaging
    without becoming part of registered Artwork;

12. Base and Loop compose according to their defined Z, color, and participation
    semantics;

13. all four Base / Loop participation combinations behave independently;

14. registered Artwork remains reusable, dimensionless, and free of standalone
    Artwork Feature geometry;

15. another Model may consume registered Artwork without requiring standalone
    Base or Loop realization;

16. arbitrary Artwork Realizations can configure Base and Loop directly through
    Model parameters without requiring specialized Variants;

17. derived parameter behavior remains Model-owned and does not introduce
    Artwork-specific semantics into generic configuration infrastructure;

18. generic planning and execution remain dependency-driven and do not contain
    Base- or Loop-specific behavior;

19. Product identity, Realization identity, Variant inheritance, and ordinary
    Artifact configuration behavior remain unchanged;

20. source-only/default Artwork behavior remains unchanged when Base and Loop
    are disabled;

21. focused and broader regression suites pass; and

22. no unnecessary large-scale redesign has been introduced.

Optional reusable Variants such as `artwork.charm` or `artwork.ear_rings` may
be added afterward as lightweight configurations of the completed Features.
They are not required to complete the underlying Feature implementation.

The guiding principle for this plan is:

> Models provide capabilities. Features are optional Model-owned capabilities.
> Variants provide reusable starting configurations. Realizations apply those
> configurations to Artifacts. Registered Artwork remains reusable and
> dimensionless, while standalone Artwork Features participate only at the
> physical representation boundaries defined by the Artwork Model.
