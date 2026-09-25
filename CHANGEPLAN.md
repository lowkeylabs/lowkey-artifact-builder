# CHANGEPLAN

## Purpose

Refactor, verify, and polish `lowkey-artifact-builder` around the actual manufacturing value chain.

The operator's goal is:

> Move customer artwork to a **correct, printable 3MF** with the fewest necessary decisions, actions, and unnecessary computations.

The primary value chain is:

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

This CHANGEPLAN now gives **manufacturing correctness and value-chain efficiency priority over CLI polish**. Recent operator walkthroughs exposed possible defects that can create incorrect manufacturing Products or repeat expensive upstream work. Those issues must be investigated and corrected before continuing secondary presentation cleanup.

This plan does not redefine Artifact, Variant, Realization, Product, configuration, build planning, Product state, Stage ownership, or Model semantics. Those remain owned by `ARCHITECTURE.md` and the applicable Model `DEFINITION.md`. If an investigation exposes a genuine architectural mismatch, resolve that mismatch explicitly against those permanent specifications before encoding a new behavior in tests.

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

`ARCHITECTURE.md` and the Model definitions remain the permanent normative specifications. The CLI README describes the intended human-facing CLI workflow. Repository HEAD defines the current implementation. This file describes temporary work required to bring HEAD into alignment.

Before each TDD slice:

1. review the relevant permanent specifications and CLI README;
2. review current HEAD and existing tests;
3. credit behavior HEAD already satisfies;
4. reproduce or otherwise establish the next unmet workflow/correctness requirement;
5. distinguish observed facts from suspected root causes;
6. resolve semantic or architectural questions before testing them;
7. add a coherent behavioral test slice;
8. observe RED for the intended reason;
9. implement the smallest correct behavior;
10. run focused tests and the complete quality suite;
11. commit and reevaluate HEAD and the value chain.

Do not implement a speculative fix merely because an observed symptom suggests one.

In particular:

```text
observed bad 3MF
      ↓
trace authoritative inputs and Products
      ↓
identify violated invariant
      ↓
RED at the owning layer
      ↓
fix
      ↓
prove downstream manufacturing result
```

Prefer workflow-sized slices when several closely related behaviors establish one operator capability and still produce understandable RED failures.

CLI tests protect user intent, scope, validation, useful errors, operator-facing output, and translation into application operations. They should not duplicate Model, engine, configuration-resolution, Product-state, or color-assignment tests already protected below the CLI.

Manufacturing correctness belongs at the lowest layer that owns the invariant. Acceptance tests should then prove that the corrected behavior reaches the public value chain.

---

# Incremental Delivery and Priority Rule

Every phase must end at a production-capable stopping point.

However, a newly discovered defect that can produce an **incorrect 3MF**, corrupt manufacturing configuration, or cause material value-chain inefficiency takes priority over later-phase CLI polish.

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

A phase previously considered complete may be reopened narrowly when new evidence shows that its production guarantee was incomplete.

---

# UI Independence

The CLI is one client of the application. It is not the application itself.

The same workflow may later be presented through:

```text
CLI
TUI
GUI
browser/API client
```

Reusable workflow behavior belongs below the UI boundary:

```text
CLI / TUI / GUI / API
          │
          ▼
 reusable application operations
          │
          ▼
 configuration / planning / engine / Products
```

Application operations should return structured results or expose semantic events usable by different interfaces.

UI-specific concerns include:

- Click argument and option parsing;
- terminal prompts;
- terminal formatting;
- progress presentation;
- human-facing CLI error translation; and
- rendering paths relative to the operator's working context.

Reusable application concerns include:

- Artifact discovery;
- source registration;
- Realization discovery;
- manufacturing state;
- build orchestration;
- Product discovery and retrieval;
- configuration operations;
- color operations; and
- cleaning operations.

Do not solve a reusable workflow problem merely by adding orchestration to a Click command module.

---

# Existing Behavior to Preserve

Significant previous work has established production behavior in:

```text
create
build
config
clean
colors
list
show
```

Treat these as existing capabilities, not blank surfaces to redesign.

Preserve established behavior unless an observed workflow or correctness defect justifies a focused change.

In particular, preserve:

- `artifact create` ingestion and Artifact identity;
- CREATE registration under `originals/`;
- BUILD materialization of Artifact workspace;
- canonical Realization discovery through configuration rather than CLI reconstruction;
- Realization-oriented BUILD behavior;
- incremental Product-state evaluation;
- reuse of current Products;
- canonical Stage Product ownership;
- dependency-driven execution;
- 3MF publication/retrieval behavior;
- Artifact/Realization CONFIG customization;
- CLEAN Artifact/Realization maintenance scope;
- established COLORS analysis and explicit recoloring semantics;
- normal configuration precedence; and
- independent Stage execution through a complete `StageContext`.

Bare commands may intentionally be read-only situational-awareness operations. This is an established CLI pattern, not behavior that must be split into separate commands.

“Thin CLI” means reusable behavior lives below presentation. It does not mean one command maps to exactly one application operation.

---

# Value-Chain Design Principle

Evaluate every change from the operator's position in the manufacturing workflow.

The primary question is:

> What must be correct, or what does the operator need to do next, to get the requested 3MF to the printer?

Use:

```text
operator need / manufacturing invariant
              ↓
application or Model capability
              ↓
CLI representation when needed
```

Do not begin with an available CLI command and invent responsibilities for it.

Inspection, configuration, color analysis, and cleaning are not goals. They exist only to remove uncertainty or obstacles to a correct manufacturing Product.

---

# Common User-Facing Behavior

## Working directory and lifecycle

The CLI operates on the current working directory as project root.

A working directory may contain any combination of:

```text
loose incoming source images
originals/
artifacts/
```

The operator must not need to create internal directories.

A missing collection directory means an empty collection, not an exceptional condition.

A registered Artifact may legitimately exist under `originals/` before BUILD has materialized `artifacts/<artifact_id>/`.

Commands must not confuse:

```text
registered Artifact
```

with:

```text
materialized Artifact workspace
```

when the distinction affects whether an operation can proceed.

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

Expected configuration, planning, build, color, and equivalent application failures must be translated by the UI boundary. Do not indiscriminately catch `Exception`.

When the application knows the next corrective value-chain action, the CLI should suggest it concisely.

For example, if COLORS requires a materialized Artifact:

```text
Error: Artifact 'clean_bg_cat' is not materialized. Try `artifact build clean_bg_cat`.
```

## Lean operator-facing output

Routine output should answer only questions useful to the next operator action.

Prefer:

```text
Artifact
Realization
what happened / current state
whether work remains
3MF or other relevant manufacturing Product
clear corrective action when needed
```

Where information is naturally tabular, prefer Rich tables.

Do not expose internal Stage, resolver, dependency, filesystem, or implementation details unless directly useful.

Paths shown to operators should be concise and useful in the current shell context. When a Product lies beneath the current project root, prefer a path relative to the current working directory rather than a long absolute path.

---

# Current Plan Status

## Previously completed work

The following work has already been established and should not be repeated without new evidence:

### Phase 1 production workflow

- CREATE intake and registration;
- BUILD routine manufacturing;
- current Product reuse;
- 3MF publication and recovery;
- CLEAN maintenance behavior;
- public `create → build → 3MF` acceptance coverage;
- semantic execution events separated from routine presentation;
- lean routine BUILD result output.

### Phase 2 manufacturing visibility

- reusable application manufacturing inspection;
- canonical/custom Realization discovery;
- `current`, `stale`, and `not built` manufacturing state;
- Product availability represented separately from freshness;
- SHOW Rich manufacturing table for a selected Artifact;
- LIST Artifact discovery;
- read-only dependency-aware planning;
- inspection that does not mutate persistent manufacturing state.

These accomplishments remain credited.

## Why the plan is being reopened

Recent real operator use exposed defects and unresolved questions that affect the manufacturing value chain:

1. an Artwork 3MF was observed with 16 artwork color components;
2. the corresponding `artifact.toml` contained 16 `printer_colors` on a five-tool workflow;
3. recolor recovery encountered 16-to-5 color-assignment failures;
4. the exact operation that originally produced the 16-color persistent state is not yet proven;
5. a cold BUILD appears to repeat Artwork prepare/raster/vector work independently for multiple Realizations;
6. COLORS on a registered but unmaterialized Artifact leaks an internal `source` resolution error;
7. expected COLORS/recolor failures can still expose Python tracebacks;
8. SHOW uses long absolute 3MF paths;
9. bare SHOW and the broader situational-awareness model need reconciliation with CREATE, BUILD, LIST, COLORS, and the CLI README;
10. CLI README workflow/presentation details have drifted from current behavior.

The first five items can affect correctness or manufacturing efficiency and therefore precede presentation work.

---

# Phase 3 — Revalidate Manufacturing Correctness and Efficiency

## Goal

Before continuing CLI polish, prove that the ordinary value chain produces the correct manufacturing Product efficiently:

```text
registered source
      ↓
build
      ↓
correct Realizations
      ↓
correct printable colors
      ↓
correct 3MF
```

This phase reopens only the production guarantees implicated by observed evidence. Do not redesign unrelated BUILD or Model behavior.

---

## 3.1 Artwork cross-Realization Product reuse

### Observed behavior

During a cold:

```text
artifact -v build clean_bg_cat
```

multiple Artwork Realizations appeared to execute preparation, rasterization, and vectorization independently.

The observation suggests a possible graph such as:

```text
prepare → raster → vector → extrude → package  artwork_default
prepare → raster → vector → extrude → package  artwork_charm
prepare → raster → vector → extrude → package  artwork_earrings
```

### Required investigation

Do not assume yet that all three upstream stages must be shared.

Review:

- `ARCHITECTURE.md` Product identity and ownership rules;
- Artwork `DEFINITION.md`;
- Stage inputs and parameters for `prepare`, `raster`, `vector`, `extrude`, and `package`;
- canonical Product locations;
- fingerprints;
- dependency bindings;
- BuildPlans for the affected Artwork Realizations; and
- existing incremental/reuse tests.

Determine the **earliest stage at which each Artwork Realization semantically differs**.

The governing invariant is:

> Realizations should not repeat upstream manufacturing work when the required Product is semantically identical and architecture permits that Product to be shared.

If charm/earring/default differences first affect extrusion or packaging, the desired graph may be:

```text
prepare → raster → vector
                       ├── extrude → package  artwork_default
                       ├── extrude → package  artwork_charm
                       └── extrude → package  artwork_earrings
```

If an earlier Variant parameter legitimately affects raster or vector, divergence must occur there instead.

### TDD slice

After resolving Product ownership:

1. establish a cold multi-Realization Artwork build;
2. prove the intended shared upstream Product executes once;
3. prove each Realization still receives the correct downstream Product;
4. prove incremental rebuild invalidation begins at the correct divergence point;
5. prove no Realization consumes another Realization's Product merely because files happen to match.

Do not implement ad-hoc file copying or cache reuse outside authoritative Product/dependency semantics.

### Completion

A multi-Realization Artwork build performs no unnecessary repeated upstream work while preserving canonical Product ownership and correct invalidation.

---

## 3.2 Reproduce and locate the 16-color persistent-state defect

### Observed facts

A real `clean_bg_cat` materialized configuration contained:

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

PrusaSlicer showed `artwork_earrings.3mf` with 16 artwork color objects corresponding to that state.

At another point, normal color analysis of the Artifact reported five measured layers and five best library assignments.

This strongly suggests bad persisted color state, but it does **not yet prove which operation created it**.

`artifact colors clean_bg_cat --recolor=library` is a prime suspect based on operator history, but causation must be reproduced from clean state before changing production code.

### Investigation

Trace:

```text
source artwork
      ↓
measured artwork colors
      ↓
system / printer / library assignments
      ↓
recolor selection
      ↓
persisted printer_colors
      ↓
Artwork extrusion
      ↓
3MF color components
```

Review:

- analysis result structure;
- `--recolor=library` selection;
- `--recolor=printer`;
- Artifact-level versus Realization-level persistence;
- recolor preflight sources;
- `printer_colors` resolution;
- Artwork layer registration;
- extrusion input;
- package/3MF object creation.

### Required invariant

`printer_colors` must represent the intended printable color selection for the applicable scope. An available library/catalog palette must not accidentally become the Artifact's complete printable layer set.

For `--recolor=library`, if existing semantics say the analysis-selected library assignments are the recolor target, persist those selected assignments—not the complete library palette.

Do not hard-code “five” unless printer capacity is normatively five at the owning layer. Tests should express the actual capacity/assignment invariant.

### TDD slices

Prefer two levels:

**Slice A — persistence**

From clean state:

1. construct an Artifact with a known measured color set;
2. provide a library larger than the printable assignment set;
3. perform the actual recolor operation;
4. assert the correct selected colors are persisted at the correct Artifact/Realization scope;
5. assert unrelated Realization overrides remain untouched.

**Slice B — manufacturing consequence**

Build the affected Artwork Realization and prove:

- the expected number of artwork color components exists;
- the components correspond to the selected printable colors;
- structural colors such as loop/hole/base/ridge remain governed by their own Model semantics;
- no complete library palette leaks into the 3MF.

### Completion

The original corruption is reproducible, its owning defect is fixed, and a clean recolor/build cannot generate the observed 16-color manufacturing Product unless 16 colors are actually valid by specification.

---

## 3.3 Recolor recovery and preflight semantics

### Observed behavior

With corrupted 16-color state, Artifact-level recolor failed during `_prepare_artifact_recolor()` with:

```text
Recoloring requires usable existing recolor sources for every applicable Realization:
Palette color count cannot be smaller than measured color count.
Measured 16, palette 5.
```

The message appeared twice, apparently for multiple applicable Realizations.

### Preserve

Artifact-level recolor should not partially mutate persistent state when some required Realization cannot be prepared.

Do not weaken correct color-assignment validation merely to make corrupted state pass.

### Investigate

Determine:

- what constitutes an “existing recolor source”;
- why corrupted generated state is selected as a recolor source;
- whether a clean authoritative source is available for recovery;
- whether recovery should require CLEAN/BUILD, RESET, or another established operation;
- whether the preflight error can identify the failing Realizations.

### Completion

A recolor either succeeds atomically or fails without mutation and with enough structured context for the UI to tell the operator what must be corrected.

---

## 3.4 Production acceptance after critical fixes

Protect the corrected value chain with a small number of acceptance tests:

```text
source
  ↓
create
  ↓
cold multi-Realization build
  ↓
correct shared/reused upstream work
  ↓
correct per-Realization geometry/colors
  ↓
valid 3MFs
```

and, where appropriate:

```text
color analysis
  ↓
explicit recolor
  ↓
build
  ↓
correct printable 3MF
```

Do not duplicate detailed LP/color or geometry assertions already owned below acceptance level.

### Phase 3 completion criterion

Phase 3 is complete when:

- no known critical manufacturing correctness defect remains;
- the 16-color defect has a reproduced root cause and regression coverage;
- Artwork Realizations reuse upstream Products to the extent required by architecture;
- BUILD still produces accessible 3MFs;
- current Products remain reusable;
- invalidation remains dependency-driven; and
- the program is again trustworthy as a production value chain.

---

# Phase 4 — Repair Exception and Recovery Paths

## Goal

Once manufacturing correctness is restored, make exception paths return the operator to the value chain without internal errors or tracebacks.

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

---

## 4.1 COLORS and registered-but-unmaterialized Artifacts

### Observed behavior

After deleting `artifacts/`, the preserved source still existed:

```text
originals/clean_bg_cat.png
```

and `artifact list` still discovered `clean_bg_cat`.

However:

```text
artifact colors clean_bg_cat
```

reported:

```text
Error: Unknown configuration value 'source'.
```

This is a valid lifecycle state leaking an internal configuration-resolution concept.

### Required operator behavior

If COLORS requires materialization before analysis, report that condition in operator terms and provide the clear next value-chain action.

For example:

```text
Error: Artifact 'clean_bg_cat' is not materialized. Try `artifact build clean_bg_cat`.
```

Do not require COLORS itself to materialize the Artifact unless architecture and workflow review establish that as the better reusable operation.

### Bare COLORS

`artifact colors` remains a valid broad operation over applicable Artifacts. It must not be changed to “requires an artifact_id” merely to avoid this lifecycle case.

Design broad-scope behavior deliberately:

- define whether unmaterialized Artifacts are inapplicable/skipped or cause an actionable batch result;
- preserve useful results for applicable Artifacts when appropriate;
- do not silently hide malformed persistent state;
- do not leak `Unknown configuration value 'source'`.

### TDD

Cover:

1. explicit registered-but-unmaterialized Artifact;
2. empty workspace;
3. missing explicitly requested Artifact;
4. broad scope containing materialized and unmaterialized Artifacts;
5. no persistent mutation during read-only analysis.

---

## 4.2 Expected error translation and suggested actions

### Observed failures

Expected operator/domain failures have escaped as Python tracebacks, including:

- `ColorError`;
- recolor-preflight `RuntimeError`; and
- internal configuration-resolution errors.

### Required behavior

Every public CLI interaction should either:

- produce useful operator output; or
- produce a concise expected error.

Expected incorrect use and expected domain/application failures must not expose Python tracebacks.

Do not blanket-catch unexpected programming defects.

Where the next corrective action is known, include it.

Examples:

```text
unmaterialized Artifact
    → Try `artifact build <artifact_id>`.

missing Artifact
    → identify that the Artifact is not defined.

unavailable Realization
    → identify the Artifact/Realization.

recolor preflight failure
    → identify affected Realization(s) and corrective condition.
```

### Implementation boundary

Prefer typed/structured application errors when the reusable operation knows the semantic condition. Click should translate those conditions into CLI prose.

Do not encode deep domain diagnosis as string matching in the CLI.

### Completion

Expected COLORS/configuration/planning/recolor failures are concise, contextual, actionable, and traceback-free.

---

## 4.3 CONFIG authored customization

Retain the existing distinction:

```text
config
    authored configuration

show
    effective manufacturing state
```

Preserve:

- Artifact-level authored configuration;
- Realization-specific authored customization;
- custom Realization creation/mutation;
- sparse configuration;
- canonical Realizations that do not appear falsely authored.

Review actual workflow friction only after critical correctness and recovery work is complete.

Developer-oriented capabilities currently attached to CONFIG, such as:

```text
--list-models
--workplan
--dump
```

remain candidates for later relocation, not immediate manufacturing work.

### Phase 4 completion criterion

Exception paths identify the obstacle, offer the next useful action when known, and return naturally to BUILD without making CONFIG/COLORS/CLEAN mandatory.

---

# Phase 5 — Reconcile Manufacturing Visibility and Situational Awareness

## Goal

Polish inspection only after manufacturing and recovery are correct.

The commands should answer distinct operator questions while fitting the same value chain.

Conceptually:

```text
artifact create
    What incoming work can enter the value chain?

artifact list
    What managed Artifact IDs exist?

artifact show
    What manufacturing state/products exist?

artifact build
    What work is necessary to make requested Products current?

artifact colors
    Where do physical colors require attention?
```

Bare invocations may provide command-relevant situational awareness. They need not all have identical output or scope.

---

## 5.1 SHOW paths

### Observed behavior

`artifact show clean_bg_cat` renders a Rich table, but the 3MF column contains long absolute paths such as:

```text
/home/.../projects/artifacts/clean_bg_cat/artwork_default.3mf
```

which are then truncated.

### Required behavior

Keep the reusable application result as a real `Path`.

At the CLI presentation boundary, when the Product is beneath the current project root, display a path relative to the current working directory:

```text
artifacts/clean_bg_cat/artwork_default.3mf
```

Do not alter canonical Product identity or persistence to achieve this presentation improvement.

---

## 5.2 Bare SHOW

Current selected-Artifact SHOW already answers:

> What can I manufacture from this Artifact, and what already exists?

Review whether bare:

```text
artifact show
```

should provide a workspace-level manufacturing overview.

Do **not** define bare SHOW merely as a prettier LIST.

LIST owns identity discovery. SHOW should earn its existence by exposing manufacturing state or Products useful to deciding the next manufacturing action.

Review the existing bare CREATE and bare BUILD situational-awareness behavior before specifying SHOW so the commands complement rather than duplicate one another.

Potential scope model, subject to design and RED:

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

---

## 5.3 LIST presentation

Current LIST is simple line-oriented output.

The CLI README currently says naturally tabular Artifact lists are candidates for Rich presentation, while also saying naturally simple output should remain simple.

Resolve this intentionally.

Possible outcomes include:

- keep LIST intentionally plain and pipeline-friendly, then clarify README; or
- use a minimal Rich table if that materially improves operator discovery.

Do not add visual weight solely for consistency with SHOW.

---

## 5.4 Realization drill-down

`artifact show <artifact> --realization <realization>` currently narrows the manufacturing table.

Do not add effective-configuration detail merely because a drill-down option exists.

If the selected one-row manufacturing view already answers the operator's question, keep it lean.

CONFIG remains the authored-configuration surface.

---

## 5.5 CLI README reconciliation

Update `src/lowkey_artifact_builder/cli/README.md` only after the command behavior is settled.

Known items to reconcile include:

- bare CREATE already provides source/Artifact situational awareness, so a preliminary LIST may no longer be necessary in the routine new-customer workflow;
- bare SHOW semantics, if added;
- LIST presentation decision;
- relative Product paths;
- registered-versus-materialized Artifact behavior;
- actionable recovery messages;
- broad command scope.

### Phase 5 completion criterion

The operator can discover work, inspect manufacturing state, identify an existing usable 3MF, and determine the next action without unnecessary duplication among CREATE, LIST, SHOW, BUILD, and COLORS.

---

# Phase 6 — Consolidate Secondary and Developer Surfaces

## Goal

After production, recovery, and inspection workflows are stable, remove remaining historical CLI inconsistencies without disturbing the established value chain.

This phase contains no speculative manufacturing capability.

## 6.1 Historical public syntax

Review remaining options and aliases against actual operator value, including historical Variant-oriented syntax such as:

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

Retain, relocate, or remove based on those answers.

## 6.2 Developer operations

Review:

- independent Stage execution;
- Model/workplan inspection;
- CONFIG developer flags;
- other diagnostic/developer capabilities.

Preserve useful architectural capabilities without making the production CLI present every engine capability.

## 6.3 Final help and message consistency

Review:

```text
artifact --help
artifact <command> --help
```

Ensure help describes operator purpose rather than implementation mechanics.

Review routine messages for:

- terse success output;
- consistent Artifact/Realization terminology;
- actionable expected errors;
- suggested next actions when known;
- useful batch summaries;
- obvious manufacturing Products;
- relative useful paths; and
- no unnecessary Stage/Model/Variant detail.

Do not force identical output shapes on commands with different purposes.

---

# Final End-to-End Acceptance

Protect a small number of complete workflows.

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

```text
Artifact
   ↓
shared upstream work where semantically identical
   ↓
Realization-specific divergence
   ↓
correct 3MFs
```

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

## Manufacturing inspection

```text
known Artifact
      ↓
show
      ↓
choose existing/current Realization
   or
identify missing/stale work
```

## Color exception

```text
colors
   ↓
optional explicit recolor
   ↓
correct persisted printable colors
   ↓
build
   ↓
correct 3MF
```

## Unmaterialized exception

```text
registered Artifact
      ↓
colors requires materialization
      ↓
actionable suggestion: build
      ↓
build
      ↓
return to optional color workflow
```

## Maintenance

```text
clean selected generated work
      ↓
build
      ↓
regenerated correct 3MF
```

Acceptance tests should remain focused on user-visible manufacturing value. Detailed geometry, configuration resolution, graph planning, Product-state, and color-assignment behavior belongs in lower-level tests.

---

# Final Completion Criterion

The work is complete when the application supports this objective:

> Move customer artwork to a **correct, printable 3MF** with the fewest necessary decisions, actions, and computations.

Specifically:

- incoming artwork can be registered without manual workspace preparation;
- Artifact identity remains operator/client assigned and opaque to the build system;
- registered and materialized Artifact states are handled intentionally;
- BUILD makes requested manufacturing work current;
- current Products are reused;
- semantically identical upstream work is not unnecessarily repeated across Realizations;
- Realizations diverge at the correct dependency boundary;
- printable color selection cannot accidentally expand into an inappropriate complete library palette;
- recolor persistence respects Artifact/Realization scope;
- resulting 3MF color components reflect the correct manufacturing color state;
- the resulting 3MF is obvious and retrievable;
- missing convenience publication does not require unnecessary geometry rebuilding when the canonical Product is current;
- CLEAN provides reliable production maintenance;
- LIST helps discover Artifact identities;
- SHOW exposes useful Realization, state, and Product information when inspection is needed;
- displayed Product paths are useful from the operator's current working directory;
- CONFIG remains an exception/customization path;
- COLORS remains an optional physical-color path;
- expected errors are concise and traceback-free;
- clear recovery actions are suggested when the application knows the next value-chain step;
- routine output is lean and focused on the next operator action;
- application workflow behavior is reusable independently of Click; and
- future CLI, TUI, GUI, browser, or API clients can present the same underlying manufacturing capabilities without reconstructing them.

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

The steady-state operator workflow is not a mandatory sequence of every command.

It is:

```text
create
   ↓
build
   ↓
use the correct 3MF
```

Everything else exists only when it removes an obstacle, corrects a manufacturing defect, reduces unnecessary work, or helps the operator make the next useful decision.

