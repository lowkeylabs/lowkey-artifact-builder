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

### Primary Optimization Objective — Minimize Time to Manufacture

The principal purpose of `lowkey-artifact-builder` is to minimize the operator effort required to transform customer-supplied artwork into manufacturing-ready customized Products.

The primary commercial use case is economical one-off and small-batch manufacturing for `lowkeylabs LLC`, including coasters, keychains, ornaments, stickers, engraved glassware, stamps, and other personalized objects.

The software shall optimize the preparation workflow rather than the physical execution speed of lasers, printers, or other manufacturing devices.

The desired operator workflow is:

```text
Customer artwork + customization
                ↓
         artifact create
                ↓
    Reusable managed Artwork
                ↓
     Product configurations
                ↓
         artifact build
                ↓
  Manufacturing-ready Products
                ↓
   Manufacturing package assembly
                ↓
      Grouped SVG / XTS project
                ↓
         xTool Studio
                ↓
          Manufacture
```

A single customer Artwork may be reused across multiple Products, product faces, dimensions, and manufacturing methods.

Product-specific defaults shall minimize repeated configuration decisions. Customization shall focus on meaningful customer choices, such as artwork, labels, messages, and product selection.

Manufacturing packages shall organize multiple independently manufacturable Products into a convenient importable representation, initially using hierarchical SVG grouping and potentially native multi-canvas `.xs` projects.

The operator shall not need to understand or manually select internal processing Stages to perform ordinary manufacturing tasks.

Requested Products and their dependencies shall determine the minimum necessary processing.

### Success Measures

Evaluate proposed features primarily by their ability to:

1. Reduce operator actions between artwork receipt and manufacturing readiness.
2. Reduce repeated work when creating multiple Products from the same Artwork.
3. Reduce manual positioning, scaling, labeling, grouping, and operation preparation in XTS.
4. Preserve manufacturing correctness, physical dimensions, and registration.
5. Support rapid customization without requiring new source code or product-specific programming.
6. Reuse existing Artwork and manufacturing Products without unnecessary recomputation.
7. Maintain reliable, deterministic outputs and a simple operator interface.

Avoid adding architectural complexity unless it provides measurable improvements in manufacturing preparation, correctness, or reuse.


---

## Phase — Hierarchical SVG Manufacturing Project Assembly

### Purpose

Enable `lowkey-artifact-builder` to combine multiple independently manufacturable Products into one self-contained, hierarchically grouped SVG document for import into xTool Studio (XTS).

The operator shall be able to import one SVG, ungroup it once to expose individual product groups, and subsequently ungroup individual products to access their manufacturing components.

This capability is independent of native `.xs` project generation and does not require separate XTS canvases.

### Manufacturing Workflow

The initial use case combines multiple products and product faces into one SVG:

```text
manufacturing-project.svg
├── coaster-front
│   ├── engraving
│   └── cut-outline (optional)
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

Each product group is independently positioned within the SVG workspace.

Each product may contain multiple manufacturing components, including raster images, vector artwork, and cutting geometry.

### Required Behavior

1. Accept multiple existing manufacturing Products for assembly into one SVG document.
2. Represent each product or product face as an independent, named top-level SVG group.
3. Preserve nested groups representing the product's manufacturing components.
4. Preserve the hierarchy of existing SVG groups where semantically meaningful.
5. Support native vector geometry and embedded raster images.
6. Preserve physical dimensions, scaling, orientation, transparency, and artwork registration.
7. Support independent positioning of product groups within the combined workspace.
8. Assign stable, unique SVG identifiers without collisions between incorporated Products.
9. Produce deterministic, self-contained SVG output.
10. Preserve original manufacturing Products without modification.
11. Avoid unnecessary tracing, extrusion, 3MF packaging, or physical printer-color assignment when producing grouped SVG output.
12. Preserve existing standalone SVG and 3MF manufacturing behavior.

### Grouping and Ungrouping Contract

The SVG hierarchy shall be intentionally structured for XTS's one-level-at-a-time Ungroup behavior.

The intended interaction is:

**Initial import**

The combined SVG is available as one grouped manufacturing project containing independently identifiable product groups.

**First Ungroup**

Ungrouping the outer project group exposes the immediate product groups:

- Coaster Front
- Coaster Back
- Keychain Front
- Keychain Back
- Sticker Front

Each product remains internally grouped.

**Subsequent Ungroup**

Ungrouping an individual product exposes its immediate manufacturing components, such as engraving artwork and cutting geometry.

Nested component groups remain intact until explicitly ungrouped.

The generated SVG shall not introduce unnecessary wrapper groups that require additional ungroup operations.

The expected interaction shall be verified against actual XTS import behavior rather than inferred solely from the SVG document structure.

### SVG Structure

Use standard SVG `<g>` elements to represent semantic group boundaries.

The preferred hierarchy is:

```text
SVG document
└── manufacturing project group
    ├── product group
    │   ├── operation/component group
    │   │   └── geometry or embedded raster
    │   └── operation/component group
    └── product group
        └── operation/component group
```

Each meaningful group shall have a stable, unique identifier.

Preserve source geometry and transformations while ensuring that incorporated Products occupy the intended physical positions.

When combining existing SVG documents, resolve nested coordinate systems, transforms, definitions, references, and identifiers without changing their rendered appearance.

### Groups Versus XTS Processing Layers

SVG groups and XTS processing layers are distinct concepts.

**SVG groups** organize related manufacturing objects and preserve product identity.

**XTS processing layers** associate objects with machine operations and processing parameters.

A product group may contain components requiring different operations, including:

- Raster engraving.
- Vector engraving.
- Cutting.
- Printable artwork.

Do not assume that SVG group boundaries automatically establish XTS processing layers.

Do not infer manufacturing operations solely from visible SVG colors.

Preserve explicit semantic operation identities within the generated SVG, while allowing XTS to assign the actual machine processing settings.

Investigate whether XTS can reliably recognize or preserve operation-specific grouping, colors, identifiers, or other supported SVG attributes during import.

Do not invent undocumented XTS metadata conventions.

### Architectural Review

Review current HEAD, the permanent specifications, and existing manufacturing Products.

Determine:

1. Which existing Products are suitable inputs for grouped SVG assembly.
2. Whether assembly belongs in an application-level operation, an existing Model realization, or another established architectural boundary.
3. How existing SVG component identities and group hierarchies are represented.
4. How physical placement and coordinate normalization should be handled.
5. How embedded raster images are preserved.
6. How identifiers and SVG references are safely merged.
7. How the assembly operation can avoid rebuilding unchanged Products.
8. How manufacturing operation identities remain distinct from SVG visual styling.

Prefer composition of existing manufacturing Products over reexecuting their ARTWORK or SHAPE processing.

Do not introduce XTS-specific behavior into the generic build engine.

Update the applicable permanent specifications before implementing new behavior.

### Test-Driven Implementation

**RED — Establish the assembly contract**

Create a coherent test set demonstrating:

1. Multiple manufacturing Products can be combined into one SVG.
2. The document contains one explicit outer project group.
3. The immediate children of that group are the individual product groups.
4. Each product retains its internal manufacturing component groups.
5. No unnecessary wrapper groups alter the intended ungrouping depth.
6. Every group has a stable, unique identifier.
7. Physical dimensions, transforms, and placement are preserved.
8. Embedded raster content remains self-contained.
9. Source SVG definitions and references remain valid after merging.
10. Repeated assembly produces deterministic output.
11. Original Products remain unchanged.

Include representative coaster, keychain, and sticker Products.

**GREEN — Implement grouped SVG assembly**

Implement the smallest reusable capability satisfying the specified assembly contract.

Reuse existing SVG composition, coordinate, registration, and Product mechanisms where appropriate.

Do not introduce new Models, Stages, or generalized project infrastructure unless the architectural review establishes a concrete requirement.

**VERIFY — XTS manufacturing acceptance**

Import the generated SVG into XTS and verify:

1. The combined SVG is recognized as one grouped object.
2. One Ungroup operation exposes the individual product groups.
3. Each product retains its internal grouping.
4. Ungrouping one product exposes its immediate manufacturing components.
5. Other product groups remain unaffected.
6. Raster images, vector geometry, and cutting contours remain correctly registered.
7. Physical dimensions and positions are preserved.
8. Engraving, cutting, and printing operations can be assigned to the intended objects without unintentionally affecting other products.

If XTS does not preserve the authored SVG hierarchy, document the observed import behavior and revise the export contract before implementation is considered complete.

### Relationship to Native `.xs` Projects

Grouped SVG assembly is the initial manufacturing project packaging capability.

Native `.xs` multi-canvas project generation remains a separate, optional investigation.

Do not make grouped SVG assembly dependent on reverse-engineering the `.xs` format.

### Completion Criteria

This phase is complete when:

- Multiple independently manufacturable Products can be packaged into one SVG.
- Product and component identities remain distinct.
- SVG hierarchy is deterministic and structurally correct.
- One-level-at-a-time ungrouping behaves as intended in XTS.
- Raster and vector content retain their intended appearance and physical registration.
- Manufacturing operations can be independently assigned in XTS.
- Existing standalone manufacturing Products remain compatible.
- Focused tests, applicable non-slow tests, Ruff, and Pyright pass.
- Applicable permanent specifications document the new capability.

### Status

**OPEN — Architectural review, specification, and implementation pending.**

Implementation shall follow the repository's specification-first, RED/GREEN test-driven development process.


---

## BUG-006 — Single-Color Raster Artwork and Boundary-Touching Shrinkwrap

### Problem

The ARTWORK model fails to prepare a valid transparent PNG containing black foreground artwork when that artwork touches the image boundaries.

Reproduction fixture: `tests/fixtures/artwork/bug06.png`

The current failure occurs in `model/models/artwork/stages/prepare.py`, during envelope construction:

```text
PrepareError: No meaningful foreground remains after envelope cleanup.
```

The image also exposes a separate color-processing requirement: ARTWORK must support artwork containing exactly one foreground color, without treating transparency as a second color or requiring multiple configured printer colors.

### Required Behavior

**A. Shrinkwrap and envelope construction**

1. Recognize foreground pixels that touch any edge of the image.
2. Correctly distinguish the transparent exterior from transparent interior regions.
3. Produce a valid, closed envelope around the visible foreground, including segments coincident with image boundaries.
4. Do not discard meaningful foreground geometry merely because it intersects the image boundary.
5. Preserve the original image dimensions and coordinates.
6. Do not require users to add transparent padding to otherwise valid artwork.

**B. Artwork color discovery**

1. Determine the effective number of foreground colors represented in the source artwork.
2. Exclude fully transparent pixels from foreground color counting.
3. Account for antialiasing, partial transparency, and insignificant pixel-level color variations.
4. Support exactly one foreground color.
5. Permit `artifact_color_count = 1`.
6. Do not infer the source artwork's color count from the configured `printer_colors` palette size.
7. When automatic color discovery is enabled, derive `artifact_color_count` from the effective foreground colors.
8. Preserve explicit user color-count overrides where supported, subject to the ARTWORK specification.
9. Ensure that a single-color image produces one meaningful artwork color partition without manufacturing an artificial background layer.

### Specification Review

Before implementation:

- Review `model/models/artwork/DEFINITION.md`.
- Review the envelope and shrinkwrap contracts.
- Review `artifact_color_count` validation, defaults, and parameter derivation.
- Review the relationship between source color discovery, raster quantization, tracing, and printer color assignment.
- Specify whether automatic color discovery is the default or an explicitly selected mode.
- Update the normative specification before modifying production code.

### Test-Driven Implementation

**RED — Regression tests**

Using `bug06.png`:

- Verify that meaningful foreground survives envelope cleanup.
- Verify that the envelope correctly handles artwork touching all four image edges.
- Verify that transparent interior regions do not invalidate the envelope.
- Verify that the image is recognized as effectively single-color artwork.
- Verify that `artifact_color_count = 1` is accepted.
- Verify that automatic color discovery produces one foreground color partition.
- Verify that varying `printer_colors` does not change the discovered source color count.

Add smaller synthetic fixtures to isolate boundary handling from color discovery.

**GREEN — Implementation**

- Correct envelope construction for boundary-touching foreground geometry.
- Correct color-count validation and automatic discovery as specified.
- Preserve the existing ARTWORK pipeline and manufacturing invariants.
- Avoid introducing artificial background colors or unnecessary color partitions.

**VERIFY**

- Run focused ARTWORK regression tests.
- Run the applicable non-slow test suite.
- Run Ruff and Pyright.
- Verify `bug06.png` through the ordinary `artifact build` workflow.
- Confirm that existing multicolor artwork remains compatible.

### Completion Criteria

BUG-006 is complete when:

- `bug06.png` builds successfully.
- Shrinkwrap produces a correct envelope without requiring transparent padding.
- Single-color transparent artwork is accepted.
- `artifact_color_count = 1` is valid.
- Automatic color discovery identifies one effective foreground color.
- Transparency does not generate an additional manufacturing color.
- Existing multicolor workflows remain compatible.
- Regression tests and quality checks pass.

### Relationship to Existing Defects

- **BUG-002:** Boundary-touching shrinkwrap failure. `bug06.png` is now a concrete reproduction fixture.
- **BUG-004:** Source-aware color counting. BUG-006 adds the explicit requirement to support a color count of one.
- **BUG-005:** Raster preservation in SVG output. This is complementary but independent.

### Status

**OPEN — Specification review and implementation pending.**

No production changes are authorized by recording this defect. Implementation shall follow specification-first, RED/GREEN test-driven development.


---

## BUG-001 — Support Embedded Raster Images in SVG Artwork

### Problem

The ARTWORK model rejects valid SVG documents containing embedded raster images.

The failure occurs during the `prepare` stage in:

`src/lowkey_artifact_builder/model/models/artwork/stages/prepare.py`

The current implementation raises:

```text
PrepareError: Embedded raster images are unsupported in native SVG artwork.
```

The reported reproduction fixture, `bug01.svg`, is an SVG exported by xTool Studio containing a Base64-encoded PNG image.

Although the SVG is valid and renders correctly in a browser, `artifact build` fails.

### Required Behavior

ARTWORK shall accept SVG documents containing a single embedded raster image, subject to the following requirements:

1. Recognize an SVG `<image>` element containing a Base64-encoded PNG.
2. Decode the embedded raster without unnecessarily altering its pixel content.
3. Preserve transparency, including the PNG alpha channel.
4. Interpret the SVG coordinate system, physical dimensions, image placement, and applicable transformations correctly.
5. Integrate the raster into the existing ARTWORK preparation and manufacturing pipeline.
6. Preserve existing behavior for native vector SVG and standalone raster artwork.
7. Report unsupported SVG image configurations through actionable, user-facing diagnostics rather than an unexplained traceback.

An SVG containing an embedded raster shall not be rejected solely because its artwork is raster-based.

### Scope

The initial implementation shall support SVG documents containing one embedded PNG image.

The following are outside the initial scope unless existing ARTWORK contracts already require them:

- Multiple embedded raster images.
- Mixed raster and vector artwork.
- Externally referenced raster images.
- Additional embedded raster formats.
- General-purpose SVG rendering or rasterization.

These cases shall not be silently treated as supported.

### Specification Review

Before implementation:

1. Review `model/models/artwork/DEFINITION.md` for existing SVG and raster input contracts.
2. Identify any normative restrictions that conflict with the required behavior.
3. Update the specification before modifying production code.
4. Preserve existing ARTWORK invariants concerning dimensions, transparency, colors, and manufacturing output.

Implementation details shall be derived from the revised specification rather than assumed from the current code.

### Test-Driven Implementation

**RED — Reproduce and specify the defect**

- Add a regression test using `bug01.svg`.
- Add a minimal synthetic SVG fixture containing a Base64-encoded PNG.
- Verify successful recognition and preparation of the embedded raster.
- Verify preservation of transparency, dimensions, and placement.
- Verify deterministic output.
- Verify that existing standalone PNG and vector SVG workflows remain unchanged.
- Add focused negative tests for unsupported embedded-image configurations.

The regression test must fail against the existing implementation for the expected reason.

**GREEN — Correct the implementation**

- Implement the smallest change that satisfies the revised ARTWORK contract.
- Reuse existing raster preparation behavior where appropriate.
- Avoid introducing a separate, inconsistent raster-processing pipeline.
- Do not introduce unrelated SVG features or architectural changes.

**VERIFY — Regression and quality checks**

- Run focused ARTWORK tests.
- Run the applicable non-slow test suite.
- Run Ruff and Pyright.
- Verify the original `bug01.svg` through the ordinary `artifact build` workflow.
- Confirm that previously supported SVG and raster inputs produce unchanged results.

### Completion Criteria

BUG-001 is complete when:

- `bug01.svg` builds successfully.
- Embedded PNG transparency and placement are preserved.
- Existing ARTWORK behavior remains compatible.
- Unsupported configurations receive clear diagnostics.
- Regression tests and required quality checks pass.
- The ARTWORK definition documents the supported SVG raster behavior.

### Status

**OPEN — Specification and implementation pending.**

Reproduction fixture: `bug01.svg`

No production code changes are authorized by recording this defect. Implementation shall follow the repository's established specification-first, RED/GREEN test-driven development process.


---

## BUG-003 — Support Stroke-Only SVG Artwork

### Problem

The ARTWORK model rejects valid SVG documents containing visible geometry defined entirely by strokes, without filled regions.

The failure occurs during the `raster` stage in:

`src/lowkey_artifact_builder/model/models/artwork/stages/raster.py`

The current implementation raises:

```text
RasterError: Native SVG contains no supported filled paths.
```

The reproduction fixture, `bug02.svg`, contains:

- A transparent 600 × 600 px SVG canvas.
- One centered circle.
- A black stroke, 5 px wide.
- No fill (`fill="none"`).
- A visible stroke extending to all four canvas boundaries.

The SVG renders correctly in standard SVG viewers but cannot be processed by ARTWORK.

### Required Behavior

ARTWORK shall accept valid SVG documents containing visible stroked geometry, regardless of whether the geometry has a fill.

1. Recognize SVG strokes as visible artwork, independently of filled regions.
2. Support stroke-only shapes and paths, including circles, ellipses, rectangles, lines, polylines, and arbitrary paths within the supported SVG geometry contract.
3. Respect stroke color, width, line caps, line joins, and applicable transformations.
4. Preserve transparent regions, including the interior of unfilled closed shapes.
5. Interpret visible strokes according to their rendered geometry rather than treating their centerlines as filled boundaries.
6. Support documents containing both stroked and filled geometry without losing either.
7. Preserve existing ARTWORK behavior for filled SVG paths and standalone raster artwork.
8. Produce deterministic manufacturing geometry consistent with the visible SVG artwork.

An SVG shall not be rejected solely because its visible geometry is represented by strokes rather than fills.

### Specification Review

Before implementation:

1. Review `model/models/artwork/DEFINITION.md` for normative SVG geometry, color, transparency, and rasterization contracts.
2. Identify existing restrictions on stroke-only geometry.
3. Define the supported stroke semantics, including how stroke width and transforms affect visible geometry.
4. Update the ARTWORK specification before changing production code.
5. Preserve existing manufacturing and color-partitioning invariants.

### Test-Driven Implementation

**RED — Reproduce and specify the defect**

- Add a regression test using `bug02.svg`.
- Verify that a stroke-only circle is accepted.
- Verify that the visible stroke is preserved at its specified width.
- Verify that the circle's interior remains transparent.
- Verify correct handling of strokes touching the SVG canvas boundary.
- Add focused tests for open paths, line caps, line joins, and transformed strokes.
- Add a mixed stroke-and-fill regression case.
- Verify that existing filled-path SVG behavior remains unchanged.

The primary regression test must fail against the existing implementation for the expected reason.

**GREEN — Correct the implementation**

- Implement the smallest coherent correction satisfying the revised ARTWORK contract.
- Reuse existing SVG geometry and raster-processing mechanisms where appropriate.
- Avoid converting stroke-only artwork into incorrectly filled shapes.
- Preserve color, transparency, dimensions, and placement.
- Avoid unrelated changes to shrinkwrap or other ARTWORK stages.

**VERIFY — Regression and quality checks**

- Run focused ARTWORK tests.
- Run the applicable non-slow test suite.
- Run Ruff and Pyright.
- Verify that `bug02.svg` completes the ordinary `artifact build` workflow.
- Confirm that existing filled SVG artwork continues to produce compatible results.

### Completion Criteria

BUG-003 is complete when:

- `bug02.svg` builds successfully.
- Stroke-only geometry is correctly represented in the resulting artwork.
- Stroke width, color, transparency, and placement are preserved.
- Mixed stroke-and-fill SVG documents behave according to the ARTWORK specification.
- Existing filled-path workflows remain compatible.
- Regression tests and required quality checks pass.
- The ARTWORK definition documents supported SVG stroke behavior.

### Status

**OPEN — Specification and implementation pending.**

Reproduction fixture: `tests/fixtures/artwork/bug02.svg`

No production changes are authorized by recording this defect. Implementation shall follow the repository's specification-first, RED/GREEN test-driven development process.

---

## BUG-004 — Derive SVG Raster Tracing Colors from Source Artwork

### Problem

When ARTWORK rasterizes an SVG containing a limited number of colors, the bitmap tracing process may use the configured `printer_colors` count rather than the actual colors present in the source artwork.

For example, an SVG containing black text and black graphics on a transparent background has one visible foreground color. However, rasterization may assign a default background color and tracing may attempt to extract additional color regions based on the configured printer palette.

This can produce incorrect color partitions, unnecessary traced layers, or geometry that does not correspond to the source artwork.

### Required Behavior

1. Determine the colors represented in the source SVG independently of the configured printer palette.
2. Distinguish transparent regions from explicitly colored background regions.
3. Treat transparency as the absence of artwork, not as an additional source color.
4. Preserve explicitly authored background colors as artwork where required by the ARTWORK specification.
5. Do not introduce a default background color into source color counting.
6. Determine the number of tracing regions from the actual source artwork and the applicable ARTWORK color-processing contract.
7. Use `printer_colors` for manufacturing color assignment or mapping, not as an implicit source-color count.
8. Preserve existing behavior for native vector SVG and standalone raster artwork unless the specification explicitly requires a change.

### Specification Review

Before implementation:

- Review `model/models/artwork/DEFINITION.md` for source color discovery, transparency, rasterization, tracing, and printer color mapping.
- Identify where default background colors enter the processing pipeline.
- Determine how SVG colors and raster pixel colors are currently classified.
- Define the relationship between source color regions, tracing layers, and manufacturing color assignments.
- Specify handling of antialiasing and intermediate raster colors without treating every distinct pixel value as an independent authored color.
- Update the normative ARTWORK definition before changing implementation.

### Test-Driven Implementation

**RED — Reproduce and specify**

Create focused regression fixtures covering:

- Black artwork on a transparent SVG background.
- Black artwork on an explicitly white SVG background.
- Two-color artwork on a transparent background.
- Two-color artwork with an explicitly colored background.
- SVG artwork whose source color count differs from the configured `printer_colors` count.
- Antialiased SVG rasterization that introduces intermediate pixel colors.

Verify that transparent regions do not become manufacturing artwork and that the number of traced color regions is independent of unrelated printer palette entries.

**GREEN — Correct the implementation**

- Implement source-aware color discovery and tracing behavior.
- Preserve transparency through rasterization and tracing.
- Separate source color interpretation from printer color mapping.
- Reuse existing color partitioning and tracing mechanisms where appropriate.
- Avoid unrelated changes to SVG geometry, shrinkwrap, or manufacturing output.

**VERIFY — Regression and quality checks**

- Run focused ARTWORK tests.
- Run the applicable non-slow test suite.
- Run Ruff and Pyright.
- Verify resulting traced geometry and color partitions.
- Confirm compatibility with existing native SVG and standalone raster workflows.

### Completion Criteria

BUG-004 is complete when:

- Single-color SVG artwork produces the expected single foreground color partition.
- Transparent backgrounds do not create additional traced artwork.
- Explicitly colored backgrounds are handled according to the ARTWORK specification.
- Source color discovery does not depend on the number of configured printer colors.
- Antialiasing does not create unintended manufacturing layers.
- Regression tests and required quality checks pass.

### Status

**OPEN — Specification review and implementation pending.**

Reproduction fixture: To be supplied or created.

Implementation shall follow the repository's specification-first, RED/GREEN test-driven development process.

---

## BUG-005 — Support Embedded Raster Artwork in SVG Manufacturing Output

### Problem

The ARTWORK and SHAPE manufacturing workflow currently relies on tracing raster artwork into vector geometry for SVG composition.

However, vectorization is not always required or desirable.

For laser engraving workflows using xTool Studio, raster artwork can be embedded directly in an SVG document. The manufacturing application can then perform raster engraving while using accompanying vector geometry for other operations.

Mandatory tracing can introduce unnecessary computation, alter image detail, generate excessive SVG geometry, and prevent use of native raster engraving controls.

### Required Behavior

1. Support a manufacturing output mode that preserves raster artwork as an embedded bitmap within an SVG document.
2. Do not require bitmap tracing when raster preservation is selected.
3. Preserve the original raster image content and transparency where possible.
4. Preserve physical dimensions, scaling, alignment, and placement within the composed SHAPE.
5. Embed raster data within the SVG rather than depending on external image files.
6. Permit embedded raster artwork to coexist with vector geometry, including base outlines, ridges, borders, and labels.
7. Preserve existing traced-vector output behavior as an independently selectable mode.
8. Ensure output is deterministic and compatible with the supported SVG manufacturing contract.
9. Keep raster preservation independent of the configured printer color count.

### Specification Review

Before implementation:

- Review the ARTWORK and SHAPE model definitions.
- Identify where raster tracing is currently required.
- Determine how prepared raster artwork is represented and passed between models.
- Define an explicit contract for selecting raster preservation versus vector tracing.
- Define the SVG representation and coordinate transformations for embedded raster artwork.
- Determine which manufacturing realizations support embedded raster content.
- Update normative model definitions before modifying production code.

### Test-Driven Implementation

**RED — Specify and reproduce**

Add regression tests demonstrating:

- A standalone PNG can be incorporated into manufacturing SVG output without tracing.
- The SVG contains an embedded raster `<image>` element.
- Embedded image data is self-contained.
- Raster transparency is preserved.
- Image dimensions, scaling, and placement are correct.
- Raster artwork can coexist with vector SHAPE components.
- Existing vector-tracing behavior remains available.
- Raster preservation does not depend on `printer_colors`.
- Repeated builds produce deterministic output.

**GREEN — Implement**

- Introduce the smallest explicit configuration mechanism required to select raster preservation.
- Reuse existing ARTWORK preparation and SHAPE placement behavior.
- Preserve raster data through composition without unnecessary conversion.
- Avoid modifying existing vector-tracing behavior except where required by the specification.
- Do not introduce xTool-specific processing into the core ARTWORK model.

**VERIFY — Regression and quality checks**

- Run focused ARTWORK and SHAPE tests.
- Run the applicable non-slow test suite.
- Run Ruff and Pyright.
- Inspect generated SVG structure.
- Validate representative manufacturing output in xTool Studio.
- Confirm compatibility with existing traced-vector workflows.

### Completion Criteria

BUG-005 is complete when:

- Raster artwork can be embedded directly in a manufacturing SVG.
- Tracing is not required in the raster-preservation mode.
- Embedded raster data remains self-contained.
- Transparency and physical placement are preserved.
- Raster and vector elements coexist correctly.
- Existing vector output behavior remains available.
- Regression tests and required quality checks pass.
- ARTWORK and SHAPE specifications document the new output behavior.

### Status

**OPEN — Specification review and implementation pending.**

No production code changes are authorized by recording this requirement. Implementation shall follow the repository's specification-first, RED/GREEN test-driven development process.

