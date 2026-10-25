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

## Phase 1 — Shared SHAPE Label Color

### Purpose

Introduce `shape_label_color` as the common default color for SHAPE labels, with an explicit default of black.

Existing label-specific color parameters derive their defaults from `shape_label_color` unless explicitly overridden. Future SHAPE label features should follow the same convention.

This allows operators to configure the default label color once while preserving independent color customization for individual labels.

### Architectural boundaries

- SHAPE owns label-color semantics. Do not introduce label-specific policy into the generic engine or configuration infrastructure.
- `shape_label_color` is an ordinary Model parameter with an explicit default of the existing catalog's black color.
- Existing label-specific color parameters, including `shape_top_border_label_color` and `shape_bottom_border_label_color`, derive their defaults from the effective `shape_label_color`.
- Explicit label-specific color overrides take precedence through normal configuration resolution.
- `shape_label_color` is independent of `shape_base_color`. Changing the Base color must not implicitly change label colors.
- Preserve existing logical color identities, color-catalog resolution, and downstream physical printer-color assignment.
- Preserve label geometry, typography, registration, component identities, and existing SVG and 3MF manufacturing behavior except for the intentional change in default label colors.
- Do not introduce new label features, generalized text styling, or additional configuration inheritance mechanisms.

### Work

1. Update SHAPE's permanent `DEFINITION.md` to establish the shared label-color contract, its default, and the precedence of label-specific overrides.
2. Declare `shape_label_color` with an explicit default of black, using the existing logical color catalog.
3. Update existing label-specific color derivations to resolve through `shape_label_color` rather than `shape_base_color`.
4. Add focused behavioral tests covering the shared default, configuration inheritance, explicit overrides, and independence from Base color.
5. Verify that SVG and 3MF manufacturing outputs consume the resulting effective label colors without changing geometry or component identities.
6. Run focused tests and the appropriate complete quality suite.

### Acceptance criteria

- `shape_label_color` is available through ordinary SHAPE parameter resolution and configuration.
- Its default resolves to the existing catalog's black color.
- With no label-specific overrides, both Top and Bottom Border Labels inherit the effective `shape_label_color`.
- Changing `shape_label_color` changes the effective colors of both labels without requiring separate overrides.
- Explicitly configuring either label's color overrides the shared default for that label only.
- Changing `shape_base_color` does not change effective label colors unless an explicit configuration dependency requires it.
- Existing SVG and 3MF outputs reflect the resolved label colors without changes to label geometry, registration, or component identity.
- Future SHAPE label features can derive their default colors from `shape_label_color` without introducing another shared color mechanism.

### Completion

Complete when the shared label-color contract is specified, implemented, and regression-tested across configuration resolution and manufacturing output.

Remove this phase and reevaluate the plan.

