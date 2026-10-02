# Shape Model Definition

The `shape` model constructs a physical object from parameterized
two-dimensional geometry.

A Shape may optionally incorporate registered Artwork produced by
another artifact.

This document defines the semantic contract of the Shape model.

## Purpose

Shape provides structural geometry for objects such as coasters,
ornaments, plaques, and similar primarily two-dimensional objects.

The initial Shape model supports:

- circle, square, and regular polygon geometry;
- configurable regular-polygon side count and rotation;
- a physical base;
- an optional integrated or separately printable outer ridge;
- independently assignable base and outer-ridge colors;
- optional registered Artwork;
- a printable multicomponent 3MF.

Shape owns the physical dimensions and placement of geometry
incorporated into the Shape.

Shape geometry is represented initially in a registered, nonphysical
coordinate space. Structural Shape geometry and incorporated Artwork
remain registered through composition.

Physical dimensionalization occurs after registered composition.

The assembled physical Shape and its partitioning into independently
printable components are distinct concepts.

Two Shape configurations may therefore describe the same assembled
physical geometry while partitioning that geometry into different
printable components.

## Geometry

Shape supports:

```text
circle
square
polygon
```

Geometry is selected by:

```text
shape_geometry
```

Regular polygon geometry is additionally controlled by:

```text
shape_sides
shape_rotation
```

`shape_sides` specifies the number of sides of a regular polygon.

It must be an integer greater than or equal to:

```text
3
```

The default polygon side count is:

```text
8
```

and therefore describes a regular octagon when:

```text
shape_geometry = "polygon"
```

`shape_sides` does not alter circle or square geometry.

`shape_rotation` specifies the counterclockwise rotation of polygon
geometry in degrees.

The default polygon rotation is:

```text
0 degrees
```

The canonical zero-degree polygon orientation places one vertex on the
positive Y axis.

For a regular polygon having:

```text
n = shape_sides
```

a rotation of:

```text
180 / n
```

degrees places the center of one side on the positive Y axis.

For example, an eight-sided polygon uses:

```text
shape_rotation = 0
```

for a vertex-centered top and:

```text
shape_rotation = 22.5
```

for a side-centered top.

`shape_rotation` may represent an arbitrary angular rotation. It is not
limited to vertex-centered or side-centered orientations.

Rotation changes polygon orientation without changing its proportions or
configured physical size.

`shape_rotation` does not alter circle or square geometry.

The parameter:

```text
shape_size
```

defines the overall physical X/Y extent of the dimensionalized Shape.

Its meaning is:

```text
circle   -> diameter
square   -> side length
polygon  -> maximum width or height of the bounding envelope
```

A dimensionalized Shape with:

```text
shape_size = 100
```

therefore has a maximum X/Y extent of 100 mm regardless of the selected
geometry.

For circle and square geometry, both the width and height are 100 mm.

For polygon geometry, the polygon is uniformly normalized after rotation
so that its greatest X/Y extent is 100 mm. The other extent may be
smaller depending on the polygon side count and rotation.

`shape_size` defines the complete assembled Shape envelope.

Optional Features do not increase this envelope unless their Feature contracts
explicitly define otherwise.

`shape_size` does not determine the coordinate extent of the registered
structural representation.

## Registered Shape Coordinate Space

Shape structural geometry is first produced in a registered, nonphysical
two-dimensional coordinate space.

The complete Shape envelope uses the canonical registered coordinate
extent:

```text
X = -0.5 through +0.5
Y = -0.5 through +0.5
```

The Shape origin is therefore:

```text
X = 0
Y = 0
```

and represents the center of the Shape.

For the supported geometries:

```text
circle   -> diameter 1.0, centered at the origin
square   -> 1.0 × 1.0, centered at the origin
polygon  -> maximum X/Y extent 1.0, centered at the origin
```

Regular polygon geometry is centered at the origin and uniformly
normalized after rotation so that its greatest X/Y extent is:

```text
1.0
```

Normalization does not stretch the polygon or otherwise change its
proportions.

The other X/Y extent may be less than `1.0` depending on polygon side
count and rotation.

The registered coordinate system establishes geometry, registration, and
relative spatial relationships.

It does not assign physical millimeter dimensions.

In particular:

```text
shape_size
```

does not change the registered outer extent of the Shape.

Changing `shape_size` changes the later physical dimensionalization of
the registered geometry rather than changing the registered geometry's
coordinate envelope.

## Structural Geometry

The `structure` stage produces registered structural Shape geometry.

Structural geometry is determined by Shape geometry policy such as:

```text
shape_geometry
shape_sides
shape_rotation
```

`shape_sides` and `shape_rotation` participate in structural geometry
only when:

```text
shape_geometry = "polygon"
```

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

```text
shape_geometry
```

including the configured side count and rotation when polygon geometry
is selected.

The complete Shape outline is established by the registered structural
geometry.

The physical thickness of the base is determined by:

```text
shape_base_raise
```

The dimensionalized base extends from:

```text
Z = 0
```

through:

```text
Z = shape_base_raise
```

Base thickness therefore belongs to physical dimensionalization rather
than to the registered two-dimensional structural representation.

## Color

Shape-owned structural and fill components have physical printing-color
assignments applied during Shape Package.

The base color is controlled by:

```text
shape_base_color
```

The default base color is:

```text
white
```

Incorporated Artwork may optionally have Shape-owned fill geometry.

Artwork-fill participation and physical height are controlled by:

```text
shape_artwork_fill_raise
```

Artwork-fill color is controlled independently by:

```text
shape_artwork_fill_color
```

The default Artwork-fill color is the resolved base color:

```text
shape_artwork_fill_color = shape_base_color
```

The fill-color default is therefore derived from the resolved value of
`shape_base_color` rather than being an independent literal color
default.

An explicitly configured Artwork-fill color overrides this derived
default.

`shape_artwork_fill_color` does not determine whether Artwork fill
geometry exists. Fill participation is determined solely by
`shape_artwork_fill_raise`.

Shape-owned component physical colors are
packaging policy. Shape Structure, Compose, and Extrude preserve the
component identity needed for downstream color assignment but do not
assign these physical colors.

Incorporated registered Artwork follows a different color contract. Its
color layers retain logical Artifact-color identity from the consumed
Artwork Vector product through Shape composition and physical extrusion.

Shape Compose and Shape Extrude do not assign physical printer colors to
those incorporated Artwork layers.

Physical printer-color assignment for incorporated Artwork occurs during
Shape Package. The `printer_colors` configuration is used as the
candidate physical printer-color assignment for the logical
Artifact-color layers represented in the incorporated Artwork. Package
resolves the one-to-one assignment and applies the resulting physical
printer colors to the packaged Artwork components.

`shape_artwork_fill_color` does not determine the physical printer
colors of incorporated registered Artwork. It applies only to
Shape-owned fill geometry.

Shape-owned physical color policy and incorporated Artwork
Artifact-color identity are therefore intentionally different concepts.

Shape-owned components receive their physical
colors during Package according to Shape color policy; incorporated
Artwork preserves the logical color identity supplied by Artwork until
Package resolves its physical printer assignment.

Color assignment does not determine structural geometry, component
partitioning, Feature participation, or Artwork-fill participation.

Likewise, structural partitioning and component participation do not
determine color assignment.

A color assigned to geometry that does not produce a corresponding
physical component has no effect on the produced artifact.

## Artwork

Artwork is optional.

A Shape without Artwork is a complete valid artifact.

Shape does not consume an Artwork source PNG and does not require a
completed standalone Artwork 3MF.

Shape consumes registered Artwork produced as an intermediate product by
the `artwork` model.

The initial Shape model consumes the registered vector representation
defined by the Artwork model.

Artwork components remain registered with one another when consumed by
Shape.

Each consumed Artwork color layer retains its logical Artifact-color
identity. The registered Artwork dependency does not require or carry a
standalone Artwork Package printer assignment into Shape.

## Artwork Dependency

Registered Artwork is supplied through the normal artifact
product-dependency mechanism.

Shape depends on the Artwork product it consumes, not on the completed
Artwork artifact.

For the current Artwork model, consuming registered vector Artwork
requires the upstream dependency:

```text
artwork/prepare
      ↓
artwork/raster
      ↓
artwork/vector
      ↓
    shape
```

Artwork stages after the consumed vector product are not prerequisites.

In particular, Shape does not require:

```text
artwork/extrude
artwork/package
```

to consume registered vector Artwork.

Shape consumes the declared Artwork manifest rather than discovering
dynamic Artwork components by scanning generated directories.

## Registered Artwork Coordinate Space

Registered Artwork may use a different coordinate extent from registered
Shape geometry.

For example, Artwork may have a registered extent derived from its
vectorization coordinate system while Shape uses its canonical:

```text
-0.5 through +0.5
```

registered envelope.

There is no requirement that one Artwork registered unit equal one Shape
registered unit.

The relationship between the two registered coordinate spaces is
established by the Shape composition transformation.

All components belonging to one registered Artwork collection share the
same Artwork coordinate system and receive the same transformation into
registered Shape space.

## Artwork Placement

Registered Artwork is placed within the registered Shape interior
region.

Shape uses one geometry-independent Artwork placement rule for every
supported Shape geometry.

The Artwork placement region is the largest circle centered at the
registered Shape origin that is wholly contained within the available
registered Shape interior region.

The placement circle is computed from the registered interior boundary.

The same computation is used regardless of whether the Shape geometry is
a circle, square, or regular polygon.

Registered Artwork is:

- centered within the Artwork placement region;
- uniformly scaled to the largest size at which its authoritative Artwork
  envelope remains contained within the Artwork placement region;

- aspect-ratio preserving;
- not stretched;
- not cropped merely to increase its fitted size.

The authoritative Artwork envelope determines Artwork occupancy for
fitting.

Shape does not infer Artwork occupancy from the independent bounds of
its individual color components.

The transformation from registered Artwork space into registered Shape
space is derived from the Artwork collection's common registered extent
and the computed Artwork placement region.

All registered Artwork color layers receive the same transformation so
that their registration is preserved.

## Registered Composition

Shape composition operates on registered geometry.

The structural Shape geometry and any incorporated registered Artwork
remain nonphysical through composition.

Conceptually:

```text
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
```

Composition establishes the spatial relationship between structural
Shape geometry and incorporated Artwork.

When Artwork is present, its registered coordinate system is transformed
into registered Shape coordinate space.

Composition does not assign the final physical X/Y dimensions of the
Shape.

Physical Shape policy may nevertheless be used to derive relative
registered-space relationships required for composition. Participating Features
may define such relationships within their Feature contracts.

Composition retains sufficient semantic component identity to support
downstream physical dimensionalization and packaging. Incorporated
Artwork retains logical Artifact-color identity; composition does not
resolve that identity to physical printer colors.

The composed result similarly retains sufficient Artwork component
identity to allow different structural and Artwork components to receive
their appropriate physical Z semantics and to remain independently
printable where required. Incorporated Artwork color layers retain their
logical Artifact-color identity through this stage.

## Physical Dimensionalization

Physical dimensionalization occurs after registered composition.

The Shape extrusion boundary converts composed registered geometry into
physical manufacturing geometry.

Conceptually:

```text
registered composition
          │
          ▼
       extrude
          │
          ▼
 physical geometry
```

At this boundary:

```text
shape_size
```

determines the overall physical X/Y extent of the Shape.

The canonical registered maximum Shape extent of `1.0` therefore
corresponds to:

```text
shape_size
```

millimeters in physical space.

For example:

```text
shape_size = 100
```

establishes:

```text
1.0 registered Shape unit = 100 mm
```

for dimensionalization.

A registered Artwork component occupying 0.8 Shape units across
therefore occupies 80 mm when incorporated into a 100 mm Shape.

Changing `shape_size` changes the physical size of the composed geometry
without changing its registered spatial relationships.

Physical Z dimensions are introduced at the dimensionalization boundary
according to the semantic role of each component.

These dimensions include:

```text
shape_base_raise
shape_outer_ridge_width
shape_outer_ridge_raise
shape_artwork_raise
```

and the defined Z policy for optional Artwork fill.

Optional Features apply their own dimensionalization and component-partitioning semantics at this boundary as defined by the applicable Feature contract.

Physical dimensionalization does not resolve incorporated Artwork to
physical printer colors. Extruded incorporated Artwork products preserve
logical Artifact-color identity for downstream Package assignment.

## Artwork Dimensionalization

Registered Artwork does not carry a predetermined physical X/Y size into
Shape.

Shape determines the physical size of incorporated Artwork from its
placement within registered Shape space and the later dimensionalization
of that Shape.

The standalone Artwork parameter:

```text
artwork_size
```

does not determine Artwork size within Shape.

For example, if registered Artwork is fitted to occupy 0.8 of the Shape
width and:

```text
shape_size = 100
```

the dimensionalized Artwork width is:

```text
80 mm
```

The same registered composition dimensionalized with:

```text
shape_size = 75
```

produces an Artwork width of:

```text
60 mm
```

without changing the registered Artwork-to-Shape placement.

Shape is therefore responsible for the physical size, placement, and
dimensionalization of Artwork incorporated into the Shape.

Shape also owns the physical Z dimensionalization of incorporated
Artwork.

The physical raise of incorporated Artwork is controlled by:

```text
shape_artwork_raise
```

`shape_artwork_raise` is a physical dimension measured in millimeters.

Its default value is:

```text
1 mm
```

Incorporated Artwork is raised on top of the Shape base.

The bottom surface of every incorporated Artwork component is located
at:

```text
Z = shape_base_raise
```

and its top surface is located at:

```text
Z = shape_base_raise + shape_artwork_raise
```

`shape_artwork_raise` must be greater than zero when Artwork is
incorporated.

All incorporated Artwork color components receive the same physical Z
dimensionalization.

The standalone Artwork parameter:

```text
artwork_raise
```

does not determine the physical Z dimensions of Artwork incorporated
into Shape.

Shape may optionally fill the portion of the registered interior region
outside the transformed Artwork envelope.

Artwork-fill existence and physical height are determined solely by:

```text
shape_artwork_fill_raise
```

When:

```text
shape_artwork_fill_raise > 0
```

Artwork fill participates.

When:

```text
shape_artwork_fill_raise <= 0
```

no Artwork fill geometry is produced.

The default Artwork-fill raise is:

```text
0 mm
```

When Artwork fill participates, the registered fill region is:

```text
registered Shape interior region
    minus
transformed registered Artwork envelope
```

The Artwork envelope is therefore the boundary between incorporated
Artwork occupancy and Shape-owned Artwork fill geometry.

Shape does not determine the fill boundary by independently inspecting
the bounds of individual Artwork color components.

Artwork fill begins on top of the Shape base.

Its bottom surface is located at:

```text
Z = shape_base_raise
```

and its top surface is located at:

```text
Z = shape_base_raise + shape_artwork_fill_raise
```

Artwork fill therefore has physical height determined independently from
incorporated Artwork.

`shape_artwork_fill_color` does not determine Artwork-fill participation
or physical geometry. When Artwork fill participates, its physical color
is assigned during Shape Package and defaults to the resolved
`shape_base_color` when no explicit fill color is configured.

When Artwork fill does not exist, only the incorporated Artwork
components are raised above the base; the remainder of the interior
region remains at the base top.

Artwork fill is a distinct semantic component from the structural base
even when its resolved color is equal to the base color.

## Coordinate-Space Boundaries

Shape distinguishes registered geometry from physical manufacturing
geometry.

Conceptually:

```text
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
```

The registered Shape coordinate system is the common coordinate system
used to establish spatial relationships between structural Shape
geometry and incorporated Artwork.

Physical parameters may inform relative relationships within registered
Shape space when necessary, including registered-space relationships required by
participating Features.

Such calculations do not make the registered coordinate system physical.

Final physical X/Y dimensionalization occurs only at the downstream
dimensionalization boundary.

## Parameters

The initial Shape model defines:

```text
shape_geometry
shape_sides
shape_rotation
shape_size
shape_base_raise
shape_base_color
shape_outer_ridge_width
shape_outer_ridge_raise
shape_outer_ridge_style
shape_outer_ridge_color
shape_inner_ridge_width
shape_inner_ridge_raise
shape_inner_to_outer_ridge_dist
shape_inner_ridge_color
shape_artwork_raise
shape_artwork_fill_raise
shape_artwork_fill_color
```

`shape_geometry` selects the structural geometry.

Its supported values are:

```text
circle
square
polygon
```

`shape_sides` selects the number of sides when:

```text
shape_geometry = "polygon"
```

Its default is:

```text
8
```

and its minimum valid value is:

```text
3
```

`shape_rotation` selects the counterclockwise polygon rotation in
degrees.

Its default is:

```text
0 degrees
```

At zero degrees, a polygon has one vertex centered on the positive Y
axis.

`shape_sides` and `shape_rotation` do not alter circle or square
geometry.

The `shape_outer_ridge_*` parameters are Feature parameters. Their participation,
defaults, validation, dimensional semantics, structural style, and color policy are
defined only by the Outer Ridge Feature contract.

The `shape_inner_ridge_*` parameters and
`shape_inner_to_outer_ridge_dist` are Feature parameters. Their
participation, defaults, validation, dimensional semantics, positioning,
and color policy are defined by the Inner Ridge Feature contract.

`shape_base_color` selects the base printing color.

Its default is:

```text
white
```

`shape_artwork_raise` determines the physical height of Artwork
incorporated into Shape above the top surface of the Shape base.

Its default is:

```text
1 mm
```

`shape_artwork_raise` must be greater than zero when Artwork is
incorporated.

When Artwork is not incorporated, `shape_artwork_raise` does not cause
Artwork geometry to be produced.

`shape_artwork_fill_raise` determines whether Shape-owned Artwork fill
participates and determines its physical height above the top surface of
the Shape base.

Its default is:

```text
0 mm
```

Artwork fill participates when:

```text
shape_artwork_fill_raise > 0
```

and does not participate when:

```text
shape_artwork_fill_raise <= 0
```

`shape_artwork_fill_color` selects the physical printing color for
participating Shape-owned Artwork fill.

Its default is the resolved value of:

```text
shape_base_color
```

An explicitly configured `shape_artwork_fill_color` overrides this
derived default.

`shape_artwork_fill_color` does not determine whether Artwork fill
participates.

The dimensional parameters are:

```text
shape_size
shape_base_raise
shape_outer_ridge_width
shape_outer_ridge_raise
shape_inner_ridge_width
shape_inner_ridge_raise
shape_inner_to_outer_ridge_dist
shape_artwork_raise
shape_artwork_fill_raise
```

and are physical dimensions measured in millimeters.

`shape_sides` is a dimensionless structural geometry parameter.

`shape_rotation` is an angular structural geometry parameter measured in
degrees.

Physical parameters do not imply that every stage consuming Shape policy
operates in physical coordinate space.

A stage operating on registered geometry may use physical parameters to
derive relative registered-space relationships when those relationships
are required before dimensionalization.

Final physical dimensionalization remains the responsibility of the
Shape dimensionalization boundary.

The packaging parameters are:

```text
printer_colors
shape_base_color
shape_outer_ridge_color
shape_inner_ridge_color
shape_artwork_fill_color
```

`printer_colors` provides the candidate physical printer colors used by
Shape Package to resolve the logical Artifact-color layers of
incorporated Artwork.

`shape_base_color` and `shape_artwork_fill_color` provide model-wide
physical color policy for Shape-owned components.
`shape_outer_ridge_color` and `shape_inner_ridge_color` are Feature
packaging parameters whose semantics are defined by their respective
Feature contracts.

These parameters are packaging policy, not structural, composition, or
extrusion geometry policy. Changing only physical color policy does not
by itself require Shape Structure, Compose, or Extrude geometry to
change.

Artwork dependency binding is not represented by a filesystem-path
parameter.

## Packaging

Physical Shape components are packaged after dimensionalization.

Package is the physical color-assignment boundary for Shape.

Shape-owned Base and Artwork-fill components retain semantic component identity
through dimensionalization. Package applies their physical printing colors according
to `shape_base_color` and `shape_artwork_fill_color`.

The resolved Artwork-fill color defaults to the resolved base color when
no explicit Artwork-fill color is configured.

Registered Artwork enters Shape with logical Artifact-color identity,
and that identity is preserved through Compose and Extrude. Package
resolves those logical Artwork colors against `printer_colors` and
applies the selected physical printer colors to the packaged Artwork
components.

Packaging preserves independently printable and independently assignable
components where required by structural or color semantics.

Participating Features preserve any independently printable or independently
colored component identity required by their Feature contracts.

Incorporated Artwork color components likewise remain suitable for
multicolor printing after their logical Artifact-color identities have
been resolved to physical printer colors.

Packaged 3MF component identity preserves both the semantic role of each
physical component and its resolved printing-color identity.

Component names use the form:

```text
<component-role> - <color>
```

For example:

```text
base - cold-white
ridge - red
artwork - black
artwork - gold
```

The packaged component name does not depend on an intermediate component
ordinal when semantic role and color provide sufficient identity.

Component naming does not determine color assignment. The component's
resolved color and RGB representation remain explicit packaging
metadata.

Packaging does not determine Shape geometry, Feature geometry or partitioning,
Artwork-fill participation or height,
Artwork fitting, or physical dimensionalization. Those semantics must
already be established before packaging.

Packaging does determine physical color assignment. For Shape-owned
components, Package applies Shape color policy. For incorporated
Artwork, Package resolves logical Artifact-color identity to physical
printer colors using `printer_colors`.

## Features

Features are optional capabilities of the Shape model.

A Shape realization may participate in zero or more Features according to the
effective parameter values defined by each Feature.

Features are distinct from intrinsic Shape properties. In particular, every Shape
has structural geometry and a Base; those required model properties are not optional
Features.

Each Feature subsection is the authoritative semantic definition of that Feature.
Feature-specific parameters, participation conditions, validation, geometry, physical
dimensions, color and material behavior, interactions with other model behavior, and
product participation are defined within that Feature subsection.

Feature-specific semantics are not duplicated in unrelated model sections. A stage
may operate on participating Features without owning their semantics.

### Outer Ridge

The Outer Ridge Feature provides an optional perimeter ridge within the complete assembled Shape envelope.

#### Parameters and Participation

A Shape may contain an outer ridge.

The ridge is controlled by:

```text
shape_outer_ridge_width
shape_outer_ridge_raise
shape_outer_ridge_style
shape_outer_ridge_color
```

The supported ridge styles are:

```text
integrated
separate
```

The ridge follows the boundary of the selected Shape geometry.

For polygon geometry, the ridge follows the configured regular polygon
after its side count, rotation, and registered normalization have been
applied.

Ridge width is measured inward from the outer Shape boundary.

For polygon geometry, ridge width is the perpendicular distance from
each outer polygon edge to its corresponding inner ridge edge.

The inner ridge boundary therefore consists of edges parallel to the
corresponding outer polygon edges.

The ridge does not increase:

```text
shape_size
```

Ridge existence is determined solely by:

```text
shape_outer_ridge_width
```

An outer ridge exists when:

```text
shape_outer_ridge_width > 0
```

An outer ridge does not exist when:

```text
shape_outer_ridge_width = 0
```

A negative outer-ridge width is invalid.

When the ridge does not exist, ridge raise, style, and color do not
alter the produced ridge geometry.

`shape_outer_ridge_raise` does not determine whether a ridge exists.

The default outer-ridge raise is:

```text
1 mm
```

for both integrated and separate ridge styles.

Ridge raise is measured relative to the top surface of the base.

The complete assembled ridge height is therefore:

```text
shape_base_raise + shape_outer_ridge_raise
```

for both ridge styles.

Ridge raise may be positive, zero, or negative.

A positive ridge raise places the ridge top above the base top.

A zero ridge raise places the ridge top flush with the base top.

A negative ridge raise places the ridge top below the base top.

The minimum valid ridge raise is:

```text
-shape_base_raise
```

so that:

```text
shape_base_raise + shape_outer_ridge_raise >= 0
```

A ridge raise less than:

```text
-shape_base_raise
```

is invalid because it would imply a negative physical ridge height.

`shape_outer_ridge_width` is a physical dimension measured in
millimeters.

When ridge geometry must participate in registered composition before
physical dimensionalization, its physical width is converted to a
relative registered-space width using the relationship between:

```text
shape_outer_ridge_width
shape_size
```

For example, a 5 mm ridge on a 100 mm Shape occupies 0.05 registered
Shape units inward from the corresponding outer boundary.

For polygon geometry, this registered inset is measured perpendicular to
each polygon edge rather than by subtracting the same value from each
vertex coordinate or circumradius.

This conversion does not assign physical dimensions to the registered
coordinate system. It expresses physical Shape policy as a relative
relationship within registered Shape space.

#### Integrated Outer Ridge

With:

```text
shape_outer_ridge_style = integrated
```

the ridge is structurally integrated with the base.

The base retains the complete Shape X/Y envelope.

The ridge occupies the perimeter region between:

```text
the complete Shape outer boundary
```

and:

```text
the ridge inner boundary
```

The dimensionalized integrated ridge is partitioned according to its
relationship to the top of the base.

The base material occupies the integrated ridge region from:

```text
Z = 0
```

through the lesser of:

```text
shape_base_raise
```

and:

```text
shape_base_raise + shape_outer_ridge_raise
```

When:

```text
shape_outer_ridge_raise > 0
```

the base retains the complete Shape X/Y envelope through:

```text
Z = shape_base_raise
```

and the portion of the ridge above the base occupies:

```text
Z = shape_base_raise
```

through:

```text
Z = shape_base_raise + shape_outer_ridge_raise
```

Only this portion above the base is represented using the independently
assigned outer-ridge color.

Conceptually, for:

```text
shape_base_raise = 2
shape_outer_ridge_raise = 1
```

the integrated structure has:

```text
base -> Z = 0 through 2
ridge color -> perimeter from Z = 2 through 3
```

When:

```text
shape_outer_ridge_raise = 0
```

the ridge top is flush with the top of the base.

The ridge's registered X/Y region continues to exist, but there is no
physical ridge-color volume above the base. The complete dimensionalized
structure is therefore base material through:

```text
Z = shape_base_raise
```

When:

```text
shape_outer_ridge_raise < 0
```

the ridge top lies below the top surface of the base while the ridge's
registered X/Y region continues to exist.

The integrated perimeter then occupies base material from:

```text
Z = 0
```

through:

```text
Z = shape_base_raise + shape_outer_ridge_raise
```

while the interior base continues through:

```text
Z = shape_base_raise
```

No independently colored ridge volume is produced because no portion of
the integrated ridge extends above the base top.

Conceptually, for:

```text
shape_base_raise = 2
shape_outer_ridge_raise = -0.5
```

the integrated structure has:

```text
interior base -> Z = 0 through 2
perimeter base -> Z = 0 through 1.5
ridge-color volume -> none
```

The base and integrated ridge belong to the same assembled structural
geometry.

Their color assignments remain independent semantic properties. An
integrated ridge may therefore be assigned a color different from the
base, but that ridge color applies only to physical ridge geometry above
the base top.

#### Separate Outer Ridge

With:

```text
shape_outer_ridge_style = separate
```

the ridge is an independently printable structural component.

The ridge retains the complete Shape outer boundary.

Its inner boundary is inset from that outer boundary by:

```text
shape_outer_ridge_width
```

The base outer boundary becomes the ridge inner boundary.

The base and ridge therefore occupy adjacent, nonoverlapping X/Y
regions.

The separately printable base occupies:

```text
Z = 0
```

through:

```text
Z = shape_base_raise
```

The separately printable ridge occupies:

```text
Z = 0
```

through:

```text
Z = shape_base_raise + shape_outer_ridge_raise
```

The separate ridge therefore uses the same complete assembled ridge
height as the corresponding integrated ridge.

Conceptually, for:

```text
shape_base_raise = 2
shape_outer_ridge_raise = 1
```

the separate structure has:

```text
base   -> Z = 0 through 2
ridge  -> Z = 0 through 3
```

For:

```text
shape_base_raise = 2
shape_outer_ridge_raise = 0
```

the separate structure has:

```text
base   -> Z = 0 through 2
ridge  -> Z = 0 through 2
```

For:

```text
shape_base_raise = 2
shape_outer_ridge_raise = -0.5
```

the separate structure has:

```text
base   -> Z = 0 through 2
ridge  -> Z = 0 through 1.5
```

At the minimum valid raise:

```text
shape_outer_ridge_raise = -shape_base_raise
```

the separate ridge has zero physical height.

The ridge remains semantically defined by its nonzero width even though
its dimensionalized physical volume is zero.

The separate ridge may be assigned a printing color independently from
the base.

Its default color is the base color.

#### Ridge Equivalence

For otherwise identical Shape parameters, changing:

```text
shape_outer_ridge_style
```

between:

```text
integrated
separate
```

does not change:

- the complete Shape outer envelope;
- the ridge outer boundary;
- the ridge inner boundary;
- the registered interior region;
- the complete assembled ridge height;
- the intended complete assembled physical geometry.

It changes the partitioning of that geometry into structural regions and
independently printable components.

For example, for a 100 mm square with:

```text
shape_outer_ridge_width = 5
```

both ridge styles have:

```text
complete outer envelope = 100 mm × 100 mm
ridge inner envelope    = 90 mm × 90 mm
```

With an integrated ridge:

```text
base outer envelope = 100 mm × 100 mm
```

because the ridge region is integrated with the full-envelope base.

With a separate ridge:

```text
base outer envelope = 90 mm × 90 mm
```

because the independently printable ridge occupies the surrounding 5 mm
perimeter region.

The union of the separate base and separate ridge corresponds to the
same intended assembled structural geometry as the integrated
construction for the same dimensional parameters.

#### Ridge Color

The outer ridge has a color assignment independent from its structural
style.

The ridge color is controlled by:

```text
shape_outer_ridge_color
```

The default outer-ridge color is the base color.

A ridge may be assigned a color different from the base regardless of
whether its style is:

```text
integrated
```

or:

```text
separate
```

Ridge style therefore describes structural partitioning and does not
determine color.

Likewise, color does not determine whether a ridge is structurally
integrated or separate.

When the ridge does not exist because:

```text
shape_outer_ridge_width = 0
```

its color has no effect on produced ridge geometry.

#### Interior Region

When the Outer Ridge participates, its inside boundary is available as a
registered Shape interior boundary.

Outer-Ridge raise and structural style do not change this registered boundary.

Other participating Features may define a more interior boundary according to
their own Feature contracts.

The resulting registered interior region provides the Shape coordinate space
into which registered Artwork is fitted.

Ridge existence for purposes of determining the interior region depends
only on:

```text
shape_outer_ridge_width > 0
```

The same ridge inner boundary is used for integrated and separate ridge
styles.

Changing ridge style therefore does not change the registered area
available for Artwork.

Changing ridge raise likewise does not change the registered area
available for Artwork.

An outer ridge reduces the registered area available for Artwork without
changing the registered outer Shape envelope or the physical value of:

```text
shape_size
```

The registered interior region provides the common Shape coordinate
space into which registered Artwork is fitted.

#### Interaction With Base

Without a separately printable Outer Ridge, the Base occupies the complete Shape X/Y envelope.

With a separately printable Outer Ridge, the Base occupies the region inside the ridge's inner boundary. The separately printable ridge therefore reduces the X/Y extent of the Base component without reducing the complete assembled Shape envelope.

The Base may be assigned a printing color. The Outer Ridge defaults to the Base color but may be assigned a different color independently.

#### Outer Ridge Invariants

A conforming Outer Ridge Feature satisfies the following:

1. An Outer Ridge follows the selected Shape boundary.
2. Outer-Ridge width is measured inward from the complete Shape boundary.
3. For polygon geometry, Outer-Ridge width is the perpendicular distance between corresponding outer and inner polygon edges.
4. The Outer Ridge lies within the Shape boundary and does not increase `shape_size`.
5. Outer-Ridge existence is determined solely by `shape_outer_ridge_width`.
6. Zero Outer-Ridge width disables the Outer Ridge.
7. Positive Outer-Ridge width defines an Outer Ridge regardless of `shape_outer_ridge_raise`.
8. Negative Outer-Ridge width is invalid.
9. The default Outer-Ridge raise is 1 mm for both ridge styles.
10. Outer-Ridge raise is measured relative to the top of the Base.
11. The complete assembled ridge height is `shape_base_raise + shape_outer_ridge_raise` for both ridge styles.
12. Outer-Ridge raise may be zero.
13. Outer-Ridge raise may be negative down to `-shape_base_raise`.
14. Outer-Ridge raise less than `-shape_base_raise` is invalid.
15. An existing Outer Ridge may be integrated with the Base or partitioned as a separately printable structural component.
16. With an integrated Outer Ridge, the Base retains the complete Shape X/Y envelope.
17. With a separate Outer Ridge, the ridge retains the complete Shape outer boundary and the Base outer boundary becomes the ridge inner boundary.
18. A separate Outer Ridge and its Base occupy adjacent, nonoverlapping X/Y regions.
19. A separate Outer Ridge occupies Z from zero through `shape_base_raise + shape_outer_ridge_raise`.
20. Integrated and separate ridge styles preserve the same complete Shape envelope, ridge boundaries, registered interior region, and intended assembled ridge height for otherwise identical Shape parameters.
21. The innermost existing ridge boundary defines the available registered interior region; when no ridge exists, the registered Shape boundary defines the interior region.
22. Ridge raise does not change the registered ridge inner boundary or registered interior region.
23. The default Outer-Ridge color is the resolved Base color.
24. An explicitly configured Outer-Ridge color overrides its derived Base-color default.
25. Outer-Ridge color is independent from Outer-Ridge structural style.
26. An integrated Outer Ridge may have a color different from the Base.
27. A separate Outer Ridge may have a color different from the Base.
28. Outer-Ridge style does not change the physical Z origin or raise of incorporated Artwork or Artwork fill.
29. Shape Extrude does not assign physical color to Outer-Ridge components.
30. Shape Package applies the Outer Ridge's physical color policy.
31. Changing only `shape_outer_ridge_color` does not by itself change Shape Structure, Compose, or Extrude geometry.

### Inner Ridge

The Inner Ridge Feature provides an optional ridge inset from the perimeter of the Shape.

The Inner Ridge is a Shape-owned component that layers on top of the Base. Unlike a separate Outer Ridge, the Inner Ridge does not partition or reduce the X/Y extent of the Base.

#### Parameters and Participation

The Inner Ridge is controlled by:

```text
shape_inner_ridge_width
shape_inner_ridge_raise
shape_inner_to_outer_ridge_dist
shape_inner_ridge_color
```

Inner-Ridge existence is determined solely by:

```text
shape_inner_ridge_width
```

An Inner Ridge exists when:

```text
shape_inner_ridge_width > 0
```

The default is:

```text
0
```

 The Inner Ridge does not participate by default.


An Inner Ridge does not exist when:

```text
shape_inner_ridge_width = 0
```

A negative Inner-Ridge width is invalid.

When the Inner Ridge does not exist, its raise, position, and color do not cause Inner-Ridge geometry to be produced.

`shape_inner_ridge_raise` does not determine whether an Inner Ridge exists.

The Inner Ridge may participate whether or not an Outer Ridge exists.

#### Geometry

The Inner Ridge follows the boundary of the selected Shape geometry.

For circle geometry, the Inner Ridge is a concentric circular band.

For square geometry, the Inner Ridge follows the corresponding inset square boundary.

For polygon geometry, the Inner Ridge follows the configured regular polygon after its side count, rotation, and registered normalization have been applied.

Inner-Ridge width is measured inward from the outer boundary of the Inner Ridge.

For polygon geometry, Inner-Ridge width is the perpendicular distance from each outer Inner-Ridge edge to its corresponding inner Inner-Ridge edge.

The inner and outer boundaries of the Inner Ridge therefore follow the same Shape geometry and remain registered with the Shape.

`shape_inner_ridge_width` is a physical dimension measured in millimeters.

When Inner-Ridge geometry must participate in registered composition before physical dimensionalization, its physical dimensions are converted to relative registered-space relationships using `shape_size`.

This conversion does not assign physical dimensions to the registered coordinate system. It expresses physical Shape policy as relative relationships within registered Shape space.

#### Position

The position of the Inner Ridge is controlled by:

```text
shape_inner_to_outer_ridge_dist
```

`shape_inner_to_outer_ridge_dist` is a physical dimension measured in millimeters.

It must be greater than or equal to:

```text
0
```

The default value is:

```text
10
```

A negative `shape_inner_to_outer_ridge_dist` is invalid.

The reference boundary used to position the Inner Ridge depends on whether an Outer Ridge participates.

When an Outer Ridge exists, `shape_inner_to_outer_ridge_dist` is measured inward from:

```text
the inside boundary of the Outer Ridge
```

to:

```text
the outside boundary of the Inner Ridge
```

Conceptually:

```text
Shape boundary
│
│<-- Outer Ridge -->│
                    │<-- distance -->│
                                      │<-- Inner Ridge -->│
                    ↑                 ↑
             inside boundary    outside boundary
              of Outer Ridge     of Inner Ridge
```

When no Outer Ridge exists, `shape_inner_to_outer_ridge_dist` is measured inward from:

```text
the outside boundary of the Base
```

to:

```text
the outside boundary of the Inner Ridge
```

Conceptually:

```text
Shape/Base boundary
│
│<------ distance ------>│
                          │<-- Inner Ridge -->│
↑                         ↑
outside boundary     outside boundary
    of Base           of Inner Ridge
```

The Inner Ridge may therefore participate independently of Outer-Ridge participation.

A distance of zero is valid.

When an Outer Ridge exists and:

```text
shape_inner_to_outer_ridge_dist = 0
```

the outside boundary of the Inner Ridge is adjacent to the inside boundary of the Outer Ridge.

When no Outer Ridge exists and:

```text
shape_inner_to_outer_ridge_dist = 0
```

the outside boundary of the Inner Ridge coincides with the outside boundary of the Base.

A zero distance permits boundary adjacency but does not permit geometric overlap.

#### Raise

The physical raise of the Inner Ridge is controlled by:

```text
shape_inner_ridge_raise
```

`shape_inner_ridge_raise` is a physical dimension measured in millimeters relative to the top surface of the Base.

It must be greater than or equal to:

```text
0
```

The default value is:

```text
1
```


A negative Inner-Ridge raise is invalid.

A positive Inner-Ridge raise places the Inner-Ridge top above the Base top.

A zero Inner-Ridge raise places the Inner-Ridge top flush with the Base top.

When the Inner Ridge participates, its complete assembled height is:

```text
shape_base_raise + shape_inner_ridge_raise
```

The Inner Ridge layers on top of the Base.

The Base remains present beneath the Inner Ridge and retains its complete X/Y extent.

The Inner Ridge therefore behaves structurally like an integrated ridge rather than partitioning a separate X/Y region from the Base.

For:

```text
shape_inner_ridge_raise > 0
```

the Base occupies:

```text
Z = 0
```

through:

```text
Z = shape_base_raise
```

and the Inner-Ridge component occupies its registered X/Y region above the Base from:

```text
Z = shape_base_raise
```

through:

```text
Z = shape_base_raise + shape_inner_ridge_raise
```

For:

```text
shape_inner_ridge_raise = 0
```

the Inner Ridge remains semantically defined by its positive width even though it contributes no physical volume above the Base.

#### Interior Region

The Inner Ridge participates in determining the registered interior region available for incorporated Artwork.

The innermost participating ridge boundary defines the available registered Shape interior region.

When an Inner Ridge exists, the interior region is bounded by:

```text
the inside boundary of the Inner Ridge
```

When no Inner Ridge exists but an Outer Ridge exists, the interior region is bounded by:

```text
the inside boundary of the Outer Ridge
```

When neither an Inner Ridge nor an Outer Ridge exists, the interior region is bounded by:

```text
the outside boundary of the Base
```

Conceptually:

```text
if Inner Ridge exists:
    interior boundary = inside boundary of Inner Ridge
elif Outer Ridge exists:
    interior boundary = inside boundary of Outer Ridge
else:
    interior boundary = outside boundary of Base
```

Inner-Ridge raise does not change the registered Inner-Ridge boundaries or the registered interior region.

The resulting registered interior region provides the Shape coordinate space into which registered Artwork is fitted.

#### Ridge Color

The Inner Ridge has a physical printing-color assignment independent from its geometry.

The Inner-Ridge color is controlled by:

```text
shape_inner_ridge_color
```

The default Inner-Ridge color is the resolved Base color:

```text
shape_inner_ridge_color = shape_base_color
```

The default is derived from the resolved value of `shape_base_color` rather than being an independent literal color default.

An explicitly configured `shape_inner_ridge_color` overrides this derived default.

When the Inner Ridge does not participate because:

```text
shape_inner_ridge_width = 0
```

its color has no effect on the produced artifact.

Inner-Ridge color is packaging policy.

Shape Structure, Compose, and Extrude preserve the semantic component identity required for downstream Inner-Ridge color assignment but do not assign its physical printing color.

Shape Package applies the resolved Inner-Ridge physical color.

Changing only `shape_inner_ridge_color` does not by itself change Shape Structure, Compose, or Extrude geometry.

#### Interaction With Outer Ridge

Inner-Ridge participation is independent of Outer-Ridge participation.

An Inner Ridge may therefore exist:

- with an integrated Outer Ridge;
- with a separate Outer Ridge;
- without an Outer Ridge.

When an Outer Ridge participates, its inside boundary is the reference boundary from which `shape_inner_to_outer_ridge_dist` positions the outside boundary of the Inner Ridge.

The Outer-Ridge structural style does not change this positioning rule because integrated and separate Outer Ridges preserve the same Outer-Ridge boundaries for otherwise identical Shape parameters.

The Inner Ridge does not alter the Outer Ridge's outer boundary, inner boundary, width, raise, structural style, or color policy.

The Inner Ridge and Outer Ridge remain distinct semantic components.

#### Interaction With Base

The Inner Ridge layers on top of the Base.

It does not remove, partition, or reduce the Base X/Y geometry.

The Base remains present beneath the Inner Ridge.

The Inner Ridge may have a physical printing color different from the Base even though it is structurally layered on top of the Base.

#### Interaction With Artwork

When the Inner Ridge participates, its inside boundary becomes the available registered interior boundary used for Artwork placement.

The existing Shape Artwork-placement policy then operates within that reduced registered interior region.

The Inner Ridge does not otherwise alter the Artwork fitting algorithm, Artwork registration, Artwork physical raise, or Artwork-fill dimensionalization.

Inner-Ridge raise does not alter Artwork placement because Artwork placement is determined from the registered Inner-Ridge boundary rather than its physical Z height.

#### Product Participation

A participating Inner Ridge contributes Shape-owned geometry to the dimensionalized Shape.

The Inner Ridge remains a separate semantic component from the Base through Shape Extrude and Package.

Shape Extrude establishes its physical geometry and preserves its component identity but does not assign its physical printing color.

Shape Package applies the resolved `shape_inner_ridge_color`.

The Inner Ridge participates in the final packaged 3MF when its dimensionalized geometry has physical volume.

#### Inner Ridge Invariants

A conforming Inner Ridge Feature satisfies the following:

1. An Inner Ridge follows the selected Shape geometry.
2. Inner-Ridge participation is determined solely by `shape_inner_ridge_width`.
3. Zero Inner-Ridge width disables the Inner Ridge.
4. Positive Inner-Ridge width defines an Inner Ridge regardless of `shape_inner_ridge_raise`.
5. Negative Inner-Ridge width is invalid.
6. Inner-Ridge width is measured inward from the outside boundary of the Inner Ridge.
7. For polygon geometry, Inner-Ridge width is the perpendicular distance between corresponding outer and inner Inner-Ridge edges.
8. An Inner Ridge may participate whether or not an Outer Ridge participates.
9. `shape_inner_to_outer_ridge_dist` positions the outside boundary of the Inner Ridge.
10. When an Outer Ridge participates, `shape_inner_to_outer_ridge_dist` is measured from the inside boundary of the Outer Ridge to the outside boundary of the Inner Ridge.
11. When no Outer Ridge participates, `shape_inner_to_outer_ridge_dist` is measured from the outside boundary of the Base to the outside boundary of the Inner Ridge.
12. `shape_inner_to_outer_ridge_dist` must be greater than or equal to zero.
13. A zero `shape_inner_to_outer_ridge_dist` permits boundary adjacency but not geometric overlap.
14. `shape_inner_ridge_raise` is measured relative to the top of the Base.
15. `shape_inner_ridge_raise` must be greater than or equal to zero.
16. A zero Inner-Ridge raise is valid.
17. A negative Inner-Ridge raise is invalid.
18. The complete assembled Inner-Ridge height is `shape_base_raise + shape_inner_ridge_raise`.
19. The Inner Ridge layers on top of the Base and does not partition or reduce the Base X/Y geometry.
20. When an Inner Ridge participates, its inside boundary defines the available registered interior region.
21. When no Inner Ridge participates but an Outer Ridge participates, the Outer Ridge's inside boundary defines the available registered interior region.
22. When neither ridge participates, the outside boundary of the Base defines the available registered interior region.
23. Inner-Ridge raise does not change the registered Inner-Ridge boundaries or registered interior region.
24. The default Inner-Ridge color is the resolved Base color.
25. An explicitly configured `shape_inner_ridge_color` overrides its derived Base-color default.
26. Inner-Ridge color does not determine Inner-Ridge participation or geometry.
27. Shape Extrude does not assign physical color to Inner-Ridge geometry.
28. Shape Package applies the Inner Ridge's physical color policy.
29. Changing only `shape_inner_ridge_color` does not by itself change Shape Structure, Compose, or Extrude geometry.
30. The Inner Ridge and Outer Ridge remain distinct semantic components when both participate.
31. Outer-Ridge style does not change the Inner-Ridge positioning reference when an Outer Ridge participates.
32. Inner-Ridge participation does not otherwise change the existing Artwork fitting algorithm, Artwork registration, Artwork physical raise, or Artwork-fill dimensionalization.

### Border Labels

Border Labels are optional Shape-owned Features that place text along the perimeter of the Shape.

The Feature provides two independently participating components:

- `top_border_label`
- `bottom_border_label`

The two labels occupy the same physical lettering band and share the geometry and font-fitting rules defined below.

Each participating label remains a distinct semantic component through Shape composition, extrusion, and packaging. The two labels may therefore have independent extrusion dimensions and independent packaged colors.

Border Labels do not cause any other Shape Feature to participate.

In particular, Border Labels do not cause the Inner Ridge to participate. Inner Ridge participation remains determined solely by `shape_inner_ridge_width`.

#### Parameters

Border Labels use shared parameters for the geometry and typography that define their common lettering band.

The shared parameters are:

```text
shape_border_label_width
shape_border_label_max_glyph_height
shape_border_label_arc_degrees
shape_border_label_end_margin
shape_border_label_font_family
```

The Top Border Label additionally uses:

```text
shape_top_border_label_text
shape_top_border_label_raise
shape_top_border_label_color
```

The Bottom Border Label additionally uses:

```text
shape_bottom_border_label_text
shape_bottom_border_label_raise
shape_bottom_border_label_color
```

The resolved common glyph height is derived from the configured maximum glyph height and the text-fitting rules below. It is not independently configured.

#### Defaults

The Border Label parameters have the following defaults:

```text
shape_border_label_width = 1 mm
shape_border_label_max_glyph_height = 5 mm
shape_border_label_arc_degrees = 140 degrees
shape_border_label_end_margin = 1 mm
shape_border_label_font_family = "DejaVu Sans"

shape_top_border_label_text = ""
shape_top_border_label_raise = 1 mm
shape_top_border_label_color = shape_base_color

shape_bottom_border_label_text = ""
shape_bottom_border_label_raise = 1 mm
shape_bottom_border_label_color = shape_base_color
```

The default empty Top and Bottom Border Label text means that neither
Border Label participates by default.

The default Top and Bottom Border Label colors are derived from the
resolved value of shape_base_color rather than being independent
literal color defaults.

An explicitly configured shape_top_border_label_color or
shape_bottom_border_label_color overrides the corresponding derived
Base-color default.

#### Participation

The Top Border Label participates when `shape_top_border_label_text` contains non-whitespace text.

The Bottom Border Label participates when `shape_bottom_border_label_text` contains non-whitespace text.

The labels participate independently.

An absent Top Border Label does not prevent the Bottom Border Label from participating.

An absent Bottom Border Label does not prevent the Top Border Label from participating.

When neither label participates, Border Labels have no effect on Shape geometry or products.

#### Reference Boundary

Both Border Labels are positioned relative to the same outer reference boundary.

The reference boundary is:

```text
if Outer Ridge participates:
    inside boundary of Outer Ridge
else:
    outside boundary of Base
```

This rule is independent of `shape_outer_ridge_style`.

For otherwise identical Shape parameters, integrated and separate Outer Ridge styles preserve the same relevant ridge boundaries and therefore produce the same Border Label reference boundary.

#### Border Width

`shape_border_label_width` is a physical distance in millimeters.

It defines the clear border on both sides of the common lettering band.

It must be greater than or equal to zero.

The outer border extends inward from the reference boundary to the Bottom Border Label baseline.

The inner border extends inward from the Top Border Label baseline toward the Shape interior.

#### Common Glyph Height

The Top Border Label and Bottom Border Label share one resolved glyph height and one common font setting.

`shape_border_label_max_glyph_height` defines the maximum physical glyph-height allocation permitted for the common lettering band.

It must be greater than zero when either Border Label participates.

The resolved glyph height must not exceed `shape_border_label_max_glyph_height`.

Both labels are measured before fitting.

The common font setting is chosen so that both participating labels fit within their permitted paths.

If both labels fit at the configured maximum glyph height, the configured maximum is used.

If either label does not fit, the common glyph height is reduced until both participating labels fit.

The more constrained participating label therefore determines the common fitted height.

A shorter label is not stretched to consume its complete available path.

When only one Border Label participates, the common glyph height is fitted using that participating label.

Rendered glyph bounds may differ between the Top and Bottom Border Labels because different character strings can have different font metrics. Both labels nevertheless use the same resolved common font setting and fit within the same physical glyph-height allocation.

#### Baseline Paths

The Top and Bottom Border Labels occupy the same physical lettering band but use different baseline paths.

Moving inward from the reference boundary:

```text
reference boundary
    ↓ shape_border_label_width
bottom_border_label baseline
    ↓ resolved common glyph height
top_border_label baseline
    ↓ shape_border_label_width
inner boundary of Border Labels
```

Therefore:

```text
bottom_border_label baseline
    =
    reference boundary
    - shape_border_label_width
```

and:

```text
top_border_label baseline
    =
    reference boundary
    - shape_border_label_width
    - resolved common glyph height
```

These expressions describe inward geometric offsets from the applicable Shape boundary rather than arithmetic on a particular coordinate representation.

The two baseline paths follow the literal Shape perimeter at their respective inward offsets.

For a circular Shape, the paths are concentric circular arcs.

For a square Shape, the paths follow the corresponding inset square perimeter.

For a polygon Shape, the paths follow the corresponding inset polygon perimeter after the configured polygon sides, rotation, and Shape normalization have been applied.

The initial implementation may focus on circular Shapes, but the normative geometry is defined in terms of literal Shape-perimeter offsets rather than an inherently circular representation.

#### Top Border Label Path

The Top Border Label is centered on the top axis of the Shape.

For a circular Shape, top-dead-center is zero degrees.

The Top Border Label path traverses from the upper-left toward the upper-right so that the text reads normally from left to right.

The rendered glyphs extend inward from the Top Border Label baseline into the common lettering band.

#### Bottom Border Label Path

The Bottom Border Label is centered on the bottom axis of the Shape.

For a circular Shape, bottom-dead-center is 180 degrees.

The Bottom Border Label path traverses in the opposite direction from the Top Border Label path so that the text remains upright and reads normally from left to right.

The rendered glyphs extend outward from the Bottom Border Label baseline into the same common lettering band occupied by the Top Border Label.

#### Font Measurement

Border Label fitting uses rendered font measurements rather than assuming that an SVG or CSS font size is equal to physical glyph height.

Text measurement produces scale-independent font metrics sufficient to determine:

- rendered text width;
- rendered glyph height;
- the relationship between font size and rendered glyph height;
- glyph extent above the text baseline;
- glyph extent below the text baseline.

These metrics may be measured once for each participating label and subsequently scaled arithmetically while fitting.

Baseline-relative glyph measurements are used to place rendered glyph bounds correctly within the common lettering band.

Font-size values used by an SVG or other intermediate representation are implementation details and are not Shape physical parameters.

#### Maximum Label Span

`shape_border_label_arc_degrees` defines the maximum permitted span for each Border Label.

It must be greater than zero and less than 180 degrees.

For a circular Shape, this represents:

```text
Top Border Label:
    -70 degrees through +70 degrees
    around top-dead-center

Bottom Border Label:
    corresponding centered span
    around bottom-dead-center
```

The same conceptual maximum-span constraint applies to non-circular Shape perimeters. The exact mapping of that span onto square and polygon perimeter paths may be implemented by the geometry-specific path representation while preserving the literal Shape-perimeter requirement.

#### End Margin

`shape_border_label_end_margin` reserves unused physical path length at both ends of the maximum permitted label path.

It must be greater than or equal to zero.

For a circular Shape, the usable path length is:

```text
baseline radius
× radians(shape_border_label_arc_degrees)
- 2 × shape_border_label_end_margin
```

The equivalent physical end-margin constraint applies to non-circular Shape paths.

End margins constrain fitting but are not included in the angular or path extent occupied by the rendered text itself.

#### Text Fitting

Each participating label must fit within the usable length of its corresponding baseline path.

The fitting process:

1. measures each participating label using the configured font family;
2. determines the common font setting corresponding to the candidate glyph-height allocation;
3. derives the Top and Bottom baseline paths for that candidate height;
4. determines the usable path length after the maximum-span and end-margin constraints;
5. determines the rendered path length required by each participating label;
6. accepts the candidate only when every participating label fits.

The configured maximum glyph height is preferred whenever it fits.

Otherwise, the fitting process reduces the common glyph height until all participating labels fit.

Fitting changes glyph height uniformly. It does not horizontally stretch, compress, or otherwise distort either label to fill its available path.

A configuration that cannot produce a positive usable glyph height is invalid.

#### Relationship to Inner Ridge

Border Labels and Inner Ridge are independent Features.

Border Labels do not determine whether Inner Ridge participates.

Inner Ridge participation remains:

```text
shape_inner_ridge_width == 0:
    Inner Ridge does not participate

shape_inner_ridge_width > 0:
    Inner Ridge participates
```

When the Inner Ridge participates, its outside boundary follows the inner border of the Border Label region.

For a participating Border Label region, the distance from the Border Label reference boundary to the outside boundary of the Inner Ridge is therefore:

```text
2 × shape_border_label_width
+ resolved common glyph height
```

When the Inner Ridge does not participate, the Border Label geometry remains valid and the inner boundary of the Border Label region remains available as a Shape interior boundary.

Border Labels do not implicitly create an Inner Ridge.

#### Interior Region

When Border Labels participate, their inner boundary contributes to determining the Shape region available for incorporated Artwork.

Moving inward from the Border Label reference boundary:

```text
outer border
lettering band
inner border
optional Inner Ridge
Artwork region
```

If the Inner Ridge participates, its inside boundary remains the boundary of the region available to incorporated Artwork.

If Border Labels participate and the Inner Ridge does not participate, the inner boundary of the Border Label region defines the region available to incorporated Artwork.

If neither Border Labels nor Inner Ridge participate, the existing Outer Ridge/Base interior-boundary rules apply.

#### Extrusion

The Top Border Label and Bottom Border Label are distinct Shape-owned extrusion components.

`shape_top_border_label_raise` controls the physical extrusion of the Top Border Label.

`shape_bottom_border_label_raise` controls the physical extrusion of the Bottom Border Label.

The two raises are independent.

Border Label extrusion layers on the Base and does not remove or partition the Base in X/Y.

The Base remains underneath the complete Border Label region.

Extrusion owns Border Label physical Z geometry but does not assign physical color.

#### Packaging and Color

The Top Border Label and Bottom Border Label remain distinct components through Package.

`shape_top_border_label_color` determines the packaged color of the Top Border Label.

`shape_bottom_border_label_color` determines the packaged color of the Bottom Border Label.

The colors are resolved independently.

Physical color is a Package-stage concern.

Structure, Compose, and Extrude preserve the semantic identity of each Border Label component without assigning its packaged physical color.

Changing only a Border Label color must not invalidate or recompute earlier Border Label geometry or extrusion products.

#### Feature Interactions

Border Labels may participate:

- with or without an Outer Ridge;
- with either Outer Ridge style;
- with or without an Inner Ridge;
- with or without incorporated Artwork;
- with only the Top Border Label;
- with only the Bottom Border Label;
- with both Border Labels.

Outer Ridge participation determines the Border Label reference boundary but does not otherwise alter Border Label typography or fitting rules.

Inner Ridge participation does not determine Border Label participation.

Border Label participation does not determine Inner Ridge participation.

Border Labels must preserve distinct component identity through Extrude and Package.

#### Border Label Invariants

1. The Top Border Label and Bottom Border Label are distinct Shape-owned components.
2. Each Border Label participates independently according to whether its text is present.
3. Border Labels do not cause Outer Ridge or Inner Ridge to participate.
4. Both labels use the same outer reference boundary.
5. The reference boundary is the inside boundary of a participating Outer Ridge, otherwise the outside boundary of Base.
6. Both labels share one border width.
7. Both labels share one fitted glyph-height allocation.
8. Both labels use one common font setting.
9. The common glyph height never exceeds the configured maximum.
10. The common glyph height is reduced when necessary until every participating label fits.
11. A shorter label is not stretched to fill its available path.
12. The Bottom Border Label baseline is one border width inward from the reference boundary.
13. The Top Border Label baseline is one border width plus the resolved common glyph height inward from the reference boundary.
14. The two baseline paths bound the same physical lettering band.
15. The Top Border Label and Bottom Border Label traverse their paths in opposite directions so both read normally from left to right.
16. Border Label paths follow the literal Shape perimeter.
17. Circular Border Label paths are concentric circular arcs.
18. Square and polygon Border Label paths follow their corresponding inset Shape perimeters.
19. Font fitting uses rendered font metrics rather than treating font size as physical glyph height.
20. Baseline-relative glyph measurements are preserved when positioning rendered text.
21. Maximum span constrains the available path.
22. Physical end margins are reserved at both ends of the maximum permitted path.
23. Border Label fitting does not horizontally stretch or compress text.
24. Border Labels remain distinct semantic components through Extrude and Package.
25. Top and Bottom Border Label raises are independently controlled by Extrude-stage parameters.
26. Top and Bottom Border Label colors are independently controlled by Package-stage parameters.
27. Changing only a Border Label color does not require recomputing earlier geometry.
28. Border Labels do not determine Inner Ridge participation.
29. When Inner Ridge participates, its inside boundary determines the incorporated Artwork region.
30. When Border Labels participate without Inner Ridge, the inner Border Label boundary determines the incorporated Artwork region.
31. Border Labels layer on Base without reducing the Base X/Y footprint.
32. When neither Border Label participates, Border Labels do not alter existing Shape geometry or products.


### Loop

The Loop Feature provides optional additive geometry extending outward from the complete assembled Shape envelope.

A Loop may be used for hanging, attachment, handling, or other purposes. Its semantic definition is geometric and does not depend on a particular intended use.

#### Parameters and Participation

The Loop is controlled by:

```text
shape_loop_inner_diameter
shape_loop_width
shape_loop_position
shape_loop_raise
shape_loop_color
```

Loop participation is determined solely by:

```text
shape_loop_inner_diameter
```

A Loop participates when:

```text
shape_loop_inner_diameter > 0
```

The default is:

```text
0 mm
```

The Loop therefore does not participate by default.

A Loop does not participate when:

```text
shape_loop_inner_diameter = 0
```

A negative `shape_loop_inner_diameter` is invalid.

When the Loop does not participate, its width, position, raise, and color do not cause Loop geometry to be produced.

`shape_loop_width`, `shape_loop_position`, `shape_loop_raise`, and `shape_loop_color` do not determine whether the Loop participates.

#### Geometry

The Loop is annular additive geometry having an inner opening and an outer boundary.

Its inner radius is:

```text
shape_loop_inner_diameter / 2
```

Its outer radius is:

```text
shape_loop_inner_diameter / 2
+ shape_loop_width
```

The Loop outer diameter is therefore:

```text
shape_loop_inner_diameter
+ 2 × shape_loop_width
```

`shape_loop_width` is a physical dimension measured in millimeters.

The default Loop width is:

```text
1 mm
```

When the Loop participates, `shape_loop_width` must be greater than zero.

The Loop is constructed relative to the complete assembled Shape envelope defined by:

```text
shape_size
```

The Loop extends outside that envelope as explicitly defined by this Feature contract.

Loop participation does not change the meaning or configured value of `shape_size`.

#### Position

The Loop position is controlled by:

```text
shape_loop_position
```

The supported positions are the four cardinal directions:

```text
0 degrees      -> top
90 degrees     -> right
180 degrees    -> bottom
-90 degrees    -> left
```

The default position is:

```text
0 degrees
```

A participating Loop must use one of the supported cardinal positions.

The Loop is centered on the corresponding cardinal axis of the dimensionalized Shape.

Its inner opening is externally tangent to the complete assembled Shape envelope at the selected cardinal position.

For a circular Shape, for example, a top Loop has:

```text
shape radius = shape_size / 2
inner radius = shape_loop_inner_diameter / 2

Loop center X = 0
Loop center Y = shape radius + inner radius
```

The inward-facing point of the Loop inner opening therefore lies exactly on the Shape envelope.

The equivalent geometric rule applies to square and polygon Shapes: the Loop inner opening is externally tangent to the dimensionalized Shape boundary at the selected cardinal position.

Loop positioning is determined from the complete assembled Shape envelope, not from optional Outer Ridge, Inner Ridge, Border Label, Artwork, or other Feature geometry.

#### Raise

The physical height of the Loop is controlled by:

```text
shape_loop_raise
```

`shape_loop_raise` is a physical dimension measured in millimeters from:

```text
Z = 0
```

The default Loop raise is the resolved Base raise:

```text
shape_loop_raise = shape_base_raise
```

The default is therefore derived from the resolved value of `shape_base_raise` rather than being an independent literal dimensional default.

An explicitly configured `shape_loop_raise` overrides this derived Base-raise default.

When the Loop participates, `shape_loop_raise` must be greater than zero.

The dimensionalized Loop occupies:

```text
Z = 0
```

through:

```text
Z = shape_loop_raise
```

The default behavior therefore produces a Loop having the same complete physical height as the Base.

#### Component Identity

A participating Loop is a distinct Shape-owned physical component.

The Loop retains its semantic component identity through Shape Extrude and Package.

The Loop may geometrically contact or overlap other assembled Shape material at its attachment region. Such contact does not remove the Loop's semantic component identity.

Shape Extrude establishes the Loop's physical geometry and physical Z dimensions but does not assign its physical printing color.

#### Loop Color

The Loop physical printing color is controlled by:

```text
shape_loop_color
```

The default Loop color is the resolved Base color:

```text
shape_loop_color = shape_base_color
```

The default is derived from the resolved value of `shape_base_color` rather than being an independent literal color default.

An explicitly configured `shape_loop_color` overrides this derived Base-color default.

Loop color is packaging policy.

Shape Structure, Compose, and Extrude preserve the semantic component identity required for downstream Loop color assignment but do not assign its physical printing color.

Shape Package applies the resolved Loop physical color.

Changing only `shape_loop_color` does not by itself change Shape Structure, Compose, or Extrude geometry.

When the Loop does not participate, its color has no effect on the produced artifact.

#### Interaction With Other Features

Loop participation is independent of all other optional Shape Features.

A Loop may therefore participate with or without:

- an Outer Ridge;
- an Inner Ridge;
- Border Labels;
- incorporated Artwork;
- Artwork fill;
- a Hole.

Other optional Features do not change the Shape envelope used to position the Loop.

The Loop does not change the registered interior region used for incorporated Artwork placement.

The Loop does not cause any other Feature to participate.

When a Hole intersects Loop material, the Hole's subtractive contract applies and the intersecting Loop material is removed.

#### Product Participation

A participating Loop contributes Shape-owned additive geometry to the dimensionalized Shape.

The Loop remains a distinct semantic component through Shape Extrude and Package.

Shape Extrude establishes its physical geometry and preserves its component identity but does not assign its physical printing color.

Shape Package applies the resolved `shape_loop_color`.

The Loop participates in the final packaged 3MF when its dimensionalized geometry has physical volume.

#### Loop Invariants

A conforming Loop Feature satisfies the following:

1. Loop is additive Shape-owned geometry.
2. Loop participation is determined solely by `shape_loop_inner_diameter`.
3. Zero `shape_loop_inner_diameter` disables the Loop.
4. Positive `shape_loop_inner_diameter` causes the Loop to participate.
5. Negative `shape_loop_inner_diameter` is invalid.
6. `shape_loop_width` defines the radial material width surrounding the Loop opening.
7. A participating Loop must have positive `shape_loop_width`.
8. The default Loop width is 1 mm.
9. Loop position is one of the four supported cardinal positions.
10. The default Loop position is zero degrees at the top of the Shape.
11. The Loop inner opening is externally tangent to the complete assembled Shape envelope at the selected cardinal position.
12. Loop positioning is derived from the Shape envelope defined by `shape_size`, not from optional Feature geometry.
13. The Loop explicitly extends beyond the Shape envelope without changing the meaning or configured value of `shape_size`.
14. `shape_loop_raise` determines the complete physical Loop height from `Z = 0`.
15. The default Loop raise is the resolved `shape_base_raise`.
16. An explicitly configured Loop raise overrides its derived Base-raise default.
17. A participating Loop must have positive physical height.
18. A participating Loop is a distinct Shape-owned physical component.
19. The default Loop color is the resolved Base color.
20. An explicitly configured Loop color overrides its derived Base-color default.
21. Loop color does not determine Loop participation or geometry.
22. Shape Extrude does not assign physical color to Loop geometry.
23. Shape Package applies the Loop's physical color policy.
24. Changing only `shape_loop_color` does not by itself change Shape Structure, Compose, or Extrude geometry.
25. Loop participation does not change the registered interior region used for incorporated Artwork.
26. Loop participation does not cause another optional Shape Feature to participate.
27. A participating Hole removes any Loop material intersecting the Hole.


### Hole

The Hole Feature provides an optional subtractive opening through the complete manufactured Shape.

A Hole is subtractive geometry rather than a physical component.

#### Parameters and Participation

The Hole is controlled by:

```text
shape_hole_diameter
shape_hole_position
shape_hole_edge_distance
```

Hole participation is determined solely by:

```text
shape_hole_diameter
```

A Hole participates when:

```text
shape_hole_diameter > 0
```

The default is:

```text
0 mm
```

The Hole therefore does not participate by default.

A Hole does not participate when:

```text
shape_hole_diameter = 0
```

A negative `shape_hole_diameter` is invalid.

When the Hole does not participate, its position and edge distance do not cause Hole geometry to be produced.

`shape_hole_position` and `shape_hole_edge_distance` do not determine whether the Hole participates.

#### Geometry

The Hole is a circular subtractive opening having physical diameter:

```text
shape_hole_diameter
```

Its radius is:

```text
shape_hole_diameter / 2
```

`shape_hole_diameter` is a physical dimension measured in millimeters.

The Hole is positioned inward from the complete assembled Shape envelope defined by:

```text
shape_size
```

The Hole does not alter that envelope or change the meaning or configured value of `shape_size`.

#### Position

The Hole position is controlled by:

```text
shape_hole_position
```

The supported positions are the four cardinal directions:

```text
0 degrees      -> top
90 degrees     -> right
180 degrees    -> bottom
-90 degrees    -> left
```

The default position is:

```text
0 degrees
```

A participating Hole must use one of the supported cardinal positions.

The Hole is centered on the corresponding cardinal axis of the dimensionalized Shape.

Its nearest edge is inset from the complete assembled Shape boundary by:

```text
shape_hole_edge_distance
```

The default Hole edge distance is:

```text
0.4 mm
```

When the Hole participates, `shape_hole_edge_distance` must be greater than or equal to:

```text
0.4 mm
```

For a circular Shape, for example, a top Hole has:

```text
shape radius = shape_size / 2
hole radius = shape_hole_diameter / 2
inset = hole radius + shape_hole_edge_distance

Hole center X = 0
Hole center Y = shape radius - inset
```

The equivalent geometric rule applies to square and polygon Shapes: the nearest edge of the Hole is inset from the dimensionalized Shape boundary by `shape_hole_edge_distance` at the selected cardinal position.

Hole positioning is determined from the complete assembled Shape envelope defined by `shape_size`, not from optional Outer Ridge, Inner Ridge, Border Label, Artwork, or other Feature geometry.

#### Subtraction

A participating Hole is subtracted from the complete manufactured Shape.

Any physical material intersecting the Hole is removed regardless of which Shape Feature or component owns that material.

This includes, when intersected:

- Base;
- Outer Ridge;
- Inner Ridge;
- Border Labels;
- Artwork fill;
- incorporated Artwork components;
- Loop;
- other physical Shape components.

The Hole passes through the complete physical Z extent of every intersecting component.

The Hole does not itself produce a physical component.

Subtraction does not change the semantic or color identity of the remaining portions of intersected components.

#### Interaction With Registered Geometry

The Hole is physical subtractive geometry applied during Shape dimensionalization.

It does not alter the registered Shape interior region or the registered geometry used for incorporated Artwork placement.

Hole participation therefore does not change Artwork fitting, registration, or registered composition.

#### Product Participation

A Hole does not contribute a component to the dimensionalized Shape or packaged 3MF.

Shape Extrude applies the Hole subtraction to all intersecting physical components.

Shape Package packages the resulting components without Hole-specific geometry or color policy.

#### Hole Invariants

A conforming Hole Feature satisfies the following:

1. Hole is subtractive Shape-owned geometry and is not a physical component.
2. Hole participation is determined solely by `shape_hole_diameter`.
3. Zero `shape_hole_diameter` disables the Hole.
4. Negative `shape_hole_diameter` is invalid.
5. Hole position is one of the four supported cardinal positions.
6. The default Hole position is zero degrees at the top of the Shape.
7. The nearest Hole edge is inset from the complete assembled Shape boundary by `shape_hole_edge_distance`.
8. The default Hole edge distance is 0.4 mm.
9. A participating Hole requires `shape_hole_edge_distance >= 0.4 mm`.
10. Hole positioning is derived from the Shape envelope defined by `shape_size`, not from optional Feature geometry.
11. Hole participation does not change the meaning or configured value of `shape_size`.
12. A participating Hole removes every intersecting physical material regardless of component ownership.
13. Hole subtraction passes through the complete physical Z extent of every intersecting component.
14. Hole subtraction preserves the semantic and color identity of remaining component material.
15. Hole participation does not change the registered interior region or incorporated Artwork fitting.
16. A Hole does not have independent raise or color policy.
17. A Hole does not produce an independent Extrude or Package component.
18. A participating Hole removes any Loop material intersecting the Hole.


## Final Product

Shape produces:

```text
artifact.3mf
```

The final artifact contains the dimensionalized structural Shape
geometry.

Participating Features contribute physical geometry and component partitioning according to their Feature contracts.

When Artwork is configured, the final artifact also contains the
incorporated Artwork components.

Artwork color components remain suitable for multicolor printing.

A Shape without Artwork still produces a complete valid printable
artifact.

## Model Invariants

The following are model-wide invariants. Feature-specific invariants are defined only
within the applicable Feature subsection and are not repeated here.

A conforming initial Shape implementation satisfies the following:

1. Shape can produce circle, square, and regular polygon geometry.
2. Regular polygon geometry is determined by `shape_sides` and `shape_rotation`.
3. `shape_sides` is an integer greater than or equal to 3.
4. The default polygon side count is 8.
5. Polygon rotation is measured counterclockwise in degrees.
6. At zero rotation, a regular polygon has one vertex centered on the positive Y axis.
7. For a regular polygon having `n` sides, rotation by `180 / n` degrees places the center of one side on the positive Y axis.
8. Polygon rotation preserves polygon proportions and configured Shape size.
9. Registered structural Shape geometry uses a canonical maximum extent of 1.0 centered at the origin.
10. Registered polygon geometry is uniformly normalized after rotation so that its greatest X/Y extent is 1.0.
11. Registered structural Shape geometry remains nonphysical until the Shape dimensionalization boundary.
12. `shape_size` has consistent physical overall-envelope semantics for every supported geometry.
13. `shape_size` does not determine the coordinate extent of registered structural Shape geometry.
14. Every Shape contains a base with physical thickness determined by `shape_base_raise`.
15. Shape can produce a complete artifact without Artwork.
16. Physical Shape policy may be converted into relative registered-space relationships when required for composition without assigning final physical dimensions to the registered coordinate system.
17. Every Shape has a base color determined by `shape_base_color` and applied during Shape Package.
18. The default base color is `white`.
19. Shape can consume registered vector Artwork produced by another artifact.
20. Consuming registered Artwork does not require standalone Artwork extrusion or packaging.
21. Dynamic Artwork component membership is obtained from its declared manifest rather than filesystem scanning.
22. Registered Artwork and registered structural Shape geometry are composed before final physical X/Y dimensionalization.
23. Shape determines the physical size and placement of incorporated Artwork.
24. Shape uses one geometry-independent Artwork placement computation for circle, square, and regular polygon geometry. The Artwork placement region is the largest circle centered at the registered Shape origin that is wholly contained within the available registered Shape interior region, and incorporated Artwork is centered and uniformly scaled to the largest size at which its authoritative envelope remains contained within that placement region.
25. Artwork aspect ratio and registration between color components are preserved.
26. All components of one registered Artwork collection receive the same transformation from Artwork registered space into Shape registered space.
27. Physical X/Y dimensionalization of the composed Shape is determined by `shape_size`.
28. Physical Z dimensions are introduced according to component semantics during downstream dimensionalization.
29. Separately printable structural components retain their identity through dimensionalization and packaging.
30. Required color distinctions remain representable through dimensionalization and packaging.
31. Packaged 3MF component names preserve semantic component role and resolved printing-color identity without relying on intermediate component ordinals.
32. Packaging occurs after physical dimensionalization.
33. Shape produces a valid printable 3MF containing its structural geometry and any incorporated Artwork components.
34. Incorporated Artwork begins at the top surface of the Shape base at `Z = shape_base_raise`.
35. Incorporated Artwork has physical height determined by `shape_artwork_raise`.
36. The default `shape_artwork_raise` is 1 mm.
37. `shape_artwork_raise` must be greater than zero when Artwork is incorporated.
38. All incorporated Artwork components receive the same physical Z dimensionalization.
39. Standalone `artwork_raise` does not determine incorporated Artwork Z dimensionalization.
40. Artwork-fill participation is determined solely by `shape_artwork_fill_raise`.
41. Artwork fill participates when `shape_artwork_fill_raise > 0` and does not participate when `shape_artwork_fill_raise <= 0`.
42. The default `shape_artwork_fill_raise` is 0 mm.
43. When Artwork fill exists, its registered geometry is the registered Shape interior region minus the transformed registered Artwork envelope.
44. Artwork fill begins at the top surface of the Shape base at `Z = shape_base_raise` and has physical height determined by `shape_artwork_fill_raise`.
45. Artwork fill remains semantically distinct from the structural base even when both resolve to the same printing color.
46. The default Artwork-fill color is the resolved base color; an explicitly configured `shape_artwork_fill_color` overrides that derived default.
47. `shape_artwork_fill_color` does not determine Artwork-fill participation or geometry.
48. Incorporated Artwork preserves logical Artifact-color identity through Shape Compose and Shape Extrude.
49. Shape Compose and Shape Extrude do not assign physical printer colors to incorporated Artwork.
50. Shape Extrude owns physical geometry and component participation and does not assign physical colors to Shape-owned components.
51. Shape Package applies physical color policy for Shape-owned components.
52. Shape Package resolves incorporated Artwork Artifact-color identity to physical printer colors using `printer_colors`.
53. Changing only `printer_colors`, `shape_base_color`, `shape_artwork_fill_color`, or Feature-specific packaging color parameters does not by itself change Shape Structure, Compose, or Extrude geometry.
54. Changing `shape_artwork_fill_raise` changes Artwork-fill participation or physical geometry and therefore affects Shape Extrude and downstream Package.

## Scope

The Shape model defines primarily two-dimensional structural objects that are composed in registered Shape space and subsequently dimensionalized into physical manufacturing geometry.

Shape owns:

- its structural geometry and physical dimensions;
- the registered Shape coordinate space;
- placement and dimensionalization of incorporated registered Artwork;
- Shape-owned physical components and Features;
- preservation of component identity required for downstream manufacturing;
- packaging of the resulting physical components into a printable artifact.

Optional Shape capabilities are defined as Features.

Each Feature subsection in this document defines that Feature's participation, geometry, dimensional behavior, interactions, component semantics, and other applicable policy. The presence or absence of a Feature in a particular realization is determined by that Feature's contract rather than by this Scope section.

The Shape model does not provide arbitrary free-form modeling or placement. Capabilities outside the structural, registered-composition, dimensionalization, Feature, and packaging contracts defined by this document require an explicit extension of the Shape model.

New Shape capabilities must be introduced deliberately through the appropriate model or Feature contract rather than inferred from implementation behavior.
