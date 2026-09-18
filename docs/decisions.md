# Décisions techniques — Edora AI Tutor

---

## LLM Provider — 12 juillet 2026
**Participants :** Islem, Yasmine
**Décision :** Gemini Flash 3.5 (API Google AI Studio)
**Raison :** Tier gratuit généreux adapté à un projet de stage sans budget, vitesse d'inférence élevée pour de bonnes performances en démo.
**Alternative écartée :** Claude API — plus strict sur le respect des consignes (ne pas halluciner hors contexte), mais tier gratuit trop limité pour du développement itératif sans budget.
**Note :** Le microservice est architecturé avec une couche d'abstraction sur le LLM, pour permettre de changer de fournisseur plus tard sans réécrire le code métier.

---

## Docker Compose Moodle + MariaDB — 13 juillet 2026
**Participants :** Islem, Yasmine
**Problème rencontré :** MariaDB 11.8 (image bitnamilegacy) crée les nouvelles bases avec la collation `utf8mb4_uca1400_ai_ci` par défaut (nouveau standard MariaDB 11.6+), non reconnue par le script d'installation Moodle comme "Unicode valide".
**Solution :** ajout de `MARIADB_EXTRA_FLAGS=--character-set-server=utf8mb4 --collation-server=utf8mb4_unicode_ci` dans le service `mariadb` du docker-compose.yml, pour forcer la collation classique attendue par Moodle dès la création de la base.
**Leçon apprise :** toujours vérifier `docker compose down -v` avant de tester une nouvelle correction — sinon un ancien volume ou un `.env` désynchronisé masque le vrai problème.

---

## Choix de Moodle Bitnami via Docker — Juillet 2026
**Participants :** Yasmine, Islem
**Décision :** Utiliser l'image Docker Bitnami/Moodle exposée sur le port 8082
**Raison :** Installation rapide et reproductible sans configuration serveur manuelle ; Bitnami préconfigure Apache, PHP et MariaDB dans un environnement isolé.
**Alternative écartée :** Installation native Moodle sur WAMP/XAMPP — trop de dépendances système à gérer manuellement, difficile à partager entre binôme en remote.

---

## Port 8082 pour Moodle, 3307 pour MariaDB — Juillet 2026
**Participants :** Yasmine, Islem
**Décision :** Mapper Moodle sur 8082 et MariaDB sur 3307 au lieu des ports standards 80 et 3306.
**Raison :** Éviter les conflits avec d'autres services locaux déjà en écoute sur les ports standards.
**Alternative écartée :** Ports 80/3306 — risque élevé de collision avec l'environnement de développement existant.

---

## Architecture en plugin Moodle de type bloc (block_tutor_ai) — Juillet 2026
**Participants :** Yasmine, Islem
**Décision :** Implémenter l'assistant IA sous forme de bloc Moodle (`block_tutor_ai`) plutôt qu'un module d'activité.
**Raison :** Un bloc est plus léger à développer, s'intègre dans n'importe quelle page de cours sans modifier le cœur de Moodle, et peut être activé/désactivé par les enseignants facilement.
**Alternative écartée :** Module d'activité Moodle — complexité de développement bien supérieure, inadapté à un assistant flottant permanent.

---

## Séparation en deux services distincts : plugin PHP + microservice FastAPI — Juillet 2026
**Participants :** Yasmine, Islem
**Décision :** Découpler le plugin Moodle (PHP) du moteur IA (Python/FastAPI) via des appels HTTP REST.
**Raison :** PHP n'a pas d'écosystème IA mature ; Python donne accès à LangChain, ChromaDB, Gemini SDK ; la séparation permet de développer et tester chaque couche indépendamment.
**Alternative écartée :** Tout en PHP avec des appels directs à l'API Gemini — impossible d'utiliser LangChain et ChromaDB.

---

## FastAPI + Uvicorn comme framework microservice Python — Juillet 2026
**Participants :** Yasmine, Islem
**Décision :** Utiliser FastAPI avec Uvicorn comme serveur ASGI sur le port 8000.
**Raison :** FastAPI génère automatiquement la documentation Swagger, impose la validation des schémas via Pydantic, et offre des performances asynchrones adaptées aux appels API Gemini potentiellement lents.
**Alternative écartée :** Flask — synchrone par défaut, pas de validation automatique des schémas.

---

## Système d'événements Moodle pour déclencher l'indexation — Juillet 2026
**Participants :** Yasmine, Islem
**Décision :** Utiliser le système d'événements Moodle (`events.php` + `observer.php`) pour détecter les uploads de ressources et déclencher automatiquement l'appel à `/upload-resource`.
**Raison :** Approche native Moodle, découplée du code principal du plugin ; l'observateur réagit à `\core\event\course_module_created` sans polling ni cron.
**Alternative écartée :** Cron Moodle périodique — latence d'indexation élevée, consommation de ressources inutile.

---

## Support multi-modules dans observer.php — Août 2026
**Participants :** Islem
**Décision :** Étendre l'observer pour accepter `resource`, `assign`, `folder`, `page`, `book` au lieu de `resource` uniquement.
**Raison :** Les enseignants uploadent des fichiers dans différents types de modules ; limiter à `resource` bloquait l'indexation de la majorité des documents.
**Alternative écartée :** Observer limité à `resource` — trop restrictif pour un usage réel en cours.

---

## Token Moodle dynamique dans observer.php — Août 2026
**Participants :** Islem
**Décision :** Lire le token Web Service dynamiquement depuis la table `mdl_external_tokens` via `$DB->get_record()` au lieu de le hardcoder.
**Raison :** Un token hardcodé devient invalide après rotation ou recréation du service Web, causant des 403/404 silencieux.
**Implémentation :**
```php
$token_record = $DB->get_record('external_tokens', ['externalserviceid' =>
    $DB->get_field('external_services', 'id', ['shortname' => 'edora_ai'])
]);
$token = $token_record->token;
```

---

## Double méthode de téléchargement avec variable DOWNLOAD_METHOD — Juillet 2026
**Participants :** Yasmine, Islem
**Décision :** Implémenter deux méthodes de téléchargement dans `resources.py` (session vs token) contrôlées par `DOWNLOAD_METHOD` dans `.env`.
**Raison :** Les deux environnements de développement se comportaient différemment ; la variable d'env permet à chacun de choisir sans modifier le code.
**Alternative écartée :** Une seule méthode forcée — bloquait l'un ou l'autre du binôme.

---

## host.docker.internal vs localhost selon le contexte réseau — Juillet 2026
**Participants :** Yasmine, Islem
**Décision :** Utiliser `host.docker.internal:8082` dans les URLs construites côté conteneur Moodle, et `localhost:8082` dans `resources.py` pour les téléchargements effectués depuis FastAPI sur la machine hôte.
**Raison :** Depuis l'intérieur du conteneur Docker, `localhost` pointe vers le conteneur lui-même.
**Règle :** Chaque développeur garde son `.env` local non commité avec la valeur adaptée à sa machine.

---

## LangChain RecursiveCharacterTextSplitter pour le chunking — Juillet 2026
**Participants :** Yasmine, Islem
**Décision :** Utiliser `RecursiveCharacterTextSplitter` avec chevauchement de chunks.
**Raison :** Le découpage récursif préserve les frontières naturelles du texte ; le chevauchement évite de couper du contexte sémantique important.
**Alternative écartée :** Découpage fixe par nombre de caractères sans chevauchement.

---

## Chunking — taille optimale — Août 2026
**Participants :** Yasmine, Islem
**Décision :** Taille de chunk retenue : 500 caractères / overlap 50.
**Raison :** Tests comparatifs effectués sur 3 configurations :
- 300/50 → timeout sur résumé, chunks trop petits perdent le contexte
- 500/50 → meilleur équilibre qualité/latence/couverture ✅
- 800/100 → résumé incomplet, moins de chunks distincts récupérés
**Documenté dans :** `docs/chunking_tests.md`

---

## gemini-embedding-2 à 3072 dimensions pour les embeddings — Juillet 2026
**Participants :** Yasmine, Islem
**Décision :** Utiliser le modèle `gemini-embedding-2` de Google avec des vecteurs de 3072 dimensions.
**Raison :** Meilleure représentation sémantique ; cohérence avec l'écosystème Google Gemini déjà utilisé pour le LLM.
**Alternative écartée :** `text-embedding-ada-002` d'OpenAI — introduirait une dépendance à un second fournisseur API.

---

## ChromaDB comme base vectorielle persistante — Juillet 2026
**Participants :** Yasmine, Islem
**Décision :** Utiliser ChromaDB en mode persistant avec stockage local dans `ai-service/chroma_db/`, avec une collection par cours (`course_X`).
**Raison :** ChromaDB est open-source, s'intègre nativement avec LangChain, ne nécessite pas de serveur externe.
**Alternative écartée :** Pinecone ou Weaviate — services cloud payants, latence réseau supplémentaire.
**Note :** `chroma_db/` est dans `.gitignore` et ne doit jamais être commité.

---

## Persona tuteur "Edo" avec prompts spécialisés par type de requête — Juillet 2026
**Participants :** Yasmine, Islem
**Décision :** Définir un persona nommé "Edo" avec cinq prompts distincts (`chat`, `quiz`, `resume`, `exemple`, `expliquer`) et des exemples few-shot par type.
**Raison :** Un persona nommé améliore l'engagement ; les prompts spécialisés permettent d'adapter le style de réponse au besoin.
**Alternative écartée :** Prompt unique générique — réponses moins adaptées, format de sortie inconsistant pour les quiz JSON.

---

## Délimiteurs RAG <chunk_cours> et <contexte_cours> dans les prompts — Juillet 2026
**Participants :** Yasmine, Islem
**Décision :** Entourer les chunks avec `<chunk_cours id='X' source='Y'>` et la question avec `<question_etudiant>` dans chaque prompt.
**Raison :** Les délimiteurs explicites réduisent les risques d'injection de prompt en séparant clairement le contexte de la question.
**Alternative écartée :** Injection des chunks en texte brut concaténé — vulnérable à l'injection de prompt.

---

## sanitize_input() avec plafond à 500 caractères — Juillet 2026
**Participants :** Yasmine, Islem
**Décision :** Nettoyer et tronquer les questions étudiantes à 500 caractères avant envoi au LLM.
**Raison :** Limite l'exposition aux injections de prompt par questions très longues ; réduit les coûts de tokens.

---

## classify_question() par matching de mots-clés — Juillet 2026
**Participants :** Yasmine, Islem
**Décision :** Classification locale par mots-clés pour router vers le bon prompt spécialisé sans appel API supplémentaire.
**Raison :** Évite un appel API Gemini juste pour classifier, réduisant la latence et les coûts.
**Alternative écartée :** Appel Gemini dédié à la classification — double la latence et le coût pour chaque question.

---

## MAX_OUTPUT_TOKENS différencié par type de tâche — Juillet 2026
**Participants :** Yasmine, Islem
**Décision :**
- `chat` / `exemple` / `expliquer` → 2048 tokens
- `resume` → 3072 tokens
- `quiz` → 6144 tokens
**Raison :** Équilibre entre réponses suffisamment détaillées et maîtrise des coûts API selon le type de tâche.

---

## Cache sémantique — cosine similarity — Août 2026
**Participants :** Yasmine, Islem
**Décision :** Cache en mémoire avec similarité cosinus (seuil 0.92, max 100 entrées).
**Raison :** Évite les appels Gemini redondants pour des questions similaires. Clé de cache inclut le `course_id` pour éviter la contamination entre cours. Quiz exclus du cache (JSON structuré toujours régénéré).
**Validé :** Cache hit — similarité 1.000 testé en logs.

---

## Compression historique à 8 échanges — Août 2026
**Participants :** Islem
**Décision :** Au-delà de 8 échanges (16 messages), résumer les anciens tours via `summarize_history()` et les remplacer par un message `system`.
**Raison :** Évite la croissance quadratique du coût tokens sur les longues conversations ; préserve le contexte récent tout en maintenant la cohérence.
**Implémentation :** `compress_history()` dans `history_service.py`, appelée dans le endpoint `/ask` avant chaque appel Gemini.
**Alternative écartée :** Fenêtre glissante sans résumé — perd définitivement le contexte des échanges anciens.

---

## Instrumentation tokens via usage_metadata — Août 2026
**Participants :** Islem
**Décision :** Logger `tokens_in`, `tokens_out`, `cost_usd` après chaque appel Gemini via `response.usage_metadata`, stockés dans `edora_usage_logs`.
**Raison :** Permet de répondre à "combien coûte 1 étudiant par mois ?" avec des données exactes issues directement de l'API Google.
**Calcul coût :** `(tokens_in * 0.075 + tokens_out * 0.30) / 1_000_000` (tarif Gemini Flash en vigueur août 2026).

---

## tiktoken — non implémenté — Août 2026
**Participants :** Yasmine, Islem
**Décision :** tiktoken non implémenté.
**Raison :** `response.usage_metadata` retourne le comptage exact des tokens après chaque appel — plus précis que l'estimation tiktoken (~90%) calibrée pour OpenAI/GPT, pas Gemini.
**Alternative retenue :** Logging post-appel via `usage_metadata` + table `edora_usage_logs`.

---

## Protection injection prompt — Août 2026
**Participants :** Yasmine, Islem
**Décision :** Délimiteurs XML dans le prompt RAG + validation de la sortie Gemini.
**Implémentation :**
- Chunks encadrés par `<chunk_cours id='N' source='...'>`
- Contexte encadré par `<contexte_cours>...</contexte_cours>`
- Question encadrée par `<question_etudiant>...</question_etudiant>`
- Validation sortie via `validate_gemini_output()` avec patterns d'injection
- Guardrail périmètre cours dans `BASE_PERSONA`
**Testé :** 3 tentatives d'injection bloquées — documenté dans `docs/tests_injection.md`

---

## Backoff exponentiel via tenacity — Août 2026
**Participants :** Islem
**Décision :** Remplacer le retry manuel (`for attempt in range(...)`) par le decorator `@retry` de la bibliothèque `tenacity`.
**Raison :** tenacity gère automatiquement le backoff, le logging des retries et la condition d'arrêt — code plus lisible et plus robuste que le retry manuel.
**Configuration retenue :**
- 4 tentatives maximum
- Backoff exponentiel : 4s → 8s → 16s → 32s (max 60s)
- `before_sleep_log` pour traçabilité automatique
**Alternative écartée :** Retry manuel avec `time.sleep()` — code verbeux, pas de backoff automatique.

---

## Plafond 50 000 tokens/session — Août 2026
**Participants :** Islem
**Décision :** Limiter chaque session étudiant à 50 000 tokens cumulés via `check_token_budget()`.
**Raison :** Empêche un étudiant de générer des coûts excessifs lors d'une session intensive ; le plafond est suffisant pour ~15-20 questions complètes.
**Note :** Le compteur `_session_tokens` est en mémoire — se remet à 0 à chaque redémarrage du serveur. Une persistance en DB pourrait être ajoutée en version future.
**Alternative écartée :** Pas de plafond — risque de dépassement de budget API en cas d'usage intensif ou malveillant.

---

## Pseudonymisation RGPD via SHA256 — Août 2026
**Participants :** Islem
**Décision :** Remplacer le `student_id` réel par un hash SHA256 tronqué à 16 chars dans tous les logs Gemini via `pseudonymize_id()`.
**Raison :** Le vrai `user_id` Moodle ne doit jamais transiter vers l'API Google pour des raisons de conformité RGPD ; le hash permet de corréler les logs sans exposer l'identité.
**Implémentation :**
```python
def pseudonymize_id(user_id: int) -> str:
    return hashlib.sha256(str(user_id).encode()).hexdigest()[:16]
```
**Données pseudonymisées :** logs Gemini (`edora.gemini`)
**Données réelles conservées :** table MariaDB `edora_usage_logs` (nécessaire pour la facturation)
**Alternative écartée :** Supprimer le student_id des logs — impossible de corréler les problèmes par étudiant pour le débogage.

---

## Détection de détresse par liste de mots-clés — Juillet 2026
**Participants :** Yasmine, Islem
**Décision :** Implémenter une détection locale de mots-clés de détresse dans `check_distress()` avant l'appel Gemini.
**Raison :** Responsabilité pédagogique et éthique ; un assistant IA doit reconnaître quand un étudiant est en difficulté émotionnelle.
**Alternative écartée :** Laisser Gemini gérer seul ces cas — le modèle n'est pas fiable pour détecter la détresse de manière systématique.

---

## Interface chat en floating panel injecté dans <body> — Juillet 2026
**Participants :** Yasmine, Islem
**Décision :** Injecter le FAB et le panel chat directement dans `<body>` via JavaScript plutôt que dans le conteneur du bloc Moodle.
**Raison :** Le bloc Moodle a un CSS contraignant causant des bugs d'affichage ; l'injection dans `<body>` donne un contrôle total sur le z-index et le positionnement.
**Alternative écartée :** Positionner le panel dans le DOM du bloc Moodle — conflits CSS non maîtrisables.

---

## renderMarkdown() côté JS — Juillet 2026
**Participants :** Yasmine, Islem
**Décision :** Implémenter une fonction `renderMarkdown()` dans `chat.js` pour convertir les réponses Gemini en HTML.
**Raison :** Gemini retourne nativement du Markdown ; sans conversion, les astérisques et dièses sont illisibles pour les étudiants.
**Alternative écartée :** Forcer Gemini à répondre en HTML brut — les prompts deviennent complexes et le modèle introduit des balises malformées.

---

## renderJsonQuiz() pour l'affichage interactif des QCM — Juillet 2026
**Participants :** Yasmine, Islem
**Décision :** Ajouter un flag `is_quiz_json` dans `AskResponse` et une fonction `renderJsonQuiz()` dans `chat.js` pour afficher les quiz en composants interactifs.
**Raison :** Un quiz en JSON structuré permet une UI interactive (sélection de réponse, feedback immédiat, score) impossible avec du Markdown brut.
**Alternative écartée :** Quiz en Markdown numéroté — pas d'interactivité possible.

---

## MariaDB edora_conversations pour l'historique — Juillet 2026
**Participants :** Yasmine, Islem
**Décision :** Stocker l'historique dans une table MariaDB `edora_conversations` via `history_service.py`.
**Raison :** MariaDB est déjà présente dans le stack Docker ; stockage relationnel pour requêtes multi-utilisateurs et conformité RGPD.
**Alternative écartée :** Historique en mémoire — ne survit pas aux redémarrages.

---

## HISTORY_WINDOW = 6 messages injectés dans le contexte Gemini — Juillet 2026
**Participants :** Yasmine, Islem
**Décision :** Limiter l'historique injecté dans chaque prompt Gemini aux 6 derniers échanges.
**Raison :** Équilibre entre cohérence conversationnelle et maîtrise de la fenêtre de contexte ; au-delà de 6 messages, les chunks RAG risquent d'être tronqués.
**Alternative écartée :** Historique complet — fait exploser la taille du prompt sur des conversations longues.

---

## Quiz de détection de niveau : 10 QCM, scoring Débutant/Intermédiaire/Avancé — Juillet 2026
**Participants :** Yasmine, Islem
**Décision :** Générer dynamiquement un quiz de 10 questions QCM via Gemini, scorer en trois niveaux (Débutant ≤ 4, Intermédiaire 5-7, Avancé ≥ 8), stocker le résultat en MariaDB.
**Raison :** La détection de niveau permet à Edo d'adapter la complexité des explications ; 10 questions est un bon compromis entre précision du diagnostic et patience de l'étudiant.
**Alternative écartée :** Auto-déclaration du niveau — subjective et inexacte.

---

## Volume Docker monté pour le plugin Moodle — Août 2026
**Participants :** Yasmine, Islem
**Décision :** Décommenter le volume mount dans `docker-compose.yml` :
```yaml
- ./moodle-plugin/blocks/tutor_ai:/bitnami/moodle/blocks/tutor_ai
```
**Raison :** Élimine la nécessité de `docker cp` manuel à chaque modification PHP/JS ; les fichiers sont synchronisés automatiquement.
**Résultat :** `git pull` suffit pour mettre à jour le plugin dans Moodle — `install-plugin.cmd` uniquement si `version.php` ou `events.php` modifiés.

---

## Incrémentation obligatoire de version.php — Juillet 2026
**Participants :** Yasmine, Islem
**Décision :** Incrémenter systématiquement le numéro de version dans `version.php` à chaque ajout de nouveau fichier ou modification structurelle du plugin.
**Raison :** Moodle détecte les mises à jour du plugin uniquement via le changement de version.
**Alternative écartée :** Mise à jour de version uniquement pour les releases majeures — cause des bugs silencieux.

---

## migrations.py — création automatique des tables au démarrage — Août 2026
**Participants :** Islem
**Décision :** Créer `db/migrations.py` appelé depuis `main.py` au startup FastAPI pour créer automatiquement `edora_conversations` et `edora_usage_logs`.
**Raison :** Évite les erreurs de "table inexistante" lors d'un premier déploiement ou après un `docker compose down -v` ; le `IF NOT EXISTS` garantit l'idempotence.
**Alternative écartée :** Migration manuelle via script SQL — oubli fréquent, source d'erreurs en déploiement.

---

## Streaming Gemini — non implémenté — Août 2026
**Participants :** Yasmine, Islem
**Décision :** Streaming non implémenté.
**Raison :** Incompatible avec le cache sémantique et le parsing JSON du quiz. Amélioration future possible pour les modes `chat` et `expliquer` uniquement.

---

## Incrémentation obligatoire de `version.php`
**Date :** Juillet 2026
**Participants :** Yasmine, Islem

### Décision
Incrémenter systématiquement le numéro de version dans `version.php` à chaque ajout de fichier ou modification structurelle du plugin.

---

## Génération d'image pédagogique via Gemini Image
**Date :** Septembre 2026
**Participants :** Islem 

### Décision
Utiliser `gemini-2.5-flash-image` (Nano Banana) pour générer des images éducatives à partir du contenu du cours.

### Pipeline retenu
```
ChromaDB → 8 chunks pertinents
    ↓
gemini-3.5-flash → prompt image EN + caption FR (JSON)
    ↓
gemini-2.5-flash-image → image PNG en base64
```

### Raison
Imagen et `gemini-2.0-flash-preview-image-generation` sont arrêtés depuis juin 2026. `gemini-2.5-flash-image` est le seul modèle image disponible sur le compte gratuit.

### Note
Les modèles Imagen ne réapparaissent pas dans `/list-image-models` malgré leur ancien fonctionnement — l'endpoint de diagnostic utilise `supported_generation_methods` qui ne remonte pas toujours les capacités image.

---

## Parsing JSON robuste pour la génération d'image
**Date :** Septembre 2026
**Participants :** Yasmine

### Décision
Remplacer le regex greedy `\{[\s\S]*?\}` par extraction via `raw.find("{")` + `raw.rfind("}")`.

### Raison
Le regex avec `?` (non-greedy) s'arrêtait au premier `}` rencontré, coupant le JSON à mi-chemin. `rfind` garantit la prise du dernier `}` = JSON complet.

### Paramètres finaux
| Paramètre | Valeur |
|---|---|
| `max_output_tokens` | `2048` |
| `response_mime_type` | `"application/json"` |
| `temperature` | `0.4` |

### Alternative écartée
Regex greedy `\{[\s\S]*\}` — toujours instable selon la longueur de la réponse.

---

## Prompt few-shot pour la génération d'image
**Date :** Septembre 2026
**Participants :** Yasmine

### Décision
Remplacer le prompt générique par un prompt few-shot avec 5 exemples domaine-spécifiques : UML, IA, Base de données, Architecture logicielle, Marketing.

### Raison
Sans few-shot, Gemini générait des icônes génériques (ampoules, engrenages, boucliers) sans rapport avec le contenu. Avec few-shot, il produit des diagrammes techniques précis — classes UML avec compartiments, flèches typées, couches architecturales.

### Règles CRITICAL du prompt
- Minimum 80 mots
- Shapes exactes, couleurs par élément, layout spatial précis
- Jamais d'icônes génériques
- ONE coherent diagram

### Résultat
Diagrammes UML avec 3 compartiments, flèches héritage/agrégation correctes, labels en langue du cours.

---

## Détection d'image par message dans le chat
**Date :** Septembre 2026
**Participants :**Islem + Yasmine

### Décision
Détecter les mots-clés image dans `sendQuestion()` avant l'appel à `/ask`, et router vers `triggerGenerateImage()` avec extraction du concept.

### Raison
L'étudiant ne pouvait déclencher la génération que via le bouton Image dans les raccourcis. La détection par message permet de cibler un concept précis (ex. *"génère une image sur l'héritage UML"*).

### Mots-clés détectés
`génère une image` · `illustre` · `montre moi une image` · `image de` · `image sur` · `visualise` · `dessine` · `schéma de` · `generate image` · `draw`

### Note
Le check `isSmallTalk()` ne s'applique pas ici — la détection image court-circuite avant.

---

## Paramètre `concept` dans `/generate-image`
**Date :** Septembre 2026
**Participants :**Islem

### Décision
Ajouter `concept: str = ""` dans `GenerateImageRequest`. Si fourni, il remplace la query d'embedding générique par le concept demandé.

### Raison
Sans concept ciblé, ChromaDB retourne les chunks les plus généraux du cours. Avec le concept, l'image porte sur le sujet précis demandé par l'étudiant.

### Implémentation
```python
query_text = request.concept if request.concept else \
    "concepts principaux définitions résumé schéma illustration cours"
```

---

## Système de récompenses XP
**Date :** Septembre 2026
**Participants :** Yasmine

### Décision
Gamification via table `mdl_edora_xp` avec XP, badges et niveaux progressifs.

### Niveaux
Bronze → Argent → Or → Platine → Diamant

### Règles XP
| Action | XP |
|---|---|
| Question | +5 |
| Quiz terminé | +20 |
| Quiz parfait | +50 |

### Badges
| Badge | Condition |
|---|---|
| 🌱 Première question | 1 question posée |
| 🔥 Curieux | 10 questions posées |
| 🏆 Quiz Master | 5 quiz complétés |
| 📚 Chercheur de savoir | 100 XP atteints |
| 🚀 Expert | 500 XP atteints |

### Note
Le XP n'est pas accordé pour le small talk — vérification `isSmallTalk()` côté JS avant l'appel `/xp/add`.

### Alternative écartée
Barre de progression seule (feature Islem) — insuffisant pour la gamification. Les deux coexistent.

---

## Logging `task_type` dans `edora_conversations`
**Date :** Septembre 2026
**Participants :** Yasmine

### Décision
Ajouter `task_type` comme paramètre optionnel dans `save_message()` et le persister dans `mdl_edora_conversations`.

### Raison
La colonne existait mais n'était jamais remplie. Le logging permet au dashboard enseignant d'afficher la répartition des types de requêtes (ex. *"40% quiz, 30% explications"*) pour identifier les besoins pédagogiques.

### Implémentation
```python
save_message(..., task_type=None)  # backward-compatible, aucune migration nécessaire
```

---

## Period filters dans le dashboard enseignant
**Date :** Septembre 2026
**Participants :** Yasmine

### Décision
Ajouter un filtre temporel dans `dashboard.php` via `$period_filter` injecté dans les requêtes SQL.

### Options disponibles
Aujourd'hui · Cette semaine · Ce mois · Tout

### Raison
Les enseignants voulaient voir l'activité récente séparément de l'historique complet.

### Bug connu
`$heatmap_data` et `$activite_hebdo` n'ont pas d'alias `ec.` — le filtre `ec.created_at` y cause une erreur SQL.

**Fix :** créer `$period_filter_no_alias` sans préfixe de table.

### Statut
⚠️ Partiellement implémenté — 4 requêtes filtrées sur 6.

---

## Course selector dans le dashboard enseignant
**Date :** Septembre 2026
**Participants :** Yasmine

### Décision
Remplacer `$courses_with_data` par `$teacher_courses` dans le sélecteur de cours du dashboard.

### Raison
`$courses_with_data` filtrait uniquement les cours ayant déjà des conversations Edora. Un enseignant sur un nouveau cours ne pouvait pas accéder au dashboard pour ce cours.

### Fix
```php
// Avant
foreach ($courses_with_data as $c) { ... $c->course_id ... }

// Après
foreach ($teacher_courses as $c) { ... $c->id ... }
```

