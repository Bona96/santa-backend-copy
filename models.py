"""Compatibility shim: re-export db.models symbols from the `db` package.

This file remains at the repository root for backward compatibility with
scripts that import `models`. New code should import from `db.models`.
"""

from db.models import *  # re-export for compatibility

__all__ = [
    name for name in dir() if not name.startswith("_")
]
