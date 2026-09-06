# Test-Driven Development

`lowkey-artifact-builder` uses test-driven development to keep changes
behaviorally precise, architecturally aligned, and appropriately scoped.

Test-driven development is a means of defining and protecting intended
behavior. It is not a requirement to develop one assertion, one test, or one
line of production code at a time.

The goal is to use tests to establish the boundary of a change without
unnecessarily freezing the current implementation, Model configuration, or
Feature set.

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

`CHANGEPLAN.md`, when present, describes planned work. It is not a permanent
normative specification.

Tests should express intended behavior supported by the permanent
specifications or by an explicit design decision.

Do not allow an existing implementation detail to become a contract merely
because it is convenient to assert in a test.

## Core Principle

A test should fail when the behavior it protects changes.

It should not ordinarily fail merely because an unrelated Model capability,
Feature, Variant, parameter, stage, Product, or repository default was added
or changed.

Tests constrain implementation to the intended behavior, not to the current
implementation.

## The TDD Cycle

Development should normally proceed through the following cycle:

```text
understand the requested change
        ↓
classify the kind of change
        ↓
identify the intended behavior
        ↓
resolve specification or design questions
        ↓
select the appropriate test boundary
        ↓
write a coherent set of tests
        ↓
run the tests
        ↓
observe RED for the intended reason
        ↓
evaluate the failures
        ↓
implement the behavior
        ↓
run focused tests
        ↓
run the broader quality suite
        ↓
commit the coherent change
```

The RED failure is part of the design process.

Do not predict or implement production changes more precisely than the
specification, tests, and observed failures justify.

## Coherent Behavioral Slices

TDD does not require one test or one assertion per red/green cycle.

Prefer a coherent behavioral slice: the smallest useful group of related
behaviors that establishes one capability or contract.

A good slice should normally be small enough that:

1. its purpose can be stated clearly;
2. its tests fail for understandable reasons;
3. the production changes form one coherent implementation;
4. it can be validated independently; and
5. it can be committed as one logical change.

A slice may contain several tests and several related production changes.

Avoid both extremes:

* do not fragment closely related behavior into unnecessarily tiny slices;
* do not combine independent capabilities into a slice so large that the
  meaning of RED failures becomes unclear.

The amount of new testing should follow the amount of new behavioral surface,
not the number of production lines changed.

## Design Before RED

TDD does not replace design.

When a requested behavior is ambiguous, resolve the semantic question before
writing a test that would implicitly make the decision.

The intended sequence is:

```text
requirement
    ↓
design decision
    ↓
permanent specification, when appropriate
    ↓
test
    ↓
implementation
```

Do not use:

```text
ambiguous requirement
    ↓
guess a test
    ↓
allow the test to become the specification
```

This is especially important during AI-assisted development. An AI can easily
turn an observed implementation detail or an unstated assumption into a
convincing but unintended test contract.

When implementation experience reveals that a permanent specification should
change, identify and make that specification decision explicitly rather than
coding around the discrepancy.

## Test Behavior, Not Inventory

Prefer tests of relationships and semantics over tests that enumerate the
complete current contents of a Model or subsystem.

When testing one Feature, assert the presence and behavior of that Feature.
Do not ordinarily assert the complete set of Features supported by the Model.

When testing one Product, assert the relevant Product semantics. Do not
ordinarily assert the complete current Product inventory.

When testing one parameter, assert its relevant resolution or behavior. Do not
ordinarily compare a complete configuration dump.

Tests should be closed over the behavior they protect and open to unrelated
Model extension.

For example, adding a `lettering` Feature to Shape should not break tests for
an unrelated Shape `loop` Feature.

Adding a `base` Feature to Artwork should not require rewriting tests for
Artwork color analysis unless the new Feature intentionally changes those
semantics.

## Configuration Defaults

Do not accidentally convert mutable repository configuration into a permanent
software contract.

An exact default value should be asserted only when changing that exact value
would constitute an intentional semantic change.

If the purpose of a test is to establish that Model defaults participate in
configuration resolution, the test should not unnecessarily freeze the
current value of an unrelated default.

For example, a test of generic configuration resolution should not normally
assert the complete current `printer_colors` list from a Model
`parameters.toml`.

Routine changes to printer inventories, palettes, tuning values, or other
Model configuration should not cause unrelated tests to fail.

When the exact default is explicitly part of the Model's documented behavior,
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

Real Models should be used when their actual Model semantics are the subject
of the test.

A new conforming Model should ordinarily require new Model-specific tests
without requiring unrelated generic engine tests to be rewritten.

## Model Tests

Model tests protect semantics owned by a Model.

A Model test should depend on as little unrelated Model behavior as practical.

For example, a test of physical Artwork sizing may establish that:

* the intended physical dimension is achieved;
* aspect ratio is preserved; and
* registered layers receive a common transform.

It should not also depend on the current printer palette, complete Feature
inventory, or unrelated packaging behavior.

Model tests may use the real Model configuration when that configuration is
material to the behavior under test.

## Acceptance Tests

Acceptance tests establish important end-to-end or user-observable
capabilities.

They should be broader and fewer than unit and Model behavior tests.

Acceptance tests should establish meaningful outcomes such as:

* an Artifact can be built into the expected persistent Product;
* one Model can consume a Product from another Model;
* a Variant can be selected and built;
* a CLI workflow produces the intended user-visible result.

Acceptance tests should not reproduce every lower-level assertion already
established by focused tests.

An acceptance test should assert the aspects of the result that make the
capability meaningful without unnecessarily snapshotting the complete current
implementation.

## External Tools

Tests should not require external modeling tools such as OpenSCAD or Inkscape
unless the test is specifically intended to exercise integration with that
tool.

Generic configuration, Model registration, planning, dependency handling,
Product resolution, and build orchestration should remain testable without
external modeling software.

Where practical, test the data or command boundary presented to an external
tool separately from integration tests that actually execute the tool.

# TDD by Change Type

Different kinds of development work require different testing strategies.

Before proposing a TDD slice, classify the work being performed.

The common categories below are guidelines for selecting the appropriate test
boundary.

## Fixing a Bug

A bug fix should begin by identifying the intended behavior and reproducing the
defect at the narrowest meaningful behavioral boundary.

First determine whether:

1. HEAD violates an existing permanent specification; or
2. HEAD conforms to the specification but the specified behavior is no longer
   desired.

In the second case, correct the permanent specification before treating the
implementation as defective.

Then add a regression test that demonstrates the incorrect behavior.

A good regression test:

* fails against the defective implementation;
* fails for the reason represented by the bug;
* expresses the corrected behavior;
* avoids unrelated Model configuration and Features; and
* remains useful after future Model extension.

Do not use a complete real-world Artifact as the regression fixture when a
small synthetic example expresses the defect more clearly.

After the regression test is RED, make the smallest coherent production change
that establishes the corrected behavior.

## Adding a New Model

A new Model should conform to existing generic Model contracts while defining
its own Model-specific semantics.

Do not copy the complete test suite of an existing Model merely because the new
Model has superficially similar stages or Products.

Generic infrastructure tests should already establish that conforming Models
can participate in registration, configuration, planning, dependency
resolution, Product resolution, and execution.

Tests for the new Model should concentrate on:

* its registration and declarative contract where necessary;
* semantics defined by its `DEFINITION.md`;
* its Model-specific stages and Products;
* its Feature behavior;
* its Model-specific validation; and
* important end-to-end Model capabilities.

If adding a conforming Model requires unrelated generic tests to add the new
Model name to expected inventories, examine whether those generic tests are
overspecified.

Model-specific behavior belongs in the Model rather than being added to the
generic engine merely to support the new Model.

## Adding a Feature to an Existing Model

A new Feature should first have its Model semantics defined.

Before writing tests, identify interactions with existing Model concepts that
could affect the meaning of the Feature.

Relevant questions may include:

* when the Feature exists;
* which parameters control it;
* parameter defaults and derivation;
* physical dimensions;
* placement;
* registration;
* material or color ownership;
* Product participation;
* interaction with other Features; and
* whether the Feature affects the Artifact's defined extent or size.

Resolve meaningful ambiguities in the applicable Model `DEFINITION.md` before
allowing tests or implementation to decide them implicitly.

Feature tests should establish the Feature's semantics without asserting the
complete current state of the Model.

Adding one Feature should not ordinarily require changing tests for unrelated
Features.

When two Models support conceptually similar Features, each Model remains
responsible for its own semantics. Reuse model-independent operations only when
the shared behavior is genuinely mechanical and reusable. Do not obtain reuse
by invoking another Model's stage implementation.

## Adding a Variant from Existing Features

A Variant is primarily configuration over capabilities already supplied by a
Model.

Once the underlying Model Features and parameter semantics are tested, adding
a Variant should normally require relatively little new behavioral testing.

Variant tests should concentrate on:

* Variant registration or discovery;
* the intended sparse parameter overrides;
* inheritance of unspecified Model defaults; and
* Variant identity and selection where relevant.

Do not repeat the complete behavioral test suite of every Feature used by the
Variant.

If Feature tests establish that a set of loop parameters produces the correct
loop geometry, a Variant test generally needs to establish that the Variant
supplies those intended loop parameters. It does not need to independently
prove the geometry again.

Add an acceptance test for a Variant only when it protects a meaningful
integration or user-facing capability not already established by the Model,
Feature, configuration, and selection tests.

Variants should remain inexpensive to add when they are compositions of
already-tested Model capabilities.

## Adding or Changing a CLI Command

CLI commands expose application capabilities and streamline user workflows.

CLI tests should protect the boundary between user intent and the underlying
application behavior.

They should concentrate on:

* command and option interpretation;
* validation of user input;
* translation of CLI input into the appropriate application operation;
* selection of Model and Variant identity;
* useful errors;
* user-visible output; and
* workflow behavior introduced specifically by the command.

Do not use CLI tests to duplicate the detailed semantics of an engine or Model
operation that already has focused tests.

For example, a CLI command exposing color analysis should test that the command
requests the correct analysis and presents the intended result. It should not
also reproduce the mathematical tests of the underlying color assignment
algorithm.

Prefer testing application behavior below Click parsing when the behavior is
not inherently a CLI concern.

Keep CLI orchestration thin enough that underlying capabilities remain usable
and testable independently.

## Refactoring

Refactoring changes implementation without intentionally changing observable
behavior.

Existing tests should normally provide the behavioral protection for a
refactoring.

Do not create tests merely because production code is being rearranged.

Add tests before refactoring only when an important existing behavior is not
adequately protected and that missing protection materially increases the risk
of the refactoring.

If a refactoring causes a test to fail, determine whether:

* observable behavior actually changed;
* the test depends on an implementation detail that is not contractual; or
* the test has revealed an architectural boundary that the refactoring
  violated.

Do not preserve an accidental implementation detail solely to keep an
overspecified test green.

# Evaluating Existing Tests

Existing tests are evidence of intended behavior, but they are not immune from
review.

When a legitimate architectural, Model, Feature, Variant, or configuration
change causes an existing test to fail, do not automatically treat production
code as incorrect.

Ask:

1. What behavior is this test intended to protect?
2. Is that behavior supported by a permanent specification?
3. Is the failing assertion material to that behavior?
4. Is the test freezing an incidental implementation detail?
5. Is the test enumerating a Model inventory that is intentionally extensible?
6. Is the test freezing a mutable repository default?
7. Has the underlying contract intentionally changed?

Rewrite or remove tests that protect behavior deliberately removed by a
specification change.

Relax tests that are unnecessarily broader than the behavior they are intended
to protect.

Do not weaken a test merely because its valid contractual assertion is
inconvenient for the new implementation.

## Curate Tests When They Are Encountered

Existing tests should gradually evolve with the testing practices in this
document, but broad test-suite cleanup is not required merely to bring older
tests into conformity with current conventions.

When development naturally causes an existing test to be examined or modified,
evaluate that test against the current testing policy.

Preserve assertions that protect intended behavior. Update, remove, or relax
assertions that instead protect:

* incidental implementation details;
* contracts that have intentionally been removed;
* complete Model, Feature, Variant, stage, or Product inventories when
  completeness is not contractual;
* unrelated Model composition or behavior;
* mutable repository configuration that is not itself under test; or
* compatibility behavior that the current specification no longer requires.

Do not add production compatibility behavior solely to keep an obsolete test
passing.

Do not expand the current change into unrelated test-suite cleanup. Tests that
are not relevant to the work at hand may remain for later evaluation.

A test encountered during a change should leave the suite at least as
behaviorally precise and no more accidentally restrictive than it was before.

# AI-Assisted Development

Tests have an additional role during AI-assisted development: they establish
the behavioral boundary within which production changes are authorized.

That makes test quality more important, not test quantity.

Before proposing tests, AI-assisted development should distinguish:

* explicit requirements;
* permanent specification;
* current implementation;
* existing tests;
* current repository configuration;
* assumptions; and
* possible future design.

Do not convert observations about HEAD into requirements without justification.

In particular:

* current Model Features do not imply a closed Feature set;
* current Products do not imply a closed Product set;
* current Variants do not imply a closed Variant set;
* current repository defaults are not automatically contractual;
* historical implementation names do not automatically define architectural
  terminology;
* the current implementation strategy is not automatically the required
  implementation strategy.

When a requested change exposes an unresolved design question, surface the
question rather than silently choosing an answer through a test or production
implementation.

Once the behavior is sufficiently defined, prefer providing a complete
coherent test slice rather than repeatedly asking for permission to add each
individual test.

After RED results are available, use the actual failures to guide production
changes rather than relying only on predictions made before the tests ran.

# Test Organization

Prefer placing tests according to the behavior they protect.

Reuse or extend existing test files when that produces clear organization.

Do not create a new test file merely to isolate every new invariant.

Create a new test file when it represents a meaningful new behavioral area,
Feature, Model, integration boundary, or acceptance capability.

Avoid large test files that accumulate unrelated behaviors merely because they
exercise the same high-level command or Model.

Test helpers should make the behavior under test clearer. They should not hide
important setup or create broad fixtures whose unrelated defaults become
implicit test dependencies.

# Completion

A TDD slice is complete when:

1. the intended behavior is sufficiently specified;
2. focused tests express that behavior;
3. the tests were observed RED for the intended reason when new behavior
   required production changes;
4. production implementation makes the focused tests pass;
5. unrelated tests remain green or any necessary test changes are understood
   and justified;
6. applicable formatting, static analysis, and broader test suites pass; and
7. permanent documentation is updated when architectural, Model, configuration,
   or public behavior changed.

The objective is not maximum test coverage or maximum test count.

The objective is a test suite that gives strong confidence in intended
behavior while allowing the architecture and Models to evolve without
unnecessary friction.

