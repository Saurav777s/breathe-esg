# ingestion/parsers/sap_parser.py
import pandas as pd
from datetime import datetime
from apps.ingestion.models import RawSAPRecord

# SAP German → English header map
SAP_COLUMN_MAP = {
    'BUKRS': 'BUKRS', 'Buchungskreis': 'BUKRS',
    'WERKS': 'WERKS', 'Werk': 'WERKS',
    'MATNR': 'MATNR', 'Materialnummer': 'MATNR',
    'MENGE': 'MENGE', 'Menge': 'MENGE',
    'MEINS': 'MEINS', 'Basismengeneinheit': 'MEINS',
    'BLDAT': 'BLDAT', 'Belegdatum': 'BLDAT',
    'WRBTR': 'WRBTR', 'Betrag in Hauswährung': 'WRBTR',
    'WAERS': 'WAERS',
    'BKTXT': 'BKTXT', 'Belegkopftext': 'BKTXT',
}

# Units SAP uses → normalized unit
UNIT_NORMALIZATION = {
    'L': 'L', 'LTR': 'L', 'GAL': 'L',  # will convert GAL→L during normalization
    'KG': 'kg', 'G': 'kg', 'T': 'kg',
    'KWH': 'kWh', 'MWH': 'kWh',
    'M3': 'm3', 'NM3': 'm3',
    'PC': 'pc', 'EA': 'pc',
}

def parse_sap_date(raw: str) -> str:
    """SAP dates come as YYYYMMDD, DD.MM.YYYY, or MM/DD/YYYY."""
    for fmt in ('%Y%m%d', '%d.%m.%Y', '%m/%d/%Y', '%Y-%m-%d'):
        try:
            return datetime.strptime(raw.strip(), fmt).strftime('%Y-%m-%d')
        except (ValueError, AttributeError):
            continue
    return raw  # return raw if unparseable, flag as warning


def parse_sap_file(batch, file_path: str) -> list[dict]:
    """
    Parse SAP OData CSV export.
    Returns list of {row_number, record, warnings}.
    """
    try:
        df = pd.read_csv(file_path, encoding='utf-8', sep=None, engine='python')
    except UnicodeDecodeError:
        df = pd.read_csv(file_path, encoding='latin-1', sep=None, engine='python')

    # Normalize column names
    df.rename(columns=SAP_COLUMN_MAP, inplace=True)

    results = []
    required = ['BUKRS', 'WERKS', 'MENGE', 'MEINS', 'BLDAT']

    for idx, row in df.iterrows():
        warnings = []
        row_dict = row.to_dict()

        # Check required fields
        for field in required:
            if field not in row_dict or pd.isna(row_dict.get(field)):
                warnings.append({'field': field, 'message': f'{field} is missing'})

        # Normalize date
        raw_date = str(row_dict.get('BLDAT', ''))
        normalized_date = parse_sap_date(raw_date)
        if normalized_date == raw_date and raw_date:
            warnings.append({'field': 'BLDAT', 'message': f'Unknown date format: {raw_date}'})

        # Normalize unit
        raw_unit = str(row_dict.get('MEINS', '')).upper()
        if raw_unit not in UNIT_NORMALIZATION:
            warnings.append({'field': 'MEINS', 'message': f'Unknown unit: {raw_unit}'})

        record = RawSAPRecord(
            batch=batch,
            row_number=idx + 2,  # 1-indexed, row 1 = header
            BUKRS=str(row_dict.get('BUKRS', '')),
            WERKS=str(row_dict.get('WERKS', '')),
            MATNR=str(row_dict.get('MATNR', '')),
            MENGE=str(row_dict.get('MENGE', '')),
            MEINS=str(row_dict.get('MEINS', '')),
            BLDAT=normalized_date,
            WRBTR=str(row_dict.get('WRBTR', '')),
            WAERS=str(row_dict.get('WAERS', '')),
            BKTXT=str(row_dict.get('BKTXT', '')),
            parse_warnings=warnings,
        )
        results.append({'row_number': idx + 2, 'record': record, 'warnings': warnings})

    return results