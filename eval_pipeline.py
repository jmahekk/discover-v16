"""
Runs a set of benchmark questions through the pipeline and measures
routing quality, retrieval quality, and per-stage latency.
"""

import json
import os
import time

from db_config import get_connection
from query_router import QueryRouter
from retriever_v14 import TwoStepRetriever

QUERIES_FILE = "eval_queries.txt"
REPORT_FILE  = "eval_report.json"
FINAL_K      = 7
BM25_K       = 100

DEFAULT_QUERIES = [
    "What defenses exist against jailbreak and prompt injection attacks on LLMs?",
    "How can large language models be compressed or distilled for faster inference?",
    "Which benchmarks evaluate chain-of-thought reasoning in language models?",
    "What methods improve machine translation for low-resource languages?",
    "How do vision-language models handle visual question answering?",
    "What techniques reduce hallucination in retrieval-augmented generation?",
    "How is bias measured and mitigated in multilingual language models?",
    "What approaches exist for dialogue state tracking in conversational AI?",
]


def load_papers():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, title, authors, abstract, introduction,
               limitations, conclusion, publication,
               refs, keywords, novelty, category, broad_category
        FROM papers ORDER BY id
    """)
    cols = ["id", "title", "authors", "abstract", "introduction",
            "limitations", "conclusion", "publication",
            "references", "keywords", "novelty", "category", "broad_category"]
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return [dict(zip(cols, row)) for row in rows]


def main():
    if os.path.exists(QUERIES_FILE):
        with open(QUERIES_FILE, encoding="utf-8") as f:
            queries = [q.strip() for q in f if q.strip()]
        print(f"Loaded {len(queries)} queries from {QUERIES_FILE}")
    else:
        queries = DEFAULT_QUERIES
        print(f"Using {len(queries)} built-in benchmark queries "
              f"(create {QUERIES_FILE} to use your own)")

    papers = load_papers()
    print(f"Loaded {len(papers)} papers from DB")

    retriever = TwoStepRetriever(papers, paper_ids=[p["id"] for p in papers])
    router = QueryRouter()

    results = []
    for qi, query in enumerate(queries, 1):
        print(f"\n[{qi}/{len(queries)}] {query}")

        route = router.route(query)
        routed_cats = set(route.categories)
        print(f"   routed -> {route.mode} ({route.confidence}): "
              f"{', '.join(list(routed_cats)[:3])}")

        t0 = time.perf_counter()
        _, top_all, tim_all = retriever.search(query, BM25_K, FINAL_K,
                                               allowed_categories=None)
        t_all = time.perf_counter() - t0

        allowed = None if route.mode == "all" else list(routed_cats)
        t0 = time.perf_counter()
        _, top_routed, tim_routed = retriever.search(query, BM25_K, FINAL_K,
                                                     allowed_categories=allowed)
        t_routed = time.perf_counter() - t0

        agreement = (sum(1 for it in top_all
                         if it["paper"].get("broad_category") in routed_cats)
                     / max(len(top_all), 1))

        all_titles    = {it["paper"].get("title") for it in top_all}
        routed_titles = {it["paper"].get("title") for it in top_routed}
        overlap = len(all_titles & routed_titles) / max(len(all_titles), 1)

        speedup = t_all / t_routed if t_routed > 0 else 1.0

        print(f"   agreement={agreement:.0%}  overlap={overlap:.0%}  "
              f"latency: all={t_all:.2f}s routed={t_routed:.2f}s "
              f"(x{speedup:.1f} faster)")

        results.append({
            "query": query,
            "route_mode": route.mode,
            "route_confidence": route.confidence,
            "routed_categories": list(routed_cats),
            "routing_ms": round(route.elapsed_ms, 1),
            "bm25_ms": round(tim_routed["bm25_ms"], 1),
            "colbert_ms": round(tim_routed["colbert_ms"], 1),
            "latency_unrestricted_s": round(t_all, 2),
            "latency_routed_s": round(t_routed, 2),
            "routing_agreement": round(agreement, 3),
            "topk_overlap": round(overlap, 3),
            "top_titles_routed": [it["paper"].get("title") for it in top_routed],
        })

    n = len(results)
    avg = lambda key: sum(r[key] for r in results) / max(n, 1)
    summary = {
        "queries": n,
        "avg_routing_agreement": round(avg("routing_agreement"), 3),
        "avg_topk_overlap": round(avg("topk_overlap"), 3),
        "avg_routing_ms": round(avg("routing_ms"), 1),
        "avg_bm25_ms": round(avg("bm25_ms"), 1),
        "avg_colbert_ms": round(avg("colbert_ms"), 1),
        "avg_latency_routed_s": round(avg("latency_routed_s"), 2),
        "avg_latency_unrestricted_s": round(avg("latency_unrestricted_s"), 2),
    }

    print("\n" + "=" * 64)
    print("SUMMARY")
    print("=" * 64)
    for k, v in summary.items():
        print(f"  {k:32s} {v}")
    print("\nInterpretation:")
    print("  routing_agreement close to 1.0 means the router picks the right categories")
    print("  topk_overlap close to 1.0 means category filtering loses no results")
    print("  latency_routed lower than latency_unrestricted means routing saves time")

    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "per_query": results}, f, indent=2)
    print(f"\nFull report saved to {REPORT_FILE}")


if __name__ == "__main__":
    main()
