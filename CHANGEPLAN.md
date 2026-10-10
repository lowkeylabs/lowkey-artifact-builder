# CHANGEPLAN

## Purpose

Continue refining `lowkey-artifact-builder` around the manufacturing value
chain established by the current repository HEAD.
The operator's ordinary goal is:

> Move customer artwork to a *correct, printable 3MF* with the fewest
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


-------------------------------------

## Phase 1 — QR Code Registered Geometry

### Purpose

Establish QR Code as a participating Shape Feature and produce its complete
registered geometry during Shape Compose.

This phase establishes the boundary from configured QR payload to registered
Shape geometry. It does not yet require interaction with incorporated Artwork
or physical extrusion and packaging.

QR Code is Shape-owned source geometry generation. It does not introduce a new
Model, standalone QR Product, raster source, or Artwork dependency.

The implementation must preserve the existing Shape stage boundary:

```text
configured QR payload
        ↓
QR encoding
        ↓
registered dark/light geometry
        ↓
Shape Compose
```

QR encoding and placement occur in registered Shape space. Physical Z
dimensionalization remains downstream.

### Acceptance criteria

Phase 1 is complete when:

1. the Shape model defines the QR Feature parameters required by
   `shape/DEFINITION.md`;
2. an empty QR payload leaves the Feature nonparticipating;
3. a nonempty QR payload causes the QR Feature to participate without requiring
   Artwork or a source PNG;
4. the payload is encoded into a deterministic QR module matrix with its
   required quiet zone;
5. the complete QR footprint consists of complementary registered `qr-dark`
   and `qr-light` geometry;
6. `qr-light` includes the required quiet zone;
7. the dark and light regions together cover the complete QR footprint without
   overlap or gaps;
8. `shape_qr_size` determines the physical size represented by the registered
   QR footprint without introducing physical dimensionalization into Compose;
9. QR scaling preserves uniform square modules;
10. `centered`, `inner-aligned`, and `outer-aligned` placement conform to the
    Shape definition;
11. `shape_qr_position` uses the defined Shape clock-angle convention for
    non-centered placement, including intermediate angles;
12. changing QR position translates the QR footprint without rotating the QR
    module grid;
13. the complete footprint, including the quiet zone, remains contained within
    the available registered Shape interior region;
14. QR-specific validation rejects invalid participating configurations at the
    Shape validation boundary;
15. QR color parameters remain packaging policy and do not alter registered QR
    geometry; and
16. existing Shape behavior remains unchanged when QR does not participate.

### TDD slices

#### Slice 1.1 — Feature configuration and encoding

Establish the Shape-owned QR configuration and encoding seam.

Use focused tests to prove:

- participation from nonempty `shape_qr_payload`;
- nonparticipation from an empty payload;
- QR-only Shape operation without Artwork;
- deterministic dark/light module geometry for a representative known payload;
- inclusion of the quiet zone in the complete footprint; and
- complementary dark/light registered geometry.

The test should protect QR semantics rather than the internal API of the chosen
QR encoding library.

Add only the validation tests needed to protect QR-specific configuration
requirements discovered or specified at this seam.

#### Slice 1.2 — Registered sizing and placement

Establish QR placement within the available registered Shape interior.

Use a coherent placement test set covering representative cases for:

- centered;
- inner-aligned; and
- outer-aligned.

Include enough clock positions to establish the angular convention and at least
one non-cardinal position to protect arbitrary-angle placement.

Protect the relationships defined by the QR Feature rather than enumerating
every angle or Shape geometry.

Verify that placement translates the QR footprint without rotating its module
grid and that containment is determined from the complete footprint including
the quiet zone.

### Completion

Before closing Phase 1:

1. compare the implementation against the QR Feature contract in
   `shape/DEFINITION.md`;
2. confirm that QR generation remains Shape-owned and does not introduce an
   unnecessary Model or Product;
3. confirm that Compose produces registered rather than physical QR geometry;
4. run the focused QR configuration, validation, encoding, and Compose tests;
5. run the appropriate complete quality suite; and
6. reevaluate HEAD before beginning Phase 2.

---

## Phase 2 — QR Code and Artwork Composition

### Purpose

Establish the registered-composition precedence between QR Code and incorporated
Artwork.

QR Code owns its complete footprint, including its quiet zone. When QR and
Artwork overlap, QR replaces only the Artwork geometry geometrically covered
by that footprint. Artwork outside the footprint must remain intact.

The intended registered composition is:

```text
transformed Artwork
        │
        ├── subtract complete QR footprint
        │
        ▼
remaining Artwork
        │
        ├──────────────┐
        │              │
        ▼              ▼
     qr-dark        qr-light
        │              │
        └──────┬───────┘
               ▼
      registered composition
```

This phase owns two-dimensional registered geometry only. It must not move QR
precedence into Extrude or rely on overlapping physical solids to produce the
intended result.

### Acceptance criteria

Phase 2 is complete when:

1. QR Code may participate with or without incorporated Artwork;
2. existing Artwork fitting and transformation occur according to the existing
   Shape Artwork-placement contract;
3. QR precedence is resolved after Artwork has been transformed into common
   registered Shape space;
4. the complete QR footprint, including the quiet zone, removes intersecting
   Artwork geometry;
5. only Artwork inside the QR footprint is removed;
6. uncovered portions of partially intersected Artwork components survive;
7. remaining Artwork preserves its registration and logical Artifact-color
   identity;
8. `qr-dark` and `qr-light` occupy the reserved QR footprint;
9. no incorporated Artwork remains beneath the QR quiet zone;
10. QR participation does not change the registered Shape interior region or
    the Artwork fitting transformation;
11. QR composition works when the footprint overlaps multiple Artwork color
    components; and
12. QR composition does not alter unrelated Shape Feature participation.

### TDD slices

#### Slice 2.1 — QR footprint precedence over Artwork

Establish one major registered-composition seam using representative Artwork
that crosses the QR footprint.

The focused tests should demonstrate that:

- intersecting Artwork is clipped at the QR footprint;
- uncovered portions of the same Artwork component remain;
- the quiet zone clears underlying Artwork;
- multiple affected Artwork color components retain their individual logical
  identities outside the footprint; and
- Artwork wholly outside the footprint is unchanged.

Do not test this as deletion of whole Artwork components. The protected
behavior is geometric clipping.

If HEAD already contains a reusable registered-geometry subtraction operation
that cleanly expresses this behavior, reuse it. Otherwise implement the
behavior at the Shape-owned composition boundary. Do not create a generalized
abstraction solely because Hole also performs subtraction: Hole currently owns
physical subtraction during dimensionalization, while QR owns registered
composition precedence.

### Completion

Before closing Phase 2:

1. compare the resulting behavior against both the QR Feature and existing
   Artwork contracts;
2. confirm that QR clipping occurs before extrusion;
3. confirm that Artwork outside the QR footprint is preserved rather than
   discarded by component;
4. confirm that quiet-zone geometry prevents underlying Artwork from remaining
   in the footprint;
5. run the focused QR/Artwork composition tests;
6. run the appropriate complete quality suite; and
7. reevaluate HEAD before beginning Phase 3.

---

## Phase 3 — QR Code Physical Dimensionalization and Packaging

### Purpose

Carry the registered QR composition through Shape Extrude and Package so that
QR Code becomes a complete printable Shape Feature.

Extrude owns physical QR Z geometry. Package owns physical dark/light color
assignment.

The stage responsibilities remain:

```text
Shape Compose
    │
    │ registered qr-dark / qr-light
    ▼
Shape Extrude
    │
    │ physical QR components
    ▼
Shape Package
    │
    │ physical dark/light colors
    ▼
printable Shape 3MF
```

The two QR color regions are partitions of one QR Feature. They share one
physical raise and must form one level QR surface.

### Acceptance criteria

Phase 3 is complete when:

1. Shape Extrude consumes the registered `qr-dark` and `qr-light` geometry
   produced by Compose;
2. both QR components use the same resolved `shape_qr_raise`;
3. with `shape_raise_style = "raised"`, both components extend from
   `Z = shape_base_raise` through
   `Z = shape_base_raise + shape_qr_raise`;
4. the complete raised QR surface is level across dark and light regions;
5. with `shape_raise_style = "inlaid"`, both QR components span
   `Z = 0` through `Z = shape_base_raise`;
6. inlaid QR regions are removed from Base so QR and Base material do not
   overlap;
7. the inlaid Base and QR partitions preserve the existing complete-volume
   Shape invariant;
8. Extrude preserves distinct `qr-dark` and `qr-light` semantic component
   identities without assigning physical colors;
9. Shape Package applies `shape_qr_dark_color` and `shape_qr_light_color` to
   the corresponding components;
10. changing only either QR color does not require recomputing Compose or
    Extrude geometry;
11. a participating Hole removes intersecting QR material according to the
    existing Hole contract;
12. the packaged 3MF preserves independently printable dark and light QR
    components;
13. a QR-only Shape with no Artwork can be built through Package into a valid
    printable 3MF;
14. a Shape containing both Artwork and QR can be built through Package while
    preserving the registered clipping established in Phase 2; and
15. packaged Shape Products containing QR remain ordinary Shape Products and
    require no QR-specific behavior from downstream consumers such as Coin.

### TDD slices

#### Slice 3.1 — Raised and inlaid QR dimensionalization

Establish the Extrude boundary with a small coherent test set covering both
Shape raise styles.

Protect:

- common dark/light raise;
- level raised QR surface;
- full-depth inlaid dark/light partitions;
- nonoverlap with inlaid Base; and
- preservation of `qr-dark` and `qr-light` component identity.

Reuse the existing Shape raised/inlaid dimensionalization machinery where its
semantics already match the QR contract rather than introducing a parallel QR
extrusion pipeline.

#### Slice 3.2 — Packaging and color

Establish Package as the QR physical-color boundary.

Protect:

- independent dark and light packaged colors;
- preservation of QR semantic component identity;
- absence of physical color assignment in Compose and Extrude; and
- color-only changes invalidating Package rather than upstream QR geometry
  Products.

Do not add QR-specific color assignment to Coin or the generic engine.

#### Slice 3.3 — Complete QR Shape capability

Add a small acceptance boundary proving the useful manufactured result.

At minimum establish that:

- an Artifact with QR configuration and no Artwork can build a packaged Shape
  3MF; and
- an Artifact with both incorporated Artwork and QR can build a packaged Shape
  3MF in which QR and preserved Artwork components coexist.

The acceptance test should establish the end-to-end capability without
duplicating the detailed geometry assertions already protected by focused
Model tests.

If practical at this boundary, inspect the packaged component identities and
physical metadata rather than depending on slicer-specific behavior.

### Completion

Phase 3 and the QR Code implementation are complete when:

1. all QR Feature requirements in `shape/DEFINITION.md` are represented by
   implementation or deliberately justified existing behavior;
2. QR remains an optional Shape Feature rather than a standalone Model;
3. QR-only Shapes do not require Artwork source material or an Artwork
   dependency;
4. QR generation and Artwork precedence remain in registered Compose;
5. physical QR Z construction remains in Extrude;
6. physical QR color assignment remains in Package;
7. raised and inlaid Shapes both satisfy the QR dimensionalization contract;
8. the complete QR footprint, including quiet zone, remains protected from
   underlying Artwork;
9. dark and light QR components share one raise while retaining independent
   packaged colors;
10. Hole subtraction continues to apply uniformly to QR and other physical
    Shape material;
11. downstream consumers can consume the resulting packaged Shape without
    QR-specific knowledge;
12. focused QR tests pass;
13. the complete slow and non-slow test suite passes;
14. pyright passes;
15. ruff passes; and
16. CHANGEPLAN is reevaluated against the resulting HEAD and the permanent
    specifications.
