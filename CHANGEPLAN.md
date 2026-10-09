# CHANGEPLAN

## Purpose

Implement the `coin` model defined by:

``` text
src/lowkey_artifact_builder/model/models/coin/DEFINITION.md
```

while preserving the manufacturing architecture and operator workflow
established by current repository HEAD.


with:

```markdown
Coin combines exactly two complete packaged Shape Products into one
two-sided manufactured object:

```text
packaged Shape Face A ──┐
                        ├──> Coin physical composition ──> printable 3MF
packaged Shape Face B ──┘
```

The implementation must preserve packaged Shape as the reusable physical
Product boundary consumed by Coin. Each Face is a complete packaged Shape
Product containing a 3MF authoritative for component geometry, component
identity, and resolved physical colors, together with persistent Shape-level
metadata required for downstream compatibility. Coin does not reconstruct
registered Shape geometry, invoke Shape stage implementations, reopen source
Shape configuration, or regenerate an incompatible Shape on behalf of a Face.

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
-   Dynamic component collections are consumed through persistent Product
    representations rather than directory scanning.
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
-   Each Face is a complete packaged Shape Product.
-   The packaged Shape 3MF is authoritative for component geometry,
    component identity, and resolved physical colors.
-   Persistent Shape-level metadata supplies compatibility information that
    cannot safely be recovered from the packaged 3MF.
-   Face B must use `inlaid` Shape dimensionalization.
-   Coin rejects an incompatible Face rather than regenerating or
    re-dimensionalizing it.
-   The two Shape `Z = 0` underside planes establish the mating plane.
-   Coin transforms complete Faces rather than reconstructing or independently
    repositioning their components.
-   Source Shape components remain independently identifiable and acquire the
    required `faceA-` or `faceB-` semantic prefix.
-   Shape Feature geometry is preserved rather than regenerated by Coin.
-   Resolved source component colors are preserved through Coin composition
    and packaging.
-   Coin does not reopen source Shape configuration or reinterpret Shape color
    policy.
-   The physical Coin component collection remains a reusable Product
    independent of the packaged Coin.
-   Packaged Coin recoloring remains a Model-independent 3MF operation rather
    than a Coin-specific color-assignment mechanism.


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

# Phase 1 --- Establish reusable packaged Shape inputs

## Purpose

Establish the reusable Shape Product boundary required by Coin.

Coin consumes complete packaged Shape Products rather than Shape extrusion Products. A packaged Shape provides:

- the complete physical Shape geometry;
- independently identifiable physical components;
- resolved physical component colors; and
- persistent Shape-level metadata required for downstream compatibility.

The packaged 3MF is authoritative for component geometry, component identity, and resolved component colors. Shape-level metadata accompanies the packaged Shape Product when required compatibility information cannot safely be recovered from the 3MF.

These changes are prerequisites to Coin but should remain generally useful Product and format capabilities rather than Coin-specific infrastructure.

Current HEAD already supports:

- logical cross-Artifact and cross-Realization `ProductRef` identity;
- targeted producer builds and transitive dependency closure;
- independent Stage execution through `StageContext`;
- independently named consumer dependency roles;
- multiple consumer roles bound to the same concrete producer Product;
- correct full-depth inlaid Shape dimensionalization;
- Shape Package ownership of physical printer-color resolution;
- independently identifiable colored components in packaged Shape 3MF files; and
- format-level 3MF writing and component recoloring.

Current HEAD does not yet provide all reusable packaged-Shape semantics required by Coin:

1. Shape Package does not persist the Shape-level metadata required to determine whether a packaged Shape is compatible with a Coin Face role; and
2. the generic 3MF format layer can write packaged components but cannot yet read an existing packaged 3MF back into the reusable component representation required for downstream physical composition.

These are independent behavioral seams and should be developed separately.

## 1.1 Independent consumer dependency roles

### Status

Complete in current HEAD.

The generic dependency system permits independently named consumer roles to bind to the same or different concrete producer Products without changing producer `ProductRef` identity.

This behavior supports the future Coin `faceA` and `faceB` dependency roles and requires no Coin-specific engine behavior.

No further implementation work is required in this slice unless later development exposes a genuine defect in the established generic contract.

## 1.2 Correct integrated inlaid Outer Ridge dimensionalization

### Status

Complete in current HEAD.

For `shape_raise_style = "inlaid"`, participating Outer Ridge geometry follows the normative full-depth nonoverlapping partition contract regardless of whether the Outer Ridge structural style is `integrated` or `separate`.

No further implementation work is required in this slice unless later manufacturing acceptance exposes a genuine dimensionalization defect.

## 1.3 Publish reusable packaged Shape metadata

### Behavioral boundary

Shape Package must publish a reusable packaged Shape Product containing the packaged 3MF together with persistent Shape-level metadata required by downstream consumers.

The packaged 3MF remains authoritative for:

- physical component geometry;
- physical component membership;
- semantic component identity; and
- resolved physical component colors.

Compatibility information that cannot safely be recovered from the 3MF must be represented as persistent Shape-level metadata rather than inferred from mesh geometry or recovered by reopening source Shape configuration.

At minimum, the packaged Shape Product must identify the resolved Shape raise style:

```text
raised
inlaid
```

so a downstream consumer can determine whether the packaged Shape satisfies a Face compatibility requirement.

This metadata describes the packaged Shape that was actually produced. It does not authorize downstream consumers to reinterpret or regenerate Shape dimensionalization.

The exact metadata filename and serialization schema are implementation details unless promoted into a permanent Product contract.

### TDD seam

Drive this change from the Shape Package Product boundary.

Begin with one high-value Shape Package test establishing that packaging an inlaid Shape produces both:

- the expected packaged 3MF; and
- persistent packaged-Shape metadata identifying its resolved raise style as `inlaid`.

The test should protect the semantic Product contract rather than incidental JSON formatting or private writer helpers.

Do not add equivalent tests for every possible raise style merely to inventory serialization. The materially different `raised` value should be exercised when Coin compatibility depends upon that distinction.

### Completion criteria

- Shape Package declares and produces persistent Shape-level compatibility metadata.
- The metadata identifies the resolved `shape_raise_style`.
- The packaged 3MF remains authoritative for component geometry, identity, membership, and resolved colors.
- Shape Extrude remains responsible only for physical dimensionalization and does not acquire Package metadata or physical color responsibilities.
- A downstream consumer can determine the packaged Shape's raise style without reopening source Shape configuration.
- Package metadata participates correctly in Product state and dependency behavior.
- Existing standalone Shape packaging behavior remains unchanged.
- Focused Shape Package tests, the broader non-slow suite, pyright, and ruff pass.

## 1.4 Read packaged 3MF components through the format layer

### Behavioral boundary

The generic 3MF format layer must support reading a packaged 3MF into the reusable component representation needed by downstream physical composition.

Reading a 3MF must recover, for each independently packaged component:

- its component identity;
- its mesh geometry; and
- its resolved physical color.

This is format-level behavior. It must not contain Shape, Coin, Artwork, Feature, Face, or other Model-specific semantics.

The read representation should compose naturally with the existing generic `Component` and `Mesh` abstractions so downstream Models can transform and repackage components without reconstructing them from source Model configuration.

Reading must not mutate the source 3MF.

### TDD seam

Protect the format boundary with a compact round-trip test.

Create representative independently identifiable components with distinguishable geometry and resolved colors, write them through the existing 3MF writer, read the resulting 3MF through the new reader, and establish semantic equivalence of:

- component membership;
- component identity;
- mesh geometry; and
- resolved physical color.

Use enough components to prove independent membership and differing colors without inventorying the complete 3MF XML representation.

Do not introduce Coin semantics into this test.

### Completion criteria

- Existing packaged 3MF files can be read through a reusable format-level operation.
- Independent component identity is preserved.
- Mesh geometry is recovered without Model-specific reconstruction.
- Resolved physical color is recovered.
- Multiple components remain independent even when they share physical properties.
- The reader contains no Shape- or Coin-specific policy.
- Existing 3MF writing, recoloring, and naming behavior remains compatible.
- Focused format tests, the broader non-slow suite, pyright, and ruff pass.

## Phase 1 completion

Phase 1 is complete when a downstream Model can independently consume two complete packaged Shape Products, including the same Product twice, and obtain from each:

- its packaged physical components;
- resolved component colors; and
- persistent Shape-level compatibility metadata.

Neither Shape source configuration nor Shape geometry-stage execution should be required to interpret an already-current packaged Shape Product.

Before closing the phase, reevaluate HEAD against `ARCHITECTURE.md`, Shape `DEFINITION.md`, Coin `DEFINITION.md`, and this plan. Run the complete slow suite at the phase boundary when appropriate in addition to the routine non-slow, pyright, and ruff quality gates.

------------------------------------------------------------------------

# Phase 2 --- Introduce the Coin physical composition model

## Purpose

Add the Coin Model and establish its reusable physical composition Product.

Coin consumes exactly two complete packaged Shape Products through independent semantic Face roles:

```text
faceA
faceB
```

This phase owns Coin semantics before final Coin packaging:

- Face dependencies;
- Face compatibility;
- Face orientation;
- rigid physical transformation;
- Face component namespacing;
- preservation of resolved component colors; and
- persistence of the physical Coin component collection.

Coin must not reconstruct Shape geometry, invoke Shape stage implementations, reopen source Shape configuration, or regenerate an incompatible Shape on behalf of a Face.

The exact Coin Stage names, numeric identifiers, physical-component serialization, and private helper organization should follow repository conventions and remain implementation details unless the permanent specifications require otherwise.

## 2.1 Model declaration and packaged Face dependency contract

### Behavioral boundary

Register a conforming `coin` Model with an ordinary `default` Variant and the minimum parameters, Stages, Products, and dependencies required by Coin `DEFINITION.md`.

The Model declares exactly two semantic Face dependency roles:

```text
faceA
faceB
```

Each role consumes a complete packaged Shape Product, including the packaged 3MF and its associated persistent Shape-level metadata.

The roles may independently bind to:

- the same packaged Shape Product;
- different Shape Realizations belonging to one Artifact; or
- packaged Shape Products belonging to different Artifacts.

Coin orientation supports:

```text
aligned
inverted
```

with `aligned` as the default.

The physical Coin component collection is a persistent Product independent of the final packaged Coin 3MF.

### TDD seam

Add only the Coin-specific declarative/configuration coverage not already guaranteed by generic Model and dependency tests.

A small coherent Coin Model test should establish the two packaged-Shape dependency roles, orientation contract, and independently declared physical and packaged Coin Products.

Do not repeat the generic dependency-role tests completed in Phase 1.1 and do not create brittle registry-inventory tests.

### Completion criteria

- `coin` is a registered Model.
- `coin.default` is directly usable.
- Coin declares independent `faceA` and `faceB` packaged Shape dependencies.
- Either role may bind to the same or a different concrete packaged Shape Product.
- Orientation resolves with `aligned` as the default and accepts `inverted`.
- Invalid orientation is rejected at the appropriate Model/configuration boundary.
- A persistent physical Coin component Product is declared independently of the packaged Coin Product.
- Coin registration introduces no Coin-specific behavior into the generic engine.

## 2.2 Face compatibility

### Behavioral boundary

Coin validates whether two already-dimensionalized packaged Shapes can form a valid Coin without repairing, regenerating, or re-dimensionalizing either Face.

Face B must use inlaid Shape dimensionalization.

Coin determines this from the persistent metadata of the packaged Shape Product:

```text
faceB.raise_style == "inlaid"
```

A non-inlaid Face B is incompatible and must fail before a Coin manufacturing Product is published.

Coin does not automatically regenerate Face B as inlaid.

The transformed outer structural boundaries of the Faces must coincide at the mating plane.

Face-local surface geometry may otherwise differ where the difference does not prevent valid mating.

Loop and Hole require bilateral compatible geometry:

- Loop on only one Face is invalid.
- Hole on only one Face is invalid.
- Participating Loops must coincide after Face orientation.
- Participating Holes must align after Face orientation.

Compatibility must use information available from the packaged Shape Products. Coin must not reopen producer configuration, scan producer directories, or reconstruct Shape Feature semantics from upstream registered geometry.

If implementation reveals that another compatibility property cannot be determined safely from the packaged Product, extend the reusable Shape Package Product contract rather than creating a Coin-side dependency on source Shape configuration.

### TDD seam

Begin with the highest-value compatibility distinction introduced by the Coin definition:

```text
test_coin_rejects_non_inlaid_face_b
```

The test should provide an otherwise usable packaged Face pair whose Face B metadata identifies raised dimensionalization and establish a deterministic Coin/domain failure without publication of a Coin manufacturing Product.

Then use a small coherent compatibility set only where materially different behavior needs protection:

- compatible ordinary Faces;
- incompatible structural boundaries; and
- bilateral Loop/Hole mismatch when those Features participate.

Do not exhaustively cross-product Shape Features or configurations.

### Completion criteria

- An inlaid Face B satisfies the raise-style compatibility requirement.
- A non-inlaid Face B is rejected.
- Coin does not regenerate or re-dimensionalize Face B.
- Compatible Faces are accepted regardless of Artifact or Realization identity.
- Face-local surface differences remain valid when the mating contract is satisfied.
- Structural-boundary incompatibility is rejected before Product publication.
- One-sided or misaligned Loop/Hole participation is rejected.
- Compatibility is determined from packaged Product information rather than producer configuration or directory scanning.
- Failures are deterministic domain/model failures rather than partial manufacturing output.

## 2.3 Rigid Face composition and orientation

### Behavioral boundary

Read the complete component collections from the two packaged Shape 3MF files and compose them around their common Shape `Z = 0` mating plane.

The two Faces occupy opposite sides of that plane with their visible Shape surfaces facing outward.

Every component belonging to a Face receives one common rigid Face transformation. Source component dimensions and intra-Face registration are preserved.

Coin supports both normative orientations:

- `aligned`: semantic tops appear at the same physical end when each outward Face is viewed directly;
- `inverted`: Face B semantic top appears at the opposite physical end from Face A.

Coin introduces no independent structural Base and does not regenerate Shape Features.

The source packaged 3MF files remain unchanged.

### TDD seam

Use representative asymmetric physical geometry or semantic markers so orientation is observable without depending upon private transformation helpers.

One high-value composition test should establish:

- the mating-plane relationship;
- opposite outward-facing Face placement;
- preservation of source dimensions;
- preservation of intra-Face registration; and
- one common transformation per Face.

A second case is justified for the materially different `inverted` orientation.

Do not test individual matrix/helper calls unless a specific algorithmic defect later warrants such coverage.

### Completion criteria

- Face A and Face B meet at their Shape underside planes.
- Their physical volumes occupy opposite sides of the mating plane rather than overlapping as duplicate Shapes.
- Every component of a Face receives the same rigid Face transformation.
- Intra-Face component registration is preserved.
- `aligned` orientation satisfies its normative semantic-top relationship.
- `inverted` orientation satisfies its normative semantic-top relationship.
- Source component dimensions are preserved.
- Coin creates no replacement Base, ridge, label, Artwork, fill, Loop, or Hole geometry.
- Source packaged Shape Products are not mutated.

## 2.4 Component identity, color preservation, and persistent physical Coin Product

### Behavioral boundary

Persist the complete transformed component collection as a reusable physical Coin Product.

Every source packaged Shape component remains independently identifiable.

Face A components use:

```text
faceA-<source-semantic-identity>
```

Face B components use:

```text
faceB-<source-semantic-identity>
```

The remainder of each source component's semantic identity is preserved.

Each component also preserves the resolved physical color supplied by its packaged Shape Product.

Face prefixing changes semantic component identity but does not reinterpret or reassign its physical color.

Components must not be merged because they touch, share a physical color, or form two halves of an apparent manufactured feature.

### TDD seam

Test the physical Coin Product boundary using representative components from both Faces, including enough variation to prove:

- Face namespacing;
- independent component membership;
- preservation of source semantic identity;
- preservation of resolved physical color; and
- valid persistent physical component materialization.

Avoid snapshotting incidental manifest formatting, filesystem layout, or private transformation representation.

### Completion criteria

- Every source physical component appears once in the physical Coin Product.
- `faceA-` and `faceB-` namespacing is correct.
- Source semantic identity after the Face prefix is unchanged.
- Every source component's resolved physical color survives composition unchanged.
- Touching and same-color components remain independently represented.
- The physical Coin component collection is persistent and canonically addressable.
- The physical Coin Product can be consumed without producing the packaged Coin 3MF.
- Requesting the physical Coin Product realizes required packaged Shape dependencies but does not execute Coin packaging.

## Phase 2 completion

Phase 2 is complete when Coin can consume two compatible complete packaged Shape Products and persist a correctly oriented, correctly namespaced, color-preserving physical Coin component collection without producing the final Coin 3MF.

Before closing the phase, reevaluate HEAD against all permanent specifications and this plan. Run the complete slow suite at the phase boundary when appropriate in addition to the routine non-slow, pyright, and ruff quality gates.

------------------------------------------------------------------------

# Phase 3 --- Package the complete Coin

## Purpose

Produce a printable multi-component Coin 3MF from the reusable physical Coin Product.

Source physical colors have already been resolved by the packaged Shape Products and preserved through Coin physical composition.

Coin packaging therefore preserves rather than reassigns Face component colors.

Packaging does not alter Face geometry, orientation, compatibility, Feature participation, component membership, or source Shape color policy.

## 3.1 Printable Coin 3MF packaging

### Behavioral boundary

Package the complete physical Coin component collection into a valid multi-component 3MF.

Every physical Coin component remains independently represented.

Packaged component names preserve Face role, source semantic identity, and resolved printing-color presentation according to the repository's established component naming policy.

Conceptually:

```text
base - white
```

from Face A becomes:

```text
faceA-base - white
```

and retains the same resolved physical color.

Likewise, a Face B component preserves its source color while acquiring the `faceB-` semantic prefix.

Coin Package must not perform a new global color assignment, reopen source Shape color configuration, or reinterpret incorporated Artwork color policy.

Packaging must not merge components merely because they share a physical color.

### TDD seam

Add one focused Coin Package test protecting the complete packaging boundary:

- consumption of the persistent physical Coin Product;
- preservation of `faceA-` / `faceB-` component identity;
- preservation of already-resolved physical colors;
- independent representation of same-color components; and
- valid multi-component 3MF output.

Use representative components from both Faces.

Do not retest detailed Face geometry transformations already protected in Phase 2.

### Completion criteria

- Coin produces a valid printable multi-component 3MF.
- Every physical Coin component intended for packaging is represented.
- Face role and source semantic component identity remain observable.
- Each component retains the resolved physical color supplied by its source packaged Shape.
- Same-color components remain independent.
- Coin Package performs no new Shape color assignment.
- Packaging does not mutate or reconstruct physical Coin geometry.
- Packaging does not require access to source Shape configuration.
- Requesting the packaged Coin Product realizes only its required dependency closure.

## 3.2 Format-level recoloring compatibility

### Behavioral boundary

A packaged Coin must participate in the repository's existing format-level recoloring contract in the same manner as other packaged multi-component 3MF Products.

Recoloring addresses stable semantic component identities such as:

```text
faceA-base
faceA-artwork-1
faceB-base
faceB-artwork-1
```

and changes component color presentation without changing:

- mesh geometry;
- Face compatibility;
- component membership;
- object identity; or
- Coin composition.

The format-level recoloring mechanism must remain Model-independent. Do not add Coin-specific recoloring branches merely to recognize Coin Products.

If existing application-level recoloring orchestration prevents otherwise-valid Coin component names from reaching the generic 3MF operation, generalize that orchestration at the reusable packaged-Product boundary rather than adding another Model-specific case.

### TDD seam

Add Coin-specific recoloring coverage only if Coin exposes a genuine limitation in the generic recoloring path.

Prefer a generic packaged-3MF test proving that namespaced semantic component identities can be recolored through the existing format contract while geometry and membership remain unchanged.

Do not duplicate existing recoloring tests when current generic behavior already satisfies this requirement.

### Completion criteria

- Packaged Coin components can be recolored by stable semantic identity.
- `faceA-` and `faceB-` namespaced components are addressable without Coin-specific format logic.
- Recoloring changes color presentation without changing geometry or component membership.
- Existing Artwork and Shape recoloring remains compatible.
- The generic 3MF format layer remains Model-independent.
- Coin does not introduce a new color-assignment mechanism.

## Phase 3 completion

Phase 3 is complete when a valid physical Coin Product can be packaged into a printable 3MF with preserved Face/component identity and preserved source physical colors, and that packaged Product remains compatible with the repository's model-independent recoloring contract.

Run the complete slow suite at the phase boundary when appropriate in addition to the routine non-slow, pyright, and ruff quality gates.

------------------------------------------------------------------------

# Phase 4 --- End-to-end Coin manufacturing acceptance

## Purpose

Establish the complete Coin capability across the real dependency graph without duplicating focused semantics already protected by earlier phases.

The acceptance boundary demonstrates that Coin is a first-class Model in the ordinary Artifact/Variant/Realization build workflow rather than a special-purpose script or alternate pipeline.

## Acceptance seam

Add a small number of broad acceptance cases sufficient to demonstrate the architecturally distinct source relationships required by Coin.

At minimum, establish that an Artifact can build a Coin 3MF from two configured packaged Shape Face dependencies and that dependency-driven execution realizes the required Shape Package Products.

The acceptance coverage must collectively prove that Coin permits:

- the same packaged Shape Product to serve both Faces;
- distinct Shape Realizations of one Artifact to serve the Faces; and
- packaged Shape Products from different Artifacts to serve the Faces.

Face B must satisfy the normative inlaid requirement in successful manufacturing cases.

These relationships need not each execute the complete expensive external-tool manufacturing path if lower-level integration coverage can establish them more precisely.

Use slow integration coverage only where actual modeling-tool output is necessary to prove the manufacturing boundary.

At least one real manufacturing acceptance path should validate the resulting Coin as a printable two-sided physical object containing representative Face components.

Do not reproduce every Feature, orientation, compatibility, color, or format assertion already protected by focused tests.

## Dependency and incremental behavior

Acceptance should demonstrate that Coin participates normally in the Product graph.

Requesting a packaged Coin must realize the transitive closure required to produce its packaged Shape dependencies and Coin Products.

Already-current packaged Shape Products should be reused rather than regenerated.

A Coin build must not invoke Shape stage implementations directly or bypass the dependency system.

Changing one Face dependency should invalidate only Products whose dependency state requires rebuilding.

Do not introduce Coin-specific dependency orchestration.

## Operator workflow

Coin participates through the existing Artifact/Variant/Realization build workflow.

Do not add a Coin-specific CLI command merely to expose the Model.

`artifact build` remains the ordinary manufacturing action.

Update CLI or user documentation only where:

- Coin requires examples for configuring its two Face dependencies;
- Coin orientation needs operator-facing explanation;
- the Face B inlaid requirement needs operator-facing explanation; or
- HEAD exposes a genuine generic-model limitation in the existing workflow.

Operator-facing failures for incompatible Faces should be concise consequences of reusable Coin/domain failures rather than special CLI manufacturing logic.

## Completion criteria

- A configured Coin Realization builds through the ordinary dependency-driven workflow.
- The same packaged Shape Product can supply both Faces.
- Different Shape Realizations of one Artifact can supply the Faces.
- Packaged Shape Products from different Artifacts can supply the Faces.
- Face B compatibility is enforced from persistent packaged Shape metadata.
- Coin consumes packaged Shape Products without reopening Shape configuration or regenerating incompatible Faces.
- At least one representative real Coin build produces the intended two-sided physical geometry and printable multi-component 3MF.
- Packaged source component identity and resolved physical colors survive into the Coin with the required Face prefixes.
- Incremental rebuild behavior remains dependency-driven and current packaged Shape Products are reused.
- Existing Artwork and Shape workflows remain production-capable.
- Existing generic recoloring behavior remains production-capable.
- No Coin-specific orchestration leaks into the generic engine, generic 3MF format layer, or CLI.
- Applicable permanent and operator documentation reflects the completed public behavior.
- The complete slow and non-slow test suite, pyright, and ruff pass.

## Project completion

Coin implementation is complete when repository HEAD conforms to `ARCHITECTURE.md`, Artwork `DEFINITION.md`, Shape `DEFINITION.md`, and Coin `DEFINITION.md`; all requirements above are either satisfied by HEAD or removed from this plan as obsolete; and the complete quality suite is green.

At that point, reevaluate `CHANGEPLAN.md` against HEAD rather than preserving it as implementation history. Once no remaining implementation work is described, the temporary plan may be removed or replaced for the next body of work.
