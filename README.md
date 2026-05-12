# Ekantik Vartalap — Project Report

**Ekantik Vartalap** is a question-answering web app built around the spiritual discourses of
Shri Premanand Ji Maharaj. A user can ask a question — in Hindi or English — and the system
finds the most relevant passages from across hundreds of recorded "Ekantik" sessions and
returns an answer grounded entirely in those teachings.

---

## What It Does

1. A visitor opens the web app and goes to the **Ask** page.
2. They type a spiritual question (Hindi or English).
3. The question is translated to Hindi if needed, then sent to the backend.
4. The backend searches a vector database of ~890 Ekantik transcripts for the most
   relevant passages (using semantic similarity).
5. Those passages are handed to a language model, which composes a final answer — citing
   the specific Ekantik number it drew from.
6. The answer is shown back on the page.

---

## Folder Structure

```
ekantik/
├── app/
│   ├── api/
│   │   └── ekantiks_api.py     ← FastAPI backend (all routes + RAG logic)
│   ├── frontend/
│   │   ├── templates/          ← Jinja2 HTML pages (home, ask, contact, disclaimer)
│   │   └── static/             ← CSS, JS, images
│   └── .env.example            ← copy to .env and fill in your GROQ_API_KEY
│
├── pipeline/
│   ├── fetch_transcripts.py    ← script that downloads YouTube transcripts
│   ├── ekantik_videos_v1.json  ← list of all Ekantik video IDs + episode numbers
│   ├── transcripts/
│   │   ├── hindi/              ← 890 raw transcript JSONs (one per episode)
│   │   └── edited_ekantik/     ← manually reviewed/corrected transcripts
│   ├── state/
│   │   ├── processed/          ← one .done file per successfully fetched video
│   │   └── failures.json       ← videos that had no Hindi transcript available
│   └── moti.html               ← quick local viewer for transcript content
│
├── notebooks/
│   ├── phase1.ipynb            ← transcript ingestion and ChromaDB indexing (Phase 1)
│   ├── phase2.ipynb            ← RAG retrieval + LLM response (Phase 2 logic)
│   └── fastAPI.ipynb           ← FastAPI wiring and testing notebook
│
├── chroma_db/                  ← vector database (needs to be populated — see below)
└── README.md                   ← this file
```

---

## The Two Phases

### Phase 1 — Building the Knowledge Base
This was done on a Mac and the results need to be transferred to the Pi.

- `pipeline/fetch_transcripts.py` downloads Hindi transcripts from YouTube for each video in
  `ekantik_videos_v1.json`. It adds polite random delays between requests.
- The resulting JSON files (one per episode) land in `pipeline/transcripts/hindi/`.
- `notebooks/phase1.ipynb` then chunked those transcripts, embedded them using the
  **LaBSE** multilingual model (`sentence-transformers/LaBSE`), and stored them in a
  ChromaDB vector database (`chroma_db/`).

**Currently:** 890 transcripts are downloaded. The ChromaDB index (`chroma_db/`) was built
on the Mac and has **not yet been transferred** to the Pi. Until it is, the `/query`
endpoint returns nothing (the front-end pages still work fine).

### Phase 2 — Answering Questions
- User query → normalize to Hindi → ChromaDB MMR retrieval (top 7 chunks) → Groq LLM →
  answer with cited Ekantik numbers.
- Language model: `openai/gpt-oss-120b` via **Groq API**.
- Translation: `deep-translator` (Google Translate, English → Hindi only).

---

## How to Run

### Prerequisites
- Python virtual environment at `~/ekantik_env` (all packages already installed).
- A `.env` file at `app/.env` containing your Groq API key:
  ```
  GROQ_API_KEY=your_key_here
  ```
- The ChromaDB data folder transferred to `chroma_db/` (copy from Mac).

### Start the server
```bash
cd ~/Documents/projects/ekantik/app/api
~/ekantik_env/bin/uvicorn ekantiks_api:app --host 0.0.0.0 --port 8001
```

The app runs on **port 8001** (port 8000 is occupied by another project on this Pi).

### Pages
| Page | URL |
|---|---|
| Home | http://localhost:8001/ |
| Ask a question | http://localhost:8001/ask |
| Contact | http://localhost:8001/contact |
| Disclaimer | http://localhost:8001/disclaimer |
| API docs | http://localhost:8001/docs |

---

## Hosting / Public Access

The Pi uses a **Cloudflare Tunnel** (`cloudflared`) to expose local services without
port-forwarding. The current tunnel config maps:

```
pifive.marutsut.me  →  http://localhost:8000
```

Port 8000 is used by a different project. To make Ekantik publicly accessible, either:

**Option A** — Add a second hostname to `~/.cloudflared/config.yml`:
```yaml
ingress:
  - hostname: ekantik.marutsut.me
    service: http://localhost:8001
  - hostname: pifive.marutsut.me
    service: http://localhost:8000
  - service: http_status:404
```
Then restart cloudflared: `sudo systemctl restart cloudflared`

**Option B** — Point pifive.marutsut.me at port 8001 (replaces the other project).

---

## Dependencies

All installed in `~/ekantik_env`:

| Package | Purpose |
|---|---|
| `fastapi` + `uvicorn` | Web server |
| `jinja2` | HTML templating |
| `langchain` + `langchain-community` | RAG orchestration |
| `langchain-groq` | Groq LLM integration |
| `chromadb` | Vector database |
| `sentence-transformers` | LaBSE embedding model |
| `langdetect` | Detect query language |
| `deep-translator` | Translate English → Hindi |
| `python-dotenv` | Load API keys from .env |

---

## Known Gaps / Next Steps

- **Transfer ChromaDB from Mac** — copy the `chroma_db2` folder from the Mac to
  `~/Documents/projects/ekantik/chroma_db/` on the Pi. Without this, `/query` returns nothing.
- **LaBSE model cache** — first run after the DB transfer will try to download LaBSE
  (~475 MB). Either ensure internet access at that moment or pre-copy the HuggingFace
  cache from the Mac (`~/.cache/huggingface/`).
- **Groq API key** — create `app/.env` with `GROQ_API_KEY=...` before querying.
- **Model name** — `openai/gpt-oss-120b` is the current Groq model; update if it changes.
