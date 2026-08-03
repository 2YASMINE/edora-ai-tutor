/**
 * Edora AI Tutor — Module chat
 * @author Islem Troudi — Phase 7 (redesign mockup)
 */

(function () {

    let conversationHistory = [];
    let conversationId = 'conv-' + Date.now();
    let lastQuestion  = '';
    let lastApiUrl    = '';
    let lastCourseId  = 0;
    var root      = document.getElementById('edo-chat-root');
    var avatarUrl = root ? root.dataset.avatarUrl : '';

    var AVATAR_IMG    = '<img src="' + avatarUrl + '" style="width:100%;height:100%;object-fit:cover;" alt="Edo">';
    var AVATAR_IMG_SM = '<img src="' + avatarUrl + '" style="width:28px;height:28px;border-radius:50%;object-fit:cover;" alt="Edo">';

    // ── SVG icons ─────────────────────────────────────────────────
    var SVG = {
        copy:    '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>',
        regen:   '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 .49-4.95"/></svg>',
        like:    '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3H14z"/><path d="M7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"/></svg>',
        dislike: '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 15v4a3 3 0 0 0 3 3l4-9V2H5.72a2 2 0 0 0-2 1.7l-1.38 9a2 2 0 0 0 2 2.3H10z"/><path d="M17 2h2.67A2.31 2.31 0 0 1 22 4v7a2.31 2.31 0 0 1-2.33 2H17"/></svg>',
        check:   '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>',
        expand:  '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 3 21 3 21 9"/><polyline points="9 21 3 21 3 15"/><line x1="21" y1="3" x2="14" y2="10"/><line x1="3" y1="21" x2="10" y2="14"/></svg>',
        minimize:'<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="5" y1="12" x2="19" y2="12"/></svg>',
        close:   '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>',
        shield:  '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>',
        attach:  '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/></svg>',
        doc:     '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>',
        send:    '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.2"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>',
        mic:     '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/></svg>',
        book:    '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/></svg>',
        quiz:    '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>',
        bulb:    '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>',
        list:    '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="21" y1="10" x2="3" y2="10"/><line x1="21" y1="6" x2="3" y2="6"/><line x1="21" y1="14" x2="3" y2="14"/><line x1="21" y1="18" x2="3" y2="18"/></svg>'
    };

    // ── Temps formaté ──────────────────────────────────────────────
    function getTime() {
        var now = new Date();
        return now.getHours().toString().padStart(2,'0') + ':' + now.getMinutes().toString().padStart(2,'0');
    }

    // ── Supprimer les suggestions contextuelles ────────────────────
    function clearSuggestions(panel) {
        var existing = panel.querySelector('.edo-dynamic-suggestions');
        if (existing) existing.remove();
    }

    // ── Afficher suggestions après une réponse bot ─────────────────
    function showSuggestions(panel, questions, apiUrl, courseId) {
        clearSuggestions(panel);
        if (!questions || questions.length === 0) return;

        var icons = [SVG.book, SVG.doc, SVG.bulb];
        var container = document.createElement('div');
        container.className = 'edo-suggestions edo-dynamic-suggestions';

        questions.forEach(function (q, i) {
            var btn = document.createElement('button');
            btn.className = 'edo-suggestion-btn';
            var iconDiv = document.createElement('span');
            iconDiv.className = 'edo-suggestion-icon';
            iconDiv.innerHTML = icons[i % icons.length];
            btn.appendChild(iconDiv);
            var text = document.createElement('span');
            text.textContent = q;
            btn.appendChild(text);
            btn.addEventListener('click', function () {
                clearSuggestions(panel);
                sendQuestion(q, apiUrl, courseId);
            });
            container.appendChild(btn);
        });

        var inputRow = panel.querySelector('.edo-input-row');
        panel.insertBefore(container, inputRow);
    }

    // ── Append message ─────────────────────────────────────────────
    function appendMessage(text, role, loading) {
        var panel    = document.getElementById('edo-panel');
        var messages = document.getElementById('edo-messages');

        if (role === 'bot' && !loading) {
            // Row avec avatar
            var row = document.createElement('div');
            row.classList.add('edo-bot-row');

            var avatarDiv = document.createElement('div');
            avatarDiv.className = 'edo-bot-avatar';
            avatarDiv.innerHTML = AVATAR_IMG;
            row.appendChild(avatarDiv);

            var bubble = document.createElement('div');
            bubble.classList.add('edo-bubble', 'edo-bubble--bot');
            bubble.innerHTML = text.replace(/\n/g, '<br>') + '<div class="edo-timestamp">' + getTime() + '</div>';
            row.appendChild(bubble);

            messages.appendChild(row);
            messages.scrollTop = messages.scrollHeight;

            // Actions sous la bulle
            var actions = document.createElement('div');
            actions.classList.add('edo-bubble-actions');

            var btnCopy    = makeActionBtn(SVG.copy   + ' Copier',    'edo-btn-copy',    '#6b7280');
            var btnRegen   = makeActionBtn(SVG.regen  + ' Régénérer', 'edo-btn-regen',   '#6b7280');
            var btnLike    = makeActionBtn(SVG.like,                   'edo-btn-like',    '#6b7280');
            var btnDislike = makeActionBtn(SVG.dislike,                'edo-btn-dislike', '#6b7280');

            actions.appendChild(btnCopy);
            actions.appendChild(btnRegen);
            actions.appendChild(btnLike);
            actions.appendChild(btnDislike);

            btnCopy.addEventListener('click', function () {
                navigator.clipboard.writeText(text).then(function () {
                    btnCopy.innerHTML = SVG.check + ' Copié';
                    btnCopy.style.color = '#22c55e';
                    setTimeout(function () {
                        btnCopy.innerHTML = SVG.copy + ' Copier';
                        btnCopy.style.color = '#6b7280';
                    }, 2000);
                });
            });

            btnRegen.addEventListener('click', function () {
                if (!lastQuestion) return;
                actions.remove();
                row.remove();
                clearSuggestions(panel);
                sendQuestion(lastQuestion, lastApiUrl, lastCourseId);
            });

            btnLike.addEventListener('click', function () {
                var active = btnLike.classList.contains('edo-feedback-active');
                btnLike.classList.remove('edo-feedback-active');
                btnLike.style.color = '#6b7280';
                btnDislike.classList.remove('edo-feedback-active');
                btnDislike.style.color = '#6b7280';
                btnDislike.style.borderColor = '';
                btnDislike.style.background  = '';
                if (!active) {
                    btnLike.classList.add('edo-feedback-active');
                    btnLike.style.color = '#22c55e';
                    btnLike.style.borderColor = '#22c55e';
                    btnLike.style.background  = '#f0fdf4';
                } else {
                    btnLike.style.borderColor = '';
                    btnLike.style.background  = '';
                }
            });

            btnDislike.addEventListener('click', function () {
                var active = btnDislike.classList.contains('edo-feedback-active');
                btnLike.classList.remove('edo-feedback-active');
                btnLike.style.color = '#6b7280';
                btnLike.style.borderColor = '';
                btnLike.style.background  = '';
                btnDislike.classList.remove('edo-feedback-active');
                btnDislike.style.color = '#6b7280';
                if (!active) {
                    btnDislike.classList.add('edo-feedback-active');
                    btnDislike.style.color = '#ef4444';
                    btnDislike.style.borderColor = '#ef4444';
                    btnDislike.style.background  = '#fef2f2';
                } else {
                    btnDislike.style.borderColor = '';
                    btnDislike.style.background  = '';
                }
            });

            messages.appendChild(actions);
            messages.scrollTop = messages.scrollHeight;
            return row;

        } else if (loading) {
            var row2 = document.createElement('div');
            row2.classList.add('edo-bot-row');

            var av2 = document.createElement('div');
            av2.className = 'edo-bot-avatar';
            av2.innerHTML = AVATAR_IMG;
            row2.appendChild(av2);

            var bubble2 = document.createElement('div');
            bubble2.classList.add('edo-bubble', 'edo-bubble--loading');
            bubble2.innerHTML = `
                <div class="edo-thinking">
                    <span class="edo-thinking__text">Edo réfléchit</span>
                    <div class="edo-thinking__dots">
                        <span class="edo-dot-anim" style="background:#0d8a8a"></span>
                        <span class="edo-dot-anim" style="background:#7c3aed"></span>
                        <span class="edo-dot-anim" style="background:#ec4899"></span>
                    </div>
                </div>`;
            row2.appendChild(bubble2);

            messages.appendChild(row2);
            messages.scrollTop = messages.scrollHeight;
            return row2;

        } else {
            // User bubble
            var bubble3 = document.createElement('div');
            bubble3.classList.add('edo-bubble', 'edo-bubble--user');
            bubble3.innerHTML = text.replace(/\n/g, '<br>') + '<div class="edo-timestamp">' + getTime() + ' ✓✓</div>';
            messages.appendChild(bubble3);
            messages.scrollTop = messages.scrollHeight;
            return bubble3;
        }
    }

    function makeActionBtn(html, cls, color) {
        var btn = document.createElement('button');
        btn.className = 'edo-action-btn ' + cls;
        btn.innerHTML = html;
        btn.style.color = color;
        return btn;
    }

    // ── Send question ──────────────────────────────────────────────
    async function sendQuestion(question, apiUrl, courseId) {
        var panel   = document.getElementById('edo-panel');
        var sendBtn = document.getElementById('edo-send');
        var input   = document.getElementById('edo-input');

        lastQuestion = question;
        lastApiUrl   = apiUrl;
        lastCourseId = courseId;

        sendBtn.disabled = true;
        input.disabled   = true;

        clearSuggestions(panel);
        appendMessage(question, 'user');
        conversationHistory.push({ role: 'user', content: question });

        var loadingRow = appendMessage('', 'bot', true);

        try {
            var response = await fetch(apiUrl + '/ask', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    question:             question,
                    course_id:            courseId,
                    student_id:           0,
                    conversation_id:      conversationId,
                    conversation_history: conversationHistory.slice(-6)
                })
            });

            loadingRow.remove();
            if (!response.ok) throw new Error('HTTP ' + response.status);

            var data = await response.json();
            appendMessage(data.answer, 'bot');
            conversationHistory.push({ role: 'assistant', content: data.answer });

            // Suggestions de suivi si l'API en retourne
            if (data.follow_up_questions && data.follow_up_questions.length > 0) {
                showSuggestions(panel, data.follow_up_questions, apiUrl, courseId);
            }

        } catch (error) {
            loadingRow.remove();
            appendMessage('⚠️ Je n\'arrive pas à joindre le serveur. Vérifie ta connexion et réessaie.', 'bot');
            console.error('[Edora Chat] Erreur fetch:', error);
        } finally {
            sendBtn.disabled = false;
            input.disabled   = false;
            input.focus();
        }
    }

    // ── Build UI ───────────────────────────────────────────────────
    function buildFloatingUI(apiUrl, courseId) {

        // FAB
        var fab = document.createElement('button');
        fab.id = 'edo-fab';
        fab.className = 'edo-fab';
        fab.setAttribute('aria-label', 'Ouvrir le tuteur IA');
        fab.innerHTML = AVATAR_IMG;

        // Panel
        var panel = document.createElement('div');
        panel.id = 'edo-panel';
        panel.className = 'edo-panel';

        panel.innerHTML = `
            <!-- HEADER -->
            <div class="edo-header">
                <div class="edo-header__avatar">${AVATAR_IMG}</div>
                <div class="edo-header__info">
                    <span class="edo-name">
                        Edora AI Tutor
                        <span class="edo-name-badge">BETA</span>
                    </span>
                    <span class="edo-subtitle">
                        <span class="edo-dot edo-dot--green"></span>
                        Votre assistant intelligent pour vos cours
                    </span>
                </div>
                <div class="edo-header__actions">
                    <button id="edo-minimize" class="edo-header__btn" title="Réduire">${SVG.minimize}</button>
                    <button id="edo-close"    class="edo-header__btn" aria-label="Fermer">${SVG.close}</button>
                </div>
            </div>

            <!-- MESSAGES -->
            <div id="edo-messages" class="edo-messages" role="log" aria-live="polite">
                <div class="edo-bot-row">
                    <div class="edo-bot-avatar">${AVATAR_IMG}</div>
                    <div class="edo-bubble edo-bubble--bot">
                        Bonjour ! Je suis Edo, votre tuteur IA 👋<br>
                        Posez-moi une question sur le contenu de ce cours.
                        <div class="edo-timestamp">${getTime()}</div>
                    </div>
                </div>
            </div>

            <!-- SHORTCUTS -->
            <div class="edo-shortcuts">
                <button class="edo-shortcut" data-question="Explique-moi ce chapitre">
                    ${SVG.book} Expliquer
                </button>
                <button class="edo-shortcut" data-question="Génère un quiz sur ce chapitre">
                    ${SVG.quiz} Quiz
                </button>
                <button class="edo-shortcut" data-question="Donne-moi un exemple concret">
                    ${SVG.bulb} Exemple
                </button>
                <button class="edo-shortcut" data-question="Résume cette leçon">
                    ${SVG.list} Résumer
                </button>
            </div>

            <!-- INPUT -->
            <div class="edo-input-row">
                <button class="edo-input-icon" id="edo-attach" title="Joindre fichier">${SVG.attach}</button>
                <input type="file" id="edo-file-input" style="display:none;" accept=".pdf,.doc,.docx,.txt,.pptx">
                <input type="text" id="edo-input" class="edo-input"
                    placeholder="Posez votre question sur le contenu du cours..."
                    aria-label="Question pour Edo" maxlength="500"/>
                <button class="edo-input-icon" id="edo-vocal" title="Message vocal">${SVG.mic}</button>
                <button id="edo-send" class="edo-send-btn" aria-label="Envoyer">${SVG.send}</button>
            </div>

            <!-- FOOTER DISCLAIMER -->
            <div class="edo-footer">
                <span class="edo-footer-icon">${SVG.shield}</span>
                <span class="edo-footer-text">Réponses générées à partir du contenu de vos cours. Vérifiez toujours les informations importantes.</span>
            </div>
        `;

        document.body.appendChild(fab);
        document.body.appendChild(panel);

        // FAB toggle
        fab.addEventListener('click', function () {
            var isOpen = panel.classList.toggle('edo-panel--open');
            fab.classList.toggle('edo-fab--open', isOpen);
            if (isOpen) setTimeout(function() { panel.querySelector('#edo-input').focus(); }, 300);
        });

        // Fermer
        panel.querySelector('#edo-close').addEventListener('click', function () {
            panel.classList.remove('edo-panel--open');
            fab.classList.remove('edo-fab--open');
        });

        // Minimiser
        panel.querySelector('#edo-minimize').addEventListener('click', function () {
            var messages  = panel.querySelector('#edo-messages');
            var shortcuts = panel.querySelector('.edo-shortcuts');
            var footer    = panel.querySelector('.edo-footer');
            var dynSug    = panel.querySelector('.edo-dynamic-suggestions');
            var inputRow  = panel.querySelector('.edo-input-row');
            var min = messages.style.display === 'none';
            messages.style.display  = min ? 'flex' : 'none';
            shortcuts.style.display = min ? 'grid' : 'none';
            footer.style.display    = min ? 'flex' : 'none';
            inputRow.style.display  = min ? 'flex' : 'none';
            if (dynSug) dynSug.style.display = min ? 'flex' : 'none';
        });

        // Raccourcis
        panel.querySelectorAll('.edo-shortcut').forEach(function (btn) {
            btn.addEventListener('click', function () {
                var q = btn.dataset.question;
                if (q) sendQuestion(q, apiUrl, courseId);
            });
        });

        // Joindre fichier
        var attachBtn = panel.querySelector('#edo-attach');
        var fileInput = panel.querySelector('#edo-file-input');

        attachBtn.addEventListener('click', function () { fileInput.click(); });

        fileInput.addEventListener('change', async function () {
            var file = fileInput.files[0];
            if (!file) return;

            appendMessage('📎 Fichier joint : ' + file.name, 'user');
            var loadingRow = appendMessage('', 'bot', true);

            try {
                var formData = new FormData();
                formData.append('file', file);
                formData.append('course_id', courseId);

                var response = await fetch(apiUrl + '/upload-file', {
                    method: 'POST',
                    body: formData
                });

                loadingRow.remove();
                if (!response.ok) throw new Error('HTTP ' + response.status);

                var data = await response.json();
                appendMessage('✅ Fichier indexé ! ' + data.chunks_created + ' extraits créés. Tu peux maintenant poser des questions dessus.', 'bot');

            } catch (error) {
                loadingRow.remove();
                appendMessage('⚠️ Erreur lors de l\'upload du fichier.', 'bot');
                console.error('[Edora Chat] Erreur upload:', error);
            }

            fileInput.value = '';
        });

        // Vocal
        var vocalBtn  = panel.querySelector('#edo-vocal');
        var textInput = panel.querySelector('#edo-input');

        if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
            var SR = window.SpeechRecognition || window.webkitSpeechRecognition;
            var recognition = new SR();
            recognition.lang = 'fr-FR';
            recognition.continuous = false;
            recognition.interimResults = false;
            var isListening = false;

            vocalBtn.addEventListener('click', function () {
                if (isListening) { recognition.stop(); return; }
                recognition.start();
            });
            recognition.onstart  = function () { isListening = true;  vocalBtn.style.color = '#ec4899'; vocalBtn.title = 'Parlez… (cliquez pour arrêter)'; };
            recognition.onresult = function (e) { textInput.value = e.results[0][0].transcript; textInput.focus(); };
            recognition.onend    = function () { isListening = false; vocalBtn.style.color = ''; vocalBtn.title = 'Message vocal'; };
            recognition.onerror  = function (e) {
                isListening = false; vocalBtn.style.color = '';
                if (e.error === 'not-allowed') appendMessage('⚠️ Accès au microphone refusé.', 'bot');
            };
        } else {
            vocalBtn.style.opacity = '0.4';
            vocalBtn.style.cursor  = 'not-allowed';
            vocalBtn.title = 'Non supporté par ce navigateur';
        }

        // Envoi
        var sendBtn = panel.querySelector('#edo-send');
        sendBtn.addEventListener('click', function () {
            var q = textInput.value.trim();
            if (!q) return;
            textInput.value = '';
            sendQuestion(q, apiUrl, courseId);
        });
        textInput.addEventListener('keydown', function (e) {
            if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendBtn.click(); }
        });
    }

    // ── Init ───────────────────────────────────────────────────────
    function init() {
        var root = document.getElementById('edo-chat-root');
        if (!root) { console.error('[Edora Chat] #edo-chat-root introuvable.'); return; }
        buildFloatingUI(root.dataset.apiUrl, parseInt(root.dataset.courseId, 10));
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();