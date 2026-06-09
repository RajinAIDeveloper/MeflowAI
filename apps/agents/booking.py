"""
Booking agent: conversational agent with tool-calling for appointment management.

Uses LangGraph's prebuilt ReAct agent with the 4 booking tools:
search_doctors, check_schedule, create_booking, cancel_booking.

The agent maintains a simple message history per session (stored in PatientMemory
or passed in from the caller for stateless API usage).
"""
from langgraph.prebuilt import create_react_agent

from .llm import get_chat_model
from .tools import make_patient_tools

BOOKING_SYSTEM_PROMPT = """You are MediFlow, an AI appointment assistant.
The patient is already signed in and identified — NEVER ask for a patient ID or
account number; the tools already act on their behalf.

Help the patient book, reschedule, cancel, or list appointments using the tools.

Guidelines:
- The current date is provided in the conversation context. NEVER ask the patient
  what today's date is — compute "today", "tomorrow", "next Monday", etc. yourself
  and pass concrete YYYY-MM-DD dates to the tools.
- For questions about the patient's own/upcoming/existing appointments, call
  list_my_appointments — do NOT give generic advice or talk about emergencies.
- When searching for doctors, use the specialty mentioned by the patient.
- search_doctors returns an `accepting_new` flag per doctor. If matches come back
  but all have accepting_new=false, DO NOT say there are no doctors — name the
  doctor(s) and explain they're in that specialty but not currently accepting new
  appointments, then offer related specialties or to try another doctor.
- Before booking, confirm the doctor, date, and time with the patient.
- NEVER guess a doctor_id. Right before calling create_booking, call
  search_doctors in THIS turn to get the doctor's real id (the earlier
  conversation does not carry tool results forward). Then call
  create_booking(doctor_id, scheduled_at, reason, appointment_type) with
  scheduled_at as ISO-8601 (e.g. 2026-06-08T09:30:00). If create_booking returns
  an error about an unknown id, search again and retry with the correct id.
- To cancel, find the appointment via list_my_appointments, then call
  cancel_booking(appointment_id).
- Never invent doctor names, times, or availability — use the tools.
- If no slots are available, suggest the next working day.
- Be concise and friendly. Format replies in clear Markdown (short paragraphs,
  bold for key details, bullet lists for options)."""


def _build_agent(patient_id: int):
    llm = get_chat_model(temperature=0.2)
    # LangGraph 1.x: the system prompt arg is `prompt` (was `state_modifier`).
    return create_react_agent(
        model=llm,
        tools=make_patient_tools(patient_id),
        prompt=BOOKING_SYSTEM_PROMPT,
    )


# Cache one agent per patient (tools are bound to the patient id).
_agents_by_patient = {}


def _get_booking_agent(patient_id: int):
    agent = _agents_by_patient.get(patient_id)
    if agent is None:
        agent = _build_agent(patient_id)
        _agents_by_patient[patient_id] = agent
    return agent


def run_booking_turn(message: str, history: list, patient_id: int) -> dict:
    """
    Run one turn of the booking conversation.

    Args:
        message: patient's latest message
        history: list of {role: 'user'|'assistant', content: str}
        patient_id: used by tools to associate bookings

    Returns:
        {response: str, updated_history: list}
    """
    agent = _get_booking_agent(patient_id)

    import time
    from django.utils import timezone
    from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

    # Give the agent the current date so it can resolve "today"/"tomorrow" itself.
    today = timezone.localdate()
    messages = [SystemMessage(content=(
        f"Current date: {today.isoformat()} ({today.strftime('%A')}). "
        f"Resolve relative dates from this; never ask the patient for the date."
    ))]
    for turn in history:
        if turn['role'] == 'user':
            messages.append(HumanMessage(content=turn['content']))
        else:
            messages.append(AIMessage(content=turn['content']))
    messages.append(HumanMessage(content=message))

    # The AIShop24H gateway intermittently returns bogus 401/402 errors; retry the
    # turn a few times so a transient blip doesn't surface as a chat failure.
    last_exc = None
    for attempt in range(3):
        try:
            result = agent.invoke({'messages': messages})
            break
        except Exception as exc:
            last_exc = exc
            time.sleep(1.0 * (attempt + 1))
    else:
        raise last_exc
    ai_response = result['messages'][-1].content

    updated_history = history + [
        {'role': 'user', 'content': message},
        {'role': 'assistant', 'content': ai_response},
    ]
    return {'response': ai_response, 'updated_history': updated_history}
