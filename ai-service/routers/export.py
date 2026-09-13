import os
import io
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_LEFT

logger = logging.getLogger(__name__)
router = APIRouter()

TEAL      = colors.HexColor('#005f73')
TEAL2     = colors.HexColor('#0a9396')
TEAL_PALE = colors.HexColor('#e0f4f4')
AMBER     = colors.HexColor('#d97706')
GRAY      = colors.HexColor('#64748b')


class ExportRequest(BaseModel):
    user_id:     int = 0
    course_id:   int = 0
    answer_text: str = ""


@router.post("/export-pdf")
async def export_pdf(request: ExportRequest):
    """
    Génère un PDF de la réponse du tuteur IA pour l'étudiant.
    Reçoit le texte de la réponse directement depuis le chat (answer_text).
    Design moderne Edora — orienté révision étudiant.
    """
    if not request.answer_text.strip():
        raise HTTPException(status_code=400, detail="Aucune réponse à exporter.")

    # ── Niveau étudiant (optionnel) ──────────────────────────────────────────
    level_label = "Non évalué"
    if request.user_id and request.course_id:
        try:
            from services.history_service import get_student_level
            level_info  = get_student_level(request.user_id, request.course_id)
            level_labels = {
                "debutant":      "Débutant 🌱",
                "intermediaire": "Intermédiaire 📘",
                "avance":        "Avancé 🚀",
                None:            "Non évalué"
            }
            level_label = level_labels.get(level_info.get("level"), "Non évalué")
        except Exception:
            pass

    # ── Génération PDF ───────────────────────────────────────────────────────
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=2.2*cm, rightMargin=2.2*cm,
        topMargin=2*cm,    bottomMargin=2*cm
    )

    styles = getSampleStyleSheet()

    # Styles personnalisés
    title_style = ParagraphStyle('EdoTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=22, textColor=TEAL,
        alignment=TA_CENTER,
        spaceAfter=4
    )
    subtitle_style = ParagraphStyle('EdoSub',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=11, textColor=TEAL2,
        alignment=TA_CENTER,
        spaceAfter=4
    )
    meta_style = ParagraphStyle('EdoMeta',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9, textColor=GRAY,
        alignment=TA_CENTER,
        spaceAfter=16
    )
    section_style = ParagraphStyle('EdoSection',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12, textColor=TEAL,
        spaceBefore=16, spaceAfter=8,
        borderPad=4
    )
    body_style = ParagraphStyle('EdoBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10, textColor=colors.HexColor('#1e293b'),
        leading=16, spaceAfter=4,
        alignment=TA_LEFT
    )
    footer_style = ParagraphStyle('EdoFooter',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8, textColor=GRAY,
        alignment=TA_CENTER,
        spaceBefore=8
    )

    story = []

    # ── En-tête ──────────────────────────────────────────────────────────────
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph("Edora AI Tutor", title_style))
    story.append(Paragraph("Réponse de votre assistant pédagogique", subtitle_style))

    from datetime import datetime
    date_str = datetime.now().strftime("%d/%m/%Y à %H:%M")
    meta_parts = [f"Date : {date_str}"]
    if request.course_id:
        meta_parts.append(f"Cours #{request.course_id}")
    if level_label != "Non évalué":
        meta_parts.append(f"Niveau : {level_label}")
    story.append(Paragraph("  ·  ".join(meta_parts), meta_style))

    story.append(HRFlowable(
        width="100%", thickness=2,
        color=TEAL, spaceAfter=16
    ))

    # ── Contenu de la réponse ─────────────────────────────────────────────────
    story.append(Paragraph("📖 Réponse d'Edo", section_style))
    story.append(HRFlowable(width="40%", thickness=1, color=TEAL2, spaceAfter=10))

    # Nettoyer le texte markdown basique pour reportlab
    answer = request.answer_text.strip()

    # Traiter ligne par ligne
    for line in answer.split('\n'):
        line = line.strip()
        if not line:
            story.append(Spacer(1, 0.2*cm))
            continue

        # Titres markdown ## → section
        if line.startswith('## '):
            story.append(Paragraph(line[3:], ParagraphStyle('EdoH2',
                parent=styles['Normal'],
                fontName='Helvetica-Bold',
                fontSize=11, textColor=TEAL2,
                spaceBefore=10, spaceAfter=4
            )))
        # Titres # → section principale
        elif line.startswith('# '):
            story.append(Paragraph(line[2:], section_style))
        # Listes - ou *
        elif line.startswith('- ') or line.startswith('* '):
            txt = line[2:]
            # Gras **...**
            txt = txt.replace('**', '<b>', 1).replace('**', '</b>', 1)
            story.append(Paragraph(
                f"<font color='#0a9396'>•</font>  {txt}",
                ParagraphStyle('EdoBullet',
                    parent=body_style,
                    leftIndent=14, spaceAfter=3
                )
            ))
        # Gras inline
        else:
            txt = line
            import re
            txt = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', txt)
            txt = re.sub(r'\*(.*?)\*',     r'<i>\1</i>', txt)
            story.append(Paragraph(txt, body_style))

    # ── Footer ────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 0.8*cm))
    story.append(HRFlowable(width="100%", thickness=1, color=TEAL2, spaceAfter=8))
    story.append(Paragraph(
        "Edora AI Tutor — Réponse générée par intelligence artificielle. "
        "Vérifiez toujours les informations importantes.",
        footer_style
    ))

    # ── Build ─────────────────────────────────────────────────────────────────
    doc.build(story)
    buffer.seek(0)

    filename = f"edora_reponse_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )