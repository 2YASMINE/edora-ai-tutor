import os
import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from models.schemas import AskRequest, AskResponse, SourceChunk
from services.embeddings import get_embedding
from services.chroma_service import search_similar_chunks
from services.gemini import (
    ask_gemini, classify_question,
    generate_level_quiz, classify_level, get_level_system_prompt
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
    a, b = np.array(v1), np.array(v2)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def get_cached_response(question_embedding: list, course_id: int) -> dict | None:
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
    "c'est quoi edora", "tu peux", "tu es"
]


def is_small_talk(question: str) -> bool:
    """Détecte si la question est un message simple sans intention pédagogique."""
    q = question.lower().strip()
    if len(q.split()) < 4:
        return any(kw in q for kw in SMALL_TALK_KEYWORDS)
    return False


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINT : GÉNÉRER LE QUIZ DE NIVEAU
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/level-quiz")
async def get_level_quiz(request: LevelQuizRequest):
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


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINT : RÉCUPÉRER LE NIVEAU D'UN ÉTUDIANT
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/student-level")
async def get_level(student_id: int = 0, course_id: int = 0):
    info = get_student_level(student_id, course_id)
    return info


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINT PRINCIPAL : /ask
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/ask", response_model=AskResponse)
async def ask(request: AskRequest):
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
    try:
        from services.history_service import get_connection
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM edora_conversations WHERE conversation_id = %s",
            (conversation_id,)
        )
        deleted = cursor.rowcount
        conn.commit()
        cursor.close()
        conn.close()
        return {"success": True, "deleted_messages": deleted}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))