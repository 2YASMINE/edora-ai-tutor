from fastapi import APIRouter, HTTPException
from models.schemas import AskRequest, AskResponse, SourceChunk
import uuid

router = APIRouter()

@router.post("/ask", response_model=AskResponse)
async def ask(request: AskRequest):
    # TODO: Phase 4 - RAG pipeline
    # TODO: Phase 5 - Gemini API call
    
    # Pour l'instant retourne une réponse vide
    return AskResponse(
        answer="Tutor AI - Coming Soon",
        conversation_id=request.conversation_id or str(uuid.uuid4()),
        sources=[],
        found_in_course=False
    )