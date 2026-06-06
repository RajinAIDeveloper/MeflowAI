from django.urls import path

from .views import (
    KnowledgeDocumentListView,
    IngestDocumentView,
    IngestDoctorProfilesView,
    SemanticSearchView,
)

urlpatterns = [
    path('documents/', KnowledgeDocumentListView.as_view(), name='rag-document-list'),
    path('ingest/', IngestDocumentView.as_view(), name='rag-ingest'),
    path('ingest/doctors/', IngestDoctorProfilesView.as_view(), name='rag-ingest-doctors'),
    path('search/', SemanticSearchView.as_view(), name='rag-search'),
]
