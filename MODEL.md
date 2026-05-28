# Data Model

## Architecture: Two-layer Raw → Normalized

Every source produces two sets of rows: raw records (exact copy of what came in)
and normalized EmissionRecords (what analysts and auditors see).

**Why two layers?**  
If an emission factor changes, or a dispute arises about what was ingested, 
the raw record is the legal source of truth. The normalized record is a 
derived view. This mirrors how accounting systems treat journals vs ledgers.

---

## Multi-tenancy

Every table has a `tenant` FK. Every queryset is filtered by `request.user.tenant`
at the view layer. We use row-level tenancy (one shared DB, tenant FK on all tables)
rather than schema-per-tenant because:
- Schema-per-tenant requires dynamic DB routing and complicates migrations
- Row-level is sufficient for a prototype; the tradeoff is that a SQL injection
  bug could theoretically leak cross-tenant data — mitigated by always filtering
  at the ORM layer, never with raw SQL

In production we'd add a `TenantMiddleware` that injects tenant into every request
and a custom QuerySet base class that auto-filters — removing the risk of an
engineer forgetting `.filter(tenant=...)`.

---

## Scope 1 / 2 / 3 Categorization

| Source | Scope | Category | How derived |
|--------|-------|----------|-------------|
| SAP — diesel/petrol | Scope 1 | mobile_combustion | MATNR substring match |
| SAP — natural gas | Scope 1 | stationary_combustion | MATNR substring match |
| SAP — other procurement | Scope 3 | purchased_goods | Default fallback |
| Utility electricity | Scope 2 | purchased_electricity | Always |
| Travel — flight | Scope 3 | business_travel_flight | Segment type |
| Travel — hotel | Scope 3 | business_travel_hotel | Segment type |
| Travel — car rental | Scope 3 | business_travel_car | Segment type |

SAP categorization via MATNR is imperfect — a real deployment needs a 
plant-to-activity lookup table from the client's SAP configuration. We flag 
this as a known gap in DECISIONS.md.

---

## Source-of-Truth Tracking

Every `EmissionRecord` carries:

| Field | Purpose |
|-------|---------|
| `source_type` | Which system (SAP / utility / travel / manual) |
| `import_batch` | FK to the specific file upload that produced this row |
| `source_row_id` | PK of the raw record (RawSAPRecord, etc.) |
| `raw_data_snapshot` | JSON copy of the raw row at import time |
| `is_edited` | True if an analyst changed any value after import |
| `edit_note` | Analyst's explanation for any edit |

This means: even if the raw record is later deleted, the EmissionRecord
retains a snapshot of what it was built from.

---

## Unit Normalization

All activity values are stored in SI base units: `L`, `kg`, `kWh`, `km`, `nights`.

Conversion happens in `normalizer.py`, never in the parser. Parsers store
raw strings. This separation means:
- If a conversion factor was wrong, you can re-run normalization without
  re-parsing the file
- Raw data is preserved exactly as received

Conversion table used:
- GAL → L × 3.78541
- MWH → kWh × 1000
- T → kg × 1000
- G → kg × 0.001

---

## Audit Trail

`AuditLog` is append-only. No updates, no deletes. Every approve/reject/edit
writes a new row with:
- Which user took the action
- Which object was affected
- A JSON diff of what changed (before/after for edits, action+note for reviews)

Records in `locked` status cannot be modified — the view layer enforces this.
The locked state is intended for records that have been submitted to auditors;
once locked, only an admin can unlock (not yet implemented — noted in TRADEOFFS.md).

---

## Key Design Decisions

**Why UUID primary keys on ImportBatch and EmissionRecord?**  
Prevents enumeration attacks (an attacker can't guess `?id=1,2,3`). Also
avoids leaking information about how many records exist.

**Why store emission factors on the record itself?**  
DEFRA updates factors annually. Storing the factor used at ingestion time means
historical records remain accurate even after factor updates. A future
`EmissionFactor` versioned model would replace the hardcoded constants.

**Why is `reviewed_by` nullable?**  
Records start as `pending_review` with no reviewer. Making it non-nullable
would require a sentinel user, which is worse than nullable.