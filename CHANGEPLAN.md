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

This CHANGEPLAN contains **only remaining work**. Completed phases have been removed. Current HEAD already establishes the physical-color Package boundary and canonical Artwork Vector reuse across Realizations; those behaviors are now constraints to preserve, not work to repeat.

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
                       /        |        \
                      /         |         \
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
- configuration precedence;
- independent Stage execution from complete resolved context;
- semantic execution events independent of terminal presentation;
- `-v` / `-vv` / `--quiet` semantic messaging independent from Python logging;
- top-level diagnostic logging policy;
- lean normal BUILD result output.

The complete suite was green at the current checkpoint:

```text
2343 tests, including slow acceptance
pyright
ruff
```

Do not repeat completed color-boundary or cross-Realization reuse work without new failing evidence.

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

# Phase 1 — Reproduce and Correct the Persistent Color-State Defect

## Goal

Establish exactly how the observed invalid color state was created, fix the owning defect, and prove that recoloring cannot accidentally expand printable Artwork layers to an entire candidate palette.

This is the next work. Do not begin with a speculative production change.

## Observed facts

A real `clean_bg_cat` Artifact was observed with:

```toml
printer_colors = [
    "grey",
    "olive-green",
    "matcha-green",
    "concrete-grey",
    "brown",
    "mint-green",
    "light-beige",
    "brick-red",
    "haze-blue",
    "light-brown",
    "apricot",
    "gold",
    "black",
    "silver",
    "fire-engine-red",
    "cold-white",
]
```

PrusaSlicer showed an Artwork 3MF with 16 Artwork color objects corresponding to that state.

Normal analysis of the source had also reported a much smaller measured Artwork color set and selected printable assignments.

The persisted state is therefore suspicious, but the operation that created it has not yet been proven.

`artifact colors clean_bg_cat --recolor=library` is a suspect based on operator history, not an established cause.

## Architecture-aligned trace

Because physical printer assignment is now Package-owned, trace:

```text
authoritative source / registered Artwork
      ↓
measured logical Artwork colors
      ↓
candidate printer/library palettes
      ↓
assignment / recolor selection
      ↓
configuration mutation
      ↓
persisted printer_colors
      ↓
Artwork Package
      ↓
physical 3MF component colors
```

Do **not** treat Artwork Extrude as the physical printer-color assignment boundary.

Artwork Extrude should remain concerned with geometry and logical Artifact-color identity. Package consumes that logical identity together with resolved physical printer-color policy.

## Investigation

Review current HEAD for:

- COLORS analysis result structures;
- measured Artwork color identity;
- printer/library/catalog palette roles;
- `--recolor=library`;
- `--recolor=printer`;
- `--recolor=reset`;
- Artifact-level versus Realization-level recolor scope;
- recolor preflight;
- configuration mutation and persistence;
- `printer_colors` resolution;
- Artwork Package assignment;
- 3MF component naming/color creation;
- existing tests that already protect any part of this path.

Determine from clean state whether the 16-color state is reproducible.

Do not force a RED if HEAD already satisfies the intended persistence semantics. If the suspected operation is already correct, credit it and continue tracing the actual corruption path.

## Required invariant

`printer_colors` represents the selected physical printer-color assignment applicable to logical Artwork colors at the configured scope.

A candidate palette is not itself the selected assignment.

Therefore:

```text
candidate library palette
    may contain many colors

measured Artwork
    may contain N logical colors

selected physical assignment
    contains the assignment required for those logical colors

persisted printer_colors
    records the selected assignment
    not the complete candidate palette
```

Do not hard-code five as a generic architectural rule. Tests should express the actual measured/assignment relationship and any printer-capacity rule at the layer that owns it.

Catalog colors remain advisory unless permanent specifications explicitly establish otherwise.

## Scope invariant

Artifact-level recolor mutates Artifact-level `printer_colors` unless an explicit Realization scope is selected.

Explicit Realization-level `printer_colors` remain Realization-owned overrides unless the requested operation explicitly targets them.

Reset semantics should continue to mean removal/restoration of inheritance according to the established configuration contract.

Do not broaden mutation scope merely to make recovery convenient.

## TDD slices

### 1.1 Reproduce persistence from clean state

Using the real reusable color operation rather than Click internals:

1. construct/register an Artifact with a known logical measured color set;
2. provide a candidate library larger than the selected printable assignment;
3. perform the actual library recolor operation;
4. inspect persisted authored configuration;
5. prove whether selected assignments or the full candidate palette were persisted;
6. prove mutation occurs at the requested Artifact/Realization scope;
7. prove unrelated Realization overrides remain untouched.

If this is GREEN under current HEAD, do not alter production code. Continue tracing other paths capable of creating the observed state.

### 1.2 Fix the owning persistence defect

Only after 1.1 identifies a violated invariant:

1. RED at the lowest layer that owns the wrong persistence;
2. implement the smallest correction;
3. retain atomic configuration mutation;
4. preserve explicit scope;
5. preserve library/printer/catalog role distinctions.

### 1.3 Manufacturing consequence

Once persistence is correct, build an affected Artwork Realization and prove:

- logical Artwork layer count remains determined by registered Artwork;
- Package maps those logical colors to the selected physical assignment;
- the 3MF contains the expected Artwork components;
- structural colors such as loop/base/ridge remain governed by their own Model semantics;
- the complete candidate library does not become a set of Artwork manufacturing components.

Keep detailed assignment/LP behavior in lower-level tests. Acceptance should prove the manufacturing consequence, not reimplement color mathematics.

## Completion

This phase is complete when:

- the original 16-color corruption path is reproduced or conclusively excluded from each suspected operation;
- the actual owning defect is identified;
- regression coverage protects the persistence invariant;
- a clean recolor/build cannot create an inappropriate full-palette `printer_colors` state;
- Artwork Package produces physical component colors from the selected assignment without changing logical Artwork geometry.

---

# Phase 2 — Recolor Recovery and Preflight

## Goal

Make recolor a reliable correction path even when existing persistent manufacturing state is stale, malformed, or incompatible, without weakening valid color-assignment rules or partially mutating configuration.

## Observed behavior

With the observed 16-color state, Artifact-level recolor failed during preflight with a message equivalent to:

```text
Recoloring requires usable existing recolor sources for every applicable Realization:
Palette color count cannot be smaller than measured color count.
Measured 16, palette 5.
```

The failure appeared more than once, apparently because multiple applicable Realizations were being prepared.

## Preserve

Artifact-level recolor must remain atomic.

If any required scope cannot be prepared safely:

```text
no partial printer_colors mutation
no partial Realization mutation
no silently weakened assignment validation
```

Do not make corrupted state “work” by allowing an invalid palette-to-measured-color assignment.

## Investigation

Determine:

- what current HEAD considers an authoritative recolor source;
- whether generated/package physical color state is being mistaken for logical measured Artwork color state;
- whether canonical registered Artwork provides a clean authoritative source;
- how canonical Artwork Vector reuse affects recolor source selection;
- whether recovery should use source/registered Products rather than previously packaged physical assignments;
- whether CLEAN, BUILD, RESET, or another established operation is genuinely required;
- how failures identify the Artifact and Realization that could not be prepared.

The physical-color Package boundary should simplify this investigation: logical measured/registered Artwork state and physical Package assignment are distinct concepts and should remain distinct during recolor preparation.

## TDD slices

### 2.1 Atomic preflight

Protect:

- all applicable scopes are prepared before authored configuration mutates;
- one failed scope leaves all authored recolor state unchanged;
- successful preparation produces a structured recolor plan/result usable by non-CLI clients.

### 2.2 Authoritative recovery source

After resolving semantics, prove recolor preparation uses the correct authoritative logical color source.

Do not use a stale packaged physical palette as a substitute for logical Artwork color identity unless the permanent Model definition explicitly requires it.

### 2.3 Contextual failure

Application-level failure should identify enough structured context for a UI to explain:

```text
Artifact
Realization, when applicable
failed condition
known corrective action, when one exists
```

Do not make the application operation return Click-formatted prose.

## Completion

A recolor either:

```text
succeeds atomically
```

or:

```text
fails without mutation
and identifies the condition preventing recovery
```

The operator is not trapped by a generated physical-color state that should be recoverable from authoritative logical Artwork state.

---

# Phase 3 — Repair Exception and Recovery Paths

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

## 3.1 COLORS on registered but unmaterialized Artifacts

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

## 3.2 Expected error translation and suggested actions

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

## 3.3 CONFIG authored customization

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

### Phase 3 completion criterion

Exception paths identify the obstacle, provide the next useful action when known, and return naturally to BUILD without making CONFIG, COLORS, or CLEAN mandatory.

---

# Phase 4 — Reconcile Manufacturing Visibility and Situational Awareness

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

## 4.1 SHOW Product paths

Reusable application results should retain real `Path` values.

At the CLI presentation boundary, when a Product lies beneath the current project root, display a useful relative path such as:

```text
artifacts/clean_bg_cat/artwork_default.3mf
```

rather than a long absolute path.

Do not alter Product identity, resolver policy, or persistence to achieve presentation formatting.

Before adding new work, verify whether current HEAD already satisfies this through the shared messaging/path presentation work. Credit it if so.

## 4.2 Bare SHOW

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

## 4.3 LIST presentation

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

## 4.4 Realization drill-down

`artifact show <artifact> --realization <realization>` narrows manufacturing inspection.

Do not add effective-configuration detail merely because a drill-down option exists.

If the selected manufacturing row already answers the operator's question, keep it lean.

CONFIG remains the authored-configuration surface.

## 4.5 CLI README reconciliation

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

### Phase 4 completion criterion

The operator can discover work, inspect manufacturing state, identify an existing usable 3MF, and determine the next action without unnecessary duplication among CREATE, LIST, SHOW, BUILD, and COLORS.

---

# Phase 5 — Consolidate Secondary and Developer Surfaces

## Goal

After production, recovery, and inspection workflows are stable, remove remaining historical CLI inconsistencies without disturbing the established value chain.

This phase contains no speculative manufacturing capability.

## 5.1 Historical public syntax

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

## 5.2 Developer operations

Review:

- independent Stage execution;
- Model/workplan inspection;
- CONFIG developer flags;
- diagnostic/developer capabilities.

Preserve useful architectural capabilities without making the production CLI present every engine capability.

Independent Stage execution from complete resolved `StageContext` is an architectural capability, not dead code merely because ordinary operators do not invoke it directly.

## 5.3 Final help and message consistency

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

