# emissions/serializers.py
from rest_framework import serializers
from .models import EmissionRecord


class EmissionRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmissionRecord
        fields = '__all__'
        read_only_fields = ['id', 'tenant', 'created_at', 'updated_at',
                            'source_type', 'import_batch', 'source_row_id']


class ReviewActionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=['approve', 'reject', 'flag'])
    note = serializers.CharField(required=False, allow_blank=True)