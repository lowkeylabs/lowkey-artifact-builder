# Test-Driven Development

## Purpose

`lowkey-artifact-builder` uses test-driven development to keep changes
behaviorally precise, architecturally aligned, and appropriately scoped.

Test-driven development is a means of defining, discovering, and protecting
intended behavior. It is not a requirement to develop one assertion, one test,
or one line of production code at a time.

The goal is to establish meaningful behavioral contracts without unnecessarily
freezing implementation details, Model configuration, or the current Feature,
Variant, Stage, and Product inventories.

Tests should provide confidence that the application produces correct,
manufacturing-ready Products while allowing its architecture and Models to
evolve without unnecessary friction.

Test quality matters more than test quantity.

## Sources of Truth

Before designing tests for a change, determine the intended behavior from the
appropriate source.

The permanent normative specifications are:

```text
ARCHITECTURE.md
src/lowkey_artifact_builder/model/models/<model>/DEFINITION.md
```

`ARCHITECTURE.md` defines system-wide architectural semantics.

Each Model `DEFINITION.md` defines the semantics owned by that Model.

Repository HEAD and its existing tests describe the current implementation of
those specifications. They are important evidence, but existing implementation
details are not automatically requirements.

The CLI README describes the intended operator-facing command model.

`CHANGEPLAN.md`, when present, describes actionable remaining work. It is not
a permanent normative specification.

`FUTURE.md` records longer-term possibilities and unresolved ideas. It is not
normative.

Tests should express intended behavior supported by permanent specifications
or explicit design decisions.

Do not allow an existing implementation detail, test expectation, repository
default, or proposed implementation strategy to become a contract merely
because it is convenient to assert.

When sources disagree, identify the disagreement and resolve the applicable
contract before implementing around it.

## Core Principles

### Test behavior, not implementation inventory

A test should fail when the behavior it protects changes.

It should not ordinarily fail merely because an unrelated Model capability,
Feature, Variant, parameter, Stage, Product, or repository default was added
or changed.

Tests constrain implementation to intended behavior, not to the current
implementation strategy.

### Test at the boundary that owns the behavior

A test should exercise the narrowest meaningful boundary that can establish
the intended contract.

The narrowest meaningful boundary is not necessarily the smallest function.

A behavior involving Product selection, dependency resolution, and manufacturing
composition may require a test spanning those operations.

Conversely, an algorithm owned entirely by one Model should not require a
complete CLI workflow to verify it.

### Use coherent behavioral slices

A TDD slice should establish one meaningful capability or contract.

A slice may require several tests and several related production changes.

Do not fragment coherent behavior into a sequence of artificial RED/GREEN
cycles for individual helpers, branches, parameters, or internal refactorings.

Do not combine unrelated capabilities into a slice so large that the meaning
of failures becomes unclear.

### Investigate failures before changing code

A failing test is evidence requiring investigation.

It is not automatically proof that production code is incorrect.

A failure may reveal:

- a genuine production defect;
- an obsolete or overspecified test;
- an unrealistic fixture or mock;
- a test implementation or typing error;
- an unresolved architectural question; or
- an environmental or external-tool problem.

Determine which explanation applies before changing production behavior or
test expectations.

### Preserve manufacturing correctness

Tests should prioritize defects that can produce incorrect manufacturing
Products, corrupt persistent manufacturing state, violate Product identity
or dependency semantics, or cause material value-chain inefficiency.

The objective is not simply to make tests pass.

The objective is to establish correct, reliable, and efficient manufacturing
behavior.

# The TDD Process

## Preparation

Before beginning a meaningful implementation slice:

1. Read `prompts/NEW_THREAD.md` and the applicable CHANGEPLAN.
2. Review the relevant permanent specifications.
3. Inspect current HEAD and the existing implementation.
4. Credit behavior that HEAD already satisfies.
5. Identify the next unmet behavioral boundary.
6. Distinguish requirements from implementation observations and assumptions.
7. Resolve meaningful architectural or semantic questions.
8. Select the appropriate testing boundary and coherent slice.

Do not assume that a previously written CHANGEPLAN phase remains necessary
or correctly scoped after HEAD has changed.

## Design Before RED

TDD does not replace design.

When requested behavior is ambiguous, resolve the semantic question before
writing a test that would implicitly make the decision.

The intended sequence is:

```text
requirement
    ↓
identify behavioral ownership
    ↓
resolve design decisions
    ↓
update permanent specification when appropriate
    ↓
select test boundary
    ↓
RED
    ↓
implementation
    ↓
GREEN
    ↓
regression validation
```

Do not use:

```text
ambiguous requirement
    ↓
guess an implementation
    ↓
write tests around the guess
    ↓
treat passing tests as architectural validation
```

This is particularly important during AI-assisted development. An AI can
easily turn an observed implementation detail or unstated assumption into
a convincing but unintended test contract.

Test-first exploration is appropriate when the correct seam or ownership
boundary is uncertain.

Such exploration should clarify the design rather than silently decide it.

If an exploratory test reveals that the assumed contract is wrong, refine
the contract and test before committing to implementation.

When implementation experience reveals that a permanent specification should
change, identify and make that specification decision explicitly rather than
coding around the discrepancy.

## The RED/GREEN Cycle

Development should normally proceed through the following cycle:

```text
understand requested change
        ↓
classify change type
        ↓
identify intended behavior
        ↓
resolve design questions
        ↓
select behavioral boundary
        ↓
write coherent test slice
        ↓
run focused tests
        ↓
observe RED for intended reason
        ↓
evaluate failures and assumptions
        ↓
implement coherent behavior
        ↓
run focused tests
        ↓
investigate remaining failures
        ↓
run broader quality suite
        ↓
update documentation as needed
        ↓
commit coherent change
```

The RED failure is part of the design process.

A useful RED demonstrates that intended behavior is missing or incorrect.

A RED caused by an invalid import, nonexistent attribute, incorrect fixture,
unrealistic mock, or test typing error does not establish the intended
production defect.

Correct the test problem before treating the result as meaningful RED.

Do not predict or implement production changes more precisely than the
specifications, tests, and observed failures justify.

## Coherent Behavioral Slices

TDD does not require one test or one assertion per RED/GREEN cycle.

Prefer the smallest useful group of related behaviors that establishes one
capability or contract.

A good slice should normally be small enough that:

1. Its purpose can be stated clearly.
2. Its tests fail for understandable reasons.
3. Its production changes form one coherent implementation.
4. It can be validated independently.
5. It can be committed as one logical change.

A slice may contain several tests and several related production changes.

Once the intended boundary is established by RED, implement the coherent
behavior needed to satisfy that boundary.

Do not begin a new RED/GREEN cycle merely because the implementation requires
another helper, parameter, branch, component, or internal refactoring.

Additional RED/GREEN cycles are appropriate when a genuinely new behavioral
boundary is discovered.

The amount of new testing should follow the amount of meaningful behavioral
surface, not the number of production lines changed.

# Selecting Test Boundaries

## Test Behavior, Not Inventory

Prefer tests of relationships and semantics over tests that enumerate the
complete current contents of a Model or subsystem.

When testing one Feature, assert the presence and behavior of that Feature.

Do not ordinarily assert the complete set of Features supported by the Model.

When testing one Product, assert the relevant Product semantics.

Do not ordinarily assert the complete current Product inventory.

When testing one parameter, assert its relevant resolution or behavior.

Do not ordinarily compare a complete configuration dump.

Tests should be closed over the behavior they protect and open to unrelated
Model extension.

For example, adding a `lettering` Feature to Shape should not break tests for
an unrelated Shape `loop` Feature.

Adding a `base` Feature to Artwork should not require rewriting tests for
Artwork color analysis unless the new Feature intentionally changes those
semantics.

Exact inventories, dependency counts, Stage sequences, and parameter sets
are appropriate when their completeness or ordering is itself contractual.

Otherwise, prefer assertions about the specific elements and relationships
material to the behavior under test.

## Configuration Defaults

Do not accidentally convert mutable repository configuration into a permanent
software contract.

An exact default value should be asserted only when changing that exact value
would constitute an intentional semantic change.

If the purpose of a test is to establish that Model defaults participate in
configuration resolution, the test should not unnecessarily freeze the current
value of an unrelated default.

For example, a test of generic configuration resolution should not normally
assert the complete current `printer_colors` list from a Model
`parameters.toml`.

Routine changes to printer inventories, palettes, tuning values, or other
Model configuration should not cause unrelated tests to fail.

When an exact default is explicitly part of the Model's documented behavior,
testing that exact value is appropriate.

## Synthetic Models and Real Models

Generic infrastructure should remain independently testable from the current
set of production Models.

Tests of generic facilities such as configuration resolution, Model
registration, planning, dependency handling, Product resolution, and build
execution should normally use small synthetic Models when the behavior under
test does not require real Model semantics.

This prevents changes to Artwork or Shape from accidentally changing the
contract of generic engine tests.

Real Models should be used when their actual semantics are the subject of
the test.

A new conforming Model should ordinarily require new Model-specific tests
without requiring unrelated generic engine tests to be rewritten.

## Model Tests

Model tests protect semantics owned by a Model.

A Model test should depend on as little unrelated Model behavior as practical.

Shared Model test fixtures should normally represent ordinary Model defaults
without making every test responsible for the complete current parameter set.

Adding a defaulted parameter to a Model or Stage should not ordinarily require
unrelated behavioral tests to be rewritten merely because their test resolver
or fixture enumerates every parameter the implementation may request.

Where practical, shared fixtures should use production defaults or otherwise
provide representative defaults while allowing tests to override only the
parameters material to the behavior under test.

Exact assertions about which parameters a Stage resolves are appropriate when
parameter ownership or Stage partitioning is itself the behavior being tested.

Keep that strictness in focused tests rather than imposing it incidentally
on all tests that exercise the Stage.

For example, a test of physical Artwork sizing may establish that:

- the intended physical dimension is achieved;
- aspect ratio is preserved; and
- registered layers receive a common transform.

It should not also depend on the current printer palette, complete Feature
inventory, or unrelated packaging behavior.

Model tests may use real Model configuration when that configuration is
material to the behavior under test.

## Cross-Model and Product Dependency Tests

Cross-Model tests protect contracts that cannot be established by testing
either Model independently.

Examples include:

- one Model consuming a registered Product from another Model;
- selection of a producer Artifact or Realization;
- correct Product identity and resolution;
- preservation of source representation;
- dependency freshness and invalidation;
- persistence and reuse of manufacturing Products.

Prefer tests that establish the intended relationship between producer,
consumer, selected Product, and resulting behavior.

Do not assert the complete current dependency inventory when only one
dependency relationship is under test.

Do not assume that every planned dependency must be consumed by every Stage.

Distinguish dependency declaration, dependency binding, Stage input exposure,
actual Product consumption, and producer build execution.

These are related but different contracts.

When the correctness of dependency selection depends on several layers,
a focused integration test may be more useful than multiple tests asserting
the internal structure of each intermediate object.

Do not introduce generic engine semantics solely to accommodate a
manufacturing-specific representation.

When a cross-Model change exposes uncertainty about Product selection,
representation, or ownership, resolve that architectural question before
rewriting existing tests to accept the new behavior.

## Acceptance Tests

Acceptance tests establish important end-to-end or user-observable
capabilities.

They should be broader and fewer than unit and Model behavior tests.

Acceptance tests should establish meaningful outcomes such as:

- an Artifact can be built into the expected persistent Product;
- one Model can consume a Product from another Model;
- a Variant can be selected and built;
- a CLI workflow produces the intended user-visible result;
- a manufacturing Product preserves the intended geometry, artwork, or
  representation.

Acceptance tests should not reproduce every lower-level assertion already
established by focused tests.

An acceptance test should assert the aspects of the result that make the
capability meaningful without unnecessarily snapshotting the complete
current implementation.

For manufacturing workflows, a small number of realistic end-to-end tests
may provide greater confidence than many tests of intermediate implementation
details.

## External Tools

Tests should not require external modeling tools such as OpenSCAD or Inkscape
unless the test is specifically intended to exercise integration with that
tool.

Generic configuration, Model registration, planning, dependency handling,
Product resolution, and build orchestration should remain testable without
external modeling software.

Where practical, test the data or command boundary presented to an external
tool separately from integration tests that actually execute the tool.

# Test Fixtures, Mocks, and Helpers

## Prefer Realistic Boundaries

Use real application objects and production interfaces where practical.

Mocks are appropriate when they isolate an external dependency, expensive
operation, nondeterministic service, or independently tested boundary.

Do not mock substantial portions of the application merely to avoid creating
small, representative domain objects.

An unrealistic mock can produce failures unrelated to production behavior
or conceal defects that realistic execution would reveal.

For example, a mock whose `has_input()` method returns a truthy value for
every requested input does not faithfully represent a Stage context with
specific available inputs.

Prefer a real Stage context or an explicitly configured test double whose
available inputs are defined.

## Keep Fixtures Minimal but Representative

A fixture should establish the conditions needed for the behavior under test.

It should not silently introduce unrelated Model Features, parameters,
dependencies, or configuration assumptions.

Shared fixtures should represent ordinary application behavior while allowing
individual tests to override only what matters.

Do not make every test responsible for the complete current dependency or
parameter inventory.

Avoid broad fixture changes that cause unrelated tests to fail when a Model
is extended.

## Preserve Type Information

Test code is production-adjacent code and must satisfy the repository's
quality standards.

Use actual domain types in helper signatures when those types are known.

Do not annotate a helper result as `object` when callers must access known
attributes such as `product_ref`, `binding`, or `path`.

Do not use `Any`, unsafe casts, or type-checker suppressions merely to silence
errors introduced by poorly typed test helpers.

Use the appropriate public types or defining-module imports according to
the repository's existing conventions.

Before expanding a helper, verify that its return type and assumptions
match the actual application contract.

A test helper should simplify the test without concealing important behavior.

## Avoid Excessive Test Abstraction

Do not create elaborate test frameworks merely to reduce a few repeated
setup statements.

Prefer explicit setup when it makes the behavioral contract easier to
understand.

Shared helpers are useful when they express stable, meaningful domain
operations or eliminate genuinely repetitive setup.

Avoid helpers that:

- conceal which Artifact or Realization is selected;
- assume a complete dependency inventory;
- freeze unrelated Model defaults;
- return untyped objects;
- introduce implicit mock behavior; or
- require unrelated tests to change when one Model evolves.

The test should remain understandable without reconstructing a large
network of helper implementations.

# TDD by Change Type

Different kinds of development work require different testing strategies.

Before proposing a TDD slice, classify the work being performed.

## Fixing a Bug

A bug fix should begin by identifying the intended behavior and reproducing
the defect at the narrowest meaningful behavioral boundary.

First determine whether:

1. HEAD violates an existing permanent specification; or
2. HEAD conforms to the specification but the specified behavior is no longer
   desired.

In the second case, correct the permanent specification before treating the
implementation as defective.

Then add a regression test that demonstrates the incorrect behavior.

A good regression test:

- fails against the defective implementation;
- fails for the reason represented by the bug;
- expresses the corrected behavior;
- avoids unrelated Model configuration and Features; and
- remains useful after future Model extension.

Do not use a complete real-world Artifact as the regression fixture when a
small synthetic example expresses the defect more clearly.

After the regression test is RED, make the smallest coherent production
change that establishes the corrected behavior.

## Adding a New Model

A new Model should conform to existing generic Model contracts while
defining its own Model-specific semantics.

Do not copy the complete test suite of an existing Model merely because
the new Model has superficially similar Stages or Products.

Generic infrastructure tests should already establish that conforming
Models can participate in registration, configuration, planning, dependency
resolution, Product resolution, and execution.

Tests for the new Model should concentrate on:

- its registration and declarative contract where necessary;
- semantics defined by its `DEFINITION.md`;
- its Model-specific Stages and Products;
- its Feature behavior;
- its Model-specific validation; and
- important end-to-end Model capabilities.

If adding a conforming Model requires unrelated generic tests to add the
new Model name to expected inventories, examine whether those generic
tests are overspecified.

Model-specific behavior belongs in the Model rather than being added to
the generic engine merely to support the new Model.

## Adding a Feature to an Existing Model

A new Feature should first have its Model semantics defined.

Before writing tests, identify interactions with existing Model concepts
that could affect the meaning of the Feature.

Relevant questions may include:

- when the Feature exists;
- which parameters control it;
- parameter defaults and derivation;
- physical dimensions;
- placement;
- registration;
- material or color ownership;
- Product participation;
- interaction with other Features; and
- whether the Feature affects the Artifact's defined extent or size.

Resolve meaningful ambiguities in the applicable Model `DEFINITION.md`
before allowing tests or implementation to decide them implicitly.

Feature tests should establish the Feature's semantics without asserting
the complete current state of the Model.

Adding one Feature should not ordinarily require changing tests for
unrelated Features.

When two Models support conceptually similar Features, each Model remains
responsible for its own semantics.

Reuse model-independent operations only when the shared behavior is
genuinely mechanical and reusable.

Do not obtain reuse by invoking another Model's Stage implementation.

## Adding a Variant from Existing Features

A Variant is primarily configuration over capabilities already supplied
by a Model.

Once the underlying Model Features and parameter semantics are tested,
adding a Variant should normally require relatively little new behavioral
testing.

Variant tests should concentrate on:

- Variant registration or discovery;
- the intended sparse parameter overrides;
- inheritance of unspecified Model defaults; and
- Variant identity and selection where relevant.

Do not repeat the complete behavioral test suite of every Feature used
by the Variant.

If Feature tests establish that a set of loop parameters produces the
correct loop geometry, a Variant test generally needs to establish that
the Variant supplies those intended loop parameters.

It does not need to independently prove the geometry again.

Add an acceptance test for a Variant only when it protects a meaningful
integration or user-facing capability not already established by the
Model, Feature, configuration, and selection tests.

Variants should remain inexpensive to add when they are compositions
of already-tested Model capabilities.

## Adding or Changing a CLI Command

CLI commands expose application capabilities and streamline user workflows.

CLI tests should protect the boundary between user intent and underlying
application behavior.

They should concentrate on:

- command and option interpretation;
- validation of user input;
- translation of CLI input into the appropriate application operation;
- selection of Model and Variant identity;
- useful errors;
- user-visible output; and
- workflow behavior introduced specifically by the command.

Do not use CLI tests to duplicate the detailed semantics of an engine or
Model operation that already has focused tests.

For example, a CLI command exposing color analysis should test that the
command requests the correct analysis and presents the intended result.

It should not also reproduce the mathematical tests of the underlying
color assignment algorithm.

Prefer testing application behavior below Click parsing when the behavior
is not inherently a CLI concern.

Keep CLI orchestration thin enough that underlying capabilities remain
usable and testable independently.

## Refactoring

Refactoring changes implementation without intentionally changing
observable behavior.

Existing tests should normally provide the behavioral protection for
a refactoring.

Do not create tests merely because production code is being rearranged.

Add tests before refactoring only when an important existing behavior
is not adequately protected and that missing protection materially
increases the risk of the refactoring.

If a refactoring causes a test to fail, determine whether:

- observable behavior actually changed;
- the test depends on an implementation detail that is not contractual; or
- the test revealed an architectural boundary that the refactoring violated.

Do not preserve an accidental implementation detail solely to keep an
overspecified test green.

# Evaluating RED and Regression Failures

## Classify Before Repairing

When a test fails, identify the failure category before changing code.

| Failure category | Appropriate response |
|---|---|
| Genuine production defect | Correct production behavior and preserve the regression test |
| Obsolete contractual assertion | Update or remove the assertion after confirming the contract change |
| Overspecified implementation assertion | Narrow the assertion to the behavior being protected |
| Invalid fixture or mock | Correct the test setup to represent actual application behavior |
| Test implementation or typing error | Correct the test code without changing production semantics |
| Architectural ambiguity | Resolve the contract before continuing implementation |
| Environmental or external-tool failure | Correct or isolate the environment without redefining application behavior |

Do not assume that all failures in a test run belong to the same category.

Do not automatically rewrite tests to reflect the behavior of the current
implementation.

Observed behavior is evidence, not necessarily the desired contract.

## Diagnose Failure Clusters

When several regression failures arise from one architectural or semantic
change, investigate their common cause before repairing individual tests.

A cluster of failures involving Product dependencies, for example, may
indicate:

- a changed dependency declaration;
- incorrect producer selection;
- inconsistent Realization binding;
- unexpected Stage input exposure;
- unnecessary producer execution;
- incorrect dependency freshness; or
- tests that freeze obsolete dependency inventories.

Do not repair each failing assertion independently without understanding
which explanation applies.

If the same underlying question appears repeatedly, stop the test-repair
cycle and return to architectural analysis.

The purpose is to avoid spending substantial time making tests accept an
implementation whose correctness has not been established.

## Distinguish Planning from Consumption

A declared dependency is not necessarily a consumed Product.

A planned dependency is not necessarily an executed producer.

A bound Product is not necessarily an input to every Stage.

A Product appearing in a Stage context does not, by itself, establish
that the Stage uses it correctly.

Tests should distinguish these contracts.

For example, verifying that SHAPE can bind both vector and raster Artwork
products does not establish which representation COMPOSE should consume.

Likewise, verifying that the planner resolves a Product does not establish
that the producer is rebuilt only when necessary.

Test the relevant contract at its owning boundary.

Do not use planning assertions as substitutes for manufacturing behavior
tests, or vice versa.

## Preserve Correctness While Relaxing Brittleness

When a legitimate architectural, Model, Feature, Variant, or configuration
change causes an existing test to fail, ask:

1. What behavior is this test intended to protect?
2. Is that behavior supported by a permanent specification?
3. Is the failing assertion material to that behavior?
4. Is the test freezing an incidental implementation detail?
5. Is the test enumerating an intentionally extensible inventory?
6. Is the test freezing a mutable repository default?
7. Has the underlying contract intentionally changed?

Rewrite or remove tests that protect behavior deliberately removed by a
specification change.

Relax tests that are unnecessarily broader than the behavior they protect.

Do not weaken a test merely because its valid contractual assertion is
inconvenient for the new implementation.

Do not change production code merely to preserve an obsolete test.

## Curate Tests When Encountered

Existing tests should gradually evolve with the testing practices in
this document.

Broad test-suite cleanup is not required merely to bring older tests
into conformity with current conventions.

When development naturally causes an existing test to be examined or
modified, evaluate it against the current testing policy.

Preserve assertions that protect intended behavior.

Update, remove, or relax assertions that instead protect:

- incidental implementation details;
- contracts intentionally removed;
- complete Model, Feature, Variant, Stage, or Product inventories when
  completeness is not contractual;
- unrelated Model composition or behavior;
- mutable repository configuration that is not under test; or
- compatibility behavior the current specification no longer requires.

Do not expand the current change into unrelated test-suite cleanup.

Tests unrelated to the current work may remain for later evaluation.

A test encountered during a change should leave the suite at least as
behaviorally precise and no more accidentally restrictive than before.

# AI-Assisted Development

Tests have an additional role during AI-assisted development: they establish
the behavioral boundary within which production changes are authorized.

That makes test quality more important, not test quantity.

Before proposing tests, distinguish:

- explicit requirements;
- permanent specifications;
- current implementation;
- existing tests;
- current repository configuration;
- assumptions; and
- possible future designs.

Do not convert observations about HEAD into requirements without justification.

In particular:

- current Model Features do not imply a closed Feature set;
- current Products do not imply a closed Product set;
- current Variants do not imply a closed Variant set;
- current repository defaults are not automatically contractual;
- historical implementation names do not automatically define architectural
  terminology; and
- the current implementation strategy is not automatically required.

## Verify Contracts Before Writing Tests

Do not invent application attributes, exported types, dependency keys,
configuration parameters, or Stage behavior to make a proposed test plausible.

When a test depends on a specific API or domain type, inspect the current
definition before relying on it.

If the current contract cannot be established from available evidence,
identify the uncertainty rather than asserting an unverified interface.

Do not introduce production API changes merely to satisfy an assumption
made in newly written tests.

## Avoid Speculative Test Repair

When RED results are available, use the actual failures to guide analysis
and implementation rather than relying only on predictions made before
the tests ran.

Do not provide repeated test rewrites that merely accommodate each new
failure without examining the shared architectural cause.

If several test modifications produce additional unrelated failures,
reassess the proposed test design.

When the requested behavior exposes an unresolved architectural question,
surface the question rather than silently choosing an answer through a
test or production implementation.

Once the behavior is sufficiently defined, prefer providing a complete
coherent test slice rather than repeatedly asking for permission to add
each individual test.

## Keep Changes Reviewable

Prefer changes that can be reviewed as one coherent behavioral unit.

When modifying existing tests, explain why the original assertion is
no longer appropriate and what behavioral protection replaces it.

Do not describe a test as obsolete solely because it fails after a
production change.

Do not declare success based only on focused tests when relevant
regressions remain unresolved.

The objective is to reduce uncertainty about correct behavior, not to
maximize the number of GREEN test results.

# Test Organization

Prefer placing tests according to the behavior they protect.

Reuse or extend existing test files when that produces clear organization.

Do not create a new test file merely to isolate every new invariant.

Create a new test file when it represents a meaningful new behavioral
area, Feature, Model, integration boundary, or acceptance capability.

Avoid large test files that accumulate unrelated behaviors merely
because they exercise the same high-level command or Model.

Test helpers should make the behavior under test clearer.

They should not hide important setup or create broad fixtures whose
unrelated defaults become implicit test dependencies.

Conversely, shared helpers should not make unrelated tests responsible
for the complete current dependency or parameter inventory.

A helper should be strict about dependencies only when that strictness
is material to the behavior being protected.

# Quality Validation

## Focused Validation

After implementing a coherent behavioral slice, run the focused tests
that establish its contract.

Confirm that failures are resolved for the intended reasons.

Do not treat a test as validated merely because an assertion was removed
or changed to match the current implementation.

Run applicable formatting, linting, and static type checks for the
modified code.

Test code is subject to the same relevant quality standards as
production code.

## Broader Regression Validation

After focused tests pass, run the appropriate broader quality suite.

Investigate failures by category and common cause.

A cluster of related failures may require revisiting the architectural
contract rather than making many isolated test modifications.

Do not expand the implementation to satisfy obsolete assertions.

Do not dismiss failures that protect valid behavior.

If an environmental or unrelated failure prevents completion, identify
it explicitly rather than claiming the entire suite is GREEN.

## Production Capability

Every completed implementation slice must leave the application
production-capable.

A focused test suite passing is insufficient if relevant manufacturing
regressions remain unexplained.

Changes must preserve existing Product identity, persistence,
dependency, configuration, and manufacturing semantics unless those
contracts have been explicitly revised.

# Commit Messages

Use Conventional Commit-style subjects for new commits:

```text
<type>: <imperative description>
```

Use `feat`, `fix`, `refactor`, `test`, `docs`, or `chore` as appropriate.

Examples:

```text
feat: add artwork loop configuration and validation
fix: preserve realization product namespace
refactor: normalize variant selection
test: verify loop participation semantics
docs: define artwork loop feature
```

Keep the subject concise and describe the coherent change being committed.

Do not rewrite existing history solely to conform to this convention.

# Completion

A TDD slice is complete when:

1. The intended behavior is sufficiently specified.
2. The behavioral ownership and testing boundary are understood.
3. Focused tests express the intended contract.
4. Tests were observed RED for the intended reason when new behavior
   required production changes.
5. Production implementation makes the focused tests pass.
6. Relevant regression failures are resolved or explicitly understood
   and justified.
7. Applicable formatting, static analysis, and broader test suites pass.
8. Permanent documentation is updated when architectural, Model,
   configuration, or public behavior changed.
9. The application remains production-capable.
10. The coherent change is ready to commit.

The objective is not maximum test coverage or maximum test count.

The objective is a test suite that gives strong confidence in correct
manufacturing behavior while allowing the architecture and Models to
evolve without unnecessary friction.

A successful TDD cycle produces more than GREEN tests.

It produces a correct behavioral contract, a coherent implementation,
and durable confidence that the application continues to do the
right thing.
