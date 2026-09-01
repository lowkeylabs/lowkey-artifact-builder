# CHANGEPLAN

This change plan introduces configurable Artwork envelope derivation for
source images whose visible subject cannot be identified correctly from
alpha alone.

The immediate motivating case is opaque-background artwork where the
current alpha-derived envelope treats the entire source raster as the
Artwork envelope.

This work is intentionally limited to Artwork preparation and the
semantics of `envelope.svg`.

`ARCHITECTURE.md` remains the permanent system specification.

`src/lowkey_artifact_builder/model/models/artwork/DEFINITION.md` remains
the permanent Artwork-model specification.

This file is temporary implementation guidance and should be deleted
when the repository again conforms to the permanent specifications.


# Goal

Permit the Artwork model to select how its physical envelope is derived
from source artwork.

The existing alpha-based behavior remains the default.

A new shrink-wrap mode derives a conservative outer envelope around
meaningful artwork even when the source background is opaque.

The resulting envelope continues to be represented by the existing
`envelope.svg` product.

No downstream Artwork stage or product contract changes.


# Intended Model Semantics

Introduce the Artwork parameter:

    artwork_envelope_mode

Initially supported values:

    alpha
    shrink-wrap

`alpha` preserves existing behavior. Meaningful source foreground is
identified from source alpha before the existing envelope-construction
operations are applied.

`shrink-wrap` distinguishes exterior background from enclosed artwork
and derives a conservative non-concave outer envelope around the
remaining artwork.

Shrink-wrap classification must be based on exterior/background
relationship rather than RGB equality alone. Interior artwork may
therefore contain colors that also occur in the exterior background.

The default is:

    artwork_envelope_mode = "alpha"

Additional modes or user-configurable shrink-wrap tuning parameters are
out of scope until concrete source examples demonstrate a need for
them.


# Permanent Specification Update

Before considering implementation complete, update the Artwork
`DEFINITION.md` to define:

* `artwork_envelope_mode`;
* the `alpha` semantics;
* the `shrink-wrap` semantics;
* `alpha` as the default;
* the invariant that matching an exterior background color does not by
  itself exclude an enclosed region from the Artwork envelope.

The permanent specification should define observable model semantics,
not the particular image-processing algorithm used to implement them.

No change to `ARCHITECTURE.md` is currently expected.


# Phase 1 — Characterize Envelope-Mode Semantics

Add focused tests to:

    tests/model/artwork/test_prepare.py

Tests should establish that:

* alpha mode preserves the existing alpha-derived behavior;
* alpha mode remains the default;
* shrink-wrap mode excludes an opaque exterior background;
* shrink-wrap preserves enclosed artwork even when its color matches
  the exterior background;
* shrink-wrap bridges exterior-connected concavities when producing
  the conservative outer envelope;
* an unsupported envelope mode is rejected.

Prefer synthetic raster fixtures whose expected geometry is obvious
from the test itself.

Tests should characterize observable semantics rather than requiring a
specific implementation algorithm.

Run the focused prepare tests and confirm the new shrink-wrap tests are
RED for the intended missing capability before adding production code.


# Phase 2 — Introduce Artwork Envelope-Mode Configuration

Add `artwork_envelope_mode` to the Artwork model parameters with the
default:

    artwork_envelope_mode = "alpha"

Resolve this parameter through the existing model/configuration
mechanisms.

Do not add Artwork-specific semantics to generic configuration,
planning, or execution infrastructure.

Validation of supported Artwork envelope modes remains owned by the
Artwork model.

Existing artifacts that do not configure `artwork_envelope_mode` must
continue to receive the current alpha-based behavior.


# Phase 3 — Implement Envelope Strategy Selection

Refactor Artwork preparation only as much as necessary to introduce a
single envelope-derivation boundary responsible for selecting the
configured strategy.

Conceptually:

    source image
        |
        +-- alpha ------+
        |               |
        +-- shrink-wrap +--> Artwork envelope

The existing alpha implementation should be reused rather than
rewritten unnecessarily.

The resulting envelope must continue through the existing prepare-stage
processing and be written to the existing `envelope.svg` product.

Do not change:

* prepare-stage inputs;
* prepare-stage outputs;
* persistent product names;
* raster-stage behavior;
* vector-stage behavior;
* extrusion behavior;
* packaging behavior;
* generic engine behavior.


# Phase 4 — Implement Shrink-Wrap Envelope Derivation

Implement the smallest deterministic image-processing operation that
satisfies the shrink-wrap tests.

The implementation should:

* infer exterior background from the source boundary;
* distinguish exterior-connected background from enclosed regions;
* preserve enclosed regions even when their color matches the exterior;
* produce a conservative outer envelope rather than following deep
  exterior concavities;
* remain deterministic for identical source pixels and configuration.

Prefer existing project dependencies and straightforward binary-image
operations.

Do not expose implementation-specific thresholds or tuning parameters
as model configuration unless tests from real artwork demonstrate that
they are necessary.

Do not add passive/aggressive variants during this phase.


# Phase 5 — Integration and Regression

Add or extend prepare-stage integration tests to establish that the
configured envelope mode is actually used by `execute()` and affects
the generated `envelope.svg`.

Verify that:

* existing alpha-mode prepare tests remain green;
* existing Artwork pipeline tests remain green;
* shrink-wrap changes only envelope derivation and the prepare products
  derived from that envelope;
* no downstream stage requires awareness of
  `artwork_envelope_mode`;
* existing artifacts without the new parameter continue to build.

Run:

    uv run pytest tests/model/artwork/test_prepare.py
    uv run pytest tests/model/artwork
    make check
    uv run pytest


# Phase 6 — Real-Image Acceptance Check

Exercise shrink-wrap mode against at least one representative opaque
background source image that demonstrates the motivating failure.

Inspect the resulting:

    envelope.svg

Confirm that:

* the source-image rectangle is no longer incorrectly treated as the
  Artwork envelope;
* the intended subject is enclosed;
* meaningful projections of the subject remain enclosed;
* unwanted exterior concavities are bridged appropriately;
* obvious enclosed regions are not removed because they share the
  exterior background color.

This check is evidence for the selected algorithm and its defaults. It
should not replace deterministic automated tests.


# Explicit Non-Goals

This change does not introduce:

* changes to Artwork rasterization;
* changes to Artwork vectorization;
* changes to Artwork extrusion;
* changes to Artwork packaging;
* new persistent products;
* changes to stage dependency declarations;
* changes to generic planning or execution;
* generic image-processing configuration;
* user-configurable shrink-wrap thresholds;
* passive/aggressive shrink-wrap modes;
* arbitrary background-removal or subject-segmentation features;
* AI-based image segmentation.

If implementation appears to require changes outside Artwork
preparation or Artwork-owned configuration/validation, stop and
reevaluate the design before expanding scope.


# Completion Criteria

This change is complete when:

* `artwork_envelope_mode` is defined by the Artwork model;
* `alpha` remains the default and preserves existing behavior;
* `shrink-wrap` correctly handles the characterized opaque-background
  cases;
* `prepare.execute()` uses the configured mode;
* `envelope.svg` remains the existing persistent envelope product;
* downstream Artwork stages require no envelope-mode knowledge;
* Artwork `DEFINITION.md` describes the new permanent semantics;
* focused, model, static-analysis, and full test suites pass;
* representative real artwork demonstrates the intended improvement;
* no unrelated architectural or pipeline changes have been introduced.

After these conditions are satisfied, delete `CHANGEPLAN.md`.
