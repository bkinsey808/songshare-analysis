"""songshare-analysis package.

Exports minimal public API and the package `__version__`.
"""

from importlib.metadata import version

# Default version fallback; if this package isn't installed as a distribution, we
# still want a usable `__version__` attribute during development.
try:
    __version__ = version("songshare-analysis")
except Exception:  # pragma: no cover - import-time fallback
    __version__ = "0.1.0"

__all__ = ["__version__"]
