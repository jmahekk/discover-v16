"""Builds the grounded, citation-instructed prompt and asks the LLM for an answer."""

from llm_module import call_llm
from context_builder import build_full_context, detect_intent


INTENT_INSTRUCTION_MAP = {
    "statistics":  "Focus on numbers, dataset sizes, sample counts, and statistics. Look carefully through abstracts and introductions.",
    "methodology": "Focus on how the methods, models, architectures and pipelines work.",
    "limitations": "Focus on limitations, drawbacks, and challenges mentioned across the papers.",
    "comparison":  "Focus on comparisons, baselines, and differences between approaches.",
    "languages":   "Focus on which languages, locales, or linguistic coverage is mentioned.",
    "results":     "Focus on evaluation results, scores, metrics, and performance numbers.",
    "use_case":    "Focus on what tasks, applications, or use cases the work supports.",
    "general":     "Provide a concise and accurate answer based on the papers.",
}


def build_llm_prompt(query: str, context: str, intent: str) -> str:
    instruction = INTENT_INSTRUCTION_MAP.get(intent, INTENT_INSTRUCTION_MAP["general"])

    return f"""You are a research assistant helping answer questions about academic papers.

User Question:
{query}

Instruction:
{instruction}
Answer ONLY using the context below. If the answer is not in the context, say "The available papers do not contain enough information to answer this question." Do NOT hallucinate.

Context from Retrieved Papers:
{context}

Answer:"""


def generate_answer(query: str, top_papers: list[dict]) -> dict:
    """
    Full answer generation pipeline.

    Args:
        query      : user's natural language question
        top_papers : Step 2 ColBERT results (list of dicts with 'paper' key)

    Returns:
        answer       : LLM generated answer
        intent       : detected query intent
        sources      : list of source paper titles
        context_used : context string sent to LLM (for debug)
    """
    if not top_papers:
        return {
            "answer": "No relevant papers were found for your query.",
            "intent": "general",
            "sources": [],
            "context_used": ""
        }

    context, intent = build_full_context(query, top_papers)
    prompt = build_llm_prompt(query, context, intent)
    answer = call_llm(prompt)

    sources = [item["paper"].get("title", "Untitled") for item in top_papers]

    return {
        "answer": answer.strip(),
        "intent": intent,
        "sources": sources,
        "context_used": context
    }


def prepare_prompt(query: str, top_papers: list[dict]) -> dict:
    """
    Builds everything needed for a streaming answer, without calling the
    LLM itself. The frontend streams the response via
    llm_module.call_llm_stream(prompt), showing text as it is generated.

    Returns:
        prompt       : full prompt string ready for the LLM
        intent       : detected query intent
        sources      : list of source paper titles
        context_used : context string sent to LLM (for debug)
    """
    if not top_papers:
        return {
            "prompt": "",
            "intent": "general",
            "sources": [],
            "context_used": ""
        }

    context, intent = build_full_context(query, top_papers)
    prompt = build_llm_prompt(query, context, intent)
    sources = [item["paper"].get("title", "Untitled") for item in top_papers]

    return {
        "prompt": prompt,
        "intent": intent,
        "sources": sources,
        "context_used": context
    }
