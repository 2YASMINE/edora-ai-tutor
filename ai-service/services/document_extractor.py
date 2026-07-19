"""
Service d'extraction de texte depuis les ressources pédagogiques Moodle.
Formats supportés : PDF (natif), DOCX, PPTX, TXT
"""

import os
import pdfplumber
from docx import Document
from pptx import Presentation


def extract_text(file_path: str) -> dict:
    """
    Point d'entrée unique — détecte le format et délègue
    à l'extracteur approprié.

    Args:
        file_path: Chemin absolu vers le fichier

    Returns:
        {
            "success": bool,
            "text": str,
            "page_count": int,
            "format": str,
            "error": str | None
        }
    """
    if not os.path.exists(file_path):
        return _error(f"Fichier introuvable : {file_path}")

    extension = os.path.splitext(file_path)[1].lower()

    extractors = {
        ".pdf":  _extract_pdf,
        ".docx": _extract_docx,
        ".pptx": _extract_pptx,
        ".txt":  _extract_txt,
    }

    if extension not in extractors:
        return _error(
            f"Format non supporté : {extension}. "
            f"Formats acceptés : {', '.join(extractors.keys())}"
        )

    return extractors[extension](file_path)


# ─────────────────────────────────────────
# Extracteurs par format
# ─────────────────────────────────────────

def _extract_pdf(file_path: str) -> dict:
    try:
        pages_text = []
        empty_pages = 0

        with pdfplumber.open(file_path) as pdf:
            total_pages = len(pdf.pages)

            for page in pdf.pages:
                text = page.extract_text()
                if text and text.strip():
                    pages_text.append(text.strip())
                else:
                    empty_pages += 1

        # Détection PDF scanné : plus de 80% de pages sans texte
        if total_pages > 0 and (empty_pages / total_pages) > 0.8:
            return _error(
                "PDF scanné détecté — extraction impossible sans OCR. "
                "Fournissez un PDF avec texte natif.",
                format="pdf",
                page_count=total_pages
            )

        full_text = "\n\n".join(pages_text)

        if not full_text.strip():
            return _error("Aucun texte extractible dans ce PDF", format="pdf")

        return {
            "success": True,
            "text": full_text,
            "page_count": total_pages,
            "format": "pdf",
            "error": None
        }

    except Exception as e:
        return _error(f"Erreur PDF : {str(e)}", format="pdf")


def _extract_docx(file_path: str) -> dict:
    try:
        doc = Document(file_path)
        paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        full_text = "\n\n".join(paragraphs)

        if not full_text:
            return _error("Aucun texte trouvé dans ce fichier Word", format="docx")

        return {
            "success": True,
            "text": full_text,
            "page_count": None,  # DOCX n'a pas de notion de page
            "format": "docx",
            "error": None
        }

    except Exception as e:
        return _error(f"Erreur DOCX : {str(e)}", format="docx")


def _extract_pptx(file_path: str) -> dict:
    try:
        prs = Presentation(file_path)
        slides_text = []

        for i, slide in enumerate(prs.slides, start=1):
            slide_content = []
            for shape in slide.shapes:
                if hasattr(shape, "text") and shape.text.strip():
                    slide_content.append(shape.text.strip())

            if slide_content:
                slides_text.append(f"[Slide {i}]\n" + "\n".join(slide_content))

        full_text = "\n\n".join(slides_text)

        if not full_text:
            return _error("Aucun texte trouvé dans ce fichier PowerPoint", format="pptx")

        return {
            "success": True,
            "text": full_text,
            "page_count": len(prs.slides),
            "format": "pptx",
            "error": None
        }

    except Exception as e:
        return _error(f"Erreur PPTX : {str(e)}", format="pptx")


def _extract_txt(file_path: str) -> dict:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read().strip()

        if not text:
            return _error("Fichier texte vide", format="txt")

        return {
            "success": True,
            "text": text,
            "page_count": None,
            "format": "txt",
            "error": None
        }

    except UnicodeDecodeError:
        # Essai avec encodage latin-1 si UTF-8 échoue
        try:
            with open(file_path, "r", encoding="latin-1") as f:
                text = f.read().strip()
            return {
                "success": True,
                "text": text,
                "page_count": None,
                "format": "txt",
                "error": None
            }
        except Exception as e:
            return _error(f"Erreur encodage TXT : {str(e)}", format="txt")

    except Exception as e:
        return _error(f"Erreur TXT : {str(e)}", format="txt")


# ─────────────────────────────────────────
# Helper
# ─────────────────────────────────────────

def _error(message: str, format: str = "unknown", page_count: int = None) -> dict:
    return {
        "success": False,
        "text": "",
        "page_count": page_count,
        "format": format,
        "error": message
    }