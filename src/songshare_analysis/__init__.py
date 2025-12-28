"""songshare-analysis package.

Exports minimal public API and the package `__version__`.
"""

from importlib.metadata import version

# Default version fallback; if this package isn't installed as a distribution, we
# still want a usable `__version__` attribute during development.
try:
    __version__ = version("songshare-analysis")
except Exception:  # pragma: no cover - import-time fallback
    # Fallback for development when package is not installed
    __version__ = "0.1.0"

from .essentia import rhythm

__all__ = ["__version__", "rhythm"]
