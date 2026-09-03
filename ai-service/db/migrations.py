import os
import logging
import pymysql
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

logger = logging.getLogger("edora.migrations")

# FIX : noms des tables avec préfixe mdl_ (convention Moodle)
# FIX : edora_conversations — ajout colonnes task_type, tokens_in, tokens_out
# FIX : edora_usage_logs — colonne student_id conservée (nom réel en DB)
TABLES = {
    "mdl_edora_conversations": """
        CREATE TABLE IF NOT EXISTS `mdl_edora_conversations` (
            `id`               INT(11)      NOT NULL AUTO_INCREMENT,
            `user_id`          INT(11)      NOT NULL,
            `course_id`        INT(11)      NOT NULL,
            `conversation_id`  VARCHAR(255) NOT NULL,
            `role`             VARCHAR(20)  NOT NULL,
            `message`          TEXT         NOT NULL,
            `created_at`       TIMESTAMP    NULL DEFAULT CURRENT_TIMESTAMP,
            `student_level`    VARCHAR(20)  DEFAULT NULL
                COMMENT 'debutant | intermediaire | avance',
            `level_score`      INT(11)      DEFAULT NULL
                COMMENT 'Score obtenu au quiz de niveau (sur 10)',
            `level_quiz_done`  TINYINT(1)   DEFAULT 0
                COMMENT '1 si le quiz de niveau a été complété',
            `task_type`        VARCHAR(50)  DEFAULT NULL
                COMMENT 'Type de tâche : chat, quiz, expliquer, resumer, exemple, flashcards',
            `tokens_in`        INT(11)      DEFAULT NULL
                COMMENT 'Tokens consommés en entrée pour cette interaction',
            `tokens_out`       INT(11)      DEFAULT NULL
                COMMENT 'Tokens générés en sortie pour cette interaction',
            PRIMARY KEY (`id`),
            KEY `idx_conversation_id` (`conversation_id`),
            KEY `idx_user_course`     (`user_id`, `course_id`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    "mdl_edora_usage_logs": """
        CREATE TABLE IF NOT EXISTS `mdl_edora_usage_logs` (
            `id`          INT          NOT NULL AUTO_INCREMENT,
            `student_id`  INT          NOT NULL,
            `course_id`   INT          NOT NULL DEFAULT 0,
            `task_type`   VARCHAR(20)  DEFAULT NULL,
            `tokens_in`   INT          NOT NULL DEFAULT 0,
            `tokens_out`  INT          NOT NULL DEFAULT 0,
            `cost_usd`    FLOAT        NOT NULL DEFAULT 0,
            `timestamp`   DATETIME     DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (`id`),
            KEY `idx_student_id` (`student_id`),
            KEY `idx_course_id`  (`course_id`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """
}


def get_connection():
    return pymysql.connect(
        host=os.getenv("MYSQL_HOST", "localhost"),
        port=int(os.getenv("MYSQL_PORT", 3306)),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        database=os.getenv("MYSQL_DATABASE"),
        charset="utf8mb4",
    )


def run_migrations():
    """Crée toutes les tables si elles n'existent pas encore."""
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            for table_name, ddl in TABLES.items():
                cur.execute(ddl)
                logger.info("Table prête : %s", table_name)
        conn.commit()
        conn.close()
        logger.info("Migrations terminées avec succès.")
    except Exception as e:
        logger.error("Erreur lors des migrations : %s", str(e))
        raise


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s"
    )
    run_migrations()