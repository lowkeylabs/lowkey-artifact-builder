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
* Artwork-envelope derivation;
* source-driven color separation;
* measured Artifact colors;
* assignment of physical printer colors to Artifact colors;
* comparison with alternative library and catalog color assignments;
* registered raster color layers;
* registered vector color layers;
* optional physical dimensionalization;
* a printable multicomponent 3MF.

Artwork deliberately separates:

* interpretation of source artwork;
* discovery of the colors represented by that artwork;
* assignment of physical filament colors to those discovered colors; and
* physical dimensionalization.


## Source

Artwork consumes one raster source:

```text
source
````

The build system materializes the source into the artifact workspace
before Artwork processing begins.

Artwork stages consume the materialized source through the build-engine
context rather than depending on the source's original filesystem
location.

## Artifact Colors

Artwork color separation is controlled by:

```text
artifact_color_count
```

`artifact_color_count` defines the number of color regions requested when
the source image is traced as multicolor Artwork.

Unless explicitly configured, `artifact_color_count` is derived from the
number of configured:

```text
printer_colors
```

The default therefore permits Artwork to use the available printer color
capacity without requiring every Artwork to contain that many colors.

An explicitly configured `artifact_color_count` permits source Artwork
with a known smaller palette to request only the colors actually represented
by the Artwork.

For example, a three-color logo may configure:

```text
artifact_color_count = 3
```

even when five printer colors are available.

Artwork preparation supplies the source's color information to multicolor
tracing. It does not first quantize the source to printer, library, or catalog
filament colors.

Multicolor tracing produces `artifact_color_count` traced color regions and
assigns an RGB representation to each region.

Those measured RGB representations are the:

```text
artifact_colors
```

`artifact_colors` describe the colors discovered in the prepared Artwork.

Artifact colors are derived product information rather than configured
physical filament identities.

An Artifact color has:

* a stable color-region identity within the prepared Artwork; and
* an RGB representation measured from the multicolor trace.

Artifact colors are not required to equal the RGB representation of any
printer, library, or catalog color.

Physical filament availability does not determine the RGB values of
`artifact_colors`.

The number of Artifact colors is:

```text
artifact_color_count
```

Artwork does not manufacture additional Artifact colors merely because
additional printer tools or filament colors are available.

## Color Availability

Artwork assigns or compares its Artifact colors against three distinct
physical color-availability scopes:

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
color assignment must reference a known color-catalog identity.

The complete physical color catalog is distinct from the printer and library
availability sets.

Catalog entries explicitly identified as synthetic test colors do not
participate in physical catalog-wide assignment.

Physical color assignment does not change:

* `artifact_colors`;
* `artifact_color_count`;
* `printer_colors`;
* `library_colors`; or
* the color catalog.

## Color Assignment

Artifact colors may be assigned to physical filament colors from three
availability scopes.

The resulting assignment sets are:

```text
printer_assignments
library_assignments
catalog_assignments
```

`printer_assignments` assigns Artifact colors to distinct colors selected
from `printer_colors`.

`library_assignments` assigns Artifact colors to distinct colors selected
from `library_colors`.

`catalog_assignments` assigns Artifact colors to distinct physical colors
selected from the complete physical color catalog.

Each assignment maps one Artifact color to one physical color and records:

* the Artifact color identity;
* the Artifact color RGB representation;
* the selected physical color semantic identity;
* the selected physical color RGB representation; and
* the perceptual distance between the Artifact color and selected physical
  color.

Assignment uses the generic perceptual color-distance semantics defined by
the shared color infrastructure.

Assignments within one scope are determined jointly.

For a scope containing at least `artifact_color_count` available physical
colors, Artwork selects a one-to-one assignment between Artifact colors and
distinct candidate physical colors that minimizes aggregate perceptual
distance.

Two different Artifact colors are not assigned the same physical color within
one assignment set.

The aggregate distance of an assignment set is the sum of the individual
Artifact-to-physical-color perceptual distances in that assignment.

The aggregate distance therefore measures how closely the selected physical
palette represents the complete set of Artifact colors.

Assignment is deterministic for the same ordered Artifact colors and ordered
candidate colors.

Candidate order provides deterministic resolution when multiple assignments
have equal aggregate distance.

Printer, library, and catalog assignments are independent.

A physical color selected by one assignment scope does not constrain the
physical colors selected by another scope.

## Printer Assignments

`printer_assignments` define the physical semantic colors used to manufacture
the current Artwork realization.

The number of printer assignments is:

```text
artifact_color_count
```

A printer assignment therefore selects the best
`artifact_color_count` distinct colors from `printer_colors`.

When:

```text
artifact_color_count < len(printer_colors)
```

some configured printer colors remain unused by the Artwork.

For example, three-color Artwork on a printer configured with five colors
uses the best three-color assignment and does not create two additional
Artifact colors merely to use every configured printer color.

Execution requiring physical printer assignment requires enough distinct
printer colors to assign every Artifact color.

The semantic physical color identity established by `printer_assignments`
is preserved through registered raster products, registered vector products,
standalone extrusion, and standalone packaging.

## Library Assignments

`library_assignments` describe the best physical realization available from:

```text
library_colors
```

The assignment selects `artifact_color_count` distinct library colors that
minimize aggregate perceptual distance to the complete set of Artifact
colors.

Library assignment is diagnostic.

It permits comparison between the currently configured printer realization
and an alternative realization using filament already present in the user's
library.

Library assignment does not automatically:

* change `printer_colors`;
* install filament;
* change Artifact configuration; or
* change persistent manufacturing products.

## Catalog Assignments

`catalog_assignments` describe the best physical realization available from
the complete physical color catalog.

The assignment selects `artifact_color_count` distinct physical catalog
colors that minimize aggregate perceptual distance to the complete set of
Artifact colors.

Catalog assignment is diagnostic.

It permits comparison between:

* the current printer realization;
* the best realization using filament already in the user's library; and
* the best realization using known physical catalog colors.

Catalog assignment does not automatically:

* purchase filament;
* change `printer_colors`;
* change `library_colors`;
* change Artifact configuration; or
* change persistent manufacturing products.

## Color Analysis

Artwork color analysis exposes the individual and aggregate perceptual
distances associated with:

```text
printer_assignments
library_assignments
catalog_assignments
```

Individual assignment distance identifies how closely a selected physical
filament color represents one Artifact color.

Aggregate assignment distance identifies how closely an entire selected
physical palette represents the complete Artifact color set.

These distances permit evaluation of both:

* individual Artifact colors that are reproduced poorly; and
* the relative quality of printer, library, and catalog palette alternatives.

Color analysis operates on persistent Artifact color information derived from
prepared Artwork.

Standalone Artwork extrusion and packaging are not prerequisites for
analyzing Artifact colors or calculating alternative assignments.

## Prepare

Preparation converts the source image into prepared Artwork described by:

```text
trace.svg
envelope.svg
```

The trace represents the prepared multicolor Artwork.

The envelope represents the outer region belonging to the Artwork.

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
the exterior background, not merely on their color.

An enclosed Artwork region is not excluded solely because its color also
occurs in the exterior background.

Envelope derivation affects interpretation of the source Artwork. It does
not alter the registered coordinate system or the semantics of downstream
Artwork products.

Preparation preserves the source color information belonging to the Artwork
rather than quantizing it to configured physical filament colors.

Preparation performs multicolor tracing using:

```text
artifact_color_count
```

as the requested number of color regions.

The RGB representations assigned to those traced regions by multicolor tracing
form `artifact_colors`.

The traced color regions collectively represent the Artwork within the
derived envelope.

Physical printer, library, or catalog color assignments do not determine
the Artifact colors discovered during preparation.

## Raster

Rasterization converts prepared Artwork into registered,
color-separated raster products.

Raster consumes the Artifact colors measured from the prepared multicolor
trace.

Raster establishes the `printer_assignments` required for the current
physical realization.

Raster products:

* use one common coordinate system;
* preserve Artifact color-region identity;
* preserve the assigned printer semantic color identity;
* represent mutually exclusive color regions;
* collectively cover the Artwork envelope;
* use `artwork_pixels` as their raster resolution;
* are described by a raster manifest.

Every location belonging to the registered Artwork is assigned to exactly one
raster color region.

Raster island cleanup may remove insignificant disconnected geometry, but it
must preserve complete color assignment of retained Artwork rather than
creating unassigned holes within the retained Artwork envelope.

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
* preserve Artifact color-region identity;
* preserve the assigned printer semantic color identity.

The Artwork envelope uses the same registered coordinate system as the
vector color layers and remains registered with them.

The envelope represents the outer occupied region of the registered Artwork.

It is not an independent color layer and does not have physical color
identity.

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

* the Artifact color regions;
* the vector product associated with each region;
* the Artifact RGB representation associated with each region;
* the assigned printer semantic color identity associated with each region;
* the assigned printer RGB representation associated with each region;
* the Artwork envelope;
* the common `registered_extent`.

The envelope represents the outer occupied region of the Artwork in the
common registered coordinate system.

A consuming model may use the envelope to fit or otherwise place the Artwork
within its own registered geometry without independently determining the
bounds of individual color layers.

The `registered_extent` defines the common registered coordinate system.

The envelope defines the occupied region within that coordinate system.

All transformations that preserve Artwork registration must be applied
consistently to the envelope and every registered color layer.

Registered Artwork has no physical manufacturing size or physical Z
semantics.

The vector manifest preserves the Artifact color information and printer
assignment information required by downstream consumers.

Color analysis may use the persistent Artifact color information to calculate
printer, library, and catalog assignments without requiring standalone
extrusion or packaging.

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

Extrusion preserves the printer semantic color assignment established for
each registered Artwork color region.

## Package

Packaging combines the dimensionalized Artwork components into:

```text
artifact.3mf
```

The final standalone Artwork artifact is a multicomponent 3MF.

Assigned printer color components remain independently printable components.

Packaging preserves the printer semantic color identity and RGB
representation established upstream.

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

Likewise, color analysis and alternative library or catalog assignment do not
require standalone Artwork extrusion or packaging.

The consuming model is responsible for the physical size, placement, and
dimensionalization of the registered Artwork within its own object.

When fitting registered Artwork within another model, the consumer may use the
registered Artwork envelope to determine geometric containment while applying
one common transformation to the envelope and all registered color layers.

Any region belonging to the consuming model but lying outside the registered
Artwork envelope is the responsibility of the consuming model.

Artwork does not assign a fill color to such surrounding geometry.

## Parameters

Artwork defines or consumes:

```text
source
artifact_color_count
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

`artifact_color_count` defines the number of color regions requested during
multicolor source tracing.

Unless explicitly configured, `artifact_color_count` is derived from the
number of configured `printer_colors`.

`artifact_colors` are derived product information rather than configuration
parameters. They contain the RGB representations measured from the
`artifact_color_count` multicolor traced regions.

`artwork_envelope_mode` defines how the Artwork envelope is derived from
the source image.

It defaults to:

```text
shrink-wrap
```

Supported envelope modes are:

```text
alpha
shrink-wrap
```

`alpha` derives the envelope from meaningful source alpha.

`shrink-wrap` derives a conservative outer envelope by distinguishing
exterior background from enclosed Artwork.

Exterior classification is not determined by color equality alone.

`artwork_pixels` defines raster processing resolution.

`artwork_min_island_area` defines the minimum retained raster island area
in pixels.

`artwork_island_connectivity` defines the connectivity used for raster
island detection.

`artwork_size` defines the physical X/Y size of standalone dimensionalized
Artwork.

`artwork_raise` defines the physical Z height of standalone dimensionalized
Artwork.

`printer_colors` identifies the configured colors currently available to
the printer.

Printer colors provide:

* the default source for deriving `artifact_color_count`; and
* the candidate physical colors used to calculate `printer_assignments`.

`library_colors` identifies the configured filament-library availability used
to calculate `library_assignments`.

Physical `artwork_size` is intentionally absent from prepare, raster, and
vector color interpretation.

The shared color catalog is reference data rather than an Artwork parameter.

Artwork consumes catalog identities and RGB representations through the
configuration resolver when printer, library, or catalog assignment requires
them.

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

Artifact color analysis and alternative physical color assignment are
consumers of persistent Artwork color information.

They do not introduce additional Artwork manufacturing stages.

## Dynamic Products

Raster, vector, and extrusion stages may produce a variable number of
color-specific products.

The number of color-specific products is determined by the prepared Artifact
color regions rather than by the total number of physical colors available in
the printer, library, or catalog.

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

8. `artifact_color_count` defines the number of color regions requested from
   multicolor source tracing.

9. Unless explicitly configured, `artifact_color_count` is derived from the
   number of configured `printer_colors`.

10. An explicitly configured `artifact_color_count` may be smaller than the
    number of configured printer colors.

11. Artwork does not create additional Artifact colors merely to use all
    available printer colors.

12. Preparation preserves source color information within the Artwork
    envelope until multicolor tracing performs source color separation.

13. Preparation does not quantize source Artwork to printer, library, or
    catalog filament RGB values before multicolor color discovery.

14. Multicolor tracing assigns RGB representations to the traced color
    regions.

15. The RGB representations measured from those traced regions form
    `artifact_colors`.

16. Artifact colors are derived product information and are not required to
    correspond exactly to any physical catalog color.

17. Physical filament availability does not determine the RGB values assigned
    to Artifact colors.

18. The prepared color regions collectively represent the Artwork within its
    envelope.

19. `printer_assignments` map Artifact colors one-to-one to distinct selected
    `printer_colors`.

20. `library_assignments` map Artifact colors one-to-one to distinct selected
    `library_colors`.

21. `catalog_assignments` map Artifact colors one-to-one to distinct selected
    physical catalog colors.

22. Each physical color assignment preserves the Artifact color identity,
    Artifact RGB representation, selected physical semantic identity,
    selected physical RGB representation, and perceptual distance.

23. Physical color assignment uses the shared generic perceptual
    color-distance semantics.

24. Each assignment scope minimizes aggregate perceptual distance across the
    complete set of Artifact colors.

25. Aggregate assignment distance is the sum of the individual perceptual
    distances in that assignment.

26. Different Artifact colors receive distinct physical color identities
    within one assignment scope.

27. Assignment is deterministic for the same ordered Artifact colors and
    ordered candidate colors.

28. Printer, library, and catalog assignments are independent.

29. `printer_assignments` establish the physical semantic color identities
    used by the current Artwork manufacturing realization.

30. When more printer colors are available than Artifact colors, unused
    printer colors remain unused.

31. Execution requiring printer assignment requires enough distinct
    `printer_colors` to assign every Artifact color.

32. Library and catalog assignments are diagnostic and do not automatically
    modify printer, library, catalog, or Artifact configuration.

33. Physical catalog-wide assignment excludes catalog entries explicitly
    identified as synthetic test colors.

34. Raster color layers use one common registered coordinate system.

35. Raster color regions are mutually exclusive.

36. Registered raster color regions collectively cover retained Artwork
    within the registered Artwork envelope.

37. Every retained Artwork location belongs to exactly one registered raster
    color region.

38. Raster island cleanup is defined in raster pixel space rather than
    physical space.

39. Raster island cleanup does not create unassigned retained Artwork merely
    by removing an insignificant color island.

40. Raster processing is independent of physical `artwork_size`.

41. Vector color layers use one common registered coordinate system.

42. Vector processing is independent of physical `artwork_size`.

43. The vector manifest records the common `registered_extent`.

44. The Artwork envelope uses the same registered coordinate system as the
    vector color layers.

45. The Artwork envelope represents the outer occupied region of registered
    Artwork.

46. The `registered_extent` defines the common registered coordinate system;
    the envelope defines the occupied region within that coordinate system.

47. All registration-preserving transformations are applied consistently to
    the Artwork envelope and every registered color layer.

48. A consumer may determine Artwork containment from the registered envelope
    without independently determining the bounds of individual color layers.

49. Registered vector Artwork has no predetermined physical manufacturing
    size.

50. Artifact color-region identity and assigned printer semantic color
    identity are preserved through registered raster and vector products.

51. Registered vector Artwork is a reusable intermediate product.

52. Standalone physical dimensionalization begins at extrusion.

53. Standalone extrusion uniformly maps `registered_extent` to `artwork_size`.

54. All color layers receive the same dimensional transformation and remain
    registered.

55. Standalone extrusion uses `artwork_raise` as the physical Z height.

56. Standalone extrusion preserves the assigned printer semantic color
    identity of each color component.

57. Standalone packaging produces a multicomponent printable 3MF.

58. Standalone packaging preserves the assigned printer semantic color
    identity and RGB representation of each component.

59. Artwork does not provide an underlying structural base.

60. Artwork does not define a fill color for geometry outside the Artwork
    envelope.

61. Geometry belonging to a consuming model outside the registered Artwork
    envelope is the responsibility of that consuming model.

62. Another model can consume registered vector Artwork without requiring
    standalone Artwork extrusion or packaging.

63. Artifact color analysis operates on persistent Artwork color information
    without requiring standalone Artwork extrusion or packaging.

64. Individual assignment distances describe the quality of physical
    reproduction of individual Artifact colors.

65. Aggregate assignment distance describes the quality of a complete
    physical color assignment.

66. Color analysis and alternative assignments do not modify persistent
    Artwork manufacturing products.

## Scope

The Artwork model includes:

* raster source interpretation;
* Artwork-envelope derivation;
* source-driven multicolor separation;
* Artifact color measurement;
* printer color assignment;
* library color assignment;
* physical-catalog color assignment;
* individual and aggregate color-distance analysis;
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
* physical sizing of Artwork when consumed by another model;
* fill color for geometry belonging to a consuming model outside the Artwork
  envelope;
* automatic mutation of printer or library color configuration;
* automatic filament installation or purchasing decisions.

Those responsibilities belong to the consuming model, configuration layer, or
explicit user action as appropriate.
