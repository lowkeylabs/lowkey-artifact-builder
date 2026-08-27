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

- `ARCHITECTURE.md` as the permanent normative specification for the system;
- each model `DEFINITION.md` as the permanent normative specification for that
  model;
- the repository implementation and tests as the current implementation of
  those specifications.

Do not silently resolve differences between the permanent specifications and
HEAD. Identify meaningful discrepancies explicitly.

## Change Plan

If `CHANGEPLAN.md` exists, read it after reviewing the permanent
specifications.

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

## Development Strategy

Development is test-driven and incremental.

Select the **next coherent TDD slice** based on the current repository state.

Prefer a meaningful group of closely related behaviors over extremely small
one-test or one-line slices.

A good slice should normally be large enough to establish one useful
capability or architectural boundary while remaining small enough to:

1. express with a focused set of tests;
2. understand why those tests initially fail;
3. implement as one coherent production change;
4. validate independently;
5. commit as one logical change set.

A slice may contain several related tests and several related production
changes when they collectively establish one capability.

Avoid both extremes:

- do not fragment closely related behavior into unnecessarily tiny slices;
- do not combine multiple independent capabilities or stages into a change so
  large that the purpose of a failing test becomes unclear.

Prefer semantic and behavioral tests over tests of incidental implementation
details.

Reuse or extend existing test files when that produces clearer organization.
Do not create a new test file merely to isolate every invariant.

## Selecting the Next Slice

Before proposing work:

1. Review `ARCHITECTURE.md`.
2. Review the applicable model `DEFINITION.md` files.
3. Review `CHANGEPLAN.md`, if present.
4. Inspect the relevant production implementation.
5. Inspect the existing tests.
6. Determine which planned behaviors HEAD already satisfies.
7. Identify the next meaningful unmet architectural or model requirement.
8. Group closely related requirements when they naturally form one coherent
   implementation slice.

Do not select a slice solely because it appears next in `CHANGEPLAN.md`.
Repository HEAD and the permanent specifications determine what work is
actually required.

When existing implementation already satisfies a planned requirement, credit
that work and move forward.

## First Response in a New Thread

For the first development turn, **do not implement production code**.

First provide a concise assessment of:

- the current repository state;
- the current phase and subsection, if `CHANGEPLAN.md` exists;
- which nearby planned work is already satisfied;
- meaningful discrepancies between HEAD and the permanent specifications;
- the next coherent TDD slice you recommend.

For the recommended slice, explain briefly:

- which architectural or model requirements it advances;
- why the selected behaviors belong in one slice;
- what behavior HEAD already provides;
- what behavior is currently missing;
- which existing test files should be modified;
- which new test files, if any, are justified.

Then provide the **complete drop-in test changes** for that slice.

Do not provide production implementation yet.

The intended workflow is:

```text
review specifications + HEAD
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

The RED failures are part of the design process. Do not predict production
changes more precisely than the tests and observed failures justify.

## Architectural Discipline

While reviewing or proposing changes:

- keep the generic engine model-independent;
- keep model semantics in the applicable model implementation;
- preserve logical product addressing and canonical product resolution;
- preserve dependency-driven minimal realization;
- preserve independent stage execution through `StageContext`;
- keep generated filesystem paths out of artifact configuration;
- consume dynamic product collections through manifests rather than directory
  scanning;
- preserve registered geometry until the responsible downstream consumer
  introduces physical dimensionalization;
- distinguish model-specific stage policy from reusable model-independent
  operations;
- prefer reusable operations when multiple model contexts demonstrate the same
  mechanical transformation;
- do not obtain shared behavior by invoking another model's stage
  implementation;
- do not introduce speculative abstractions merely because they might be useful
  to a future model;
- do not treat numeric stage IDs as semantic identities or operation types.

When implementation experience reveals that a permanent specification should
change, identify that as a specification decision rather than silently coding
around it.

## Working Principle

The permanent specifications define the destination.

Repository HEAD defines the starting point.

`CHANGEPLAN.md`, when present, describes a proposed route between them.

The tests define the immediate behavioral target.

Each production change should be large enough to establish a meaningful
capability, but no larger than necessary to make that coherent set of tests
pass.
