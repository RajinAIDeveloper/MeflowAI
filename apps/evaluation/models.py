from django.db import models

from apps.accounts.models import User


class EvaluationRun(models.Model):
    class AgentType(models.TextChoices):
        TRIAGE = 'triage', 'Triage Agent'
        BOOKING = 'booking', 'Booking Agent'
        RAG = 'rag', 'RAG Pipeline'

    agent_type = models.CharField(max_length=20, choices=AgentType.choices)
    query = models.TextField()
    response = models.TextField()
    context = models.JSONField(default=list, blank=True)

    # Ragas metrics (null until evaluated)
    faithfulness = models.FloatField(null=True, blank=True)
    answer_relevancy = models.FloatField(null=True, blank=True)
    context_precision = models.FloatField(null=True, blank=True)
    context_recall = models.FloatField(null=True, blank=True)

    # DeepEval metrics
    hallucination_score = models.FloatField(null=True, blank=True)
    toxicity_score = models.FloatField(null=True, blank=True)

    latency_ms = models.PositiveIntegerField(null=True, blank=True)
    ran_at = models.DateTimeField(auto_now_add=True)
    ran_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='eval_runs'
    )

    class Meta:
        db_table = 'evaluation_runs'
        ordering = ['-ran_at']

    def __str__(self):
        return f"[{self.agent_type}] {self.ran_at:%Y-%m-%d %H:%M}"
