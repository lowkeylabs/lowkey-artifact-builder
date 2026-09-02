# Change Plan — Artwork Color Model Realignment

This change plan realigns the Artwork implementation and CLI with the
permanent Artwork model specification:

```text
src/lowkey_artifact_builder/model/models/artwork/DEFINITION.md
```

# Status

```text
Phase 1 - Started
Phase 2 - Not started
Phase 3 - Not started
Phase 4 - Not started
Phase 5 - Not started
Phase 6 - Not started
Phase 7 - Not started
Phase 8 - Not started
Phase 9 - Not started
```

# Target

This change plan realigns the Artwork implementation and CLI with the
permanent Artwork model specification:

```text
src/lowkey_artifact_builder/model/models/artwork/DEFINITION.md
```

The permanent specification is authoritative.

The current implementation contains substantial functionality developed
under the previous Artwork color model. That functionality should be
preserved where it remains consistent with the permanent specification
and replaced where its semantics conflict.

The target Artwork color pipeline is:

```text
source raster
    │
    ├── derive Artwork envelope
    │
    ▼
prepared full-color Artwork
    │
    ▼
multicolor trace
colors = artifact_color_count
    │
    ▼
artifact_colors
    │
    ▼
printer_assignments
    │
    ▼
registered raster layers
    │
    ▼
registered vector layers
    │
    ▼
extrude
    │
    ▼
package
```

Alternative physical realizations are calculated independently as:

```text
artifact_colors
    ├── printer_assignments
    ├── library_assignments
    └── catalog_assignments
```

Artwork interpretation and physical filament assignment are distinct
responsibilities.

The implementation must preserve existing architectural boundaries:

* configuration owns configuration resolution;
* model-owned validation owns Artwork configuration semantics;
* generic color infrastructure owns model-independent color mathematics;
* Artwork owns Artifact-color interpretation and physical-color assignment;
* the CLI owns presentation;
* the planner and build engine remain free of Artwork-specific color policy.

Development remains test-driven. Each implementation slice begins with tests
that express the relevant permanent specification invariants.

# Phase 1 — Realign Artwork Configuration Semantics

Replace the obsolete configured Artwork-palette model with the permanent
`artifact_color_count` model.

Remove Artwork configuration concepts that no longer exist:

```text
artwork_colors
artwork_fill_color
```

Introduce:

```text
artifact_color_count
```

`artifact_color_count` is an Artwork configuration parameter.

Unless explicitly configured, it is derived from:

```text
len(printer_colors)
```

An explicit value may be smaller than the number of configured printer colors.

For example:

```text
printer_colors = 5 colors
artifact_color_count = 3
```

means that multicolor tracing discovers three Artifact colors and two printer
colors may remain unused.

`artifact_colors` are not configuration. They are derived product information
created by multicolor tracing.

Remove obsolete Artwork derivations for:

```text
artwork_colors
artwork_fill_color
```

and replace them with the smallest derivation necessary for the default
`artifact_color_count`.

Remove validation rules whose only purpose was to enforce
`artwork_fill_color` membership in `artwork_colors`.

Add model-owned validation for `artifact_color_count` where execution requires
it.

Tests should establish that:

* `artifact_color_count` may be explicitly configured;
* an explicit `artifact_color_count` participates in ordinary configuration
  precedence;
* the default `artifact_color_count` equals the number of configured
  `printer_colors`;
* resolving the default does not create `artifact_colors`;
* `artifact_color_count` must be a positive integer when required by planned
  execution;
* `artifact_color_count` may be smaller than the number of printer colors;
* obsolete `artwork_colors` derivation is no longer used;
* obsolete `artwork_fill_color` derivation is no longer used;
* Artwork validation no longer requires an Artwork fill color;
* `printer_colors` and `library_colors` continue to validate as catalog
  references when the corresponding execution requires them;
* validation remains execution-scoped;
* generic configuration infrastructure contains no Artwork-specific color
  rules.

Update Artwork stage declarations so parameters reflect the permanent model.

In particular:

```text
prepare
    artifact_color_count
    artwork_envelope_mode as otherwise required by existing configuration

raster
    printer_colors
    artwork_pixels
    artwork_min_island_area
    artwork_island_connectivity

vector
    no physical sizing parameters

extrude
    artwork_size
    artwork_raise
```

Parameter declarations should describe actual stage dependencies rather than
retain obsolete `artwork_colors` or `artwork_fill_color` dependencies.

Phase 1 is complete when configuration resolution, model validation, and
Artwork stage declarations express the new permanent parameter model.

# Phase 2 — Preserve Source Colors Through Prepare

Realign Artwork Prepare with the permanent source-driven color-discovery
semantics.

Prepare must continue to derive and preserve the Artwork envelope.

Existing envelope behavior, including:

```text
alpha
shrink-wrap
```

and the established shrink-wrap classification and diagnostics remain part of
the Artwork model and must not be discarded as part of the color refactor.

Prepare must stop reducing source Artwork to configured physical filament
colors before multicolor tracing.

Remove from the Prepare execution path the old behavior that:

* resolves `artwork_colors`;
* resolves `artwork_fill_color`;
* fills the Artwork according to a configured physical color;
* quantizes the normalized source to exact configured filament RGB values;
* performs cleanup whose purpose is repairing artifacts created by that
  physical-palette quantization;
* determines Inkscape trace cardinality from the physical palette size.

Prepare instead supplies source color information belonging to the Artwork to
Inkscape and requests:

```text
colors = artifact_color_count
```

Pixels outside the derived envelope remain outside the Artwork.

The traced regions collectively represent the Artwork within the envelope.

Tests should establish that:

* Prepare requests exactly `artifact_color_count` colors from multicolor
  tracing;
* explicit `artifact_color_count = 3` requests three colors even when five
  printer colors are configured;
* the default color count still follows printer capacity;
* changing printer RGB values without changing `artifact_color_count` does not
  quantize or otherwise rewrite source RGB values before tracing;
* Prepare does not require `artwork_colors`;
* Prepare does not require `artwork_fill_color`;
* Prepare does not pre-quantize the source to `printer_colors`;
* Prepare does not pre-quantize the source to `library_colors`;
* Prepare does not pre-quantize the source to catalog colors;
* source color distinctions survive normalization until Inkscape color
  discovery;
* existing alpha-envelope behavior remains valid;
* existing shrink-wrap envelope behavior remains valid;
* existing complex-background warning behavior remains valid;
* existing concavity and transparent-crop envelope regressions remain valid;
* trace output remains clipped to the derived Artwork envelope.

Tests that currently encode physical-palette quantization as required Prepare
behavior should be replaced rather than preserved as compatibility behavior.

Phase 2 is complete when Prepare discovers source colors through Inkscape
rather than imposing physical filament colors before tracing.

# Phase 3 — Establish Artifact Colors as Persistent Product Information

Make the colors assigned by multicolor tracing explicit Artifact-color
information.

For each traced color region, preserve:

```text
Artifact color-region identity
Artifact RGB
```

The Artifact RGB is the RGB representation assigned by multicolor tracing.

It is not a printer, library, or catalog RGB merely because a nearby physical
color exists.

Artifact-color identity must be stable enough for downstream manifests to
associate one region with:

```text
Artifact color
printer assignment
geometry product
```

Determine the smallest manifest evolution that preserves this information
through registered Artwork.

Avoid introducing a new manufacturing stage solely for Artifact-color
metadata when an existing persistent manifest provides the necessary
persistence and dependency boundary.

Tests should establish that:

* the number of Artifact colors equals the traced color-region count;
* traced RGB values become `artifact_colors`;
* Artifact RGB values need not exist in the physical color catalog;
* Artifact colors remain distinguishable from assigned printer colors;
* Artifact color-region identity remains stable through Raster and Vector;
* registered Artwork preserves Artifact RGB information;
* registered Artwork preserves the printer assignment separately from
  Artifact RGB information;
* a persistent registered Artwork product contains enough information for
  later library and catalog assignment without rereading or reinterpreting the
  original source image.

Phase 3 is complete when registered Artwork persistently distinguishes
source-derived Artifact colors from physical printer assignments.

# Phase 4 — Generic Optimal One-to-One Color Assignment

Retain and, where necessary, adapt the existing generic color-assignment
infrastructure to support the permanent Artwork assignment semantics.

The generic operation accepts:

```text
measured colors
candidate physical colors
```

and selects a one-to-one assignment minimizing aggregate perceptual distance.

The operation must support:

```text
number of candidates >= number of measured colors
```

It must not require equal-sized source and candidate palettes.

Each measured color receives one distinct candidate color.

The result must preserve sufficient information for Artwork to record:

```text
measured color identity
measured RGB
selected physical color identity
selected physical RGB
individual perceptual distance
```

The complete assignment exposes:

```text
aggregate perceptual distance
```

The established generic perceptual color-distance implementation remains
authoritative.

Tests should establish that:

* exact RGB assignments have zero distance;
* a single measured color can be assigned from multiple candidates;
* multiple measured colors receive distinct candidate identities;
* a candidate set larger than the measured set selects only the globally best
  subset;
* the globally optimal one-to-one assignment is selected rather than
  independent nearest-neighbor matches;
* individual perceptual distances are retained;
* aggregate distance is the sum of individual assignment distances;
* assignment is deterministic;
* ordered candidate input deterministically resolves equal-score alternatives;
* insufficient distinct candidates are rejected explicitly;
* generic assignment contains no Artwork, printer, library, catalog,
  filament-inventory, CLI, or build-engine policy.

Existing generic primitives that remain useful should be reused rather than
duplicated.

Obsolete generic functionality need not be removed merely because Artwork no
longer uses it, provided it remains valid generic infrastructure and has
independent tests.

Phase 4 is complete when generic infrastructure can optimally assign N
measured colors to N distinct colors selected from M candidates where M >= N.

# Phase 5 — Establish Printer Assignments During Rasterization

Realign Raster with the permanent manufacturing semantics.

Raster consumes the Artifact colors measured from the Prepare trace.

Raster calculates:

```text
printer_assignments
```

using the generic one-to-one assignment operation.

Candidates come only from:

```text
printer_colors
```

The number of assignments equals the number of Artifact colors.

If more printer colors are available than Artifact colors, Raster selects the
best subset and leaves the remaining printer colors unused.

Raster must no longer require:

```text
number of traced colors == len(printer_colors)
```

or an equivalent equality through obsolete `artwork_colors`.

Execution requiring Raster must reject a configuration that cannot provide
enough distinct printer colors to assign every Artifact color.

Raster output must preserve both sides of the distinction:

```text
Artifact identity + Artifact RGB
printer identity + printer RGB
individual distance
```

The complete printer assignment must also make aggregate assignment distance
available to appropriate consumers.

Raster geometry remains:

* registered;
* mutually exclusive;
* complete over retained Artwork within the envelope;
* independent of physical `artwork_size`.

Island cleanup must not create unassigned retained Artwork merely by deleting
a small color island. Tests should characterize the required reassignment or
coverage behavior before production changes are made in this area.

Tests should establish that:

* three traced Artifact colors can be assigned using five printer candidates;
* exactly three distinct printer colors are selected in that case;
* the selected three minimize aggregate perceptual distance;
* two Artifact colors cannot silently receive the same printer identity;
* insufficient printer colors fail explicitly;
* Artifact RGB and printer RGB remain separately represented;
* individual assignment distances are persisted;
* aggregate printer-assignment distance is available;
* raster regions remain mutually exclusive;
* retained Artwork is completely assigned;
* Raster remains independent of `artwork_size`.

Phase 5 is complete when Raster establishes the physical printer realization
without changing the Artifact colors discovered by Prepare.

# Phase 6 — Preserve Artifact and Printer Color Semantics Downstream

Realign Vector, Extrude, Package, and registered Artwork consumers with the
new manifest semantics.

Vector must preserve:

```text
Artifact color-region identity
Artifact RGB
assigned printer identity
assigned printer RGB
```

while converting registered raster geometry into registered vector geometry.

Vector's binary-mask tracing remains a geometry operation. It must not
rediscover or reinterpret Artifact colors.

Extrude must preserve the printer semantic identity assigned to every
registered Artwork region while introducing:

```text
artwork_size
artwork_raise
```

Package must preserve those printer semantic identities and RGB
representations in the multicomponent 3MF.

Registered Artwork consumers such as Shape must continue to receive registered
geometry without requiring standalone Artwork extrusion or packaging.

Tests should establish that:

* Vector preserves Artifact RGB separately from printer RGB;
* Vector preserves Artifact color-region identity;
* Vector preserves printer semantic assignment;
* Vector's binary tracing does not perform color discovery;
* Extrude preserves printer assignment;
* Package preserves printer assignment into the 3MF;
* registration remains unchanged;
* `registered_extent` remains dimensionless;
* another model can consume registered Artwork without Artwork extrusion or
  packaging;
* existing Shape incorporation behavior remains valid.

Phase 6 is complete when Artifact colors and physical printer assignments
remain semantically distinct and correctly preserved throughout downstream
manufacturing.

# Phase 7 — Three-Scope Artwork Assignment Analysis

Replace the old independent color-match and fixed-palette recommendation
semantics with the permanent three-scope assignment model.

Artwork analysis calculates:

```text
printer_assignments
library_assignments
catalog_assignments
```

from persistent Artifact-color information.

`printer_assignments` represent the current manufacturing realization.

`library_assignments` select the best distinct physical colors from:

```text
library_colors
```

`catalog_assignments` select the best distinct physical colors from the
complete physical catalog.

Catalog-wide assignment excludes entries explicitly identified as synthetic
test colors.

Each scope produces:

```text
one assignment per Artifact color
individual perceptual distances
aggregate perceptual distance
```

The number of selected physical colors is:

```text
len(artifact_colors)
```

not printer capacity and not a fixed value of five.

Remove Artwork-specific behavior based on:

```text
independent nearest-color matches
fixed-size five-tool recommendations
mandatory white
artwork_fill_color
```

Tests should establish that:

* analysis uses persistent Artifact RGB values rather than assigned printer
  RGB values as its measured colors;
* printer analysis reproduces the optimal current printer assignment;
* library assignment considers only `library_colors`;
* catalog assignment considers only physical catalog colors;
* all three scopes perform globally optimal one-to-one assignment;
* all three scopes select exactly one distinct physical color per Artifact
  color;
* individual distances are exposed;
* aggregate distances are exposed;
* a three-color Artifact produces three-color library and catalog assignments
  even on a five-tool printer;
* synthetic catalog colors do not leak into physical catalog assignment;
* analysis does not modify persistent Artwork products;
* analysis does not modify `printer_colors` or `library_colors`;
* analysis does not require standalone Artwork extrusion or packaging;
* analysis remains Artwork-owned.

Phase 7 is complete when Artwork can produce structured printer, library, and
catalog assignments conforming to the permanent specification.

# Phase 8 — Realign `artifact colors` CLI

Replace the existing color-match plus five-tool recommendation presentation
with presentation of the three assignment scopes.

The CLI consumes structured Artwork analysis. It does not calculate color
distances or assignments itself.

The report should expose enough information to answer:

```text
Which configured printer colors best reproduce the Artifact colors?

Which colors already in the filament library would reproduce them better?

Which physical catalog colors would reproduce them best?

Where are the largest individual reproduction errors?

How much better is one complete assignment than another?
```

A conceptual report is:

```text
Artifact       Printer             Library             Catalog
RGB            Color   Distance    Color   Distance     Color   Distance
-----------------------------------------------------------------------
#C90011        red       3.20       red       3.20       red       1.10
#020202        black     0.80       black     0.80       black     0.40
#FAFAF9        white     2.10       white     1.50       white     0.60

Scope      Selected physical colors       Aggregate distance
-------------------------------------------------------------
Printer    red, black, white               6.10
Library    red, black, white               5.50
Catalog    red, black, white               2.10
```

Exact presentation may evolve independently of the structured analysis
contract.

Remove CLI dependencies on:

```text
artwork_fill_color
five-tool recommendation
mandatory white
```

Tests should establish that:

* `artifact colors <artifact>` reports all Artifact colors;
* Artifact RGB values shown by the CLI are source-derived traced RGB values;
* printer, library, and catalog assignments are distinguishable;
* individual distances are displayed;
* aggregate distances are displayed;
* selected physical color identities are displayed;
* a three-color Artifact reports three assignments per scope;
* CLI ordering is deterministic;
* the CLI consumes structured Artwork analysis rather than recomputing it;
* requesting color analysis does not modify configuration;
* requesting color analysis does not require standalone Artwork extrusion or
  packaging when registered Artwork already exists;
* existing targeted-product planning semantics remain intact.

Phase 8 is complete when `artifact colors` accurately presents the permanent
Artwork assignment model.

# Phase 9 — Remove Obsolete Artwork Color Model and Complete Conformance Audit

After the replacement semantics are working, remove obsolete Artwork-specific
implementation and tests whose only purpose was the superseded color model.

Candidates include Artwork-specific concepts and paths involving:

```text
artwork_colors
artwork_fill_color
five-tool Artwork palette recommendation
mandatory Artwork white
Prepare physical-palette quantization
Prepare cleanup required solely because of physical-palette quantization
independent Artwork nearest-color analysis
```

Do not remove generic color operations merely because Artwork no longer uses
them if they remain coherent model-independent functionality.

Search the repository for stale Artwork references in:

```text
source
tests
fixtures
CLI help
docstrings
configuration
model stage declarations
acceptance tests
```

Run conformance tests that exercise at least:

```text
limited-palette logo
full printer-capacity Artwork
alpha-envelope Artwork
shrink-wrap Artwork
registered Artwork consumed by Shape
standalone Artwork 3MF
artifact colors diagnostic
```

Tests should establish that:

* no executable Artwork path requires `artwork_colors`;
* no executable Artwork path requires `artwork_fill_color`;
* no Artwork path assumes five Artifact colors;
* no Artwork path assumes all configured printer colors must be used;
* no Prepare path quantizes source colors to physical filament colors before
  color discovery;
* Artifact RGB values remain distinct from physical assignment RGB values;
* printer assignments drive manufacturing identity;
* library and catalog assignments remain diagnostic;
* envelope semantics remain conformant;
* registered Artwork reuse remains conformant;
* standalone Artwork packaging remains conformant;
* generic configuration, planner, and engine code contain no Artwork-specific
  color policy;
* all permanent Artwork invariants are represented by implementation and
  focused tests.

Run the normal repository quality gates after the focused tests:

```text
pytest
pyright
ruff
```

including the established slow/acceptance suite where appropriate.

Phase 9 is complete when HEAD and Artwork `DEFINITION.md` agree and no obsolete
Artwork color semantics remain in executable code.

# Completion Criteria

This change plan is complete when:

* `artifact_color_count` is the Artwork configuration input controlling
  multicolor trace cardinality;
* its default is derived from the number of configured `printer_colors`;
* `artifact_colors` are source-derived RGB values measured from multicolor
  tracing;
* Artifact colors are not pre-quantized to physical filament colors;
* Artwork has no `artwork_fill_color` concept;
* Artwork has no configured `artwork_colors` semantic palette;
* `printer_assignments` optimally assign distinct configured printer colors to
  Artifact colors;
* `library_assignments` optimally assign distinct owned filament colors to
  Artifact colors;
* `catalog_assignments` optimally assign distinct physical catalog colors to
  Artifact colors;
* all assignment scopes expose individual and aggregate perceptual distances;
* assignment cardinality follows the number of Artifact colors rather than
  printer capacity;
* unused printer colors may remain unused;
* registered Artwork persistently distinguishes Artifact RGB from assigned
  printer RGB;
* downstream manufacturing preserves printer semantic assignments;
* the CLI reports the three assignment scopes without recomputing them;
* envelope derivation and registered geometry behavior remain conformant;
* another model can consume registered Artwork without standalone Artwork
  extrusion or packaging;
* color analysis and alternative assignment do not implicitly mutate
  configuration;
* generic configuration, planning, and build-engine infrastructure remain
  free of Artwork-specific color policy;
* permanent specifications, implementation, and tests agree.

After these criteria are satisfied and the repository conforms to the
permanent specifications, this `CHANGEPLAN.md` may be removed.
