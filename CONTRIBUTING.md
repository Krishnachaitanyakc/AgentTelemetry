# Contributing to AgentTelemetry

Thank you for your interest in contributing to AgentTelemetry. This document
provides guidelines to make the contribution process straightforward.

## Getting Started

1. **Fork the repository** and clone your fork locally.
2. **Create a feature branch** from `master`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Install development dependencies**:
   ```bash
   pip install -e ".[dev]"
   ```
4. **Make your changes**, ensuring they follow the guidelines below.
5. **Run the test suite** to verify nothing is broken:
   ```bash
   pytest tests/ -v
   ```
6. **Submit a pull request** against the `master` branch with a clear
   description of your changes.

## Code Style

- Follow the existing code patterns and conventions in the repository.
- Add type hints to function signatures.
- Include docstrings for all public classes, methods, and functions.
- Keep functions focused and concise.

## Testing

- Add tests for any new functionality.
- Place tests in the appropriate subdirectory under `tests/`
  (`test_core/`, `test_exporters/`, `test_instrumentors/`).
- Ensure all existing tests continue to pass before submitting your PR.

## Reporting Issues

When opening an issue, please include:

- A clear and descriptive title.
- Steps to reproduce the problem.
- Expected behavior vs. actual behavior.
- Python version, OS, and any relevant dependency versions.
- Minimal code to reproduce the issue, if applicable.

## Pull Request Guidelines

- Keep PRs focused on a single change or feature.
- Reference any related issues in the PR description (e.g., "Closes #42").
- Ensure the test suite passes.
- Update documentation if your change affects public APIs.

## License

By contributing to AgentTelemetry, you agree that your contributions will be
licensed under the Apache License 2.0.
