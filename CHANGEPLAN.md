# CHANGEPLAN

## Purpose

Continue refining `lowkey-artifact-builder` around the manufacturing value
chain established by the current repository HEAD.

The operator's ordinary goal is:

> Move customer artwork to a **correct, printable 3MF** with the fewest
> necessary decisions, actions, and computations.

The normal production path is intentionally short:

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

`create` and `build` define the ordinary value chain. `show`, `config`,
`colors`, and `clean` support that path when the operator needs discovery,
inspection, customization, correction, color selection, or maintenance. These
support commands must not become mandatory ceremony before routine
manufacturing.

This CHANGEPLAN contains remaining work rather than a history of completed
implementation. Completed behavior should normally be credited from HEAD and
removed from the plan rather than retained as historical checklists.

## Planning and development rules

`ARCHITECTURE.md` and the applicable Model `DEFINITION.md` files are normative.
Repository HEAD defines the current implementation. The CLI README defines the
intended operator-facing command model. This CHANGEPLAN describes temporary
remaining work and must not redefine permanent architecture.

At the beginning of a thread and before each meaningful implementation slice:

1. reload and follow `prompts/NEW_THREAD.md`;
2. compare CHANGEPLAN with current HEAD, `ARCHITECTURE.md`, applicable Model
   definitions, and the relevant CLI documentation;
3. credit behavior HEAD already satisfies;
4. identify the next unmet behavioral boundary rather than assuming the plan
   is still current;
5. resolve semantic or architectural questions before encoding behavior in
   tests;
6. use TDD for meaningful behavioral seams, without creating one-test-per-line
   ceremony;
7. implement the smallest correct change at the layer that owns the behavior;
8. run focused tests and then the appropriate complete quality suite; and
9. reevaluate the plan against the resulting HEAD.

Tests should protect useful behavioral boundaries rather than inventory
implementation details. High-level CLI/application seams should be protected
as they are introduced, while lower-level tests should be added only where
they protect behavior actually owned by that layer.

A newly discovered defect that can produce an incorrect manufacturing Product,
corrupt persistent manufacturing state, or cause material value-chain
inefficiency takes priority over CLI presentation work.

Every phase must leave the application production-capable.

## Common constraints

Preserve the separation between operator presentation and reusable application
behavior:

```text
CLI / TUI / GUI / API
          │
          ▼
reusable application operations
          │
          ▼
configuration / planning / engine / Products
```

Click owns parsing, terminal presentation, prompts, and translation of
structured application errors into operator-facing prose. Reusable workflow
behavior belongs below Click and should return structured domain/application
information rather than Rich objects or presentation-specific strings.

The CLI operates on the current working directory as project root. A registered
Artifact may legitimately exist under `originals/` before
`artifacts/<artifact_id>/` exists. Commands must preserve the distinction
between registered Artifact identity, materialized Artifact workspace, and
manufacturing Product state.

Missing collection directories normally represent empty collections. An
explicitly requested missing object is an operator error. Expected domain
errors should be concise and traceback-free; unexpected invariant or
programming failures must not be indiscriminately converted into ordinary
operator failures.

Routine output should be lean and oriented toward the operator's next useful
decision. Operator-facing Product paths should be concise and useful from the
project root. Do not expose Stage, resolver, dependency, or filesystem
mechanics unless they answer an operator question.

Do not change Product identity, dependency semantics, configuration precedence,
Model semantics, manufacturing ownership, persistence semantics, or color
semantics merely to simplify CLI presentation. If work exposes a genuine
architectural mismatch, resolve that mismatch explicitly against the permanent
specifications before proceeding.

---

# Phase 1 — Consolidate Workspace and Manufacturing Inspection in SHOW

## Purpose

Remove the separate `artifact list` command and make `artifact show` the
progressive inspection surface for workspace, Artifact, and Realization
manufacturing state.

The command should answer progressively:

```text
artifact show
    workspace inventory

artifact show <artifact>
    Artifact manufacturing inspection

artifact show <artifact> --realization <realization>
    focused Realization manufacturing inspection
```

Bare SHOW replaces LIST rather than duplicating it. The workspace view should
provide enough information to understand what Artifacts are registered, which
have materialized Artifact trees, how many effective Realizations exist, and
how those Realizations are distributed across established manufacturing
states.

The exact terminal columns, labels, and layout are not fixed by this plan.
Choose and refine presentation while implementing the behavior, keeping output
lean and useful.

## Decisions and required behavior

### Workspace inventory

Bare:

```text
artifact show
```

discovers Artifact identity from registration under `originals/`.

For each registered Artifact, workspace inspection must make it possible to
determine:

- whether `artifacts/<artifact_id>/` exists;
- how many effective Realizations are defined; and
- how those Realizations are distributed across the established manufacturing
  states, including current, stale, and not built where applicable.

Registration is authoritative for membership in the workspace inventory. An
orphan `artifacts/<artifact_id>/` directory does not independently create a
registered Artifact entry.

Artifact-tree existence is orthogonal to manufacturing state. A tree existing
does not imply that any Realization or Product is current.

A registered but unmaterialized Artifact remains visible. Its effective
Realizations must still be discoverable and represented in the workspace
summary.

Workspace SHOW must reuse the established manufacturing-state semantics rather
than invent an aggregate state model. Every effective Realization should be
accounted for by the state summary.

Bare SHOW over an empty workspace succeeds and reports that no Artifacts were
found.

### Artifact inspection

Existing:

```text
artifact show <artifact>
```

remains the Realization-oriented manufacturing inspection surface.

It should expose the effective canonical and custom Realizations useful to the
operator, their manufacturing state, and available manufacturing Products.

A current or stale Product path should be presented as a useful project-relative
path when possible. Reusable application results should retain real `Path`
values; path formatting belongs at the presentation boundary.

Do not add effective configuration detail to SHOW. Configuration provenance and
authored customization belong to CONFIG.

### Realization inspection

Existing:

```text
artifact show <artifact> --realization <realization>
```

remains the focused form of Artifact inspection.

It should use the same manufacturing semantics as Artifact inspection while
narrowing the result to the requested Realization.

An explicitly requested missing Artifact or Realization remains a concise
operator-facing error.

### LIST removal

Remove `artifact list` from the public command surface once bare SHOW provides
the required workspace discovery.

Remove or revise LIST-specific registration, implementation, tests, help, and
documentation. Do not retain a second public command solely as an alias unless
new compatibility evidence establishes a concrete need.

The CLI README and operator workflows should use bare SHOW wherever LIST
previously supplied Artifact discovery.

## High-level implementation steps

1. Compare current LIST and SHOW application/CLI seams and identify reusable
   discovery and manufacturing-inspection behavior already present in HEAD.
2. Establish high-level tests for bare SHOW covering the important workspace
   boundary: registered Artifact discovery, registered-but-unmaterialized
   visibility, materialized-tree visibility, effective Realization count, and
   manufacturing-state categorization.
3. Introduce or adapt a reusable application-level workspace inspection result
   rather than assembling domain behavior only inside `cmd_show.py`.
4. Extend `cmd_show.py` so zero Artifact IDs selects workspace inspection while
   preserving the existing Artifact and Realization scopes.
5. Refine the workspace presentation on-the-fly from structured application
   results; do not encode presentation choices into the application layer.
6. Protect selected SHOW Product-path presentation with a focused test and
   render project-relative paths when possible.
7. Remove LIST and its obsolete tests/registration after bare SHOW satisfies
   its discovery role.
8. Reconcile `src/lowkey_artifact_builder/cli/README.md`, CLI help, and affected
   operator-facing examples with the resulting behavior.
9. Run focused SHOW/application tests, then the complete applicable test,
   type-check, and lint suite.

Do not manufacture Products, materialize missing Artifact trees, or mutate
persistent state merely to answer SHOW.

## Completion criteria

Phase 1 is complete when:

- `artifact list` is no longer part of the public CLI;
- bare `artifact show` inventories registered Artifacts from `originals/`;
- registered-but-unmaterialized Artifacts remain visible;
- workspace SHOW distinguishes Artifact-tree existence from Realization
  manufacturing state;
- effective Realizations are counted and categorized using established
  manufacturing-state semantics;
- `artifact show <artifact>` continues to expose useful Realization
  manufacturing state and Products;
- `artifact show <artifact> --realization <realization>` remains a lean focused
  inspection;
- operator-facing Product paths are useful relative paths where possible;
- SHOW remains read-only and does not take ownership of BUILD behavior;
- reusable inspection behavior exists below Click;
- the important high-level behavioral seams are protected without redundant
  low-level test ceremony; and
- CLI documentation and help agree with the resulting HEAD.

---

# Phase 2

---

# Phase 3 — Rework CONFIG Around Effective Resolution and Provenance

## Purpose

Make CONFIG the operator/developer inspection surface for understanding how a
Realization's effective configuration was resolved.

For any selected Realization, CONFIG should make it possible to discover the
effective settings used by the resolver and understand the provenance or owner
of each setting.

This work should build around the existing resolver and configuration
precedence rather than independently reconstructing effective configuration in
the CLI.

CONFIG remains distinct from SHOW:

```text
SHOW
    manufacturing state and available Products

CONFIG
    effective settings and where those settings came from
```

CONFIG may also retain explicit configuration mutation where that capability
is useful, but inspection of effective resolution and provenance is the central
design concern of this phase.

## Required behavior to establish

For a selected Artifact/Realization, CONFIG should be able to report the
effective parameter set and identify the meaningful source/owner of each value.

Relevant provenance may include, according to the configuration model actually
established by HEAD and the permanent specifications:

- Model/default parameter definitions such as `parameters.toml`;
- Artifact-level authored configuration in `artifact.toml`;
- Realization-level authored configuration in `artifact.toml`; and
- other resolver-supported configuration layers that materially participate
  in the effective value.

Do not invent provenance categories from filesystem location alone. Provenance
must correspond to the actual resolution model.

The resolver remains authoritative for precedence and effective values. CONFIG
should consume resolver results or a reusable resolver-adjacent inspection
capability rather than duplicate precedence rules.

Sparse authored configuration must remain sparse. Inspecting effective values
must not cause defaults or inherited values to be written into `artifact.toml`.

The exact terminal layout is not fixed by this plan. The presentation should
make value and provenance understandable without exposing irrelevant resolver
internals.

## High-level implementation steps

1. Audit current `cmd_config.py`, CONFIG application operations, resolver APIs,
   configuration data structures, tests, and relevant permanent
   specifications.
2. Document the actual resolution layers and precedence already established by
   HEAD before defining provenance output.
3. Identify whether the resolver already retains enough provenance to support
   CONFIG inspection. If not, introduce the smallest reusable structured
   result at the resolver/application boundary that can report effective value
   plus provenance without changing resolution semantics.
4. Establish high-level tests proving that CONFIG reports effective values and
   distinguishes important provenance boundaries, including defaults,
   Artifact-level overrides, and Realization-level overrides where applicable.
5. Refactor CONFIG inspection to consume the reusable resolution/provenance
   capability rather than reconstructing precedence inside Click.
6. Preserve useful CONFIG mutation behavior and sparse authored configuration;
   adjust syntax only when a demonstrated operator/developer need warrants it.
7. Review broad CONFIG scope and developer-oriented flags against the clarified
   purpose of CONFIG. Retain, relocate, or simplify them based on actual value,
   without removing reusable engine capabilities merely to simplify the CLI.
8. Reconcile CONFIG documentation and help with the resulting behavior.
9. Run focused resolver/config/application/CLI tests, then the complete
   applicable quality suite.

## Completion criteria

Phase 3 is complete when:

- CONFIG can inspect a selected Realization's effective settings;
- each reported setting can identify meaningful provenance/ownership according
  to the real resolver model;
- effective values and provenance come from reusable resolver/application
  behavior rather than duplicated CLI precedence logic;
- default, Artifact-level, and Realization-level resolution boundaries are
  correctly represented where applicable;
- inspection does not materialize manufacturing work or mutate sparse authored
  configuration;
- useful CONFIG mutation behavior remains correct;
- CONFIG's public and developer-oriented scopes have intentional purposes;
- important resolution/provenance seams are protected by focused tests; and
- CONFIG help and CLI documentation agree with resulting HEAD.

---

# Phase 4 — Consolidate Remaining CLI Surfaces and Final Acceptance

## Purpose

After the focused command work described elsewhere in this plan, review the
remaining historical CLI inconsistencies, developer surfaces, help, messaging,
and end-to-end acceptance coverage without disturbing the established
manufacturing value chain.

This phase is cleanup and consolidation. It does not justify speculative
manufacturing capability or architectural simplification.

## Historical and developer surfaces

Review remaining public options, aliases, and developer operations against
actual operator or developer value, including where applicable:

- Variant-oriented public syntax such as `--variant` and `--all-variants`;
- independent Stage execution;
- Model/workplan inspection;
- diagnostic/developer capabilities; and
- command options whose historical purpose is no longer clear.

For each candidate, determine whether it is:

- required for ordinary manufacturing;
- a useful exception/customization capability;
- a useful developer capability;
- redundant with a clearer established operation; or
- obsolete presentation around a still-useful reusable capability.

Retain, relocate, deprecate, or remove based on those answers.

Do not confuse Variant identity with Realization identity. Do not remove a
useful architecture-level capability merely because ordinary manufacturing has
a simpler CLI path.

Where developer operations remain public, make their purpose and scope
explicit. Where they do not belong in ordinary operator workflow, prefer clear
separation or relocation over deleting reusable capability.

## Help and message consistency

Review:

```text
artifact --help
artifact <command> --help
```

Help should describe operator purpose rather than implementation mechanics.

Review routine output and errors for:

- terse success output;
- consistent Artifact, Variant, Realization, and Product terminology;
- actionable expected errors;
- suggested next actions when the application knows them;
- useful batch summaries;
- obvious manufacturing Products;
- useful relative paths; and
- absence of unnecessary Stage/resolver/dependency implementation detail.

Do not force identical output shapes on commands with different purposes.

## Final acceptance review

Protect a small number of complete value-chain workflows and reuse existing
lower-level evidence rather than duplicating it.

At minimum, compare current acceptance coverage with these operator outcomes:

```text
incoming artwork
      ↓
create
      ↓
build
      ↓
correct printable 3MF
```

```text
registered Artifact
      ↓
show / build
      ↓
existing current Product reused or required work identified
      ↓
correct printable 3MF
```

```text
configuration or color exception
      ↓
appropriate support operation
      ↓
build only what is necessary
      ↓
correct printable 3MF
```

```text
clean selected generated work
      ↓
build
      ↓
dependency-driven regeneration
      ↓
correct printable 3MF
```

Acceptance tests should remain focused on user-visible manufacturing value.
Detailed geometry, configuration resolution, graph planning, Product-state,
dependency, and color-assignment behavior belongs at the lower layers that own
those semantics.

Add acceptance coverage only where a meaningful end-to-end behavioral boundary
is not already protected.

## High-level implementation steps

1. Audit remaining public CLI syntax and developer operations against current
   HEAD and operator/developer value.
2. Resolve or document intentional homes for retained secondary/developer
   capabilities.
3. Reconcile top-level and command help with the final public command model.
4. Review routine messages and expected errors for consistency and useful next
   actions.
5. Compare existing acceptance tests with the final value-chain workflows and
   add only missing high-value coverage.
6. Run the complete test, type-check, and lint suite.
7. Recompare final HEAD with `ARCHITECTURE.md`, Model definitions, CLI
   documentation, and this CHANGEPLAN; remove completed planning material that
   no longer represents remaining work.

## Completion criteria

Phase 4 is complete when:

- the public CLI presents a short, coherent manufacturing workflow;
- secondary and developer capabilities have intentional homes;
- obsolete public syntax and historical presentation have been removed or
  intentionally retained;
- help and routine messages reflect the final command model;
- expected operator/domain failures are concise and actionable without hiding
  unexpected defects;
- the final acceptance suite protects the important manufacturing value-chain
  outcomes without duplicating lower-level tests;
- application workflow behavior remains reusable independently of Click; and
- repository documentation agrees with final HEAD.

The completed CLI should continue to support the central objective:

> Move customer artwork to a **correct, printable 3MF** with the fewest
> necessary decisions, actions, and computations.
