# D.I.S.C.O.V.E.R.

A question answering and retrieval tool over research papers from ACL, EACL, EMNLP, NAACL, CoNLL and Findings (2025-2026). There are 4,912 papers in the database. Ask a question in plain English and the tool finds the most relevant papers and writes an answer grounded in them, with inline citations you can click to jump to the source.

The app has two parts: a FastAPI backend that does the retrieval and talks to the LLM, and a React frontend for the website. Both run together from one command.

## What's in this folder

- `api.py` - the FastAPI backend, serves both the API and the built website
- `frontend/` - the React + TypeScript website (source in `frontend/src`, built output in `frontend/dist`)
- `query_router.py`, `retriever_v14.py`, `context_builder.py`, `llm_answer.py`, `llm_module.py` - the retrieval and answer pipeline
- `db_config.py` - database connection, reads credentials from `.env`
- `category_discovery.py`, `classify_papers.py`, `precompute_colbert.py` - one time offline scripts used to build the category shelves and the ColBERT cache
- `run_v11.py` and the scraping/extraction scripts (`scrape_urls.py`, `read_urls.py`, `downloader.py`, `extract_core.py`) - the pipeline that collected and parsed the original papers
- `requirements_v15.txt` - Python dependencies
- `colbert_doc_embeddings.npy` - precomputed embeddings used for fast re-ranking

## Requirements

- Python 3.12
- Node.js 18 and npm
- MySQL, with the `research_papers` database already loaded
- A Groq API key (free tier works, get one at console.groq.com)

## Setup

Open a terminal in this folder.

**1. Python environment**

```
python -m venv venv
venv\Scripts\activate
pip install -r requirements_v15.txt
```

**2. Environment variables**

Copy `.env.example` to a new file named `.env`, then fill in your own MySQL password and Groq API key:

```
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=research_papers

GROQ_API_KEY=your_groq_api_key
```

`.env` is in `.gitignore` and never gets uploaded to GitHub. This is the file that holds your real secrets.

**3. Frontend**

The site is already built (`frontend/dist` exists), so this step is optional unless you want to change the frontend code. If you do:

```
cd frontend
npm install
npm run build
cd ..
```

## Running it

```
venv\Scripts\activate
python -m uvicorn api:app --port 8000
```

Wait for it to finish loading papers, BM25 and ColBERT (takes under a minute), then open http://localhost:8000 in a browser. That's the whole app running on one port. Stop it with Ctrl+C.

Don't add `--reload` to that command, the pipeline takes a while to load and reload would reload it on every file save.

## Working on the frontend

Run the backend as above in one terminal, then in a second terminal:

```
cd frontend
npm run dev
```

Open http://localhost:5173. Changes to files in `frontend/src` show up instantly. When you're done, run `npm run build` again so the production server on port 8000 picks up the change.

## Troubleshooting

**Browser says it can't connect on localhost:8000** - the backend isn't running yet, or is still loading. Watch the terminal for "Uvicorn running".

**"DB connection" error at startup** - MySQL isn't running, or `DB_PASSWORD` in `.env` doesn't match your MySQL root password.

**Search works but answers fail** - Groq API problem. Check your internet connection and that `GROQ_API_KEY` in `.env` is a real, active key.

**Re-ranking feels slow** - the ColBERT cache is out of date, probably because papers were added or removed from the database. Re-run `python precompute_colbert.py`.

**Changed frontend code but nothing changes on :8000** - run `npm run build` inside `frontend` again, or use the dev server on :5173 instead while actively working on it.
