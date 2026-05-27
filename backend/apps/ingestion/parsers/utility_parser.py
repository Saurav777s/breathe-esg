# ingestion/parsers/utility_parser.py
import pandas as pd
from datetime import datetime


def parse_utility_file(batch, file_path: str) -> list[dict]:
    """
    Parse utility portal CSV.
    Handles common column name variations from different utility portals.
    """
    COLUMN_ALIASES = {
        'meter_id': ['meter_id', 'Meter ID', 'MeterID', 'meter id'],
        'site_name': ['site_name', 'Site', 'Facility', 'Location'],
        'billing_period_start': ['billing_period_start', 'Period Start', 'Start Date', 'From'],
        'billing_period_end': ['billing_period_end', 'Period End', 'End Date', 'To'],
        'consumption_kwh': ['consumption_kwh', 'kWh', 'Usage (kWh)', 'Consumption', 'Energy (kWh)'],
        'demand_kw': ['demand_kw', 'Demand (kW)', 'Peak Demand', 'kW'],
        'tariff_code': ['tariff_code', 'Tariff', 'Rate Code', 'Rate Schedule'],
        'cost_local_currency': ['cost_local_currency', 'Cost', 'Amount', 'Total ($)', 'Charges'],
        'currency': ['currency', 'Currency'],
    }

    df = pd.read_csv(file_path)

    # Resolve column aliases
    resolved = {}
    for canonical, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in df.columns:
                resolved[alias] = canonical
                break

    df.rename(columns=resolved, inplace=True)

    from ingestion.models import RawUtilityRecord
    results = []

    for idx, row in df.iterrows():
        warnings = []
        row_dict = row.to_dict()

        # Validate kWh is numeric
        kwh_raw = str(row_dict.get('consumption_kwh', ''))
        try:
            float(kwh_raw.replace(',', ''))
        except ValueError:
            warnings.append({'field': 'consumption_kwh', 'message': f'Non-numeric kWh: {kwh_raw}'})

        record = RawUtilityRecord(
            batch=batch,
            row_number=idx + 2,
            meter_id=str(row_dict.get('meter_id', '')),
            site_name=str(row_dict.get('site_name', '')),
            billing_period_start=str(row_dict.get('billing_period_start', '')),
            billing_period_end=str(row_dict.get('billing_period_end', '')),
            consumption_kwh=kwh_raw,
            demand_kw=str(row_dict.get('demand_kw', '')),
            tariff_code=str(row_dict.get('tariff_code', '')),
            cost_local_currency=str(row_dict.get('cost_local_currency', '')),
            currency=str(row_dict.get('currency', 'USD')),
            parse_warnings=warnings,
        )
        results.append({'row_number': idx + 2, 'record': record, 'warnings': warnings})

    return results