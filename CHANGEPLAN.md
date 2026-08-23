# Change Plan

This document tracks the incremental migration of
`lowkey-artifact-builder` toward the architecture defined in
`ARCHITECTURE.md`.

It is intentionally brief and operational.

`ARCHITECTURE.md` defines the target design and invariants.
`CHANGEPLAN.md` records the planned path from the current implementation
to that architecture.

As work progresses, compare both documents against the current repository
before selecting the next change.

---

# Approach

The existing artwork model is working and serves as the primary regression
baseline.

Changes should therefore be incremental rather than a rewrite.

Prefer a test-driven workflow:

1. identify the architectural invariant being implemented;
2. write or revise tests that express that invariant;
3. make the smallest implementation change necessary;
4. update affected existing tests;
5. run the complete test, lint, formatting, and type-check suite;
6. keep each completed step independently working.

Avoid implementing several architectural concepts simultaneously when they
can be introduced separately.

The existing artwork pipeline should remain functionally correct throughout
the migration unless a change intentionally modifies its documented behavior.

---

# Planned Work

## Phase 1 — Stage and Product Identity

Establish the lowest-level specification invariants.

- Add stable numeric IDs to `StageSpec`.
- Assign artwork stages IDs such as:
  - `10 prepare`
  - `20 raster`
  - `30 vector`
  - `40 extrude`
  - `50 package`
- Make `ProductSpec.path` relative to its producing stage.
- Remove stage directory names from product paths.
- Preserve semantic stage dependencies by stage name.
- Add tests for stage IDs and stage-local product paths.
- Add validation/tests for duplicate stage IDs and names where appropriate.

Do not introduce the new filesystem hierarchy or resolver in this phase.

---

## Phase 2 — Logical Product References

Introduce a structured logical product identity.

- Add a `ProductRef` value object.
- Centralize parsing and formatting.
- Define equality and identity semantics.
- Reject malformed or ambiguous references.
- Keep logical references independent of filesystem paths.
- Add comprehensive unit tests before integrating references into builds.

Do not prematurely freeze serialized syntax beyond what the architecture
requires.

---

## Phase 3 — Product Resolver and Filesystem Policy

Introduce centralized mapping from logical products to physical locations.

- Add the product resolver.
- Centralize artifact/model/realization/stage/product path construction.
- Implement the model and stage directory hierarchy.
- Format stage directories using stable IDs and semantic names.
- Ensure every generated product has one canonical location.
- Remove model-specific global path construction.
- Test resolver behavior using temporary workspaces.

---

## Phase 4 — Migrate the Artwork Model

Route the existing artwork pipeline through the new resolver and filesystem
layout.

- Preserve existing artwork transformations.
- Move generated products beneath their producing stages.
- Remove special filesystem treatment of `artifact.3mf`.
- Ensure manifests and dynamic product collections continue to work.
- Add end-to-end regression coverage for the artwork pipeline.
- Verify generated SVG, raster, STL, and 3MF products remain functionally
  equivalent.

This phase establishes the first complete implementation of the new storage
architecture.

---

## Phase 5 — Variants and Realizations

Introduce model-scoped variants and configured realizations.

- Define model-scoped variants.
- Establish default variant behavior.
- Distinguish reusable variants from individual realizations.
- Support multiple realizations of the same model and variant without
  collisions.
- Add tests for parameter and realization isolation.

Avoid creating dimensional variants where ordinary realization parameters
are sufficient.

---

## Phase 6 — Defined Graph and Product Catalog

Represent everything the system knows how to produce.

- Construct the Defined Graph from registered models, variants, stages,
  products, and dependencies.
- Validate the complete graph.
- Detect duplicate identities.
- Detect missing dependencies and producers.
- Detect cycles.
- Derive the Product Catalog from the Defined Graph.
- Add graph-level invariant tests.

---

## Phase 7 — Requested and Realization Graphs

Determine which products are actually required.

- Interpret artifact configuration as requested products/realizations.
- Compute transitive product dependencies.
- Construct the Realization Graph.
- Support product-targeted builds.
- Verify that requesting an upstream product does not execute unnecessary
  downstream stages.

For example, requesting artwork vector geometry should permit:

```text
prepare → raster → vector
```

without requiring:

```text
extrude → package
```

---

## Phase 8 — Independent Stage Execution

Make individual registered stages executable through the same execution
contract used by normal graph-driven builds.

- Establish a complete resolved stage execution context.
- Refactor stage invocation so normal builds execute stages through one
  reusable execution primitive.
- Ensure stage implementations do not depend upon implicit model traversal.
- Add explicit single-stage execution through the CLI.
- Resolve CLI-supplied inputs, dependency products, parameters, and output
  locations into the normal stage execution context.
- Validate explicit inputs and outputs against the registered `StageSpec`.
- Execute only the requested stage; do not implicitly execute dependencies.
- Add tests proving that graph-driven and explicit execution invoke the same
  stage implementation contract.
- Add CLI tests for successful execution and invalid/missing inputs,
  parameters, products, and stage identities.

Do not introduce a second stage implementation API for command-line
execution.

Ad-hoc sequences of explicit stage commands may be used for experimentation
and development, but persistent reusable workflows should be represented by
models or declarative graphs.

---

## Phase 9 — Product State and Resumability

Make execution depend upon product state.

* Define and implement appropriate states such as:

  * `ABSENT`
  * `INCOMPLETE`
  * `INVALID`
  * `STALE`
  * `CURRENT`
* Use manifests and completion metadata where appropriate.
* Detect interrupted stages.
* Reuse current products.
* Rebuild stale products and their affected dependents.
* Add restart and partial-build tests.

---

## Phase 10 — Cross-Model and Cross-Artifact Reuse

Exercise the first-class product architecture.

* Allow one model to consume products from another model.
* Allow one artifact to consume products from another artifact.
* Resolve dependencies to the required product rather than the producer's
  complete pipeline.
* Verify that current upstream products are reused without unnecessary work.

---

## Phase 11 — Registered Geometry and Composition

Formalize reusable 2D geometry contracts and exercise them with additional
models.

* Define registered relative geometry semantics.
* Preserve registration across transformations.
* Keep raster and vector products independent of manufacturing size.
* Introduce fitting/dimensionalization at the consuming stage.
* Implement a second production model such as coaster, ornament, or keychain.
* Exercise embedding and composition.
* Eventually test multi-artifact composition.

Use the normative scenarios in `ARCHITECTURE.md` as acceptance tests.

---

# Continuous Activities

Throughout the migration:

* keep `ARCHITECTURE.md` synchronized with intentional architectural changes;
* keep this plan synchronized with completed and newly discovered work;
* preserve existing behavior unless intentionally changing it;
* prefer invariant tests over implementation-specific tests;
* maintain unit tests for value objects and specifications;
* maintain integration tests for resolver, graph, and planner behavior;
* maintain end-to-end artwork regression coverage;
* run the complete project quality suite after each completed step;
* update documentation and CLI output when user-visible behavior changes;
* avoid compatibility layers that unnecessarily preserve obsolete internal
  architecture;
* remove obsolete code and tests once their replacements are established.

---

# Working Rule

Before beginning each change:

1. review `ARCHITECTURE.md`;
2. review this `CHANGEPLAN.md`;
3. inspect the current repository;
4. identify the smallest unmet architectural invariant;
5. write or revise the tests that demonstrate it;
6. implement only enough to satisfy that invariant;
7. run the complete quality suite;
8. update this plan when the repository's state or remaining work changes.

The repository, `ARCHITECTURE.md`, and `CHANGEPLAN.md` should together provide
enough context to determine the next incremental change without relying on
conversation history.

# Status

- Phase 1 - Complete
- Phase 2 - Complete
