"""
Triage agent: patient describes symptoms → severity + department + doctor recommendations.

Graph:
    START → knowledge_node → triage_node → rag_lookup_node → respond_node → END

knowledge_node retrieves curated medical knowledge (FAQs, symptom guides,
department info, hospital policies) relevant to the symptoms; triage_node
classifies severity/department *grounded in that knowledge*; rag_lookup_node
retrieves relevant doctors; respond_node composes the final response.
"""
from typing import TypedDict
from langgraph.graph import StateGraph, END

from .llm import get_llm

# Knowledge doc types consulted during triage (everything except doctor profiles,
# which are retrieved separately for recommendations).
KNOWLEDGE_DOC_TYPES = ['medical_faq', 'department_info', 'hospital_policy']


class TriageState(TypedDict):
    symptoms: str
    severity: str        # low / medium / high / emergency
    department: str
    knowledge: list      # curated medical knowledge chunks (grounding)
    rag_results: list    # recommended doctor profiles
    response: str
    patient_id: int


TRIAGE_SYSTEM_PROMPT = """You are MediFlow, an AI medical triage assistant.
Use the provided reference knowledge (if any) to inform your assessment, but rely
on sound medical judgement. Analyse the patient's symptoms and respond with a JSON object:
{
  "severity": "low|medium|high|emergency",
  "department": "<medical department>",
  "reasoning": "<one sentence>"
}
Do not include markdown fences. Output only the JSON."""

RESPONSE_SYSTEM_PROMPT = """You are MediFlow, a friendly patient navigation assistant.
Based on the triage assessment and available doctors, write a warm, clear response that:
1. Acknowledges the patient's symptoms empathetically.
2. Explains the assessed urgency level.
3. Recommends 1-3 specific doctors from the list (use their real names).
4. Suggests whether to book immediately or schedule for later.
Keep it under 150 words."""


def knowledge_node(state: TriageState) -> TriageState:
    """Retrieve curated medical knowledge relevant to the symptoms (grounding)."""
    from apps.rag.ingest import semantic_search
    results = semantic_search(
        state['symptoms'],
        doc_types=KNOWLEDGE_DOC_TYPES,
        top_k=4,
    )
    state['knowledge'] = [
        {'title': r.title, 'content': r.content, 'doc_type': r.doc_type}
        for r in results
    ]
    return state


def _knowledge_text(state: TriageState, limit: int = 300) -> str:
    items = state.get('knowledge') or []
    if not items:
        return 'None available.'
    return '\n'.join(f"- {k['title']}: {k['content'][:limit]}" for k in items)


def triage_node(state: TriageState) -> TriageState:
    import json
    llm = get_llm(temperature=0.1)
    from langchain_core.messages import SystemMessage, HumanMessage
    result = llm.invoke([
        SystemMessage(content=TRIAGE_SYSTEM_PROMPT),
        HumanMessage(content=(
            f"Reference medical knowledge:\n{_knowledge_text(state)}\n\n"
            f"Patient symptoms: {state['symptoms']}"
        )),
    ])
    try:
        data = json.loads(result.content)
        state['severity'] = data.get('severity', 'medium')
        state['department'] = data.get('department', 'General Practice')
    except (json.JSONDecodeError, AttributeError):
        state['severity'] = 'medium'
        state['department'] = 'General Practice'
    return state


def rag_lookup_node(state: TriageState) -> TriageState:
    from apps.rag.ingest import semantic_search
    query = f"{state['department']} doctor for {state['symptoms']}"
    results = semantic_search(query, doc_type='doctor_profile', top_k=3)
    state['rag_results'] = [
        {'title': r.title, 'content': r.content, 'metadata': r.metadata}
        for r in results
    ]
    return state


def respond_node(state: TriageState) -> TriageState:
    llm = get_llm(temperature=0.4)
    from langchain_core.messages import SystemMessage, HumanMessage

    doctors_text = '\n'.join(
        f"- {r['title']}: {r['content'][:200]}" for r in state['rag_results']
    ) or 'No specific doctors found; recommend General Practice.'

    prompt = (
        f"Patient symptoms: {state['symptoms']}\n"
        f"Severity: {state['severity']}, Department: {state['department']}\n"
        f"Reference knowledge:\n{_knowledge_text(state, limit=200)}\n"
        f"Available doctors:\n{doctors_text}"
    )
    result = llm.invoke([
        SystemMessage(content=RESPONSE_SYSTEM_PROMPT),
        HumanMessage(content=prompt),
    ])
    state['response'] = result.content
    return state


def build_triage_graph():
    graph = StateGraph(TriageState)
    graph.add_node('knowledge', knowledge_node)
    graph.add_node('triage', triage_node)
    graph.add_node('rag_lookup', rag_lookup_node)
    graph.add_node('respond', respond_node)
    graph.set_entry_point('knowledge')
    graph.add_edge('knowledge', 'triage')
    graph.add_edge('triage', 'rag_lookup')
    graph.add_edge('rag_lookup', 'respond')
    graph.add_edge('respond', END)
    return graph.compile()


_triage_graph = None


def run_triage(symptoms: str, patient_id: int) -> dict:
    global _triage_graph
    if _triage_graph is None:
        _triage_graph = build_triage_graph()

    result = _triage_graph.invoke({
        'symptoms': symptoms,
        'severity': '',
        'department': '',
        'knowledge': [],
        'rag_results': [],
        'response': '',
        'patient_id': patient_id,
    })
    return {
        'severity': result['severity'],
        'department': result['department'],
        'response': result['response'],
        'recommended_doctors': result['rag_results'],
        'knowledge_sources': [
            {'title': k['title'], 'doc_type': k['doc_type']}
            for k in result.get('knowledge', [])
        ],
    }
