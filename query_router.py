"""Decides which broad category (or categories) a question belongs to,
by comparing it against every category's centroid and description."""

import json
import time
from dataclasses import dataclass, field

import numpy as np
from sentence_transformers import SentenceTransformer

from config_v14 import (
    EMBEDDING_MODEL,
    BROAD_CATEGORIES_FILE,
    ROUTER_CENTROID_WEIGHT,
    ROUTER_DESC_WEIGHT,
    ROUTER_MIN_SCORE,
    ROUTER_MARGIN,
    ROUTER_MAX_CATEGORIES,
)


@dataclass
class RouteResult:
    """Everything the frontend needs to explain the routing decision."""
    categories: list
    mode: str
    confidence: str
    scores: list = field(default_factory=list)
    elapsed_ms: float = 0.0


def _normalize(matrix: np.ndarray) -> np.ndarray:
    """L2-normalise rows so a dot product equals cosine similarity."""
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return matrix / norms


class QueryRouter:
    def __init__(self, categories_file: str = BROAD_CATEGORIES_FILE,
                 model: SentenceTransformer | None = None):
        """
        A model can be passed in so the app shares one SentenceTransformer
        instance across the router and other components, saving memory
        and a second model load at startup.
        """
        with open(categories_file, encoding="utf-8") as f:
            cats = json.load(f)

        self.names        = [c["name"] for c in cats]
        self.descriptions = [c.get("description", "") for c in cats]

        self.centroids = _normalize(np.array([c["centroid"] for c in cats],
                                             dtype=np.float32))

        self.model = model or SentenceTransformer(EMBEDDING_MODEL)

        desc_texts = [f"{n}. {d}" for n, d in zip(self.names, self.descriptions)]
        self.desc_embs = _normalize(
            np.array(self.model.encode(desc_texts), dtype=np.float32)
        )

    def route(self, query: str) -> RouteResult:
        """Decide which broad categories the query should be searched in."""
        t0 = time.perf_counter()

        q = np.array(self.model.encode([query]), dtype=np.float32)
        q = _normalize(q)[0]

        centroid_sims = self.centroids @ q
        desc_sims     = self.desc_embs @ q

        blended = (ROUTER_CENTROID_WEIGHT * centroid_sims
                   + ROUTER_DESC_WEIGHT * desc_sims)

        order  = np.argsort(blended)[::-1]
        scores = [(self.names[i], float(blended[i])) for i in order]
        best   = scores[0][1]

        elapsed_ms = (time.perf_counter() - t0) * 1000

        if best < ROUTER_MIN_SCORE:
            return RouteResult(
                categories=list(self.names),
                mode="all",
                confidence="low",
                scores=scores,
                elapsed_ms=elapsed_ms,
            )

        selected = [name for name, s in scores if s >= best - ROUTER_MARGIN]
        selected = selected[:ROUTER_MAX_CATEGORIES]

        if len(selected) == 1:
            runner_up_gap = best - scores[1][1] if len(scores) > 1 else 1.0
            confidence = "high" if runner_up_gap >= ROUTER_MARGIN * 2 else "medium"
            mode = "single"
        else:
            confidence = "medium"
            mode = "multi"

        return RouteResult(
            categories=selected,
            mode=mode,
            confidence=confidence,
            scores=scores,
            elapsed_ms=elapsed_ms,
        )


if __name__ == "__main__":
    router = QueryRouter()

    test_queries = [
        "What defenses exist against jailbreak and prompt injection attacks?",
        "How can we compress large language models for edge devices?",
        "Which datasets exist for visual question answering?",
        "What methods are used for low-resource machine translation?",
        "chain of thought reasoning evaluation benchmarks",
        "hello there",
    ]

    for tq in test_queries:
        r = router.route(tq)
        print(f"\nQ: {tq}")
        print(f"   mode={r.mode}  confidence={r.confidence}  ({r.elapsed_ms:.0f} ms)")
        for name, s in r.scores[:4]:
            marker = ">>" if name in r.categories else "  "
            print(f"   {marker} {s:.3f}  {name}")
