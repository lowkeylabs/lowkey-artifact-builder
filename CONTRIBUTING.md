# Contributing

Contributions to lowkey-artifact-builder are welcome.

lowkey-artifact-builder is an open-source project developed by
lowkeylabs and distributed under the Apache License, Version 2.0.

## Development

The project is under active development. Development setup,
testing, formatting, and other project conventions are documented
in the repository README and `pyproject.toml`.

`ARCHITECTURE.md` defines the system architecture, and each model's
`DEFINITION.md` defines the behavior owned by that model. Changes should
preserve these specifications or update them explicitly when intended
behavior changes.

Before submitting a change:

1. Create a branch for the change.
2. Add or update tests as appropriate.
3. Run the project's test suite.
4. Keep changes focused on a single purpose.
5. Update documentation when behavior or public interfaces change.

## Models

Artifact models are intended to be independently extensible packages
that implement the model interfaces defined by lowkey-artifact-builder.

New models should:

* use the model registry rather than modifying the generic pipeline
  for model-specific behavior;
* declare their supported features;
* declare their build stages and dependencies;
* declare the products produced by each stage; and
* include appropriate tests for model registration, planning, and
  model-specific behavior.

Model-specific behavior should remain within the model package whenever
practical. Adding a conforming model should not require adding
model-specific behavior to the generic engine.

## Tests

New functionality and bug fixes should include appropriate automated
tests.

The project uses test-driven development. Tests should protect meaningful
behavior without unnecessarily freezing incidental implementation details,
the complete current feature set of a model, or mutable repository
configuration.

Development should proceed in coherent behavioral slices. A slice may
contain several closely related tests and production changes when they
collectively establish one capability; test-driven development does not
require one test or one assertion per development cycle.

When testing generic infrastructure, prefer small synthetic models when
real model behavior is not relevant. Model tests should concentrate on
the semantics under test and remain tolerant of unrelated model
extensions.

Exact configuration defaults should be asserted when the value itself is
part of the behavior being protected, not merely because it is the
current repository default.

Detailed testing and TDD practices are documented in
`prompts/TEST_DRIVEN_DEVELOPMENT.md`.

Tests should not require external modeling tools such as OpenSCAD or
Inkscape unless the test is specifically an integration test for that
tool.

The generic model registry, build planner, dependency graph, and
pipeline runner should be testable without external modeling software.

## Issues

Bug reports and feature requests may be submitted through GitHub Issues.

When reporting a bug, please include enough information to reproduce
the problem, including relevant commands, configuration, and error
output.

## Pull Requests

Pull requests should describe:

* what is being changed;
* why the change is needed;
* how the change was tested; and
* any compatibility or configuration implications.

Large architectural changes should generally be discussed before a
substantial implementation is submitted.

## Licensing

By submitting a contribution to this project, you agree that your
contribution may be distributed under the Apache License, Version 2.0.

Contributors retain copyright in their contributions unless otherwise
agreed in writing.

See `LICENSE`, `NOTICE`, and `COPYRIGHT` for additional information.
