"""
Ragas evaluation runner. Called after triage/RAG responses to score quality.

Metrics used:
- faithfulness: does the answer stick to the retrieved context?
- answer_relevancy: how relevant is the answer to the question?
- context_precision: are high-ranked chunks actually relevant?
- context_recall: does the context cover the ground truth?

Usage:
    from apps.evaluation.ragas_runner import evaluate_rag_response
    scores = evaluate_rag_response(query, response, contexts)
"""
import logging

logger = logging.getLogger(__name__)


def evaluate_rag_response(
    query: str,
    response: str,
    contexts: list[str],
    ground_truth: str = '',
) -> dict:
    """
    Run Ragas metrics on a single RAG response.

    Returns dict with keys: faithfulness, answer_relevancy,
    context_precision, context_recall. Values are floats 0-1 or None on error.
    """
    try:
        from datasets import Dataset
        from ragas import evaluate
        from ragas.metrics import (
            faithfulness,
            answer_relevancy,
            context_precision,
            context_recall,
        )

        data = {
            'question': [query],
            'answer': [response],
            'contexts': [contexts],
            'ground_truth': [ground_truth or response],
        }
        dataset = Dataset.from_dict(data)
        result = evaluate(dataset, metrics=[
            faithfulness, answer_relevancy, context_precision, context_recall,
        ])
        return {
            'faithfulness': result['faithfulness'],
            'answer_relevancy': result['answer_relevancy'],
            'context_precision': result['context_precision'],
            'context_recall': result['context_recall'],
        }
    except Exception as exc:
        logger.warning("Ragas evaluation failed: %s", exc)
        return {
            'faithfulness': None,
            'answer_relevancy': None,
            'context_precision': None,
            'context_recall': None,
        }
