# Laser Model Definition

The `laser` model produces two-dimensional manufacturing Products from registered Shape composition.

Laser reuses Shape's established planar geometry, incorporated Artwork, and participating Features. It does not reconstruct Shape geometry or perform physical Z dimensionalization.

This document defines the semantic contract of the Laser model.

## Purpose

Laser converts reusable registered composition into manufacturing-ready two-dimensional files for import into laser software, including xTool Studio.

Laser owns the output representation and physical two-dimensional sizing. It does not own the source design or the laser-processing job.

Conceptually:

```text
Shape Compose
      |
      v
    Laser
      |
      v
artifact.svg / artifact.png
```

## Composition

Laser consumes Shape Compose Products through the established Product-dependency mechanism.

Shape remains authoritative for:

- structural geometry;
- incorporated Artwork placement and clipping;
- participating Shape Features;
- registered component geometry and identity.

Laser preserves that composition without repeating Shape's geometry-generation or Artwork-placement logic.

Laser does not require Shape Extrude or Shape Package.

## Coordinate Space and Dimensions

Laser consumes geometry in registered Shape coordinates and establishes physical X/Y dimensions using the effective Shape size.

All exported objects share one coordinate system and preserve their relative registration, proportions, and orientation.

Laser does not introduce Z dimensions.

## Components and Objects

A semantic component identifies a meaningful part of the composed design. An exported object is its representation in a manufacturing file.

Laser preserves semantic component identity where the output format supports independent objects.

SVG grouping, display colors, document order, and downstream laser-processing layers do not define semantic identity.

Structural Shape geometry does not implicitly become a filled engraving surface.

## Artwork

Laser supports incorporated Artwork in two representations:

- **Vector:** registered color-separated geometry, preserving logical Artwork-color identities.
- **Raster:** one registered image object, preserving its placement, transparency, and applicable clipping.

Shape's composed Artwork placement is authoritative for either representation.

Selecting raster Artwork replaces the corresponding exported vector Artwork objects. Both representations must not produce duplicate Artwork coverage.

Laser may consume additional Artwork Products when required by the selected representation, using declared Product dependencies.

## Packaging

Laser produces self-contained two-dimensional manufacturing files.

SVG preserves independently identifiable objects where supported. It combines the selected composition into one document with physical dimensions.

PNG represents a flattened rasterization of the selected visible composition, with explicit resolution, dimensions, and transparency policy.

Both formats represent the same selected design, subject to their different object-identity capabilities.

Packaging does not assign laser operations, power, speed, line density, engraving mode, or execution order.

## Features

Laser Features extend output representation or manufacturing-oriented behavior without redefining Shape composition.

Each optional Feature owns its parameters, participation, interactions, and invariants.

### Vector SVG

#### Participation

Vector SVG packaging is the initial Laser capability.

It consumes existing Shape Compose geometry and produces:

```text
artifact.svg
```

#### Geometry

The output combines the participating component SVG geometry into one document.

The Shape structural composition document is not itself exported as an additional filled object. Structural geometry is represented only through explicitly participating output objects.

Component geometry retains its established registration and semantic identity.

#### Object Participation

The structural Base is represented by its outline by default, not a filled surface.

Participating ridges, labels, Artwork, and other applicable Shape Features remain independently identifiable where supported by SVG.

An object is included according to its composition and Laser participation policy, not merely because a source SVG file exists.

#### Portability

The SVG is self-contained, physically dimensioned, and suitable for import into xTool Studio.

Text and applicable geometry are represented by portable vector paths. The output must not depend on external images, unresolved fonts, or editor-specific resources.

#### Vector SVG Invariants

1. SVG packaging consumes registered Shape composition without requiring extrusion.
2. The output is one physically dimensioned SVG document.
3. Exported geometry preserves Shape registration and orientation.
4. Structural composition geometry is not duplicated as an implicit filled Base.
5. The default Base representation is an outline.
6. Participating components retain semantic identity.
7. SVG packaging does not assign laser-processing settings.

### Raster Artwork

Raster Artwork is an optional output-representation Feature.

It substitutes one registered image object for incorporated vector Artwork while preserving Shape's authoritative placement, scale, orientation, and clipping.

The exported SVG must not also contain the replaced vector Artwork objects.

Raster Artwork is embedded in a self-contained SVG when supported by the target importer. Otherwise, a separately registered raster Product may be used without duplicating composition logic.

### PNG Output

PNG Output is an optional packaging Feature.

It rasterizes the selected visible composition into one image at explicitly defined physical dimensions and resolution.

PNG preserves the intended appearance and transparency but does not preserve independent semantic objects.

## Final Product

Laser produces manufacturing-ready two-dimensional Products, initially:

```text
artifact.svg
```

Additional supported representations include:

```text
artifact.png
```

These Products participate in the ordinary Model, Variant, Realization, dependency, build, and manufacturing-state contracts.

## Model Invariants

1. Laser is a distinct Model.
2. Laser consumes registered Shape composition through declared Product dependencies.
3. Shape remains authoritative for composition, Feature geometry, and Artwork placement.
4. Laser does not duplicate Shape composition or require Shape extrusion or packaging.
5. Laser establishes physical X/Y output dimensions without Z dimensionalization.
6. All exported objects preserve their common registration.
7. Semantic component identity is independent of output grouping, display color, and laser-processing settings.
8. Laser does not implicitly convert the structural Base into a filled engraving region.
9. Vector and raster representations of the same incorporated Artwork do not produce duplicate coverage.
10. SVG and PNG represent the same selected visible design, subject to format differences.
11. Laser does not assign physical printer colors or laser-processing operations.
12. Laser Products use the established dependency, identity, and manufacturing-state machinery.

## Scope

Laser owns two-dimensional output representation, object participation, physical sizing, and manufacturing-file packaging.

Shape owns the source planar composition and its Features. Artwork owns registered source-artwork representations.

Laser does not provide independent Shape geometry generation, arbitrary object placement, physical extrusion, or machine-specific laser processing.

New Laser capabilities should be introduced as self-contained Features without changing the core Model contract unless the underlying architectural semantics change.
