# emissions/models.py
import uuid
from django.db import models
from apps.core.models import Tenant, User
from apps.ingestion.models import ImportBatch


class EmissionRecord(models.Model):
    """
    The single normalized table every source collapses into.
    This is the source of truth for analysts and auditors.
    """
    SCOPE_CHOICES = [
        ('scope1', 'Scope 1 — Direct'),
        ('scope2', 'Scope 2 — Electricity'),
        ('scope3', 'Scope 3 — Value Chain'),
    ]
    CATEGORY_CHOICES = [
        # Scope 1
        ('stationary_combustion', 'Stationary Combustion'),
        ('mobile_combustion', 'Mobile Combustion'),
        # Scope 2
        ('purchased_electricity', 'Purchased Electricity'),
        # Scope 3
        ('business_travel_flight', 'Business Travel — Flight'),
        ('business_travel_hotel', 'Business Travel — Hotel'),
        ('business_travel_car', 'Business Travel — Car'),
        ('purchased_goods', 'Purchased Goods & Services'),
    ]
    STATUS_CHOICES = [
        ('pending_review', 'Pending Review'),
        ('flagged', 'Flagged / Suspicious'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('locked', 'Locked for Audit'),
    ]
    SOURCE_TYPES = [
        ('sap_fuel_procurement', 'SAP'),
        ('utility_electricity', 'Utility'),
        ('travel_corporate', 'Travel'),
        ('manual', 'Manual Entry'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='emission_records')

    # Scope & category
    scope = models.CharField(max_length=10, choices=SCOPE_CHOICES)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)

    # Time
    activity_start = models.DateField()
    activity_end = models.DateField(null=True, blank=True)
    reporting_year = models.IntegerField()

    # Normalized activity data
    activity_value = models.DecimalField(max_digits=18, decimal_places=4)
    activity_unit = models.CharField(max_length=20)  # always SI: kWh, kg, km, nights

    # Computed emissions
    emission_factor = models.DecimalField(max_digits=18, decimal_places=6, null=True)
    emission_factor_source = models.CharField(max_length=255, blank=True)
    co2e_kg = models.DecimalField(max_digits=18, decimal_places=4, null=True)

    # Provenance — WHERE did this row come from?
    source_type = models.CharField(max_length=50, choices=SOURCE_TYPES)
    import_batch = models.ForeignKey(
        ImportBatch, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='emission_records'
    )
    source_row_id = models.CharField(max_length=100, blank=True)  # RawXxx pk
    raw_data_snapshot = models.JSONField(default=dict)  # copy of raw row at import time

    # Location / facility
    facility_code = models.CharField(max_length=100, blank=True)
    facility_name = models.CharField(max_length=255, blank=True)
    country_code = models.CharField(max_length=3, blank=True)

    # Review workflow
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending_review')
    flag_reason = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='reviewed_records'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    is_edited = models.BooleanField(default=False)  # was it changed after import?
    edit_note = models.TextField(blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-activity_start']

    def __str__(self):
        return f"{self.tenant} | {self.scope} | {self.category} | {self.activity_start}"