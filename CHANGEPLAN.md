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
Product boundary consumed by Coin. Each Face is one complete packaged Shape
Product whose 3MF is authoritative for component geometry, component identity,
resolved physical colors, and embedded persistent Shape-level compatibility
metadata. Coin does not reconstruct registered Shape geometry, invoke Shape
stage implementations, reopen source Shape configuration, or regenerate an
incompatible Shape on behalf of a Face.

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
    component identity, resolved physical colors, and embedded persistent
    Shape-level compatibility metadata.
-   Shape-level compatibility metadata must not be inferred from component
    geometry, identity, or resolved colors.
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
