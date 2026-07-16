from fastapi import APIRouter, HTTPException
from models.schemas import UploadResourceRequest, UploadResourceResponse

router = APIRouter()

@router.post("/upload-resource", response_model=UploadResourceResponse)
async def upload_resource(request: UploadResourceRequest):
    # TODO: Phase 3 - Extraction PDF + chunking + ChromaDB
    
    return UploadResourceResponse(
        status="processing",
        resource_id=request.resource_id,
        chunks_created=None
    )