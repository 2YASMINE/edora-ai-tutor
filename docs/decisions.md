# Décisions techniques

## LLM Provider — 12 juillet 2026

**Décision :** Gemini Flash 3.5 (API Google AI Studio)
**Participants :** Islem, Yasmine
**Raison principale :** Tier gratuit généreux adapté à un projet de stage sans budget, vitesse d'inférence élevée pour de bonnes performances en démo.
**Alternative écartée et pourquoi :** Claude API — plus strict sur le respect des consignes (ne pas halluciner hors contexte), mais tier gratuit trop limité pour du développement itératif sans budget.
**Note pour la suite :** Le microservice sera architecturé avec une couche d'abstraction sur le LLM, pour permettre de changer de fournisseur plus tard sans réécrire le code métier.

\## Docker Compose Moodle + MariaDB — 13 juillet 2026

\*Participant : islem \*

\*Problème rencontré :\* MariaDB 11.8 (image bitnamilegacy) crée les nouvelles bases avec la collation utf8mb4\_uca1400\_ai\_ci par défaut (nouveau standard MariaDB 11.6+), non reconnue par le script d'installation Moodle comme "Unicode valide".

\*Solution :\* ajout de MARIADB\_EXTRA\_FLAGS=--character-set-server=utf8mb4 --collation-server=utf8mb4\_unicode\_ci dans le service mariadb du docker-compose.yml, pour forcer la collation classique attendue par Moodle dès la création de la base.

\*Leçon apprise :\* toujours vérifier docker compose down -v avant de tester une nouvelle correction — sinon un ancien volume ou un .env désynchronisé masque le vrai problème.



\## 14/07/2026 —\*Participant : yasmine \*





\### Tâches accomplies

\- Configuré l'environnement Bitnami (docker-compose d'Islem)

\- Résolu conflit port 3306 (MySQL Windows) → changé vers 3307

\- Résolu conflit port 8080 → changé vers 8082

\- Installé et testé l'API Gemini → modèle retenu : gemini-3.5-flash

\- Copié et installé le plugin block\_tutor\_ai dans Moodle Bitnami

\- Pushé tout le travail sur le repo officiel Edora



\### Décisions prises

\- Modèle LLM retenu : gemini-3.5-flash (gratuit, disponible en Tunisie)

\- Repo officiel : edoralms-moodle-block\_ai\_tutor\_03



\### Problèmes rencontrés

\- Port 3306 occupé par MySQL Windows → solution : changer vers 3307

\- Port 8080 occupé → solution : changer vers 8082

\- Plugin non trouvé dans repo → solution : copié depuis ancien container



\### Prochaine étape

\- Squelette FastAPI (microservice Python)
## Docker Compose Moodle + MariaDB — 13 juillet 2026
**Participants :** Islem , 
**Problème rencontré :** MariaDB 11.8 (image bitnamilegacy) crée les nouvelles bases avec la collation `utf8mb4_uca1400_ai_ci` par défaut (nouveau standard MariaDB 11.6+), non reconnue par le script d'installation Moodle comme "Unicode valide".
**Solution :** ajout de `MARIADB_EXTRA_FLAGS=--character-set-server=utf8mb4 --collation-server=utf8mb4_unicode_ci` dans le service `mariadb` du docker-compose.yml, pour forcer la collation classique attendue par Moodle dès la création de la base.
**Leçon apprise :** toujours vérifier `docker compose down -v` avant de tester une nouvelle correction — sinon un ancien volume ou un `.env` désynchronisé masque le vrai problème.
>>>>>>> d7863ba5a65c26d89043c4e719be0b79d658987a



