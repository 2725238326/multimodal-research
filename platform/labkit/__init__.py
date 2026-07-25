"""labkit — research experiment registry + visualization for multimodal-research.

The package name is ``labkit`` (NOT ``platform``): the enclosing ``platform/``
directory is deliberately not a Python package, so it never shadows the stdlib
``platform`` module. Put ``platform/`` on sys.path and ``import labkit``.

Core modules (schema, store, cli) depend only on the Python standard library so
that agents and training scripts can log runs without installing anything. The
optional visualization layer (server.py) needs FastAPI/uvicorn; the analysis
module (analyses/) uses numpy, which is already a project dependency.
"""

from __future__ import annotations

__version__ = "0.1.0"
