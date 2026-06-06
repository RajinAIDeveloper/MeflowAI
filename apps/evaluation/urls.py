from django.urls import path

from .views import (
    EvaluationRunListView,
    EvaluationRunDetailView,
    EvaluationSummaryView,
    RunRagasEvaluationView,
)

urlpatterns = [
    path('', EvaluationRunListView.as_view(), name='eval-run-list'),
    path('summary/', EvaluationSummaryView.as_view(), name='eval-summary'),
    path('<int:pk>/', EvaluationRunDetailView.as_view(), name='eval-run-detail'),
    path('<int:pk>/evaluate/', RunRagasEvaluationView.as_view(), name='eval-run-ragas'),
]
