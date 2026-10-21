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

## Phase 3 — Independent SHAPE Border Labels

### Purpose

Allow the top and bottom SHAPE border labels to use independent font families
and arc spans, while preserving existing shared defaults. Support a small,
explicit set of symbolic text commands useful in decorative labels.

### Architectural boundaries

- Border labels remain SHAPE-owned features, not a standalone Model.
- Existing `shape_border_label_font_family` and
  `shape_border_label_arc_degrees` retain their meaning as shared defaults.
- Per-position settings override only the corresponding label; omitted
  overrides preserve current behavior.
- Symbol expansion, if implemented, is deterministic and occurs before text
  measurement and placement. Do not introduce a general LaTeX parser.
- Preserve existing label fit, registration, and manufacturing semantics.

### Work

1. Review the current border-label parameter, resolver, composition, and glyph
   fitting boundaries; update the SHAPE definition with precise override and
   symbolic-command semantics before implementation.
2. Add top/bottom font-family and arc-span overrides through the existing
   configuration hierarchy. Preserve shared-parameter compatibility.
3. Add a deliberately limited whitelist of symbolic commands (initially the
   centered dot `\\cdot` if supported by the selected font), with defined
   behavior for unknown commands and missing glyphs.
4. Test independent overrides, legacy defaults, text fitting, and generated
   SVG/3MF behavior; run the appropriate full quality suite.

### Acceptance criteria

- Top and bottom labels can use different fonts and arc spans in one SHAPE.
- Configurations using only the existing shared settings produce equivalent
  geometry and outputs.
- Supported symbolic commands render predictably; unsupported commands fail
  clearly rather than silently changing text.
- Existing label fitting and other SHAPE features remain functional.

### Completion

Complete when independent settings and the agreed symbolic-command subset are
specified, implemented, and regression-tested. Remove this phase and
reevaluate the plan.

## Phase 4 — Outer Ridge Inset

### Purpose

Allow the SHAPE Outer Ridge to be inset from the outside base boundary,
exposing an optional perimeter of base material without changing the base's
physical dimensions.

### Architectural boundaries

- The SHAPE base boundary remains authoritative for overall size and physical
  extent; the Outer Ridge is a distinct feature.
- A zero inset preserves current geometry.
- Inner Ridge and border-label positioning must remain coherent with the
  resulting Outer Ridge geometry.
- Invalid combinations of inset, ridge widths, and available space fail
  clearly rather than generating degenerate geometry.
- Do not introduce generalized structure offsets or a new composition system.

### Work

1. Inspect existing Structure and Compose ownership of base, ridge, and label
   boundaries. Define the inset measurement and constraints in SHAPE's
   permanent specification.
2. Add a backward-compatible inset parameter and apply it at the geometry
   boundary that owns ridge placement.
3. Verify zero-inset compatibility, nonzero inset, related feature placement,
   and consistency between SVG and 3MF outputs.

### Acceptance criteria

- An inset Outer Ridge is visibly separated from the base perimeter by the
  configured physical distance.
- Base dimensions do not change; the default remains unchanged.
- Dependent ridges and labels remain correctly placed, or invalid settings
  produce explicit errors.
- SVG and 3MF representations agree on the intended geometry.

### Completion

Complete when the inset is specified, implemented, and regression-tested.
Remove this phase and reevaluate the plan.

## Phase 5 — Separate SVG Cut Boundary from Printable Structure

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
