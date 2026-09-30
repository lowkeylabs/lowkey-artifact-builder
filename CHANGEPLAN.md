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


9. Implement each critical seam as a coherent TDD slice. Establish the seam
   with the minimum useful test or small test set, then complete the related
   implementation before beginning another RED/GREEN cycle. Do not subdivide
   the work into single-test/single-change cycles merely because multiple
   internal changes are required. Add lower-level tests only when they protect
   an independently meaningful boundary or reproduce a discovered defect.

10. Run focused Shape tests after completing each major behavioral seam. Once the
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


# Phase 2 — Implement the Shape Border Labels Feature

## Purpose

Implement the Border Labels Feature defined by the normative Shape Model
contract in:

```text
src/lowkey_artifact_builder/model/models/shape/DEFINITION.md
```

Border Labels are optional Shape-owned text components that follow the Shape
perimeter.

The Feature provides two independently participating components:

```text
top_border_label
bottom_border_label
```

The labels share a common lettering band, font setting, fitted glyph height,
border geometry, maximum span, and end-margin policy while retaining
independent text, physical raise, and packaged color.

The normative Shape definition owns the detailed semantics, participation
rules, geometry, fitting, interaction with Outer Ridge and Inner Ridge,
interior-region behavior, dimensionalization, component identity, and
packaging color behavior. This phase implements that contract without
redefining it here.

The implementation must extend the existing Shape manufacturing pipeline:

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

Border Labels do not require a new Stage, Variant, Realization, build workflow,
or CLI operation. Their participation follows from effective Shape
configuration.

The initial implementation focus is circular Shape geometry. The implementation
should preserve the geometry-neutral Feature boundaries established by the
Shape definition so that literal square and polygon perimeter paths can be
supported without replacing the Border Label model.

## Required behavior to establish

Top and Bottom Border Labels participate independently according to their
configured text.

When neither label participates, Border Labels must not alter existing Shape
geometry, Artwork placement, physical components, or packaged output.

A participating Border Label must:

- use the reference boundary defined by the Shape contract;
- follow the literal Shape perimeter at its applicable inward offset;
- participate in the common lettering band;
- use the common fitted font setting and glyph-height allocation;
- respect the configured maximum span and physical end margins;
- preserve normal left-to-right readability through the appropriate Top or
  Bottom path direction;
- remain a distinct semantic component through Shape composition, extrusion,
  and packaging;
- layer on top of the Base rather than partitioning or reducing Base X/Y
  geometry;
- use its own configured physical raise during Extrude; and
- receive its own resolved physical printing color during Package.

For circular Shapes, the implementation must establish the normative radial
relationships:

```text
reference boundary
    ↓ shape_border_label_width
bottom_border_label baseline
    ↓ resolved common glyph height
top_border_label baseline
    ↓ shape_border_label_width
inner boundary of Border Labels
```

The Bottom Border Label therefore follows the circular path one border width
inside the reference boundary.

The Top Border Label follows the circular path one border width plus the
resolved common glyph height inside the reference boundary.

The two labels traverse their paths in opposite directions so that both render
upright and read normally from left to right.

Text fitting must use rendered font measurements rather than treating SVG or
CSS font size as physical glyph height.

Both participating labels must use one common fitted font setting. The
configured maximum glyph height is used when both labels fit. Otherwise the
common height is reduced until every participating label fits its usable path.
The shorter label is not stretched or otherwise distorted to consume unused
path length.

The fitting implementation should preserve the useful behavior demonstrated by
the earlier `low-ornament-workflow` implementation where that behavior agrees
with the current Shape definition, including:

- measuring each participating string rather than assuming character-count
  geometry;
- retaining scale-independent font metrics;
- accounting for baseline-relative glyph bounds;
- using one common fitted font setting for Top and Bottom labels;
- preferring the configured maximum height when it fits;
- reducing the common height only when necessary;
- reserving physical end margins;
- and avoiding repeated external font measurement during iterative fitting.

The current Shape definition, not the earlier implementation, remains
authoritative where the two differ.

## Interaction with existing Shape Features

Border Labels must use the same reference-boundary semantics already defined
by Shape Features:

```text
Outer Ridge participates
    → inside boundary of Outer Ridge

no Outer Ridge
    → outside boundary of Base
```

Outer-Ridge style must not change the resulting Border Label reference
boundary.

Border Labels and Inner Ridge remain independent Features.

Border Label participation must not cause Inner Ridge to participate, and
Inner-Ridge participation must remain controlled solely by:

```text
shape_inner_ridge_width
```

When Border Labels and Inner Ridge both participate, the Inner Ridge outside
boundary follows the inner border of the Border Label region according to the
normative Shape contract.

When Border Labels participate without Inner Ridge, the inner Border Label
boundary becomes the available registered Shape interior boundary.

When Inner Ridge participates, its inside boundary remains the available
registered interior boundary for incorporated Artwork.

Artwork placement must continue to consume the general Shape interior-region
result rather than acquire Border-Label-specific fitting logic.

Phase 2 should build on the completed Inner Ridge capability from Phase 1
rather than create a second competing implementation of ridge positioning or
interior-region ownership.

## Stage ownership

Border Label implementation must preserve existing Shape stage
responsibilities.

### Structure

Shape Structure remains responsible for canonical registered Shape geometry.

Do not add Border-Label-specific structural products merely because labels
exist downstream unless implementation evidence demonstrates that such a
Product is required by the existing Shape architecture.

### Compose

Shape Compose owns the registered spatial relationships required by Border
Labels.

For the initial circular implementation, Compose should establish or preserve
the information needed for:

- the applicable reference boundary;
- Top and Bottom baseline paths;
- the common lettering band;
- font measurement and fitting;
- the resolved common glyph height;
- readable Top and Bottom text paths;
- the inner Border Label boundary; and
- the resulting available registered interior boundary.

Physical Shape parameters may be converted into relative registered-space
relationships using `shape_size` where required by the existing Shape
composition model. This does not make registered Shape space physical.

Font measurement and text-on-path construction should be implemented as
reusable mechanical operations where practical rather than embedding external
tool mechanics throughout Shape policy.

Do not obtain reuse by invoking another Model's Stage implementation or by
coupling the current Model to the historical `low-ornament-workflow`
application.

### Extrude

Shape Extrude owns Border Label physical manufacturing geometry.

A participating Top Border Label and Bottom Border Label must become distinct
Shape-owned physical components using their independently configured raises.

Border Label geometry layers on top of the Base. The Base remains underneath
the Border Label region and retains its existing X/Y extent.

Extrude preserves semantic component identity but does not assign physical
printing color.

### Package

Shape Package owns Border Label physical color assignment.

The Top and Bottom Border Label components must receive their independently
resolved configured colors during Package.

Extend the existing Shape-owned component color mechanism rather than adding a
parallel packaging path for labels.

Changing only a Border Label color must not require Shape Structure, Compose,
or Extrude geometry to be recomputed.

## TDD and validation strategy

Use TDD to protect important Border Label behavioral seams rather than testing
every parameter, helper, glyph, or intermediate calculation.

Prefer extending existing Shape tests where they already exercise the owning
boundary. Introduce a new focused test module only when Border Label behavior
does not fit an existing behavioral test surface.

The critical seams for this Feature are:

1. **Participation and registered-geometry seam**

   Establish that configured text causes the applicable Top or Bottom Border
   Label to participate and that absent label text preserves existing Shape
   behavior.

   Protect independent participation without separately testing every
   permutation unless implementation reveals a defect.

2. **Circular path and shared-fitting seam**

   Establish one representative circular case proving the important geometry
   relationships:

   - the correct Outer-Ridge/Base reference boundary is used;
   - Top and Bottom baselines occupy the common lettering band at their
     specified offsets;
   - the two paths have the required opposite directions; and
   - both labels resolve to one common fitted font setting/height when fitting
     is required.

   Prefer one or a small number of representative strings that expose these
   relationships rather than a catalog of typography cases.

3. **Interior-region interaction seam**

   Establish that participating Border Labels affect the available registered
   interior boundary according to the Shape contract and that Inner Ridge,
   when participating, remains the innermost boundary used for Artwork.

   Reuse Phase 1 interior-region evidence rather than repeating all
   Outer-Ridge and Inner-Ridge combinations.

4. **Extrude/Package ownership seam**

   Establish that Top and Bottom labels survive as distinct physical
   components with independent raises and receive their independent physical
   colors only during Package.

   Protect the important invalidation boundary: changing only a Border Label
   color belongs to Package and must not unnecessarily invalidate registered
   composition or physical extrusion.

5. **End-to-end manufacturing seam**

   Add or extend one high-value acceptance/manufacturing test proving that a
   representative circular Shape with Border Labels reaches a correct
   multicomponent printable 3MF.

   Do not reproduce font-fitting, geometry, resolver, component-manifest, or
   color assertions already protected at their owning boundaries.

Additional tests should be added when implementation exposes an actual bug,
ambiguous boundary, regression risk, or otherwise unprotected behavior. Test
count is not a completion criterion.

## High-level implementation steps

1. Recompare current HEAD with the Shape definition and completed Phase 1
   implementation before beginning Border Label production changes. Credit any
   reusable Inner-Ridge, registered-boundary, component-manifest, and
   Shape-owned color work already present.

2. Add the Border Label parameters to the Shape Model configuration surface
   using the defaults, validation, participation, and derived behavior defined
   by the Shape contract.

   Use ordinary Model/default, Variant, and Artifact-specific configuration
   resolution. Do not introduce a Border-Label-specific precedence mechanism.

3. Establish independent Top and Bottom participation from their effective
   text parameters while keeping shared Border Label policy common to both
   components.

4. Extract or introduce the smallest reusable font-measurement and text-path
   operations needed by Shape.

   Use the earlier `low-ornament-workflow` implementation as implementation
   evidence where useful, but adapt its mechanics to the current registered
   Shape architecture rather than porting its ornament-specific radial-stack
   assumptions.

5. Implement the circular Border Label fitting operation.

   Measure participating strings, derive scale-independent metrics, attempt the
   configured maximum glyph height, and reduce the common height only when
   necessary for every participating label to fit within its usable path.

   Avoid repeatedly invoking an external measurement tool during iterative
   fitting when measured metrics can instead be scaled arithmetically.

6. Extend Shape Compose to derive the circular Top and Bottom baseline paths
   from the applicable registered reference boundary and the configured
   physical Border Label relationships.

   Preserve opposite Top/Bottom path directions and baseline-relative glyph
   placement so that both labels are upright and readable.

7. Integrate the Border Label inner boundary with the reusable Shape
   interior-region computation.

   When Inner Ridge participates, preserve its ownership of the innermost
   Artwork boundary. When it does not, allow the Border Label inner boundary
   to become the available interior boundary.

8. Extend Shape Extrude so that each participating Border Label becomes a
   distinct Shape-owned physical component with its configured raise above the
   Base.

9. Extend Shape Package so that Top and Bottom Border Labels receive their
   independently resolved physical colors through the existing Shape-owned
   component-color mechanism.

10. Ensure Product dependencies and invalidation reflect stage ownership.

    Text, font, fitting, border, and path-affecting changes must invalidate the
    Products that depend on their geometry. Raise-only changes should begin at
    the physical dimensionalization boundary where possible. Color-only changes
    must remain Package concerns.

11. Implement each critical seam as a coherent TDD slice. Establish the seam
    with the minimum useful test or small test set, then complete the related
    implementation before beginning another RED/GREEN cycle. Do not subdivide
    the work into single-test/single-change cycles merely because multiple
    internal changes are required. Add lower-level tests only when they protect
    an independently meaningful boundary or reproduce a discovered defect.

12. Run focused Shape tests after each coherent behavioral slice. When the
    circular Border Label implementation is complete, run the complete
    applicable test, type-check, and lint suite and inspect at least one
    representative packaged circular Shape with both labels.

13. Recompare resulting HEAD with `ARCHITECTURE.md`, the Shape definition,
    existing Shape Variants, and this CHANGEPLAN. Resolve discovered semantic
    mismatches at their owning layer rather than encoding them as Border Label
    exceptions.

## Completion criteria

Phase 2 is complete when:

- Border Label parameters participate in normal Shape configuration resolution
  according to the Shape definition;
- Top and Bottom Border Labels participate independently from their configured
  text;
- neither label participating preserves existing Shape behavior;
- circular Border Labels use the correct Outer-Ridge/Base reference boundary;
- the Bottom Border Label baseline is one configured border width inward from
  that reference boundary;
- the Top Border Label baseline is one configured border width plus the
  resolved common glyph height inward from that reference boundary;
- Top and Bottom labels traverse their circular paths in opposite directions
  and both render upright and readable from left to right;
- rendered font metrics rather than nominal font size determine physical glyph
  fitting;
- participating labels share one common fitted font setting and glyph-height
  allocation;
- the configured maximum glyph height is retained when both labels fit and is
  reduced only when necessary;
- each participating label respects the configured maximum span and physical
  end margins;
- shorter text is not stretched or compressed to fill unused path;
- Border Labels use the correct inner boundary for Shape interior-region
  computation;
- Border Labels do not cause Inner Ridge to participate;
- a participating Inner Ridge remains the innermost boundary used for
  incorporated Artwork;
- Border Labels layer on the Base without partitioning or reducing Base X/Y
  geometry;
- Top and Bottom Border Labels survive as distinct semantic and physical
  components with independently configurable raises;
- Shape Package assigns their independently resolved physical colors;
- changing only Border Label color does not unnecessarily rebuild earlier
  geometry Products;
- a representative circular Shape with Border Labels produces a correct
  multicomponent printable 3MF;
- important participation, circular fitting/path, interior-region,
  Extrude/Package, and manufacturing seams have focused test protection;
- any defects discovered during implementation receive focused regression
  coverage where useful; and
- the complete applicable quality suite is green.

Square and regular-polygon Border Label path construction need not be completed
as part of this initial Phase 2 implementation. The implementation must not
introduce circle-specific architecture that conflicts with the normative
literal-perimeter semantics already defined for those geometries.

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
