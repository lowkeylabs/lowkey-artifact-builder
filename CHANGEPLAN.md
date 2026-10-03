# CHANGEPLAN

## Purpose

Continue refining `lowkey-artifact-builder` around the manufacturing value
chain established by the current repository HEAD.
The operator's ordinary goal is:

> Move customer artwork to a ****\\*\\*correct, printable 3MF\\*\***** with the fewest
> necessary decisions, actions, and computations.

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
correct printable 3MF
      ↓
slicer / share / upload / print
```

`create` and `build` define the ordinary value chain. `show`, `config`,
`colors`, and `clean` support that path when the operator needs discovery,
inspection, customization, correction, color selection, or maintenance. These
support commands must not become mandatory ceremony before routine
manufacturing.
This CHANGEPLAN contains remaining work rather than a history of completed
implementation. Completed behavior should normally be credited from HEAD and
removed from the plan rather than retained as historical checklists.

## Planning and development rules

`ARCHITECTURE.md` and the applicable Model `DEFINITION.md` files are normative.
Repository HEAD defines the current implementation. The CLI README defines the
intended operator-facing command model. This CHANGEPLAN describes temporary
remaining work and must not redefine permanent architecture.
At the beginning of a thread and before each meaningful implementation slice:

1. reload and follow `prompts/NEW_THREAD.md`;
2. compare CHANGEPLAN with current HEAD, `ARCHITECTURE.md`, applicable Model

   definitions, and the relevant CLI documentation;

3. credit behavior HEAD already satisfies;
4. identify the next unmet behavioral boundary rather than assuming the plan

   is still current;

5. resolve known semantic or architectural questions before encoding behavior

   in tests, while allowing test-first exploration to discover or clarify
   uncertain seams and ownership boundaries;

6. organize TDD around major behavioral seams or boundaries, using one test or

   a small coherent test set to drive a substantial implementation slice rather
   than creating single-test/single-change cycles;

7. implement the smallest correct change at the layer that owns the behavior;
8. run focused tests and then the appropriate complete quality suite; and
9. reevaluate the plan against the resulting HEAD.

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
`artifacts/\\<artifact_id>/` exists. Commands must preserve the distinction
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

## Phase 1 — (placeholder)

(placeholder)

# Phase 2 — Add Shape Loop

## Purpose

Implement the Shape Loop Feature defined by the current Shape model specification.
Shape Loop should use the carefully designed and debugged Artwork Loop as behavioral and geometric precedent while remaining a Shape-owned Feature with its own geometry implementation, component, dimensionalization, and Package color semantics.
Shape Loop must integrate with the Shape raise-style policy established by
Phase 1.
The Shape specification now defines the raise-style contract:

- with `shape_raise_style = "raised"`, Loop occupies physical Z from zero

  through `shape_loop_raise`;

- with `shape_raise_style = "inlaid"`, Loop occupies the complete Shape

  thickness from `Z = 0` through `shape_base_raise`;

- `shape_loop_raise` remains resolved configuration under `"inlaid"` but does

  not determine the manufactured Loop height; and

- because Loop is additive geometry outside the principal Shape envelope,

  inlaid Loop does not require a corresponding subtraction from Base.
The central manufacturing contract is:

> A participating Shape Loop is additive Shape-owned geometry whose inner opening is externally tangent to the complete assembled Shape envelope at the selected cardinal position.

Loop is a distinct physical component. Unlike Hole, it adds material and therefore participates in both Shape Extrude component production and Shape Package color assignment.
The Loop is positioned relative to the complete assembled Shape envelope defined by `shape_size`. Optional Shape Features do not redefine that positioning boundary.
This phase should migrate proven Artwork Loop behavior rather than redesigning Loop geometry.

## Required behavior to establish

Shape defines:

```text
shape_loop_inner_diameter
shape_loop_width
shape_loop_position
shape_loop_raise
shape_loop_color
```

with participation determined solely by:

```text
shape_loop_inner_diameter > 0
```

Zero inner diameter disables Loop participation.
Loop uses the same cardinal-position convention as Artwork Loop:

```text
0      -> top
90     -> right
180    -> bottom
-90    -> left
```

The Loop inner opening is externally tangent to the dimensionalized complete Shape boundary at the selected cardinal position.
Its geometry is determined by:

```text
inner radius = shape_loop_inner_diameter / 2
outer radius =
    inner radius
    + shape_loop_width
```

Loop explicitly extends beyond the normal `shape_size` envelope. This extension is part of the Loop Feature contract and does not change the meaning or configured value of `shape_size`.
Loop positioning must not depend on whether an Outer Ridge, Inner Ridge, Border Label, Artwork fill, incorporated Artwork, or other optional Feature participates.
A participating Loop is a distinct Shape-owned physical component.
Its physical dimensionalization follows the Shape raise-style policy.
`shape_loop_raise` defaults from:

```text
shape_base_raise
```

For a raised Shape, the Loop occupies:

```text
Z = 0 .. shape_loop_raise
```

For an inlaid Shape, the Loop occupies:

```text
Z = 0 .. shape_base_raise
```

`shape_loop_raise` remains resolved configuration under `"inlaid"` but does
not determine the manufactured Loop height.
Because Loop is additive geometry outside the principal Shape envelope,
inlaid Loop does not participate in the Base/component partition and does
not require a corresponding subtraction from Base.
Its physical printing color is controlled by:

```text
shape_loop_color
```

with the default derived from the resolved:

```text
shape_base_color
```

Loop physical color is Package policy. Changing only `shape_loop_color` must not invalidate or recompute Structure, Compose, or Extrude geometry.
Loop participation does not alter the registered interior region or Artwork fitting.

## Implementation boundary

Shape Extrude owns Loop physical dimensionalization and component participation.
Structure and Compose should not manufacture physical Loop geometry or change registered Shape/Artwork composition merely because Loop participates.
Shape Extrude should produce a distinct semantic Loop component while leaving its physical printer color unresolved.
Shape Package owns Loop physical color assignment. It should recognize the Loop as a supported Shape-owned component, apply an explicit `shape_loop_color` when configured, and otherwise inherit the resolved Base color.
Shape owns its Loop geometry and policy. Implement Shape Loop in the Shape model rather than reusing or extracting the Artwork Loop implementation.
Artwork Loop should serve as proven behavioral and geometric precedent. The shared `Bounds` primitive may be used for the physical envelope, but `LoopGeometry`, Loop construction, participation, Shape-specific raise, Shape-specific color, component identity, and Stage ownership remain model-owned.
Do not introduce a shared Loop Feature or generic Loop manufacturing subsystem merely because the Artwork and Shape geometry calculations are initially similar.
Do not make Shape Loop inherit Artwork's attachment-color policy. Artwork requires attachment-layer color inheritance because standalone Artwork has dynamic Artifact-color layers. Shape has an established semantic Base color and therefore follows Shape-owned component color policy.

## TDD seams

Establish Loop through two major behavioral boundaries without decomposing the work into single-change cycles.

### Extrude seam

Use one high-value test or small coherent test group to establish that a participating Loop:

- is positioned relative to the dimensionalized Shape envelope;
- preserves the proven inner-opening tangency rule;
- receives the configured/default physical raise; and
- becomes a distinct Shape-owned physical component.

The test should establish the manufacturing boundary rather than separately inventorying every internal helper or cardinal branch.

### Package seam

Use a focused Package-level test to establish that:

- Loop is recognized as a Shape-owned component;
- its default physical color is the resolved Base color;
- an explicit `shape_loop_color` overrides that inherited color; and
- color resolution remains Package-only behavior.

These are separate meaningful seams because Extrude owns physical component production while Package owns physical printer color.
Existing Artwork Loop tests should be used as behavioral evidence and regression protection rather than mechanically duplicated into a full parallel Shape test suite.

## High-level implementation steps

1. Audit the existing Artwork Loop parameters, validation, geometry helper, Extrude integration, Package behavior, and focused tests against the new Shape Loop Feature contract.
2. Audit current Shape parameter registration, derivation, validation, Stage parameter ownership, Extrude component construction, Package component-color handling, and relevant tests.
3. Add the Shape Loop configuration parameters and validation defined by the Shape specification.
4. Add the derived `shape_loop_raise` behavior from the effective `shape_base_raise` while preserving explicit override precedence.
5. Establish the high-value failing test or small coherent test set at the Shape Extrude manufacturing seam.
6. Implement the Shape-owned Loop geometry using the proven Artwork Loop geometry calculation as precedent and the shared `Bounds` primitive for the dimensionalized Shape envelope.
7. Produce a distinct Shape-owned Loop extrusion component, using

   `shape_loop_raise` for its complete height under `"raised"` and
   `shape_base_raise` for its complete height under `"inlaid"`; do not add
   inlaid Loop geometry to the shared Base-partition subtraction.

8. Preserve Loop semantic component identity through the Shape extrusion manifest.
9. Establish the focused Package seam for Loop physical color.
10. Extend Shape Package to recognize Loop and resolve `shape_loop_color`, defaulting to the resolved Base color when no explicit override exists.
11. Verify that changing only Loop color affects Package without changing earlier geometry products.
12. Verify that Loop participation does not alter registered composition, the registered interior region, or Artwork fitting.
13. Run focused Shape Loop/Extrude/Package tests, relevant Artwork Loop regression tests, and then the appropriate complete quality suite.
14. Recompare resulting HEAD with the Shape definition and remove this phase when the Feature contract is fully satisfied.

## Completion criteria

Phase 2 is complete when:

- the Shape Loop parameters resolve and validate according to the Shape Feature contract;
- zero `shape_loop_inner_diameter` produces no Loop;
- positive `shape_loop_inner_diameter` produces a distinct physical Loop component;
- Loop position is derived from the complete dimensionalized Shape envelope defined by `shape_size`;
- the Loop inner opening is externally tangent to the Shape boundary at the selected cardinal position;
- `shape_loop_width` correctly determines the radial material width surrounding the opening;
- Loop may extend beyond the normal `shape_size` envelope without changing the meaning of `shape_size`;
- under `"raised"`, `shape_loop_raise` controls complete Loop height from

  `Z = 0`;

- under `"inlaid"`, Loop spans the complete Shape thickness from `Z = 0`

  through `shape_base_raise`, while `shape_loop_raise` remains resolved
  configuration without determining manufactured height;

- inlaid Loop remains additive outside the principal Shape envelope and does

  not participate in Base subtraction;

- the default Loop raise derives from the effective `shape_base_raise`, with explicit configuration taking precedence;
- Loop retains distinct Shape-owned component identity through Extrude and Package;
- the default Loop color is the resolved Base color;
- an explicit `shape_loop_color` overrides the Base-color default;
- physical Loop color is assigned only during Package;
- changing only `shape_loop_color` does not require recomputing Structure, Compose, or Extrude;
- Loop participation does not alter the registered interior region or Artwork fitting;
- important Loop behavior is protected at the Extrude and Package ownership boundaries without unnecessary inventory-style tests;
- existing Artwork Loop behavior remains correct; and
- the complete applicable test, type-check, and lint suite is green.

# Phase 3 — Rework CONFIG Around Effective Resolution and Provenance

## Purpose

Make CONFIG the operator/developer inspection surface for understanding how a
Realization's effective configuration was resolved.
For any selected Realization, CONFIG should make it possible to discover the
effective settings used by the resolver and understand the provenance or owner
of each setting.
This work should build around the existing resolver and configuration
precedence rather than independently reconstructing effective configuration in
the CLI.
CONFIG remains distinct from SHOW:

```text
SHOW
    manufacturing state and available Products
CONFIG
    effective settings and where those settings came from
```

CONFIG may also retain explicit configuration mutation where that capability
is useful, but inspection of effective resolution and provenance is the central
design concern of this phase.

## Required behavior to establish

For a selected Artifact/Realization, CONFIG should be able to report the
effective parameter set and identify the meaningful source/owner of each value.
Relevant provenance may include, according to the configuration model actually
established by HEAD and the permanent specifications:

- Model/default parameter definitions such as `parameters.toml`;
- Artifact-level authored configuration in `artifact.toml`;
- Realization-level authored configuration in `artifact.toml`; and
- other resolver-supported configuration layers that materially participate

  in the effective value.
Do not invent provenance categories from filesystem location alone. Provenance
must correspond to the actual resolution model.
The resolver remains authoritative for precedence and effective values. CONFIG
should consume resolver results or a reusable resolver-adjacent inspection
capability rather than duplicate precedence rules.
Sparse authored configuration must remain sparse. Inspecting effective values
must not cause defaults or inherited values to be written into `artifact.toml`.
The exact terminal layout is not fixed by this plan. The presentation should
make value and provenance understandable without exposing irrelevant resolver
internals.

## High-level implementation steps

1. Audit current `cmd_config.py`, CONFIG application operations, resolver APIs,

   configuration data structures, tests, and relevant permanent
   specifications.

2. Document the actual resolution layers and precedence already established by

   HEAD before defining provenance output.

3. Identify whether the resolver already retains enough provenance to support

   CONFIG inspection. If not, introduce the smallest reusable structured
   result at the resolver/application boundary that can report effective value
   plus provenance without changing resolution semantics.

4. Establish high-level tests proving that CONFIG reports effective values and

   distinguishes important provenance boundaries, including defaults,
   Artifact-level overrides, and Realization-level overrides where applicable.

5. Refactor CONFIG inspection to consume the reusable resolution/provenance

   capability rather than reconstructing precedence inside Click.

6. Preserve useful CONFIG mutation behavior and sparse authored configuration;

   adjust syntax only when a demonstrated operator/developer need warrants it.

7. Review broad CONFIG scope and developer-oriented flags against the clarified

   purpose of CONFIG. Retain, relocate, or simplify them based on actual value,
   without removing reusable engine capabilities merely to simplify the CLI.

8. Reconcile CONFIG documentation and help with the resulting behavior.
9. Run focused resolver/config/application/CLI tests, then the complete

   applicable quality suite.

## Completion criteria

Phase 3 is complete when:

- CONFIG can inspect a selected Realization's effective settings;
- each reported setting can identify meaningful provenance/ownership according

  to the real resolver model;

- effective values and provenance come from reusable resolver/application

  behavior rather than duplicated CLI precedence logic;

- default, Artifact-level, and Realization-level resolution boundaries are

  correctly represented where applicable;

- inspection does not materialize manufacturing work or mutate sparse authored

  configuration;

- useful CONFIG mutation behavior remains correct;
- CONFIG's public and developer-oriented scopes have intentional purposes;
- important resolution/provenance seams are protected by focused tests; and
- CONFIG help and CLI documentation agree with resulting HEAD.

**---**

# Phase 4 — Consolidate Remaining CLI Surfaces and Final Acceptance

## Purpose

After the focused command work described elsewhere in this plan, review the
remaining historical CLI inconsistencies, developer surfaces, help, messaging,
and end-to-end acceptance coverage without disturbing the established
manufacturing value chain.
This phase is cleanup and consolidation. It does not justify speculative
manufacturing capability or architectural simplification.

## Historical and developer surfaces

Review remaining public options, aliases, and developer operations against
actual operator or developer value, including where applicable:

- Variant-oriented public syntax such as `--variant` and `--all-variants`;
- independent Stage execution;
- Model/workplan inspection;
- diagnostic/developer capabilities; and
- command options whose historical purpose is no longer clear.

For each candidate, determine whether it is:

- required for ordinary manufacturing;
- a useful exception/customization capability;
- a useful developer capability;
- redundant with a clearer established operation; or
- obsolete presentation around a still-useful reusable capability.

Retain, relocate, deprecate, or remove based on those answers.
Do not confuse Variant identity with Realization identity. Do not remove a
useful architecture-level capability merely because ordinary manufacturing has
a simpler CLI path.
Where developer operations remain public, make their purpose and scope
explicit. Where they do not belong in ordinary operator workflow, prefer clear
separation or relocation over deleting reusable capability.

## Help and message consistency

Review:

```text
artifact --help
artifact \\<command> --help
```

Help should describe operator purpose rather than implementation mechanics.
Review routine output and errors for:

- terse success output;
- consistent Artifact, Variant, Realization, and Product terminology;
- actionable expected errors;
- suggested next actions when the application knows them;
- useful batch summaries;
- obvious manufacturing Products;
- useful relative paths; and
- absence of unnecessary Stage/resolver/dependency implementation detail.

Do not force identical output shapes on commands with different purposes.

## Final acceptance review

Protect a small number of complete value-chain workflows and reuse existing
lower-level evidence rather than duplicating it.
At minimum, compare current acceptance coverage with these operator outcomes:

```text
incoming artwork
      ↓
create
      ↓
build
      ↓
correct printable 3MF
```

```text
registered Artifact
      ↓
show / build
      ↓
existing current Product reused or required work identified
      ↓
correct printable 3MF
```

```text
configuration or color exception
      ↓
appropriate support operation
      ↓
build only what is necessary
      ↓
correct printable 3MF
```

```text
clean selected generated work
      ↓
build
      ↓
dependency-driven regeneration
      ↓
correct printable 3MF
```

Acceptance tests should remain focused on user-visible manufacturing value.
Detailed geometry, configuration resolution, graph planning, Product-state,
dependency, and color-assignment behavior belongs at the lower layers that own
those semantics.
Add acceptance coverage only where a meaningful end-to-end behavioral boundary
is not already protected.

## High-level implementation steps

1. Audit remaining public CLI syntax and developer operations against current

   HEAD and operator/developer value.

2. Resolve or document intentional homes for retained secondary/developer

   capabilities.

3. Reconcile top-level and command help with the final public command model.
4. Review routine messages and expected errors for consistency and useful next

   actions.

5. Compare existing acceptance tests with the final value-chain workflows and

   add only missing high-value coverage.

6. Run the complete test, type-check, and lint suite.
7. Recompare final HEAD with `ARCHITECTURE.md`, Model definitions, CLI

   documentation, and this CHANGEPLAN; remove completed planning material that
   no longer represents remaining work.

## Completion criteria

Phase 4 is complete when:

- the public CLI presents a short, coherent manufacturing workflow;
- secondary and developer capabilities have intentional homes;
- obsolete public syntax and historical presentation have been removed or

  intentionally retained;

- help and routine messages reflect the final command model;
- expected operator/domain failures are concise and actionable without hiding

  unexpected defects;

- the final acceptance suite protects the important manufacturing value-chain

  outcomes without duplicating lower-level tests;

- application workflow behavior remains reusable independently of Click; and
- repository documentation agrees with final HEAD.

The completed CLI should continue to support the central objective:

> Move customer artwork to a ****\\*\\*correct, printable 3MF\\*\***** with the fewest
> necessary decisions, actions, and computations.

