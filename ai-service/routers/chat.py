import os
import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from models.schemas import AskRequest, AskResponse, SourceChunk
from services.embeddings import get_embedding
from services.chroma_service import search_similar_chunks
from services.gemini import (
    ask_gemini, classify_question,
    generate_level_quiz, classify_level, get_level_system_prompt, generate_flashcards
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
    "c'est quoi edora", "tu peux", "tu es", "cc", "Bnjr", "Bnsr",
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
        query_embedding = get_embedding(
            "concepts principaux du cours résumé général")
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
        query_embedding = get_embedding(
            "concepts clés définitions résumé du cours")
        chunks = search_similar_chunks(
            course_id=request.course_id,
            query_embedding=query_embedding,
            n_results=8
        )
    except Exception:
        chunks = []

    if not chunks:
        raise HTTPException(
            status_code=404, detail="Aucun contenu disponible pour ce cours.")

    result = generate_flashcards(chunks)
    if not result["success"]:
        raise HTTPException(
            status_code=503, detail="Impossible de générer les flashcards.")

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
        AskResponse : {answer, conversation_id, sources,
            found_in_course, chunks_used, is_quiz_json}

    Raises:
        HTTPException 400: Question vide ou trop longue.
        HTTPException 503: Erreur Gemini non récupérable.
    """
    # Étape 1 : Validation
    if len(request.question.strip()) == 0:
        raise HTTPException(
            status_code=400, detail="La question ne peut pas être vide.")
    if len(request.question) > 500:
        raise HTTPException(
            status_code=400, detail="Question trop longue (max 500 caractères).")

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
        "expliquer": 15,
        "exemple":   10,
        "chat":      15,
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

    # ── Détection lacunes : logger si score faible ──────────────────
    SIMILARITY_THRESHOLD = 0.5
    if results:
        max_score = max(1 - chunk["distance"] for chunk in results)
        if max_score < SIMILARITY_THRESHOLD:
            try:
                from services.history_service import get_connection
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO mdl_edora_unanswered (course_id, user_id, question, similarity_score)
                    VALUES (%s, %s, %s, %s)
                """, (request.course_id, request.student_id, request.question, max_score))
                conn.commit()
                cursor.close()
                conn.close()
                logger.info(
                    "Question sans réponse RAG loggée — score: %.3f", max_score)
            except Exception as e:
                logger.warning("Erreur log unanswered : %s", str(e))
    if max_score < SIMILARITY_THRESHOLD:
        try:
            from services.history_service import get_connection
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO mdl_edora_unanswered (course_id, user_id, question, similarity_score)
                VALUES (%s, %s, %s, %s)
            """, (request.course_id, request.student_id, request.question, max_score))
            conn.commit()
            cursor.close()
            conn.close()
            logger.info(
                "Question sans réponse RAG loggée — score: %.3f", max_score)
        except Exception as e:
            logger.warning("Erreur log unanswered : %s", str(e))

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
                gemini_result["answer"] = json.dumps(
                    quiz_data, ensure_ascii=False)
                gemini_result["is_quiz_json"] = True
                logger.info("Quiz JSON parsé — %d questions",
                            len(quiz_data["questions"]))
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(
                "Quiz JSON invalide, réponse brute conservée : %s", str(e))
            gemini_result["is_quiz_json"] = False

    # Étape 12 : conversation_id
    conversation_id = request.conversation_id or str(uuid.uuid4())

    # Étape 13 : Sauvegarde MariaDB
    save_message(request.student_id, request.course_id,
                 conversation_id, "user", request.question, task_type)
    save_message(request.student_id, request.course_id,
                 conversation_id, "assistant", gemini_result["answer"], task_type)

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
        {"conversation_id": str, "messages": [
            {"role", "message", "created_at"}], "count": int}

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
        {"conversations": [
            {"conversation_id", "first_message", "created_at", "message_count"}]}
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
        _model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
        _resp = _client.models.generate_content(
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
        brace_end = raw.rfind("}")
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
                last_brace = raw_clean.rfind('}')
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
        raise HTTPException(
            status_code=503, detail="Réponse Gemini non parsable en JSON.")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Erreur /mindmap : %s", str(e))
        raise HTTPException(status_code=503, detail=str(e))

 # ══════════════════════════════════════════════════════════════════════════════
# ENDPOINT : REFORMULER UNE RÉPONSE SELON LE NIVEAU
# ══════════════════════════════════════════════════════════════════════════════


class ReformulateRequest(BaseModel):
    text:      str
    level:     int  # 1 = simple, 2 = standard, 3 = expert
    course_id: int = 0


REFORMULATE_PROMPTS = {
    1: """Reformule ce texte pour un enfant de 10 ans.
RÈGLES STRICTES :
- Utilise uniquement des mots simples du quotidien
- Ajoute une analogie concrète (jeu, nourriture, sport...)
- Maximum 3 phrases courtes
- Retourne UNIQUEMENT la reformulation, rien d'autre
- PAS de méta-commentaires, PAS d'introduction, PAS de conclusion""",

    2: """Reformule ce texte avec une explication claire et pédagogique.
RÈGLES STRICTES :
- Définis les termes techniques importants
- Structure en 2-3 phrases bien construites
- Retourne UNIQUEMENT la reformulation, rien d'autre
- PAS de méta-commentaires, PAS d'introduction, PAS de conclusion""",

    3: """Reformule ce texte avec une explication technique et spécialisée.
RÈGLES STRICTES :
- Utilise les termes spécialisés et le vocabulaire expert du domaine
- Sois précis, rigoureux et complet
- Maximum 5 phrases bien structurées
- Retourne UNIQUEMENT la reformulation, rien d'autre
- PAS de méta-commentaires, PAS d'introduction, PAS de conclusion"""
}


@router.post("/reformulate")
async def reformulate(request: ReformulateRequest):
    """
    Reformule un texte selon le niveau choisi par l'étudiant.
    level 1 = simple, 2 = standard, 3 = expert.
    """
    if not request.text.strip():
        raise HTTPException(
            status_code=400, detail="Le texte ne peut pas être vide.")
    if request.level not in [1, 2, 3]:
        raise HTTPException(
            status_code=400, detail="Le niveau doit être 1, 2 ou 3.")

    prompt_instruction = REFORMULATE_PROMPTS[request.level]

    prompt = f"{prompt_instruction}\n\nTexte à reformuler :\n{request.text}"

    try:
        from google import genai as _genai
        from google.genai import types as _types
        _client = _genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        _model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
        _resp = _client.models.generate_content(
            model=_model,
            contents=prompt,
            config=_types.GenerateContentConfig(
                temperature=0.3,
                max_output_tokens=4096,  # FIX : 2024 trop bas pour niveau Expert
            )
        )
        reformulated = _resp.text.strip() if _resp.text else ""
        if not reformulated:
            raise HTTPException(
                status_code=503, detail="Réponse vide de Gemini.")

        return {"success": True, "reformulated": reformulated, "level": request.level}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Erreur /reformulate : %s", str(e))
        raise HTTPException(status_code=503, detail=str(e))


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINT : QUESTIONS SANS RÉPONSE RAG (LACUNES DU COURS)
# ══════════════════════════════════════════════════════════════════════════════
@router.get("/unanswered")
async def get_unanswered(course_id: int):
    """
    Retourne le top 5 des questions sans réponse RAG pour un cours.
    Ce sont les questions avec un score de similarité < 0.5.
    """
    try:
        from services.history_service import get_connection
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT question, similarity_score, COUNT(*) as nb_fois, MIN(created_at) as first_seen
            FROM mdl_edora_unanswered
            WHERE course_id = %s
            GROUP BY question
            ORDER BY nb_fois DESC, similarity_score ASC
            LIMIT 5
        """, (course_id,))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return {"course_id": course_id, "unanswered": [
            {
                "question": r["question"],
                "score": round(r["similarity_score"], 3),
                "nb_fois": r["nb_fois"],
                "first_seen": str(r["first_seen"])
            } for r in rows
        ]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINT : GÉNÉRER UNE IMAGE EXPLICATIVE DU COURS (SVG via Gemini)
# ══════════════════════════════════════════════════════════════════════════════


class GenerateImageRequest(BaseModel):
    course_id:  int
    student_id: int = 0
    concept:    str = ""


@router.get("/list-image-models")
async def list_image_models():
    """Endpoint de diagnostic — liste les modèles Gemini supportant la génération d'images."""
    try:
        from google import genai as _genai
        _client = _genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        models = _client.models.list()
        image_models = []
        for m in models:
            supported = getattr(m, "supported_generation_methods", []) or []
            if any("image" in str(s).lower() or "generate" in str(s).lower() for s in supported):
                image_models.append({
                    "name": getattr(m, "name", str(m)),
                    "display_name": getattr(m, "display_name", ""),
                    "methods": [str(s) for s in supported]
                })
        return {"image_capable_models": image_models, "total": len(image_models)}
    except Exception as e:
        return {"error": str(e)}


@router.post("/generate-image")
async def generate_image(request: GenerateImageRequest):
    """
    Génère une image pédagogique IA du cours via Gemini Image Generation.

    Pipeline :
    1. Récupère les chunks clés du cours via ChromaDB.
    2. Gemini (modèle texte) génère un prompt image EN + caption FR depuis le contenu du cours.
    3. Gemini imagen (modèle image) génère l'image PNG.
    4. Retourne l'image en base64 + le caption.

    Returns:
        {"image_b64": str, "mime_type": str, "caption": str, "model_used": str}

    Raises:
        HTTPException 404: Aucun contenu de cours.
        HTTPException 503: Erreur génération Gemini.
    """

    import base64
    import json as _json
    import re as _re

    # ── Étape 1 : Récupérer le contenu du cours ───────────────────
    try:
        query_text = request.concept if request.concept else "concepts principaux définitions résumé schéma illustration cours" 
        query_embedding = get_embedding(query_text)
        chunks = search_similar_chunks(
            course_id=request.course_id,
            query_embedding=query_embedding,
            n_results=8
        )
    except Exception as e:
        logger.error("Erreur ChromaDB /generate-image : %s", str(e))
        chunks = []

    if not chunks:
        raise HTTPException(
            status_code=404,
            detail="Aucun contenu de cours disponible. Importez d'abord des ressources."
        )

        # ── Étape 2 : Construire le contexte du cours ─────────────────
    import re as _re_clean
    course_content = ""
    for i, chunk in enumerate(chunks[:8]):
        text = chunk.get("text", "")
        text = _re_clean.sub(r'\b\d{1,3}\b', '', text)
        text = _re_clean.sub(r'\d{1,2}/\d{1,2}/\d{4}', '', text)
        text = text.strip()
        course_content += f"[Extrait {i+1}]\n{text}\n\n"
    course_content = course_content[:4000]

    # ── Étape 3 : Gemini text → prompt image EN + caption FR ──────
    from google import genai as _genai
    from google.genai import types as _types

    _api_key = os.getenv("GEMINI_API_KEY")
    _text_model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
    _client = _genai.Client(api_key=_api_key)

    caption = "Illustration pédagogique des concepts du cours."
    image_prompt = ""

    try:
        specific_concept = (
    f"\n=== SPECIFIC CONCEPT REQUESTED ===\n{request.concept}\nFocus the image EXCLUSIVELY on this concept.\n"
    if request.concept else
    "\n=== COURSE OVERVIEW REQUESTED ===\nNo specific concept was requested. Generate a SINGLE comprehensive diagram that visually represents ALL the main concepts of this course and their relationships. The diagram must be a global overview — like a visual syllabus — showing how the key topics connect to each other.\n"
)
        meta_prompt = f"""You are an expert educational graphic designer creating VISUAL INFOGRAPHIC POSTERS for e-learning platforms.

Your mission: analyze the course content below and generate a detailed image prompt that produces a STUNNING, COLORFUL, VISUALLY RICH educational poster — NOT a technical wireframe diagram.

=== COURSE CONTENT ===
{course_content[:2500]}
{specific_concept}

=== GOLDEN RULES FOR THE IMAGE PROMPT ===
1. ALWAYS start with: "Vibrant educational infographic poster about [EXACT TOPIC]."
2. The poster MUST have a large bold TITLE at the top inside a colored gradient banner (e.g., deep teal, royal blue, rich purple).
3. Divide the poster into 3 or 4 large COLORED SECTIONS — each section is a rounded card with a SOLID COLOR FILL (not white). Use: deep teal, coral orange, golden yellow, rich purple, forest green, royal blue. Each section must have:
   - A large relevant ICON or EMOJI-style pictogram at the top (brain, gears, magnifying glass, network, lightbulb, arrow cycle, DNA helix, chart, server, etc.)
   - A bold white or dark section TITLE
   - 2-3 short bullet points of key information
4. Use VISUAL METAPHORS that match the topic: flowing arrows showing processes, node networks, layered architecture, circular cycles, comparison charts, step-by-step numbered flows.
5. Bottom strip: a dark background ribbon with 4-5 key concept KEYWORDS shown as colored pill/badge tags.
6. Style: VIBRANT, BOLD, HIGH-CONTRAST. Think: Canva educational template, Visme infographic, professional e-learning poster. Bright saturated colors, gradient fills, rounded corners, subtle shadows on cards.
7. Typography: large bold title (48pt+), section headers (24pt), readable body text. All text labels in the language of the course content.
8. ABSOLUTELY FORBIDDEN: plain white boxes, wireframe diagrams, UML-style boxes with compartments, minimal flat line art, gray backgrounds, boring technical charts.
9. The image should look like something you would see on Pinterest under "beautiful educational infographic" or "stunning learning poster".

=== FEW-SHOT EXAMPLES ===

EXAMPLE 1 — Artificial Intelligence Course:
Content keywords: neural network, deep learning, layers, training, dataset, classification
→ image_prompt: "Vibrant educational infographic poster about Deep Learning and Neural Networks. Top banner: bold white title DEEP LEARNING on deep navy gradient background with glowing brain icon. Three large rounded cards below: LEFT CARD in deep teal — large layered-circles neural network pictogram, bold title INPUT LAYER, bullets: Raw data entry / Images, text, numbers / 784 input nodes. CENTER CARD in rich purple — interconnected nodes with flowing arrows pictogram, bold title HIDDEN LAYERS, bullets: Pattern extraction / Weighted connections / ReLU activation. RIGHT CARD in coral orange — target output icon, bold title OUTPUT LAYER, bullets: Classification result / Softmax probabilities / Confidence score. Connecting gradient arrows between cards showing left-to-right data flow. Bottom dark ribbon with colored pill tags: Backpropagation, Gradient Descent, Epochs, Loss Function, Overfitting. Background: very light blue-gray. Bold shadows on cards, rounded corners, professional vibrant e-learning poster style."
→ caption: "Un réseau de neurones apprend par rétropropagation à classifier les données d'entraînement."

EXAMPLE 2 — Database Course:
Content keywords: SQL, tables, primary key, foreign key, joins, relational model, normalization
→ image_prompt: "Vibrant educational infographic poster about Relational Databases and SQL. Top banner: bold white title BASES DE DONNÉES RELATIONNELLES on deep blue gradient, database cylinder icon glowing in gold. Four rounded colored cards in a 2x2 grid: TOP-LEFT card royal blue — stacked table icon, bold title TABLES & CLÉS, bullets: Clé primaire unique / Clé étrangère = lien / Contraintes d'intégrité. TOP-RIGHT card forest green — Venn diagram circles icon, bold title LES JOINTURES SQL, bullets: INNER JOIN = intersection / LEFT JOIN = tout à gauche / Types de jointures. BOTTOM-LEFT card golden yellow with dark text — funnel normalization icon, bold title NORMALISATION, bullets: 1NF: atomicité / 2NF: dépendances / 3NF: transitivité. BOTTOM-RIGHT card coral orange — gears icon, bold title REQUÊTES SQL, bullets: SELECT, FROM, WHERE / GROUP BY, ORDER BY / Sous-requêtes imbriquées. Center connecting element: four arrows pointing to a central golden badge labeled SQL. Bottom dark ribbon with pills: SELECT, JOIN, INDEX, ACID, Clé Primaire. Gradient card backgrounds, rounded corners, strong shadows, vibrant professional poster."
→ caption: "Le modèle relationnel organise les données en tables liées par des clés pour des requêtes SQL efficaces."

EXAMPLE 3 — Logic and Reasoning Course:
Content keywords: propositional logic, deductive reasoning, inductive reasoning, inference rules, resolution
→ image_prompt: "Vibrant educational infographic poster about Logic and Automated Reasoning. Top banner: bold white title LOGIQUE & RAISONNEMENT on deep purple-to-teal gradient with glowing brain-and-gears icon. Three tall rounded cards side by side: LEFT CARD deep teal — top-down funnel icon with P→Q label, bold title RAISONNEMENT DÉDUCTIF in white, bullets in white: Prémisses → Conclusion / Modus Ponens: si P alors Q / Certitude absolue / Exemple: théorèmes. CENTER CARD golden amber — upward arrows converging icon, bold title RAISONNEMENT INDUCTIF in dark, bullets: Observations → Règle / Du particulier au général / Probabiliste / Exemple: cygnes blancs. RIGHT CARD coral red — omega symbol with lightning icon, bold title RÉSOLUTION & PREUVE in white, bullets: Clause P ∨ Q / Résolvante = nouvelle clause / Base de clauses / Réfutation par contradiction. Large curved arrow looping from RIGHT back to LEFT showing cycle of knowledge. Bottom dark navy ribbon with bright pill tags: Modus Ponens, Clause de Horn, Résolvante, Inférence, Réfutation. Overall: vivid poster aesthetic, bold typography, gradient card fills, rounded corners, glowing accent icons."
→ caption: "Les méthodes de raisonnement logique permettent de déduire ou d'induire des conclusions à partir de prémisses."

EXAMPLE 4 — Software Architecture Course:
Content keywords: MVC, microservices, API, REST, layers, components, design patterns
→ image_prompt: "Vibrant educational infographic poster about Software Architecture Patterns. Top banner: bold white title ARCHITECTURE LOGICIELLE on deep navy-to-indigo gradient with interconnected hexagons icon. Three large rounded cards: LEFT CARD rich purple — three horizontal layers icon with browser/gear/database symbols, bold title ARCHITECTURE MVC in white, bullets: View = interface utilisateur / Controller = logique métier / Model = données & BD. CENTER CARD forest green — six hexagonal service pods connected by lines icon, bold title MICROSERVICES in white, bullets: Services indépendants / Communication REST/API / Déploiement autonome. RIGHT CARD coral orange — two-way arrows with lock icon, bold title API REST in white, bullets: GET POST PUT DELETE / JSON / Stateless & scalable. Diagonal gradient banner cutting across the bottom of all cards with text: Design Patterns. Bottom dark ribbon with colored pills: SOLID, MVC, API Gateway, CI/CD, Docker. Background: very light warm gray. Vibrant poster, strong card shadows, rounded corners, professional modern style."
→ caption: "Les architectures logicielles MVC et microservices organisent le code pour la maintenabilité et la scalabilité."

=== YOUR TASK ===
Step 1 — Identify: the EXACT topic of this course in one sentence, and 3-5 core concepts to visualize.
Step 2 — Generate the image_prompt:
- MUST start with "Vibrant educational infographic poster about [EXACT TOPIC]."
- MUST include a colored gradient title banner with icon
- MUST have 3 or 4 large colored section cards (each with its own solid color fill — NO white cards)
- MUST describe icons/pictograms for each section (relevant to the topic, not generic)
- MUST include connecting visual elements (arrows, flows, central badge)
- MUST end with a bottom dark ribbon with colored pill/badge keyword tags
- MUST specify: "Vibrant poster aesthetic, bold typography, gradient fills, rounded corners, strong drop shadows, professional e-learning visual style."
- Minimum 120 words — describe EVERY card, EVERY color, EVERY visual element
- All text labels in the same language as the course content

Step 3 — Generate the caption:
- In FRENCH, 10-15 words, complete sentence starting with capital, ending with period.

Respond ONLY with this valid JSON (double quotes mandatory, absolutely zero extra text before or after):
{{"image_prompt": "...", "caption": "..."}}"""

        meta_resp = _client.models.generate_content(
            model=_text_model,
            contents=meta_prompt,
            config=_types.GenerateContentConfig(
                temperature=0.4,
                max_output_tokens=2048,
                response_mime_type="application/json",
            )
        )

        raw = meta_resp.text.strip() if meta_resp.text else ""
        raw = _re.sub(r"```(?:json)?\s*", "", raw)
        raw = _re.sub(r"```", "", raw).strip()
        brace_start = raw.find("{")
        brace_end = raw.rfind("}")
        if brace_start >= 0 and brace_end > brace_start:
            json_match_str = raw[brace_start:brace_end + 1]
            meta_data = _json.loads(json_match_str)
        else:
            raise ValueError(f"Aucun JSON trouvé dans : {raw[:200]}")

        image_prompt = meta_data.get("image_prompt", "").strip()
        caption      = meta_data.get("caption", caption).strip()
        if not caption.endswith("."):
            caption += "."

        logger.info("Prompt image : %s", image_prompt)

    except Exception as e:
        logger.warning("Erreur génération prompt image : %s", str(e))
        first_words = " ".join(course_content.split()[:40])
        image_prompt = (
            f"Clean flat design educational illustration about: {first_words}. "
            "White background, colorful icons, no text, professional infographic style, no letters."
        )

    if not image_prompt:
        image_prompt = (
            "Educational infographic illustration, clean flat design, colorful, "
            "white background, learning concepts diagram, no text, professional."
        )

    # ── Étape 4 : Gemini Image Generation ─────────────────────────
    IMAGE_MODELS_TO_TRY = [
        "imagen-4.0-generate-preview-06-06",
        "imagen-3.0-generate-002",
        "imagen-3.0-generate-001",
        "gemini-2.5-flash-preview-05-20",
        "gemini-2.5-flash-image",
        "gemini-3.1-flash-image",
        "gemini-3.1-flash-lite-image",
    ]

    last_error = None
    for img_model in IMAGE_MODELS_TO_TRY:
        try:
            logger.info("Essai modèle image : %s", img_model)
            img_b64 = None
            mime    = "image/png"

            # ── Imagen models (imagen-3, imagen-4) : API generate_images ──────
            if img_model.startswith("imagen"):
                img_response = _client.models.generate_images(
                    model=img_model,
                    prompt=image_prompt,
                    config=_types.GenerateImagesConfig(
                        number_of_images=1,
                        aspect_ratio="1:1",
                    )
                )
                if img_response.generated_images:
                    raw_bytes = img_response.generated_images[0].image.image_bytes
                    mime = "image/png"
                    img_b64 = (
                        base64.b64encode(raw_bytes).decode("utf-8")
                        if isinstance(raw_bytes, (bytes, bytearray))
                        else raw_bytes
                    )

            # ── Gemini models : API generate_content ──────────────────────────
            else:
                img_response = _client.models.generate_content(
                    model=img_model,
                    contents=image_prompt,
                    config=_types.GenerateContentConfig(
                        response_modalities=["IMAGE", "TEXT"],
                        temperature=0.4,
                    )
                )
                for part in (img_response.candidates[0].content.parts
                             if img_response.candidates else []):
                    if hasattr(part, "inline_data") and part.inline_data:
                        raw_bytes = part.inline_data.data
                        mime      = part.inline_data.mime_type or "image/png"
                        img_b64   = (
                            base64.b64encode(raw_bytes).decode("utf-8")
                            if isinstance(raw_bytes, (bytes, bytearray))
                            else raw_bytes
                        )
                        break

            if not img_b64:
                raise ValueError("Aucune image retournée par le modèle")

            logger.info("Image générée — model=%s course=%s mime=%s",
                        img_model, request.course_id, mime)
            return {
                "image_b64":  img_b64,
                "mime_type":  mime,
                "caption":    caption,
                "prompt":     image_prompt,
                "model_used": img_model
            }

        except Exception as e:
            logger.warning("Modèle %s échoué : %s", img_model, str(e))
            last_error = e
            continue

    logger.error("Tous les modèles image ont échoué. Dernier : %s", str(last_error))
    raise HTTPException(
        status_code=503,
        detail=(
            f"Aucun modèle Gemini image disponible sur ce compte. "
            f"Dernière erreur : {str(last_error)}"
        )
    )