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

### Artwork placement beyond its fitting region

**Goal:** Allow incorporated Artwork to extend beyond the region used to fit or
initially position it. For example, a Cobra Kai graphic may cross the Inner
Ridge while remaining within the permitted SHAPE envelope.

**Preserve:** A clear distinction among the fitting region, any permitted
placement boundary, and any actual clipping boundary. Avoid unintended
cropping or changes to Artwork geometry. Overlap behavior must be explicit and
manufacturing-correct for each supported output.

**Unresolved:** Placement limits, clipping policy, interaction with ridges and
labels, and whether existing composition mechanisms suffice.

### Deterministic planar composition

**Goal:** Support meaningful front-to-back ordering of Artwork, ridges, labels,
QR codes, and future reusable components, yielding the intended visible design.

**Preserve:** Semantic component identity and logical colors; consistent
registration across outputs; deterministic overlap behavior. Planar visibility
ordering is distinct from physical extrusion height. Opaque vector overlaps
must not silently produce conflicting manufactured regions.

**Unresolved:** Whether fixed semantic precedence suffices or configurable
ordering is needed; when clipping, geometric subtraction, or raster compositing
is appropriate; and which existing operations can be reused.

### Reusable SVG decorations

**Goal:** Incorporate externally authored SVG motifs—stars, diamonds,
flourishes, serifs, and other small decorative elements—at arbitrary locations,
including multiple placements of the same motif with independent translation,
scale, and rotation.

**Preserve:** Reuse of ARTWORK's established SVG processing where appropriate;
source geometry and authored color identity unless deliberately overridden;
independent instance identity and reliable registration. Do not create a
competing SVG interpretation pipeline merely for decorations.

**Unresolved:** The smallest useful placement interface, source references,
color overrides, stroke handling, and how placement interacts with ordering.

### Multiple ARTWORK and BANNER instances

**Goal:** Eventually compose several independently positioned reusable ARTWORK
and BANNER sources into one SHAPE. A quartered coat of arms with different
images, a central crest, and a motto banner is a motivating example.

**Preserve:** Reusable source Products, independent instance transforms,
explicit clipping where required, deterministic ordering, and dependency
correctness. Existing single-Artwork workflows must remain usable.

**Unresolved:** Instance configuration, dependency representation, clipping,
registration, and any necessary infrastructure changes. **Do not implement a
full quadrant-placement or generic instance framework prematurely.**

### Standalone BANNER Model

**Goal:** Create reusable parametric ribbons or scrolls with integrated text,
including suitable curves, folds, typography, and visual regions, for use in
SHAPE and other compositions.

**Preserve:** BANNER is conceptually a standalone reusable Model, analogous to
ARTWORK—not a replacement for SHAPE-owned top/bottom border labels or ridges.
Its output should participate in composition without special-purpose
manufacturing pipelines.

**Unresolved:** Geometry and typography contract, parameters, Products,
registration, and integration. No detailed BANNER implementation is planned.

## Representation, color, and manufacturing outputs

### Raster Artwork alongside vector geometry

**Goal:** Allow a choice of raster or vector representation for incorporated
Artwork, supporting photographic or grayscale bitmap engraving and full-color
printing while retaining vector ridges, labels, cut contours, and decorations.

**Preserve:** Artwork placement, physical size, orientation, registration,
transparency, and intentional clipping across representations. SVG can contain
embedded raster images, but compatibility with a particular importer must be
verified. Do not silently convert a requested raster representation into a
limited-color vector approximation.

**Unresolved:** Where representation selection belongs, which Artwork Products
are required, mixed-content SVG import behavior in xTool Studio, and explicit
policies for outputs that cannot consume raster content.

### Device-independent design colors

**Goal:** Support designs with more logical/display colors than the five
physical toolheads of a Prusa XL, including full-color SVG, raster engraving,
and inkjet print-and-cut workflows.

**Preserve:** The existing distinction between logical Artifact-color identity
and physical printer-color assignment. A device-specific limit must not become
a universal limit on authored geometry. Color appearance, semantic component
identity, and manufacturing operation are separate concerns; SVG fill colors
alone must not determine CUT, SCORE, ENGRAVE, or PRINT operations.

**Unresolved:** Whether PNG color-count defaults should be decoupled from
`printer_colors` for non-3MF workflows, and how output-specific assignments and
compatibility failures should be expressed. Retain current 3MF behavior unless
an explicit change is justified.

### xTool Studio XS packaging

**Goal:** Produce an xTool Studio `.xs` project from LAB-composed geometry, with
independently configurable objects for printing, engraving, scoring, and
cutting as supported by the target software and machine.

**Preserve:** One authoritative composed design, physical dimensions, common
coordinate system, object/component identity, and exact print/cut registration.
The outside cut boundary must be independently assignable from printable
ridges and Artwork. SHAPE remains authoritative for its geometry; packaging
must not reimplement SHAPE composition. Retiring the LASER Model does not imply
removing existing SHAPE SVG output.

**Unresolved:** Actual `.xs` file structure, whether one SVG with groups is
sufficient or separate embedded objects/documents are needed, machine-operation
metadata, and xTool Studio import behavior. Inspect real `.xs` projects
containing independently configured PRINT and CUT objects before designing
packaging. Do not assume the XS format or its capabilities.

### Print-and-cut and decal products

**Goal:** Reuse a composed SHAPE design for full-color inkjet printing on
suitable adhesive media followed by laser contour cutting, as demonstrated in
the xTool M2 workflow. Support future decals, stickers, and printed transfers
without requiring a new design Model.

**Preserve:** Separation of printable artwork from the nonprinting cut contour;
shared size, origin, and registration; full authored colors and optional raster
content. The SHAPE outside boundary is a natural initial cut contour. Ridges
and labels may be printed rather than physically extruded. Keep existing
working SVG-based workflows functional.

**Unresolved:** Whether the existing SVG plus improved component separation is
sufficient, or whether output-specific packaging, bleed, safe margins, print
resolution, transparency, and contour-cut options are needed. Non-PVC media
must still be checked for laser-safe coatings, adhesive, and backing.

### Optional SVG overlap diagnostics

**Goal:** Make native-SVG color-overlap failures easier to diagnose, for example
by reporting conflicting source object IDs and useful intersection location or
extent information.

**Preserve:** Existing strict rejection of prohibited positive-area overlap
between different logical colors; do not silently change SVG geometry or
permit invalid overlaps as a diagnostic shortcut.

**Unresolved:** Whether current error reporting is sufficient and what
additional diagnostic information can be obtained reliably and cheaply.

## Promotion to CHANGEPLAN

Promote an item only when its intended behavior is sufficiently clear to write
meaningful acceptance criteria and a coherent implementation slice. A brief
feasibility investigation may be promoted first when an external format,
importer behavior, or dependency boundary is unknown. Avoid detailed
speculative phase sequences here; re-evaluate priorities after each completed
CHANGEPLAN phase.



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

