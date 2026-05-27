# ingestion/serializers.py
from rest_framework import serializers
from .models import ImportBatch


class ImportBatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImportBatch
        fields = ['id', 'source_type', 'file_name', 'status',
                  'row_count', 'error_count', 'error_log',
                  'created_at', 'processed_at']
        read_only_fields = fields


class FileUploadSerializer(serializers.Serializer):
    source_type = serializers.ChoiceField(choices=ImportBatch.SOURCE_TYPES)
    file = serializers.FileField()