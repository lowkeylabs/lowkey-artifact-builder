# Coin Model Definition

The `coin` model constructs a two-sided physical object from two complete physical Shapes.

Each side of a Coin is a **Face**.

A Face is a complete physical Shape as established by Shape physical dimensionalization. It includes the Shape Base and every participating physical component and Feature produced by that Shape realization.

Coin does not reconstruct either Face from registered Shape geometry and does not reinterpret Shape Feature semantics. It consumes reusable physical Shape Products, establishes their relative orientation, preserves their component identity and logical color requirements, and packages the resulting two-sided object.

Conceptually:

```text
Shape Face A ──┐
               ├──> Coin ──> printable 3MF
Shape Face B ──┘
```

## Purpose

Coin provides a reusable manufacturing model for combining two independently realized physical Shapes back-to-back.

The two Faces may originate from:

- the same Shape Realization;
- different Shape Realizations of the same Artifact; or
- Shape Realizations belonging to different Artifacts.

Coin depends on Products by logical Product identity. It does not depend on generated filesystem paths.

## Faces

Every Coin has exactly two Faces:

```text
faceA
faceB
```

`faceA` and `faceB` are Coin-owned semantic roles. They identify how two source Shape Products participate in the Coin; they do not alter the logical identity of either source Product.

Each Face consumes the complete physical component collection established by Shape physical dimensionalization.

A Face retains:

- its source Shape's physical geometry;
- its physical component partition;
- participating Shape Features;
- incorporated Artwork;
- component semantic identity; and
- logical color requirements.

Coin must not require either source Shape to be packaged before it can participate as a Face.

## Physical Composition

Shape establishes `Z = 0` as the underside of a complete physical Shape.

Coin joins the two source Shape `Z = 0` planes to form the Face mating plane.

The two Faces occupy opposite sides of that mating plane, with each Face's visible Shape surface facing outward.

The two Shape Bases therefore form opposite physical halves of the Coin rather than overlapping volumes.

Coin does not introduce an independent structural Base between the Faces.

The physical Coin is the composition of the transformed physical component collections of Face A and Face B.

A whole-object transformation may subsequently reposition the composed Coin without changing the Face relationship.

## Face Orientation

Coin controls the relative orientation of Face A and Face B.

Orientation determines how the semantic top of Face B relates to the semantic top of Face A after the Faces are placed on opposite sides of the Coin.

Coin supports:

```text
aligned
inverted
```

With `aligned` orientation, the semantic tops of both Faces appear at the same physical end of the Coin when each Face is viewed directly from its outward side.

With `inverted` orientation, the semantic top of Face B appears at the opposite physical end from the semantic top of Face A when each Face is viewed directly from its outward side.

Orientation applies uniformly to every physical component belonging to a Face.

Particular reflection, rotation, translation, or mesh operations used to establish Face orientation are implementation details.

The default Coin orientation is `aligned`.

## Compatibility

Coin composes already-dimensionalized Shapes and does not repair incompatible Face geometry.

The transformed outer structural boundaries of the two Faces must coincide at the mating plane.

Compatibility is determined by physical geometry rather than by requiring identical source Variant names, Artifact identities, Realization names, or configuration histories.

Face-local surface geometry may differ. The Faces may independently differ in:

- raised or inlaid dimensionalization;
- Base thickness;
- incorporated Artwork;
- Artwork fill;
- Outer Ridge dimensionalization;
- Inner Ridge participation or dimensionalization;
- Border Labels;
- component colors; and
- other face-local geometry that does not prevent valid mating.

Features that cross or extend from the structural boundary require compatible mating geometry as defined by their Coin semantics.

An incompatible pair of Faces is invalid and must not produce a Coin manufacturing Product.

## Shape Features

Coin preserves physical Feature geometry established by each source Shape.

Coin does not independently regenerate Shape Outer Ridge, Inner Ridge, Border Label, Artwork, Artwork Fill, Loop, or Hole geometry.

### Outer Ridge and Inner Ridge

Outer Ridge and Inner Ridge remain Face-local physical components.

Each Face preserves the ridge geometry and dimensionalization established by its source Shape.

The Faces need not use identical ridge participation, width, raise, raise style, color, or other face-local ridge configuration unless a difference prevents valid mating.

### Border Labels, Artwork, and Artwork Fill

Border Labels, incorporated Artwork, and Artwork Fill remain Face-local physical components.

Coin preserves their geometry, dimensionalization, component identity, and logical color requirements as established by the source Shape.

No correspondence is required between the Face A and Face B surface-component collections.

### Loop

A participating Shape Loop extends from the Shape structural boundary and begins at the Shape `Z = 0` plane.

When Loop participates in a Coin, both Faces must provide compatible Loop geometry after Face orientation is applied.

The Face A and Face B Loop components remain distinct physical components. They meet at the mating plane and together form the complete two-sided Loop.

Coin does not remove either source Loop and does not generate a replacement Coin-specific Loop.

A Coin in which only one Face has a Loop, or in which the transformed Face Loops do not mate compatibly, is invalid.

### Hole

Hole is subtractive Shape geometry and is not an independent physical component.

When Hole participates in a Coin, both Faces must provide compatible Hole geometry after Face orientation is applied.

The source Shape holes meet at the mating plane and form one continuous opening through the complete Coin.

Coin does not perform a replacement Hole subtraction.

A Coin in which only one Face has a Hole, or in which the transformed Face holes do not align, is invalid.

## Component Identity

Coin preserves every source Shape physical component as an independently identifiable Coin component.

Components originating from Face A receive the semantic prefix:

```text
faceA-
```

Components originating from Face B receive the semantic prefix:

```text
faceB-
```

The remainder of the source component's semantic identity is preserved.

For example:

```text
base                  -> faceA-base
ridge                 -> faceA-ridge
loop                  -> faceA-loop
artwork-1             -> faceA-artwork-1

base                  -> faceB-base
ridge                 -> faceB-ridge
loop                  -> faceB-loop
artwork-1             -> faceB-artwork-1
```

Coin does not merge components merely because they touch, share a logical color, or form two halves of one apparent manufactured feature.

Face identity remains observable through physical composition and packaging.

## Color

Coin preserves the logical color requirements associated with every source Shape component.

Coin does not require source Shapes to have resolved physical printer assignments before composition.

Logical color identity must remain sufficient to preserve the intended color semantics of each Face even when the Faces originate from different Artifacts or Realizations.

Physical Coin composition does not assign physical printer colors.

Coin packaging resolves the complete Coin's logical color requirements against the Coin Realization's `printer_colors`.

Final printer-color assignment therefore considers both Faces as one manufactured object.

Components are not merged merely because they resolve to the same physical printing color.

Changing only Coin printer-color configuration does not change Coin physical geometry.

## Physical Transformation

Coin consumes physical Shape geometry after Shape has introduced physical X/Y and Z dimensions.

Coin does not repeat Shape registered composition, Artwork placement, Shape sizing, Feature participation, or Shape dimensionalization.

Coin changes only the placement and orientation necessary to compose the two source Shapes as opposite Faces of one object.

Every component belonging to one Face receives the same rigid Face transformation.

Coin must not independently transform individual Face components in a way that changes their registration with the other components of that Face.

Coin preserves the physical dimensions of each source component.

## Packaging

Packaging occurs after physical Coin composition.

Coin packaging consumes the complete Coin physical component collection.

Packaging:

- preserves `faceA-` and `faceB-` component identity;
- resolves logical color requirements against `printer_colors`;
- assigns physical printer colors;
- preserves independently printable component membership; and
- produces a printable Coin 3MF.

Packaging does not determine Face geometry, Face orientation, component participation, or Shape Feature geometry.

## Products and Dependencies

Coin consumes two complete physical Shape Products, one for each Face.

The dependency system must permit the two Face roles to refer independently to the same or different Shape Products.

The physical Coin component collection is itself a persistent Product and may be consumed independently of the packaged Coin.

Coin's packaged 3MF is a Product produced from that physical component collection.

Dependencies determine required execution. Consuming physical Shape Products for Coin must not require downstream Shape Products that Coin does not consume.

Coin Products may themselves be consumed by later Realizations, Models, Artifacts, or builds.

## Final Product

The ordinary packaged Coin Product is a printable multi-component 3MF containing the physical components of both Faces.

Its component names preserve Face role and source component semantic identity.

The packaged 3MF is one Product of the Coin model. It is not architecturally privileged over reusable upstream Coin Products.

## Model Invariants

1. A Coin consists of exactly two Faces, identified as `faceA` and `faceB`.
2. Each Face is a complete physical Shape produced after Shape physical dimensionalization.
3. A Face may originate from the same or a different Artifact or Realization as the other Face.
4. Coin consumes Shape Products by logical Product identity rather than generated filesystem path.
5. Coin does not require packaged source Shape Products.
6. Coin does not reconstruct Faces from registered Shape geometry.
7. Coin does not reinterpret Shape Feature participation or dimensionalization.
8. The source Shape `Z = 0` planes establish the Coin mating plane.
9. The two Faces occupy opposite sides of the mating plane with their visible surfaces facing outward.
10. Every physical component of a Face receives the same rigid Face transformation.
11. Coin transformation preserves source component dimensions and intra-Face registration.
12. The transformed outer structural boundaries of the two Faces coincide at the mating plane.
13. Compatible Faces need not originate from identical Variants, Realizations, Artifacts, or configuration histories.
14. Face-local geometry may differ when the difference does not prevent valid physical mating.
15. Outer Ridge and Inner Ridge remain Face-local components and are not regenerated by Coin.
16. Border Labels, Artwork, and Artwork Fill remain Face-local components and are not regenerated by Coin.
17. When Loop participates, both Faces provide compatible transformed Loop geometry.
18. Face A and Face B Loop components remain distinct and meet at the mating plane to form the complete Loop.
19. Coin does not generate a replacement Loop.
20. When Hole participates, both Faces provide compatible transformed Hole geometry.
21. Compatible source Shape holes form one continuous Coin Hole.
22. Coin does not perform a replacement Hole subtraction.
23. A one-sided or geometrically incompatible Loop or Hole makes the Face pair invalid.
24. Every source physical component remains independently identifiable after Coin composition.
25. Face A component identities are prefixed with `faceA-`.
26. Face B component identities are prefixed with `faceB-`.
27. Prefixing Face identity does not otherwise reinterpret the source component's semantic role.
28. Coin does not merge components merely because they touch or share a printing color.
29. Coin preserves the logical color requirements of source Shape components.
30. Physical Coin composition does not assign physical printer colors.
31. Coin packaging resolves physical printer colors for the complete two-Face object using the Coin Realization's `printer_colors`.
32. Physical printer-color assignment does not determine component participation or geometry.
33. Coin supports `aligned` and `inverted` Face orientation, with `aligned` as the default.
34. Face orientation changes only the relative physical orientation of the complete Faces.
35. Coin has no independent structural Base between its Faces.
36. Coin does not repeat registered Shape composition or Shape physical dimensionalization.
37. Physical Coin composition precedes packaging.
38. An incompatible Face pair must not produce a Coin manufacturing Product.
39. The physical Coin component collection remains a reusable Product independently of the packaged Coin.
40. Coin remains dependency-driven and realizes only Products required by the requested dependency closure.

## Scope

The Coin model defines two-sided manufactured objects composed from exactly two complete physical Shape Products.

Coin owns:

- the semantic roles Face A and Face B;
- compatibility requirements between the two Faces;
- relative Face orientation;
- physical composition of the Faces around their common mating plane;
- preservation and namespacing of Face component identity;
- preservation of logical color requirements; and
- packaging of the composed physical components into a printable artifact.

Shape continues to own the geometry, dimensionalization, Feature semantics, and component partition of each source Face.

Coin does not provide arbitrary multi-object assembly, free-form placement, source Shape modification, Feature reconstruction, or general-purpose mesh editing.

Capabilities outside the two-Face physical-composition and packaging contract defined by this document require an explicit extension of the Coin model or a different Model.

New Coin capabilities must be introduced deliberately through the appropriate Model or Feature contract rather than inferred from implementation behavior.
