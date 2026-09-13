import os
import logging
import pymysql
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

logger = logging.getLogger("edora.migrations")

# Tables avec prefixe mdl_ (convention Moodle)
# mdl_edora_conversations  -- historique chat
# mdl_edora_usage_logs     -- logs tokens/couts API
# mdl_edora_mastery        -- progression maitrise concepts (Islem - feature/mastery-bar)
# mdl_edora_unanswered     -- questions sans reponse RAG  (Yasmine - feature/mindmap)
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
            `student_level`    VARCHAR(20)  DEFAULT NULL,
            `level_score`      INT(11)      DEFAULT NULL,
            `level_quiz_done`  TINYINT(1)   DEFAULT 0,
            `task_type`        VARCHAR(50)  DEFAULT NULL,
            `tokens_in`        INT(11)      DEFAULT NULL,
            `tokens_out`       INT(11)      DEFAULT NULL,
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
    """,
    "mdl_edora_mastery": """
        CREATE TABLE IF NOT EXISTS `mdl_edora_mastery` (
            `id`         INT(11)      NOT NULL AUTO_INCREMENT,
            `user_id`    INT(11)      NOT NULL,
            `course_id`  INT(11)      NOT NULL,
            `chunk_id`   VARCHAR(255) NOT NULL,
            `concept`    VARCHAR(255) DEFAULT NULL,
            `correct`    TINYINT(1)   NOT NULL DEFAULT 0,
            `created_at` TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (`id`),
            KEY `idx_user_course` (`user_id`, `course_id`),
            KEY `idx_chunk`       (`chunk_id`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    "mdl_edora_unanswered": """
        CREATE TABLE IF NOT EXISTS `mdl_edora_unanswered` (
            `id`               INT          NOT NULL AUTO_INCREMENT,
            `course_id`        INT          NOT NULL,
            `user_id`          INT          NOT NULL,
            `question`         TEXT         NOT NULL,
            `similarity_score` FLOAT        NOT NULL,
            `created_at`       TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (`id`),
            KEY `idx_course` (`course_id`)
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
    """Cree toutes les tables si elles n'existent pas encore."""
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            for table_name, ddl in TABLES.items():
                cur.execute(ddl)
                logger.info("Table prete : %s", table_name)
        conn.commit()
        conn.close()
        logger.info("Migrations terminees avec succes.")
    except Exception as e:
        logger.error("Erreur lors des migrations : %s", str(e))
        raise


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
    )
    run_migrations()