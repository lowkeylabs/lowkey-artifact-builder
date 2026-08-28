# Shape Model Definition

The `shape` model constructs a physical object from parameterized
two-dimensional geometry.

A Shape may optionally incorporate registered Artwork produced by another
artifact.

This document defines the semantic contract of the Shape model.


## Purpose

Shape provides structural geometry for objects such as coasters,
ornaments, plaques, and similar primarily two-dimensional objects.

The initial Shape model supports:

- circle, square, and octagon geometry;
- a physical base;
- an optional integrated or separately printable outer ridge;
- optional registered Artwork;
- a printable multicomponent 3MF.

Shape owns the physical dimensions and placement of geometry incorporated
into the Shape.

Shape geometry is represented initially in a registered, nonphysical
coordinate space. Structural Shape geometry and incorporated Artwork remain
registered through composition.

Physical dimensionalization occurs after registered composition.

The assembled physical Shape and its partitioning into independently
printable components are distinct concepts.

Two Shape configurations may therefore describe the same assembled physical
geometry while partitioning that geometry into different printable
components.


## Geometry

Shape supports:

    circle
    square
    octagon

Geometry is selected by:

    shape_geometry

The parameter:

    shape_size

defines the overall physical X/Y extent of the dimensionalized Shape.

Its meaning is:

    circle   -> diameter
    square   -> side length
    octagon  -> width and height of the bounding box

A dimensionalized Shape with:

    shape_size = 100

therefore fits within a 100 mm × 100 mm envelope regardless of the
selected geometry.

`shape_size` defines the complete assembled Shape envelope.

Optional structural features, including an outer ridge, do not increase
this envelope.

`shape_size` does not determine the coordinate extent of the registered
structural representation.


## Registered Shape Coordinate Space

Shape structural geometry is first produced in a registered,
nonphysical two-dimensional coordinate space.

The complete Shape envelope uses the canonical registered coordinate
extent:

    X = -0.5 through +0.5
    Y = -0.5 through +0.5

The Shape origin is therefore:

    X = 0
    Y = 0

and represents the center of the Shape.

For the supported geometries:

    circle   -> diameter 1.0, centered at the origin
    square   -> 1.0 × 1.0, centered at the origin
    octagon  -> 1.0 × 1.0 bounding envelope, centered at the origin

The registered coordinate system establishes geometry, registration,
and relative spatial relationships.

It does not assign physical millimeter dimensions.

In particular:

    shape_size

does not change the registered outer extent of the Shape.

Changing `shape_size` changes the later physical dimensionalization of
the registered geometry rather than changing the registered geometry's
coordinate envelope.


## Structural Geometry

The `structure` stage produces registered structural Shape geometry.

Structural geometry is determined by Shape geometry policy such as:

    shape_geometry

The structural representation is two-dimensional registered geometry.

Structural geometry describes the complete Shape envelope independently
of how later physical geometry is partitioned into printable components.

The `structure` stage does not produce the final physical Shape,
extruded manufacturing geometry, or a packaged 3MF.

Structural geometry is a persistent product that may be inspected,
resolved, and consumed through the normal product-dependency mechanism.


## Base

Every Shape contains a structural base.

The base follows the selected:

    shape_geometry

The complete Shape outline is established by the registered structural
geometry.

The physical thickness of the base is determined by:

    shape_base_raise

The dimensionalized base extends from:

    Z = 0

through:

    Z = shape_base_raise

Base thickness therefore belongs to physical dimensionalization rather
than to the registered two-dimensional structural representation.

Without a separately printable outer ridge, the base occupies the complete
Shape X/Y envelope.

With a separately printable outer ridge, the base occupies the region
inside the ridge's inner boundary.

The separately printable ridge therefore reduces the X/Y extent of the
base component without reducing the complete assembled Shape envelope.


## Outer Ridge

A Shape may contain an outer ridge.

The ridge is controlled by:

    shape_outer_ridge_width
    shape_outer_ridge_raise
    shape_outer_ridge_style

The supported ridge styles are:

    integrated
    separate

The ridge follows the boundary of the selected Shape geometry.

Ridge width is measured inward from the outer Shape boundary.

The ridge does not increase:

    shape_size

The ridge exists only when both:

    shape_outer_ridge_width > 0
    shape_outer_ridge_raise > 0

If either value is zero, the ridge does not exist.

When the ridge does not exist, `shape_outer_ridge_style` has no effect on
the produced geometry.

`shape_outer_ridge_width` is a physical dimension measured in millimeters.

When ridge geometry must participate in registered composition before
physical dimensionalization, its physical width is converted to a
relative registered-space width using the relationship between:

    shape_outer_ridge_width
    shape_size

For example, a 5 mm ridge on a 100 mm Shape occupies 0.05 registered
Shape units inward from the corresponding outer boundary.

This conversion does not assign physical dimensions to the registered
coordinate system. It expresses physical Shape policy as a relative
relationship within registered Shape space.


## Integrated Outer Ridge

With:

    shape_outer_ridge_style = integrated

the ridge is structurally integrated with the base.

The base retains the complete Shape X/Y envelope.

The ridge occupies the perimeter region between:

    the complete Shape outer boundary

and:

    the ridge inner boundary

The ridge lies on top of the base.

The dimensionalized base occupies:

    Z = 0

through:

    Z = shape_base_raise

The dimensionalized ridge occupies:

    Z = shape_base_raise

through:

    Z = shape_base_raise + shape_outer_ridge_raise

The base and ridge together form one structural printable component.

Conceptually, for:

    shape_base_raise = 2
    shape_outer_ridge_raise = 1

the integrated structure has:

    base   -> Z = 0 through 2
    ridge  -> Z = 2 through 3

The complete assembled structural height at the ridge is therefore:

    shape_base_raise + shape_outer_ridge_raise


## Separate Outer Ridge

With:

    shape_outer_ridge_style = separate

the ridge is an independently printable structural component.

The ridge retains the complete Shape outer boundary.

Its inner boundary is inset from that outer boundary by:

    shape_outer_ridge_width

The base outer boundary becomes the ridge inner boundary.

The base and ridge therefore occupy adjacent, nonoverlapping X/Y regions.

The separately printable base occupies:

    Z = 0

through:

    Z = shape_base_raise

The separately printable ridge occupies:

    Z = 0

through:

    Z = shape_base_raise + shape_outer_ridge_raise

The separate ridge uses the complete assembled ridge height because it
replaces both the perimeter portion of the base and the raised ridge that
would otherwise occupy that perimeter.

Conceptually, for:

    shape_base_raise = 2
    shape_outer_ridge_raise = 1

the separate structure has:

    base   -> Z = 0 through 2
    ridge  -> Z = 0 through 3

The resulting assembled physical geometry is equivalent to the integrated
construction, but the structural geometry is partitioned into two
independently printable components.

This partitioning permits the outer ridge to be assigned independently
from the base during downstream multicomponent printing.


## Ridge Equivalence

For otherwise identical Shape parameters, changing:

    shape_outer_ridge_style

between:

    integrated
    separate

does not change:

- the complete Shape outer envelope;
- the ridge outer boundary;
- the ridge inner boundary;
- the registered interior region;
- the complete assembled structural height;
- the complete assembled physical geometry.

It changes only the partitioning of that geometry into independently
printable structural components.

For example, for a 100 mm square with:

    shape_outer_ridge_width = 5

both ridge styles have:

    complete outer envelope = 100 mm × 100 mm
    ridge inner envelope    = 90 mm × 90 mm

With an integrated ridge:

    base outer envelope = 100 mm × 100 mm

because the ridge lies on top of the base.

With a separate ridge:

    base outer envelope = 90 mm × 90 mm

because the independently printable ridge occupies the surrounding
5 mm perimeter region.

The union of the separate base and separate ridge corresponds to the
same assembled structural geometry as the integrated base and ridge.


## Interior Region

Shape defines a registered interior region available for Artwork.

Without an outer ridge, the interior region is bounded by the registered
Shape boundary.

With an outer ridge, the interior region is bounded by the registered
inner boundary of the ridge.

The same ridge inner boundary is used for integrated and separate ridge
styles.

Changing ridge style therefore does not change the registered area
available for Artwork.

An outer ridge reduces the registered area available for Artwork without
changing the registered outer Shape envelope or the physical value of:

    shape_size

The registered interior region provides the common Shape coordinate
space into which registered Artwork is fitted.


## Artwork

Artwork is optional.

A Shape without Artwork is a complete valid artifact.

Shape does not consume an Artwork source PNG and does not require a
completed standalone Artwork 3MF.

Shape consumes registered Artwork produced as an intermediate product by
another artifact using the `artwork` model.

The initial Shape model consumes the registered vector representation
defined by the Artwork model.

Artwork components remain registered with one another when consumed by
Shape.


## Artwork Dependency

Registered Artwork is supplied through the normal artifact
product-dependency mechanism.

Shape depends on the Artwork product it consumes, not on the completed
Artwork artifact.

For the current Artwork model, consuming registered vector Artwork
requires the upstream dependency:

    artwork/prepare
          ↓
    artwork/raster
          ↓
    artwork/vector
          ↓
        shape

Artwork stages after the consumed vector product are not prerequisites.

In particular, Shape does not require:

    artwork/extrude
    artwork/package

to consume registered vector Artwork.

Shape consumes the declared Artwork manifest rather than discovering
dynamic Artwork components by scanning generated directories.


## Registered Artwork Coordinate Space

Registered Artwork may use a different coordinate extent from registered
Shape geometry.

For example, Artwork may have a registered extent derived from its
vectorization coordinate system while Shape uses its canonical:

    -0.5 through +0.5

registered envelope.

There is no requirement that one Artwork registered unit equal one Shape
registered unit.

The relationship between the two registered coordinate spaces is
established by the Shape composition transformation.

All components belonging to one registered Artwork collection share the
same Artwork coordinate system and receive the same transformation into
registered Shape space.


## Artwork Placement

Registered Artwork is placed within the registered Shape interior region.

Artwork is:

- centered within the Shape;
- uniformly scaled;
- aspect-ratio preserving;
- contained within the available interior region.

Artwork is not stretched to fill the interior region.

Artwork is not cropped merely to fill the interior region.

The transformation from registered Artwork space into registered Shape
space is derived from the Artwork collection's common registered extent
and the available registered Shape interior region.

All registered Artwork color layers receive the same transformation so
that their registration is preserved.


## Registered Composition

Shape composition operates on registered geometry.

The structural Shape geometry and any incorporated registered Artwork
remain nonphysical through composition.

Conceptually:

    registered Shape structure ─────┐
                                    │
                                    ▼
                                 compose
                                    ▲
                                    │
    registered Artwork ─────────────┘
                                    │
                                    ▼
                         registered composition

Composition establishes the spatial relationship between structural
Shape geometry and incorporated Artwork.

When Artwork is present, its registered coordinate system is transformed
into registered Shape coordinate space.

Composition does not assign the final physical X/Y dimensions of the
Shape.

Composition retains sufficient semantic component identity to support
downstream physical dimensionalization and packaging.

In particular, when:

    shape_outer_ridge_style = separate

the base region and outer-ridge region must remain distinguishable so
that downstream dimensionalization can produce independently printable
structural components.

When:

    shape_outer_ridge_style = integrated

the base and ridge belong to one structural printable component even
though their physical Z semantics differ.

The composed result similarly retains sufficient Artwork component
identity to allow different structural and Artwork components to receive
their appropriate physical Z semantics and to remain independently
printable where required.


## Physical Dimensionalization

Physical dimensionalization occurs after registered composition.

The Shape extrusion boundary converts composed registered geometry into
physical manufacturing geometry.

Conceptually:

    registered composition
              │
              ▼
           extrude
              │
              ▼
      physical geometry

At this boundary:

    shape_size

determines the overall physical X/Y extent of the Shape.

The canonical registered Shape width of `1.0` therefore corresponds to:

    shape_size

millimeters in physical space.

For example:

    shape_size = 100

establishes:

    1.0 registered Shape unit = 100 mm

for the dimensionalization of the complete Shape envelope.

A registered Artwork component occupying 0.8 Shape units across therefore
occupies 80 mm when incorporated into a 100 mm Shape.

Changing `shape_size` changes the physical size of the composed geometry
without changing its registered spatial relationships.

Physical Z dimensions are also introduced at the dimensionalization
boundary according to the semantic role of each component.

These dimensions include:

    shape_base_raise
    shape_outer_ridge_raise

and the defined Z policy for incorporated Artwork.

Ridge style determines structural component partitioning during
dimensionalization.

For an integrated ridge, dimensionalization produces one structural
component containing the base and raised perimeter geometry.

For a separate ridge, dimensionalization produces independent base and
outer-ridge structural components whose assembled union corresponds to
the integrated structural geometry.


## Artwork Dimensionalization

Registered Artwork does not carry a predetermined physical X/Y size into
Shape.

Shape determines the physical size of incorporated Artwork from its
placement within registered Shape space and the later dimensionalization
of that Shape.

The standalone Artwork parameter:

    artwork_size

does not determine Artwork size within Shape.

For example, if registered Artwork is fitted to occupy 0.8 of the Shape
width and:

    shape_size = 100

the dimensionalized Artwork width is:

    80 mm

The same registered composition dimensionalized with:

    shape_size = 75

produces an Artwork width of:

    60 mm

without changing the registered Artwork-to-Shape placement.

Shape is therefore responsible for the physical size, placement, and
dimensionalization of Artwork incorporated into the Shape.

The Z semantics of incorporated Artwork must be defined before physical
Artwork composition is considered complete.


## Coordinate-Space Boundaries

Shape distinguishes registered geometry from physical manufacturing
geometry.

Conceptually:

    Artwork source / processing space
                │
                ▼
      registered Artwork space
                │
                │ fit / transform
                ▼
        registered Shape space
                │
                │ compose
                ▼
      registered composition
                │
                │ dimensionalize
                ▼
        physical millimeter space

The registered Shape coordinate system is the common coordinate system
used to establish spatial relationships between structural Shape geometry
and incorporated Artwork.

Physical parameters may inform relative relationships within registered
Shape space when necessary, such as determining the registered inner
boundary corresponding to a physical ridge width.

Such calculations do not make the registered coordinate system physical.

Final physical X/Y dimensionalization occurs only at the downstream
dimensionalization boundary.


## Parameters

The initial Shape model defines:

    shape_geometry
    shape_size
    shape_base_raise
    shape_outer_ridge_width
    shape_outer_ridge_raise
    shape_outer_ridge_style

`shape_geometry` selects the structural geometry.

`shape_outer_ridge_style` selects how an enabled outer ridge is partitioned
into printable structural geometry.

Its supported values are:

    integrated
    separate

The default ridge style is:

    integrated

The dimensional parameters are:

    shape_size
    shape_base_raise
    shape_outer_ridge_width
    shape_outer_ridge_raise

and are physical dimensions measured in millimeters.

Physical parameters do not imply that every stage consuming Shape policy
operates in physical coordinate space.

A stage operating on registered geometry may use physical parameters to
derive relative registered-space relationships when those relationships
are required before dimensionalization.

Final physical dimensionalization remains the responsibility of the
Shape dimensionalization boundary.

Artwork dependency binding is not represented by a filesystem-path
parameter.


## Packaging

Physical Shape components are packaged after dimensionalization.

Packaging preserves independently printable components where required.

With an integrated outer ridge, the base and outer ridge are packaged as
one structural component.

With a separate outer ridge, the base and outer ridge remain independent
structural components in the packaged artifact.

Incorporated Artwork color components likewise remain independently
printable components suitable for multicolor printing.

Packaging does not determine Shape geometry, ridge geometry, ridge
partitioning, Artwork fitting, or physical dimensionalization.

Those semantics must already be established before packaging.


## Final Product

Shape produces:

    artifact.3mf

The final artifact contains the dimensionalized structural Shape geometry.

Without a separate outer ridge, the structural base and any integrated
ridge are represented as one structural printable component.

With a separate outer ridge, the final artifact contains independently
printable base and outer-ridge structural components.

When Artwork is configured, the final artifact also contains the
incorporated Artwork components.

Artwork color components remain independently printable components for
multicolor printing.

A Shape without Artwork still produces a complete valid printable
artifact.


## Invariants

A conforming initial Shape implementation satisfies the following:

1. Shape can produce circle, square, and octagon geometry.

2. Registered structural Shape geometry uses a canonical 1.0 × 1.0
   envelope centered at the origin.

3. Registered structural Shape geometry remains nonphysical until the
   Shape dimensionalization boundary.

4. `shape_size` has consistent physical overall-envelope semantics for
   every supported geometry.

5. `shape_size` does not determine the coordinate extent of registered
   structural Shape geometry.

6. Every Shape contains a base with physical thickness determined by
   `shape_base_raise`.

7. Shape can produce a complete artifact without Artwork.

8. An outer ridge follows the selected Shape boundary.

9. Outer-ridge width is measured inward from the complete Shape boundary.

10. The outer ridge lies within the Shape boundary and does not increase
    `shape_size`.

11. Zero outer-ridge width or zero outer-ridge raise disables the outer
    ridge.

12. An enabled outer ridge may be integrated with the base or partitioned
    as a separately printable structural component.

13. With an integrated outer ridge, the base retains the complete Shape
    X/Y envelope and the ridge occupies the perimeter above the base.

14. With a separate outer ridge, the ridge retains the complete Shape
    outer boundary and the base outer boundary becomes the ridge inner
    boundary.

15. A separate outer ridge and its base occupy adjacent, nonoverlapping
    X/Y regions.

16. An integrated ridge occupies Z from `shape_base_raise` through
    `shape_base_raise + shape_outer_ridge_raise`.

17. A separate ridge occupies Z from zero through
    `shape_base_raise + shape_outer_ridge_raise`.

18. Integrated and separate ridge styles produce equivalent complete
    assembled structural geometry for otherwise identical Shape
    parameters.

19. Changing ridge style does not change the complete Shape envelope,
    ridge inner boundary, registered interior region, or complete assembled
    structural height.

20. The inner boundary of an outer ridge defines the available registered
    interior region when the ridge exists.

21. Physical Shape policy may be converted into relative registered-space
    relationships when required for composition without assigning final
    physical dimensions to the registered coordinate system.

22. Shape can consume registered vector Artwork produced by another
    artifact.

23. Consuming registered Artwork does not require standalone Artwork
    extrusion or packaging.

24. Dynamic Artwork component membership is obtained from its declared
    manifest rather than filesystem scanning.

25. Registered Artwork and registered structural Shape geometry are
    composed before final physical X/Y dimensionalization.

26. Shape determines the physical size and placement of incorporated
    Artwork.

27. Incorporated Artwork is centered and uniformly contained within the
    available interior region.

28. Artwork aspect ratio and registration between color components are
    preserved.

29. All components of one registered Artwork collection receive the same
    transformation from Artwork registered space into Shape registered
    space.

30. Physical X/Y dimensionalization of the composed Shape is determined
    by `shape_size`.

31. Physical Z dimensions are introduced according to component semantics
    during downstream dimensionalization.

32. Separately printable structural components retain their identity
    through dimensionalization and packaging.

33. Packaging occurs after physical dimensionalization.

34. Shape produces a valid printable 3MF containing its structural
    geometry and any incorporated Artwork components.


## Initial Scope

The initial Shape model includes:

- circle geometry;
- square geometry;
- octagon geometry;
- canonical registered Shape geometry;
- physical Shape size;
- physical base thickness;
- optional integrated outer ridge;
- optional separately printable outer ridge;
- structural component partitioning;
- optional registered Artwork;
- centered, aspect-preserving Artwork fitting;
- registered Shape/Artwork composition;
- downstream physical dimensionalization;
- final multicomponent 3MF packaging.

The initial Shape model does not include:

- internal ridges;
- dashed ridges;
- hangers;
- handles;
- text or labels;
- arbitrary Artwork positioning;
- multiple independent Artwork placements;
- arbitrary custom Shape outlines.

These capabilities may be added later by deliberately extending the Shape
definition.
