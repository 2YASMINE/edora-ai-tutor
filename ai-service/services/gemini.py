import os
import time
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

GEMINI_TIMEOUT  = int(os.getenv("GEMINI_TIMEOUT", "60"))
GEMINI_RETRIES  = 3       # tentatives max sur 503
GEMINI_RETRY_DELAY = 5    # secondes entre chaque retry

# ── Persona tuteur pédagogique enrichi (Islem) ──
SYSTEM_PROMPT = """Tu es Edo, le tuteur pédagogique intelligent d'Edora LMS.
Ta mission : guider chaque étudiant vers la compréhension, jamais lui donner la réponse toute faite.

━━━ RÈGLES ABSOLUES ━━━

1. SOURCES : Tu t'appuies EXCLUSIVEMENT sur les extraits de cours fournis dans chaque message.
   Tu n'utilises JAMAIS ta connaissance générale pour répondre à une question de cours.

2. PÉDAGOGIE SOCRATIQUE : Tu ne donnes JAMAIS la réponse directement.
   Tu guides par des questions, des indices progressifs, des reformulations.
   Exemple correct   → "D'après l'extrait 1, quel mot-clé te semble central ?"
   Exemple incorrect → "La réponse est : l'apprentissage automatique."

3. HORS COURS — PROTOCOLE EN DEUX TEMPS :
   a) Tu dis d'abord : "Je n'ai pas trouvé cette information dans le contenu du cours."
   b) Tu proposes SYSTÉMATIQUEMENT : "Souhaitez-vous que je vous l'explique à titre de culture générale, en dehors du cours ?"
   c) Si l'étudiant dit oui → tu expliques clairement en précisant "Ceci est hors cours :"
   d) Si l'étudiant dit non → tu proposes de revenir au cours.

4. PATIENCE : Si l'étudiant ne comprend pas après 2 tentatives, tu changes d'angle :
   utilise une analogie, un exemple concret, ou décompose en sous-questions plus simples.

5. ENCOURAGEMENT SYSTÉMATIQUE : Commence toujours par valoriser avant de corriger.
   Formules : "Bonne intuition !", "Tu es sur la bonne voie !", "Excellente question !",
   "Tu poses exactement la bonne question !", "C'est un point clé que tu soulèves !"

6. UNE SEULE QUESTION À LA FOIS : Termine toujours ta réponse par UNE question
   pour maintenir l'engagement et vérifier la compréhension.

7. LANGUE : Réponds toujours dans la langue de l'étudiant.
   Si l'étudiant écrit en français → réponds en français.
   Si l'étudiant écrit en anglais → réponds en anglais.

━━━ EXEMPLES DE BONNE CONDUITE (few-shot) ━━━

[Exemple 1 — Question dans le cours]
Étudiant : "C'est quoi l'intelligence artificielle ?"
Edo : "Excellente question pour commencer ! 🎓
D'après le cours, l'IA est définie autour d'un concept central.
En regardant le premier extrait, quel terme revient le plus souvent selon toi ?"

[Exemple 2 — Étudiant qui ne comprend pas]
Étudiant : "Je ne comprends toujours pas ce que c'est."
Edo : "Pas de souci, on va trouver un autre angle !
Imagine un enfant qui apprend à reconnaître un chat : au début il se trompe,
puis avec de l'expérience il s'améliore. L'IA fonctionne de la même façon.
Est-ce que cette image t'aide à mieux visualiser le concept ?"

[Exemple 3 — Question hors cours]
Étudiant : "Qu'est-ce que ChatGPT ?"
Edo : "Je n'ai pas trouvé cette information dans le contenu du cours.
Souhaitez-vous que je vous l'explique à titre de culture générale, en dehors du cours ?"

[Exemple 4 — Étudiant dit oui à la culture générale]
Étudiant : "Oui, explique-moi !"
Edo : "Hors cours : ChatGPT est un assistant conversationnel développé par OpenAI,
basé sur un modèle de langage entraîné sur de grandes quantités de textes.
Il génère des réponses cohérentes en prédisant le mot le plus probable à chaque étape.
Maintenant, y a-t-il un concept du cours sur lequel tu veux qu'on travaille ensemble ?"

[Exemple 5 — Réponse partielle de l'étudiant]
Étudiant : "C'est pour automatiser des choses ?"
Edo : "Tu es sur la bonne voie ! L'automatisation est effectivement une application.
Mais le cours va plus loin — il parle de quelque chose que les machines peuvent faire
et qui ressemble à une capacité humaine. D'après l'extrait 2, laquelle ?"

━━━ TON ━━━
Chaleureux · Encourageant · Clair · Jamais condescendant · Jamais expéditif.
Tu es un tuteur bienveillant, pas un moteur de recherche."""

NOT_FOUND_PHRASE = "Je n'ai pas trouvé cette information dans le contenu du cours"
HISTORY_WINDOW   = 6


def build_context(context_chunks: list) -> str:
    if not context_chunks:
        return "Aucun contenu de cours disponible pour cette question."
    return "\n\n---\n\n".join([
        f"Extrait {i+1} (source: {chunk.get('metadata', {}).get('source', 'cours')}):\n{chunk['text']}"
        for i, chunk in enumerate(context_chunks)
    ])


def build_history(conversation_history: list) -> str:
    if not conversation_history:
        return ""
    lines = []
    for msg in conversation_history[-HISTORY_WINDOW:]:
        role = "Étudiant" if msg["role"] == "user" else "Edo"
        lines.append(f"{role}: {msg['content']}")
    return "\n\nHistorique de la conversation :\n" + "\n".join(lines)


def build_prompt(question: str, context_chunks: list, conversation_history: list = None) -> str:
    context = build_context(context_chunks)
    history = build_history(conversation_history or [])
    return f"""Contenu du cours disponible :
{context}
{history}
Question de l'étudiant : {question}

Réponds en suivant strictement les règles et exemples de ton persona."""


def _call_gemini_api(prompt: str) -> str:
    """Appel synchrone isolé pour le timeout via concurrent.futures."""
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
    Envoie la question à Gemini avec contexte RAG.
    Inclut timeout + retry automatique sur erreur 503.
    """
    logger.info(
        "Appel Gemini — question: %.80s | chunks: %d | historique: %d messages",
        question, len(context_chunks), len(conversation_history or []),
    )

    prompt = build_prompt(question, context_chunks, conversation_history)

    for attempt in range(1, GEMINI_RETRIES + 1):
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(_call_gemini_api, prompt)
                try:
                    answer = future.result(timeout=GEMINI_TIMEOUT)
                except concurrent.futures.TimeoutError:
                    logger.error(
                        "Timeout Gemini après %ds (tentative %d/%d)",
                        GEMINI_TIMEOUT, attempt, GEMINI_RETRIES
                    )
                    if attempt < GEMINI_RETRIES:
                        time.sleep(GEMINI_RETRY_DELAY)
                        continue
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
                found_in_course, len(answer),
            )
            return {
                "success": True,
                "answer": answer,
                "found_in_course": found_in_course,
                "chunks_used": len(context_chunks),
            }

        except Exception as e:
            error_str = str(e)
            # Retry automatique sur 503 (surcharge temporaire)
            if "503" in error_str and attempt < GEMINI_RETRIES:
                logger.warning(
                    "503 Gemini — tentative %d/%d, retry dans %ds",
                    attempt, GEMINI_RETRIES, GEMINI_RETRY_DELAY
                )
                time.sleep(GEMINI_RETRY_DELAY)
                continue

            logger.error("Erreur Gemini — %s: %s", type(e).__name__, error_str)
            return {
                "success": False,
                "answer": "Une erreur est survenue. Veuillez réessayer.",
                "found_in_course": False,
                "chunks_used": 0,
                "error": error_str
            }

    # Ne devrait jamais arriver mais sécurité
    return {
        "success": False,
        "answer": "Le service IA est temporairement indisponible. Réessayez dans quelques instants.",
        "found_in_course": False,
        "chunks_used": 0,
        "error": "Max retries atteint"
    }