# CHANGEPLAN

## Purpose

Continue refining `lowkey-artifact-builder` around the manufacturing value
chain established by the current repository HEAD.

The operator's ordinary goal is:

> Move customer artwork to a correct, manufacturing-ready Product with the
> fewest necessary decisions, actions, and computations.

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
manufacturing-ready Product
      ↓
slicer / xTool Studio / share / manufacture
```

`create` and `build` define the ordinary value chain. `show`, `config`,
`colors`, and `clean` support that path when the operator needs discovery,
inspection, customization, correction, color selection, or maintenance. These
support commands must not become mandatory ceremony before routine
manufacturing.

This CHANGEPLAN contains actionable remaining work, not a history of completed
implementation or a catalog of speculative capabilities. Completed behavior
should be credited from HEAD and removed from the plan. Longer-term goals and
unresolved design ideas belong in `FUTURE.md`; that document is not normative.

Before promoting an item from `FUTURE.md`, reevaluate current HEAD and the
permanent specifications and establish a sufficiently understood behavioral
boundary.

Phases may be removed, reordered, combined, or rewritten after each completed
implementation slice. Phase numbering is local to the current plan.

## Planning and development rules

`ARCHITECTURE.md` and the applicable Model `DEFINITION.md` files are normative.
Repository HEAD defines the current implementation. The CLI README defines the
intended operator-facing command model.

`prompts/TEST_DRIVEN_DEVELOPMENT.md` defines the development and testing
methodology. It governs behavioral test design, RED/GREEN cycles, test
organization, regression evaluation, and completion criteria.

This CHANGEPLAN describes temporary remaining work. It must not redefine
permanent architecture or duplicate the detailed TDD methodology.

At the beginning of a thread and before each meaningful implementation slice:

1. Reload and follow `prompts/NEW_THREAD.md` and
   `prompts/TEST_DRIVEN_DEVELOPMENT.md`.
2. Compare CHANGEPLAN with current HEAD, `ARCHITECTURE.md`, applicable Model
   definitions, and relevant CLI documentation.
3. Credit behavior HEAD already satisfies.
4. Identify the next unmet behavioral boundary rather than assuming the plan
   is still current.
5. Distinguish explicit requirements, normative specifications, existing
   behavior, test assumptions, and unresolved design questions.
6. Resolve meaningful semantic or architectural questions before encoding
   behavior in tests or implementation. Test-first exploration may help
   discover or clarify an uncertain boundary, but an exploratory test must
   not silently become the specification.
7. Select a coherent behavioral TDD slice, using one test or a small related
   test set to establish the intended contract.
8. Implement the smallest correct, coherent production change at the layer
   that owns the behavior.
9. Run focused tests, evaluate failures, and then run the appropriate
   complete quality suite.
10. Reevaluate the plan against the resulting implementation and update
    permanent documentation when required.

Tests should protect useful behavioral boundaries rather than inventory
implementation details. High-level CLI/application seams should be protected
as they are introduced. Lower-level tests should protect behavior actually
owned by that layer.

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
structured application errors into operator-facing prose.

Reusable workflow behavior belongs below Click and should return structured
domain/application information rather than Rich objects or
presentation-specific strings.

The CLI operates on the current working directory as project root.

A registered Artifact may legitimately exist under `originals/` before
`artifacts/<artifact_id>/` exists.

Commands must preserve the distinction between registered Artifact identity,
materialized Artifact workspace, and manufacturing Product state.

Missing collection directories normally represent empty collections. An
explicitly requested missing object is an operator error.

Expected domain errors should be concise and traceback-free; unexpected
invariant or programming failures must not be indiscriminately converted into
ordinary operator failures.

Routine output should be lean and oriented toward the operator's next useful
decision. Operator-facing Product paths should be concise and useful from the
project root.

Do not expose Stage, resolver, dependency, or filesystem mechanics unless
they answer an operator question.

Do not change Product identity, dependency semantics, configuration
precedence, Model semantics, manufacturing ownership, persistence semantics,
or color semantics merely to simplify CLI presentation.

If work exposes a genuine architectural mismatch, resolve that mismatch
explicitly against the permanent specifications before proceeding.

Manufacturing-specific representations and operations must not be smuggled
into the generic engine or inferred solely from visual color.

Preserve established logical color identities, component registration, and
existing SHAPE SVG and 3MF behavior unless an explicit Model contract change
requires otherwise.

## TDD execution and regression discipline

Follow `prompts/TEST_DRIVEN_DEVELOPMENT.md` for the complete TDD methodology.
The following rules reinforce its application to every CHANGEPLAN phase.

### Behavioral boundaries

TDD remains test-first for meaningful new behavior.

Before implementing a change, establish the intended behavioral contract and
select the appropriate test boundary.

A RED test should demonstrate missing or incorrect behavior, not merely an
unimplemented helper, a particular internal structure, or an incidental
implementation assumption.

TDD cycles should normally correspond to coherent behavioral slices rather
than individual implementation changes.

One test may be sufficient to establish a boundary. A small related test set
is appropriate when materially different cases are needed to define the same
contract.

Once RED establishes the intended boundary, implement the coherent behavior
needed to make it work. Do not start another RED/GREEN cycle merely because
the implementation requires another helper, parameter, branch, component,
or internal refactoring.

Add narrower tests when they protect independently meaningful contracts,
clarify uncertain boundaries, reproduce defects, or address specific
algorithmic or regression risks.

Test quantity should follow meaningful behavioral surface, not the number
of implementation changes.

### Evaluating failures

A failing test is evidence requiring investigation, not automatic proof that
production code is incorrect.

Before changing production code or modifying an existing test, determine:

1. What behavioral contract does the test protect?
2. Is that contract supported by a permanent specification or explicit
   design decision?
3. Does the failure demonstrate incorrect production behavior?
4. Does the test instead depend on incidental implementation structure,
   mutable configuration, an extensible inventory, or an unrealistic fixture?
5. Has the relevant contract intentionally changed?

Preserve valid contractual assertions, even when they are inconvenient for
the new implementation.

Revise or remove obsolete and overspecified assertions when justified by
the intended behavior. Do not weaken tests merely to obtain GREEN.

Do not introduce production compatibility behavior solely to satisfy an
obsolete test.

When several failures cluster around a shared architectural or semantic
change, investigate the common cause before repairing tests individually.

In particular, do not repeatedly rewrite test expectations to accommodate
an implementation whose underlying contract remains unresolved.

### Test isolation and maintenance

Use the testing level appropriate to the behavior being protected.

Generic engine behavior should not unnecessarily depend on the current
inventory or configuration of production Models.

Model tests should focus on semantics owned by that Model.

Acceptance tests should establish meaningful integrated or operator-visible
outcomes without duplicating every lower-level assertion.

Prefer realistic fixtures and actual application objects where practical.
Use mocks at meaningful boundaries, and ensure mocked behavior represents
the contract being exercised.

Avoid test helpers that accidentally impose unrelated parameter, dependency,
Feature, Variant, Stage, or Product inventories on every caller.

When existing tests are encountered during development, improve their
behavioral precision where relevant, but do not expand the current slice
into unrelated test-suite cleanup.

### Completion

A behavioral slice is complete when:

1. The intended behavior and ownership boundary are sufficiently understood.
2. Appropriate focused tests establish the contract.
3. New behavior has been observed RED for the intended reason before
   implementation, where applicable.
4. The production implementation satisfies the intended behavior.
5. Regression failures have been resolved or explicitly justified against
   the applicable contracts.
6. Focused tests and the appropriate broader quality suite pass.
7. Permanent specifications and operator documentation are updated when
   their contracts or documented behavior have changed.
8. The application remains production-capable.

Do not declare a slice complete merely because its new tests pass while
relevant regressions remain unexplained.

The objective is not maximum test count or coverage. It is confidence in
correct manufacturing behavior without unnecessary restrictions on future
architectural and Model evolution.
