from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.doctors.permissions import IsAdminUser
from .ingest import ingest_document, ingest_doctor_profiles, semantic_search
from .models import KnowledgeDocument
from .serializers import (
    KnowledgeDocumentSerializer,
    IngestRequestSerializer,
    SearchRequestSerializer,
    SearchResultSerializer,
)


class KnowledgeDocumentListView(generics.ListAPIView):
    queryset = KnowledgeDocument.objects.all()
    serializer_class = KnowledgeDocumentSerializer
    permission_classes = (permissions.IsAuthenticated, IsAdminUser)


class IngestDocumentView(APIView):
    permission_classes = (permissions.IsAuthenticated, IsAdminUser)

    def post(self, request):
        serializer = IngestRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        doc = ingest_document(**serializer.validated_data)
        return Response(KnowledgeDocumentSerializer(doc).data, status=status.HTTP_201_CREATED)


class IngestDoctorProfilesView(APIView):
    """Bulk re-index all doctor profiles (run after bulk doctor edits)."""
    permission_classes = (permissions.IsAuthenticated, IsAdminUser)

    def post(self, request):
        ingest_doctor_profiles()
        return Response({'detail': 'Doctor profiles indexed successfully.'})


class SemanticSearchView(APIView):
    """POST {"query": "...", "doc_type": "...", "top_k": 5}"""
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        serializer = SearchRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        results = semantic_search(
            query=serializer.validated_data['query'],
            doc_type=serializer.validated_data.get('doc_type'),
            top_k=serializer.validated_data['top_k'],
        )
        return Response(SearchResultSerializer(results, many=True).data)
