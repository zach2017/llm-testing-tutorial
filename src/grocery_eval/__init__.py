"""Grocery-store reading-comprehension benchmark for small local LLMs served by Ollama.

Modules
-------
ollama_client  - dependency-free HTTP client for the Ollama API
mock_backend   - deterministic fake models so the pipeline can be tested without Ollama
scoring        - heuristic answer scoring and failure-mode taxonomy
stats          - confidence intervals, paired bootstrap, exact sign test
report         - aggregation and Markdown / CSV / JSON report writers
"""

__version__ = "1.0.0"
