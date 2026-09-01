# Change Plan

This document tracks the remaining incremental work required to bring
`lowkey-artifact-builder` into conformance with its permanent specifications.

A fresh comparison of repository HEAD against the permanent specifications
identified one remaining architectural implementation gap: the architecture now
requires configuration validation to follow required execution, but the
repository does not yet provide the corresponding execution-scoped validation
mechanism.

Artwork provides the first concrete model requirement for this mechanism:

```text
artwork_fill_color must be present in artwork_colors
```

This plan contains only the work remaining after that comparison.

## Status

```text
Phase 1 — Completed
Phase 2 — Started
```

## Permanent Specifications

The permanent normative specifications are:

```text
ARCHITECTURE.md

src/lowkey_artifact_builder/model/models/artwork/DEFINITION.md

src/lowkey_artifact_builder/model/models/shape/DEFINITION.md
```

`CHANGEPLAN.md` is not a normative specification.

It records only the temporary implementation path from repository HEAD toward
the permanent specifications.

Before selecting each implementation slice, compare repository HEAD against the
permanent specifications rather than assuming this plan remains complete.

When repository HEAD conforms to the permanent specifications, this file should
be deleted rather than retained as historical documentation.

# Development Method

Development is test-driven and incremental.

For each slice:

1. Identify one unmet architectural or model invariant.
2. Determine the observable behavior that demonstrates the invariant.
3. Write or revise the smallest useful test that expresses that behavior.
4. Confirm that the new test fails for the intended reason.
5. Make the smallest production-code change necessary to satisfy the test.
6. Refactor only after the required behavior is green.
7. Run the affected tests.
8. Run the complete test, lint, formatting, and type-check suite when the slice
   is complete.
9. Commit the independently working slice.
10. Reevaluate repository HEAD before selecting the next slice.

Tests should preferentially express semantic contracts and invariants rather
than incidental implementation details.

Do not introduce abstractions beyond those required to express the validation
contract established by the permanent specifications.

# Phase 1 — Execution-Scoped Configuration Validation

Implement the validation semantics required by `ARCHITECTURE.md`.

Configuration resolution and configuration validation are distinct
responsibilities.

Resolution determines the effective value of configuration.

Validation determines whether resolved configuration required by planned
execution is valid for the model operations that will execute.

The planner determines the scope of required execution. Model-specific
validation rules remain owned by their models.

Current persistent products may satisfy dependencies without requiring
historical configuration, source inputs, or producer stages to remain valid.

## 1.1 Establish the Generic Model Validation Contract

Introduce the smallest generic mechanism by which a model can declare
validation rules over resolved configuration.

Tests should establish that:

* a model may declare zero validation rules;
* a model validation rule can inspect multiple resolved configuration values;
* a valid resolved configuration passes validation;
* an invalid resolved configuration produces a configuration-validation error;
* validation rules remain model-owned;
* generic configuration and planning infrastructure does not contain
  Artwork-specific or Shape-specific semantic rules;
* merely resolving a configuration value does not implicitly execute
  cross-parameter model validation.

The mechanism should support cross-parameter invariants rather than being
limited to validation of one parameter in isolation.

Do not introduce a schema language, validation DSL, inheritance hierarchy, or
other framework beyond what is required by demonstrated model validation
needs.

## 1.2 Scope Validation to Required Execution

Integrate model configuration validation with planning so validation follows
the Execution Plan.

Tests should establish that:

* configuration required by a stage that must execute is validated;
* model validation relevant to that stage is applied before execution;
* configuration used only by a stage that does not need to execute is not
  required to validate merely because the stage exists in the model;
* an already-current persistent product may satisfy a dependency without
  validating the historical configuration that produced it;
* historical source inputs are not required merely to consume an already-current
  product;
* validation scope follows required execution rather than the complete Defined
  Graph;
* validation does not alter dependency closure or product-state decisions.

The planner determines which stages require execution. It must not contain
model-specific knowledge about what constitutes valid Artwork or Shape
configuration.

## 1.3 Validate Artwork Fill-Color Membership

Use Artwork as the first concrete consumer of the generic validation
mechanism.

The Artwork definition requires:

```text
artwork_fill_color ∈ artwork_colors
```

Tests should establish that:

* the default `artwork_fill_color` is `white`;
* an explicitly configured non-white fill color is valid when it belongs to
  `artwork_colors`;
* an Artwork palette does not inherently require `white`;
* a palette without `white` is valid when `artwork_fill_color` explicitly
  selects another palette member;
* a resolved `artwork_fill_color` absent from `artwork_colors` fails validation
  when execution requiring that invariant is planned;
* the same invalid historical Artwork configuration does not prevent reuse of
  an already-current downstream persistent product when the stage requiring
  the configuration will not execute.

Do not restore `artwork_fill_color` as a derived value.

Do not special-case Artwork validation in the generic configuration system,
planner, or engine.

## 1.4 Apply Configured Artwork Fill During Preparation

Complete the existing Artwork fill-color semantic change by ensuring Artwork
preparation uses the configured `artwork_fill_color` rather than hard-coded
white policy.

Tests should establish that:

* otherwise unassigned pixels inside the derived Artwork envelope receive the
  resolved `artwork_fill_color`;
* the default behavior remains white;
* an explicitly configured non-white fill color is used by preparation;
* changing the fill color changes semantic/color assignment rather than
  Artwork envelope geometry;
* preparation does not independently impose a requirement that the palette
  contain `white`;
* preparation relies on validated resolved configuration rather than
  reimplementing planner-level validation policy.

Use the shared color catalog and existing Artwork preparation mechanisms.

Do not conflate:

```text
artwork_fill_color
```

with:

```text
shape_artwork_fill_color
```

The former belongs to Artwork preparation inside the Artwork envelope. The
latter belongs to Shape-owned optional fill geometry around incorporated
registered Artwork.

## 1.5 Review Existing Validation-Like Checks

Review existing model derivations and stage implementations for checks that
currently serve as configuration validation.

In particular inspect Artwork and Shape for:

* cross-parameter invariants;
* parameter type/value checks embedded in derivations;
* configuration checks embedded in stages;
* checks that exist only because no model validation mechanism previously
  existed.

Move a check into the new validation mechanism only when it clearly represents
a model configuration invariant and doing so improves conformance with the new
architectural validation boundary.

Do not migrate:

* operation preconditions that depend on materialized files;
* product validation;
* stage-result validation;
* filesystem validity checks;
* checks intrinsic to the mechanics of a reusable operation.

Do not turn this review into a general validation refactor.

Completion of Phase 1 means the architecture's execution-scoped configuration
validation contract is implemented and Artwork fill-color semantics provide
executable evidence of that contract.

# Phase 2 — Final Permanent-Specification Conformance Audit

After Phase 1 is complete, perform a fresh comparison of repository HEAD
against:

```text
ARCHITECTURE.md

src/lowkey_artifact_builder/model/models/artwork/DEFINITION.md

src/lowkey_artifact_builder/model/models/shape/DEFINITION.md
```

Do not audit HEAD against this CHANGEPLAN alone.

## 2.1 Audit Permanent Specifications

Confirm that repository HEAD provides executable evidence for all currently
implemented architectural and model requirements.

Pay particular attention to:

* execution-scoped configuration validation;
* separation of configuration resolution from validation;
* model ownership of model-specific validation rules;
* reuse of current products without recursive historical validation;
* Artwork fill-color membership;
* Artwork preparation using the configured fill color;
* existing Artwork registered-geometry and packaging semantics;
* existing Shape registered-geometry, dimensionalization, color, fill, ridge,
  dependency, and packaging semantics;
* absence of model-specific behavior in the generic engine.

Do not require explicitly future models or capabilities merely because they
appear in architectural reference scenarios.

## 2.2 Reevaluate Shared Operations

Review for demonstrated model-independent duplication introduced or exposed by
the validation work.

Do not introduce additional abstractions unless multiple implementations
demonstrate the same model-independent contract.

Model-specific policy remains model-owned.

## 2.3 Full Repository Validation

Run the complete repository validation suite, including slow tests.

Use the repository's standard full-validation command.

Any failure revealing a permanent-specification discrepancy should result in a
new narrowly scoped implementation slice before proceeding.

## 2.4 Delete CHANGEPLAN.md

If the final audit finds no meaningful difference between repository HEAD and:

```text
ARCHITECTURE.md
artwork/DEFINITION.md
shape/DEFINITION.md
```

and the complete repository validation suite is green, delete:

```text
CHANGEPLAN.md
```

Do not preserve a completed CHANGEPLAN as historical documentation.

Version control already records that history.

If the final audit identifies another meaningful discrepancy:

1. remove completed work from this document;
2. replace it with only the newly discovered remaining work;
3. restart phase numbering from Phase 1;
4. continue until HEAD conforms to the permanent specifications.
