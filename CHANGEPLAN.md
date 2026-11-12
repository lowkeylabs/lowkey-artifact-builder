# CHANGEPLAN

## Purpose

Continue refining `lowkey-artifact-builder` around the manufacturing value chain established by current repository HEAD. The operator's ordinary goal is:

> Move customer artwork to correct, manufacturing-ready Products with the fewest necessary decisions, actions, and computations.

```text
customer artwork
      ↓
artifact create
      ↓
managed Artifact
      ↓
artifact build (requested Realization Products and dependencies)
      ↓
independent manufacturing-ready SHAPE SVG Products
      ↓
xTool Studio / share / manufacture
```

`create` and `build` define the ordinary value chain. `show`, `config`, `colors`, and `clean` support discovery, inspection, customization, correction, and maintenance; they must not become mandatory ceremony. A single customer Artwork can support multiple independently configured ARTWORK Realizations and multiple SHAPE Realizations. The operator should not have to manually duplicate Artwork or transfer intermediate files between Realizations.

This CHANGEPLAN contains actionable remaining work, not completed implementation history or speculative capabilities. Credit existing HEAD behavior and remove completed phases. Longer-term ideas belong in `FUTURE.md`, which is not normative. Phase numbers are local to this plan and may change as work is completed.

## Current Implementation Scope — First-Class SHAPE SVG Manufacturing

**The primary first-class manufacturing outputs are independently buildable SVG Products for each requested SHAPE Realization, intended for xTool Studio.** SVG is not merely a side effect of a 3D-printing pipeline. A SHAPE SVG must be useful without executing Extrude or Package when those stages are unnecessary for the requested Product.

A single Artifact may have several ARTWORK Realizations, such as full-color raster, grayscale raster, traced vector, or color-limited vector, and several SHAPE Realizations, such as printable coaster, raster-engraved coaster, vector-engraved coaster, or Prusa coaster. Each SHAPE Realization must select the upstream ARTWORK Realization whose registered Product it consumes. Reusable configurations belong to Model-scoped Variants; Realizations are Artifact-specific applications of Variants, with supported customizations. Illustrative Realization names are not declarations of existing catalog Variants.

```text
                              customer source
                                    |
                                 Artifact
                                    |
                +-------------------+-------------------+
                |                   |                   |
         artwork_full_color   artwork_grayscale     artwork_prusa
                |                   |                   |
         registered raster   registered raster    registered vectors
                |                   |                   |
         coaster_print       coaster_engrave       coaster_prusa
                |                   |                   |
           Compose SVG         Compose SVG          Compose SVG
                |                   |                   |
         terminal SVG         terminal SVG           Extrude
                                                        |
                                                     Package
                                                        |
                                                       3MF
```

The diagram illustrates distinct Realizations, not new Models or mandatory Stage names. Verify actual Stage and Product declarations in HEAD before changing them. The dependency planner, not the CLI or Compose implementation alone, must know which upstream Realization is selected.

Active work may change ARTWORK representation, Realization dependency binding, SHAPE planar geometry, SVG composition, and manufacturing-project assembly. Existing 3MF behavior must remain compatible, but new physical extrusion behavior, optional Base, revised Z-raise semantics, and 3MF component partitioning remain deferred to `FUTURE.md` under **SHAPE Physical Realization — Optional Base and Independent Components**. Do not expand an SVG phase into physical Extrude work merely to support planar features.

**Depth-map compatibility:** A future `artwork_depth` Realization may provide a grayscale raster that a SHAPE Realization embeds in an SVG together with grayscale fills for ridges, border regions, and labels. SHAPE need not construct Z-aware geometry to compose this SVG. Existing SHAPE color parameters can encode grayscale values; no new depth parameters or special depth-composition mode are authorized by this plan. Depth-map generation, grayscale-range validation, and calibrated material-removal behavior are deferred to `FUTURE.md` pending their own specification and manufacturing tests.

## Planning and Development Rules

`ARCHITECTURE.md` and applicable Model `DEFINITION.md` files are normative. HEAD defines implemented behavior; the CLI README defines the intended operator-facing command model. This plan does not silently override permanent specifications.

Before each implementation slice:

1. Reload and follow `prompts/NEW_THREAD.md` and `prompts/TEST_DRIVEN_DEVELOPMENT.md`.
2. Compare HEAD, `ARCHITECTURE.md`, applicable Model definitions, relevant code and tests, and this plan.
3. Credit completed behavior and identify the next unmet behavioral boundary.
4. Resolve normative or architectural conflicts before encoding new requirements in RED tests.
5. Use one test or a small coherent test set to establish a meaningful behavioral seam.
6. Implement the smallest correct change in the layer that owns the behavior.
7. Run focused tests, applicable non-slow tests, Ruff, and Pyright; perform xTool Studio acceptance when required.
8. Reevaluate the plan, update specifications and documentation, and commit only verified scoped changes.

Preserve the separation:

```text
CLI / TUI / GUI / API
          |
          v
reusable application operations
          |
          v
configuration / planning / engine / Products
```

Click owns parsing, prompts, terminal presentation, and translation of structured application errors. Reusable workflow behavior belongs below Click. The CLI operates on the current working directory as project root. A registered Artifact may exist under `originals/` before `artifacts/<artifact_id>/` exists. Missing collections normally mean empty collections; a requested missing object is an operator error. Expected errors should be concise and traceback-free; unexpected invariant failures must remain distinguishable.

Product paths should be concise and useful from project root. Avoid exposing internal Stage or resolver mechanics unless they answer an operator question. Do not change Product identity, dependency semantics, configuration precedence, Model ownership, persistence, or color semantics merely for CLI presentation. The generic engine must not acquire SHAPE- or xTool-specific interpretation policy.

### TDD cycles

TDD is test-first: RED establishes a behavioral boundary, GREEN implements the coherent behavior, VERIFY protects the manufacturing workflow. Do not force one test per helper or parameter. Add narrower tests only for independently meaningful contracts, uncertain algorithms, or regressions. Every phase must leave the application production-capable. Incorrect manufacturing Products, corrupt persistent state, and material value-chain inefficiency take priority over presentation polish.

### Primary optimization objective — Minimize time to manufacture

The primary commercial use case is economical one-off and small-batch manufacturing for lowkeylabs LLC: coasters, keychains, ornaments, stickers, engraved glassware, stamps, and coordinated collections. Optimize preparation, not machine execution speed. Product-specific defaults should minimize repeated decisions; operator customization should focus on artwork, labels, messages, dimensions, and product selection.

The requested Product and its transitive dependencies determine the minimum work. One customer Artwork may be reused across products, product faces, sizes, and manufacturing methods without unnecessary recomputation. Manufacturing-project assembly may later group independently completed SVG Products for convenient xTool Studio import.

**Success measures:** fewer operator actions; less repeated source preparation; less manual positioning and labeling in xTool Studio; correct physical dimensions and registration; reusable Products and deterministic output; no unnecessary Extrude/Package; and simple operator-facing workflows.

## Working Rules

1. **HEAD is authoritative.** Reinspect the relevant current implementation before each phase.
2. **Specifications precede new contracts.** Reconcile `ARCHITECTURE.md` and Model definitions before tests assert revised behavior.
3. **Follow RED/GREEN/VERIFY.** Prefer coherent behavioral slices over mechanical change-by-change cycles.
4. **Preserve ownership.** ARTWORK interprets source content and registers representations; SHAPE selects upstream Products and owns geometry, placement, composition, and physical manufacturing; the engine owns generic dependency planning and Product state.
5. **Reuse existing mechanisms.** Prefer existing Variants, Realizations, Product dependencies, Stage outputs, registered geometry, and SVG composition.
6. **Keep representation separate from manufacturing.** Transparency is not a color; printer colors do not define source colors; visual SVG groups or grayscale fills do not automatically assign xTool operations or calibrated depths.
7. **Preserve compatibility.** Existing `artwork_default` dependencies, SVG Products, and 3MF workflows must continue to work unless a reviewed specification explicitly changes them.
8. **Avoid speculative scope.** Do not introduce a new Model, generic framework, native `.xs` generation, or physical extrusion behavior without a demonstrated need.
9. **Verify manufacturing behavior.** Test physical dimensions, SVG self-containment, component registration, and actual xTool Studio import where relevant.
10. **Record outcomes.** Remove completed or superseded work from the active plan.

## Roadmap and Dependencies

| Order | Phase | Consolidates | Primary result |
| --- | --- | --- | --- |
| 4 | Raster-Preserving SVG Manufacturing | BUG-005 | Embedded raster from a selected ARTWORK Realization in terminal SHAPE SVG |
| 5 | Multi-Realization SVG Manufacturing Acceptance | End-to-end selection, isolation, and xTool acceptance | One source yields independently manufacturable raster/vector SVGs and compatible 3MF |
| 6 | Broader SVG Source Interpretation | BUG-001 + BUG-003 | Embedded PNG SVG inputs and visible stroke geometry |
| 7 | SHAPE Perimeter Region and SVG Fill | First-class planar Perimeter | Independently dimensioned and colored perimeter region |
| 8 | SHAPE Placement and Reusable SVG Decorations | Former SHAPE placement/decorations | Multiple independently transformed motif instances |
| 9 | SHAPE Clipping and Deterministic Planar Composition | Clipping and overlap | Manufacturing-correct planar clipping and precedence |
| 10 | Artwork Scaling and Boundary Policies | Artwork enlargement | Explicit enlargement with fixed outer SHAPE boundary |
| 11 | Hierarchical SVG Manufacturing Project Assembly | Manufacturing project assembly | Grouped SVG containing independently manufacturable Products |

**Dependency policy:**  Phase 4 makes raster representation composable; Phase 5 verifies the combined end-to-end manufacturing contract. Phases 6–10 extend supported source and planar composition features; Phase 11 assembles existing Products. Independent defect fixes may move earlier when required for manufacturing correctness, but must not undermine the dependency and Product contracts.

---

## Phase 4 — Raster-Preserving SVG Manufacturing

**Status:** OPEN — Specification and implementation pending; depends on Phases 1–3.

### Purpose

Allow a SHAPE Compose Product to incorporate a raster Product from its **selected** ARTWORK Realization as an embedded SVG `<image>`, while retaining vector structural geometry such as ridges, labels, borders, and cut contours. Tracing is not mandatory for raster engraving or printing.

### Architectural Boundaries

- ARTWORK owns raster/grayscale interpretation and registration; SHAPE owns placement, scaling, clipping, physical size, and planar composition.
- The SHAPE dependency must point to the selected ARTWORK Realization and compatible registered raster Product; no default-Realization shortcut is allowed.
- Embed image bytes in a self-contained SVG; preserve alpha, aspect ratio, orientation, and registration. Keep SVG vector components independently identifiable.
- A grayscale depth map is a possible future raster input, not a requirement to implement depth estimation or Z-aware extrusion here.
- Do not add xTool processing settings to generic ARTWORK/SHAPE logic or execute 3MF stages for SVG-only requests.

### TDD Work

**RED:** Standalone PNG and grayscale ARTWORK Products embed as self-contained `<image>` elements in distinct SHAPE Realization SVGs; alpha, transforms, physical dimensions, and registered placement survive. Raster and vector SHAPE features coexist. The selected ARTWORK Realization is honored; `printer_colors` is not consulted for raster output. Existing traced-vector composition remains selectable.

**GREEN:** Extend existing ARTWORK Product consumption and SHAPE Compose SVG serialization, not a parallel raster pipeline.

**VERIFY:** Inspect generated SVGs and import representative full-color and grayscale raster products into xTool Studio. Check image placement, size, transparency, independent structural groups, and unchanged 3MF builds.

### Completion

A selected raster or grayscale ARTWORK Realization produces a manufacturing-ready SHAPE SVG containing correctly registered embedded raster content and independent vector SHAPE features, without mandatory tracing or extrusion.

---

## Phase 5 — Multi-Realization SVG Manufacturing Acceptance

**Status:** OPEN — Integration and xTool Studio acceptance pending; depends on Phases 1–4.

### Purpose

Demonstrate the primary value chain: **one customer source, multiple ARTWORK Realizations, multiple SHAPE Realizations, multiple independent manufacturing-ready SVG Products**, with a compatible 3MF path when requested.

### Required Scenario

One Artifact declares at least:

- A full-color raster ARTWORK Realization consumed by a printable SHAPE Realization.
- A grayscale raster ARTWORK Realization consumed by a raster-engraving SHAPE Realization.
- A vector or color-limited ARTWORK Realization consumed by a vector SHAPE Realization and/or existing Prusa path.

Each SHAPE Realization independently selects its ARTWORK Realization, retains the same relevant Shape geometry and label customization, and produces a separately addressable SVG. These names and product configurations are examples; prefer reusable Model Variants for repeated setups.

### Acceptance Contract

1. `artifact create` registers the customer source once. No manual copying of artwork or manufactured SVGs is required.
2. Each SHAPE SVG is requested, built, inspected, and rebuilt independently through ordinary application/CLI operations.
3. The planner executes only selected dependencies and required stages. Unrelated Realizations and Extrude/Package are skipped for SVG-only builds.
4. Each output has stable Realization-qualified identity, correct physical dimensions, deterministic SVG, and independent Product state.
5. Changes to one ARTWORK Realization affect only dependent SHAPE Products; changes to common source content affect the appropriate dependent paths.
6. xTool Studio imports the individual SVGs with usable raster/vector content and SHAPE component grouping. Confirm observed operation assignment behavior rather than assuming colors/groups automatically map to operations.
7. Existing default-ARTWORK and 3MF builds remain compatible.

### TDD Work

**RED:** High-level application/CLI acceptance tests covering three ARTWORK representations, three SHAPE consumers, independent SVG Products, dependency isolation, targeted invalidation, and compatibility. Avoid duplicating every lower-level case already covered by prior phases.

**GREEN:** Fix integration gaps in the layer that owns them; do not introduce a new manufacturing-project abstraction simply to make the acceptance scenario pass.

**VERIFY:** Perform real xTool Studio imports of the individual SVG Products; record dimensions, hierarchy, and raster/vector handling. Run the complete required quality suite.

### Completion

The normal workflow reliably produces multiple distinct xTool-ready SHAPE SVGs from one customer source, with correct Realization dependencies and without unnecessary manufacturing preparation.

---

## Phase 6 — Broader SVG Source Interpretation

**\*\*Status:\*\*** OPEN — Specification and implementation pending.

### Purpose

Accept two common forms of valid customer-authored SVG that the existing ARTWORK pipeline does not fully support: SVG documents containing an embedded PNG, and geometry whose visible appearance is defined by strokes.

These are distinct testable slices under one source-compatibility phase. Implement and verify them separately.

### Slice A — Embedded PNG in SVG (BUG-001)

**\*\*Reproduction:\*\*** `bug01.svg`, an xTool Studio-exported SVG containing a Base64 PNG. Confirm the fixture's location at current HEAD.

**\*\*Required behavior\*\***

1. Recognize one embedded Base64 PNG `<image>` element.

2. Decode it without unnecessary pixel alteration; preserve alpha.

3. Respect document dimensions, `viewBox`, image placement, and applicable transforms.

4. Integrate the image into the established ARTWORK processing path, preserving the selected representation and Realization-specific preparation policy.

5. Preserve standalone PNG and native vector SVG behavior.

6. Provide actionable diagnostics for unsupported cases.

Initially exclude multiple images, mixed image/vector content, external image references, additional raster formats, and general-purpose SVG rendering unless a current permanent specification already requires them.

### Slice B — Stroke-Only and Mixed SVG Geometry (BUG-003)

**\*\*Reproduction:\*\*** `tests/fixtures/artwork/bug02.svg`, a transparent 600 × 600 SVG with a black, unfilled circle stroke touching the canvas boundary. Confirm fixture availability at current HEAD.

**\*\*Required behavior\*\***

1. Interpret visible strokes, not merely filled path interiors.

2. Support supported SVG shapes and paths, including circles, ellipses, rectangles, lines, polylines, and paths.

3. Respect stroke width, color, caps, joins, and transforms.

4. Preserve transparent interiors of unfilled shapes.

5. Support mixed stroke-and-fill geometry without losing either.

6. Preserve registered color semantics, overlap rules, and deterministic manufacturing geometry.

7. Reuse ARTWORK's interpretation machinery; do not implement stroke semantics separately inside SHAPE decorations.

### TDD Work

**\*\*RED:\*\*** Add reproduction tests and minimal synthetic cases for each slice, including dimensions, transparency, transforms, deterministic results, and explicit unsupported cases.

**\*\*GREEN:\*\*** Implement the smallest coherent source-interpretation extensions against revised ARTWORK specifications.

**\*\*VERIFY:\*\*** Build both reproduction fixtures through `artifact build`; verify existing PNG, filled SVG, and multicolor behavior; run required tests and quality checks.

### Completion

The supported embedded-image and stroke-only SVG cases build correctly, produce registered geometry or raster representation as specified, and do not introduce competing SVG semantics.

**---**

## Phase 7 — SHAPE Perimeter Region and SVG Fill

**\*\*Status:\*\*** OPEN — Normative specification review, migration contract, and SVG implementation pending. Physical extrusion is deferred.

### Purpose

Establish `shape_perimeter` as a first-class SHAPE planar region, alongside the Outer Ridge, Border Label, Inner Ridge, and Artwork regions. The Perimeter is not an incidental remainder of Outer Ridge placement. It has independently specified geometry, component identity, and logical fill color.

Introduce `shape_perimeter_width` to define the region measured inward from the authoritative Shape boundary, and `shape_perimeter_fill_color` to define its SVG fill. The Outer Ridge, when present, begins immediately inside the Perimeter. Preserve `shape_size` and the outer manufacturing cut contour. Defer `shape_perimeter_fill_raise`, Z-dimensionalization, and physical extrusion to `FUTURE.md`.

### Contract to Resolve

1. Define the Perimeter as the planar band bounded externally by the complete Shape envelope and internally by the inward offset specified by `shape_perimeter_width`. Its registration and existence do not depend on an Outer Ridge being present.

2. Establish `shape_perimeter_width` as the single authoritative width parameter for this region. Use the same physical measurement conventions already established for inset geometry, including perpendicular offsets for polygon edges. Require finite, nonnegative width and specify geometric bounds and empty-region behavior, including zero width.

3. Define Outer Ridge placement relative to the inner Perimeter boundary. When an Outer Ridge exists, its outer boundary begins at that boundary and its own width is controlled by `shape_outer_ridge_width`. Specify behavior for absent ridges and for dimensions that cannot fit inside the Shape envelope.

4. Introduce `shape_perimeter_fill_color` as an independently configurable logical color, not an alias for `shape_base_color` or `shape_outer_ridge_color`. Resolve its default/inheritance behavior so existing artifacts retain their established appearance unless explicitly customized.

5. Explicitly reconcile the existing `shape_outer_ridge_inset` parameter with the new first-class `shape_perimeter_width`. Preserve legacy artifact geometry through a documented compatibility/migration policy; do not leave two independently effective parameters controlling the same region. Specify precedence, conflict diagnostics, and whether the old name is accepted as a deprecated alias before implementing tests. Do not silently reinterpret existing configurations.

6. Register Perimeter geometry and identity independently in SHAPE Compose, and emit it as a distinct canonical SVG component with stable logical color and physical dimensions. Reuse established geometric offset helpers where appropriate, without making Perimeter ownership depend on the Outer Ridge.

7. Define planar interactions with Outer Ridge, Border Fill, Artwork Region Fill, labels, and other registered geometry. Preserve deterministic component boundaries and avoid prohibited positive-area color overlaps. Do not infer xTool Studio processing settings from visual colors alone.

8. Preserve existing 3MF behavior and all unrelated SHAPE geometry. Do not modify Extrude, introduce new Base partitioning, or implement new Z-height semantics in this phase.

### TDD Work

**\*\*RED:\*\*** Establish the normative contract, then test independent Perimeter geometry and fill color for circle, square, and polygon Shapes. Cover zero and nonzero width, absent and present Outer Ridge, distinct Perimeter and Base colors, fixed outer cut contour, component identity, geometric bounds, invalid dimensions, and deterministic SVG output. Add compatibility tests for legacy `shape_outer_ridge_inset` configurations and the selected migration/precedence policy.

**\*\*GREEN:\*\*** Extend SHAPE configuration, derived geometry as needed, Compose registration, and canonical SVG output. Make `shape_perimeter_width` authoritative while preserving legacy input through the specified compatibility boundary. Reuse existing planar offset calculations; do not add a competing width mechanism or change Extrude.

**\*\*VERIFY:\*\*** Inspect generated SVG and import representative cases into xTool Studio. Verify physical size, distinct Perimeter grouping and fill, correct ridge placement, stable cut contour, legacy configuration compatibility, and unchanged existing 3MF workflows. Run focused and complete applicable quality checks.

### Completion

Perimeter is a first-class, independently registered SHAPE planar region controlled by `shape_perimeter_width` and `shape_perimeter_fill_color`. It remains well-defined without an Outer Ridge, existing configurations have an explicit compatibility path, and canonical SVG manufacturing works without new physical extrusion behavior.

**---**

## Phase 8 — SHAPE Placement and Reusable SVG Decorations

**\*\*Status:\*\*** OPEN — Specification and implementation pending.

### Purpose

Allow SHAPE to incorporate externally authored decorative SVG motifs—stars, diamonds, flourishes, serifs, filigree, and similar geometry—as independently positioned instances. Reuse one source at multiple positions without copying source files or creating separate ARTWORK Realizations.

This combines the former placement-contract and reusable-decoration phases: placement should be defined only to the extent needed by a real decoration use case.

### Architectural Boundaries

- SHAPE owns source references, instance identity, placement, and registered planar composition. Existing physical manufacturing ownership is unchanged; new decoration extrusion is deferred.

- ARTWORK owns the reusable SVG source interpretation contract; SHAPE must not invoke another Model's Stage implementation directly.

- Reuse registered coordinate space and existing SHAPE Structure/Compose boundaries. Do not extend Extrude or 3MF packaging for decoration support in this phase.

- Keep source interpretation, instance transforms, and color overrides separate.

- Preserve authored geometry, logical colors, and source proportions unless explicitly overridden.

- Do not introduce a generalized component-instance or dependency framework merely for anticipated future Models.

### Work

1. Inspect current registered Artwork placement, SHAPE composition, component identities, and existing transformation helpers.

2. Specify the smallest SHAPE configuration for a decoration source and multiple named instances.

3. Define translation, uniform scaling, rotation, transform order, and registered-to-physical placement.

4. Preserve independent instance identities when two instances share one SVG source.

5. Define optional logical color overrides without silently replacing authored colors.

6. Carry registered decoration geometry through canonical SVG manufacturing, preserving independent instance identities, transforms, and logical colors. Do not introduce new 3MF realization behavior in this phase.

7. Validate unsupported source constructs, invalid references, transforms, and colors clearly.

8. Preserve all existing SHAPE behavior when decorations are absent.

### TDD Work

**\*\*RED:\*\*** One motif reused at two or more locations with different transforms, stable registration, separate identities, correct colors, and validation failures.

**\*\*GREEN:\*\*** Implement placement and decoration incorporation together using existing mechanisms.

**\*\*VERIFY:\*\*** Build a representative decorated SHAPE into canonical SVG. Check registration, dimensions, independent instance identities, logical colors, and xTool Studio import behavior. Confirm existing 3MF workflows remain compatible without requiring new decoration extrusion support. Run required tests and quality checks.

### Completion

Reusable SVG decorations participate in SHAPE manufacturing with independent transforms and semantic identities, without speculative infrastructure or regressions.

**---**

## Phase 9 — SHAPE Clipping and Deterministic Planar Composition

**\*\*Status:\*\*** OPEN — Specification and implementation pending.

### Purpose

Allow a positioned decoration to be restricted to a selected SHAPE region, and define deterministic overlap behavior among decorations, Artwork, ridges, labels, QR codes, and other participating components.

This combines the former clipping and planar-composition phases because clipping and overlap precedence must yield one coherent manufacturing result, not merely the right SVG appearance.

### Architectural Boundaries

- SHAPE remains authoritative for its registered planar geometry, including the Shape boundary, Artwork, Inner Ridge, Outer Ridge, and other participating regions.

- Clipping modifies registered planar geometry, not merely SVG visibility.

- Planar precedence is distinct from physical Z-dimensionalization.

- Preserve common registration, component identity, logical colors, and deterministic planar geometry.

- Do not silently permit prohibited positive-area overlap between distinct vector material partitions. Distinguish raster display layering from 3D color-partition constraints; raster image pixels are not separate SHAPE material partitions.

- Reuse existing planar overlap, subtraction, and partitioning machinery; prefer fixed semantic precedence over configurable ordering unless real use cases demand it.

- Preserve existing default Artwork fitting and SHAPE composition.

- Do not introduce new Extrude behavior or physical Z-partitioning requirements in this phase.

### Work

1. Define selectable clipping regions initially considering Base, Artwork, Inner Ridge, and Outer Ridge.

2. For each region, explicitly define whether it means enclosed area, occupied physical area, or another precise geometric domain.

3. Define absent/empty-region behavior and how clipping interacts with transforms and color-separated components.

4. Review current overlap precedence among existing SHAPE Features before adding decoration-specific behavior.

5. Establish deterministic planar semantics for supported overlaps, distinguishing visible SVG layering, registered component ownership, and deferred physical partitioning.

6. Clip against authoritative registered geometry and preserve resulting component identities.

7. Reject ambiguous or unsupported overlap combinations with actionable diagnostics.

8. Carry the resulting registered geometry into canonical SVG manufacturing, preserving component identities and deterministic planar relationships. Defer new raised/inlaid physical realization behavior.

### TDD Work

**\*\*RED:\*\*** Boundary-crossing motifs clipped to different regions; missing-region validation; overlaps between decorations and representative SHAPE Features; cases with different logical colors.

**\*\*GREEN:\*\*** Implement only missing planar clipping, precedence, subtraction, or registration behavior.

**\*\*VERIFY:\*\*** Confirm that clipping changes registered planar geometry rather than only SVG display. Inspect canonical SVG output, including component boundaries, colors, registration, and overlap behavior. Confirm existing 3MF workflows remain compatible without introducing new extrusion semantics. Run required tests and quality checks.

### Completion

Supported clipping and overlap cases have documented, deterministic planar manufacturing semantics. Canonical SVG preserves intended registered regions and component identities, with no unintended changes to existing SHAPE configurations or existing 3MF behavior.

**---**

## Phase 10 — Artwork Scaling and Boundary Policies

**\*\*Status:\*\*** OPEN — Specification and implementation pending.

### Purpose

Permit incorporated Artwork to grow beyond its initial fitting region while preserving a deliberate relationship between Artwork extent, internal SHAPE regions, and the outer manufacturing boundary.

The initial policy is **\*\*clip\*\***. More expansive boundary behavior is deferred.

### Architectural Boundaries

- Existing Artwork fitting and registration remain the default.

- Artwork scaling, clipping, nominal SHAPE boundary, and manufactured envelope are separate concepts.

- Preserve aspect ratio, logical color identity, and registration.

- Do not automatically enlarge the authoritative Shape envelope, alter `shape_size`, or change the outer cut contour when Artwork grows.

- Reuse the placement, clipping, and composition contracts from Phases 8 and 9.

- Do not implement `extend` or `expand` without a separate manufacturing specification.

### Work

1. Review existing Artwork fit/scale behavior and the new SHAPE placement and clipping contracts.

2. Define explicit enlargement beyond the initial Artwork fitting region.

3. Establish initial `clip` semantics:

   - Artwork may cross internal SHAPE regions.

   - Artwork beyond the nominal SHAPE boundary is clipped.

   - The authoritative Shape envelope, `shape_size`, and the outer cut contour remain unchanged.

4. Define interactions with ridges, labels, QR codes, and decorations using established planar precedence.

5. Preserve correct registered planar geometry and canonical SVG manufacturing under the `clip` policy. Do not modify raised/inlaid physical realization behavior as part of this phase.

6. Record `extend` and `expand` as deferred possibilities, not automatic consequences of scaling.

### TDD Work

**\*\*RED:\*\*** Enlarged Artwork crosses an internal boundary and the nominal outer boundary while preserving aspect ratio, registration, component identity, and fixed Shape envelope and outer cut-contour dimensions.

**\*\*GREEN:\*\*** Extend existing Artwork fitting and clipping rather than introducing an alternate composition path.

**\*\*VERIFY:\*\*** Check canonical SVG output for enlarged Artwork, clipping, fixed Shape dimensions, registration, and component identity. Confirm unchanged default Artwork fitting and existing 3MF compatibility. Run required tests and quality checks.

### Completion

Explicit Artwork enlargement is manufacturing-correct under the `clip` policy, and existing SHAPE dimensions and default Artwork behavior remain stable.

**---**

## Phase 11 — Hierarchical SVG Manufacturing Project Assembly

**\*\*Status:\*\*** OPEN — Architectural review, specification, and implementation pending.

### Purpose

Combine multiple existing, independently manufacturable Products into one self-contained, hierarchically grouped SVG document for xTool Studio import.

This is a **\*\*manufacturing project assembly operation\*\***, not a new ARTWORK or SHAPE interpretation pipeline. It should consume completed Products without rebuilding their geometry.

### Example Project

```text

manufacturing-project.svg

└── project

    ├── coaster-front

    │   ├── engraving

    │   └── cut-outline

    ├── coaster-back

    │   └── engraving

    ├── keychain-front

    │   ├── engraving

    │   └── cut-outline

    ├── keychain-back

    │   └── engraving

    └── sticker-front

        ├── printable-artwork

        └── cut-contour

```

Each product or product face has an independent position within the project workspace.

### Architectural Boundaries

- Prefer application-level assembly of existing manufacturing Products; select the exact boundary after reviewing current Product identity and publication mechanisms.

- Preserve source Products unchanged and avoid retracing, extruding, repackaging 3MF, or reassigning printer colors.

- Keep XTS-specific assumptions outside the generic engine.

- Distinguish SVG grouping and semantic operation identities from XTS processing layers and actual machine settings.

- Do not assume SVG IDs, colors, or groups automatically create XTS processing layers.

- Do not depend on native `.xs` generation or undocumented XTS metadata.

- Preserve standalone SVG and 3MF manufacturing behavior.

### Required Behavior

1. Accept multiple existing manufacturing Products.

2. Produce one outer project group with each product as an immediate named child group.

3. Preserve meaningful nested manufacturing component groups without unnecessary wrappers.

4. Support native vector geometry and embedded raster content.

5. Preserve physical size, transparency, transforms, orientation, and artwork registration.

6. Support independent positioning of product groups in one workspace.

7. Resolve identifier collisions and references, including SVG definitions and nested coordinate systems.

8. Produce deterministic, self-contained SVG.

9. Preserve source Products and their semantic operation/component identities.

10. Permit independently assigning engraving, cutting, and printing operations in XTS after import.

### Grouping Acceptance Contract

The intended interaction is:

1. Import the combined SVG as one grouped manufacturing project.

2. Ungroup once to expose individual product groups.

3. Ungroup an individual product to expose its immediate manufacturing components.

4. Leave other product groups intact.

5. Assign processing settings to intended components without unintentionally affecting unrelated Products.

**\*\*XTS behavior must be observed, not inferred.\*\*** If XTS changes the authored hierarchy, document the observed behavior and revise the export contract before considering the phase complete.

### TDD Work

**\*\*RED\*\***

- Assemble multiple representative coaster, keychain, and sticker Products.

- Verify exact group depth and stable, unique IDs.

- Preserve physical dimensions, independent placement, and nested component identities.

- Preserve embedded raster data, SVG definitions, and internal references.

- Verify deterministic output and unchanged source Products.

- Reject unsupported or incompatible Product representations clearly.

**\*\*GREEN\*\***

Implement the smallest reusable assembly operation using established Product, SVG, coordinate, and registration mechanisms. Do not add a new Model, Stage, or generalized project framework without a demonstrated architectural need.

**\*\*VERIFY\*\***

Import representative assemblies into xTool Studio and verify grouping, ungrouping, dimensions, raster/vector registration, and independent processing assignments. Run required tests and quality checks.

### Completion

Multiple existing Products can be imported as one manufacturing SVG, remain independently identifiable and positionable, and retain usable component grouping and registration in XTS.

**---**

## Deferred Work and Explicit Non-Goals

These are not additional active phases. Revisit them only when a real manufacturing requirement justifies a separate specification and plan:

- **Depth-map generation** using a future `artwork_depth` Realization (potentially Depth Anything V2 Small), including model selection, source masking, normalization, depth-map provenance, and licensing review.
- **Depth-map grayscale compatibility validation:** compare an ARTWORK depth map's actual minimum/maximum grayscale values with existing SHAPE component fills (for example `shape_outer_ridge_color`, `shape_border_fill_color`, and `shape_label_color`), warn about or reject specifically defined incompatible depth relationships, and preserve intended component heights. Do not add depth-specific SHAPE parameters by default.
- **Depth-map xTool manufacturing calibration:** verify whether xTool Studio treats vector SVG grayscale fills and embedded grayscale rasters consistently, including the relationship between luminance, power, passes, and physical material removal. A grayscale value does not itself guarantee a particular removal depth.
- Native height-field-to-mesh or 3MF relief generation, if future manufacturing needs it. Ordinary raster-preserving SHAPE SVG composition must not depend on it.
- Native `.xs` multi-canvas project generation or reverse-engineering.
- A generalized component-instance framework or new BANNER Model.
- Multiple embedded raster images, mixed image/vector SVG input, external image links, or arbitrary SVG rendering beyond Phase 6's initial contract.
- Artwork boundary `extend` or `expand` policies.
- Configurable general-purpose layer ordering when fixed semantic precedence suffices.
- Automatic assignment of xTool processing parameters from arbitrary SVG groups or colors.
- Broader project management, nesting optimization, or machine-specific manufacturing orchestration.
- SHAPE physical realization changes, including optional Base, zero-volume component omission, uniform Z-raise semantics, revised raised/inlaid component partitioning, and independent 3MF objects. Preserve agreed design considerations in `FUTURE.md`.
- Physical extrusion of new reusable decorations, clipping behaviors, and enlarged Artwork beyond existing supported 3MF capabilities.
- Perimeter physical realization, including `shape_perimeter_fill_raise`, physical Base partitioning, and independent 3MF geometry. First-class planar Perimeter registration, `shape_perimeter_width`, and `shape_perimeter_fill_color` remain active in Phase 7.

## Phase Execution Checklist

For each phase or independently testable slice:

- [ ] Reload HEAD and inspect relevant permanent specifications, implementation, and tests.
- [ ] Confirm reproductions and existing capabilities before editing.
- [ ] Resolve open semantic decisions; revise normative documentation first.
- [ ] Define one coherent RED test boundary and verify expected failure.
- [ ] Implement the smallest GREEN change.
- [ ] Run focused tests, applicable non-slow tests, Ruff, and Pyright.
- [ ] Perform manufacturing acceptance when the contract requires it.
- [ ] Update documentation, record completion evidence, and identify the next slice.
- [ ] Commit only the verified, scoped change.

## Next Action

Begin with the next appropriate phase and slice.

**Do not implement new depth-map processing, depth parameters, physical Extrude changes, or native xTool project formats as part of this first slice.**

No implementation work is authorized merely by adopting this plan.

