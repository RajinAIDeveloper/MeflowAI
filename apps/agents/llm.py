"""
LLM factory: returns LangChain chat models so agents stay LLM-agnostic.

Two entry points:
  - get_llm()        → for plain TEXT generation (triage classify/respond).
                       Tries settings.AISHOP24H_MODELS in order and uses the first
                       returning NON-EMPTY text. A model that raises (402/403/404)
                       OR returns blank content (e.g. gemini-3-flash-preview emits
                       empty text + a phantom tool_call via this gateway) is skipped.
  - get_chat_model() → for TOOL-CALLING agents (booking ReAct agent). Returns a
                       single RAW chat model that supports .bind_tools(). No
                       empty-content guard/fallback wrapper — those break tool-call
                       turns (which legitimately have empty content) and aren't
                       bindable by create_react_agent.

Provider precedence (both): AIShop24H > OPENAI_API_KEY > Ollama.

Note: this only covers generation. Embeddings for RAG/pgvector come from the
local bge model in apps/rag/embeddings.py, regardless of provider here.
"""
import time

from django.conf import settings

# Status codes the AIShop24H gateway returns spuriously on otherwise-valid calls.
_RETRY_STATUSES = {401, 402, 408, 409, 429, 500, 502, 503, 504}
_http_client = None


def _retrying_http_client():
    """A shared httpx client whose transport retries the gateway's bogus
    401/402/5xx responses at the HTTP layer — so a single flaky call is retried
    in place (no re-running of agent tools, no double-booking risk)."""
    global _http_client
    if _http_client is None:
        import httpx

        class _RetryTransport(httpx.HTTPTransport):
            def __init__(self, retries=8, backoff=0.4, **kw):
                super().__init__(**kw)
                self._retries, self._backoff = retries, backoff

            def handle_request(self, request):
                attempt = 0
                while True:
                    response = super().handle_request(request)
                    if response.status_code not in _RETRY_STATUSES or attempt >= self._retries:
                        return response
                    response.read()
                    response.close()
                    time.sleep(min(self._backoff * (2 ** attempt), 5.0))
                    attempt += 1

        _http_client = httpx.Client(transport=_RetryTransport(retries=8), timeout=90.0)
    return _http_client


def _require_nonempty(message):
    """Raise so .with_fallbacks() advances when a model returns blank text."""
    if not (getattr(message, 'content', '') or '').strip():
        raise ValueError('LLM returned empty content')
    return message


def _aishop_model(name, temperature):
    """A single raw ChatOpenAI pointed at the AIShop24H gateway (with HTTP retries)."""
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(
        model=name,
        temperature=temperature,
        api_key=settings.AISHOP24H_API_KEY,
        base_url=settings.AISHOP24H_BASE_URL,
        max_retries=1,
        http_client=_retrying_http_client(),
    )


def get_chat_model(temperature: float = 0.2):
    """Raw chat model for tool-calling agents (must support .bind_tools())."""
    if settings.AISHOP24H_API_KEY and settings.AISHOP24H_MODELS:
        return _aishop_model(settings.AISHOP24H_MODELS[0], temperature)

    if settings.OPENAI_API_KEY:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model='gpt-4o-mini', temperature=temperature,
                          api_key=settings.OPENAI_API_KEY)

    from langchain_ollama import ChatOllama
    return ChatOllama(model=settings.OLLAMA_MODEL, base_url=settings.OLLAMA_BASE_URL,
                      temperature=temperature)


def get_llm(temperature: float = 0.2):
    """Text-generation model: ordered fallback that skips empty/erroring models."""
    if settings.AISHOP24H_API_KEY and settings.AISHOP24H_MODELS:
        from langchain_core.runnables import RunnableLambda

        def _guarded(name):
            # Retry each model a few times — the AIShop24H gateway intermittently
            # returns bogus 401/402 "unknown_error" responses on otherwise-valid
            # calls; retrying absorbs those. The empty-content guard also triggers
            # a retry (and then the next model) for blank replies.
            return (
                _aishop_model(name, temperature) | RunnableLambda(_require_nonempty)
            ).with_retry(stop_after_attempt=4, wait_exponential_jitter=True)

        models = settings.AISHOP24H_MODELS
        chain = _guarded(models[0])
        if len(models) > 1:
            chain = chain.with_fallbacks([_guarded(m) for m in models[1:]])
        return chain

    return get_chat_model(temperature)
