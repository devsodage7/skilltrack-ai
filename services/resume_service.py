"""
Resume analysis pipeline (business layer).

    upload -> validate -> store -> extract PDF text -> A1 skill extraction
           -> persist resume_records -> update student_skills (resume_level)
           -> re-fuse current_level

The service never touches Flask request objects: it receives a FileStorage
only inside `analyze_upload`, which is the single HTTP-aware entry point.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any

from app.utils.security import (
    extension_allowed,
    looks_like_pdf,
    random_stored_name,
    sanitise_filename,
)
from config import Config
from ml.skill_extractor import extract_skills
from models import career_model, resume_model, skill_model, student_model
from services import skill_service

MAX_TEXT_CHARS = 200_000
MIN_TEXT_CHARS = 40

try:  # PyMuPDF >= 1.24 exposes both names
    import pymupdf as fitz
except ImportError:  # pragma: no cover
    try:
        import fitz  # type: ignore
    except ImportError:  # pragma: no cover
        fitz = None


class ResumeError(Exception):
    """User-facing resume problem (bad file, unreadable PDF, ...)."""


# ---------------------------------------------------------------------
# PDF text
# ---------------------------------------------------------------------
def extract_pdf_text(pdf_bytes: bytes) -> tuple[str, int]:
    """Return (text, page_count). Raises ResumeError for unreadable files."""
    if fitz is None:
        raise ResumeError(
            "PyMuPDF is not installed. Run: pip install -r requirements.txt"
        )

    try:
        document = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as exc:  # noqa: BLE001
        raise ResumeError("The PDF could not be opened. It may be damaged.") from exc

    try:
        if document.is_encrypted and document.needs_pass:
            raise ResumeError("This PDF is password protected. Upload an unlocked copy.")
        pages = document.page_count
        chunks: list[str] = []
        for index in range(pages):
            try:
                chunks.append(document[index].get_text("text") or "")
            except Exception:  # noqa: BLE001 - one bad page should not kill the run
                continue
    finally:
        document.close()

    text = "\n".join(chunks).strip()
    if len(text) < MIN_TEXT_CHARS:
        raise ResumeError(
            "No readable text found. This looks like a scanned image PDF - "
            "export it again as a text PDF (or paste the text version)."
        )

    return text[:MAX_TEXT_CHARS], pages


# ---------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------
def _store_file(pdf_bytes: bytes) -> tuple[str, Path]:
    Path(Config.UPLOAD_FOLDER).mkdir(parents=True, exist_ok=True)
    stored_name = random_stored_name(".pdf")
    path = Path(Config.UPLOAD_FOLDER) / stored_name
    path.write_bytes(pdf_bytes)
    return stored_name, path


def _read_upload(file_storage: Any) -> tuple[bytes, str]:
    """Validate the upload and return (bytes, original_name)."""
    if file_storage is None or not getattr(file_storage, "filename", ""):
        raise ResumeError("Choose a PDF file first.")

    filename = sanitise_filename(file_storage.filename)
    if not extension_allowed(filename):
        raise ResumeError("Only .pdf files are accepted.")

    stream = file_storage.stream
    stream.seek(0, os.SEEK_END)
    size = stream.tell()
    stream.seek(0)

    if size <= 0:
        raise ResumeError("The file is empty.")
    if size > Config.MAX_UPLOAD_MB * 1024 * 1024:
        raise ResumeError(f"The file is larger than {Config.MAX_UPLOAD_MB} MB.")

    head = stream.read(8)
    stream.seek(0)
    if not looks_like_pdf(head):
        raise ResumeError("That file is not a real PDF (the header is wrong).")

    return stream.read(), filename


# ---------------------------------------------------------------------
# Skill evidence
# ---------------------------------------------------------------------
def _apply_resume_levels(student_id: int, detected: list[dict]) -> int:
    """Write resume evidence and re-fuse every touched skill."""
    touched = 0

    for row in detected:
        try:
            skill_id = int(row["skill_id"])
            level = float(row["level"])
        except (KeyError, TypeError, ValueError):
            continue
        if level <= 0:
            continue

        existing = skill_model.get_student_skill(student_id, skill_id) or {}
        fused, weights = skill_service.fuse_levels(
            existing.get("self_level"),
            level,
            existing.get("quiz_level"),
        )
        skill_model.upsert_student_skill(
            student_id=student_id,
            skill_id=skill_id,
            resume_level=level,
            current_level=fused,
            last_source="hybrid" if len(weights) > 1 else "resume",
        )
        touched += 1

    return touched


# ---------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------
def analyze_upload(file_storage: Any, student_id: int, career_id: int | None = None) -> dict:
    """
    Full resume run. Returns a summary dict used by the UI.

    Raises ResumeError with a message that is safe to show to the student.
    """
    pdf_bytes, original_name = _read_upload(file_storage)
    file_hash = hashlib.sha256(pdf_bytes).hexdigest()

    text, pages = extract_pdf_text(pdf_bytes)

    skills = skill_model.list_skills()
    requirements = career_model.career_requirements(career_id) if career_id else []
    result = extract_skills(text, skills, requirements)

    detected = result["detected"]
    detected_ids = {int(row["skill_id"]) for row in detected}
    missing = [
        str(req.get("skill_name"))
        for req in requirements
        if int(req.get("skill_id") or 0) not in detected_ids
    ]

    stored_name, _path = _store_file(pdf_bytes)
    duplicate = resume_model.find_by_hash(student_id, file_hash)

    record_id = resume_model.insert_record(
        student_id=student_id,
        career_id=career_id,
        original_name=original_name,
        stored_name=stored_name,
        file_size=len(pdf_bytes),
        file_hash=file_hash,
        extracted_text=text,
        detected_skills=[
            {
                "skill_id": row["skill_id"],
                "name": row["name"],
                "level": row["level"],
                "mentions": row["mentions"],
                "signals": row["signals"],
                "snippet": (row["snippets"][0][:220] if row.get("snippets") else ""),
            }
            for row in detected
        ],
        missing_skills=missing[:40],
        match_score=result["match_score"],
    )

    touched = _apply_resume_levels(student_id, detected)

    return {
        "record_id": record_id,
        "original_name": original_name,
        "file_size": len(pdf_bytes),
        "pages": pages,
        "duplicate": bool(duplicate),
        "detected": detected,
        "not_detected": result["not_detected"],
        "fuzzy_hits": result["fuzzy_hits"],
        "missing": missing,
        "match_score": result["match_score"],
        "stats": result["stats"],
        "skills_updated": touched,
    }


def latest_analysis(student_id: int) -> dict | None:
    """Latest stored resume, decoded for the template."""
    record = resume_model.latest_for_student(student_id)
    if not record:
        return None

    record["detected_list"] = resume_model.parsed_detected(record)
    record["missing_list"] = resume_model.parsed_missing(record)
    record["file_kb"] = round(float(record.get("file_size") or 0) / 1024, 1)
    return record


def history(student_id: int, limit: int = 8) -> list[dict]:
    rows = resume_model.list_for_student(student_id, limit=limit)
    for row in rows:
        row["file_kb"] = round(float(row.get("file_size") or 0) / 1024, 1)
        row["detected_count"] = len(resume_model.parsed_detected(row))
        row["match_score"] = float(row["match_score"]) if row.get("match_score") is not None else None
    return rows


def career_name(career_id: int | None) -> str | None:
    if not career_id:
        return None
    career = career_model.get_career(int(career_id))
    return career["name"] if career else None


def delete_file(stored_name: str) -> None:
    """Remove the stored PDF (used when a record is deleted)."""
    try:
        (Path(Config.UPLOAD_FOLDER) / stored_name).unlink(missing_ok=True)
    except OSError:
        pass


def profile_hint(student_id: int) -> dict:
    """Small summary for the resume page header."""
    student = student_model.get_by_id(student_id) or {}
    return {
        "has_goal": bool(student.get("career_goal_id")),
        "goal_name": career_name(student.get("career_goal_id")),
        "resume_count": resume_model.count_for_student(student_id),
    }
