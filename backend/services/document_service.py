import shutil
import uuid
from pathlib import Path

from sqlalchemy.orm import Session

from ..config import CHUNK_OVERLAP, CHUNK_SIZE, UPLOAD_DIR
from ..models import Document, Section, Subject
from ..rag.chunking import chunk_text
from ..rag.embedding import embed_texts
from ..rag.vector_store import VectorStoreManager
from ..utils.pdf_loader import extract_pdf_pages


vector_store = VectorStoreManager()


def get_or_create_section(db: Session, year: str, section_name: str) -> Section:
    section = (
        db.query(Section)
        .filter(Section.year == year.strip(), Section.name == section_name.strip())
        .first()
    )
    if section:
        return section

    section = Section(year=year.strip(), name=section_name.strip())
    db.add(section)
    db.commit()
    db.refresh(section)
    return section


def get_or_create_subject(db: Session, year: str, section_name: str, subject_name: str) -> Subject:
    section = get_or_create_section(db, year, section_name)

    subject = (
        db.query(Subject)
        .filter(
            Subject.year == year.strip(),
            Subject.section_id == section.id,
            Subject.name == subject_name.strip(),
        )
        .first()
    )
    if subject:
        return subject

    subject = Subject(year=year.strip(), section_id=section.id, name=subject_name.strip())
    db.add(subject)
    db.commit()
    db.refresh(subject)
    return subject


def ingest_pdf(db: Session, year: str, section_name: str, subject_name: str, file_obj) -> dict:
    subject = get_or_create_subject(db, year, section_name, subject_name)

    original_name = Path(file_obj.filename).name
    unique_name = f"{uuid.uuid4().hex}_{original_name}"
    file_path = UPLOAD_DIR / unique_name

    with file_path.open("wb") as buffer:
        shutil.copyfileobj(file_obj.file, buffer)

    pages = extract_pdf_pages(file_path)
    metadata_rows: list[dict] = []
    chunk_texts_list: list[str] = []

    for page_num, page_text in pages:
        page_chunks = chunk_text(page_text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP)
        for idx, chunk in enumerate(page_chunks):
            chunk_texts_list.append(chunk)
            metadata_rows.append(
                {
                    "filename": original_name,
                    "page": page_num,
                    "chunk_index": idx,
                    "text": chunk,
                }
            )

    if chunk_texts_list:
        embeddings = embed_texts(chunk_texts_list)
        vector_store.add_embeddings(year=year, subject=subject_name, embeddings=embeddings, metadata_rows=metadata_rows)

    document = Document(
        subject_id=subject.id,
        filename=original_name,
        stored_path=str(file_path),
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    return {
        "document_id": document.id,
        "filename": document.filename,
        "pages": len(pages),
        "chunks_indexed": len(chunk_texts_list),
    }
