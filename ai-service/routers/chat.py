import os
import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from models.schemas import AskRequest, AskResponse, SourceChunk
from services.embeddings import get_embedding
from services.chroma_service import search_similar_chunks
from services.gemini import (
    ask_gemini, classify_question,
    generate_level_quiz, classify_level, get_level_system_prompt,generate_flashcards 
)
from services.history_service import (
    save_message, get_history, get_user_history,
    get_student_level, save_student_level, quiz_already_done,
    compress_history
)
import logging
import numpy as np
import asyncio
logger = logging.getLogger(__name__)
router = APIRouter()




CACHE_SIMILARITY_THRESHOLD = 0.92  # seuil de similarité
MAX_CACHE_SIZE = 100                # éviter fuite mémoire

semantic_cache = {}  # {question: {"embedding": [...], "response": {...}}}


def cosine_similarity(v1: list, v2: list) -> float:
    """
    Calcule la similarité cosinus entre deux vecteurs d'embeddings.

    Utilisée par le cache sémantique pour comparer l'embedding de la question
    courante avec ceux déjà mis en cache.

    Args:
        v1: Premier vecteur (liste de floats).
        v2: Deuxième vecteur (liste de floats, même dimension que v1).

    Returns:
        Score de similarité cosinus entre 0.0 et 1.0.
    """
    a, b = np.array(v1), np.array(v2)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def get_cached_response(question_embedding: list, course_id: int) -> dict | None:
    """
    Recherche une réponse en cache sémantique pour la question courante.

    Parcourt semantic_cache et calcule la similarité cosinus entre l'embedding
    de la question et chaque entrée du cache filtrée par course_id.
    Retourne la meilleure réponse si le score dépasse CACHE_SIMILARITY_THRESHOLD (0.92).

    Args:
        question_embedding: Vecteur d'embedding de la question courante.
        course_id:          ID du cours (évite les collisions entre cours).

    Returns:
        Dict réponse cachée {"answer", "found_in_course", "chunks_used", "sources", ...}
        ou None si aucun hit au-dessus du seuil.
    """
    best_score = 0
    best_response = None
    for key, entry in semantic_cache.items():
        if entry.get("course_id") != course_id:
            continue
        score = cosine_similarity(question_embedding, entry["embedding"])
        if score > best_score:
            best_score = score
            best_response = entry["response"]
    if best_score >= CACHE_SIMILARITY_THRESHOLD:
        logger.info("Cache hit — similarité: %.3f", best_score)
        return best_response
    return None


def save_to_cache(question: str, question_embedding: list, response: dict, course_id: int):
    """
    Sauvegarde une réponse dans le cache sémantique en mémoire.

    Si le cache atteint MAX_CACHE_SIZE (100 entrées), supprime l'entrée la plus ancienne
    (premier élément du dict, Python 3.7+ préserve l'ordre d'insertion).
    La clé est la question normalisée (minuscules + strip).

    Args:
        question:          Question brute de l'étudiant (sera normalisée en clé).
        question_embedding: Vecteur d'embedding pour les futures comparaisons cosinus.
        response:          Dict réponse Gemini à mettre en cache.
        course_id:         ID du cours associé à cette réponse.
    """
    if len(semantic_cache) >= MAX_CACHE_SIZE:
        oldest = next(iter(semantic_cache))
        del semantic_cache[oldest]
    semantic_cache[question.lower().strip()] = {
        "embedding":  question_embedding,
        "response":   response,
        "course_id":  course_id
    }


# ══════════════════════════════════════════════════════════════════════════════
# SCHÉMAS POUR LES ENDPOINTS NIVEAU
# ══════════════════════════════════════════════════════════════════════════════

class LevelQuizRequest(BaseModel):
    course_id:       int
    student_id:      int = 0
    conversation_id: str = ""


class LevelSaveRequest(BaseModel):
    course_id:       int
    student_id:      int = 0
    conversation_id: str
    score:           int
    total:           int = 10


# ══════════════════════════════════════════════════════════════════════════════
# MOTS-CLÉS : MESSAGES NON PÉDAGOGIQUES (pas de quiz de niveau)
# ══════════════════════════════════════════════════════════════════════════════

SMALL_TALK_KEYWORDS = [
    "bonjour", "bonsoir", "salut", "hello", "hi", "hey",
    "merci", "au revoir", "bye", "ciao", "bonne journée",
    "comment vas", "ça va", "comment tu vas", "quoi de neuf",
    "ok", "oui", "non", "d'accord", "super", "cool", "bien",
    "aide", "help", "qui es-tu", "qui es tu", "présente-toi",
    "c'est quoi edora", "tu peux", "tu es","cc","Bnjr","Bnsr",
]


def is_small_talk(question: str) -> bool:
    """
    Détecte si la question est un message social sans intention pédagogique.

    Condition : la question fait moins de 4 mots ET contient un mot-clé de SMALL_TALK_KEYWORDS.
    Court-circuite le pipeline RAG complet pour ces messages (pas d'embedding, pas de ChromaDB).

    Args:
        question: Question brute de l'étudiant.

    Returns:
        True si la question est identifiée comme small talk, False sinon.
    """
    q = question.lower().strip()
    if len(q.split()) < 4:
        return any(kw in q for kw in SMALL_TALK_KEYWORDS)
    return False


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINT : GÉNÉRER LE QUIZ DE NIVEAU
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/level-quiz")
async def get_level_quiz(request: LevelQuizRequest):
    """
    Génère le quiz de diagnostic de niveau pour un étudiant dans un cours.

    Si le quiz a déjà été complété (quiz_already_done), retourne immédiatement
    le niveau et le score existants sans régénérer.
    Sinon, récupère jusqu'à 8 chunks RAG du cours via ChromaDB et appelle
    generate_level_quiz pour produire un quiz de 10 questions QCM.

    Args (body JSON via LevelQuizRequest):
        course_id:       ID du cours Moodle.
        student_id:      ID de l'étudiant (défaut 0).
        conversation_id: UUID de la conversation courante (défaut "").

    Returns:
        {"already_done": True,  "level": str, "score": int}   si quiz déjà fait.
        {"already_done": False, "quiz": str}                   sinon (Markdown du quiz).

    Raises:
        HTTPException 404: Aucun contenu de cours disponible dans ChromaDB.
        HTTPException 503: Échec de la génération par Gemini.
    """
    if quiz_already_done(request.student_id, request.course_id):
        level_info = get_student_level(request.student_id, request.course_id)
        return {
            "already_done": True,
            "level":        level_info["level"],
            "score":        level_info["score"]
        }

    try:
        from services.embeddings import get_embedding
        query_embedding = get_embedding("concepts principaux du cours résumé général")
        chunks = search_similar_chunks(
            course_id=request.course_id,
            query_embedding=query_embedding,
            n_results=8
        )
    except Exception:
        chunks = []

    if not chunks:
        raise HTTPException(
            status_code=404,
            detail="Aucun contenu de cours disponible pour générer le quiz."
        )

    result = generate_level_quiz(chunks)
    if not result["success"]:
        raise HTTPException(
            status_code=503, detail="Impossible de générer le quiz de niveau.")

    return {
        "already_done": False,
        "quiz":         result["quiz"]
    }


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINT : SAUVEGARDER LE NIVEAU APRÈS LE QUIZ
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/level-save")
async def save_level(request: LevelSaveRequest):
    level = classify_level(request.score, request.total)
    success = save_student_level(
        user_id=request.student_id,
        course_id=request.course_id,
        conversation_id=request.conversation_id,
        level=level,
        score=request.score
    )
    if not success:
        raise HTTPException(
            status_code=500, detail="Erreur lors de la sauvegarde du niveau.")

    level_labels = {
        "debutant":      "Débutant 🌱",
        "intermediaire": "Intermédiaire 📘",
        "avance":        "Avancé 🚀"
    }
    return {
        "success": True,
        "level":   level,
        "label":   level_labels.get(level, level),
        "score":   request.score,
        "total":   request.total
    }

class FlashcardsRequest(BaseModel):
    course_id: int
    student_id: int = 0

@router.post("/flashcards")
async def get_flashcards(request: FlashcardsRequest):
    """Génère des flashcards depuis le contenu du cours."""
    try:
        query_embedding = get_embedding("concepts clés définitions résumé du cours")
        chunks = search_similar_chunks(
            course_id=request.course_id,
            query_embedding=query_embedding,
            n_results=8
        )
    except Exception:
        chunks = []

    if not chunks:
        raise HTTPException(status_code=404, detail="Aucun contenu disponible pour ce cours.")

    result = generate_flashcards(chunks)
    if not result["success"]:
        raise HTTPException(status_code=503, detail="Impossible de générer les flashcards.")

    return {"flashcards": result["flashcards"]}

# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINT : RÉCUPÉRER LE NIVEAU D'UN ÉTUDIANT
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/student-level")
async def get_level(student_id: int = 0, course_id: int = 0):
    """
    Retourne le niveau pédagogique actuel d'un étudiant pour un cours.

    Délègue directement à get_student_level (history_service).

    Args (query params):
        student_id: ID Moodle de l'étudiant.
        course_id:  ID du cours Moodle.

    Returns:
        {"level": str|None, "score": int|None, "quiz_done": bool}
    """
    info = get_student_level(student_id, course_id)
    return info


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINT PRINCIPAL : /ask
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/ask", response_model=AskResponse)
async def ask(request: AskRequest):
    """
    Endpoint principal du tuteur IA : traite la question d'un étudiant et retourne une réponse pédagogique.

    Pipeline en 13 étapes :
    1.  Validation de la question (non vide, ≤ 500 chars).
    2.  Classification du type de tâche (classify_question).
    3.  Court-circuit small talk → appel Gemini sans RAG, sauvegarde et retour immédiat.
    4.  Récupération du niveau étudiant (get_student_level).
    5.  Calcul de l'embedding de la question.
    6.  Vérification du cache sémantique → retour immédiat si hit.
    7.  Détermination du nombre de chunks selon le type de tâche (3 à 15).
    8.  Recherche ChromaDB (search_similar_chunks).
    9.  Construction des context_chunks et sources.
    10. Récupération et compression de l'historique (compress_history, max 8 tours).
    11. Appel ask_gemini avec le niveau étudiant injecté.
    12. Parsing JSON du quiz si task_type="quiz" (nettoyage des backticks).
    13. Sauvegarde MariaDB + mise en cache (sauf quiz) + retour AskResponse.

    Args (body JSON via AskRequest):
        question:             Question de l'étudiant.
        course_id:            ID du cours Moodle.
        student_id:           ID de l'étudiant.
        conversation_id:      UUID existant ou None (généré automatiquement).
        conversation_history: Historique partiel envoyé par le client.

    Returns:
        AskResponse : {answer, conversation_id, sources, found_in_course, chunks_used, is_quiz_json}

    Raises:
        HTTPException 400: Question vide ou trop longue.
        HTTPException 503: Erreur Gemini non récupérable.
    """
    # Étape 1 : Validation
    if len(request.question.strip()) == 0:
        raise HTTPException(status_code=400, detail="La question ne peut pas être vide.")
    if len(request.question) > 500:
        raise HTTPException(status_code=400, detail="Question trop longue (max 500 caractères).")

    # Étape 2 : Classification
    task_type = classify_question(request.question)

    # ── SMALL TALK : court-circuit ────────────────────────────────
    if is_small_talk(request.question):
        await asyncio.sleep(0)
        gemini_result = ask_gemini(
            question=request.question,
            context_chunks=[],
            conversation_history=[],
            student_id=request.student_id,
            course_id=request.course_id,
            task_type="chat",
            student_level=None
        )
        conversation_id = request.conversation_id or str(uuid.uuid4())
        save_message(request.student_id, request.course_id,
                     conversation_id, "user", request.question)
        save_message(request.student_id, request.course_id,
                     conversation_id, "assistant", gemini_result["answer"])
        return AskResponse(
            answer=gemini_result["answer"],
            conversation_id=conversation_id,
            sources=[],
            found_in_course=False,
            chunks_used=0,
            is_quiz_json=False
        )

    # Étape 3 : Niveau étudiant
    level_info = get_student_level(request.student_id, request.course_id)
    student_level = level_info.get("level")

    # Étape 4 : Embedding
    question_embedding = get_embedding(request.question)

    # ── CACHE ─────────────────────────────────────────────────────
    cached = get_cached_response(question_embedding, request.course_id)
    if cached:
        conversation_id = request.conversation_id or str(uuid.uuid4())
        save_message(request.student_id, request.course_id,
                     conversation_id, "user", request.question)
        save_message(request.student_id, request.course_id,
                     conversation_id, "assistant", cached["answer"])
        return AskResponse(
            answer=cached["answer"],
            conversation_id=conversation_id,
            sources=cached.get("sources", []),
            found_in_course=cached.get("found_in_course", True),
            chunks_used=cached.get("chunks_used", 0),
            is_quiz_json=cached.get("is_quiz_json", False)
        )

    # Étape 5 : Chunks adaptatifs
    N_CHUNKS = {
        "resume":    15,
        "quiz":      10,
        "expliquer": 10,
        "exemple":   10,
        "chat":      10,
    }
    n_results = N_CHUNKS.get(task_type, 3)

    # Étape 6 : Recherche ChromaDB
    results = search_similar_chunks(
        course_id=request.course_id,
        query_embedding=question_embedding,
        n_results=n_results
    )

    # Étape 7 : Chunks + sources
    context_chunks = []
    sources = []
    if results:
        for chunk in results:
            context_chunks.append({
                "text":     chunk["text"],
                "metadata": chunk["metadata"]
            })
            sources.append(SourceChunk(
                resource_name=chunk["metadata"].get("source", "cours"),
                chunk_excerpt=chunk["text"]
            ))

    # Étape 8 : Historique + compression
    history = [
        {"role": msg.role, "content": msg.content}
        for msg in (request.conversation_history or [])
    ]
    # Compresser si > 8 échanges
    history = compress_history(history, max_turns=8)

    # Étape 9 : task_type enrichi avec le niveau
    effective_task = task_type
    if student_level and task_type == "expliquer":
        effective_task = f"expliquer_{student_level}"

    # Étape 10 : Appel Gemini
    gemini_result = ask_gemini(
        question=request.question,
        context_chunks=context_chunks,
        conversation_history=history,
        student_id=request.student_id,
        course_id=request.course_id,
        task_type=task_type,
        student_level=student_level
    )

    # Étape 11 : Gestion erreur
    if not gemini_result["success"]:
        raise HTTPException(
            status_code=503,
            detail=f"Erreur Gemini : {gemini_result.get('error', 'inconnue')}"
        )

    # Étape 11.5 : Parser JSON quiz
    if task_type == "quiz" and gemini_result["success"]:
        import json
        try:
            raw = gemini_result["answer"].strip()
            raw = raw.replace("```json", "").replace("```", "").strip()
            quiz_data = json.loads(raw)
            if "questions" in quiz_data:
                gemini_result["answer"] = json.dumps(quiz_data, ensure_ascii=False)
                gemini_result["is_quiz_json"] = True
                logger.info("Quiz JSON parsé — %d questions", len(quiz_data["questions"]))
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("Quiz JSON invalide, réponse brute conservée : %s", str(e))
            gemini_result["is_quiz_json"] = False

    # Étape 12 : conversation_id
    conversation_id = request.conversation_id or str(uuid.uuid4())

    # Étape 13 : Sauvegarde MariaDB
    save_message(request.student_id, request.course_id,
                 conversation_id, "user", request.question)
    save_message(request.student_id, request.course_id,
                 conversation_id, "assistant", gemini_result["answer"])

    # ── CACHE : sauvegarder (sauf quiz) ──────────────────────────
    if gemini_result["success"] and task_type != "quiz":
        save_to_cache(
            request.question,
            question_embedding,
            {
                "answer":          gemini_result["answer"],
                "found_in_course": gemini_result["found_in_course"],
                "chunks_used":     gemini_result["chunks_used"],
                "is_quiz_json":    False,
                "sources":         [s.dict() for s in sources]
            },
            request.course_id
        )

    return AskResponse(
        answer=gemini_result["answer"],
        conversation_id=conversation_id,
        sources=sources,
        found_in_course=gemini_result["found_in_course"],
        chunks_used=gemini_result["chunks_used"],
        is_quiz_json=gemini_result.get("is_quiz_json", False)
    )


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS HISTORIQUE
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/history")
async def get_conversation_history(conversation_id: str, course_id: int = 0):
    """
    Retourne l'historique complet d'une conversation sous forme de liste de messages.

    Args (query params):
        conversation_id: UUID de la conversation.
        course_id:       Non utilisé dans la requête SQL actuelle (réservé pour filtrage futur).

    Returns:
        {"conversation_id": str, "messages": [{"role", "message", "created_at"}], "count": int}

    Raises:
        HTTPException 500: Erreur de connexion ou de requête MariaDB.
    """
    try:
        messages = get_history(conversation_id)
        return {
            "conversation_id": conversation_id,
            "messages": [
                {
                    "role":       m["role"],
                    "message":    m["message"],
                    "created_at": str(m["created_at"])
                }
                for m in messages
            ],
            "count": len(messages)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversations")
async def get_conversations(user_id: int = 0, course_id: int = 0):
    """
    Retourne la liste des conversations d'un étudiant dans un cours, triées par date décroissante.

    Groupe les messages par conversation_id, extrait le premier message user
    comme titre (tronqué à 60 chars + "..."), et trie par created_at DESC.

    Args (query params):
        user_id:   ID Moodle de l'étudiant.
        course_id: ID du cours Moodle.

    Returns:
        {"conversations": [{"conversation_id", "first_message", "created_at", "message_count"}]}
        {"conversations": []} si aucune conversation existante.

    Raises:
        HTTPException 500: Erreur MariaDB.
    """
    try:
        rows = get_user_history(user_id=user_id, course_id=course_id)
        if not rows:
            return {"conversations": []}

        grouped = {}
        for row in rows:
            cid = row["conversation_id"]
            if cid not in grouped:
                grouped[cid] = []
            grouped[cid].append(row)

        conversations = []
        for cid, msgs in grouped.items():
            first_user = next((m for m in msgs if m["role"] == "user"), None)
            conversations.append({
                "conversation_id": cid,
                "first_message":   first_user["message"][:60] + "..." if first_user and len(first_user["message"]) > 60 else (first_user["message"] if first_user else ""),
                "created_at":      str(msgs[0]["created_at"]),
                "message_count":   len(msgs)
            })

        conversations.sort(key=lambda x: x["created_at"], reverse=True)
        return {"conversations": conversations}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/conversation/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """
    Supprime tous les messages d'une conversation de la table mdl_edora_conversations.

    Args (path param):
        conversation_id: UUID de la conversation à supprimer.

    Returns:
        {"success": True, "deleted_messages": int}  (nombre de lignes supprimées)

    Raises:
        HTTPException 500: Erreur MariaDB.
    """
    try:
        from services.history_service import get_connection
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM mdl_edora_conversations WHERE conversation_id = %s",
            (conversation_id,)
        )
        deleted = cursor.rowcount
        conn.commit()
        cursor.close()
        conn.close()
        return {"success": True, "deleted_messages": deleted}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINT : BARRE DE PROGRESSION MAÎTRISE
# ══════════════════════════════════════════════════════════════════════════════

class MasteryUpdateRequest(BaseModel):
    user_id:  int
    course_id: int
    chunk_id:  str
    is_correct: bool = True

@router.get("/mastery")
async def get_mastery(user_id: int, course_id: int):
    """
    Retourne la progression de maîtrise des concepts pour un étudiant.

    Args (query params):
        user_id:   ID Moodle de l'étudiant.
        course_id: ID du cours Moodle.

    Returns:
        {"mastered": N, "total": M, "percent": X}
    """
    from services.history_service import get_connection
    from services.chroma_service import get_client
    chroma = get_client()

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT COUNT(DISTINCT chunk_id) as mastered
            FROM mdl_edora_mastery
            WHERE user_id = %s AND course_id = %s AND correct = 1
        """, (user_id, course_id))
        mastered = cursor.fetchone()["mastered"]

        # Total concepts via ChromaDB
        try:
            from services.chroma_service import get_client
            chroma = get_client()
            collection = chroma.get_collection(f"course_{course_id}")
            total = collection.count()
        except Exception:
            total = 0

        percent = round((mastered / total * 100), 1) if total > 0 else 0
        return {"mastered": mastered, "total": total, "percent": percent}
    finally:
        cursor.close()
        conn.close()


@router.post("/mastery/update")
async def update_mastery(request: MasteryUpdateRequest):
    """
    Enregistre une réponse correcte à un quiz (chunk maîtrisé).

    Args (body JSON):
        user_id, course_id, chunk_id, is_correct
    """
    from services.history_service import get_connection
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO mdl_edora_mastery (user_id, course_id, chunk_id, correct)
VALUES (%s, %s, %s, %s)
ON DUPLICATE KEY UPDATE correct = VALUES(correct)
        """, (request.user_id, request.course_id, request.chunk_id, int(request.is_correct)))
        conn.commit()
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINT : MIND MAP
# ══════════════════════════════════════════════════════════════════════════════

class MindMapRequest(BaseModel):
    course_id:  int
    student_id: int = 0


@router.post("/mindmap")
async def generate_mindmap(request: MindMapRequest):
    """
    Génère une Mind Map pédagogique depuis le contenu du cours via ChromaDB.

    Nouveau pipeline (COURSE → RAG → GEMINI → MINDMAP) :
    1. Récupère les chunks pertinents du cours via ChromaDB
    2. Construit un prompt pédagogique pour Gemini
    3. Gemini identifie concepts + relations + descriptions + importance
    4. Retourne JSON structuré pour D3.js

    Raises:
        HTTPException 404: Aucun contenu de cours dans ChromaDB.
        HTTPException 503: Erreur Gemini ou JSON invalide.
    """
    import json as _json
    import re as _re

    # ── Étape 1 : Récupérer le contenu du cours via ChromaDB ─────────────────
    try:
        query_embedding = get_embedding(
            "concepts principaux définitions notions importantes résumé du cours"
        )
        chunks = search_similar_chunks(
            course_id=request.course_id,
            query_embedding=query_embedding,
            n_results=12
        )
    except Exception as e:
        logger.error("Erreur ChromaDB /mindmap : %s", str(e))
        chunks = []

    if not chunks:
        raise HTTPException(
            status_code=404,
            detail="Aucun contenu de cours disponible. Importez d'abord des ressources dans le cours."
        )

    # ── Étape 2 : Construire le contexte depuis les chunks ───────────────────
    course_content = ""
    for i, chunk in enumerate(chunks[:12]):
        text = chunk.get("text", "")
        source = chunk.get("metadata", {}).get("source", "cours")
        course_content += f"[Extrait {i+1} — {source}]\n{text}\n\n"

    course_content = course_content[:8000]

    # ── Étape 3 : Prompt pédagogique pour Gemini ─────────────────────────────
    prompt = f"""Tu es un expert en pédagogie et en cartographie des connaissances.

Analyse ce contenu de cours et génère une Mind Map pédagogique structurée.

CONTENU DU COURS :
{course_content}

INSTRUCTIONS :
Tu dois retourner UNIQUEMENT un objet JSON valide, sans aucun texte avant ou après, sans markdown, sans backticks.

Structure JSON exacte à respecter :
{{
  "title": "Titre du cours en 3-5 mots",
  "nodes": [
    {{
      "id": "root",
      "label": "Concept central",
      "type": "root",
      "description": "Définition courte et claire du sujet principal (1-2 phrases).",
      "importance": "high"
    }},
    {{
      "id": "n1",
      "label": "Concept principal",
      "type": "main",
      "description": "Explication courte de ce concept (1-2 phrases).",
      "importance": "high"
    }},
    {{
      "id": "n2",
      "label": "Sous-concept",
      "type": "sub",
      "description": "Ce que cela signifie concrètement.",
      "importance": "medium"
    }},
    {{
      "id": "n3",
      "label": "Détail",
      "type": "detail",
      "description": "Information complémentaire.",
      "importance": "low"
    }}
  ],
  "links": [
    {{"source": "root", "target": "n1", "label": "comprend"}},
    {{"source": "n1", "target": "n2", "label": "inclut"}},
    {{"source": "n2", "target": "n3", "label": "exemple"}}
  ]
}}

Règles strictes :
- 1 seul noeud "root" (le concept central du cours)
- Entre 2 et 4 noeuds "main" (concepts principaux seulement)
- Entre 2 et 5 noeuds "sub" (sous-concepts)
- Entre 1 et 4 noeuds "detail" (exemples ou définitions clés uniquement)
- Total : entre 6 et 14 noeuds MAXIMUM — ne dépasse pas 14 noeuds
- Labels courts : 2-3 mots maximum
- Descriptions : 1 phrase courte maximum (moins de 15 mots)
- importance : "high", "medium" ou "low"
- Retourne UNIQUEMENT le JSON valide, rien d'autre avant ou après
- N'utilise pas d'apostrophes dans les valeurs JSON
"""

    # ── Étape 4 : Appel Gemini DIRECT (sans ask_gemini pour éviter les prompts système) ──
    raw = ""
    try:
        from google import genai as _genai
        from google.genai import types as _types
        _client = _genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        _model  = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
        _resp   = _client.models.generate_content(
            model=_model,
            contents=prompt,
            config=_types.GenerateContentConfig(
                temperature=0.1,
                max_output_tokens=8192,
                response_mime_type="application/json",
            )
        )
        raw = _resp.text.strip() if _resp.text else ""

        # Parsing robuste
        raw = _re.sub(r"^```(?:json)?\s*", "", raw, flags=_re.MULTILINE)
        raw = _re.sub(r"```\s*$",           "", raw, flags=_re.MULTILINE)
        raw = raw.strip()

        # Extraire le premier objet JSON si Gemini a ajouté du texte
        brace_start = raw.find("{")
        brace_end   = raw.rfind("}")
        if brace_start >= 0 and brace_end > brace_start:
            raw = raw[brace_start:brace_end + 1]

        # Tentative 1 : parser directement
        try:
            graph = _json.loads(raw)
        except _json.JSONDecodeError:
            # Tentative 2 : nettoyer les caractères de contrôle invisibles
            raw_clean = _re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', raw)
            # Tentative 3 : truncate au dernier noeud valide si JSON tronqué
            try:
                graph = _json.loads(raw_clean)
            except _json.JSONDecodeError:
                # Tentative 4 : extraire avec json repair manuel
                # Couper après le dernier lien complet
                last_bracket = raw_clean.rfind(']')
                last_brace   = raw_clean.rfind('}')
                if last_bracket > 0 and last_brace > last_bracket:
                    raw_clean = raw_clean[:last_brace + 1]
                elif last_bracket > 0:
                    # Fermer le JSON manuellement
                    raw_clean = raw_clean[:last_bracket + 1] + '}}'
                graph = _json.loads(raw_clean)

        if "nodes" not in graph or "links" not in graph:
            raise ValueError("Clés manquantes dans le JSON")

        logger.info(
            "MindMap cours générée — course=%s noeuds=%d liens=%d",
            request.course_id, len(graph["nodes"]), len(graph["links"])
        )

        return {
            "success": True,
            "title":   graph.get("title", "Mind Map du cours"),
            "nodes":   graph["nodes"],
            "links":   graph["links"]
        }

    except _json.JSONDecodeError as e:
        logger.error("MindMap JSON invalide : %s | raw: %.300s", str(e), raw)
        raise HTTPException(status_code=503, detail="Réponse Gemini non parsable en JSON.")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Erreur /mindmap : %s", str(e))
        raise HTTPException(status_code=503, detail=str(e))