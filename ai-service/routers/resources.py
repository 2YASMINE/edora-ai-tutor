import httpx
import os
import logging
import asyncio

from urllib.parse import urlparse, unquote
from fastapi import APIRouter, HTTPException, Request, BackgroundTasks
from models.schemas import UploadResourceRequest, UploadResourceResponse
from services.document_extractor import extract_text
from services.chunker import chunk_text
from services.embeddings import get_embedding
from services.chroma_service import store_chunks
import os

print("TOKEN UTILISE :", os.getenv("MOODLE_WS_TOKEN"))

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/upload-resource", response_model=UploadResourceResponse)
async def upload_resource(
    request: UploadResourceRequest,
    req: Request,
    background_tasks: BackgroundTasks
):
    """
    Reçoit la ressource Moodle et repond immediatement.
    Le traitement lourd (extraction, embeddings, ChromaDB)
    se fait en arriere-plan pour ne pas bloquer Moodle.
    """
    logger.info("========== NOUVELLE RESSOURCE ==========")
    logger.info(f"IP SOURCE     : {req.client.host}")
    logger.info(f"Course ID     : {request.course_id}")
    logger.info(f"Resource ID   : {request.resource_id}")
    logger.info(f"Resource type : {request.resource_type}")
    logger.info(f"File URL      : {request.file_url}")

    # Lancer le traitement en arriere-plan
    background_tasks.add_task(
        process_resource,
        request.file_url,
        request.resource_id,
        request.resource_type,
        request.course_id
    )

    # Repondre immediatement a Moodle (evite le timeout de 10s)
    return UploadResourceResponse(
        status="processing",
        resource_id=request.resource_id,
        chunks_created=None
    )


async def process_resource(
    file_url: str,
    resource_id: int,
    resource_type: str,
    course_id: int
):
    """
    Pipeline complet en arriere-plan :
    1. Telecharger le fichier depuis Moodle
    2. Extraire le texte
    3. Chunker le texte
    4. Generer les embeddings (avec pause pour rate limit)
    5. Stocker dans ChromaDB
    """
    file_path = None

    try:
        # ── Etape 1 : Telecharger ──
        file_path = await _download_file(file_url, resource_id, resource_type)
        logger.info(f"[BG] Fichier telecharge : {file_path}")

        # ── Etape 2 : Extraire le texte ──
        extraction = extract_text(file_path)
        logger.info(f"[BG] Extraction : succes={extraction['success']} format={extraction.get('format')}")

        if not extraction["success"]:
            logger.error(f"[BG] Extraction echouee : {extraction['error']}")
            return

        # ── Etape 3 : Chunking ──
        chunks = chunk_text(
            text=extraction["text"],
            source=file_url.split("/")[-1].split("?")[0],
            course_id=course_id,
            resource_id=resource_id
        )
        logger.info(f"[BG] {len(chunks)} chunks crees")

        if not chunks:
            logger.error("[BG] Aucun chunk genere")
            return

        # ── Etape 4 : Embeddings avec rate limiting ──
        # Gemini free tier : 100 req/min → pause de 0.7s entre chaque appel
        embedded_chunks = []
        for i, chunk in enumerate(chunks):
            logger.info(f"[BG] Embedding {i+1}/{len(chunks)}...")
            try:
                embedding = get_embedding(chunk.page_content)
                embedded_chunks.append({
                    "text": chunk.page_content,
                    "embedding": embedding,
                    "metadata": chunk.metadata
                })
            except Exception as e:
                logger.error(f"[BG] Erreur embedding chunk {i+1} : {str(e)}")
                # Pause plus longue si rate limit atteint
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    logger.info("[BG] Rate limit atteint — pause 60s...")
                    await asyncio.sleep(60)
                    # Reessayer ce chunk
                    try:
                        embedding = get_embedding(chunk.page_content)
                        embedded_chunks.append({
                            "text": chunk.page_content,
                            "embedding": embedding,
                            "metadata": chunk.metadata
                        })
                    except Exception as e2:
                        logger.error(f"[BG] Echec definitif chunk {i+1} : {str(e2)}")
                        continue

            # Pause entre chaque appel pour respecter 100 req/min
            await asyncio.sleep(0.7)

        logger.info(f"[BG] {len(embedded_chunks)} embeddings generes")

        if not embedded_chunks:
            logger.error("[BG] Aucun embedding genere")
            return

        # ── Etape 5 : Stockage ChromaDB ──
        result = store_chunks(
            course_id=course_id,
            embedded_chunks=embedded_chunks
        )
        logger.info(f"[BG] ChromaDB : {result['chunks_stored']} chunks stockes dans '{result['collection_name']}'")

        if result["success"]:
            logger.info(f"[BG] ===== INDEXATION TERMINEE : resource_{resource_id} =====")
        else:
            logger.error(f"[BG] Erreur ChromaDB : {result['error']}")

    except Exception as e:
        logger.error(f"[BG] Erreur inattendue : {str(e)}")

    finally:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"[BG] Fichier temporaire supprime : {file_path}")


async def _download_file(file_url: str, resource_id: int, resource_type: str = "pdf") -> str:
    """
    Telecharge un fichier depuis une URL Moodle authentifiee.
    DOWNLOAD_METHOD=session → session login (Windows natif)
    DOWNLOAD_METHOD=token   → tokenpluginfile direct
    """
    tmp_dir = os.getenv("TMP_DIR", "C:/Users/wiki/edora_uploads")
    os.makedirs(tmp_dir, exist_ok=True)

    moodle_url = os.getenv("MOODLE_INTERNAL_URL", "http://host.docker.internal:8082")
    ws_token = os.getenv("MOODLE_WS_TOKEN", "")
    download_method = os.getenv("DOWNLOAD_METHOD", "session")

    # Remplacer host.docker.internal par l'URL locale
    file_url = file_url.replace("http://host.docker.internal:8082", moodle_url)

    if download_method == "session":
        # Convertir tokenpluginfile → pluginfile pour session login
        file_url = file_url.replace(f"tokenpluginfile.php/{ws_token}", "pluginfile.php")

    logger.info(f"DOWNLOAD_METHOD = {download_method}")
    logger.info(f"URL FINALE = {file_url}")

    parsed_url = urlparse(file_url)
    decoded_path = unquote(parsed_url.path)
    extension = os.path.splitext(decoded_path)[1].lower()

    logger.info(f"Extension detectee : {extension}")

    if not extension:
        fallback_map = {
            "pdf": ".pdf",
            "docx": ".docx",
            "pptx": ".pptx",
            "txt": ".txt"
        }
        extension = fallback_map.get(resource_type.lower(), ".pdf")

    file_path = f"{tmp_dir}/resource_{resource_id}{extension}"

    try:
        async with httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True
        ) as client:

            if download_method == "session":
                # Etape 1 : Recuperer le logintoken
                import re
                login_url = f"{moodle_url}/login/index.php"
                login_page = await client.get(login_url)
                token_match = re.search(r'name="logintoken" value="([^"]+)"', login_page.text)
                login_token = token_match.group(1) if token_match else ""

                # Etape 2 : Se connecter
                await client.post(login_url, data={
                    "username": os.getenv("MOODLE_ADMIN_USER", "admin"),
                    "password": os.getenv("MOODLE_ADMIN_PASSWORD", "Edora2026!"),
                    "logintoken": login_token
                })
                logger.info("Connexion Moodle effectuee via session")

            # Telecharger le fichier
            response = await client.get(file_url)
            logger.info(f"Reponse Moodle : HTTP {response.status_code}")
            response.raise_for_status()

            with open(file_path, "wb") as f:
                f.write(response.content)

        return file_path

    except httpx.HTTPStatusError as e:
        logger.error(f"Moodle a retourne une erreur : {e.response.status_code}")
        raise HTTPException(status_code=404, detail={
            "error": "file_not_found",
            "message": "Impossible de telecharger le fichier depuis Moodle.",
            "moodle_status": e.response.status_code
        })

    except httpx.RequestError as e:
        logger.error(f"Erreur connexion Moodle : {str(e)}")
        raise HTTPException(status_code=500, detail={
            "error": "connection_failed",
            "message": f"Impossible de contacter Moodle : {str(e)}"
        })

    except Exception as e:
        logger.error(f"Erreur telechargement : {str(e)}")
        raise HTTPException(status_code=500, detail={
            "error": "download_failed",
            "message": str(e)
        })