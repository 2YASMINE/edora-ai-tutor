import os
import json
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.history_service import get_connection

logger = logging.getLogger(__name__)
router = APIRouter()

# ══════════════════════════════════════════════════════════════════════════════
# XP RULES
# ══════════════════════════════════════════════════════════════════════════════

XP_RULES = {
    "question":      5,   # Question posée
    "quiz_done":    20,   # Quiz complété
    "quiz_perfect": 50,   # Quiz parfait (10/10)
    "first_login":  10,   # Première connexion
}

BADGES_RULES = {
    "first_question":  {"xp": 0,   "questions": 1,  "label": "🌱 Première question"},
    "curious":         {"xp": 0,   "questions": 10, "label": "🔥 Curieux"},
    "quiz_master":     {"xp": 0,   "quizzes":   5,  "label": "🏆 Quiz Master"},
    "knowledge_seeker":{"xp": 100, "questions": 0,  "label": "📚 Chercheur de savoir"},
    "expert":          {"xp": 500, "questions": 0,  "label": "🚀 Expert"},
}

LEVELS = [
    {"name": "Bronze",   "min_xp": 0},
    {"name": "Argent",   "min_xp": 100},
    {"name": "Or",       "min_xp": 300},
    {"name": "Platine",  "min_xp": 600},
    {"name": "Diamant",  "min_xp": 1000},
]


def get_level(xp: int) -> str:
    level = LEVELS[0]["name"]
    for l in LEVELS:
        if xp >= l["min_xp"]:
            level = l["name"]
    return level


def check_badges(xp: int, questions: int, quizzes: int, current_badges: list) -> list:
    new_badges = []
    for badge_id, rule in BADGES_RULES.items():
        if badge_id in current_badges:
            continue
        earned = True
        if rule["xp"] > 0 and xp < rule["xp"]:
            earned = False
        if rule.get("questions", 0) > 0 and questions < rule["questions"]:
            earned = False
        if rule.get("quizzes", 0) > 0 and quizzes < rule["quizzes"]:
            earned = False
        if earned:
            new_badges.append({"id": badge_id, "label": rule["label"]})
    return new_badges


# ══════════════════════════════════════════════════════════════════════════════
# SCHEMAS
# ══════════════════════════════════════════════════════════════════════════════

class XpAddRequest(BaseModel):
    user_id:   int
    course_id: int
    action:    str  # "question", "quiz_done", "quiz_perfect"


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/xp")
async def get_xp(user_id: int, course_id: int):
    """Retourne XP, badges et niveau d'un étudiant."""
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT xp, badges, questions_count, quizzes_count
            FROM mdl_edora_xp
            WHERE user_id = %s AND course_id = %s
        """, (user_id, course_id))
        row = cursor.fetchone()
        cursor.close()
        conn.close()

        if not row:
            return {
                "xp": 0, "level": "Bronze",
                "badges": [], "questions_count": 0,
                "quizzes_count": 0, "next_level_xp": 100
            }

        xp = row["xp"]
        badges = json.loads(row["badges"] or "[]")
        level = get_level(xp)
        next_level_xp = next((l["min_xp"] for l in LEVELS if l["min_xp"] > xp), None)

        return {
            "xp":              xp,
            "level":           level,
            "badges":          badges,
            "questions_count": row["questions_count"],
            "quizzes_count":   row["quizzes_count"],
            "next_level_xp":   next_level_xp
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/xp/add")
async def add_xp(request: XpAddRequest):
    """Ajoute des XP et vérifie les nouveaux badges."""
    xp_gained = XP_RULES.get(request.action, 0)
    if xp_gained == 0:
        raise HTTPException(status_code=400, detail=f"Action inconnue : {request.action}")

    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        # Récupérer ou créer la ligne
        cursor.execute("""
            INSERT INTO mdl_edora_xp (user_id, course_id, xp, badges, questions_count, quizzes_count)
            VALUES (%s, %s, 0, '[]', 0, 0)
            ON DUPLICATE KEY UPDATE id = id
        """, (request.user_id, request.course_id))
        conn.commit()

        # Incrémenter selon l'action
        if request.action == "question":
            cursor.execute("""
                UPDATE mdl_edora_xp
                SET xp = xp + %s, questions_count = questions_count + 1
                WHERE user_id = %s AND course_id = %s
            """, (xp_gained, request.user_id, request.course_id))
        elif request.action in ["quiz_done", "quiz_perfect"]:
            cursor.execute("""
                UPDATE mdl_edora_xp
                SET xp = xp + %s, quizzes_count = quizzes_count + 1
                WHERE user_id = %s AND course_id = %s
            """, (xp_gained, request.user_id, request.course_id))
        conn.commit()

        # Récupérer les nouvelles valeurs
        cursor.execute("""
            SELECT xp, badges, questions_count, quizzes_count
            FROM mdl_edora_xp
            WHERE user_id = %s AND course_id = %s
        """, (request.user_id, request.course_id))
        row = cursor.fetchone()
        current_badges = json.loads(row["badges"] or "[]")
        badge_ids = [b["id"] for b in current_badges]

        # Vérifier nouveaux badges
        new_badges = check_badges(
            row["xp"], row["questions_count"],
            row["quizzes_count"], badge_ids
        )

        if new_badges:
            all_badges = current_badges + new_badges
            cursor.execute("""
                UPDATE mdl_edora_xp SET badges = %s
                WHERE user_id = %s AND course_id = %s
            """, (json.dumps(all_badges, ensure_ascii=False),
                  request.user_id, request.course_id))
            conn.commit()

        cursor.close()
        conn.close()

        return {
            "success":    True,
            "xp_gained":  xp_gained,
            "total_xp":   row["xp"],
            "level":      get_level(row["xp"]),
            "new_badges": new_badges
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))