# CHANGEPLAN

## Purpose

Continue refining `lowkey-artifact-builder` around the manufacturing value
chain established by the current repository HEAD.
The operator's ordinary goal is:

> Move customer artwork to a *correct, printable 3MF* with the fewest
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

5. resolve known semantic or architectural questions before encoding behavior

   in tests, while allowing test-first exploration to discover or clarify
   uncertain seams and ownership boundaries;

6. organize TDD around major behavioral seams or boundaries, using one test or

   a small coherent test set to drive a substantial implementation slice rather
   than creating single-test/single-change cycles;

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

## TDD cycles

TDD remains test-first. Before implementing a meaningful new behavior, write a
test that exercises the behavioral seam or boundary being established.

The purpose of the initial failing test is not only verification. A test may
also be used to discover or clarify the appropriate seam, ownership boundary,
or contract before implementation. If the test exposes a better boundary than
the one initially assumed, refine the design and test before committing to the
implementation.

TDD cycles should normally correspond to substantial behavioral seams or
boundaries rather than individual implementation changes. Once a failing test
establishes the intended seam, implement the coherent behavior necessary to
make that seam work. Do not begin a new RED/GREEN cycle merely because that
implementation requires another helper, parameter, branch, component, or
internal refactoring.

One test may be sufficient to establish a seam. A small coherent group of tests
is appropriate when materially different cases are necessary to define the
same boundary. Prefer these high-value behavioral tests over many narrow tests
that separately inventory implementation details.

Add narrower tests when they help discover an uncertain boundary, protect an
independently meaningful contract, reproduce a defect, or address a specific
algorithmic or regression risk.


---------------------------

add phases and slices here
