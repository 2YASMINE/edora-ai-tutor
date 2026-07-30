import os
import uuid
from fastapi import APIRouter, HTTPException
from models.schemas import AskRequest, AskResponse, SourceChunk
from services.embeddings import get_embedding
from services.chroma_service import search_similar_chunks
from services.gemini import ask_gemini

router = APIRouter()

@router.post("/ask", response_model=AskResponse)
async def ask(request: AskRequest):
    """
    Reçoit la question de l'étudiant et retourne une réponse basée sur le cours.
    """
    # Étape 1 : Embedding de la question
    question_embedding = get_embedding(request.question)

    # Étape 2 : Recherche dans ChromaDB
    results = search_similar_chunks(
        course_id=request.course_id,
        query_embedding=question_embedding,
        n_results=3
    )

    # Étape 3 : Construire les chunks de contexte
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

    # Étape 4 : Convertir l'historique en format dict pour gemini.py
    history = [
        {"role": msg.role, "content": msg.content}
        for msg in (request.conversation_history or [])
    ]

    # Étape 5 : Appel Gemini
    gemini_result = ask_gemini(
        question=request.question,
        context_chunks=context_chunks,
        conversation_history=history
    )

    # Étape 6 : Gestion erreur Gemini
    if not gemini_result["success"]:
        raise HTTPException(
            status_code=503,
            detail=f"Erreur Gemini : {gemini_result.get('error', 'inconnue')}"
        )

    return AskResponse(
        answer=gemini_result["answer"],
        conversation_id=request.conversation_id or str(uuid.uuid4()),
        sources=sources,
        found_in_course=gemini_result["found_in_course"],
        chunks_used=gemini_result["chunks_used"]
    )