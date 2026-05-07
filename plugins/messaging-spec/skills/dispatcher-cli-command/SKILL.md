---
name: dispatcher-cli-command
description: Dispatcher CLI Command pattern for messaging bootstrap. Use when exposing dispatchers as command-line entry points (e.g., for containerized deployments) so each dispatcher can be run as a separate process via a Click-based CLI.
user-invocable: false
disable-model-invocation: false
---

# Dispatcher CLI Command

Category: Bootstrap Pattern

# Dispatcher CLI Command

## Purpose

- Provide command-line interface to run dispatchers.
- Enable running dispatchers as separate processes.
- Support containerized deployments with distinct commands.

## Structure

- Uses Click library for CLI framework.
- CLI group as main entry point.
- Each dispatcher has its own command.
- Commands call runner functions from entrypoint module.

## Template Parameters

When using the template, replace these placeholders with your project-specific values:

- `{{ dispatcher_name }}` - Name identifier for this dispatcher (e.g., `document_ops`)
- `{{ command_name }}` - CLI command name (e.g., `dispatch_document_ops` or `dispatch-document-ops`)
- `{{ runner_function }}` - Runner function to call (e.g., `run_document_ops_dispatcher`)

## Example

```python
# __main__.py
import click

from my_project.entrypoint import (
    run_api,
    run_document_ops_dispatcher,
    run_profile_ops_dispatcher,
    run_subject_extraction_dispatcher,
)

@click.group()
def cli() -> None:
    pass

@click.command()
def serve() -> None:
    run_api()

@click.command()
def dispatch_document_ops() -> None:
    run_document_ops_dispatcher()

@click.command()
def dispatch_subject_extraction() -> None:
    run_subject_extraction_dispatcher()

@click.command()
def dispatch_profile_ops() -> None:
    run_profile_ops_dispatcher()

if __name__ == "__main__":
    cli.add_command(serve)
    cli.add_command(dispatch_document_ops)
    cli.add_command(dispatch_subject_extraction)
    cli.add_command(dispatch_profile_ops)
    cli()
```

## Usage

Run dispatchers from command line:

```bash
# Run API server
python -m my_project serve

# Run document ops dispatcher
python -m my_project dispatch_document_ops

# Run subject extraction dispatcher
python -m my_project dispatch_subject_extraction

# Run profile ops dispatcher
python -m my_project dispatch_profile_ops
```

## Docker/Kubernetes Usage

Each command can be a separate container entrypoint:

```docker
# API server
CMD ["python", "-m", "my_project", "serve"]

# Document ops dispatcher
CMD ["python", "-m", "my_project", "dispatch_document_ops"]
```

```yaml
# Kubernetes deployment
spec:
  containers:
    - name: document-ops-dispatcher
      command: ["python", "-m", "my_project", "dispatch_document_ops"]
```

## Naming Conventions

| Dispatcher | Command Name | Runner Function |
| --- | --- | --- |
| `document_ops` | `dispatch_document_ops` | `run_document_ops_dispatcher` |
| `subject_extraction` | `dispatch_subject_extraction` | `run_subject_extraction_dispatcher` |
| `profile_ops` | `dispatch_profile_ops` | `run_profile_ops_dispatcher` |

## Key Points

- **One command per dispatcher** — enables independent scaling.
- **Commands are thin** — just call runner functions.
- **Click group** — organizes all commands under single CLI.
- **Module execution** — `python -m package` pattern for clean invocation.

## Testing Guidance

- Test CLI commands invoke correct runner functions.
- Use Click's testing utilities (`CliRunner`).
- Mock runner functions to avoid starting actual processes.

---

## Template

```python
@click.command()
def {{ command_name }}() -> None:
    {{ runner_function }}()
```

## Placeholders

| Placeholder | Description | Example |
| --- | --- | --- |
| `{{ command_name }}` | CLI command name | `dispatch_document_ops`, `dispatch-document-ops` |
| `{{ runner_function }}` | Runner function to call | `run_document_ops_dispatcher` |
