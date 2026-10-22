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

## Phase 1 — SHAPE Ridge Inset and Surface Regions

### Purpose

Extend SHAPE's perimeter geometry and surface-color capabilities to support:

- An optional Outer Ridge inset that exposes a perimeter of Base material without changing the Shape's physical dimensions.
- An independently colored Border Fill occupying the complete region between the Outer Ridge and Inner Ridge.
- An independently colored Artwork Region Fill occupying the complete central region, regardless of whether Artwork participates.

Both fill colors default to the effective Base color. The resulting SVG and 3MF Products must preserve consistent geometry, component identity, and manufacturing semantics.

### Architectural boundaries

- The SHAPE Base boundary remains authoritative for overall size and physical extent. Outer Ridge inset does not change `shape_size` or the registered Shape envelope.
- Outer Ridge inset is measured inward from the Base boundary to the Outer Ridge's outer edge. Ridge width is measured inward from that edge. For polygon geometry, both distances are perpendicular to the corresponding edges.
- A zero inset preserves existing Outer Ridge geometry. A zero-width Outer Ridge does not participate regardless of its configured inset.
- Inner Ridge and Border Label positioning remain relative to the appropriate participating boundaries. Inset must not silently change their established spacing semantics.
- The exposed perimeter outside an inset Outer Ridge retains `shape_base_color`.
- Introduce `shape_border_fill_color` for the region between the Outer Ridge and Inner Ridge, and `shape_artwork_region_fill_color` for the central region. Both default to the resolved `shape_base_color`, not a fixed color literal.
- Surface regions are SHAPE-owned physical components, not merely SVG paint attributes. Their colors are resolved through existing SHAPE packaging policy.
- Fill regions cover their complete geometric interiors, independently of Artwork or Border Label participation. Foreground components retain their independently configured colors.
- Enclosed spaces within lettering and Artwork geometry, including glyph counters such as those in A and D, remain filled with the appropriate background region material rather than becoming unintended holes.
- Preserve the existing `shape_artwork_fill_color` Feature and its participation semantics. Artwork Region Fill is a distinct capability and does not replace or redefine Artwork Fill.
- Raised and inlaid dimensionalization must preserve the intended assembled geometry without unintended overlapping printable volumes or gaps.
- Preserve logical Artwork color identity, component registration, existing ridge styles, and established SHAPE manufacturing behavior.
- Invalid combinations of inset, ridge widths, region boundaries, and available space fail explicitly rather than generating degenerate geometry.
- Do not introduce generalized structure offsets, a new composition system, or manufacturing-specific behavior in the generic engine.

### Work

1. **Specify geometry and participation.** Inspect existing Structure, Compose, Extrude, and Package ownership of Base, Outer Ridge, Border Labels, Inner Ridge, Artwork, and fill geometry. Update SHAPE's permanent definition with the inset measurement, surface-region boundaries, participation rules, and dimensionalization semantics. Define boundary fallback behavior when either ridge is absent.

2. **Implement Outer Ridge inset.** Add the backward-compatible `shape_outer_ridge_inset` parameter, defaulting to zero. Apply the inset at the SHAPE geometry boundary that owns ridge placement. Preserve the complete Base boundary and update dependent ridge and label references without changing their established spacing relationships.

3. **Implement Border Fill.** Add `shape_border_fill_color`, defaulting to the resolved `shape_base_color`. Define the complete Border Fill region from the applicable outer and inner boundaries. Preserve the background behind independently colored Border Labels, including enclosed glyph counters. The region must not depend on label participation.

4. **Implement Artwork Region Fill.** Add `shape_artwork_region_fill_color`, defaulting to the resolved `shape_base_color`. Define the complete central surface region independently of incorporated Artwork participation. Preserve background material between Artwork components and within enclosed Artwork geometry. Keep this region distinct from the existing Artwork Fill Feature.

5. **Preserve physical manufacturing semantics.** Carry the new region identities through registered composition, physical extrusion, and packaging. Ensure raised and inlaid styles produce valid, nonoverlapping printable components with the intended assembled geometry. Apply physical colors through existing packaging mechanisms rather than assigning them during registered composition.

6. **Validate compatibility and outputs.** Use coherent TDD slices to verify zero-inset and default-color compatibility, nonzero inset geometry, independent fill colors, missing-ridge boundary behavior, dependent feature placement, enclosed foreground spaces, and SVG/3MF consistency. Run focused tests and the appropriate complete quality suite.

### Acceptance criteria

- A nonzero Outer Ridge inset exposes the configured physical width of Base material around the perimeter without changing overall Shape dimensions.
- A zero inset preserves existing Outer Ridge geometry and manufacturing behavior.
- Inner Ridge and Border Labels remain correctly positioned relative to their applicable reference boundaries.
- Border Fill covers the complete region between the applicable ridge boundaries, including areas behind labels and enclosed spaces within glyphs.
- Artwork Region Fill covers the complete central region even when no Artwork is incorporated, including gaps and enclosed spaces within participating Artwork.
- Border Fill and Artwork Region Fill can use distinct colors independently of Base, ridges, labels, and incorporated Artwork.
- When either fill color is unspecified, its effective color follows the resolved Base color. Existing configurations retain equivalent geometry, colors, and manufacturing output.
- The existing Artwork Fill Feature retains its independent behavior and configuration.
- Missing or nonparticipating ridges use explicitly defined boundary fallbacks without introducing unintended geometry.
- Raised and inlaid manufacturing representations preserve complete assembled geometry, valid component partitioning, and independently assignable physical colors.
- Invalid dimensions and impossible region configurations produce explicit errors.
- SVG and 3MF outputs agree on region boundaries, registration, and intended physical component identities.

### Completion

Complete when Outer Ridge inset and both surface-fill capabilities are specified in SHAPE's permanent definition, implemented through the existing SHAPE manufacturing pipeline, and regression-tested for geometry, color defaults, independent color assignment, enclosed regions, and SVG/3MF consistency.

Remove this phase and reevaluate the remaining CHANGEPLAN against HEAD.

---

## Phase 2 — Separate SVG Cut Boundary from Printable Structure

### Purpose

Make the outside SHAPE boundary independently identifiable in the existing
SHAPE SVG so an operator can assign a laser CUT operation separately from
printed or engraved ridges and other artwork in xTool Studio.

### Architectural boundaries

- Preserve a single authoritative base boundary and the existing physical
  coordinate system, size, and registration of all SVG components.
- Separate cut-contour identity from printable ridge geometry. A cut contour
  must not accidentally become a printed outline or filled graphic.
- Preserve existing SHAPE SVG and 3MF geometry and behavior except for the
  intentional SVG organization change.
- Do not assume SVG grouping alone is sufficient for xTool Studio operation
  assignment. Verify importer behavior before choosing an export contract.
- Do not implement `.xs` packaging in this phase. Whether XS needs separate
  SVG documents or independently configured project objects remains future
  investigation.

### Work

1. Inspect current SHAPE SVG serialization, including the `structure` group,
   Outer Ridge fill, and no-Outer-Ridge fallback. Define the cut-contour and
   printable-component contract in SHAPE's specification.
2. Emit an independently identifiable, closed outside cut contour, separate
   from printable structure, without changing registration or duplicating
   unintended visible geometry.
3. Validate the result with representative SHAPE SVGs and an xTool Studio
   import/operation-assignment test; adjust the representation based on
   observed behavior rather than assumptions about SVG groups.
4. Regression-test SVG output and unaffected 3MF workflows; run the
   appropriate full quality suite.

### Acceptance criteria

- The outside boundary can be distinguished from printable ridges and artwork
  without reconstructing its geometry.
- xTool Studio can assign CUT to the outside contour separately from the
  intended print/engrave components, or a documented importer limitation
  identifies the remaining packaging requirement.
- The cut contour and artwork retain exact relative placement and physical
  size, including SHAPEs without an Outer Ridge.
- No unintended printed outline, duplicate cut path, or regression in existing
  SHAPE manufacturing output is introduced.

### Completion

Complete when the SVG separation contract is implemented and verified, with
any unresolved XS-specific packaging requirement recorded in `FUTURE.md`.
Remove this phase and reevaluate the plan.
