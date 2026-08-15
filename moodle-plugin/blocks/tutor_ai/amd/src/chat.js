/**
 * Edora AI Tutor — Module chat
 * @author Islem Troudi — Phase 7 (historique + panneau latéral)
 * @author Yasmine — Floating button + MariaDB schema + Phase 8 (level detection, cache, markdown)
 * @fix Islem — studentId depuis dataset, renderMarkdown intégré
 */

(function () {

    let conversationHistory = [];
    let conversationId      = 'conv-' + Date.now();
    let lastQuestion        = '';
    let lastApiUrl          = '';
    let lastCourseId        = 0;

    var rootEl     = document.getElementById('edo-chat-root');
    var avatarUrl  = rootEl ? rootEl.dataset.avatarUrl : '';

    // ── FIX : récupérer le vrai studentId depuis le dataset PHP ──
    var studentId  = rootEl ? (rootEl.dataset.studentId || '0') : '0';

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
        plus:    '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>',
        file:    '<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>',
        chevron: '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"/></svg>'
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

    // ── FIX : renderMarkdown — rendu visuel du Markdown ───────
    function renderMarkdown(text) {
        if (!text) return '';
        var html = text
            // Titres ## et ###
            .replace(/^### (.+)$/gm, '<h4 style="margin:10px 0 4px;font-size:13px;color:#005f73;font-weight:700;">$1</h4>')
            .replace(/^## (.+)$/gm,  '<h3 style="margin:12px 0 5px;font-size:14px;color:#005f73;font-weight:700;">$1</h3>')
            .replace(/^# (.+)$/gm,   '<h2 style="margin:14px 0 6px;font-size:15px;color:#005f73;font-weight:700;">$1</h2>')
            // Gras **texte**
            .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
            // Italique *texte*
            .replace(/\*(.+?)\*/g, '<em>$1</em>')
            // Listes - item
            .replace(/^- (.+)$/gm, '<li style="margin:3px 0;padding-left:4px;">$1</li>')
            // Listes numérotées
            .replace(/^\d+\. (.+)$/gm, '<li style="margin:3px 0;padding-left:4px;">$1</li>')
            // Entourer les <li> consécutifs
            .replace(/(<li[^>]*>.*<\/li>\n?)+/g, '<ul style="margin:6px 0 6px 16px;padding:0;list-style:disc;">$&</ul>')
            // Sauts de ligne
            .replace(/\n\n/g, '</p><p style="margin:6px 0;">')
            .replace(/\n/g, '<br>');
        return '<p style="margin:0;">' + html + '</p>';
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
            // FIX : utiliser renderMarkdown au lieu de .replace(\n, <br>)
            bubble.innerHTML = renderMarkdown(text) + '<div class="edo-timestamp">' + getTime() + '</div>';
            row.appendChild(bubble);
            messages.appendChild(row);
            messages.scrollTop = messages.scrollHeight;

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

    // ── Séparateur visuel ──────────────────────────────────────
    function addSeparator(label) {
        var messages = document.getElementById('edo-messages');
        if (!messages) return;
        var sep = document.createElement('div');
        sep.style.cssText = 'text-align:center;font-size:11px;color:#9ca3af;padding:8px 0;display:flex;align-items:center;gap:8px;';
        sep.innerHTML = '<span style="flex:1;height:1px;background:#e5e7eb;"></span><span>' + label + '</span><span style="flex:1;height:1px;background:#e5e7eb;"></span>';
        messages.appendChild(sep);
    }

    // ── Charger une conversation ───────────────────────────────
    async function loadConversation(convId, apiUrl, courseId) {
        try {
            var resp = await fetch(apiUrl + '/history?conversation_id=' + encodeURIComponent(convId) + '&course_id=' + courseId);
            if (!resp.ok) return;
            var data = await resp.json();
            if (!data.messages || data.messages.length === 0) return;
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

    async function loadLastConversation(apiUrl, courseId) {
        var savedId = localStorage.getItem('edo_conv_' + courseId);
        if (!savedId) return;
        await loadConversation(savedId, apiUrl, courseId);
    }

    // ── Modal suppression ──────────────────────────────────────
    function showDeleteConfirm(convId, firstMsg, wrapper, apiUrl, courseId) {
        var existing = document.getElementById('edo-delete-modal');
        if (existing) existing.remove();
        var modal = document.createElement('div');
        modal.id = 'edo-delete-modal';
        modal.style.cssText = 'position:absolute;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.45);backdrop-filter:blur(3px);z-index:200;display:flex;align-items:center;justify-content:center;border-radius:20px;animation:fadeIn 0.18s ease both;';
        var preview = firstMsg ? (firstMsg.length > 40 ? firstMsg.substring(0,40)+'…' : firstMsg) : 'cette conversation';
        modal.innerHTML = '<div style="background:#fff;border-radius:16px;padding:24px 22px;width:82%;box-shadow:0 8px 32px rgba(0,0,0,0.18);display:flex;flex-direction:column;gap:16px;animation:panelIn 0.2s cubic-bezier(0.34,1.48,0.64,1) both;"><div style="display:flex;align-items:flex-start;gap:12px;"><div style="width:36px;height:36px;border-radius:10px;background:#fef2f2;display:flex;align-items:center;justify-content:center;flex-shrink:0;color:#ef4444;"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4h6v2"/></svg></div><div><div style="font-size:14px;font-weight:700;color:#111827;margin-bottom:4px;">Supprimer la conversation</div><div style="font-size:12.5px;color:#6b7280;line-height:1.5;">« ' + preview + ' »<br>Cette action est irréversible.</div></div></div><div style="display:flex;gap:8px;"><button id="edo-del-cancel" style="flex:1;padding:9px;border-radius:10px;border:1.5px solid #e5e7eb;background:#f9fafb;color:#374151;font-size:13px;cursor:pointer;font-weight:500;">Annuler</button><button id="edo-del-confirm" style="flex:1;padding:9px;border-radius:10px;border:none;background:linear-gradient(135deg,#ef4444,#dc2626);color:#fff;font-size:13px;cursor:pointer;font-weight:600;box-shadow:0 2px 8px rgba(239,68,68,0.3);">Supprimer</button></div></div>';
        var panel = document.getElementById('edo-panel');
        panel.appendChild(modal);
        modal.querySelector('#edo-del-cancel').addEventListener('click', function () { modal.remove(); });
        modal.querySelector('#edo-del-confirm').addEventListener('click', async function () {
            var confirmBtn = modal.querySelector('#edo-del-confirm');
            confirmBtn.textContent = '…'; confirmBtn.style.opacity = '0.7';
            try {
                var resp = await fetch(apiUrl + '/conversation/' + encodeURIComponent(convId), { method: 'DELETE' });
                if (!resp.ok) throw new Error('HTTP ' + resp.status);
                modal.remove(); wrapper.remove();
                if (convId === conversationId) {
                    conversationId = 'conv-' + Date.now(); conversationHistory = [];
                    localStorage.removeItem('edo_conv_' + courseId);
                    var messages = document.getElementById('edo-messages');
                    if (messages) {
                        messages.innerHTML = '';
                        var row = document.createElement('div'); row.classList.add('edo-bot-row');
                        row.innerHTML = '<div class="edo-bot-avatar">' + AVATAR_IMG_SM + '</div><div class="edo-bubble edo-bubble--bot">Conversation supprimée. Posez une nouvelle question 👋<div class="edo-timestamp">' + getTime() + '</div></div>';
                        messages.appendChild(row);
                    }
                }
                var list = document.getElementById('edo-history-list');
                if (list && list.children.length === 0) list.innerHTML = '<div style="text-align:center;color:#9ca3af;font-size:13px;padding:20px 0;">Aucune conversation pour l\'instant.</div>';
            } catch (e) { confirmBtn.textContent = 'Supprimer'; confirmBtn.style.opacity = '1'; console.error('[Edora] Erreur suppression :', e); }
        });
        modal.addEventListener('click', function (e) { if (e.target === modal) modal.remove(); });
    }

    // ── Panneau historique ─────────────────────────────────────
    async function buildHistoryPanel(apiUrl, courseId) {
        var existing = document.getElementById('edo-history-panel');
        if (existing) { existing.remove(); return; }
        var hp = document.createElement('div');
        hp.id = 'edo-history-panel';
        hp.style.cssText = 'position:absolute;top:0;left:0;right:0;bottom:0;background:#ffffff;z-index:100;display:flex;flex-direction:column;border-radius:20px;overflow:hidden;animation:panelIn 0.22s cubic-bezier(0.34,1.48,0.64,1) both;';
        hp.innerHTML = '<div style="padding:14px 16px;background:linear-gradient(135deg,#005f73,#0a9396);display:flex;align-items:center;gap:10px;flex-shrink:0;"><span style="color:rgba(255,255,255,0.85);">' + SVG.history + '</span><span style="font-size:14px;font-weight:700;color:#fff;flex:1;">Mes conversations</span><button id="edo-history-close" style="background:rgba(255,255,255,0.12);border:1px solid rgba(255,255,255,0.22);border-radius:7px;width:28px;height:28px;cursor:pointer;color:rgba(255,255,255,0.85);display:flex;align-items:center;justify-content:center;">' + SVG.close + '</button></div><div style="padding:10px 12px;border-bottom:1px solid #edf0f3;flex-shrink:0;"><button id="edo-new-conv" style="width:100%;padding:9px 12px;border-radius:10px;border:1.5px dashed #0a9396;background:transparent;color:#0a9396;font-size:13px;cursor:pointer;display:flex;align-items:center;justify-content:center;gap:6px;font-weight:500;">' + SVG.plus + ' Nouvelle conversation</button></div><div id="edo-history-list" style="flex:1;overflow-y:auto;padding:8px 10px;display:flex;flex-direction:column;gap:6px;"><div style="text-align:center;color:#9ca3af;font-size:13px;padding:20px 0;">Chargement…</div></div>';
        var panel = document.getElementById('edo-panel');
        panel.appendChild(hp);
        hp.querySelector('#edo-history-close').addEventListener('click', function () { hp.remove(); });
        hp.querySelector('#edo-new-conv').addEventListener('click', function () {
            conversationId = 'conv-' + Date.now(); conversationHistory = [];
            localStorage.removeItem('edo_conv_' + courseId);
            var messages = document.getElementById('edo-messages'); messages.innerHTML = '';
            var row = document.createElement('div'); row.classList.add('edo-bot-row');
            row.innerHTML = '<div class="edo-bot-avatar">' + AVATAR_IMG_SM + '</div><div class="edo-bubble edo-bubble--bot">Bonjour ! Je suis Edo, votre tuteur IA 👋<br>Posez-moi une question sur le contenu de ce cours.<div class="edo-timestamp">' + getTime() + '</div></div>';
            messages.appendChild(row); hp.remove();
        });
        try {
            // FIX : utiliser le vrai studentId
            var resp = await fetch(apiUrl + '/conversations?user_id=' + studentId + '&course_id=' + courseId);
            var data = await resp.json();
            var list = hp.querySelector('#edo-history-list');
            if (!data.conversations || data.conversations.length === 0) { list.innerHTML = '<div style="text-align:center;color:#9ca3af;font-size:13px;padding:20px 0;">Aucune conversation pour l\'instant.</div>'; return; }
            list.innerHTML = '';
            data.conversations.forEach(function (conv) {
                var isActive = conv.conversation_id === conversationId;
                var item = document.createElement('button');
                item.style.cssText = 'width:100%;text-align:left;padding:11px 13px;border-radius:11px;cursor:pointer;border:1.5px solid ' + (isActive ? '#0a9396' : '#e5e7eb') + ';background:' + (isActive ? '#e9f5f2' : '#f9fafb') + ';transition:all 0.15s;display:flex;flex-direction:column;gap:4px;';
                item.innerHTML = '<div style="font-size:13px;font-weight:500;color:' + (isActive ? '#005f73' : '#111827') + ';white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:100%;">' + SVG.chat + '&nbsp; ' + (conv.first_message || 'Conversation') + '</div><div style="font-size:11px;color:#9ca3af;display:flex;gap:8px;"><span>' + formatDate(conv.created_at) + '</span><span>·</span><span>' + conv.message_count + ' messages</span>' + (isActive ? '<span style="color:#0a9396;font-weight:600;">· Active</span>' : '') + '</div>';
                item.addEventListener('mouseenter', function () { if (!isActive) { item.style.background='#f0f7f6'; item.style.borderColor='#94d2bd'; } });
                item.addEventListener('mouseleave', function () { if (!isActive) { item.style.background='#f9fafb'; item.style.borderColor='#e5e7eb'; } });
                item.addEventListener('click', async function () { hp.remove(); await loadConversation(conv.conversation_id, apiUrl, courseId); });
                var wrapper = document.createElement('div'); wrapper.style.cssText = 'display:flex;align-items:stretch;gap:6px;';
                item.style.width = 'auto'; item.style.flex = '1';
                var delBtn = document.createElement('button');
                delBtn.title = 'Supprimer';
                delBtn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4h6v2"/></svg>';
                delBtn.style.cssText = 'flex-shrink:0;background:none;border:1px solid #e5e7eb;border-radius:10px;width:36px;cursor:pointer;color:#9ca3af;display:flex;align-items:center;justify-content:center;transition:all 0.15s;';
                delBtn.addEventListener('mouseenter', function () { delBtn.style.background='#fef2f2'; delBtn.style.borderColor='#ef4444'; delBtn.style.color='#ef4444'; });
                delBtn.addEventListener('mouseleave', function () { delBtn.style.background='none'; delBtn.style.borderColor='#e5e7eb'; delBtn.style.color='#9ca3af'; });
                delBtn.addEventListener('click', function (e) { e.stopPropagation(); showDeleteConfirm(conv.conversation_id, conv.first_message, wrapper, apiUrl, courseId); });
                wrapper.appendChild(item); wrapper.appendChild(delBtn); list.appendChild(wrapper);
            });
        } catch (e) { var list2 = hp.querySelector('#edo-history-list'); list2.innerHTML = '<div style="text-align:center;color:#ef4444;font-size:13px;padding:20px 0;">Erreur de chargement.</div>'; }
    }

    // ── Extraits de cours (sources RAG) ───────────────────────
    function renderSources(sources, messages) {
        if (!sources || sources.length === 0) return;
        var wrapper = document.createElement('div');
        wrapper.style.cssText = 'margin-left:44px;margin-top:4px;margin-bottom:6px;max-width:88%;';
        var isOpen = false;
        var toggle = document.createElement('button');
        toggle.style.cssText = 'display:flex;align-items:center;gap:6px;background:none;border:none;cursor:pointer;font-size:11.5px;color:#6b7280;padding:2px 0;margin-bottom:6px;transition:color 0.15s;';
        toggle.innerHTML = SVG.book + '<span class="edo-src-label">' + sources.length + ' extrait(s) du cours utilisé(s)</span><span class="edo-src-chevron" style="display:inline-flex;transition:transform 0.2s;">' + SVG.chevron + '</span>';
        toggle.addEventListener('mouseenter', function() { toggle.style.color = '#0a9396'; });
        toggle.addEventListener('mouseleave', function() { toggle.style.color = '#6b7280'; });
        var srcContainer = document.createElement('div');
        srcContainer.style.cssText = 'display:none;flex-direction:column;gap:8px;';
        toggle.addEventListener('click', function() {
            isOpen = !isOpen;
            srcContainer.style.display = isOpen ? 'flex' : 'none';
            var chevron = toggle.querySelector('.edo-src-chevron');
            if (chevron) chevron.style.transform = isOpen ? 'rotate(180deg)' : 'rotate(0deg)';
            var label = toggle.querySelector('.edo-src-label');
            if (label) label.textContent = isOpen ? 'Masquer les extraits' : sources.length + ' extrait(s) du cours utilisé(s)';
            messages.scrollTop = messages.scrollHeight;
        });
        sources.forEach(function(src, idx) {
            var card = document.createElement('div');
            card.style.cssText = 'background:#f0f9f9;border:1px solid #94d2bd;border-left:3px solid #0a9396;border-radius:8px;padding:10px 12px;font-size:12px;color:#374151;line-height:1.6;';
            var srcName = src.resource_name ? decodeURIComponent(src.resource_name.replace(/\+/g, ' ').replace(/%20/g, ' ')) : 'Cours';
            srcName = srcName.replace(/\.(pdf|docx?|pptx?|txt)$/i, '');
            var srcHeader = document.createElement('div');
            srcHeader.style.cssText = 'display:flex;align-items:center;gap:5px;margin-bottom:7px;font-size:11px;font-weight:600;color:#0a9396;';
            srcHeader.innerHTML = SVG.file + '<span>Extrait ' + (idx + 1) + ' — ' + srcName + '</span>';
            var srcText = document.createElement('div');
            srcText.style.cssText = 'white-space:pre-wrap;font-family:inherit;color:#4b5563;font-size:12px;line-height:1.65;border-top:1px solid #b2d8d8;padding-top:7px;margin-top:2px;';
            srcText.textContent = src.chunk_excerpt ? src.chunk_excerpt.trim() : '';
            card.appendChild(srcHeader);
            card.appendChild(srcText);
            srcContainer.appendChild(card);
        });
        wrapper.appendChild(toggle);
        wrapper.appendChild(srcContainer);
        messages.appendChild(wrapper);
        messages.scrollTop = messages.scrollHeight;
    }

    // ── Quiz interactif ────────────────────────────────────────
    function renderInteractiveQuiz(text, messages) {
        if (!text.includes('Bonne réponse') && !text.includes('✅')) return false;
        var parts = text.split(/(?=\*\*Question\s+\d+\s*:)/i);
        var blocks = parts.filter(function(b) { return b.trim().match(/^\*\*Question/i); });
        if (blocks.length === 0) return false;

        var row = document.createElement('div');
        row.classList.add('edo-bot-row');
        var av = document.createElement('div'); av.className = 'edo-bot-avatar'; av.innerHTML = AVATAR_IMG_SM;
        row.appendChild(av);
        var container = document.createElement('div');
        container.style.cssText = 'display:flex;flex-direction:column;gap:14px;max-width:88%;';

        var introText = parts[0] ? parts[0].trim() : '';
        if (introText && !introText.match(/^\*\*Question/i)) {
            var intro = document.createElement('div');
            intro.style.cssText = 'font-size:13px;color:#374151;padding:2px 0 4px;';
            intro.textContent = introText.replace(/\*\*/g, '');
            container.appendChild(intro);
        }

        var score = { correct: 0, total: blocks.length, answered: 0 };

        blocks.forEach(function(block, idx) {
            var lines = block.split('\n').map(function(l) { return l.trim(); }).filter(Boolean);
            var qLine = lines[0] || '';
            var qText = qLine.replace(/^\*\*Question\s*\d+\s*:\*?\*?\s*/i, '').replace(/\*\*/g, '').trim();
            var options = []; var seen = {}; var correctLetter = ''; var explanation = '';

            lines.forEach(function(line) {
                var multiMatch = line.match(/([A-D])\)\s+(.+?)(?=\s{2,}[A-D]\)|$)/g);
                if (multiMatch) {
                    multiMatch.forEach(function(m) {
                        var p2 = m.match(/^([A-D])\)\s+(.+)/);
                        if (p2 && !seen[p2[1]]) { seen[p2[1]] = true; options.push({ letter: p2[1], text: p2[2].trim() }); }
                    });
                } else {
                    var single = line.match(/^([A-D])\)\s+(.+)/);
                    if (single && !seen[single[1]]) { seen[single[1]] = true; options.push({ letter: single[1], text: single[2].trim() }); }
                }
                var ans = line.match(/✅\s*Bonne\s*r[ée]ponse\s*:\s*([A-D])\s*[—\-–]\s*(.+)/i);
                if (ans) { correctLetter = ans[1]; explanation = ans[2].trim(); }
            });

            var qDiv = document.createElement('div');
            qDiv.style.cssText = 'background:#f8fafc;border:1.5px solid #e2e8f0;border-radius:12px;padding:14px 16px;';
            var qTitle = document.createElement('div');
            qTitle.style.cssText = 'font-size:13px;font-weight:600;color:#1e293b;margin-bottom:10px;line-height:1.4;';
            qTitle.textContent = 'Question ' + (idx + 1) + ' : ' + qText;
            qDiv.appendChild(qTitle);

            var optContainer = document.createElement('div');
            optContainer.style.cssText = 'display:flex;flex-direction:column;gap:7px;';
            var answered = false;

            options.forEach(function(opt) {
                var btn = document.createElement('button');
                btn.style.cssText = 'text-align:left;padding:9px 13px;border-radius:8px;border:1.5px solid #e2e8f0;background:#ffffff;font-size:12.5px;color:#374151;cursor:pointer;transition:all 0.15s;width:100%;';
                btn.innerHTML = '<strong>' + opt.letter + ')</strong> ' + opt.text;
                btn.addEventListener('mouseenter', function() { if (!answered) { btn.style.background='#f0f9ff'; btn.style.borderColor='#7dd3fc'; } });
                btn.addEventListener('mouseleave', function() { if (!answered) { btn.style.background='#ffffff'; btn.style.borderColor='#e2e8f0'; } });
                btn.addEventListener('click', function() {
                    if (answered) return;
                    answered = true; score.answered++;
                    var isCorrect = (opt.letter === correctLetter);
                    if (isCorrect) score.correct++;
                    optContainer.querySelectorAll('button').forEach(function(b) {
                        b.style.cursor = 'default';
                        var lm = b.innerHTML.match(/<strong>([A-D])\)<\/strong>/);
                        var bL = lm ? lm[1] : '';
                        if (bL === correctLetter) { b.style.background='#f0fdf4'; b.style.borderColor='#22c55e'; b.style.color='#15803d'; }
                        else if (b === btn && !isCorrect) { b.style.background='#fef2f2'; b.style.borderColor='#ef4444'; b.style.color='#dc2626'; }
                        else { b.style.opacity='0.4'; }
                    });
                    var expDiv = document.createElement('div');
                    expDiv.style.cssText = 'margin-top:10px;padding:9px 12px;border-radius:8px;font-size:12.5px;line-height:1.5;' + (isCorrect ? 'background:#f0fdf4;border:1px solid #86efac;color:#15803d;' : 'background:#fef2f2;border:1px solid #fca5a5;color:#dc2626;');
                    expDiv.innerHTML = isCorrect ? '✅ <strong>Bonne réponse !</strong> ' + explanation : '❌ <strong>Mauvaise réponse.</strong> La bonne réponse est <strong>' + correctLetter + '</strong>. ' + explanation;
                    qDiv.appendChild(expDiv);
                    messages.scrollTop = messages.scrollHeight;
                    if (score.answered === score.total) {
                        var pct = Math.round((score.correct / score.total) * 100);
                        var emoji = pct >= 80 ? '🎉' : pct >= 50 ? '👍' : '💪';
                        var msg = pct >= 80 ? 'Excellent travail !' : pct >= 50 ? 'Bon effort, continue !' : 'Continue à réviser, tu vas y arriver !';
                        var scoreDiv = document.createElement('div');
                        scoreDiv.style.cssText = 'margin-top:6px;padding:14px;border-radius:10px;background:linear-gradient(135deg,#005f73,#0a9396);color:#fff;text-align:center;font-size:14px;';
                        scoreDiv.innerHTML = emoji + ' <strong>Score final : ' + score.correct + '/' + score.total + ' (' + pct + '%)</strong><br><span style="font-size:12px;opacity:0.9;">' + msg + '</span>';
                        container.appendChild(scoreDiv);
                        messages.scrollTop = messages.scrollHeight;
                    }
                });
                optContainer.appendChild(btn);
            });

            qDiv.appendChild(optContainer);
            container.appendChild(qDiv);
        });

        var ts = document.createElement('div');
        ts.style.cssText = 'font-size:11px;color:#9ca3af;text-align:right;margin-top:2px;';
        ts.textContent = getTime();
        container.appendChild(ts);
        row.appendChild(container);
        messages.appendChild(row);
        messages.scrollTop = messages.scrollHeight;
        return true;
    }

    // ── État du niveau étudiant ────────────────────────────────
    var studentLevel     = null;
    var levelQuizDone    = false;
    var levelQuizPending = false;

    var SMALL_TALK = [
        "bonjour","bonsoir","salut","hello","hi","hey","merci",
        "au revoir","bye","ciao","ok","oui","non","d'accord",
        "super","cool","bien","aide","help","qui es-tu","qui es tu",
        "comment vas","ça va","quoi de neuf","présente","edora"
    ];

    function isSmallTalk(question) {
        var q = question.toLowerCase().trim();
        if (q.split(' ').length < 4) {
            return SMALL_TALK.some(function(kw) { return q.includes(kw); });
        }
        return false;
    }

    // FIX : utiliser studentId variable (pas 0 hardcodé)
    async function loadStudentLevel(apiUrl, courseId) {
        try {
            var resp = await fetch(
                apiUrl + '/student-level?student_id=' + studentId + '&course_id=' + courseId
            );
            if (!resp.ok) return;
            var data = await resp.json();
            if (data.level) {
                studentLevel  = data.level;
                levelQuizDone = true;
            } else if (data.quiz_done) {
                levelQuizDone = true;
            }
        } catch(e) {
            console.warn('[Edora] Erreur chargement niveau :', e);
        }
    }

    function showLevelBadge(level) {
        var existing = document.getElementById('edo-level-badge');
        if (existing) existing.remove();
        var labels = {
            debutant:      { text: '🌱 Débutant',       color: '#059669', bg: '#d1fae5' },
            intermediaire: { text: '📘 Intermédiaire',  color: '#0a9396', bg: '#cffafe' },
            avance:        { text: '🚀 Avancé',          color: '#7c3aed', bg: '#ede9fe' }
        };
        var info = labels[level] || { text: level, color: '#6b7280', bg: '#f3f4f6' };
        var badge = document.createElement('div');
        badge.id = 'edo-level-badge';
        badge.style.cssText = 'display:flex;align-items:center;gap:6px;margin:6px 44px 2px;padding:5px 10px;border-radius:20px;font-size:11.5px;font-weight:600;color:' + info.color + ';background:' + info.bg + ';width:fit-content';
        badge.textContent = info.text;
        var messages = document.getElementById('edo-messages');
        if (messages) messages.appendChild(badge);
    }

    function renderLevelQuiz(quizText, apiUrl, courseId, convId, onComplete) {
        var messages = document.getElementById('edo-messages');
        if (!messages) return;
        var introRow = document.createElement('div');
        introRow.classList.add('edo-bot-row');
        var introAv = document.createElement('div'); introAv.className = 'edo-bot-avatar'; introAv.innerHTML = AVATAR_IMG_SM;
        introRow.appendChild(introAv);
        var introBubble = document.createElement('div');
        introBubble.classList.add('edo-bubble', 'edo-bubble--bot');
        introBubble.style.cssText = 'background:linear-gradient(135deg,#e0f7fa,#f0fdf4);border:1.5px solid #0a9396;';
        introBubble.innerHTML = '🎯 <strong>Avant de commencer, faisons connaissance !</strong><br>Pour que je puisse adapter mes explications à ton niveau, réponds à ce petit quiz de <strong>10 questions</strong> sur le cours.<br><span style="font-size:11px;color:#6b7280;">Cela ne prend que 2 minutes — promis ! 😊</span><div class="edo-timestamp">' + getTime() + '</div>';
        introRow.appendChild(introBubble);
        messages.appendChild(introRow);
        messages.scrollTop = messages.scrollHeight;

        var parts = quizText.split(/(?=\*\*Question\s+\d+\s*:)/i);
        var blocks = parts.filter(function(b) { return b.trim().match(/^\*\*Question/i); });
        if (blocks.length === 0) { onComplete(5, 10); return; }

        var quizWrapper = document.createElement('div');
        quizWrapper.style.cssText = 'margin:8px 0 8px 44px;max-width:88%;display:flex;flex-direction:column;gap:10px;';
        var score = { correct: 0, total: blocks.length, answered: 0 };

        blocks.forEach(function(block, idx) {
            var lines = block.split('\n').map(function(l){ return l.trim(); }).filter(Boolean);
            var qLine = lines[0] || '';
            var qText = qLine.replace(/^\*\*Question\s*\d+\s*:\*?\*?\s*/i,'').replace(/\*\*/g,'').trim();
            var options = []; var seen = {}; var correctLetter = ''; var explanation = '';
            lines.forEach(function(line) {
                var multi = line.match(/([A-D])\)\s+(.+?)(?=\s{2,}[A-D]\)|$)/g);
                if (multi) { multi.forEach(function(m) { var p = m.match(/^([A-D])\)\s+(.+)/); if (p && !seen[p[1]]) { seen[p[1]]=true; options.push({letter:p[1],text:p[2].trim()}); } }); }
                else { var s = line.match(/^([A-D])\)\s+(.+)/); if (s && !seen[s[1]]) { seen[s[1]]=true; options.push({letter:s[1],text:s[2].trim()}); } }
                var ans = line.match(/✅\s*Bonne\s*r[ée]ponse\s*:\s*([A-D])\s*[—\-–]\s*(.+)/i);
                if (ans) { correctLetter=ans[1]; explanation=ans[2].trim(); }
            });
            var qCard = document.createElement('div');
            qCard.style.cssText = 'background:#f8fafc;border:1.5px solid #e2e8f0;border-radius:10px;padding:12px 14px;';
            var qHeader = document.createElement('div');
            qHeader.style.cssText = 'font-size:12.5px;font-weight:600;color:#1e293b;margin-bottom:8px;';
            qHeader.innerHTML = '<span style="color:#0a9396;">Q' + (idx+1) + '.</span> ' + qText;
            qCard.appendChild(qHeader);
            var optDiv = document.createElement('div');
            optDiv.style.cssText = 'display:flex;flex-direction:column;gap:5px;';
            var answered = false;
            options.forEach(function(opt) {
                var btn = document.createElement('button');
                btn.style.cssText = 'text-align:left;padding:7px 11px;border-radius:7px;border:1.5px solid #e2e8f0;background:#fff;font-size:12px;color:#374151;cursor:pointer;transition:all 0.15s;width:100%;';
                btn.innerHTML = '<strong>' + opt.letter + ')</strong> ' + opt.text;
                btn.addEventListener('mouseenter', function(){ if(!answered){ btn.style.background='#f0f9ff'; btn.style.borderColor='#7dd3fc'; } });
                btn.addEventListener('mouseleave', function(){ if(!answered){ btn.style.background='#fff'; btn.style.borderColor='#e2e8f0'; } });
                btn.addEventListener('click', function() {
                    if (answered) return;
                    answered = true; score.answered++;
                    var isCorrect = (opt.letter === correctLetter);
                    if (isCorrect) score.correct++;
                    optDiv.querySelectorAll('button').forEach(function(b) {
                        b.style.cursor = 'default';
                        var lm = b.innerHTML.match(/<strong>([A-D])\)<\/strong>/);
                        var bL = lm ? lm[1] : '';
                        if (bL === correctLetter) { b.style.background='#f0fdf4'; b.style.borderColor='#22c55e'; b.style.color='#15803d'; }
                        else if (b === btn && !isCorrect) { b.style.background='#fef2f2'; b.style.borderColor='#ef4444'; b.style.color='#dc2626'; }
                        else { b.style.opacity='0.4'; }
                    });
                    var exp = document.createElement('div');
                    exp.style.cssText = 'margin-top:6px;padding:6px 10px;border-radius:6px;font-size:11.5px;' + (isCorrect ? 'background:#f0fdf4;color:#15803d;border:1px solid #86efac;' : 'background:#fef2f2;color:#dc2626;border:1px solid #fca5a5;');
                    exp.innerHTML = isCorrect ? '✅ ' + explanation : '❌ Bonne réponse : <strong>' + correctLetter + '</strong> — ' + explanation;
                    qCard.appendChild(exp);
                    messages.scrollTop = messages.scrollHeight;
                    if (score.answered === score.total) {
                        setTimeout(function() {
                            showLevelResult(score.correct, score.total, apiUrl, courseId, convId, onComplete);
                        }, 800);
                    }
                });
                optDiv.appendChild(btn);
            });
            qCard.appendChild(optDiv);
            quizWrapper.appendChild(qCard);
        });
        messages.appendChild(quizWrapper);
        messages.scrollTop = messages.scrollHeight;
    }

    async function showLevelResult(correct, total, apiUrl, courseId, convId, onComplete) {
        var messages = document.getElementById('edo-messages');
        var pct = Math.round((correct / total) * 100);
        var levelInfo = {
            debutant:      { label: '🌱 Débutant',      color: '#059669', bg: 'linear-gradient(135deg,#d1fae5,#a7f3d0)', msg: 'Pas d\'inquiétude, on va construire tes bases ensemble, étape par étape !' },
            intermediaire: { label: '📘 Intermédiaire', color: '#0a9396', bg: 'linear-gradient(135deg,#cffafe,#a5f3fc)', msg: 'Tu as de bonnes bases ! On va approfondir ensemble.' },
            avance:        { label: '🚀 Avancé',         color: '#7c3aed', bg: 'linear-gradient(135deg,#ede9fe,#ddd6fe)', msg: 'Excellent ! Tes explications seront adaptées à ton niveau d\'expertise.' }
        };
        var level = correct <= 4 ? 'debutant' : correct <= 7 ? 'intermediaire' : 'avance';
        var info = levelInfo[level];
        try {
            // FIX : utiliser studentId variable
            await fetch(apiUrl + '/level-save', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ course_id: courseId, student_id: studentId, conversation_id: convId, score: correct, total: total })
            });
        } catch(e) { console.warn('[Edora] Erreur sauvegarde niveau :', e); }
        studentLevel  = level;
        levelQuizDone = true;
        var resultRow = document.createElement('div');
        resultRow.classList.add('edo-bot-row');
        var resAv = document.createElement('div'); resAv.className = 'edo-bot-avatar'; resAv.innerHTML = AVATAR_IMG_SM;
        resultRow.appendChild(resAv);
        var resCard = document.createElement('div');
        resCard.style.cssText = 'background:' + info.bg + ';border:2px solid ' + info.color + ';border-radius:14px;padding:16px 18px;max-width:85%;display:flex;flex-direction:column;gap:8px';
        resCard.innerHTML = '<div style="font-size:15px;font-weight:700;color:' + info.color + ';">' + info.label + ' — ' + correct + '/' + total + ' (' + pct + '%)</div><div style="font-size:12.5px;color:#374151;line-height:1.5;">' + info.msg + '</div><div style="font-size:11.5px;color:#6b7280;margin-top:4px;">Désormais, toutes mes explications seront adaptées à ton niveau. Tu peux maintenant poser ta question ! 😊</div><div class="edo-timestamp">' + getTime() + '</div>';
        resultRow.appendChild(resCard);
        messages.appendChild(resultRow);
        messages.scrollTop = messages.scrollHeight;
        showLevelBadge(level);
        levelQuizPending = false;
        onComplete(correct, total);
    }

    async function checkAndTriggerLevelQuiz(question, apiUrl, courseId, convId, onProceed) {
        if (levelQuizDone || levelQuizPending || isSmallTalk(question)) { onProceed(); return; }
        levelQuizPending = true;
        try {
            var resp = await fetch(apiUrl + '/level-quiz', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                // FIX : utiliser studentId variable
                body: JSON.stringify({ course_id: courseId, student_id: studentId, conversation_id: convId })
            });
            if (!resp.ok) { levelQuizPending = false; onProceed(); return; }
            var data = await resp.json();
            if (data.already_done) {
                studentLevel  = data.level;
                levelQuizDone = true;
                levelQuizPending = false;
                if (studentLevel) showLevelBadge(studentLevel);
                onProceed();
                return;
            }
            renderLevelQuiz(data.quiz, apiUrl, courseId, convId, function(correct, total) { onProceed(); });
        } catch(e) {
            console.warn('[Edora] Erreur quiz niveau :', e);
            levelQuizPending = false;
            onProceed();
        }
    }

    // ── Send question ──────────────────────────────────────────
    async function sendQuestion(question, apiUrl, courseId) {
        var sendBtn = document.getElementById('edo-send');
        var input   = document.getElementById('edo-input');
        lastQuestion = question; lastApiUrl = apiUrl; lastCourseId = courseId;
        sendBtn.disabled = true; input.disabled = true;
        clearSuggestions();
        appendMessage(question, 'user');
        conversationHistory.push({ role: 'user', content: question });

        await checkAndTriggerLevelQuiz(question, apiUrl, courseId, conversationId, async function() {
            var loadingRow = appendMessage('', 'bot', true);
            try {
                var response = await fetch(apiUrl + '/ask', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    // FIX : utiliser studentId variable (plus 0 hardcodé)
                    body: JSON.stringify({
                        question:             question,
                        course_id:            courseId,
                        student_id:           studentId,
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
                var msgEl = document.getElementById('edo-messages');
                var isQuiz = renderInteractiveQuiz(data.answer, msgEl);
                if (!isQuiz) appendMessage(data.answer, 'bot');
                conversationHistory.push({ role: 'assistant', content: data.answer });
                if (data.sources && data.sources.length > 0 && data.found_in_course) {
                    renderSources(data.sources, msgEl);
                }
                if (data.follow_up_questions && data.follow_up_questions.length > 0) {
                    showSuggestions(data.follow_up_questions, apiUrl, courseId);
                }
            } catch (error) {
                if (document.querySelector('.edo-bubble--loading')) {
                    document.querySelector('.edo-bubble--loading').closest('.edo-bot-row').remove();
                }
                appendMessage('⚠️ Je n\'arrive pas à joindre le serveur. Vérifie ta connexion et réessaie.', 'bot');
                console.error('[Edora Chat] Erreur fetch:', error);
            } finally {
                sendBtn.disabled = false; input.disabled = false; input.focus();
            }
        });

        if (levelQuizPending) {
            sendBtn.disabled = false; input.disabled = false;
        }
    }

    function buildFloatingUI(apiUrl, courseId) {
        var fab = document.createElement('button');
        fab.id = 'edo-fab'; fab.className = 'edo-fab';
        fab.setAttribute('aria-label', 'Ouvrir le tuteur IA');
        fab.innerHTML = AVATAR_IMG;

        var panel = document.createElement('div');
        panel.id = 'edo-panel'; panel.className = 'edo-panel';
        panel.innerHTML = '<div class="edo-header"><div class="edo-header__avatar">' + AVATAR_IMG + '</div><div class="edo-header__info"><span class="edo-name">Edora AI Tutor<span class="edo-name-badge">BETA</span></span><span class="edo-subtitle"><span class="edo-dot edo-dot--green"></span>Votre assistant intelligent pour vos cours</span></div><div class="edo-header__actions"><button id="edo-history-btn" class="edo-header__btn" title="Historique des conversations">' + SVG.history + '</button><button id="edo-minimize" class="edo-header__btn" title="Réduire">' + SVG.minimize + '</button><button id="edo-close" class="edo-header__btn" aria-label="Fermer">' + SVG.close + '</button></div></div><div id="edo-messages" class="edo-messages" role="log" aria-live="polite"><div class="edo-bot-row"><div class="edo-bot-avatar">' + AVATAR_IMG_SM + '</div><div class="edo-bubble edo-bubble--bot">Bonjour ! Je suis Edo, votre tuteur IA 👋<br>Posez-moi une question sur le contenu de ce cours.<div class="edo-timestamp">' + getTime() + '</div></div></div></div><div class="edo-shortcuts"><button class="edo-shortcut" data-question="Explique-moi les concepts principaux de ce cours">' + SVG.book + ' Expliquer</button><button class="edo-shortcut" data-question="Génère un quiz de 3 questions QCM sur ce cours">' + SVG.quiz + ' Quiz</button><button class="edo-shortcut" data-question="Donne-moi des exemples concrets tirés de ce cours">' + SVG.bulb + ' Exemple</button><button class="edo-shortcut" data-question="Résume et synthétise le contenu complet de ce cours">' + SVG.list + ' Résumer</button></div><div class="edo-input-row"><button class="edo-input-icon" id="edo-attach" title="Joindre fichier">' + SVG.attach + '</button><input type="file" id="edo-file-input" style="display:none;" accept=".pdf,.doc,.docx,.txt,.pptx"><input type="text" id="edo-input" class="edo-input" placeholder="Posez votre question sur le contenu du cours..." aria-label="Question pour Edo" maxlength="500"/><button class="edo-input-icon" id="edo-vocal" title="Message vocal">' + SVG.mic + '</button><button id="edo-send" class="edo-send-btn" aria-label="Envoyer">' + SVG.send + '</button></div><div class="edo-footer"><span class="edo-footer-icon">' + SVG.shield + '</span><span class="edo-footer-text">Réponses générées à partir du contenu de vos cours. Vérifiez toujours les informations importantes.</span></div>';

        document.body.appendChild(fab);
        document.body.appendChild(panel);
        loadLastConversation(apiUrl, courseId);
        // FIX : plus besoin de passer studentId en paramètre, c'est une variable de module
        loadStudentLevel(apiUrl, courseId);

        fab.addEventListener('click', function () {
            var isOpen = panel.classList.toggle('edo-panel--open');
            fab.classList.toggle('edo-fab--open', isOpen);
            if (isOpen) setTimeout(function() { panel.querySelector('#edo-input').focus(); }, 300);
        });
        panel.querySelector('#edo-history-btn').addEventListener('click', function () { buildHistoryPanel(apiUrl, courseId); });
        panel.querySelector('#edo-close').addEventListener('click', function () { panel.classList.remove('edo-panel--open'); fab.classList.remove('edo-fab--open'); });
        panel.querySelector('#edo-minimize').addEventListener('click', function () {
            var els = ['#edo-messages', '.edo-shortcuts', '.edo-footer', '.edo-input-row', '.edo-dynamic-suggestions'];
            var messages = panel.querySelector('#edo-messages');
            var min = messages.style.display === 'none';
            els.forEach(function(sel) { var el = panel.querySelector(sel); if (!el) return; var isGrid = sel === '.edo-shortcuts'; el.style.display = min ? (isGrid ? 'grid' : 'flex') : 'none'; });
        });
        panel.querySelectorAll('.edo-shortcut').forEach(function (btn) {
            btn.addEventListener('click', function () { var q = btn.dataset.question; if (q) sendQuestion(q, apiUrl, courseId); });
        });

        var attachBtn = panel.querySelector('#edo-attach');
        var fileInput = panel.querySelector('#edo-file-input');
        attachBtn.addEventListener('click', function () { fileInput.click(); });
        fileInput.addEventListener('change', async function () {
            var file = fileInput.files[0]; if (!file) return;
            appendMessage('📎 Fichier joint : ' + file.name, 'user');
            var lr = appendMessage('', 'bot', true);
            try {
                var fd = new FormData(); fd.append('file', file); fd.append('course_id', courseId);
                var r = await fetch(apiUrl + '/upload-file', { method: 'POST', body: fd });
                lr.remove(); if (!r.ok) throw new Error('HTTP ' + r.status);
                var d = await r.json();
                appendMessage('✅ Fichier indexé ! ' + d.chunks_created + ' extraits créés.', 'bot');
            } catch (e) { lr.remove(); appendMessage('⚠️ Erreur lors de l\'upload du fichier.', 'bot'); }
            fileInput.value = '';
        });

        var vocalBtn  = panel.querySelector('#edo-vocal');
        var textInput = panel.querySelector('#edo-input');
        if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
            var SR = window.SpeechRecognition || window.webkitSpeechRecognition;
            var recognition = new SR(); recognition.lang = 'fr-FR'; recognition.continuous = false; recognition.interimResults = false;
            var isListening = false;
            vocalBtn.addEventListener('click', function () { if (isListening) { recognition.stop(); return; } recognition.start(); });
            recognition.onstart  = function () { isListening = true;  vocalBtn.style.color = '#ec4899'; };
            recognition.onresult = function (e) { textInput.value = e.results[0][0].transcript; textInput.focus(); };
            recognition.onend    = function () { isListening = false; vocalBtn.style.color = ''; };
            recognition.onerror  = function (e) { isListening = false; vocalBtn.style.color = ''; if (e.error === 'not-allowed') appendMessage('⚠️ Accès au microphone refusé.', 'bot'); };
        } else { vocalBtn.style.opacity = '0.4'; vocalBtn.style.cursor = 'not-allowed'; }

        var sendBtn = panel.querySelector('#edo-send');
        sendBtn.addEventListener('click', function () { var q = textInput.value.trim(); if (!q) return; textInput.value = ''; sendQuestion(q, apiUrl, courseId); });
        textInput.addEventListener('keydown', function (e) { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendBtn.click(); } });
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