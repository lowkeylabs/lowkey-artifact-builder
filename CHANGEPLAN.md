# Change Plan — Artwork Color Availability and Matching

This change plan introduces explicit filament-library configuration and
Artwork color-match analysis.

The system already distinguishes the complete color catalog from
`printer_colors`. This change adds a third availability scope:

```text
color catalog
    all known physical filament colors

library_colors
    colors physically available for installation

printer_colors
    colors currently installed, intended, or otherwise available
    to the printer for a build
```

Artwork color requirements can then be compared independently against:

```text
printer colors
library colors
catalog colors
```

The resulting analysis should allow a user to determine:

* how closely the currently configured printer colors match prepared Artwork;
* whether colors already present in the local filament library provide better
  matches;
* whether colors from the complete physical filament catalog provide better
  matches;
* which filament changes or purchases would improve reproduction of the
  prepared Artwork.

Color analysis is diagnostic. It does not implicitly modify configuration.

The implementation should preserve existing architectural boundaries:

* configuration owns configuration resolution and validation;
* generic color infrastructure owns model-independent color mathematics;
* Artwork owns interpretation of prepared Artwork color requirements;
* the CLI owns presentation;
* the build engine does not acquire Artwork-specific color-selection policy.

# Phase 1 — Specify and Configure Filament Availability

Update the permanent specifications to define the distinction between:

```text
color catalog
library_colors
printer_colors
```

Add the system parameter:

```text
library_colors
```

`library_colors` identifies catalog colors physically owned and available for
installation on a printer.

Both:

```text
library_colors
printer_colors
```

must contain color identities defined by the color catalog.

Do not require:

```text
printer_colors ⊆ library_colors
```

The two parameters represent independent current-state facts.

Synthetic test colors remain available for automated tests but should not be
treated as physical filament candidates when performing catalog-wide physical
filament recommendations.

Tests should establish that:

* `library_colors` participates in ordinary configuration resolution;
* system configuration may provide a default `library_colors`;
* workspace configuration may override `library_colors`;
* artifact configuration may override `library_colors`;
* every resolved `library_colors` entry must reference a known catalog color
  when execution requires library color analysis;
* every resolved `printer_colors` entry must reference a known catalog color
  when execution requires printer color analysis;
* duplicate or otherwise invalid availability configuration is handled
  consistently with the established configuration-validation contract;
* validation remains execution-scoped;
* generic configuration infrastructure contains no Artwork-specific matching
  rules.

Phase 1 is complete when filament availability is explicitly represented and
validated without introducing Artwork-specific behavior into generic
configuration infrastructure.

# Phase 2 — Generic Color Matching

Extend the existing generic color infrastructure with the smallest
model-independent operation required to find the closest catalog color to a
requested RGB color.

The operation should accept:

```text
requested color
candidate colors
```

and return sufficient semantic information to identify:

```text
requested color
matched candidate color
perceptual distance
```

Matching should use the existing perceptual color-distance semantics rather
than introduce a second independent color-distance implementation.

The operation must support arbitrary candidate-set sizes. It must not require
one-to-one assignment or equal-sized source and destination palettes.

Tests should establish that:

* an exact RGB match selects the corresponding candidate;
* the perceptually nearest candidate is selected when no exact match exists;
* matching can operate against one candidate;
* matching can operate against many candidates;
* the returned result preserves the semantic identity of the selected catalog
  color;
* the returned result includes the perceptual distance;
* candidate ordering provides deterministic behavior for equal-distance ties;
* an empty candidate set is rejected explicitly;
* generic matching contains no Artwork, printer, library, filament inventory,
  CLI, or build-engine policy.

Existing one-to-one color-assignment behavior should remain unchanged unless
the new generic primitive provides a clean internal implementation for it.

Phase 2 is complete when any requested RGB color can be deterministically
matched against an arbitrary catalog-derived candidate set.

# Phase 3 — Artwork Color Match Analysis

Define Artwork color-match analysis over prepared Artwork.

The analysis must use the semantic colors represented by prepared Artwork
rather than independently reinterpreting the original source image.

For every prepared Artwork color, determine its closest match independently
against:

```text
printer_colors
library_colors
physical color catalog
```

Each match should retain at least:

```text
Artwork semantic color identity
Artwork RGB
matched catalog color identity
matched catalog RGB
perceptual distance
```

Catalog-wide matching must consider physical filament entries and exclude
synthetic colors reserved for tests.

Artwork analysis must not:

* modify `artwork_colors`;
* modify `printer_colors`;
* modify `library_colors`;
* install filament;
* alter persistent products merely because analysis was requested.

Tests should establish that:

* prepared Artwork semantic colors are the source of analysis;
* every Artwork color receives an independent printer match;
* every Artwork color receives an independent library match;
* every Artwork color receives an independent physical-catalog match;
* printer matching considers only `printer_colors`;
* library matching considers only `library_colors`;
* catalog matching considers the physical filament catalog;
* synthetic test colors can support isolated tests without becoming real
  catalog recommendation candidates;
* semantic color identities are preserved in analysis results;
* perceptual distances are exposed;
* analysis does not mutate resolved configuration;
* analysis remains Artwork-owned rather than becoming build-engine policy.

Prefer deriving analysis from an existing persistent prepared or registered
Artwork product when that product already contains sufficient semantic color
information. Do not introduce a new persistent stage or product unless an
independent persistence, dependency, inspection, or resumption boundary is
actually required.

Phase 3 is complete when prepared Artwork can produce structured three-scope
color-match analysis independently of CLI presentation.

# Phase 4 — Standard CLI Color Report

Expose Artwork color-match analysis through the standard CLI presentation.

Once the required Artwork preparation products exist, the user should be able
to inspect a report showing, for every Artwork color:

```text
Artwork
Printer match
Library match
Catalog match
```

Each match should expose enough information to distinguish the selected color
and assess match quality, including perceptual distance.

Conceptually:

```text
Artwork Color Matches

Artwork          Printer              Library              Catalog
---------------------------------------------------------------------------
red              fire-engine-red      fire-engine-red      fire-engine-red
green            brown                pine-green           pine-green
orange           gold                 apricot              apricot
blue             black                blue                 rgb-blue
white            white                white                white
```

The exact presentation may evolve, but presentation must remain separate from
the structured analysis semantics.

The CLI must not reproduce color matching algorithms.

Tests should establish that:

* the CLI can request/report Artwork color analysis;
* the report identifies all prepared Artwork colors;
* printer, library, and catalog matches are distinguishable;
* match distances can be displayed;
* report ordering is deterministic;
* CLI presentation consumes structured analysis rather than recomputing it;
* requesting a report does not modify configuration;
* requesting a report does not require standalone Artwork extrusion or
  packaging when prepared/registered Artwork is already sufficient;
* existing build behavior remains unchanged.

Phase 4 is complete when color-match information is available as a normal,
read-only CLI diagnostic for prepared Artwork.

# Phase 5 — Five-Tool Printer Palette Recommendation

Build palette recommendation on top of the color-analysis infrastructure.

For the current five-tool printer use case, recommend:

```text
white
+
four additional colors
```

where `white` is mandatory.

Produce recommendations independently for:

```text
current printer colors
library colors
physical color catalog
```

The optimization must evaluate the palette as a whole rather than merely
selecting the independently nearest filament for each Artwork color.

A candidate palette should be scored according to how well the complete
prepared Artwork can be represented by that palette using the established
perceptual color-distance semantics.

The result should provide sufficient structured information to compare:

```text
current printer capability
best palette available from owned filament
best palette available from the physical catalog
```

Tests should establish that:

* the requested palette size is honored;
* mandatory colors are always included;
* `white` can be supplied as the mandatory color for the five-tool use case;
* recommendations contain no duplicate color identities;
* library recommendations select only from `library_colors`;
* catalog recommendations select only from physical catalog entries;
* synthetic test colors do not leak into physical recommendations;
* the globally better palette is preferred over a palette produced solely by
  independent nearest-color choices;
* palette scoring is deterministic;
* recommendation results expose their aggregate match score;
* recommendation does not mutate `printer_colors`, `library_colors`, or
  `artwork_colors`;
* recommendation logic remains outside the CLI and build engine.

The CLI report may then summarize, conceptually:

```text
Current printer:
    white
    black
    brown
    gold
    silver
    score: ...

Recommended from library:
    white
    ...
    score: ...

Recommended from catalog:
    white
    ...
    score: ...
```

This phase should not automatically rewrite configuration. Any future operation
that applies a recommendation to `printer_colors` should be planned separately
as an explicit configuration mutation.

Phase 5 is complete when the system can recommend and compare complete
five-color printer palettes while keeping recommendation distinct from
configuration mutation.

# Completion Criteria

This change plan is complete when:

* the system distinguishes catalog, library, and printer color availability;
* `library_colors` and `printer_colors` resolve and validate as catalog
  references;
* generic color infrastructure can perform nearest-color matching;
* prepared Artwork can be analyzed against printer, library, and catalog
  colors;
* the CLI provides a standard read-only Artwork color-match report;
* five-tool palette recommendations can be produced with mandatory `white`;
* recommendations can distinguish currently installed, locally available, and
  purchasable filament options;
* color analysis and recommendation do not implicitly mutate configuration;
* generic configuration, planning, and build-engine infrastructure remain free
  of Artwork-specific color policy;
* permanent specifications and implementation agree.

After these criteria are satisfied and the repository conforms to the updated
permanent specifications, this CHANGEPLAN may be removed.
