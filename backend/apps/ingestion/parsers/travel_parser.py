# ingestion/parsers/travel_parser.py
import json
from apps.ingestion.models import RawTravelRecord

# IATA to country mapping (subset — expand as needed)
IATA_COUNTRY = {
    'JFK': 'US', 'LHR': 'GB', 'CDG': 'FR', 'FRA': 'DE',
    'SIN': 'SG', 'DXB': 'AE', 'HKG': 'HK', 'NRT': 'JP',
    'BOM': 'IN', 'DEL': 'IN', 'MAA': 'IN', 'BLR': 'IN',
}


def parse_travel_file(batch, file_path: str) -> list[dict]:
    """
    Parse Concur/Navan-style JSON export.
    Expected shape: list of trip objects each with 'segments' array.
    """
    with open(file_path, 'r') as f:
        data = json.load(f)

    # Support both top-level list and {"trips": [...]} envelope
    if isinstance(data, dict):
        trips = data.get('trips', data.get('data', []))
    else:
        trips = data

    results = []
    row_num = 1

    for trip in trips:
        segments = trip.get('segments', [])
        if not segments:
            # Treat the trip itself as one segment
            segments = [trip]

        for segment in segments:
            warnings = []

            seg_type = segment.get('type', trip.get('type', '')).lower()
            if seg_type not in ('flight', 'hotel', 'car', 'rail'):
                warnings.append({
                    'field': 'type',
                    'message': f'Unknown segment type: {seg_type}'
                })

            origin = segment.get('origin', segment.get('from', ''))
            dest = segment.get('destination', segment.get('to', ''))

            if seg_type == 'flight' and not (origin and dest):
                warnings.append({
                    'field': 'origin/destination',
                    'message': 'Flight missing airport codes — cannot compute distance'
                })

            record = RawTravelRecord(
                batch=batch,
                row_number=row_num,
                trip_id=str(trip.get('id', trip.get('trip_id', ''))),
                traveler_id=str(trip.get('traveler_id', trip.get('employee_id', ''))),
                segment_type=seg_type,
                origin_code=str(origin).upper(),
                destination_code=str(dest).upper(),
                departure_date=str(segment.get('departure_date', segment.get('check_in', ''))),
                return_date=str(segment.get('return_date', segment.get('check_out', ''))),
                vendor=str(segment.get('vendor', segment.get('airline', segment.get('hotel_name', '')))),
                cabin_class=str(segment.get('cabin_class', segment.get('class', 'economy'))).lower(),
                cost_usd=str(segment.get('cost_usd', segment.get('amount', ''))),
                nights=str(segment.get('nights', '')),
                parse_warnings=warnings,
            )
            results.append({'row_number': row_num, 'record': record, 'warnings': warnings})
            row_num += 1

    return results