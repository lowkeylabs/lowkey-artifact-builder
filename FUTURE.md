# FUTURE

## Purpose

Preserve longer-term capabilities and design intent for `lowkey-artifact-builder`
(LAB) without turning exploratory ideas into premature implementation plans.

This document is a **parking lot, not a change plan or normative specification**.
It records desired behavior, motivating examples, and important constraints, but
neither commits to a particular architecture nor establishes phase order,
parameter names, Stage ownership, or implementation mechanisms.

`ARCHITECTURE.md` and the applicable Model `DEFINITION.md` files remain normative.
Repository HEAD defines the current implementation. `CHANGEPLAN.md` contains
only actionable, near-term work. Before promoting an item into CHANGEPLAN,
reload HEAD, review the permanent specifications, credit existing capabilities,
resolve the necessary semantic questions, and select a coherent TDD boundary.
Items may be combined, split, revised, or discarded as implementation and
manufacturing experience develops.

## Composition and placement

### Multiple ARTWORK and BANNER instances

****Goal:**** Eventually compose several independently positioned reusable ARTWORK
and BANNER sources into one SHAPE. A quartered coat of arms with different
images, a central crest, and a motto banner is a motivating example.

****Preserve:**** Reusable source Products, independent instance transforms,
explicit clipping where required, deterministic ordering, and dependency
correctness. Existing single-Artwork workflows must remain usable.

****Unresolved:**** Instance configuration, dependency representation, clipping,
registration, and any necessary infrastructure changes. **Do not implement a
full quadrant-placement or generic instance framework prematurely.**

### Standalone BANNER Model

****Goal:**** Create reusable parametric ribbons or scrolls with integrated text,
including suitable curves, folds, typography, and visual regions, for use in
SHAPE and other compositions.

****Preserve:**** BANNER is conceptually a standalone reusable Model, analogous to
ARTWORK—not a replacement for SHAPE-owned top/bottom border labels or ridges.
Its output should participate in composition without special-purpose
manufacturing pipelines.

****Unresolved:**** Geometry and typography contract, parameters, Products,
registration, and integration. No detailed BANNER implementation is planned.

## Representation, color, and manufacturing outputs

### Raster Artwork alongside vector geometry

****Goal:**** Allow a choice of raster or vector representation for incorporated
Artwork, supporting photographic or grayscale bitmap engraving and full-color
printing while retaining vector ridges, labels, cut contours, and decorations.

****Preserve:**** Artwork placement, physical size, orientation, registration,
transparency, and intentional clipping across representations. SVG can contain
embedded raster images, but compatibility with a particular importer must be
verified. Do not silently convert a requested raster representation into a
limited-color vector approximation.

****Unresolved:**** Where representation selection belongs, which Artwork Products
are required, mixed-content SVG import behavior in xTool Studio, and explicit
policies for outputs that cannot consume raster content.

### Device-independent design colors

****Goal:**** Support designs with more logical/display colors than the five
physical toolheads of a Prusa XL, including full-color SVG, raster engraving,
and inkjet print-and-cut workflows.

****Preserve:**** The existing distinction between logical Artifact-color identity
and physical printer-color assignment. A device-specific limit must not become
a universal limit on authored geometry. Color appearance, semantic component
identity, and manufacturing operation are separate concerns; SVG fill colors
alone must not determine CUT, SCORE, ENGRAVE, or PRINT operations.

****Unresolved:**** Whether PNG color-count defaults should be decoupled from
`printer_colors` for non-3MF workflows, and how output-specific assignments and
compatibility failures should be expressed. Retain current 3MF behavior unless
an explicit change is justified.

### xTool Studio XS packaging

****Goal:**** Produce an xTool Studio `.xs` project from LAB-composed geometry, with
independently configurable objects for printing, engraving, scoring, and
cutting as supported by the target software and machine.

****Preserve:**** One authoritative composed design, physical dimensions, common
coordinate system, object/component identity, and exact print/cut registration.
The outside cut boundary must be independently assignable from printable
ridges and Artwork. SHAPE remains authoritative for its geometry; packaging
must not reimplement SHAPE composition. Retiring the LASER Model does not imply
removing existing SHAPE SVG output.

****Unresolved:**** Actual `.xs` file structure, whether one SVG with groups is
sufficient or separate embedded objects/documents are needed, machine-operation
metadata, and xTool Studio import behavior. Inspect real `.xs` projects
containing independently configured PRINT and CUT objects before designing
packaging. Do not assume the XS format or its capabilities.

### Print-and-cut and decal products

****Goal:**** Reuse a composed SHAPE design for full-color inkjet printing on
suitable adhesive media followed by laser contour cutting, as demonstrated in
the xTool M2 workflow. Support future decals, stickers, and printed transfers
without requiring a new design Model.

****Preserve:**** Separation of printable artwork from the nonprinting cut contour;
shared size, origin, and registration; full authored colors and optional raster
content. The SHAPE outside boundary is a natural initial cut contour. Ridges
and labels may be printed rather than physically extruded. Keep existing
working SVG-based workflows functional.

****Unresolved:**** Whether the existing SVG plus improved component separation is
sufficient, or whether output-specific packaging, bleed, safe margins, print
resolution, transparency, and contour-cut options are needed. Non-PVC media
must still be checked for laser-safe coatings, adhesive, and backing.

### Optional SVG overlap diagnostics

****Goal:**** Make native-SVG color-overlap failures easier to diagnose, for example
by reporting conflicting source object IDs and useful intersection location or
extent information.

****Preserve:**** Existing strict rejection of prohibited positive-area overlap
between different logical colors; do not silently change SVG geometry or
permit invalid overlaps as a diagnostic shortcut.

****Unresolved:**** Whether current error reporting is sufficient and what
additional diagnostic information can be obtained reliably and cheaply.

## Configuration Authoring and Simplification

### Goal

Extend LAB's basic parameter annotation capability into a comprehensive configuration-authoring workflow that helps operators understand, customize, and simplify Artifact and Realization configuration.

### Potential capabilities

- Generate complete, commented configuration snapshots for every available Variant and every effective Realization, including inherited parameter values.
- Provide inactive, configuration-ready Realization templates for available Variants without creating actual Realizations.
- Remove generated annotations through an explicit `--unannotate` operation.
- Simplify active configuration through a `--clean` or `--prune` operation that removes redundant parameter overrides.
- Optionally preview configuration changes before applying them.

### Essential invariants

- Existing Model definitions, Variant definitions, and configuration resolution remain authoritative.
- Generated references do not change active configuration.
- Removing an override is permitted only when its removal preserves current effective configuration.
- Configuration simplification must preserve required declarations, user-authored content, and valid TOML structure.
- Removing redundant overrides deliberately restores inheritance and may change behavior if inherited defaults change later.
- No new configuration precedence or persistence semantics are introduced merely for annotation or cleanup.

### Unresolved questions

- Whether configuration snapshots should include value provenance and explanatory metadata.
- Whether simplification should be called `--clean`, `--prune`, or something else, given the existing `artifact clean` command.
- How to preserve user formatting and comments during configuration rewriting.
- Whether full configuration templates should include all registered Variants or only those relevant to the selected Artifact.

### MCP-Assisted Configuration Discovery

****Goal:**** Allow AI clients to discover and explain LAB's supported configuration parameters, defaults, constraints, and effective values through an optional Model Context Protocol (MCP) interface.

****Preserve:**** Existing Model definitions, configuration resolution, and application operations remain authoritative. MCP is an adapter, not a new Model, required build dependency, or independent configuration system. Parameter discovery and validation should be reusable by the CLI and other interfaces.

****Potential capabilities:**** List Models and parameters; describe individual parameters; inspect effective configuration and provenance; validate proposed changes. Configuration modification and build operations may be considered later.

****Unresolved:**** Whether existing parameter metadata is sufficient for useful descriptions, which reusable application operations are needed, and how an MCP server would be installed and connected to supported clients. Do not implement MCP before establishing a demonstrated need beyond basic annotation.

## Promotion to CHANGEPLAN

Promote an item only when its intended behavior is sufficiently clear to write
meaningful acceptance criteria and a coherent implementation slice. A brief
feasibility investigation may be promoted first when an external format,
importer behavior, or dependency boundary is unknown. Avoid detailed
speculative phase sequences here; re-evaluate priorities after each completed
CHANGEPLAN phase.



## SHAPE Physical Realization — Optional Base and Independent Components

**Status:** Deferred — design decisions established; implementation not scheduled.

### Purpose

Extend the SHAPE model's physical realization to support optional Base geometry, independent surface components, and consistent Z-height semantics.

This work is deferred while development prioritizes manufacturing-ready SVG output for laser fabrication.

### Architectural Decisions

These sections are labeled numerically for convienence and do not specify an implementation order.

**1. Authoritative Shape Boundary**

`shape_size` and the registered Shape geometry establish the authoritative outer envelope.

All Shape-owned geometry, including the perimeter, outer ridge, border labels, inner ridge, fills, and artwork, must respect that envelope unless an explicit future feature permits extensions.

The Shape boundary exists independently of any physical Base.

**2. Optional Base**

The Base is an optional physical component.

`shape_base_raise = 0.0` permits a Shape without a physical Base. A zero-volume Base must not generate an STL or 3MF object.

The absence of Base does not invalidate the Shape.

**3. Uniform Z-Raise Semantics**

All component raise parameters measure height above the top surface of the Base.

For raised components:

- `z_bottom = shape_base_raise`
- `z_top = shape_base_raise + component_raise`

When `shape_base_raise = 0.0`, raised components begin at Z=0.

Inlaid components may extend below the Base surface and replace Base material. Their raise still measures height above the Base surface; raise and total physical thickness are distinct concepts.

**4. Independent Components**

Ridges, labels, artwork, Border Fill, Artwork Region Fill, and future Perimeter Fill are independently manufacturable components.

A valid 3MF does not require:

- A physical Base.
- A connected assembly.
- A completely filled Shape envelope.
- Connectivity between individual component meshes.

Disconnected lettering or artwork may be printed directly on the build plate.

Positive-volume components must be preserved. Zero-volume components must be omitted.

No artificial connecting geometry should be introduced.

**5. Consistent Fill Semantics**

Border Fill, Artwork Region Fill, and future Perimeter Fill follow the same physical realization rules.

They differ in registered planar geometry, not in fundamental Z-height or Base interaction semantics.

Raised fills sit above Base. Inlaid fills replace participating Base material.

**6. Additional Parameters**

Future configuration work will introduce:

- `shape_border_fill_raise`
- `shape_artwork_region_fill_raise`
- `shape_perimeter_fill_color`
- `shape_perimeter_fill_raise`

Parameter defaults, inheritance, and backward compatibility must be established during implementation.

**7. Perimeter Fill**

Perimeter Fill occupies the region between the authoritative Shape boundary and the outer boundary of the inset Outer Ridge.

Unlike Border Fill and Artwork Region Fill, this region requires additional registration work in Compose.

The region may be empty when the Outer Ridge inset is zero.

**8. Compose and Extrude Responsibilities**

Compose owns:

- Authoritative planar Shape geometry.
- Registered component boundaries.
- Component placement.
- SVG composition and output.

Extrude owns:

- Z-height realization.
- Physical component volumes.
- Raised and inlaid construction.
- Base subtraction where applicable.
- Omission of zero-volume components.
- Packaging independently printable components.

The existing Compose geometry supports most of these decisions without modification.

Perimeter Fill requires additional planar registration in Compose. This capability may be introduced independently for SVG manufacturing before its physical extrusion behavior is implemented.

### Deferred Implementation

When this work resumes:

1. Establish acceptance tests for optional Base and independent components.
2. Introduce and validate fill raise parameters.
3. Implement uniform raised and inlaid Z semantics.
4. Correct separate Outer Ridge/Base partitioning.
5. Permit zero-volume components to be omitted.
6. Register and implement Perimeter Fill.
7. Verify circle, square, and polygon geometry.
8. Preserve existing manufacturing behavior through regression tests.

### Current Priority

Do not implement these changes as part of the current SVG development work.

Continue the active `CHANGEPLAN.md` phases focused on SVG composition, registered planar geometry, xTool Studio compatibility, and laser manufacturing.


## ARTWORK — Deferred Representation Processing Strategies

### Context

The initial ARTWORK representation architecture supports independently selected `artwork_representation` and `artwork_processing` parameters.

The initial implementation establishes source-preserving, raster-preserving, and vector-processing capabilities without implementing every possible processing strategy.

The following capabilities are deferred pending specific manufacturing requirements, normative specifications, and independent TDD implementation slices.

### Candidate Processing Strategies

- **Grayscale conversion:** Convert color raster Artwork to grayscale, with an explicit alpha and background-handling policy.
- **Raster dithering:** Support Jarvis, Floyd–Steinberg, and other raster dithering strategies.
- **Explicit vector tracing:** Support color tracing, mask tracing, and pixel-boundary tracing as independently selectable strategies.
- **Vector optimization:** Provide configurable simplification, smoothing, optimization, and intentional color reduction.
- **Ordered processing pipelines:** Consider composable processing operations when individual processing strategies prove insufficient.
- **Depth-map generation:** Support depth-map generation and depth-specific semantics under a separate specification and manufacturing validation.
- **SVG rasterization:** Extend SVG-to-raster support beyond the currently specified source interpretation contract.

### Architectural Guidance

These capabilities may extend `artwork_processing` without changing the meaning of `artwork_representation` or requiring special Realization names.

Preserve the distinction between:

- Representation — the required registered output.
- Processing — the strategy used to produce that representation.
- Realization — an independently configured application of the ARTWORK Model.

Do not introduce a general-purpose processing pipeline framework without a demonstrated manufacturing requirement.

### Manufacturing Motivation

Grayscale raster output remains an intended manufacturing capability, particularly for laser engraving and ablation workflows.

It is not required for completion of the initial `none` and `auto` processing implementation.

Individual capabilities should move from this document into `CHANGEPLAN.md` when selected for active implementation.

