import httpx
import re
from bs4 import BeautifulSoup
import os
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

MOODLE_BASE_URL = os.getenv("MOODLE_BASE_URL", "http://localhost:8082")
MOODLE_WS_TOKEN = os.getenv("MOODLE_WS_TOKEN", "")
print("===== MOODLE EXTRACTOR LOADED =====")
print("ENV PATH:", env_path)
print("===================================")

async def extract_course_content(course_id: int) -> dict:
    """
    R├®cup├¿re et extrait le texte de toutes les ressources
    textuelles d'un cours Moodle.
    """
    # R├®cup├®rer la structure du cours
    course_contents = await _get_course_contents(course_id)
    if not course_contents["success"]:
        return {
            "success": False,
            "course_id": course_id,
            "sections": [],
            "full_text": "",
            "error": course_contents["error"]
        }

    # R├®cup├®rer toutes les pages du cours en un seul appel
    pages_by_id = await _get_all_pages(course_id)

    sections = []
    full_text_parts = []

    for section in course_contents["data"]:
        section_name = section.get("name", "Section sans titre")
        section_text_parts = []

        # R├®sum├® de section si pr├®sent
        summary = section.get("summary", "")
        if summary:
            clean_summary = _clean_html(summary)
            if clean_summary:
                section_text_parts.append(clean_summary)

        # Parcourir les modules
        for module in section.get("modules", []):
            modname = module.get("modname", "")
            module_name = module.get("name", "Ressource")
            module_text = ""

            if modname == "page":
                # Utiliser le contenu r├®cup├®r├® via mod_page_get_pages_by_courses
                instance_id = module.get("instance")
                if instance_id and instance_id in pages_by_id:
                    html_content = pages_by_id[instance_id].get("content", "")
                    module_text = _clean_html(html_content)

            elif modname in ("resource", "folder"):
                # Les fichiers upload├®s sont trait├®s par document_extractor
                module_text = f"[Fichier upload├® ÔÇö trait├® s├®par├®ment]"

            # Description de l'activit├® si pr├®sente
            description = module.get("description", "")
            if description and not module_text:
                module_text = _clean_html(description)

            if module_text and module_text.strip():
                section_text_parts.append(
                    f"[{module_name}]\n{module_text}"
                )

        section_text = "\n\n".join(section_text_parts)
        if section_text.strip():
            sections.append({
                "name": section_name,
                "text": section_text
            })
            full_text_parts.append(
                f"=== {section_name} ===\n{section_text}"
            )

    full_text = "\n\n".join(full_text_parts)

    if not full_text.strip():
        return {
            "success": False,
            "course_id": course_id,
            "sections": [],
            "full_text": "",
            "error": "Aucun contenu textuel trouv├® dans ce cours"
        }

    return {
        "success": True,
        "course_id": course_id,
        "sections": sections,
        "full_text": full_text,
        "error": None
    }


async def _get_course_contents(course_id: int) -> dict:
    """Structure compl├¿te du cours via l'API Moodle."""
    params = {
        "wstoken": MOODLE_WS_TOKEN,
        "wsfunction": "core_course_get_contents",
        "moodlewsrestformat": "json",
        "courseid": course_id
    }
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{MOODLE_BASE_URL}/webservice/rest/server.php",
                params=params
            )
            data = response.json()
            if isinstance(data, dict) and "exception" in data:
                return {"success": False, "data": [], "error": data.get("message")}
            return {"success": True, "data": data, "error": None}
    except Exception as e:
        return {"success": False, "data": [], "error": str(e)}


async def _get_all_pages(course_id: int) -> dict:
    """
    R├®cup├¿re le contenu HTML de toutes les pages du cours.
    Retourne un dict index├® par instance id : {instance_id: page_data}
    """
    params = {
        "wstoken": MOODLE_WS_TOKEN,
        "wsfunction": "mod_page_get_pages_by_courses",
        "moodlewsrestformat": "json",
        "courseids[0]": course_id
    }
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{MOODLE_BASE_URL}/webservice/rest/server.php",
                params=params
            )
            data = response.json()
            if isinstance(data, dict) and "exception" in data:
                return {}
            pages = data.get("pages", [])
            # Indexer par id (= instance id du module)
            return {page["id"]: page for page in pages}
    except Exception:
        return {}


def _clean_html(html: str) -> str:
    """Supprime les balises HTML et retourne le texte propre."""
    if not html or not html.strip():
        return ""
    try:
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style"]):
            tag.decompose()
        text = soup.get_text(separator="\n")
        lines = [line.strip() for line in text.splitlines()]
        return "\n".join(line for line in lines if line)
    except Exception:
        return re.sub(r"<[^>]+>", " ", html).strip()