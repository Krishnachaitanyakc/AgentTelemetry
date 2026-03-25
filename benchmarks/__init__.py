"""AgentTelemetry benchmark suite.

Provides mock clients, fault injection, reference applications,
and a benchmark runner for evaluating telemetry effectiveness.

Package layout::

    benchmarks/
        mocks/          - Mock Anthropic and OpenAI clients
        faults/         - Fault injection framework
        apps/           - Reference agent applications
        run_benchmarks.py  - Main benchmark runner
"""
