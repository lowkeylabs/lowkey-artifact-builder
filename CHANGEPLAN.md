# CHANGEPLAN — Artwork Hole Feature

Add an optional `Hole` Feature to the Artwork model.

The Hole is subtractive standalone physical geometry. It creates a circular
through-hole at a selected cardinal position of the standalone Artwork object.

The Feature is controlled by:

```text
artwork_hole_diameter
artwork_hole_position
artwork_hole_edge_distance
```

Participation is determined exclusively by:

```text
artwork_hole_diameter > 0
```

An effective diameter of zero disables the Feature.

The Hole has no semantic color and does not produce an independently printable
component.

The Hole exists only during standalone Artwork physical dimensionalization. It
is not part of registered Artwork.

The Hole cuts through all participating standalone physical geometry occupying
its X/Y region, including:

* Artwork color components;
* Base geometry; and
* Outer Ridge geometry.

The Hole center lies on one of the four cardinal axes through the standalone
Artwork center.

`artwork_hole_edge_distance` is the physical material distance, along the
selected cardinal axis, between the outer edge of the finished size-controlled
Artwork object and the nearest edge of the Hole.

The applicable outer boundary is:

* the dimensionalized Artwork envelope when no Outer Ridge participates; or
* the outer boundary of the Outer Ridge when the Outer Ridge participates.

A participating Hole must leave at least:

```text
0.4 mm
```

between the Hole edge and that outer boundary.

Development follows `prompts/TEST_DRIVEN_DEVELOPMENT.md`. Each slice should
establish RED for the intended behavior before its production implementation is
added.

---

# Phase 1 — Define the Permanent Hole Semantics

Update:

```text
src/lowkey_artifact_builder/model/models/artwork/DEFINITION.md
```

with an authoritative `Hole` Feature subsection.

Define the following semantics.

## Parameters

```text
artwork_hole_diameter
artwork_hole_position
artwork_hole_edge_distance
```

## Participation

```text
artwork_hole_diameter = 0
```

disables Hole participation.

```text
artwork_hole_diameter > 0
```

enables Hole participation.

Negative diameter is invalid.

## Position

`artwork_hole_position` accepts the same four cardinal positions and orientation
used by the Artwork Loop Feature:

```text
  0     top
 90     right
180     bottom
-90     left
```

The Hole center lies on the corresponding cardinal axis through the standalone
Artwork center.

## Geometry

The Hole is circular in X/Y.

Let:

```text
r_hole = artwork_hole_diameter / 2
d_edge = artwork_hole_edge_distance
```

For the selected cardinal position, determine the point at which the outward
cardinal ray intersects the outer boundary of the finished size-controlled
Artwork object.

The Hole center lies inward from that boundary by:

```text
r_hole + d_edge
```

along the selected cardinal axis.

Therefore the nearest Hole edge is exactly:

```text
artwork_hole_edge_distance
```

from the applicable outer boundary.

When no Outer Ridge participates, the applicable boundary is the dimensionalized
Artwork envelope.

When the Outer Ridge participates, the applicable boundary is the Outer Ridge's
outer boundary.

## Minimum Remaining Material

Whenever the Hole participates:

```text
artwork_hole_edge_distance >= 0.4 mm
```

must hold.

Values below `0.4 mm` are invalid for a participating Hole.

Hole-specific placement requirements do not apply when the Hole is disabled.

## Subtractive Semantics

The Hole is subtractive geometry rather than a printable component.

It removes material throughout the complete Z extent of every participating
standalone Artwork physical component intersecting the Hole's X/Y region.

This includes, where present:

```text
Artwork proper
Base
Outer Ridge
```

The resulting opening must therefore pass completely through the manufactured
standalone Artwork object.

The Hole does not have a semantic physical color.

## Registered Artwork

The Hole is not part of prepared, raster, or vector registered Artwork.

A consumer of registered Artwork does not receive Hole geometry and does not
require standalone Hole dimensionalization.

---

# Phase 2 — Configuration, Participation, Validation, and Planar Geometry

Add focused Artwork tests establishing the Hole's configuration and geometric
contract before implementing production behavior.

Prefer dedicated tests such as:

```text
tests/model/artwork/test_hole.py
tests/model/artwork/test_hole_geometry.py
```

rather than expanding unrelated Feature tests.

## 2.1 Configuration and Participation

Establish that:

* Hole parameters are ordinary Artwork parameters;
* ordinary Artwork disables Hole participation by default;
* an arbitrary Artwork Realization may configure Hole without requiring a
  specialized Variant;
* `artwork_hole_diameter = 0` is valid and disables Hole;
* negative `artwork_hole_diameter` is invalid;
* positive `artwork_hole_diameter` enables Hole participation;
* participating Hole configuration requires
  `artwork_hole_edge_distance >= 0.4`;
* `artwork_hole_edge_distance = 0.4` is valid;
* values below `0.4` are invalid for a participating Hole;
* disabled Hole configuration does not unnecessarily impose participating-Hole
  placement requirements;
* the four defined cardinal positions are accepted; and
* unsupported positions are rejected.

Do not assert the complete Artwork parameter or Feature inventory.

## 2.2 Planar Hole Geometry

Establish a small Artwork-owned geometry operation for Hole placement.

Tests should establish that:

* Hole radius is `artwork_hole_diameter / 2`;
* Hole geometry is circular;
* the Hole center lies on the selected cardinal axis;
* all four cardinal positions use the defined Artwork orientation;
* the nearest Hole edge is exactly `artwork_hole_edge_distance` inward from the
  applicable outer boundary;
* placement uses the actual dimensionalized Artwork coordinate system rather
  than assuming fixed coordinates;
* non-square Artwork envelopes retain correct cardinal placement;
* Hole geometry does not change the defined outer extent of the Artwork object;
  and
* Hole geometry remains entirely subtractive rather than becoming additional
  manufactured extent.

Keep this slice independent of STL generation where practical.

Run the focused Hole tests and observe RED for the missing Hole configuration,
validation, and geometry behavior.

Implement only the production behavior required to make this slice GREEN.

---

# Phase 3 — Integrate Hole With Artwork Dimensionalization

Extend standalone Artwork extrusion so that a participating Hole is subtracted
from the physical Artwork components.

Tests should establish that:

* Hole does not participate when `artwork_hole_diameter = 0`;
* a participating Hole cuts completely through Artwork color components at its
  X/Y location;
* Hole subtraction does not create a separately printable Hole component;
* no semantic color is assigned to Hole;
* unrelated Artwork geometry remains registered after subtraction;
* Hole participation does not change `artwork_size`;
* Hole participation does not alter registered Artwork products; and
* Hole configuration is relevant to standalone extrusion rather than prepare,
  raster, or vector processing.

Prefer testing the modeling/command boundary separately from external modeling
tool integration where practical.

---

# Phase 4 — Compose Hole With Base

Establish Hole interaction with the existing Base Feature.

When Base and Hole both participate, the same X/Y Hole must pass through the
Base as well as the Artwork proper.

Tests should establish that:

* Base participation does not change the Hole's X/Y center;
* the Hole passes completely through the Base;
* the Hole remains registered through Base and Artwork geometry;
* Base Z translation of the Artwork proper does not interrupt the through-hole;
* Hole does not acquire Base color or any other semantic color; and
* disabling Hole preserves ordinary Base behavior.

Do not duplicate unrelated Base semantics already protected by Base tests.

---

# Phase 5 — Compose Hole With Outer Ridge

Establish Hole interaction with the existing Outer Ridge Feature.

When Outer Ridge participates, Hole placement is measured from the Outer Ridge's
outer boundary rather than from the scaled Artwork-proper boundary.

Tests should establish that:

* the Hole center remains on the selected cardinal axis;
* `artwork_hole_edge_distance` is measured from the Outer Ridge outer boundary;
* the nearest Hole edge remains exactly the configured edge distance from that
  boundary;
* the minimum `0.4 mm` material requirement therefore applies between the Hole
  and the outer edge of the Outer Ridge;
* the Hole cuts through Outer Ridge material when its X/Y region intersects the
  ridge;
* the same Hole remains registered through any underlying Base and Artwork
  geometry;
* Hole participation does not change the Outer Ridge outer extent;
* Hole has no semantic color; and
* disabling Hole preserves ordinary Outer Ridge behavior.

Do not redefine Outer Ridge sizing semantics as part of this work.

---

# Phase 6 — Loop Interaction

Hole and Loop are independent optional Artwork Features.

Establish only the interaction behavior necessary to ensure that they compose
without accidental coupling.

Tests should establish that:

* Hole participation does not require Loop participation;
* Loop participation does not require Hole participation;
* `artwork_hole_position` is independent of `loop_position`;
* enabling Hole does not change Loop geometry;
* enabling Loop does not change the applicable size-controlled boundary used
  for Hole placement;
* Loop attachment geometry outside the size-controlled Artwork extent does not
  become the boundary from which `artwork_hole_edge_distance` is measured; and
* Hole does not participate in Loop color derivation or attachment-color
  selection.

Do not introduce shared Hole/Loop configuration merely because both use
cardinal-axis placement.

Reuse model-independent geometric mechanics only where the behavior is
genuinely mechanical and the resulting ownership remains clear.

---

# Phase 7 — Packaging and End-to-End Acceptance

Establish the complete standalone Artwork capability.

Add or extend an acceptance test demonstrating a meaningful Hole-enabled
standalone Artwork build.

The acceptance boundary should establish that:

* an Artwork Realization can enable Hole through ordinary parameters;
* the Artifact builds through standalone extrusion and packaging;
* the final `artifact.3mf` contains the expected printable physical components;
* the circular Hole passes through the manufactured object;
* the Hole does not appear as an independent printable/color component; and
* existing semantic printer-color identities of manufactured components remain
  preserved.

Where useful, exercise a composition containing:

```text
Artwork
Base
Outer Ridge
Hole
```

so one acceptance case demonstrates the important through-hole composition
without reproducing every focused Feature assertion.

Loop need not be included in the acceptance fixture unless doing so protects an
otherwise untested integration boundary.

---

# Phase 8 — Conformance and Cleanup

After the focused and acceptance behavior is GREEN:

1. run the complete non-slow test suite;
2. run formatting and lint checks;
3. run static type checking;
4. review changed existing tests against
   `prompts/TEST_DRIVEN_DEVELOPMENT.md`;
5. remove implementation duplication exposed by the completed Feature where
   doing so is local and behavior-preserving;
6. verify that generic engine code contains no Artwork-specific Hole semantics;
7. verify that Hole semantics remain owned by the Artwork model;
8. verify that registered Artwork remains unaffected by standalone Hole
   configuration; and
9. verify that unrelated Artwork Features and Variants did not acquire new
   accidental contracts.

Do not broaden this phase into unrelated repository cleanup.

---

# Completion Criteria

The Artwork Hole Feature is complete when:

* `DEFINITION.md` permanently defines Hole semantics;
* Hole participation is controlled by `artwork_hole_diameter > 0`;
* diameter zero disables Hole;
* Hole supports positions `0`, `90`, `180`, and `-90`;
* Hole is circular in X/Y;
* Hole center lies on the selected cardinal axis;
* Hole placement is measured inward from the finished size-controlled Artwork
  boundary;
* that boundary includes the Outer Ridge outer edge when Outer Ridge
  participates;
* the nearest Hole edge is exactly `artwork_hole_edge_distance` from that
  boundary;
* a participating Hole requires at least `0.4 mm` of material between its edge
  and the applicable outer boundary;
* Hole cuts through Artwork proper and any participating Base and Outer Ridge;
* Hole has no semantic color;
* Hole produces no independently printable component;
* Hole does not alter registered Artwork;
* Hole and Loop remain independent Features;
* standalone packaging preserves the resulting through-hole;
* focused tests protect the Feature semantics without freezing unrelated Artwork
  inventory or defaults; and
* the complete repository quality suite passes.

