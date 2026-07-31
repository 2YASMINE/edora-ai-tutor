@echo off
echo Installation du plugin Tutor AI dans Moodle...

docker exec edora-moodle mkdir -p /bitnami/moodle/blocks/tutor_ai
docker exec edora-moodle mkdir -p /bitnami/moodle/blocks/tutor_ai/db
docker exec edora-moodle mkdir -p /bitnami/moodle/blocks/tutor_ai/classes
docker exec edora-moodle mkdir -p /bitnami/moodle/blocks/tutor_ai/lang/en
docker exec edora-moodle mkdir -p /bitnami/moodle/blocks/tutor_ai/amd/src

docker cp moodle-plugin\blocks\tutor_ai\version.php edora-moodle:/bitnami/moodle/blocks/tutor_ai/version.php
docker cp moodle-plugin\blocks\tutor_ai\block_tutor_ai.php edora-moodle:/bitnami/moodle/blocks/tutor_ai/block_tutor_ai.php
docker cp moodle-plugin\blocks\tutor_ai\db\events.php edora-moodle:/bitnami/moodle/blocks/tutor_ai/db/events.php
docker cp moodle-plugin\blocks\tutor_ai\db\access.php edora-moodle:/bitnami/moodle/blocks/tutor_ai/db/access.php
docker cp moodle-plugin\blocks\tutor_ai\classes\observer.php edora-moodle:/bitnami/moodle/blocks/tutor_ai/classes/observer.php
docker cp moodle-plugin\blocks\tutor_ai\lang\en\block_tutor_ai.php edora-moodle:/bitnami/moodle/blocks/tutor_ai/lang/en/block_tutor_ai.php
docker cp moodle-plugin\blocks\tutor_ai\amd\src\chat.js edora-moodle:/bitnami/moodle/blocks/tutor_ai/amd/src/chat.js
docker cp moodle-plugin\blocks\tutor_ai\styles.css edora-moodle:/bitnami/moodle/blocks/tutor_ai/styles.css

echo.
echo Plugin copie avec succes !
echo Allez sur http://localhost:8082/admin/index.php pour finaliser l'installation.