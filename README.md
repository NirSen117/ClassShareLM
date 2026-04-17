# ClassShareLM — Classroom Intelligence System

A shared AI-powered platform for classroom subjects using Retrieval-Augmented Generation (RAG).

## What This Project Does

- Upload subject documents (PDF)
- Build subject-wise FAISS vector index from document chunks
- Ask grounded questions from selected subject only
- Generate summaries, notes, and MCQ quizzes
- Store all generated outputs in SQLite
- Show generated outputs in a shared knowledge feed

## System Design (Practical RAG)

1. PDF upload -> text extraction per page
2. Text chunking -> overlap-aware chunks
3. Embeddings -> sentence-transformers (`all-MiniLM-L6-v2`)
4. Vector storage -> FAISS index per year+subject
5. Retrieval -> top-k chunks from selected subject index
6. Generation -> LLM prompt with retrieved context only
7. Persistence -> SQLite stores all generated outputs
8. Feed -> shared list of generated content per subject

## Folder Structure

```text
hackathon/
  backend/
    main.py
    config.py
    db.py
    models.py
    schemas.py
    services/
      document_service.py
      generation_service.py
    rag/
      chunking.py
      embedding.py
      vector_store.py
      llm.py
    utils/
      pdf_loader.py
    storage/
      uploads/
      faiss_indices/
  frontend/
    index.html
    styles.css
    app.js
  requirements.txt
  README.md
```

## Database Schema (SQLite)

### subjects
- id (PK)
- year (indexed)
- name (indexed)
- created_at
- Unique constraint on (year, name)

### documents
- id (PK)
- subject_id (FK -> subjects.id)
- filename
- stored_path
- uploaded_at

### generated_content
- id (PK)
- subject_id (FK -> subjects.id)
- content_type (`answer`, `quiz`, `summary`, `notes`)
- query_text
- difficulty (nullable)
- explanation_mode (bool)
- content (full generated text)
- sources_json (JSON string with filename/page/chunk/score)
- is_cached (bool)
- created_at

## API Endpoints

- `POST /subjects/upsert`
- `GET /subjects`
- `POST /documents/upload` (multipart: year, subject, file)
- `POST /generate/ask`
- `POST /generate/summary`
- `POST /generate/notes`
- `POST /generate/quiz`
- `GET /feed?year=...&subject=...&limit=50`

## Run Instructions

### 1) Create virtual environment

```bash
cd hackathon
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

### 2) Install dependencies

```bash
pip install -r requirements.txt
```

### 3) Configure environment (optional, recommended)

Create `.env` in `backend/`:

```env
GOOGLE_API_KEY=your_google_ai_studio_key_here
GEMINI_MODEL=gemini-2.0-flash
EMBEDDING_MODEL_NAME=sentence-transformers/all-MiniLM-L6-v2
TOP_K=4
CHUNK_SIZE=900
CHUNK_OVERLAP=150
```

If no API key is set, app uses a fallback response based on retrieved context.

### 4) Run the app

```bash
uvicorn backend.main:app --reload
```

Open your browser to [http://localhost:8000](http://localhost:8000). The web frontend and API are both served from the same server.

### 5) Use the app

1. Configure Academic Year and Subject in the sidebar
2. Upload a PDF document and wait for indexing
3. Use the tabs to ask questions, generate summaries, notes, or quizzes
4. Check the Feed tab to browse all generated content

## Notes for Hackathon Demo

- Subject isolation is enforced via separate FAISS index folders.
- Cached reuse is enabled for repeated queries by content type.
- All generations are stored to support a shared classroom feed.
- You can extend to MongoDB later by swapping persistence layer.

## GitHub Setup

1. Create a new empty repository on GitHub.
2. From this folder, run:

```bash
git init
git add .
git commit -m "Initial classroom intelligence system"
git branch -M main
git remote add origin <your-github-repo-url>
git push -u origin main
```

3. Keep your `.env` file out of GitHub. Use [backend/.env.example](backend/.env.example) as the template.

## Hosting on Render

The backend (FastAPI) serves both the API and the static web frontend from a single service.

### Deploy to Render

1. Create a new **Web Service** on Render from the GitHub repo.
2. **Build command**: `pip install -r requirements.txt`
3. **Start command**: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
4. Add environment variables from `backend/.env.example`.

That's it — one service handles everything.

## Deployment Notes

- FAISS indexes and uploaded PDFs are stored locally in `backend/storage/`.
- For a hackathon demo, this is enough if the service stays up.
- If you want persistence across redeploys, move file storage to a mounted volume or cloud object storage later.
- SQLite is fine for the hackathon. For production, replace it with Postgres or MongoDB.
