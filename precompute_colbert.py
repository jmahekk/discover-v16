"""
One-time script that encodes every paper for ColBERT ahead of time, so
re-ranking does not need to encode documents live on every query.
"""

import json
import time

import numpy as np
from fastembed import LateInteractionTextEmbedding

from db_config import get_connection
from retriever_v14 import build_colbert_text
from config_v14 import COLBERT_CACHE_FILE, COLBERT_META_FILE

BATCH_SIZE = 64

# Each worker process loads its own copy of the model (~600MB RAM each).
# 4 is a good default for a machine with 8GB+ RAM, 0 uses all CPU cores,
# 1 is single-process and safest on low-RAM machines.
PARALLEL_WORKERS = 4


def fetch_papers():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, title, abstract, conclusion, keywords
        FROM papers
        ORDER BY id
    """)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    papers = [
        {"id": r[0], "title": r[1] or "", "abstract": r[2] or "",
         "conclusion": r[3] or "", "keywords": r[4] or ""}
        for r in rows
    ]
    print(f"Fetched {len(papers)} papers")
    return papers


def main():
    papers = fetch_papers()
    texts = [build_colbert_text(p) for p in papers]

    print("Loading ColBERT model...")
    model = LateInteractionTextEmbedding("colbert-ir/colbertv2.0")

    print(f"Encoding {len(texts)} papers "
          f"({PARALLEL_WORKERS or 'all'} parallel workers, batches of {BATCH_SIZE})...")
    print("(First minute may look idle while worker processes load the model.)")
    start = time.time()

    all_embeddings = []
    done = 0
    for emb in model.passage_embed(texts, batch_size=BATCH_SIZE,
                                   parallel=PARALLEL_WORKERS):
        all_embeddings.append(np.array(emb, dtype=np.float16))
        done += 1
        if done % 256 == 0 or done == len(texts):
            elapsed = time.time() - start
            rate = done / elapsed if elapsed else 0
            eta = (len(texts) - done) / rate if rate else 0
            print(f"   {done}/{len(texts)}  ({rate:.1f} papers/s, ~{eta/60:.1f} min left)")

    arr = np.empty(len(all_embeddings), dtype=object)
    for i, e in enumerate(all_embeddings):
        arr[i] = e
    np.save(COLBERT_CACHE_FILE, arr, allow_pickle=True)

    with open(COLBERT_META_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "paper_ids": [p["id"] for p in papers],
            "model": "colbert-ir/colbertv2.0",
            "created_unix": time.time(),
        }, f)

    total_min = (time.time() - start) / 60
    print(f"\nDone in {total_min:.1f} min.")
    print(f"   Saved: {COLBERT_CACHE_FILE} + {COLBERT_META_FILE}")


if __name__ == "__main__":
    main()
