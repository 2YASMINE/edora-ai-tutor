import httpx
import os
from fastapi import APIRouter, HTTPException
from models.schemas import UploadResourceRequest, UploadResourceResponse
from services.document_extractor import extract_text

router = APIRouter()


@router.post("/upload-resource", response_model=UploadResourceResponse)
async def upload_resource(request: UploadResourceRequest):
    """
    Reçoit une ressource Moodle, télécharge le fichier,
    et extrait son texte selon le format détecté.
    Phase 3 : extraction uniquement (chunking + ChromaDB en Phase 4)
    """

    # Étape 1 — Télécharger le fichier depuis Moodle
    file_path = await _download_file(request.file_url, request.resource_id)

    # Étape 2 — Extraire le texte
    result = extract_text(file_path)

    # Étape 3 — Nettoyer le fichier temporaire
    if os.path.exists(file_path):
        os.remove(file_path)

    # Étape 4 — Retourner le résultat
    if not result["success"]:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "extraction_failed",
                "message": result["error"],
                "format": result["format"]
            }
        )

    # Pour l'instant on retourne juste le statut d'extraction
    # chunks_created sera renseigné en Phase 4 (ChromaDB)
    return UploadResourceResponse(
        status="extracted",
        resource_id=request.resource_id,
        chunks_created=None
    )


async def _download_file(file_url: str, resource_id: int) -> str:
    """
    Télécharge un fichier depuis une URL Moodle
    et le sauvegarde temporairement.

    Returns:
        Chemin local du fichier téléchargé
    """
    # Dossier temporaire pour les fichiers en cours de traitement
    tmp_dir = "/tmp/edora_uploads"
    os.makedirs(tmp_dir, exist_ok=True)

    # Déduire l'extension depuis l'URL
    extension = os.path.splitext(file_url.split("?")[0])[1].lower()
    if not extension:
        extension = ".pdf"  # fallback par défaut

    file_path = f"{tmp_dir}/resource_{resource_id}{extension}"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(file_url)
            response.raise_for_status()

            with open(file_path, "wb") as f:
                f.write(response.content)

        return file_path

    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "file_not_found",
                "message": f"Impossible de télécharger le fichier depuis Moodle : {str(e)}"
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "download_failed",
                "message": f"Erreur lors du téléchargement : {str(e)}"
            }
        )