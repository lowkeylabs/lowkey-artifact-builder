# CHANGEPLAN

## Purpose

Implement the `coin` model defined by:

``` text
src/lowkey_artifact_builder/model/models/coin/DEFINITION.md
```

while preserving the manufacturing architecture and operator workflow
established by current repository HEAD.

Coin combines exactly two complete physical Shape Products into one
two-sided manufactured object:

``` text
Shape Face A ──┐
               ├──> Coin physical composition ──> printable 3MF
Shape Face B ──┘
```

The implementation must preserve the architectural distinction between
reusable physical manufacturing Products and packaged 3MF Products. Coin
consumes Shape after Shape physical dimensionalization and before Shape
packaging; it does not reconstruct registered Shape geometry, invoke
Shape stage implementations, or require packaged Shape Products.

The ordinary value chain remains:

``` text
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

Coin extends that value chain through Product composition rather than
introducing a separate operator workflow.

This CHANGEPLAN contains remaining work rather than a history of
completed implementation. Completed behavior should normally be credited
from HEAD and removed from the plan rather than retained as historical
checklists.

## Planning and development rules

`ARCHITECTURE.md` and the applicable Model `DEFINITION.md` files are
normative. Repository HEAD defines the current implementation. The CLI
README defines the intended operator-facing command model. This
CHANGEPLAN describes temporary remaining work and must not redefine
permanent architecture.

At the beginning of a thread and before each meaningful implementation
slice:

1.  reload and follow `prompts/NEW_THREAD.md`;
2.  compare CHANGEPLAN with current HEAD, `ARCHITECTURE.md`, applicable
    Model definitions, and the relevant CLI documentation;
3.  credit behavior HEAD already satisfies;
4.  identify the next unmet behavioral boundary rather than assuming the
    plan is still current;
5.  resolve known semantic or architectural questions before encoding
    behavior in tests, while allowing test-first exploration to discover
    or clarify uncertain seams and ownership boundaries;
6.  organize TDD around major behavioral seams or boundaries, using one
    test or a small coherent test set to drive a substantial
    implementation slice rather than creating single-test/single-change
    cycles;
7.  implement the smallest correct change at the layer that owns the
    behavior;
8.  run focused tests and then the appropriate complete quality suite;
    and
9.  reevaluate the plan against the resulting HEAD.

Tests should protect useful behavioral boundaries rather than inventory
implementation details. High-level application and Model seams should be
protected as they are introduced, while lower-level tests should be
added only where they protect behavior actually owned by that layer.

A newly discovered defect that can produce an incorrect manufacturing
Product, corrupt persistent manufacturing state, or cause material
value-chain inefficiency takes priority over presentation work.

Every phase must leave the application production-capable.

## Common constraints

Preserve the separation between operator presentation and reusable
application behavior:

``` text
CLI / TUI / GUI / API
          │
          ▼
reusable application operations
          │
          ▼
configuration / planning / engine / Products
```

Preserve the architectural Product graph:

-   Products are addressed by logical identity rather than generated
    paths.
-   Dependencies determine execution.
-   Only the transitive closure required for requested Products is
    realized.
-   A consumer may use Products from another Realization, Model,
    Artifact, or previous build.
-   A 3MF is not a privileged Product.
-   Dynamic component collections are consumed through manifests rather
    than directory scanning.
-   Stage implementations execute from complete `StageContext` values
    and do not traverse other Models.
-   Generic configuration, planning, dependency, and execution
    infrastructure remains Model-independent.
-   Model-specific geometry, compatibility, orientation, and color
    policy remain with the owning Model.
-   Reusable operations should contain only genuinely Model-independent
    mechanics.

For Coin specifically:

-   `faceA` and `faceB` are independent semantic dependency roles.
-   Each Face is a complete physical Shape Product established after
    Shape dimensionalization and before Shape packaging.
-   The two Shape `Z = 0` underside planes establish the mating plane.
-   Coin transforms complete Faces rather than reconstructing or
    independently repositioning their components.
-   Source Shape components remain independently identifiable and
    acquire the required `faceA-` or `faceB-` semantic prefix.
-   Shape Feature geometry is preserved rather than regenerated by Coin.
-   Coin physical composition does not assign physical printer colors.
-   Coin packaging resolves physical printer colors across the complete
    two-Face object.
-   The physical Coin component collection remains a reusable Product
    independent of the packaged Coin.

Do not introduce compatibility behavior merely to preserve an obsolete
test. When an existing test is encountered, preserve its contractual
assertions while relaxing incidental inventory, implementation, or
mutable-configuration assumptions as directed by
`prompts/TEST_DRIVEN_DEVELOPMENT.md`.

## TDD cycles

TDD remains test-first. Before implementing a meaningful new behavior,
write a test that exercises the behavioral seam or boundary being
established.

The purpose of the initial failing test is not only verification. A test
may also be used to discover or clarify the appropriate seam, ownership
boundary, or contract before implementation. If the test exposes a
better boundary than the one initially assumed, refine the design and
test before committing to the implementation.

TDD cycles should normally correspond to substantial behavioral seams or
boundaries rather than individual implementation changes. Once a failing
test establishes the intended seam, implement the coherent behavior
necessary to make that seam work. Do not begin a new RED/GREEN cycle
merely because that implementation requires another helper, parameter,
branch, component, or internal refactoring.

One test may be sufficient to establish a seam. A small coherent group
of tests is appropriate when materially different cases are necessary to
define the same boundary. Prefer these high-value behavioral tests over
many narrow tests that separately inventory implementation details.

Add narrower tests when they help discover an uncertain boundary,
protect an independently meaningful contract, reproduce a defect, or
address a specific algorithmic or regression risk.

------------------------------------------------------------------------

# Phase 1 --- Establish reusable physical Shape inputs

## Purpose

Remove the current architectural blockers that prevent two complete
Shape physical Products from being consumed independently and faithfully
by Coin.

These changes are prerequisites to Coin but are not Coin-specific work.
They should leave the generic dependency system and Shape physical
Product boundary more generally reusable.

Current HEAD already supports:

-   logical cross-Artifact and cross-Realization `ProductRef` identity;
-   targeted producer builds and transitive dependency closure;
-   persistent Shape extrusion manifests;
-   independent Stage execution through `StageContext`;
-   Artifact-color identity for incorporated Artwork through Shape
    Extrude; and
-   Shape Package ownership of final physical printer-color assignment.

Current HEAD does not yet provide all semantics required by Coin:

1.  consumer dependency identity is effectively derived from producer
    Product identity, so two dependencies on the same producer
    Model/Stage/Product cannot coexist as independent `faceA` and
    `faceB` roles;
2.  Shape-owned extrusion components do not preserve sufficient logical
    color requirements for a downstream Model to package them faithfully
    without reopening producer configuration; and
3.  integrated Outer Ridge dimensionalization does not currently honor
    the normative full-depth inlaid Shape contract.

These are separate behavioral seams and should normally be developed as
separate coherent TDD slices within this phase.

## 1.1 Independent consumer dependency roles

### Behavioral boundary

A Stage must be able to declare two independently named consumer roles
that both refer to the same producer Model/Stage/Product definition and
bind each role independently to the same or different concrete producer
Products.

The consumer-side role is not part of producer Product identity.

For Coin this permits:

``` text
faceA ──> <artifact>:shape:<realization>:<physical-stage>:manifest
faceB ──> <artifact>:shape:<realization>:<physical-stage>:manifest
```

including:

-   the same Shape Product bound to both roles;
-   two Shape Realizations of one Artifact; and
-   Shape Realizations from different Artifacts.

Execution-facing `StageContext` input names must remain unambiguous and
consumer-semantic. Fingerprinting, incremental state, planning, and
dependency execution must distinguish the two bindings without changing
canonical `ProductRef` identity.

### TDD seam

Begin with a synthetic producer and consumer rather than Coin.

Use one coherent generic dependency test set to establish that two named
roles may target the same producer Product definition, receive
independent bindings, appear independently in the planned Stage context,
and participate correctly in dependency/fingerprint state.

Update existing generic tests only where their current assumptions about
dependency input naming or binding identity are intentionally
superseded.

Do not add Coin semantics to the generic engine tests.

### Completion criteria

-   Two consumer dependency roles may refer to the same producer
    Model/Stage/Product definition.
-   Each role binds independently to a concrete Artifact and
    Realization.
-   Both roles may bind to the exact same concrete Product.
-   Planned and independently resolved Stage contexts expose unambiguous
    semantic inputs.
-   Producer `ProductRef` identity remains unchanged.
-   Targeted dependency builds remain minimal.
-   Incremental/fingerprint behavior distinguishes dependency roles and
    their bindings correctly.
-   Existing single-dependency consumers continue to work after
    deliberate migration to the generalized contract.
-   Focused dependency/config/context tests, the broader non-slow suite,
    pyright, and ruff pass.

## 1.2 Correct integrated inlaid Outer Ridge dimensionalization

### Behavioral boundary

Bring Shape Extrude into conformance with the existing Shape definition
before Coin begins consuming Shape physical Products.

For `shape_raise_style = "inlaid"`, a participating Outer Ridge is a
nonoverlapping full-depth partition spanning `Z = 0` through
`shape_base_raise`, regardless of whether `shape_outer_ridge_style`
resolves to `integrated` or `separate`.

The union of Base and participating inlaid components must reconstruct
the intended complete flat Shape volume.

### TDD seam

Add or refine one high-value Shape extrusion regression seam
demonstrating that integrated + inlaid Outer Ridge follows the normative
full-depth partition contract.

Prefer assertions about assembled geometry, component Z extent, and
nonoverlap/reconstruction over assertions about private helper
selection.

Where the same dimensionalization machinery covers multiple Shape
geometries, do not duplicate equivalent tests for every helper or
geometry unless a materially different implementation path creates
independent regression risk.

### Completion criteria

-   Integrated + inlaid Outer Ridge conforms to Shape `DEFINITION.md`.
-   Existing raised integrated behavior remains unchanged.
-   Existing separate raised and inlaid behavior remains unchanged.
-   No registered Structure or Compose semantics change.
-   The correction is protected at a meaningful Shape physical-product
    boundary.
-   Focused Shape tests, the broader non-slow suite, pyright, and ruff
    pass.

## 1.3 Preserve Shape logical color requirements through physical dimensionalization

### Behavioral boundary

A complete physical Shape Product must contain sufficient persistent
logical color information for a downstream consumer to preserve the
Shape's intended component colors without resolving physical printer
assignments and without reopening the source Shape's configuration.

This applies to Shape-owned components as well as the existing
incorporated Artwork color identity.

Shape physical dimensionalization must not assign physical printer
colors.

Shape Package must continue to own physical printer-color resolution for
a standalone Shape, and changing only packaging/printer-color
configuration must not change Shape physical geometry.

The persistent representation may distinguish different kinds of logical
color identity where their semantics differ; incorporated Artwork's
Artifact-color identity need not be collapsed into Shape-owned semantic
color configuration.

### TDD seam

Drive this change from the reusable Shape physical Product boundary.

Establish that a Shape extrusion manifest carries enough logical color
information for its components to be packaged correctly without
consulting Shape geometry-stage configuration for color semantics.

Then establish that ordinary Shape packaging consumes that persistent
logical color information and retains existing standalone Shape color
behavior.

Avoid freezing an incidental JSON schema beyond fields whose persistence
is part of the reusable Product contract.

### Completion criteria

-   Shape-owned physical components persist their logical color
    requirements.
-   Incorporated Artwork continues to preserve its required
    Artifact-color identity.
-   No physical printer assignment occurs during Shape physical
    dimensionalization.
-   Shape Package can package a complete Shape from its physical Product
    and packaging configuration without reconstructing source Shape
    color policy.
-   Standalone Shape output preserves existing intended color behavior.
-   Changing only `printer_colors` does not stale or alter Shape
    physical geometry.
-   The Shape physical Product is sufficient for a downstream Model to
    preserve logical component colors.
-   Focused Shape color/package tests, the broader non-slow suite,
    pyright, and ruff pass.

## Phase 1 completion

Phase 1 is complete when a downstream Model can independently consume
two complete Shape physical Products, including the same Product twice,
while each Product is normatively correct and carries the logical
component information needed for later whole-object packaging.

Before closing the phase, rerun the appropriate complete slow and
non-slow test suite and reevaluate HEAD against `ARCHITECTURE.md`, Shape
`DEFINITION.md`, Coin `DEFINITION.md`, and this plan.

------------------------------------------------------------------------

# Phase 2 --- Introduce the Coin physical composition model

## Purpose

Add the Coin Model and establish its reusable physical composition
Product.

This phase owns Coin semantics before packaging: Face dependencies,
compatibility, orientation, rigid Face transformation, component
identity, and persistent physical Coin component collection.

Do not make Coin reconstruct Shape geometry or invoke Shape stage
implementations. Coin consumes complete physical Shape Products through
the generic dependency system established in Phase 1.

The exact Coin Stage names, numeric identifiers, manifest
representation, and private helper organization should be chosen from
existing repository conventions during implementation. They are not
additional permanent semantics unless the normative specifications are
intentionally amended.

## 2.1 Model declaration and Face dependency contract

### Behavioral boundary

Register a conforming `coin` Model with an ordinary `default` Variant
and the minimum parameters, Stages, Products, and dependencies required
by the Coin definition.

The Model must declare exactly two semantic Face dependency roles:

``` text
faceA
faceB
```

Both consume complete physical Shape Products.

Coin orientation supports:

``` text
aligned
inverted
```

with `aligned` as the Model default.

The physical Coin component collection is a persistent Product
independent of the packaged Coin.

### TDD seam

Add Coin Model tests for the Coin-specific declarative and configuration
contract only where registration/configuration behavior is not already
guaranteed by generic Model tests.

Do not create inventory tests that require unrelated generic registries
or Models to enumerate `coin` permanently.

### Completion criteria

-   `coin` is a registered Model.
-   `coin.default` is directly usable.
-   Coin declares independent `faceA` and `faceB` Shape physical Product
    dependencies.
-   Orientation resolves with `aligned` as the normative default and
    accepts `inverted`.
-   Invalid Coin orientation is rejected at the appropriate
    Model/configuration boundary.
-   A persistent physical Coin component Product is declared separately
    from the packaged Product.
-   Coin registration does not introduce Coin-specific logic into the
    generic engine.

## 2.2 Face compatibility

### Behavioral boundary

Coin validates whether two already-dimensionalized Shapes can mate
without repairing or reconstructing them.

At minimum, the transformed outer structural boundaries must coincide at
the mating plane.

Face-local geometry may differ where it does not prevent mating.

Loop and Hole require bilateral compatible geometry:

-   Loop on only one Face is invalid.
-   Hole on only one Face is invalid.
-   Participating Loops must coincide after Face orientation.
-   Participating Holes must align after Face orientation.

Compatibility must be determined from persistent physical Shape Product
information sufficient for this purpose. Coin must not reopen source
Shape configuration as a substitute for a reusable Product contract and
must not infer semantic compatibility by scanning generated directories.

If implementation work reveals that the Shape physical Product lacks
required persistent compatibility metadata, extend that Product contract
at the Shape boundary rather than teaching Coin to reverse-engineer STL
geometry or producer configuration. Such an extension must preserve
Shape ownership of Shape semantics.

### TDD seam

Use a small coherent set of Coin compatibility cases that distinguishes:

-   compatible ordinary Faces;
-   incompatible structural boundaries; and
-   bilateral Loop/Hole mismatch where those Features participate.

Do not exhaustively cross-product every Shape Feature or geometry.

Tests should express compatibility outcomes rather than private metadata
or comparison algorithms.

### Completion criteria

-   Compatible Faces are accepted regardless of Artifact/Realization
    identity.
-   Different face-local decoration and dimensionalization remain valid
    when the mating contract is satisfied.
-   Structural-boundary incompatibility is rejected before a Coin
    manufacturing Product is published.
-   One-sided or misaligned Loop/Hole participation is rejected.
-   Compatibility uses persistent Product semantics rather than source
    configuration or directory scanning.
-   Failures are deterministic domain/model failures rather than partial
    manufacturing output.

## 2.3 Rigid Face composition and orientation

### Behavioral boundary

Compose the two complete Shape Faces around their common `Z = 0` mating
plane.

The two Faces must occupy opposite sides of the mating plane with their
visible Shape surfaces facing outward.

Every component belonging to a Face receives one common rigid Face
transformation. Source dimensions and intra-Face registration are
preserved.

Implement both normative orientations:

-   `aligned`: semantic tops appear at the same physical end when each
    outward Face is viewed directly;
-   `inverted`: Face B semantic top appears at the opposite physical
    end.

Coin introduces no independent Base and does not regenerate Shape
Features.

### TDD seam

Use representative asymmetric physical geometry or semantic markers so
aligned and inverted orientation can be distinguished unambiguously.

One high-value composition test should establish the mating-plane
relationship, outward-facing Faces, preserved dimensions, and common
per-Face transform.

A second case is justified for the materially different `inverted`
orientation.

Do not test individual transformation helper calls.

### Completion criteria

-   Face A and Face B meet at their Shape underside planes.
-   Their physical volumes occupy opposite sides of the mating plane
    rather than overlapping as duplicate Shapes.
-   All components of each Face retain their mutual registration.
-   `aligned` orientation satisfies the normative semantic-top
    relationship.
-   `inverted` orientation satisfies the normative semantic-top
    relationship.
-   Source component dimensions are preserved.
-   Coin creates no replacement Base, ridge, label, Artwork, fill, Loop,
    or Hole geometry.

## 2.4 Component identity and persistent physical Coin Product

### Behavioral boundary

Persist the complete transformed component collection as a reusable Coin
Product.

Every source component remains independently identifiable.

Face A components use:

``` text
faceA-<source-semantic-identity>
```

Face B components use:

``` text
faceB-<source-semantic-identity>
```

The remainder of source semantic identity and logical color requirements
are preserved.

Components must not be merged because they touch or share a logical
color.

### TDD seam

Test the physical Coin Product as a manifest/component-collection
boundary, using representative Shape-owned and incorporated Artwork
components.

Protect semantic namespacing, path/materialization validity, component
cardinality where material to the fixture, and preservation of logical
color requirements.

Avoid snapshotting incidental manifest formatting or directory layout.

### Completion criteria

-   Every source physical component appears once in the Coin physical
    Product.
-   `faceA-` and `faceB-` namespacing is correct.
-   The source semantic identity after the Face prefix is unchanged.
-   Logical color requirements survive composition.
-   Touching/same-color components remain independently represented.
-   The physical Coin component collection is persistent, canonically
    addressable, and consumable without packaging.
-   Requesting only the physical Coin Product does not execute Coin
    packaging or source Shape packaging.

## Phase 2 completion

Phase 2 is complete when Coin can consume two compatible complete Shape
physical Products and persist a correctly oriented, correctly
namespaced, color-semantic-preserving physical Coin component collection
without producing a 3MF.

Before closing the phase, rerun the appropriate complete slow and
non-slow test suite and reevaluate HEAD against all permanent
specifications and this plan.

------------------------------------------------------------------------

# Phase 3 --- Package the complete Coin

## Purpose

Produce a printable multi-component Coin 3MF from the reusable physical
Coin Product.

Packaging owns final physical printer-color assignment across both Faces
as one manufactured object. It does not alter Face geometry,
orientation, Feature participation, or component membership.

## 3.1 Whole-Coin color assignment

### Behavioral boundary

Resolve all logical color requirements from both Faces against the Coin
Realization's `printer_colors` as one packaging problem.

Preserve the distinction between Shape-owned logical color requirements
and incorporated Artwork Artifact-color identity where their source
semantics require different representation, while producing one coherent
physical printer assignment for the complete Coin.

Changing only Coin packaging/printer-color configuration must not alter
or rebuild the physical Coin geometry Product except through normal
downstream staleness of packaging.

### TDD seam

Use a Coin containing representative components from both Faces with
logical color requirements that demonstrate whole-object assignment.

Protect final physical color semantics and the geometry/package
ownership boundary rather than exact internal assignment data
structures.

Reuse generic color-assignment machinery where its existing contract
applies; do not duplicate the mathematical color assignment algorithm
inside Coin.

### Completion criteria

-   Both Faces participate in one final printer-color assignment.
-   Logical Face color intent is preserved.
-   Physical printer colors are absent from the upstream physical Coin
    Product.
-   Changing only `printer_colors` affects packaging rather than
    physical Coin composition.
-   Coin-specific code does not duplicate generic color-assignment
    mechanics.

## 3.2 Printable 3MF packaging

### Behavioral boundary

Package the complete physical Coin component collection into a valid
multi-component 3MF.

Packaged component names preserve:

``` text
faceA-...
faceB-...
```

and source semantic component identity, together with the repository's
established resolved printing-color naming policy.

Packaging must not merge components merely because they share a physical
printer color.

### TDD seam

Add a focused Coin package test protecting:

-   consumption of the persistent physical Coin Product;
-   preservation of Face/component identity;
-   physical printer-color assignment; and
-   valid multi-component 3MF output.

Do not retest the detailed geometry transformations already protected in
Phase 2.

### Completion criteria

-   Coin produces a valid printable 3MF.
-   Every physical Coin component intended for packaging is represented.
-   Face and semantic component identity remain observable in packaged
    component names.
-   Same-color components remain independent.
-   Packaging does not mutate or reconstruct Coin physical geometry.
-   Requesting the packaged Product realizes only the required Coin and
    producer dependency closure.

## Phase 3 completion

Phase 3 is complete when a valid physical Coin Product can be packaged
into a printable 3MF with correct whole-Coin color assignment and
preserved component identity.

Run the appropriate complete slow and non-slow test suite, pyright, and
ruff before closing the phase.

------------------------------------------------------------------------

# Phase 4 --- End-to-end Coin manufacturing acceptance

## Purpose

Establish the complete Coin capability across the real dependency graph
without duplicating the focused semantics already protected by earlier
phases.

The acceptance boundary should demonstrate that Coin is a first-class
Model in the ordinary build workflow, not a special-purpose script or
alternate pipeline.

## Acceptance seam

Add a small number of broad acceptance cases sufficient to demonstrate
the architecturally distinct source relationships required by Coin.

At minimum, establish that an Artifact can build a Coin 3MF from two
configured Shape Face dependencies and that dependency-driven execution
reaches the required Shape physical Products without requiring Shape
packaging.

The acceptance coverage must collectively prove the Coin definition
permits:

-   the same Shape Product to serve both Faces;
-   distinct Shape Realizations to serve the two Faces; and
-   cross-Artifact Shape consumption.

These cases need not each execute the complete expensive external-tool
manufacturing path if lower-level integration tests can establish a case
more precisely. Use slow integration coverage only where actual
modeling-tool output is necessary to prove the manufacturing boundary.

At least one real manufacturing acceptance path should validate the
resulting Coin as a printable two-sided physical object with
representative Face components.

Do not reproduce every Feature, orientation, compatibility, or color
assertion already covered by focused tests.

## Operator workflow

Coin should participate through the existing
Artifact/Variant/Realization build workflow.

Do not add a Coin-specific CLI command merely to expose the Model.

Update CLI or user documentation only where the existing generic
workflow needs Coin-specific examples or where HEAD exposes a genuine
generic-model limitation.

`artifact build` remains the ordinary manufacturing action.

## Completion criteria

-   A configured Coin Realization builds through the ordinary
    dependency-driven workflow.
-   The same Shape Product can supply both Faces.
-   Different Realizations of one Artifact can supply the Faces.
-   Shape Products from different Artifacts can supply the Faces.
-   Coin consumes Shape physical Products without requiring Shape 3MF
    packaging.
-   At least one representative real Coin build produces the intended
    two-sided physical geometry and printable 3MF.
-   Incremental rebuild behavior remains dependency-driven: unchanged
    current Shape physical Products are reused.
-   Existing Artwork and Shape workflows remain production-capable.
-   No Coin-specific orchestration has leaked into the generic engine or
    CLI.
-   Applicable permanent/user documentation reflects the completed
    public behavior.
-   The complete slow and non-slow test suite, pyright, and ruff pass.

## Project completion

Coin implementation is complete when repository HEAD conforms to
`ARCHITECTURE.md`, Artwork `DEFINITION.md`, Shape `DEFINITION.md`, and
Coin `DEFINITION.md`; all requirements above are either satisfied by
HEAD or removed from this plan as obsolete; and the complete quality
suite is green.

At that point, reevaluate `CHANGEPLAN.md` against HEAD rather than
preserving it as implementation history. Once no remaining
implementation work is described, the temporary plan may be removed or
replaced for the next body of work.
