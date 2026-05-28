# Decisions

## SAP — OData CSV flat file export

**What I researched:** SAP exposes procurement and fuel data via multiple mechanisms:
IDoc (batch EDI format, binary/text, requires ABAP middleware), OData services
(REST-like, returns JSON/XML/CSV), BAPI function calls (requires RFC connection),
and direct flat-file exports from transactions like MB52 (stock overview),
ME2M (purchase orders), or FB03 (accounting documents).

**What I chose:** OData CSV flat file, as exported from transaction ME2M or MB52.

**Why:** IDoc requires ABAP knowledge to decode the segment structure and is
primarily used for system-to-system EDI, not sustainability reporting. OData
is the modern SAP interface but requires a live RFC/oData service endpoint per
client — too much setup for onboarding. CSV flat file is what sustainability
leads actually email over or drop in SharePoint.

**German headers:** SAP installations in Germany (and many global SAP configs)
export German column names. We handle this with an explicit alias map in
`sap_parser.py` — Buchungskreis→BUKRS, Belegdatum→BLDAT, etc.

**Subset handled:** Fuel purchases (diesel, petrol, natural gas) identified by
MATNR substring, plus generic procurement. Excluded: partial deliveries
(ELIKZ flag), return orders (negative MENGE), multi-currency conversion,
batch management, serial numbers.

**What I'd ask the PM:**
- "Does the client have a MATNR-to-activity mapping table in their SAP config,
  or do we need to build one from scratch?"
- "Is the plant code (WERKS) the right granularity for facility mapping, or do
  they track by cost center (KOSTL)?"
- "Do they export from ME2M (purchase orders) or MB52 (stock movements)? The
  column sets differ."

---

## Utility — Portal CSV export

**What I researched:** Utilities deliver consumption data via: PDF bills (most
common for small sites), portal CSV exports (most large utilities — EDF, National
Grid, PG&E, BESCOM all offer this), Green Button API (US standard, XML-based),
and ESPI (Energy Service Provider Interface, similar to Green Button).

**What I chose:** Portal CSV export.

**Why:** PDF parsing is fragile — layout changes between billing cycles break
parsers, and table extraction from PDFs requires OCR for some utilities. Green
Button/ESPI is US-specific and requires OAuth per utility account. CSV export
is universal, stable, and what facilities teams actually use when pulling monthly
reports.

**Billing period handling:** Billing periods often don't align with calendar months
(e.g., 17th to 16th). We store `billing_period_start` and `billing_period_end`
as separate fields and use `billing_period_start` as `activity_start` on the
EmissionRecord. The `activity_end` field captures the end date.

**Column aliasing:** Different utility portals use different column names for the
same data. We resolve this with a COLUMN_ALIASES dict in `utility_parser.py`
— the parser tries each known alias before falling back.

**Subset handled:** Single-meter CSV, consumption in kWh, monthly or billing-period
granularity. Excluded: interval/AMI data (15-minute smart meter), time-of-use
breakdown, reactive power (kVAR), fuel mix data for Scope 2 market-based method.

**What I'd ask the PM:**
- "Does the client want location-based or market-based Scope 2? Market-based
  requires supplier-specific emission factors (RECs, PPAs), not grid averages."
- "Are there sites on solar/wind PPAs that should be zero-rated?"
- "Do billing periods align across all sites, or does each meter have its own cycle?"

---

## Corporate Travel — JSON file upload (Concur/Navan format)

**What I researched:** Concur exposes data via its v4 Travel API (OAuth 2.0,
returns JSON itinerary objects). Navan has a similar REST API. Both also offer
data download exports (CSV or JSON) from their admin portals. Typical JSON
shape: a trips array, each trip containing a segments array with type, origin,
destination, dates, vendor, cost.

**What I chose:** JSON file upload simulating a Concur/Navan data download export.

**Why:** Real API integration requires OAuth setup per client (client_id,
client_secret, entity_id for Concur), IT approval, and often a Concur
Implementation Partner engagement. For onboarding a new client in 4 days,
file upload is the realistic path. The JSON shape we parse matches Concur's
actual export format.

**Distance calculation:** Concur does not always include flight distance.
We maintain a lookup table of common airport pairs. Unknown routes get a
1500km default and are auto-flagged for analyst review. A production system
would use a great-circle distance API (e.g. aviation-edge.com).

**Subset handled:** Flights, hotels, car rentals. Emission factors applied:
DEFRA 2023 aviation (economy short-haul 0.255 kg CO₂e/km), hotel (31 kg CO₂e/night),
car (0.192 kg CO₂e/km — medium petrol). Excluded: rail, ferry, actual vs
booked discrepancy, cabin class uplift factors (business class ~2× economy).

**What I'd ask the PM:**
- "Does the client want personal travel excluded, or is all corporate card
  spend in scope?"
- "Should we apply cabin class uplift? Business class has ~2× the emission
  factor of economy per DEFRA."
- "Is there a preferred distance source, or is great-circle sufficient?"

---

## Ingestion mechanism — synchronous, in-request

Files are parsed synchronously within the HTTP request cycle. For large files
this will time out (Render's free tier has a 30s request timeout). The
alternative is a Celery task queue with Redis broker. We chose synchronous
for simplicity — noted in TRADEOFFS.md.