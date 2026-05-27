from django.shortcuts import render

# Create your views here.
# emissions/views.py
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import EmissionRecord
from .serializers import EmissionRecordSerializer, ReviewActionSerializer
from apps.core.models import AuditLog


class EmissionRecordListView(APIView):
    def get(self, request):
        qs = EmissionRecord.objects.filter(tenant=request.user.tenant)

        # Filters
        rec_status = request.query_params.get('status')
        scope = request.query_params.get('scope')
        source_type = request.query_params.get('source_type')
        year = request.query_params.get('year')

        if rec_status:
            qs = qs.filter(status=rec_status)
        if scope:
            qs = qs.filter(scope=scope)
        if source_type:
            qs = qs.filter(source_type=source_type)
        if year:
            qs = qs.filter(reporting_year=year)

        return Response(EmissionRecordSerializer(qs, many=True).data)


class EmissionRecordDetailView(APIView):
    def get_object(self, pk, tenant):
        try:
            return EmissionRecord.objects.get(pk=pk, tenant=tenant)
        except EmissionRecord.DoesNotExist:
            return None

    def get(self, request, pk):
        obj = self.get_object(pk, request.user.tenant)
        if not obj:
            return Response(status=404)
        return Response(EmissionRecordSerializer(obj).data)

    def patch(self, request, pk):
        obj = self.get_object(pk, request.user.tenant)
        if not obj:
            return Response(status=404)
        if obj.status == 'locked':
            return Response({'error': 'Record is locked for audit'}, status=400)

        old_data = EmissionRecordSerializer(obj).data
        serializer = EmissionRecordSerializer(obj, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save(is_edited=True)
            AuditLog.objects.create(
                tenant=request.user.tenant,
                user=request.user,
                action='updated',
                model_name='EmissionRecord',
                object_id=str(pk),
                diff={'before': old_data, 'after': serializer.data},
            )
            return Response(serializer.data)
        return Response(serializer.errors, status=400)


class ReviewActionView(APIView):
    def post(self, request, pk):
        obj = None
        try:
            obj = EmissionRecord.objects.get(pk=pk, tenant=request.user.tenant)
        except EmissionRecord.DoesNotExist:
            return Response(status=404)

        if obj.status == 'locked':
            return Response({'error': 'Record already locked'}, status=400)

        serializer = ReviewActionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        action = serializer.validated_data['action']
        note = serializer.validated_data.get('note', '')

        ACTION_STATUS_MAP = {
            'approve': 'approved',
            'reject': 'rejected',
            'flag': 'flagged',
        }

        obj.status = ACTION_STATUS_MAP[action]
        obj.reviewed_by = request.user
        obj.reviewed_at = timezone.now()
        if note:
            obj.edit_note = note
        obj.save()

        AuditLog.objects.create(
            tenant=request.user.tenant,
            user=request.user,
            action=action + 'd' if action != 'flag' else 'updated',
            model_name='EmissionRecord',
            object_id=str(pk),
            diff={'action': action, 'note': note},
        )

        return Response({'status': obj.status})


class BulkReviewView(APIView):
    def post(self, request):
        ids = request.data.get('ids', [])
        action = request.data.get('action')
        note = request.data.get('note', '')

        if action not in ('approve', 'reject'):
            return Response({'error': 'Invalid action'}, status=400)

        new_status = 'approved' if action == 'approve' else 'rejected'
        updated = EmissionRecord.objects.filter(
            pk__in=ids,
            tenant=request.user.tenant,
        ).exclude(status='locked').update(
            status=new_status,
            reviewed_by=request.user,
            reviewed_at=timezone.now(),
        )

        return Response({'updated': updated})


class DashboardSummaryView(APIView):
    def get(self, request):
        qs = EmissionRecord.objects.filter(tenant=request.user.tenant)
        year = request.query_params.get('year')
        if year:
            qs = qs.filter(reporting_year=year)

        from django.db.models import Sum, Count
        summary = qs.values('scope', 'status').annotate(
            count=Count('id'),
            total_co2e=Sum('co2e_kg'),
        )

        return Response({
            'total_records': qs.count(),
            'pending_review': qs.filter(status='pending_review').count(),
            'flagged': qs.filter(status='flagged').count(),
            'approved': qs.filter(status='approved').count(),
            'total_co2e_kg': qs.aggregate(Sum('co2e_kg'))['co2e_kg__sum'],
            'by_scope_and_status': list(summary),
        })