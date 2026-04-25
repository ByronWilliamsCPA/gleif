"""Shared test fixtures for GLEIF tests."""

from __future__ import annotations

import csv
from pathlib import Path

import duckdb
import pytest

from gleif.db import (
    create_schema,
    load_lei_records,
    load_relationships,
    load_reporting_exceptions,
)


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
    headers = [
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
    rows = [
        [
            "PARENT00000000000001",
            "Parent Corp",
            "123 Main St",
            "",
            "New York",
            "US-NY",
            "US",
            "10001",
            "123 Main St",
            "",
            "New York",
            "US-NY",
            "US",
            "10001",
            "RA000001",
            "ENT001",
            "US",
            "GENERAL",
            "",
            "8888",
            "",
            "ACTIVE",
            "2000-01-01",
            "",
            "",
            "2010-01-01",
            "2024-01-01",
            "ISSUED",
            "2025-12-31",
            "LOU000000000000001",
            "FULLY_CORROBORATED",
            "CONFORMING",
        ],
        [
            "CHILD000000000000001",
            "Child A Inc.",
            "456 Oak Ave",
            "",
            "Chicago",
            "US-IL",
            "US",
            "60601",
            "456 Oak Ave",
            "",
            "Chicago",
            "US-IL",
            "US",
            "60601",
            "RA000001",
            "ENT002",
            "US",
            "GENERAL",
            "",
            "8888",
            "",
            "ACTIVE",
            "2005-06-15",
            "",
            "",
            "2012-03-01",
            "2024-01-01",
            "ISSUED",
            "2025-12-31",
            "LOU000000000000001",
            "FULLY_CORROBORATED",
            "CONFORMING",
        ],
        [
            "CHILD000000000000002",
            "Child B Ltd.",
            "789 Pine Rd",
            "",
            "London",
            "GB-LND",
            "GB",
            "EC1A 1BB",
            "789 Pine Rd",
            "",
            "London",
            "GB-LND",
            "GB",
            "EC1A 1BB",
            "RA000002",
            "ENT003",
            "GB",
            "GENERAL",
            "",
            "9999",
            "",
            "ACTIVE",
            "2008-03-20",
            "",
            "",
            "2013-05-01",
            "2024-01-01",
            "ISSUED",
            "2025-12-31",
            "LOU000000000000002",
            "FULLY_CORROBORATED",
            "CONFORMING",
        ],
        [
            "ULTIMATE000000000001",
            "Ultimate Holdings PLC",
            "1 Tower Bridge",
            "",
            "London",
            "GB-LND",
            "GB",
            "SE1 2UP",
            "1 Tower Bridge",
            "",
            "London",
            "GB-LND",
            "GB",
            "SE1 2UP",
            "RA000002",
            "ENT004",
            "GB",
            "GENERAL",
            "",
            "9999",
            "",
            "ACTIVE",
            "1995-01-01",
            "",
            "",
            "2010-01-01",
            "2024-01-01",
            "ISSUED",
            "2025-12-31",
            "LOU000000000000002",
            "FULLY_CORROBORATED",
            "CONFORMING",
        ],
    ]
    with csv_path.open("w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(headers)
        writer.writerows(rows)
    return csv_path


@pytest.fixture
def rr_csv(tmp_data_dir: Path) -> Path:
    """Create a small Level 2 Relationship Record CSV fixture."""
    csv_path = tmp_data_dir / "relationships.csv"
    headers = [
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
    rows = [
        # Child A -> Parent (direct)
        [
            "CHILD000000000000001",
            "LEI",
            "PARENT00000000000001",
            "LEI",
            "IS_DIRECTLY_CONSOLIDATED_BY",
            "ACTIVE",
            "2010-01-01",
            "",
            "ACCOUNTING_PERIOD",
            "",
            "",
            "",
            "",
            "",
            "2012-03-01",
            "2024-01-01",
            "PUBLISHED",
            "2025-12-31",
            "LOU000000000000001",
            "FULLY_CORROBORATED",
            "ACCOUNTS_FILING",
            "",
        ],
        # Child B -> Parent (direct)
        [
            "CHILD000000000000002",
            "LEI",
            "PARENT00000000000001",
            "LEI",
            "IS_DIRECTLY_CONSOLIDATED_BY",
            "ACTIVE",
            "2010-01-01",
            "",
            "ACCOUNTING_PERIOD",
            "",
            "",
            "",
            "",
            "",
            "2013-05-01",
            "2024-01-01",
            "PUBLISHED",
            "2025-12-31",
            "LOU000000000000002",
            "FULLY_CORROBORATED",
            "ACCOUNTS_FILING",
            "",
        ],
        # Child A -> Ultimate (ultimate)
        [
            "CHILD000000000000001",
            "LEI",
            "ULTIMATE000000000001",
            "LEI",
            "IS_ULTIMATELY_CONSOLIDATED_BY",
            "ACTIVE",
            "2010-01-01",
            "",
            "ACCOUNTING_PERIOD",
            "",
            "",
            "",
            "",
            "",
            "2012-03-01",
            "2024-01-01",
            "PUBLISHED",
            "2025-12-31",
            "LOU000000000000001",
            "FULLY_CORROBORATED",
            "ACCOUNTS_FILING",
            "",
        ],
        # Parent -> Ultimate (direct)
        [
            "PARENT00000000000001",
            "LEI",
            "ULTIMATE000000000001",
            "LEI",
            "IS_DIRECTLY_CONSOLIDATED_BY",
            "ACTIVE",
            "2005-01-01",
            "",
            "ACCOUNTING_PERIOD",
            "",
            "",
            "",
            "",
            "",
            "2010-01-01",
            "2024-01-01",
            "PUBLISHED",
            "2025-12-31",
            "LOU000000000000001",
            "FULLY_CORROBORATED",
            "ACCOUNTS_FILING",
            "",
        ],
    ]
    with csv_path.open("w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(headers)
        writer.writerows(rows)
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
    with csv_path.open("w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(headers)
        writer.writerows(rows)
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
    loaded_db.execute(
        "INSERT INTO lei_records "
        "(lei, legal_name, entity_status, registration_status, "
        "entity_category, legal_jurisdiction) VALUES "
        "('GRANDCHILD0000000001', 'Grandchild GmbH', "
        "'ACTIVE', 'ISSUED', 'GENERAL', 'DE')"
    )
    loaded_db.execute(
        "INSERT INTO relationships "
        "(start_node_id, start_node_id_type, end_node_id, "
        "end_node_id_type, relationship_type, relationship_status) "
        "VALUES "
        "('GRANDCHILD0000000001', 'LEI', 'CHILD000000000000001', "
        "'LEI', 'IS_DIRECTLY_CONSOLIDATED_BY', 'ACTIVE')"
    )
    loaded_db.execute(
        "INSERT INTO relationships "
        "(start_node_id, start_node_id_type, end_node_id, "
        "end_node_id_type, relationship_type, relationship_status) "
        "VALUES "
        "('GRANDCHILD0000000001', 'LEI', 'ULTIMATE000000000001', "
        "'LEI', 'IS_ULTIMATELY_CONSOLIDATED_BY', 'ACTIVE')"
    )
    return loaded_db


@pytest.fixture
def diamond_db(
    deep_hierarchy_db: duckdb.DuckDBPyConnection,
) -> duckdb.DuckDBPyConnection:
    """Extend deep_hierarchy_db with a diamond structure.

    Shared Subsidiary is a child of both Child A and Child B.
    """
    deep_hierarchy_db.execute(
        "INSERT INTO lei_records "
        "(lei, legal_name, entity_status, registration_status, "
        "entity_category, legal_jurisdiction) VALUES "
        "('SHARED00000000000001', 'Shared Subsidiary SA', "
        "'ACTIVE', 'ISSUED', 'GENERAL', 'CH')"
    )
    deep_hierarchy_db.execute(
        "INSERT INTO relationships "
        "(start_node_id, start_node_id_type, end_node_id, "
        "end_node_id_type, relationship_type, relationship_status) "
        "VALUES "
        "('SHARED00000000000001', 'LEI', 'CHILD000000000000001', "
        "'LEI', 'IS_DIRECTLY_CONSOLIDATED_BY', 'ACTIVE')"
    )
    deep_hierarchy_db.execute(
        "INSERT INTO relationships "
        "(start_node_id, start_node_id_type, end_node_id, "
        "end_node_id_type, relationship_type, relationship_status) "
        "VALUES "
        "('SHARED00000000000001', 'LEI', 'CHILD000000000000002', "
        "'LEI', 'IS_DIRECTLY_CONSOLIDATED_BY', 'ACTIVE')"
    )
    return deep_hierarchy_db
