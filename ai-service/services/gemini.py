import os
import logging
import concurrent.futures
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

# ── Logging structuré (Islem) ──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("edora.gemini")

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# ── Timeout appel Gemini en secondes (Islem) ──
GEMINI_TIMEOUT = int(os.getenv("GEMINI_TIMEOUT", "30"))

# ── Persona tuteur pédagogique (Islem) ──
SYSTEM_PROMPT = """Tu es Edo, le tuteur pédagogique intelligent d'Edora LMS.
Ton rôle est d'accompagner les étudiants dans leur apprentissage avec bienveillance et méthode.

Règles absolues :
1. Tu réponds UNIQUEMENT à partir du contenu du cours fourni. Tu n'inventes rien, tu n'utilises pas ta connaissance générale.
2. Tu ne donnes JAMAIS la réponse directement. Tu guides l'étudiant par des questions, des indices et des reformulations pour qu'il arrive lui-même à la réponse.
3. Si la réponse n'est pas dans le cours, tu le dis clairement : "Je n'ai pas trouvé cette information dans le contenu du cours", puis tu proposes à l'étudiant de reformuler sa question ou de consulter son enseignant.
4. Tu es patient. Si l'étudiant ne comprend pas, tu réexpliques différemment, avec un autre angle ou un exemple tiré du cours.
5. Tu encourages toujours. Tu valorises l'effort de l'étudiant avant de corriger ou de guider ("Bonne intuition !", "Tu es sur la bonne voie !", "C'est une excellente question !").
6. Tu poses UNE seule question à la fois pour ne pas surcharger l'étudiant.
7. Tu t'exprimes toujours dans la langue de l'étudiant (français par défaut).

Ton ton : chaleureux, encourageant, clair. Jamais condescendant, jamais expéditif."""

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
    """
    context = build_context(context_chunks)
    history = build_history(conversation_history or [])

    return f"""Contenu du cours disponible :
{context}
{history}
Question de l'étudiant : {question}

Réponds en te basant uniquement sur le contenu du cours ci-dessus."""


def _call_gemini_api(prompt: str) -> str:
    """
    Appel synchrone à l'API Gemini — isolé pour pouvoir être exécuté
    dans un thread avec timeout via concurrent.futures.
    """
    response = client.models.generate_content(
        model="gemini-3.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.3,
            max_output_tokens=1024,
        )
    )
    return response.text


def ask_gemini(question: str, context_chunks: list, conversation_history: list = None) -> dict:
    """
    Envoie la question à Gemini avec le contexte RAG.
    Inclut un timeout strict via concurrent.futures.ThreadPoolExecutor.
    """
    logger.info(
        "Appel Gemini — question: %.80s | chunks: %d | historique: %d messages",
        question,
        len(context_chunks),
        len(conversation_history or []),
    )

    try:
        prompt = build_prompt(question, context_chunks, conversation_history)

        # ── Timeout : thread séparé + futures (Islem) ──
        # Fonctionne dans un script ordinaire ET dans FastAPI
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_call_gemini_api, prompt)
            try:
                answer = future.result(timeout=GEMINI_TIMEOUT)
            except concurrent.futures.TimeoutError:
                logger.error(
                    "Timeout Gemini après %ds — question: %.80s",
                    GEMINI_TIMEOUT,
                    question
                )
                return {
                    "success": False,
                    "answer": "Le service IA met trop de temps à répondre. Veuillez réessayer dans quelques instants.",
                    "found_in_course": False,
                    "chunks_used": 0,
                    "error": f"Timeout après {GEMINI_TIMEOUT}s"
                }

        found_in_course = bool(context_chunks) and NOT_FOUND_PHRASE not in answer

        logger.info(
            "Réponse Gemini reçue — found_in_course: %s | longueur réponse: %d chars",
            found_in_course,
            len(answer),
        )

        return {
            "success": True,
            "answer": answer,
            "found_in_course": found_in_course,
            "chunks_used": len(context_chunks),
        }

    except Exception as e:
        logger.error("Erreur Gemini — %s: %s", type(e).__name__, str(e))
        return {
            "success": False,
            "answer": "Une erreur est survenue. Veuillez réessayer.",
            "found_in_course": False,
            "chunks_used": 0,
            "error": str(e)
        }