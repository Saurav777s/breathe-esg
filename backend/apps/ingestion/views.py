from django.shortcuts import render

# Create your views here.
# ingestion/views.py
import os
import tempfile
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser

from .models import ImportBatch
from .serializers import FileUploadSerializer, ImportBatchSerializer
from .parsers.sap_parser import parse_sap_file
from .parsers.utility_parser import parse_utility_file
from .parsers.travel_parser import parse_travel_file
from .normalizer import normalize_sap_record, normalize_utility_record, normalize_travel_record
from apps.emissions.models import EmissionRecord


class UploadView(APIView):
    parser_classes = [MultiPartParser]

    def post(self, request):
        serializer = FileUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        file = serializer.validated_data['file']
        source_type = serializer.validated_data['source_type']

        batch = ImportBatch.objects.create(
            tenant=request.user.tenant,
            uploaded_by=request.user,
            source_type=source_type,
            file_name=file.name,
            file=file,
            status='processing',
        )

        # Save to temp file for parsing
        suffix = os.path.splitext(file.name)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            for chunk in file.chunks():
                tmp.write(chunk)
            tmp_path = tmp.name

        try:
            PARSERS = {
                'sap_fuel_procurement': (parse_sap_file, normalize_sap_record),
                'utility_electricity': (parse_utility_file, normalize_utility_record),
                'travel_corporate': (parse_travel_file, normalize_travel_record),
            }
            parse_fn, normalize_fn = PARSERS[source_type]
            results = parse_fn(batch, tmp_path)

            raw_records = [r['record'] for r in results]
            warnings_map = {r['row_number']: r['warnings'] for r in results}

            # Bulk save raw records
            model_class = raw_records[0].__class__ if raw_records else None
            if model_class:
                model_class.objects.bulk_create(raw_records)

            # Normalize and create EmissionRecords
            emission_records = []
            for raw in model_class.objects.filter(batch=batch) if model_class else []:
                em = normalize_fn(raw, request.user.tenant, batch)
                if em:
                    emission_records.append(em)

            EmissionRecord.objects.bulk_create(emission_records)

            error_count = sum(1 for r in results if r['warnings'])
            batch.row_count = len(results)
            batch.error_count = error_count
            batch.error_log = [
                {'row': r['row_number'], 'warnings': r['warnings']}
                for r in results if r['warnings']
            ]
            batch.status = 'completed'
            batch.processed_at = timezone.now()
            batch.save()

        except Exception as e:
            batch.status = 'failed'
            batch.error_log = [{'error': str(e)}]
            batch.save()
            return Response({'error': str(e)}, status=500)
        finally:
            os.unlink(tmp_path)

        return Response(ImportBatchSerializer(batch).data, status=201)


class BatchListView(APIView):
    def get(self, request):
        batches = ImportBatch.objects.filter(
            tenant=request.user.tenant
        ).order_by('-created_at')
        return Response(ImportBatchSerializer(batches, many=True).data)
