/**
 * Edora AI Tutor — Module chat
 * @author Islem Troudi — Phase 7 (historique + panneau latéral)
 * @author Yasmine — Floating button + MariaDB schema
 */

(function () {

    let conversationHistory = [];
    let conversationId      = 'conv-' + Date.now();
    let lastQuestion        = '';
    let lastApiUrl          = '';
    let lastCourseId        = 0;

    var rootEl     = document.getElementById('edo-chat-root');
    var avatarUrl  = rootEl ? rootEl.dataset.avatarUrl : '';

    var AVATAR_IMG    = '<img src="' + avatarUrl + '" style="width:100%;height:100%;object-fit:cover;" alt="Edo">';
    var AVATAR_IMG_SM = '<img src="' + avatarUrl + '" style="width:28px;height:28px;border-radius:50%;object-fit:cover;" alt="Edo">';

    var SVG = {
        copy:    '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>',
        regen:   '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 .49-4.95"/></svg>',
        like:    '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3H14z"/><path d="M7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"/></svg>',
        dislike: '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 15v4a3 3 0 0 0 3 3l4-9V2H5.72a2 2 0 0 0-2 1.7l-1.38 9a2 2 0 0 0 2 2.3H10z"/><path d="M17 2h2.67A2.31 2.31 0 0 1 22 4v7a2.31 2.31 0 0 1-2.33 2H17"/></svg>',
        check:   '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>',
        shield:  '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>',
        attach:  '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/></svg>',
        send:    '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.2"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>',
        mic:     '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/></svg>',
        minimize:'<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="5" y1="12" x2="19" y2="12"/></svg>',
        close:   '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>',
        history: '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>',
        book:    '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/></svg>',
        quiz:    '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>',
        bulb:    '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>',
        list:    '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="21" y1="10" x2="3" y2="10"/><line x1="21" y1="6" x2="3" y2="6"/><line x1="21" y1="14" x2="3" y2="14"/><line x1="21" y1="18" x2="3" y2="18"/></svg>',
        chat:    '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>',
        plus:    '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>'
    };

    function getTime() {
        var now = new Date();
        return now.getHours().toString().padStart(2,'0') + ':' + now.getMinutes().toString().padStart(2,'0');
    }

    function formatDate(str) {
        try {
            var d = new Date(str);
            return d.toLocaleDateString('fr-FR', { day:'2-digit', month:'short' })
                 + ' ' + d.getHours().toString().padStart(2,'0')
                 + ':' + d.getMinutes().toString().padStart(2,'0');
        } catch(e) { return str; }
    }

    // ── Suggestions dynamiques ─────────────────────────────────
    function clearSuggestions() {
        var panel = document.getElementById('edo-panel');
        var existing = panel ? panel.querySelector('.edo-dynamic-suggestions') : null;
        if (existing) existing.remove();
    }

    function showSuggestions(questions, apiUrl, courseId) {
        clearSuggestions();
        var panel = document.getElementById('edo-panel');
        if (!questions || questions.length === 0 || !panel) return;
        var icons = [SVG.book, SVG.bulb, SVG.list];
        var container = document.createElement('div');
        container.className = 'edo-suggestions edo-dynamic-suggestions';
        questions.forEach(function (q, i) {
            var btn = document.createElement('button');
            btn.className = 'edo-suggestion-btn';
            btn.innerHTML = '<span class="edo-suggestion-icon">' + icons[i % icons.length] + '</span><span>' + q + '</span>';
            btn.addEventListener('click', function () {
                clearSuggestions();
                sendQuestion(q, apiUrl, courseId);
            });
            container.appendChild(btn);
        });
        var inputRow = panel.querySelector('.edo-input-row');
        panel.insertBefore(container, inputRow);
    }

    // ── Append message ─────────────────────────────────────────
    function appendMessage(text, role, loading) {
        var messages = document.getElementById('edo-messages');
        if (!messages) return null;

        if (role === 'bot' && !loading) {
            var row = document.createElement('div');
            row.classList.add('edo-bot-row');

            var av = document.createElement('div');
            av.className = 'edo-bot-avatar';
            av.innerHTML = AVATAR_IMG_SM;
            row.appendChild(av);

            var bubble = document.createElement('div');
            bubble.classList.add('edo-bubble', 'edo-bubble--bot');
            bubble.innerHTML = text.replace(/\n/g, '<br>') + '<div class="edo-timestamp">' + getTime() + '</div>';
            row.appendChild(bubble);
            messages.appendChild(row);
            messages.scrollTop = messages.scrollHeight;

            // Actions
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
                    setTimeout(function () { btnCopy.innerHTML = SVG.copy + ' Copier'; btnCopy.style.color = '#6b7280'; }, 2000);
                });
            });
            btnRegen.addEventListener('click', function () {
                if (!lastQuestion) return;
                actions.remove(); row.remove(); clearSuggestions();
                sendQuestion(lastQuestion, lastApiUrl, lastCourseId);
            });
            btnLike.addEventListener('click', function () {
                var active = btnLike.classList.toggle('edo-feedback-active');
                btnLike.style.color = active ? '#22c55e' : '#6b7280';
                btnLike.style.borderColor = active ? '#22c55e' : '';
                btnLike.style.background  = active ? '#f0fdf4' : '';
                btnDislike.classList.remove('edo-feedback-active');
                btnDislike.style.color = '#6b7280'; btnDislike.style.borderColor = ''; btnDislike.style.background = '';
            });
            btnDislike.addEventListener('click', function () {
                var active = btnDislike.classList.toggle('edo-feedback-active');
                btnDislike.style.color = active ? '#ef4444' : '#6b7280';
                btnDislike.style.borderColor = active ? '#ef4444' : '';
                btnDislike.style.background  = active ? '#fef2f2' : '';
                btnLike.classList.remove('edo-feedback-active');
                btnLike.style.color = '#6b7280'; btnLike.style.borderColor = ''; btnLike.style.background = '';
            });

            messages.appendChild(actions);
            messages.scrollTop = messages.scrollHeight;
            return row;

        } else if (loading) {
            var row2 = document.createElement('div');
            row2.classList.add('edo-bot-row');
            var av2 = document.createElement('div');
            av2.className = 'edo-bot-avatar';
            av2.innerHTML = AVATAR_IMG_SM;
            row2.appendChild(av2);
            var b2 = document.createElement('div');
            b2.classList.add('edo-bubble', 'edo-bubble--loading');
            b2.innerHTML = '<div class="edo-thinking"><span class="edo-thinking__text">Edo réfléchit</span><div class="edo-thinking__dots"><span class="edo-dot-anim" style="background:#0a9396"></span><span class="edo-dot-anim" style="background:#7c3aed"></span><span class="edo-dot-anim" style="background:#ec4899"></span></div></div>';
            row2.appendChild(b2);
            messages.appendChild(row2);
            messages.scrollTop = messages.scrollHeight;
            return row2;

        } else {
            var b3 = document.createElement('div');
            b3.classList.add('edo-bubble', 'edo-bubble--user');
            b3.innerHTML = text.replace(/\n/g, '<br>') + '<div class="edo-timestamp">' + getTime() + ' ✓✓</div>';
            messages.appendChild(b3);
            messages.scrollTop = messages.scrollHeight;
            return b3;
        }
    }

    function makeActionBtn(html, cls, color) {
        var btn = document.createElement('button');
        btn.className = 'edo-action-btn ' + cls;
        btn.innerHTML = html;
        btn.style.color = color;
        return btn;
    }

    // ── Séparateur visuel dans les messages ────────────────────
    function addSeparator(label) {
        var messages = document.getElementById('edo-messages');
        if (!messages) return;
        var sep = document.createElement('div');
        sep.style.cssText = 'text-align:center;font-size:11px;color:#9ca3af;padding:8px 0;display:flex;align-items:center;gap:8px;';
        sep.innerHTML = '<span style="flex:1;height:1px;background:#e5e7eb;"></span><span>' + label + '</span><span style="flex:1;height:1px;background:#e5e7eb;"></span>';
        messages.appendChild(sep);
    }

    // ── Charger une conversation dans le chat ──────────────────
    async function loadConversation(convId, apiUrl, courseId) {
        try {
            var resp = await fetch(apiUrl + '/history?conversation_id=' + encodeURIComponent(convId) + '&course_id=' + courseId);
            if (!resp.ok) return;
            var data = await resp.json();
            if (!data.messages || data.messages.length === 0) return;

            // Reset
            conversationId      = convId;
            conversationHistory = [];
            var messages = document.getElementById('edo-messages');
            messages.innerHTML  = '';

            localStorage.setItem('edo_conv_' + courseId, convId);

            addSeparator(SVG.history + ' Conversation restaurée');

            data.messages.forEach(function (msg) {
                var role = msg.role === 'assistant' ? 'bot' : 'user';
                appendMessage(msg.message, role);
                conversationHistory.push({ role: msg.role, content: msg.message });
            });

            addSeparator('✦ Continuez ici');

        } catch (e) {
            console.warn('[Edora] Erreur chargement conversation :', e);
        }
    }

    // ── Charger la dernière conversation au démarrage ──────────
    async function loadLastConversation(apiUrl, courseId) {
        var savedId = localStorage.getItem('edo_conv_' + courseId);
        if (!savedId) return;
        await loadConversation(savedId, apiUrl, courseId);
    }

    // ── Modal confirmation suppression ───────────────────────
    function showDeleteConfirm(convId, firstMsg, wrapper, apiUrl, courseId) {
        // Supprimer modal existant
        var existing = document.getElementById('edo-delete-modal');
        if (existing) existing.remove();

        var modal = document.createElement('div');
        modal.id = 'edo-delete-modal';
        modal.style.cssText = `
            position:absolute;top:0;left:0;right:0;bottom:0;
            background:rgba(0,0,0,0.45);backdrop-filter:blur(3px);
            z-index:200;display:flex;align-items:center;justify-content:center;
            border-radius:20px;animation:fadeIn 0.18s ease both;
        `;

        var preview = firstMsg ? (firstMsg.length > 40 ? firstMsg.substring(0,40)+'…' : firstMsg) : 'cette conversation';

        modal.innerHTML = `
            <div style="
                background:#fff;border-radius:16px;padding:24px 22px;width:82%;
                box-shadow:0 8px 32px rgba(0,0,0,0.18);
                display:flex;flex-direction:column;gap:16px;
                animation:panelIn 0.2s cubic-bezier(0.34,1.48,0.64,1) both;
            ">
                <div style="display:flex;align-items:flex-start;gap:12px;">
                    <div style="
                        width:36px;height:36px;border-radius:10px;
                        background:#fef2f2;display:flex;align-items:center;justify-content:center;
                        flex-shrink:0;color:#ef4444;
                    ">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <polyline points="3 6 5 6 21 6"/>
                            <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/>
                            <path d="M10 11v6"/><path d="M14 11v6"/>
                            <path d="M9 6V4h6v2"/>
                        </svg>
                    </div>
                    <div>
                        <div style="font-size:14px;font-weight:700;color:#111827;margin-bottom:4px;">Supprimer la conversation</div>
                        <div style="font-size:12.5px;color:#6b7280;line-height:1.5;">
                            « ${preview} »<br>
                            Cette action est irréversible.
                        </div>
                    </div>
                </div>
                <div style="display:flex;gap:8px;">
                    <button id="edo-del-cancel" style="
                        flex:1;padding:9px;border-radius:10px;border:1.5px solid #e5e7eb;
                        background:#f9fafb;color:#374151;font-size:13px;cursor:pointer;
                        font-weight:500;transition:background 0.15s;
                    ">Annuler</button>
                    <button id="edo-del-confirm" style="
                        flex:1;padding:9px;border-radius:10px;border:none;
                        background:linear-gradient(135deg,#ef4444,#dc2626);
                        color:#fff;font-size:13px;cursor:pointer;
                        font-weight:600;transition:opacity 0.15s;
                        box-shadow:0 2px 8px rgba(239,68,68,0.3);
                    ">Supprimer</button>
                </div>
            </div>
        `;

        var panel = document.getElementById('edo-panel');
        panel.appendChild(modal);

        // Annuler
        modal.querySelector('#edo-del-cancel').addEventListener('click', function () {
            modal.remove();
        });

        // Confirmer suppression
        modal.querySelector('#edo-del-confirm').addEventListener('click', async function () {
            var confirmBtn = modal.querySelector('#edo-del-confirm');
            confirmBtn.textContent = '…';
            confirmBtn.style.opacity = '0.7';

            try {
                var resp = await fetch(apiUrl + '/conversation/' + encodeURIComponent(convId), {
                    method: 'DELETE'
                });

                if (!resp.ok) throw new Error('HTTP ' + resp.status);

                modal.remove();
                wrapper.remove();

                // Si c'était la conversation active, reset
                if (convId === conversationId) {
                    conversationId      = 'conv-' + Date.now();
                    conversationHistory = [];
                    localStorage.removeItem('edo_conv_' + courseId);
                    var messages = document.getElementById('edo-messages');
                    if (messages) {
                        messages.innerHTML = '';
                        var row = document.createElement('div');
                        row.classList.add('edo-bot-row');
                        row.innerHTML = '<div class="edo-bot-avatar">' + AVATAR_IMG_SM + '</div>'
                            + '<div class="edo-bubble edo-bubble--bot">Conversation supprimée. Posez une nouvelle question 👋<div class="edo-timestamp">' + getTime() + '</div></div>';
                        messages.appendChild(row);
                    }
                }

                // Vérifier si la liste est vide
                var list = document.getElementById('edo-history-list');
                if (list && list.children.length === 0) {
                    list.innerHTML = '<div style="text-align:center;color:#9ca3af;font-size:13px;padding:20px 0;">Aucune conversation pour l\'instant.</div>' ; 
                }

            } catch (e) {
                confirmBtn.textContent = 'Supprimer';
                confirmBtn.style.opacity = '1';
                console.error('[Edora] Erreur suppression :', e);
            }
        });

        // Clic en dehors = fermer
        modal.addEventListener('click', function (e) {
            if (e.target === modal) modal.remove();
        });
    }

    // ── Panneau historique latéral ─────────────────────────────
    async function buildHistoryPanel(apiUrl, courseId) {
        // Supprimer si déjà ouvert
        var existing = document.getElementById('edo-history-panel');
        if (existing) { existing.remove(); return; }

        var hp = document.createElement('div');
        hp.id = 'edo-history-panel';
        hp.style.cssText = `
            position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            background: #ffffff;
            z-index: 100;
            display: flex;
            flex-direction: column;
            border-radius: 20px;
            overflow: hidden;
            animation: panelIn 0.22s cubic-bezier(0.34, 1.48, 0.64, 1) both;
        `;

        // Header du panneau
        hp.innerHTML = `
            <div style="
                padding: 14px 16px;
                background: linear-gradient(135deg, #005f73, #0a9396);
                display: flex;
                align-items: center;
                gap: 10px;
                flex-shrink: 0;
            ">
                <span style="color:rgba(255,255,255,0.85);">${SVG.history}</span>
                <span style="font-size:14px;font-weight:700;color:#fff;flex:1;">Mes conversations</span>
                <button id="edo-history-close" style="
                    background:rgba(255,255,255,0.12);border:1px solid rgba(255,255,255,0.22);
                    border-radius:7px;width:28px;height:28px;cursor:pointer;color:rgba(255,255,255,0.85);
                    display:flex;align-items:center;justify-content:center;
                ">${SVG.close}</button>
            </div>
            <div style="
                padding: 10px 12px;
                border-bottom: 1px solid #edf0f3;
                flex-shrink: 0;
            ">
                <button id="edo-new-conv" style="
                    width:100%;padding:9px 12px;border-radius:10px;
                    border:1.5px dashed #0a9396;background:transparent;
                    color:#0a9396;font-size:13px;cursor:pointer;
                    display:flex;align-items:center;justify-content:center;gap:6px;
                    transition:background 0.15s;font-weight:500;
                ">${SVG.plus} Nouvelle conversation</button>
            </div>
            <div id="edo-history-list" style="
                flex:1;overflow-y:auto;padding:8px 10px;display:flex;flex-direction:column;gap:6px;
            ">
                <div style="text-align:center;color:#9ca3af;font-size:13px;padding:20px 0;">
                    Chargement…
                </div>
            </div>
        `;

        var panel = document.getElementById('edo-panel');
        panel.appendChild(hp);

        // Fermer
        hp.querySelector('#edo-history-close').addEventListener('click', function () {
            hp.remove();
        });

        // Nouvelle conversation
        hp.querySelector('#edo-new-conv').addEventListener('click', function () {
            conversationId      = 'conv-' + Date.now();
            conversationHistory = [];
            localStorage.removeItem('edo_conv_' + courseId);
            var messages = document.getElementById('edo-messages');
            messages.innerHTML = '';
            // Message de bienvenue
            var row = document.createElement('div');
            row.classList.add('edo-bot-row');
            row.innerHTML = '<div class="edo-bot-avatar">' + AVATAR_IMG_SM + '</div>'
                + '<div class="edo-bubble edo-bubble--bot">Bonjour ! Je suis Edo, votre tuteur IA 👋<br>Posez-moi une question sur le contenu de ce cours.<div class="edo-timestamp">' + getTime() + '</div></div>';
            messages.appendChild(row);
            hp.remove();
        });

        // Charger la liste
        try {
            var resp = await fetch(apiUrl + '/conversations?user_id=0&course_id=' + courseId);
            var data = await resp.json();
            var list = hp.querySelector('#edo-history-list');

            if (!data.conversations || data.conversations.length === 0) {
                list.innerHTML = '<div style="text-align:center;color:#9ca3af;font-size:13px;padding:20px 0;">Aucune conversation pour l\'instant.</div>';
                return;
            }

            list.innerHTML = '';
            data.conversations.forEach(function (conv) {
                var isActive = conv.conversation_id === conversationId;
                var item = document.createElement('button');
                item.style.cssText = `
                    width:100%;text-align:left;padding:11px 13px;border-radius:11px;cursor:pointer;
                    border:1.5px solid ${isActive ? '#0a9396' : '#e5e7eb'};
                    background:${isActive ? '#e9f5f2' : '#f9fafb'};
                    transition:all 0.15s;display:flex;flex-direction:column;gap:4px;
                `;
                item.innerHTML = `
                    <div style="font-size:13px;font-weight:500;color:${isActive ? '#005f73' : '#111827'};
                        white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:100%;">
                        ${SVG.chat}&nbsp; ${conv.first_message || 'Conversation'}
                    </div>
                    <div style="font-size:11px;color:#9ca3af;display:flex;gap:8px;">
                        <span>${formatDate(conv.created_at)}</span>
                        <span>·</span>
                        <span>${conv.message_count} messages</span>
                        ${isActive ? '<span style="color:#0a9396;font-weight:600;">· Active</span>' : ''}
                    </div>
                `;
                item.addEventListener('mouseenter', function () {
                    if (!isActive) { item.style.background = '#f0f7f6'; item.style.borderColor = '#94d2bd'; }
                });
                item.addEventListener('mouseleave', function () {
                    if (!isActive) { item.style.background = '#f9fafb'; item.style.borderColor = '#e5e7eb'; }
                });
                item.addEventListener('click', async function () {
                    hp.remove();
                    await loadConversation(conv.conversation_id, apiUrl, courseId);
                });

                // ── Bouton poubelle ──────────────────────────
                var wrapper = document.createElement('div');
                wrapper.style.cssText = 'display:flex;align-items:stretch;gap:6px;';
                item.style.width = 'auto';
                item.style.flex = '1';

                var delBtn = document.createElement('button');
                delBtn.title = 'Supprimer';
                delBtn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4h6v2"/></svg>';
                delBtn.style.cssText = 'flex-shrink:0;background:none;border:1px solid #e5e7eb;border-radius:10px;width:36px;cursor:pointer;color:#9ca3af;display:flex;align-items:center;justify-content:center;transition:all 0.15s;';
                delBtn.addEventListener('mouseenter', function () { delBtn.style.background='#fef2f2'; delBtn.style.borderColor='#ef4444'; delBtn.style.color='#ef4444'; });
                delBtn.addEventListener('mouseleave', function () { delBtn.style.background='none'; delBtn.style.borderColor='#e5e7eb'; delBtn.style.color='#9ca3af'; });
                delBtn.addEventListener('click', function (e) {
                    e.stopPropagation();
                    showDeleteConfirm(conv.conversation_id, conv.first_message, wrapper, apiUrl, courseId);
                });

                wrapper.appendChild(item);
                wrapper.appendChild(delBtn);
                list.appendChild(wrapper);
            });

        } catch (e) {
            var list2 = hp.querySelector('#edo-history-list');
            list2.innerHTML = '<div style="text-align:center;color:#ef4444;font-size:13px;padding:20px 0;">Erreur de chargement.</div>';
        }
    }

    // ── Send question ──────────────────────────────────────────
    async function sendQuestion(question, apiUrl, courseId) {
        var sendBtn = document.getElementById('edo-send');
        var input   = document.getElementById('edo-input');

        lastQuestion = question;
        lastApiUrl   = apiUrl;
        lastCourseId = courseId;

        sendBtn.disabled = true;
        input.disabled   = true;

        clearSuggestions();
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

            if (data.conversation_id) {
                conversationId = data.conversation_id;
                localStorage.setItem('edo_conv_' + courseId, conversationId);
            }

            appendMessage(data.answer, 'bot');
            conversationHistory.push({ role: 'assistant', content: data.answer });

            if (data.follow_up_questions && data.follow_up_questions.length > 0) {
                showSuggestions(data.follow_up_questions, apiUrl, courseId);
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

    // ── Build UI ───────────────────────────────────────────────
    function buildFloatingUI(apiUrl, courseId) {

        var fab = document.createElement('button');
        fab.id = 'edo-fab';
        fab.className = 'edo-fab';
        fab.setAttribute('aria-label', 'Ouvrir le tuteur IA');
        fab.innerHTML = AVATAR_IMG;

        var panel = document.createElement('div');
        panel.id = 'edo-panel';
        panel.className = 'edo-panel';

        panel.innerHTML = `
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
                    <button id="edo-history-btn" class="edo-header__btn" title="Historique des conversations">${SVG.history}</button>
                    <button id="edo-minimize"    class="edo-header__btn" title="Réduire">${SVG.minimize}</button>
                    <button id="edo-close"       class="edo-header__btn" aria-label="Fermer">${SVG.close}</button>
                </div>
            </div>

            <div id="edo-messages" class="edo-messages" role="log" aria-live="polite">
                <div class="edo-bot-row">
                    <div class="edo-bot-avatar">${AVATAR_IMG_SM}</div>
                    <div class="edo-bubble edo-bubble--bot">
                        Bonjour ! Je suis Edo, votre tuteur IA 👋<br>
                        Posez-moi une question sur le contenu de ce cours.
                        <div class="edo-timestamp">${getTime()}</div>
                    </div>
                </div>
            </div>

            <div class="edo-shortcuts">
                <button class="edo-shortcut" data-question="Explique-moi ce chapitre">${SVG.book} Expliquer</button>
                <button class="edo-shortcut" data-question="Génère un quiz sur ce chapitre">${SVG.quiz} Quiz</button>
                <button class="edo-shortcut" data-question="Donne-moi un exemple concret">${SVG.bulb} Exemple</button>
                <button class="edo-shortcut" data-question="Résume cette leçon">${SVG.list} Résumer</button>
            </div>

            <div class="edo-input-row">
                <button class="edo-input-icon" id="edo-attach" title="Joindre fichier">${SVG.attach}</button>
                <input type="file" id="edo-file-input" style="display:none;" accept=".pdf,.doc,.docx,.txt,.pptx">
                <input type="text" id="edo-input" class="edo-input"
                    placeholder="Posez votre question sur le contenu du cours..."
                    aria-label="Question pour Edo" maxlength="500"/>
                <button class="edo-input-icon" id="edo-vocal" title="Message vocal">${SVG.mic}</button>
                <button id="edo-send" class="edo-send-btn" aria-label="Envoyer">${SVG.send}</button>
            </div>

            <div class="edo-footer">
                <span class="edo-footer-icon">${SVG.shield}</span>
                <span class="edo-footer-text">Réponses générées à partir du contenu de vos cours. Vérifiez toujours les informations importantes.</span>
            </div>
        `;

        document.body.appendChild(fab);
        document.body.appendChild(panel);

        // Charger la dernière conversation
        loadLastConversation(apiUrl, courseId);

        // FAB
        fab.addEventListener('click', function () {
            var isOpen = panel.classList.toggle('edo-panel--open');
            fab.classList.toggle('edo-fab--open', isOpen);
            if (isOpen) setTimeout(function() { panel.querySelector('#edo-input').focus(); }, 300);
        });

        // Bouton historique 🕐
        panel.querySelector('#edo-history-btn').addEventListener('click', function () {
            buildHistoryPanel(apiUrl, courseId);
        });

        // Fermer
        panel.querySelector('#edo-close').addEventListener('click', function () {
            panel.classList.remove('edo-panel--open');
            fab.classList.remove('edo-fab--open');
        });

        // Minimiser
        panel.querySelector('#edo-minimize').addEventListener('click', function () {
            var els = ['#edo-messages', '.edo-shortcuts', '.edo-footer', '.edo-input-row', '.edo-dynamic-suggestions'];
            var messages = panel.querySelector('#edo-messages');
            var min = messages.style.display === 'none';
            els.forEach(function(sel) {
                var el = panel.querySelector(sel);
                if (!el) return;
                var isGrid = sel === '.edo-shortcuts';
                el.style.display = min ? (isGrid ? 'grid' : 'flex') : 'none';
            });
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
            var lr = appendMessage('', 'bot', true);
            try {
                var fd = new FormData();
                fd.append('file', file);
                fd.append('course_id', courseId);
                var r = await fetch(apiUrl + '/upload-file', { method: 'POST', body: fd });
                lr.remove();
                if (!r.ok) throw new Error('HTTP ' + r.status);
                var d = await r.json();
                appendMessage('✅ Fichier indexé ! ' + d.chunks_created + ' extraits créés.', 'bot');
            } catch (e) {
                lr.remove();
                appendMessage('⚠️ Erreur lors de l\'upload du fichier.', 'bot');
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
            vocalBtn.addEventListener('click', function () { if (isListening) { recognition.stop(); return; } recognition.start(); });
            recognition.onstart  = function () { isListening = true;  vocalBtn.style.color = '#ec4899'; };
            recognition.onresult = function (e) { textInput.value = e.results[0][0].transcript; textInput.focus(); };
            recognition.onend    = function () { isListening = false; vocalBtn.style.color = ''; };
            recognition.onerror  = function (e) { isListening = false; vocalBtn.style.color = ''; if (e.error === 'not-allowed') appendMessage('⚠️ Accès au microphone refusé.', 'bot'); };
        } else {
            vocalBtn.style.opacity = '0.4'; vocalBtn.style.cursor = 'not-allowed';
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

    // ── Init ───────────────────────────────────────────────────
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