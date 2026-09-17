# CHANGEPLAN

## Purpose

This change plan streamlines the user-facing workflow of
`lowkey-artifact-builder` around the common production path:

```text
raw PNGs
    ↓
create
    ↓
Artifacts
    ↓
build
    ↓
3MF Products
    ↓
recolor
    ↓
operator-ready 3MFs
    ↓
PrusaSlicer / printer
```

The CLI should optimize this common case while preserving the architectural
distinction between Models, Variants, Artifacts, Realizations, Stages, and
Products.

The central CLI principle is:

> Users normally address Artifacts and Realizations. Variants provide
> Model-owned reusable configuration from which Realizations are derived.

Configuration is therefore exceptional in the ordinary production workflow.
Canonical Realizations permit a newly created Artifact to use every registered
Model Variant without requiring Artifact-specific configuration.

The intended routine batch workflow is:

```text
artifact create
artifact build
artifact build --build-all
# artifact recolor --colors printer
```

Artifact-specific configuration is required only when a canonical Realization
must be customized or an additional named Realization must be defined.

---

# Development Method

This plan is subordinate to:

```text
ARCHITECTURE.md
src/lowkey_artifact_builder/model/models/<model>/DEFINITION.md
prompts/NEW_THREAD.md
prompts/TEST_DRIVEN_DEVELOPMENT.md
```

The permanent specifications define intended behavior. Repository HEAD defines
the current implementation. This file describes a route between them.

At the beginning of each development thread and before selecting each new TDD
slice:

1. review the permanent specifications relevant to the work;
2. review `prompts/TEST_DRIVEN_DEVELOPMENT.md`;
3. review current repository HEAD;
4. review existing tests;
5. determine which work described here HEAD already satisfies;
6. identify meaningful discrepancies rather than silently resolving them;
7. select the next coherent unmet behavioral slice.

Phase and subsection ordering in this document does not override that process.

Work listed here must not be repeated merely because it remains listed. Credit
behavior already satisfied by HEAD and proceed to the next unmet requirement.

Each behavioral change follows:

```text
resolve semantics
    ↓
write coherent tests
    ↓
observe RED
    ↓
evaluate failures
    ↓
implement
    ↓
focused tests
    ↓
complete quality suite
    ↓
commit
    ↓
reevaluate HEAD
```

CLI tests should protect user intent, option interpretation, useful errors, and
translation into application operations. They should not duplicate engine,
configuration, color-assignment, or Model semantics already protected at a
lower level.

Each phase below is intended to leave the application in a coherent and usable
state. A phase may contain multiple independently committed TDD slices.

---

# Cross-Phase CLI Semantics

## Realizations are the execution coordinate

Normal CLI execution addresses:

```text
Artifact + Realization
```

not:

```text
Artifact + Variant
```

A Variant is a Model-owned reusable configuration.

A Realization is the application of that Variant to an Artifact, optionally
with Artifact-specific customization.

Multiple Realizations may originate from the same Variant, so Variant identity
is not a sufficient general execution coordinate.

Normal user-facing build, inspection, cleaning, and recoloring operations
should therefore use Realization names.

## Canonical Realizations require no Artifact configuration

Every registered Model Variant supplies a canonical Realization to every
Artifact according to the architecture.

Examples include:

```text
artwork.default  -> artwork_default
shape.default    -> shape_default
shape.ornament   -> shape_ornament
```

A newly created Artifact therefore does not need to declare those Realizations
in `artifact.toml`.

Artifact configuration should contain only source metadata and actual
Artifact-specific customization.

## Scope convention

Where applicable, commands use the same scope convention:

```text
<command>
    all applicable Artifacts

<command> dog
    Artifact dog

<command> --realization shape_ornament
    that Realization across applicable Artifacts

<command> dog --realization shape_ornament
    that Realization of dog
```

Commands must define sensible behavior when a requested Realization is not
available for one or more selected Artifacts rather than silently changing the
meaning of the request.

## Project-owned paths

Artifact-owned managed inputs may be referenced from Artifact configuration
using paths relative to the project root.

Such paths are resolved relative to the project root, not the process working
directory and not the directory containing `artifact.toml`.

For example:

```toml
source = "artifacts/dog/artifact.png"
original = "originals/dog.png"
```

These are persistent references to Artifact-owned source resources.

Generated Model, Stage, and Product filesystem paths must not be persisted in
Artifact configuration.

The distinction is:

```text
Artifact-owned managed input
    persistent source/configuration resource
    may be referenced by project-relative path

generated Model/Stage Product
    materialization of the build graph
    must not be persisted as Artifact configuration
```

The filesystem may materialize generated Products, but Artifact configuration
must continue to address manufacturing behavior through logical configuration
and Product identity rather than generated paths.

---

## Phase 1 — Intake and Build

### Goal

Complete the Phase 1 production workflow by establishing a clear lifecycle
boundary between source ingestion and Artifact/Product materialization.

The governing distinction is:

```text
CREATE
    ingest source PNGs into the authoritative preserved-source registry

BUILD
    materialize ingested Artifacts and realize their Products
```

The normal Phase 1 workflow remains:

```bash
artifact create
artifact build
artifact build --build-all
```

The following behavior is already established and is not repeated as remaining
work in this plan:

* canonical Realizations exist without Artifact-specific serialization;
* Artifact source and original provenance paths are project-relative;
* bare `artifact build` reports read-only build status;
* narrowed and project-wide incremental build and rebuild scopes operate on
  Artifacts and Realizations;
* independent build failures are aggregated where safe;
* packaged 3MF components use shared human-readable semantic/color naming.

The remaining Phase 1 work is:

1. make `originals/` the authoritative registry of ingested Artifact sources;
2. restrict `artifact create` to source ingestion;
3. make `artifact build` discover ingested Artifacts from `originals/` and own
   materialization of missing baseline Artifact state;
4. preserve the read-only semantics of bare `artifact build`;
5. extend executing build scopes to materialize missing Artifact state before
   realizing Products; and
6. materialize convenient Artifact-level copies of successfully packaged 3MF
   Products.

---

### 1.1 Artifact lifecycle boundary

The Phase 1 lifecycle is:

```text
external/root PNG
        │
        │ CREATE — ingestion
        ▼
originals/<artifact_id>.png
        │
        │ BUILD — Artifact materialization
        ▼
artifacts/<artifact_id>/
    artifact.toml
    artifact.png
        │
        │ BUILD — Product realization
        ▼
Realizations / Products
```

These transitions have distinct ownership.

`artifact create` owns only the transition into the preserved-source registry.

`artifact build` owns everything downstream of that registry, including
materializing baseline Artifact state when necessary and realizing requested
Products.

CREATE must not create or reconstruct the Artifact workspace merely as a side
effect of successful ingestion.

BUILD must not ingest arbitrary external or root-level PNGs merely because it
can discover them.

This boundary keeps source identity decisions separate from deterministic
materialization and build execution.

---

### 1.2 Preserved originals are the ingested Artifact registry

A preserved original has the canonical project-owned path:

```text
originals/<artifact_id>.png
```

The filename stem identifies the ingested Artifact.

For example:

```text
originals/
    smith-dog.png
    jones-cat.png
```

defines the ingested Artifact identities:

```text
smith-dog
jones-cat
```

An Artifact therefore becomes known to the project when its canonical preserved
original exists.

The existence of:

```text
originals/smith-dog.png
```

does not require that:

```text
artifacts/smith-dog/
```

already exist.

The latter is materialized Artifact state owned by BUILD.

Artifact identity is established by the preserved filename, not by the PNG
content fingerprint.

Two preserved originals may therefore contain identical bytes:

```text
originals/
    dog.png          SHA256 = abc123
    smith-dog.png    SHA256 = abc123
```

and still represent two independent ingested Artifacts:

```text
dog
smith-dog
```

Fingerprint equality must never collapse, alias, rename, or otherwise merge
existing Artifact identities.

---

### 1.3 CREATE owns ingestion only

`artifact create` establishes canonical preserved Artifact sources in:

```text
originals/
```

Its responsibility ends at that registry boundary.

Successful CREATE must not establish:

```text
artifacts/<artifact_id>/artifact.toml
artifacts/<artifact_id>/artifact.png
```

Those are BUILD materializations.

Root-level PNGs remain the un-ingested intake queue.

For ordinary filename-derived intake:

```text
smith-dog.png
    ↓
artifact create
    ↓
originals/smith-dog.png
```

For explicitly named ingestion:

```bash
artifact create smith-dog --source dog.png
```

the Artifact ID, rather than the external filename, determines the canonical
preserved-original name:

```text
dog.png
    ↓
artifact create smith-dog --source dog.png
    ↓
originals/smith-dog.png
```

The external source filename is not persistent Artifact identity.

CREATE does not need to author `artifact.toml` merely to record this identity.
The canonical preserved filename already establishes:

```text
artifact_id = smith-dog
original = originals/smith-dog.png
```

The materialized Artifact configuration created later by BUILD may record the
project-relative source relationships required by normal execution:

```toml
source = "artifacts/smith-dog/artifact.png"
original = "originals/smith-dog.png"
```

Both paths are project-relative and are resolved relative to the project root.

`source` is the Artifact-managed working source consumed by normal Model
execution.

`original` is the preserved authoritative source from which baseline Artifact
state can be materialized.

Neither is a generated Model/Stage Product path.

---

### 1.4 Intake ownership and destructive normalization

Bare:

```bash
artifact create
```

owns the root-level PNG intake queue.

A successfully ingested root-level PNG may therefore be consumed, including
being moved or renamed into its canonical preserved location.

The conceptual operation is:

```text
root intake PNG
    ↓
establish originals/<artifact_id>.png
    ↓
consume/remove root intake PNG
```

The implementation need not use a literal filesystem rename if another
ordering provides stronger failure safety.

The required invariant is:

> Intake must never destroy the only known copy of an input PNG.

The root intake PNG must not be consumed until a durable preserved original
exists.

Explicit source ownership remains distinct from bare batch ownership.

An explicitly supplied source outside the owned root intake workflow is
caller-owned and must not be deleted merely because it was used to establish
the canonical preserved original.

CREATE stops after successful ingestion. It does not subsequently materialize
the Artifact workspace.

---

### 1.5 Duplicate intake across Artifact names

Fingerprinting remains byte-oriented and uses a strong content fingerprint such
as SHA-256.

Fingerprints are an on-demand intake and integrity mechanism. They are not
persisted as Artifact configuration, Artifact metadata, or Model parameters.

Because preserved originals form the authoritative ingested-source registry,
bare intake duplicate detection may compare an incoming root PNG against
preserved originals even when the filenames differ.

For example:

```text
dog.png                         SHA256 = abc123
originals/smith-dog.png         SHA256 = abc123
```

may establish that `dog.png` is a duplicate of the already-ingested source for
Artifact `smith-dog`.

The filename `dog.png` must not cause ingestion of a second Artifact named
`dog` when the intake PNG has been uniquely identified as an already-preserved
source.

A unique fingerprint match may therefore report:

```text
dog.png    DUPLICATE of Artifact 'smith-dog'
```

This use of fingerprints is limited to determining whether incoming intake has
already been preserved.

Content equality does not define persistent Artifact identity.

---

### 1.6 Ambiguous duplicate intake

Multiple preserved Artifact originals are allowed to have the same
fingerprint.

Therefore:

```text
originals/
    dog.png          SHA256 = abc123
    smith-dog.png    SHA256 = abc123
```

is valid persistent state.

If a new root-level PNG also has:

```text
customer.png         SHA256 = abc123
```

its content cannot identify which existing Artifact, if either, the incoming
file represents.

That intake item is therefore ambiguous.

The CLI must:

* not arbitrarily select one of the matching Artifacts;
* not collapse the existing Artifacts;
* not infer a new persistent Artifact identity solely from the fingerprint;
* not delete the incoming PNG as a verified duplicate;
* report the ambiguity clearly and leave the incoming PNG intact.

A fingerprint may prove content equality. It may identify an existing Artifact
for duplicate-intake purposes only when the matching preserved Artifact source
is unique.

---

### 1.7 Duplicate cleanup

The established duplicate-cleanup interface remains:

```bash
artifact create --clean
```

`--clean` applies only to bare batch intake.

Without `--clean`, a positively verified duplicate remains in the root intake
queue unless the operator explicitly approves its removal.

With `--clean`, a positively verified duplicate may be removed automatically.

Cleanup must never remove an incoming PNG whose duplicate status is ambiguous,
conflicting, or otherwise unverified.

`--clean` means:

> clean verified duplicate intake files

It does not mean force ingestion, overwrite an existing preserved original,
replace an Artifact source, materialize an Artifact, or discard
ambiguous/conflicting input.

---

### 1.8 CREATE preflight and mutation safety

CREATE must preflight predictable destructive conflicts before normal batch
mutation.

Artifact identity comparisons are case-insensitive so projects remain portable
between case-sensitive and case-insensitive filesystems.

Preflight must protect at least:

* canonical preserved-original identities;
* proposed new Artifact identities;
* canonical `originals/<artifact_id>.png` destinations;
* ambiguous duplicate matches;
* conflicting input.

A genuine predictable collision must not silently overwrite existing state or
cause automatic alternate Artifact IDs such as `dog(1)`.

Verified duplicates are resolved intake items rather than genuine collisions
and do not prevent independent safe intake.

Unexpected runtime failures must preserve enough source state to ensure that
the only known copy of an input PNG is not lost.

CLI output should distinguish at least:

```text
NEW
DUPLICATE
FAILED
```

or equivalent human-readable states so batch ingestion remains auditable.

Artifact workspace integrity is not CREATE's responsibility merely because an
Artifact workspace happens to exist. BUILD owns the relationship between an
ingested preserved source and its materialized Artifact state.

---

### 1.9 BUILD discovers the ingested Artifact universe

BUILD must not derive the complete Artifact universe solely from existing
directories under:

```text
artifacts/
```

The authoritative inventory of ingested Artifact identities is:

```text
originals/*.png
```

For example:

```text
originals/
    dog.png
    cat.png

artifacts/
    cat/
        artifact.toml
        artifact.png
```

contains two ingested Artifacts:

```text
dog
cat
```

even though only `cat` currently has materialized Artifact state.

Build discovery must therefore be capable of distinguishing:

```text
ingested Artifact
    canonical preserved original exists

materialized Artifact
    baseline Artifact workspace exists

built Realization
    required Products exist and are current
```

The filesystem relationship between `originals/` and `artifacts/` should be
reconciled through shared project-level Artifact discovery/status behavior
rather than independently reconstructed in multiple CLI commands.

CREATE and BUILD may consume different portions of that shared project state,
but command modules should not develop conflicting definitions of Artifact
identity or existence.

---

### 1.10 Bare BUILD remains read-only

Bare:

```bash
artifact build
```

remains a status operation.

It must not:

* ingest root-level PNGs;
* materialize missing Artifact workspaces;
* execute Stages;
* rebuild Products; or
* otherwise mutate persistent project state.

It should, however, report ingested Artifacts whose baseline Artifact state has
not yet been materialized.

For example:

```text
originals/
    dog.png
    cat.png

artifacts/
    cat/
        artifact.toml
        artifact.png
```

must not cause `dog` to disappear from build status merely because its Artifact
workspace is absent.

The output should make the distinction actionable, for example conceptually:

```text
dog
    Artifact            ABSENT / NOT MATERIALIZED

cat
    Artifact            CURRENT
    artwork_default     CURRENT
    shape_default       STALE
    shape_ornament      CURRENT
```

Exact presentation belongs to the CLI display design, but the semantic
distinction must remain clear.

BUILD should not pretend that Realization/Product state has been successfully
resolved for an Artifact whose prerequisite baseline Artifact state does not
yet exist.

---

### 1.11 Executing BUILD materializes missing Artifact state

An executing build scope owns deterministic materialization of selected
ingested Artifacts.

For an ingested Artifact:

```text
originals/smith-dog.png
```

whose baseline workspace is absent, executing BUILD may establish:

```text
artifacts/smith-dog/
    artifact.toml
    artifact.png
```

before normal Realization/Product planning and execution.

The materialized baseline Artifact conceptually records:

```toml
source = "artifacts/smith-dog/artifact.png"
original = "originals/smith-dog.png"
```

and copies the preserved source into the Artifact-managed working source:

```text
originals/smith-dog.png
        ↓
artifacts/smith-dog/artifact.png
```

The preserved original is not moved, renamed, or deleted during
materialization.

Materialization is driven by the preserved filename and not by fingerprints.

Thus:

```text
originals/
    dog.png          SHA256 = abc123
    smith-dog.png    SHA256 = abc123
```

with both Artifact directories absent materializes two independent Artifacts:

```text
artifacts/
    dog/
        artifact.toml
        artifact.png
    smith-dog/
        artifact.toml
        artifact.png
```

The two Artifacts remain independent even though their source bytes are
identical.

After materialization, normal configuration resolution supplies canonical
Realizations without requiring Artifact-specific Realization serialization.

---

### 1.12 BUILD scope and materialization

Materialization participates in the established build scope rather than
becoming an independent CREATE operation.

For example:

```bash
artifact build dog
```

may materialize `dog` from:

```text
originals/dog.png
```

when `dog` is selected for execution and its Artifact workspace is absent.

It then proceeds with the normal incremental build of the selected effective
Realizations.

Likewise:

```bash
artifact build --build-all
```

may materialize every selected ingested Artifact whose baseline Artifact state
is absent and then bring the applicable project build scope current.

BUILD must not materialize unrelated ingested Artifacts outside the requested
scope merely because they were discovered during project inventory.

Materialization is prerequisite work for build execution, not a separate
implicit invocation of CREATE.

CREATE remains responsible only for establishing the ingested source registry.

---

### 1.13 Artifact recovery and materialization limits

Because `originals/` is authoritative for ingested source identity, the
following development workflow is valid:

```bash
rm -rf artifacts
artifact build
```

The bare build reports that the ingested Artifacts require materialization.

Then:

```bash
artifact build --build-all
```

materializes their baseline Artifact state and proceeds through the normal
incremental build graph.

Materialization restores only state derivable from the preserved original and
normal Artifact defaults.

It must not imply that arbitrary Artifact-authored customization can be
recovered after its only persistent representation has been deleted.

Once later phases introduce Artifact-specific customization, deleting the
`artifacts/` tree may also delete information that cannot be reconstructed from
`originals/`.

Therefore:

```text
originals/
```

is authoritative for ingested Artifact source identity, but it is not
necessarily a backup of all future Artifact-authored configuration.

---

### 1.14 Existing Artifact behavior and integrity

When both:

```text
originals/<artifact_id>.png
```

and:

```text
artifacts/<artifact_id>/
```

already exist, BUILD must not recreate or overwrite healthy baseline Artifact
state merely because the preserved original is present.

Normal incremental Product-state semantics continue to determine what build
work is required.

Incomplete or inconsistent materialized Artifact state must not silently become
an implicit source-replacement operation.

In particular, BUILD must not interpret changed bytes in a preserved original,
managed source, or unrelated incoming PNG as an implicit request to replace
Artifact-authored state.

Source replacement, if supported later, requires separately defined explicit
semantics.

Before implementing automatic handling of partially materialized Artifact
directories, define which states are safely reconstructable and which represent
integrity failures requiring operator attention.

Do not let repair semantics emerge accidentally from filesystem copying.

---

### 1.15 Artifact-level packaged 3MF materialization

The canonical packaged 3MF remains the persistent Product of the Model package
Stage.

For example:

```text
artifacts/smith-dog/
    artwork/
        artwork_default/
            50-package/
                artifact.3mf
```

That Stage Product remains authoritative for build planning, Product state,
dependency resolution, freshness, and execution.

After successful package execution, materialize a convenience copy beside
`artifact.toml`.

For example:

```text
artifacts/smith-dog/
    artifact.toml
    artifact.png
    artwork.default.3mf
    shape.default.3mf
    shape.ornament.3mf
```

The convenience filename should identify the qualified Variant associated with
the Realization where that identity is available and unambiguous.

Examples include:

```text
artwork.default.3mf
shape.default.3mf
shape.ornament.3mf
```

A materialized Artifact-level 3MF is a convenience copy, not another logical
Product.

It must not:

* participate independently in Product state;
* become a dependency target;
* replace the canonical package-stage Product;
* be persisted as a generated Product path in `artifact.toml`;
* cause Model package stages to construct Artifact-level filesystem paths.

Ownership remains:

```text
Model package Stage
    ↓
produces canonical packaged Product
    ↓
Engine confirms successful execution
    ↓
Engine materializes Artifact-level convenience copy
```

Materialization occurs only after package execution succeeds.

Merely discovering that an existing canonical packaged Product is already
current must not independently cause package execution or imply that a new
Product exists.

The engine remains responsible for the boundary between successful Stage
execution and Artifact-level convenience materialization. Models continue to
produce only their declared Products through normal Stage execution.

Before implementation, verify naming behavior for explicitly named
noncanonical Realizations so convenience filenames cannot collide when
multiple Realizations originate from the same Variant.

Also define cleanup/rebuild behavior for an existing convenience copy when its
canonical package Product is removed, rebuilt, or fails before replacing the
previous materialization. The convenience copy must never become authoritative
merely because it survived changes to canonical Product state.

---

## Phase 1 completion criterion

Phase 1 is complete when:

1. CREATE safely normalizes root or explicitly selected PNG intake into the
   authoritative `originals/<artifact_id>.png` registry without materializing
   Artifact workspaces;

2. Artifact identity is derived from the canonical preserved filename rather
   than from a content fingerprint;

3. duplicate intake can recognize uniquely matching preserved content even
   when the incoming filename differs from the Artifact ID, without treating
   fingerprints as persistent Artifact identity;

4. identical fingerprints across multiple preserved Artifacts remain valid and
   produce safe ambiguity rather than identity collapse;

5. BUILD discovers ingested Artifacts from `originals/` even when their
   `artifacts/<artifact_id>/` workspace does not yet exist;

6. bare `artifact build` remains read-only and reports missing Artifact
   materialization as part of project build status;

7. executing narrowed and project-wide build scopes materialize missing
   baseline Artifact state for selected ingested Artifacts before normal
   Realization/Product execution;

8. deleting reconstructable baseline Artifact state can be recovered through
   BUILD without re-ingesting sources through CREATE;

9. established incremental/rebuild workflows continue to operate on every
   effective Realization after Artifact materialization; and

10. successful package execution can materialize an appropriately named
    convenience 3MF beside `artifact.toml` without changing canonical Product
    semantics.

The ordinary Phase 1 workflow is:

```text
root/external PNGs
    ↓
artifact create
    ↓
originals/<artifact_id>.png
    ↓
artifact build
    ↓
inspect materialization + build state
    ↓
artifact build --build-all
    ↓
materialized Artifacts
    +
canonical packaged Products
    +
operator-convenient 3MF copies
```

The governing ownership rule is:

> CREATE ingests. BUILD materializes and realizes Products.

---

# Phase 2 — Customization and Reset

## Goal

At the end of Phase 2, the user can customize Realizations when the canonical
configuration is insufficient and can discard generated work safely.

Phase 1 remains the ordinary workflow.

Phase 2 adds:

```text
artifact config
artifact clean
```

---

## 2.1 Authored configuration

Define:

```text
config = authored/persistent configuration
```

`config` must not become another view of fully resolved Model configuration.

For example:

```text
artifact config dog --realization shape_ornament
```

shows only Artifact-authored customization for that Realization.

If the canonical Realization has no Artifact-specific customization, report
that condition clearly rather than dumping inherited Model/Variant defaults.

---

## 2.2 Realization customization

Support:

```text
artifact config dog \
    --realization shape_ornament \
    --parameters shape_size=110
```

This materializes or updates Artifact-specific customization of an already
existing canonical Realization.

Customizing a canonical Realization does not require `--create`.

Parameter validation and resolution remain owned by the existing
configuration/Model infrastructure. CLI code should not duplicate
Model-specific parameter semantics.

---

## 2.3 Additional named Realizations

Permit an Artifact to define an additional named Realization when required.

For example:

```text
artifact config dog \
    --realization large-ornament \
    --create \
    --parameters variant=shape.ornament shape_size=125
```

CLI configuration treats `variant=shape.ornament` as a configuration
assignment rather than introducing a separate normal `--variant` execution
coordinate.

Required semantics:

* `--create` permits creation of a noncanonical Realization name;
* canonical Realizations already exist and do not require `--create`;
* a misspelled/nonexistent noncanonical Realization must not silently become a
  new Realization without `--create`;
* updating one Realization must preserve unrelated Realization declarations;
* configuration persistence must support safe nested Realization updates rather
  than replacing the entire `[realizations]` table.

Before implementing bulk configuration across Artifacts, explicitly settle
mixed-state and atomicity behavior when some selected Artifacts already contain
the named Realization and others do not.

---

## 2.4 Bulk customization

Once single-Artifact mutation is sound, support the normal scope convention
where useful.

For example:

```text
artifact config \
    --realization large-ornament \
    --create \
    --parameters variant=shape.ornament shape_size=125
```

may define the same additional Realization across the selected Artifact scope.

Bulk mutation must have explicit failure/atomicity semantics before tests are
written.

Do not let batch behavior emerge accidentally from a loop around a
single-Artifact mutator.

---

## 2.5 Clean

Align `clean` with Artifact/Realization execution coordinates.

Support:

```text
artifact clean dog --realization shape_ornament
```

to remove derived Products belonging to that Realization while preserving:

* `artifact.toml`;
* managed source inputs;
* preserved originals;
* unrelated Realizations.

Also support the broader scopes where safe and useful:

```text
artifact clean dog
artifact clean --realization shape_ornament
artifact clean
```

Because broad cleaning is destructive, define confirmation/explicitness policy
before implementing the no-argument form.

Cleaning removes generated Products. It does not remove the Artifact or its
authored configuration.

After cleaning, `artifact build` should report the affected Realizations as
requiring work, and the normal build commands should be capable of restoring
them.

---

## Phase 2 completion criterion

The Phase 1 workflow still works unchanged.

Additionally, the user can customize an existing canonical Realization or
define an additional named Realization, build it through the normal
Realization-oriented build interface, clean its generated Products, and rebuild
it.

No manual TOML editing is required for ordinary customization.

---

# Phase 3 — Recolor for Printer Operation

## Goal

At the end of Phase 3, built 3MFs can optionally be transformed quickly into
operator-friendly 3MFs whose component color metadata and presentation
communicate the intended physical filament assignment.

No geometry work is repeated.

Add:

```text
artifact recolor
```

The production workflow becomes:

```text
artifact create
artifact build
artifact build --build-all
artifact recolor --colors printer
```

---

## 3.1 Recolor operates on packaged component color semantics

`recolor` operates downstream of ordinary geometry generation.

It must not rerun:

* source preparation;
* tracing;
* rasterization;
* vectorization;
* geometry composition;
* extrusion; or
* other geometry-producing operations.

Recolor operates on independently printable components already represented by
a packaged 3MF and on the semantic color information preserved for those
components.

Packaged components may obtain their color semantics in different ways.

For Artwork-derived color components:

```text
measured Artifact color
    ↓
Artwork physical-color assignment
    ↓
packaged component
```

For Model-owned structural components, such as Shape base or outer ridge:

```text
Model-owned semantic printing color
    ↓
packaged component
```

These are distinct semantics and must not be conflated.

Artwork assignment policy applies to Artifact colors. It must not be
indiscriminately reapplied to Model-owned structural colors that already
identify intended semantic physical colors.

Likewise, recoloring a complete Shape 3MF must not ignore structural components
merely because they are not Artwork color regions.

Recolor should therefore preserve both:

* stable independently printable component identity; and
* the semantic source and meaning of that component's printing color.

Prefer reusable, Model-independent 3MF metadata transformation where the
operation is purely mechanical. Do not move Artwork assignment policy or Shape
color policy into generic 3MF infrastructure.

---

## 3.2 Recolor existing 3MF Products

Recolor transforms an existing packaged manufacturing Product into an
operator-facing representation.

Preserve the canonical built 3MF and produce a distinct recolored output unless
a later explicit design decision changes this policy.

Recoloring should be deterministic and idempotent.

Repeated recoloring must not accumulate presentation labels.

The transformation must preserve manufacturing geometry, including:

* mesh coordinates;
* component geometry;
* component partitioning; and
* build composition.

Only operator-facing color/material metadata and presentation information
required by the selected physical color realization should change.

---

## 3.3 Printer recoloring

Support:

```text
artifact recolor --colors printer
```

For Artwork color components, printer recoloring uses the established Artwork
`printer_assignments` semantics: the globally optimal one-to-one assignment
between Artifact colors and configured printer colors.

For Model-owned structural components, the Model's already-resolved semantic
printing color remains authoritative.

Recolor must not reinterpret an explicit Shape color, for example, as a
measured Artwork color merely because another printer color has a closer RGB
value.

The resulting 3MF should make component identity and intended physical color
immediately understandable in PrusaSlicer.

Conceptually:

```text
dog-color-1 - Fire Engine Red
dog-color-2 - Cold White
dog-color-3 - Pine Green
dog-base - Cold White
dog-outer-ridge - Gold
```

Do not replace stable component identity merely with a color name.

The operator must be able to identify both:

* what component this is; and
* what physical color is intended.

Before implementation, settle how a Model-owned semantic color that is not
currently present in `printer_colors` should be represented to the operator.
Do not silently substitute another color through Artwork assignment policy.

---

## 3.4 Library recoloring

Support:

```text
artifact recolor --colors library
```

For Artwork color components, library recoloring uses the established Artwork
`library_assignments` semantics: the globally optimal one-to-one assignment
from filament physically present in the configured library.

For Model-owned structural components, preserve the owning Model's semantic
printing-color intent.

Before implementation, settle the operator-facing behavior when an explicitly
requested structural color is absent from the library. This is an availability
question about an already selected semantic color, not automatically an
Artwork color-matching problem.

This mode allows the operator to determine which loaded filament should remain
and which filament swaps from owned inventory are warranted before printing.

Recolor must reuse established Artwork color-assignment semantics rather than
implementing another nearest-color algorithm.

---

## 3.5 Catalog improvement analysis

Artwork color analysis already distinguishes:

```text
printer_assignments
library_assignments
catalog_assignments
```

and defines individual and aggregate perceptual distance.

Recolor should be capable of presenting those existing comparisons as
production guidance for Artwork-derived color components.

Catalog assignment is diagnostic rather than an assertion that the user owns
those colors.

For Artwork colors, report individual and aggregate perceptual distance
sufficiently to answer:

> How much could this Artwork improve using filament already in the library?

and:

> How much further could it improve if another known catalog color were
> purchased?

Conceptually:

```text
Layer    Selected          Distance    Best catalog       Distance
1        Fire Engine Red      5.8      Cardinal Red          1.0
2        Cold White           1.2      Polar White           0.8
3        Pine Green           3.7      Forest Green          1.5
```

Useful derived comparisons include:

```text
printer improvement = printer aggregate distance - library aggregate distance

purchase improvement = library aggregate distance - catalog aggregate distance
```

These calculations apply to Artwork assignment semantics.

Do not automatically treat a Model-owned structural semantic color as another
measured Artwork color participating in the global Artwork assignment.

Catalog analysis must not silently mutate:

* `printer_colors`;
* `library_colors`;
* Artifact configuration;
* Model-owned structural color configuration; or
* the canonical manufacturing Product.

---

## 3.6 Recolor scope

Apply the normal scope convention:

```text
artifact recolor dog --realization shape_ornament --colors printer
artifact recolor dog --colors printer
artifact recolor --realization shape_ornament --colors printer
artifact recolor --colors printer
```

Only existing applicable packaged Products should be recolored.

Recolor must not implicitly trigger an expensive geometry build merely because
a requested 3MF is absent. Missing build prerequisites should be reported
clearly.

---

## Phase 3 completion criterion

The user can take built Artifacts and rapidly generate operator-ready 3MFs
using the intended physical filament assignments.

For Artwork-derived components, the user can choose assignments based on:

* colors currently available to the printer; or
* colors physically available in the filament library.

The user also receives quantitative Artwork color analysis indicating how much
color fidelity could improve using library or catalog colors.

Model-owned structural components retain the semantic printing colors defined
by their owning Models rather than being incorrectly absorbed into Artwork's
color-matching policy.

No geometry is rebuilt during recoloring.

---

# Phase 4 — Inspection

## Goal

At the end of Phase 4, the user can answer distinct questions without
confusing authored configuration, effective configuration, addressable
objects, and color analysis.

The commands are:

```text
artifact list
artifact config
artifact show
artifact colors
```

Their responsibilities are intentionally distinct:

```text
list
    What exists / what can I address?

config
    What have I explicitly configured?

show
    What configuration will actually be used?

colors
    Why did the Artwork color system make these assignments?
```

---

## 4.1 List

Define:

```text
artifact list
```

to list defined Artifact IDs.

Define:

```text
artifact list dog
```

to list the effective Realizations addressable for `dog`, including canonical
Realizations and explicitly declared additional Realizations.

Listing should use the authoritative Realization catalog rather than
reconstructing it independently in CLI code.

`list` reports identity and availability, not complete configuration.

---

## 4.2 Show

Make `show` Realization-oriented.

For example:

```text
artifact show dog --realization shape_ornament
```

shows the fully resolved configuration that would actually be used for that
Realization.

It should resolve the Realization directly through configuration semantics
rather than detouring through Variant-oriented build planning merely to obtain
a resolver.

Resolved output may include useful provenance where that helps explain whether
a value came from:

* Model defaults;
* Variant overrides;
* Workspace configuration;
* Artifact configuration; or
* Realization customization.

Do not make `show` synonymous with `config`.

---

## 4.3 Colors

Retain `colors` as the detailed Artwork color-analysis command.

It should expose the established Artwork color analysis across:

```text
printer
library
catalog
```

including individual and aggregate perceptual distances.

`recolor` is the production operation that prepares packaged components for
operator use.

`colors` is the Artwork color-assignment inspection/diagnostic operation.

The two should share the applicable underlying Artwork color-analysis semantics
rather than developing parallel assignment implementations.

Where color analysis requires only persistent registered Artwork products,
build only the minimum missing dependency closure required for that analysis.
Do not require standalone Artwork packaging merely to inspect color quality.

Model-owned structural printing colors are not Artifact color regions and
should not be silently included in Artwork's global one-to-one color analysis.

---

## 4.4 Remove misplaced inspection responsibilities

As the new command responsibilities become established, remove or relocate
legacy CLI behavior that no longer belongs to its command.

In particular, Model catalog/workplan inspection currently attached to
Artifact configuration should not force `config` to serve two unrelated
purposes.

Before moving or deleting developer-oriented capabilities, determine whether
they remain useful and choose an explicit home for them rather than silently
discarding them.

---

## Phase 4 completion criterion

Without editing files or invoking developer internals, a user can determine:

* which Artifacts exist;
* which Realizations are available;
* what Artifact-specific configuration was authored;
* what effective configuration a Realization will use;
* whether builds are current;
* and why Artwork physical colors were selected.

The production workflow established in Phases 1–3 remains unchanged.

---

# Phase 5 — CLI Consolidation and Production Polish

## Goal

Complete the transition from the historical CLI to the streamlined
Artifact/Realization-oriented workflow without retaining contradictory command
semantics.

This phase should contain no speculative new manufacturing capability.

It consolidates behavior already proven useful in the preceding phases.

---

## 5.1 Retire obsolete normal-workflow syntax

Review remaining public options and remove or clearly isolate obsolete
Variant-oriented normal execution syntax such as:

```text
--variant
--all-variants
```

where Realization-oriented equivalents now define the intended user workflow.

Do not remove internal Model/Variant coordinates merely because they are no
longer ordinary CLI coordinates.

Variants remain architecturally essential configuration identities.

---

## 5.2 Developer and Stage operations

Review independent Stage execution and other developer-oriented operations.

Preserve the architectural ability to execute a Stage through a complete
`StageContext`.

Do not force specialized Stage execution into the ordinary production command
semantics merely to reduce the number of top-level commands.

If developer operations require a separate command surface, make that
separation explicit.

---

## 5.3 Output consistency

Make routine command output consistent around:

```text
Artifact
Realization
state/action
Product where relevant
```

Avoid exposing implementation-oriented Model/Variant coordinates when they do
not help the user perform the requested operation.

Errors should identify the actionable Artifact/Realization scope that failed.

Batch operations should summarize successful, skipped/current, and failed work
without obscuring the underlying error.

---

## 5.4 End-to-end production acceptance

Protect the final common workflow with a small number of meaningful acceptance
tests.

A representative workflow should establish that the user can:

```text
place PNGs in intake
    ↓
artifact create
    ↓
artifact build
    ↓
inspect pending build state
    ↓
artifact build --build-all
    ↓
artifact recolor --colors printer
    ↓
obtain operator-ready 3MF Products
```

A customization acceptance path should establish only the additional behavior
that matters:

```text
create
    ↓
config one Realization
    ↓
build that Realization
    ↓
recolor
```

Do not duplicate detailed Model geometry, configuration resolution, build
graph, or color-assignment assertions already protected by focused tests.

---

## Phase 5 completion criterion

The normal user-facing CLI presents one coherent mental model:

```text
create    ingest customer sources

build     inspect build state or make selected work current

config    author Artifact/Realization exceptions

clean     discard generated work

recolor   prepare built 3MFs for physical filament choices

list      discover addressable Artifacts and Realizations

show      inspect effective resolved configuration

colors    inspect Artwork color-assignment quality
```

Variants remain Model-owned reusable configuration.

Realizations remain the Artifact-scoped execution coordinate.

The common production workflow requires no manual configuration when Model
Variants already describe the desired products.

---

# Target Production Workflow

For a routine batch:

```text
# Customer PNGs are placed in the project root.

artifact create

# See what the new intake or configuration changes require.
artifact build

# Bring the project current.
artifact build --build-all

```

When filament swaps from owned inventory are acceptable:

```text
artifact recolor --colors library
```

When one Artifact requires an exception:

```text
artifact config smith-dog \
    --realization shape_ornament \
    --parameters shape_size=110

artifact build smith-dog --realization shape_ornament

artifact recolor smith-dog \
    --realization shape_ornament \
    --colors printer
```

Inspection and maintenance remain available without complicating the ordinary
path:

```text
artifact list
artifact list smith-dog

artifact config smith-dog --realization shape_ornament
artifact show smith-dog --realization shape_ornament

artifact colors smith-dog

artifact clean smith-dog --realization shape_ornament
```

The desired steady-state workflow is therefore:

```text
create → build → recolor → print
```

with:

```text
config
clean
list
show
colors
```

used when the ordinary path requires customization, maintenance, or
explanation.
