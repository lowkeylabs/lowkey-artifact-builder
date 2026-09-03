# Change Plan — Artifact Workflow, Realizations, Product References, and Color Analysis

This change plan aligns the current implementation with the desired artifact-authoring and maker workflow while preserving the architectural principles established by `ARCHITECTURE.md` and the relevant model `DEFINITION.md` files.

`ARCHITECTURE.md` and model `DEFINITION.md` files remain normative. This document is temporary implementation guidance and should be removed when the planned work is complete and HEAD conforms to the permanent specifications.

Implementation should proceed test-first in coherent slices. Before each phase, compare the proposed behavior with current HEAD, `ARCHITECTURE.md`, and every relevant model `DEFINITION.md`. Do not silently resolve specification discrepancies in implementation. If a requirement in this plan requires a permanent architectural or model-semantic change, update the appropriate permanent specification deliberately before or with the implementation.

The generic engine must remain model-independent. Model-specific feature semantics, configuration rules, validation, and analysis policy remain model-owned.

Completed work should be removed from this plan once it is implemented, committed, and adequately evidenced. Git history and tests record completed implementation work. This plan records only the remaining work required to align HEAD with the permanent specifications.

---

# Phase 4 — Features and Self-Documenting Configuration

The intended public manufacturable identity remains:

```text
(artifact_id, realization)
```

Do not introduce a more granular public product-identity dimension for size, variant, feature selection, or similar configuration.

Variants remain the model-owned mechanism for reusable named parameter presets described by `ARCHITECTURE.md`.

A realization may select a model variant and may override parameters provided by that variant. Variant selection is configuration reuse and does not form an additional public artifact identity dimension.

Parameters such as physical size remain configuration within a realization. Distinct manufacturable products may be represented by distinct realizations when appropriate.

## 4.3 Explicit Feature Selection

Review the existing model feature mechanism and determine whether explicit feature-selection vocabulary is required for clear, stable, human-editable realization configuration.

Evaluate support for explicit positive and negative feature vocabulary such as:

```text
hanger
no_hanger

handle
no_handle

lettering
no_lettering
```

The purpose is to make realization intent explicit, particularly when `artifact.toml` is edited directly.

If this representation is adopted:

* positive and negative forms represent explicit intent;
* contradictory selections such as `hanger` and `no_hanger` must be rejected rather than resolved through precedence;
* feature semantics remain model-owned;
* generic configuration infrastructure must not contain Shape-specific or other model-specific feature rules;
* adding a new model feature must not silently change the semantics of an existing realization.

The exact representation should follow from comparison of HEAD with `ARCHITECTURE.md` and the relevant model `DEFINITION.md` rather than being imposed if the existing feature mechanism provides a cleaner equivalent.

Do not introduce a second reusable-preset abstraction for feature combinations. Reusable parameter presets remain variants.

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

Provide a safe mechanism to refresh generated or self-documenting portions of an existing `artifact.toml` when model capabilities evolve.

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
* freshening informational configuration cannot change the products produced by an existing realization;
* repeated freshening is stable and idempotent where appropriate.

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

Do not encode variant, physical size, feature selection, stage identity, or another configuration dimension into the published filename beyond the realization name.

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
* Shape setup can invoke or reuse normal Artwork creation;
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
* verify that variants remain reusable model-owned parameter presets rather than becoming an additional artifact identity dimension;
* verify that both local and cross-artifact dependencies use the same logical product-reference mechanisms;
* verify that cleaning followed by rebuilding reproduces derived products from persistent configuration and required source inputs;
* verify that any permanent invariants discovered during implementation have been incorporated into `ARCHITECTURE.md` or the appropriate model `DEFINITION.md`.

Once permanent specifications and HEAD are aligned, remove the completed `CHANGEPLAN.md` content rather than treating this temporary plan as an additional permanent specification.

