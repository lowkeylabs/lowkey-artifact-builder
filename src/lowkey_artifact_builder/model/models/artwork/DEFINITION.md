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

* a raster source image;
* a semantic color palette;
* preparation and normalization of the source;
* registered raster color layers;
* registered vector color layers;
* optional physical dimensionalization;
* a printable multicomponent 3MF.

Artwork deliberately separates interpretation of source artwork from
physical dimensionalization.

## Source

Artwork consumes one raster source:

```text
source
```

The build system materializes the source into the artifact workspace
before Artwork processing begins.

Artwork stages consume the materialized source through the build-engine
context rather than depending on the source's original filesystem
location.

## Colors

Artwork uses an ordered semantic color palette:

```text
artwork_colors
```

`artwork_colors` is normally derived from the configured printer colors
but may be explicitly configured.

Artwork preparation uses a semantic fill color:

```text
artwork_fill_color
```

The default Artwork fill color is:

```text
white
```

The resolved `artwork_fill_color` must be present in `artwork_colors`.

The fill color is used for otherwise unassigned pixels inside the derived
Artwork envelope. `white` has no special semantic meaning other than being
the default fill color.

Each Artwork color has:

* a semantic color identity; and
* an RGB representation.

Semantic color identity is preserved through the color-separated raster,
vector, extrusion, and packaging products.

## Prepare

Preparation converts the source image into normalized artwork described
by:

```text
trace.svg
envelope.svg
```

The trace represents the prepared multicolor artwork.

The envelope represents the outer region belonging to the artwork.

Pixels outside the envelope do not belong to the Artwork.

Artwork envelope derivation is controlled by:

```text
artwork_envelope_mode
```

Supported envelope modes are:

```text
alpha
shrink-wrap
```

The default envelope mode is:

```text
shrink-wrap
```

`alpha` derives the Artwork envelope from meaningful source alpha.

`shrink-wrap` derives a conservative outer envelope by distinguishing
exterior background from enclosed Artwork.

Shrink-wrap classification depends on whether source regions belong to
the exterior background, not merely on their color. An enclosed Artwork
region is not excluded solely because its color also occurs in the
exterior background.

Envelope derivation affects interpretation of the source Artwork. It does
not alter the registered coordinate system or the semantics of downstream
Artwork products.

Prepared artwork is reduced to the configured Artwork color palette.

Otherwise unassigned pixels inside the envelope are assigned the configured:

```text
artwork_fill_color
```

before color separation.

## Raster

Rasterization converts prepared artwork into registered,
color-separated raster products.

Raster products:

* use one common coordinate system;
* preserve semantic color identity;
* represent mutually exclusive color regions;
* use `artwork_pixels` as their raster resolution;
* are described by a raster manifest.

Dynamic raster products are stored relative to their manifest.

Raster island cleanup is controlled by:

```text
artwork_min_island_area
artwork_island_connectivity
```

Island area is measured in raster pixels.

Raster processing does not depend on physical `artwork_size`.

## Vector

Vectorization converts registered raster color layers into registered
vector color layers.

All vector layers:

* use one common coordinate system;
* remain registered with one another;
* preserve semantic color identity.

The Artwork envelope uses the same registered coordinate system as the
vector color layers and remains registered with them.

The envelope represents the outer occupied region of the registered Artwork.

It is not an independent layer and does not have semantic color identity.

The common coordinate system is described by:

```text
registered_extent
```

in the vector manifest.

`registered_extent` is dimensionless.

Registered vector geometry has no physical manufacturing size.

Vector processing does not depend on:

```text
artwork_size
artwork_raise
```

## Registered Artwork

The vector-stage products, together with the registered Artwork envelope,
form the reusable registered representation of Artwork.

Registered Artwork consists of:

* the vector manifest;
* the color-layer products described by the vector manifest;
* the Artwork envelope;
* the common `registered_extent`.

The registered representation provides a downstream consumer with:

* the semantic color layers;
* the vector product associated with each layer;
* the color representation of each layer;
* the Artwork envelope;
* the common `registered_extent`.

The envelope represents the outer occupied region of the Artwork in the
common registered coordinate system.

A consuming model may use the envelope to fit or otherwise place the Artwork
within its own registered geometry without independently determining the
bounds of individual color layers.

The `registered_extent` defines the common registered coordinate system. The
envelope defines the occupied region within that coordinate system.

All transformations that preserve Artwork registration must be applied
consistently to the envelope and every registered color layer.

Registered Artwork has no physical manufacturing size or physical Z
semantics.

## Extrude

Extrusion is the physical dimensionalization boundary for standalone
Artwork.

Extrusion introduces:

```text
artwork_size
artwork_raise
```

The common registered coordinate system is uniformly scaled so that:

```text
registered_extent -> artwork_size
```

All color layers receive the same physical X/Y transformation.

The registered Artwork is centered as one coordinate system rather than
centering individual color layers.

Each color layer is extruded from:

```text
Z = 0
```

through:

```text
Z = artwork_raise
```

Extrusion produces independently printable color components described by
an extrusion manifest.

## Package

Packaging combines the dimensionalized Artwork components into:

```text
artifact.3mf
```

The final standalone Artwork artifact is a multicomponent 3MF.

Semantic color components remain independently printable components.

Artwork does not add an underlying structural base to the standalone
artifact.

## Reuse

Registered Artwork may be consumed by another artifact before standalone
Artwork extrusion or packaging.

For the current Artwork model, a consumer of registered vector Artwork
requires:

```text
artwork/prepare
      │
      ├──────────────┐
      │              │
      ▼              │
artwork/raster       │
      │              │
      ▼              │
artwork/vector ◄─────┘
      │
      ▼
   consumer
```

The vector stage consumes both:

* registered raster color layers produced by `artwork/raster`; and
* the registered Artwork envelope produced by `artwork/prepare`.

The later Artwork stages:

```text
artwork/extrude
artwork/package
```

are not prerequisites merely because another model consumes registered
vector Artwork.

The consuming model is responsible for the physical size, placement, and
dimensionalization of the registered Artwork within its own object.

When fitting registered Artwork within another model, the consumer may use the
registered Artwork envelope to determine geometric containment while applying
one common transformation to the envelope and all registered color layers.

## Parameters

Artwork defines or consumes:

```text
source
artwork_colors
artwork_fill_color
artwork_envelope_mode
artwork_pixels
artwork_min_island_area
artwork_island_connectivity
artwork_size
artwork_raise
```

`source` identifies the external raster input.

`artwork_colors` defines the ordered semantic palette.

`artwork_fill_color` defines the semantic color assigned to otherwise
unassigned pixels inside the Artwork envelope. It defaults to `white` and
must be present in `artwork_colors`.


`artwork_envelope_mode` defines how the Artwork envelope is derived from
the source image. It defaults to `alpha`.

Supported envelope modes are:

```text
alpha
shrink-wrap
```

`alpha` derives the envelope from meaningful source alpha.

`shrink-wrap` derives a conservative outer envelope by distinguishing
exterior background from enclosed Artwork. Exterior classification is not
determined by color equality alone.

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

```text
10 prepare
20 raster
30 vector
40 extrude
50 package
```

with dependencies:

```text
prepare
   │
   ├──────────────┐
   │              │
   ▼              │
raster            │
   │              │
   ▼              │
vector ◄──────────┘
   │
   ▼
extrude
   │
   ▼
package
```

The direct dependencies reflect the products consumed by each stage:

* `raster` depends on `prepare`;
* `vector` depends on `raster` for registered color layers;
* `vector` also depends directly on `prepare` for the registered Artwork
  envelope;
* `extrude` depends on `vector`;
* `package` depends on `extrude`.

The principal declared products are:

```text
prepare/trace.svg
prepare/envelope.svg
raster/products.json
vector/products.json
extrude/products.json
package/artifact.3mf
```

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
3. Artwork envelope derivation is controlled by `artwork_envelope_mode`.
4. `artwork_envelope_mode` defaults to `alpha`.
5. `alpha` envelope derivation determines meaningful source foreground from
   source alpha.
6. `shrink-wrap` envelope derivation produces a conservative outer envelope
   by distinguishing exterior background from enclosed Artwork.
7. Shrink-wrap does not exclude an enclosed Artwork region solely because
   its color also occurs in the exterior background.
8. Prepared Artwork uses the configured semantic color palette.
9. Otherwise unassigned pixels inside the Artwork envelope use
   `artwork_fill_color`, which must be present in `artwork_colors`.
10. Raster color layers use one common registered coordinate system.
11. Raster color regions are mutually exclusive.
12. Raster island cleanup is defined in raster pixel space rather than
    physical space.
13. Raster processing is independent of physical `artwork_size`.
14. Vector color layers use one common registered coordinate system.
15. Vector processing is independent of physical `artwork_size`.
16. The vector manifest records the common `registered_extent`.
17. The Artwork envelope uses the same registered coordinate system as the
    vector color layers.
18. The Artwork envelope represents the outer occupied region of registered
    Artwork.
19. The `registered_extent` defines the common registered coordinate system;
    the envelope defines the occupied region within that coordinate system.
20. All registration-preserving transformations are applied consistently to
    the Artwork envelope and every registered color layer.
21. A consumer may determine Artwork containment from the registered envelope
    without independently determining the bounds of individual color layers.
22. Registered vector Artwork has no predetermined physical manufacturing
    size.
23. Semantic color identity is preserved through the color-separated
    products.
24. Registered vector Artwork is a reusable intermediate product.
25. Standalone physical dimensionalization begins at extrusion.
26. Standalone extrusion uniformly maps `registered_extent` to
    `artwork_size`.
27. All color layers receive the same dimensional transformation and
    remain registered.
28. Standalone extrusion uses `artwork_raise` as the physical Z height.
29. Standalone packaging produces a multicomponent printable 3MF.
30. Artwork does not provide an underlying structural base.
31. Another model can consume registered vector Artwork without requiring
    standalone Artwork extrusion or packaging.


## Scope

The Artwork model includes:

* raster source interpretation;
* artwork-envelope derivation;
* semantic color separation;
* registered raster geometry;
* registered vector geometry;
* standalone dimensionalization;
* standalone multicomponent 3MF packaging;
* reusable registered vector Artwork.

Artwork does not define:

* structural bases;
* circles, squares, octagons, or other supporting Shape geometry;
* structural ridges;
* hangers or handles;
* labels or text belonging to another object;
* placement of Artwork within another model;
* physical sizing of Artwork when consumed by another model.

Those responsibilities belong to the model consuming the registered
Artwork.
