"""URLs, column mappings, and enums for GLEIF golden copy datasets."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

GLEIF_BASE_URL = "https://goldencopy.gleif.org/api/v2/golden-copies/publishes"

DEFAULT_DATA_DIR = Path.home() / ".local" / "share" / "gleif" / "data"
DEFAULT_DB_PATH = Path.home() / ".local" / "share" / "gleif" / "gleif.duckdb"


class DatasetType(StrEnum):
    """GLEIF golden copy dataset types."""

    LEI = "lei2"
    RELATIONSHIPS = "rr"
    REPORTING_EXCEPTIONS = "repex"


DATASET_URLS: dict[DatasetType, str] = {
    DatasetType.LEI: f"{GLEIF_BASE_URL}/lei2/latest.csv",
    DatasetType.RELATIONSHIPS: f"{GLEIF_BASE_URL}/rr/latest.csv",
    DatasetType.REPORTING_EXCEPTIONS: f"{GLEIF_BASE_URL}/repex/latest.csv",
}

DATASET_LABELS: dict[DatasetType, str] = {
    DatasetType.LEI: "Level 1 - LEI Records",
    DatasetType.RELATIONSHIPS: "Level 2 - Relationships",
    DatasetType.REPORTING_EXCEPTIONS: "Level 2 - Reporting Exceptions",
}

# ---------------------------------------------------------------------------
# Level 1 column mapping: CSV header -> DuckDB column name
# The full CSV has 338 columns; we select only the ~30 core fields.
# ---------------------------------------------------------------------------
LEI_CORE_COLUMNS: dict[str, str] = {
    "LEI": "lei",
    "Entity.LegalName": "legal_name",
    "Entity.LegalAddress.FirstAddressLine": "legal_address_line1",
    "Entity.LegalAddress.AdditionalAddressLine.1": "legal_address_line2",
    "Entity.LegalAddress.City": "legal_address_city",
    "Entity.LegalAddress.Region": "legal_address_region",
    "Entity.LegalAddress.Country": "legal_address_country",
    "Entity.LegalAddress.PostalCode": "legal_address_postal_code",
    "Entity.HeadquartersAddress.FirstAddressLine": "hq_address_line1",
    "Entity.HeadquartersAddress.AdditionalAddressLine.1": "hq_address_line2",
    "Entity.HeadquartersAddress.City": "hq_address_city",
    "Entity.HeadquartersAddress.Region": "hq_address_region",
    "Entity.HeadquartersAddress.Country": "hq_address_country",
    "Entity.HeadquartersAddress.PostalCode": "hq_address_postal_code",
    "Entity.RegistrationAuthority.RegistrationAuthorityID": "registration_authority_id",
    "Entity.RegistrationAuthority.RegistrationAuthorityEntityID": (
        "registration_authority_entity_id"
    ),
    "Entity.LegalJurisdiction": "legal_jurisdiction",
    "Entity.EntityCategory": "entity_category",
    "Entity.EntitySubCategory": "entity_sub_category",
    "Entity.LegalForm.EntityLegalFormCode": "legal_form_code",
    "Entity.LegalForm.OtherLegalForm": "legal_form_other",
    "Entity.EntityStatus": "entity_status",
    "Entity.EntityCreationDate": "entity_creation_date",
    "Entity.AssociatedEntity.AssociatedLEI": "associated_lei",
    "Entity.AssociatedEntity.type": "associated_entity_type",
    "Registration.InitialRegistrationDate": "initial_registration_date",
    "Registration.LastUpdateDate": "last_update_date",
    "Registration.RegistrationStatus": "registration_status",
    "Registration.NextRenewalDate": "next_renewal_date",
    "Registration.ManagingLOU": "managing_lou",
    "Registration.ValidationSources": "validation_sources",
    "ConformityFlag": "conformity_flag",
}

# ---------------------------------------------------------------------------
# Level 2 relationship record column mapping
# ---------------------------------------------------------------------------
RR_CORE_COLUMNS: dict[str, str] = {
    "Relationship.StartNode.NodeID": "start_node_id",
    "Relationship.StartNode.NodeIDType": "start_node_id_type",
    "Relationship.EndNode.NodeID": "end_node_id",
    "Relationship.EndNode.NodeIDType": "end_node_id_type",
    "Relationship.RelationshipType": "relationship_type",
    "Relationship.RelationshipStatus": "relationship_status",
    "Relationship.Period.1.startDate": "period_1_start_date",
    "Relationship.Period.1.endDate": "period_1_end_date",
    "Relationship.Period.1.periodType": "period_1_type",
    "Relationship.Qualifiers.1.QualifierDimension": "qualifier_1_dimension",
    "Relationship.Qualifiers.1.QualifierCategory": "qualifier_1_category",
    "Relationship.Quantifiers.1.MeasurementMethod": "quantifier_1_method",
    "Relationship.Quantifiers.1.QuantifierAmount": "quantifier_1_amount",
    "Relationship.Quantifiers.1.QuantifierUnits": "quantifier_1_units",
    "Registration.InitialRegistrationDate": "registration_initial_date",
    "Registration.LastUpdateDate": "registration_last_update",
    "Registration.RegistrationStatus": "registration_status",
    "Registration.NextRenewalDate": "registration_next_renewal",
    "Registration.ManagingLOU": "managing_lou",
    "Registration.ValidationSources": "validation_sources",
    "Registration.ValidationDocuments": "validation_documents",
    "Registration.ValidationReference": "validation_reference",
}

# ---------------------------------------------------------------------------
# Level 2 reporting exceptions column mapping
# ---------------------------------------------------------------------------
REPEX_COLUMNS: dict[str, str] = {
    "LEI": "lei",
    "Exception.Category": "exception_category",
    "Exception.Reason.1": "exception_reason_1",
    "Exception.Reference.1": "exception_reference_1",
}

# Relationship type constants
DIRECT_PARENT = "IS_DIRECTLY_CONSOLIDATED_BY"
ULTIMATE_PARENT = "IS_ULTIMATELY_CONSOLIDATED_BY"
CONSOLIDATION_TYPES = {DIRECT_PARENT, ULTIMATE_PARENT}

# Maximum recursion depth for hierarchy traversal
MAX_HIERARCHY_DEPTH = 50
