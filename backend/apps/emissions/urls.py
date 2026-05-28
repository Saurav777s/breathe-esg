from django.urls import path
from .views import (EmissionRecordListView, EmissionRecordDetailView,
                    ReviewActionView, BulkReviewView, DashboardSummaryView)

urlpatterns = [
    path('dashboard/', DashboardSummaryView.as_view()),
    path('records/', EmissionRecordListView.as_view()),
    path('records/bulk-review/', BulkReviewView.as_view()),        # MUST be before <uuid:pk>
    path('records/<uuid:pk>/', EmissionRecordDetailView.as_view()),
    path('records/<uuid:pk>/review/', ReviewActionView.as_view()),
]