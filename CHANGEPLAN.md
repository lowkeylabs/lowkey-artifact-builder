# CHANGEPLAN

## Purpose

Continue refining `lowkey-artifact-builder` around the actual
manufacturing value chain from the current repository HEAD.

The operator's ordinary goal is:

> Move customer artwork to a **correct, printable 3MF** with the fewest
> necessary decisions, actions, and computations.

The primary value chain remains:

``` text
customer artwork
      ↓
artifact create
      ↓
managed Artifact
      ↓
artifact build
      ↓
correct printable 3MF
      ↓
slicer / share / upload / print
```

`create` and `build` define the ordinary production path.

Other commands support that path when the operator needs discovery,
explanation, customization, correction, color selection, or maintenance:

``` text
list
show
config
colors
clean
```

These commands are helpers or exception paths. They must not become
mandatory ceremony before routine manufacturing.

This CHANGEPLAN contains **only remaining work**. Completed phases are
removed rather than retained as historical checklists. Current HEAD
already establishes the manufacturing and recovery behavior summarized
below; those behaviors are constraints to preserve, not work to repeat.

This plan does not redefine Artifact, Variant, Realization, Product,
configuration, build planning, Product state, Stage ownership, Model
semantics, or color semantics. Those remain owned by `ARCHITECTURE.md`
and the applicable Model `DEFINITION.md`. If an investigation exposes a
genuine mismatch with those permanent specifications, resolve that
mismatch explicitly before encoding new behavior in tests.

------------------------------------------------------------------------

# Development Method

This plan is subordinate to:

``` text
ARCHITECTURE.md
src/lowkey_artifact_builder/model/models/<model>/DEFINITION.md
src/lowkey_artifact_builder/cli/README.md
prompts/NEW_THREAD.md
prompts/TEST_DRIVEN_DEVELOPMENT.md
```

`ARCHITECTURE.md` and Model definitions are normative. Repository HEAD
defines the current implementation. This file is a temporary plan for
remaining work.

Before each implementation slice:

1.  review the relevant permanent specifications and current HEAD;
2.  credit behavior HEAD already satisfies;
3.  reproduce or otherwise establish the next unmet workflow or
    correctness requirement;
4.  distinguish observed facts from suspected causes;
5.  resolve semantic or architectural questions before changing
    behavior;
6.  use TDD where the change introduces or corrects a meaningful
    behavioral boundary;
7.  avoid one-test-per-line ceremony when an already-protected semantic
    boundary merely needs an obvious implementation correction;
8.  implement the smallest correct behavior;
9.  run focused tests;
10. run the complete applicable quality suite;
11. commit and reevaluate HEAD and the value chain.

Do not implement a speculative fix merely because an observed symptom
suggests one.

For manufacturing defects:

``` text
observed bad manufacturing state / 3MF
      ↓
trace authoritative inputs, configuration, and Products
      ↓
identify violated invariant and owning layer
      ↓
RED at that layer when new behavioral evidence is needed
      ↓
smallest correct fix
      ↓
prove downstream manufacturing result
```

Tests should protect behavioral boundaries, not inventory implementation
details.

Use synthetic Models for generic engine behavior unless real Model
semantics are the subject of the test.

Manufacturing correctness belongs at the lowest layer that owns the
invariant. Acceptance tests should prove only that the corrected
behavior reaches the public value chain.

------------------------------------------------------------------------

# Priority Rule

A newly discovered defect that can produce an **incorrect 3MF**, corrupt
manufacturing configuration, or cause material value-chain inefficiency
takes priority over CLI polish.

Priority order:

``` text
1. correct manufacturing Product
2. correct persistent manufacturing state
3. correct dependency reuse / avoid unnecessary manufacturing work
4. reliable recovery and exception paths
5. clear operator guidance and errors
6. inspection/presentation polish
7. historical/developer CLI cleanup
```

Every phase should leave the program production-capable.

------------------------------------------------------------------------

# Architectural Invariants to Preserve

Current HEAD has already established important architecture that
remaining work must not regress.

## Product and dependency semantics

-   Products are first-class persistent outputs.
-   There is no engine-level privileged final Product.
-   A requested Product defines a build target.
-   Dependency closure, not numeric Stage order or filesystem layout,
    determines execution.
-   Logical Product identity is independent of generated filesystem
    path.
-   Realizations own their Products and generated namespaces.
-   Product dependencies may cross Stages, Realizations, Models,
    Artifacts, and builds.
-   Current Products are reusable manufacturing assets.
-   Stage implementations execute from complete resolved `StageContext`;
    orchestration remains outside Stage implementation.

Do not implement reuse by aliasing sibling Realization directories,
scanning generated files, or copying Products outside authoritative
Product/dependency semantics.

## Canonical Artwork reuse

Current HEAD establishes canonical registered Artwork through:

``` text
artwork_default.prepare
        ↓
artwork_default.raster
        ↓
artwork_default.vector
```

Named Artwork manufacturing Realizations consume the canonical logical
Vector Product through Product dependency semantics and diverge
downstream:

``` text
                    artwork_default.vector
                       /        |        \
                      /         |         \
                     ▼          ▼          ▼
          default.extrude   named.extrude   named.extrude
                 ↓               ↓               ↓
          default.package   named.package   named.package
```

A named Realization does not own or duplicate canonical `prepare`,
`raster`, or `vector` Products merely because it ultimately manufactures
its own 3MF.

Preserve the established same-plan versus external Product-dependency
semantics across normal execution, fingerprint planning, incremental
execution, execution planning, and planned Stage contexts.

## External input semantics

For planned external inputs:

``` text
source_path
    configured external source resource
    fingerprint provenance

path
    Artifact-owned materialized execution copy
```

Required fingerprints are computed from authoritative external source
provenance before materialization. Stage execution consumes the
Artifact-owned materialized path.

## Physical-color boundary

Physical printer-color policy must not invalidate geometry that is
otherwise unchanged.

Artwork preserves logical Artifact-color identity through Raster,
Vector, and Extrude. Artwork Package resolves physical printer
assignment.

Shape preserves logical incorporated Artwork identity through Compose
and Extrude. Shape Extrude owns geometry and component participation.
Shape Package resolves physical colors for Shape-owned components and
incorporated Artwork.

Changing only physical color policy must not force unnecessary upstream
geometry rebuilds.

For Shape, preserve the permanent semantics already defined in
`shape/DEFINITION.md`, including:

-   `shape_artwork_fill_raise` controls Artwork-fill participation and
    physical height;
-   `shape_artwork_fill_color` does not control participation or
    geometry;
-   absent Artwork-fill color inherits resolved base color;
-   Shape-owned physical colors are Package concerns;
-   incorporated Artwork physical printer assignment is a Package
    concern.

## Recolor persistence and recovery

Current HEAD establishes recolor as a Package-boundary correction
operation over authoritative logical Artwork state.

Preserve these semantics:

-   `printer_colors` persists the selected physical assignment
    applicable to logical Artwork colors; it is not a copy of the
    complete candidate library/catalog palette;
-   Artifact-scoped recolor mutates Artifact-level `printer_colors`
    while retaining explicit Realization-level overrides;
-   Realization-scoped recolor mutates only the selected Realization
    scope;
-   reset restores inheritance according to the established
    configuration contract;
-   all applicable recolor scopes are prepared before authored
    configuration or final-3MF mutation begins;
-   prospective physical assignments are computed and validated before
    persistence;
-   one failed scope leaves authored recolor state unchanged;
-   existing-final Artwork recolor uses canonical registered
    `artwork_default` Vector state as the authoritative logical color
    source;
-   named Artwork manufacturing Realizations do not require duplicate
    named Vector manifests for recolor;
-   Shape existing-final recolor follows the Shape plan's bound Artwork
    Product dependency;
-   recovery does not substitute stale packaged physical colors for
    registered logical Artwork identity;
-   recovery does not execute manufacturing stages merely to recreate a
    missing authoritative recolor source;
-   packaged registered Artwork components use the shared `artwork-N`
    semantic namespace; legacy `color-N` packaged names may be
    recognized only as a migration compatibility path and are rewritten
    to canonical `artwork-N` identity when recolored;
-   expected recolor prerequisites use semantic application errors at
    the UI boundary rather than being hidden by blanket exception
    handling;
-   unexpected invariant/programming failures remain visible; and
-   printer-color reconciliation preserves one installed slot for each
    required installed color while allowing redundant installed
    duplicates to be reused for missing required colors.

Do not reopen persistence, canonical-source, atomic-preflight, or
reconciliation semantics without new failing evidence.

## Artifact lifecycle

CREATE owns source ingestion and registration.

BUILD owns Artifact workspace materialization and manufacturing work.

A registered Artifact may legitimately exist under `originals/` before
`artifacts/<artifact_id>/` exists.

COLORS does not materialize Artifacts and does not execute manufacturing
work merely to make color analysis possible.

Explicit COLORS against a registered but unmaterialized Artifact reports
the lifecycle condition and directs the operator back to BUILD.

Read-only color analysis consumes current registered Artwork state. If
the required Vector Product is absent, stale, or otherwise requires
manufacturing work, COLORS defers that work to BUILD rather than
executing manufacturing Stages itself.

Broad COLORS may report useful analyses for applicable materialized
Artifacts while separately identifying registered Artifacts for which
BUILD is required.

## UI independence

The CLI is one client of reusable application capabilities.

Reusable workflow behavior belongs below Click:

``` text
CLI / TUI / GUI / API
          │
          ▼
 reusable application operations
          │
          ▼
 configuration / planning / engine / Products
```

Click owns parsing, terminal presentation, prompts, and translation of
structured application errors into operator-facing prose.

Do not solve reusable workflow problems only inside CLI command modules.

------------------------------------------------------------------------

# Existing Behavior to Preserve

Treat these as established capabilities unless new evidence demonstrates
a defect:

-   `artifact create` ingestion and operator-assigned Artifact identity;
-   CREATE registration under `originals/`;
-   BUILD materialization of Artifact workspace;
-   registered-versus-materialized Artifact discovery;
-   canonical and custom Realization discovery through configuration;
-   Realization-oriented manufacturing builds;
-   Product-targeted dependency planning;
-   incremental Product-state evaluation;
-   reuse of current Products;
-   canonical Artwork Vector reuse across named Artwork Realizations;
-   cross-Model registered Artwork consumption by Shape without
    requiring standalone Artwork Extrude/Package;
-   dependency-driven invalidation;
-   3MF publication/retrieval behavior;
-   Artifact/Realization CONFIG customization;
-   sparse authored configuration;
-   canonical Realizations that need not appear as authored Realization
    entries;
-   CLEAN Artifact/Realization maintenance scope;
-   COLORS analysis and explicit recoloring;
-   COLORS remaining read-only unless an explicit recolor operation is
    requested;
-   COLORS refusing to materialize or manufacture missing/stale
    prerequisites;
-   actionable registered-but-unmaterialized COLORS recovery through
    BUILD;
-   expected COLORS/configuration/planning/recolor errors translated at
    the CLI boundary;
-   invariant/programming failures not indiscriminately swallowed;
-   recolor persistence of the selected physical assignment rather than
    the complete candidate palette;
-   Artifact-scoped recolor persistence without overwriting explicit
    Realization-level `printer_colors`;
-   prospective recolor assignment validation before authored
    configuration mutation;
-   atomic Artifact/bulk recolor preflight across applicable scopes;
-   existing-final recolor from authoritative canonical registered
    Artwork rather than packaged physical color state;
-   named Artwork recolor through canonical `artwork_default` registered
    Artwork without requiring named Vector manifests;
-   Shape recolor through its planned bound Artwork Product dependency;
-   existing-final recolor without executing manufacturing stages to
    recreate missing prerequisites;
-   canonical packaged Artwork component identity as `artwork-N`, with
    legacy `color-N` names accepted and migrated during existing-final
    recolor;
-   printer-color reconciliation that reuses redundant installed
    duplicate slots correctly;
-   configuration precedence;
-   independent Stage execution from complete resolved context;
-   semantic execution events independent of terminal presentation;
-   `-v` / `-vv` / `--quiet` semantic messaging independent from Python
    logging;
-   top-level diagnostic logging policy;
-   lean normal BUILD result output.

Do not repeat completed color-boundary, cross-Realization reuse,
recolor-persistence, recolor-recovery, COLORS lifecycle, or
expected-error-translation work without new failing evidence.

------------------------------------------------------------------------

# Common Operator Behavior

## Working directory and lifecycle

The CLI operates on the current working directory as project root.

A workspace may contain:

``` text
loose incoming source images
originals/
artifacts/
```

A registered Artifact may legitimately exist under `originals/` before
BUILD materializes `artifacts/<artifact_id>/`.

Commands must distinguish:

``` text
registered Artifact
```

from:

``` text
materialized Artifact workspace
```

when that distinction affects whether an operation can proceed.

A missing collection directory means an empty collection, not an
exceptional condition.

## Scope

Where meaningful:

``` text
COMMAND
    all applicable Artifacts

COMMAND dog
    Artifact dog

COMMAND --realization shape_ornament
    that Realization across applicable Artifacts

COMMAND dog --realization shape_ornament
    that Realization of dog
```

An explicitly supplied Artifact or Realization asserts that the
addressed object exists.

Not every command must implement every broad scope. Scope should match
the operator question owned by the command.

## Empty, absent, unmaterialized, and broken state

Distinguish:

``` text
empty collection
    normal result

explicitly requested object absent
    operator-facing error

registered but not yet materialized Artifact
    valid lifecycle state
    operation may proceed or provide a value-chain recovery action

discovered persistent object malformed or inconsistent
    operator-facing configuration/application error

unexpected programming defect
    not silently swallowed
```

Expected configuration, planning, build, color, and equivalent
application failures should be translated at the UI boundary. Do not
indiscriminately catch `Exception`.

When the application knows the next corrective value-chain action, the
UI should present it concisely.

## Lean operator-facing output

Routine output should answer only questions useful to the next operator
action:

``` text
Artifact
Realization
what happened / current state
whether work remains
3MF or other relevant manufacturing Product
clear corrective action when needed
```

Do not expose internal Stage, resolver, dependency, or filesystem
mechanics unless directly useful.

Operator-facing Product paths should be concise and useful from the
current project root.

------------------------------------------------------------------------

# Phase 1 --- Finish Manufacturing Visibility Documentation

## Goal

Close the small remaining inspection/documentation gap without inventing
new workflow requirements.

Manufacturing correctness, lifecycle recovery, CONFIG authored
customization, COLORS recovery, and expected-error translation are
already established. This phase is not a reopening of those areas.

## 1.1 Verify SHOW Product-path presentation

Current selected-Artifact SHOW already exposes:

-   effective Realization;
-   built-in/custom type;
-   manufacturing state; and
-   accessible 3MF.

Verify the actual CLI output for a current Product beneath the project
root.

The desired presentation is a useful project-relative path such as:

``` text
artifacts/clean_bg_cat/artwork_default.3mf
```

rather than an unnecessarily long absolute path.

Reusable application results should retain real `Path` values. Any
formatting correction belongs at the CLI presentation boundary.

Do not alter Product identity, resolver policy, publication policy, or
persistence merely to change path presentation.

If current HEAD already emits a useful relative path, credit the
behavior and make no production change.

## 1.2 Reconcile the CLI README

After SHOW path behavior is verified, update:

``` text
src/lowkey_artifact_builder/cli/README.md
```

to describe current operator behavior rather than historical
implementation work.

Remove stale planning language such as:

``` text
Before continuing the Artwork planning/reuse investigation...
```

That investigation and its associated semantic verbosity/logging work
are complete.

Document the ordinary workflow as:

``` text
create → build → 3MF
```

LIST, SHOW, CONFIG, COLORS, and CLEAN are optional supporting operations
used only when they answer an operator question or remove an obstacle.

Reconcile the README with current HEAD in these areas:

-   CREATE registers source material without manufacturing Products;
-   BUILD materializes registered Artifacts when necessary and makes
    requested manufacturing Products current;
-   LIST remains a simple Artifact-identity discovery command;
-   SHOW requires a selected Artifact and exposes Realization
    manufacturing state;
-   bare SHOW is not a workspace-wide replacement for LIST;
-   `show <artifact> --realization <realization>` is a lean Realization
    drill-down;
-   CONFIG describes authored configuration/customization rather than
    effective manufacturing state;
-   COLORS does not materialize Artifacts or execute manufacturing work
    to recreate missing/stale registered Artwork;
-   registered-but-unmaterialized COLORS failures return the operator to
    BUILD;
-   expected domain errors are translated without hiding unexpected
    programming defects;
-   operator-facing Product paths are relative/useful where appropriate;
-   current semantic verbosity and diagnostic logging behavior;
-   canonical Product reuse where it materially helps explain operator
    behavior;
-   broad command scope only where the command actually supports and
    benefits from it.

Do not turn the CLI README into an engine architecture document.

### Resolved presentation decisions

The following questions no longer require implementation work:

**Bare SHOW**

Keep SHOW Artifact-oriented:

``` text
artifact show <artifact>
artifact show <artifact> --realization <realization>
```

LIST owns workspace-level Artifact identity discovery. Do not add bare
SHOW merely to duplicate LIST or invent an Artifact-level aggregate
manufacturing state.

**LIST**

Keep LIST plain and pipeline-friendly.

It answers one simple question:

> What managed Artifact IDs exist?

A Rich table would add visual weight without adding operator
information. The CLI README's general recommendation to use Rich for
naturally tabular structured output does not require a one-column
Artifact identity list to become a table.

**Realization drill-down**

Current:

``` text
artifact show <artifact> --realization <realization>
```

is sufficient when its selected manufacturing row answers the operator's
question.

Do not add effective configuration detail to SHOW merely because
drill-down exists. CONFIG remains the authored-configuration surface.

### Phase 1 completion criterion

The CLI README accurately describes current HEAD, and SHOW presents
useful Product paths without changing manufacturing semantics.

If SHOW path presentation is already correct, this phase is
documentation-only.

------------------------------------------------------------------------

# Phase 2 --- Consolidate Secondary and Developer Surfaces

## Goal

After production, recovery, and inspection workflows are stable and
documented, remove remaining historical CLI inconsistencies without
disturbing the established value chain.

This phase contains no speculative manufacturing capability.

## 2.1 Historical public syntax

Review remaining options and aliases against actual operator value,
including Variant-oriented syntax such as:

``` text
--variant
--all-variants
```

For each candidate ask:

1.  Does an operator still need this capability?
2.  Is it part of routine manufacturing?
3.  Is it an exception/customization capability?
4.  Is it primarily a developer capability?
5.  Does another established operation express the need more directly?
6.  Would changing it break a useful architecture-level capability
    merely to simplify CLI presentation?

Retain, relocate, deprecate, or remove based on those answers.

Do not confuse Variant identity with Realization identity.

Do not remove a useful engine capability merely because ordinary
manufacturing now has a simpler Realization-oriented CLI path.

## 2.2 Developer operations

Review:

-   independent Stage execution;
-   Model/workplan inspection;
-   CONFIG developer flags;
-   diagnostic/developer capabilities.

Preserve useful architectural capabilities without making the production
CLI present every engine capability.

Independent Stage execution from complete resolved `StageContext` is an
architectural capability, not dead code merely because ordinary
operators do not invoke it directly.

Where developer operations remain public, make their purpose and scope
explicit.

Where they do not belong in ordinary operator workflow, consider
relocation or clearer separation rather than deleting reusable
capability.

## 2.3 Final help and message consistency

Review:

``` text
artifact --help
artifact <command> --help
```

Help should describe operator purpose rather than implementation
mechanics.

Review routine messages for:

-   terse success output;
-   consistent Artifact/Variant/Realization terminology;
-   actionable expected errors;
-   suggested next actions when known;
-   useful batch summaries;
-   obvious manufacturing Products;
-   useful relative paths;
-   no unnecessary Stage/Model/Variant implementation detail.

Do not force identical output shapes on commands with different
purposes.

### Phase 2 completion criterion

The public CLI presents the shortest practical manufacturing workflow,
secondary/developer capabilities have an intentional home, and
help/messages no longer reflect superseded CLI models.

------------------------------------------------------------------------

# Final End-to-End Acceptance

Protect a small number of complete workflows. Reuse existing acceptance
evidence rather than duplicating lower-level tests.

Do not add new acceptance tests merely to restate behavior already
adequately protected at lower levels.

## Routine new work

``` text
incoming artwork
      ↓
create
      ↓
build
      ↓
correct 3MF
```

## Multi-Realization Artwork production

This behavior is already established and should remain protected:

``` text
Artifact
   ↓
canonical registered Artwork
   ↓
shared artwork_default Vector Product
   ↓
Realization-specific downstream divergence
   ↓
correct 3MFs
```

Do not require named Artwork Realizations to materialize duplicate
canonical upstream Products.

## Existing current work

``` text
known Artifact
      ↓
build or show
      ↓
current Product reused
      ↓
3MF
```

## Color exception

``` text
colors
   ↓
optional explicit recolor
   ↓
correct selected physical assignment persisted
   ↓
Package-only physical color invalidation where geometry is unchanged
   ↓
correct 3MF
```

## Recolor recovery

``` text
bad/stale color state
      ↓
recolor preflight
      ↓
authoritative logical color source
      ↓
atomic correction or contextual failure
      ↓
build
      ↓
correct 3MF
```

## Unmaterialized lifecycle exception

``` text
registered Artifact
      ↓
colors / inspection operation
      ↓
intentional lifecycle behavior
      ↓
actionable recovery when work cannot proceed
      ↓
return to value chain
```

COLORS specifically does not materialize or manufacture the Artifact as
part of this recovery path.

## Maintenance

``` text
clean selected generated work
      ↓
build
      ↓
dependency-driven regeneration
      ↓
correct 3MF
```

Acceptance tests should remain focused on user-visible manufacturing
value. Detailed geometry, configuration resolution, graph planning,
Product-state, dependency, and color-assignment behavior belongs in
lower-level tests.

------------------------------------------------------------------------

# Final Completion Criterion

The remaining work is complete when the application supports this
objective:

> Move customer artwork to a **correct, printable 3MF** with the fewest
> necessary decisions, actions, and computations.

Specifically:

-   incoming artwork can be registered without manual workspace
    preparation;
-   Artifact identity remains operator/client assigned and opaque to the
    build system;
-   registered and materialized Artifact states are handled
    intentionally;
-   BUILD makes requested manufacturing Products current;
-   current Products are reused;
-   canonical registered Artwork is reused across downstream
    Realizations according to Product dependency semantics;
-   Realizations diverge at the correct dependency boundary;
-   logical Product identity remains independent of filesystem location;
-   printable color selection cannot accidentally expand into an
    inappropriate complete candidate palette;
-   recolor persistence respects Artifact/Realization scope;
-   recolor recovery is atomic and uses authoritative logical color
    state;
-   physical color policy remains a Package concern where defined by
    Model semantics;
-   color-only changes do not unnecessarily invalidate geometry;
-   printer-color reconciliation correctly preserves required installed
    colors while allowing redundant installed duplicates to be reused;
-   resulting 3MF component colors reflect correct selected
    manufacturing color state;
-   resulting 3MFs are obvious and retrievable;
-   CLEAN provides reliable production maintenance;
-   LIST helps discover Artifact identities;
-   SHOW exposes useful Realization, state, and Product information when
    inspection is needed;
-   displayed Product paths are useful from the operator's current
    working directory;
-   CONFIG remains an exception/customization path;
-   COLORS remains an optional physical-color path;
-   COLORS does not take ownership of Artifact materialization or
    manufacturing;
-   expected domain errors are concise and traceback-free;
-   unexpected invariant/programming defects are not silently converted
    into ordinary operator failures;
-   clear recovery actions are suggested when the application knows the
    next useful step;
-   routine output remains lean and focused on operator decisions;
-   application workflow behavior is reusable independently of Click;
    and
-   future CLI, TUI, GUI, browser, or API clients can present the same
    manufacturing capabilities without reconstructing domain behavior.

The target mental model remains:

``` text
                         ┌──────── list / show ────────┐
                         │       when uncertain        │
                         │                             ▼
customer artwork → create → Artifact → build → correct printable 3MF → printer
                                   ▲         │
                                   │         │
                      ┌────────────┘         │
                      │                      │
                config / colors             │
                when customization          │
                requires attention          │
                                           │
                         clean ─────────────┘
                         when generated work
                         must be discarded
```

The steady-state operator workflow is:

``` text
create
   ↓
build
   ↓
use the correct 3MF
```

Everything else exists only when it removes an obstacle, corrects a
manufacturing defect, reduces unnecessary work, or helps the operator
make the next useful decision.
