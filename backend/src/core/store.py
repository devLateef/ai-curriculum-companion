"""Shared LanceDB connection helpers.

Used by both corpus.py (build) and vector.py (query) so the two agree on where the
database lives and how to test for the table.
"""

import lancedb

from . import config


def connect():
    return lancedb.connect(config.DB_PATH)


def table_names(db) -> list[str]:
    """Return table names as a plain list.

    LanceDB 0.37 returns a ListTablesResponse object from list_tables(), while the
    deprecated table_names() returns a list. Membership tests against the response
    object fail silently rather than raising, so normalize here.
    """
    result = db.list_tables()
    return list(getattr(result, "tables", result))
