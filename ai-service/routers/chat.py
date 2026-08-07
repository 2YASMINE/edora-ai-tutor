import os
import uuid
from fastapi import APIRouter, HTTPException
from models.schemas import AskRequest, AskResponse, SourceChunk
from services.embeddings import get_embedding
from services.chroma_service import search_similar_chunks
from services.gemini import ask_gemini, classify_question
from services.history_service import save_message, get_history

router = APIRouter()

@router.post("/ask", response_model=AskResponse)
async def ask(request: AskRequest):
    """
    Reçoit la question de l'étudiant et retourne une réponse basée sur le cours.
    """
    # Étape 1 : Valider longueur entrée (sécurité)
    if len(request.question.strip()) == 0:
        raise HTTPException(status_code=400, detail="La question ne peut pas être vide.")
    if len(request.question) > 500:
        raise HTTPException(status_code=400, detail="Question trop longue (max 500 caractères).")

    # Étape 2 : Classifier la question en amont
    task_type = classify_question(request.question)

    # Étape 3 : Embedding de la question
    question_embedding = get_embedding(request.question)

    # Étape 4 : Recherche dans ChromaDB (filtrée par course_id)
    results = search_similar_chunks(
        course_id=request.course_id,
        query_embedding=question_embedding,
        n_results=3
    )

    # Étape 5 : Construire les chunks de contexte
    context_chunks = []
    sources = []

    if results:
        for chunk in results:
            context_chunks.append({
                "text": chunk["text"],
                "metadata": chunk["metadata"]
            })
            sources.append(SourceChunk(
                resource_name=chunk["metadata"].get("source", "cours"),
                chunk_excerpt=chunk["text"][:100] + "..."
            ))

    # Étape 6 : Convertir l'historique en format dict
    history = [
        {"role": msg.role, "content": msg.content}
        for msg in (request.conversation_history or [])
    ]

    # Étape 7 : Appel Gemini avec task_type + student_id (pseudonymisé dans gemini.py)
    gemini_result = ask_gemini(
        question=request.question,
        context_chunks=context_chunks,
        conversation_history=history,
        student_id=request.student_id,
        task_type=task_type
    )

    # Étape 8 : Gestion erreur Gemini
    if not gemini_result["success"]:
        raise HTTPException(
            status_code=503,
            detail=f"Erreur Gemini : {gemini_result.get('error', 'inconnue')}"
        )

    # Étape 9 : Générer conversation_id
    conversation_id = request.conversation_id or str(uuid.uuid4())

    # Étape 10 : Sauvegarder dans MariaDB
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