"""
Groq LLM generator for the RAG pipeline.

Uses ChatGroq with llama-3.1-8b-instant (fast, free-tier).
Accepts separate system/user messages for proper instruction-following.
"""

from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from config.settings import GROQ_API_KEY, GROQ_MODEL, LLM_TEMPERATURE, LLM_MAX_TOKENS


class GroqGenerator:
    """
    Groq LLM wrapper for answer generation.

    Why Groq?
    - LPU hardware: ~500 tokens/sec — 10-20x faster than GPU inference
    - Free tier with generous rate limits (6000 req/day on free plan)
    - First-class LangChain integration via langchain-groq
    - llama-3.1-8b-instant: best speed/quality for factual Q&A
    """

    def __init__(
        self,
        model: str = GROQ_MODEL,
        temperature: float = LLM_TEMPERATURE,
        max_tokens: int = LLM_MAX_TOKENS,
    ):
        """
        Initialize the Groq LLM.

        Args:
            model:       Groq model name. Default from settings (llama-3.1-8b-instant).
            temperature: Sampling temperature. Low (0.1-0.2) for factual Q&A.
            max_tokens:  Maximum tokens in the response.
        """
        if not GROQ_API_KEY:
            raise ValueError(
                "GROQ_API_KEY is not set. Add it to your .env file:\n"
                "  GROQ_API_KEY=gsk_..."
            )
        self.model_name = model
        self.llm = ChatGroq(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            groq_api_key=GROQ_API_KEY,
        )

    def generate(self, system_prompt: str, user_message: str) -> str:
        """
        Generate an answer from system + user messages.

        Args:
            system_prompt: The grounding instructions (from prompt_builder).
            user_message:  The context + question message (from prompt_builder).

        Returns:
            The LLM's answer as a plain string.
        """
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message),
        ]
        response = self.llm.invoke(messages)
        return response.content.strip()

    def generate_with_metadata(self, system_prompt: str, user_message: str) -> dict:
        """
        Generate an answer and return generation metadata.

        Returns:
            dict with:
              answer:        str  — the generated answer
              model:         str  — model name used
              input_tokens:  int  — tokens in prompt
              output_tokens: int  — tokens in response
        """
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message),
        ]
        response = self.llm.invoke(messages)
        usage    = getattr(response, "usage_metadata", {}) or {}

        return {
            "answer":        response.content.strip(),
            "model":         self.model_name,
            "input_tokens":  usage.get("input_tokens",  0),
            "output_tokens": usage.get("output_tokens", 0),
        }
