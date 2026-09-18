# Journal de bord — block_tutor_ai

---

## 13/07/2026 — Yasmine & Islem

### Tâches accomplies
- Installé Moodle 4.4 via Docker (MariaDB 10.11 + moodlehq/moodle-php-apache:8.2)
- Résolu problème `dbtype mysqli` → `mariadb` dans `config.php`
- Testé API Gemini → modèle retenu : `gemini-3.5-flash`
- Étudié structure plugin Moodle de type block
- Créé squelette complet du plugin `block_tutor_ai` (7 fichiers)
- Plugin installé et visible dans Moodle ✅

### Décisions prises
- Modèle LLM retenu : `gemini-3.5-flash` (gratuit, disponible en Tunisie)
- Tier gratuit généreux adapté à un projet de stage sans budget

### Problèmes rencontrés
- `dbtype mysqli` non reconnu → solution : `mariadb` dans `config.php`
- MariaDB 11.8 crée les bases avec collation `utf8mb4_uca1400_ai_ci` non reconnue par Moodle → solution : forcer `utf8mb4_unicode_ci` via `MARIADB_EXTRA_FLAGS` dans docker-compose.yml
- Leçon : toujours faire `docker compose down -v` avant de tester une correction

---

## 14/07/2026 — Yasmine

### Tâches accomplies
- Configuré l'environnement Bitnami (docker-compose d'Islem)
- Résolu conflit port 3306 (MySQL Windows) → changé vers 3307
- Résolu conflit port 8080 → changé vers 8082
- Installé et testé l'API Gemini → modèle retenu : `gemini-3.5-flash`
- Copié et installé le plugin `block_tutor_ai` dans Moodle Bitnami
- Pushé tout le travail sur le repo officiel Edora

### Décisions prises
- Repo officiel : `edoralms-moodle-block_ai_tutor_03`

### Problèmes rencontrés
- Port 3306 occupé par MySQL Windows → solution : changer vers 3307
- Port 8080 occupé → solution : changer vers 8082
- Plugin non trouvé dans repo → solution : copié depuis ancien container

### Prochaine étape
- Squelette FastAPI (microservice Python)

---

## 15/07/2026 — Yasmine
### Phase 2 — Squelette FastAPI

### Tâches accomplies
- Créé le squelette FastAPI (microservice IA)
  - Endpoints : `/health`, `/ask`, `/upload-resource`
  - Structure : `main.py`, `routers/`, `services/`, `models/`
  - Documentation automatique sur `/docs`
- Validé la communication Hello World plugin Moodle → FastAPI
  - Moodle appelle `http://host.docker.internal:8000/health`
  - Réponse affichée dans le bloc Tutor AI ✅
- Pushé tout le travail sur `main`

### Architecture microservice
- Framework : FastAPI + Uvicorn
- Communication : HTTP REST entre plugin PHP et microservice Python
- URL Docker : `host.docker.internal:8000`

### Prochaine étape
- Endpoint déclencheur d'extraction (Phase 3)

---

## 20/07/2026 — Yasmine
### Phase 3 — Pipeline d'ingestion

### Tâches accomplies
- Récupéré le code d'Islem (extraction PDF/DOCX/PPTX/TXT + pages Moodle)
- Installé les dépendances : `pdfplumber`, `python-docx`, `python-pptx`, `beautifulsoup4`, `python-dotenv`
- Configuré token Moodle dans `.env` (web services activés, REST activé, service Edora AI créé)
- Testé extraction PDF → OK
- Testé extraction pages Moodle → OK | 1 section
- Créé `db/events.php` → enregistre l'observer Moodle
- Créé `classes/observer.php` → appelle `/upload-resource` automatiquement
- Testé → upload PDF dans Moodle déclenche bien le microservice ✅
- Phase 3 complète ✅

### Prochaine étape
- Phase 4 : Chunking + Embeddings + ChromaDB

---

## Fin juillet 2026 — Yasmine & Islem
### Phase 4 — Chunking, Embeddings, ChromaDB

### Tâches accomplies (Yasmine)
- Implémenté `chunker.py` — découpage LangChain (`RecursiveCharacterTextSplitter`)
- Implémenté `embeddings.py` — vecteurs 3072 dimensions via `gemini-embedding-2`

### Tâches accomplies (Islem)
- Implémenté `chroma_service.py` — stockage dans ChromaDB (collection `course_X`)
- Tests d'intégration pipeline complet ✅

### Pipeline RAG (indexation)
```
Prof uploade PDF → Observer PHP → /upload-resource
→ document_extractor.py → chunker.py → embeddings.py → chroma_service.py (ChromaDB)
```

### Prochaine étape
- Phase 5 : Construction du prompt + Appel Gemini

---

## Début août 2026 — Yasmine & Islem
### Phase 5 — Prompt pédagogique + Appel Gemini

### Tâches accomplies (Yasmine)
- Conçu le prompt système avec persona tuteur (Edo)
- Implémenté la classification de questions via `classify_question()`
- Prompts spécialisés par type de tâche (explication, quiz, résumé…)
- Ajout few-shot examples et délimiteurs RAG (`<contexte_cours>` / `<question_etudiant>`)
- Détection de détresse étudiante
- Sanitization des inputs

### Tâches accomplies (Islem)
- Implémenté `gemini.py` — appel API Gemini + gestion erreurs/timeouts/logging

### Prochaine étape
- Phase 6 : Interface chat UI

---

## Mi-août 2026 — Yasmine & Islem
### Phase 6 — Interface Chat UI

### Tâches accomplies
- Interface chat flottante dans le bloc Moodle (panel + avatar Edo)
- Boutons d'action SVG (quiz, résumé, explication…)
- `chat.js` AMD module complet
- `chat.mustache` template Moodle
- `styles.css` — UI responsive

### Notes techniques
- JS déployé via `docker cp` + `php admin/cli/purge_caches.php`
- Volume mount Docker configuré pour éviter les `docker cp` répétés

---

## Fin août 2026 — Yasmine & Islem
### Phase 7 — Historique de conversation

### Tâches accomplies
- Table MariaDB `mdl_edora_conversations` pour persister les échanges
- `history_service.py` — `save_message()` + récupération historique par session
- Historique injecté dans le contexte Gemini à chaque appel
- `conversation_id` transmis depuis le frontend

---

## Début septembre 2026 — Yasmine
### Feature — Transcription vidéo (Whisper + yt-dlp)
**Branche :** `feature/yasmine-whisper-video`

### Tâches accomplies
- Intégration Whisper pour transcription audio/vidéo
- Intégration yt-dlp pour extraction audio
- Chunking timestamp-aware `[MM:SS]` dans `chunker.py`
- `document_extractor.py` étendu pour les formats vidéo
- `observer.php` mis à jour pour détecter les extensions vidéo

### Problèmes connus
- `ffmpeg_location` hardcodé — à déplacer dans `FFMPEG_PATH` env var
- Observer Moodle ne déclenche pas toujours fiablement pour les uploads mp4

---

## Début septembre 2026 — Yasmine
### Feature — Flashcards
**Branche :** `feature/yasmine-flashcards`

### Tâches accomplies
- Endpoint `POST /flashcards` dans FastAPI
- `generate_flashcards()` dans `gemini.py`
- UI flip card grid dans `chat.js` (CSS animation)

### Bugs résolus
- `TASK_KEYWORDS` mal configuré (string au lieu de liste) → crash 503 dans `classify_question()`
- URL regex fix : `.replace(/\/ask$/, '') + '/flashcards'` au lieu de string replace

---

## Mi-septembre 2026 — Islem
### Features — Mindmap, Gap detection, Rapport PDF, Slider reformulation
**Branche :** `feature/mindmap`

### Tâches accomplies
- Slider de reformulation des réponses (Gemini)
- Détection automatique des lacunes du cours (questions à faible similarité → MariaDB)
- Générateur de rapport PDF de session (reportlab + Gemini)
- Bouton expand du panel chat

---

## 19-23 août 2026 — Yasmine & Islem
### Phase 8 — Amélioration Qualité & Performance

### Tâches accomplies (Yasmine)
- Refactoring Prompt Engineering (Priorité CRITIQUE)
- Système de détection du niveau étudiant (Priorité CRITIQUE)
- Amélioration des 4 icônes fonctionnelles (Priorité HAUTE)
- Performance : Cache sémantique + Chunking optimisé
- Support nouveaux formats de fichiers

### Tâches accomplies (Islem)
- Gestion de l'historique : Résumé des anciens tours
- Instrumentation tokens + Logging des coûts

---

## 25-26 août 2026 — Yasmine & Islem
### Phase 9 — Sécurité & Fiabilité

### Tâches accomplies (Yasmine)
- Protection injection de prompt (Priorité CRITIQUE)
- Guardrails : Rester dans le périmètre du cours

### Tâches accomplies (Islem)
- Pseudonymisation des données étudiants (RGPD)
- Backoff exponentiel + Plafond de dépenses par session


---

## 29 août — 6 septembre 2026 — Yasmine & Islem
### Phase 10 — Amélioration Qualité & Performance V2

### Tâches accomplies (Islem)
- TTS — lecture vocale des réponses
- Dark / Light mode
- Mode Examen Anti-triche
- Dashboard enseignant analytique
- Barre progression maîtrise
- Mind Map interactive
- Téléchargement rapport dans le dashboard admin

### Tâches accomplies (Yasmine)
- Détection humeur étudiant
- Flashcards interactives
- Explain Like I'm… slider
- Rapport PDF session étudiant

---

## 14-15 septembre 2026 — Yasmine & Islem
### Phase 11 — Tests + Documentation

### Tâches accomplies
- Tests fonctionnels end-to-end
- Préparation démonstration/déploiement Edora (instance live)

---

## 15-16/09/2026 — Yasmine
### Feature — Génération d'image pédagogique + Système XP
**Branche :** `feature/xp-rewards`

### Génération d'image ( Islem)

- Endpoint `/generate-image` (version initiale)
- Appel à la fonction résumé dans le bouton génération image
- Refactoring endpoint `/generate-image`
- Prompt few-shot 5 exemples domaine-spécifiques (UML, IA, BDD, Architecture, Marketing)
- Fix parsing JSON : `rfind('}')` au lieu de regex non-greedy
- `max_output_tokens=2048`, `response_mime_type='application/json'`, `temperature=0.4`
- Détection mots-clés image depuis `chat.js` → route vers `triggerGenerateImage()`
- Paramètre `concept` ajouté dans `GenerateImageRequest` pour cibler un sujet précis
- Modèle retenu : `gemini-2.5-flash-image` (Imagen arrêté depuis juin 2026)

### Système XP & Badges(Yasmine)
- Table `mdl_edora_xp` créée
- Router `xp.py` : `GET /xp`, `POST /xp/add`
- Widget XP dans le header du chat + notifications animées
- Badges : 🌱 Première question · 🔥 Curieux · 🏆 Quiz Master · 📚 Chercheur de savoir · 🚀 Expert
- Niveaux : Bronze → Argent → Or → Platine → Diamant
- XP non accordé pour le small talk (`isSmallTalk()` côté JS)

### Autres fixes
- Fix scroll quiz : `scrollIntoView` vers `nextCard` après réponse
- Fix `task_type` logging : `save_message()` accepte maintenant `task_type` optionnel
- Fix course selector dashboard : `$teacher_courses` au lieu de `$courses_with_data`
- Period filters dashboard (`Aujourd'hui / Cette semaine / Ce mois / Tout`) — partiel (bug heatmap `ec.created_at`)
