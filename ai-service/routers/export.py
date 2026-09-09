import os
import io
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle
from reportlab.lib.enums import TA_CENTER

logger = logging.getLogger(__name__)
router = APIRouter()

TEAL = colors.HexColor('#005f73')
TEAL2 = colors.HexColor('#0a9396')
LIGHT_BG = colors.HexColor('#f0f9ff')

@router.get("/export-pdf")
async def export_pdf(user_id: int, course_id: int):
    """
    Génère un PDF de bilan de session étudiant.
    """
    # ── Étape 1 : Récupérer l'historique ────────────────────────────────────
    try:
        from services.history_service import get_connection, get_student_level
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT role, message, created_at
            FROM mdl_edora_conversations
            WHERE user_id = %s AND course_id = %s
            ORDER BY created_at ASC
            LIMIT 50
        """, (user_id, course_id))
        messages = cursor.fetchall()
        cursor.close()
        conn.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if not messages:
        raise HTTPException(status_code=404, detail="Aucune conversation trouvée pour cet étudiant.")

    # ── Étape 2 : Niveau étudiant ────────────────────────────────────────────
    from services.history_service import get_student_level
    level_info = get_student_level(user_id, course_id)
    level_labels = {
        "debutant": "Débutant 🌱",
        "intermediaire": "Intermédiaire 📘",
        "avance": "Avancé 🚀",
        None: "Non évalué"
    }
    level_label = level_labels.get(level_info.get("level"), "Non évalué")

    # ── Étape 3 : Prompt Gemini ──────────────────────────────────────────────
    conversation_text = ""
    for m in messages:
        role = "Étudiant" if m["role"] == "user" else "Edo"
        conversation_text += f"{role}: {m['message']}\n\n"
    conversation_text = conversation_text[:6000]

    prompt = f"""Analyse cette conversation entre un étudiant et le tuteur IA Edo.
Retourne UNIQUEMENT un JSON valide sans texte avant ni après :

{{
  "concepts": ["concept 1", "concept 2", "concept 3"],
  "points_forts": ["point fort 1", "point fort 2"],
  "a_revoir": ["point à revoir 1", "point à revoir 2"],
  "recommandations": ["recommandation 1", "recommandation 2"]
}}

Conversation :
{conversation_text}
"""

    try:
        import json
        from google import genai as _genai
        from google.genai import types as _types
        _client = _genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        _model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
        _resp = _client.models.generate_content(
            model=_model,
            contents=prompt,
            config=_types.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=2048,
                response_mime_type="application/json",
            )
        )
        raw = _resp.text.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        analysis = json.loads(raw)
    except Exception as e:
        logger.error("Erreur Gemini export PDF : %s", str(e))
        analysis = {
            "concepts": ["Analyse non disponible"],
            "points_forts": ["Session complétée"],
            "a_revoir": [],
            "recommandations": ["Continuer à pratiquer"]
        }

    # ── Étape 4 : Générer le PDF ─────────────────────────────────────────────
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm)

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('T', parent=styles['Title'],
        textColor=TEAL, fontSize=20, spaceAfter=6, alignment=TA_CENTER)
    subtitle_style = ParagraphStyle('S', parent=styles['Normal'],
        textColor=TEAL2, fontSize=11, spaceAfter=16, alignment=TA_CENTER)
    h1_style = ParagraphStyle('H1', parent=styles['Heading1'],
        textColor=TEAL, fontSize=13, spaceBefore=14, spaceAfter=8)
    body_style = ParagraphStyle('B', parent=styles['Normal'],
        fontSize=10, spaceAfter=4, leading=14)

    story = []
    story.append(Paragraph("Edora AI Tutor", title_style))
    story.append(Paragraph("Bilan de session étudiant", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=2, color=TEAL, spaceAfter=16))

    # Infos
    story.append(Paragraph(f"Niveau détecté : {level_label}", body_style))
    story.append(Paragraph(f"Messages échangés : {len(messages)}", body_style))
    story.append(Spacer(1, 0.3*cm))

    # Concepts
    story.append(Paragraph("📚 Concepts abordés", h1_style))
    for c in analysis.get("concepts", []):
        story.append(Paragraph(f"• {c}", body_style))

    # Points forts
    story.append(Paragraph("✅ Points forts", h1_style))
    for p in analysis.get("points_forts", []):
        story.append(Paragraph(f"• {p}", body_style))

    # À revoir
    story.append(Paragraph("⚠️ Points à revoir", h1_style))
    for r in analysis.get("a_revoir", []):
        story.append(Paragraph(f"• {r}", body_style))

    # Recommandations
    story.append(Paragraph("💡 Recommandations", h1_style))
    for rec in analysis.get("recommandations", []):
        story.append(Paragraph(f"• {rec}", body_style))

    story.append(Spacer(1, 0.5*cm))
    story.append(HRFlowable(width="100%", thickness=1, color=TEAL2, spaceAfter=8))
    story.append(Paragraph("Edora AI Tutor — Stage été 2026", subtitle_style))

    doc.build(story)
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=bilan_edora_cours{course_id}.pdf"}
    )