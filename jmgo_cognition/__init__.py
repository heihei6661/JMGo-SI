"""JMGo MetaCognition — open framework.

The reasoning core (``jmgo_core``) is a separately distributed proprietary
binary. This package only contains the framework, the stable API contract and
open adapters. Without the core it runs :class:`NullCore`, which keeps the
loop observable but returns ``core_missing``.
"""
from .api import Core, CoreUnavailable, NullCore, load_core
from .loop import run_loop


def run_task(*args, **kwargs):
    """Lazy import so the package stays light and ``-m`` has no import warnings."""
    from .embodied import run_task as _run_task
    return _run_task(*args, **kwargs)

__version__ = "0.1.0"

__all__ = [
    "Core",
    "CoreUnavailable",
    "NullCore",
    "load_core",
    "run_loop",
    "run_task",
    "__version__",
]
