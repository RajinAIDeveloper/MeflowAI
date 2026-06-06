from django.db.models import Avg, Count
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.doctors.permissions import IsAdminUser
from .models import EvaluationRun
from .ragas_runner import evaluate_rag_response
from .serializers import EvaluationRunSerializer, EvaluationSummarySerializer


class EvaluationRunListView(generics.ListAPIView):
    serializer_class = EvaluationRunSerializer
    permission_classes = (permissions.IsAuthenticated, IsAdminUser)

    def get_queryset(self):
        qs = EvaluationRun.objects.select_related('ran_by')
        agent_type = self.request.query_params.get('agent_type')
        if agent_type:
            qs = qs.filter(agent_type=agent_type)
        return qs


class EvaluationRunDetailView(generics.RetrieveAPIView):
    queryset = EvaluationRun.objects.select_related('ran_by')
    serializer_class = EvaluationRunSerializer
    permission_classes = (permissions.IsAuthenticated, IsAdminUser)


class EvaluationSummaryView(APIView):
    """
    Returns per-agent-type aggregate metrics — powers the dashboard charts.
    GET /api/evaluation/summary/
    """
    permission_classes = (permissions.IsAuthenticated, IsAdminUser)

    def get(self, request):
        summaries = (
            EvaluationRun.objects
            .values('agent_type')
            .annotate(
                count=Count('id'),
                avg_faithfulness=Avg('faithfulness'),
                avg_answer_relevancy=Avg('answer_relevancy'),
                avg_latency_ms=Avg('latency_ms'),
            )
        )
        serializer = EvaluationSummarySerializer(summaries, many=True)
        return Response(serializer.data)


class RunRagasEvaluationView(APIView):
    """
    Re-score an existing EvaluationRun with Ragas and save the metrics.
    POST /api/evaluation/<pk>/evaluate/
    """
    permission_classes = (permissions.IsAuthenticated, IsAdminUser)

    def post(self, request, pk):
        try:
            run = EvaluationRun.objects.get(pk=pk)
        except EvaluationRun.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        contexts = [c.get('content', '') for c in (run.context or [])]
        scores = evaluate_rag_response(
            query=run.query,
            response=run.response,
            contexts=contexts,
        )

        for field, value in scores.items():
            setattr(run, field, value)
        run.save(update_fields=list(scores.keys()))

        return Response(EvaluationRunSerializer(run).data)
