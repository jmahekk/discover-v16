"""
FastAPI backend for DISCOVER. Loads the whole retrieval pipeline once at
startup and exposes it to the frontend as a set of web endpoints.
"""

import sys

for stream in (sys.stdout, sys.stderr):
    if stream and hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8", errors="replace")

import json
import time
from collections import Counter
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from db_config import get_connection
from query_router import QueryRouter
from retriever_v14 import TwoStepRetriever
from llm_answer import prepare_prompt, generate_answer
from llm_module import call_llm_stream

PAPER_COLS = [
    "id", "title", "authors", "abstract", "introduction",
    "limitations", "conclusion", "publication",
    "references", "keywords", "novelty", "category", "broad_category",
]


def load_papers() -> list[dict]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, title, authors, abstract, introduction,
               limitations, conclusion, publication,
               refs, keywords, novelty, category, broad_category
        FROM papers
        ORDER BY id
    """)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return [dict(zip(PAPER_COLS, row)) for row in rows]


print("Loading papers from database...")
PAPERS = load_papers()
PAPERS_BY_ID = {p["id"]: p for p in PAPERS}
print(f"{len(PAPERS)} papers loaded")

RETRIEVER = TwoStepRetriever(PAPERS, paper_ids=[p["id"] for p in PAPERS])
ROUTER = QueryRouter()

CATEGORY_COUNTS = Counter(p["broad_category"] for p in PAPERS if p.get("broad_category"))
VENUE_COUNTS = Counter(p["publication"] for p in PAPERS if p.get("publication"))

app = FastAPI(title="DISCOVER API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def paper_summary(p: dict) -> dict:
    """Compact paper representation for lists and cards."""
    return {
        "id": p["id"],
        "title": p.get("title") or "Untitled",
        "authors": (p.get("authors") or "")[:160],
        "publication": p.get("publication") or "",
        "broad_category": p.get("broad_category") or "",
        "category": p.get("category") or "",
        "abstract": (p.get("abstract") or "")[:600],
        "keywords": (p.get("keywords") or "")[:200],
    }


@app.get("/api/meta")
def meta():
    return {
        "total_papers": len(PAPERS),
        "categories": [
            {"name": name, "count": count}
            for name, count in CATEGORY_COUNTS.most_common()
        ],
        "venues": [
            {"name": name, "count": count}
            for name, count in VENUE_COUNTS.most_common()
        ],
        "colbert_cache": RETRIEVER.colbert.doc_cache is not None,
    }


class SearchRequest(BaseModel):
    query: str
    mode: str = "auto"
    categories: list[str] = []
    bm25_k: int = 100
    final_k: int = 7


@app.post("/api/search")
def search(req: SearchRequest):
    query = req.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query is empty.")

    routing = None
    allowed = None

    if req.mode == "auto":
        route = ROUTER.route(query)
        allowed = None if route.mode == "all" else route.categories
        routing = {
            "mode": route.mode,
            "confidence": route.confidence,
            "categories": route.categories,
            "scores": [{"name": n, "score": round(s, 4)} for n, s in route.scores],
            "elapsed_ms": round(route.elapsed_ms, 1),
        }
    elif req.mode == "manual" and req.categories:
        allowed = req.categories
        routing = {
            "mode": "manual",
            "confidence": "manual",
            "categories": req.categories,
            "scores": [],
            "elapsed_ms": 0.0,
        }
    else:
        routing = {
            "mode": "all", "confidence": "manual",
            "categories": [], "scores": [], "elapsed_ms": 0.0,
        }

    in_scope = (len(PAPERS) if not allowed
                else sum(1 for p in PAPERS if p.get("broad_category") in set(allowed)))

    step1, step2, timings = RETRIEVER.search(
        query,
        bm25_top_k=req.bm25_k,
        final_top_k=req.final_k,
        allowed_categories=allowed,
    )

    return {
        "routing": routing,
        "papers_in_scope": in_scope,
        "candidates": [
            {
                "id": it["paper"]["id"],
                "title": it["paper"].get("title") or "Untitled",
                "broad_category": it["paper"].get("broad_category") or "",
                "bm25": round(it["bm25_score"], 3),
            }
            for it in step1
        ],
        "results": [
            {
                **paper_summary(it["paper"]),
                "novelty": (it["paper"].get("novelty") or "")[:400],
                "bm25": round(it["bm25_score"], 3),
                "colbert": round(it["colbert_score"], 3),
            }
            for it in step2
        ],
        "timings": {
            "bm25_ms": round(timings["bm25_ms"], 1),
            "colbert_ms": round(timings["colbert_ms"], 1),
        },
    }


class AnswerRequest(BaseModel):
    query: str
    paper_ids: list[int]
    debug: bool = False


CITE_INSTRUCTION = (
    "When you state a fact taken from a specific paper, cite it inline "
    "with its number in square brackets, for example [1] or [2], matching "
    "the [Paper N] numbers in the context. Cite only papers from the context."
)


@app.post("/api/answer")
def answer(req: AnswerRequest):
    """
    Streams NDJSON lines:
      {"type": "meta", "intent": ..., "sources": [...]}
      {"type": "delta", "text": "..."}         (many of these)
      {"type": "done", "elapsed_ms": ..., "context": ...?}
    The frontend reads the stream with fetch() and renders text live.
    """
    top_papers = [
        {"paper": PAPERS_BY_ID[pid]}
        for pid in req.paper_ids
        if pid in PAPERS_BY_ID
    ]
    query = req.query.strip()

    prep = prepare_prompt(query, top_papers)
    if not prep["prompt"]:
        def empty():
            yield json.dumps({"type": "meta", "intent": "general", "sources": []}) + "\n"
            yield json.dumps({"type": "delta",
                              "text": "No relevant papers were found for this question."}) + "\n"
            yield json.dumps({"type": "done", "elapsed_ms": 0}) + "\n"
        return StreamingResponse(empty(), media_type="application/x-ndjson")

    head, _, tail = prep["prompt"].rpartition("Answer:")
    prompt = f"{head}{CITE_INSTRUCTION}\n\nAnswer:{tail}" if head else prep["prompt"]

    def stream():
        start = time.perf_counter()
        yield json.dumps({
            "type": "meta",
            "intent": prep["intent"],
            "sources": prep["sources"],
        }) + "\n"

        try:
            for chunk in call_llm_stream(prompt):
                yield json.dumps({"type": "delta", "text": chunk}) + "\n"
        except Exception as exc:
            try:
                result = generate_answer(query, top_papers)
                yield json.dumps({"type": "delta", "text": result["answer"]}) + "\n"
            except Exception:
                yield json.dumps({
                    "type": "delta",
                    "text": f"The language model could not be reached ({exc}). "
                            "Check your Groq API key and internet connection, then retry.",
                }) + "\n"

        done: dict = {"type": "done",
                      "elapsed_ms": round((time.perf_counter() - start) * 1000, 1)}
        if req.debug:
            done["context"] = prep["context_used"]
        yield json.dumps(done) + "\n"

    return StreamingResponse(stream(), media_type="application/x-ndjson")


@app.get("/api/papers")
def papers(category: str = "", venue: str = "", q: str = "",
           page: int = 1, page_size: int = 25):
    items = PAPERS
    if category:
        items = [p for p in items if p.get("broad_category") == category]
    if venue:
        items = [p for p in items if p.get("publication") == venue]
    if q:
        needle = q.lower()
        items = [p for p in items
                 if needle in (p.get("title") or "").lower()
                 or needle in (p.get("authors") or "").lower()
                 or needle in (p.get("keywords") or "").lower()]

    total = len(items)
    page = max(1, page)
    page_size = min(max(1, page_size), 100)
    start = (page - 1) * page_size
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "papers": [paper_summary(p) for p in items[start:start + page_size]],
    }


@app.get("/api/papers/{paper_id}")
def paper_detail(paper_id: int):
    p = PAPERS_BY_ID.get(paper_id)
    if not p:
        raise HTTPException(status_code=404, detail="Paper not found.")
    return {
        **paper_summary(p),
        "abstract": p.get("abstract") or "",
        "introduction": (p.get("introduction") or "")[:2500],
        "conclusion": (p.get("conclusion") or "")[:2500],
        "limitations": p.get("limitations") or "",
        "novelty": p.get("novelty") or "",
        "keywords": p.get("keywords") or "",
    }


@app.get("/api/insights")
def insights():
    total = max(len(PAPERS), 1)
    coverage = {
        "abstract": sum(1 for p in PAPERS if p.get("abstract")),
        "limitations": sum(1 for p in PAPERS if p.get("limitations")),
        "novelty": sum(1 for p in PAPERS if p.get("novelty")),
        "keywords": sum(1 for p in PAPERS if p.get("keywords")),
    }
    return {
        "total_papers": len(PAPERS),
        "categories": [
            {"name": n, "count": c} for n, c in CATEGORY_COUNTS.most_common()
        ],
        "venues": [
            {"name": n, "count": c} for n, c in VENUE_COUNTS.most_common(12)
        ],
        "coverage": {k: round(100 * v / total, 1) for k, v in coverage.items()},
    }


DIST = Path(__file__).parent / "frontend" / "dist"

if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{full_path:path}")
    def spa(full_path: str):
        candidate = DIST / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(DIST / "index.html")
