import os
import mysql.connector
from dotenv import load_dotenv
import logging

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '..', '.env'))
logger = logging.getLogger("edora.history")


def get_connection():
    """
    Crée et retourne une connexion mysql.connector vers la base MariaDB Moodle.

    Les paramètres de connexion sont lus depuis les variables d'environnement :
    MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_ROOT_PASSWORD, MYSQL_DATABASE.

    Returns:
        Objet connexion mysql.connector actif.

    Raises:
        mysql.connector.Error: Si la connexion échoue (hôte inaccessible, auth, etc.).
    """
    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST", "localhost"),
        port=int(os.getenv("MYSQL_PORT", "3307")),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_ROOT_PASSWORD", ""),
        database=os.getenv("MYSQL_DATABASE", "moodle_db")
    )


def save_message(user_id: int, course_id: int, conversation_id: str, role: str, message: str):
    """
    Insère un message dans la table `edora_conversations`.

    Ouvre une connexion, exécute l'INSERT, commite et ferme.
    En cas d'erreur, logue sans lever d'exception pour ne pas bloquer le flux principal.

    Args:
        user_id:         ID Moodle de l'étudiant.
        course_id:       ID du cours Moodle.
        conversation_id: UUID de la conversation (généré côté router si absent).
        role:            "user" ou "assistant".
        message:         Contenu textuel du message.
    """
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
    """
    Récupère tous les messages d'une conversation triés par date croissante.

    Args:
        conversation_id: UUID de la conversation.

    Returns:
        Liste de dicts {"role", "message", "created_at"} ordonnés ASC par created_at.
        Liste vide en cas d'erreur ou de conversation inexistante.
    """
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
    """
    Récupère tous les messages d'un étudiant dans un cours donné, toutes conversations confondues.

    Utilisé par l'endpoint GET /conversations pour reconstruire la liste des conversations.

    Args:
        user_id:   ID Moodle de l'étudiant.
        course_id: ID du cours Moodle.

    Returns:
        Liste de dicts {"conversation_id", "role", "message", "created_at"} triés ASC.
        Liste vide en cas d'erreur.
    """
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
    Récupère le niveau pédagogique détecté d'un étudiant pour un cours donné.

    Effectue deux requêtes successives si nécessaire :
    1. Cherche la ligne la plus récente où student_level IS NOT NULL.
    2. Si aucune, vérifie si level_quiz_done = 1 existe (quiz fait mais niveau non stocké).

    Args:
        user_id:   ID Moodle de l'étudiant.
        course_id: ID du cours Moodle.

    Returns:
        {"level": str|None, "score": int|None, "quiz_done": bool}
        En cas d'erreur : {"level": None, "score": None, "quiz_done": False}
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
    Persiste le niveau détecté de l'étudiant après le quiz de diagnostic.

    Met à jour toutes les lignes existantes de l'étudiant dans le cours
    (student_level, level_score, level_quiz_done = 1).
    Si aucune ligne n'existe encore (rowcount == 0), insère une ligne de référence
    avec role='assistant' et message='Quiz de niveau complété'.

    Args:
        user_id:         ID Moodle de l'étudiant.
        course_id:       ID du cours Moodle.
        conversation_id: UUID de la conversation courante.
        level:           Niveau classifié ("debutant", "intermediaire", "avance").
        score:           Score obtenu au quiz (nombre de bonnes réponses sur 10).

    Returns:
        True si la sauvegarde a réussi, False en cas d'exception.
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
                VALUES (%s, %s, %s, 'assistant',
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
     """
    Vérifie rapidement si l'étudiant a déjà complété le quiz de niveau pour ce cours.

    Effectue un SELECT 1 ... LIMIT 1 sur level_quiz_done = 1 pour minimiser la charge.

    Args:
        user_id:   ID Moodle de l'étudiant.
        course_id: ID du cours Moodle.

    Returns:
        True si une ligne avec level_quiz_done = 1 existe, False sinon ou en cas d'erreur.
    """
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
    Compresse l'historique de conversation si celui-ci dépasse max_turns échanges.

    Un "tour" = 1 message user + 1 message assistant = 2 entrées.
    Si len(history) > max_turns * 2 :
      - Les messages anciens sont résumés via summarize_history (gemini.py).
      - Le résumé est injecté comme premier message avec role="system".
      - Les max_turns * 2 messages récents sont conservés intacts.
    Si le résumé échoue, seuls les messages récents sont retournés (sans message system).

    Args:
        history:    Liste de dicts {"role": str, "content": str}.
        max_turns:  Nombre maximum de tours à conserver sans compression (défaut : 8).

    Returns:
        Historique potentiellement compressé :
        [{"role": "system", "content": "Résumé..."}] + messages_récents
        ou simplement messages_récents si la compression a échoué.
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