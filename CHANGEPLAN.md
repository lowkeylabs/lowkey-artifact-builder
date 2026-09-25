# CHANGEPLAN

## Purpose

Refactor and polish the user-facing workflow of `lowkey-artifact-builder`
around the actual manufacturing value chain.

The operator's goal is:

> Move customer artwork to a correct, printable 3MF with the fewest necessary
> decisions and actions.

The primary value-chain commands are:

```text
customer artwork
      ↓
artifact create
      ↓
managed Artifact
      ↓
artifact build
      ↓
printable 3MF
      ↓
slicer / share / upload / print
```

`create` and `build` therefore define the ordinary production path.

Other commands support that path when the operator needs discovery,
explanation, customization, correction, color selection, or maintenance:

```text
list
show
config
colors
clean
```

These commands are helpers or exception paths. They are powerful operator
controls, but they must not become mandatory ceremony before routine
manufacturing.

Given an `artifact_id`, the operator should be able to get from that ID to the
desired printable 3MF quickly, while being shown only the decisions or
corrective actions that actually require attention.

This plan is a workflow and CLI refactor. It does not redefine Artifact,
Variant, Realization, Product, configuration, build planning, Product state, or
Model semantics. Those remain owned by `ARCHITECTURE.md` and the applicable
Model `DEFINITION.md`.

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

`ARCHITECTURE.md` and the Model definitions remain the permanent normative
specifications. The CLI README describes the intended human-facing CLI
workflow. Repository HEAD defines the current implementation. This file
describes temporary work required to bring HEAD into alignment.

Before each TDD slice:

1. review the relevant specifications and CLI README;
2. review current HEAD and existing tests;
3. credit behavior HEAD already satisfies;
4. identify the next unmet operator workflow;
5. resolve any remaining semantic question before testing it;
6. add a coherent behavioral test slice;
7. observe RED for the intended reason;
8. implement the behavior;
9. run focused tests and the complete quality suite;
10. commit and reevaluate HEAD.

TDD slices do not need to correspond to one feature or one small production
change.

For this refactor, prefer a larger coherent slice when several closely related
behaviors together establish one operator workflow and can still produce
understandable RED failures.

The useful unit is the smallest **workflow capability** that can be designed,
tested, implemented, and committed coherently.

CLI tests should protect:

- user intent;
- command and option interpretation;
- scope;
- validation;
- useful errors;
- operator-facing output; and
- translation into application operations.

They should not duplicate Model, engine, configuration-resolution,
Product-state, or color-matching tests already protected below the CLI.

---

# Incremental Delivery Rule

Every phase in this plan must end at a production-capable stopping point.

Later phases may improve discovery, explanation, customization, maintenance, or
specialized control, but completion of a later phase must not be required for
the operator to obtain useful manufacturing Products from capabilities
established by an earlier phase.

In particular:

```text
Phase 1
    must leave create → build → 3MF usable for production

Phase 2
    adds better discovery and manufacturing visibility
    without making inspection mandatory

Phase 3
    improves exception/customization paths
    without changing the ordinary production requirement

Phase 4
    consolidates secondary/developer surfaces and presentation
```

At the end of every phase, reevaluate the complete operator workflow before
starting the next phase.

---

# UI Independence

The CLI is one client of the application. It is not the application itself.

The same manufacturing workflow may later be presented through:

```text
CLI
TUI
GUI
browser/API client
```

Reusable workflow behavior therefore belongs below the UI boundary.

The preferred structure is:

```text
CLI / TUI / GUI / API
          │
          ▼
 reusable application operations
          │
          ▼
 configuration / planning / engine / Products
```

Application operations should return structured results or expose semantic
events that can be consumed by different user interfaces.

UI-specific concerns include:

- Click argument and option parsing;
- terminal prompts;
- terminal formatting;
- progress presentation;
- human-facing CLI error translation.

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

Do not solve a workflow problem merely by adding orchestration to
`cmd_create.py`, `cmd_build.py`, or another Click command module when the
behavior is useful to other clients.

A workflow capability is not complete merely because it can be driven from a
Click callback. Its underlying operation should be reusable without invoking or
emulating the CLI.

Testing should reflect that boundary:

```text
application tests
    prove reusable workflow behavior

CLI tests
    prove argument → operation translation
    and result → human-facing presentation
```

Existing engine/configuration APIs need not be wrapped gratuitously. Introduce
or refactor an application-level operation when doing so removes UI-owned
workflow logic or provides a capability that multiple interfaces can use.

---

# Existing Behavior to Preserve

Significant work has already gone into the CLI in previous change plans.

In particular:

```text
create
build
config
clean
colors
```

already implement substantial production behavior.

`create`, `build`, `config`, and `clean` should require only minimal
refactoring, if any, unless review identifies an actual obstacle to a more
efficient manufacturing workflow.

`colors` already has substantial completed analysis and recoloring behavior and
should likewise retain its established semantics.

Treat these commands as existing capabilities, not blank surfaces to redesign.

Preserve established create, build, and clean semantics unless we identify a specific operator-workflow improvement that justifies changing them. Optimize the value chain around those commands rather than redesigning those commands from first principles.

The existing create, build, and clean workflows are the starting point for the production value chain. Significant previous CHANGEPLAN work established their semantics and tests. This plan should preserve those behaviors by default and make only focused changes needed to improve the operator workflow, presentation, reuse across interfaces, or value-chain efficiency.

Bare commands may intentionally differ from their mutating forms. In particular, bare commands such as artifact create and artifact build may be read-only situational-awareness operations that reduce operator cognitive load by showing current state and guiding the operator toward useful next actions. This is a deliberate CLI design pattern, not behavior to be factored into separate commands.

“Thin CLI” means that reusable domain/application behavior should live below the presentation layer. It does not require one command to correspond to one application operation, nor does it prohibit a command from selecting read-only versus mutating behavior according to its arguments.

We may intentionally change an established command if implementation experience
shows that a different interaction materially reduces operator work or makes
the manufacturing path clearer. Such a change must be justified by the value
chain rather than by a desire for syntactic uniformity.

Preserve established behavior including:

- `artifact create` ingestion and operator-assigned Artifact identity;
- canonical Realization discovery through configuration rather than CLI-owned
  reconstruction;
- the substantial Realization-oriented and incremental behavior already
  implemented by `artifact build`;
- incremental Product-state evaluation and reuse of current Products;
- `artifact config` Artifact/Realization customization;
- `artifact clean` Artifact/Realization maintenance scope;
- `artifact colors` analysis and recoloring;
- normal configuration precedence;
- dependency-driven minimal realization;
- canonical Stage Product ownership; and
- independent Stage execution through a complete `StageContext`.

Do not reopen established Model, build-engine, configuration, or color
semantics merely as part of CLI polishing.

---

# Value-Chain Design Principle

Evaluate the CLI from the operator's position in the manufacturing workflow,
not by trying to make every command look structurally identical.

The design question is:

> What does the operator need to do next to get the requested 3MF to the
> printer?

Then determine which reusable application capability and UI operation best
supports that step.

Use:

```text
operator need
      ↓
application capability
      ↓
CLI representation
```

not:

```text
available CLI command
      ↓
invent additional responsibilities for it
```

Inspection is not itself the goal.

Configuration is not itself the goal.

Color analysis is not itself the goal.

Cleaning is not itself the goal.

Each exists only to remove an obstacle, answer a necessary question, or support
the creation of the correct manufacturing Product.

---

# Common User-Facing Behavior

These conventions apply where they improve the operator workflow. They do not
require every command to support every possible scope.

## Working directory

The CLI operates on the current working directory as the project root.

A working directory may contain any combination of:

```text
loose incoming source images
originals/
artifacts/
```

The operator must not need to create internal storage directories before using
the application.

A missing collection directory means that the corresponding collection is
empty. It is not itself an exceptional condition.

## Scope

Where applicable:

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

Support a scope only when it makes the operation more useful.

An explicitly supplied Artifact or Realization is an assertion that the
addressed object exists. Failure should be reported as a concise
operator-facing error.

## Empty, absent, and broken state

Distinguish:

```text
empty collection
    normal result

explicitly requested object absent
    operator-facing error

discovered persistent object malformed or inconsistent
    operator-facing configuration/application error
```

Broad operations against an empty workspace should not fail merely because
`artifacts/` or `originals/` is absent.

Expected configuration, planning, build, and equivalent application errors
must be translated by the UI boundary.

Do not indiscriminately catch unexpected programming defects.

## Lean operator-facing output

Routine CLI output should answer only questions useful to the next operator
action.

Prefer information such as:

```text
Artifact
Realization
what happened
whether work remains
3MF or other relevant manufacturing Product
```

Where operator-facing information is naturally tabular, prefer Rich tables with concise headers rather than manually formatted columns or unstructured repeated lines.

Avoid narrating internal orchestration.

Do not expose Model, Variant, Stage, dependency, resolver, filesystem, or
implementation details unless they are directly useful for the requested
operation.

Successful routine commands should be terse.

Errors should identify the actionable Artifact/Realization and problem without
a Python traceback for expected failures.

Batch output should make successes, skipped/current work, and failures easy to
distinguish without overwhelming the operator with per-stage noise.

---

# Phase 1 — Polish the Production Value Chain

## Goal

Make the existing production path clean, direct, and production-ready:

```text
incoming customer artwork
      ↓
create
      ↓
Artifact
      ↓
build
      ↓
printable 3MF
```

`clean` supports this path when generated work must intentionally be discarded.

This phase begins by reviewing and preserving the substantial existing behavior
of `create`, `build`, and `clean`.

The expected work is primarily cleanup, application/UI separation, consistent
workspace behavior, and leaner operator-facing presentation.

Do not assume these commands require structural redesign.

At the end of Phase 1, the program must already be fully usable for routine
value creation without any work from later phases.

---

## 1.1 Review the existing production path end to end

Before changing individual commands, exercise current HEAD as an operator.

Cover at least:

```text
new source → create → build → 3MF

existing Artifact → build selected Realization → 3MF

current Realization → build → reuse → 3MF

clean → build → regenerated 3MF
```

Record only actual discrepancies from the intended workflow.

Pay particular attention to:

- unnecessary questions or command steps;
- noisy or implementation-oriented output;
- missing or unclear 3MF presentation;
- inconsistent empty-workspace behavior;
- expected errors that leak tracebacks;
- duplicated orchestration in Click modules;
- situations where current Products are rebuilt unnecessarily; and
- situations where an operator cannot easily tell what Product resulted.

Use this review to choose the first coherent TDD slice.

---

## 1.2 `create`: make intake quiet and direct

`create` is the boundary between unmanaged customer source material and a
managed Artifact.

The operator assigns the Artifact identity during creation.

For example:

```text
artifact create baird-lilo --source lilo.png
```

The `artifact_id` remains opaque to the build system. `baird-lilo` may encode an
operator's business convention, but the application must not infer customer,
source, Variant, or Product semantics from that structure.

Bare:

```text
artifact create
```

may discover incoming source images according to the established ingestion
workflow.

### Preserve unless a discrepancy is found

Current `create` work should already cover much of:

- loose-source discovery;
- explicit source registration;
- operator-selected Artifact identity;
- duplicate recognition;
- managed source preservation;
- workspace materialization as needed; and
- batch ingestion.

Do not rewrite these behaviors merely to fit a new internal abstraction.

### Refactor where useful

Ensure that:

- no manual creation of `originals/` or `artifacts/` is required;
- no-source behavior is concise and intentional;
- collisions and inconsistent managed state are useful operator errors;
- successful output identifies what was created without narrating internal
  filesystem work; and
- reusable ingestion behavior is not trapped inside Click callbacks.

### Completion

Incoming customer artwork can become a managed Artifact with the minimum
necessary operator input.

---

## 1.3 `build`: make the requested Product current

`build` is the principal value-producing command.

Its operator meaning is:

> Make the requested manufacturing Product current.

The operator should not need to think in terms of Stages or dependency
execution during routine production.

### Preserve substantial existing behavior

Previous work has already established significant `build` behavior including:

- Artifact discovery;
- canonical and custom Realization discovery;
- Realization-oriented execution;
- incremental Product-state evaluation;
- current Product reuse;
- Artifact materialization;
- batch execution;
- dry-run/status behavior;
- rebuild behavior;
- semantic execution events; and
- independent Stage execution.

Credit this behavior before designing changes.

### Routine manufacturing

A selected Realization should remain directly buildable:

```text
artifact build baird-lilo --realization shape_ornament
```

Broad build behavior should remain useful where it reduces operator work.

Incremental execution must continue to reuse current Products and realize only
the required dependency closure.

### Presentation

Routine build output should emphasize:

```text
Artifact / Realization
current, built, or failed
resulting 3MF
```

It should not require the operator to interpret a stream of Stage events unless
that detail is explicitly requested or needed to diagnose a failure.

If current semantic execution events are useful to future UIs, preserve them
below the presentation layer while making normal CLI rendering leaner.

### Historical selection syntax

Review public Variant-oriented syntax such as:

```text
--variant
--all-variants
```

only if it interferes with the efficient production workflow.

Do not remove working capability merely to make the syntax uniform.

Variants remain architecturally essential regardless of whether a particular
Variant selector remains part of the routine CLI.

### Completion

Given an Artifact and desired Realization, the operator can make the required
manufacturing Product current with minimal interaction and clear output.

---

## 1.4 Make the resulting 3MF obvious and accessible

BUILD creates value because its manufacturing Product can leave the builder and
enter the manufacturing/delivery workflow.

```text
Artifact
   ↓
Realization
   ↓
build
   ↓
3MF
══════════════════════ delivery boundary
   ↓
slicer / share / upload / print
```

HEAD already publishes a realization-named convenience 3MF beside
`artifact.toml` when a package Stage executes.

The canonical Stage Product remains authoritative.

### Review publication/retrieval behavior

Exercise at least:

```text
package executes
    → canonical Product exists
    → realization-named 3MF is available

package already current
    → canonical Product reused
    → operator can still obtain the 3MF

canonical Product current
published convenience copy absent
    → operator can obtain the 3MF without geometry rebuild
```

The application may retrieve the canonical Product directly, restore the
published convenience copy, or expose a small reusable Product
retrieval/publication operation.

Do not make canonical Product ownership dependent on CLI presentation.

Do not add PrusaSlicer-, email-, or upload-specific integration in this phase.
Those are consumers of the Product retrieval capability.

### Completion

A successful or already-current build leaves the operator with an obvious,
accessible printable 3MF.

---

## 1.5 `clean`: production maintenance without friction

`clean` supports production when generated work needs to be discarded and
regenerated.

It is not part of the normal happy path, but it must be reliable enough that
Phase 1 is independently usable.

Preserve existing Artifact and Realization cleaning semantics.

Review:

```text
artifact clean dog

artifact clean dog --realization shape_ornament

artifact clean --realization shape_ornament

artifact clean --force
```

as applicable to current behavior.

Ensure that cleaning:

- removes only intended generated Products;
- preserves Artifact configuration and Artifact-owned inputs;
- uses the same useful Artifact/Realization terminology as build;
- handles empty collections sensibly;
- reports expected errors concisely; and
- leaves subsequent build behavior correct.

Do not expand `clean` into Artifact deletion.

### Completion

The operator can intentionally discard generated work and return immediately to
the normal `build → 3MF` path.

---

## 1.6 Phase 1 workflow slices

Prefer workflow-sized TDD slices over artificially tiny command edits.

Reasonable slices include:

### Slice A — routine single-Artifact production

```text
source
  ↓
create
  ↓
build selected/default manufacturing work
  ↓
3MF clearly available
```

Cover lean success output and current-Product reuse where they belong to the
same observable workflow.

### Slice B — workspace and batch production

Cover coherent behavior for:

- empty workspace;
- loose intake;
- multiple Artifacts;
- independent failures;
- useful batch summaries; and
- expected error translation.

Do not force unrelated edge cases into this slice merely because they involve a
CLI.

### Slice C — maintenance and recovery

```text
current Product
      ↓
clean selected scope
      ↓
build
      ↓
correct regenerated 3MF
```

Also cover recovery/access when the canonical current Product exists but an
operator-facing convenience publication is missing.

The exact slice boundaries should be chosen after reviewing HEAD and existing
tests.

---

## Phase 1 Completion Criterion

Phase 1 is complete when the program is independently useful for routine
production.

For artwork whose defaults already describe the desired manufactured object:

```text
create → build → 3MF
```

is sufficient.

The operator does not need `list`, `show`, `config`, or `colors` merely to
complete an ordinary job.

`clean` is available when maintenance is required.

Successful routine output is terse and focused on value created.

Expected errors are actionable and do not expose tracebacks.

The underlying production operations are reusable by a future CLI, TUI, GUI, or
API presentation.

---

# Phase 2 — Add Manufacturing Visibility

## Goal

Improve discovery and inspection without changing the Phase 1 production path.

Phase 1 remains fully usable if Phase 2 is never implemented.

Phase 2 helps the operator answer questions that arise around the production
workflow:

```text
What Artifact is this?

What can I manufacture from it?

What has already been manufactured?

Is the desired Product current?

Where is the 3MF?

Does anything actually require attention?
```

The primary commands are:

```text
artifact list
artifact show
```

Inspection exists to remove uncertainty. It must not become a prerequisite for
`build`.

---

## 2.1 `list`: discover managed Artifacts

An operator may manage many Artifacts and may want to review existing IDs before
registering incoming artwork.

`artifact list` answers:

> What managed Artifacts do I already have?

### Required behavior

```text
artifact list
```

lists managed Artifact IDs.

It should:

- use authoritative Artifact discovery;
- require no build planning;
- require no generated Products;
- work in an empty workspace; and
- remain concise.

For example, an empty workspace may report:

```text
No artifacts found.
```

Do not overload:

```text
artifact list dog
```

to mean Realization discovery.

Once an Artifact is known, its Realizations belong to the Artifact
manufacturing view.

### Completion

The operator can efficiently review existing Artifact identities before
choosing an ID for new incoming artwork or selecting existing work.

---

## 2.2 `show`: manufacturing overview for an Artifact

Given an Artifact, the useful first question is:

> What can I manufacture from this Artifact, and what already exists?

Use:

```text
artifact show baird-lilo
```

to present the effective canonical and custom Realizations together with the
facts needed for the next manufacturing decision.

Conceptually:

```text
Realization          Type       State       3MF
artwork_default      built-in   current     artwork_default.3mf
shape_default        built-in   not built   —
shape_ornament       built-in   current     shape_ornament.3mf
large-ornament       custom     stale       large-ornament.3mf
```

Exact formatting is presentation detail.

The operator should be able to determine:

- which Realizations are available;
- which are canonical and which are customized when that distinction helps;
- whether a Realization is missing, stale, or current in useful operator terms;
- whether a manufacturing 3MF exists; and
- whether any action is required before using it.

State and Product availability are separate facts.

A stale Realization may still have an existing 3MF. Do not hide an existing
Product merely because newer inputs make it stale.

Use authoritative Realization discovery and existing Product-state semantics.
Do not reconstruct those rules in CLI presentation code.

### Current HEAD discrepancy

Current `show` is primarily a resolved-configuration view and exposes
Variant-oriented selection.

Refactor only what is necessary to make it answer the operator's manufacturing
question.

### Completion

Given an `artifact_id`, the operator can see the shortest path from that
Artifact to the desired printable 3MF.

---

## 2.3 Realization drill-down

When the manufacturing overview shows that explanation is useful:

```text
artifact show baird-lilo --realization shape_ornament
```

should explain the effective Realization that would be manufactured.

This is a drill-down from the manufacturing view, not a required step before
build.

Resolve the Realization through normal configuration/Realization semantics
rather than using Variant-oriented CLI build planning merely to obtain a
resolver.

Useful provenance may be shown where it helps explain an effective value.

Do not make `show` synonymous with authored `config`.

---

## 2.4 Shared discovery and state operations

If `list`, `show`, `build`, or a future UI need the same Artifact,
Realization, Product, or state information, expose that information through
reusable application operations.

Avoid structures such as:

```text
cmd_show.py
    reconstructs manufacturing state

cmd_build.py
    reconstructs manufacturing state differently

future GUI
    must reconstruct it a third time
```

Prefer:

```text
application manufacturing view/state
       ├── CLI
       ├── future TUI
       ├── future GUI
       └── API
```

Keep presentation-specific tables and prose in the UI layer.

---

## Phase 2 Completion Criterion

Phase 2 is complete when:

- Phase 1's `create → build → 3MF` workflow remains sufficient for routine work;
- `list` makes existing Artifact discovery easy;
- `show` makes available Realizations, useful state, and existing 3MFs visible;
- the operator can identify whether action is actually required;
- inspection does not mutate persistent state; and
- the underlying inspection/state capability is reusable outside the CLI.

The program remains independently production-capable at this stopping point.

---

# Phase 3 — Refine Exception and Customization Paths

## Goal

Improve the controls used when the ordinary production path does not already
produce the desired manufacturing result.

The ordinary path remains:

```text
create → build → 3MF
```

Exception paths branch from it only when needed.

Typical examples are:

```text
configuration exception
    config → build → 3MF

color exception
    colors [→ recolor] → 3MF

maintenance exception
    clean → build → 3MF
```

Phase 3 must not make these commands prerequisites for routine production.

---

## 3.1 `config`: authored customization

`config` answers:

> What have I explicitly configured, or what do I need to customize?

Preserve the substantial existing Artifact/Realization configuration behavior.

```text
artifact config baird-lilo
```

should remain focused on authored Artifact configuration.

```text
artifact config baird-lilo --realization shape_ornament
```

should remain focused on authored customization for that Realization.

A canonical Realization with no explicit customization should not be made to
look as though all inherited/default values were authored in `artifact.toml`.

Existing mutation and custom-Realization creation behavior should be preserved
unless actual workflow use identifies unnecessary friction.

### Separate authored and effective configuration

`config` owns authored configuration.

`show --realization` may explain the effective manufacturing configuration.

Do not make the commands duplicate each other.

### Misplaced developer inspection

Review Model/developer inspection currently attached to `config`, including
capabilities such as:

```text
--list-models
--workplan
--dump
```

If these remain useful, give them an explicit developer-oriented home rather
than forcing Artifact configuration to serve unrelated purposes.

Do not silently discard useful developer capability.

### Completion

The operator enters `config` only when the manufactured Artifact requires
customization or authored configuration needs inspection.

---

## 3.2 `colors`: physical-color exception

`colors` answers:

> Do the physical printing colors require operator attention?

Preserve the established color-analysis and recoloring semantics.

Without `--recolor`, `artifact colors` remains read-only analysis.

Mutation remains explicit through:

```text
--recolor=printer
--recolor=library
--recolor=reset
--recolor=reset-all-realizations
```

Catalog remains advisory and cannot be selected as a recolor target.

Artifact-level recolor must continue to preserve explicit Realization-level
`printer_colors`.

Realization-level recolor affects only the selected Realization.

Artwork color rows remain independently printable Artifact colors.

Model-owned structural printing colors must not be silently folded into
Artwork's global one-to-one color assignment.

### Refactor only operator interaction

Review `colors` for:

- leaner output where possible;
- empty-workspace behavior;
- concise expected errors;
- Artifact/Realization scope consistency; and
- reusable application behavior beneath Click presentation.

Do not reopen the assignment algorithm or persistence rules without evidence of
an actual defect.

### Completion

The operator uses `colors` only when physical color choice requires attention,
and can then return immediately to the manufacturing workflow.

---

## 3.3 Exception-path guidance

Where useful, `show`, `build`, or another manufacturing operation may identify
that attention is required.

Such guidance should identify the problem and the appropriate next action
without forcing the action.

Conceptually:

```text
desired Realization current
    → use 3MF

desired Realization stale/missing
    → build

configuration requires customization
    → config

physical colors require operator choice
    → colors
```

Do not turn these into a rigid wizard or mandatory sequence.

A future GUI or TUI may render the same structured conditions as buttons,
warnings, or contextual actions.

---

## Phase 3 Completion Criterion

Phase 3 is complete when:

- the ordinary `create → build → 3MF` workflow remains unchanged;
- authored configuration has a focused operator surface;
- effective configuration remains distinguishable from authored configuration;
- color analysis/recoloring remains an optional physical-color control;
- exception paths return naturally to the manufacturing path;
- no exception command becomes mandatory ceremony; and
- reusable operations remain UI-independent.

The program remains independently production-capable at this stopping point.

---

# Phase 4 — Consolidate Secondary and Developer Surfaces

## Goal

After the production and exception workflows are stable, remove remaining
historical CLI inconsistencies without disturbing the established value chain.

This phase contains no speculative manufacturing capability.

---

## 4.1 Review historical public syntax

Review remaining public options and aliases against actual operator value.

Candidates may include historical Variant-oriented normal-workflow syntax such
as:

```text
--variant
--all-variants
```

Do not remove syntax solely because another form appears more uniform.

For each candidate ask:

1. Does an operator still need this capability?
2. Is it part of routine manufacturing?
3. Is it an exception/customization capability?
4. Is it primarily a developer capability?
5. Does another established operation already express the need more directly?

Retain, relocate, or remove behavior based on those answers.

---

## 4.2 Developer operations

Review independent Stage execution, Model/workplan inspection, and other
developer-oriented capabilities.

Preserve architectural capabilities that remain useful.

Keep them from complicating the routine production surface.

A separate developer-oriented command surface is acceptable if it provides a
clearer boundary.

Do not make the production CLI responsible for presenting every engine
capability.

---

## 4.3 Final help and message consistency

Review:

```text
artifact --help
artifact <command> --help
```

after command responsibilities are stable.

Ensure help describes operator purpose rather than implementation mechanics.

Review routine messages across commands for:

- terse successful output;
- consistent Artifact/Realization terminology;
- actionable expected errors;
- useful batch summaries;
- obvious manufacturing Products; and
- no unnecessary Stage/Model/Variant detail.

Do not force identical output shapes on commands with different operator
purposes.

---

## 4.4 End-to-end acceptance

Protect a small number of complete workflows rather than reproducing every
focused command test.

### Routine new work

```text
incoming artwork
      ↓
create
      ↓
build
      ↓
3MF
```

### Existing current work

```text
known Artifact
      ↓
build or show
      ↓
current Product reused
      ↓
3MF
```

### Manufacturing inspection

```text
known Artifact
      ↓
show
      ↓
choose existing/current Realization
   or
identify missing/stale work
```

### Configuration exception

```text
config customization
      ↓
build
      ↓
correct 3MF
```

### Color exception

```text
colors
      ↓
optional recolor
      ↓
operator-ready 3MF
```

### Maintenance

```text
clean selected generated work
      ↓
build
      ↓
regenerated 3MF
```

Keep these acceptance tests focused on user-visible value. Detailed geometry,
configuration resolution, graph planning, Product-state, and color-assignment
behavior belongs in existing lower-level tests.

---

## Phase 4 Completion Criterion

The public CLI presents a coherent manufacturing workflow while remaining a
thin client over reusable application capabilities.

Routine production remains:

```text
create → build → 3MF
```

Everything else exists to make that path easier when the ordinary case needs
discovery, explanation, customization, correction, or maintenance.

---

# Final Completion Criterion

The refactor is complete when the application supports this operator objective:

> Move customer artwork to a correct, printable 3MF with the fewest necessary
> decisions and actions.

Given an `artifact_id`, the operator can get from that ID to the desired
printable 3MF quickly while being shown only decisions or corrective actions
that actually require attention.

Specifically:

- incoming artwork can be registered without manual workspace preparation;
- Artifact identity remains operator/client assigned and opaque to the build
  system;
- `build` makes requested manufacturing work current;
- current Products are reused;
- the resulting 3MF is obvious and retrievable;
- missing convenience publication does not require unnecessary geometry
  rebuilding when the canonical Product is already current;
- `clean` provides reliable production maintenance;
- `list` helps discover managed Artifact identities;
- `show` exposes useful Realization, state, and Product information when
  inspection is needed;
- `config` is an exception/customization path rather than routine ceremony;
- `colors` is an exception/physical-color path rather than routine ceremony;
- expected errors are concise and actionable;
- routine output is lean and focused on the next operator action;
- application workflow behavior is reusable independently of Click; and
- future CLI, TUI, GUI, browser, or API clients can present the same underlying
  manufacturing capabilities without reconstructing them.

The target mental model is:

```text
                    ┌──────── list / show ────────┐
                    │       when uncertain         │
                    │                              ▼
customer artwork → create → Artifact → build → printable 3MF → printer
                                  ▲         │
                                  │         │
                    ┌─────────────┘         │
                    │                       │
              config / colors               │
              when customization            │
              requires attention            │
                                            │
                         clean ──────────────┘
                         when generated work
                         must be discarded
```

The steady-state operator workflow is not a mandatory sequence of every
available command.

It is:

```text
create
   ↓
build
   ↓
use the 3MF
```

with every other capability available only when it adds value.
