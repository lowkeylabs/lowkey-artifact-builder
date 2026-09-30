# CHANGEPLAN

## Purpose

Continue refining `lowkey-artifact-builder` around the manufacturing value
chain established by the current repository HEAD.

The operator's ordinary goal is:

> Move customer artwork to a **correct, printable 3MF** with the fewest
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
5. resolve semantic or architectural questions before encoding behavior in
   tests;
6. use TDD for meaningful behavioral seams, without creating one-test-per-line
   ceremony;
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


# Phase 1 — Implement the Shape Inner Ridge Feature

## Purpose

Implement the `shape_inner_ridge` Feature defined by the normative Shape Model
contract in:

```text
src/lowkey_artifact_builder/model/models/shape/DEFINITION.md
```

The Inner Ridge is an optional Shape-owned structural Feature that follows the
Shape geometry and layers on top of the Shape Base.

Its parameters are:

```text
shape_inner_ridge_width
shape_inner_ridge_raise
shape_inner_to_outer_ridge_dist
shape_inner_ridge_color
```

The normative Shape definition owns the detailed semantics, defaults,
validation, geometry, interaction with the Outer Ridge, available interior
region, dimensionalization, component identity, and packaging color behavior.
This phase implements that contract without redefining it here.

The implementation should extend the existing Shape manufacturing pipeline
rather than introduce Inner-Ridge-specific workflow outside the Shape Model.

The resulting pipeline remains:

```text
Shape Structure
      ↓
Shape Compose
      ↓
Shape Extrude
      ↓
Shape Package
      ↓
printable 3MF
```

Inner Ridge must participate at the existing boundaries according to the
responsibilities already assigned to those stages.

## Required behavior to establish

Inner Ridge is disabled by default because:

```text
shape_inner_ridge_width = 0 mm
```

Enabling Inner Ridge must not require a new Variant, Realization, Stage, build
workflow, or CLI operation. It is a Shape Feature whose participation follows
from effective Shape configuration.

A participating Inner Ridge must:

- follow the selected Shape geometry;
- support circle, square, and regular polygon geometry consistently with the
  Shape Model;
- remain registered with the Shape;
- use `shape_inner_ridge_width` as its sole participation control;
- use `shape_inner_to_outer_ridge_dist` to position its outside boundary;
- use the inside boundary of a participating Outer Ridge as its positioning
  reference;
- use the outside boundary of the Base as its positioning reference when no
  Outer Ridge participates;
- layer on top of the Base rather than partitioning or reducing Base X/Y
  geometry;
- use `shape_inner_ridge_raise` for its physical height above the Base;
- remain a distinct semantic component through Extrude and Package;
- become the innermost registered boundary available for incorporated Artwork
  when it participates; and
- receive its physical printing color during Package rather than during
  Structure, Compose, or Extrude.

The effective defaults defined by the Shape Model are:

```text
shape_inner_ridge_width         = 0 mm
shape_inner_ridge_raise         = 1 mm
shape_inner_to_outer_ridge_dist = 10 mm
shape_inner_ridge_color         = resolved shape_base_color
```

The implementation must preserve the distinction between geometry and
packaging color. Changing only `shape_inner_ridge_color` must not invalidate or
recompute Shape Structure, Compose, or Extrude geometry.

Inner Ridge must work both with and without an Outer Ridge. Its positioning
must remain correct for both integrated and separate Outer-Ridge styles.

When Inner Ridge participates, incorporated Artwork must fit within the
available registered interior region bounded by the inside boundary of the
Inner Ridge. When Inner Ridge does not participate, existing Outer-Ridge/Base
interior-region behavior must remain unchanged.

Existing Shape output must remain unchanged when Inner Ridge is left at its
default nonparticipating width.

## TDD and validation strategy

Use TDD to protect important behavioral seams and manufacturing boundaries, not
to create a test for every parameter, branch, helper, or implementation step.

Before adding a test, identify the behavior or failure mode that the test is
protecting. Prefer extending an existing test when it already exercises the
appropriate boundary.

The critical seams for this Feature are:

1. **Feature participation and geometry boundary**

   Establish that a positive Inner-Ridge width causes the expected
   Inner-Ridge geometry/component to participate while the default zero width
   preserves existing Shape behavior.

   One focused test may protect this boundary; separate tests for every
   individual width/default branch are unnecessary unless implementation
   exposes a defect.

2. **Positioning and interior-region boundary**

   Establish that Inner Ridge is positioned relative to the correct reference
   boundary and that its inside boundary becomes the available registered
   interior boundary used for incorporated Artwork.

   Coverage should exercise the materially different cases needed to protect
   the contract, particularly Outer Ridge present versus absent. Do not
   multiply tests merely to enumerate integrated/separate styles or every
   Shape geometry when existing lower-level geometry evidence already protects
   their common semantics.

3. **Extrude/Package ownership boundary**

   Establish that Inner Ridge survives as a distinct semantic component into
   physical manufacturing and receives its resolved physical color during
   Package.

   Protect the important invalidation boundary: a color-only change belongs to
   Package and must not require earlier geometry work.

4. **End-to-end manufacturing seam**

   If existing acceptance coverage does not already exercise the relevant
   Shape Feature path, add or extend one high-value manufacturing test proving
   that a Shape with a participating Inner Ridge can produce the expected
   printable multicomponent 3MF.

   Do not duplicate geometry, resolver, color, or Product-state assertions
   already protected at their owning layers.

Additional tests should be added when implementation reveals a bug, ambiguous
boundary, regression risk, or behavior not adequately protected by these
seams. Test count is not a completion criterion.

## High-level implementation steps

1. Reload the Shape Model definition and audit the current Shape Model
   specification, parameter definitions, Feature registration, Variant
   defaults, Structure, Compose, Extrude, Package, component/manifests, and
   relevant tests before changing implementation.

2. Add the Inner-Ridge parameters to the Shape Model's configuration/schema
   surface using the defaults, types, validation, and derived-color behavior
   defined by the Shape contract.

   Reuse existing parameter resolution and derived/default mechanisms,
   particularly the mechanism already used for Shape-owned colors. Do not
   introduce Inner-Ridge-specific configuration precedence.

3. Represent Inner Ridge as a Shape Feature using the existing Model/Feature
   architecture. Participation must derive from effective
   `shape_inner_ridge_width` rather than from Variant names, CLI behavior, or
   filesystem state.

4. Extend registered Shape geometry/composition so that a participating Inner
   Ridge follows the selected Shape geometry and is positioned using the
   applicable reference boundary:

   ```text
   Outer Ridge participates
       → inside boundary of Outer Ridge

   no Outer Ridge
       → outside boundary of Base
   ```

   Apply `shape_inner_to_outer_ridge_dist` inward from that reference to the
   outside boundary of the Inner Ridge.

5. Generalize available-interior computation so that the innermost
   participating ridge owns the interior boundary:

   ```text
   Inner Ridge participates
       → inside boundary of Inner Ridge

   else Outer Ridge participates
       → inside boundary of Outer Ridge

   else
       → outside boundary of Base
   ```

   Incorporated Artwork placement should continue to consume this reusable
   interior-region result rather than acquire Inner-Ridge-specific placement
   logic.

6. Extend Shape Extrude so that participating Inner-Ridge geometry layers on
   top of the complete Base and retains distinct semantic component identity.

   Extrude owns physical Inner-Ridge geometry and raise but does not assign its
   physical printing color.

7. Extend Shape Package so that a participating Inner-Ridge component receives
   the resolved `shape_inner_ridge_color`.

   Reuse existing Shape-owned component color and packaging mechanisms.
   `shape_inner_ridge_color` defaults to the resolved `shape_base_color`, and
   an explicit Inner-Ridge color overrides that derived default.

8. Ensure Product dependency/invalidation behavior reflects stage ownership.

   Geometry-affecting Inner-Ridge parameters must invalidate the appropriate
   geometry Products. A change only to `shape_inner_ridge_color` must affect
   Package without unnecessarily rebuilding Structure, Compose, or Extrude.

9. Exercise the critical behavioral seams described above as implementation
   proceeds. Add lower-level tests only when they protect behavior genuinely
   owned by that layer or expose/prevent an actual defect.

10. Run focused Shape tests after each meaningful behavioral slice. Once the
    Feature is complete, run the complete applicable test, type-check, and lint
    suite and inspect at least one representative packaged Shape Product where
    useful for confirming manufacturing behavior.

11. Recompare resulting HEAD with the Shape Model definition,
    `ARCHITECTURE.md`, existing Shape Variants, and this CHANGEPLAN. Credit
    behavior already satisfied and resolve any discovered mismatch at the
    layer that owns it.

## Completion criteria

Phase 1 is complete when:

- all four Inner-Ridge parameters participate in normal Shape configuration
  resolution with the defaults and validation defined by the Shape Model;
- the default configuration produces no Inner Ridge and preserves existing
  Shape behavior;
- positive `shape_inner_ridge_width` causes Inner Ridge to participate;
- Inner Ridge follows circle, square, and regular polygon Shape geometry
  through the existing geometry mechanisms;
- Inner Ridge can participate with either integrated or separate Outer Ridge
  and can also participate without an Outer Ridge;
- its outside boundary is positioned according to
  `shape_inner_to_outer_ridge_dist` and the correct Outer-Ridge/Base reference
  boundary;
- its inside boundary becomes the available registered interior boundary when
  Inner Ridge participates;
- incorporated Artwork continues to use the general Shape interior-region and
  fitting mechanisms;
- Inner Ridge layers on top of the Base with physical height determined by
  `shape_inner_ridge_raise`;
- Base geometry remains underneath the Inner Ridge rather than being
  partitioned by it;
- Inner Ridge remains a distinct semantic component through Extrude and
  Package;
- Package assigns the resolved `shape_inner_ridge_color`, including inheritance
  from `shape_base_color`;
- changing only Inner-Ridge color does not unnecessarily rebuild earlier
  geometry Products;
- a representative participating Inner Ridge reaches a correct printable 3MF;
- existing Shape behavior remains correct when Inner Ridge does not
  participate;
- critical participation, positioning/interior, Extrude/Package, and
  manufacturing seams have appropriate test protection without
  one-test-per-change ceremony;
- any bugs discovered during implementation have focused regression coverage
  where useful; and
- the complete applicable quality suite is green.


---

# Phase 2

---

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

---

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
artifact <command> --help
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

> Move customer artwork to a **correct, printable 3MF** with the fewest
> necessary decisions, actions, and computations.
