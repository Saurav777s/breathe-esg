# ingestion/models.py
import uuid
from django.db import models
from apps.core.models import Tenant, User


class ImportBatch(models.Model):
    """One file upload = one batch. Tracks parse status."""
    SOURCE_TYPES = [
        ('sap_fuel_procurement', 'SAP Fuel & Procurement'),
        ('utility_electricity', 'Utility Electricity'),
        ('travel_corporate', 'Corporate Travel'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    source_type = models.CharField(max_length=50, choices=SOURCE_TYPES)
    file_name = models.CharField(max_length=255)
    file = models.FileField(upload_to='imports/%Y/%m/')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    row_count = models.IntegerField(default=0)
    error_count = models.IntegerField(default=0)
    error_log = models.JSONField(default=list)  # [{row, field, message}]
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.source_type} — {self.file_name} ({self.status})"


class RawSAPRecord(models.Model):
    """Raw SAP OData CSV row, stored before normalization."""
    batch = models.ForeignKey(ImportBatch, on_delete=models.CASCADE, related_name='sap_rows')
    row_number = models.IntegerField()

    # SAP field names kept as-is for traceability
    BUKRS = models.CharField(max_length=10, blank=True)   # Company Code
    WERKS = models.CharField(max_length=10, blank=True)   # Plant
    MATNR = models.CharField(max_length=40, blank=True)   # Material Number
    MENGE = models.CharField(max_length=20, blank=True)   # Quantity (string — normalize later)
    MEINS = models.CharField(max_length=10, blank=True)   # Unit of Measure
    BLDAT = models.CharField(max_length=20, blank=True)   # Document Date (raw string)
    WRBTR = models.CharField(max_length=20, blank=True)   # Amount
    WAERS = models.CharField(max_length=5, blank=True)    # Currency
    BKTXT = models.CharField(max_length=255, blank=True)  # Description

    parse_warnings = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)


class RawUtilityRecord(models.Model):
    """Raw utility portal CSV row."""
    batch = models.ForeignKey(ImportBatch, on_delete=models.CASCADE, related_name='utility_rows')
    row_number = models.IntegerField()

    meter_id = models.CharField(max_length=100, blank=True)
    site_name = models.CharField(max_length=255, blank=True)
    billing_period_start = models.CharField(max_length=30, blank=True)
    billing_period_end = models.CharField(max_length=30, blank=True)
    consumption_kwh = models.CharField(max_length=20, blank=True)
    demand_kw = models.CharField(max_length=20, blank=True)
    tariff_code = models.CharField(max_length=50, blank=True)
    cost_local_currency = models.CharField(max_length=20, blank=True)
    currency = models.CharField(max_length=5, blank=True)

    parse_warnings = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)


class RawTravelRecord(models.Model):
    """Raw Concur/Navan travel JSON record."""
    SEGMENT_TYPES = [
        ('flight', 'Flight'),
        ('hotel', 'Hotel'),
        ('car', 'Car Rental'),
        ('rail', 'Rail'),
    ]

    batch = models.ForeignKey(ImportBatch, on_delete=models.CASCADE, related_name='travel_rows')
    row_number = models.IntegerField()

    trip_id = models.CharField(max_length=100, blank=True)
    traveler_id = models.CharField(max_length=100, blank=True)
    segment_type = models.CharField(max_length=20, choices=SEGMENT_TYPES, blank=True)
    origin_code = models.CharField(max_length=10, blank=True)   # IATA airport or city
    destination_code = models.CharField(max_length=10, blank=True)
    departure_date = models.CharField(max_length=30, blank=True)
    return_date = models.CharField(max_length=30, blank=True)
    vendor = models.CharField(max_length=100, blank=True)
    cabin_class = models.CharField(max_length=30, blank=True)   # economy/business
    cost_usd = models.CharField(max_length=20, blank=True)
    nights = models.CharField(max_length=10, blank=True)        # hotels

    parse_warnings = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
