# CHANGEPLAN

## Purpose

Continue refining `lowkey-artifact-builder` around the manufacturing value chain established by the current repository HEAD.

The operator's ordinary goal is:

> Move customer artwork to a **correct, manufacturing-ready Product** with the fewest necessary decisions, actions, and computations.

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
slicer / laser software / share / manufacture
```

A manufacturing Product may be a printable 3MF, a laser-ready SVG or PNG, or another format defined by a Model. The selected Realization determines the manufacturing output.

`create` and `build` define the ordinary value chain. `show`, `config`, `colors`, and `clean` support that path when the operator needs discovery, inspection, customization, correction, color selection, or maintenance. These support commands must not become mandatory ceremony before routine manufacturing.

This CHANGEPLAN contains remaining work rather than a history of completed implementation. Completed behavior should normally be credited from HEAD and removed from the plan rather than retained as historical checklists.

## Planning and development rules

`ARCHITECTURE.md` and the applicable Model `DEFINITION.md` files are normative. Repository HEAD defines the current implementation. The CLI README defines the intended operator-facing command model. This CHANGEPLAN describes temporary remaining work and must not redefine permanent architecture.

At the beginning of a thread and before each meaningful implementation slice:

1. Reload and follow `prompts/NEW_THREAD.md`.
2. Compare CHANGEPLAN with current HEAD, `ARCHITECTURE.md`, applicable Model definitions, and relevant CLI documentation.
3. Credit behavior HEAD already satisfies.
4. Identify the next unmet behavioral boundary rather than assuming the plan is still current.
5. Resolve known semantic or architectural questions before encoding behavior in tests, while allowing test-first exploration to discover or clarify uncertain seams and ownership boundaries.
6. Organize TDD around major behavioral seams or boundaries, using one test or a small coherent test set to drive a substantial implementation slice rather than creating single-test/single-change cycles.
7. Implement the smallest correct change at the layer that owns the behavior.
8. Run focused tests and then the appropriate complete quality suite.
9. Reevaluate the plan against the resulting HEAD.

Tests should protect useful behavioral boundaries rather than inventory implementation details. High-level CLI/application seams should be protected as they are introduced, while lower-level tests should be added only where they protect behavior actually owned by that layer.

A newly discovered defect that can produce an incorrect manufacturing Product, corrupt persistent manufacturing state, or cause material value-chain inefficiency takes priority over CLI presentation work.

Every phase must leave the application production-capable.

## Common constraints

Preserve the separation between operator presentation and reusable application behavior:

```text
CLI / TUI / GUI / API
          │
          ▼
reusable application operations
          │
          ▼
configuration / planning / engine / Products
```

Click owns parsing, terminal presentation, prompts, and translation of structured application errors into operator-facing prose. Reusable workflow behavior belongs below Click and should return structured domain/application information rather than Rich objects or presentation-specific strings.

The CLI operates on the current working directory as project root. A registered Artifact may legitimately exist under `originals/` before `artifacts/<artifact_id>/` exists. Commands must preserve the distinction between registered Artifact identity, materialized Artifact workspace, and manufacturing Product state.

Missing collection directories normally represent empty collections. An explicitly requested missing object is an operator error. Expected domain errors should be concise and traceback-free; unexpected invariant or programming failures must not be indiscriminately converted into ordinary operator failures.

Routine output should be lean and oriented toward the operator's next useful decision. Operator-facing Product paths should be concise and useful from the project root. Do not expose Stage, resolver, dependency, or filesystem mechanics unless they answer an operator question.

Do not change Product identity, dependency semantics, configuration precedence, Model semantics, manufacturing ownership, persistence semantics, or color semantics merely to simplify CLI presentation. If work exposes a genuine architectural mismatch, resolve that mismatch explicitly against the permanent specifications before proceeding.

Manufacturing formats are Model-owned outputs, not special cases in the generic build engine. Models may produce different representations of shared geometry while preserving the established dependency, Product identity, and manufacturing-state contracts.

## TDD cycles

TDD remains test-first. Before implementing a meaningful new behavior, write a test that exercises the behavioral seam or boundary being established.

The purpose of the initial failing test is not only verification. A test may also be used to discover or clarify the appropriate seam, ownership boundary, or contract before implementation. If the test exposes a better boundary than the one initially assumed, refine the design and test before committing to the implementation.

TDD cycles should normally correspond to substantial behavioral seams or boundaries rather than individual implementation changes. Once a failing test establishes the intended seam, implement the coherent behavior necessary to make that seam work. Do not begin a new RED/GREEN cycle merely because that implementation requires another helper, parameter, branch, component, or internal refactoring.

One test may be sufficient to establish a seam. A small coherent group of tests is appropriate when materially different cases are necessary to define the same boundary. Prefer these high-value behavioral tests over many narrow tests that separately inventory implementation details.

Add narrower tests when they help discover an uncertain boundary, protect an independently meaningful contract, reproduce a defect, or address a specific algorithmic or regression risk.

---

## Phase 1 — LASER Model and 2D Manufacturing Products

### Purpose

Introduce a `laser` Model that produces manufacturing-ready SVG or PNG files for import into xTool Studio.

LASER is the two-dimensional manufacturing counterpart to SHAPE. It reuses SHAPE's registered planar composition, including structural geometry, Artwork placement, ridges, labels, loops, holes, and other applicable Features, without physical Z extrusion.

LASER supports incorporated Artwork as either registered vector geometry or a raster image. SVG output may combine independently identifiable vector objects and embedded raster Artwork in one self-contained document.

LASER defines the manufactured 2D design, not the laser-processing job. xTool Studio remains responsible for assigning engraving operations and machine settings.

### Architectural boundaries

- LASER is a distinct Model with its own Variants, Realizations, Stages, parameters, and Products.
- LASER consumes registered SHAPE Compose geometry through the existing Product-dependency mechanism. It may additionally consume ARTWORK vector or raster Products when required by the selected representation.
- SHAPE owns structural geometry, Feature composition, Artwork placement, and clipping. LASER must not duplicate these implementations.
- SHAPE Compose must expose persistent planar geometry, semantic component identities, and authoritative Artwork placement and clipping independently of Artwork's vector representation.
- LASER may substitute registered raster Artwork for composed vector Artwork without retaining or duplicating the corresponding vector objects. This substitution must preserve SHAPE's authoritative placement, scale, orientation, and clipping.
- If existing Products are insufficient, strengthen their contracts at the owning boundaries rather than reconstructing geometry from a 3MF or copying SHAPE logic.
- LASER owns physical 2D output dimensions, Artwork representation selection, object participation, SVG/PNG serialization, and manufacturing-oriented representation policy.
- LASER distinguishes semantic components, exported objects, visible composition, and downstream laser-processing operations. These are separate concepts.
- Semantic component identity is independent of SVG grouping, document order, display color, and xTool Studio processing layers.
- Vector Artwork preserves logical Artwork-color identity. Raster Artwork is represented as one image object rather than artificial color-separated layers.
- SVG output preserves independently identifiable objects where supported. PNG output flattens the selected visible composition and does not preserve independent object identities.
- Object participation is explicit. Structural geometry does not automatically become a filled engraving region. The default base representation is an outline rather than a filled surface.
- Overlap, masking, clipping, transparency, and visibility are deterministic. Intentional independent operations may overlap, but unintended duplicate engraving coverage must not arise from implicit structural fills.
- Registered composition remains independent of output resolution, serialization, rasterization, and laser-machine settings.
- LASER does not assign physical printer colors, laser power, speed, line density, engraving mode, or execution order.
- Existing ARTWORK, SHAPE, and COIN semantics, Product identities, dependency behavior, and manufacturing state remain intact.

### Work

1. **Establish xTool Studio compatibility before finalizing the Model definition.** Create a self-contained test SVG containing distinct vector paths, multiple fills, converted text, and an embedded transparent PNG. Import it into xTool Studio 1.9.11 and determine:
   - Whether embedded raster Artwork remains an independently configurable bitmap object.
   - Whether vector objects and groups retain useful independent selection and processing behavior.
   - Whether same-style object merging affects intended object separation.
   - Whether physical dimensions, orientation, transparency, and registration are preserved.
   - Whether mixed-content SVG is practical or separately registered SVG/PNG Products are necessary.

2. Audit SHAPE Structure and Compose Products, manifests, component identities, geometry representations, and dependencies. Inspect ARTWORK vector and raster Products to identify the authoritative reusable pre-extrusion composition boundary and suitable Artwork representations.

3. Resolve the LASER representation contract using the audit and import-test findings. Define vector/raster Artwork selection, authoritative placement and clipping, object participation, overlap behavior, physical sizing, and any required compatibility fallback.

4. Define `laser/DEFINITION.md`, including Model semantics, dependencies, supported Features, Variants, parameters, Stages, Products, component identities, object participation, output formats, and xTool Studio compatibility expectations. Update `ARCHITECTURE.md` where necessary.

5. Expose or extend registered SHAPE Compose Products to provide reusable planar geometry, semantic component identities, and Artwork placement and clipping independently of the incorporated Artwork representation. LASER must be able to substitute registered raster Artwork for vector Artwork without duplicating either Artwork placement logic or exported geometry.

6. Register LASER using the existing Model, Variant, Realization, configuration, dependency, and manufacturing-state machinery.

7. Implement SVG packaging as one self-contained, physically dimensioned document using a common coordinate system. Preserve stable semantic identifiers for exported objects, including base outline, ridges, labels, and Artwork components.

8. Support vector Artwork as registered color-separated objects and raster Artwork as one registered image object. Embed raster Artwork within SVG where verified compatible with xTool Studio, preserving its authoritative placement, clipping, transparency, and physical dimensions.

9. Convert text and applicable geometry into portable vector paths. Avoid external resources, unresolved fonts, and editor-specific SVG dependencies.

10. Implement explicit object-participation and 2D composition rules:
    - Export the base outline by default without filling the entire base.
    - Preserve enabled ridges, labels, Artwork, and applicable structural Features as independently identifiable objects.
    - Apply authoritative placement and clipping consistently to vector and raster Artwork.
    - Export only the selected Artwork representation, without retaining duplicate vector or raster coverage.
    - Preserve intentional independent overlaps while preventing unintended duplicate filled regions.
    - Keep semantic object identity independent of display color and downstream engraving settings.

11. Implement PNG packaging as a flattened rasterization of the selected visible composition, with explicit physical dimensions, resolution, background/transparency, and color policy.

12. Ensure SVG and PNG represent the same selected design, subject to documented differences between independent SVG objects and flattened PNG output.

13. If mixed-content SVG cannot preserve required raster/vector behavior in xTool Studio, provide a documented fallback using separately registered SVG and PNG Products without duplicating composition or placement logic.

14. Integrate LASER into ordinary `artifact build`, `show`, `config`, and manufacturing-status workflows without introducing mandatory operator steps.

15. Document xTool Studio import behavior and limitations. Defer grayscale optimization, histogram adjustment, dithering, material profiles, and machine-specific engraving settings to subsequent work.

### Acceptance criteria

- The mixed-content SVG import experiment has been performed against xTool Studio 1.9.11, and its findings are reflected in `laser/DEFINITION.md`.
- A LASER Realization builds through the existing CLI and dependency machinery.
- LASER consumes only the required SHAPE Compose and ARTWORK Products; SHAPE extrusion and 3MF packaging are not prerequisites.
- LASER supports applicable SHAPE planar Features without duplicating geometry-generation or Artwork-placement implementations.
- LASER supports vector and raster Artwork with consistent physical size, registration, orientation, placement, and clipping.
- Raster Artwork substitution does not retain or duplicate corresponding vector Artwork geometry.
- SVG output is self-contained, physically dimensioned, and preserves independently identifiable semantic objects.
- The default base representation is an outline, not an implicitly filled engraving region.
- Vector Artwork retains logical color-region identities; raster Artwork remains a single image object.
- PNG output preserves the complete selected visible composition at the configured dimensions and resolution.
- Object participation, overlap, clipping, transparency, and visibility have deterministic, documented behavior.
- Representative xTool Studio imports verify dimensions, appearance, registration, and useful object separation. Any importer limitations are documented and addressed by the defined fallback.
- Changes to shared composed geometry or selected ARTWORK Products correctly invalidate dependent LASER Products. Changes confined to SHAPE extrusion or printer packaging do not unnecessarily rebuild LASER Products.
- Existing ARTWORK, SHAPE, and COIN 3MF manufacturing remains functional.
- Major composition-consumption, Artwork representation, SVG/PNG packaging, and CLI/application boundaries are protected by a small coherent set of behavioral tests.
- The appropriate complete test suite, pyright, and ruff pass.

### Completion

Phase 1 is complete when LASER is a first-class manufacturing Model that reuses SHAPE's registered pre-extrusion composition, supports vector and raster Artwork, and produces independently buildable SVG and PNG manufacturing Products verified for practical import into xTool Studio.

LASER must not require SHAPE extrusion, 3MF packaging, duplicated composition logic, duplicated Artwork coverage, or manual reconstruction of Artwork placement. Advanced image optimization and machine-specific engraving settings remain outside this phase.


---------------------------

## Phase 2 — SHAPE Artwork Placement Controls

### Purpose

Allow an operator to adjust the position and size of incorporated Artwork within a SHAPE Realization without editing source Artwork or changing structural Shape geometry.

Introduce three optional SHAPE parameters:

- `shape_artwork_offset_x = 0.0` — horizontal translation in physical millimeters; positive moves right.
- `shape_artwork_offset_y = 0.0` — vertical translation in physical millimeters; positive moves toward the top of the finished Shape.
- `shape_artwork_scale = 1.0` — positive, dimensionless multiplier applied to the existing automatically fitted Artwork size.

Neutral defaults preserve existing manufacturing behavior. These are SHAPE composition controls, not standalone ARTWORK parameters or changes to Model/Variant/Realization inheritance.

### Architectural boundaries

- SHAPE Compose owns the common registered Artwork placement transform. Extend that existing mechanism rather than introducing separate component transforms or downstream mesh adjustments.
- Preserve the existing automatic-fit placement as the baseline. Apply the additional uniform scale about the fitted Artwork center, then apply physical X/Y offsets in the finished Shape coordinate convention.
- Transform the authoritative Artwork envelope and every incorporated Artwork component identically. Preserve relative geometry, registration, logical color identities, and component topology.
- Convert millimeter offsets at the owning composition boundary using the effective Shape size and registered coordinate system; do not interpret them as source SVG pixels or unscaled registered units.
- Preserve structural Shape geometry, ridges, border labels, loops, holes, and other Features. Artwork placement must not translate these components.
- Maintain the existing interior placement and clipping contracts. A requested placement that violates required clearances or permitted containment must produce a clear configuration/manufacturing error rather than silently crop, deform, or auto-reduce the requested transform.
- Persist the resolved placement transform in the existing SHAPE Compose Product/manifest contract so dependent consumers, including LASER, reuse authoritative placement without recomputation.
- Parameter changes invalidate SHAPE Compose and its dependent Products through normal stage fingerprinting; they must not invalidate upstream ARTWORK Products or SHAPE Structure when those inputs are unchanged.

### Work

1. Audit the current SHAPE Compose Artwork fitting, registered transforms, containment/clipping rules, manifest, and dependent consumers. Confirm the physical-to-registered coordinate convention and existing placement constraints before implementation.
2. Add the three parameters to SHAPE's declared configuration vocabulary and Compose Stage parameter dependencies, with defaults, units, sign conventions, and validation documented in `shape/DEFINITION.md` and `parameters.toml`.
3. Extend the existing common Artwork placement calculation to apply uniform scale and offsets after automatic fitting. Keep all Artwork components and their envelope on one authoritative transform.
4. Validate finite offsets, finite positive scale, and transformed Artwork placement against the permitted interior and any applicable Feature clearances. Reject invalid requests with actionable errors; preserve existing neutral-default behavior.
5. Ensure composed geometry, fill/envelope behavior, manifest placement metadata, and downstream extrusion/packaging consistently consume the adjusted transform. Keep the placement contract suitable for LASER's vector/raster Artwork substitution.
6. Add focused test-first coverage at the SHAPE Compose boundary for neutral defaults, nonzero X/Y translation, relative scaling, shared component/envelope registration, and invalid placement. Add a representative end-to-end manufacturing and freshness test only where needed to protect the cross-stage contract.
7. Verify configuration inspection and ordinary build behavior for an Artifact-specific Realization using these overrides. Run the appropriate complete tests, pyright, and ruff.

### Acceptance criteria

- All three parameters are accepted in SHAPE Realization configuration and appear with correct effective values and provenance in configuration inspection.
- Zero offsets and unit scale preserve existing SHAPE output and manufacturing behavior.
- Positive X moves incorporated Artwork right; positive Y moves it toward the top of the finished Shape. Both are expressed in physical millimeters.
- Scale multiplies the existing fitted Artwork size uniformly about its center; Artwork proportions are preserved.
- Every Artwork component, the authoritative envelope, and dependent fill geometry remain aligned after translation and scaling.
- Ridges, labels, base, loops, holes, and other structural Features remain fixed.
- Invalid parameter values or placements fail clearly rather than generating clipped or geometrically inconsistent Products.
- The composed Product publishes authoritative placement sufficient for downstream consumers, including LASER, without duplicating placement calculations.
- Changing placement parameters rebuilds the affected SHAPE Compose and downstream Products but does not unnecessarily rebuild upstream ARTWORK or SHAPE Structure Products.
- Existing SHAPE and other Model manufacturing remains functional; focused behavioral tests, the appropriate complete suite, pyright, and ruff pass.

### Completion

Phase 2 is complete when SHAPE Realizations can independently translate and uniformly scale incorporated Artwork within the permitted interior, using stable physical units and one authoritative Compose transform, without altering source Artwork or unrelated Shape Features.

