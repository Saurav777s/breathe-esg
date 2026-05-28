# Sources — Research and Sample Data Rationale

## SAP Fuel & Procurement

**Format researched:** SAP OData CSV export from transaction ME2M (Purchase Orders
by Material) and MB52 (Warehouse Stocks of Material). Documentation reviewed:
SAP Help Portal (help.sap.com) for ME2M field list, SAP Community forums for
real-world export column name variations, and multiple ESG platform implementation
guides that describe SAP integration patterns.

**What I learned:**
- SAP installations in Germany and many global configs export German column headers:
  BUKRS=Buchungskreis (company code), WERKS=Werk (plant), MENGE=Menge (quantity),
  MEINS=Basismengeneinheit (base unit of measure), BLDAT=Belegdatum (document date)
- Dates come in at least three formats depending on SAP locale: YYYYMMDD (standard),
  DD.MM.YYYY (German locale), MM/DD/YYYY (US locale) — all three are real
- Units use SAP internal codes: L (litre), LTR (litre alternate), GAL (US gallon),
  KG (kilogram), M3 (cubic meter), KWH (kilowatt-hour)
- MATNR (material number) is a free-form 18-character field — clients use it
  inconsistently. We do substring matching on common fuel identifiers

**Why sample_sap.csv looks the way it does:**
- Mixed date formats (YYYYMMDD, DD.MM.YYYY, ISO) to test the date parser
- One GAL row to test unit conversion (250 GAL → 946.35 L)
- One row with no WERKS to trigger the "missing plant code" flag
- One row with quantity 999,999 to trigger the "unusually high quantity" flag
- MATNR values contain recognizable substrings (DIESEL, NATGAS, PETROL) to
  test the category inference logic

**What would break in a real deployment:**
- MATNR values in real SAP are often cryptic internal codes like `000000000010012345`
  — substring matching on 'DIESEL' would miss them entirely. We'd need the client's
  material master table (MM60) to map MATNR to a material group and description
- Multi-currency: WRBTR is in local currency (WAERS), not USD. We'd need FX rates
- Credit memos and return deliveries have negative MENGE — our parser doesn't
  handle negative quantities (they'd create negative emission records)
- SAP can export the same purchase order line multiple times across partial
  deliveries — deduplication by BELNR (document number) + BUZEI (line item) needed

---

## Utility Electricity

**Format researched:** Portal CSV exports from PG&E (Pacific Gas & Electric),
EDF Energy UK, and BESCOM (Bangalore Electricity Supply Company). Also reviewed
Green Button Connect My Data specification and ESPI XML schema for completeness.

**What I learned:**
- Every utility portal has slightly different column names for the same data:
  PG&E uses "Usage (kWh)", EDF uses "Consumption (kWh)", BESCOM uses "Units Consumed"
- Billing periods rarely align with calendar months — most utilities bill on a
  rolling 28-33 day cycle starting from meter installation date
- Large commercial accounts often have separate demand charges (kW peak) billed
  separately from consumption (kWh)
- Some utilities include a "fuel mix" column showing % renewable — relevant for
  Scope 2 market-based method

**Why sample_utility.csv looks the way it does:**
- Multiple meters across different sites (HQ floors, warehouses) — realistic for
  an enterprise client with multiple facilities
- Two months of data per meter to test that the parser handles multiple billing
  periods for the same meter correctly
- One data centre row with 1,200,000 kWh — triggers the ">1GWh" flag, tests
  that analysts see it immediately in the review dashboard
- Chennai and Mumbai sites — realistic for an Indian enterprise client

**What would break in a real deployment:**
- Interval data (15-minute AMI/smart meter readings) would have thousands of rows
  per meter per month — we'd need to aggregate before normalizing
- Time-of-use tariffs split consumption into peak/off-peak — our model stores
  a single consumption figure, losing this granularity
- PDF bills from smaller utilities (common in India) would need OCR — our CSV
  parser can't handle them

---

## Corporate Travel

**Format researched:** Concur Travel API v4 documentation (developer.concur.com),
Navan (formerly TripActions) export format, and SAP Concur's "Get Itinerary"
endpoint response schema. Also reviewed GBTA (Global Business Travel Association)
data standards for trip reporting.

**What I learned:**
- Concur's v4 API returns trip objects with nested segments arrays — each segment
  has a type (Air, Hotel, Car, Rail) and type-specific fields
- Flight segments in Concur include origin/destination airport codes (IATA) but
  do NOT include distance — distance must be computed from coordinates or a
  lookup table
- Hotel segments include check-in/check-out dates but not always the number of
  nights — must be computed from date difference
- Business class flights have approximately 2× the emission factor of economy
  per DEFRA guidelines — we apply a flat economy factor in this prototype

**Why sample_travel.json looks the way it does:**
- Mix of routes: LHR-JFK (known, 5540km), BOM-LHR (known, 7200km),
  MAA-SIN (known, 3450km), DEL-CDG (unknown, triggers flag)
- Mix of cabin classes: economy and business — tests that cabin_class is stored
- Mix of segment types: flights, hotels, and one car rental
- DEL-CDG trip has no distance in the lookup table — tests that the "unknown
  route" flag appears in the review dashboard

**What would break in a real deployment:**
- Airport code lookup table covers only ~20 routes — any real client would have
  hundreds of unique routes. Need a great-circle distance API or a comprehensive
  IATA distance database
- Concur API requires OAuth 2.0 per-client credentials — file upload is fine
  for onboarding but not for automated monthly ingestion
- Cancelled trips appear in Concur exports with a 'Cancelled' status — we don't
  filter them, so cancelled flights would incorrectly add to emissions totals