# Artwork Model Definition

The `artwork` model converts raster source artwork into registered,
color-separated geometry.

Registered Artwork may be dimensionalized into a standalone multicolor
3MF or consumed as an intermediate product by another model.

This document defines the semantic contract of the Artwork model.


## Purpose

Artwork interprets raster source artwork and converts it into reusable
registered geometry.

The Artwork model supports:

- a raster source image;
- a semantic color palette;
- preparation and normalization of the source;
- registered raster color layers;
- registered vector color layers;
- optional physical dimensionalization;
- a printable multicomponent 3MF.

Artwork deliberately separates interpretation of source artwork from
physical dimensionalization.


## Source

Artwork consumes one raster source:

    source

The build system materializes the source into the artifact workspace
before Artwork processing begins.

Artwork stages consume the materialized source through the build-engine
context rather than depending on the source's original filesystem
location.


## Colors

Artwork uses an ordered semantic color palette:

    artwork_colors

`artwork_colors` is normally derived from the configured printer colors
but may be explicitly configured.

Each Artwork color has:

- a semantic color identity; and
- an RGB representation.

Semantic color identity is preserved through the color-separated raster,
vector, extrusion, and packaging products.


## Prepare

Preparation converts the source image into normalized artwork described
by:

    trace.svg
    envelope.svg

The trace represents the prepared multicolor artwork.

The envelope represents the outer region belonging to the artwork.

Pixels outside the envelope do not belong to the Artwork.

Prepared artwork is reduced to the configured Artwork color palette.


## Raster

Rasterization converts prepared artwork into registered,
color-separated raster products.

Raster products:

- use one common coordinate system;
- preserve semantic color identity;
- represent mutually exclusive color regions;
- use `artwork_pixels` as their raster resolution;
- are described by a raster manifest.

Dynamic raster products are stored relative to their manifest.

Raster island cleanup is controlled by:

    artwork_min_island_area
    artwork_island_connectivity

Island area is measured in raster pixels.

Raster processing does not depend on physical `artwork_size`.


## Vector

Vectorization converts registered raster color layers into registered
vector color layers.

All vector layers:

- use one common coordinate system;
- remain registered with one another;
- preserve semantic color identity.

The common coordinate system is described by:

    registered_extent

in the vector manifest.

`registered_extent` is dimensionless.

Registered vector geometry has no physical manufacturing size.

Vector processing does not depend on:

    artwork_size
    artwork_raise


## Registered Artwork

The vector-stage products form the reusable registered representation of
Artwork.

Registered Artwork consists of the vector manifest and the color-layer
products it describes.

The registered representation provides a downstream consumer with:

- the semantic color layers;
- the vector product associated with each layer;
- the color representation of each layer;
- the common `registered_extent`.

A consumer can therefore dimensionalize the Artwork without independently
determining the bounds of each color layer.

All transformations that preserve Artwork registration must be applied
consistently to every registered color layer.


## Extrude

Extrusion is the physical dimensionalization boundary for standalone
Artwork.

Extrusion introduces:

    artwork_size
    artwork_raise

The common registered coordinate system is uniformly scaled so that:

    registered_extent -> artwork_size

All color layers receive the same physical X/Y transformation.

The registered Artwork is centered as one coordinate system rather than
centering individual color layers.

Each color layer is extruded from:

    Z = 0

through:

    Z = artwork_raise

Extrusion produces independently printable color components described by
an extrusion manifest.


## Package

Packaging combines the dimensionalized Artwork components into:

    artifact.3mf

The final standalone Artwork artifact is a multicomponent 3MF.

Semantic color components remain independently printable components.

Artwork does not add an underlying structural base to the standalone
artifact.


## Reuse

Registered Artwork may be consumed by another artifact before standalone
Artwork extrusion or packaging.

For the current Artwork model, a consumer of registered vector Artwork
requires:

    artwork/prepare
          ↓
    artwork/raster
          ↓
    artwork/vector
          ↓
    consumer

The later Artwork stages:

    artwork/extrude
    artwork/package

are not prerequisites merely because another model consumes registered
vector Artwork.

The consuming model is responsible for the physical size, placement, and
dimensionalization of the registered Artwork within its own object.


## Parameters

Artwork defines or consumes:

    source
    artwork_colors
    artwork_pixels
    artwork_min_island_area
    artwork_island_connectivity
    artwork_size
    artwork_raise

`source` identifies the external raster input.

`artwork_colors` defines the ordered semantic palette.

`artwork_pixels` defines raster processing resolution.

`artwork_min_island_area` defines the minimum retained raster island area
in pixels.

`artwork_island_connectivity` defines the connectivity used for raster
island detection.

`artwork_size` defines the physical X/Y size of standalone dimensionalized
Artwork.

`artwork_raise` defines the physical Z height of standalone dimensionalized
Artwork.

Physical `artwork_size` is intentionally absent from raster and vector
processing.


## Stages

Artwork defines:

    10 prepare
    20 raster
    30 vector
    40 extrude
    50 package

with dependencies:

    prepare
       ↓
    raster
       ↓
    vector
       ↓
    extrude
       ↓
    package

The principal declared products are:

    prepare/trace.svg
    prepare/envelope.svg
    raster/products.json
    vector/products.json
    extrude/products.json
    package/artifact.3mf

Product paths are local to their producing stages.


## Dynamic Products

Raster, vector, and extrusion stages may produce a variable number of
color-specific products.

These dynamic products are described by the declared stage manifest.

Consumers use the manifest to discover dynamic products rather than
scanning stage directories.

Dynamic-product paths recorded by a manifest are relative to that
manifest's stage-local product location.


## Invariants

A conforming Artwork implementation satisfies the following:

1. Artwork consumes a materialized raster source image.

2. Prepared Artwork is limited to its derived artwork envelope.

3. Prepared Artwork uses the configured semantic color palette.

4. Raster color layers use one common registered coordinate system.

5. Raster color regions are mutually exclusive.

6. Raster island cleanup is defined in raster pixel space rather than
   physical space.

7. Raster processing is independent of physical `artwork_size`.

8. Vector color layers use one common registered coordinate system.

9. Vector processing is independent of physical `artwork_size`.

10. The vector manifest records the common `registered_extent`.

11. Registered vector Artwork has no predetermined physical manufacturing
    size.

12. Semantic color identity is preserved through the color-separated
    products.

13. Registered vector Artwork is a reusable intermediate product.

14. Standalone physical dimensionalization begins at extrusion.

15. Standalone extrusion uniformly maps `registered_extent` to
    `artwork_size`.

16. All color layers receive the same dimensional transformation and
    remain registered.

17. Standalone extrusion uses `artwork_raise` as the physical Z height.

18. Standalone packaging produces a multicomponent printable 3MF.

19. Artwork does not provide an underlying structural base.

20. Another model can consume registered vector Artwork without requiring
    standalone Artwork extrusion or packaging.


## Scope

The Artwork model includes:

- raster source interpretation;
- artwork-envelope derivation;
- semantic color separation;
- registered raster geometry;
- registered vector geometry;
- standalone dimensionalization;
- standalone multicomponent 3MF packaging;
- reusable registered vector Artwork.

Artwork does not define:

- structural bases;
- circles, squares, octagons, or other supporting Shape geometry;
- structural ridges;
- hangers or handles;
- labels or text belonging to another object;
- placement of Artwork within another model;
- physical sizing of Artwork when consumed by another model.

Those responsibilities belong to the model consuming the registered
Artwork.
