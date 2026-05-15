"""GLEIF Golden Copy data loader and LEI relationship query library.

This package downloads the three GLEIF (Global Legal Entity Identifier
Foundation) golden copy datasets, loads them into a local DuckDB
database, and exposes typed query functions for traversing corporate
hierarchies, looking up entities by LEI, and searching by legal name.

The package powers a ``gleif`` command-line tool, but every operation
is also importable for programmatic use.

Datasets
--------
* **Level 1 - LEI Records** (``lei2``): one row per registered legal
  entity, with legal name, address, registration status, etc.
* **Level 2 - Relationships** (``rr``): parent/child consolidation
  relationships between LEIs.
* **Level 2 - Reporting Exceptions** (``repex``): documented reasons
  an entity did not report a parent relationship.

Installation
------------
.. code-block:: bash

    uv tool install gleif       # or: pip install gleif

The CLI is then available as ``gleif``::

    gleif refresh                   # download + load into DuckDB
    gleif lei 2138005YL12BKW2FQA89  # look up an LEI
    gleif name "Apple"              # substring legal-name search

Minimal programmatic usage
--------------------------
.. code-block:: python

    from gleif.constants import DEFAULT_DB_PATH
    from gleif.db import get_connection
    from gleif.queries import get_full_report

    con = get_connection(DEFAULT_DB_PATH)
    try:
        report = get_full_report(con, "2138005YL12BKW2FQA89")
        if report is not None:
            print(report.entity.legal_name)
            for child in report.children:
                print(" ", child.lei, child.legal_name)
    finally:
        con.close()

Public API
----------
The submodules below are the supported entry points; symbols imported
without a leading underscore are part of the public API.

* :mod:`gleif.constants` - dataset enums, URLs, default paths.
* :mod:`gleif.download` - async download of golden-copy archives.
* :mod:`gleif.db` - DuckDB schema creation and CSV bulk loading.
* :mod:`gleif.queries` - typed relationship-traversal queries.
* :mod:`gleif.isin` - ISIN lookups via the GLEIF REST API.
* :mod:`gleif.models` - frozen dataclasses for query results.
* :mod:`gleif.cli` - the Typer ``gleif`` CLI application.
"""
