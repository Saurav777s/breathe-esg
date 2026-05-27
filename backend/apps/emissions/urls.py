# emissions/urls.py
from django.urls import path
from .views import (EmissionRecordListView, EmissionRecordDetailView,
                    ReviewActionView, BulkReviewView, DashboardSummaryView)

urlpatterns = [
    path('records/', EmissionRecordListView.as_view()),
    path('records/<uuid:pk>/', EmissionRecordDetailView.as_view()),
    path('records/<uuid:pk>/review/', ReviewActionView.as_view()),
    path('records/bulk-review/', BulkReviewView.as_view()),
    path('dashboard/', DashboardSummaryView.as_view()),
]