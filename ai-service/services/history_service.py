"""
history_service.py — Gestion de l'historique des conversations et des niveaux étudiants.

Ce module fournit toutes les opérations MariaDB liées aux conversations Edora :
- Sauvegarde et récupération des messages (table mdl_edora_conversations)
- Gestion du niveau pédagogique détecté par quiz (colonnes student_level, level_score)
- Compression de l'historique long pour maîtriser les coûts Gemini
"""

import os
import mysql.connector
from dotenv import load_dotenv
import logging

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '..', '.env'))
logger = logging.getLogger("edora.history")


def get_connection():
    """
    Ouvre et retourne une connexion MariaDB à partir des variables d'environnement.

    Utilise mysql.connector avec les paramètres définis dans le .env :
    MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_ROOT_PASSWORD, MYSQL_DATABASE.

    Returns:
        Connexion mysql.connector active. L'appelant est responsable de la fermer.

    Raises:
        mysql.connector.Error: Si la connexion échoue (hôte injoignable, credentials invalides).
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
    Sauvegarde un message dans la table mdl_edora_conversations.

    Appelée deux fois par question : une fois pour le message "user"
    (question de l'étudiant) et une fois pour le message "assistant"
    (réponse d'Edo). Le conversation_id permet de regrouper les messages
    d'une même session de chat.

    Args:
        user_id:         Identifiant Moodle de l'étudiant (vrai ID, pas pseudonymisé).
        course_id:       Identifiant du cours Moodle.
        conversation_id: UUID unique de la conversation (ex: "conv-1786710816896").
        role:            Rôle de l'auteur du message — "user" | "assistant" | "system".
        message:         Contenu textuel du message.
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO mdl_edora_conversations
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
    Récupère tous les messages d'une conversation dans l'ordre chronologique.

    Utilisée par l'endpoint GET /history pour afficher l'historique complet
    d'une conversation dans l'interface Moodle.

    Args:
        conversation_id: UUID de la conversation à récupérer.

    Returns:
        Liste de dicts {"role": str, "message": str, "created_at": datetime},
        triée par ordre chronologique croissant. Liste vide si erreur ou introuvable.
    """
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT role, message, created_at
            FROM mdl_edora_conversations
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
    Récupère toutes les conversations d'un étudiant dans un cours donné.

    Utilisée par l'endpoint GET /conversations pour afficher la liste
    des conversations dans le panneau historique de l'interface chat.

    Args:
        user_id:   Identifiant Moodle de l'étudiant.
        course_id: Identifiant du cours — filtre les conversations au cours actif.

    Returns:
        Liste de dicts {"conversation_id", "role", "message", "created_at"},
        triée par ordre chronologique. Liste vide si erreur ou aucune conversation.
    """
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT conversation_id, role, message, created_at
            FROM mdl_edora_conversations
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
    Récupère le niveau pédagogique détecté d'un étudiant pour un cours.

    Interroge la table mdl_edora_conversations sur les colonnes student_level,
    level_score, level_quiz_done. Le niveau est persisté après le quiz initial
    et réutilisé à chaque session pour adapter les prompts Gemini.

    Args:
        user_id:   Identifiant Moodle de l'étudiant.
        course_id: Identifiant du cours.

    Returns:
        Dict avec trois clés :
        - "level": str | None — "debutant" | "intermediaire" | "avance" | None
        - "score": int | None — Score obtenu au quiz (sur 10)
        - "quiz_done": bool — True si le quiz a été complété (même sans niveau stocké)
    """
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT student_level, level_score, level_quiz_done
            FROM mdl_edora_conversations
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
        conn2 = get_connection()
        cursor2 = conn2.cursor(dictionary=True)
        cursor2.execute("""
            SELECT level_quiz_done
            FROM mdl_edora_conversations
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
    Sauvegarde le niveau pédagogique détecté après la complétion du quiz.

    Met à jour toutes les lignes existantes de l'étudiant dans ce cours
    (UPDATE) et marque level_quiz_done=1. Si l'étudiant n'a aucune ligne
    existante (première interaction), insère une ligne de référence système.

    Args:
        user_id:         Identifiant Moodle de l'étudiant.
        course_id:       Identifiant du cours.
        conversation_id: UUID de la conversation active lors du quiz.
        level:           Niveau calculé — "debutant" | "intermediaire" | "avance".
        score:           Nombre de bonnes réponses obtenues (sur 10).

    Returns:
        True si la sauvegarde a réussi, False en cas d'erreur.
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE mdl_edora_conversations
            SET student_level   = %s,
                level_score     = %s,
                level_quiz_done = 1
            WHERE user_id = %s AND course_id = %s
        """, (level, score, user_id, course_id))
        if cursor.rowcount == 0:
            cursor.execute("""
                INSERT INTO mdl_edora_conversations
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
    Vérifie rapidement si l'étudiant a déjà complété le quiz de niveau.

    Utilisée au début de checkAndTriggerLevelQuiz() côté frontend et dans
    l'endpoint /level-quiz côté backend pour éviter de re-déclencher le quiz
    à chaque nouvelle session.

    Args:
        user_id:   Identifiant Moodle de l'étudiant.
        course_id: Identifiant du cours.

    Returns:
        True si une ligne avec level_quiz_done=1 existe pour cet étudiant/cours.
        False si le quiz n'a pas encore été fait ou en cas d'erreur.
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 1 FROM mdl_edora_conversations
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
    Compresse l'historique de conversation quand il dépasse le seuil de tours.

    Évite la croissance quadratique du coût tokens sur les longues conversations.
    Si l'historique dépasse max_turns échanges (= max_turns * 2 messages),
    les messages anciens sont résumés via summarize_history() et remplacés
    par un seul message system contenant le résumé.

    Exemple avec max_turns=8 et 20 messages dans history :
    - old_messages  = messages[0:4]   (les 4 anciens)
    - recent_messages = messages[4:]  (les 16 récents conservés)
    - Résultat : [{"role": "system", "content": "Résumé: ..."}, ...16 messages récents]

    Args:
        history:   Liste complète de messages {"role": str, "content": str}.
                   Contient les messages déjà envoyés par le frontend.
        max_turns: Nombre maximum d'échanges (user+assistant) avant compression.
                   Un échange = 2 messages. Défaut : 8 (= 16 messages max).

    Returns:
        Liste compressée avec un message system de résumé en tête (si compression),
        ou la liste originale si elle n'excède pas le seuil.
        En cas d'échec du résumé, retourne uniquement les messages récents.
    """
    max_messages = max_turns * 2
    if len(history) <= max_messages:
        return history
    old_messages    = history[:-max_messages]
    recent_messages = history[-max_messages:]
    from services.gemini import summarize_history
    summary_text = summarize_history(old_messages)
    if not summary_text:
        logger.warning("Résumé historique échoué — on garde uniquement les %d derniers messages", max_messages)
        return recent_messages
    compressed = [
        {"role": "system", "content": f"Résumé des échanges précédents : {summary_text}"}
    ] + recent_messages
    logger.info(
        "Historique compressé — %d anciens messages → 1 résumé + %d récents",
        len(old_messages), len(recent_messages)
    )
    return compressed