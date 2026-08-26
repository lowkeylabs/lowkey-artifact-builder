# Shape Model Definition

The `shape` model constructs a physical object from parameterized
two-dimensional geometry.

A Shape may optionally incorporate registered artwork produced by another
artifact.

This document defines the semantic contract of the Shape model.


## Purpose

Shape provides structural geometry for objects such as coasters,
ornaments, plaques, and similar primarily two-dimensional objects.

The initial Shape model supports:

- circle, square, and octagon geometry;
- a physical base;
- an optional outer ridge;
- optional registered artwork;
- a printable multicomponent 3MF.

Shape owns the physical dimensions and placement of geometry incorporated
into the Shape.


## Geometry

Shape supports:

    circle
    square
    octagon

Geometry is selected by:

    shape_geometry

The parameter:

    shape_size

defines the overall X/Y extent of the Shape.

Its meaning is:

    circle   -> diameter
    square   -> side length
    octagon  -> width and height of the bounding box

A Shape with:

    shape_size = 100

therefore fits within a 100 mm × 100 mm envelope regardless of the
selected geometry.


## Base

Every Shape contains a structural base.

The base follows the selected `shape_geometry`.

Its X/Y extent is determined by:

    shape_size

Its physical thickness is determined by:

    shape_base_raise

The base extends from:

    Z = 0

through:

    Z = shape_base_raise


## Outer Ridge

A Shape may contain an outer ridge.

The ridge is controlled by:

    shape_outer_ridge_width
    shape_outer_ridge_raise

The ridge follows the boundary of the selected Shape geometry.

Ridge width is measured inward from the outer Shape boundary.

The ridge does not increase `shape_size`.

The ridge exists only when both:

    shape_outer_ridge_width > 0
    shape_outer_ridge_raise > 0

If either value is zero, the ridge does not exist.

The ridge begins at the top of the base and extends to:

    Z = shape_base_raise + shape_outer_ridge_raise


## Interior Region

Shape defines an interior region available for artwork.

Without an outer ridge, the interior region is bounded by the Shape
boundary.

With an outer ridge, the interior region is bounded by the inner boundary
of the ridge.

An outer ridge therefore reduces the area available for artwork without
changing the overall Shape size.


## Artwork

Artwork is optional.

A Shape without Artwork is a complete valid artifact.

Shape does not consume an Artwork source PNG and does not require a
completed standalone Artwork 3MF.

Shape consumes registered artwork produced as an intermediate product by
another artifact using the `artwork` model.

The initial Shape model consumes the registered vector representation
defined by the Artwork model.


## Artwork Dependency

Registered Artwork is supplied through the normal artifact
product-dependency mechanism.

Shape depends on the Artwork product it consumes, not on the completed
Artwork artifact.

For the current Artwork model, consuming registered vector artwork
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


## Artwork Placement

Registered Artwork is placed within the Shape interior region.

Artwork is:

- centered within the Shape;
- uniformly scaled;
- aspect-ratio preserving;
- contained within the available interior region.

Artwork is not stretched to fill the interior region.

Artwork is not cropped merely to fill the interior region.

All registered Artwork color layers receive the same transformation so
that their registration is preserved.


## Artwork Dimensionalization

Registered Artwork does not carry a predetermined physical X/Y size into
Shape.

Shape determines the physical size of the Artwork from the available
interior region.

The standalone Artwork parameter:

    artwork_size

does not determine Artwork size within Shape.

Shape is responsible for the physical size, placement, and
dimensionalization of Artwork incorporated into the Shape.

The Z semantics of incorporated Artwork will be defined before Artwork
composition is implemented.


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

Artwork dependency binding is not represented by a filesystem-path
parameter.


## Final Product

Shape produces:

    artifact.3mf

The final artifact contains the structural Shape geometry.

When Artwork is configured, the final artifact also contains the
incorporated Artwork components.

Artwork color components remain independently printable components for
multicolor printing.


## Invariants

A conforming initial Shape implementation satisfies the following:

1. Shape can produce circle, square, and octagon geometry.

2. `shape_size` has consistent overall-envelope semantics for every
   supported geometry.

3. Every Shape contains a base with thickness determined by
   `shape_base_raise`.

4. Shape can produce a complete artifact without Artwork.

5. An outer ridge follows the selected Shape boundary.

6. The outer ridge lies within the Shape boundary and does not increase
   `shape_size`.

7. Zero outer-ridge width or zero outer-ridge raise disables the outer
   ridge.

8. The inner boundary of an outer ridge defines the available interior
   region when the ridge exists.

9. Shape can consume registered vector Artwork produced by another
   artifact.

10. Consuming registered Artwork does not require standalone Artwork
    extrusion or packaging.

11. Shape determines the physical size and placement of incorporated
    Artwork.

12. Incorporated Artwork is centered and uniformly contained within the
    available interior region.

13. Artwork aspect ratio and registration between color components are
    preserved.

14. Shape produces a valid printable 3MF containing its structural
    geometry and any incorporated Artwork components.


## Initial Scope

The initial Shape model includes:

- circle geometry;
- square geometry;
- octagon geometry;
- physical Shape size;
- physical base thickness;
- optional outer ridge;
- optional registered Artwork;
- centered, aspect-preserving Artwork fitting;
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
