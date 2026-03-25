# Contributing to AgentTelemetry

Thank you for your interest in contributing to AgentTelemetry.

## Development Setup

```bash
# Clone the repository
git clone https://github.com/agenttelemetry/agenttelemetry.git
cd agenttelemetry

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Run the test suite
pytest tests/unit/ tests/benchmarks/ -v
```

Integration tests require the corresponding framework packages:

```bash
# Run integration tests for a specific adapter
pip install -e ".[langchain]"
pytest tests/integration/test_langchain.py -v
```

## Code Structure

```
src/agenttelemetry/
  __init__.py              # Public API re-exports
  core/
    spans.py               # AgentSpanKind, semantic attribute keys, start_agent_span
    privacy.py             # PrivacyLevel enum, filter_attributes
    context.py             # AgentContextPropagator (W3C Trace Context)
    tracer.py              # AgentTelemetryProvider, configure()
    exporters.py           # Console and JSON file exporters
  adapters/
    __init__.py            # Re-exports all adapter classes
    anthropic_sdk.py       # Anthropic SDK instrumentation
    openai_sdk.py          # OpenAI SDK instrumentation
    langchain.py           # LangChain callback handler
    crewai.py              # CrewAI hook-based instrumentation
    autogen.py             # AutoGen monkey-patching
    llamaindex.py          # LlamaIndex span handler
    custom.py              # Manual instrumentation helpers
  analysis/
    anomaly_detection.py   # AnomalyDetector
    cost_aggregation.py    # CostAggregator
    decision_attribution.py # DecisionAttributor
    hallucination_tracing.py # HallucinationTracer
tests/
  unit/                    # Unit tests (no external deps required)
  integration/             # Integration tests (require framework packages)
  benchmarks/              # Performance overhead benchmarks
```

## How to Add a New Adapter

1. Create `src/agenttelemetry/adapters/your_framework.py`.
2. Subclass `opentelemetry.instrumentation.instrumentor.BaseInstrumentor`.
3. Implement `instrumentation_dependencies()`, `_instrument(**kwargs)`, and `_uninstrument(**kwargs)`.
4. In `_instrument`, accept `tracer_provider` and `privacy_level` from kwargs.
5. Use `start_agent_span` or the OTel tracer directly to create spans with `AGENT_SPAN_KIND` set.
6. Use `filter_attributes()` and `should_capture_content()` to respect privacy settings.
7. Add the class to `src/agenttelemetry/adapters/__init__.py`.
8. Add integration tests in `tests/integration/test_your_framework.py`.
9. Add an optional dependency group in `pyproject.toml`.

## How to Add a New Span Kind

1. Add the constant to `AgentSpanKind` in `src/agenttelemetry/core/spans.py` and include it in `_ALL`.
2. Define any associated semantic attribute keys in the same file.
3. If the attribute contains content (prompts, completions, tool I/O), add it to `_CONTENT_ATTRS` in `privacy.py`.
4. Optionally add a typed helper in `src/agenttelemetry/adapters/custom.py`.
5. Add unit tests in `tests/unit/test_spans.py`.

## Testing Guidelines

- All new code must have unit tests. Run `pytest tests/unit/ -v` before submitting.
- Integration tests should use mocks or lightweight fixtures -- do not require live API keys.
- Benchmark tests in `tests/benchmarks/` measure instrumentation overhead.
- Use `pytest-mock` for patching and `pytest-asyncio` for async tests.
- The CI matrix runs Python 3.9 through 3.12.

## Pull Request Guidelines

- Keep PRs focused on a single change or feature.
- Reference any related issues in the PR description.
- Ensure the test suite passes.
- Update documentation if your change affects public APIs.

## License

By contributing to AgentTelemetry, you agree that your contributions will be
licensed under the Apache License 2.0.
