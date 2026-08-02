/**
 * Edora AI Tutor — Module chat
 * @author Islem Troudi — Phase 6
 * @author Yasmine — Floating button
 */

(function () {

    let conversationHistory = [];
    let conversationId = 'conv-' + Date.now();
    let lastQuestion  = '';
    let lastApiUrl    = '';
    let lastCourseId  = 0;

    var AVATAR_IMG    = '<img src="/blocks/tutor_ai/pix/edo-avatar.png" style="width:40px;height:40px;border-radius:50%;object-fit:cover;" alt="Edo">';
    var AVATAR_IMG_SM = '<img src="/blocks/tutor_ai/pix/edo-avatar.png" style="width:28px;height:28px;border-radius:50%;object-fit:cover;" alt="Edo">';

    // ── SVG icons ─────────────────────────────────────────────────
    var SVG = {
        copy:   '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>',
        regen:  '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 .49-4.95"/></svg>',
        like:   '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3H14z"/><path d="M7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"/></svg>',
        dislike:'<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 15v4a3 3 0 0 0 3 3l4-9V2H5.72a2 2 0 0 0-2 1.7l-1.38 9a2 2 0 0 0 2 2.3H10z"/><path d="M17 2h2.67A2.31 2.31 0 0 1 22 4v7a2.31 2.31 0 0 1-2.33 2H17"/></svg>',
        check:  '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>'
    };

    function appendMessage(text, role, loading) {
        const messages = document.getElementById('edo-messages');
        const bubble   = document.createElement('div');
        bubble.classList.add('edo-bubble', 'edo-bubble--' + role);

        if (loading) {
            bubble.classList.add('edo-bubble--loading');
            bubble.innerHTML = `
                <div class="edo-thinking">
                    <span class="edo-thinking__text">AI Tutor is thinking</span>
                    <div class="edo-thinking__dots">
                        <span class="edo-dot-anim" style="background:#14b8a6"></span>
                        <span class="edo-dot-anim" style="background:#7c3aed"></span>
                        <span class="edo-dot-anim" style="background:#ec4899"></span>
                    </div>
                </div>`;
        } else {
            const now  = new Date();
            const time = now.getHours().toString().padStart(2,'0') + ':' + now.getMinutes().toString().padStart(2,'0');
            bubble.innerHTML = text.replace(/\n/g, '<br>') + '<div class="edo-timestamp">' + time + '</div>';

            if (role === 'bot') {
                const actions = document.createElement('div');
                actions.classList.add('edo-bubble-actions');

                // Créer chaque bouton proprement (pas de innerHTML avec listeners)
                var btnCopy    = makeActionBtn(SVG.copy   + ' Copier',     'edo-btn-copy',    '#6b7280');
                var btnRegen   = makeActionBtn(SVG.regen  + ' Régénérer',  'edo-btn-regen',   '#6b7280');
                var btnLike    = makeActionBtn(SVG.like,                    'edo-btn-like',    '#6b7280');
                var btnDislike = makeActionBtn(SVG.dislike,                 'edo-btn-dislike', '#6b7280');

                actions.appendChild(btnCopy);
                actions.appendChild(btnRegen);
                actions.appendChild(btnLike);
                actions.appendChild(btnDislike);

                // 📋 Copier
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

                // 🔄 Régénérer
                btnRegen.addEventListener('click', function () {
                    if (!lastQuestion) return;
                    actions.remove();
                    bubble.remove();
                    sendQuestion(lastQuestion, lastApiUrl, lastCourseId);
                });

                // 👍 Like
                btnLike.addEventListener('click', function () {
                    var active = btnLike.classList.contains('edo-feedback-active');
                    // Reset les deux
                    btnLike.classList.remove('edo-feedback-active');
                    btnLike.style.color = '#6b7280';
                    btnDislike.classList.remove('edo-feedback-active');
                    btnDislike.style.color = '#6b7280';
                    // Toggle
                    if (!active) {
                        btnLike.classList.add('edo-feedback-active');
                        btnLike.style.color = '#22c55e';
                        btnLike.style.borderColor = '#22c55e';
                        btnLike.style.background  = '#f0fdf4';
                        btnDislike.style.borderColor = '';
                        btnDislike.style.background  = '';
                    } else {
                        btnLike.style.borderColor = '';
                        btnLike.style.background  = '';
                    }
                });

                // 👎 Dislike
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
                        btnLike.style.borderColor = '';
                        btnLike.style.background  = '';
                    } else {
                        btnDislike.style.borderColor = '';
                        btnDislike.style.background  = '';
                    }
                });

                messages.appendChild(bubble);
                messages.appendChild(actions);
                messages.scrollTop = messages.scrollHeight;
                return bubble;
            }
        }

        messages.appendChild(bubble);
        messages.scrollTop = messages.scrollHeight;
        return bubble;
    }

    function makeActionBtn(html, cls, color) {
        var btn = document.createElement('button');
        btn.className = 'edo-action-btn ' + cls;
        btn.innerHTML = html;
        btn.style.color = color;
        btn.style.display = 'inline-flex';
        btn.style.alignItems = 'center';
        btn.style.gap = '4px';
        return btn;
    }

    async function sendQuestion(question, apiUrl, courseId) {
        const sendBtn = document.getElementById('edo-send');
        const input   = document.getElementById('edo-input');

        lastQuestion = question;
        lastApiUrl   = apiUrl;
        lastCourseId = courseId;

        sendBtn.disabled = true;
        input.disabled   = true;

        appendMessage(question, 'user');
        conversationHistory.push({ role: 'user', content: question });

        const loadingBubble = appendMessage('', 'bot', true);

        try {
            const response = await fetch(apiUrl + '/ask', {
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

            loadingBubble.remove();
            if (!response.ok) throw new Error('HTTP ' + response.status);

            const data = await response.json();
            appendMessage(data.answer, 'bot');
            conversationHistory.push({ role: 'assistant', content: data.answer });

        } catch (error) {
            loadingBubble.remove();
            appendMessage('⚠️ Je n\'arrive pas à joindre le serveur. Vérifie ta connexion et réessaie.', 'bot');
            console.error('[Edora Chat] Erreur fetch:', error);
        } finally {
            sendBtn.disabled = false;
            input.disabled   = false;
            input.focus();
        }
    }

    function buildFloatingUI(apiUrl, courseId) {

        const fab = document.createElement('button');
        fab.id = 'edo-fab';
        fab.className = 'edo-fab';
        fab.setAttribute('aria-label', 'Ouvrir le tuteur IA');
        fab.innerHTML = AVATAR_IMG;

        const panel = document.createElement('div');
        panel.id = 'edo-panel';
        panel.className = 'edo-panel';
        panel.innerHTML = `
            <div class="edo-header">
                <div class="edo-header__avatar">${AVATAR_IMG_SM}</div>
                <div class="edo-header__info">
                    <span class="edo-name">AI Tutor</span>
                    <span class="edo-subtitle">
                        <span class="edo-dot edo-dot--green"></span> En ligne
                    </span>
                </div>
                <div class="edo-header__actions">
                    <button id="edo-minimize" class="edo-header__btn" title="Réduire">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="5" y1="12" x2="19" y2="12"></line></svg>
                    </button>
                    <button id="edo-close" class="edo-header__btn" aria-label="Fermer">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
                    </button>
                </div>
            </div>

            <div id="edo-messages" class="edo-messages" role="log" aria-live="polite">
                <div class="edo-bubble edo-bubble--bot">
                    Bonjour ! Je suis Edo, votre tuteur IA 👋 Posez-moi une question sur le cours.
                </div>
            </div>

            <div class="edo-shortcuts">
                <button class="edo-shortcut" data-question="Explique-moi ce chapitre">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"></path><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"></path></svg>
                    Expliquer
                </button>
                <button class="edo-shortcut" data-question="Génère un quiz sur ce chapitre">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path></svg>
                    Quiz
                </button>
                <button class="edo-shortcut" data-question="Donne-moi un exemple concret">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
                    Exemple
                </button>
                <button class="edo-shortcut" data-question="Résume cette leçon">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="21" y1="10" x2="3" y2="10"></line><line x1="21" y1="6" x2="3" y2="6"></line><line x1="21" y1="14" x2="3" y2="14"></line><line x1="21" y1="18" x2="3" y2="18"></line></svg>
                    Résumer
                </button>
            </div>

            

            <div class="edo-input-row">
                <button class="edo-input-icon" id="edo-attach" title="Joindre fichier">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"></path></svg>
                </button>
                <input type="file" id="edo-file-input" style="display:none;" accept=".pdf,.doc,.docx,.txt,.pptx">
                <input type="text" id="edo-input" class="edo-input"
                    placeholder="Posez une question sur ce cours..."
                    aria-label="Question pour Edo" maxlength="500"/>
                <button class="edo-input-icon" id="edo-vocal" title="Message vocal">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path><path d="M19 10v2a7 7 0 0 1-14 0v-2"></path><line x1="12" y1="19" x2="12" y2="23"></line><line x1="8" y1="23" x2="16" y2="23"></line></svg>
                </button>
                <button id="edo-send" class="edo-send-btn" aria-label="Envoyer">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>
                </button>
            </div>

            <div class="edo-footer">
                <span class="edo-badge">✓ Basé sur le cours</span>
                <span class="edo-badge">✓ RAG activé</span>
            </div>
        `;

        document.body.appendChild(fab);
        document.body.appendChild(panel);

        // FAB toggle
        fab.addEventListener('click', function () {
            var isOpen = panel.classList.toggle('edo-panel--open');
            fab.classList.toggle('edo-fab--open', isOpen);
            if (isOpen) panel.querySelector('#edo-input').focus();
        });

        // Fermer
        panel.querySelector('#edo-close').addEventListener('click', function () {
            panel.classList.remove('edo-panel--open');
            fab.classList.remove('edo-fab--open');
        });

        // Minimiser
        panel.querySelector('#edo-minimize').addEventListener('click', function () {
            var messages   = panel.querySelector('#edo-messages');
            var shortcuts  = panel.querySelector('.edo-shortcuts');
            var footer     = panel.querySelector('.edo-footer');
            var askAnother = panel.querySelector('.edo-ask-another');
            var inputRow   = panel.querySelector('.edo-input-row');
            var min = messages.style.display === 'none';
            messages.style.display   = min ? 'flex'  : 'none';
            if (shortcuts)  shortcuts.style.display  = min ? 'grid'  : 'none';
            if (footer)     footer.style.display     = min ? 'flex'  : 'none';
            if (askAnother) askAnother.style.display = min ? 'block' : 'none';
            if (inputRow)   inputRow.style.display   = min ? 'flex'  : 'none';
        });

        // Raccourcis
        panel.querySelectorAll('.edo-shortcut').forEach(function (btn) {
            btn.addEventListener('click', function () {
                var q = btn.dataset.question;
                if (q) sendQuestion(q, apiUrl, courseId);
            });
        });

        

        /// Joindre fichier
var attachBtn = panel.querySelector('#edo-attach');
var fileInput = panel.querySelector('#edo-file-input');

attachBtn.addEventListener('click', function () { fileInput.click(); });

fileInput.addEventListener('change', async function () {
    var file = fileInput.files[0];
    if (!file) return;

    appendMessage('📎 Fichier joint : ' + file.name, 'user');
    const loadingBubble = appendMessage('', 'bot', true);

    try {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('course_id', courseId);

        const response = await fetch(apiUrl + '/upload-file', {
            method: 'POST',
            body: formData
        });

        loadingBubble.remove();

        if (!response.ok) throw new Error('HTTP ' + response.status);

        const data = await response.json();
        appendMessage('✅ Fichier indexé ! ' + data.chunks_created + ' extraits créés. Tu peux maintenant poser des questions dessus.', 'bot');

    } catch (error) {
        loadingBubble.remove();
        appendMessage('⚠️ Erreur lors de l\'upload du fichier.', 'bot');
        console.error('[Edora Chat] Erreur upload:', error);
    }

    fileInput.value = '';
});

        // Vocal
        var vocalBtn = panel.querySelector('#edo-vocal');
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
            recognition.onstart = function () {
                isListening = true;
                vocalBtn.style.color = '#ec4899';
                vocalBtn.title = 'Parlez... (cliquez pour arrêter)';
            };
            recognition.onresult = function (e) {
                textInput.value = e.results[0][0].transcript;
                textInput.focus();
            };
            recognition.onend = function () {
                isListening = false;
                vocalBtn.style.color = '';
                vocalBtn.title = 'Message vocal';
            };
            recognition.onerror = function (e) {
                isListening = false;
                vocalBtn.style.color = '';
                if (e.error === 'not-allowed') {
                    appendMessage('⚠️ Accès au microphone refusé.', 'bot');
                }
            };
        } else {
            vocalBtn.style.opacity = '0.4';
            vocalBtn.style.cursor = 'not-allowed';
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
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendBtn.click();
            }
        });
    }

    function init() {
        var root = document.getElementById('edo-chat-root');
        if (!root) { console.error('[Edora Chat] #edo-chat-root introuvable.'); return; }
        var apiUrl   = root.dataset.apiUrl;
        var courseId = parseInt(root.dataset.courseId, 10);
        buildFloatingUI(apiUrl, courseId);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();