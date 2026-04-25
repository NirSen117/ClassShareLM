from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from .auth import get_current_user, require_auth
from .config import FRONTEND_DIR
from .db import Base, engine, get_db
from .models import User
from .schemas import (
    AskRequest,
    FeedResponse,
    GenerationResponse,
    NotesRequest,
    QuizRequest,
    SectionIn,
    SectionResponse,
    SubjectIn,
    SummaryRequest,
    UserResponse,
)
from .services.document_service import get_or_create_section, get_or_create_subject, ingest_pdf
from .services.generation_service import (
    ask_question,
    generate_notes,
    generate_quiz,
    generate_summary,
    get_feed,
    list_sections,
    list_subjects,
)


Base.metadata.create_all(bind=engine)

app = FastAPI(title="ClassShareLM — Classroom Social Media", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---- Health ----
@app.get("/health")
def health_check():
    return {"status": "ok"}


# ---- Auth ----
@app.get("/auth/me", response_model=UserResponse)
async def get_me(user: User = Depends(require_auth)):
    return {
        "id": user.id,
        "firebase_uid": user.firebase_uid,
        "email": user.email,
        "display_name": user.display_name,
        "photo_url": user.photo_url,
    }


# ---- Sections ----
@app.post("/sections/upsert", response_model=SectionResponse)
def upsert_section(
    payload: SectionIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    section = get_or_create_section(db, payload.year, payload.name)
    return {"id": section.id, "year": section.year, "name": section.name}


@app.get("/sections")
def get_sections_route(year: str | None = None, db: Session = Depends(get_db)):
    return {"items": list_sections(db, year=year)}


# ---- Subjects ----
@app.get("/subjects")
def get_subjects(
    year: str | None = None,
    section: str | None = None,
    db: Session = Depends(get_db),
):
    return {"items": list_subjects(db, year=year, section_name=section)}


@app.post("/subjects/upsert")
def upsert_subject(
    payload: SubjectIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    subject = get_or_create_subject(db, payload.year, payload.section, payload.subject)
    return {"id": subject.id, "year": subject.year, "subject": subject.name}


# ---- Upload ----
@app.post("/documents/upload")
def upload_document(
    year: str = Form(...),
    section: str = Form(...),
    subject: str = Form(...),
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    try:
        result = ingest_pdf(db, year=year, section_name=section, subject_name=subject, file_obj=file)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Upload failed: {exc}") from exc

    return {"message": "Document uploaded and indexed successfully.", "data": result}


# ---- Generate ----
@app.post("/generate/ask", response_model=GenerationResponse)
async def ask(payload: AskRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user_id = user.id if user else None
    try:
        content, sources, cached = ask_question(
            db=db,
            year=payload.year,
            subject_name=payload.subject,
            question=payload.question,
            explanation_mode=payload.explanation_mode,
            user_id=user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"content": content, "sources": sources, "cached": cached}


@app.post("/generate/summary", response_model=GenerationResponse)
async def summary(payload: SummaryRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user_id = user.id if user else None
    try:
        content, sources, cached = generate_summary(
            db=db,
            year=payload.year,
            subject_name=payload.subject,
            focus=payload.focus,
            user_id=user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"content": content, "sources": sources, "cached": cached}


@app.post("/generate/notes", response_model=GenerationResponse)
async def notes(payload: NotesRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user_id = user.id if user else None
    try:
        content, sources, cached = generate_notes(
            db=db,
            year=payload.year,
            subject_name=payload.subject,
            focus=payload.focus,
            user_id=user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"content": content, "sources": sources, "cached": cached}


@app.post("/generate/quiz", response_model=GenerationResponse)
async def quiz(payload: QuizRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user_id = user.id if user else None
    try:
        content, sources, cached = generate_quiz(
            db=db,
            year=payload.year,
            subject_name=payload.subject,
            topic=payload.topic,
            difficulty=payload.difficulty,
            num_questions=payload.num_questions,
            user_id=user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"content": content, "sources": sources, "cached": cached}


# ---- Feed ----
@app.get("/feed", response_model=FeedResponse)
async def feed(
    year: str | None = None,
    subject: str | None = None,
    limit: int = 50,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_id = user.id if user else None
    result = get_feed(db=db, year=year, subject_name=subject, user_id=user_id, limit=limit)
    return result


# --- Serve the web frontend as static files ---
# Mount static assets (CSS, JS) at root — placed AFTER API routes so API takes priority
app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
