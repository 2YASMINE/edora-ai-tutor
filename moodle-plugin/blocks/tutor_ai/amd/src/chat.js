/**
 * Edora AI Tutor — Module chat
 * @author Islem Troudi — Phase 6
 */

(function () {

    let conversationHistory = [];
    let conversationId = 'conv-' + Date.now();

    function appendMessage(text, role, loading) {
        const messages = document.getElementById('edo-messages');
        const bubble = document.createElement('div');
        bubble.classList.add('edo-bubble', 'edo-bubble--' + role);

        if (loading) {
            bubble.classList.add('edo-bubble--loading');
            bubble.innerHTML = '<span class="edo-spinner"></span> Edo réfléchit…';
        } else {
            bubble.innerHTML = text.replace(/\n/g, '<br>');
        }

        messages.appendChild(bubble);
        messages.scrollTop = messages.scrollHeight;
        return bubble;
    }

    async function sendQuestion(question, apiUrl, courseId) {
        const sendBtn = document.getElementById('edo-send');
        const input   = document.getElementById('edo-input');

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

            if (!response.ok) {
                throw new Error('HTTP ' + response.status);
            }

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

    function init() {
        const root    = document.getElementById('edo-chat-root');
        const input   = document.getElementById('edo-input');
        const sendBtn = document.getElementById('edo-send');

        if (!root || !input || !sendBtn) {
            console.error('[Edora Chat] Éléments DOM introuvables.');
            return;
        }

        const apiUrl   = root.dataset.apiUrl;
        const courseId = parseInt(root.dataset.courseId, 10);

        sendBtn.addEventListener('click', function () {
            const question = input.value.trim();
            if (!question) return;
            input.value = '';
            sendQuestion(question, apiUrl, courseId);
        });

        input.addEventListener('keydown', function (e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendBtn.click();
            }
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();