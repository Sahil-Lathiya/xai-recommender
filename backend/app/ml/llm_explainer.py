"""
LLM Explainer — GPT-4o-mini via LangChain.

Design rules:
  1. Cache first — same product+reasons combo never calls OpenAI twice.
  2. Always returns a string — NEVER raises an exception to the caller.
  3. Silent fallback — if OpenAI fails for ANY reason, generate from templates.
  4. Token tracking — warns in logs when estimated usage exceeds 100 000 tokens.
"""
import hashlib
import logging
from typing import Optional

from app.core.config import settings
from app.ml.cache import embedding_cache

logger = logging.getLogger(__name__)

# ── Token / cost tracking (process-lifetime counters) ─────────────────────────
_total_tokens_estimated: int = 0
_total_llm_calls: int = 0
_TOKEN_WARNING_THRESHOLD: int = 100_000

# Rough pricing for gpt-4o-mini (input + output blended estimate)
_COST_PER_TOKEN_USD: float = 0.000_000_375  # ~$0.15/1M input + $0.60/1M output blended

# ── Prompts ───────────────────────────────────────────────────────────────────
_SYSTEM_PROMPT = (
    "You are a helpful, friendly shopping assistant. "
    "Explain AI recommendations in exactly 2 sentences. "
    "Be specific about product features. "
    "Say 'because you' not 'based on your data'."
)

_HUMAN_TEMPLATE = (
    "Product: {product_name} (£{price:.2f}, rated {rating}/5, "
    "{review_count:,} reviews). "
    "Top 3 recommendation reasons: {top_3_reasons}. "
    "User summary: {user_summary}. "
    "Write a friendly 2-sentence explanation."
)


def _make_cache_key(product_id: str, top_3_reasons: list[str]) -> str:
    raw = f"{product_id}:{'|'.join(sorted(top_3_reasons))}"
    return f"llm:{hashlib.md5(raw.encode()).hexdigest()}"


class LLMExplainer:
    """
    Singleton LLM explainer.
    The LangChain chain is initialised lazily on first use to keep
    startup time fast (model loading takes priority).
    """

    def __init__(self) -> None:
        self._chain = None

    # ── Lazy chain initialisation ───────────────────────────────────────────────

    def _get_chain(self):
        if self._chain is not None:
            return self._chain

        from langchain_core.output_parsers import StrOutputParser
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(
            model=settings.OPENAI_LLM_MODEL,
            api_key=settings.OPENAI_API_KEY,
            max_tokens=settings.OPENAI_MAX_TOKENS,
            temperature=0.4,
            request_timeout=10,
        )

        prompt = ChatPromptTemplate.from_messages([
            ("system", _SYSTEM_PROMPT),
            ("human", "{human_input}"),
        ])

        self._chain = prompt | llm | StrOutputParser()
        return self._chain

    # ── Public API ──────────────────────────────────────────────────────────────

    async def explain(
        self,
        product_name: str,
        price: float,
        rating: float,
        review_count: int,
        top_3_reasons: list[str],
        user_summary: str,
        product_id: Optional[str] = None,
    ) -> str:
        """
        Generate a 2-sentence natural-language explanation for a recommendation.

        Always returns a non-empty string.
        On any failure (network error, API down, rate limit, invalid key):
          → silently returns a template-generated fallback.
        """
        global _total_tokens_estimated, _total_llm_calls

        cache_key = _make_cache_key(
            str(product_id or product_name), top_3_reasons
        )
        cached = embedding_cache.get(cache_key)
        if cached is not None:
            return cached

        human_input = _HUMAN_TEMPLATE.format(
            product_name=product_name,
            price=price,
            rating=rating,
            review_count=review_count,
            top_3_reasons="; ".join(top_3_reasons),
            user_summary=user_summary,
        )

        try:
            chain = self._get_chain()
            raw_result = await chain.ainvoke({"human_input": human_input})
            explanation = str(raw_result).strip()

            if not explanation:
                raise ValueError("Empty response from LLM")

            # Estimate tokens (4 chars ≈ 1 token)
            prompt_chars = len(_SYSTEM_PROMPT) + len(human_input)
            completion_chars = len(explanation)
            estimated = (prompt_chars + completion_chars) // 4
            _total_tokens_estimated += estimated
            _total_llm_calls += 1

            if _total_tokens_estimated > _TOKEN_WARNING_THRESHOLD:
                logger.warning(
                    "LLM token usage warning: ~%d tokens used this session "
                    "(threshold: %d). Check OpenAI dashboard.",
                    _total_tokens_estimated,
                    _TOKEN_WARNING_THRESHOLD,
                )

            embedding_cache[cache_key] = explanation
            return explanation

        except Exception as exc:
            # Silent fallback — log the error, return template, never raise
            logger.warning(
                "LLM fallback triggered for '%s': %s",
                product_name,
                type(exc).__name__,
            )
            fallback = self._template_fallback(
                product_name=product_name,
                rating=rating,
                review_count=review_count,
                top_3_reasons=top_3_reasons,
            )
            # Cache the fallback too so the same failure isn't retried every time
            embedding_cache[cache_key] = fallback
            return fallback

    async def generate_user_summary(
        self,
        favourite_category: Optional[str],
        avg_rating: float,
        review_count: int,
    ) -> str:
        """
        Produce a one-line summary of the user's profile for the explanation prompt.
        No API call — deterministic from stats.
        """
        parts = []
        if favourite_category:
            parts.append(f"{favourite_category} enthusiast")
        if review_count > 50:
            parts.append("experienced reviewer")
        elif review_count > 10:
            parts.append("regular shopper")
        else:
            parts.append("new shopper")

        if avg_rating >= 4.0:
            parts.append("high standards")
        elif avg_rating <= 2.5:
            parts.append("selective taste")

        return ", ".join(parts) if parts else "general shopper"

    def get_usage_stats(self) -> dict:
        """Return token usage stats for the dashboard endpoint."""
        return {
            "total_tokens_estimated": _total_tokens_estimated,
            "total_calls": _total_llm_calls,
            "estimated_cost_usd": round(
                _total_tokens_estimated * _COST_PER_TOKEN_USD, 6
            ),
        }

    # ── Fallback generator ──────────────────────────────────────────────────────

    def _template_fallback(
        self,
        product_name: str,
        rating: float,
        review_count: int,
        top_3_reasons: list[str],
    ) -> str:
        """
        Generate a natural-sounding explanation from SHAP reasons alone.
        Caller cannot distinguish this from a real LLM response.
        """
        reason_1 = (
            top_3_reasons[0]
            if len(top_3_reasons) > 0
            else "your product preferences"
        )
        reason_2 = (
            top_3_reasons[1]
            if len(top_3_reasons) > 1
            else "its strong customer reviews"
        )

        sentences = [
            f"We recommend {product_name} because {reason_1}",
            f"and {reason_2}.",
            f"With a {rating:.1f}/5 rating from {review_count:,} verified buyers, "
            f"it's a strong match for your shopping profile.",
        ]

        # Two sentences: combine first two into one, third is the second sentence
        return f"{sentences[0]} {sentences[1]} {sentences[2]}"


# Module-level singleton — imported by route handlers
llm_explainer = LLMExplainer()
