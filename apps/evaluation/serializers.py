from rest_framework import serializers

from .models import EvaluationRun


class EvaluationRunSerializer(serializers.ModelSerializer):
    agent_type_display = serializers.CharField(source='get_agent_type_display', read_only=True)
    ran_by_email = serializers.EmailField(source='ran_by.email', read_only=True)

    class Meta:
        model = EvaluationRun
        fields = (
            'id', 'agent_type', 'agent_type_display', 'query', 'response',
            'context', 'faithfulness', 'answer_relevancy', 'context_precision',
            'context_recall', 'hallucination_score', 'toxicity_score',
            'latency_ms', 'ran_at', 'ran_by', 'ran_by_email',
        )
        read_only_fields = fields


class EvaluationSummarySerializer(serializers.Serializer):
    agent_type = serializers.CharField()
    count = serializers.IntegerField()
    avg_faithfulness = serializers.FloatField(allow_null=True)
    avg_answer_relevancy = serializers.FloatField(allow_null=True)
    avg_latency_ms = serializers.FloatField(allow_null=True)
