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