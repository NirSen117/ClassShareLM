from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    firebase_uid: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), index=True)
    display_name: Mapped[str] = mapped_column(String(120), default="")
    photo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    generated_contents = relationship("GeneratedContent", back_populates="user", cascade="all, delete-orphan")


class Section(Base):
    __tablename__ = "sections"
    __table_args__ = (UniqueConstraint("year", "name", name="uq_section_year_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    year: Mapped[str] = mapped_column(String(50), index=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    subjects = relationship("Subject", back_populates="section", cascade="all, delete-orphan")


class Subject(Base):
    __tablename__ = "subjects"
    __table_args__ = (UniqueConstraint("year", "section_id", "name", name="uq_subject_year_section_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    year: Mapped[str] = mapped_column(String(50), index=True)
    section_id: Mapped[int] = mapped_column(ForeignKey("sections.id"), index=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    section = relationship("Section", back_populates="subjects")
    documents = relationship("Document", back_populates="subject", cascade="all, delete-orphan")
    generated_contents = relationship("GeneratedContent", back_populates="subject", cascade="all, delete-orphan")


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"), index=True)
    filename: Mapped[str] = mapped_column(String(300))
    stored_path: Mapped[str] = mapped_column(String(500))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    subject = relationship("Subject", back_populates="documents")


class GeneratedContent(Base):
    __tablename__ = "generated_content"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"), index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    content_type: Mapped[str] = mapped_column(String(30), index=True)
    query_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    difficulty: Mapped[str | None] = mapped_column(String(20), nullable=True)
    explanation_mode: Mapped[bool] = mapped_column(Boolean, default=False)
    content: Mapped[str] = mapped_column(Text)
    sources_json: Mapped[str] = mapped_column(Text, default="[]")
    is_cached: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    subject = relationship("Subject", back_populates="generated_contents")
    user = relationship("User", back_populates="generated_contents")
