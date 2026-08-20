## Choix de Moodle Bitnami via Docker — Juillet 2026
**Participant :** Yasmine + Islem
**Décision :** Utiliser l'image Docker Bitnami/Moodle exposée sur le port 8082
**Raison :** Installation rapide et reproductible sans configuration serveur manuelle ; Bitnami préconfigure Apache, PHP et MariaDB dans un environnement isolé
**Alternative écartée :** Installation native Moodle sur WAMP/XAMPP — trop de dépendances système à gérer manuellement, difficile à partager entre binôme en remote

---

## Port 8082 pour Moodle, 3307 pour MariaDB — Juillet 2026
**Participant :** Yasmine + Islem
**Décision :** Mapper Moodle sur 8082 et MariaDB sur 3307 au lieu des ports standards 80 et 3306
**Raison :** Éviter les conflits avec d'autres services locaux (serveurs web locaux, MySQL natif) déjà en écoute sur les ports standards
**Alternative écartée :** Ports 80/3306 — risque élevé de collision avec l'environnement de développement existant sur les machines du binôme

---

## Architecture en plugin Moodle de type bloc (block_tutor_ai) — Juillet 2026
**Participant :** Yasmine + Islem
**Décision :** Implémenter l'assistant IA sous forme de bloc Moodle (`block_tutor_ai`) plutôt qu'un module d'activité
**Raison :** Un bloc est plus léger à développer, s'intègre dans n'importe quelle page de cours sans modifier le cœur de Moodle, et peut être activé/désactivé par les enseignants facilement
**Alternative écartée :** Module d'activité Moodle — complexité de développement bien supérieure, nécessite une page dédiée, inadapté à un assistant flottant permanent

---

## Séparation en deux services distincts : plugin PHP + microservice FastAPI — Juillet 2026
**Participant :** Yasmine + Islem
**Décision :** Découpler le plugin Moodle (PHP) du moteur IA (Python/FastAPI) via des appels HTTP REST
**Raison :** PHP n'a pas d'écosystème IA mature ; Python donne accès à LangChain, ChromaDB, Gemini SDK et toutes les bibliothèques NLP nécessaires ; la séparation permet de développer et tester chaque couche indépendamment
**Alternative écartée :** Tout en PHP avec des appels directs à l'API Gemini — impossible d'utiliser LangChain, ChromaDB et les outils Python du pipeline RAG

---

## FastAPI + Uvicorn comme framework microservice Python — Juillet 2026
**Participant :** Yasmine + Islem
**Décision :** Utiliser FastAPI avec Uvicorn comme serveur ASGI sur le port 8000
**Raison :** FastAPI génère automatiquement la documentation Swagger, impose la validation des schémas via Pydantic, et offre des performances asynchrones adaptées aux appels API Gemini potentiellement lents
**Alternative écartée :** Flask — synchrone par défaut, pas de validation automatique des schémas, moins adapté aux endpoints IA avec des temps de réponse variables

---

## Système d'événements Moodle pour déclencher l'indexation — Juillet 2026
**Participant :** Yasmine + Islem
**Décision :** Utiliser le système d'événements Moodle (`events.php` + `observer.php`) pour détecter les uploads de ressources et déclencher automatiquement l'appel à `/upload-resource`
**Raison :** Approche native Moodle, découplée du code principal du plugin ; l'observateur réagit à `\core\event\course_module_created` sans polling ni cron
**Alternative écartée :** Cron Moodle périodique qui scrute les nouvelles ressources — latence d'indexation élevée, consommation de ressources inutile, complexité de gestion des doublons

---

## Format d'URL tokenpluginfile.php pour le téléchargement de fichiers — Juillet 2026
**Participant :** Yasmine + Islem
**Décision :** Utiliser le format `tokenpluginfile.php/{token}/{context_id}/...` dans `observer.php` pour construire l'URL de téléchargement envoyée à FastAPI
**Raison :** Les fichiers Moodle ne sont pas accessibles publiquement ; ce format permet une authentification sans session via le token Web Service
**Alternative écartée :** URL `pluginfile.php` classique — nécessite une session PHP active côté FastAPI, impossible à maintenir dans un microservice Python sans état

---

## Double méthode de téléchargement avec variable DOWNLOAD_METHOD — Juillet 2026
**Participant :** Yasmine + Islem
**Décision :** Implémenter deux méthodes de téléchargement dans `resources.py` (session vs token) contrôlées par la variable d'environnement `DOWNLOAD_METHOD`
**Raison :** Les deux environnements de développement (Yasmine et Islem) se comportaient différemment ; la variable d'env permet à chacun de choisir la méthode fonctionnelle sans modifier le code
**Alternative écartée :** Une seule méthode forcée — bloquait l'un ou l'autre du binôme selon l'environnement

---

## host.docker.internal vs localhost selon le contexte réseau — Juillet 2026
**Participant :** Yasmine + Islem
**Décision :** Utiliser `host.docker.internal:8082` dans les URLs construites côté conteneur Moodle, et `localhost:8082` dans `resources.py` pour les téléchargements effectués depuis FastAPI sur la machine hôte
**Raison :** Depuis l'intérieur du conteneur Docker, `localhost` pointe vers le conteneur lui-même et non vers la machine hôte ; `host.docker.internal` est le DNS Docker pour atteindre l'hôte
**Alternative écartée :** IP fixe de la machine hôte — non portable entre les machines du binôme

---

## LangChain RecursiveCharacterTextSplitter pour le chunking — Juillet 2026
**Participant :** Yasmine + Islem
**Décision :** Utiliser `RecursiveCharacterTextSplitter` de LangChain avec chevauchement de chunks pour le découpage des documents
**Raison :** Le découpage récursif préserve les frontières naturelles du texte (paragraphes, phrases) ; le chevauchement évite de couper du contexte sémantique important entre deux chunks adjacents
**Alternative écartée :** Découpage fixe par nombre de caractères sans chevauchement — risque élevé de couper des phrases au milieu, dégradant la qualité des réponses RAG

---

## gemini-embedding-2 à 3072 dimensions pour les embeddings — Juillet 2026
**Participant :** Yasmine + Islem
**Décision :** Utiliser le modèle `gemini-embedding-2` de Google avec des vecteurs de 3072 dimensions
**Raison :** Meilleure représentation sémantique que les modèles à dimensions inférieures ; cohérence avec l'écosystème Google Gemini déjà utilisé pour le LLM
**Alternative écartée :** `text-embedding-ada-002` d'OpenAI (1536 dimensions) — introduirait une dépendance à un second fournisseur API et des coûts supplémentaires

---

## ChromaDB comme base vectorielle persistante — Juillet 2026
**Participant :** Yasmine+ Islem 
**Décision :** Utiliser ChromaDB en mode persistant avec stockage local dans `ai-service/chroma_db/`, avec une collection par cours (`course_X`)
**Raison :** ChromaDB est open-source, s'intègre nativement avec LangChain, ne nécessite pas de serveur externe, et la persistance sur disque survit aux redémarrages du service
**Alternative écartée :** Pinecone ou Weaviate — services cloud payants, latence réseau supplémentaire, dépendance externe non justifiée pour un MVP de stage

---

## Persona tuteur "Edo" avec prompts spécialisés par type de requête — Juillet 2026
**Participant :** Yasmine + Islem
**Décision :** Définir un persona nommé "Edo" avec cinq prompts distincts (`chat`, `quiz`, `resume`, `exemple`, `expliquer`) et des exemples few-shot par type
**Raison :** Un persona nommé améliore l'engagement des étudiants ; les prompts spécialisés permettent d'adapter le style de réponse au besoin (expliquer ≠ générer un quiz ≠ résumer) ; les few-shot examples stabilisent le format de sortie
**Alternative écartée :** Prompt unique générique — réponses moins adaptées au contexte pédagogique, format de sortie inconsistant notamment pour les quiz JSON

---

## Délimiteurs RAG <chunk_cours> et <contexte_cours> dans les prompts — Juillet 2026
**Participant :** Yasmine + Islem
**Décision :** Entourer les chunks de contexte avec des balises XML `<chunk_cours id='X' source='Y'>` et la question avec `<question_etudiant>` dans chaque prompt
**Raison :** Les délimiteurs explicites réduisent les risques d'injection de prompt en séparant clairement le contexte de cours de la question étudiant ; recommandation directe des superviseurs
**Alternative écartée :** Injection des chunks en texte brut concaténé — le modèle peut confondre le contenu du cours avec des instructions, vulnérabilité à l'injection de prompt

---

## sanitize_input() avec plafond à 500 caractères — Juillet 2026
**Participant :** Yasmine + Islem
**Décision :** Implémenter une fonction `sanitize_input()` qui nettoie et tronque les questions étudiantes à 500 caractères avant envoi au LLM
**Raison :** Limite l'exposition aux injections de prompt par questions très longues ; réduit les coûts de tokens ; recommandation de sécurité des superviseurs
**Alternative écartée :** Pas de limite — une question malicieusement longue peut noyer les instructions système du prompt ou générer des coûts API excessifs

---

## classify_question() par matching de mots-clés avant appel API — Juillet 2026
**Participant :** Yasmine + Islem
**Décision :** Implémenter une classification locale par mots-clés pour router vers le bon prompt spécialisé sans appel API supplémentaire
**Raison :** Évite un appel API Gemini juste pour classifier la question, réduisant la latence et les coûts ; la classification par mots-clés est suffisamment précise pour distinguer quiz/résumé/explication/exemple
**Alternative écartée :** Appel Gemini dédié à la classification — double la latence et le coût pour chaque question

---

## MAX_OUTPUT_TOKENS = 2048 dans gemini.py — Juillet 2026
**Participant :** Yasmine + Islem
**Décision :** Fixer le plafond de génération à 2048 tokens de sortie pour tous les appels Gemini
**Raison :** Équilibre entre des réponses pédagogiques suffisamment détaillées et la maîtrise des coûts API ; au-delà de 2048 tokens, les réponses deviennent trop longues pour une interface chat
**Alternative écartée :** Pas de limite (défaut Gemini) — risque de réponses excessivement longues et de dépassement de budget API en production

---

## GEMINI_TIMEOUT comme variable d'environnement + tenacity pour retry — Juillet 2026
**Participant :** Yasmine + Islem
**Décision :** Paramétrer le timeout des appels Gemini via `GEMINI_TIMEOUT` dans le `.env` et utiliser la bibliothèque `tenacity` pour les retry automatiques avec backoff exponentiel
**Raison :** L'API Gemini peut être lente ou retourner des erreurs transitoires ; le retry automatique améliore la robustesse sans alourdir le code métier ; le timeout configurable permet d'ajuster selon les environnements
**Alternative écartée :** Timeout hardcodé sans retry — une erreur réseau passagère fait échouer définitivement la requête, dégradant l'expérience étudiant

---

## Détection de détresse par liste de mots-clés dans gemini.py — Juillet 2026
**Participant :** Yasmine + Islem
**Décision :** Implémenter une détection locale de mots-clés de détresse (stress, panique, incompréhension profonde) pour adapter la réponse d'Edo avant l'appel Gemini
**Raison :** Responsabilité pédagogique et éthique ; un assistant IA doit reconnaître quand un étudiant est en difficulté émotionnelle et réorienter vers des ressources humaines
**Alternative écartée :** Laisser Gemini gérer seul ces cas — le modèle n'est pas fiable pour détecter la détresse de manière systématique sans instruction explicite

---

## Interface chat en floating panel injecté dans <body> — Juillet 2026
**Participant :** Yasmine + Islem
**Décision :** Injecter le FAB (floating action button) et le panel chat directement dans `<body>` via JavaScript plutôt que dans le conteneur du bloc Moodle
**Raison :** Le bloc Moodle a un CSS contraignant qui limitait le positionnement flottant et causait des bugs d'affichage (notamment sous Brave) ; l'injection dans `<body>` donne un contrôle total sur le z-index et le positionnement fixed
**Alternative écartée :** Positionner le panel dans le DOM du bloc Moodle — conflits CSS non maîtrisables avec le thème Moodle, bug de disparition du bouton sous certains navigateurs

---

## Avatar personnalisé edo-avatar.png à la place de l'emoji 🦉 — Juillet 2026
**Participant :** Yasmine + Islem
**Décision :** Remplacer l'emoji hibou par une image SVG/PNG personnalisée `pix/edo-avatar.png` servie depuis le plugin Moodle
**Raison :** L'emoji s'affichait différemment selon les systèmes d'exploitation (Windows vs macOS vs mobile) ; une image personnalisée garantit un rendu identique partout et renforce l'identité visuelle d'Edo
**Alternative écartée :** Conserver l'emoji — rendu inconsistant cross-platform, aspect peu professionnel pour une démo superviseurs

---

## Boutons d'action SVG (copier, régénérer, like, dislike) — Juillet 2026
**Participant :** Yasmine + Islem
**Décision :** Implémenter les boutons d'action de chaque message via des icônes SVG inline plutôt que des icônes de bibliothèque externe
**Raison :** Pas de dépendance externe (Font Awesome, Material Icons) à charger dans Moodle ; les SVG inline sont stylisables directement en CSS et ne nécessitent pas de requête réseau supplémentaire
**Alternative écartée :** Font Awesome ou Bootstrap Icons — requête CDN supplémentaire, risque de blocage par la politique CSP de Moodle, surcharge pour seulement 4 icônes

---

## renderMarkdown() côté JS pour le formatage des réponses — Juillet 2026
**Participant :** Yasmine + Islem
**Décision :** Implémenter une fonction `renderMarkdown()` dans `chat.js` pour convertir les réponses Gemini (Markdown) en HTML affiché dans le chat
**Raison :** Gemini retourne nativement du Markdown (gras, listes, code) ; sans conversion, le rendu brut avec les astérisques et dièses est illisible pour les étudiants
**Alternative écartée :** Forcer Gemini à répondre en HTML brut — les prompts deviennent complexes et le modèle introduit régulièrement des balises malformées

---

## renderJsonQuiz() pour l'affichage interactif des QCM — Juillet 2026
**Participant :** Yasmine + Islem
**Décision :** Ajouter un flag `is_quiz_json` dans `AskResponse` et une fonction `renderJsonQuiz()` dans `chat.js` pour afficher les quiz en composants interactifs cliquables
**Raison :** Un quiz en JSON structuré permet une UI interactive (sélection de réponse, feedback immédiat, score) impossible avec du Markdown brut ; le flag `is_quiz_json` permet au JS de choisir le bon renderer
**Alternative écartée :** Quiz en Markdown numéroté — pas d'interactivité possible, impossible de valider la réponse ou d'afficher un score automatiquement

---

## MariaDB edora_conversations pour l'historique — Juillet 2026
**Participant :** Yasmine + Islem
**Décision :** Stocker l'historique des conversations dans une table MariaDB `edora_conversations` (user_id, course_id, role, content, timestamp) via `history_service.py`
**Raison :** MariaDB est déjà présente dans le stack Docker du projet ; stocker en base relationnelle permet des requêtes par utilisateur/cours, la pagination, et facilite la conformité RGPD (suppression sur demande)
**Alternative écartée :** Historique en mémoire Redis ou fichiers JSON — Redis ajoute un service Docker supplémentaire ; les fichiers JSON ne supportent pas les requêtes multi-utilisateurs et sont difficiles à purger

---

## HISTORY_WINDOW = 6 messages injectés dans le contexte Gemini — Juillet 2026
**Participant :** Yasmine + Islem
**Décision :** Limiter l'historique injecté dans chaque prompt Gemini aux 6 derniers échanges (3 tours utilisateur/assistant)
**Raison :** Équilibre entre cohérence conversationnelle (Gemini se souvient du contexte récent) et maîtrise de la fenêtre de contexte ; au-delà de 6 messages, les chunks RAG et les instructions système risquent d'être tronqués
**Alternative écartée :** Historique complet — fait exploser la taille du prompt sur des conversations longues, augmente les coûts et peut dépasser la fenêtre de contexte de Gemini Flash

---

## Colonnes student_level, level_score, level_quiz_done dans MariaDB — Juillet 2026
**Participant :** Yasmine + Islem
**Décision :** Ajouter trois colonnes de niveau (`student_level`, `level_score`, `level_quiz_done`) directement dans la table étudiants existante plutôt qu'une table séparée
**Raison :** Le niveau est une propriété stable de l'étudiant dans un cours donné, pas une entité à part entière ; une colonne simple évite une jointure supplémentaire à chaque appel RAG
**Alternative écartée :** Table `edora_student_levels` séparée — surengineering pour trois champs simples, jointure SQL à chaque requête sans bénéfice architectural réel

---

## Quiz de détection de niveau : 10 QCM, scoring Débutant/Intermédiaire/Avancé — Juillet 2026
**Participant :** Yasmine + Islem
**Décision :** Générer dynamiquement un quiz de 10 questions QCM via Gemini, scorer en trois niveaux (Débutant < 4, Intermédiaire 4-7, Avancé > 7), stocker le résultat en MariaDB
**Raison :** La détection de niveau permet à Edo d'adapter la complexité des explications à l'étudiant ; 10 questions est un bon compromis entre précision du diagnostic et patience de l'étudiant
**Alternative écartée :** Auto-déclaration du niveau par l'étudiant — subjective et souvent inexacte ; quiz de plus de 10 questions — abandon trop fréquent avant la fin

---

## Volume Docker monté pour chroma_db au lieu de docker cp — Juillet 2026
**Participant :** Yasmine + Islem
**Décision :** Décommenter le volume mount dans `docker-compose.yml` pour synchroniser `ai-service/chroma_db/` directement entre l'hôte et le conteneur
**Raison :** Élimine la nécessité de `docker cp` manuel à chaque modification ; les données ChromaDB persistent sur l'hôte et survivent aux recreate de conteneur ; les deux développeurs voient immédiatement les changements
**Alternative écartée :** `docker cp` à chaque mise à jour — processus manuel error-prone, risque d'oublier de copier et de travailler avec une base vectorielle désynchronisée

---

## Incrémentation obligatoire de version.php à chaque ajout de fichier plugin — Juillet 2026
**Participant :** Yasmine + Islem
**Décision :** Établir la convention d'incrémenter systématiquement le numéro de version dans `version.php` à chaque ajout de nouveau fichier ou modification structurelle du plugin
**Raison :** Moodle détecte les mises à jour du plugin uniquement via le changement de version ; sans incrémentation, les nouveaux fichiers (templates, pix, AMD modules) ne sont pas chargés par Moodle
**Alternative écartée :** Mise à jour de version uniquement pour les releases majeures — cause des bugs silencieux où Moodle ignore les nouveaux assets, difficiles à diagnostiquer


## Chunking — taille optimale — août 2026
**Participant :** Yasmine  + Islem
**Décision :** Taille de chunk retenue : 500 caractères / overlap 50  
**Raison :** Tests comparatifs effectués sur 3 configurations :
- 300/50 → timeout sur résumé, chunks trop petits perdent le contexte
- 500/50 → meilleur équilibre qualité/latence/couverture ✅
- 800/100 → résumé incomplet, moins de chunks distincts récupérés  
**Documenté dans :** `docs/chunking_tests.md`

---

## Cache sémantique — cosine similarity — août 2026
**Participant :** Yasmine  + Islem
**Décision :** Cache en mémoire avec similarité cosinus (seuil 0.92)  
**Raison :** Évite les appels Gemini redondants pour des questions similaires. Clé de cache inclut le `course_id` pour éviter la contamination entre cours. Quiz exclus du cache (JSON structuré toujours régénéré).  
**Validé :** Cache hit — similarité 1.000 testé en logs.

---

## Streaming Gemini — non implémenté — août 2026
**Participant :** Yasmine  + Islem
**Décision :** Streaming non implémenté  
**Raison :** Incompatible avec le cache sémantique et le parsing JSON du quiz. Amélioration future possible pour les modes `chat` et `expliquer` uniquement.

---

## tiktoken — non implémenté — août 2026
**Participant :** Yasmine  + Islem
**Décision :** tiktoken non implémenté  
**Raison :**
Le projet utilise déjà `response.usage_metadata` de l'API Gemini qui retourne
le comptage exact des tokens après chaque appel :
- `prompt_token_count` — tokens d'entrée exacts
- `candidates_token_count` — tokens de sortie exacts
- Ces valeurs sont loggées et stockées dans `edora_usage_logs`

`tiktoken` est calibré pour les modèles OpenAI (GPT), pas Gemini.
Son comptage serait une estimation à ~90% — moins précis que ce qu'on a déjà.

**Alternative retenue :**
Logging post-appel via `usage_metadata` + table `edora_usage_logs` en MariaDB.
Cela permet de répondre à "combien coûte un étudiant par mois ?" avec des données exactes.

---

**Raison :**
L'API Gemini ne propose pas de distinction petit/grand modèle comparable
à GPT-3.5 vs GPT-4. `gemini-3.5-flash` est déjà le modèle le plus
économique disponible avec des performances suffisantes pour tous les
types de tâches du projet (chat, quiz, résumé, explication).

Le gain potentiel ne justifie pas la complexité d'implémentation
dans le cadre de ce stage.

**Alternative retenue :**
Différenciation des `max_output_tokens` par type de tâche :
- `chat` / `exemple` → 2048 tokens
- `resume` → 3072 tokens  
- `quiz` → 6144 tokens
---

## Protection injection prompt — août 2026
**Participant :** Yasmine  + Islem
**Décision :** Délimiteurs XML dans le prompt RAG  
**Implémentation :**
- Chunks encadrés par `<chunk_cours id='N' source='...'>`
- Contexte encadré par `<contexte_cours>...</contexte_cours>`
- Question encadrée par `<question_etudiant>...</question_etudiant>`
- Validation sortie Gemini via `validate_gemini_output()`
- Guardrail périmètre cours dans `BASE_PERSONA`  
**Testé :** 3 tentatives d'injection bloquées — documenté dans `docs/tests_injection.md`

---

## Volume Docker monté — août 2026
**Participant :** Yasmine  + Islem
**Problème :** Chaque merge nécessitait `docker cp` + purge cache + upgrade DB Moodle.  
**Décision :** Décommenter le volume dans `docker-compose.yml` :
```yaml
- ./moodle-plugin/blocks/tutor_ai:/bitnami/moodle/blocks/tutor_ai
```
**Résultat :** Les modifications PHP/JS sont instantanément visibles dans Moodle sans aucune commande manuelle.