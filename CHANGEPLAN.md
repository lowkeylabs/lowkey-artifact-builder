# CHANGEPLAN

## Purpose

Continue refining `lowkey-artifact-builder` around the manufacturing value
chain established by the current repository HEAD.
The operator's ordinary goal is:

> Move customer artwork to a correct, manufacturing-ready Product with the
> fewest necessary decisions, actions, and computations.

The normal production path is intentionally short:

```text
customer artwork
      ↓
artifact create
      ↓
managed Artifact
      ↓
artifact build
      ↓
manufacturing-ready Product
      ↓
slicer / xTool Studio / share / manufacture
```

`create` and `build` define the ordinary value chain. `show`, `config`,
`colors`, and `clean` support that path when the operator needs discovery,
inspection, customization, correction, color selection, or maintenance. These
support commands must not become mandatory ceremony before routine
manufacturing.

This CHANGEPLAN contains actionable remaining work, not a history of completed
implementation or a catalog of speculative capabilities. Completed behavior
should be credited from HEAD and removed from the plan. Longer-term goals and
unresolved design ideas belong in `FUTURE.md`; that document is not normative.
Before promoting an item from `FUTURE.md`, reevaluate current HEAD and the
permanent specifications and establish a sufficiently understood behavioral
boundary. Phases may be removed, reordered, combined, or rewritten after each
completed implementation slice. Phase numbering is local to the current plan.

## Planning and development rules

`ARCHITECTURE.md` and the applicable Model `DEFINITION.md` files are normative.
Repository HEAD defines the current implementation. The CLI README defines the
intended operator-facing command model. This CHANGEPLAN describes temporary
remaining work and must not redefine permanent architecture.
At the beginning of a thread and before each meaningful implementation slice:

1. Reload and follow `prompts/NEW_THREAD.md`.
2. Compare CHANGEPLAN with current HEAD, `ARCHITECTURE.md`, applicable Model
   definitions, and relevant CLI documentation.
3. Credit behavior HEAD already satisfies.
4. Identify the next unmet behavioral boundary rather than assuming the plan
   is still current.
5. Resolve known semantic or architectural questions before encoding behavior
   in tests, while allowing test-first exploration to discover or clarify
   uncertain seams and ownership boundaries.
6. Organize TDD around major behavioral seams or boundaries, using one test or
   a small coherent test set to drive a substantial implementation slice rather
   than creating single-test/single-change cycles.
7. Implement the smallest correct change at the layer that owns the behavior.
8. Run focused tests and then the appropriate complete quality suite.
9. Reevaluate the plan against the resulting HEAD.

Tests should protect useful behavioral boundaries rather than inventory
implementation details. High-level CLI/application seams should be protected
as they are introduced, while lower-level tests should be added only where
they protect behavior actually owned by that layer.
A newly discovered defect that can produce an incorrect manufacturing Product,
corrupt persistent manufacturing state, or cause material value-chain
inefficiency takes priority over CLI presentation work.
Every phase must leave the application production-capable.

## Common constraints

Preserve the separation between operator presentation and reusable application
behavior:

```text
CLI / TUI / GUI / API
          │
          ▼
reusable application operations
          │
          ▼
configuration / planning / engine / Products
```

Click owns parsing, terminal presentation, prompts, and translation of
structured application errors into operator-facing prose. Reusable workflow
behavior belongs below Click and should return structured domain/application
information rather than Rich objects or presentation-specific strings.
The CLI operates on the current working directory as project root. A registered
Artifact may legitimately exist under `originals/` before
`artifacts/<artifact_id>/` exists. Commands must preserve the distinction
between registered Artifact identity, materialized Artifact workspace, and
manufacturing Product state.
Missing collection directories normally represent empty collections. An
explicitly requested missing object is an operator error. Expected domain
errors should be concise and traceback-free; unexpected invariant or
programming failures must not be indiscriminately converted into ordinary
operator failures.
Routine output should be lean and oriented toward the operator's next useful
decision. Operator-facing Product paths should be concise and useful from the
project root. Do not expose Stage, resolver, dependency, or filesystem
mechanics unless they answer an operator question.
Do not change Product identity, dependency semantics, configuration precedence,
Model semantics, manufacturing ownership, persistence semantics, or color
semantics merely to simplify CLI presentation. If work exposes a genuine
architectural mismatch, resolve that mismatch explicitly against the permanent
specifications before proceeding.

Manufacturing-specific representations and operations must not be smuggled into
the generic engine or inferred solely from visual color. Preserve established
logical color identities, component registration, and existing SHAPE SVG and
3MF behavior unless an explicit Model contract change requires otherwise.

## TDD cycles

TDD remains test-first. Before implementing a meaningful new behavior, write a
test that exercises the behavioral seam or boundary being established.
The purpose of the initial failing test is not only verification. A test may
also be used to discover or clarify the appropriate seam, ownership boundary,
or contract before implementation. If the test exposes a better boundary than
the one initially assumed, refine the design and test before committing to the
implementation.
TDD cycles should normally correspond to substantial behavioral seams or
boundaries rather than individual implementation changes. Once a failing test
establishes the intended seam, implement the coherent behavior necessary to
make that seam work. Do not begin a new RED/GREEN cycle merely because that
implementation requires another helper, parameter, branch, component, or
internal refactoring.
One test may be sufficient to establish a seam. A small coherent group of tests
is appropriate when materially different cases are necessary to define the
same boundary. Prefer these high-value behavioral tests over many narrow tests
that separately inventory implementation details.
Add narrower tests when they help discover an uncertain boundary, protect an
independently meaningful contract, reproduce a defect, or address a specific
algorithmic or regression risk.

---


The operator's ordinary goal is to move customer artwork into correct, reusable manufacturing Products with the fewest necessary decisions, actions, and computations.

This plan prioritizes **source correctness**, then **efficient representation and interpretation**, then **SHAPE composition**, and finally **assembly of independently manufacturable Products**. It consolidates the existing defect backlog and SHAPE feature phases without treating future possibilities as commitments.

## Working Rules

1. **HEAD is authoritative.** At the beginning of each phase, review current HEAD and the relevant permanent specifications, code, and tests. Reconcile this plan with any work already completed.
2. **Specifications precede implementation.** Update the applicable `DEFINITION.md` and other normative contracts before writing implementation tests that assert new behavior.
3. **Use the repository's RED/GREEN/VERIFY process.** Follow `prompts/NEW_THREAD.md` and `prompts/TEST_DRIVEN_DEVELOPMENT.md`; make one coherent, testable change at a time.
4. **Preserve architectural ownership.** ARTWORK owns source interpretation and registered artwork. SHAPE owns its geometry, placement, composition, and physical manufacturing. The generic engine must not acquire model-specific policy.
5. **Reuse existing mechanisms.** Prefer existing registered geometry, Products, dependencies, and stages over new Models, generalized instance frameworks, or parallel SVG pipelines.
6. **Separate source semantics from manufacturing choices.** Transparency is not a color; physical printer colors do not define source colors; SVG visual groups do not inherently define xTool processing layers.
7. **Preserve compatibility and determinism.** Existing Artifacts, Realizations, canonical SVG, and 3MF workflows must continue to work unless an explicit specification revision states otherwise.
8. **Do not expand scope implicitly.** A phase may expose a related requirement, but that does not authorize speculative features or unrelated refactoring.
9. **Verification is required.** Run focused tests, applicable non-slow tests, Ruff, and Pyright. Add real xTool Studio acceptance checks where the contract depends on its behavior.
10. **Record outcomes.** Mark completed phases with evidence, update permanent documentation, and remove or consolidate superseded backlog entries.

## Roadmap and Dependencies

| Order | Phase | Consolidates | Primary result |
| --- | --- | --- | --- |
| 1 | ARTWORK Envelope and Source-Color Correctness | BUG-006 + BUG-004; related BUG-002 | Valid boundary-touching, transparent, single-color artwork |
| 2 | Raster-Preserving SVG Manufacturing | BUG-005 | Embedded bitmap artwork in canonical manufacturing SVG without mandatory tracing |
| 3 | Broader SVG Source Interpretation | BUG-001 + BUG-003 | Embedded PNG SVG inputs and visible stroke geometry |
| 4 | SHAPE Placement and Reusable SVG Decorations | Former SHAPE Phases 1 + 2 | Multiple independently transformed motif instances |
| 5 | SHAPE Clipping and Deterministic Planar Composition | Former SHAPE Phases 3 + 4 | Manufacturing-correct clipping and overlap behavior |
| 6 | Artwork Scaling and Boundary Policies | Former SHAPE Phase 5 | Explicit artwork enlargement with a fixed outer SHAPE boundary |
| 7 | Hierarchical SVG Manufacturing Project Assembly | Existing assembly phase | One grouped SVG containing multiple independently manufacturable Products |

**Dependency policy:** Phase 1 is the correctness foundation for raster tracing. Phase 2 supplies a useful manufacturing representation before project assembly. Phase 3 supplies the SVG interpretation needed by reusable decorations. Phase 4 precedes decoration clipping; Phase 5 supplies composition rules reused by Phase 6. Phase 7 uses established manufacturing Products rather than rebuilding them.

Phases 2 and 3 are substantially independent after their contracts are defined. Their relative order may change if a demonstrated customer workflow warrants it. Phase 7 may begin with an architectural spike earlier, but its implementation should not preempt the correctness and representation contracts it consumes.

---

## Phase 1 — ARTWORK Envelope and Source-Color Correctness

**Status:** OPEN — Specification review and implementation pending.

### Purpose

Correct valid raster artwork that touches image boundaries and establish coherent source-driven foreground color semantics. Combine the overlapping color requirements of BUG-006 and BUG-004 rather than implementing two competing color-discovery policies.

### Reproductions

- `tests/fixtures/artwork/bug06.png` — black foreground on a transparent PNG, including foreground that touches image boundaries; currently reported to fail during envelope cleanup.
- Existing transparent and explicitly colored SVG fixtures, plus small synthetic cases for single-color and multicolor interpretation.

The reproduction path is recorded in the prior backlog; verify the fixture exists at current HEAD before relying on it.

### Contract to Resolve

1. Foreground pixels on any image edge are valid artwork. Exterior transparency and enclosed transparent regions must remain distinguishable.
2. Shrinkwrap and envelope cleanup must not remove meaningful boundary-touching geometry or require transparent padding.
3. Preserve original source dimensions and coordinates; generate a valid, closed envelope.
4. Count meaningful **foreground colors**, not fully transparent pixels or incidental antialiasing variations.
5. Support exactly one foreground color and `artifact_color_count = 1`.
6. Specify whether automatic color discovery is the default or an explicit mode, and how an explicit user override interacts with it.
7. Define source color counting independently of the number or identities of `printer_colors`; retain physical color mapping as a separate concern.
8. Distinguish transparent backgrounds from explicitly authored colored backgrounds, including SVGs that are rasterized.
9. Preserve existing multicolor and native vector behavior unless a deliberate specification revision requires otherwise.

**Specification decision:** Current ARTWORK documentation permits deriving a PNG tracing count from the number of printer colors. Replacing that behavior with source-driven discovery is a normative change; decide the exact default and override contract before RED tests.

### TDD Work

**RED**

- Reproduce boundary-touching shrinkwrap failure with `bug06.png`.
- Isolate edge handling, enclosed holes, alpha thresholds, and small-component cleanup with synthetic images.
- Establish single-color and multicolor source-count tests, including antialiasing and partial transparency.
- Test transparent versus explicitly colored backgrounds and independence from `printer_colors`.
- Verify explicit count overrides according to the revised contract.

**GREEN**

- Correct envelope and cleanup behavior at image boundaries.
- Implement only the specified source-color discovery and count resolution.
- Avoid artificial background layers and unnecessary tracing partitions.

**VERIFY**

- Build the real reproduction through the ordinary `artifact build` path.
- Verify correct geometry and one foreground partition for single-color input.
- Confirm existing multicolor, SVG, and SHAPE incorporation workflows remain compatible.
- Run required tests and quality checks.

### Completion

Boundary-touching artwork builds without padding; transparency does not become a manufacturing color; single-color input is supported; source-color policy is specified and tested; existing workflows remain compatible.

---

## Phase 2 — Raster-Preserving SVG Manufacturing

**Status:** OPEN — Specification and implementation pending.

### Purpose

Allow canonical manufacturing SVG output to carry raster artwork as an embedded bitmap instead of requiring it to be traced into vector geometry. This is especially valuable for laser engraving while retaining vector outlines, labels, ridges, and cut contours.

### Architectural Boundaries

- Preserve raster content and alpha where possible, with physical dimensions, scaling, orientation, and registration established by SHAPE.
- Reuse ARTWORK preparation and existing SHAPE placement/composition; do not create a second raster interpretation pipeline.
- Select raster preservation explicitly versus existing traced-vector output; preserve the vector workflow.
- Keep xTool-specific processing policy outside the generic ARTWORK and SHAPE contracts.
- Preserve source data and self-containment without introducing unnecessary 3MF or printer-color work when only manufacturing SVG is requested.
- Distinguish canonical SVG manufacturing output from ARTWORK's intermediate traced representations.

### TDD Work

**RED**

1. A standalone PNG produces a manufacturing SVG with an embedded `<image>`.
2. Image bytes are self-contained and repeatable; no external asset reference is required.
3. Alpha, aspect ratio, physical size, rotation, and SHAPE registration are preserved.
4. Raster artwork coexists with vector engraving, labels, ridges, and cut geometry.
5. Raster preservation does not depend on `printer_colors`.
6. Existing traced-vector output remains selectable and unchanged by default.

**GREEN**

Implement the smallest representation selection and data flow that meet the contract. Reuse existing registered placement and SVG composition instead of adding unrelated stages or Models.

**VERIFY**

Inspect the generated SVG and import representative outputs into xTool Studio. Verify raster engraving can be assigned independently of cutting geometry and that physical dimensions remain correct. Run required tests and quality checks.

### Completion

An operator can manufacture a SHAPE from embedded raster artwork and vector structural features without mandatory tracing, while existing SVG and 3MF workflows remain compatible.

---

## Phase 3 — Broader SVG Source Interpretation

**Status:** OPEN — Specification and implementation pending.

### Purpose

Accept two common forms of valid customer-authored SVG that the existing ARTWORK pipeline does not fully support: SVG documents containing an embedded PNG, and geometry whose visible appearance is defined by strokes.

These are distinct testable slices under one source-compatibility phase. Implement and verify them separately.

### Slice A — Embedded PNG in SVG (BUG-001)

**Reproduction:** `bug01.svg`, an xTool Studio-exported SVG containing a Base64 PNG. Confirm the fixture's location at current HEAD.

**Required behavior**

1. Recognize one embedded Base64 PNG `<image>` element.
2. Decode it without unnecessary pixel alteration; preserve alpha.
3. Respect document dimensions, `viewBox`, image placement, and applicable transforms.
4. Integrate the image into the established ARTWORK processing path.
5. Preserve standalone PNG and native vector SVG behavior.
6. Provide actionable diagnostics for unsupported cases.

Initially exclude multiple images, mixed image/vector content, external image references, additional raster formats, and general-purpose SVG rendering unless a current permanent specification already requires them.

### Slice B — Stroke-Only and Mixed SVG Geometry (BUG-003)

**Reproduction:** `tests/fixtures/artwork/bug02.svg`, a transparent 600 × 600 SVG with a black, unfilled circle stroke touching the canvas boundary. Confirm fixture availability at current HEAD.

**Required behavior**

1. Interpret visible strokes, not merely filled path interiors.
2. Support supported SVG shapes and paths, including circles, ellipses, rectangles, lines, polylines, and paths.
3. Respect stroke width, color, caps, joins, and transforms.
4. Preserve transparent interiors of unfilled shapes.
5. Support mixed stroke-and-fill geometry without losing either.
6. Preserve registered color semantics, overlap rules, and deterministic manufacturing geometry.
7. Reuse ARTWORK's interpretation machinery; do not implement stroke semantics separately inside SHAPE decorations.

### TDD Work

**RED:** Add reproduction tests and minimal synthetic cases for each slice, including dimensions, transparency, transforms, deterministic results, and explicit unsupported cases.

**GREEN:** Implement the smallest coherent source-interpretation extensions against revised ARTWORK specifications.

**VERIFY:** Build both reproduction fixtures through `artifact build`; verify existing PNG, filled SVG, and multicolor behavior; run required tests and quality checks.

### Completion

The supported embedded-image and stroke-only SVG cases build correctly, produce registered geometry or raster representation as specified, and do not introduce competing SVG semantics.

---

## Phase 4 — SHAPE Placement and Reusable SVG Decorations

**Status:** OPEN — Specification and implementation pending.

### Purpose

Allow SHAPE to incorporate externally authored decorative SVG motifs—stars, diamonds, flourishes, serifs, filigree, and similar geometry—as independently positioned instances. Reuse one source at multiple positions without copying source files or creating separate ARTWORK Realizations.

This combines the former placement-contract and reusable-decoration phases: placement should be defined only to the extent needed by a real decoration use case.

### Architectural Boundaries

- SHAPE owns source references, instance identity, placement, composition, and physical manufacturing.
- ARTWORK owns the reusable SVG source interpretation contract; SHAPE must not invoke another Model's Stage implementation directly.
- Reuse registered coordinate space and existing SHAPE Structure/Compose/Extrude/Package boundaries.
- Keep source interpretation, instance transforms, and color overrides separate.
- Preserve authored geometry, logical colors, and source proportions unless explicitly overridden.
- Do not introduce a generalized component-instance or dependency framework merely for anticipated future Models.

### Work

1. Inspect current registered Artwork placement, SHAPE composition, component identities, and existing transformation helpers.
2. Specify the smallest SHAPE configuration for a decoration source and multiple named instances.
3. Define translation, uniform scaling, rotation, transform order, and registered-to-physical placement.
4. Preserve independent instance identities when two instances share one SVG source.
5. Define optional logical color overrides without silently replacing authored colors.
6. Carry decoration geometry through canonical SVG and 3MF manufacturing.
7. Validate unsupported source constructs, invalid references, transforms, and colors clearly.
8. Preserve all existing SHAPE behavior when decorations are absent.

### TDD Work

**RED:** One motif reused at two or more locations with different transforms, stable registration, separate identities, correct colors, and validation failures.

**GREEN:** Implement placement and decoration incorporation together using existing mechanisms.

**VERIFY:** Build a representative decorated SHAPE into both SVG and 3MF; check registration, dimensions, identities, and compatibility. Run required tests and quality checks.

### Completion

Reusable SVG decorations participate in SHAPE manufacturing with independent transforms and semantic identities, without speculative infrastructure or regressions.

---

## Phase 5 — SHAPE Clipping and Deterministic Planar Composition

**Status:** OPEN — Specification and implementation pending.

### Purpose

Allow a positioned decoration to be restricted to a selected SHAPE region, and define deterministic overlap behavior among decorations, Artwork, ridges, labels, QR codes, and other participating components.

This combines the former clipping and planar-composition phases because clipping and overlap precedence must yield one coherent manufacturing result, not merely the right SVG appearance.

### Architectural Boundaries

- SHAPE remains authoritative for Base, Artwork, Inner Ridge, Outer Ridge, and other region geometry.
- Clipping modifies participating geometry, not merely SVG visibility.
- Planar precedence is distinct from physical Z dimensionalization.
- Preserve common registration, component identity, logical colors, and valid physical partitions.
- Do not silently allow conflicting positive-area manufactured overlaps between different logical colors.
- Reuse existing overlap, subtraction, and partitioning machinery; prefer fixed semantic precedence over configurable ordering unless real use cases demand it.
- Preserve existing default Artwork fitting and SHAPE composition.

### Work

1. Define selectable clipping regions initially considering Base, Artwork, Inner Ridge, and Outer Ridge.
2. For each region, explicitly define whether it means enclosed area, occupied physical area, or another precise geometric domain.
3. Define absent/empty-region behavior and how clipping interacts with transforms and color-separated components.
4. Review current overlap precedence among existing SHAPE Features before adding decoration-specific behavior.
5. Establish deterministic semantics for supported overlaps, distinguishing visibility, material ownership, and physical partitioning.
6. Clip against authoritative registered geometry and preserve resulting component identities.
7. Reject ambiguous or unsupported overlap combinations with actionable diagnostics.
8. Carry the resulting geometry consistently into canonical SVG and raised/inlaid 3MF manufacturing.

### TDD Work

**RED:** Boundary-crossing motifs clipped to different regions; missing-region validation; overlaps between decorations and representative SHAPE Features; cases with different logical colors.

**GREEN:** Implement only missing clipping, precedence, subtraction, or partitioning behavior.

**VERIFY:** Confirm that clipping affects physical geometry, not just SVG display; inspect SVG and 3MF results; protect existing composition behavior; run required tests and quality checks.

### Completion

Supported clipping and overlap cases have documented, deterministic manufacturing semantics. SVG and 3MF agree on occupied regions and component identities, with no unintended changes to existing SHAPE configurations.

---

## Phase 6 — Artwork Scaling and Boundary Policies

**Status:** OPEN — Specification and implementation pending.

### Purpose

Permit incorporated Artwork to grow beyond its initial fitting region while preserving a deliberate relationship between Artwork extent, internal SHAPE regions, and the outer manufacturing boundary.

The initial policy is **clip**. More expansive boundary behavior is deferred.

### Architectural Boundaries

- Existing Artwork fitting and registration remain the default.
- Artwork scaling, clipping, nominal SHAPE boundary, and manufactured envelope are separate concepts.
- Preserve aspect ratio, logical color identity, and registration.
- Do not automatically enlarge the Base or alter `shape_size` when Artwork grows.
- Reuse the placement, clipping, and composition contracts from Phases 4 and 5.
- Do not implement `extend` or `expand` without a separate manufacturing specification.

### Work

1. Review existing Artwork fit/scale behavior and the new SHAPE placement and clipping contracts.
2. Define explicit enlargement beyond the initial Artwork fitting region.
3. Establish initial `clip` semantics:
   - Artwork may cross internal SHAPE regions.
   - Artwork beyond the nominal SHAPE boundary is clipped.
   - Base dimensions, `shape_size`, and the outer cut contour remain unchanged.
4. Define interactions with ridges, labels, QR codes, and decorations using established planar precedence.
5. Preserve correct raised and inlaid manufacturing.
6. Record `extend` and `expand` as deferred possibilities, not automatic consequences of scaling.

### TDD Work

**RED:** Enlarged Artwork crosses an internal boundary and the nominal outer boundary while preserving aspect ratio, registration, component identity, and fixed Base dimensions.

**GREEN:** Extend existing Artwork fitting and clipping rather than introducing an alternate composition path.

**VERIFY:** Check canonical SVG and 3MF, including raised and inlaid cases; confirm unchanged default fitting behavior; run required tests and quality checks.

### Completion

Explicit Artwork enlargement is manufacturing-correct under the `clip` policy, and existing SHAPE dimensions and default Artwork behavior remain stable.

---

## Phase 7 — Hierarchical SVG Manufacturing Project Assembly

**Status:** OPEN — Architectural review, specification, and implementation pending.

### Purpose

Combine multiple existing, independently manufacturable Products into one self-contained, hierarchically grouped SVG document for xTool Studio import.

This is a **manufacturing project assembly operation**, not a new ARTWORK or SHAPE interpretation pipeline. It should consume completed Products without rebuilding their geometry.

### Example Project

```text
manufacturing-project.svg
└── project
    ├── coaster-front
    │   ├── engraving
    │   └── cut-outline
    ├── coaster-back
    │   └── engraving
    ├── keychain-front
    │   ├── engraving
    │   └── cut-outline
    ├── keychain-back
    │   └── engraving
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

**XTS behavior must be observed, not inferred.** If XTS changes the authored hierarchy, document the observed behavior and revise the export contract before considering the phase complete.

### TDD Work

**RED**

- Assemble multiple representative coaster, keychain, and sticker Products.
- Verify exact group depth and stable, unique IDs.
- Preserve physical dimensions, independent placement, and nested component identities.
- Preserve embedded raster data, SVG definitions, and internal references.
- Verify deterministic output and unchanged source Products.
- Reject unsupported or incompatible Product representations clearly.

**GREEN**

Implement the smallest reusable assembly operation using established Product, SVG, coordinate, and registration mechanisms. Do not add a new Model, Stage, or generalized project framework without a demonstrated architectural need.

**VERIFY**

Import representative assemblies into xTool Studio and verify grouping, ungrouping, dimensions, raster/vector registration, and independent processing assignments. Run required tests and quality checks.

### Completion

Multiple existing Products can be imported as one manufacturing SVG, remain independently identifiable and positionable, and retain usable component grouping and registration in XTS.

---

## Deferred Work and Explicit Non-Goals

These are not additional active phases. Revisit them only when a real manufacturing requirement justifies a separate specification and plan:

- Native `.xs` multi-canvas project generation or reverse-engineering.
- A generalized component-instance framework or new BANNER Model.
- Multiple embedded raster images, mixed image/vector SVG input, external image links, or arbitrary SVG rendering beyond the initial Phase 3 contract.
- Artwork boundary `extend` or `expand` policies.
- Configurable general-purpose layer ordering when fixed semantic precedence suffices.
- Automatic assignment of xTool processing parameters from arbitrary SVG groups or colors.
- Broader project management, nesting optimization, or machine-specific manufacturing orchestration.

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

