from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from .config import FRONTEND_DIR
from .db import Base, engine, get_db
from .schemas import (
    AskRequest,
    FeedResponse,
    GenerationResponse,
    NotesRequest,
    QuizRequest,
    SubjectIn,
    SummaryRequest,
)
from .services.document_service import get_or_create_subject, ingest_pdf
from .services.generation_service import (
    ask_question,
    generate_notes,
    generate_quiz,
    generate_summary,
    get_feed,
    list_subjects,
)


Base.metadata.create_all(bind=engine)

app = FastAPI(title="Classroom Intelligence System", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/subjects")
def get_subjects(db: Session = Depends(get_db)):
    return {"items": list_subjects(db)}


@app.post("/subjects/upsert")
def upsert_subject(payload: SubjectIn, db: Session = Depends(get_db)):
    subject = get_or_create_subject(db, payload.year, payload.subject)
    return {"id": subject.id, "year": subject.year, "subject": subject.name}


@app.post("/documents/upload")
def upload_document(
    year: str = Form(...),
    subject: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    try:
        result = ingest_pdf(db, year=year, subject_name=subject, file_obj=file)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Upload failed: {exc}") from exc

    return {"message": "Document uploaded and indexed successfully.", "data": result}


@app.post("/generate/ask", response_model=GenerationResponse)
def ask(payload: AskRequest, db: Session = Depends(get_db)):
    try:
        content, sources, cached = ask_question(
            db=db,
            year=payload.year,
            subject_name=payload.subject,
            question=payload.question,
            explanation_mode=payload.explanation_mode,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"content": content, "sources": sources, "cached": cached}


@app.post("/generate/summary", response_model=GenerationResponse)
def summary(payload: SummaryRequest, db: Session = Depends(get_db)):
    try:
        content, sources, cached = generate_summary(
            db=db,
            year=payload.year,
            subject_name=payload.subject,
            focus=payload.focus,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"content": content, "sources": sources, "cached": cached}


@app.post("/generate/notes", response_model=GenerationResponse)
def notes(payload: NotesRequest, db: Session = Depends(get_db)):
    try:
        content, sources, cached = generate_notes(
            db=db,
            year=payload.year,
            subject_name=payload.subject,
            focus=payload.focus,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"content": content, "sources": sources, "cached": cached}


@app.post("/generate/quiz", response_model=GenerationResponse)
def quiz(payload: QuizRequest, db: Session = Depends(get_db)):
    try:
        content, sources, cached = generate_quiz(
            db=db,
            year=payload.year,
            subject_name=payload.subject,
            topic=payload.topic,
            difficulty=payload.difficulty,
            num_questions=payload.num_questions,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"content": content, "sources": sources, "cached": cached}


@app.get("/feed", response_model=FeedResponse)
def feed(
    year: str | None = None,
    subject: str | None = None,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    items = get_feed(db=db, year=year, subject_name=subject, limit=limit)
    return {"items": items}


# --- Serve the web frontend as static files ---
# Mount static assets (CSS, JS) at root — placed AFTER API routes so API takes priority
app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
