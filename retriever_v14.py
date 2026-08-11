"""The two-step search: a fast BM25 pass over all papers, then a ColBERT
re-rank of the shortlist using precomputed document embeddings."""

import json
import os
import re
import time

import numpy as np
from rank_bm25 import BM25Okapi
from fastembed import LateInteractionTextEmbedding

from config_v14 import COLBERT_CACHE_FILE, COLBERT_META_FILE


def tokenize(text: str) -> list[str]:
    """Lowercase and split into word tokens for BM25."""
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return text.split()


def build_document_text(paper: dict) -> str:
    """
    Concatenate all relevant fields into one string for BM25 indexing.
    Fields are weighted by importance via repetition: title x3, keywords x2,
    abstract x2, rest x1.
    """
    parts = [
        (paper.get("title", "") + " ") * 3,
        (paper.get("keywords", "") + " ") * 2,
        (paper.get("abstract", "") + " ") * 2,
        paper.get("introduction", ""),
        paper.get("conclusion", ""),
        paper.get("limitations", ""),
        paper.get("novelty", ""),
        paper.get("category", ""),
    ]
    return " ".join(p for p in parts if p)


def build_colbert_text(paper: dict) -> str:
    """Focused text used for ColBERT re-ranking."""
    return " ".join([
        paper.get("title", "") or "",
        paper.get("abstract", "") or "",
        paper.get("conclusion", "") or "",
        paper.get("keywords", "") or "",
    ])


class BM25Retriever:
    def __init__(self, papers: list[dict]):
        self.papers = papers
        print("Building BM25 index over all papers (one time)...")
        corpus = [tokenize(build_document_text(p)) for p in papers]
        self.bm25 = BM25Okapi(corpus)
        print(f"BM25 index ready ({len(papers)} papers)")

    def retrieve(self, query: str, top_k: int = 100,
                 allowed_categories: set | None = None) -> list[dict]:
        """
        Score all papers, then mask out papers whose broad_category is not
        in allowed_categories (None means no filter). Masking after scoring
        is cheap and avoids rebuilding the index per category.
        """
        tokens = tokenize(query)
        scores = np.array(self.bm25.get_scores(tokens))

        if allowed_categories is not None:
            mask = np.array([
                (p.get("broad_category") in allowed_categories)
                for p in self.papers
            ])
            scores = np.where(mask, scores, -np.inf)

        k = min(top_k, len(scores))
        top_idx = np.argpartition(-scores, k - 1)[:k]
        top_idx = top_idx[np.argsort(-scores[top_idx])]

        results = [
            {"index": int(i), "paper": self.papers[i],
             "bm25_score": float(scores[i])}
            for i in top_idx
            if scores[i] > 0
        ]

        if len(results) < 10:
            results = [
                {"index": int(i), "paper": self.papers[i],
                 "bm25_score": float(max(scores[i], 0.0))}
                for i in top_idx[:10]
                if scores[i] != -np.inf
            ]

        return results


class ColBERTReranker:
    def __init__(self, papers: list[dict], paper_ids: list | None = None):
        """
        papers: full paper list, same order as BM25Retriever.
        paper_ids: DB ids in the same order, used to validate the
        precomputed cache against the current paper set.
        """
        print("Loading ColBERT model (first run downloads ~500MB)...")
        self.model = LateInteractionTextEmbedding("colbert-ir/colbertv2.0")
        print("ColBERT model loaded")

        self.papers = papers
        self.doc_cache = None
        self._try_load_cache(paper_ids)

    def _try_load_cache(self, paper_ids):
        """Load precomputed document embeddings if present and valid."""
        if not (os.path.exists(COLBERT_CACHE_FILE) and os.path.exists(COLBERT_META_FILE)):
            print("No ColBERT cache found, documents will be encoded per query.")
            print("(Run precompute_colbert.py once to make re-ranking much faster.)")
            return
        try:
            with open(COLBERT_META_FILE, encoding="utf-8") as f:
                meta = json.load(f)
            if paper_ids is not None and meta.get("paper_ids") != list(paper_ids):
                print("ColBERT cache is stale (paper set changed), ignoring it.")
                print("Re-run precompute_colbert.py to refresh.")
                return
            cache = np.load(COLBERT_CACHE_FILE, allow_pickle=True)
            self.doc_cache = list(cache)
            print(f"ColBERT cache loaded ({len(self.doc_cache)} papers), fast re-ranking on")
        except Exception as e:
            print(f"Could not load ColBERT cache ({e}), falling back to on-the-fly encoding.")

    @staticmethod
    def _maxsim_score(query_vecs: np.ndarray, doc_vecs: np.ndarray) -> float:
        """
        Core ColBERT scoring, MaxSim:
          score(q, d) = sum_i max_j (q_i . d_j)
        """
        dot_products = np.dot(query_vecs, doc_vecs.T)
        return float(dot_products.max(axis=1).sum())

    def rerank(self, query: str, candidates: list[dict], top_k: int = 7) -> list[dict]:
        if not candidates:
            return []

        query_vecs = np.array(list(self.model.query_embed([query]))[0],
                              dtype=np.float32)

        if self.doc_cache is not None:
            doc_embeddings = [
                np.asarray(self.doc_cache[c["index"]], dtype=np.float32)
                for c in candidates
            ]
        else:
            doc_texts = [build_colbert_text(c["paper"]) for c in candidates]
            doc_embeddings = [
                np.array(e, dtype=np.float32)
                for e in self.model.passage_embed(doc_texts)
            ]

        scored = []
        for c, doc_vecs in zip(candidates, doc_embeddings):
            scored.append({
                "paper": c["paper"],
                "bm25_score": c["bm25_score"],
                "colbert_score": self._maxsim_score(query_vecs, doc_vecs),
            })

        scored.sort(key=lambda x: x["colbert_score"], reverse=True)
        return scored[:top_k]


class TwoStepRetriever:
    def __init__(self, papers: list[dict], paper_ids: list | None = None):
        """Built once over all papers. Category filtering happens per query."""
        self.bm25 = BM25Retriever(papers)
        self.colbert = ColBERTReranker(papers, paper_ids)

    def search(self, query: str, bm25_top_k: int = 100, final_top_k: int = 7,
               allowed_categories: list | None = None):
        """
        Full two-step search with optional category restriction.

        Returns:
            step1_results: list of {paper, bm25_score}
            step2_results: list of {paper, bm25_score, colbert_score}
            timings: {"bm25_ms": ..., "colbert_ms": ...}
        """
        allowed = set(allowed_categories) if allowed_categories else None

        t0 = time.perf_counter()
        step1 = self.bm25.retrieve(query, top_k=bm25_top_k,
                                   allowed_categories=allowed)
        t1 = time.perf_counter()

        step2 = self.colbert.rerank(query, step1, top_k=final_top_k)
        t2 = time.perf_counter()

        timings = {
            "bm25_ms": (t1 - t0) * 1000,
            "colbert_ms": (t2 - t1) * 1000,
        }
        return step1, step2, timings
