from django.contrib import admin

from .models import EvaluationRun


@admin.register(EvaluationRun)
class EvaluationRunAdmin(admin.ModelAdmin):
    list_display = ('agent_type', 'faithfulness', 'answer_relevancy',
                    'latency_ms', 'ran_at', 'ran_by')
    list_filter = ('agent_type',)
    readonly_fields = ('query', 'response', 'context', 'ran_at', 'ran_by',
                       'faithfulness', 'answer_relevancy',
                       'context_precision', 'context_recall',
                       'hallucination_score', 'toxicity_score', 'latency_ms')
    date_hierarchy = 'ran_at'
