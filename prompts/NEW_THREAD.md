# New Development Thread

We are continuing development of `lowkey-artifact-builder`.

Repository:

```text
https://github.com/lowkeylabs/lowkey-artifact-builder
```

Begin by reviewing the **current repository at HEAD**.

Do not assume implementation details, architectural decisions, phase status, or
completed work from previous conversations when they conflict with the
repository.

The repository is the authoritative source for the current implementation.

## Permanent Specifications

Read and compare:

```text
ARCHITECTURE.md
src/lowkey_artifact_builder/model/models/<model>/DEFINITION.md
```

for every model relevant to the current work.

Treat:

* `ARCHITECTURE.md` as the permanent normative specification for the system;
* each model `DEFINITION.md` as the permanent normative specification for that
  model;
* the repository implementation and tests as the current implementation of
  those specifications.

Do not silently resolve differences between the permanent specifications and
HEAD. Identify meaningful discrepancies explicitly.

## Development Method

Read and follow:

```text
prompts/TEST_DRIVEN_DEVELOPMENT.md
```

for the project's test-driven development practices.

Development is test-driven and incremental. Tests should define and protect
intended behavior without unnecessarily freezing incidental implementation
details, mutable repository configuration, or independently extensible model
capabilities.

Apply the testing strategy appropriate to the kind of change being made,
including bug fixes, new models, new model features, new variants, CLI
workflow changes, and refactoring.

Resolve meaningful specification or design questions before allowing tests or
production implementation to decide them implicitly.

Select the **next coherent TDD slice** based on the current repository state
and the practices defined in `prompts/TEST_DRIVEN_DEVELOPMENT.md`.

## Change Plan

If `CHANGEPLAN.md` exists, read it after reviewing the permanent
specifications and development method.

`CHANGEPLAN.md` is a temporary implementation plan for bringing repository
HEAD into alignment with the permanent specifications. It is not itself a
normative specification.

Determine the actual current phase and status by comparing:

1. the permanent specifications;
2. `CHANGEPLAN.md`;
3. repository HEAD;
4. the existing tests.

Do not assume that work listed in `CHANGEPLAN.md` remains incomplete merely
because it is still listed there.

Do not propose repeating work that HEAD already satisfies.

If HEAD has evolved in a way that makes part of `CHANGEPLAN.md` obsolete,
identify that explicitly.

## Selecting the Next Slice

Before proposing work:

1. Review `ARCHITECTURE.md`.
2. Review the applicable model `DEFINITION.md` files.
3. Review `prompts/TEST_DRIVEN_DEVELOPMENT.md`.
4. Review `CHANGEPLAN.md`, if present.
5. Inspect the relevant production implementation.
6. Inspect the existing tests.
7. Determine which planned behaviors HEAD already satisfies.
8. Identify the next meaningful unmet architectural or model requirement.
9. Group closely related requirements when they naturally form one coherent
   implementation slice.

Do not select a slice solely because it appears next in `CHANGEPLAN.md`.

Repository HEAD and the permanent specifications determine what work is
actually required.

When existing implementation already satisfies a planned requirement, credit
that work and move forward.

## First Response in a New Thread

For the first development turn, **do not implement production code**.

First provide a concise assessment of:

* the current repository state;
* the current phase and subsection, if `CHANGEPLAN.md` exists;
* which nearby planned work is already satisfied;
* meaningful discrepancies between HEAD and the permanent specifications;
* the next coherent TDD slice you recommend.

For the recommended slice, explain briefly:

* which architectural or model requirements it advances;
* why the selected behaviors belong in one slice;
* what behavior HEAD already provides;
* what behavior is currently missing;
* which existing test files should be modified;
* which new test files, if any, are justified.

Then provide the **complete drop-in test changes** for that slice.

Do not provide production implementation yet.

The intended workflow is:

```text
review specifications + TDD practices + HEAD
        ↓
select coherent slice
        ↓
write tests
        ↓
run tests
        ↓
observe RED failures
        ↓
evaluate those failures
        ↓
implement production change
        ↓
run focused tests
        ↓
run complete quality suite
        ↓
commit
        ↓
reevaluate HEAD
```

The RED failures are part of the design process. Use the actual failures to
guide production changes rather than predicting implementation changes more
precisely than the specifications, tests, and observed failures justify.

## Architectural Discipline

While reviewing or proposing changes:

* keep the generic engine model-independent;
* keep model semantics in the applicable model implementation;
* preserve logical product addressing and canonical product resolution;
* preserve dependency-driven minimal realization;
* preserve independent stage execution through `StageContext`;
* keep generated filesystem paths out of artifact configuration;
* consume dynamic product collections through manifests rather than directory
  scanning;
* preserve registered geometry until the responsible downstream consumer
  introduces physical dimensionalization;
* distinguish model-specific stage policy from reusable model-independent
  operations;
* prefer reusable operations when multiple model contexts demonstrate the same
  mechanical transformation;
* do not obtain shared behavior by invoking another model's stage
  implementation;
* do not introduce speculative abstractions merely because they might be useful
  to a future model;
* do not treat numeric stage IDs as semantic identities or operation types.

When implementation experience reveals that a permanent specification should
change, identify that as a specification decision rather than silently coding
around it.

## Working Principle

The permanent specifications define the destination.

Repository HEAD defines the starting point.

`prompts/TEST_DRIVEN_DEVELOPMENT.md` defines how behavioral changes are
developed and tested.

`CHANGEPLAN.md`, when present, describes a proposed route between the starting
point and destination.

The tests define the immediate behavioral target.

Each production change should establish one coherent capability or correction
and should be no larger than necessary to satisfy that behavioral target.

