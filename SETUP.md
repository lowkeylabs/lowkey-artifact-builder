# Development Setup

## TL;DR

For a new checkout:

```bash
git clone https://github.com/lowkeylabs/lowkey-artifact-builder.git
cd lowkey-artifact-builder

uv sync
source .venv/bin/activate
pre-commit install

make check
```

Verify the CLI:

```bash
artifact --help
```

For an existing development environment:

```bash
git pull
uv sync
make check
```

The normal development cycle is:

```bash
make format
make check
```

If you use `direnv`, configure it once as described below and the project's
virtual environment will be activated automatically whenever you enter the
repository.

The remainder of this document explains the setup in detail.


## Requirements

`lowkey-artifact-builder` uses:

- Python 3.14 or later
- [uv](https://docs.astral.sh/uv/) for Python environment and dependency management
- pytest for testing
- Ruff for linting and formatting
- Pyright for static type checking
- pre-commit for automated repository checks

Git is also required for normal development.


## Clone the Repository

Clone the repository and enter the project directory:

```bash
git clone https://github.com/lowkeylabs/lowkey-artifact-builder.git
cd lowkey-artifact-builder
```


## Install uv

If `uv` is not already installed, follow the installation instructions at:

https://docs.astral.sh/uv/getting-started/installation/

Verify the installation:

```bash
uv --version
```


## Create the Development Environment

Synchronize the project environment:

```bash
uv sync
```

This creates the project's `.venv` virtual environment, installs
`lowkey-artifact-builder`, and installs the development dependency group
defined in `pyproject.toml`.

There is no need to separately install the project in editable mode.
`uv sync` installs the local project appropriately for development.

Do not use:

```bash
uv add --editable .
```

`uv add` adds a dependency to the project. Since `.` is the project itself,
that would attempt to create a self-dependency.


## Activate the Virtual Environment

The virtual environment can be activated manually:

```bash
source .venv/bin/activate
```

After activation, the project CLI and development tools can be invoked
directly:

```bash
artifact --help
pytest
ruff check .
pyright
```

The same commands can be run without activating the environment by using
`uv run`:

```bash
uv run artifact --help
uv run pytest
uv run ruff check .
uv run pyright
```


## Optional: Automatic Activation with direnv

[`direnv`](https://direnv.net/) can automatically activate the project's
virtual environment when entering the repository and restore the previous
environment when leaving it.

`direnv` is optional and is not required to build or develop
`lowkey-artifact-builder`.


### Install direnv

On Ubuntu:

```bash
sudo apt install direnv
```


### Configure zsh

Add the following to `~/.zshrc`:

```bash
eval "$(direnv hook zsh)"
```

Reload the shell configuration:

```bash
source ~/.zshrc
```


### Configure the Project

Create `.envrc` in the repository root containing:

```bash
source .venv/bin/activate
```

Authorize the file:

```bash
direnv allow
```

Afterward, entering the project directory automatically activates the
virtual environment:

```bash
cd ~/projects/lowkey-artifact-builder
```

Leaving the project directory restores the previous environment.


## Install Pre-commit Hooks

Install the repository's pre-commit hooks:

```bash
pre-commit install
```

The configured checks will then run automatically when committing changes.

Run all pre-commit checks manually with:

```bash
pre-commit run --all-files
```


## Verify the Development Environment

Run the complete project check:

```bash
make check
```

Individual checks can also be run separately:

```bash
make test
make lint
make typecheck
```

Formatting can be applied with:

```bash
make format
```

A typical development cycle is therefore:

```bash
make format
make check
```


## Run the CLI

With the virtual environment active:

```bash
artifact --help
```

Or without activating it:

```bash
uv run artifact --help
```

As commands are added to the project, they will be available beneath the
`artifact` command.

The planned command structure includes commands such as:

```bash
artifact models
artifact config
artifact plan <artifact_id>
artifact build <artifact_id>
artifact status <artifact_id>
artifact clean <artifact_id>
```

Not all commands shown above may be implemented during early development.


## Updating Dependencies

After changes to `pyproject.toml`, synchronize the environment:

```bash
uv sync
```

The generated `uv.lock` file should be committed to the repository so that
development and testing environments can be reproduced consistently.


## Generated Artifacts

`lowkey-artifact-builder` stores all generated build products beneath:

```text
artifacts/
```

The final build product for an artifact is:

```text
artifacts/<artifact_id>.3mf
```

Intermediate and reviewable build products are stored beneath:

```text
artifacts/<artifact_id>/
```

For example:

```text
artifacts/
├── 2121_stuart.3mf
│
└── 2121_stuart/
    ├── holder/
    │   ├── model.scad
    │   └── model.stl
    │
    ├── labels/
    │   ├── source.svg
    │   ├── paths.svg
    │   └── model.stl
    │
    └── artwork/
        └── ...
```

The artifact directory structure identifies the artifact and build stage,
allowing intermediate files within a stage to use consistent names such as:

```text
model.scad
model.stl
source.svg
paths.svg
mask.png
```

Generated products under `artifacts/` should not be committed to the
repository.


## Documentation

Repository-level development and contributor documentation is maintained
in files at the repository root, including:

```text
README.md
SETUP.md
CONTRIBUTING.md
```

Source material for the project website and GitHub Pages documentation is
maintained under:

```text
site-src/
```

The generated GitHub Pages site is written to:

```text
docs/
```

Files under `docs/` should therefore be treated as generated site output
rather than the authoritative source for project documentation.

Both `site-src/` and `docs/` may be tracked by Git as appropriate for the
project's GitHub Pages publishing workflow.


## Clean Development Files

Python development, testing, and packaging products can be removed with:

```bash
make clean
```

The development `clean` target should not remove application-generated
artifact products.

Generated artifact state is intentionally separate from Python development
state and is managed by the artifact builder itself.

The artifact filesystem follows this convention:

```text
artifacts/<artifact_id>/     intermediate and reviewable products
artifacts/<artifact_id>.3mf  final ready-to-slice product
```
