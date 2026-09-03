# Change Plan — Variant / Realization Semantic Alignment

## Purpose

Bring the current repository into conformance with `ARCHITECTURE.md` and the applicable Model `DEFINITION.md` files following the revised architectural semantics of Model, Feature, Variant, Artifact, Realization, Stage, and Product.

This plan is temporary.

`ARCHITECTURE.md` and the Model `DEFINITION.md` files are the permanent normative specifications. Existing implementation terminology and tests are evidence of current behavior, not independent architectural authority.

The migration should preserve the large body of existing correct behavior while correcting the narrower set of semantics that have become conflated over time.

The final action of this plan is to delete `CHANGEPLAN.md`.

---

# Migration Principles and Invariants

These principles govern every phase of the migration.

## 1. Architecture is normative; terminology in HEAD is not

Do not infer architectural meaning from an identifier, filename, configuration section, test name, comment, or historical term alone.

Terms such as:

* `product`
* `realization`
* `variant`
* `artifact`
* `model`

may have been used historically for concepts that do not exactly correspond to the normative concepts now defined by `ARCHITECTURE.md`.

Determine what an existing construct **does** before deciding what architectural concept it represents.

A lexical match is evidence for investigation, not evidence of architectural identity.

## 2. Interpret terminology semantically, not lexically

For every significant historical use of an architectural term:

1. determine the behavior or concept represented in that context;
2. map that concept to the current architecture;
3. determine whether the behavior is compatible with the architecture;
4. only then decide whether code, tests, configuration, or terminology should change.

Do not perform repository-wide search-and-replace migrations based only on terminology.

Historical terminology may remain when it has a distinct, unambiguous technical meaning and does not conflict with the architectural model.

## 3. Realization means instantiation of a Variant

For purposes of the architectural domain model:

> A Realization is the instantiation of a Variant for an Artifact, with or without Artifact-specific customization.

Equivalently:

```text
Artifact + Variant + optional customization
                    ↓
               Realization
```

A Realization is concrete and Artifact-specific.

A Realization is **not**:

* a reusable catalog definition;
* a second parameter-preset mechanism;
* an independently reusable product configuration;
* an independent Model selection;
* an independent Variant selection separate from Model identity.

Whenever historical code uses `realization`, ask:

> Does this represent the instantiation of a Variant for an Artifact?

If yes, it is a candidate for the architectural Realization concept.

If no, determine what concept it actually represents before changing it.

## 4. Historical named realizations may actually be Variants

A historical construct such as:

```toml
[realizations.ornament]
model = "shape"
variant = "default"
...
```

must not automatically be treated as an architectural Realization merely because it is named `realizations`.

If it defines a reusable named constructible configuration, its semantics are closer to a Variant.

Tests around such constructs may therefore contain useful Variant behavior under historical Realization terminology.

Preserve useful behavioral coverage while migrating the concept to its proper architectural home.

## 5. Variant is the reusable catalog definition

A Variant is a complete, named, Model-scoped constructible configuration.

Its identity is:

```text
Model + Variant name
```

A Variant may define:

* selected Features;
* parameter defaults;
* other Model-owned configuration necessary to describe the reusable offering.

Selecting a Variant necessarily identifies its Model.

Two Variants may legitimately select identical Features and differ only in parameter defaults when they represent distinct catalog offerings.

Artifact-specific customization does not create a new Variant.

## 6. Do not conflate customer-facing products with Stage Products

The word `product` may occur in two different senses.

A customer-facing or catalog product is conceptually represented by a Variant.

An architectural `Product` is:

> a named persistent output produced by a Stage.

Examples include manifests, SVGs, STLs, registered geometry, and 3MF files.

These concepts must remain distinct even when ordinary prose uses the same English word for both.

Do not rename or migrate technical Product infrastructure merely because a Variant is also described informally as a product offering.

## 7. Preserve behavior that the architecture does not require us to change

The migration is not an opportunity for broad cleanup or redesign.

Existing behavior remains a regression requirement unless:

* `ARCHITECTURE.md` requires different behavior;
* an applicable Model `DEFINITION.md` requires different behavior; or
* the behavior exists only to support a superseded semantic model.

Prefer the smallest architectural change that establishes the required boundary.

## 8. Existing tests must be classified, not blindly preserved or rewritten

Tests encountered during migration fall into three broad categories.

### Semantic rewrite

The test asserts behavior that conflicts with the normative architecture.

Rewrite or remove the conflicting assertion and replace it with architectural behavior.

### Fixture or API migration

The behavior asserted by the test remains correct, but its setup uses superseded configuration, naming, or APIs.

Migrate the setup while preserving the behavioral assertion.

### Architectural invariant

The test exercises behavior unaffected by the semantic migration.

Do not rewrite it merely because nearby implementation details change.

The large existing test suite is a regression shield. Preserve it whenever possible.

## 9. Migrate incrementally from green to intentional red to green

Do not perform a broad architectural rewrite and then classify hundreds of failures afterward.

The expected development pattern is:

```text
green suite
    ↓
small intentional RED slice
    ↓
minimal production change
    ↓
green suite
    ↓
next intentional RED slice
```

Each slice begins by reviewing the applicable permanent specifications and existing tests.

New or revised tests establish the intended architectural boundary before production code changes.

## 10. Every phase ends in acceptance

Each phase must end with an acceptance test or equivalent integrated executable evidence demonstrating that the architectural capability introduced by that phase works through its intended boundary.

Unit tests alone do not close a phase.

Existing non-conflicting tests must remain green at phase completion.

## 11. Avoid compatibility architecture unless it has demonstrated value

Do not preserve superseded semantics merely to keep old tests or internal APIs unchanged.

Temporary compatibility mechanisms may be introduced when they materially reduce migration risk, but they must not create a second permanent architectural model.

If compatibility code is introduced, its removal must be accounted for before this plan closes.

## 12. Names should converge after semantics converge

Correct behavior and ownership first.

Rename identifiers, tests, comments, configuration sections, and documentation when doing so improves correspondence with the normative architecture, but do not begin with mechanical terminology cleanup.

The final terminology audit is semantic, not merely lexical.

---

# Phase 0 — Semantic Inventory and Migration Boundary

Establish the semantic migration boundary before changing production behavior.

Review current implementation and tests involving:

* Model;
* Feature;
* Variant;
* Realization;
* Artifact configuration;
* Product;
* Product references;
* graph construction;
* planning;
* dependency binding;
* execution context;
* completion and fingerprint identity;
* persistent paths;
* CLI workflows.

For each important occurrence of historically overloaded terminology, determine the concept represented by its behavior.

In particular, distinguish:

```text
historical reusable "realization" configuration
    → candidate Variant semantics

Artifact-specific application of a Variant
    → Realization semantics

customer-facing "product"
    → Variant/catalog-offering semantics

persistent Stage output
    → Product semantics

ordinary execution/stage "realization"
    → inspect independently; do not assume domain Realization
```

Classify affected test families as:

* semantic rewrite;
* fixture/API migration;
* expected architectural invariant.

Record the resulting impact map in this `CHANGEPLAN.md` rather than creating another permanent specification.

Do not attempt to enumerate every individual affected test before beginning implementation. The purpose is to establish the semantic boundaries and identify the major migration surfaces.

### Phase acceptance

Phase 0 is complete when the repository has been reviewed sufficiently to identify:

* which current constructs are actually acting as Variants;
* which current constructs represent architectural Realizations;
* where `Product` means persistent Stage output versus informal catalog offering;
* the major test families requiring semantic rewrite;
* the major test families likely requiring fixture/API migration;
* the major test families expected to remain invariant.

No production semantic change is required to close Phase 0.

---

# Phase 1 — Declarative Model, Feature, and Variant Alignment

Align the reusable Model-owned definition layer with `ARCHITECTURE.md`.

A Model must own its Features and Variants.

A Variant must represent a complete constructible Model-scoped configuration rather than merely a named parameter preset.

Establish support for Variant Feature selection and the validation necessary to ensure that Variant definitions are internally valid.

Preserve the useful existing behavior of Model defaults and Variant parameter defaults where compatible with the architecture.

The declarative model should establish at minimum that:

* Variant identity is Model-scoped;
* a Variant belongs to exactly one Model;
* a Variant may select zero or more Model Features;
* selected Features must exist in that Model;
* duplicate Feature selection is invalid;
* Variant parameter defaults remain immutable definition data;
* two Variants may select the same Features and differ only in parameter defaults;
* a default Variant remains available where appropriate;
* a Variant is sufficient, together with Model defaults and required Artifact inputs, to describe a constructible offering.

Do not yet force Artifact/configuration/runtime migration into this phase.

### Phase acceptance

Demonstrate through an integrated declarative Model test that a Model can define multiple complete Variants with Feature selections and parameter defaults, that those definitions validate independently of any Artifact, and that their identities are unambiguously Model-scoped.

All non-conflicting existing tests must remain green.

---

# Phase 2 — Artifact, Variant, and Realization Configuration Semantics

Migrate configuration semantics to the architectural relationship:

```text
Artifact + Variant + optional Artifact customization
                    ↓
               Realization
```

Remove the semantic requirement that a Realization independently select both Model and Variant.

Selecting a Variant must identify its Model.

Historical named reusable `realizations.*` configuration must be evaluated by behavior. Where it is actually defining reusable catalog configurations, migrate that responsibility to Variants rather than preserving it as architectural Realization behavior.

Artifact configuration should express which Variant or Variants are applied to the Artifact and any Artifact-specific customization required for each application.

The resulting Realization must retain its originating Variant even when Artifact customization changes effective parameter values.

Configuration precedence must continue to provide deterministic effective configuration, but its implementation must reflect the new ownership model.

Rewrite existing tests only where their asserted semantics conflict with the architecture. Tests whose assertions remain valid should receive only the fixture/API migration necessary to express the new configuration.

### Phase acceptance

Using real configuration resolution, demonstrate:

* a Model-owned Variant can be selected for an Artifact;
* selecting the Variant determines the Model;
* applying it produces the effective Realization configuration;
* Artifact-specific overrides customize that Realization;
* customization does not change the originating Variant;
* multiple Variants can be applied to the same Artifact without defining reusable configurations as independently named Realizations.

All non-conflicting existing tests must remain green.

---

# Phase 3 — Runtime Identity, Graph, Planning, and Persistence Alignment

Propagate the corrected Variant/Realization semantics through the runtime without changing unrelated execution behavior.

Review and align as necessary:

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
* filesystem realization namespaces.

Do not assume that every current use of the word `realization` represents the architectural Realization. Change behavior only where the represented concept conflicts with the normative model.

The Defined Graph must continue to validate complete Model-owned definitions independently of which Variants are instantiated for particular Artifacts.

A runtime Realization must be traceable to:

```text
Artifact
    +
Model-scoped Variant
    +
optional Artifact customization
```

Product identity must continue to identify persistent Stage outputs rather than customer-facing Variant offerings.

Preserve dependency-driven execution, resumability, persistent reuse, incremental behavior, and cross-Artifact/cross-Model dependencies unless the architecture specifically requires a change.

Prefer migration of fixture/configuration construction over rewriting engine behavioral assertions when those assertions remain architecturally valid.

### Phase acceptance

Demonstrate through integrated planning and execution tests that:

* a requested Artifact/Variant application produces the correct Realization graph;
* the correct Stage/Product dependency closure is planned;
* Products retain stable logical identity;
* existing current Products can still satisfy dependencies;
* incremental execution and reuse continue to operate;
* Variant identity and Realization identity are not conflated.

All non-conflicting engine and acceptance tests must remain green.

---

# Phase 4 — Model Catalogs and Public Workflow Alignment

Apply the corrected semantics to the actual Artwork and Shape Models and to user-facing workflows.

Review each Model `DEFINITION.md` before changing that Model.

Define only those Features and Variants justified by the applicable permanent Model specification. Examples in `ARCHITECTURE.md` are conceptual unless the Model definition makes them normative.

Align as necessary:

* Model registration;
* Model Variant catalogs;
* Artifact creation/configuration;
* CLI display and selection;
* build commands;
* dependency references;
* configuration inspection;
* filesystem presentation;
* user-visible terminology.

The normal workflow should make the catalog relationship apparent:

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

Where a local Variant name is sufficient to identify the single application of that Variant to an Artifact, preserve the architecture's allowance for using that Variant name as the Realization namespace.

### Phase acceptance

Demonstrate real user workflows for the applicable Artwork and Shape Models that:

* discover/select valid Variants;
* apply them to Artifacts;
* accept Artifact-specific customization;
* build the expected dependency graph;
* produce the expected persistent Products;
* permit multiple Variant applications to the same Artifact where supported;
* do not require independently defined reusable Realization configurations.

At least one acceptance path must produce actual manufacturing output through the normal CLI workflow.

All non-conflicting existing CLI, Model, and acceptance tests must remain green.

---

# Phase 5 — Repository-Wide Architectural Conformance

Perform the final conformance audit against:

* `ARCHITECTURE.md`;
* every applicable Model `DEFINITION.md`;
* the implementation at HEAD;
* the complete test suite.

Search for terminology associated with the migration, but treat search results only as candidates for semantic inspection.

For significant remaining occurrences of overloaded terms such as `realization` and `product`, determine their actual meaning in context before deciding whether they require modification.

Verify specifically that:

* reusable constructible catalog definitions are Variants;
* Variants are Model-scoped;
* Variant selection identifies the Model;
* Features are Model-owned capabilities selected/configured by Variants;
* architectural Realizations are Artifact-specific instantiations of Variants;
* Artifact customization does not create a new Variant;
* Realization is not a second reusable configuration mechanism;
* persistent Stage outputs remain architectural Products;
* customer-facing product terminology is not conflated with Stage Product identity;
* Defined Graph validation remains complete;
* dependency-driven planning remains intact;
* Product reuse and incremental execution remain intact;
* Model-specific semantics have not leaked into generic infrastructure;
* obsolete compatibility behavior introduced during migration has been removed or explicitly justified by the permanent specifications.

Review tests changed during the migration and ensure that behavioral assertions were not weakened merely to obtain green results.

Run the complete repository checks, including the full non-slow test suite, type checking, linting, and other normal project validation.

### Final architectural acceptance

Add or identify integrated acceptance coverage demonstrating the complete normative relationship:

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

The acceptance coverage must demonstrate both an uncustomized and an Artifact-customized application of a Variant and establish that both Realizations retain the same originating Variant.

It must also demonstrate that a distinct reusable catalog offering is represented by a distinct Variant rather than by an independently reusable Realization definition.

All repository checks must pass.

---

# Completion

When Phase 5 acceptance is green and the repository conforms to the permanent specifications:

1. perform one final comparison of HEAD against `ARCHITECTURE.md` and the applicable Model `DEFINITION.md` files;
2. confirm that no unresolved item in this plan remains;
3. confirm that temporary compatibility mechanisms introduced by this migration have been removed unless permanently justified;
4. confirm the complete repository validation suite is green;
5. delete `CHANGEPLAN.md`.

Deletion of `CHANGEPLAN.md` is the final change of this migration.
