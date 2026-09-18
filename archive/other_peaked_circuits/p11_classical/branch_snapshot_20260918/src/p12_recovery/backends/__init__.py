"""Backend adapters; importing this package never authenticates or submits work."""

from .base import CompilationBackend

__all__ = ["CompilationBackend"]
