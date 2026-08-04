import os
import uuid
from fastapi import APIRouter, HTTPException
from models.schemas import AskRequest, AskResponse, SourceChunk
from services.embeddings import get_embedding
from services.chroma_service import search_similar_chunks
from services.gemini import ask_gemini
from services.history_service import save_message, get_history, get_user_history

router = APIRouter()

@router.post("/ask", response_model=AskResponse)
async def ask(request: AskRequest):
    question_embedding = get_embedding(request.question)
    results = search_similar_chunks(
        course_id=request.course_id,
        query_embedding=question_embedding,
        n_results=3
    )
    context_chunks = []
    sources = []
    if results:
        for chunk in results:
            context_chunks.append({"text": chunk["text"], "metadata": chunk["metadata"]})
            sources.append(SourceChunk(
                resource_name=chunk["metadata"].get("source", "cours"),
                chunk_excerpt=chunk["text"][:100] + "..."
            ))
    history = [
        {"role": msg.role, "content": msg.content}
        for msg in (request.conversation_history or [])
    ]
    gemini_result = ask_gemini(
        question=request.question,
        context_chunks=context_chunks,
        conversation_history=history
    )
    if not gemini_result["success"]:
        raise HTTPException(status_code=503, detail=f"Erreur Gemini : {gemini_result.get('error', 'inconnue')}")

    conversation_id = request.conversation_id or str(uuid.uuid4())

    save_message(user_id=request.student_id, course_id=request.course_id,
                 conversation_id=conversation_id, role="user", message=request.question)
    save_message(user_id=request.student_id, course_id=request.course_id,
                 conversation_id=conversation_id, role="assistant", message=gemini_result["answer"])

    return AskResponse(
        answer=gemini_result["answer"],
        conversation_id=conversation_id,
        sources=sources,
        found_in_course=gemini_result["found_in_course"],
        chunks_used=gemini_result["chunks_used"]
    )


# ── GET /history — messages d'une conversation ─────────────
@router.get("/history")
async def get_conversation_history(conversation_id: str, course_id: int = 0):
    try:
        messages = get_history(conversation_id)
        return {
            "conversation_id": conversation_id,
            "messages": [
                {"role": m["role"], "message": m["message"], "created_at": str(m["created_at"])}
                for m in messages
            ],
            "count": len(messages)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── GET /conversations — liste de toutes les conversations ─
@router.get("/conversations")
async def get_conversations(user_id: int = 0, course_id: int = 0):
    """
    Retourne la liste des conversations groupées par conversation_id.
    Chaque entrée : { conversation_id, first_message, last_message, created_at, message_count }
    """
    try:
        rows = get_user_history(user_id=user_id, course_id=course_id)
        if not rows:
            return {"conversations": []}

        # Grouper par conversation_id
        grouped = {}
        for row in rows:
            cid = row["conversation_id"]
            if cid not in grouped:
                grouped[cid] = []
            grouped[cid].append(row)

        conversations = []
        for cid, msgs in grouped.items():
            # Premier message user
            first_user = next((m for m in msgs if m["role"] == "user"), None)
            last_msg   = msgs[-1]
            conversations.append({
                "conversation_id": cid,
                "first_message":   first_user["message"][:60] + "..." if first_user and len(first_user["message"]) > 60 else (first_user["message"] if first_user else ""),
                "created_at":      str(msgs[0]["created_at"]),
                "message_count":   len(msgs)
            })

        # Trier par date décroissante (plus récent en premier)
        conversations.sort(key=lambda x: x["created_at"], reverse=True)

        return {"conversations": conversations}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── DELETE /conversation — supprimer une conversation ──────
@router.delete("/conversation/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """
    Supprime tous les messages d'une conversation par son ID.
    """
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