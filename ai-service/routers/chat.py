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
    get_student_level, save_student_level, quiz_already_done
)

router = APIRouter()

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
    score:           int   # score obtenu sur 10
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
    # Message très court (< 4 mots) = probablement pas pédagogique
    if len(q.split()) < 4:
        return any(kw in q for kw in SMALL_TALK_KEYWORDS)
    return False


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINT : GÉNÉRER LE QUIZ DE NIVEAU
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/level-quiz")
async def get_level_quiz(request: LevelQuizRequest):
    """
    Génère un quiz de 10 questions pour détecter le niveau de l'étudiant.
    Appelé par le frontend lors de la 1ère vraie question pédagogique.
    """
    # Vérifier si le quiz a déjà été fait
    if quiz_already_done(request.student_id, request.course_id):
        level_info = get_student_level(request.student_id, request.course_id)
        return {
            "already_done": True,
            "level":        level_info["level"],
            "score":        level_info["score"]
        }

    # Récupérer des chunks du cours pour générer le quiz
    # On utilise un embedding générique pour couvrir l'ensemble du cours
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

    # Générer le quiz via Gemini
    result = generate_level_quiz(chunks)
    if not result["success"]:
        raise HTTPException(status_code=503, detail="Impossible de générer le quiz de niveau.")

    return {
        "already_done": False,
        "quiz":         result["quiz"]
    }


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINT : SAUVEGARDER LE NIVEAU APRÈS LE QUIZ
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/level-save")
async def save_level(request: LevelSaveRequest):
    """
    Sauvegarde le niveau détecté après que l'étudiant a complété le quiz.
    """
    level = classify_level(request.score, request.total)
    success = save_student_level(
        user_id=request.student_id,
        course_id=request.course_id,
        conversation_id=request.conversation_id,
        level=level,
        score=request.score
    )
    if not success:
        raise HTTPException(status_code=500, detail="Erreur lors de la sauvegarde du niveau.")

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
    """Retourne le niveau actuel de l'étudiant pour un cours."""
    info = get_student_level(student_id, course_id)
    return info


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINT PRINCIPAL : /ask
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/ask", response_model=AskResponse)
async def ask(request: AskRequest):
    """
    Reçoit la question de l'étudiant et retourne une réponse basée sur le cours.
    Intègre le niveau étudiant dans le prompt si détecté.
    """
    # Étape 1 : Validation
    if len(request.question.strip()) == 0:
        raise HTTPException(status_code=400, detail="La question ne peut pas être vide.")
    if len(request.question) > 500:
        raise HTTPException(status_code=400, detail="Question trop longue (max 500 caractères).")

    # Étape 2 : Classification de la question
    task_type = classify_question(request.question)

    # Étape 3 : Récupérer le niveau étudiant (si déjà détecté)
    level_info = get_student_level(request.student_id, request.course_id)
    student_level = level_info.get("level")  # None si pas encore détecté

    # Étape 4 : Embedding de la question
    question_embedding = get_embedding(request.question)

    # Étape 5 : Nombre de chunks adapté au type de tâche
    N_CHUNKS = {
        "resume":    10,
        "quiz":       5,
        "expliquer":  5,
        "exemple":    3,
        "chat":       3,
    }
    n_results = N_CHUNKS.get(task_type, 3)

    # Étape 6 : Recherche ChromaDB
    results = search_similar_chunks(
        course_id=request.course_id,
        query_embedding=question_embedding,
        n_results=n_results
    )

    # Étape 7 : Construire chunks + sources
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
                chunk_excerpt=chunk["text"]   # texte complet
            ))

    # Étape 8 : Historique
    history = [
        {"role": msg.role, "content": msg.content}
        for msg in (request.conversation_history or [])
    ]

    # Étape 9 : Construire le task_type enrichi avec le niveau
    # Si un niveau est détecté, on le passe à ask_gemini qui l'injecte dans le prompt
    effective_task = task_type
    if student_level and task_type == "expliquer":
        # Pour les explications, le niveau impacte directement le prompt
        effective_task = f"expliquer_{student_level}"

    # Étape 10 : Appel Gemini
    gemini_result = ask_gemini(
        question=request.question,
        context_chunks=context_chunks,
        conversation_history=history,
        student_id=request.student_id,
        task_type=task_type,
        student_level=student_level   # nouveau paramètre
    )

    # Étape 11 : Gestion erreur
    if not gemini_result["success"]:
        raise HTTPException(
            status_code=503,
            detail=f"Erreur Gemini : {gemini_result.get('error', 'inconnue')}"
        )

    # Étape 12 : conversation_id
    conversation_id = request.conversation_id or str(uuid.uuid4())

    # Étape 13 : Sauvegarde MariaDB
    save_message(
        user_id=request.student_id,
        course_id=request.course_id,
        conversation_id=conversation_id,
        role="user",
        message=request.question
    )
    save_message(
        user_id=request.student_id,
        course_id=request.course_id,
        conversation_id=conversation_id,
        role="assistant",
        message=gemini_result["answer"]
    )

    return AskResponse(
        answer=gemini_result["answer"],
        conversation_id=conversation_id,
        sources=sources,
        found_in_course=gemini_result["found_in_course"],
        chunks_used=gemini_result["chunks_used"]
    )


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS HISTORIQUE (inchangés)
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/history")
async def get_conversation_history(conversation_id: str, course_id: int = 0):
    """Récupère les messages d'une conversation par son ID."""
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
    """Retourne la liste des conversations d'un étudiant dans un cours."""
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
    """Supprime tous les messages d'une conversation."""
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
