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
- an optional outer ridge;
- optional registered Artwork;
- a printable multicomponent 3MF.

Shape owns the physical dimensions and placement of geometry incorporated
into the Shape.

Shape geometry is represented initially in a registered, nonphysical
coordinate space. Structural Shape geometry and incorporated Artwork remain
registered through composition.

Physical dimensionalization occurs after registered composition.


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

The `structure` stage does not produce the final physical Shape,
extruded manufacturing geometry, or a packaged 3MF.

Structural geometry is a persistent product that may be inspected,
resolved, and consumed through the normal product-dependency mechanism.


## Base

Every Shape contains a structural base.

The base follows the selected:

    shape_geometry

Its two-dimensional outline is established by the registered structural
geometry.

During physical dimensionalization, that registered outline is scaled so
that the complete physical Shape envelope is determined by:

    shape_size

The physical thickness of the base is determined by:

    shape_base_raise

The dimensionalized base extends from:

    Z = 0

through:

    Z = shape_base_raise

Base thickness therefore belongs to physical dimensionalization rather
than to the registered two-dimensional structural representation.


## Outer Ridge

A Shape may contain an outer ridge.

The ridge is controlled by:

    shape_outer_ridge_width
    shape_outer_ridge_raise

The ridge follows the boundary of the selected Shape geometry.

Ridge width is measured inward from the outer Shape boundary.

The ridge does not increase:

    shape_size

The ridge exists only when both:

    shape_outer_ridge_width > 0
    shape_outer_ridge_raise > 0

If either value is zero, the ridge does not exist.

`shape_outer_ridge_width` is a physical dimension measured in
millimeters.

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

The dimensionalized ridge begins at the top of the base:

    Z = shape_base_raise

and extends through:

    Z = shape_base_raise + shape_outer_ridge_raise


## Interior Region

Shape defines a registered interior region available for Artwork.

Without an outer ridge, the interior region is bounded by the registered
Shape boundary.

With an outer ridge, the interior region is bounded by the registered
inner boundary of the ridge.

An outer ridge therefore reduces the registered area available for
Artwork without changing the registered outer Shape envelope or the
physical value of:

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

The composed result retains sufficient component identity to allow
different structural and Artwork components to receive their appropriate
physical Z semantics during downstream dimensionalization and to remain
independently printable where required.


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

`shape_geometry` selects the structural geometry.

The remaining parameters are physical dimensions measured in
millimeters.

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

In particular, incorporated Artwork color components remain independently
printable components suitable for multicolor printing.

Packaging does not determine Shape geometry, Artwork fitting, or physical
dimensionalization.


## Final Product

Shape produces:

    artifact.3mf

The final artifact contains the dimensionalized structural Shape
geometry.

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

9. The outer ridge lies within the Shape boundary and does not increase
   `shape_size`.

10. Zero outer-ridge width or zero outer-ridge raise disables the outer
    ridge.

11. The inner boundary of an outer ridge defines the available registered
    interior region when the ridge exists.

12. Physical Shape policy may be converted into relative registered-space
    relationships when required for composition without assigning final
    physical dimensions to the registered coordinate system.

13. Shape can consume registered vector Artwork produced by another
    artifact.

14. Consuming registered Artwork does not require standalone Artwork
    extrusion or packaging.

15. Dynamic Artwork component membership is obtained from its declared
    manifest rather than filesystem scanning.

16. Registered Artwork and registered structural Shape geometry are
    composed before final physical X/Y dimensionalization.

17. Shape determines the physical size and placement of incorporated
    Artwork.

18. Incorporated Artwork is centered and uniformly contained within the
    available interior region.

19. Artwork aspect ratio and registration between color components are
    preserved.

20. All components of one registered Artwork collection receive the same
    transformation from Artwork registered space into Shape registered
    space.

21. Physical X/Y dimensionalization of the composed Shape is determined
    by `shape_size`.

22. Physical Z dimensions are introduced according to component semantics
    during downstream dimensionalization.

23. Packaging occurs after physical dimensionalization.

24. Shape produces a valid printable 3MF containing its structural
    geometry and any incorporated Artwork components.


## Initial Scope

The initial Shape model includes:

- circle geometry;
- square geometry;
- octagon geometry;
- canonical registered Shape geometry;
- physical Shape size;
- physical base thickness;
- optional outer ridge;
- optional registered Artwork;
- centered, aspect-preserving Artwork fitting;
- registered Shape/Artwork composition;
- downstream physical dimensionalization;
- final 3MF packaging.

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
