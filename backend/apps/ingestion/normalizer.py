# ingestion/normalizer.py
from decimal import Decimal, InvalidOperation
from datetime import datetime, date
from apps.emissions.models import EmissionRecord

# SAP Material → category/scope mapping (extend with real MATNR patterns)
SAP_MATERIAL_CATEGORY_MAP = {
    # Diesel
    'DIESEL': ('scope1', 'mobile_combustion'),
    'FUEL_DIESEL': ('scope1', 'mobile_combustion'),
    'PETROL': ('scope1', 'mobile_combustion'),
    # Natural gas
    'NATGAS': ('scope1', 'stationary_combustion'),
    'NATURAL_GAS': ('scope1', 'stationary_combustion'),
    # Procurement (default Scope 3)
    'DEFAULT': ('scope3', 'purchased_goods'),
}

# Unit conversion to SI base
UNIT_TO_SI = {
    'L': ('L', Decimal('1')),
    'LTR': ('L', Decimal('1')),
    'GAL': ('L', Decimal('3.78541')),
    'KG': ('kg', Decimal('1')),
    'G': ('kg', Decimal('0.001')),
    'T': ('kg', Decimal('1000')),
    'KWH': ('kWh', Decimal('1')),
    'MWH': ('kWh', Decimal('1000')),
    'M3': ('m3', Decimal('1')),
}

# Emission factors (kg CO2e per unit) — source: DEFRA 2023
EMISSION_FACTORS = {
    ('L', 'mobile_combustion'): Decimal('2.68'),    # diesel kg CO2e/L
    ('L', 'stationary_combustion'): Decimal('2.68'),
    ('kWh', 'purchased_electricity'): Decimal('0.233'),  # UK grid avg
    ('kg', 'purchased_goods'): Decimal('0.1'),       # placeholder
    ('km', 'business_travel_flight'): Decimal('0.255'),  # economy short-haul
    ('nights', 'business_travel_hotel'): Decimal('31.0'),  # kg CO2e/night
    ('km', 'business_travel_car'): Decimal('0.192'),
}

# Approx flight distances (km) by airport pair — for demo
FLIGHT_DISTANCES = {
    ('LHR', 'JFK'): 5540, ('JFK', 'LHR'): 5540,
    ('DEL', 'LHR'): 6700, ('BOM', 'LHR'): 7200,
    ('MAA', 'SIN'): 3450, ('BLR', 'SIN'): 3400,
    ('NRT', 'LAX'): 8750,
}


def safe_decimal(value: str) -> Decimal | None:
    try:
        return Decimal(str(value).replace(',', '').strip())
    except (InvalidOperation, ValueError):
        return None


def normalize_sap_record(raw, tenant, batch) -> EmissionRecord | None:
    qty = safe_decimal(raw.MENGE)
    if qty is None:
        return None

    unit_upper = raw.MEINS.upper()
    si_unit, factor = UNIT_TO_SI.get(unit_upper, (raw.MEINS, Decimal('1')))
    normalized_qty = qty * factor

    # Derive category from material number prefix
    scope, category = SAP_MATERIAL_CATEGORY_MAP.get(
        raw.MATNR.upper(),
        SAP_MATERIAL_CATEGORY_MAP['DEFAULT']
    )
    for key in SAP_MATERIAL_CATEGORY_MAP:
        if key in raw.MATNR.upper():
            scope, category = SAP_MATERIAL_CATEGORY_MAP[key]
            break

    try:
        act_date = datetime.strptime(raw.BLDAT, '%Y-%m-%d').date()
    except ValueError:
        act_date = date.today()

    ef_key = (si_unit, category)
    ef = EMISSION_FACTORS.get(ef_key)
    co2e = (normalized_qty * ef) if ef else None

    flags = []
    if normalized_qty > 100000:
        flags.append('Unusually high quantity — verify')
    if not raw.WERKS:
        flags.append('Missing plant code WERKS')

    return EmissionRecord(
        tenant=tenant,
        scope=scope,
        category=category,
        activity_start=act_date,
        reporting_year=act_date.year,
        activity_value=normalized_qty,
        activity_unit=si_unit,
        emission_factor=ef,
        emission_factor_source='DEFRA 2023',
        co2e_kg=co2e,
        source_type='sap_fuel_procurement',
        import_batch=batch,
        source_row_id=str(raw.pk),
        raw_data_snapshot={
            'BUKRS': raw.BUKRS, 'WERKS': raw.WERKS,
            'MATNR': raw.MATNR, 'MENGE': raw.MENGE,
            'MEINS': raw.MEINS, 'BLDAT': raw.BLDAT,
        },
        facility_code=raw.WERKS,
        status='flagged' if flags else 'pending_review',
        flag_reason='; '.join(flags),
    )


def normalize_utility_record(raw, tenant, batch) -> EmissionRecord | None:
    kwh = safe_decimal(raw.consumption_kwh)
    if kwh is None:
        return None

    try:
        start = datetime.strptime(raw.billing_period_start, '%Y-%m-%d').date()
    except ValueError:
        start = date.today()

    ef = EMISSION_FACTORS.get(('kWh', 'purchased_electricity'))
    co2e = kwh * ef if ef else None

    flags = []
    if kwh > 1_000_000:
        flags.append('Consumption > 1GWh — verify meter multiplier')

    return EmissionRecord(
        tenant=tenant,
        scope='scope2',
        category='purchased_electricity',
        activity_start=start,
        reporting_year=start.year,
        activity_value=kwh,
        activity_unit='kWh',
        emission_factor=ef,
        emission_factor_source='DEFRA 2023 Grid Average',
        co2e_kg=co2e,
        source_type='utility_electricity',
        import_batch=batch,
        source_row_id=str(raw.pk),
        raw_data_snapshot={
            'meter_id': raw.meter_id, 'site_name': raw.site_name,
            'consumption_kwh': raw.consumption_kwh,
            'billing_period_start': raw.billing_period_start,
            'billing_period_end': raw.billing_period_end,
        },
        facility_code=raw.meter_id,
        facility_name=raw.site_name,
        status='flagged' if flags else 'pending_review',
        flag_reason='; '.join(flags),
    )


def normalize_travel_record(raw, tenant, batch) -> EmissionRecord | None:
    try:
        dep_date = datetime.strptime(raw.departure_date[:10], '%Y-%m-%d').date()
    except (ValueError, TypeError):
        dep_date = date.today()

    flags = []

    if raw.segment_type == 'flight':
        pair = (raw.origin_code, raw.destination_code)
        dist = FLIGHT_DISTANCES.get(pair)
        if not dist:
            dist = 1500  # default unknown route
            flags.append(f'Unknown route {pair} — used default 1500km')
        ef = EMISSION_FACTORS.get(('km', 'business_travel_flight'))
        co2e = Decimal(dist) * ef if ef else None
        return EmissionRecord(
            tenant=tenant,
            scope='scope3',
            category='business_travel_flight',
            activity_start=dep_date,
            reporting_year=dep_date.year,
            activity_value=Decimal(dist),
            activity_unit='km',
            emission_factor=ef,
            emission_factor_source='DEFRA 2023 Aviation',
            co2e_kg=co2e,
            source_type='travel_corporate',
            import_batch=batch,
            source_row_id=str(raw.pk),
            raw_data_snapshot={
                'trip_id': raw.trip_id, 'origin': raw.origin_code,
                'destination': raw.destination_code, 'cabin': raw.cabin_class,
            },
            status='flagged' if flags else 'pending_review',
            flag_reason='; '.join(flags),
        )

    elif raw.segment_type == 'hotel':
        nights = safe_decimal(raw.nights) or Decimal('1')
        ef = EMISSION_FACTORS.get(('nights', 'business_travel_hotel'))
        co2e = nights * ef if ef else None
        return EmissionRecord(
            tenant=tenant,
            scope='scope3',
            category='business_travel_hotel',
            activity_start=dep_date,
            reporting_year=dep_date.year,
            activity_value=nights,
            activity_unit='nights',
            emission_factor=ef,
            emission_factor_source='DEFRA 2023 Hotel',
            co2e_kg=co2e,
            source_type='travel_corporate',
            import_batch=batch,
            source_row_id=str(raw.pk),
            raw_data_snapshot={
                'trip_id': raw.trip_id, 'vendor': raw.vendor,
                'nights': raw.nights,
            },
            status='flagged' if flags else 'pending_review',
        )

    return None