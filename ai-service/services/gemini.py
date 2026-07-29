import os
from google import genai
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# ── Persona tuteur pédagogique ──
SYSTEM_PROMPT = """Tu es Edo, un assistant tuteur pédagogique intégré dans la plateforme Edora LMS.

Ton rôle est d'aider les étudiants à comprendre le contenu de leur cours.

Tes règles absolues :
1. Tu réponds UNIQUEMENT en te basant sur le contenu du cours fourni dans le contexte.
2. Si la réponse n'est pas dans le contexte, dis honnêtement : "Je n'ai pas trouvé cette information dans le contenu du cours."
3. Tu ne donnes JAMAIS directement la réponse à un exercice — tu guides l'étudiant vers la réflexion.
4. Tu es patient, encourageant et bienveillant.
5. Tu expliques les concepts de plusieurs façons si l'étudiant ne comprend pas.
6. Tu utilises des exemples concrets pour illustrer les concepts.
7. Tu poses des questions de relance pour vérifier la compréhension.

Ton ton : chaleureux, pédagogique, encourageant. Jamais condescendant."""


def build_prompt(question: str, context_chunks: list, conversation_history: list = None) -> str:
    """
    Construit le prompt complet pour Gemini.
    
    Args:
        question: question de l'étudiant
        context_chunks: chunks pertinents trouvés dans ChromaDB
        conversation_history: historique de la conversation
    
    Returns:
        Prompt complet formaté
    """
    # Construire le contexte depuis les chunks
    if context_chunks:
        context = "\n\n---\n\n".join([
            f"Extrait {i+1} (source: {chunk.get('metadata', {}).get('source', 'cours')}):\n{chunk['text']}"
            for i, chunk in enumerate(context_chunks)
        ])
    else:
        context = "Aucun contenu de cours disponible pour cette question."

    # Construire l'historique
    history_text = ""
    if conversation_history:
        history_text = "\n\nHistorique de la conversation :\n"
        for msg in conversation_history[-4:]:  # Garde les 4 derniers messages
            role = "Étudiant" if msg["role"] == "user" else "Edo"
            history_text += f"{role}: {msg['content']}\n"

    prompt = f"""Contenu du cours disponible :
{context}
{history_text}
Question de l'étudiant : {question}

Réponds en te basant uniquement sur le contenu du cours ci-dessus."""

    return prompt


def ask_gemini(question: str, context_chunks: list, conversation_history: list = None) -> dict:
    """
    Envoie la question à Gemini avec le contexte RAG.
    
    Args:
        question: question de l'étudiant
        context_chunks: chunks pertinents de ChromaDB
        conversation_history: historique conversation
    
    Returns:
        dict avec answer, found_in_course
    """
    try:
        prompt = build_prompt(question, context_chunks, conversation_history)
        
        full_prompt = f"{SYSTEM_PROMPT}\n\n{prompt}"
        
        response = client.models.generate_content(
            model="gemini-3.5-flash",
            contents=full_prompt
        )
        
        answer = response.text
        found_in_course = bool(context_chunks)
        
        return {
            "success": True,
            "answer": answer,
            "found_in_course": found_in_course
        }

    except Exception as e:
        return {
            "success": False,
            "answer": "Une erreur est survenue. Veuillez réessayer.",
            "found_in_course": False,
            "error": str(e)
        }