"""Compatibility shim: re-export db.database symbols from the `db` package.

This file remains at the repository root for backward compatibility with
scripts that import `database`. New code should import from `db.database`.
"""

from db.database import engine, SessionLocal, get_db  # re-export

__all__ = ["engine", "SessionLocal", "get_db"]