from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.chroma_service import search_similar_chunks
from services.embeddings import get_embedding
from services.gemini import generate_flashcards
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


class FlashcardsRequest(BaseModel):
    course_id: int
    nb: int = 8


@router.post("/flashcards")
async def generate_flashcards_endpoint(req: FlashcardsRequest):
    try:
        query_vec = get_embedding("concepts importants résumé cours")
        chunks = search_similar_chunks(
            course_id=req.course_id,
            query_embedding=query_vec,
            n_results=12
        )

        if not chunks:
            raise HTTPException(status_code=404, detail="Aucun contenu indexé pour ce cours.")

        result = generate_flashcards(chunks)

        if not result["success"]:
            raise HTTPException(status_code=503, detail=result.get("error", "Erreur Gemini"))

        return {"flashcards": result["flashcards"], "course_id": req.course_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur /flashcards: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))