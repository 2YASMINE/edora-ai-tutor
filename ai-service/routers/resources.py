import httpx
import os
import logging
import asyncio

from urllib.parse import urlparse, unquote
from fastapi import APIRouter, HTTPException, Request, BackgroundTasks, UploadFile, File, Form
from models.schemas import UploadResourceRequest, UploadResourceResponse
from services.document_extractor import extract_text
from services.chunker import chunk_text
from services.embeddings import get_embedding
from services.chroma_service import store_chunks

print("TOKEN UTILISE :", os.getenv("MOODLE_WS_TOKEN"))

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/upload-resource", response_model=UploadResourceResponse)
async def upload_resource(
    request: UploadResourceRequest,
    req: Request,
    background_tasks: BackgroundTasks
):
    logger.info("========== NOUVELLE RESSOURCE ==========")
    logger.info(f"IP SOURCE     : {req.client.host}")
    logger.info(f"Course ID     : {request.course_id}")
    logger.info(f"Resource ID   : {request.resource_id}")
    logger.info(f"Resource type : {request.resource_type}")
    logger.info(f"File URL      : {request.file_url}")

    background_tasks.add_task(
        process_resource,
        request.file_url,
        request.resource_id,
        request.resource_type,
        request.course_id
    )

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
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    logger.info("[BG] Rate limit atteint — pause 60s...")
                    await asyncio.sleep(60)
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


@router.post("/upload-file")
async def upload_file(
    file: UploadFile = File(...),
    course_id: int = Form(...)
):
    logger.info(f"[UPLOAD-FILE] Fichier reçu : {file.filename} | course_id={course_id}")

    tmp_dir = os.getenv("TMP_DIR", "C:/Users/wiki/edora_uploads")
    os.makedirs(tmp_dir, exist_ok=True)
    file_path = f"{tmp_dir}/{file.filename}"

    try:
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        extraction = extract_text(file_path)
        if not extraction["success"]:
            raise HTTPException(status_code=400, detail="Extraction échouée")

        chunks = chunk_text(
            text=extraction["text"],
            source=file.filename,
            course_id=course_id,
            resource_id=0
        )

        embedded_chunks = []
        for chunk in chunks:
            try:
                embedding = get_embedding(chunk.page_content)
                embedded_chunks.append({
                    "text": chunk.page_content,
                    "embedding": embedding,
                    "metadata": chunk.metadata
                })
                await asyncio.sleep(0.7)
            except Exception as e:
                logger.error(f"Erreur embedding : {str(e)}")
                continue

        result = store_chunks(
            course_id=course_id,
            embedded_chunks=embedded_chunks
        )

        logger.info(f"[UPLOAD-FILE] {result['chunks_stored']} chunks stockés")

        return {
            "status": "ok",
            "filename": file.filename,
            "chunks_created": result["chunks_stored"]
        }

    except Exception as e:
        logger.error(f"[UPLOAD-FILE] Erreur : {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


async def _download_file(file_url: str, resource_id: int, resource_type: str = "pdf") -> str:
    tmp_dir = os.getenv("TMP_DIR", "C:/Users/wiki/edora_uploads")
    os.makedirs(tmp_dir, exist_ok=True)

    moodle_url = os.getenv("MOODLE_INTERNAL_URL", "http://host.docker.internal:8082")
    ws_token = os.getenv("MOODLE_WS_TOKEN", "")
    download_method = os.getenv("DOWNLOAD_METHOD", "session")

    file_url = file_url.replace("http://host.docker.internal:8082", moodle_url)

    if download_method == "session":
        file_url = file_url.replace(f"tokenpluginfile.php/{ws_token}", "pluginfile.php")
        file_url = file_url.replace("/webservice/pluginfile.php", "/pluginfile.php")
        if "?token=" in file_url:
            file_url = file_url.split("?token=")[0]
        logger.info(f"URL NETTOYEE = {file_url}")

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
                import re
                login_url = f"{moodle_url}/login/index.php"
                login_page = await client.get(login_url)
                token_match = re.search(r'name="logintoken" value="([^"]+)"', login_page.text)
                login_token = token_match.group(1) if token_match else ""

                await client.post(login_url, data={
                    "username": os.getenv("MOODLE_ADMIN_USER", "admin"),
                    "password": os.getenv("MOODLE_ADMIN_PASSWORD", "Edora2026!"),
                    "logintoken": login_token
                })
                logger.info("Connexion Moodle effectuee via session")
                logger.info(f"Cookies obtenus : {dict(client.cookies)}")

            response = await client.get(file_url)
            logger.info(f"Reponse Moodle : HTTP {response.status_code}")
            response.raise_for_status()

            content = response.content
            logger.info(f"[BG] Taille fichier reçu : {len(content)} octets")
            logger.info(f"[BG] Premiers octets : {content[:20]}")

            if len(content) < 100:
                raise Exception(
                    f"Fichier trop petit ({len(content)} octets) — probablement une page d'erreur HTML"
                )

            if extension == ".pdf" and content[:4] != b'%PDF':
                logger.error(f"[BG] Contenu reçu (pas un PDF) : {content[:200]}")
                raise Exception("Le fichier téléchargé n'est pas un PDF valide")

            with open(file_path, "wb") as f:
                f.write(content)

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