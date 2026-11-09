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


## Phase 1 — SHAPE Composition Contracts and Placement

### Purpose

Establish the SHAPE composition semantics needed to position externally
authored SVG geometry independently of incorporated Artwork, ridges,
labels, and other existing SHAPE Features.

Preserve the existing registered coordinate system, physical sizing,
component identities, and manufacturing behavior while introducing
the smallest useful contract for independently placed geometry.

### Architectural boundaries

- SHAPE remains authoritative for placement, composition, physical
  dimensions, and manufacturing of incorporated geometry.
- Existing SHAPE Structure, Compose, Extrude, and Package responsibilities
  remain authoritative unless a demonstrated mismatch requires an
  explicit specification change.
- Reuse established ARTWORK SVG interpretation and registered geometry
  mechanisms where appropriate. Do not create a competing SVG pipeline.
- Keep generic engine behavior independent of SHAPE-specific placement
  and composition policies.
- Preserve existing Artwork fitting, registration, and manufacturing
  behavior when no new placement capability is configured.
- Do not introduce a generalized component-instance framework merely
  to anticipate multiple ARTWORK sources or a future BANNER Model.

### Work

1. Inspect current SHAPE composition, registered geometry, Artwork
   incorporation, component identity, and manufacturing boundaries.
   Identify existing mechanisms that already support independently
   positioned geometry.
2. Define the minimum placement contract for reusable SVG geometry,
   including source references, instance identity, translation, uniform
   scaling, rotation, and transform registration.
3. Resolve the coordinate and transform semantics against the existing
   SHAPE registered coordinate space. Preserve source proportions and
   predictable physical placement.
4. Define how placed geometry participates in SHAPE composition and
   subsequent manufacturing without introducing unnecessary new
   Products, Stages, or generic engine abstractions.
5. Update the applicable permanent Model specification before tests
   establish new placement semantics.

### TDD boundary

Establish a coherent SHAPE Model test boundary demonstrating that
independently positioned geometry retains the intended transforms,
registration, and semantic identities without changing existing
SHAPE geometry or incorporated Artwork behavior.

Use focused tests to clarify ownership where existing composition
mechanisms are insufficient.

### Completion

- Placement semantics are defined in the permanent SHAPE specification.
- Existing composition mechanisms are reused wherever sufficient.
- The necessary placement contract is established without speculative
  infrastructure.
- Existing SHAPE and ARTWORK manufacturing behavior remains intact.


## Phase 2 — Reusable SVG Decorations

### Purpose

Allow SHAPE to incorporate externally authored SVG decorative motifs,
including stars, diamonds, flourishes, serifs, filigree, and similar
small graphical elements.

Support multiple independently positioned instances of the same SVG
source without requiring duplicate source files or separate ARTWORK
Realizations.

### Architectural boundaries

- Decorations are incorporated geometry owned by SHAPE composition,
  not a new manufacturing Model.
- SVG interpretation should reuse ARTWORK's established processing
  contracts and reusable operations where appropriate, without
  invoking another Model's Stage implementation.
- Preserve authored source geometry and logical color identities
  unless an explicit color override is requested.
- Each decoration instance retains a distinct semantic identity even
  when multiple instances reference the same SVG source.
- Placement and source interpretation remain separate concerns.
- Existing SHAPE composition and manufacturing behavior is unchanged
  when no decorations are configured.
- Do not introduce a generalized dependency or source-instance system
  beyond what this capability actually requires.

### Work

1. Define the SHAPE configuration interface for referencing reusable
   SVG decoration sources and declaring independently placed instances.
2. Support translation, uniform scaling, and rotation of individual
   decoration instances using the placement semantics established
   in Phase 1.
3. Preserve source geometry, authored colors, and instance identity
   through registered composition.
4. Define and implement explicit logical color overrides where needed,
   without changing the meaning of source-authored colors by default.
5. Resolve SVG stroke handling and unsupported source constructs
   against existing ARTWORK SVG behavior rather than introducing
   decoration-specific interpretation rules.
6. Carry decoration geometry through the existing SHAPE manufacturing
   path to canonical SVG and 3MF Products.
7. Provide clear validation for invalid source references, transforms,
   colors, and unsupported geometry.

### TDD boundary

Use one coherent SHAPE Model test set to establish that an external
SVG motif can be incorporated multiple times with independent
transforms, preserved registration, and correct logical colors.

Add a focused manufacturing acceptance test demonstrating that
decorations survive the complete SHAPE build into the intended
manufacturing Product.

Avoid duplicating existing ARTWORK SVG interpretation tests.

### Completion

- An external SVG motif can be reused at multiple SHAPE locations.
- Instance transforms and logical identities remain independent.
- Authored colors and explicit overrides behave predictably.
- Decorations participate correctly in SVG and 3MF manufacturing.
- Existing SHAPE configurations remain compatible.


## Phase 3 — Decoration Clipping Regions

### Purpose

Allow individual SVG decoration instances to specify the SHAPE region
within which their geometry is permitted to appear.

Support decorative elements that intentionally cross region boundaries
while retaining only the portion belonging to the selected clipping
region.

### Architectural boundaries

- Clipping is distinct from placement and front-to-back composition
  ordering.
- Clipping modifies participating geometry, not merely SVG visibility.
- Clipping must produce consistent registered geometry for downstream
  SVG and 3MF manufacturing.
- SHAPE remains authoritative for Base, Artwork, Inner Ridge, and
  Outer Ridge geometry and their associated boundaries.
- Clipping must not change the physical dimensions or shape of the
  selected region.
- Existing Artwork fitting and clipping behavior remains unchanged
  unless explicitly revised by a separate contract.
- Do not create a second system for computing SHAPE structural
  boundaries.

### Work

1. Define the selectable clipping regions derived from existing SHAPE
   geometry, initially considering:
   - Base
   - Artwork
   - Inner Ridge
   - Outer Ridge
2. Resolve whether each named region represents its enclosed area,
   its occupied physical region, or another explicitly defined
   geometric area. Do not infer these meanings from Feature names.
3. Define behavior when the selected region is absent, empty, or
   geometrically incompatible with the decoration.
4. Define how clipping interacts with instance transforms, authored
   colors, and independently registered components.
5. Implement clipping against authoritative registered SHAPE geometry,
   preserving the intended boundaries and component identities.
6. Ensure clipped decoration geometry is manufactured consistently
   in canonical SVG and 3MF outputs.
7. Preserve existing behavior when no clipping region is explicitly
   selected.

### TDD boundary

Establish a focused SHAPE composition test set demonstrating that
the same positioned SVG motif produces different, correct geometry
when clipped to different supported regions.

Include meaningful boundary-crossing cases and absent-region
validation.

Protect the manufacturing boundary with an acceptance case that
verifies clipping affects the final physical Product, not only
the canonical SVG display.

### Completion

- Decoration instances can select supported clipping regions.
- Region meanings and absent-region behavior are explicitly defined.
- Clipping preserves registration and logical component identity.
- SVG and 3MF Products contain correctly clipped geometry.
- Existing SHAPE geometry and default composition remain unchanged.


## Phase 4 — Deterministic Planar Composition

### Purpose

Establish predictable front-to-back relationships among incorporated
Artwork, SVG decorations, ridges, labels, QR codes, and other
participating SHAPE geometry.

Ensure the intended visible design is consistent with manufacturing
geometry rather than relying on incidental SVG element order or
physical extrusion height.

### Architectural boundaries

- Planar visibility ordering and physical Z dimensionalization are
  distinct Model concepts.
- Preserve semantic component identity, logical colors, and common
  registration across manufacturing outputs.
- Do not silently permit conflicting positive-area manufactured
  overlaps between different logical colors.
- Reuse existing SHAPE overlap, partitioning, and extrusion behavior
  where it already satisfies the required semantics.
- Prefer fixed semantic precedence when sufficient; introduce
  configurable ordering only when supported use cases require it.
- Do not introduce general-purpose compositing machinery solely
  to anticipate future Models or output formats.

### Work

1. Review existing overlap and precedence behavior for Artwork,
   ridges, labels, QR codes, and decorations.
2. Identify the meaningful composition conflicts introduced by
   independently positioned and clipped SVG decorations.
3. Define deterministic precedence for supported overlapping
   components, distinguishing visibility from physical geometry.
4. Determine when existing clipping, geometric subtraction, or
   component partitioning is sufficient to produce correct
   manufactured geometry.
5. Implement only the additional composition behavior required
   for supported SHAPE use cases.
6. Preserve consistent component identity and logical colors through
   SVG and 3MF manufacturing.
7. Reject unsupported or ambiguous overlap combinations clearly
   rather than silently manufacturing conflicting geometry.

### TDD boundary

Establish a coherent SHAPE Model test boundary using representative
overlapping decorations and existing SHAPE Features.

Verify the intended visible regions, component identities, and
manufacturing-compatible geometry without asserting incidental
internal processing order.

Add manufacturing acceptance coverage only for materially new
integration behavior not already protected by existing tests.

### Completion

- Supported overlaps have deterministic, documented semantics.
- Planar ordering is independent of physical extrusion height.
- Conflicting manufactured geometry is resolved or rejected
  according to the defined Model contract.
- Canonical SVG and 3MF outputs preserve intended composition.
- Existing SHAPE configurations retain their established behavior.


## Phase 5 — Artwork Scaling and Boundary Policies

### Purpose

Extend incorporated Artwork placement beyond its initial fitting
region while preserving explicit control over the relationship
between Artwork extent and the SHAPE boundary.

Allow Artwork to overlap internal SHAPE regions without silently
changing the Base dimensions or manufacturing envelope.

### Architectural boundaries

- Existing Artwork fitting and registration remain the default.
- Artwork scaling, clipping, and physical SHAPE extent are distinct
  concepts.
- Preserve Artwork aspect ratio, common registration, and logical
  component identities.
- The nominal SHAPE boundary, transformed Artwork extent, clipping
  boundary, and assembled manufacturing envelope must remain
  distinguishable.
- Do not automatically enlarge the Base because Artwork exceeds
  its initial fitting region.
- Reuse established placement, clipping, and composition mechanisms
  rather than introducing Artwork-specific alternatives.
- Do not implement boundary expansion or unsupported protrusion
  semantics without an explicit manufacturing contract.

### Work

1. Review existing incorporated Artwork fitting, scaling, registration,
   and clipping behavior against the mechanisms established by the
   preceding phases.
2. Define explicit Artwork scaling beyond the initial fitting region,
   preserving aspect ratio and predictable placement.
3. Establish the initial `clip` boundary policy:
   - Artwork may extend across internal SHAPE regions.
   - Artwork outside the nominal SHAPE boundary is clipped.
   - Base dimensions, `shape_size`, and the outside cut contour
     remain unchanged.
4. Define how enlarged Artwork interacts with ridges, labels, QR
   codes, and decorations under the established composition rules.
5. Ensure resulting geometry is valid for canonical SVG and 3MF
   manufacturing, including raised and inlaid configurations.
6. Evaluate `extend` and `expand` as separate possible capabilities
   only after the initial clipping behavior is manufacturing-correct.
   Do not implement them implicitly as consequences of scaling.
7. Update the permanent SHAPE specification to reflect the accepted
   scaling and boundary behavior.

### TDD boundary

Establish a focused SHAPE Model test set demonstrating that Artwork
can extend beyond its original fitting region while preserving
registration, proportions, and the nominal Base boundary.

Include a manufacturing acceptance case where enlarged Artwork
crosses an internal SHAPE boundary and is correctly clipped at
the outside SHAPE boundary.

Protect existing default Artwork incorporation behavior against
regression.

### Completion

- Artwork can be explicitly scaled beyond its initial fitting region.
- The initial clipping policy preserves nominal SHAPE dimensions.
- Internal overlap follows established composition semantics.
- SVG and 3MF Products remain manufacturing-correct.
- Existing Artwork workflows remain unchanged by default.
- `extend` and `expand` remain deferred unless separately specified
  and justified by manufacturing requirements.

