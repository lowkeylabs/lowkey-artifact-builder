# Change Plan — Artifact Workflow, Realizations, Product References, and Color Analysis

This change plan aligns the current implementation with the desired artifact-authoring and maker workflow while preserving the architectural principles established by `ARCHITECTURE.md` and the relevant model `DEFINITION.md` files.

`ARCHITECTURE.md` and model `DEFINITION.md` files remain normative. This document is temporary implementation guidance and should be removed when the planned work is complete and HEAD conforms to the permanent specifications.

Implementation should proceed test-first in coherent slices. Before each phase, compare the proposed behavior with current HEAD, `ARCHITECTURE.md`, and every relevant model `DEFINITION.md`. Do not silently resolve specification discrepancies in implementation. If a requirement in this plan requires a permanent architectural or model-semantic change, update the appropriate permanent specification deliberately before or with the implementation.

The generic engine must remain model-independent. Model-specific feature semantics, configuration rules, validation, and analysis policy remain model-owned.

Completed work should be removed from this plan once it is implemented, committed, and adequately evidenced. Git history and tests record completed implementation work. This plan records only the remaining work required to align HEAD with the permanent specifications.

---

# Phase 1 — Demand-Driven Color Analysis

Make `artifact colors <artifact_id>` work for artifacts whose required Artwork products have not previously been built.

The color command should identify the registered Artwork vector manifest through normal product planning and realize only the products required to perform the requested analysis.

Tests should establish that:

* `artifact colors <artifact_id>` succeeds when the required registered Artwork products already exist and are current;

* `artifact colors <artifact_id>` succeeds when the artifact has never been built;

* the command uses normal planning and execution rather than directly invoking historical producer stages;

* only the stages required to obtain the registered Artwork color-analysis inputs are executed;

* Artwork extrusion and packaging are not executed merely to perform color analysis;

* current persistent products satisfy dependencies without unnecessary producer execution;

* normal freshness and dependency semantics remain authoritative;

* failure to realize a required product produces an appropriate command failure rather than an incidental `FileNotFoundError`;

* color-analysis behavior remains independent of filesystem-path assumptions beyond normal product resolution.

Prefer fixing the orchestration of existing planning and execution mechanisms rather than introducing color-specific build logic.

## 1.1 Catalog Assignment Preference

Color analysis produces independent assignment scopes for the current printer, the user's physical-color library, and the complete physical-color catalog.

When catalog assignment has multiple assignments with the same minimum aggregate perceptual distance, prefer an equally optimal assignment that uses colors already present in the user's library.

The governing ordering is:

1. minimize aggregate perceptual color distance;
2. among equally optimal catalog assignments, prefer assignments using more colors already present in the library.

Library preference must never cause a perceptually worse assignment to replace a better assignment.

This preference is Artwork color-analysis policy rather than a generic property of color assignment. Generic color-assignment infrastructure must not contain concepts such as printer, library, catalog, filament ownership, or Artwork.

Tests should establish that:

* a strictly better perceptual catalog assignment wins regardless of library membership;

* when catalog assignments have equal minimum perceptual distance, an assignment using a library color is preferred over an otherwise equivalent assignment using a non-library color;

* when multiple colors participate in an equal-cost assignment, the assignment using the greatest applicable library preference is selected;

* printer assignment remains independent of catalog preference;

* library assignment remains independent of catalog preference;

* catalog preference does not alter the primary minimum-distance objective;

* catalog preference is expressed through a generic assignment mechanism or other model-independent abstraction rather than by introducing library/catalog semantics into generic color utilities.

Avoid numerical tie-breaking techniques that can change the primary distance optimum.

---

# Phase 2 — Artifact Lifecycle CLI

Clarify the user-facing artifact lifecycle while retaining the verb-first CLI grammar:

```text
artifact <operation> [artifact_id] [operation-options]
```

The CLI should evolve toward a coherent vocabulary including:

```text
artifact create <artifact_id>
artifact config <artifact_id>
artifact show <artifact_id>
artifact build <artifact_id>
artifact colors <artifact_id>
artifact clean <artifact_id>
artifact list
```

A future destructive `delete` operation may be added separately when its semantics are required.

Do not convert artifact operations into flags such as:

```text
artifact <artifact_id> --build
```

Creation and configuration should become conceptually distinct:

* `create` establishes a new persistent artifact definition;

* `config` inspects or modifies an existing artifact definition;

* `show` provides non-mutating inspection;

* `build` realizes requested products;

* `colors` performs color analysis;

* `clean` removes derived products while preserving persistent artifact configuration;

* `list` discovers available artifacts.

Tests should establish the intended lifecycle semantics before changing existing command behavior.

Preserve compatibility where practical during migration, but do not retain ambiguous behavior solely for compatibility if it conflicts with the clarified lifecycle.

---

# Phase 3 — Artifact Cleaning

Add a simple artifact-cleaning operation:

```text
artifact clean <artifact_id>
```

The initial implementation may remove complete generated model directories beneath the artifact silo rather than attempting stage-level cleaning.

For an artifact such as:

```text
artifacts/dog/
    artifact.toml
    artwork/
    shape/
```

cleaning may remove:

```text
artwork/
shape/
```

while preserving:

```text
artifact.toml
```

Tests should establish that:

* cleaning preserves `artifact.toml`;

* generated Artwork products are removed;

* generated Shape products are removed;

* cleaning an artifact with no generated products is safe;

* cleaning one artifact does not affect another artifact;

* subsequently rebuilding a cleaned artifact works through normal planning and execution;

* published root-level realization products introduced by a later phase are considered derived products and are also removed by clean;

* clean does not become an alternate configuration-deletion mechanism.

The governing invariant is:

> Cleaning removes rebuildable derived products while preserving the persistent artifact definition.

---

# Phase 4 — Realizations, Feature Bundles, and Self-Documenting Configuration

Review and clarify the existing realization, variant, and feature-bundle mechanisms before implementing changes.

The intended public manufacturable identity is:

```text
(artifact_id, realization)
```

Do not introduce a more granular public product-identity dimension for size, variant, feature bundle, or similar configuration.

Distinct catalog products are distinct realizations.

Examples include:

```text
default
ornament
ornament_small
ornament_large
coaster
coaster_large
drink_lid
keychain
```

A realization represents a named buildable configuration corresponding to a distinct manufacturable product.

For example:

```text
dog.default
dog.ornament
dog.ornament_large
dog.coaster
dog.keychain
```

Parameters such as physical size remain configuration within a realization. They do not introduce identities such as:

```text
dog.ornament.90mm
dog.ornament.100mm
```

unless a future permanent specification deliberately introduces such a concept.

## 4.1 `default` Is an Ordinary Realization

Every generated artifact configuration should provide a `default` realization.

`default` is an ordinary buildable realization. Its special role is only that it is selected when no explicit realization is requested.

Conceptually:

```text
artifact build dog
```

and:

```text
artifact build dog --realization default
```

select the same realization.

The implementation should avoid a separate pipeline or special manufacturing path for `default`.

A `[default]` configuration block should be suitable for copying, renaming, and editing to create another realization.

## 4.2 Feature Bundles Are Configuration Reuse, Not Product Identity

Review the existing feature-bundle mechanism and preserve it where it provides useful reusable configuration.

Feature bundles must not become another public product-identity dimension.

A realization may use a feature bundle and override parameters as appropriate, but the maker-facing product remains identified by artifact and realization.

For example, `ornament` and `ornament_large` may share the same feature bundle while differing in dimensions or other parameters.

## 4.3 Explicit Feature Selection

Evaluate support for explicit positive and negative feature vocabulary such as:

```text
hanger
no_hanger
handle
no_handle
lettering
no_lettering
```

The purpose is human-readable configuration, particularly when `artifact.toml` is edited directly.

If this representation is adopted:

* positive and negative forms represent explicit intent;

* contradictory selections such as `hanger` and `no_hanger` must be rejected rather than resolved through precedence;

* feature semantics remain model-owned;

* generic configuration infrastructure must not contain Shape-specific feature rules;

* adding a new model feature must not silently change the semantics of an existing realization.

The exact representation should follow from the HEAD audit rather than being imposed if the existing feature mechanism provides a cleaner equivalent.

## 4.4 Self-Documenting `artifact.toml`

Treat human editability and self-documentation as explicit configuration requirements.

A maker with an `artifact.toml` file should be able to discover the model-supported feature vocabulary needed to create or modify realizations without consulting source code or a separate manual.

Evaluate a generated informational section such as:

```toml
[feature_catalog]

features = [
    "artwork",
    "no_artwork",
    "hanger",
    "no_hanger",
    "handle",
    "no_handle",
    "lettering",
    "no_lettering",
]
```

The exact syntax is subject to the configuration audit, but the semantic requirement is not.

The feature catalog should be derived from model-owned feature declarations rather than maintained as a second independent list.

Where practical, the self-documenting configuration should also expose the configuration vocabulary associated with features, such as relevant parameter names or concise generated comments.

The goal is not to duplicate full developer documentation. The goal is that a maker can reasonably determine how to author another realization from the artifact configuration itself.

## 4.5 Configuration Freshening

Provide a safe mechanism to refresh generated/self-documenting portions of an existing `artifact.toml` when model capabilities evolve.

The exact CLI spelling should be selected after reviewing the existing configuration command. A form such as:

```text
artifact config dog --freshen
```

is illustrative rather than normative.

Freshening may update generated information such as `[feature_catalog]`.

It must not modify the effective configuration of existing realizations.

Tests should establish that:

* newly supported features can become discoverable in an existing artifact configuration;

* existing realizations are not automatically given new positive or negative feature selections;

* parameter values belonging to existing realizations remain unchanged;

* freshening the informational configuration cannot change the products produced by an existing realization;

* repeated freshening is stable/idempotent where appropriate.

The governing invariant is:

> Refreshing configuration documentation must not change the resolved semantics of an existing realization.

---

# Phase 5 — Compact Product References and Cross-Artifact Dependencies

Preserve support for products and dependencies across artifact silos.

An artifact silo may contain products from multiple models:

```text
artifacts/dog/
    artifact.toml
    artwork/
        default/
    shape/
        default/
        ornament/
        coaster/
        keychain/
```

A model realization should be able to consume a product produced within the same artifact silo or a product owned by another artifact silo.

Locality must not alter dependency semantics.

## 5.1 Compact Product Reference Syntax

In addition to the existing structured/name-value representation of product references, accept a compact representation:

```text
<artifact_id>.<model>.<realization>.<product>
```

For example:

```text
dog.artwork.default.manifest
```

or:

```text
company-logo.artwork.default.manifest
```

The compact and structured forms must normalize to the same logical product-reference representation before planning or execution.

Planning, dependency resolution, freshness evaluation, and stage execution must not depend on which serialization the user supplied.

Tests should establish that:

* a compact local product reference parses correctly;

* a compact cross-artifact product reference parses correctly;

* the existing structured representation remains supported;

* equivalent compact and structured references produce equal logical product identities;

* malformed compact references produce configuration errors;

* product references are not interpreted as filesystem paths;

* a current persistent product in another artifact can satisfy a dependency without rebuilding its producer;

* a missing or stale external product causes the normal planner to select the required producer work;

* dependencies may cross artifact boundaries without model-specific planner behavior.

Prefer a simple unambiguous grammar. If compact references use `.` as their delimiter, establish and validate whatever identifier restrictions are required rather than introducing unnecessary escaping rules.

## 5.2 Artifact Silo Independence

The common business workflow may place Artwork and Shape realizations in the same artifact silo, but this must not become a requirement.

For example, a Shape realization in one artifact may reuse Artwork from another artifact.

The planner and product catalog remain responsible for logical dependency resolution.

Do not introduce special local-Artwork lookup behavior that bypasses normal product references.

---

# Phase 6 — Published Realization Products

When a realization successfully produces its completed 3MF product, provide a convenient maker-facing copy at the artifact-silo root.

The canonical pipeline product remains owned by its producing stage.

For example, a canonical product may remain:

```text
artifacts/dog/shape/coaster/40-package/artifact.3mf
```

while the artifact root additionally exposes:

```text
artifacts/dog/dog.coaster.3mf
```

Use the naming convention:

```text
<artifact_id>.<realization>.3mf
```

Examples:

```text
dog.default.3mf
dog.ornament.3mf
dog.ornament_large.3mf
dog.coaster.3mf
dog.keychain.3mf
```

Tests should establish that:

* building the default realization publishes `<artifact_id>.default.3mf`;

* building a named realization publishes `<artifact_id>.<realization>.3mf`;

* publishing does not replace or relocate the canonical stage product;

* publishing occurs only after the required packaged product has been successfully produced;

* rebuilding a realization safely refreshes its published copy;

* building one realization does not overwrite another realization's published product;

* artifact IDs and realization names are handled consistently with identifier rules;

* `artifact clean` removes published copies because they are derived products;

* publication remains a convenience/output operation rather than a second source of product truth.

Do not encode feature bundle, physical size, stage identity, or another configuration dimension into the published filename beyond the realization name.

---

# Phase 7 — Visual Color Comparison

Add graphical comparison to color analysis:

```text
artifact colors <artifact_id> --view
```

The view should present one row of four side-by-side Artwork renderings:

```text
Original | Printer | Library | Catalog
```

The panels represent:

1. the original/discovered registered Artwork colors;
2. the current-printer assignment;
3. the library-color assignment;
4. the complete physical-catalog assignment.

Prefer rendering from existing registered Artwork geometry and substituting semantic color assignments rather than inventing an independent graphical representation of the Artwork.

Tests should separate graphical-data preparation from GUI mechanics so correctness does not depend entirely on visual/manual inspection.

Tests should establish that:

* the four comparison renderings are produced from the same registered Artwork geometry;

* original Artwork colors remain unchanged in the original panel;

* each assignment panel substitutes the corresponding assigned physical colors;

* semantic color identity and RGB values remain correctly associated;

* the view uses color-analysis results rather than independently recomputing assignment policy;

* `--view` works when color analysis first requires demand-driven realization of Artwork products;

* GUI/view concerns remain outside generic planning and model semantics.

The exact graphical toolkit should be selected only after reviewing existing project rendering/vector dependencies.

---

# Phase 8 — Shape/Artwork Creation Workflow

Improve interactive Shape creation so Artwork selection is natural for the maker while continuing to use normal product dependency semantics.

When creating or configuring a Shape realization that can incorporate Artwork, the workflow should support choices conceptually equivalent to:

```text
Available Artwork:
    <existing choices...>
    No artwork
    Define new artwork
```

Existing Artwork may be owned by the current artifact silo or another artifact silo.

Selecting existing Artwork should configure a normal logical product dependency.

Selecting `No artwork` should configure the Shape realization according to the model's explicit no-Artwork semantics.

Selecting `Define new artwork` should reuse the normal Artwork creation/configuration machinery rather than introducing a Shape-specific duplicate Artwork setup implementation.

The common workflow should support an artifact silo representing an image/design and multiple products made from it:

```text
artifacts/customer-image/
    artifact.toml
    artwork/
        default/
    shape/
        default/
        ornament/
        ornament_large/
        coaster/
        keychain/
    customer-image.default.3mf
    customer-image.ornament.3mf
    customer-image.ornament_large.3mf
    customer-image.coaster.3mf
    customer-image.keychain.3mf
```

However, the implementation must also permit a Shape realization to reference Artwork owned by another artifact:

```text
other-image.artwork.default.manifest
```

Do not make filesystem co-location a prerequisite for composition.

Tests should establish that:

* Shape setup can select Artwork from the current artifact;

* Shape setup can select Artwork from another artifact;

* Shape setup can explicitly select no Artwork where model semantics permit it;

* Shape setup can invoke/reuse normal Artwork creation;

* created dependencies are ordinary product references;

* subsequent planning follows those dependencies normally;

* no duplicate Shape-specific Artwork configuration implementation is introduced;

* multiple Shape realizations can reuse the same Artwork;

* the workflow remains compatible with the self-documenting realization configuration established earlier.

---

# Completion Criteria

The change plan is complete when all remaining phases are implemented and HEAD conforms to the resulting permanent architecture and model definitions.

Before declaring completion:

* run the full non-slow test suite;

* run the project's static/type checks;

* compare HEAD against `ARCHITECTURE.md`;

* compare each affected model against its `DEFINITION.md`;

* verify that generic engine/configuration/planning code contains no model-specific semantic rules introduced by this work;

* verify that artifact configuration remains understandable and editable without requiring knowledge of internal stage paths;

* verify that `(artifact_id, realization)` is sufficient to identify a maker-facing manufacturable product;

* verify that both local and cross-artifact dependencies use the same logical product-reference mechanisms;

* verify that cleaning followed by rebuilding reproduces derived products from persistent configuration and required source inputs;

* verify that color analysis is practical against the complete physical catalog;

* verify that catalog assignment prefers already-owned library colors only when doing so preserves the minimum perceptual-distance optimum;

* verify that any permanent invariants discovered during implementation have been incorporated into `ARCHITECTURE.md` or the appropriate model `DEFINITION.md`.

Once permanent specifications and HEAD are aligned, remove the completed `CHANGEPLAN.md` content rather than treating this temporary plan as an additional permanent specification.

