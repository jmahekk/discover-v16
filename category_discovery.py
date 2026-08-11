"""
Phase 1 of building the broad categories: samples papers, embeds and
clusters them, then asks the LLM to name each cluster. One-time offline job.
"""

import json
import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sentence_transformers import SentenceTransformer
import pymysql

from db_config import get_connection
from llm_module import call_llm
from config_v14 import (
    EMBEDDING_MODEL,
    N_CLUSTERS_MIN,
    N_CLUSTERS_MAX,
    SAMPLE_PER_SOURCE,
    BROAD_CATEGORIES_FILE,
)


def fetch_sample_papers():
    """
    Fetch a large random sample from the DB using ORDER BY RAND() to get
    a representative cross-section of all conference types.
    Returns a list of dicts: id, title, abstract, keywords, category.
    """
    conn   = get_connection()
    cursor = conn.cursor()

    limit = SAMPLE_PER_SOURCE * 7

    cursor.execute("""
        SELECT id, title, abstract, keywords, category
        FROM papers
        ORDER BY RAND()
        LIMIT %s
    """, (limit,))

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

    print(f"Fetched {len(papers)} sample papers from DB")
    return papers


def build_embed_text(paper: dict) -> str:
    """Combine paper fields into one string for embedding. Title is repeated to give it more weight."""
    return (
        f"{paper['title']}. {paper['title']}. "
        f"{paper['keywords']}. {paper['category']}. "
        f"{paper['abstract']}"
    )


def embed_papers(papers: list, model: SentenceTransformer) -> np.ndarray:
    texts = [build_embed_text(p) for p in papers]
    print(f"Embedding {len(texts)} papers with {EMBEDDING_MODEL}...")
    embeddings = model.encode(texts, batch_size=64, show_progress_bar=True)
    return embeddings


def find_best_k(embeddings: np.ndarray) -> int:
    """
    Try k from N_CLUSTERS_MIN to N_CLUSTERS_MAX and pick the k with the
    highest silhouette score (how well-separated the clusters are, -1 to +1,
    higher is better). Uses sample_size=500 for speed.
    """
    best_k     = N_CLUSTERS_MIN
    best_score = -1.0

    print(f"\nTesting k from {N_CLUSTERS_MIN} to {N_CLUSTERS_MAX}...")

    for k in range(N_CLUSTERS_MIN, N_CLUSTERS_MAX + 1):
        km     = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = km.fit_predict(embeddings)
        score  = silhouette_score(embeddings, labels, sample_size=500, random_state=42)
        print(f"   k={k:2d}  silhouette={score:.4f}")

        if score > best_score:
            best_score = score
            best_k     = k

    print(f"\nBest k = {best_k}  (silhouette = {best_score:.4f})")
    return best_k


def name_cluster(cluster_papers: list) -> tuple:
    """
    Send up to 20 papers from a cluster to the LLM and ask it to produce
    one broad category name plus a one-sentence description.
    Returns (name, description).
    """
    sample = cluster_papers[:20]

    paper_lines = "\n".join([
        f"- Title: {p['title']}\n  Keywords: {p['keywords']}\n  Old category: {p['category']}"
        for p in sample
    ])

    prompt = f"""Below are research papers from the same cluster. Analyse their topics carefully.

Papers:
{paper_lines}

Your task:
Assign ONE broad academic category name that covers ALL these papers.

Rules:
- The category MUST be broad enough to cover all papers listed
- Use 2 to 5 words maximum
- Must be a real NLP/AI research area
- Good examples:
    Multilingual NLP
    Question Answering and Reading Comprehension
    Text Generation and Summarization
    Dialogue and Conversational AI
    Information Extraction and Knowledge Graphs
    LLM Alignment and Safety
    Vision and Language
    Low-Resource and Cross-Lingual NLP
    Evaluation and Benchmarking
    Sentiment and Opinion Mining
    Reasoning and Commonsense NLP
    Machine Translation
    Efficient NLP and Model Compression
- Bad examples (too broad): Artificial Intelligence, NLP, Machine Learning, Deep Learning

Respond ONLY in this format and nothing else:
Category Name: <name>
Description: <one sentence describing what this category covers>
"""

    response = call_llm(prompt)

    name        = ""
    description = ""

    for line in response.strip().split("\n"):
        if line.startswith("Category Name:"):
            name = line.replace("Category Name:", "").strip()
        elif line.startswith("Description:"):
            description = line.replace("Description:", "").strip()

    return name, description


def discover_categories():
    """Full pipeline: sample, embed, cluster, name clusters, save broad_categories.json."""

    papers     = fetch_sample_papers()
    model      = SentenceTransformer(EMBEDDING_MODEL)
    embeddings = embed_papers(papers, model)

    best_k = find_best_k(embeddings)

    print(f"\nRunning final KMeans with k={best_k}...")
    km     = KMeans(n_clusters=best_k, random_state=42, n_init=10)
    labels = km.fit_predict(embeddings)

    clusters: dict = {}
    for i, label in enumerate(labels):
        clusters.setdefault(int(label), []).append(papers[i])

    broad_categories = []

    for cluster_id, cluster_papers in clusters.items():
        print(f"\nNaming cluster {cluster_id}  ({len(cluster_papers)} papers)...")
        name, description = name_cluster(cluster_papers)
        centroid          = km.cluster_centers_[cluster_id].tolist()

        broad_categories.append({
            "id":           cluster_id,
            "name":         name,
            "description":  description,
            "centroid":     centroid,
            "sample_count": len(cluster_papers),
        })

        print(f"   -> {name}")

    with open(BROAD_CATEGORIES_FILE, "w", encoding="utf-8") as f:
        json.dump(broad_categories, f, indent=2, ensure_ascii=False)

    print(f"\nDiscovered {len(broad_categories)} broad categories")
    print(f"   Saved to {BROAD_CATEGORIES_FILE}")

    print("\nCategories discovered:")
    for bc in broad_categories:
        print(f"  [{bc['id']:2d}] {bc['name']}  ({bc['sample_count']} sample papers)")

    return broad_categories


if __name__ == "__main__":
    discover_categories()
