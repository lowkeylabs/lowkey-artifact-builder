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

* circle, square, and regular polygon geometry;
* configurable regular-polygon side count and rotation;
* a physical base;
* an optional integrated or separately printable outer ridge;
* independently assignable base and outer-ridge colors;
* optional registered Artwork;
* a printable multicomponent 3MF.

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

`shape_rotation` specifies the counterclockwise rotation of polygon geometry
in degrees.

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

For polygon geometry, the polygon is uniformly normalized after rotation so
that its greatest X/Y extent is 100 mm. The other extent may be smaller
depending on the polygon side count and rotation.

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

Regular polygon geometry is centered at the origin and uniformly normalized
after rotation so that its greatest X/Y extent is:

```text
1.0
```

Normalization does not stretch the polygon or otherwise change its
proportions.

The other X/Y extent may be less than `1.0` depending on polygon side count
and rotation.

The registered coordinate system establishes geometry, registration,
and relative spatial relationships.

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

`shape_sides` and `shape_rotation` participate in structural geometry only
when:

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

including the configured side count and rotation when polygon geometry is
selected.

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

Without a separately printable outer ridge, the base occupies the complete
Shape X/Y envelope.

With a separately printable outer ridge, the base occupies the region
inside the ridge's inner boundary.

The separately printable ridge therefore reduces the X/Y extent of the
base component without reducing the complete assembled Shape envelope.

The base may be assigned a printing color.

The outer ridge defaults to the base color but may be assigned a different
color independently.

## Color

Shape structural components have semantic printing-color assignments.

The base color is controlled by:

```text
shape_base_color
```

The default base color is:

```text
white
```

The outer-ridge color is controlled by:

```text
shape_outer_ridge_color
```

The default outer-ridge color is the resolved base color:

```text
shape_outer_ridge_color = shape_base_color
```

The ridge-color default is therefore derived from the resolved value of:

```text
shape_base_color
```

rather than being an independent literal color default.

For example, with no explicit color configuration:

```text
shape_base_color = "white"
shape_outer_ridge_color = "white"
```

If the base color is configured as:

```text
shape_base_color = "black"
```

and no ridge color is explicitly configured, the resolved colors are:

```text
shape_base_color = "black"
shape_outer_ridge_color = "black"
```

An explicitly configured outer-ridge color overrides this derived default.

For example:

```text
shape_base_color = "white"
shape_outer_ridge_color = "red"
```

assigns white to the base and red to the outer ridge.

Incorporated Artwork may optionally have a Shape-owned fill color.

The Artwork fill color is controlled by:

```text
shape_artwork_fill_color
```

The default Artwork fill color is:

```text
none
```

The presence of a resolved Artwork fill color determines whether Artwork
fill geometry exists.

When:

```text
shape_artwork_fill_color = none
```

no Artwork fill geometry is produced.

When `shape_artwork_fill_color` resolves to a color, Shape produces Artwork
fill geometry using that semantic printing color.

Artwork fill color does not determine the color of registered Artwork
components. Those components retain the semantic colors supplied by the
consumed registered Artwork.

Color values are semantic color names resolved through the system's common
color-resolution mechanism.

Color assignment does not determine structural geometry, component
partitioning, or whether an outer ridge exists.

Likewise, structural partitioning does not determine color assignment.

A color assigned to geometry that does not produce a corresponding physical
component has no effect on the produced artifact.


## Outer Ridge

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

For polygon geometry, ridge width is the perpendicular distance from each
outer polygon edge to its corresponding inner ridge edge.

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

When the ridge does not exist, ridge raise, style, and color do not alter
the produced ridge geometry.

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

`shape_outer_ridge_width` is a physical dimension measured in millimeters.

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

## Integrated Outer Ridge

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

## Separate Outer Ridge

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

The base and ridge therefore occupy adjacent, nonoverlapping X/Y regions.

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

The separate ridge therefore uses the same complete assembled ridge height
as the corresponding integrated ridge.

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

## Ridge Equivalence

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

* the complete Shape outer envelope;
* the ridge outer boundary;
* the ridge inner boundary;
* the registered interior region;
* the complete assembled ridge height;
* the intended complete assembled physical geometry.

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

because the independently printable ridge occupies the surrounding
5 mm perimeter region.

The union of the separate base and separate ridge corresponds to the
same intended assembled structural geometry as the integrated
construction for the same dimensional parameters.

## Ridge Color

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

## Interior Region

Shape defines a registered interior region available for Artwork.

The interior region is bounded by the innermost existing ridge boundary.

When no ridge exists, the interior region is bounded by the registered
Shape boundary.

In the initial Shape model, which supports only the outer ridge, an
existing outer ridge's inner boundary therefore defines the interior
region.

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

Registered Artwork is placed within the registered Shape interior region.

Shape uses one geometry-independent Artwork placement rule for every supported
Shape geometry.

The Artwork placement region is the largest circle centered at the registered
Shape origin that is wholly contained within the available registered Shape
interior region.

The placement circle is computed from the registered interior boundary. The
same computation is used regardless of whether the Shape geometry is a circle,
square, or regular polygon.

Registered Artwork is:

* centered within the Artwork placement region;

* uniformly scaled to the largest size at which its authoritative Artwork
  envelope remains contained within the Artwork placement region;

* aspect-ratio preserving;

* not stretched;

* not cropped merely to increase its fitted size.

The authoritative Artwork envelope determines Artwork occupancy for fitting.

Shape does not infer Artwork occupancy from the independent bounds of its
individual color components.

The transformation from registered Artwork space into registered Shape space
is derived from the Artwork collection's common registered extent and the
computed Artwork placement region.

All registered Artwork color layers receive the same transformation so that
their registration is preserved.

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
registered-space relationships required for composition. For example,
`shape_outer_ridge_width` and `shape_size` determine the relative
registered inset of the ridge inner boundary.

Composition retains sufficient semantic component identity to support
downstream physical dimensionalization, color assignment, and packaging.

When:

```text
shape_outer_ridge_width > 0
```

the registered composition contains the outer-ridge partition regardless
of ridge raise.

When:

```text
shape_outer_ridge_style = separate
```

the base region and outer-ridge region remain distinguishable so that
downstream dimensionalization can produce independently printable
structural components.

When:

```text
shape_outer_ridge_style = integrated
```

the base and ridge belong to one assembled structural geometry even though
their physical Z and color semantics may differ.

The composed result similarly retains sufficient Artwork component
identity to allow different structural and Artwork components to receive
their appropriate physical Z semantics and to remain independently
printable where required.

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

The canonical registered maximum Shape extent of `1.0` therefore corresponds
to:

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

A registered Artwork component occupying 0.8 Shape units across therefore
occupies 80 mm when incorporated into a 100 mm Shape.

Changing `shape_size` changes the physical size of the composed geometry
without changing its registered spatial relationships.

Physical Z dimensions are introduced at the dimensionalization boundary
according to the semantic role of each component.

These dimensions include:

```text
shape_base_raise
shape_outer_ridge_raise
shape_artwork_raise
```

and the defined Z policy for optional Artwork fill.

For either ridge style, the complete assembled ridge height is:

```text
shape_base_raise + shape_outer_ridge_raise
```

Ridge raise may be negative, but it must satisfy:

```text
shape_outer_ridge_raise >= -shape_base_raise
```

Ridge style determines structural component partitioning during
dimensionalization.

For an integrated ridge, dimensionalization preserves the full-envelope
base and applies the ridge-region Z semantics to the outer perimeter.

For a separate ridge, dimensionalization produces independent base and
outer-ridge structural components.

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

Shape also owns the physical Z dimensionalization of incorporated Artwork.

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

The bottom surface of every incorporated Artwork component is located at:

```text
Z = shape_base_raise
```

and its top surface is located at:

```text
Z = shape_base_raise + shape_artwork_raise
```

`shape_artwork_raise` must be greater than zero when Artwork is incorporated.

All incorporated Artwork color components receive the same physical Z
dimensionalization.

The standalone Artwork parameter:

```text
artwork_raise
```

does not determine the physical Z dimensions of Artwork incorporated into
Shape.

Shape may optionally fill the portion of the registered interior region
outside the transformed Artwork envelope.

Artwork fill existence is determined solely by:

```text
shape_artwork_fill_color
```

When no Artwork fill color is configured, no Artwork fill geometry is
produced.

When an Artwork fill color is configured, the registered fill region is:

```text
registered Shape interior region
    minus
transformed registered Artwork envelope
```

The Artwork envelope is therefore the boundary between incorporated Artwork
occupancy and Shape-owned Artwork fill geometry.

Shape does not determine the fill boundary by independently inspecting the
bounds of individual Artwork color components.

Artwork fill uses the same physical Z dimensionalization as incorporated
Artwork.

Its bottom surface is located at:

```text
Z = shape_base_raise
```

and its top surface is located at:

```text
Z = shape_base_raise + shape_artwork_raise
```

There is no independent Artwork-fill raise parameter.

When Artwork fill exists, the incorporated Artwork and surrounding fill
therefore form a common raised interior surface.

When Artwork fill does not exist, only the incorporated Artwork components
are raised above the base; the remainder of the interior region remains at
the base top.

Artwork fill is a distinct semantic component from the structural base even
when its configured color is equal to the base color.

Outer-ridge style does not change the Z origin or physical raise of
incorporated Artwork or Artwork fill.

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
shape_artwork_raise
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

`shape_rotation` selects the counterclockwise polygon rotation in degrees.

Its default is:

```text
0 degrees
```

At zero degrees, a polygon has one vertex centered on the positive Y axis.

`shape_sides` and `shape_rotation` do not alter circle or square geometry.

`shape_outer_ridge_width` determines whether an outer ridge exists and
determines its inward physical width.

The default ridge width is:

```text
0 mm
```

so the default Shape contains no outer ridge.

`shape_outer_ridge_raise` determines the position of the ridge top relative
to the base top.

The default ridge raise is:

```text
1 mm
```

for both ridge styles.

A ridge raise of zero is valid and places the ridge top flush with the
base top.

A negative ridge raise is valid down to:

```text
-shape_base_raise
```

`shape_outer_ridge_style` selects how an existing outer ridge is
structurally partitioned.

Its supported values are:

```text
integrated
separate
```

The default ridge style is:

```text
integrated
```

`shape_base_color` selects the base printing color.

Its default is:

```text
white
```

`shape_outer_ridge_color` selects the ridge printing color.

Its default is the resolved value of:

```text
shape_base_color
```

An explicitly configured `shape_outer_ridge_color` overrides this derived
default.

`shape_artwork_raise` determines the physical height of Artwork incorporated
into Shape above the top surface of the Shape base.

Its default is:

```text
1 mm
```

`shape_artwork_raise` must be greater than zero when Artwork is incorporated.

When Artwork is not incorporated, `shape_artwork_raise` does not cause
Artwork geometry to be produced.

`shape_artwork_fill_color` optionally selects the semantic printing color
for the portion of the registered Shape interior outside the transformed
Artwork envelope.

Its default is:

```text
none
```

The absence of an Artwork fill color disables Artwork fill geometry.

A configured Artwork fill color enables Artwork fill geometry when Artwork
is incorporated.

There is no separate boolean controlling Artwork fill existence and no
independent Artwork-fill raise parameter.

The dimensional parameters are:

```text
shape_size
shape_base_raise
shape_outer_ridge_width
shape_outer_ridge_raise
shape_artwork_raise
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

Artwork dependency binding is not represented by a filesystem-path
parameter.


## Packaging

Physical Shape components are packaged after dimensionalization.

Packaging preserves independently printable and independently assignable
components where required by structural or color semantics.

A separate outer ridge remains an independent structural component in the
packaged artifact.

An integrated outer ridge remains structurally integrated with the base,
while its independently assigned color must remain representable when the
ridge color differs from the base color.

Incorporated Artwork color components likewise remain suitable for
multicolor printing.

Packaged 3MF component identity preserves both the semantic role of each
physical component and its semantic printing-color identity.

Component names use the form:

```text
<artifact-id>-<component-role>-<color>
```

For example:

```text
ornament-base-cold-white
ornament-ridge-red
ornament-artwork-black
ornament-artwork-gold
```

The packaged component name does not depend on an intermediate component
ordinal when semantic role and color provide sufficient identity.

Component naming does not determine color assignment. The component's
semantic color and RGB representation remain explicit packaging metadata.

Packaging does not determine Shape geometry, ridge geometry, ridge
partitioning, ridge height, ridge color policy, Artwork fitting, or
physical dimensionalization.

Those semantics must already be established before packaging.

## Final Product

Shape produces:

```text
artifact.3mf
```

The final artifact contains the dimensionalized structural Shape geometry.

Without an outer ridge, the final artifact contains the structural base
and any incorporated Artwork components.

With an integrated outer ridge, the ridge is structurally integrated with
the full-envelope base while preserving the color semantics required for
multicolor printing.

With a separate outer ridge, the final artifact contains independently
printable base and outer-ridge structural components.

When Artwork is configured, the final artifact also contains the
incorporated Artwork components.

Artwork color components remain suitable for multicolor printing.

A Shape without Artwork still produces a complete valid printable
artifact.

## Invariants

A conforming initial Shape implementation satisfies the following:

1. Shape can produce circle, square, and regular polygon geometry.

2. Regular polygon geometry is determined by `shape_sides` and
   `shape_rotation`.

3. `shape_sides` is an integer greater than or equal to 3.

4. The default polygon side count is 8.

5. Polygon rotation is measured counterclockwise in degrees.

6. At zero rotation, a regular polygon has one vertex centered on the
   positive Y axis.

7. For a regular polygon having `n` sides, rotation by `180 / n` degrees
   places the center of one side on the positive Y axis.

8. Polygon rotation preserves polygon proportions and configured Shape size.

9. Registered structural Shape geometry uses a canonical maximum extent of
   1.0 centered at the origin.

10. Registered polygon geometry is uniformly normalized after rotation so
    that its greatest X/Y extent is 1.0.

11. Registered structural Shape geometry remains nonphysical until the
    Shape dimensionalization boundary.

12. `shape_size` has consistent physical overall-envelope semantics for
    every supported geometry.

13. `shape_size` does not determine the coordinate extent of registered
    structural Shape geometry.

14. Every Shape contains a base with physical thickness determined by
    `shape_base_raise`.

15. Shape can produce a complete artifact without Artwork.

16. An outer ridge follows the selected Shape boundary.

17. Outer-ridge width is measured inward from the complete Shape boundary.

18. For polygon geometry, outer-ridge width is the perpendicular distance
    between corresponding outer and inner polygon edges.

19. The outer ridge lies within the Shape boundary and does not increase
    `shape_size`.

20. Outer-ridge existence is determined solely by
    `shape_outer_ridge_width`.

21. Zero outer-ridge width disables the outer ridge.

22. Positive outer-ridge width defines an outer ridge regardless of
    `shape_outer_ridge_raise`.

23. Negative outer-ridge width is invalid.

24. The default outer-ridge raise is 1 mm for both ridge styles.

25. Outer-ridge raise is measured relative to the top of the base.

26. The complete assembled ridge height is
    `shape_base_raise + shape_outer_ridge_raise` for both ridge styles.

27. Outer-ridge raise may be zero.

28. Outer-ridge raise may be negative down to
    `-shape_base_raise`.

29. Outer-ridge raise less than `-shape_base_raise` is invalid.

30. An existing outer ridge may be integrated with the base or partitioned
    as a separately printable structural component.

31. With an integrated outer ridge, the base retains the complete Shape
    X/Y envelope.

32. With a separate outer ridge, the ridge retains the complete Shape
    outer boundary and the base outer boundary becomes the ridge inner
    boundary.

33. A separate outer ridge and its base occupy adjacent, nonoverlapping
    X/Y regions.

34. A separate ridge occupies Z from zero through
    `shape_base_raise + shape_outer_ridge_raise`.

35. Integrated and separate ridge styles preserve the same complete Shape
    envelope, ridge boundaries, registered interior region, and intended
    assembled ridge height for otherwise identical Shape parameters.

36. The innermost existing ridge boundary defines the available registered
    interior region; when no ridge exists, the registered Shape boundary
    defines the interior region.

37. Ridge raise does not change the registered ridge inner boundary or
    registered interior region.

38. Physical Shape policy may be converted into relative registered-space
    relationships when required for composition without assigning final
    physical dimensions to the registered coordinate system.

39. Every Shape has a semantic base color determined by `shape_base_color`.

40. The default base color is `white`.

41. The default outer-ridge color is the resolved base color.

42. An explicitly configured outer-ridge color overrides its derived
    base-color default.

43. Outer-ridge color is independent from outer-ridge structural style.

44. An integrated ridge may have a color different from the base.

45. A separate ridge may have a color different from the base.

46. Shape can consume registered vector Artwork produced by another
    artifact.

47. Consuming registered Artwork does not require standalone Artwork
    extrusion or packaging.

48. Dynamic Artwork component membership is obtained from its declared
    manifest rather than filesystem scanning.

49. Registered Artwork and registered structural Shape geometry are
    composed before final physical X/Y dimensionalization.

50. Shape determines the physical size and placement of incorporated
    Artwork.

51. Shape uses one geometry-independent Artwork placement computation for
    circle, square, and regular polygon geometry. The Artwork placement region
    is the largest circle centered at the registered Shape origin that is
    wholly contained within the available registered Shape interior region,
    and incorporated Artwork is centered and uniformly scaled to the largest
    size at which its authoritative envelope remains contained within that
    placement region.

52. Artwork aspect ratio and registration between color components are
    preserved.

53. All components of one registered Artwork collection receive the same
    transformation from Artwork registered space into Shape registered
    space.

54. Physical X/Y dimensionalization of the composed Shape is determined
    by `shape_size`.

55. Physical Z dimensions are introduced according to component semantics
    during downstream dimensionalization.

56. Separately printable structural components retain their identity
    through dimensionalization and packaging.

57. Required color distinctions remain representable through
    dimensionalization and packaging.

58. Packaged 3MF component names preserve artifact identity, semantic
    component role, and semantic printing-color identity without relying
    on intermediate component ordinals.

59. Packaging occurs after physical dimensionalization.

60. Shape produces a valid printable 3MF containing its structural
    geometry and any incorporated Artwork components.

61. Incorporated Artwork begins at the top surface of the Shape base at
    `Z = shape_base_raise`.

62. Incorporated Artwork has physical height determined by
    `shape_artwork_raise`.

63. The default `shape_artwork_raise` is 1 mm.

64. `shape_artwork_raise` must be greater than zero when Artwork is
    incorporated.

65. All incorporated Artwork components receive the same physical Z
    dimensionalization.

66. Standalone `artwork_raise` does not determine incorporated Artwork Z
    dimensionalization.

67. Artwork fill existence is determined solely by the presence of
    `shape_artwork_fill_color`.

68. When Artwork fill exists, its registered geometry is the registered
    Shape interior region minus the transformed registered Artwork
    envelope.

69. Artwork fill receives the same physical Z dimensionalization as
    incorporated Artwork.

70. Artwork fill remains semantically distinct from the structural base
    even when both resolve to the same printing color.

71. Outer-ridge style does not change the physical Z origin or raise of
    incorporated Artwork or Artwork fill.


## Initial Scope

The initial Shape model includes:

* circle geometry;
* square geometry;
* configurable regular polygon geometry;
* polygon side count of three or greater;
* polygon rotation;
* canonical registered Shape geometry;
* physical Shape size;
* physical base thickness;
* optional integrated outer ridge;
* optional separately printable outer ridge;
* positive, zero, and permitted negative outer-ridge raise;
* base and outer-ridge color assignment;
* structural component partitioning;
* optional registered Artwork;
* centered, aspect-preserving Artwork fitting;
* registered Shape/Artwork composition;
* Shape-owned physical raise for incorporated Artwork;
* optional Shape-owned Artwork fill color and geometry;
* common physical raise for incorporated Artwork and enabled Artwork fill;
* downstream physical dimensionalization;
* final multicomponent 3MF packaging.

The initial Shape model does not include:

* irregular polygons;
* internal ridges;
* dashed ridges;
* hangers;
* handles;
* text or labels;
* arbitrary Artwork positioning;
* multiple independent Artwork placements;
* independent Artwork-fill raise;
* recessed or embedded Artwork;
* arbitrary custom Shape outlines.

These capabilities may be added later by deliberately extending the Shape
definition.
