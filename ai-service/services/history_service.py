import os
import mysql.connector
from dotenv import load_dotenv
import logging

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '..', '.env'))
logger = logging.getLogger("edora.history")


def get_connection():
    """Connexion à MariaDB."""
    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST", "localhost"),
        port=int(os.getenv("MYSQL_PORT", "3307")),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_ROOT_PASSWORD", ""),
        database=os.getenv("MYSQL_DATABASE", "moodle_db")
    )


def save_message(user_id: int, course_id: int, conversation_id: str, role: str, message: str):
    """Sauvegarde un message dans la table edora_conversations."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO edora_conversations
            (user_id, course_id, conversation_id, role, message)
            VALUES (%s, %s, %s, %s, %s)
        """, (user_id, course_id, conversation_id, role, message))
        conn.commit()
        cursor.close()
        conn.close()
        logger.info(f"Message sauvegardé — conversation_id={conversation_id} role={role}")
    except Exception as e:
        logger.error(f"Erreur sauvegarde message : {str(e)}")


def get_history(conversation_id: str) -> list:
    """Récupère l'historique d'une conversation."""
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT role, message, created_at
            FROM edora_conversations
            WHERE conversation_id = %s
            ORDER BY created_at ASC
        """, (conversation_id,))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return rows
    except Exception as e:
        logger.error(f"Erreur récupération historique : {str(e)}")
        return []


def get_user_history(user_id: int, course_id: int) -> list:
    """Récupère toutes les conversations d'un étudiant dans un cours."""
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT conversation_id, role, message, created_at
            FROM edora_conversations
            WHERE user_id = %s AND course_id = %s
            ORDER BY created_at ASC
        """, (user_id, course_id))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return rows
    except Exception as e:
        logger.error(f"Erreur récupération historique utilisateur : {str(e)}")
        return []


# ══════════════════════════════════════════════════════════════════════════════
# GESTION DU NIVEAU ÉTUDIANT
# ══════════════════════════════════════════════════════════════════════════════

def get_student_level(user_id: int, course_id: int) -> dict:
    """
    Récupère le niveau détecté d'un étudiant pour un cours donné.
    Retourne : {level, score, quiz_done} ou {level: None, quiz_done: False}
    """
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT student_level, level_score, level_quiz_done
            FROM edora_conversations
            WHERE user_id = %s AND course_id = %s
              AND student_level IS NOT NULL
            ORDER BY created_at DESC
            LIMIT 1
        """, (user_id, course_id))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        if row:
            return {
                "level":     row["student_level"],
                "score":     row["level_score"],
                "quiz_done": bool(row["level_quiz_done"])
            }
        # Vérifier si le quiz a été fait (même sans niveau stocké)
        conn2 = get_connection()
        cursor2 = conn2.cursor(dictionary=True)
        cursor2.execute("""
            SELECT level_quiz_done
            FROM edora_conversations
            WHERE user_id = %s AND course_id = %s
              AND level_quiz_done = 1
            LIMIT 1
        """, (user_id, course_id))
        row2 = cursor2.fetchone()
        cursor2.close()
        conn2.close()
        return {
            "level":     None,
            "score":     None,
            "quiz_done": bool(row2) if row2 else False
        }
    except Exception as e:
        logger.error(f"Erreur récupération niveau étudiant : {str(e)}")
        return {"level": None, "score": None, "quiz_done": False}


def save_student_level(user_id: int, course_id: int,
                       conversation_id: str, level: str, score: int):
    """
    Sauvegarde le niveau détecté de l'étudiant.
    Met à jour toutes les lignes de la conversation courante
    et marque le quiz comme complété.
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Mettre à jour la conversation courante
        cursor.execute("""
            UPDATE edora_conversations
            SET student_level   = %s,
                level_score     = %s,
                level_quiz_done = 1
            WHERE user_id = %s AND course_id = %s
        """, (level, score, user_id, course_id))

        # Si aucune ligne n'existe encore (première interaction),
        # insérer une ligne de référence
        if cursor.rowcount == 0:
            cursor.execute("""
                INSERT INTO edora_conversations
                (user_id, course_id, conversation_id, role,
                 message, student_level, level_score, level_quiz_done)
                VALUES (%s, %s, %s, 'system',
                        'Quiz de niveau complété', %s, %s, 1)
            """, (user_id, course_id, conversation_id, level, score))

        conn.commit()
        cursor.close()
        conn.close()
        logger.info(
            f"Niveau étudiant sauvegardé — user_id={user_id} "
            f"course_id={course_id} level={level} score={score}/10"
        )
        return True
    except Exception as e:
        logger.error(f"Erreur sauvegarde niveau étudiant : {str(e)}")
        return False


def quiz_already_done(user_id: int, course_id: int) -> bool:
    """Vérifie rapidement si l'étudiant a déjà fait le quiz de niveau."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 1 FROM edora_conversations
            WHERE user_id = %s AND course_id = %s AND level_quiz_done = 1
            LIMIT 1
        """, (user_id, course_id))
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        return result is not None
    except Exception as e:
        logger.error(f"Erreur vérification quiz niveau : {str(e)}")
        return False

def compress_history(history: list, max_turns: int = 8) -> list:
    """
    Si l'historique dépasse max_turns échanges (user+assistant),
    résume les anciens tours et les remplace par un message system.
    
    history : liste de {"role": ..., "content": ...}
    Retourne : historique compressé
    """
    # Un "tour" = 1 message user + 1 message assistant = 2 entrées
    max_messages = max_turns * 2

    if len(history) <= max_messages:
        return history  # pas besoin de compresser

    # Séparer : anciens tours à résumer / tours récents à garder
    old_messages  = history[:-max_messages]
    recent_messages = history[-max_messages:]

    # Résumer les anciens tours via Gemini
    from services.gemini import summarize_history
    summary_text = summarize_history(old_messages)

    if not summary_text:
        # Si le résumé échoue, on garde juste les messages récents
        logger.warning("Résumé historique échoué — on garde uniquement les %d derniers messages", max_messages)
        return recent_messages

    # Construire l'historique compressé
    compressed = [
        {"role": "system", "content": f"Résumé des échanges précédents : {summary_text}"}
    ] + recent_messages

    logger.info(
        "Historique compressé — %d anciens messages → 1 résumé + %d récents",
        len(old_messages), len(recent_messages)
    )
    return compressed