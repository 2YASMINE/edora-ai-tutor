import os
import logging
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# ── Persona tuteur pédagogique (Islem) ──
SYSTEM_PROMPT = ""

# Phrase signature qu'Edo dit quand il ne trouve pas la réponse
NOT_FOUND_PHRASE = "Je n'ai pas trouvé cette information dans le contenu du cours"

# Nombre de messages d'historique à conserver (paramétrable pour Phase 7)
HISTORY_WINDOW = 6  # = 3 échanges


def build_context(context_chunks: list) -> str:
    """Formate les chunks ChromaDB en bloc contexte lisible."""
    if not context_chunks:
        return "Aucun contenu de cours disponible pour cette question."
    
    return "\n\n---\n\n".join([
        f"Extrait {i+1} (source: {chunk.get('metadata', {}).get('source', 'cours')}):\n{chunk['text']}"
        for i, chunk in enumerate(context_chunks)
    ])


def build_history(conversation_history: list) -> str:
    """Formate les N derniers messages de l'historique."""
    if not conversation_history:
        return ""
    
    lines = []
    for msg in conversation_history[-HISTORY_WINDOW:]:
        role = "Étudiant" if msg["role"] == "user" else "Edo"
        lines.append(f"{role}: {msg['content']}")
    
    return "\n\nHistorique de la conversation :\n" + "\n".join(lines)


def build_prompt(question: str, context_chunks: list, conversation_history: list = None) -> str:
    """
    Construit le prompt utilisateur pour Gemini (sans le system prompt).

    Args:
        question: question de l'étudiant
        context_chunks: chunks pertinents trouvés dans ChromaDB
        conversation_history: historique de la conversation

    Returns:
        Prompt formaté (contexte + historique + question)
    """
    context = build_context(context_chunks)
    history = build_history(conversation_history or [])

    return f"""Contenu du cours disponible :
{context}
{history}
Question de l'étudiant : {question}

Réponds en te basant uniquement sur le contenu du cours ci-dessus."""


def ask_gemini(question: str, context_chunks: list, conversation_history: list = None) -> dict:
    """
    Envoie la question à Gemini avec le contexte RAG.

    Args:
        question: question de l'étudiant
        context_chunks: chunks pertinents de ChromaDB
        conversation_history: historique conversation

    Returns:
        dict avec success, answer, found_in_course, chunks_used
    """
    try:
        prompt = build_prompt(question, context_chunks, conversation_history)

        response = client.models.generate_content(
            model="gemini-3.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.3,
                max_output_tokens=1024,
            )
        )

        answer = response.text

        found_in_course = bool(context_chunks) and NOT_FOUND_PHRASE not in answer

        return {
            "success": True,
            "answer": answer,
            "found_in_course": found_in_course,
            "chunks_used": len(context_chunks),
        }

    except Exception as e:
        return {
            "success": False,
            "answer": "Une erreur est survenue. Veuillez réessayer.",
            "found_in_course": False,
            "chunks_used": 0,
            "error": str(e)
        }