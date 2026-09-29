# CHANGEPLAN

## Purpose

Continue refining `lowkey-artifact-builder` around the actual manufacturing value chain from the current repository HEAD.

The operator's ordinary goal is:

> Move customer artwork to a **correct, printable 3MF** with the fewest necessary decisions, actions, and computations.

The primary value chain remains:
```text
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

Other commands support that path when the operator needs discovery, explanation, customization, correction, color selection, or maintenance:
```text
list
show
config
colors
clean
```

These commands are helpers or exception paths. They must not become mandatory ceremony before routine manufacturing.

This CHANGEPLAN contains **only remaining work**. Completed phases have been removed. Current HEAD already establishes the physical-color Package boundary, canonical Artwork Vector reuse across Realizations, correct recolor persistence, atomic recolor preflight, and authoritative existing-final recolor recovery; those behaviors are now constraints to preserve, not work to repeat.

This plan does not redefine Artifact, Variant, Realization, Product, configuration, build planning, Product state, Stage ownership, Model semantics, or color semantics. Those remain owned by `ARCHITECTURE.md` and the applicable Model `DEFINITION.md`. If an investigation exposes a genuine mismatch with those permanent specifications, resolve that mismatch explicitly before encoding new behavior in tests.

---

# Development Method

This plan is subordinate to:
```text
ARCHITECTURE.md
src/lowkey_artifact_builder/model/models/<model>/DEFINITION.md
src/lowkey_artifact_builder/cli/README.md
prompts/NEW_THREAD.md
prompts/TEST_DRIVEN_DEVELOPMENT.md
```

`ARCHITECTURE.md` and Model definitions are normative. Repository HEAD defines the current implementation. This file is a temporary plan for remaining work.

Before each TDD slice:

1. review the relevant permanent specifications and current HEAD;
2. credit behavior HEAD already satisfies;
3. reproduce or otherwise establish the next unmet workflow or correctness requirement;
4. distinguish observed facts from suspected causes;
5. resolve semantic or architectural questions before RED;
6. add the smallest coherent behavioral test slice;
7. observe RED for the intended reason;
8. implement the smallest correct behavior;
9. run focused tests;
10. run the complete applicable quality suite;
11. commit and reevaluate HEAD and the value chain.

Do not implement a speculative fix merely because an observed symptom suggests one.

For manufacturing defects:
```text
observed bad manufacturing state / 3MF
      ↓
trace authoritative inputs, configuration, and Products
      ↓
identify violated invariant and owning layer
      ↓
RED at that layer
      ↓
smallest correct fix
      ↓
prove downstream manufacturing result
```

Tests should protect behavioral boundaries, not inventory implementation details.

Use synthetic Models for generic engine behavior unless real Model semantics are the subject of the test.

Manufacturing correctness belongs at the lowest layer that owns the invariant. Acceptance tests should prove only that the corrected behavior reaches the public value chain.

---

# Priority Rule

A newly discovered defect that can produce an **incorrect 3MF**, corrupt manufacturing configuration, or cause material value-chain inefficiency takes priority over CLI polish.

Priority order:
```text
1. correct manufacturing Product
2. correct persistent manufacturing state
3. correct dependency reuse / avoid unnecessary manufacturing work
4. reliable recovery and exception paths
5. clear operator guidance and errors
6. inspection/presentation polish
7. historical/developer CLI cleanup
```

Every phase should leave the program production-capable.

---

# Architectural Invariants to Preserve

Current HEAD has already established important architecture that remaining work must not regress.

## Product and dependency semantics

- Products are first-class persistent outputs.
- There is no engine-level privileged final Product.
- A requested Product defines a build target.
- Dependency closure, not numeric Stage order or filesystem layout, determines execution.
- Logical Product identity is independent of generated filesystem path.
- Realizations own their Products and generated namespaces.
- Product dependencies may cross Stages, Realizations, Models, Artifacts, and builds.
- Current Products are reusable manufacturing assets.
- Stage implementations execute from complete resolved `StageContext`; orchestration remains outside Stage implementation.

Do not implement reuse by aliasing sibling Realization directories, scanning generated files, or copying Products outside authoritative Product/dependency semantics.

## Canonical Artwork reuse

Current HEAD establishes canonical registered Artwork through:
```text
artwork_default.prepare
        ↓
artwork_default.raster
        ↓
artwork_default.vector
```

Named Artwork manufacturing Realizations consume the canonical logical Vector Product through Product dependency semantics and diverge downstream:
```text
                    artwork_default.vector
                       /        |        \\
                      /         |         \\
                     ▼          ▼          ▼
          default.extrude   named.extrude   named.extrude
                 ↓               ↓               ↓
          default.package   named.package   named.package
```

A named Realization does not own or duplicate canonical `prepare`, `raster`, or `vector` Products merely because it ultimately manufactures its own 3MF.

Preserve the established same-plan versus external Product-dependency semantics across normal execution, fingerprint planning, incremental execution, execution planning, and planned Stage contexts.

## External input semantics

For planned external inputs:
```text
source_path
    configured external source resource
    fingerprint provenance
path
    Artifact-owned materialized execution copy
```

Required fingerprints are computed from authoritative external source provenance before materialization. Stage execution consumes the Artifact-owned materialized path.

## Physical-color boundary

Physical printer-color policy must not invalidate geometry that is otherwise unchanged.

Artwork preserves logical Artifact-color identity through Raster, Vector, and Extrude. Artwork Package resolves physical printer assignment.

Shape preserves logical incorporated Artwork identity through Compose and Extrude. Shape Extrude owns geometry and component participation. Shape Package resolves physical colors for Shape-owned components and incorporated Artwork.

Changing only physical color policy must not force unnecessary upstream geometry rebuilds.

For Shape, preserve the permanent semantics already defined in `shape/DEFINITION.md`, including:

- `shape_artwork_fill_raise` controls Artwork-fill participation and physical height;
- `shape_artwork_fill_color` does not control participation or geometry;
- absent Artwork-fill color inherits resolved base color;
- Shape-owned physical colors are Package concerns;
- incorporated Artwork physical printer assignment is a Package concern.

## Recolor persistence and recovery

Current HEAD establishes recolor as a Package-boundary correction operation over authoritative logical Artwork state.

Preserve these semantics:

- `printer_colors` persists the selected physical assignment applicable to logical Artwork colors; it is not a copy of the complete candidate library/catalog palette;
- Artifact-scoped recolor mutates Artifact-level `printer_colors` while retaining explicit Realization-level overrides;
- Realization-scoped recolor mutates only the selected Realization scope;
- reset restores inheritance according to the established configuration contract;
- all applicable recolor scopes are prepared before authored configuration or final-3MF mutation begins;
- prospective physical assignments are computed and validated before persistence;
- one failed scope leaves authored recolor state unchanged;
- existing-final Artwork recolor uses canonical registered `artwork_default` Vector state as the authoritative logical color source;
- named Artwork manufacturing Realizations do not require duplicate named Vector manifests for recolor;
- Shape existing-final recolor follows the Shape plan's bound Artwork Product dependency;
- recovery does not substitute stale packaged physical colors for registered logical Artwork identity;
- recovery does not execute manufacturing stages merely to recreate a missing authoritative recolor source; and
- packaged registered Artwork components use the shared `artwork-N` semantic namespace. Legacy `color-N` packaged names may be recognized only as a migration compatibility path and are rewritten to canonical `artwork-N` identity when recolored.

Recolor application failures may still require UI-boundary translation and suggested-action work in Phase 1. Do not reopen persistence, canonical-source, or atomic-preflight semantics without new failing evidence.

## UI independence

The CLI is one client of reusable application capabilities.

Reusable workflow behavior belongs below Click:
```text
CLI / TUI / GUI / API
          │
          ▼
 reusable application operations
          │
          ▼
 configuration / planning / engine / Products
```

Click owns parsing, terminal presentation, prompts, and translation of structured application errors into operator-facing prose.

Do not solve reusable workflow problems only inside CLI command modules.

---

# Existing Behavior to Preserve

Treat these as established capabilities unless new evidence demonstrates a defect:

- `artifact create` ingestion and operator-assigned Artifact identity;
- CREATE registration under `originals/`;
- BUILD materialization of Artifact workspace;
- canonical and custom Realization discovery through configuration;
- Realization-oriented manufacturing builds;
- Product-targeted dependency planning;
- incremental Product-state evaluation;
- reuse of current Products;
- canonical Artwork Vector reuse across named Artwork Realizations;
- cross-Model registered Artwork consumption by Shape without requiring standalone Artwork Extrude/Package;
- dependency-driven invalidation;
- 3MF publication/retrieval behavior;
- Artifact/Realization CONFIG customization;
- CLEAN Artifact/Realization maintenance scope;
- COLORS analysis and explicit recoloring;
- recolor persistence of the selected physical assignment rather than the complete candidate palette;
- Artifact-scoped recolor persistence without overwriting explicit Realization-level `printer_colors`;
- prospective recolor assignment validation before authored configuration mutation;
- atomic Artifact/bulk recolor preflight across applicable scopes;
- existing-final recolor from authoritative canonical registered Artwork rather than packaged physical color state;
- named Artwork recolor through canonical `artwork_default` registered Artwork without requiring named Vector manifests;
- Shape recolor through its planned bound Artwork Product dependency;
- existing-final recolor without executing manufacturing stages to recreate missing prerequisites;
- canonical packaged Artwork component identity as `artwork-N`, with legacy `color-N` names accepted and migrated during existing-final recolor;
- configuration precedence;
- independent Stage execution from complete resolved context;
- semantic execution events independent of terminal presentation;
- `-v` / `-vv` / `--quiet` semantic messaging independent from Python logging;
- top-level diagnostic logging policy;
- lean normal BUILD result output.

The complete suite was green at the current checkpoint:
```text
2350 tests, including slow acceptance
pyright
ruff
```

Do not repeat completed color-boundary, cross-Realization reuse, recolor-persistence, or recolor-recovery work without new failing evidence.

---

# Common Operator Behavior

## Working directory and lifecycle

The CLI operates on the current working directory as project root.

A workspace may contain:
```text
loose incoming source images
originals/
artifacts/
```

A registered Artifact may legitimately exist under `originals/` before BUILD materializes `artifacts/<artifact_id>/`.

Commands must distinguish:
```text
registered Artifact
```

from:
```text
materialized Artifact workspace
```

when that distinction affects whether an operation can proceed.

A missing collection directory means an empty collection, not an exceptional condition.

## Scope

Where meaningful:
```text
COMMAND
    all applicable Artifacts
COMMAND dog
    Artifact dog
COMMAND --realization shape_ornament
    that Realization across applicable Artifacts
COMMAND dog --realization shape_ornament
    that Realization of dog
```

An explicitly supplied Artifact or Realization asserts that the addressed object exists.

## Empty, absent, unmaterialized, and broken state

Distinguish:
```text
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

Expected configuration, planning, build, color, and equivalent application failures should be translated at the UI boundary. Do not indiscriminately catch `Exception`.

When the application knows the next corrective value-chain action, expose it structurally so the UI can present it concisely.

## Lean operator-facing output

Routine output should answer only questions useful to the next operator action:
```text
Artifact
Realization
what happened / current state
whether work remains
3MF or other relevant manufacturing Product
clear corrective action when needed
```

Do not expose internal Stage, resolver, dependency, or filesystem mechanics unless directly useful.

Operator-facing Product paths should be concise and useful from the current project root.

---

# Phase 1 — Repair Exception and Recovery Paths

## Goal

Return operators to the manufacturing value chain without internal configuration errors or Python tracebacks.

The ordinary path remains:
```text
create → build → 3MF
```

Exception paths remain optional:
```text
configuration exception
    config → build → 3MF
color exception
    colors [→ recolor] → build → 3MF
maintenance exception
    clean → build → 3MF
```

## 1.1 COLORS on registered but unmaterialized Artifacts

### Observed behavior

A registered source may legitimately exist as:
```text
originals/clean_bg_cat.png
```

while `artifacts/clean_bg_cat/` does not yet exist.

`artifact list` can still discover the Artifact.

Previously:
```text
artifact colors clean_bg_cat
```

leaked:
```text
Error: Unknown configuration value 'source'.
```

This exposes an internal configuration-resolution concept for a valid lifecycle state.

### Resolve semantics first

Determine whether COLORS analysis truly requires a materialized Artifact under current architecture.

Possible valid outcomes include:

1. COLORS can operate from registered authoritative source/Products without a materialized workspace; or
2. COLORS requires materialization and should return a structured “not materialized” condition.

Do not assume the second merely because it matches the old implementation.

If materialization is required, the UI should be able to present a concise next action such as:
```text
Artifact 'clean_bg_cat' is not materialized.
Try `artifact build clean_bg_cat`.
```

Do not make COLORS itself perform BUILD unless architecture/workflow review establishes that as the reusable application behavior.

### Broad COLORS

`artifact colors` remains a broad operation over applicable Artifacts.

Define broad-scope behavior deliberately:

- empty workspace is normal;
- explicit missing Artifact is an error;
- registered/unmaterialized Artifacts are handled according to the resolved lifecycle semantics;
- useful results for applicable Artifacts should not be discarded unnecessarily;
- malformed persistent state is not silently hidden;
- read-only analysis does not mutate persistent state.

### TDD

Cover the reusable application boundary first, then CLI translation:

1. explicit registered-but-unmaterialized Artifact;
2. empty workspace;
3. missing explicitly requested Artifact;
4. broad scope with mixed lifecycle states;
5. no mutation during read-only analysis.

## 1.2 Expected error translation and suggested actions

Expected operator/domain failures must not expose Python tracebacks.

Known categories include:

- color assignment/preflight failures;
- configuration-resolution failures;
- missing Artifact/Realization;
- lifecycle state that prevents an operation;
- planning/build failures that are expected domain conditions.

Do not blanket-catch unexpected programming defects.

Prefer typed/structured application errors where the reusable operation owns the semantic condition. Click should translate those into concise operator prose.

Do not diagnose deep application conditions through CLI string matching.

Where the application knows a corrective action, represent that information structurally so the CLI can render a useful suggestion.

### Completion

Expected COLORS/configuration/planning/recolor failures are concise, contextual, actionable when possible, and traceback-free.

## 1.3 CONFIG authored customization

Preserve the distinction:
```text
config
    authored configuration
show
    effective manufacturing state
```

Preserve:

- Artifact-level authored configuration;
- Realization-specific customization;
- custom Realization creation/mutation;
- sparse configuration;
- canonical Realizations that do not appear falsely authored.

Review CONFIG workflow only where actual remaining friction is demonstrated.

Developer-oriented CONFIG capabilities such as model/workplan/dump inspection remain candidates for later consolidation, not manufacturing-critical work.

### Phase 1 completion criterion

Exception paths identify the obstacle, provide the next useful action when known, and return naturally to BUILD without making CONFIG, COLORS, or CLEAN mandatory.

---

# Phase 2 — Reconcile Manufacturing Visibility and Situational Awareness

## Goal

Polish inspection only after manufacturing correctness and recovery are trustworthy.

Each command should answer a distinct operator question:
```text
artifact create
    What incoming work can enter the value chain?
artifact list
    What managed Artifact IDs exist?
artifact show
    What manufacturing state and Products exist?
artifact build
    What work is necessary to make requested Products current?
artifact colors
    Where does physical color require attention?
```

Bare invocations may provide command-relevant situational awareness. They do not need identical output or scope.

## 2.1 SHOW Product paths

Reusable application results should retain real `Path` values.

At the CLI presentation boundary, when a Product lies beneath the current project root, display a useful relative path such as:
```text
artifacts/clean_bg_cat/artwork_default.3mf
```

rather than a long absolute path.

Do not alter Product identity, resolver policy, or persistence to achieve presentation formatting.

Before adding new work, verify whether current HEAD already satisfies this through the shared messaging/path presentation work. Credit it if so.

## 2.2 Bare SHOW

Selected-Artifact SHOW already answers:

> What can I manufacture from this Artifact, and what already exists?

Review whether bare:
```text
artifact show
```

adds useful workspace-level manufacturing awareness.

Do not define it merely as a prettier LIST.

LIST owns Artifact identity discovery. SHOW should expose manufacturing state or Products useful for deciding the next manufacturing action.

Review bare CREATE and bare BUILD behavior before specifying bare SHOW so the commands complement rather than duplicate one another.

A possible scope model, subject to workflow evidence and RED, is:
```text
artifact show
    manufacturing overview across applicable Artifacts
artifact show clean_bg_cat
    Realization manufacturing overview for one Artifact
artifact show --realization artwork_default
    selected Realization across applicable Artifacts, if useful
artifact show clean_bg_cat --realization artwork_default
    selected Realization of one Artifact
```

Do not invent an Artifact-level aggregate `current/stale/not built` state unless its semantics are clearly useful and defined.

## 2.3 LIST presentation

Current LIST is intentionally simple unless structured presentation materially improves operator discovery.

Resolve the tension in the CLI README between:
```text
Artifact lists are candidates for Rich tables
```

and:
```text
naturally simple output should remain simple
```

Possible outcomes:

- keep LIST plain and pipeline-friendly, then document that decision; or
- use a minimal Rich table if it adds meaningful operator value.

Do not add visual weight solely for consistency with SHOW.

## 2.4 Realization drill-down

`artifact show <artifact> --realization <realization>` narrows manufacturing inspection.

Do not add effective-configuration detail merely because a drill-down option exists.

If the selected manufacturing row already answers the operator's question, keep it lean.

CONFIG remains the authored-configuration surface.

## 2.5 CLI README reconciliation

Update `src/lowkey_artifact_builder/cli/README.md` only after remaining command behavior is settled.

Known stale material includes references to work that HEAD has already completed, including language such as “Before continuing the Artwork planning/reuse investigation”.

Reconcile:

- actual normal `create → build → 3MF` workflow;
- whether preliminary LIST/SHOW steps are optional rather than routine ceremony;
- bare SHOW semantics, if added;
- LIST presentation decision;
- relative Product paths;
- registered-versus-materialized Artifact behavior;
- actionable recovery messages;
- broad command scope;
- current semantic verbosity/logging behavior;
- current canonical Product reuse behavior where operator documentation needs to mention it.

Do not turn the CLI README into an engine architecture document.

### Phase 2 completion criterion

The operator can discover work, inspect manufacturing state, identify an existing usable 3MF, and determine the next action without unnecessary duplication among CREATE, LIST, SHOW, BUILD, and COLORS.

---

# Phase 3 — Consolidate Secondary and Developer Surfaces

## Goal

After production, recovery, and inspection workflows are stable, remove remaining historical CLI inconsistencies without disturbing the established value chain.

This phase contains no speculative manufacturing capability.

## 3.1 Historical public syntax

Review remaining options and aliases against actual operator value, including Variant-oriented syntax such as:
```text
--variant
--all-variants
```

For each candidate ask:

1. Does an operator still need this capability?
2. Is it part of routine manufacturing?
3. Is it an exception/customization capability?
4. Is it primarily a developer capability?
5. Does another established operation express the need more directly?
6. Would changing it break a useful architecture-level capability merely to simplify CLI presentation?

Retain, relocate, deprecate, or remove based on those answers.

Do not confuse Variant identity with Realization identity.

## 3.2 Developer operations

Review:

- independent Stage execution;
- Model/workplan inspection;
- CONFIG developer flags;
- diagnostic/developer capabilities.

Preserve useful architectural capabilities without making the production CLI present every engine capability.

Independent Stage execution from complete resolved `StageContext` is an architectural capability, not dead code merely because ordinary operators do not invoke it directly.

## 3.3 Final help and message consistency

Review:
```text
artifact --help
artifact <command> --help
```

Help should describe operator purpose rather than implementation mechanics.

Review routine messages for:

- terse success output;
- consistent Artifact/Variant/Realization terminology;
- actionable expected errors;
- suggested next actions when known;
- useful batch summaries;
- obvious manufacturing Products;
- useful relative paths;
- no unnecessary Stage/Model/Variant implementation detail.

Do not force identical output shapes on commands with different purposes.

---

# Final End-to-End Acceptance

Protect a small number of complete workflows. Reuse existing acceptance evidence rather than duplicating lower-level tests.

## Routine new work

```text
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
```text
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

Do not require named Artwork Realizations to materialize duplicate canonical upstream Products.

## Existing current work

```text
known Artifact
      ↓
build or show
      ↓
current Product reused
      ↓
3MF
```

## Color exception

```text
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

```text
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

```text
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

## Maintenance

```text
clean selected generated work
      ↓
build
      ↓
dependency-driven regeneration
      ↓
correct 3MF
```

Acceptance tests should remain focused on user-visible manufacturing value. Detailed geometry, configuration resolution, graph planning, Product-state, dependency, and color-assignment behavior belongs in lower-level tests.

---

# Final Completion Criterion

The remaining work is complete when the application supports this objective:

> Move customer artwork to a **correct, printable 3MF** with the fewest necessary decisions, actions, and computations.

Specifically:

- incoming artwork can be registered without manual workspace preparation;
- Artifact identity remains operator/client assigned and opaque to the build system;
- registered and materialized Artifact states are handled intentionally;
- BUILD makes requested manufacturing Products current;
- current Products are reused;
- canonical registered Artwork is reused across downstream Realizations according to Product dependency semantics;
- Realizations diverge at the correct dependency boundary;
- logical Product identity remains independent of filesystem location;
- printable color selection cannot accidentally expand into an inappropriate complete candidate palette;
- recolor persistence respects Artifact/Realization scope;
- recolor recovery is atomic and uses authoritative logical color state;
- physical color policy remains a Package concern where defined by Model semantics;
- color-only changes do not unnecessarily invalidate geometry;
- resulting 3MF component colors reflect correct selected manufacturing color state;
- resulting 3MFs are obvious and retrievable;
- CLEAN provides reliable production maintenance;
- LIST helps discover Artifact identities;
- SHOW exposes useful Realization, state, and Product information when inspection is needed;
- displayed Product paths are useful from the operator's current working directory;
- CONFIG remains an exception/customization path;
- COLORS remains an optional physical-color path;
- expected domain errors are concise and traceback-free;
- clear recovery actions are suggested when the application knows the next useful step;
- routine output remains lean and focused on operator decisions;
- application workflow behavior is reusable independently of Click; and
- future CLI, TUI, GUI, browser, or API clients can present the same manufacturing capabilities without reconstructing domain behavior.

The target mental model remains:
```text
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
```text
create
   ↓
build
   ↓
use the correct 3MF
```

Everything else exists only when it removes an obstacle, corrects a manufacturing defect, reduces unnecessary work, or helps the operator make the next useful decision.
