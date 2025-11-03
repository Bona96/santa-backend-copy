"""Compatibility shim: re-export db.mongo_client symbols from the `db` package.

This file remains at the repository root for backward compatibility with
scripts that import `mongo_client`. New code should import from `db.mongo_client`.
"""

from db.mongo_client import *  # re-export

__all__ = ["get_mongo_client", "get_mongo_db"]
