# Coin Model Definition

The `coin` model constructs a two-sided physical object from two complete physical Shapes.

Each side of a Coin is a **Face**.

A Face is a complete physical Shape as established by Shape physical dimensionalization. It includes the Shape Base and every participating physical component and Feature produced by that Shape realization.

Coin does not reconstruct either Face from registered Shape geometry and does not reinterpret Shape Feature semantics. It consumes packaged Shape Products containing complete physical geometry, component identity, resolved component colors, and the Shape-level metadata required for Face compatibility. Coin establishes the relative orientation of those Faces, preserves their component identity and resolved colors, and produces the resulting two-sided object.

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

faceA and faceB are Coin-owned semantic roles. They identify how two source Shape Products participate in the Coin; they do not alter the logical identity of either source Product.

Each Face consumes a complete packaged Shape Product.

A packaged Shape provides:
- the complete physical Shape geometry;
- the physical component partition;
- participating Shape Features;
- incorporated Artwork;
- component semantic identity;
- resolved component colors; and
- Shape-level physical metadata required for downstream compatibility.

The packaged 3MF is authoritative for component geometry, component identity,
resolved component colors, and persistent Shape-level compatibility metadata.

Coin does not reopen source Shape configuration or regenerate a different Shape realization on behalf of a Face.

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

Coin composes already-dimensionalized, packaged Shapes and does not repair or regenerate incompatible Face geometry.

Face B must use `inlaid` Shape dimensionalization. A packaged Shape used as Face B must therefore identify its Shape raise style as `inlaid`. A non-inlaid Face B is incompatible and must not produce a Coin manufacturing Product.

Coin validates this requirement from persistent Shape-level metadata rather than by reopening source Shape configuration or inferring dimensionalization from mesh geometry.

The transformed outer structural boundaries of the two Faces must coincide at the mating plane.

Compatibility is otherwise determined by physical geometry rather than by requiring identical source Variant names, Artifact identities, Realization names, or configuration histories.

Subject to the Face B inlaid requirement, Face-local surface geometry may differ. The Faces may independently differ in:

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

Coin preserves their geometry, dimensionalization, component identity, and resolved component colors as established by the packaged source Shape.


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

Coin does not merge components merely because they touch, share a resolved physical color, or form two halves of one apparent manufactured feature.

Face identity remains observable through physical composition and packaging.

## Color

Each packaged Shape provides the resolved physical color associated with every physical component.

Coin preserves those resolved component colors when composing its Faces. Face prefixing changes component semantic identity but does not change the component's resolved color.

For example:

```text
base - white
```

from Face A becomes conceptually:

```text
faceA-base - white
```

with the same physical color.

Coin physical composition does not reinterpret Shape color policy, reopen source Shape color configuration, or independently assign source Shape component colors.

The packaged Shape 3MF is authoritative for the resolved colors of its components.

Components are not merged merely because they share a physical printing color.

Recoloring a packaged Coin is a format-level operation over its semantic component identities and does not alter Coin geometry, Face compatibility, or component membership.


## Physical Transformation

Coin consumes physical Shape geometry after Shape has introduced physical X/Y and Z dimensions.

Coin does not repeat Shape registered composition, Artwork placement, Shape sizing, Feature participation, or Shape dimensionalization.

Coin changes only the placement and orientation necessary to compose the two source Shapes as opposite Faces of one object.

Every component belonging to one Face receives the same rigid Face transformation.

Coin must not independently transform individual Face components in a way that changes their registration with the other components of that Face.

Coin preserves the physical dimensions of each source component.


## Packaging

Packaging occurs after physical Coin composition.

Coin packaging consumes the complete transformed component collections of both Faces.

Packaging:

- preserves `faceA-` and `faceB-` component identity;
- preserves each source component's resolved physical color;
- preserves independently printable component membership; and
- produces a printable Coin 3MF.

Packaging does not determine Face geometry, Face orientation, component participation, Shape Feature geometry, or source Shape color policy.

Coin packaging does not require access to either source Shape's configuration.

## Products and Dependencies

Coin consumes two complete packaged Shape Products, one for each Face.

A packaged Shape Product provides the packaged 3MF including embedded Shape-level metadata required for downstream compatibility. The 3MF is authoritative for physical component geometry, component identity, and resolved component colors.

The dependency system must permit the two Face roles to refer independently to the same or different packaged Shape Products.

The physical Coin component collection is itself a persistent Product and may be consumed independently of the packaged Coin.

Coin's packaged 3MF is a Product produced from that physical component collection.

Dependencies determine required execution. Requiring a packaged Shape Product causes the dependency closure to realize the Shape stages necessary to produce that Product.

Coin Products may themselves be consumed by later Realizations, Models, Artifacts, or builds.


## Final Product

The ordinary packaged Coin Product is a printable multi-component 3MF containing the physical components of both Faces.

Its component names preserve Face role and source component semantic identity.

The packaged 3MF is one Product of the Coin model. It is not architecturally privileged over reusable upstream Coin Products.

## Model Invariants

1. A Coin consists of exactly two Faces, identified as `faceA` and `faceB`.
2. Each Face is a complete packaged Shape Product.
3. A Face may originate from the same or a different Artifact or Realization as the other Face.
4. Coin consumes Shape Products by logical Product identity rather than generated filesystem path.
5. A packaged Shape 3MF is authoritative for its physical component geometry, component identity, and resolved component colors.
6. Persistent Shape-level metadata embedded in the packaged Shape 3MF provides compatibility information that cannot be recovered safely from component geometry, identity, or resolved colors.
7. Face B must use `inlaid` Shape dimensionalization.
8. Coin rejects a non-inlaid Face B rather than regenerating or re-dimensionalizing it.
9. Coin does not reopen source Shape configuration.
10. Coin does not reconstruct Faces from registered Shape geometry.
11. Coin does not reinterpret Shape Feature participation or dimensionalization.
12. The source Shape `Z = 0` planes establish the Coin mating plane.
13. The two Faces occupy opposite sides of the mating plane with their visible surfaces facing outward.
14. Every physical component of a Face receives the same rigid Face transformation.
15. Coin transformation preserves source component dimensions and intra-Face registration.
16. The transformed outer structural boundaries of the two Faces coincide at the mating plane.
17. Compatible Faces need not originate from identical Variants, Realizations, Artifacts, or configuration histories.
18. Subject to the Face B inlaid requirement, Face-local geometry may differ when the difference does not prevent valid physical mating.
19. Outer Ridge and Inner Ridge remain Face-local components and are not regenerated by Coin.
20. Border Labels, Artwork, and Artwork Fill remain Face-local components and are not regenerated by Coin.
21. When Loop participates, both Faces provide compatible transformed Loop geometry.
22. Face A and Face B Loop components remain distinct and meet at the mating plane to form the complete Loop.
23. Coin does not generate a replacement Loop.
24. When Hole participates, both Faces provide compatible transformed Hole geometry.
25. Compatible source Shape holes form one continuous Coin Hole.
26. Coin does not perform a replacement Hole subtraction.
27. A one-sided or geometrically incompatible Loop or Hole makes the Face pair invalid.
28. Every source physical component remains independently identifiable after Coin composition.
29. Face A component identities are prefixed with `faceA-`.
30. Face B component identities are prefixed with `faceB-`.
31. Prefixing Face identity does not otherwise reinterpret the source component's semantic role.
32. Coin does not merge components merely because they touch or share a printing color.
33. Coin preserves the resolved physical color of every source Shape component.
34. Coin physical composition does not reinterpret Shape color policy or independently reassign source Shape component colors.
35. Recoloring changes component color presentation without changing Coin geometry, compatibility, or component membership.
36. Coin supports `aligned` and `inverted` Face orientation, with `aligned` as the default.
37. Face orientation changes only the relative physical orientation of the complete Faces.
38. Coin has no independent structural Base between its Faces.
39. Coin does not repeat registered Shape composition or Shape physical dimensionalization.
40. Physical Coin composition precedes Coin packaging.
41. An incompatible Face pair must not produce a Coin manufacturing Product.
42. The physical Coin component collection remains a reusable Product independently of the packaged Coin.
43. Coin remains dependency-driven and realizes only Products required by the requested dependency closure.

## Scope

The Coin model defines two-sided manufactured objects composed from exactly two complete packaged Shape Products.

Coin owns:

- the semantic roles Face A and Face B;
- compatibility requirements between the two Faces;
- the requirement that Face B use inlaid Shape dimensionalization;
- relative Face orientation;
- physical composition of the Faces around their common mating plane;
- preservation and namespacing of Face component identity;
- preservation of resolved source component colors; and
- packaging of the composed physical components into a printable artifact.

Shape continues to own the geometry, dimensionalization, Feature semantics, component partition, and physical color resolution of each source Face.

Coin does not provide arbitrary multi-object assembly, free-form placement, source Shape modification, Shape re-dimensionalization, Feature reconstruction, or general-purpose mesh editing.

Capabilities outside the two-Face physical-composition and packaging contract defined by this document require an explicit extension of the Coin model or a different Model.

New Coin capabilities must be introduced deliberately through the appropriate Model or Feature contract rather than inferred from implementation behavior.
