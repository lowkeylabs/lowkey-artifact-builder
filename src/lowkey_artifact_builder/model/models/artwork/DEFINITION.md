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
* color-availability analysis;
* printer-palette recommendation;
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

Unless explicitly configured, `artwork_fill_color` is derived from the
configured `printer_colors`.

The derived fill color is the configured printer color perceptually closest
to ideal RGB white:

```text
RGB(255, 255, 255)
```

Selection uses the generic perceptual color-distance semantics defined by the
shared color infrastructure.

The selected value preserves the semantic identity of the corresponding
printer color. Artwork does not substitute or invent a generic `white`
identity for the selected physical color.

When multiple printer colors have equal perceptual distance from ideal white,
printer color order determines the result.

An explicitly configured `artwork_fill_color` overrides this derivation
through normal configuration resolution.

The resolved `artwork_fill_color` must be present in `artwork_colors`.

The fill color is used for otherwise unassigned pixels inside the derived
Artwork envelope.

Each Artwork color has:

* a semantic color identity; and
* an RGB representation.

Semantic color identity is preserved through the color-separated raster,
vector, extrusion, and packaging products.

## Color Availability

Artwork may compare its prepared semantic colors against three distinct
color-availability scopes:

```text
printer_colors
library_colors
color catalog
```

`printer_colors` identifies colors currently available to the printer.

`library_colors` identifies colors physically available from the user's
filament library.

The color catalog identifies known physical filament colors and provides
their semantic identities and RGB representations.

`printer_colors` and `library_colors` are independent resolved configuration
parameters. Neither is required to be a subset of the other.

Every resolved `printer_colors` or `library_colors` entry used by Artwork
color analysis must reference a known color-catalog identity.

The complete physical color catalog is distinct from the printer and library
availability sets. Catalog entries explicitly identified as synthetic test
colors do not participate in physical catalog-wide analysis or recommendation.

Color-availability analysis is diagnostic. It does not change:

* `printer_colors`;
* `library_colors`;
* `artwork_colors`; or
* the color catalog.

## Color Matching

Registered Artwork may be analyzed against the printer, library, and physical
catalog availability scopes.

For each prepared Artwork semantic color, analysis independently determines:

* the nearest printer color;
* the nearest library color; and
* the nearest physical catalog color.

Each match preserves:

* the Artwork semantic color identity;
* the selected candidate color identity; and
* the perceptual distance between them.

Matching uses the generic perceptual color-distance semantics defined by the
shared color infrastructure.

Printer, library, and catalog matching are independent. A color selected in
one scope does not constrain the color selected in another scope.

Color analysis operates on persistent registered Artwork color information.
Standalone Artwork extrusion and packaging are not prerequisites for analyzing
registered Artwork colors.

## Palette Recommendation

Artwork may recommend fixed-size filament palettes for representing the
complete prepared Artwork.

Recommendations are produced independently for:

```text
printer
library
physical catalog
```

Each candidate palette is evaluated as a whole.

The score for a candidate palette is the aggregate perceptual distance required
to represent every prepared Artwork color by its nearest color in that
candidate palette.

Palette recommendation therefore optimizes the complete palette rather than
independently selecting one filament for each Artwork color.

A recommendation provides:

* the selected semantic color identities; and
* the aggregate perceptual match score.

Recommendation is deterministic for the same ordered Artwork colors and
candidate colors.

A recommendation may require one or more mandatory semantic color identities.
Every mandatory color must be present in and included by each candidate scope
being recommended. A recommendation cannot silently omit a required mandatory
color.

Recommended palettes contain distinct semantic color identities.

Like color analysis, palette recommendation is diagnostic and does not modify
configuration or persistent Artwork products.


## Five-Tool Palette Recommendation

The current five-tool Artwork recommendation selects:

```text
resolved artwork filler
+
four additional filament colors
```

for a total palette size of five.

The resolved `artwork_fill_color` is the mandatory color for five-tool
palette recommendation. Because `artwork_fill_color` is normally derived
as the configured printer color perceptually closest to ideal RGB white,
the recommendation preserves the physical semantic identity of the
printer's effective white color.

`artwork_fill_color` determines the color assigned to otherwise unassigned
pixels inside the Artwork envelope and the mandatory color included in each
five-tool palette recommendation.

Unless explicitly configured, `artwork_fill_color` is derived from the
configured `printer_colors` as the color perceptually closest to ideal RGB
white:

RGB(255, 255, 255)

Five-tool recommendation uses the resolved `artwork_fill_color` semantic
identity directly. It does not independently select, infer, or substitute a
separate white color identity.

Five-tool recommendations are produced independently for:

* the current printer colors;
* the filament library; and
* the physical color catalog.

The three scopes may therefore produce different recommended palettes and
different aggregate scores.

This permits comparison of:

* how well the current printer configuration can represent the Artwork;
* how well an alternative palette using available library filament can
  represent the Artwork; and
* how well an alternative palette using known physical catalog filament can
  represent the Artwork.

Five-tool recommendation does not automatically install filament, change
printer configuration, change library configuration, or rewrite Artifact
configuration.


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

The vector manifest preserves the semantic color identity and RGB
representation required for subsequent color analysis and palette
recommendation.

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

Likewise, color analysis and palette recommendation operate on registered
Artwork without requiring standalone Artwork extrusion or packaging.

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
printer_colors
library_colors
```

`source` identifies the external raster input.

`artwork_colors` defines the ordered semantic palette.

`artwork_fill_color` defines the semantic color assigned to otherwise
unassigned pixels inside the Artwork envelope.

Unless explicitly configured, it is derived from `printer_colors` as the
configured printer color perceptually closest to ideal RGB white using the
shared perceptual color-distance semantics.

The derived value preserves the selected printer color's semantic identity.

The resolved `artwork_fill_color` must be present in `artwork_colors`.

`artwork_envelope_mode` defines how the Artwork envelope is derived from
the source image. It defaults to `shrink-wrap`.

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

`printer_colors` identifies the configured printer color availability used by Artwork fill-color derivation, color analysis, and palette recommendation.

`library_colors` identifies the configured filament-library availability used
by Artwork color analysis and palette recommendation.

Physical `artwork_size` is intentionally absent from raster and vector
processing.

The shared color catalog is reference data rather than an Artwork parameter.
Artwork consumes catalog identities and RGB representations through the
configuration resolver when color analysis or recommendation requires them.

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

Color analysis and palette recommendation are consumers of registered Artwork
products. They do not introduce additional Artwork manufacturing stages.

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

2. Prepared Artwork is limited to its derived Artwork envelope.

3. Artwork envelope derivation is controlled by `artwork_envelope_mode`.

4. `artwork_envelope_mode` defaults to `shrink-wrap`.

5. `alpha` envelope derivation determines meaningful source foreground from
   source alpha.

6. `shrink-wrap` envelope derivation produces a conservative outer envelope
   by distinguishing exterior background from enclosed Artwork.

7. Shrink-wrap does not exclude an enclosed Artwork region solely because
   its color also occurs in the exterior background.

8. Prepared Artwork uses the configured semantic color palette.

9. Unless explicitly configured, `artwork_fill_color` is derived from
   `printer_colors` as the configured printer color perceptually closest to
   ideal RGB white.

10. Derived `artwork_fill_color` selection uses the shared generic perceptual
    color-distance semantics.

11. Derived `artwork_fill_color` preserves the semantic identity of the
    selected printer color.

12. Equal-distance fill-color candidates are resolved deterministically
    according to printer color order.

13. Otherwise unassigned pixels inside the Artwork envelope use
    `artwork_fill_color`, which must be present in `artwork_colors`.

14. Raster color layers use one common registered coordinate system.

15. Raster color regions are mutually exclusive.

16. Raster island cleanup is defined in raster pixel space rather than
    physical space.

17. Raster processing is independent of physical `artwork_size`.

18. Vector color layers use one common registered coordinate system.

19. Vector processing is independent of physical `artwork_size`.

20. The vector manifest records the common `registered_extent`.

21. The Artwork envelope uses the same registered coordinate system as the
    vector color layers.

22. The Artwork envelope represents the outer occupied region of registered
    Artwork.

23. The `registered_extent` defines the common registered coordinate system;
    the envelope defines the occupied region within that coordinate system.

24. All registration-preserving transformations are applied consistently to
    the Artwork envelope and every registered color layer.

25. A consumer may determine Artwork containment from the registered envelope
    without independently determining the bounds of individual color layers.

26. Registered vector Artwork has no predetermined physical manufacturing
    size.

27. Semantic color identity is preserved through the color-separated
    products.

28. Registered vector Artwork is a reusable intermediate product.

29. Standalone physical dimensionalization begins at extrusion.

30. Standalone extrusion uniformly maps `registered_extent` to
    `artwork_size`.

31. All color layers receive the same dimensional transformation and
    remain registered.

32. Standalone extrusion uses `artwork_raise` as the physical Z height.

33. Standalone packaging produces a multicomponent printable 3MF.

34. Artwork does not provide an underlying structural base.

35. Another model can consume registered vector Artwork without requiring
    standalone Artwork extrusion or packaging.

36. `printer_colors` and `library_colors` are independent color-availability
    scopes whose entries reference known catalog color identities when the
    corresponding analysis is required.

37. Artwork color analysis independently matches every prepared semantic
    Artwork color against printer, library, and physical-catalog candidates.

38. Artwork color matches preserve the requested semantic identity, selected
    candidate identity, and perceptual distance.

39. Physical catalog-wide analysis excludes catalog entries explicitly
    identified as synthetic test colors.

40. Artwork color analysis operates on registered Artwork without requiring
    standalone Artwork extrusion or packaging.

41. Artwork color analysis does not modify Artwork, printer, library, or
    catalog configuration.

42. Palette recommendation evaluates candidate palettes as complete palettes
    against the complete prepared Artwork.

43. Palette recommendation uses aggregate perceptual distance from every
    prepared Artwork color to its nearest selected palette color as its score.

44. Printer, library, and physical-catalog palette recommendations are
    independent.

45. Recommended palettes contain distinct semantic color identities.

46. Mandatory palette colors must be present in and included by every
    candidate scope being recommended.

47. Palette recommendation is deterministic for the same ordered Artwork and
    candidate colors.

48. Palette recommendation does not modify Artwork, printer, library, or
    catalog configuration.

49. Five-tool Artwork recommendation produces a five-color palette consisting
    of the resolved `artwork_fill_color` as a mandatory palette color plus four
    additional colors.

50. Five-tool Artwork recommendation uses the resolved `artwork_fill_color`
    semantic identity directly. It does not independently select, infer, or
    substitute a separate white color identity.

51. Five-tool recommendations independently compare current printer colors,
    library colors, and the physical color catalog.



## Scope

The Artwork model includes:

* raster source interpretation;
* Artwork-envelope derivation;
* semantic color separation;
* registered raster geometry;
* registered vector geometry;
* color-availability analysis;
* fixed-size palette recommendation;
* five-tool printer-palette recommendation;
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
* physical sizing of Artwork when consumed by another model;
* automatic mutation of printer or library color configuration;
* automatic filament installation or purchasing decisions.

Those responsibilities belong to the consuming model, configuration layer, or
explicit user action as appropriate.
