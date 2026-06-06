import time
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.evaluation.models import EvaluationRun


class TriageView(APIView):
    """POST {"symptoms": "I have chest pain and shortness of breath"}"""
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        symptoms = request.data.get('symptoms', '').strip()
        if not symptoms:
            return Response({'detail': 'symptoms is required.'}, status=status.HTTP_400_BAD_REQUEST)

        from .triage import run_triage
        start = time.monotonic()
        result = run_triage(symptoms=symptoms, patient_id=request.user.pk)
        latency_ms = int((time.monotonic() - start) * 1000)

        EvaluationRun.objects.create(
            agent_type=EvaluationRun.AgentType.TRIAGE,
            query=symptoms,
            response=result['response'],
            context=result['recommended_doctors'],
            latency_ms=latency_ms,
            ran_by=request.user,
        )
        return Response(result)


class BookingChatView(APIView):
    """
    Stateless chat endpoint — caller maintains history.

    POST {"message": "...", "history": [{role, content}, ...]}
    """
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        message = request.data.get('message', '').strip()
        history = request.data.get('history', [])
        if not message:
            return Response({'detail': 'message is required.'}, status=status.HTTP_400_BAD_REQUEST)

        from .booking import run_booking_turn
        start = time.monotonic()
        result = run_booking_turn(
            message=message,
            history=history,
            patient_id=request.user.pk,
        )
        latency_ms = int((time.monotonic() - start) * 1000)

        EvaluationRun.objects.create(
            agent_type=EvaluationRun.AgentType.BOOKING,
            query=message,
            response=result['response'],
            latency_ms=latency_ms,
            ran_by=request.user,
        )
        return Response(result)
