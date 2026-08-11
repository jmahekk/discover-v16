"""Every call to the Groq LLM goes through here, with automatic fallback
across multiple keys and models when one hits its rate limit."""

import os
import re
import time
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

DEFAULT_MODELS = [
    "llama-3.1-8b-instant",
    "llama-3.3-70b-versatile",
    "qwen/qwen3-32b",
    "meta-llama/llama-4-scout-17b-16e-instruct",
    "openai/gpt-oss-20b",
    "openai/gpt-oss-120b",
]


def _load_api_configs():
    configs = []
    for env_name in ("GROQ_API_KEY", "GROQ_API_KEY_2", "GROQ_API_KEY_3"):
        key = os.environ.get(env_name)
        if key:
            configs.append({"key": key, "models": list(DEFAULT_MODELS)})
    if not configs:
        raise RuntimeError("No Groq API key found. Set GROQ_API_KEY in your .env file.")
    return configs


API_CONFIGS = _load_api_configs()

current_key_idx = 0
current_model_idx = 0


def get_client():
    return Groq(api_key=API_CONFIGS[current_key_idx]["key"])


def call_llm(prompt):
    global current_key_idx, current_model_idx

    while current_key_idx < len(API_CONFIGS):
        key_config = API_CONFIGS[current_key_idx]
        models = key_config["models"]

        while current_model_idx < len(models):
            model = models[current_model_idx]
            client = Groq(api_key=key_config["key"])

            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}]
                )
                return response.choices[0].message.content

            except Exception as e:
                error_msg = str(e)
                if "rate_limit_exceeded" in error_msg or "429" in error_msg:
                    print(f"  Rate limit hit on key={current_key_idx + 1} model='{model}'. Trying next model...")
                    current_model_idx += 1
                else:
                    raise

        print(f"  All models exhausted for key {current_key_idx + 1}. Switching to next key...")
        current_key_idx += 1
        current_model_idx = 0

    raise Exception("All keys and models exhausted for today. Wait 24 hours for reset.")


def call_llm_stream(prompt):
    global current_key_idx, current_model_idx

    while current_key_idx < len(API_CONFIGS):
        key_config = API_CONFIGS[current_key_idx]
        models = key_config["models"]

        while current_model_idx < len(models):
            model = models[current_model_idx]
            client = Groq(api_key=key_config["key"])

            try:
                stream = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    stream=True,
                )
                for chunk in stream:
                    delta = chunk.choices[0].delta.content
                    if delta:
                        yield delta
                return

            except Exception as e:
                error_msg = str(e)
                if "rate_limit_exceeded" in error_msg or "429" in error_msg:
                    print(f"  Rate limit hit on key={current_key_idx + 1} model='{model}'. Trying next model...")
                    current_model_idx += 1
                else:
                    raise

        print(f"  All models exhausted for key {current_key_idx + 1}. Switching to next key...")
        current_key_idx += 1
        current_model_idx = 0

    raise Exception("All keys and models exhausted for today. Wait 24 hours for reset.")


def build_prompt(data):
    return f"""
Title:
{data.get("title", "")}

Abstract:
{data.get("abstract", "")[:1200]}

Introduction:
{data.get("introduction", "")[:1500]}

Conclusion:
{data.get("conclusion", "")[:1000]}

Limitations:
{data.get("limitations", "")[:800]}

Tasks:
1. Generate 5-8 concise academic keywords.
2. Write a 2-3 sentence novelty statement.
3. Assign a SPECIFIC research category (NOT broad fields like AI/ML/NLP).

Rules:
- Category must be narrow and domain-specific.
- Examples:
  - "Multilingual Benchmarking of LLMs"
  - "Cross-cultural NLP"
  - "Vision-Language Reasoning"
  - "LLM Safety and Bias Evaluation"
- Avoid generic labels like Artificial Intelligence, Machine Learning, NLP.

Format:

Keywords:
- ...

Novelty:
...

Category:
...
"""


def clean_text(text):
    return text.replace("*", "").strip()


def parse_output(text):
    text = clean_text(text)

    keywords = []
    novelty = ""
    category = ""

    kw = re.search(r"Keywords:(.*?)(?=\n\n|\nNovelty:)", text, re.DOTALL)
    if kw:
        keywords = [
            clean_text(x.strip("- ").strip())
            for x in kw.group(1).split("\n")
            if x.strip()
        ]

    nov = re.search(r"Novelty:(.*?)(?=\n\n|\nCategory:)", text, re.DOTALL)
    if nov:
        novelty = clean_text(nov.group(1).strip())

    cat = re.search(r"Category:(.*)", text, re.DOTALL)
    if cat:
        category = clean_text(cat.group(1).strip())

    return keywords, novelty, category


def process_llm(data):
    prompt = build_prompt(data)

    print("  Running LLM...")
    start = time.time()

    output = call_llm(prompt)

    duration = round(time.time() - start, 2)
    keywords, novelty, category = parse_output(output)

    return {
        "groq_keywords": ", ".join(keywords),
        "groq_novelty": novelty,
        "groq_category": category,
        "groq_time_sec": duration
    }


def generate_limitations(data):
    prompt = f"""
Given a research paper:

Title:
{data.get("title", "")}

Abstract:
{data.get("abstract", "")[:1200]}

Introduction:
{data.get("introduction", "")[:1500]}

Conclusion:
{data.get("conclusion", "")[:1000]}

Task:
If limitations are not explicitly provided, infer and generate 2-3 realistic limitations of the work.

Rules:
- Be logical and grounded
- Do NOT hallucinate unrealistic claims
- Be concise

Format:
Limitations:
- ...
- ...
"""

    response = call_llm(prompt)
    response = response.replace("*", "")

    match = re.search(r"Limitations:(.*)", response, re.DOTALL)
    if match:
        return match.group(1).strip()

    return ""
