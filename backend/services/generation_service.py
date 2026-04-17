import json

from sqlalchemy.orm import Session

from ..config import TOP_K
from ..models import GeneratedContent, Subject
from ..rag.embedding import embed_query
from ..rag.llm import LLMService
from ..rag.vector_store import VectorStoreManager


llm_service = LLMService()
vector_store = VectorStoreManager()


def _subject_or_404(db: Session, year: str, subject_name: str) -> Subject | None:
    return (
        db.query(Subject)
        .filter(Subject.year == year.strip(), Subject.name == subject_name.strip())
        .first()
    )


def _format_sources(results: list[dict]) -> list[dict]:
    sources: list[dict] = []
    for row in results:
        sources.append(
            {
                "filename": row.get("filename", "unknown"),
                "page": int(row.get("page", 0)),
                "chunk_index": int(row.get("chunk_index", 0)),
                "score": float(row.get("score", 0.0)),
            }
        )
    return sources


def _context_block(results: list[dict]) -> str:
    if not results:
        return ""
    lines: list[str] = []
    for i, row in enumerate(results, start=1):
        lines.append(
            f"[{i}] Source: {row.get('filename')} | page {row.get('page')} | chunk {row.get('chunk_index')}\n"
            f"{row.get('text', '')}"
        )
    return "\n\n".join(lines)


def _find_cached(
    db: Session,
    *,
    subject_id: int,
    content_type: str,
    query_text: str | None,
    difficulty: str | None = None,
    explanation_mode: bool = False,
) -> GeneratedContent | None:
    q = db.query(GeneratedContent).filter(
        GeneratedContent.subject_id == subject_id,
        GeneratedContent.content_type == content_type,
        GeneratedContent.query_text == query_text,
        GeneratedContent.difficulty == difficulty,
        GeneratedContent.explanation_mode == explanation_mode,
    )
    return q.order_by(GeneratedContent.created_at.desc()).first()


def _save_generation(
    db: Session,
    *,
    subject_id: int,
    content_type: str,
    query_text: str | None,
    difficulty: str | None,
    explanation_mode: bool,
    content: str,
    sources: list[dict],
    is_cached: bool,
) -> GeneratedContent:
    item = GeneratedContent(
        subject_id=subject_id,
        content_type=content_type,
        query_text=query_text,
        difficulty=difficulty,
        explanation_mode=explanation_mode,
        content=content,
        sources_json=json.dumps(sources),
        is_cached=is_cached,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def _run_rag(year: str, subject_name: str, query: str, top_k: int = TOP_K) -> tuple[list[dict], list[dict]]:
    query_vec = embed_query(query)
    results = vector_store.search(year=year, subject=subject_name, query_embedding=query_vec, top_k=top_k)
    return results, _format_sources(results)


def ask_question(db: Session, year: str, subject_name: str, question: str, explanation_mode: bool) -> tuple[str, list[dict], bool]:
    subject = _subject_or_404(db, year, subject_name)
    if subject is None:
        raise ValueError("Subject not found. Upload at least one document first.")

    cached = _find_cached(
        db,
        subject_id=subject.id,
        content_type="answer",
        query_text=question.strip(),
        explanation_mode=explanation_mode,
    )
    if cached:
        return cached.content, json.loads(cached.sources_json), True

    retrieved, sources = _run_rag(year, subject_name, question)
    context = _context_block(retrieved)

    if not context:
        content = "No indexed content found for this subject yet. Please upload documents first."
        _save_generation(
            db,
            subject_id=subject.id,
            content_type="answer",
            query_text=question.strip(),
            difficulty=None,
            explanation_mode=explanation_mode,
            content=content,
            sources=[],
            is_cached=False,
        )
        return content, [], False

    explanation_line = "Also provide a short reasoning path." if explanation_mode else "Keep answer concise."
    system_prompt = "You are an academic assistant. Use only provided context. If context is insufficient, clearly say so."
    user_prompt = (
        f"Question: {question}\n\n"
        f"Instruction: {explanation_line}\n"
        "Cite the source number references like [1], [2].\n\n"
        f"Context:\n{context}"
    )
    content = llm_service.generate(system_prompt, user_prompt)

    _save_generation(
        db,
        subject_id=subject.id,
        content_type="answer",
        query_text=question.strip(),
        difficulty=None,
        explanation_mode=explanation_mode,
        content=content,
        sources=sources,
        is_cached=False,
    )
    return content, sources, False


def generate_summary(db: Session, year: str, subject_name: str, focus: str | None) -> tuple[str, list[dict], bool]:
    subject = _subject_or_404(db, year, subject_name)
    if subject is None:
        raise ValueError("Subject not found. Upload at least one document first.")

    query = (focus or "full summary").strip()
    cache_key = f"summary::{query}"
    cached = _find_cached(db, subject_id=subject.id, content_type="summary", query_text=cache_key)
    if cached:
        return cached.content, json.loads(cached.sources_json), True

    retrieved, sources = _run_rag(year, subject_name, query)
    context = _context_block(retrieved)
    system_prompt = "You create precise study summaries from provided context only."
    user_prompt = (
        f"Create a structured summary for: {query}\n"
        "Use headings and short paragraphs.\n\n"
        f"Context:\n{context}"
    )
    content = llm_service.generate(system_prompt, user_prompt)

    _save_generation(
        db,
        subject_id=subject.id,
        content_type="summary",
        query_text=cache_key,
        difficulty=None,
        explanation_mode=False,
        content=content,
        sources=sources,
        is_cached=False,
    )
    return content, sources, False


def generate_notes(db: Session, year: str, subject_name: str, focus: str | None) -> tuple[str, list[dict], bool]:
    subject = _subject_or_404(db, year, subject_name)
    if subject is None:
        raise ValueError("Subject not found. Upload at least one document first.")

    query = (focus or "important notes").strip()
    cache_key = f"notes::{query}"
    cached = _find_cached(db, subject_id=subject.id, content_type="notes", query_text=cache_key)
    if cached:
        return cached.content, json.loads(cached.sources_json), True

    retrieved, sources = _run_rag(year, subject_name, query)
    context = _context_block(retrieved)

    system_prompt = "You generate concise bullet-point notes from context only."
    user_prompt = (
        f"Generate bullet-point study notes for: {query}\n"
        "Group by concept and keep each bullet short.\n\n"
        f"Context:\n{context}"
    )
    content = llm_service.generate(system_prompt, user_prompt)

    _save_generation(
        db,
        subject_id=subject.id,
        content_type="notes",
        query_text=cache_key,
        difficulty=None,
        explanation_mode=False,
        content=content,
        sources=sources,
        is_cached=False,
    )
    return content, sources, False


def generate_quiz(
    db: Session,
    year: str,
    subject_name: str,
    topic: str,
    difficulty: str,
    num_questions: int,
) -> tuple[str, list[dict], bool]:
    subject = _subject_or_404(db, year, subject_name)
    if subject is None:
        raise ValueError("Subject not found. Upload at least one document first.")

    cache_key = f"quiz::{topic.strip()}::{num_questions}"
    cached = _find_cached(
        db,
        subject_id=subject.id,
        content_type="quiz",
        query_text=cache_key,
        difficulty=difficulty,
    )
    if cached:
        return cached.content, json.loads(cached.sources_json), True

    retrieved, sources = _run_rag(year, subject_name, topic)
    context = _context_block(retrieved)

    system_prompt = "You create MCQ quizzes from context only."
    user_prompt = (
        f"Create {num_questions} {difficulty} MCQs for topic: {topic}.\n"
        "Format: Question, options A-D, Correct Answer, and 1-line explanation.\n\n"
        f"Context:\n{context}"
    )
    content = llm_service.generate(system_prompt, user_prompt)

    _save_generation(
        db,
        subject_id=subject.id,
        content_type="quiz",
        query_text=cache_key,
        difficulty=difficulty,
        explanation_mode=False,
        content=content,
        sources=sources,
        is_cached=False,
    )
    return content, sources, False


def get_feed(db: Session, year: str | None, subject_name: str | None, limit: int = 50) -> list[dict]:
    q = db.query(GeneratedContent, Subject).join(Subject, Subject.id == GeneratedContent.subject_id)

    if year:
        q = q.filter(Subject.year == year.strip())
    if subject_name:
        q = q.filter(Subject.name == subject_name.strip())

    rows = q.order_by(GeneratedContent.created_at.desc()).limit(limit).all()

    items: list[dict] = []
    for generated, subject in rows:
        items.append(
            {
                "id": generated.id,
                "year": subject.year,
                "subject": subject.name,
                "content_type": generated.content_type,
                "query_text": generated.query_text,
                "difficulty": generated.difficulty,
                "explanation_mode": generated.explanation_mode,
                "content": generated.content,
                "sources": json.loads(generated.sources_json),
                "is_cached": generated.is_cached,
                "created_at": generated.created_at,
            }
        )
    return items


def list_subjects(db: Session) -> list[dict]:
    subjects = db.query(Subject).order_by(Subject.year.asc(), Subject.name.asc()).all()
    return [{"id": s.id, "year": s.year, "subject": s.name} for s in subjects]
