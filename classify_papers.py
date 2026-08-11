"""
Phase 2 of building the broad categories: assigns every paper to whichever
category centroid it is closest to, with an LLM fallback for weak matches.
"""

import json
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer

from db_config import get_connection
from llm_module import call_llm
from config_v14 import (
    EMBEDDING_MODEL,
    SIMILARITY_THRESHOLD,
    BROAD_CATEGORIES_FILE,
)


def fetch_all_papers() -> list:
    """Fetch all papers from the DB for classification."""
    conn   = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, title, abstract, keywords, category
        FROM papers
    """)

    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    papers = [
        {
            "id":       row[0],
            "title":    row[1] or "",
            "abstract": (row[2] or "")[:500],
            "keywords": row[3] or "",
            "category": row[4] or "",
        }
        for row in rows
    ]

    print(f"Fetched {len(papers)} papers for classification")
    return papers


def update_db(results: list):
    """Bulk-update broad_category in MySQL, committing every 500 rows."""
    conn   = get_connection()
    cursor = conn.cursor()

    print(f"\nWriting broad_category for {len(results)} papers to DB...")

    for i, r in enumerate(results):
        cursor.execute(
            "UPDATE papers SET broad_category = %s WHERE id = %s",
            (r["broad_category"], r["id"])
        )

        if (i + 1) % 500 == 0:
            conn.commit()
            print(f"   {i+1}/{len(results)} rows committed...")

    conn.commit()
    cursor.close()
    conn.close()
    print("DB update complete.")


def build_embed_text(paper: dict) -> str:
    """Same text construction used in category_discovery.py for consistency."""
    return (
        f"{paper['title']}. {paper['title']}. "
        f"{paper['keywords']}. {paper['category']}. "
        f"{paper['abstract']}"
    )


def llm_classify(paper: dict, category_names: list) -> str:
    """
    Called when cosine similarity is too low to be confident. Sends the
    paper to Groq and asks it to pick exactly one category from the list.
    Returns the matched category name.
    """
    cats_text = "\n".join(f"{i+1}. {n}" for i, n in enumerate(category_names))

    prompt = f"""Classify this research paper into exactly ONE of the categories below.

Title: {paper['title']}
Keywords: {paper['keywords']}
Abstract: {paper['abstract'][:400]}

Categories:
{cats_text}

Respond with ONLY the category name exactly as written above. No explanation.
"""

    response = call_llm(prompt).strip()
    response_lower = response.lower()

    for name in category_names:
        if name.lower() in response_lower or response_lower in name.lower():
            return name

    return category_names[0]


def classify_all_papers():
    """
    Full pipeline: load categories, embed all papers, assign by cosine
    similarity with LLM fallback for low confidence, then update the DB.
    """

    with open(BROAD_CATEGORIES_FILE, encoding="utf-8") as f:
        broad_categories = json.load(f)

    category_names = [bc["name"]    for bc in broad_categories]
    centroids      = np.array([bc["centroid"] for bc in broad_categories])

    print(f"Loaded {len(broad_categories)} broad categories from {BROAD_CATEGORIES_FILE}")

    model = SentenceTransformer(EMBEDDING_MODEL)

    papers = fetch_all_papers()

    texts      = [build_embed_text(p) for p in papers]
    print(f"Embedding {len(texts)} papers...")
    embeddings = model.encode(texts, batch_size=64, show_progress_bar=True)

    results           = []
    llm_fallback_count = 0

    for i, (paper, emb) in enumerate(zip(papers, embeddings)):
        sims      = cosine_similarity([emb], centroids)[0]
        best_idx  = int(np.argmax(sims))
        best_score = float(sims[best_idx])

        if best_score >= SIMILARITY_THRESHOLD:
            assigned = category_names[best_idx]
            method   = "embedding"
        else:
            assigned = llm_classify(paper, category_names)
            method   = "llm_fallback"
            llm_fallback_count += 1

        results.append({
            "id":             paper["id"],
            "broad_category": assigned,
            "confidence":     round(best_score, 4),
            "method":         method,
        })

        if (i + 1) % 500 == 0:
            print(f"   Classified {i+1}/{len(papers)}...  LLM fallbacks so far: {llm_fallback_count}")

    print(f"\nClassification done.")
    print(f"   Embedding assignments : {len(results) - llm_fallback_count}")
    print(f"   LLM fallbacks         : {llm_fallback_count}")

    update_db(results)

    print("\nBroad category distribution:")
    from collections import Counter
    dist = Counter(r["broad_category"] for r in results)
    for name, count in dist.most_common():
        print(f"  {count:5d}  {name}")


if __name__ == "__main__":
    classify_all_papers()
