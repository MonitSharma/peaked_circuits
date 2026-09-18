"""P1-specific, answer-blind BlueQubit attack tooling."""

# Keep optional profiling dependencies from preventing import of independent
# TNO tooling.  The profiling function remains available whenever its
# structural parser is installed.
try:
    from .profile import profile_circuit
except ModuleNotFoundError as exc:
    if exc.name != "structural":
        raise
    profile_circuit = None

__all__ = ["profile_circuit"]
