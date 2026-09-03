# Change Plan — Variant / Realization Semantic Alignment

## Purpose

Bring the current repository into conformance with `ARCHITECTURE.md` and the applicable Model `DEFINITION.md` files following the clarified architectural semantics of Model, Feature, Variant, Artifact, Realization, Stage, and Product.

This plan is temporary.

`ARCHITECTURE.md` and the Model `DEFINITION.md` files are the permanent normative specifications. Existing implementation terminology and tests are evidence of current behavior, not independent architectural authority.

The migration should preserve the large body of existing correct behavior while adding the comparatively small amount of machinery necessary to make Variant semantics explicit.

The final action of this plan is to delete `CHANGEPLAN.md`.

---

# Migration Principles and Invariants

## 1. Architecture is normative

Do not infer architectural meaning from an identifier, filename, configuration section, test name, comment, or historical term alone.

Determine what an existing construct does before deciding what architectural concept it represents.

A lexical match is evidence for investigation, not evidence of architectural identity.

## 2. Preserve compatible existing representations

The migration is not a terminology cleanup.

In particular, the existing decomposed representation:

```text
model = shape
realization = ornament
```

may represent the same Variant identity as the fully qualified reference:

```text
variant = shape.ornament
```

where the historical `realization` field carries the local Variant name.

Such representations may remain where their meaning is unambiguous.

Do not rename Product references, execution identities, filesystem namespaces, completion identities, fingerprints, or similar structures merely to replace this decomposed representation with a fully qualified Variant string.

## 3. Variant identity has compact and decomposed forms

A Variant's complete identity is:

```text
Model + local Variant name
```

For example:

```text
shape + ornament
```

may be represented compactly as:

```text
shape.ornament
```

or decomposed as:

```text
model = shape
local name = ornament
```

A fully qualified Variant reference is a compact representation of the same identity, not an additional identity mechanism.

Public interfaces may support the compact form while normalizing immediately to existing decomposed machinery.

## 4. Realization means application of a Variant

An architectural Realization is:

```text
Artifact + Variant + optional Artifact-specific customization
                    ↓
               Realization
```

A Realization is concrete and Artifact-specific.

It is not:

* a reusable catalog definition;
* a second parameter-preset mechanism;
* an independent Model selection;
* an independent Variant selection separate from Model identity.

Historical fields named `realization` do not necessarily represent this domain concept.

## 5. Variant is the reusable catalog definition

A Variant is a complete, named, Model-scoped constructible configuration.

It defines:

* selected Features;
* parameter defaults;
* other Model-owned configuration necessary to describe the offering.

Selecting a Variant necessarily identifies its Model.

Two Variants may select identical Features and differ only in parameter defaults when they intentionally represent distinct catalog offerings.

Artifact-specific customization does not create a new Variant.

## 6. Default Variants preserve historical Model behavior

Existing Models already provide directly usable behavior without explicit specialized Variant selection.

That historical behavior is understood as behavior of the corresponding `default` Variant.

Making the default Variant explicit, including explicitly articulating its Features, must not by itself reduce or redefine that historical behavior.

An implicitly supplied `default` Variant is therefore not assumed to be semantically empty merely because its definition was historically implicit.

## 7. Existing ordinary Model tests are default-Variant tests

Tests exercising a Model's ordinary historical behavior without selecting a specialized Variant are presumed to exercise that Model's `default` Variant unless their assertions explicitly conflict with the permanent specifications.

Do not rewrite such tests merely to make `default` selection explicit.

Existing tests should be classified as:

### Default-Variant behavioral test

The test describes historical Model-default behavior now understood as behavior of `<model>.default`.

Preserve it.

### Architectural invariant

The test exercises behavior unaffected by this migration.

Preserve it.

### Fixture or API migration

The behavioral assertion remains correct but setup must change to exercise new Variant machinery.

Change only the necessary setup.

### Semantic reclassification

The test exercises useful behavior but historically assigns that behavior to the wrong architectural concept.

Preserve the useful behavioral coverage while moving ownership to the correct concept.

### Semantic replacement

The test explicitly requires behavior prohibited by the permanent architecture.

Replace that assertion with the normative behavior.

Preservation is the default.

## 8. Do not conflate customer offerings with Stage Products

A customer-facing or catalog offering is represented by a Variant.

An architectural Product is a named persistent output produced by a Stage.

Existing ProductSpec, ProductRef, Product Catalog, Product dependency, persistence, and reuse machinery should remain unchanged unless a specific architectural discrepancy is demonstrated.

## 9. Features articulate optional Model capabilities

Features are Model-owned optional composable capabilities or behaviors.

Stages are not automatically Features.

Intrinsic Model behavior is not automatically a Feature.

During this migration, introduce Features to articulate existing separable capabilities before using Feature machinery to introduce new Model behavior.

Do not invent Feature definitions merely to map every existing Stage or operation onto one.

## 10. Prefer normalization at boundaries

Where a compact Variant reference such as:

```text
shape.ornament
```

is accepted by an API or configuration interface, prefer normalizing it at that boundary into the representation already used by the implementation.

Do not propagate a second parallel identity representation through the runtime merely because compact Variant references are convenient externally.

## 11. Migrate incrementally

Use:

```text
green suite
    ↓
intentional RED slice
    ↓
minimal production change
    ↓
green suite
    ↓
next slice
```

Do not perform broad migrations and classify failures afterward.

## 12. Every phase ends in acceptance

Each implementation phase ends with integrated executable evidence demonstrating the capability introduced or verified by that phase.

Existing non-conflicting tests remain green.

If a phase's required behavior is already satisfied by HEAD, prove that behavior and close the phase without manufacturing production changes.

---

# Phase 0 — Semantic Inventory and Migration Boundary

## Status: Complete

The repository and permanent specifications have been reviewed sufficiently to establish the migration boundary.

The resulting architectural conclusions have been incorporated into `ARCHITECTURE.md`.

## Findings

### Variant definition is the principal declarative gap

Current Variant machinery principally treats a Variant as a named Model-scoped parameter preset.

The permanent architecture requires a Variant to be a complete constructible Model-scoped configuration including:

* selected Features;
* parameter defaults;
* Model identity through Model ownership.

This is the primary new semantic machinery required.

### Existing decomposed runtime identity is compatible

Existing structures commonly identify execution context using a pair such as:

```text
model = shape
realization = ornament
```

where `realization` carries the local Variant name.

This is compatible with the fully qualified Variant identity:

```text
shape.ornament
```

No repository-wide runtime identity rename is required.

### Product infrastructure is architecturally compatible

Technical Product infrastructure represents persistent Stage outputs.

It is not the catalog-offering concept represented by Variant.

ProductSpec, ProductRef, dependency binding, Product state, persistence, and reuse are expected architectural invariants unless later tests demonstrate a specific discrepancy.

### Filesystem namespaces are compatible

A path such as:

```text
artifacts/cat/shape/ornament/...
```

already decomposes the relevant Variant identity into Model and local Variant/Realization namespace.

No physical path migration is required merely to introduce fully qualified Variant references.

### Historical default behavior maps to default Variants

Existing Model behavior exercised without specialized Variant selection is understood as behavior of:

```text
artwork.default
shape.default
```

Existing tests exercising that behavior should ordinarily remain unchanged.

### Historical reusable realization configuration requires semantic inspection

Historical reusable named configuration under constructs such as `realizations.*` must be classified according to behavior.

Where such configuration defines a reusable catalog offering, that responsibility belongs to Variant.

This does not imply that every runtime field or namespace named `realization` must change.

## Phase 0 acceptance

Satisfied.

The migration boundary is now:

```text
substantive new machinery:
    Variant = Model-owned Features + parameter defaults

compact identity:
    shape.ornament

equivalent existing representation:
    model=shape + realization=ornament

architectural Realization:
    Artifact + Variant + optional customization

expected invariant:
    existing runtime/Product/path machinery
```

No production semantic change is required for Phase 0.

---

# Phase 1 — Complete Declarative Variant Semantics

Align the reusable Model-owned definition layer with `ARCHITECTURE.md`.

This phase should begin with tests in the existing Model/Variant test family.

## Required behavior

Establish that:

* a Model owns its Variants;
* Variant local names are Model-scoped;
* a Variant may select zero or more Features belonging to that Model;
* Variant Feature selections are immutable definition data;
* Variant parameter defaults remain immutable definition data;
* selected Features must exist in the owning Model;
* duplicate Feature selections are invalid;
* two Variants may select the same Features while differing in parameter defaults;
* a default Variant remains available where appropriate;
* existing implicit default behavior remains valid;
* making an existing default Variant explicit does not reduce historical Model behavior.

Prefer extending the existing `VariantSpec` and Model-definition validation rather than introducing a second Variant abstraction.

Do not introduce Artifact/configuration/runtime changes merely to complete this declarative layer.

## TDD boundary

The first RED slice should establish the complete Variant definition contract before changing production code.

Existing Variant tests that correctly establish Model scoping, immutability, default availability, and parameter behavior should be retained and expanded rather than replaced.

## Phase acceptance

Using an integrated declarative Model definition, demonstrate multiple Model-owned Features and multiple complete Variants whose Feature selections and parameter defaults differ.

The definitions must validate independently of any Artifact.

The Variant identities must be unambiguously Model-scoped.

Existing default Model behavior must remain green.

---

# Phase 2 — Compact Variant References and Configuration Application

Add fully qualified Variant references where they materially simplify selection and configuration.

The central equivalence is:

```text
variant = shape.ornament

        ⇅

model = shape
realization = ornament
```

The compact form should normalize to the existing decomposed representation rather than creating parallel runtime identity machinery.

## Required behavior

Establish that:

* a fully qualified Variant reference identifies both Model and local Variant name;
* selecting `shape.ornament` identifies Model `shape`;
* malformed or unknown Variant references fail clearly;
* compact and decomposed references to the same Variant are equivalent;
* conflicting compact and decomposed selections are rejected or otherwise handled by one explicit, tested rule;
* omission of specialized Variant selection continues to select the appropriate default Variant;
* Artifact-specific parameter overrides customize the resulting Realization without changing its originating Variant;
* existing configuration precedence remains deterministic.

Where existing APIs benefit from compact selection, add a `variant=` form or equivalent boundary syntax and normalize it immediately.

Do not require every internal structure to carry a fully qualified Variant string.

## Historical configuration

Inspect historical reusable named `realizations.*` configuration separately from runtime fields named `realization`.

Where a historical configuration block is actually defining a reusable catalog offering, migrate that reusable definition responsibility to Model-owned Variants.

Do not migrate runtime identity fields merely because they share the same historical name.

## Phase acceptance

Using real configuration resolution, demonstrate that:

```text
variant = shape.ornament
```

and:

```text
model = shape
realization = ornament
```

identify the same Variant and produce equivalent effective configuration for the same Artifact.

Also demonstrate Artifact-specific customization while retaining `shape.ornament` as the originating Variant.

All non-conflicting configuration tests remain green.

---

# Phase 3 — Runtime Conformance Verification

Verify that the existing runtime correctly carries the clarified Variant/Realization semantics.

This is primarily a verification phase.

Do not assume runtime refactoring is required.

Review:

* requested Realization construction;
* Defined Graph derivation;
* Realization Graph construction;
* Product identity and Product references;
* dependency resolution and binding;
* planning;
* Stage context;
* execution identity;
* completion state;
* fingerprints;
* incremental reuse;
* persistent Product lookup;
* filesystem Realization namespaces.

## Expected result

Existing decomposed runtime identities such as:

```text
artifact
model
realization/local Variant name
stage
product
```

are expected to remain valid.

A runtime Realization must remain traceable to:

```text
Artifact
    +
Model-scoped Variant
    +
optional Artifact customization
```

without requiring every runtime object to carry a new fully qualified Variant field.

## Required evidence

Demonstrate that compact and decomposed Variant selection converge before or at the runtime boundary and therefore produce equivalent:

* Realization Graphs;
* Build Plans;
* ProductRefs;
* dependency bindings;
* Stage contexts;
* canonical Product locations;
* completion identities;
* fingerprints;
* incremental/reuse behavior.

If existing behavior already satisfies these requirements, add or identify sufficient integrated evidence and close the phase without production changes.

Change production runtime code only where a focused test demonstrates an architectural discrepancy.

## Phase acceptance

An Artifact/Variant application must produce the correct dependency closure and stable Product identities.

Current Products must continue to satisfy dependencies.

Incremental execution and cross-Artifact/cross-Model reuse must remain intact.

Compact Variant references must not create a second runtime identity system.

---

# Phase 4 — Articulate Actual Artwork and Shape Variants

Apply the completed generic machinery to the actual Artwork and Shape Models.

Review each Model's `DEFINITION.md` before changing that Model.

Do not infer Feature membership solely from existing Stages.

## Existing behavior first

Identify which optional or separable capabilities are currently implicit in each Model's historical default behavior.

Articulate those capabilities as Features only where justified by the applicable Model definition and architecture.

Then make the Model's Variant catalog explicit.

The first explicit `default` Variant for an existing Model must describe the existing constructible default offering rather than redefine it.

In particular:

```text
artwork.default after migration
```

must preserve the applicable historical behavior of:

```text
artwork before explicit Variant articulation
```

and likewise for:

```text
shape.default
```

unless a permanent Model specification explicitly requires different behavior.

## Variant catalogs

Define only Variants justified by the applicable Model specification.

Potential names appearing in `ARCHITECTURE.md`, such as:

```text
shape.ornament
shape.ornament-large
shape.coaster
shape.keychain
```

remain conceptual until made normative by the Shape Model definition or an intentional Model-definition change.

Distinct reusable offerings should be distinct Variants.

Artifact-specific customization remains customization of an application, not creation of another Variant.

## Public workflow

Expose Variant discovery and compact Variant selection where useful through normal configuration and CLI workflows.

The intended user model should be apparent:

```text
Model
    ↓
available Variants
    ↓
Variant applied to Artifact
    ↓
Realization
    ↓
Products
```

Do not expose architectural Realization as a second reusable catalog-definition layer.

Do not change filesystem presentation merely to replace an existing valid decomposed Variant representation.

## Phase acceptance

Demonstrate real Artwork and Shape workflows that:

* preserve historical default behavior;
* discover/select valid Variants;
* apply a Variant to an Artifact;
* accept Artifact-specific customization;
* select the correct Feature behavior;
* build the expected dependency graph;
* produce expected persistent Products.

At least one acceptance path must produce actual manufacturing output through the normal CLI workflow.

All non-conflicting existing Model, CLI, and acceptance tests remain green.

---

# Phase 5 — Repository-Wide Conformance and Cleanup

Perform the final conformance audit against:

* `ARCHITECTURE.md`;
* every applicable Model `DEFINITION.md`;
* implementation at HEAD;
* the complete test suite.

Search for historical terms such as `variant`, `realization`, `model`, and `product`, but inspect their semantics rather than treating lexical matches as defects.

## Verify

Confirm that:

* Variant definitions are complete Model-owned constructible configurations;
* Variants select Features and provide parameter defaults;
* Variant identity is Model-scoped;
* fully qualified Variant references are equivalent to decomposed Model/local-name references;
* historical fields named `realization` may remain when they unambiguously carry the local Variant/Realization namespace required by the implementation;
* selecting a Variant identifies its Model;
* default Variants preserve historical Model-default behavior;
* Features represent Model-owned optional capabilities rather than mechanically mirroring Stages;
* architectural Realizations are Artifact-specific applications of Variants;
* Artifact customization does not create a new Variant;
* reusable catalog offerings are not independently defined as Realizations;
* persistent Stage outputs remain architectural Products;
* Product identity and reuse remain stable;
* dependency-driven planning remains intact;
* Defined Graph validation remains complete;
* incremental execution remains intact;
* cross-Model and cross-Artifact Product reuse remains intact;
* generic infrastructure contains no Model-specific Feature semantics;
* no unnecessary second Variant identity representation has been propagated through the runtime;
* temporary compatibility mechanisms introduced during the migration have been removed or permanently justified.

Review tests changed during the migration and ensure behavioral assertions were not weakened merely to obtain green results.

Run the complete repository validation suite, including the normal non-slow tests, type checking, linting, and other project checks.

## Final architectural acceptance

Demonstrate:

```text
Model
  └── Variant
        ├── selected Features
        └── defaults
              │
              │ applied to
              ▼
Artifact ─────────────> Realization
                            │
                            └── Stages
                                  │
                                  └── persistent Products
```

Acceptance must include:

1. an uncustomized application of a Variant;
2. a customized application of the same Variant;
3. proof that both retain the same originating Variant;
4. a distinct reusable catalog offering represented by a distinct Variant;
5. equivalent compact and decomposed Variant references;
6. preservation of default-Variant historical behavior;
7. stable persistent Product identity and reuse.

All repository checks must pass.

---

# Completion

When Phase 5 acceptance is green and the repository conforms to the permanent specifications:

1. perform one final comparison of HEAD against `ARCHITECTURE.md` and every applicable Model `DEFINITION.md`;
2. confirm no unresolved item in this plan remains;
3. confirm temporary compatibility mechanisms introduced by this migration have been removed unless permanently justified;
4. confirm the complete repository validation suite is green;
5. delete `CHANGEPLAN.md`.

Deletion of `CHANGEPLAN.md` is the final change of this migration.

