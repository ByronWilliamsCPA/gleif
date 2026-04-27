# Data Model & Schema

## GLEIF datasets

GLEIF publishes three golden copy datasets daily at:

```text
https://goldencopy.gleif.org/api/v2/golden-copies/publishes/{dataset}/latest.csv
```

| Dataset key | Label | Table |
| ----------- | ----- | ----- |
| `lei2` | Level 1 - LEI Records | `lei_records` |
| `rr` | Level 2 - Relationships | `relationships` |
| `repex` | Level 2 - Reporting Exceptions | `reporting_exceptions` |

---

## `lei_records` table

Populated from the Level 1 LEI dataset. The full CSV has 338 columns; only the core fields are loaded.

| Column | Type | Source CSV field | Notes |
| ------ | ---- | ---------------- | ----- |
| `lei` | VARCHAR PK | `LEI` | 20-character alphanumeric identifier |
| `legal_name` | VARCHAR | `Entity.LegalName` | |
| `legal_address_line1` | VARCHAR | `Entity.LegalAddress.FirstAddressLine` | |
| `legal_address_line2` | VARCHAR | `Entity.LegalAddress.AdditionalAddressLine.1` | |
| `legal_address_city` | VARCHAR | `Entity.LegalAddress.City` | |
| `legal_address_region` | VARCHAR | `Entity.LegalAddress.Region` | |
| `legal_address_country` | VARCHAR | `Entity.LegalAddress.Country` | ISO 3166-1 alpha-2 |
| `legal_address_postal_code` | VARCHAR | `Entity.LegalAddress.PostalCode` | |
| `hq_address_line1` | VARCHAR | `Entity.HeadquartersAddress.FirstAddressLine` | |
| `hq_address_line2` | VARCHAR | `Entity.HeadquartersAddress.AdditionalAddressLine.1` | |
| `hq_address_city` | VARCHAR | `Entity.HeadquartersAddress.City` | |
| `hq_address_region` | VARCHAR | `Entity.HeadquartersAddress.Region` | |
| `hq_address_country` | VARCHAR | `Entity.HeadquartersAddress.Country` | ISO 3166-1 alpha-2 |
| `hq_address_postal_code` | VARCHAR | `Entity.HeadquartersAddress.PostalCode` | |
| `registration_authority_id` | VARCHAR | `Entity.RegistrationAuthority.RegistrationAuthorityID` | |
| `registration_authority_entity_id` | VARCHAR | `Entity.RegistrationAuthority.RegistrationAuthorityEntityID` | |
| `legal_jurisdiction` | VARCHAR | `Entity.LegalJurisdiction` | ISO 3166-1 or ISO 3166-2 code |
| `entity_category` | VARCHAR | `Entity.EntityCategory` | e.g., `GENERAL`, `BRANCH`, `FUND` |
| `entity_sub_category` | VARCHAR | `Entity.EntitySubCategory` | |
| `legal_form_code` | VARCHAR | `Entity.LegalForm.EntityLegalFormCode` | ELF code |
| `legal_form_other` | VARCHAR | `Entity.LegalForm.OtherLegalForm` | Free-text when no ELF code |
| `entity_status` | VARCHAR | `Entity.EntityStatus` | `ACTIVE` or `INACTIVE` |
| `entity_creation_date` | VARCHAR | `Entity.EntityCreationDate` | ISO 8601 |
| `associated_lei` | VARCHAR | `Entity.AssociatedEntity.AssociatedLEI` | For branches/funds |
| `associated_entity_type` | VARCHAR | `Entity.AssociatedEntity.type` | |
| `initial_registration_date` | VARCHAR | `Registration.InitialRegistrationDate` | |
| `last_update_date` | VARCHAR | `Registration.LastUpdateDate` | |
| `registration_status` | VARCHAR | `Registration.RegistrationStatus` | e.g., `ISSUED`, `LAPSED` |
| `next_renewal_date` | VARCHAR | `Registration.NextRenewalDate` | |
| `managing_lou` | VARCHAR | `Registration.ManagingLOU` | LEI of the Local Operating Unit |
| `validation_sources` | VARCHAR | `Registration.ValidationSources` | |
| `conformity_flag` | VARCHAR | `ConformityFlag` | |

---

## `relationships` table

Populated from the Level 2 Relationships dataset.

| Column | Type | Source CSV field |
| ------ | ---- | ---------------- |
| `start_node_id` | VARCHAR NOT NULL | `Relationship.StartNode.NodeID` |
| `end_node_id` | VARCHAR NOT NULL | `Relationship.EndNode.NodeID` |
| `relationship_type` | VARCHAR NOT NULL | `Relationship.RelationshipType` |
| `relationship_status` | VARCHAR | `Relationship.RelationshipStatus` |
| `start_node_id_type` | VARCHAR | `Relationship.StartNode.NodeIDType` |
| `end_node_id_type` | VARCHAR | `Relationship.EndNode.NodeIDType` |
| `period_1_start_date` | VARCHAR | `Relationship.Period.1.startDate` |
| `period_1_end_date` | VARCHAR | `Relationship.Period.1.endDate` |
| `period_1_type` | VARCHAR | `Relationship.Period.1.periodType` |
| `qualifier_1_dimension` | VARCHAR | `Relationship.Qualifiers.1.QualifierDimension` |
| `qualifier_1_category` | VARCHAR | `Relationship.Qualifiers.1.QualifierCategory` |
| `quantifier_1_method` | VARCHAR | `Relationship.Quantifiers.1.MeasurementMethod` |
| `quantifier_1_amount` | VARCHAR | `Relationship.Quantifiers.1.QuantifierAmount` |
| `quantifier_1_units` | VARCHAR | `Relationship.Quantifiers.1.QuantifierUnits` |
| `registration_initial_date` | VARCHAR | `Registration.InitialRegistrationDate` |
| `registration_last_update` | VARCHAR | `Registration.LastUpdateDate` |
| `registration_status` | VARCHAR | `Registration.RegistrationStatus` |
| `registration_next_renewal` | VARCHAR | `Registration.NextRenewalDate` |
| `managing_lou` | VARCHAR | `Registration.ManagingLOU` |
| `validation_sources` | VARCHAR | `Registration.ValidationSources` |
| `validation_documents` | VARCHAR | `Registration.ValidationDocuments` |
| `validation_reference` | VARCHAR | `Registration.ValidationReference` |

**Primary key:** `(start_node_id, end_node_id, relationship_type)`

**Indexes:**

| Index | Column |
| ----- | ------ |
| `idx_rel_start` | `start_node_id` |
| `idx_rel_end` | `end_node_id` |
| `idx_rel_type` | `relationship_type` |
| `idx_rel_status` | `relationship_status` |

### Relationship direction

`start_node_id` is the **child**; `end_node_id` is the **parent**. Read the relationship type left-to-right: `child IS_DIRECTLY_CONSOLIDATED_BY parent`.

### Relationship types

| Constant | Value | Meaning |
| -------- | ----- | ------- |
| `DIRECT_PARENT` | `IS_DIRECTLY_CONSOLIDATED_BY` | Immediate parent entity |
| `ULTIMATE_PARENT` | `IS_ULTIMATELY_CONSOLIDATED_BY` | Top-level parent in the ownership chain |

Non-consolidation types (branches, funds, etc.) appear in the `other_relationships` section of a report.

---

## `reporting_exceptions` table

An exception record means the entity cannot or does not report its ownership relationships.

| Column | Type | Source CSV field |
| ------ | ---- | ---------------- |
| `lei` | VARCHAR NOT NULL | `LEI` |
| `exception_category` | VARCHAR NOT NULL | `Exception.Category` |
| `exception_reason_1` | VARCHAR | `Exception.Reason.1` |
| `exception_reference_1` | VARCHAR | `Exception.Reference.1` |

**Primary key:** `(lei, exception_category)`

**Index:** `idx_repex_lei` on `lei`

Common exception categories: `DIRECT_ACCOUNTING_CONSOLIDATION_PARENT`, `ULTIMATE_ACCOUNTING_CONSOLIDATION_PARENT`. Common reasons: `NON_PUBLIC`, `LEGAL_OBSTACLES`, `NATURAL_PERSONS`, `NO_KNOWN_PERSON`.

---

## `load_metadata` table

Tracks when each dataset was last loaded.

| Column | Type | Notes |
| ------ | ---- | ----- |
| `dataset_type` | VARCHAR PK | `lei2`, `rr`, or `repex` |
| `publish_date` | VARCHAR | From the `x-gleif-publish-date` response header |
| `loaded_at` | TIMESTAMP | Set to `current_timestamp` on load |
| `record_count` | INTEGER | Row count after load |

---

## Python data model

Query functions in `queries.py` return frozen dataclasses from `models.py`:

```python
@dataclass(frozen=True)
class EntityInfo:
    lei: str
    legal_name: str
    entity_status: str
    registration_status: str
    entity_category: str | None
    legal_jurisdiction: str | None
    legal_address_city: str | None
    legal_address_country: str | None
    hq_address_city: str | None
    hq_address_country: str | None

@dataclass(frozen=True)
class RelatedEntity:
    lei: str
    legal_name: str | None
    relationship_type: str
    relationship_status: str
    direction: str  # "parent" | "child" | "sibling" | "other"

@dataclass(frozen=True)
class ReportingException:
    exception_category: str
    exception_reason: str | None
    exception_reference: str | None

@dataclass(frozen=True)
class HierarchyNode:
    lei: str
    legal_name: str | None
    depth: int  # 0 = starting entity, 1 = parent, etc.
    entity_status: str | None
    entity_category: str | None
    legal_jurisdiction: str | None
    relationship_type: str | None
    parent_lei: str | None

@dataclass(frozen=True)
class CorporateGroup:
    root: EntityInfo
    descendants: list[HierarchyNode]
    total_entities: int

@dataclass(frozen=True)
class LEIRelationshipReport:
    entity: EntityInfo
    direct_parent: EntityInfo | None
    ultimate_parent: EntityInfo | None
    children: list[RelatedEntity]
    siblings: list[RelatedEntity]
    other_relationships: list[RelatedEntity]
    reporting_exceptions: list[ReportingException]
```
