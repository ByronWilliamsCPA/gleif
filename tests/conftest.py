"""Shared test fixtures for GLEIF tests."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from typing import TYPE_CHECKING

import duckdb
import pytest

from gleif.db import (
    create_schema,
    load_lei_records,
    load_relationships,
    load_reporting_exceptions,
)

if TYPE_CHECKING:
    from pathlib import Path


# ---------------------------------------------------------------------------
# CSV header definitions
# ---------------------------------------------------------------------------

_LEI_HEADERS = [
    "LEI",
    "Entity.LegalName",
    "Entity.LegalAddress.FirstAddressLine",
    "Entity.LegalAddress.AdditionalAddressLine.1",
    "Entity.LegalAddress.City",
    "Entity.LegalAddress.Region",
    "Entity.LegalAddress.Country",
    "Entity.LegalAddress.PostalCode",
    "Entity.HeadquartersAddress.FirstAddressLine",
    "Entity.HeadquartersAddress.AdditionalAddressLine.1",
    "Entity.HeadquartersAddress.City",
    "Entity.HeadquartersAddress.Region",
    "Entity.HeadquartersAddress.Country",
    "Entity.HeadquartersAddress.PostalCode",
    "Entity.RegistrationAuthority.RegistrationAuthorityID",
    "Entity.RegistrationAuthority.RegistrationAuthorityEntityID",
    "Entity.LegalJurisdiction",
    "Entity.EntityCategory",
    "Entity.EntitySubCategory",
    "Entity.LegalForm.EntityLegalFormCode",
    "Entity.LegalForm.OtherLegalForm",
    "Entity.EntityStatus",
    "Entity.EntityCreationDate",
    "Entity.AssociatedEntity.AssociatedLEI",
    "Entity.AssociatedEntity.type",
    "Registration.InitialRegistrationDate",
    "Registration.LastUpdateDate",
    "Registration.RegistrationStatus",
    "Registration.NextRenewalDate",
    "Registration.ManagingLOU",
    "Registration.ValidationSources",
    "ConformityFlag",
]

_RR_HEADERS = [
    "Relationship.StartNode.NodeID",
    "Relationship.StartNode.NodeIDType",
    "Relationship.EndNode.NodeID",
    "Relationship.EndNode.NodeIDType",
    "Relationship.RelationshipType",
    "Relationship.RelationshipStatus",
    "Relationship.Period.1.startDate",
    "Relationship.Period.1.endDate",
    "Relationship.Period.1.periodType",
    "Relationship.Qualifiers.1.QualifierDimension",
    "Relationship.Qualifiers.1.QualifierCategory",
    "Relationship.Quantifiers.1.MeasurementMethod",
    "Relationship.Quantifiers.1.QuantifierAmount",
    "Relationship.Quantifiers.1.QuantifierUnits",
    "Registration.InitialRegistrationDate",
    "Registration.LastUpdateDate",
    "Registration.RegistrationStatus",
    "Registration.NextRenewalDate",
    "Registration.ManagingLOU",
    "Registration.ValidationSources",
    "Registration.ValidationDocuments",
    "Registration.ValidationReference",
]


# ---------------------------------------------------------------------------
# Row builders
# ---------------------------------------------------------------------------


Address = tuple[str, str, str, str, str]
"""Postal address as ``(line1, city, region, country, postcode)``."""


@dataclass(frozen=True)
class _LeiSpec:
    """Distinguishing fields for a single LEI fixture row.

    Everything else (HQ address mirroring legal address, ACTIVE /
    ISSUED / CONFORMING status fields, fixed validation source) is
    pinned by :func:`_lei_row`.
    """

    lei: str
    legal_name: str
    address: Address
    ra_id: str
    ent_id: str
    jurisdiction: str
    legal_form: str
    creation_date: str
    initial_reg_date: str
    lou: str


def _lei_row(spec: _LeiSpec) -> list[str]:
    """Build a Level 1 LEI CSV row from a :class:`_LeiSpec`."""
    line1, city, region, country, postcode = spec.address
    return [
        spec.lei,
        spec.legal_name,
        line1,
        "",
        city,
        region,
        country,
        postcode,
        line1,
        "",
        city,
        region,
        country,
        postcode,
        spec.ra_id,
        spec.ent_id,
        spec.jurisdiction,
        "GENERAL",
        "",
        spec.legal_form,
        "",
        "ACTIVE",
        spec.creation_date,
        "",
        "",
        spec.initial_reg_date,
        "2024-01-01",
        "ISSUED",
        "2025-12-31",
        spec.lou,
        "FULLY_CORROBORATED",
        "CONFORMING",
    ]


def _rr_row(
    *,
    child_lei: str,
    parent_lei: str,
    relationship_type: str,
    start_date: str,
    initial_reg_date: str,
    lou: str,
) -> list[str]:
    """Build a Level 2 Relationship Record CSV row.

    All rows are ACTIVE, PUBLISHED, accounting-period-typed, and
    validated against ACCOUNTS_FILING.
    """
    return [
        child_lei,
        "LEI",
        parent_lei,
        "LEI",
        relationship_type,
        "ACTIVE",
        start_date,
        "",
        "ACCOUNTING_PERIOD",
        "",
        "",
        "",
        "",
        "",
        initial_reg_date,
        "2024-01-01",
        "PUBLISHED",
        "2025-12-31",
        lou,
        "FULLY_CORROBORATED",
        "ACCOUNTS_FILING",
        "",
    ]


def _write_csv(csv_path: Path, headers: list[str], rows: list[list[str]]) -> None:
    """Write a header row followed by data rows to ``csv_path``."""
    with csv_path.open("w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(headers)
        writer.writerows(rows)


# ---------------------------------------------------------------------------
# DB extension helpers
# ---------------------------------------------------------------------------


def insert_lei(
    con: duckdb.DuckDBPyConnection,
    *,
    lei: str,
    legal_name: str,
    jurisdiction: str,
) -> None:
    """Append a minimal lei_records row for hierarchy-extension fixtures."""
    con.execute(
        "INSERT INTO lei_records "
        "(lei, legal_name, entity_status, registration_status, "
        "entity_category, legal_jurisdiction) VALUES "
        "($1, $2, 'ACTIVE', 'ISSUED', 'GENERAL', $3)",
        [lei, legal_name, jurisdiction],
    )


def insert_relationship(
    con: duckdb.DuckDBPyConnection,
    *,
    child_lei: str,
    parent_lei: str,
    relationship_type: str,
) -> None:
    """Append an ACTIVE relationship row for hierarchy-extension fixtures."""
    con.execute(
        "INSERT INTO relationships "
        "(start_node_id, start_node_id_type, end_node_id, "
        "end_node_id_type, relationship_type, relationship_status) "
        "VALUES ($1, 'LEI', $2, 'LEI', $3, 'ACTIVE')",
        [child_lei, parent_lei, relationship_type],
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_data_dir(tmp_path: Path) -> Path:
    """Provide a temporary data directory."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    return data_dir


@pytest.fixture
def lei_csv(tmp_data_dir: Path) -> Path:
    """Create a small Level 1 LEI CSV fixture file."""
    csv_path = tmp_data_dir / "lei_records.csv"
    rows = [
        _lei_row(
            _LeiSpec(
                lei="PARENT00000000000001",
                legal_name="Parent Corp",
                address=("123 Main St", "New York", "US-NY", "US", "10001"),
                ra_id="RA000001",
                ent_id="ENT001",
                jurisdiction="US",
                legal_form="8888",
                creation_date="2000-01-01",
                initial_reg_date="2010-01-01",
                lou="LOU000000000000001",
            ),
        ),
        _lei_row(
            _LeiSpec(
                lei="CHILD000000000000001",
                legal_name="Child A Inc.",
                address=("456 Oak Ave", "Chicago", "US-IL", "US", "60601"),
                ra_id="RA000001",
                ent_id="ENT002",
                jurisdiction="US",
                legal_form="8888",
                creation_date="2005-06-15",
                initial_reg_date="2012-03-01",
                lou="LOU000000000000001",
            ),
        ),
        _lei_row(
            _LeiSpec(
                lei="CHILD000000000000002",
                legal_name="Child B Ltd.",
                address=("789 Pine Rd", "London", "GB-LND", "GB", "EC1A 1BB"),
                ra_id="RA000002",
                ent_id="ENT003",
                jurisdiction="GB",
                legal_form="9999",
                creation_date="2008-03-20",
                initial_reg_date="2013-05-01",
                lou="LOU000000000000002",
            ),
        ),
        _lei_row(
            _LeiSpec(
                lei="ULTIMATE000000000001",
                legal_name="Ultimate Holdings PLC",
                address=("1 Tower Bridge", "London", "GB-LND", "GB", "SE1 2UP"),
                ra_id="RA000002",
                ent_id="ENT004",
                jurisdiction="GB",
                legal_form="9999",
                creation_date="1995-01-01",
                initial_reg_date="2010-01-01",
                lou="LOU000000000000002",
            ),
        ),
    ]
    _write_csv(csv_path, _LEI_HEADERS, rows)
    return csv_path


@pytest.fixture
def rr_csv(tmp_data_dir: Path) -> Path:
    """Create a small Level 2 Relationship Record CSV fixture."""
    csv_path = tmp_data_dir / "relationships.csv"
    rows = [
        # Child A -> Parent (direct)
        _rr_row(
            child_lei="CHILD000000000000001",
            parent_lei="PARENT00000000000001",
            relationship_type="IS_DIRECTLY_CONSOLIDATED_BY",
            start_date="2010-01-01",
            initial_reg_date="2012-03-01",
            lou="LOU000000000000001",
        ),
        # Child B -> Parent (direct)
        _rr_row(
            child_lei="CHILD000000000000002",
            parent_lei="PARENT00000000000001",
            relationship_type="IS_DIRECTLY_CONSOLIDATED_BY",
            start_date="2010-01-01",
            initial_reg_date="2013-05-01",
            lou="LOU000000000000002",
        ),
        # Child A -> Ultimate (ultimate)
        _rr_row(
            child_lei="CHILD000000000000001",
            parent_lei="ULTIMATE000000000001",
            relationship_type="IS_ULTIMATELY_CONSOLIDATED_BY",
            start_date="2010-01-01",
            initial_reg_date="2012-03-01",
            lou="LOU000000000000001",
        ),
        # Parent -> Ultimate (direct)
        _rr_row(
            child_lei="PARENT00000000000001",
            parent_lei="ULTIMATE000000000001",
            relationship_type="IS_DIRECTLY_CONSOLIDATED_BY",
            start_date="2005-01-01",
            initial_reg_date="2010-01-01",
            lou="LOU000000000000001",
        ),
    ]
    _write_csv(csv_path, _RR_HEADERS, rows)
    return csv_path


@pytest.fixture
def repex_csv(tmp_data_dir: Path) -> Path:
    """Create a small Level 2 Reporting Exceptions CSV fixture."""
    csv_path = tmp_data_dir / "reporting_exceptions.csv"
    headers = [
        "LEI",
        "Exception.Category",
        "Exception.Reason.1",
        "Exception.Reference.1",
    ]
    rows = [
        [
            "ULTIMATE000000000001",
            "ULTIMATE_ACCOUNTING_CONSOLIDATION_PARENT",
            "NO_KNOWN_PERSON",
            "",
        ],
    ]
    _write_csv(csv_path, headers, rows)
    return csv_path


@pytest.fixture
def loaded_db(
    lei_csv: Path,
    rr_csv: Path,
    repex_csv: Path,
) -> duckdb.DuckDBPyConnection:
    """Create an in-memory DuckDB with all three datasets loaded."""
    con = duckdb.connect(":memory:")
    create_schema(con)
    load_lei_records(con, lei_csv)
    load_relationships(con, rr_csv)
    load_reporting_exceptions(con, repex_csv)
    return con


@pytest.fixture
def deep_hierarchy_db(
    loaded_db: duckdb.DuckDBPyConnection,
) -> duckdb.DuckDBPyConnection:
    """Extend loaded_db with a grandchild for 4-level hierarchy testing.

    Hierarchy: Ultimate -> Parent -> [Child A -> Grandchild, Child B].
    """
    insert_lei(
        loaded_db,
        lei="GRANDCHILD0000000001",
        legal_name="Grandchild GmbH",
        jurisdiction="DE",
    )
    insert_relationship(
        loaded_db,
        child_lei="GRANDCHILD0000000001",
        parent_lei="CHILD000000000000001",
        relationship_type="IS_DIRECTLY_CONSOLIDATED_BY",
    )
    insert_relationship(
        loaded_db,
        child_lei="GRANDCHILD0000000001",
        parent_lei="ULTIMATE000000000001",
        relationship_type="IS_ULTIMATELY_CONSOLIDATED_BY",
    )
    return loaded_db


@pytest.fixture
def diamond_db(
    deep_hierarchy_db: duckdb.DuckDBPyConnection,
) -> duckdb.DuckDBPyConnection:
    """Extend deep_hierarchy_db with a diamond structure.

    Shared Subsidiary is a child of both Child A and Child B.
    """
    insert_lei(
        deep_hierarchy_db,
        lei="SHARED00000000000001",
        legal_name="Shared Subsidiary SA",
        jurisdiction="CH",
    )
    insert_relationship(
        deep_hierarchy_db,
        child_lei="SHARED00000000000001",
        parent_lei="CHILD000000000000001",
        relationship_type="IS_DIRECTLY_CONSOLIDATED_BY",
    )
    insert_relationship(
        deep_hierarchy_db,
        child_lei="SHARED00000000000001",
        parent_lei="CHILD000000000000002",
        relationship_type="IS_DIRECTLY_CONSOLIDATED_BY",
    )
    return deep_hierarchy_db
