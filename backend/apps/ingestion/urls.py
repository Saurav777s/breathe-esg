# ingestion/urls.py
from django.urls import path
from .views import UploadView, BatchListView

urlpatterns = [
    path('upload/', UploadView.as_view()),
    path('batches/', BatchListView.as_view()),
]